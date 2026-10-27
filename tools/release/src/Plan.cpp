#include "Plan.h"

#include <algorithm>
#include <cctype>
#include <map>
#include <set>

#include "Engine.h"
#include "Host.h"
#include "Layered.h"
#include "Media.h"
#include "Subprocess.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

std::string lower(std::string s)
{
	for (auto& c : s) c = (char)std::tolower((unsigned char)c);
	return s;
}

// '*' and '?' within one name, case-insensitive (Windows and macOS file systems are)
bool matchName(const char* p, const char* s)
{
	while (*p) {
		if (*p == '*') {
			while (*p == '*') ++p;
			if (!*p) return true;
			for (; *s; ++s) if (matchName(p, s)) return true;
			return matchName(p, s);
		}
		if (!*s) return false;
		if (*p != '?' && std::tolower((unsigned char)*p) != std::tolower((unsigned char)*s)) return false;
		++p;
		++s;
	}
	return !*s;
}

std::vector<std::string> split(const std::string& s)
{
	std::vector<std::string> parts;
	size_t start = 0;
	while (start <= s.size()) {
		size_t sl = s.find('/', start);
		if (sl == std::string::npos) sl = s.size();
		if (sl > start) parts.push_back(s.substr(start, sl - start));
		start = sl + 1;
	}
	return parts;
}

bool matchParts(const std::vector<std::string>& pat, size_t pi, const std::vector<std::string>& path, size_t si)
{
	if (pi == pat.size()) return si == path.size();
	if (pat[pi] == "**") {
		for (size_t k = si; k <= path.size(); ++k)
			if (matchParts(pat, pi + 1, path, k)) return true;
		return false;
	}
	if (si == path.size()) return false;
	return matchName(pat[pi].c_str(), path[si].c_str()) && matchParts(pat, pi + 1, path, si + 1);
}

bool isAudioSource(const std::string& ext) { return ext == ".wav" || ext == ".flac"; }
bool isImageSource(const std::string& ext) { return ext == ".png" || ext == ".bmp" || ext == ".tlg"; }
bool isScript(const std::string& ext)
{
	return ext == ".ks" || ext == ".tjs" || ext == ".csv" || ext == ".txt" || ext == ".asd" || ext == ".json" || ext == ".func";
}
// Files the game reads layers from: clipfile's clip:// and psdfile's psd://. They're art sources,
// left out by default (*.clip, *.psd), unless a script names one
bool isLayeredSource(const std::string& ext) { return ext == ".clip" || ext == ".psd"; }

std::string extOf(const std::string& name)
{
	const size_t sl = name.find_last_of("/\\");
	const size_t dot = name.rfind('.');
	return dot == std::string::npos || (sl != std::string::npos && dot < sl) ? std::string() : lower(name.substr(dot));
}

std::string leafOf(const std::string& name)
{
	const size_t sl = name.find_last_of("/\\");
	return sl == std::string::npos ? name : name.substr(sl + 1);
}

// The script as UTF-8: UTF-16LE (with a BOM) converted, anything else as it is (UTF-8, or
// Shift_JIS, whose single-byte characters are ASCII)
std::string scriptText(const std::string& raw)
{
	if (raw.size() < 2 || (unsigned char)raw[0] != 0xFF || (unsigned char)raw[1] != 0xFE) return raw;
	std::string out;
	for (size_t i = 2; i + 1 < raw.size(); i += 2) {
		uint32_t cp = (unsigned char)raw[i] | ((unsigned char)raw[i + 1] << 8);
		if (cp >= 0xD800 && cp < 0xDC00 && i + 3 < raw.size()) {
			const uint32_t lo = (unsigned char)raw[i + 2] | ((unsigned char)raw[i + 3] << 8);
			if (lo >= 0xDC00 && lo < 0xE000) { cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00); i += 2; }
		}
		if (cp < 0x80) out += (char)cp;
		else if (cp < 0x800) { out += (char)(0xC0 | (cp >> 6)); out += (char)(0x80 | (cp & 0x3F)); }
		else if (cp < 0x10000) { out += (char)(0xE0 | (cp >> 12)); out += (char)(0x80 | ((cp >> 6) & 0x3F)); out += (char)(0x80 | (cp & 0x3F)); }
		else { out += (char)(0xF0 | (cp >> 18)); out += (char)(0x80 | ((cp >> 12) & 0x3F)); out += (char)(0x80 | ((cp >> 6) & 0x3F)); out += (char)(0x80 | (cp & 0x3F)); }
	}
	return out;
}

// The .clip and .psd files the scripts load layers from, as lower-case leaf names: the file in
// clip://name.clip/root/... and psd://name.psd/root/...
std::set<std::string> layeredFilesNamed(const std::vector<GameFile>& files)
{
	std::set<std::string> named;
	for (const auto& f : files) {
		if (!isScript(extOf(f.name))) continue;
		std::string raw;
		if (!krt::readFile(f.source, raw)) continue;
		const std::string text = scriptText(raw);
		const std::string low = lower(text);
		for (const char* scheme : { "clip://", "psd://" }) {
			const size_t n = std::string(scheme).size();
			for (size_t at = low.find(scheme); at != std::string::npos; at = low.find(scheme, at + n)) {
				size_t end = at + n;
				while (end < text.size() && text[end] != '/' && text[end] != '"' && text[end] != '\'' &&
				       text[end] != ']' && text[end] != '\r' && text[end] != '\n' && text[end] != ' ' && text[end] != '\t')
					++end;
				if (end < text.size() && text[end] == '/' && end > at + n) named.insert(lower(text.substr(at + n, end - at - n)));
			}
		}
	}
	return named;
}

// The names characters drawn from layers take their poses from: the files column of
// charinit.csv (character,pose,files,...), lower case, without a folder. A pose's layers at a level
// are <files>_<level>.txt, or, when there's none, <files>_<level>.psd or .clip
// (KAGEnvCharacterEx.tjs's findStandLayerFile), and <files>.txt etc. without levels
std::set<std::string> charinitFiles(const std::vector<GameFile>& files)
{
	std::set<std::string> names;
	for (const auto& f : files) {
		if (lower(leafOf(f.name)) != "charinit.csv") continue;
		std::string raw;
		if (!krt::readFile(f.source, raw)) continue;
		std::string text = scriptText(raw);
		if (text.size() >= 3 && text.compare(0, 3, "\xEF\xBB\xBF") == 0) text.erase(0, 3);
		size_t pos = 0;
		while (pos < text.size()) {
			size_t end = text.find('\n', pos);
			if (end == std::string::npos) end = text.size();
			const std::string line = text.substr(pos, end - pos);
			pos = end + 1;
			std::vector<std::string> cols;
			size_t start = 0;
			for (;;) {
				const size_t comma = line.find(',', start);
				std::string c = krt::trim(line.substr(start, comma == std::string::npos ? std::string::npos : comma - start));
				if (c.size() >= 2 && c.front() == '"' && c.back() == '"') c = c.substr(1, c.size() - 2);
				cols.push_back(c);
				if (comma == std::string::npos) break;
				start = comma + 1;
			}
			if (cols.size() < 3 || cols[0].empty() || cols[0][0] == '#' || cols[2].empty()) continue;
			names.insert(lower(leafOf(cols[2])));
		}
	}
	return names;
}

// Whether a .psd or .clip (its lower-case leaf) is a pose's layers by charinit.csv's names
bool namedByCharinit(const std::string& leaf, const std::set<std::string>& names)
{
	const size_t dot = leaf.rfind('.');
	const std::string stem = leaf.substr(0, dot);
	for (const auto& n : names) {
		if (stem == n || (stem.size() > n.size() + 1 && stem.compare(0, n.size() + 1, n + "_") == 0)) return true;
	}
	return false;
}

} // namespace

bool matchExclude(const std::string& pattern, const std::string& path, bool isDir)
{
	std::string pat = pattern;
	bool dirOnly = false;
	if (!pat.empty() && pat.back() == '/') { dirOnly = true; pat.pop_back(); }
	if (pat.empty()) return false;
	if (dirOnly && !isDir) return false;
	if (pat.find('/') == std::string::npos) {
		const size_t sl = path.rfind('/');
		return matchName(pat.c_str(), path.c_str() + (sl == std::string::npos ? 0 : sl + 1));
	}
	if (pat[0] == '/') pat.erase(0, 1);
	return matchParts(split(pat), 0, split(path), 0);
}

std::vector<GameFile> collectGameFiles(const Json& s, const Project& p, int* excluded)
{
	std::vector<GameFile> files;
	std::vector<std::string> patterns;
	const Json& exclude = at(s, "contents.exclude");
	for (const auto& e : exclude.elements()) patterns.push_back(e.asStr());
	int skipped = 0;
	std::error_code ec;
	const fs::path outDir = fs::weakly_canonical(p.root / krt::toPath(str(s, "output.folder")), ec);
	const bool keepFont = !at(s, "contents.font").isBool() || flag(s, "contents.font");

	std::vector<GameFile> layered;   // .clip and .psd files a pattern left out
	auto walk = [&](const fs::path& dir, const std::string& prefix) {
		std::error_code ec2;
		for (fs::recursive_directory_iterator it(dir, fs::directory_options::skip_permission_denied, ec2), end;
		     it != end; it.increment(ec2)) {
			if (ec2) break;
			const bool isDir = it->is_directory(ec2);
			const std::string rel = prefix + krt::fromPath(fs::relative(it->path(), dir, ec2));
			const std::string leaf = krt::fromPath(it->path().filename());
			bool skip = !leaf.empty() && leaf[0] == '.';   // .git, .DS_Store and the like
			if (!skip && isDir && fs::weakly_canonical(it->path(), ec2) == outDir) skip = true;
			bool excludedByPattern = false;
			for (const auto& pat : patterns) if (!skip && matchExclude(pat, rel, isDir)) skip = excludedByPattern = true;
			if (!skip && !isDir && !keepFont && lower(leaf) == "notosansjp-regular.otf") skip = true;
			if (skip) {
				if (isDir) it.disable_recursion_pending();
				else if (excludedByPattern && isLayeredSource(extOf(leaf)))
					layered.push_back({ it->path(), rel, (uint64_t)it->file_size(ec2) });
				++skipped;
				continue;
			}
			if (isDir || !it->is_regular_file(ec2)) continue;
			files.push_back({ it->path(), rel, (uint64_t)it->file_size(ec2) });
		}
	};
	walk(p.data, "");
	if (!p.frameworkInData && !p.framework.empty() && flag(s, "contents.framework")) walk(p.framework, "system/");
	// ... go in after all when a script loads layers from them (clip://, psd://), or when they're
	// the poses charinit.csv names and the game has no layer structure of that name (.txt) the
	// framework would read first. kagex-release splits them into the structure and pictures
	// (Layered.h), which a framework from after KAGEX 0.9.2 reads
	if (!layered.empty()) {
		const std::set<std::string> named = layeredFilesNamed(files);
		std::set<std::string> poses, have;
		if (!p.framework.empty() && frameworkReadsSplitLayers(p.framework)) {
			poses = charinitFiles(files);
			for (const auto& f : files) have.insert(lower(leafOf(f.name)));
		}
		for (auto& f : layered) {
			const std::string leaf = lower(leafOf(f.name));
			const bool pose = namedByCharinit(leaf, poses) && !have.count(leaf.substr(0, leaf.rfind('.')) + ".txt");
			if (!named.count(leaf) && !pose) continue;
			files.push_back(std::move(f));
			--skipped;
		}
	}
	std::sort(files.begin(), files.end(), [](const GameFile& a, const GameFile& b) { return a.name < b.name; });
	if (excluded) *excluded = skipped;
	return files;
}

std::string packageBaseName(const Json& s, const std::string& platform)
{
	return str(s, "identity.exeName") + "-" + str(s, "identity.version") + "-" + platform;
}

const std::vector<std::string>& splitFolderNames()
{
	static const std::vector<std::string> names = {
		"bgimage", "bgm", "effect", "evimage", "face", "fgimage", "image", "others", "rule",
		"scenario", "sound", "thum", "uipsd", "video", "voice" };
	return names;
}

Json makePlan(const Json& s, const Project& p)
{
	Json plan = Json::object();
	int excluded = 0;
	const auto files = collectGameFiles(s, p, &excluded);
	uint64_t bytes = 0;
	std::map<std::string, std::pair<int, uint64_t>> byExt;
	int images = 0, audio = 0, scripts = 0, layeredFiles = 0;
	const std::string audioTo = str(s, "media.audio.convert");
	const bool imagesKept = str(s, "media.images.opaque") == "keep" && str(s, "media.images.alpha") == "keep";
	for (const auto& f : files) {
		bytes += f.size;
		std::string ext = lower(krt::fromPath(krt::toPath(f.name).extension()));
		auto& e = byExt[ext.empty() ? "(none)" : ext];
		e.first++;
		e.second += f.size;
		if (isAudioSource(ext) && audioTo != "keep") ++audio;
		if (isImageSource(ext) && !imagesKept) ++images;
		if (ext == ".tjs" && flag(s, "contents.compileScripts")) ++scripts;
		if (isLayeredSource(ext)) ++layeredFiles;
	}
	// the folders a desktop build packs into archives of their own
	std::vector<std::string> parts;
	for (const auto& n : splitFolderNames()) {
		const std::string prefix = n + "/";
		for (const auto& f : files)
			if (f.name.compare(0, prefix.size(), prefix) == 0) { parts.push_back(n + ".xp3"); break; }
	}
	std::string partList;
	for (const auto& n : parts) partList += (partList.empty() ? "" : ", ") + n;
	const bool hidden = flag(s, "archive.encrypt") && flag(s, "archive.hideNames");
	Json data = Json::object();
	data.set("files", Json((long long)files.size()));
	data.set("bytes", Json((long long)bytes));
	data.set("excluded", Json(excluded));
	data.set("convertImages", Json(images));
	data.set("convertAudio", Json(audio));
	data.set("compileScripts", Json(scripts));
	// .psd and .clip files split into layer pictures (Layered.h), when the framework reads them
	data.set("splitLayered", Json(p.framework.empty() || frameworkReadsSplitLayers(p.framework) ? layeredFiles : 0));
	data.set("framework", Json(p.frameworkInData ? "data/system" : flag(s, "contents.framework") ? "template/system, copied in as data/system" : "not included"));
	Json exts = Json::array();
	std::vector<std::pair<std::string, std::pair<int, uint64_t>>> sorted(byExt.begin(), byExt.end());
	std::sort(sorted.begin(), sorted.end(), [](const auto& a, const auto& b) { return a.second.second > b.second.second; });
	for (const auto& [ext, v] : sorted) {
		Json e = Json::object();
		e.set("ext", Json(ext));
		e.set("files", Json(v.first));
		e.set("bytes", Json((long long)v.second));
		exts.push(std::move(e));
	}
	data.set("byExtension", std::move(exts));
	// compiled scenarios: the scripts in !scnlist.txt
	Json scenes = Json::object();
	const bool compile = flag(s, "scenes.compile") && !p.sceneList.empty();
	int listed = 0;
	std::string list;
	if (compile && krt::readFile(p.sceneList, list)) {
		size_t pos = 0;
		while (pos < list.size()) {
			size_t end = list.find('\n', pos);
			if (end == std::string::npos) end = list.size();
			const std::string line = krt::trim(list.substr(pos, end - pos));
			pos = end + 1;
			if (!line.empty() && line[0] != '#' && line.find(':') == std::string::npos) ++listed;
		}
	}
	scenes.set("compile", Json(compile));
	scenes.set("scripts", Json(listed));
	scenes.set("encrypted", Json(compile && flag(s, "scenes.encrypt")));
	// .scn with the scnfile plugin in this computer's engine, else .scn.json; "" when that
	// engine isn't here yet
	{
		const std::string host = hostId();
		const fs::path engine = engineIfPresent(host, flag(s, "engine.debug"), localEngines({}, p.root));
		scenes.set("format", Json(engine.empty() ? std::string() : engineHasScnfile(engine) ? ".scn" : ".scn.json"));
	}
	data.set("scenes", std::move(scenes));
	plan.set("data", std::move(data));

	const std::string out = str(s, "output.folder");
	const std::string exe = str(s, "identity.exeName");
	const std::string archive = str(s, "output.archive");
	Json outputs = Json::array();
	for (const auto& pl : platforms()) {
		const std::string id = pl.id, base = "platforms." + id + ".";
		if (!flag(s, base + "enabled")) continue;
		const std::string dataMode = str(s, base + "data");
		Json o = Json::object();
		o.set("platform", Json(id));
		o.set("title", Json(pl.title));
		const std::string name = packageBaseName(s, id);
		std::string folder = out + "/" + name, package, kind;
		Json contents = Json::array();
		auto add = [&](const std::string& c) { contents.push(Json(c)); };
		// a desktop's archives: data.xp3 (its startup.tjs the one name kept, with hidden names) and
		// the folders' archives beside it
		const bool splits = (dataMode == "xp3" || dataMode == "bind") &&
			(id == "windows" || id == "linux" || id == "steam" || (id == "macos" && frameworkFindsSplitArchives(p.framework)));
		auto partsEntry = [&](const std::string& where) {
			if (splits && !partList.empty()) add(where + partList);
		};
		auto dataEntry = [&]() {
			if (dataMode == "xp3") add(hidden ? "data.xp3 (the names hidden; its startup.tjs opens the archives)" : "data.xp3");
			else if (dataMode == "folder" || dataMode == "files") add("data/");
			partsEntry("");
		};
		auto archived = [&](const std::string& autoKind) {
			const std::string k = archive == "auto" ? autoKind : archive;
			if (k == "none") return std::string();
			return folder + (k == "tar.gz" ? ".tar.gz" : ".zip");
		};
		if (id == "windows") {
			add(exe + ".exe" + (dataMode == "bind" ? " (with the data bound in)" : ""));
			add(exe + ".cf");
			add("SDL3.dll");
			add("plugin/");
			dataEntry();
			package = archived("zip");
		} else if (id == "linux" || id == "steam") {
			add(exe + (dataMode == "bind" ? " (with the data bound in)" : ""));
			add(exe + ".cf");
			add("libSDL3.so.0");
			add("plugin/");
			dataEntry();
			if (flag(s, base + "desktopEntry") && id == "linux") add(exe + ".desktop, " + exe + ".png");
			package = archived("tar.gz");
		} else if (id == "macos") {
			const std::string app = str(s, "identity.title") + ".app";
			add(app);
			add("  Contents/MacOS/krkrz, Contents/Resources/" + std::string(dataMode == "xp3" ? "data.xp3" : "data/"));
			partsEntry("  Contents/Resources/");
			package = str(s, base + "format") == "dmg" ? folder + ".dmg" : archived("zip");
		} else if (id == "web") {
			add("index.html, krkrz.js, krkrz.wasm, coi-serviceworker.js, manifest.webmanifest, icons");
			add(dataMode == "xp3" ? "gamedata/data.xp3" : "gamedata/ (each file loaded when the game needs it)");
			package = archived("zip");
		} else if (id == "android") {
			const std::string fmt = str(s, base + "format");
			folder.clear();
			package = out + "/" + exe + "-" + str(s, "identity.version") + (fmt == "aab" ? ".aab" : ".apk");
			add(std::string("application ID ") + str(s, base + "applicationId") + ", versionCode " +
			    std::to_string(at(s, base + "versionCode").asInt() > 0 ? at(s, base + "versionCode").asInt() : versionNumber(str(s, "identity.version"))));
			add(std::string("assets/") + (dataMode == "xp3" ? "data.xp3" : "data/"));
		} else if (id == "ios") {
			const bool device = str(s, base + "target") == "device";
			folder.clear();
			package = device ? out + "/" + exe + "-" + str(s, "identity.version") + ".ipa"
			                 : out + "/" + name + "-simulator.zip";
			add(std::string("bundle ID ") + str(s, base + "bundleId") + (device ? ", signed for devices" : ", for the Simulator"));
			add(std::string(dataMode == "xp3" ? "data.xp3" : "data/") + " in the app");
		}
		o.set("folder", Json(folder));
		o.set("package", Json(package));
		o.set("contents", std::move(contents));
		outputs.push(std::move(o));
	}
	plan.set("outputs", std::move(outputs));
	return plan;
}

} // namespace kr
