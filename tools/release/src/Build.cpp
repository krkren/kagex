#include "Build.h"

#include <algorithm>
#include <chrono>
#include <cstring>
#include <map>
#include <regex>
#include <set>
#include <thread>

#include "Archive.h"
#include "Encrypt.h"
#include "Engine.h"
#include "Host.h"
#include "Icons.h"
#include "Keys.h"
#include "Media.h"
#include "Plan.h"
#include "Sign.h"
#include "Scripts.h"
#include "Scenes.h"
#include "Subprocess.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"
#include "krt/xp3/Xp3.h"
#include "KagexWebJs.h"

#ifdef KR_HAVE_RELEASE_LIB
#include "krt/release/Release.h"
#endif
#ifndef _WIN32
#include <sys/stat.h>
#endif

namespace fs = std::filesystem;

namespace kr {

namespace {

// Progress of one part of the build, as a share of the whole
class PartProgress : public krt::Progress {
public:
	PartProgress(krt::Progress& outer, double from, double to) : outer_(outer), from_(from), to_(to) {}
	void progress(double r, const std::string& m) override { outer_.progress(r < 0 ? -1 : from_ + (to_ - from_) * r, m); }
	void log(const std::string& line) override { outer_.log(line); }
	bool canceled() const override { return outer_.canceled(); }
private:
	krt::Progress& outer_;
	double from_, to_;
};

struct Failure {
	std::string message;
};

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

void mustMkdirs(const fs::path& p)
{
	std::error_code ec;
	fs::create_directories(p, ec);
	if (ec) throw Failure{ "Can't create " + krt::fromPath(p) + ": " + ec.message() };
}

void mustRemove(const fs::path& p)
{
	std::error_code ec;
	fs::remove_all(p, ec);
	if (ec) throw Failure{ "Can't remove " + krt::fromPath(p) + " (is it open somewhere?): " + ec.message() };
}

void copyFile(const fs::path& from, const fs::path& to)
{
	std::error_code ec;
	fs::create_directories(to.parent_path(), ec);
	fs::copy_file(from, to, fs::copy_options::overwrite_existing, ec);
	if (ec) throw Failure{ "Can't copy " + krt::fromPath(from) + " to " + krt::fromPath(to) + ": " + ec.message() };
}

// A folder, with its symbolic links as links
void copyTree(const fs::path& from, const fs::path& to)
{
	std::error_code ec;
	fs::create_directories(to, ec);
	fs::copy(from, to, fs::copy_options::recursive | fs::copy_options::copy_symlinks | fs::copy_options::overwrite_existing, ec);
	if (ec) throw Failure{ "Can't copy " + krt::fromPath(from) + ": " + ec.message() };
}

void writeText(const fs::path& p, const std::string& text)
{
	std::error_code ec;
	fs::create_directories(p.parent_path(), ec);
	if (!krt::writeFile(p, text)) throw Failure{ "Can't write " + krt::fromPath(p) };
}

void makeExecutable(const fs::path& p)
{
#ifndef _WIN32
	::chmod(p.c_str(), 0755);
#else
	(void)p;
#endif
}

uint64_t treeSize(const fs::path& p)
{
	std::error_code ec;
	if (fs::is_regular_file(p, ec)) return fs::file_size(p, ec);
	uint64_t n = 0;
	for (fs::recursive_directory_iterator it(p, ec), end; it != end; it.increment(ec))
		if (!ec && it->is_regular_file(ec)) n += it->file_size(ec);
	return n;
}

std::string xmlEscape(const std::string& s)
{
	std::string o;
	for (char c : s) {
		if (c == '&') o += "&amp;";
		else if (c == '<') o += "&lt;";
		else if (c == '>') o += "&gt;";
		else o += c;
	}
	return o;
}

// Sets a top-level <string> in an XML property list (adds the key when it isn't there)
void plistSet(std::string& xml, const std::string& key, const std::string& value)
{
	const std::string k = "<key>" + key + "</key>";
	size_t at = xml.find(k);
	const std::string v = "<string>" + xmlEscape(value) + "</string>";
	if (at != std::string::npos) {
		size_t s = xml.find('<', at + k.size());
		if (s != std::string::npos && xml.compare(s, 8, "<string>") == 0) {
			const size_t e = xml.find("</string>", s);
			if (e != std::string::npos) { xml.replace(s, e + 9 - s, v); return; }
		}
		if (s != std::string::npos && xml.compare(s, 9, "<string/>") == 0) { xml.replace(s, 9, v); return; }
		return;
	}
	const size_t end = xml.rfind("</dict>");
	if (end != std::string::npos) xml.insert(end, "\t" + k + "\n\t" + v + "\n");
}

std::string plistGet(const std::string& xml, const std::string& key)
{
	const std::string k = "<key>" + key + "</key>";
	const size_t at = xml.find(k);
	if (at == std::string::npos) return "";
	const size_t s = xml.find("<string>", at);
	const size_t e = xml.find("</string>", s);
	if (s == std::string::npos || e == std::string::npos) return "";
	return xml.substr(s + 8, e - s - 8);
}

std::string fileSafe(const std::string& s)
{
	std::string o;
	for (char c : s) o += (c == '/' || c == '\\' || c == ':' || c == '*' || c == '?' || c == '"' || c == '<' || c == '>' || c == '|') ? '-' : c;
	while (!o.empty() && (o.back() == ' ' || o.back() == '.')) o.pop_back();
	return o.empty() ? "Game" : o;
}

// UTF-16LE (the engine's console log) to UTF-8
std::string utf16leToUtf8(const std::string& in)
{
	std::string out;
	size_t i = (in.size() >= 2 && (unsigned char)in[0] == 0xFF && (unsigned char)in[1] == 0xFE) ? 2 : 0;
	for (; i + 1 < in.size(); i += 2) {
		uint32_t c = (unsigned char)in[i] | ((unsigned char)in[i + 1] << 8);
		if (c >= 0xD800 && c < 0xDC00 && i + 3 < in.size()) {
			const uint32_t lo = (unsigned char)in[i + 2] | ((unsigned char)in[i + 3] << 8);
			if (lo >= 0xDC00 && lo < 0xE000) { c = 0x10000 + ((c - 0xD800) << 10) + (lo - 0xDC00); i += 2; }
		}
		if (c < 0x80) out += (char)c;
		else if (c < 0x800) { out += (char)(0xC0 | c >> 6); out += (char)(0x80 | (c & 63)); }
		else if (c < 0x10000) { out += (char)(0xE0 | c >> 12); out += (char)(0x80 | ((c >> 6) & 63)); out += (char)(0x80 | (c & 63)); }
		else { out += (char)(0xF0 | c >> 18); out += (char)(0x80 | ((c >> 12) & 63)); out += (char)(0x80 | ((c >> 6) & 63)); out += (char)(0x80 | (c & 63)); }
	}
	return out;
}

} // namespace

std::string engineConfig(const Json& s, const Project& p)
{
	std::string out = "; " + str(s, "identity.title") + " " + str(s, "identity.version") +
	                  ": engine options (each line is a command-line option without its \"-\")\n";
	// the developer's own options from krkrz.cf, without the ones written below
	std::string text;
	if (krt::readFile(p.root / "krkrz.cf", text)) {
		size_t pos = 0;
		while (pos < text.size()) {
			size_t end = text.find('\n', pos);
			if (end == std::string::npos) end = text.size();
			std::string line = text.substr(pos, end - pos);
			pos = end + 1;
			if (!line.empty() && line.back() == '\r') line.pop_back();
			const std::string t = krt::trim(line);
			if (t.empty() || t[0] == ';') continue;
			const std::string key = lower(krt::trim(t.substr(0, t.find('='))));
			if (key == "orgname" || key == "appname" || key == "debugwin") continue;
			out += t + "\n";
		}
	}
	out += "orgname=" + str(s, "identity.orgName") + "\n";
	out += "appname=" + str(s, "identity.appName") + "\n";
	if (!flag(s, "engine.debug")) out += "debugwin=no\n";
	return out;
}

namespace {

class Builder {
public:
	Builder(const Json& s, const Project& p, const BuildOptions& o, krt::Progress& pr) : s_(s), p_(p), o_(o), pr_(pr) {}
	~Builder()
	{
		wipeArchiveKey(archiveKey_);
		wipeSceneKey(key_);
		std::fill(privPem_.begin(), privPem_.end(), '\0');
	}

	Json execute()
	{
		Json result = Json::object();
		Json outputs = Json::array();
		bool ok = true;
		try {
			const auto issues = validate(s_, p_);
			for (const auto& i : issues) {
				if (i.level == "error") throw Failure{ "The settings have problems: " + i.field + ": " + i.message };
			}
			for (const auto& pl : platforms()) {
				const std::string id = pl.id;
				const bool chosen = o_.only.empty() ? flag(s_, "platforms." + id + ".enabled")
				                                    : std::find(o_.only.begin(), o_.only.end(), id) != o_.only.end();
				if (chosen) chosen_.push_back(id);
			}
			if (chosen_.empty() && str(s_, "output.patchFrom").empty()) throw Failure{ "No platform to build" };

			// engine packages in engines/ next to data/ (or --engines, KAGEX_RELEASE_ENGINES)
			// come before the cache
			o_.engines = localEngines(o_.engines, p_.root);
			if (!o_.engines.empty()) pr_.log("Engine packages from " + krt::fromPath(o_.engines));

			out_ = fs::weakly_canonical(p_.root / krt::toPath(str(s_, "output.folder")));
			work_ = out_ / ".work";
			mustRemove(work_);
			mustMkdirs(work_);

			// the keys, from the game's keys file, up front: a bad or missing key stops the build
			// before it does any work. Each kind of protection has a key of its own (Keys.h)
			{
				const KeysNeeded need = keysNeeded(s_);
				GameKeys keys;
				std::string err;
				if (!loadKeys(s_, p_, need, keys, err)) throw Failure{ err };
				signing_ = need.signing;
				if (signing_) {
					privPem_ = keys.signing;
					if (!derivePublicKey(privPem_, pubPem_, err)) throw Failure{ "Signing: " + err };
				}
				if (need.archive) {
					if (!canEncryptArchive()) throw Failure{ "This kagex-release was built without xp3crypt, so it can't encrypt the archive" };
					archiveKey_ = keys.archive;
					haveArchiveKey_ = true;
					hashNames_ = flag(s_, "archive.hideNames");
				}
				if (need.scenes) {
					if (!canEncryptScenes()) throw Failure{ "This kagex-release was built without scnfile, so it can't encrypt scenarios" };
					key_ = keys.scenes;
					haveKey_ = true;
				}
			}

			stage(PartProgress(pr_, 0.0, 0.05));
			media(PartProgress(pr_, 0.05, 0.2));
			scenes(PartProgress(pr_, 0.2, 0.21));   // before signStage: a compiling run of a signed game would refuse its options
			signStage();   // write the public key and the self-test into the data (before it is compiled/hashed/packed)
			if (flag(s_, "contents.compileScripts")) scripts(PartProgress(pr_, 0.21, 0.22));
			fileList(PartProgress(pr_, 0.22, 0.25));
			if (!str(s_, "output.patchFrom").empty()) outputs.push(patch(PartProgress(pr_, 0.25, 0.25)));
			if (hashNames_) packHashed(PartProgress(pr_, 0.25, 0.35));
			else if (needsXp3()) { splitIfNeeded(PartProgress(pr_, 0.25, 0.27)); packXp3(PartProgress(pr_, 0.27, 0.35)); }
			prepareIcons();

			const double span = 0.6 / std::max<size_t>(1, chosen_.size());
			for (size_t i = 0; i < chosen_.size(); ++i) {
				const std::string id = chosen_[i];
				PartProgress part(pr_, 0.35 + span * i, 0.35 + span * (i + 1));
				Json o = Json::object();
				o.set("platform", Json(id));
				for (const auto& pl : platforms()) if (id == pl.id) o.set("title", Json(pl.title));
				try {
					if (pr_.canceled()) throw Failure{ "Canceled" };
					const PlatformStatus st = checkPlatform(id, s_, p_);
					if (!st.possible) {
						std::string why;
						for (const auto& r : st.requirements) if (!r.ok) why += (why.empty() ? "" : "; ") + r.name + ": " + r.detail;
						throw Failure{ "Can't be built on this computer: " + why };
					}
					fs::path folder, package;
					buildPlatform(id, part, folder, package);
					o.set("ok", Json(true));
					o.set("folder", Json(krt::fromPath(folder)));
					o.set("package", Json(krt::fromPath(package)));
					o.set("bytes", Json((long long)treeSize(package.empty() ? folder : package)));
					if (!package.empty()) packages_.push_back(package);
					built_[id] = folder;
				} catch (const Failure& f) {
					ok = false;
					o.set("ok", Json(false));
					o.set("error", Json(f.message));
					pr_.log(id + ": " + f.message);
				}
				outputs.push(std::move(o));
			}
			if (patchFailed_) ok = false;
			if (flag(s_, "output.checksums") && !packages_.empty()) writeChecksums();
			if (flag(s_, "output.check")) {
				Json check = testRun(PartProgress(pr_, 0.95, 1.0));
				if (check.has("ok") && !check["ok"].asBool()) ok = false;
				result.set("check", std::move(check));
			}
			if (!o_.keepWork) {
				std::error_code ec;
				fs::remove_all(work_, ec);
			}
		} catch (const Failure& f) {
			ok = false;
			result.set("error", Json(f.message));
		} catch (const std::exception& e) {
			ok = false;
			result.set("error", Json(std::string("Unexpected error: ") + e.what()));
		}
		pr_.progress(1.0, ok ? "Done" : "Finished with errors");
		result.set("ok", Json(ok));
		result.set("outputFolder", Json(krt::fromPath(out_)));
		result.set("outputs", std::move(outputs));
		result.set("notes", Json::array(notes_));
		if (media_.isObj()) result.set("media", media_);
		if (scripts_.isObj()) result.set("scripts", scripts_);
		{
			// what the packages are protected with (the keys file's keys)
			Json prot = Json::object();
			prot.set("archive", Json(std::string(!haveArchiveKey_ ? "plain" : hashNames_ ? "encrypted, names hidden" : "encrypted")));
			prot.set("scenes", Json(std::string(scenesSealed_ ? "encrypted" : scenesPsb_ ? "plain .scn" : "not compiled to .scn")));
			prot.set("signed", Json(signing_));
			result.set("protection", std::move(prot));
		}
		return result;
	}

private:
	//-----------------------------------------------------------------------
	// The game's files
	//-----------------------------------------------------------------------
	void stage(krt::Progress&& pr)
	{
		stage_ = work_ / "data";
		pr.progress(0, "Collecting the game's files");
		const auto files = collectGameFiles(s_, p_);
		std::error_code ec;
		size_t i = 0;
		for (const auto& f : files) {
			if ((++i & 63) == 0) {
				pr.progress((double)i / files.size(), "Collecting the game's files");
				if (pr.canceled()) throw Failure{ "Canceled" };
			}
			const fs::path to = stage_ / krt::toPath(f.name);
			fs::create_directories(to.parent_path(), ec);
			// a hard link where it can be (nothing writes to the staged files), else a copy
			fs::create_hard_link(f.source, to, ec);
			if (ec) copyFile(f.source, to);
		}
		pr.log("Game files: " + std::to_string(files.size()));
		linked_ = linkedPlugins();
	}

	void media(krt::Progress&& pr)
	{
		MediaResult m;
		std::string err;
		if (!convertMedia(s_, stage_, pr, m, err)) throw Failure{ err };
		if (m.images || m.sounds) {
			const auto mb = [](uint64_t b) { return std::to_string((b + 524288) / 1048576) + " MB"; };
			pr.log("Converted " + std::to_string(m.images) + " images and " + std::to_string(m.sounds) + " sounds (" +
			       std::to_string(m.fromCache) + " from the cache): " + mb(m.bytesBefore) + " -> " + mb(m.bytesAfter));
		}
		if (m.rewrittenScripts) pr.log("Rewrote the file names in " + std::to_string(m.rewrittenScripts) + " scripts");
		for (const auto& n : m.notes) { pr.log(n); notes_.push_back(n); }
		media_ = Json::object();
		media_.set("images", Json(m.images));
		media_.set("sounds", Json(m.sounds));
		media_.set("fromCache", Json(m.fromCache));
		media_.set("bytesBefore", Json((long long)m.bytesBefore));
		media_.set("bytesAfter", Json((long long)m.bytesAfter));
		media_.set("keptByReference", Json(m.keptByReference));
		media_.set("keptForEffects", Json(m.keptForEffects));
		media_.set("rewrittenScripts", Json(m.rewrittenScripts));
	}

	//-----------------------------------------------------------------------
	// The scripts, compiled to bytecode by this computer's engine (Scripts.h)
	//-----------------------------------------------------------------------
	void scripts(krt::Progress&& pr)
	{
		const fs::path exe = compileEngine(pr);
		ScriptsResult r;
		std::string err;
		const bool ok = compileScripts(s_, p_, stage_, exe, work_, pr, r, err);
		const fs::path logFile = out_ / "compile-scripts.log";
		if (!r.log.empty()) writeText(logFile, r.log);
		if (!ok) throw Failure{ err };
		std::string line = "Compiled " + std::to_string(r.compiled) + " scripts to bytecode";
		std::vector<std::string> parts;
		if (r.expressions) parts.push_back(std::to_string(r.expressions) + " as expressions");
		if (r.fixed) parts.push_back(std::to_string(r.fixed) + " with constants beyond 32 bits put right");
		if (!parts.empty()) {
			line += " (";
			for (size_t i = 0; i < parts.size(); ++i) line += (i ? "; " : "") + parts[i];
			line += ")";
		}
		pr.log(line);
		Json kept = Json::array();
		for (const auto& [name, why] : r.kept) {
			const std::string note = "Kept as source: " + name + ": " + why;
			pr.log(note);
			notes_.push_back(note);
			Json k = Json::object();
			k.set("name", Json(name));
			k.set("why", Json(why));
			kept.push(std::move(k));
		}
		scripts_ = Json::object();
		scripts_.set("compiled", Json(r.compiled));
		scripts_.set("expressions", Json(r.expressions));
		scripts_.set("fixed", Json(r.fixed));
		scripts_.set("truncates", Json(r.truncates));
		scripts_.set("kept", std::move(kept));
		scripts_.set("log", Json(krt::fromPath(logFile)));
	}

	// This computer's engine, from its package (on macOS a copy of the app, signed: an unsigned
	// one isn't allowed to start)
	fs::path compileEngine(krt::Progress& pr)
	{
		const std::string host = hostId();
		fs::path engine;
		std::string err;
		pr.progress(-1, "Getting this computer's engine to compile the scripts");
		if (!ensureEngine(host, flag(s_, "engine.debug"), o_.engines, pr, engine, err))
			throw Failure{ "Compiling the scripts takes this computer's (" + host + ") engine: " + err };
		if (host == "windows") return engine / "krkrz.exe";
		if (host == "linux") return engine / "krkrz";
		std::error_code ec;
		fs::path src;
		for (const auto& e : fs::directory_iterator(engine, ec))
			if (e.is_directory(ec) && e.path().extension() == ".app") src = e.path();
		if (src.empty()) throw Failure{ "The macOS engine package has no .app" };
		const fs::path app = work_ / "compile-engine" / src.filename();
		mustMkdirs(app.parent_path());
		copyTree(src, app);
		fs::remove_all(app / "Contents" / "_CodeSignature", ec);
		RunOptions opt;
		opt.timeoutSeconds = 600;
		const RunResult r = run("codesign", { "--force", "--deep", "--sign", "-", krt::fromPath(app) }, opt);
		if (!r.ok()) throw Failure{ "codesign failed: " + krt::trim(r.output) };
		return app / "Contents" / "MacOS" / "krkrz";
	}

	//-----------------------------------------------------------------------
	// Compiled scenarios (doc/scn.txt): the scripts in !scnlist.txt, compiled by this computer's
	// engine into .scn (a PSB, when the engine has the scnfile plugin) or .scn.json, encrypted
	// with the game's key when it has one; the scripts themselves are left out, with the
	// compiler's own parsermacro.ks and parseroption.txt
	//-----------------------------------------------------------------------
	static bool endsWith(const std::string& s, const char* tail)
	{
		const size_t n = std::strlen(tail);
		return s.size() >= n && s.compare(s.size() - n, n, tail) == 0;
	}

	void scenes(krt::Progress&& pr)
	{
		if (!flag(s_, "scenes.compile")) return;
		std::error_code ec;
		// what the developer's own runs compiled is left out, and every script compiled again
		// (removed, not written over: the staged files are links to the game's own)
		std::vector<fs::path> old;
		std::set<std::string> listed;   // the scripts !scnlist.txt names, lower case
		bool haveList = false;
		for (fs::recursive_directory_iterator it(stage_, ec), end; it != end; it.increment(ec)) {
			if (ec) break;
			if (!it->is_regular_file(ec)) continue;
			const std::string n = lower(krt::fromPath(it->path().filename()));
			if (endsWith(n, ".scn") || endsWith(n, ".scn.json")) old.push_back(it->path());
			if (n != "!scnlist.txt") continue;
			haveList = true;
			std::string text;
			krt::readFile(it->path(), text);
			size_t pos = 0;
			while (pos < text.size()) {
				size_t end = text.find('\n', pos);
				if (end == std::string::npos) end = text.size();
				std::string line = krt::trim(text.substr(pos, end - pos));
				pos = end + 1;
				if (line.size() >= 3 && (unsigned char)line[0] == 0xEF && (unsigned char)line[1] == 0xBB && (unsigned char)line[2] == 0xBF) line = krt::trim(line.substr(3));
				if (line.empty() || line[0] == '#' || line.find(':') != std::string::npos) continue;
				const size_t slash = line.find_last_of("/\\");
				listed.insert(lower(slash == std::string::npos ? line : line.substr(slash + 1)));
			}
		}
		for (const auto& f : old) fs::remove(f, ec);
		if (!haveList) throw Failure{ "Compiling scenarios: the game has no !scnlist.txt (doc/scn.txt)" };

		const std::string host = hostId();
		fs::path engine;
		std::string err;
		pr.progress(0, "Getting the " + host + " engine to compile the scenarios");
		if (!ensureEngine(host, flag(s_, "engine.debug"), o_.engines, pr, engine, err)) throw Failure{ "Compiling scenarios: " + err };
		fs::path exe;
		if (host == "windows") exe = engine / "krkrz.exe";
		else if (host == "linux") exe = engine / "krkrz";
		else {
			for (const auto& e : fs::directory_iterator(engine, ec))
				if (e.is_directory(ec) && e.path().extension() == ".app") exe = e.path() / "Contents" / "MacOS" / "krkrz";
		}
		if (exe.empty() || !fs::is_regular_file(exe, ec)) throw Failure{ "Compiling scenarios: the " + host + " engine package has no engine" };

		// the game, headless where it can be (the framework keeps a compiling run's window
		// hidden), through its -scncompile, which compiles and exits
		const fs::path dir = work_ / "compile";
		mustRemove(dir);
		mustMkdirs(dir / "save");
		RunOptions opt;
		opt.timeoutSeconds = 1800;
		opt.workDir = exe.parent_path();
		opt.env = { { "SDL_AUDIO_DRIVER", "dummy" } };
		if (host == "linux") opt.env.push_back({ "SDL_VIDEO_DRIVER", "offscreen" });
		opt.canceled = [&pr]() { return pr.canceled(); };
		pr.progress(-1, "Compiling the scenarios");
		pr.log("Compiling the scenarios with " + krt::fromPath(exe));
		const RunResult r = run(krt::fromPath(exe), { krt::fromPath(stage_), "-scncompile=all", "-datapath=" + krt::fromPath(dir / "save") + "/" }, opt);
		if (pr.canceled()) throw Failure{ "Canceled" };
		std::string raw, log;
		if (krt::readFile(dir / "save" / "krkr.console.log", raw)) log = utf16leToUtf8(raw);
		if (log.empty()) log = r.output;
		writeText(out_ / "compile-scenarios.log", log);
		std::string summary;
		std::vector<std::string> problems, warnings;
		size_t pos = 0;
		while (pos < log.size()) {
			size_t end = log.find('\n', pos);
			if (end == std::string::npos) end = log.size();
			std::string line = log.substr(pos, end - pos);
			pos = end + 1;
			if (!line.empty() && line.back() == '\r') line.pop_back();
			if (line.find("Compiled scenarios: ") != std::string::npos) summary = line.substr(line.find("Compiled scenarios: ") + 20);
			else if (line.find(":Scenario conversion error:") != std::string::npos || line.find("Script exception raised") != std::string::npos ||
			         line.find("\xe3\x82\xb9\xe3\x82\xaf\xe3\x83\xaa\xe3\x83\x97\xe3\x83\x88\xe3\x81\xa7\xe4\xbe\x8b\xe5\xa4\x96") != std::string::npos)
				problems.push_back(krt::trim(line));
			else if (line.find("warning: ") != std::string::npos) warnings.push_back(krt::trim(line.substr(line.find("warning: ") + 9)));
		}
		for (const auto& w : warnings) pr.log("scenarios: warning: " + w);
		// the summary is in the engine's log; a run that exits 0 compiled everything even when
		// the log didn't get written (the count of compiled files is checked below)
		if (!r.ok()) {
			std::string why = problems.empty() ? std::string(r.timedOut ? "it took over half an hour" : r.started ? "the engine stopped" : "the engine couldn't be started: " + krt::trim(r.output))
			                                   : problems.front();
			throw Failure{ "Compiling scenarios failed: " + why + " (see compile-scenarios.log)" };
		}
		if (!summary.empty()) pr.log("Compiled scenarios: " + summary);
		if (!warnings.empty())
			notes_.push_back("Compiling scenarios: " + std::to_string(warnings.size()) + (warnings.size() == 1 ? " warning" : " warnings") + " (see compile-scenarios.log)");

		// what was compiled: encrypted, and the scripts left out
		std::vector<fs::path> compiled;
		std::vector<fs::path> compilerFiles;
		bool json = false;
		for (fs::recursive_directory_iterator it(stage_, ec), end; it != end; it.increment(ec)) {
			if (ec) break;
			if (!it->is_regular_file(ec)) continue;
			const std::string n = lower(krt::fromPath(it->path().filename()));
			if (endsWith(n, ".scn")) compiled.push_back(it->path());
			else if (endsWith(n, ".scn.json")) { compiled.push_back(it->path()); json = true; }
			else if (n == "parsermacro.ks" || n == "parseroption.txt") compilerFiles.push_back(it->path());
		}
		std::set<std::string> done;
		for (const auto& f : compiled) {
			std::string n = lower(krt::fromPath(f.filename()));
			n.resize(n.size() - (endsWith(n, ".scn.json") ? 9 : 4));
			done.insert(n);
		}
		std::string missing;
		for (const auto& n : listed) if (!done.count(n)) missing += (missing.empty() ? "" : ", ") + n;
		if (!missing.empty()) throw Failure{ "Compiling scenarios: no compiled file for " + missing + " (see compile-scenarios.log)" };
		if (compiled.empty()) {
			notes_.push_back("Scenarios: !scnlist.txt lists no scripts, so nothing was compiled");
			return;
		}
		scenesPsb_ = !json;
		if (haveKey_) {
			if (json)
				throw Failure{ "The scenarios were compiled to .scn.json, which can't be encrypted: the " + host +
				               " engine has no scnfile plugin (use engine packages that have it), or parseroption.txt asks for format=json" };
			pr.progress(-1, "Encrypting the scenarios");
			for (const auto& f : compiled)
				if (!sealScene(f, key_, err)) throw Failure{ "Encrypting the scenarios: " + err };
			scenesSealed_ = true;
		}
		for (const auto& f : compiled) {
			std::string script = krt::fromPath(f);
			script.resize(script.size() - (endsWith(lower(script), ".scn.json") ? 9 : 4));
			fs::remove(krt::toPath(script), ec);
		}
		for (const auto& f : compilerFiles) fs::remove(f, ec);
		pr.log("Scenarios: " + std::to_string(compiled.size()) + " compiled to " + (json ? ".scn.json" : ".scn") +
		       (haveKey_ ? ", encrypted" : "") + "; their scripts are left out");
		if (json) notes_.push_back("Scenarios: compiled to .scn.json (plain text), as the " + host + " engine has no scnfile plugin");
		else if (!haveKey_) notes_.push_back("Scenarios: compiled, not encrypted (no key)");
	}

	// What compiled scenarios need from a platform's engine: the scnfile plugin, to read .scn
	// files, with the game's key written into its slot when they're encrypted. root: the
	// platform's own copy of the engine
	void scenesInto(const std::string& id, const fs::path& root)
	{
		if (!scenesPsb_) return;
		std::string err;
		const auto slots = sceneKeySlots(root, err);
		if (!err.empty()) throw Failure{ "The engine's scnfile plugin: " + err };
		if (slots.empty())
			throw Failure{ "The " + id + " engine has no scnfile plugin, which plays the compiled scenarios (.scn): use engine packages that have it" };
		if (!haveKey_) return;
		std::string names;
		for (const auto& f : slots) {
			if (!writeSceneKey(f, key_, err)) throw Failure{ "Writing the scenario key: " + err };
			std::error_code ec;
			std::string rel = krt::fromPath(fs::relative(f, root, ec));
			std::replace(rel.begin(), rel.end(), '\\', '/');
			names += (names.empty() ? "" : ", ") + rel;
		}
		pr_.log(id + ": the scenario key is in " + names);
	}

	//-----------------------------------------------------------------------
	// The file list, and a patch of what changed since an earlier one
	//-----------------------------------------------------------------------
	// <file name>-<version>-files.json beside the packages: every file in data (after the media
	// conversion, with the framework as system/) and its SHA-256. A later build names it in
	// output.patchFrom to make a patch of the files that are new or changed since
	void fileList(krt::Progress&& pr)
	{
		std::vector<std::string> names;
		std::error_code ec;
		for (fs::recursive_directory_iterator it(stage_, ec), end; it != end; it.increment(ec)) {
			if (ec) break;
			if (!it->is_regular_file(ec)) continue;
			std::string n = krt::fromPath(fs::relative(it->path(), stage_, ec));
			std::replace(n.begin(), n.end(), '\\', '/');
			names.push_back(n);
		}
		std::sort(names.begin(), names.end());
		Json files = Json::object();
		hashes_.clear();
		for (size_t i = 0; i < names.size(); ++i) {
			if ((i & 31) == 0) {
				pr.progress((double)i / names.size(), "File list");
				if (pr.canceled()) throw Failure{ "Canceled" };
			}
			std::string hex, err;
			if (!sha256File(stage_ / krt::toPath(names[i]), hex, err)) throw Failure{ err };
			files.set(names[i], Json(hex));
			hashes_[names[i]] = hex;
		}
		Json list = Json::object();
		list.set("format", Json(1));
		list.set("title", Json(str(s_, "identity.title")));
		list.set("version", Json(str(s_, "identity.version")));
		list.set("files", std::move(files));
		const fs::path file = out_ / krt::toPath(str(s_, "identity.exeName") + "-" + str(s_, "identity.version") + "-files.json");
		writeText(file, list.dump(1) + "\n");
		pr.log("File list: " + krt::fromPath(file));
	}

	// <file name>-<version>-patch/patch.zip: the files that are new or changed since the file list
	// in output.patchFrom, in data/'s layout. The framework loads patch.zip from next to the game
	// or from its save folder (Initialize.tjs), so a patch made from the full release's list holds
	// every change since and replaces the patch before it. It can't take files away
	Json patch(krt::Progress&& pr)
	{
		Json o = Json::object();
		o.set("platform", Json("patch"));
		o.set("title", Json("Patch"));
		try {
			const std::string fromName = str(s_, "output.patchFrom");
			const fs::path from = p_.root / krt::toPath(fromName);
			std::string text, err;
			Json old;
			if (!krt::readFile(from, text)) throw Failure{ "Can't read " + fromName };
			const Json& list = old;
			if (!Json::parse(text, old, &err) || !list["files"].isObj()) throw Failure{ fromName + " isn't a file list from kagex-release" + (err.empty() ? "" : ": " + err) };
			const std::string since = list["version"].asStr();
			std::map<std::string, std::string> before;
			for (const auto& [name, hex] : list["files"].members()) before[name] = hex.asStr();
			std::vector<std::string> changed;
			for (const auto& [name, hex] : hashes_) {
				const auto it = before.find(name);
				if (it == before.end() || it->second != hex) changed.push_back(name);
			}
			int removed = 0;
			for (const auto& [name, hex] : before) if (!hashes_.count(name)) ++removed;

			const std::string base = str(s_, "identity.exeName") + "-" + str(s_, "identity.version") + "-patch";
			const fs::path folder = out_ / krt::toPath(base);
			const fs::path zip = folder / "patch.zip";
			mustRemove(folder);
			mustMkdirs(folder);
			const fs::path dir = work_ / "patch";
			mustRemove(dir);
			mustMkdirs(dir);
			std::error_code ec;
			for (const auto& name : changed) {
				const fs::path to = dir / krt::toPath(name);
				fs::create_directories(to.parent_path(), ec);
				fs::create_hard_link(stage_ / krt::toPath(name), to, ec);
				if (ec) copyFile(stage_ / krt::toPath(name), to);
			}
			pr.progress(-1, "Patch");
			if (!zipFolder(dir, zip, "", err)) throw Failure{ err };
			if (signing_) { signChecked(zip); pr.log("Signed the patch (patch.zip.sig)"); }   // a signed game only mounts a signed patch
			packages_.push_back(zip);
			o.set("ok", Json(true));
			o.set("folder", Json(krt::fromPath(folder)));
			o.set("package", Json(krt::fromPath(zip)));
			o.set("bytes", Json((long long)treeSize(zip)));
			const auto files = [](size_t n) { return std::to_string(n) + (n == 1 ? " file" : " files"); };
			std::string note = "Patch since " + (since.empty() ? fromName : since) + ": " + files(changed.size()) + " new or changed";
			if (changed.empty()) note += " (nothing to patch)";
			if (removed) note += "; " + files(removed) + " removed since then " + (removed == 1 ? "stays" : "stay") + " in the game (a patch can't remove files)";
			notes_.push_back(note);
			pr.log(note);
			// read before any patch is mounted, so changes to them can't reach players this way
			std::vector<std::string> early;
			for (const auto& name : changed) {
				const std::string leaf = lower(krt::fromPath(krt::toPath(name).filename()));
				if (leaf == "initialize.tjs" || leaf == "storages.tjs" || leaf == "startup.tjs") early.push_back(name);
			}
			if (!early.empty()) {
				std::string list;
				for (const auto& e : early) list += (list.empty() ? "" : ", ") + e;
				notes_.push_back("The patch changes " + list + ", which the game reads before it loads patches: those changes need a full release");
			}
		} catch (const Failure& f) {
			o.set("ok", Json(false));
			o.set("error", Json(f.message));
			pr.log("patch: " + f.message);
			patchFailed_ = true;
		}
		return o;
	}

	// The plugins the scripts name ("plugin/foo.dll", KAGLinkPlugin("foo")), lower case
	std::set<std::string> linkedPlugins()
	{
		std::set<std::string> names;
		static const std::regex re(R"re(["']([A-Za-z0-9_]+)(\.dll)?["'])re");
		static const std::regex re2(R"re(plugin/([A-Za-z0-9_]+)\.dll)re");
		std::error_code ec;
		for (fs::recursive_directory_iterator it(stage_, ec), end; it != end; it.increment(ec)) {
			if (ec || !it->is_regular_file(ec)) continue;
			const std::string ext = lower(krt::fromPath(it->path().extension()));
			if (ext != ".tjs" && ext != ".ks") continue;
			std::string text;
			if (!krt::readFile(it->path(), text)) continue;
			for (std::sregex_iterator m(text.begin(), text.end(), re), e; m != e; ++m) names.insert(lower((*m)[1]));
			for (std::sregex_iterator m(text.begin(), text.end(), re2), e; m != e; ++m) names.insert(lower((*m)[1]));
		}
		return names;
	}

	bool pluginWanted(const std::string& file)
	{
		if (str(s_, "contents.plugins") != "linked") return true;
		std::string stem = lower(krt::fromPath(krt::toPath(file).stem()));
		if (stem.rfind("lib", 0) == 0 && !linked_.count(stem)) stem = stem.substr(3);
		return linked_.count(stem) > 0;
	}

	bool needsXp3()
	{
		for (const auto& id : chosen_) {
			const std::string d = str(s_, "platforms." + id + ".data");
			if (d == "xp3" || d == "bind") return true;
		}
		return false;
	}

	void packXp3(krt::Progress&& pr)
	{
		xp3_ = work_ / "data.xp3";
		if (haveArchiveKey_) {
			pr.progress(0, "Packing data.xp3 (encrypted)");
			int files = 0;
			uint64_t bytes = 0;
			std::string err;
			if (!packEncrypted(stage_, xp3_, archiveKey_, false, files, bytes, err)) throw Failure{ "Couldn't pack the encrypted data.xp3: " + err };
			std::error_code ec;
			if (!fs::is_regular_file(xp3_, ec) || files == 0) throw Failure{ "Couldn't pack the encrypted data.xp3" };
			pr.log("data.xp3: " + std::to_string(files) + " files, " + std::to_string(bytes / 1048576) + " MB, encrypted");
			return;
		}
		pr.progress(0, "Packing data.xp3");
		const auto r = krt::xp3::pack(stage_, xp3_, krt::xp3::PackOptions::defaults(), pr);
		if (r.canceled) throw Failure{ "Canceled" };
		std::error_code ec;
		if (!fs::is_regular_file(xp3_, ec) || r.files == 0) throw Failure{ "Couldn't pack data.xp3" };
		pr.log("data.xp3: " + std::to_string(r.files) + " files, " + std::to_string(r.arcBytes / 1048576) + " MB");
	}

	// Hidden file names: one encrypted, name-hashed archive (data.xpc) the game reads through the
	// xpcrypt:// medium, plus a plain bootstrap startup.tjs that mounts it. The game's folders are
	// inside data.xpc with their names hashed, so nothing is readable in the package but the engine
	void packHashed(krt::Progress&& pr)
	{
		// the plain bootstrap: template/system/hashed-bootstrap.tjs, copied into the staged data
		std::error_code ec;
		if (!krt::readFile(stage_ / "system" / "hashed-bootstrap.tjs", bootstrap_) || bootstrap_.empty())
			throw Failure{ "Hiding the file names needs template/system/hashed-bootstrap.tjs in the framework (update template/system)" };
		xpc_ = work_ / "data.xpc";
		pr.progress(0, "Packing data.xpc (encrypted, names hidden)");
		int files = 0;
		uint64_t bytes = 0;
		std::string err;
		if (!packEncrypted(stage_, xpc_, archiveKey_, true, files, bytes, err)) throw Failure{ "Couldn't pack data.xpc: " + err };
		if (!fs::is_regular_file(xpc_, ec) || files == 0) throw Failure{ "Couldn't pack data.xpc" };
		// the engine's signature check reads sizes as 32-bit numbers, and data.xpc can't be split
		if (signing_ && fs::file_size(xpc_, ec) >= 2000ULL * 1048576)
			throw Failure{ "This signed build's data.xpc is " + humanGB(fs::file_size(xpc_, ec)) + ": with hidden file names the data is one archive, "
				"and the engine's signature check can't read 2 GB or more of it. Turn Hide names off (the data is then split into archives under 2 GB), or reduce the data" };
		pr.log("data.xpc: " + std::to_string(files) + " files, " + std::to_string(bytes / 1048576) + " MB, encrypted with hidden names");
	}

	// Write the game's key into the platform's engine, which must have the xp3crypt plugin (its
	// key slot). root: the platform's own copy of the engine. Called when the platform ships the
	// encrypted data.xp3 (xp3 or bind data mode), or a hashed data.xpc
	void archiveKeyInto(const std::string& id, const fs::path& root)
	{
		if (!haveArchiveKey_) return;
		std::string err;
		const auto slots = archiveKeySlots(root, err);
		if (!err.empty()) throw Failure{ "The engine's xp3crypt plugin: " + err };
		if (slots.empty())
			throw Failure{ "The " + id + " engine has no xp3crypt plugin, which decrypts the archive: use engine packages that have it built in" };
		std::string names;
		for (const auto& f : slots) {
			if (!writeArchiveKey(f, archiveKey_, err)) throw Failure{ "Writing the archive key: " + err };
			std::error_code ec;
			std::string rel = krt::fromPath(fs::relative(f, root, ec));
			std::replace(rel.begin(), rel.end(), '\\', '/');
			names += (names.empty() ? "" : ", ") + rel;
		}
		pr_.log(id + ": the archive key is in " + names);
	}

	// Whether the platform ships the encrypted data.xp3 (so its engine needs the key)
	bool encryptedXp3For(const std::string& id)
	{
		if (!haveArchiveKey_) return false;
		if (hashNames_) return true;   // the hashed data.xpc is always read through the medium, so the engine needs the key
		const std::string d = str(s_, "platforms." + id + ".data");
		return d == "xp3" || d == "bind";
	}

	void prepareIcons()
	{
		const std::string icon = str(s_, "identity.icon");
		fs::path src = icon.empty() ? fs::path() : p_.root / krt::toPath(icon);
		if (src.empty()) return;
		std::string err;
		if (!icons_.load(src, err)) throw Failure{ "The icon: " + err };
	}

	//-----------------------------------------------------------------------
	// Signing (SignatureCheck.tjs verifies these at start-up)
	//-----------------------------------------------------------------------
	static std::string humanGB(uint64_t b)
	{
		char buf[32];
		std::snprintf(buf, sizeof(buf), "%.2f GB", b / 1073741824.0);
		return buf;
	}

	// SignatureKey.tjs sets the public key as a TJS string; a signed build is recognised by it.
	static std::string keyTjs(const std::string& pubPem)
	{
		std::string esc;
		for (char c : pubPem) {
			if (c == '\\') esc += "\\\\";
			else if (c == '"') esc += "\\\"";
			else if (c == '\r') {}            // keep only \n, written as an escape
			else if (c == '\n') esc += "\\n";
			else esc += c;
		}
		return "// Written by kagex-release: the public key for the signature check (SignatureCheck.tjs).\n"
		       "global.KAGSignaturePublicKey = \"" + esc + "\";\n"
		       "global.KAGSignatureCheckEngine = true;\n";
	}

	// Writes the public key and the self-test into the staged data, before it is hashed and packed.
	void signStage()
	{
		if (!signing_) return;
		writeText(stage_ / "SignatureKey.tjs", keyTjs(pubPem_));
		// the self-test: content whose .sig deliberately doesn't match, so a working plugin reports
		// a mismatch (a plugin stubbed to always succeed is then caught)
		std::string data(4096, '\0');
		for (size_t i = 0; i < data.size(); ++i) data[i] = (char)((i * 131 + 7) & 0xFF);
		const fs::path decoy = stage_ / "SignatureDecoy.bin";
		writeText(decoy, data);
		std::string err;
		if (!signFileWith(decoy, privPem_, err)) throw Failure{ "Signing (self-test): " + err };
		data[0] = (char)(data[0] ^ 0xFF);   // break the content so it no longer matches the signature
		writeText(decoy, data);
	}

	void signChecked(const fs::path& f)
	{
		std::string err;
		if (!signFileWith(f, privPem_, err)) throw Failure{ "Couldn't sign " + krt::fromPath(f.filename()) + ": " + err };
		if (!verifyFileWith(f, pubPem_, err)) throw Failure{ "The signature for " + krt::fromPath(f.filename()) + " didn't verify: " + err };
	}

	uint64_t splitThresholdBytes()
	{
		const std::string env = getEnv("KAGEX_RELEASE_SPLIT_THRESHOLD_MB");
		const long long mb = env.empty() ? 2000 : std::atoll(env.c_str());
		return (uint64_t)(mb > 0 ? mb : 2000) * 1048576ULL;
	}

	// Splits the biggest media folders out of data.xp3 into their own archives beside it, so no
	// archive reaches the engine's 2 GB signature-check limit. Forced on for a signed build whose
	// data is that large; otherwise follows signing.splitArchives. Windows and Linux only (the
	// parts sit beside the engine, where the framework looks for them).
	void splitIfNeeded(krt::Progress&& pr)
	{
		bool want = flag(s_, "signing.splitArchives");
		const uint64_t threshold = splitThresholdBytes();
		const uint64_t dataBytes = treeSize(stage_);
		const bool mustSplit = signing_ && dataBytes >= threshold;
		if (mustSplit) want = true;
		if (!want) return;
		for (const auto& id : chosen_)
			if (id == "macos" || id == "android" || id == "ios" || id == "web")
				throw Failure{ std::string(mustSplit ? "This signed build's data is " + humanGB(dataBytes) + ", so data.xp3 must be split to stay under the engine's 2 GB signature-check limit. " : "") +
					"Splitting the data into separate archives is supported for Windows and Linux only; build " + id + " on its own, or turn splitting off" };

		static const std::set<std::string> splittable = {
			"video", "bgm", "voice", "sound", "bgimage", "fgimage", "image", "evimage", "thum" };
		struct Folder { std::string name; uint64_t size; };
		std::vector<Folder> folders;
		std::error_code ec;
		for (const auto& e : fs::directory_iterator(stage_, ec)) {
			if (!e.is_directory(ec)) continue;
			const std::string n = krt::fromPath(e.path().filename());
			if (splittable.count(lower(n))) folders.push_back({ n, treeSize(e.path()) });
		}
		std::sort(folders.begin(), folders.end(), [](const Folder& a, const Folder& b) { return a.size > b.size; });

		const uint64_t signLimit = 2000ULL * 1048576;   // the engine's ~2 GB signature-check limit (fixed, not the test threshold)
		uint64_t remaining = dataBytes;
		for (const auto& f : folders) {
			if (mustSplit && remaining < threshold) break;   // enough moved out already
			if (signing_ && f.size >= signLimit)
				throw Failure{ "The " + f.name + " folder is " + humanGB(f.size) + " on its own; a signed build can't put 2 GB or more into one archive "
					"(the engine's signature check uses 32-bit sizes). Split that folder's contents across smaller folders" };
			pr.progress(-1, "Splitting out " + f.name + ".xp3");
			const fs::path part = work_ / krt::toPath(f.name + ".xp3");
			if (haveArchiveKey_) {
				// an encrypted build encrypts its parts too (the plugin decrypts every XP3 read)
				int files = 0;
				uint64_t bytes = 0;
				std::string err;
				if (!packEncrypted(stage_ / krt::toPath(f.name), part, archiveKey_, false, files, bytes, err))
					throw Failure{ "Couldn't pack the encrypted " + f.name + ".xp3: " + err };
			} else {
				const auto r = krt::xp3::pack(stage_ / krt::toPath(f.name), part, krt::xp3::PackOptions::defaults(), pr);
				if (r.canceled) throw Failure{ "Canceled" };
			}
			if (!fs::is_regular_file(part, ec)) throw Failure{ "Couldn't pack " + f.name + ".xp3" };
			partXp3_[f.name] = part;
			partNames_.push_back(f.name);
			mustRemove(stage_ / krt::toPath(f.name));
			remaining -= f.size;
			pr_.log("Split out " + f.name + ".xp3 (" + humanGB(f.size) + ")");
		}
		if (mustSplit && remaining >= threshold)
			throw Failure{ "Couldn't get data.xp3 under 2 GB by moving the media folders out (" + humanGB(remaining) + " left). "
				"Reduce the data, or move more of it into the media folders that can be split (video, bgm, voice, sound, image, bgimage, fgimage, evimage, thum)" };
	}

	void copyParts(const fs::path& dir)
	{
		for (const auto& [name, part] : partXp3_) copyFile(part, dir / krt::toPath(name + ".xp3"));
	}

	// Signs a Windows/Linux/Steam package: the engine files (with a signed list of them), the game
	// archive, and the split parts. The last step, after the executable is final.
	void signDesktopPackage(const std::string& id, const fs::path& dir)
	{
		if (!signing_) return;
		const bool win = id == "windows";
		const std::string exeName = str(s_, "identity.exeName");
		const std::string exeLeaf = win ? exeName + ".exe" : exeName;
		std::vector<std::string> rel;
		rel.push_back(exeLeaf);
		rel.push_back(exeName + ".cf");
		std::error_code ec;
		for (const auto& e : fs::directory_iterator(dir, ec)) {
			if (!e.is_regular_file(ec)) continue;
			const std::string n = krt::fromPath(e.path().filename()), ln = lower(n);
			if (n == exeLeaf || n == exeName + ".cf") continue;
			const bool isLib = win ? (ln.size() > 4 && ln.compare(ln.size() - 4, 4, ".dll") == 0)
			                       : (ln.rfind("lib", 0) == 0 && ln.find(".so") != std::string::npos);
			if (isLib) rel.push_back(n);
		}
		if (fs::is_directory(dir / "plugin", ec))
			for (const auto& e : fs::directory_iterator(dir / "plugin", ec))
				if (e.is_regular_file(ec)) rel.push_back("plugin/" + krt::fromPath(e.path().filename()));

		pr_.progress(-1, "Signing " + id);
		for (const auto& r : rel) signChecked(dir / krt::toPath(r));
		std::string manifest = "; engine files for the signature check, relative to the executable (kagex-release)\n";
		for (const auto& r : rel) manifest += r + "\n";
		writeText(dir / krt::toPath(exeLeaf + ".sigfiles"), manifest);
		signChecked(dir / krt::toPath(exeLeaf + ".sigfiles"));

		if (hashNames_) {
			// hidden names: data.xpc and the plain bootstrap that mounts it
			signChecked(dir / "data.xpc");
			signChecked(dir / "data" / "startup.tjs");
		} else if (str(s_, "platforms." + id + ".data") != "bind") signChecked(dir / "data.xp3");   // a bound exe is signed above
		for (const auto& name : partNames_) signChecked(dir / krt::toPath(name + ".xp3"));
		pr_.log("Signed " + std::to_string(rel.size()) + " engine files, the archive" +
		        (partNames_.empty() ? std::string() : " and " + std::to_string(partNames_.size()) + " part(s)"));
	}

	// Signs a macOS app's data archive inside the bundle, before codesign reseals it. The engine
	// files (the executable and the plugin dylibs) are NOT signed here: codesign --deep rewrites
	// their embedded signatures a moment later, which would break a krt::sig .sig, so the app's own
	// code signature (Developer ID, or ad hoc) is what vouches for them. codesign records a hash of
	// data.xp3 without changing its bytes, so its .sig stays valid; the framework skips the engine
	// file list on macOS (SignatureCheck.tjs). Splitting is disabled on macOS, so there are no parts.
	void signMacosApp(const fs::path& contents)
	{
		if (!signing_) return;
		pr_.progress(-1, "Signing macOS");
		if (hashNames_) {
			signChecked(contents / "Resources" / "data.xpc");
			signChecked(contents / "Resources" / "data" / "startup.tjs");
		} else signChecked(contents / "Resources" / "data.xp3");
		pr_.log("Signed the game archive (macOS; codesign seals the engine)");
	}

	//-----------------------------------------------------------------------
	// Platforms
	//-----------------------------------------------------------------------
	void buildPlatform(const std::string& id, krt::Progress& pr, fs::path& folder, fs::path& package)
	{
		const bool debug = flag(s_, "engine.debug");
		if (debug && !hasDebugEngine(id)) notes_.push_back(id + ": no debug engine is published for it; the release engine is used");
		fs::path engine;
		std::string err;
		pr.progress(0, "Getting the " + id + " engine");
		if (!ensureEngine(id, debug, o_.engines, pr, engine, err)) throw Failure{ err };

		if (id == "android") {
			pr.progress(0.2, "Building the Android app with Gradle");
			buildAndroid(engine, pr, package);
			return;
		}
		if (id == "ios") {
			pr.progress(0.2, "Assembling the iOS app");
			buildIos(engine, pr, package);
			return;
		}
		folder = out_ / krt::toPath(packageBaseName(s_, id));
		mustRemove(folder);
		mustMkdirs(folder);
		pr.progress(0.3, "Assembling " + id);
		if (id == "windows") buildWindows(engine, folder);
		else if (id == "linux" || id == "steam") buildLinux(id, engine, folder);
		else if (id == "macos") buildMacos(engine, folder);
		else if (id == "web") buildWeb(engine, folder);
		else throw Failure{ "Building for " + id + " isn't in this version of the tool yet" };

		for (const auto& e : at(s_, "contents.extraFiles").elements()) {
			const fs::path src = p_.root / krt::toPath(e.asStr());
			std::error_code ec;
			if (fs::is_directory(src, ec)) copyTree(src, folder / src.filename());
			else copyFile(src, folder / src.filename());
		}

		pr.progress(0.7, "Packing " + id);
		package = archive(id, folder);
	}

	void dataInto(const std::string& id, const fs::path& dir)
	{
		if (hashNames_) {
			// data.xpc next to the engine, and a plain data/ with just the bootstrap startup.tjs
			copyFile(xpc_, dir / "data.xpc");
			writeText(dir / "data" / "startup.tjs", bootstrap_);
			return;
		}
		const std::string mode = str(s_, "platforms." + id + ".data");
		if (mode == "xp3") { copyFile(xp3_, dir / "data.xp3"); copyParts(dir); }
		else if (mode == "folder") copyTree(stage_, dir / "data");
	}

	void licensesInto(const fs::path& engine, const fs::path& dir)
	{
		if (!flag(s_, "contents.licenses")) return;
		std::error_code ec;
		if (fs::is_regular_file(engine / "license.txt", ec)) copyFile(engine / "license.txt", dir / "license.txt");
		if (fs::is_directory(engine / "licenses", ec)) copyTree(engine / "licenses", dir / "licenses");
	}

	void pluginsInto(const fs::path& from, const fs::path& to)
	{
		std::error_code ec;
		if (!fs::is_directory(from, ec)) return;
		int kept = 0, left = 0;
		for (const auto& e : fs::directory_iterator(from, ec)) {
			if (!e.is_regular_file(ec)) continue;
			const std::string name = krt::fromPath(e.path().filename());
			if (!pluginWanted(name)) { ++left; continue; }
			copyFile(e.path(), to / e.path().filename());
			++kept;
		}
		if (left) pr_.log("Plugins: " + std::to_string(kept) + " linked by the scripts, " + std::to_string(left) + " left out");
	}

	// Appends data.xp3 to the executable, at a 16-byte boundary (where the engine looks)
	void bind(const fs::path& exe)
	{
		std::string a, b;
		if (!krt::readFile(exe, a) || !krt::readFile(xp3_, b)) throw Failure{ "Can't bind the data into " + krt::fromPath(exe.filename()) };
		a.resize((a.size() + 15) / 16 * 16, '\0');
		a += b;
		writeText(exe, a);
	}

	void buildWindows(const fs::path& engine, const fs::path& dir)
	{
		const std::string exeName = str(s_, "identity.exeName") + ".exe";
		const fs::path exe = dir / krt::toPath(exeName);
		bool resources = false;
#ifdef KR_HAVE_RELEASE_LIB
		if (flag(s_, "platforms.windows.versionInfo")) {
			namespace rl = krt::release;
			rl::Settings rs;
			rs.exe = krt::fromPath(engine / "krkrz.exe");
			rs.output = krt::fromPath(exe);
			rs.force = true;
			if (icons_.loaded()) {
				std::string ico, err;
				if (!icons_.ico(ico, err)) throw Failure{ "The icon: " + err };
				writeText(work_ / "icon.ico", ico);
				rs.icon = krt::fromPath(work_ / "icon.ico");
			}
			const std::string title = str(s_, "identity.title"), version = str(s_, "identity.version");
			rs.version = {
				{ "FileDescription", title }, { "ProductName", title }, { "CompanyName", str(s_, "identity.orgName") },
				{ "LegalCopyright", str(s_, "identity.copyright") }, { "FileVersion", version }, { "ProductVersion", version },
				{ "OriginalFilename", exeName }, { "InternalName", str(s_, "identity.exeName") },
			};
			rs.dataMode = rl::Settings::DataMode::None;
			PartProgress quiet(pr_, -1, -1);
			const rl::Result r = rl::run(rs, dir, quiet);
			if (!r.ok) throw Failure{ "Setting the exe's icon and version info: " + r.message };
			resources = true;
		}
#endif
		if (!resources) {
			copyFile(engine / "krkrz.exe", exe);
			if (flag(s_, "platforms.windows.versionInfo") && std::string(hostId()) != "windows")
				notes_.push_back("windows: the exe keeps the KAGEX icon and version info (they can be set when this tool runs on Windows)");
		}
		std::error_code ec;
		for (const auto& e : fs::directory_iterator(engine, ec)) {
			const std::string n = lower(krt::fromPath(e.path().filename()));
			if (e.is_regular_file(ec) && n.size() > 4 && n.compare(n.size() - 4, 4, ".dll") == 0) copyFile(e.path(), dir / e.path().filename());
		}
		pluginsInto(engine / "plugin", dir / "plugin");
		if (encryptedXp3For("windows")) archiveKeyInto("windows", dir);   // before bind, so the exe is keyed first
		scenesInto("windows", dir);
		writeText(dir / krt::toPath(str(s_, "identity.exeName") + ".cf"), engineConfig(s_, p_));
		const std::string mode = str(s_, "platforms.windows.data");
		if (mode == "bind" && !hashNames_) { bind(exe); copyParts(dir); }
		else dataInto("windows", dir);
		licensesInto(engine, dir);
		signDesktopPackage("windows", dir);
	}

	void buildLinux(const std::string& id, const fs::path& engine, const fs::path& dir)
	{
		const std::string exeName = str(s_, "identity.exeName");
		const fs::path exe = dir / krt::toPath(exeName);
		copyFile(engine / "krkrz", exe);
		makeExecutable(exe);
		std::error_code ec;
		for (const auto& e : fs::directory_iterator(engine, ec)) {
			const std::string n = krt::fromPath(e.path().filename());
			if (n.rfind("lib", 0) == 0 && n.find(".so") != std::string::npos) {
				if (e.is_symlink(ec)) {
					fs::copy_symlink(e.path(), dir / e.path().filename(), ec);
					if (ec) copyFile(e.path(), dir / e.path().filename());
				} else copyFile(e.path(), dir / e.path().filename());
			}
		}
		pluginsInto(engine / "plugin", dir / "plugin");
		if (encryptedXp3For(id)) archiveKeyInto(id, dir);   // before bind, so the executable is keyed first
		scenesInto(id, dir);
		writeText(dir / krt::toPath(exeName + ".cf"), engineConfig(s_, p_));
		const std::string mode = str(s_, "platforms." + id + ".data");
		if (mode == "bind" && !hashNames_) { bind(exe); copyParts(dir); }
		else dataInto(id, dir);
		licensesInto(engine, dir);
		if (id == "linux" && flag(s_, "platforms.linux.desktopEntry")) {
			std::string entry = "[Desktop Entry]\nType=Application\nName=" + str(s_, "identity.title") +
			                    "\nExec=" + exeName + "\nCategories=Game;\nTerminal=false\n";
			if (icons_.loaded()) {
				std::string png, err;
				if (!icons_.png(256, png, err)) throw Failure{ "The icon: " + err };
				writeText(dir / krt::toPath(exeName + ".png"), png);
				entry += "Icon=" + exeName + "\n";
			}
			writeText(dir / krt::toPath(exeName + ".desktop"), entry);
		}
		signDesktopPackage(id, dir);
	}

	void buildMacos(const fs::path& engine, const fs::path& dir)
	{
		std::error_code ec;
		fs::path src;
		for (const auto& e : fs::directory_iterator(engine, ec))
			if (e.is_directory(ec) && e.path().extension() == ".app") src = e.path();
		if (src.empty()) throw Failure{ "The macOS engine package has no .app" };
		const fs::path app = dir / krt::toPath(fileSafe(str(s_, "identity.title")) + ".app");
		copyTree(src, app);
		const fs::path contents = app / "Contents", res = contents / "Resources";
		fs::remove_all(contents / "_CodeSignature", ec);
		fs::remove_all(res / "data", ec);
		fs::remove(res / "data.xp3", ec);
		fs::remove(res / "krkrz.cf", ec);

		std::string plist;
		if (!krt::readFile(contents / "Info.plist", plist)) throw Failure{ "The macOS engine has no Info.plist" };
		const std::string oldIcon = plistGet(plist, "CFBundleIconFile");
		const std::string title = str(s_, "identity.title"), version = str(s_, "identity.version");
		plistSet(plist, "CFBundleName", str(s_, "identity.shortName").substr(0, 15));
		plistSet(plist, "CFBundleDisplayName", title);
		plistSet(plist, "CFBundleIdentifier", str(s_, "platforms.macos.bundleId"));
		plistSet(plist, "CFBundleShortVersionString", version);
		plistSet(plist, "CFBundleVersion", version);
		plistSet(plist, "NSHumanReadableCopyright", str(s_, "identity.copyright"));
		plistSet(plist, "CFBundleGetInfoString", title + " " + version);
		if (icons_.loaded()) {
			std::string icns, err;
			if (!icons_.icns(icns, err)) throw Failure{ "The icon: " + err };
			if (!oldIcon.empty()) {
				fs::remove(res / krt::toPath(oldIcon), ec);
				fs::remove(res / krt::toPath(oldIcon + ".icns"), ec);
			}
			writeText(res / "AppIcon.icns", icns);
			plistSet(plist, "CFBundleIconFile", "AppIcon");
		}
		writeText(contents / "Info.plist", plist);

		// plugins sit next to the executable in the app
		if (str(s_, "contents.plugins") == "linked") {
			for (const auto& e : fs::directory_iterator(contents / "MacOS", ec)) {
				const std::string n = krt::fromPath(e.path().filename());
				if (n.size() > 6 && n.compare(n.size() - 6, 6, ".dylib") == 0 && n.find("SDL3") == std::string::npos && !pluginWanted(n))
					fs::remove(e.path(), ec);
			}
		}
		scenesInto("macos", app);
		writeText(contents / "MacOS" / "krkrz.cf", engineConfig(s_, p_));
		dataInto("macos", res);
		licensesInto(engine, res);
		if (encryptedXp3For("macos")) archiveKeyInto("macos", app);   // before signing (macSign re-signs the keyed binary)
		signMacosApp(contents);   // sign the engine files and data before codesign reseals the bundle
		macSign(app);
	}

	void macSign(const fs::path& app)
	{
		const std::string base = "platforms.macos.";
		const bool devId = str(s_, base + "signing") == "developer-id";
		std::vector<std::string> args = { "--force", "--deep", "--sign", devId ? str(s_, base + "identity") : std::string("-") };
		if (devId) { args.push_back("--options"); args.push_back("runtime"); args.push_back("--timestamp"); }
		args.push_back(krt::fromPath(app));
		RunOptions opt;
		opt.timeoutSeconds = 600;
		pr_.progress(-1, "Signing the app");
		RunResult r = run("codesign", args, opt);
		if (!r.ok()) throw Failure{ "codesign failed: " + krt::trim(r.output) };
		r = run("codesign", { "--verify", "--deep", "--strict", krt::fromPath(app) }, opt);
		if (!r.ok()) throw Failure{ "The signed app doesn't verify: " + krt::trim(r.output) };
		if (devId && flag(s_, base + "notarize")) {
			const fs::path zip = work_ / "notarize.zip";
			pr_.progress(-1, "Notarizing (this takes a few minutes)");
			r = run("ditto", { "-c", "-k", "--keepParent", krt::fromPath(app), krt::fromPath(zip) }, opt);
			if (!r.ok()) throw Failure{ "ditto failed: " + krt::trim(r.output) };
			RunOptions nopt;
			nopt.timeoutSeconds = 3600;
			nopt.onLine = [this](const std::string& l) { pr_.log("notarytool: " + l); };
			nopt.canceled = [this]() { return pr_.canceled(); };
			r = run("xcrun", { "notarytool", "submit", krt::fromPath(zip), "--keychain-profile", str(s_, base + "notaryProfile"), "--wait" }, nopt);
			if (!r.ok() || r.output.find("status: Accepted") == std::string::npos) throw Failure{ "Notarization failed (see the log)" };
			r = run("xcrun", { "stapler", "staple", krt::fromPath(app) }, opt);
			if (!r.ok()) throw Failure{ "stapler failed: " + krt::trim(r.output) };
		}
	}

	//-----------------------------------------------------------------------
	// Android: krkrz_android's Gradle project with the engine prebuilt (the engine package),
	// given the game's data, names and icon, and built with the developer's JDK and SDK
	//-----------------------------------------------------------------------
	static std::string androidString(const std::string& v)
	{
		std::string o;
		for (size_t i = 0; i < v.size(); ++i) {
			const char c = v[i];
			if (c == '&') o += "&amp;";
			else if (c == '<') o += "&lt;";
			else if (c == '>') o += "&gt;";
			else if (c == '\'' || c == '"' || c == '\\') { o += '\\'; o += c; }
			else if (i == 0 && (c == '@' || c == '?')) { o += '\\'; o += c; }
			else o += c;
		}
		return o;
	}

	static std::string propertiesPath(const fs::path& p)
	{
		// java.util.Properties: backslashes and colons escaped
		std::string o;
		for (char c : krt::fromPath(p)) {
			if (c == '\\' || c == ':') o += '\\';
			o += c;
		}
		return o;
	}

	void buildAndroid(const fs::path& engine, krt::Progress& pr, fs::path& package)
	{
		const std::string base = "platforms.android.";
		std::error_code ec;
		const fs::path proj = work_ / "android";
		mustRemove(proj);
		if (!fs::is_directory(engine / "project", ec)) throw Failure{ "The Android engine package has no Gradle project" };
		copyTree(engine / "project", proj);
		makeExecutable(proj / "gradlew");
		if (encryptedXp3For("android")) archiveKeyInto("android", proj);   // key the engine .so before Gradle packages it
		scenesInto("android", proj);

		// app-config.json: the engine's settings, with the game's
		Json cfg;
		std::string text, err;
		if (!krt::readFile(proj / "app-config.json", text) || !Json::parse(text, cfg, &err)) throw Failure{ "The Android engine package's app-config.json: " + err };
		const std::string exe = str(s_, "identity.exeName"), version = str(s_, "identity.version");
		const long long code = at(s_, base + "versionCode").asInt() > 0 ? at(s_, base + "versionCode").asInt() : versionNumber(version);
		cfg.set("applicationId", Json(str(s_, base + "applicationId")));
		cfg.set("versionCode", Json(code));
		cfg.set("versionName", Json(version));
		Json apk = Json::object();
		apk.set("baseName", Json(exe));
		cfg.set("apk", std::move(apk));
		Json sources = Json::array();
		auto source = [&](const char* type, const fs::path& from, const char* to, const char* include) {
			Json o = Json::object();
			o.set("type", Json(type));
			o.set("from", Json(krt::fromPath(from)));
			o.set("to", Json(to));
			if (include) o.set("include", Json::array({ include }));
			sources.push(std::move(o));
		};
		source("mirror", proj / "engine-assets", "", nullptr);
		if (str(s_, base + "data") == "xp3") {
			const fs::path dir = work_ / "android-data";
			fs::create_directories(dir, ec);
			fs::remove(dir / "data.xp3", ec);
			fs::create_hard_link(xp3_, dir / "data.xp3", ec);
			if (ec) copyFile(xp3_, dir / "data.xp3");
			source("flatten", dir, "", "data.xp3");
		} else {
			source("mirror", stage_, "data", nullptr);
		}
		Json pack = Json::object();
		pack.set("baseFolder", Json(krt::fromPath(proj)));
		pack.set("resOverride", Json(krt::fromPath(proj / "res-override")));
		pack.set("sources", std::move(sources));
		cfg.set("assetPack", std::move(pack));
		writeText(proj / "app-config.json", cfg.dump(2) + "\n");

		// the name (in every language the kit names it in) and the icon
		const fs::path res = proj / "res-override";
		for (const char* values : { "values", "values-ja", "values-zh-rCN", "values-zh-rTW" })
			writeText(res / values / "strings.xml", "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<resources>\n    <string name=\"app_name\">" +
			          androidString(str(s_, "identity.title")) + "</string>\n</resources>\n");
		if (icons_.loaded()) {
			writeText(res / "values" / "colors.xml", "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<resources>\n    <color name=\"ic_launcher_background\">#FF000000</color>\n</resources>\n");
			// the adaptive icon's 72dp visible square, inside its 108dp layer
			const std::string inset = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<inset xmlns:android=\"http://schemas.android.com/apk/res/android\"\n"
				"    android:drawable=\"@mipmap/kagex_release_icon\" android:inset=\"16.667%\" />\n";
			writeText(res / "drawable" / "ic_launcher_foreground.xml", inset);
			writeText(res / "drawable" / "ic_launcher_monochrome.xml", inset);
			for (const auto& [dir, px] : std::vector<std::pair<const char*, int>>{ { "mipmap-mdpi", 72 }, { "mipmap-hdpi", 108 }, { "mipmap-xhdpi", 144 }, { "mipmap-xxhdpi", 216 }, { "mipmap-xxxhdpi", 288 } }) {
				std::string png;
				if (!icons_.png(px, png, err)) throw Failure{ "The icon: " + err };
				writeText(res / dir / "kagex_release_icon.png", png);
			}
		}

		const fs::path sdk = androidSdk();
		if (sdk.empty()) throw Failure{ "No Android SDK found (set ANDROID_HOME)" };
		writeText(proj / "local.properties", "sdk.dir=" + propertiesPath(sdk) + "\n");

		RunOptions opt;
		opt.workDir = proj;
		opt.timeoutSeconds = 3600;
		opt.env = { { "PROJECT_DIR", krt::fromPath(proj) }, { "ANDROID_HOME", krt::fromPath(sdk) } };
		const fs::path jdk = javaHome();
		if (!jdk.empty()) opt.env.push_back({ "JAVA_HOME", krt::fromPath(jdk) });
		const std::string ks = str(s_, base + "keystore");
		if (!ks.empty()) {
			auto secret = [&](const char* key, const char* env) {
				auto it = o_.secrets.find(key);
				return it != o_.secrets.end() ? it->second : getEnv(env);
			};
			const std::string storePass = secret("androidStorePassword", "KAGEX_ANDROID_STORE_PASSWORD");
			std::string keyPass = secret("androidKeyPassword", "KAGEX_ANDROID_KEY_PASSWORD");
			if (storePass.empty()) throw Failure{ "The keystore's password wasn't given (the window asks for it; on the command line set KAGEX_ANDROID_STORE_PASSWORD)" };
			if (keyPass.empty()) keyPass = storePass;
			opt.env.push_back({ "RELEASE_STORE_FILE", krt::fromPath(fs::absolute(p_.root / krt::toPath(ks))) });
			opt.env.push_back({ "RELEASE_STORE_PASSWORD", storePass });
			opt.env.push_back({ "RELEASE_KEY_ALIAS", str(s_, base + "keyAlias") });
			opt.env.push_back({ "RELEASE_KEY_PASSWORD", keyPass });
		}
		const bool aab = str(s_, base + "format") == "aab";
		const std::string task = std::string(":app:") + (aab ? "bundle" : "assemble") + (ks.empty() ? "ReleaseDebugSigned" : "Release");
		std::string logText;
		opt.onLine = [&](const std::string& l) {
			logText += l + "\n";
			if (l.rfind("> Task", 0) == 0) pr.progress(-1, "Gradle: " + l.substr(7));
			else if (!l.empty()) pr.log("gradle: " + l);
		};
		opt.canceled = [&]() { return pr.canceled(); };
#ifdef _WIN32
		const fs::path gradlew = proj / "gradlew.bat";
#else
		const fs::path gradlew = proj / "gradlew";
#endif
		pr.log("Gradle " + task + " (the first build downloads Gradle and the Android build tools)");
		const RunResult r = run(krt::fromPath(gradlew), { "--no-daemon", "--console=plain", task }, opt);
		writeText(out_ / "android-build.log", logText.empty() ? r.output : logText);
		if (!r.ok()) throw Failure{ std::string(r.timedOut ? "Gradle took over an hour" : "Gradle failed") + " (see android-build.log)" };

		const std::string ext = aab ? ".aab" : ".apk";
		fs::path found;
		fs::file_time_type newest{};
		for (fs::recursive_directory_iterator it(proj / "build", ec), end; it != end; it.increment(ec)) {
			if (ec || !it->is_regular_file(ec) || lower(krt::fromPath(it->path().extension())) != ext) continue;
			if (krt::fromPath(it->path()).find("outputs") == std::string::npos) continue;
			const auto t = it->last_write_time(ec);
			if (found.empty() || t > newest) { found = it->path(); newest = t; }
		}
		if (found.empty()) throw Failure{ "Gradle made no " + ext + " (see android-build.log)" };
		package = out_ / krt::toPath(exe + "-" + version + ext);
		copyFile(found, package);
		if (ks.empty()) notes_.push_back("android: signed with a debug key, for testing (Google Play needs your own key)");
	}

	//-----------------------------------------------------------------------
	// iOS: the engine's app (device or Simulator) given the game's data, names, version and icon,
	// and signed: ad hoc for the Simulator, with the developer's certificate and provisioning
	// profile for devices (an .ipa)
	//-----------------------------------------------------------------------
	RunResult mustRun(const std::string& what, const std::string& program, const std::vector<std::string>& args, int timeout = 600)
	{
		RunOptions opt;
		opt.timeoutSeconds = timeout;
		RunResult r = run(program, args, opt);
		if (!r.ok()) throw Failure{ what + " failed: " + krt::trim(r.output) };
		return r;
	}

	void buildIos(const fs::path& engine, krt::Progress& pr, fs::path& package)
	{
		const std::string base = "platforms.ios.";
		const bool device = str(s_, base + "target") == "device";
		std::error_code ec;
		fs::path src;
		for (const auto& e : fs::directory_iterator(engine / (device ? "device" : "simulator"), ec))
			if (e.is_directory(ec) && e.path().extension() == ".app") src = e.path();
		if (src.empty()) throw Failure{ std::string("The iOS engine package has no app for ") + (device ? "devices" : "the Simulator") };

		const fs::path dir = work_ / "ios";
		mustRemove(dir);
		const std::string exe = str(s_, "identity.exeName"), version = str(s_, "identity.version");
		const fs::path app = dir / "Payload" / krt::toPath(exe + ".app");
		copyTree(src, app);
		for (const char* gone : { "data", "data.xp3", "_CodeSignature", "embedded.mobileprovision" }) fs::remove_all(app / gone, ec);
		scenesInto("ios", app);

		// Info.plist (Xcode writes it binary: edited as XML, written back binary)
		const fs::path plist = app / "Info.plist";
		mustRun("plutil", "plutil", { "-convert", "xml1", krt::fromPath(plist) });
		std::string xml;
		krt::readFile(plist, xml);
		const long long build = at(s_, base + "buildNumber").asInt() > 0 ? at(s_, base + "buildNumber").asInt() : versionNumber(version);
		plistSet(xml, "CFBundleIdentifier", str(s_, base + "bundleId"));
		plistSet(xml, "CFBundleDisplayName", str(s_, "identity.shortName"));
		plistSet(xml, "CFBundleName", str(s_, "identity.shortName").substr(0, 15));
		plistSet(xml, "CFBundleShortVersionString", version);
		plistSet(xml, "CFBundleVersion", std::to_string(build));
		plistSet(xml, "NSHumanReadableCopyright", str(s_, "identity.copyright"));
		const std::string minOs = plistGet(xml, "MinimumOSVersion").empty() ? "16.0" : plistGet(xml, "MinimumOSVersion");
		writeText(plist, xml);

		// the icon: an asset catalog with the 1024 icon, compiled by actool into the app
		if (icons_.loaded()) {
			pr.progress(-1, "Compiling the icon");
			const fs::path set = dir / "Assets.xcassets" / "AppIcon.appiconset";
			std::string png, err;
			if (!icons_.png(1024, png, err)) throw Failure{ "The icon: " + err };
			writeText(set / "icon-1024.png", png);
			writeText(set / "Contents.json", "{\n  \"images\" : [ { \"filename\" : \"icon-1024.png\", \"idiom\" : \"universal\", \"platform\" : \"ios\", \"size\" : \"1024x1024\" } ],\n"
			                                 "  \"info\" : { \"author\" : \"xcode\", \"version\" : 1 }\n}\n");
			writeText(dir / "Assets.xcassets" / "Contents.json", "{\n  \"info\" : { \"author\" : \"xcode\", \"version\" : 1 }\n}\n");
			for (const auto& e : fs::directory_iterator(app, ec)) {
				const std::string n = krt::fromPath(e.path().filename());
				if (n == "Assets.car" || n.rfind("AppIcon", 0) == 0) fs::remove(e.path(), ec);
			}
			const fs::path partial = dir / "icon-info.plist";
			mustRun("actool", "xcrun", { "actool", krt::fromPath(dir / "Assets.xcassets"), "--compile", krt::fromPath(app),
				"--platform", device ? "iphoneos" : "iphonesimulator", "--minimum-deployment-target", minOs, "--app-icon", "AppIcon",
				"--target-device", "iphone", "--target-device", "ipad", "--output-partial-info-plist", krt::fromPath(partial),
				"--output-format", "human-readable-text" }, 300);
			// the icon entries actool made replace the engine's
			RunOptions opt;
			opt.timeoutSeconds = 60;
			run("/usr/libexec/PlistBuddy", { "-c", "Delete :CFBundleIcons", krt::fromPath(plist) }, opt);
			run("/usr/libexec/PlistBuddy", { "-c", "Delete :CFBundleIcons~ipad", krt::fromPath(plist) }, opt);
			// PlistBuddy splits its command at spaces: the file to merge goes where a path has none
			fs::path merge = fs::temp_directory_path(ec) / ("kagex-release-icons-" + std::to_string(std::hash<std::string>()(krt::fromPath(dir)) % 1000000) + ".plist");
			if (krt::fromPath(merge).find(' ') != std::string::npos) merge = "/tmp/kagex-release-icons.plist";
			copyFile(partial, merge);
			const RunResult mr = run("/usr/libexec/PlistBuddy", { "-c", "Merge " + krt::fromPath(merge), krt::fromPath(plist) }, opt);
			fs::remove(merge, ec);
			if (!mr.ok()) throw Failure{ "PlistBuddy failed: " + krt::trim(mr.output) };
		}
		mustRun("plutil", "plutil", { "-convert", "binary1", krt::fromPath(plist) });

		dataInto("ios", app);
		licensesInto(engine, app);
		if (encryptedXp3For("ios")) archiveKeyInto("ios", app);   // key the engine before signing

		pr.progress(-1, "Signing the app");
		if (!device) {
			mustRun("codesign", "codesign", { "--force", "--sign", "-", "--timestamp=none", krt::fromPath(app) });
			package = out_ / krt::toPath(packageBaseName(s_, "ios") + "-simulator.zip");
			std::string err;
			fs::remove(package, ec);
			if (!zipFolder(dir / "Payload", package, "", err)) throw Failure{ err };
			return;
		}
		const std::string identity = str(s_, base + "identity");
		const fs::path profile = fs::absolute(p_.root / krt::toPath(str(s_, base + "profile")));
		copyFile(profile, app / "embedded.mobileprovision");
		const fs::path decoded = dir / "profile.plist", ents = dir / "entitlements.plist";
		{
			RunOptions opt;
			opt.timeoutSeconds = 60;
			// a provisioning profile is a signed plist; an unsigned one is taken as it is (tests)
			if (!run("security", { "cms", "-D", "-i", krt::fromPath(profile), "-o", krt::fromPath(decoded) }, opt).ok())
				copyFile(profile, decoded);
		}
		mustRun("Reading the provisioning profile", "plutil", { "-extract", "Entitlements", "xml1", "-o", krt::fromPath(ents), krt::fromPath(decoded) });
		{
			RunOptions opt;
			opt.timeoutSeconds = 60;
			const RunResult r = run("plutil", { "-extract", "Entitlements.application-identifier", "raw", "-o", "-", krt::fromPath(decoded) }, opt);
			const std::string appId = krt::trim(r.output), bundle = str(s_, base + "bundleId");
			const size_t dot = appId.find('.');
			const std::string pattern = dot == std::string::npos ? appId : appId.substr(dot + 1);
			const bool match = pattern == bundle || pattern == "*" ||
				(pattern.size() > 1 && pattern.back() == '*' && bundle.rfind(pattern.substr(0, pattern.size() - 1), 0) == 0);
			if (r.ok() && !match) throw Failure{ "The provisioning profile is for " + pattern + ", not " + bundle };
		}
		// what's inside the app first, then the app with the profile's entitlements
		for (fs::recursive_directory_iterator it(app, ec), end; it != end; it.increment(ec)) {
			const std::string ext = krt::fromPath(it->path().extension());
			if (ext == ".dylib" || ext == ".framework") {
				mustRun("codesign", "codesign", { "--force", "--sign", identity, krt::fromPath(it->path()) });
				if (ext == ".framework") it.disable_recursion_pending();
			}
		}
		mustRun("codesign", "codesign", { "--force", "--sign", identity, "--entitlements", krt::fromPath(ents), krt::fromPath(app) });
		mustRun("The signature check", "codesign", { "--verify", "--deep", "--strict", krt::fromPath(app) });
		package = out_ / krt::toPath(exe + "-" + version + ".ipa");
		fs::remove(package, ec);
		std::string err;
		fs::remove_all(dir / "ipa", ec);
		fs::create_directories(dir / "ipa", ec);
		fs::rename(dir / "Payload", dir / "ipa" / "Payload", ec);
		if (!zipFolder(dir / "ipa", package, "", err)) throw Failure{ err };
	}

	//-----------------------------------------------------------------------
	// Web: the krkrz_web site with the game's data, title, manifest and icons
	//-----------------------------------------------------------------------
	void buildWeb(const fs::path& engine, const fs::path& dir)
	{
		std::error_code ec;
		for (const auto& e : fs::directory_iterator(engine, ec)) {
			const std::string n = krt::fromPath(e.path().filename());
			if (n == "engine.json" || n == "license.txt" || n == "licenses") continue;
			if (e.is_directory(ec)) copyTree(e.path(), dir / e.path().filename());
			else copyFile(e.path(), dir / e.path().filename());
		}
		scenesInto("web", dir);
		std::string js;
		if (!krt::readFile(dir / "krkrz.js", js)) throw Failure{ "The web engine has no krkrz.js" };
		// krkrz.data is the engine's preloaded /data.xp3 (the files packager's metadata in
		// krkrz.js says how big it is)
		static const std::regex pre(R"re(files:\[\{filename:"/data\.xp3",start:0,end:\d+\}\],remote_package_size:\d+)re");
		const bool xp3 = str(s_, "platforms.web.data") == "xp3";
		auto preload = [&](uint64_t size) {
			const std::string n = std::to_string(size);
			std::string out = std::regex_replace(js, pre, "files:[{filename:\"/data.xp3\",start:0,end:" + n + "}],remote_package_size:" + n,
			                                     std::regex_constants::format_first_only);
			if (out == js && !std::regex_search(js, pre)) return false;
			writeText(dir / "krkrz.js", out);
			return true;
		};
		std::string config;
		krt::readFile(dir / "webconfig.js", config);
		std::string args = "-orgname=" + str(s_, "identity.orgName") + " -appname=" + str(s_, "identity.appName");
		{
			// the engine's other options (memory pools) stay
			std::smatch m;
			static const std::regex argsRe(R"re(KRKRZ_WEB_DEFAULT_ARGS\s*=\s*"([^"]*)")re");
			if (std::regex_search(config, m, argsRe)) {
				std::string rest = m[1];
				size_t pos = 0;
				while (pos < rest.size()) {
					size_t end = rest.find(' ', pos);
					if (end == std::string::npos) end = rest.size();
					const std::string a = rest.substr(pos, end - pos);
					pos = end + 1;
					if (a.empty() || a.rfind("-orgname=", 0) == 0 || a.rfind("-appname=", 0) == 0 || a.rfind("-debugwin=", 0) == 0) continue;
					args += " " + a;
				}
			}
		}
		if (!flag(s_, "engine.debug")) args += " -debugwin=no";
		if (xp3) {
			copyFile(xp3_, dir / "krkrz.data");
			if (!preload(fs::file_size(xp3_, ec))) throw Failure{ "This web engine's krkrz.js doesn't load krkrz.data as data.xp3; choose files for the web data" };
		} else {
			// the files, in lower case (the site asks for every file in lower case)
			std::map<std::string, std::string> lowerNames;
			Json list = Json::array(), prefetch = Json::array();
			std::vector<std::string> names;
			for (fs::recursive_directory_iterator it(stage_, ec), end; it != end; it.increment(ec)) {
				if (ec || !it->is_regular_file(ec)) continue;
				names.push_back(krt::fromPath(fs::relative(it->path(), stage_, ec)));
			}
			std::sort(names.begin(), names.end());
			for (const auto& n : names) {
				const std::string l = lower(n);
				auto [at, fresh] = lowerNames.emplace(l, n);
				if (!fresh) throw Failure{ "The web needs file names that differ in more than case: " + at->second + " and " + n };
				copyFile(stage_ / krt::toPath(n), dir / "gamedata" / krt::toPath(l));
				list.push(Json(l));
				const std::string ext = l.substr(l.rfind('.') == std::string::npos ? l.size() : l.rfind('.'));
				const bool script = ext == ".ks" || ext == ".tjs" || ext == ".csv" || ext == ".txt" || ext == ".asd" || ext == ".func" || ext == ".sli";
				if (script || l.rfind("system/", 0) == 0) prefetch.push(Json(l));
			}
			writeText(dir / "gamedata.krkrz_files.json", list.dump());
			writeText(dir / "gamedata" / "krkrz_files.json", list.dump());   // where static hosts serve it
			writeText(dir / "krkrz_prefetch.json", prefetch.dump());
			// the engine's own data.xp3 isn't used: an empty one saves every visitor a download
			writeText(dir / "krkrz.data", "");
			if (!preload(0)) notes_.push_back("web: krkrz.data (the engine's sample data) is downloaded but not used");
		}
		auto setVar = [&](const std::string& name, const std::string& value) {
			const std::regex re("var " + name + R"re(\s*=\s*[^;\n]*;)re");
			const std::string line = "var " + name + " = " + value + ";";
			if (std::regex_search(config, re)) config = std::regex_replace(config, re, line);
			else config += line + "\n";
		};
		setVar("KRKRZ_WEB_DATA_XP3", xp3 ? "true" : "false");
		setVar("KRKRZ_WEB_DATA_PRELOAD", "false");
		setVar("KRKRZ_WEB_DEFAULT_WEBBASE", xp3 ? "\"\"" : "\"gamedata/\"");
		setVar("KRKRZ_WEB_DEFAULT_ARGS", Json(args).dump());
		writeText(dir / "webconfig.js", config);
		if (encryptedXp3For("web")) archiveKeyInto("web", dir);   // the key goes into krkrz.wasm
		webPage(dir);
		licensesInto(engine, dir);
	}

	// width and height of a PNG or JPEG (for og:image:width/height); false when it can't tell
	static bool imageSize(const fs::path& file, int& w, int& h)
	{
		std::string d;
		if (!krt::readFile(file, d) || d.size() < 24) return false;
		auto u8 = [&](size_t i) { return (unsigned)(unsigned char)d[i]; };
		auto be16 = [&](size_t i) { return (int)(u8(i) << 8 | u8(i + 1)); };
		if (d.compare(0, 8, "\x89PNG\r\n\x1a\n") == 0) {
			w = (int)(u8(16) << 24 | u8(17) << 16 | u8(18) << 8 | u8(19));
			h = (int)(u8(20) << 24 | u8(21) << 16 | u8(22) << 8 | u8(23));
			return w > 0 && h > 0;
		}
		if (u8(0) != 0xff || u8(1) != 0xd8) return false;
		for (size_t i = 2; i + 9 < d.size();) {
			if (u8(i) != 0xff) return false;
			const unsigned m = u8(i + 1);
			if (m == 0xff) { ++i; continue; }
			if (m >= 0xc0 && m <= 0xcf && m != 0xc4 && m != 0xc8 && m != 0xcc) {
				h = be16(i + 5);
				w = be16(i + 7);
				return w > 0 && h > 0;
			}
			if (m == 0xd8 || (m >= 0xd0 && m <= 0xd7) || m == 0x01) { i += 2; continue; }
			i += 2 + (size_t)be16(i + 2);
		}
		return false;
	}

	// index.html and what goes with it, as .github/platforms/web-static-host.py does for the
	// sample: the title; coi-serviceworker's reload once its worker is ready; the home-screen
	// manifest and icons; link previews (Open Graph, Twitter card); kagex-web.js (updates and Add
	// to Home Screen, from platform/web, built into this tool) and the build's id, in
	// kagex-build.json and in the page (<meta name=kagex-build>, ?v=<id> on its scripts). The
	// added head tags sit between <!--kagex-head--> and <!--/kagex-head-->.
	void webPage(const fs::path& dir)
	{
		std::string html;
		if (!krt::readFile(dir / "index.html", html)) throw Failure{ "The web engine has no index.html" };
		const std::string title = str(s_, "identity.title"), shortName = str(s_, "identity.shortName");
		const std::string description = str(s_, "platforms.web.description"), preview = str(s_, "platforms.web.preview");
		std::string url = str(s_, "platforms.web.url");
		if (!url.empty() && url.back() != '/') url += '/';
		auto esc = [](const std::string& v) {
			std::string o;
			for (char c : v) {
				if (c == '&') o += "&amp;"; else if (c == '<') o += "&lt;"; else if (c == '>') o += "&gt;"; else if (c == '"') o += "&quot;"; else o += c;
			}
			return o;
		};
		std::error_code ec;

		// the files the page uses
		writeText(dir / "kagex-web.js", std::string(reinterpret_cast<const char*>(kKagexWebJs), sizeof(kKagexWebJs)));
		if (icons_.loaded()) {
			for (const auto& [file, size] : std::vector<std::pair<std::string, int>>{ { "icon-192.png", 192 }, { "icon-512.png", 512 }, { "apple-touch-icon.png", 180 } }) {
				std::string png, err;
				if (!icons_.png(size, png, err)) throw Failure{ "The icon: " + err };
				writeText(dir / krt::toPath(file), png);
			}
		}
		for (const char* old : { "preview.jpg", "preview.jpeg", "preview.png", "kagex-build.json" }) fs::remove(dir / old, ec);
		std::string image = "icon-512.png";
		int iw = 512, ih = 512;
		if (!preview.empty()) {
			const fs::path src = p_.root / krt::toPath(preview);
			std::string ext = krt::fromPath(src.extension());
			for (auto& c : ext) c = (char)std::tolower((unsigned char)c);
			image = "preview" + std::string(ext == ".png" ? ".png" : ".jpg");
			copyFile(src, dir / krt::toPath(image));
			if (!imageSize(src, iw, ih)) iw = ih = 0;
		}

		Json app = Json::object();
		app.set("id", Json("./"));
		app.set("name", Json(title));
		app.set("short_name", Json(shortName));
		if (!description.empty()) app.set("description", Json(description));
		app.set("start_url", Json("./"));
		app.set("scope", Json("./"));
		app.set("display", Json("fullscreen"));
		app.set("display_override", Json::array({ "fullscreen", "standalone" }));
		app.set("orientation", Json("landscape"));
		app.set("background_color", Json("#000000"));
		app.set("theme_color", Json("#000000"));
		Json icons = Json::array();
		for (const char* purpose : { "any", "maskable" }) {
			for (int size : { 192, 512 }) {
				Json i = Json::object();
				i.set("src", Json("icon-" + std::to_string(size) + ".png"));
				i.set("sizes", Json(std::to_string(size) + "x" + std::to_string(size)));
				i.set("type", Json("image/png"));
				i.set("purpose", Json(purpose));
				icons.push(std::move(i));
			}
		}
		app.set("icons", std::move(icons));
		writeText(dir / "manifest.webmanifest", app.dump(2) + "\n");

		// the build's id: a hash of every file the page uses
		std::vector<std::string> names;
		for (fs::recursive_directory_iterator it(dir, ec), end; it != end; it.increment(ec)) {
			if (ec || !it->is_regular_file(ec)) continue;
			const std::string n = krt::fromPath(fs::relative(it->path(), dir, ec));
			if (n != "index.html" && n != "kagex-build.json" && n != "serve.py") names.push_back(n);
		}
		std::sort(names.begin(), names.end());
		Sha256 all;
		for (const auto& n : names) {
			std::string hex, err;
			if (!sha256File(dir / krt::toPath(n), hex, err)) throw Failure{ err };
			all.update(n.data(), n.size() + 1);   // the name, its NUL, the file's hash
			all.update(hex.data(), hex.size());
		}
		const std::string build = all.hex().substr(0, 16);
		Json bj = Json::object();
		bj.set("build", Json(build));
		writeText(dir / "kagex-build.json", bj.dump() + "\n");

		// index.html
		const std::string coiTag = "<script src=\"coi-serviceworker.js\"></script>";
		if (html.find("window.coi=") == std::string::npos && html.find(coiTag) != std::string::npos)
			html.replace(html.find(coiTag), 0, "<script>window.coi={doReload:function(){navigator.serviceWorker.ready.then(function(){window.location.reload();});}};</script>");
		const size_t t0 = html.find("<title>"), t1 = html.find("</title>");
		if (t0 == std::string::npos || t1 == std::string::npos || t1 < t0) throw Failure{ "The web engine's index.html has no <title>" };
		html.replace(t0 + 7, t1 - t0 - 7, esc(title));
		static const std::regex block(R"re(<!--kagex-head-->[\s\S]*?<!--/kagex-head-->)re");
		static const std::regex legacy(R"re(<link rel=manifest [^>]*>|<link rel=apple-touch-icon [^>]*>|<meta name=(?:theme-color|mobile-web-app-capable|apple-mobile-web-app-[a-z-]+) [^>]*>)re");
		html = std::regex_replace(html, block, "");
		html = std::regex_replace(html, legacy, "");
		std::string head = "<!--kagex-head--><meta name=kagex-build content=\"" + build + "\">";
		if (!description.empty()) head += "<meta name=description content=\"" + esc(description) + "\">";
		head += "<link rel=manifest href=manifest.webmanifest><link rel=icon href=icon-192.png><meta name=theme-color content=\"#000000\">"
			"<meta name=mobile-web-app-capable content=yes><meta name=apple-mobile-web-app-capable content=yes>"
			"<meta name=apple-mobile-web-app-status-bar-style content=black-translucent>"
			"<meta name=apple-mobile-web-app-title content=\"" + esc(shortName) + "\"><link rel=apple-touch-icon href=apple-touch-icon.png>"
			"<meta property=og:type content=website><meta property=og:site_name content=\"" + esc(title) + "\">"
			"<meta property=og:title content=\"" + esc(title) + "\">";
		if (!description.empty()) head += "<meta property=og:description content=\"" + esc(description) + "\">";
		if (!url.empty()) head += "<meta property=og:url content=\"" + esc(url) + "\">";
		head += "<meta property=og:image content=\"" + esc(url + image) + "\">";
		if (iw > 0) head += "<meta property=og:image:width content=" + std::to_string(iw) + "><meta property=og:image:height content=" + std::to_string(ih) + ">";
		head += "<meta property=og:image:alt content=\"" + esc(title) + "\">";
		head += std::string("<meta name=twitter:card content=") + (preview.empty() ? "summary" : "summary_large_image") + "><!--/kagex-head-->";
		const size_t at = html.find("</title>") + 8;
		html.insert(at, head);

		// kagex-web.js right before webconfig.js (after the page's Module, before krkrz.js), and
		// the scripts with the build's id
		static const std::regex oldTag(R"re(<script src=["']?kagex-web\.js[^"'\s>]*["']?></script>)re");
		html = std::regex_replace(html, oldTag, "");
		static const std::regex configTag(R"re(<script src=["']?webconfig\.js)re");
		std::smatch m;
		if (!std::regex_search(html, m, configTag)) throw Failure{ "The web engine's index.html doesn't load webconfig.js" };
		html.insert((size_t)m.position(0), "<script src=\"kagex-web.js\"></script>");
		for (const char* script : { "webconfig.js", "krkrz.js", "kagex-web.js" }) {
			std::string name = script;
			const std::regex re(std::string(R"re(src=(["']?))re") + std::regex_replace(name, std::regex(R"(\.)"), R"(\.)") + R"re((?:\?v=[0-9a-f]*)?\1(?=[\s>]))re");
			html = std::regex_replace(html, re, "src=\"" + name + "?v=" + build + "\"");
		}
		writeText(dir / "index.html", html);
	}

	//-----------------------------------------------------------------------
	// Packages
	//-----------------------------------------------------------------------
	fs::path archive(const std::string& id, const fs::path& folder)
	{
		std::string kind = str(s_, "output.archive");
		const std::string name = krt::fromPath(folder.filename());
		std::string err;
		if (id == "macos") {
			const bool dmg = str(s_, "platforms.macos.format") == "dmg";
			if (dmg) {
				const fs::path pkg = out_ / krt::toPath(name + ".dmg");
				std::error_code ec;
				fs::remove(pkg, ec);
				RunOptions opt;
				opt.timeoutSeconds = 1800;
				RunResult r = run("hdiutil", { "create", "-volname", str(s_, "identity.title"), "-srcfolder", krt::fromPath(folder),
				                               "-ov", "-format", "UDZO", krt::fromPath(pkg) }, opt);
				if (!r.ok()) throw Failure{ "hdiutil failed: " + krt::trim(r.output) };
				return pkg;
			}
			if (kind == "none") return {};
			// a zip of the app as it is (ditto keeps what the signature covers)
			const fs::path pkg = out_ / krt::toPath(name + ".zip");
			std::error_code ec;
			fs::remove(pkg, ec);
			if (!zipFolder(folder, pkg, "", err)) throw Failure{ err };
			return pkg;
		}
		if (kind == "auto") kind = (id == "linux" || id == "steam") ? "tar.gz" : "zip";
		if (kind == "none") return {};
		const std::string exeName = str(s_, "identity.exeName");
		// executables keep their flag even when packed on Windows
		auto modeOf = [&](const std::string& rel, uint32_t mode) -> uint32_t {
			if ((id == "linux" || id == "steam") && rel == exeName) return 0100755;
			return mode;
		};
		const fs::path pkg = out_ / krt::toPath(name + (kind == "tar.gz" ? ".tar.gz" : ".zip"));
		std::error_code ec;
		fs::remove(pkg, ec);
		const bool ok = kind == "tar.gz" ? tarGzFolder(folder, pkg, name + "/", err, modeOf)
		                                 : zipFolder(folder, pkg, name + "/", err, modeOf);
		if (!ok) throw Failure{ err };
		return pkg;
	}

	void writeChecksums()
	{
		const fs::path file = out_ / "SHA256SUMS";
		std::map<std::string, std::string> sums;
		std::string text;
		if (krt::readFile(file, text)) {
			size_t pos = 0;
			while (pos < text.size()) {
				size_t end = text.find('\n', pos);
				if (end == std::string::npos) end = text.size();
				const std::string line = text.substr(pos, end - pos);
				pos = end + 1;
				const size_t sp = line.find("  ");
				std::error_code ec;
				if (sp != std::string::npos && fs::exists(out_ / krt::toPath(line.substr(sp + 2)), ec)) sums[line.substr(sp + 2)] = line.substr(0, sp);
			}
		}
		for (const auto& p : packages_) {
			std::string hex, err;
			pr_.progress(-1, "Checksums");
			if (!sha256File(p, hex, err)) throw Failure{ err };
			sums[krt::fromPath(p.filename())] = hex;
		}
		std::string outText;
		for (const auto& [n, h] : sums) outText += h + "  " + n + "\n";
		writeText(file, outText);
	}

	//-----------------------------------------------------------------------
	// Test run: this computer's build, for a few seconds, through the engine's REPL
	//-----------------------------------------------------------------------
	// A signed build's test run: start it (no REPL), let it run a few seconds, then read the log
	// for the "signatures verified" line and no failure or script error.
	Json signedTestRun(const fs::path& exe, const fs::path& dir, const std::string& host)
	{
		Json r = Json::object();
		RunOptions opt;
		opt.timeoutSeconds = 120;
		opt.workDir = exe.parent_path();
		opt.env = { { "SDL_AUDIO_DRIVER", "dummy" } };
		if (host == "linux" && getEnv("DISPLAY").empty() && getEnv("WAYLAND_DISPLAY").empty())
			opt.env.push_back({ "SDL_VIDEO_DRIVER", "offscreen" });
		const auto start = std::chrono::steady_clock::now();
		opt.canceled = [&]() {
			if (pr_.canceled()) return true;
			return std::chrono::steady_clock::now() - start > std::chrono::seconds(20);
		};
		const RunResult rr = run(krt::fromPath(exe), { "-datapath=" + krt::fromPath(dir / "save") + "/" }, opt);
		std::string log, raw;
		if (krt::readFile(dir / "save" / "krkr.console.log", raw)) log = utf16leToUtf8(raw);
		if (log.empty()) log = rr.output;
		writeText(out_ / "test-run.log", log);

		std::vector<std::string> errors;
		size_t pos = 0;
		while (pos < log.size()) {
			size_t end = log.find('\n', pos);
			if (end == std::string::npos) end = log.size();
			const std::string line = log.substr(pos, end - pos);
			pos = end + 1;
			if (line.find("Script exception raised") != std::string::npos ||
			    line.find("\xe3\x82\xb9\xe3\x82\xaf\xe3\x83\xaa\xe3\x83\x97\xe3\x83\x88\xe3\x81\xa7\xe4\xbe\x8b\xe5\xa4\x96") != std::string::npos ||
			    line.find("! trace :") != std::string::npos ||
			    line.find("Signature check:") != std::string::npos)
				errors.push_back(krt::trim(line));
		}
		const bool verified = log.find("Signatures verified; starting the game") != std::string::npos;
		r.set("ran", Json(true));
		r.set("started", Json(verified));
		r.set("errors", Json::array(errors));
		r.set("log", Json(krt::fromPath(out_ / "test-run.log")));
		if (!verified && log.find("GLES context is unavailable") != std::string::npos) {
			r.set("inconclusive", Json(true));
			r.set("message", Json("Not tested: the engine found no OpenGL ES driver on this computer (a virtual machine?), so the signed build couldn't start here"));
		} else {
			r.set("ok", Json(verified && errors.empty()));
			if (!verified && !errors.empty()) r.set("message", Json("The signature check stopped the build (see test-run.log)"));
			else if (!verified) r.set("message", Json(rr.started ? "The signed build didn't report its signatures verified within the time limit (see test-run.log)" : "The engine couldn't be started: " + rr.output));
			else if (!errors.empty()) r.set("message", Json("Signatures verified, but there were script errors (see test-run.log)"));
			else r.set("message", Json("Signatures verified and the game started without script errors"));
		}
		pr_.log("Test run: " + r["message"].asStr());
		return r;
	}

	Json testRun(krt::Progress&& pr)
	{
		Json r = Json::object();
		const std::string host = hostId();
		auto it = built_.find(host);
		if (it == built_.end()) {
			r.set("ran", Json(false));
			r.set("message", Json("Nothing was built for this computer (" + host + "), so there's no test run"));
			return r;
		}
		fs::path exe;
		const std::string exeName = str(s_, "identity.exeName");
		if (host == "windows") exe = it->second / krt::toPath(exeName + ".exe");
		else if (host == "linux") exe = it->second / krt::toPath(exeName);
		else exe = it->second / krt::toPath(fileSafe(str(s_, "identity.title")) + ".app") / "Contents" / "MacOS" / "krkrz";

		const fs::path dir = work_ / "test";
		std::error_code ec;
		fs::remove_all(dir, ec);
		fs::create_directories(dir / "save", ec);
		fs::create_directories(dir / "repl", ec);
		pr.progress(-1, "Test run");
		pr.log("Test run: " + krt::fromPath(exe));

		// A signed build refuses the REPL (it's an injection route), so its test run reads the log
		// instead of driving the engine through the REPL.
		if (signing_) return signedTestRun(exe, dir, host);

		RunOptions opt;
		opt.timeoutSeconds = 120;
		opt.workDir = exe.parent_path();
		opt.env = { { "SDL_AUDIO_DRIVER", "dummy" } };
		if (host == "linux" && getEnv("DISPLAY").empty() && getEnv("WAYLAND_DISPLAY").empty())
			opt.env.push_back({ "SDL_VIDEO_DRIVER", "offscreen" });
		const auto start = std::chrono::steady_clock::now();
		std::string state = "starting";
		bool sent = false, started = false;
		std::chrono::steady_clock::time_point startedAt;
		const fs::path cmdTmp = dir / "repl" / "cmd.tmp", cmd = dir / "repl" / "cmd", resp = dir / "repl" / "resp";
		opt.canceled = [&]() {
			if (pr.canceled()) return true;
			const auto now = std::chrono::steady_clock::now();
			if (started) return now - startedAt > std::chrono::seconds(5);   // let the first scenes run
			std::error_code e2;
			if (sent && fs::exists(resp, e2)) {
				std::string text;
				krt::readFile(resp, text);
				fs::remove(resp, e2);
				sent = false;
				if (text.find("kag-running") != std::string::npos) { started = true; startedAt = now; }
			}
			if (!sent && now - start > std::chrono::seconds(2)) {
				krt::writeFile(cmdTmp, "typeof global.kag != \"undefined\" && global.kag !== void ? \"kag-running\" : \"waiting\"");
				fs::rename(cmdTmp, cmd, e2);
				sent = !e2;
			}
			return now - start > std::chrono::seconds(60);
		};
		const RunResult rr = run(krt::fromPath(exe), { "-datapath=" + krt::fromPath(dir / "save") + "/", "-replfile=" + krt::fromPath(dir / "repl") }, opt);
		std::string log;
		std::string raw;
		if (krt::readFile(dir / "save" / "krkr.console.log", raw)) log = utf16leToUtf8(raw);
		if (log.empty()) log = rr.output;
		std::vector<std::string> errors;
		size_t pos = 0;
		while (pos < log.size()) {
			size_t end = log.find('\n', pos);
			if (end == std::string::npos) end = log.size();
			std::string line = log.substr(pos, end - pos);
			pos = end + 1;
			if (line.find("Script exception raised") != std::string::npos || line.find("\xe3\x82\xb9\xe3\x82\xaf\xe3\x83\xaa\xe3\x83\x97\xe3\x83\x88\xe3\x81\xa7\xe4\xbe\x8b\xe5\xa4\x96") != std::string::npos ||
			    line.find("! trace :") != std::string::npos)
				errors.push_back(krt::trim(line));
		}
		writeText(out_ / "test-run.log", log);
		r.set("ran", Json(true));
		r.set("started", Json(started));
		r.set("errors", Json::array(errors));
		r.set("log", Json(krt::fromPath(out_ / "test-run.log")));
		// a computer without an OpenGL ES driver (a virtual machine) can't run the engine: that
		// says nothing about the build
		const bool noGraphics = !started && log.find("GLES context is unavailable") != std::string::npos;
		if (noGraphics) {
			r.set("inconclusive", Json(true));
			r.set("message", Json("Not tested: the engine found no OpenGL ES driver on this computer (a virtual machine?), so the game couldn't start here"));
		} else {
			r.set("ok", Json(started && errors.empty()));
			if (!started) r.set("message", Json(rr.started ? "The game didn't get going within a minute (see test-run.log)" : "The engine couldn't be started: " + rr.output));
			else if (!errors.empty()) r.set("message", Json("Script errors (see test-run.log)"));
			else r.set("message", Json("The game started without script errors"));
		}
		pr.log("Test run: " + r["message"].asStr());
		return r;
	}

	const Json& s_;
	const Project& p_;
	BuildOptions o_;
	krt::Progress& pr_;
	std::vector<std::string> chosen_, notes_;
	fs::path out_, work_, stage_, xp3_;
	std::set<std::string> linked_;
	IconSource icons_;
	std::vector<fs::path> packages_;
	std::map<std::string, fs::path> built_;
	std::map<std::string, std::string> hashes_;   ///< the staged files' SHA-256 (fileList)
	bool patchFailed_ = false;
	Json media_, scripts_;
	// signing
	bool signing_ = false;
	std::string privPem_, pubPem_;                ///< the signing keys (set when signing_)
	std::vector<std::string> partNames_;          ///< folders split out of data.xp3 (signed/large builds)
	std::map<std::string, fs::path> partXp3_;     ///< part name -> work_/<name>.xp3
	ArchiveKey archiveKey_{};     ///< the game's key for an encrypted data.xp3 (when haveArchiveKey_)
	bool haveArchiveKey_ = false;
	bool hashNames_ = false;      ///< one encrypted, name-hashed archive (data.xpc) + a plain bootstrap
	fs::path xpc_;                ///< the hashed archive (work/data.xpc)
	std::string bootstrap_;       ///< the plain bootstrap startup.tjs that mounts it
	SceneKey key_{};             ///< the game's key for compiled scenarios (when haveKey_)
	bool haveKey_ = false;
	bool scenesPsb_ = false;     ///< scenarios compiled to .scn: the engines need the scnfile plugin
	bool scenesSealed_ = false;  ///< and encrypted with the game's scenes key
};

} // namespace

Json build(const Json& settings, const Project& project, const BuildOptions& options, krt::Progress& progress)
{
	Builder b(settings, project, options, progress);
	return b.execute();
}

} // namespace kr
