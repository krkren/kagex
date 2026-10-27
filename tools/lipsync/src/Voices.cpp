#include "Voices.h"

#include <algorithm>
#include <map>
#include <set>

#include "Archive.h"
#include "Engine.h"
#include "Host.h"
#include "Subprocess.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

std::string lower(std::string s)
{
	std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return (char)std::tolower(c); });
	return s;
}

bool isSound(const fs::path& p)
{
	const std::string e = lower(krt::fromPath(p.extension()));
	return e == ".wav" || e == ".ogg" || e == ".opus" || e == ".flac";
}

// UTF-16LE (with or without its BOM) to UTF-8
std::string utf16leToUtf8(const std::string& in)
{
	std::string out;
	size_t i = (in.size() >= 2 && (unsigned char)in[0] == 0xFF && (unsigned char)in[1] == 0xFE) ? 2 : 0;
	while (i + 1 < in.size()) {
		unsigned cp = (unsigned char)in[i] | ((unsigned char)in[i + 1] << 8);
		i += 2;
		if (cp >= 0xD800 && cp < 0xDC00 && i + 1 < in.size()) {
			const unsigned lo = (unsigned char)in[i] | ((unsigned char)in[i + 1] << 8);
			if (lo >= 0xDC00 && lo < 0xE000) {
				cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
				i += 2;
			}
		}
		if (cp < 0x80) out += (char)cp;
		else if (cp < 0x800) { out += (char)(0xC0 | (cp >> 6)); out += (char)(0x80 | (cp & 0x3F)); }
		else if (cp < 0x10000) { out += (char)(0xE0 | (cp >> 12)); out += (char)(0x80 | ((cp >> 6) & 0x3F)); out += (char)(0x80 | (cp & 0x3F)); }
		else { out += (char)(0xF0 | (cp >> 18)); out += (char)(0x80 | ((cp >> 12) & 0x3F)); out += (char)(0x80 | ((cp >> 6) & 0x3F)); out += (char)(0x80 | (cp & 0x3F)); }
	}
	return out;
}

std::vector<std::string> splitLines(const std::string& text)
{
	std::vector<std::string> out;
	size_t pos = 0;
	while (pos <= text.size()) {
		size_t end = text.find('\n', pos);
		if (end == std::string::npos) end = text.size();
		std::string line = text.substr(pos, end - pos);
		if (!line.empty() && line.back() == '\r') line.pop_back();
		out.push_back(line);
		pos = end + 1;
	}
	return out;
}

std::vector<std::string> splitTabs(const std::string& line)
{
	std::vector<std::string> f;
	size_t pos = 0;
	while (true) {
		const size_t t = line.find('\t', pos);
		f.push_back(line.substr(pos, t == std::string::npos ? std::string::npos : t - pos));
		if (t == std::string::npos) break;
		pos = t + 1;
	}
	return f;
}

// A folder of the game's data that isn't the framework's (data/system), relative to data/
bool inFramework(const fs::path& rel)
{
	auto it = rel.begin();
	return it != rel.end() && lower(krt::fromPath(*it)) == "system";
}

// Whether a script can voice a line: it has a speaker's name (【...】) or sets a voice (voice=,
// nextvoice=). The others (system screens, macros) aren't worth compiling, and some can't be
// ([call] and [return] aren't for compiled scenarios). In UTF-8, Shift_JIS or UTF-16LE
bool mayHaveVoices(const fs::path& script)
{
	std::string d;
	if (!krt::readFile(script, d)) return false;
	static const std::string marks[] = { "\xE3\x80\x90", "\x81\x79", std::string("\x10\x30", 2), "voice=", "voice =",
	                                     std::string("v\0o\0i\0c\0e\0=\0", 12) };
	for (const auto& m : marks) if (d.find(m) != std::string::npos) return true;
	return false;
}

} // namespace

bool findGameEngine(const Project& project, const fs::path& enginesDir, krt::Progress& progress, fs::path& exe, std::string& error)
{
	std::error_code ec;
	if (!project.engine.empty() && fs::is_regular_file(project.engine, ec)) { exe = project.engine; return true; }
	const std::string host = hostId();
	fs::path dir;
	if (!ensureEngine(host, false, localEngines(enginesDir, project.root), progress, dir, error)) return false;
	if (host == "windows") { exe = dir / "krkrz.exe"; return true; }
	if (host == "linux") { exe = dir / "krkrz"; return true; }
	// macOS: a copy of the app, signed ad hoc (an unsigned one isn't allowed to start)
	fs::path src;
	for (const auto& e : fs::directory_iterator(dir, ec))
		if (e.is_directory(ec) && e.path().extension() == ".app") src = e.path();
	if (src.empty()) { error = "The macOS engine package has no .app"; return false; }
	const fs::path app = cacheDir() / "lipsync-engine" / src.filename();
	const fs::path bin = app / "Contents" / "MacOS" / "krkrz";
	if (!fs::is_regular_file(bin, ec) || fs::last_write_time(bin, ec) < fs::last_write_time(src / "Contents" / "MacOS" / "krkrz", ec)) {
		fs::remove_all(app, ec);
		fs::create_directories(app.parent_path(), ec);
		fs::copy(src, app, fs::copy_options::recursive | fs::copy_options::copy_symlinks, ec);
		if (ec) { error = "Can't copy the engine: " + ec.message(); return false; }
		fs::remove_all(app / "Contents" / "_CodeSignature", ec);
		RunOptions opt;
		opt.timeoutSeconds = 600;
		const RunResult r = run("codesign", { "--force", "--deep", "--sign", "-", krt::fromPath(app) }, opt);
		if (!r.ok()) { error = "codesign failed: " + krt::trim(r.output); return false; }
	}
	exe = bin;
	return true;
}

bool readVoiceLines(const Project& project, const fs::path& engine, krt::Progress& progress,
                    std::vector<VoiceLine>& lines, std::vector<std::string>& problems, std::string& log, std::string& error)
{
	lines.clear();
	problems.clear();
	std::error_code ec;
	// every script of the game (its own, not the framework's): the compiler gives the voiced ones
	std::vector<std::string> scripts;
	std::set<std::string> seen;
	for (fs::recursive_directory_iterator it(project.data, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		if (!it->is_regular_file(ec) || lower(krt::fromPath(it->path().extension())) != ".ks") continue;
		const fs::path rel = it->path().lexically_relative(project.data);
		if (inFramework(rel)) continue;
		const std::string name = krt::fromPath(it->path().filename());
		if (seen.count(lower(name)) || !mayHaveVoices(it->path())) continue;
		seen.insert(lower(name));
		scripts.push_back(name);
	}
	std::sort(scripts.begin(), scripts.end());
	Sha256 h;
	const std::string root = krt::fromPath(project.root);
	h.update(root.data(), root.size());
	const fs::path work = cacheDir() / "lipsync-lines" / h.hex().substr(0, 16);
	fs::remove_all(work, ec);
	fs::create_directories(work / "save", ec);
	std::string list = "\xEF\xBB\xBF";
	for (const auto& s : scripts) list += s + "\n";
	const fs::path listFile = work / "scripts.txt";
	if (!krt::writeFile(listFile, list)) { error = "Can't write " + krt::fromPath(listFile); return false; }

	RunOptions opt;
	opt.timeoutSeconds = 900;
	opt.workDir = engine.parent_path();
	opt.env = { { "SDL_AUDIO_DRIVER", "dummy" } };
	if (std::string(hostId()) == "linux") opt.env.push_back({ "SDL_VIDEO_DRIVER", "offscreen" });
	opt.canceled = [&progress]() { return progress.canceled(); };
	progress.progress(-1, "Reading the lines of " + std::to_string(scripts.size()) + " scripts");
	const RunResult r = run(krt::fromPath(engine), { krt::fromPath(project.data), "-voicelines=" + krt::fromPath(listFile),
	                                                 "-datapath=" + krt::fromPath(work / "save") + "/" }, opt);
	if (progress.canceled()) { error = "Canceled"; return false; }
	std::string raw;
	if (krt::readFile(work / "save" / "krkr.console.log", raw)) log = utf16leToUtf8(raw);
	if (log.empty()) log = r.output;
	std::string summary;
	for (const auto& line : splitLines(log)) {
		if (line.find("Voice lines: ") != std::string::npos) summary = line.substr(line.find("Voice lines: "));
		else if (line.find("Script exception raised") != std::string::npos ||
		         line.find("\xe3\x82\xb9\xe3\x82\xaf\xe3\x83\xaa\xe3\x83\x97\xe3\x83\x88\xe3\x81\xa7\xe4\xbe\x8b\xe5\xa4\x96") != std::string::npos)
			problems.push_back(krt::trim(line));
		else if (!summary.empty() && line.find("   ") != std::string::npos)
			problems.push_back(krt::trim(line.substr(line.find("   "))));   // "<time>   <script>: <error>"
	}
	const fs::path outFile = fs::path(krt::fromPath(listFile) + ".out");
	if (!krt::readFile(outFile, raw)) {
		if (summary.empty())
			error = r.started ? "The game didn't list its lines: it needs the World and this KAGEX's framework (template/system, for -voicelines)"
			                  : "The engine couldn't be started: " + krt::trim(r.output);
		else
			error = "The game didn't write its lines";
		if (!problems.empty()) error += " (" + problems.front() + ")";
		return false;
	}
	for (const auto& line : splitLines(utf16leToUtf8(raw))) {
		if (line.empty()) continue;
		const auto f = splitTabs(line);
		if (f.size() < 5) continue;
		lines.push_back({ f[0], f[1], f[2], f[3], f[4], f.size() >= 6 ? f[5] : std::string() });
	}
	return true;
}

std::vector<Voice> listVoices(const Project& project, const std::vector<VoiceLine>& lines, const std::vector<std::string>& extra)
{
	// every sound in the game's data, by name (the engine finds files by name alone)
	std::map<std::string, fs::path> sounds;
	std::vector<fs::path> voiceFolderSounds;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(project.data, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		if (!it->is_regular_file(ec) || !isSound(it->path())) continue;
		const fs::path rel = it->path().lexically_relative(project.data);
		if (inFramework(rel)) continue;
		sounds.emplace(lower(krt::fromPath(it->path().filename())), it->path());
		for (const auto& part : rel.parent_path())
			if (lower(krt::fromPath(part)) == "voice") { voiceFolderSounds.push_back(it->path()); break; }
	}
	std::vector<Voice> out;
	std::map<std::string, size_t> byName;
	auto add = [&](const std::string& name) -> Voice& {
		const std::string key = lower(name);
		auto it = byName.find(key);
		if (it != byName.end()) return out[it->second];
		Voice v;
		v.name = name;
		auto s = sounds.find(key);
		if (s != sounds.end()) v.file = s->second;
		byName[key] = out.size();
		out.push_back(std::move(v));
		return out.back();
	};
	for (const auto& l : lines) add(l.voice).lines.push_back(l);
	for (const auto& f : voiceFolderSounds) add(krt::fromPath(f.filename()));
	for (const auto& n : extra) add(n);
	for (auto& v : out) refreshVoice(v);
	std::stable_sort(out.begin(), out.end(), [](const Voice& a, const Voice& b) { return lower(a.name) < lower(b.name); });
	return out;
}

std::vector<Voice> voicesWithTracks(const Project& project)
{
	std::vector<Voice> out;
	std::error_code ec;
	for (fs::recursive_directory_iterator it(project.data, ec), end; it != end; it.increment(ec)) {
		if (ec) break;
		if (!it->is_regular_file(ec) || lower(krt::fromPath(it->path().extension())) != ".lip") continue;
		if (inFramework(it->path().lexically_relative(project.data))) continue;
		Voice v;
		v.file = voiceOfLip(it->path());
		v.name = krt::fromPath((v.file.empty() ? it->path() : v.file).filename());
		refreshVoice(v);
		if (v.file.empty()) {
			v.lip = it->path();
			v.header = readLipHeader(v.lip);
		}
		out.push_back(std::move(v));
	}
	std::sort(out.begin(), out.end(), [](const Voice& a, const Voice& b) { return lower(a.name) < lower(b.name); });
	return out;
}

void refreshVoice(Voice& v)
{
	std::error_code ec;
	if (v.file.empty() || !fs::is_regular_file(v.file, ec)) {
		v.lip.clear();
		v.header = LipHeader();
		v.status = "missing";
		return;
	}
	v.lip = v.file.parent_path() / (krt::fromPath(v.file.stem()) + ".lip");
	v.header = readLipHeader(v.lip);
	if (!v.header.exists) { v.status = "none"; return; }
	if (!v.header.ours) { v.status = "manual"; return; }
	std::string hex, err;
	v.status = sha256File(v.file, hex, err) && hex == v.header.voiceHash ? "current" : "stale";
}

std::vector<std::string> lineTextsFor(const Voice& v)
{
	std::vector<std::string> out;
	for (const auto& l : v.lines) {
		const std::string t = krt::trim(l.reading.empty() ? l.text : l.reading);
		if (!t.empty() && std::find(out.begin(), out.end(), t) == out.end()) out.push_back(t);
	}
	return out;
}

bool writeLip(const Voice& voice, const std::string& text, const AlignResult& r, std::string& error)
{
	std::string hex;
	if (!sha256File(voice.file, hex, error)) return false;
	std::string t = text;
	for (auto& c : t) if (c == '\n' || c == '\r') c = ' ';
	std::string out;
	out += "# kagex-lipsync " KAGEX_RELEASE_VERSION ": the mouth over " + voice.name + ", from its line (tools/lipsync)\n";
	out += "# voice: " + hex + "\n";
	out += "# text: " + t + "\n";
	out += "# language: " + r.language + "\n";
	out += "# ms, the mouth from then on (a i u e o, n for the lips closed, - for any other sound), how open (0-2)\n";
	for (const auto& m : r.marks) out += std::to_string(m.ms) + "\t" + m.mouth + "\t" + std::to_string(m.open) + "\n";
	// replaced, not written into: a file another program has hard-linked stays as it was
	const fs::path tmp = fs::path(krt::fromPath(voice.lip) + ".tmp");
	if (!krt::writeFile(tmp, out)) { error = "Can't write " + krt::fromPath(tmp); return false; }
	std::error_code ec;
	fs::rename(tmp, voice.lip, ec);
	if (ec) {
		fs::remove(voice.lip, ec);
		fs::rename(tmp, voice.lip, ec);
		if (ec) { error = "Can't write " + krt::fromPath(voice.lip) + ": " + ec.message(); return false; }
	}
	return true;
}

} // namespace kr
