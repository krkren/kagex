#include "Plan.h"

#include <algorithm>
#include <cctype>
#include <map>

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
			for (const auto& pat : patterns) if (!skip && matchExclude(pat, rel, isDir)) skip = true;
			if (!skip && !isDir && !keepFont && lower(leaf) == "notosansjp-regular.otf") skip = true;
			if (skip) {
				if (isDir) it.disable_recursion_pending();
				++skipped;
				continue;
			}
			if (isDir || !it->is_regular_file(ec2)) continue;
			files.push_back({ it->path(), rel, (uint64_t)it->file_size(ec2) });
		}
	};
	walk(p.data, "");
	if (!p.frameworkInData && !p.framework.empty() && flag(s, "contents.framework")) walk(p.framework, "system/");
	std::sort(files.begin(), files.end(), [](const GameFile& a, const GameFile& b) { return a.name < b.name; });
	if (excluded) *excluded = skipped;
	return files;
}

std::string packageBaseName(const Json& s, const std::string& platform)
{
	return str(s, "identity.exeName") + "-" + str(s, "identity.version") + "-" + platform;
}

Json makePlan(const Json& s, const Project& p)
{
	Json plan = Json::object();
	int excluded = 0;
	const auto files = collectGameFiles(s, p, &excluded);
	uint64_t bytes = 0;
	std::map<std::string, std::pair<int, uint64_t>> byExt;
	int images = 0, audio = 0;
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
	}
	Json data = Json::object();
	data.set("files", Json((long long)files.size()));
	data.set("bytes", Json((long long)bytes));
	data.set("excluded", Json(excluded));
	data.set("convertImages", Json(images));
	data.set("convertAudio", Json(audio));
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
		auto dataEntry = [&]() {
			if (dataMode == "xp3") add("data.xp3");
			else if (dataMode == "folder" || dataMode == "files") add("data/");
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
