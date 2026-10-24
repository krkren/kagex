#include "Build.h"

#include <algorithm>
#include <chrono>
#include <map>
#include <regex>
#include <set>
#include <thread>

#include "Archive.h"
#include "Engine.h"
#include "Host.h"
#include "Icons.h"
#include "Plan.h"
#include "Subprocess.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"
#include "krt/xp3/Xp3.h"

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
			if (chosen_.empty()) throw Failure{ "No platform to build" };

			out_ = fs::weakly_canonical(p_.root / krt::toPath(str(s_, "output.folder")));
			work_ = out_ / ".work";
			mustRemove(work_);
			mustMkdirs(work_);

			stage(PartProgress(pr_, 0.0, 0.15));
			if (needsXp3()) packXp3(PartProgress(pr_, 0.15, 0.35));
			prepareIcons();

			const double span = 0.6 / chosen_.size();
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
		pr.progress(0, "Packing data.xp3");
		const auto r = krt::xp3::pack(stage_, xp3_, krt::xp3::PackOptions::defaults(), pr);
		if (r.canceled) throw Failure{ "Canceled" };
		std::error_code ec;
		if (!fs::is_regular_file(xp3_, ec) || r.files == 0) throw Failure{ "Couldn't pack data.xp3" };
		pr.log("data.xp3: " + std::to_string(r.files) + " files, " + std::to_string(r.arcBytes / 1048576) + " MB");
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

		folder = out_ / krt::toPath(packageBaseName(s_, id));
		mustRemove(folder);
		mustMkdirs(folder);
		pr.progress(0.3, "Assembling " + id);
		if (id == "windows") buildWindows(engine, folder);
		else if (id == "linux" || id == "steam") buildLinux(id, engine, folder);
		else if (id == "macos") buildMacos(engine, folder);
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
		const std::string mode = str(s_, "platforms." + id + ".data");
		if (mode == "xp3") copyFile(xp3_, dir / "data.xp3");
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
		writeText(dir / krt::toPath(str(s_, "identity.exeName") + ".cf"), engineConfig(s_, p_));
		const std::string mode = str(s_, "platforms.windows.data");
		if (mode == "bind") bind(exe);
		else dataInto("windows", dir);
		licensesInto(engine, dir);
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
		writeText(dir / krt::toPath(exeName + ".cf"), engineConfig(s_, p_));
		const std::string mode = str(s_, "platforms." + id + ".data");
		if (mode == "bind") bind(exe);
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
		writeText(contents / "MacOS" / "krkrz.cf", engineConfig(s_, p_));
		dataInto("macos", res);
		licensesInto(engine, res);
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
};

} // namespace

Json build(const Json& settings, const Project& project, const BuildOptions& options, krt::Progress& progress)
{
	Builder b(settings, project, options, progress);
	return b.execute();
}

} // namespace kr
