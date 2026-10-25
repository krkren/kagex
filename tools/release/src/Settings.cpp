#include "Settings.h"

#include <cctype>
#include <regex>
#include <set>

#include "Media.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

Json strings(std::initializer_list<const char*> items)
{
	Json a = Json::array();
	for (const char* s : items) a.push(Json(s));
	return a;
}

Json obj(std::initializer_list<std::pair<const char*, Json>> members)
{
	Json o = Json::object();
	for (const auto& [k, v] : members) o.set(k, v);
	return o;
}

std::string hostPlatform()
{
#if defined(_WIN32)
	return "windows";
#elif defined(__APPLE__)
	return "macos";
#else
	return "linux";
#endif
}

// "My Game" by "Some Maker" -> com.somemaker.mygame (letters and digits only in each part, so it
// is valid for Android, iOS and macOS alike)
std::string defaultBundleId(const std::string& org, const std::string& app)
{
	auto part = [](const std::string& s, const char* fallback) {
		std::string out;
		for (unsigned char c : s)
			if (std::isalnum(c) && c < 0x80) out += (char)std::tolower(c);
		if (out.empty() || std::isdigit((unsigned char)out[0])) out = fallback + out;
		return out;
	};
	return "com." + part(org, "studio") + "." + part(app, "game");
}

bool reservedNames(const std::string& org, const std::string& app)
{
	auto lower = [](std::string s) { for (auto& c : s) c = (char)std::tolower((unsigned char)c); return s; };
	const std::string o = lower(org), a = lower(app);
	return (o == "krkren" && a == "kagex") || (o == "wamsoft" && a == "krkrz");
}

bool oneOf(const std::string& v, std::initializer_list<const char*> allowed)
{
	for (const char* a : allowed) if (v == a) return true;
	return false;
}

std::string relativeTo(const fs::path& p, const fs::path& base)
{
	if (p.empty()) return "";
	std::error_code ec;
	fs::path r = fs::relative(p, base, ec);
	return krt::fromPath(ec || r.empty() ? p : r);
}

} // namespace

const std::vector<PlatformInfo>& platforms()
{
	static const std::vector<PlatformInfo> list = {
		{ "windows", "Windows" },
		{ "linux", "Linux" },
		{ "steam", "Linux for Steam" },
		{ "macos", "macOS" },
		{ "web", "Web" },
		{ "android", "Android" },
		{ "ios", "iOS" },
	};
	return list;
}

Json defaultSettings(const Project& p)
{
	const std::string title = !p.title.empty() ? p.title : krt::fromPath(p.root.filename());
	std::string shortName = title;
	if (shortName.size() > 12) {
		const size_t sp = shortName.find(' ');
		shortName = shortName.substr(0, sp != std::string::npos && sp > 0 ? sp : 12);
	}
	std::string org = p.orgName, app = p.appName;
	if (org.empty() || app.empty() || reservedNames(org, app)) {
		org = slug(p.maker);
		app = slug(title);
	}
	std::string exe = slug(title);
	if (exe.empty()) exe = "game";
	std::string copyright;
	if (!p.maker.empty()) copyright = "(c) " + (p.year.empty() ? std::string() : p.year + " ") + p.maker;
	const std::string bundle = defaultBundleId(org.empty() ? p.maker : org, app.empty() ? title : app);
	const std::string host = hostPlatform();

	Json s = Json::object();
	s.set("format", Json(kSettingsFormat));
	s.set("identity", obj({
		{ "title", Json(title) },
		{ "shortName", Json(shortName) },
		{ "exeName", Json(exe) },
		{ "version", Json(p.version.empty() ? std::string("1.0.0") : p.version) },
		{ "copyright", Json(copyright) },
		{ "orgName", Json(org) },
		{ "appName", Json(app) },
		{ "icon", Json(relativeTo(p.icon, p.root)) },
	}));
	s.set("engine", obj({ { "debug", Json(false) } }));
	s.set("contents", obj({
		{ "framework", Json(true) },
		{ "font", Json(true) },
		{ "licenses", Json(true) },
		{ "exclude", strings({ "*.psd", "*.clip", "*.bak", "*.tmp", "Thumbs.db", "desktop.ini", ".DS_Store" }) },
		{ "extraFiles", Json::array() },
		{ "plugins", Json("all") },
		{ "compileScripts", Json(true) },
	}));
	s.set("media", obj({
		{ "audio", obj({
			{ "convert", Json("opus") },
			{ "opusKbps", obj({ { "bgm", Json(128) }, { "sound", Json(96) }, { "voice", Json(64) }, { "*", Json(96) } }) },
			{ "vorbisQuality", Json(5) },
		}) },
		{ "images", obj({
			{ "opaque", Json("tlg6") },
			{ "alpha", Json("tlg6") },
			{ "jpegQuality", Json(90) },
		}) },
		{ "references", Json("keep") },
	}));
	s.set("output", obj({
		{ "folder", Json("release") },
		{ "archive", Json("auto") },
		{ "checksums", Json(true) },
		{ "check", Json(true) },
		{ "patchFrom", Json("") },
	}));
	Json pl = Json::object();
	pl.set("windows", obj({ { "enabled", Json(host == "windows") }, { "data", Json("xp3") }, { "versionInfo", Json(true) } }));
	pl.set("linux", obj({ { "enabled", Json(host == "linux") }, { "data", Json("xp3") }, { "desktopEntry", Json(true) } }));
	pl.set("steam", obj({ { "enabled", Json(false) }, { "data", Json("xp3") } }));
	pl.set("macos", obj({
		{ "enabled", Json(host == "macos") }, { "data", Json("xp3") }, { "bundleId", Json(bundle) },
		{ "signing", Json("adhoc") }, { "identity", Json("") }, { "notarize", Json(false) },
		{ "notaryProfile", Json("") }, { "format", Json("zip") },
	}));
	pl.set("web", obj({
		{ "enabled", Json(false) }, { "data", Json("files") }, { "url", Json("") }, { "description", Json("") },
		{ "preview", Json(p.preview.empty() ? std::string() : relativeTo(p.preview, p.root)) },
	}));
	pl.set("android", obj({
		{ "enabled", Json(false) }, { "format", Json("apk") }, { "data", Json("xp3") },
		{ "applicationId", Json(bundle) }, { "versionCode", Json(0) },
		{ "keystore", Json("") }, { "keyAlias", Json("") },
	}));
	pl.set("ios", obj({
		{ "enabled", Json(false) }, { "target", Json("device") }, { "data", Json("xp3") },
		{ "bundleId", Json(bundle) }, { "buildNumber", Json(0) },
		{ "identity", Json("") }, { "profile", Json("") },
	}));
	s.set("platforms", std::move(pl));
	return s;
}

Json withDefaults(const Json& settings, const Json& defaults)
{
	if (!defaults.isObj() || !settings.isObj()) return settings.isNull() ? defaults : settings;
	Json out = Json::object();
	for (const auto& [k, dv] : defaults.members())
		out.set(k, settings.has(k) ? withDefaults(settings[k], dv) : dv);
	// members the defaults don't know (a newer file, or notes) are kept
	for (const auto& [k, v] : settings.members())
		if (!defaults.has(k)) out.set(k, v);
	return out;
}

const Json& at(const Json& settings, const std::string& dotted)
{
	static const Json null;
	const Json* cur = &settings;
	size_t start = 0;
	while (start <= dotted.size()) {
		size_t dot = dotted.find('.', start);
		if (dot == std::string::npos) dot = dotted.size();
		const std::string key = dotted.substr(start, dot - start);
		if (!cur->isObj() || !cur->has(key)) return null;
		cur = &cur->at(key);
		start = dot + 1;
	}
	return *cur;
}

std::string str(const Json& settings, const std::string& dotted) { return at(settings, dotted).asStr(); }
bool flag(const Json& settings, const std::string& dotted) { return at(settings, dotted).asBool(); }

long long versionNumber(const std::string& version)
{
	long long parts[3] = { 0, 0, 0 };
	int n = 0;
	size_t i = 0;
	while (i < version.size() && n < 3) {
		if (!std::isdigit((unsigned char)version[i])) break;
		long long v = 0;
		while (i < version.size() && std::isdigit((unsigned char)version[i])) v = v * 10 + (version[i++] - '0');
		parts[n++] = v;
		if (i < version.size() && version[i] == '.') ++i;
		else break;
	}
	return parts[0] * 10000 + parts[1] * 100 + parts[2];
}

std::vector<Issue> validate(const Json& s, const Project& p)
{
	std::vector<Issue> out;
	auto error = [&](const std::string& f, const std::string& m) { out.push_back({ "error", f, m }); };
	auto warn = [&](const std::string& f, const std::string& m) { out.push_back({ "warning", f, m }); };
	std::error_code ec;
	auto exists = [&](const std::string& rel) { return fs::exists(p.root / krt::toPath(rel), ec); };

	if (at(s, "format").asInt(kSettingsFormat) > kSettingsFormat)
		error("format", "This release.json is from a newer kagex-release; update the tool");

	// identity
	const std::string title = str(s, "identity.title");
	if (krt::trim(title).empty()) error("identity.title", "The game needs a title");
	if (str(s, "identity.shortName").empty()) error("identity.shortName", "The short name (shown under home screen icons) is empty");
	else if (str(s, "identity.shortName").size() > 16) warn("identity.shortName", "Home screens cut names longer than about 12 characters");

	static const std::regex exeRe(R"([A-Za-z0-9][A-Za-z0-9._-]*)");
	static const std::set<std::string> reservedExe = { "con", "prn", "aux", "nul", "com1", "com2", "com3", "com4",
		"com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9" };
	const std::string exe = str(s, "identity.exeName");
	std::string exeLower = exe;
	for (auto& c : exeLower) c = (char)std::tolower((unsigned char)c);
	if (!std::regex_match(exe, exeRe)) error("identity.exeName", "The file name may use letters, digits, '.', '-' and '_' (no spaces), starting with a letter or digit");
	else if (reservedExe.count(exeLower)) error("identity.exeName", "\"" + exe + "\" is a reserved file name on Windows");

	static const std::regex versionRe(R"(\d{1,5}(\.\d{1,5}){0,2})");
	const std::string version = str(s, "identity.version");
	if (!std::regex_match(version, versionRe)) {
		error("identity.version", "The version must be numbers like 1.0 or 1.2.3 (stores and operating systems accept nothing else)");
	} else {
		size_t a = version.find('.');
		if (a != std::string::npos) {
			size_t b = version.find('.', a + 1);
			const long long minor = std::stoll(version.substr(a + 1, b == std::string::npos ? std::string::npos : b - a - 1));
			const long long patch = b == std::string::npos ? 0 : std::stoll(version.substr(b + 1));
			if ((minor > 99 || patch > 99) && (flag(s, "platforms.android.enabled") || flag(s, "platforms.ios.enabled")))
				warn("identity.version", "Minor and patch numbers above 99 don't fit the automatic Android versionCode / iOS build number; set them yourself");
		}
		if (!p.version.empty() && p.version != version)
			warn("identity.version", "first.ks says sf.software_version = \"" + p.version + "\"; the game shows that one in About");
	}

	static const std::regex nameRe(R"([A-Za-z0-9][A-Za-z0-9._-]*)");
	const std::string org = str(s, "identity.orgName"), app = str(s, "identity.appName");
	if (!std::regex_match(org, nameRe)) error("identity.orgName", "The organization name names the save folder: letters, digits, '.', '-' and '_' (no spaces)");
	if (!std::regex_match(app, nameRe)) error("identity.appName", "The app name names the save folder: letters, digits, '.', '-' and '_' (no spaces)");
	if (reservedNames(org, app)) {
		std::string o = org;
		for (auto& c : o) c = (char)std::tolower((unsigned char)c);
		error("identity.appName", org + "/" + app + " is " + (o == "krkren" ? "the KAGEX sample's" : "the engine's default, shared by every game on it") +
		      ": saves would mix with theirs. Choose names of your own");
	}

	const std::string icon = str(s, "identity.icon");
	if (!icon.empty()) {
		if (!exists(icon)) error("identity.icon", "The icon " + icon + " doesn't exist");
		else if (krt::toPath(icon).extension() != ".png" && krt::toPath(icon).extension() != ".PNG") error("identity.icon", "The icon must be a PNG (1024x1024 is best)");
	} else {
		warn("identity.icon", "No icon: the packages get the KAGEX icon");
	}

	// contents and media
	const std::string plugins = str(s, "contents.plugins");
	if (!oneOf(plugins, { "all", "linked" })) error("contents.plugins", "plugins is \"all\" or \"linked\"");
	if (!p.frameworkInData && p.framework.empty())
		error("contents.framework", "The game has no data/system and there is no template/system next to data/ to copy in");
	if (flag(s, "contents.compileScripts") && flag(s, "engine.debug"))
		warn("contents.compileScripts", "Errors in compiled scripts show no line numbers: a build for testers is easier to debug with the scripts as they are");
	const Json& extra = at(s, "contents.extraFiles");
	for (const auto& e : extra.elements())
		if (!exists(e.asStr())) error("contents.extraFiles", e.asStr() + " doesn't exist");

	if (!oneOf(str(s, "media.audio.convert"), { "opus", "vorbis", "keep" })) error("media.audio.convert", "Audio is converted to \"opus\" or \"vorbis\", or kept (\"keep\")");
	if (str(s, "media.audio.convert") == "opus" && !p.framework.empty() && !frameworkPlaysOpus(p.framework))
		error("media.audio.convert", "This game's framework (" + std::string(p.frameworkInData ? "data/system" : "template/system") +
		      ") doesn't look for .opus files: it predates KAGEX 0.3.0. Choose Ogg Vorbis, or update it from KAGEX 0.3.0's template/system");
	const Json& opusKbps = at(s, "media.audio.opusKbps");
	for (const auto& [folder, kbps] : opusKbps.members())
		if (kbps.asInt() < 6 || kbps.asInt() > 510) error("media.audio.opusKbps", "Opus bitrates are 6 to 510 kbps (" + folder + ": " + std::to_string(kbps.asInt()) + ")");
	const long long vq = at(s, "media.audio.vorbisQuality").asInt(5);
	if (vq < 0 || vq > 10) error("media.audio.vorbisQuality", "The Vorbis quality is 0 to 10");
	if (!oneOf(str(s, "media.images.opaque"), { "tlg6", "tlg5", "png", "jpeg", "keep" })) error("media.images.opaque", "Opaque images become \"tlg6\", \"tlg5\", \"png\" or \"jpeg\", or are kept (\"keep\")");
	if (!oneOf(str(s, "media.images.alpha"), { "tlg6", "tlg5", "png", "jpeg-mask", "keep" })) error("media.images.alpha", "Transparent images become \"tlg6\", \"tlg5\", \"png\" or \"jpeg-mask\", or are kept (\"keep\")");
	{
		const std::string opaque = str(s, "media.images.opaque"), alpha = str(s, "media.images.alpha");
		const bool opaqueConverts = opaque != "png" && opaque != "keep", alphaConverts = alpha != "png" && alpha != "keep";
		if ((opaqueConverts || alphaConverts) && !p.framework.empty() && !frameworkFindsConvertedImages(p.framework))
			error(alphaConverts ? "media.images.alpha" : "media.images.opaque",
			      "This game's framework (" + std::string(p.frameworkInData ? "data/system" : "template/system") +
			      ") looks for buttons' hover, pressed and focus images as .png, .tlg5, .tlg6 or .bmp only: it predates KAGEX 0.3.1, "
			      "and with images converted to TLG or JPEG its buttons wouldn't highlight. Convert images to PNG or keep them, "
			      "or update it from KAGEX 0.3.1's template/system");
	}
	const long long jq = at(s, "media.images.jpegQuality").asInt(90);
	if (jq < 1 || jq > 100) error("media.images.jpegQuality", "The JPEG quality is 1 to 100");
	if (!oneOf(str(s, "media.references"), { "keep", "rewrite" })) error("media.references", "references is \"keep\" or \"rewrite\"");

	// output
	const std::string folder = str(s, "output.folder");
	if (krt::trim(folder).empty()) error("output.folder", "Choose a folder for the packages");
	else {
		fs::path outDir = fs::weakly_canonical(p.root / krt::toPath(folder), ec);
		fs::path data = fs::weakly_canonical(p.data, ec);
		auto rel = fs::relative(outDir, data, ec);
		if (!ec && !rel.empty() && *rel.begin() != "..") error("output.folder", "The output folder can't be inside data/ (it would be packed into the next build)");
	}
	if (!oneOf(str(s, "output.archive"), { "auto", "zip", "tar.gz", "none" })) error("output.archive", "archive is \"auto\", \"zip\", \"tar.gz\" or \"none\"");
	const std::string patchFrom = str(s, "output.patchFrom");
	if (!patchFrom.empty() && !exists(patchFrom)) error("output.patchFrom", "The file list " + patchFrom + " doesn't exist (a build writes <file name>-<version>-files.json beside its packages)");

	// platforms
	int enabled = 0;
	static const std::regex bundleRe(R"([A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+)");
	static const std::regex androidIdRe(R"([A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+)");
	for (const auto& pl : platforms()) {
		const std::string base = std::string("platforms.") + pl.id + ".";
		if (!flag(s, base + "enabled")) continue;
		++enabled;
		const std::string id = pl.id;
		const std::string data = str(s, base + "data");
		if (id == "windows" && !oneOf(data, { "xp3", "folder", "bind" })) error(base + "data", "Windows data is \"xp3\", \"folder\" or \"bind\" (into the exe)");
		if ((id == "linux" || id == "steam") && !oneOf(data, { "xp3", "folder", "bind" }))
			error(base + "data", std::string(pl.title) + " data is \"xp3\", \"folder\" or \"bind\" (into the executable)");
		if ((id == "macos" || id == "android" || id == "ios") && !oneOf(data, { "xp3", "folder" }))
			error(base + "data", std::string(pl.title) + " data is \"xp3\" or \"folder\"");
		if (id == "web" && !oneOf(data, { "files", "xp3" })) error(base + "data", "Web data is \"files\" (loaded as needed) or \"xp3\"");
		if (id == "web") {
			static const std::regex urlRe(R"(https?://[^\s"<>]+)");
			const std::string url = str(s, base + "url"), preview = str(s, base + "preview");
			if (!url.empty() && !std::regex_match(url, urlRe)) error(base + "url", "The site's address starts with https:// (like https://studio.example/game/)");
			if (url.empty()) warn(base + "url", "Without the site's address, link previews (Discord, Slack, X) show no image");
			if (!preview.empty()) {
				std::string ext = krt::fromPath(krt::toPath(preview).extension());
				for (auto& c : ext) c = (char)std::tolower((unsigned char)c);
				if (!exists(preview)) error(base + "preview", "The preview image " + preview + " doesn't exist");
				else if (ext != ".png" && ext != ".jpg" && ext != ".jpeg") error(base + "preview", "The preview image is a PNG or JPEG (1200x630 is best)");
			}
		}
		if (id == "macos") {
			if (!std::regex_match(str(s, base + "bundleId"), bundleRe)) error(base + "bundleId", "The bundle ID looks like com.studio.game (letters, digits and '-')");
			const std::string signing = str(s, base + "signing");
			if (!oneOf(signing, { "adhoc", "developer-id" })) error(base + "signing", "macOS signing is \"adhoc\" or \"developer-id\"");
			if (signing == "developer-id" && str(s, base + "identity").empty()) error(base + "identity", "Developer ID signing needs the certificate's name (Developer ID Application: ...)");
			if (flag(s, base + "notarize") && signing != "developer-id") error(base + "notarize", "Notarization needs Developer ID signing");
			if (flag(s, base + "notarize") && str(s, base + "notaryProfile").empty()) error(base + "notaryProfile", "Notarization needs a notarytool keychain profile (xcrun notarytool store-credentials)");
			if (signing == "adhoc") warn(base + "signing", "Ad hoc signed apps open only after the player allows them (right-click > Open, or System Settings > Privacy & Security)");
			if (!oneOf(str(s, base + "format"), { "zip", "dmg" })) error(base + "format", "The macOS package is \"zip\" or \"dmg\"");
		}
		if (id == "android") {
			if (!std::regex_match(str(s, base + "applicationId"), androidIdRe)) error(base + "applicationId", "The application ID looks like com.studio.game (each part starts with a letter; letters, digits and '_')");
			if (!oneOf(str(s, base + "format"), { "apk", "aab" })) error(base + "format", "The Android package is \"apk\" or \"aab\" (Google Play)");
			const std::string ks = str(s, base + "keystore");
			if (!ks.empty() && !exists(ks)) error(base + "keystore", "The keystore " + ks + " doesn't exist");
			if (!ks.empty() && str(s, base + "keyAlias").empty()) error(base + "keyAlias", "Name the key in the keystore (its alias)");
			if (ks.empty()) warn(base + "keystore", "No keystore: the package is signed with a debug key (fine for testing, not for Google Play)");
			const long long vc = at(s, base + "versionCode").asInt();
			if (vc < 0 || vc > 2100000000) error(base + "versionCode", "versionCode is 1 to 2100000000 (0 = from the version)");
		}
		if (id == "ios") {
			if (!std::regex_match(str(s, base + "bundleId"), bundleRe)) error(base + "bundleId", "The bundle ID looks like com.studio.game (letters, digits and '-')");
			const std::string target = str(s, base + "target");
			if (!oneOf(target, { "device", "simulator" })) error(base + "target", "The iOS build is for a \"device\" or the \"simulator\"");
			if (target == "device") {
				if (str(s, base + "identity").empty()) error(base + "identity", "A device build is signed with your certificate (Apple Development / Apple Distribution: ...)");
				const std::string prof = str(s, base + "profile");
				if (prof.empty()) error(base + "profile", "A device build needs its provisioning profile (.mobileprovision)");
				else if (!exists(prof)) error(base + "profile", "The profile " + prof + " doesn't exist");
			}
		}
	}
	if (!enabled && patchFrom.empty()) error("platforms", "Choose at least one platform");
	return out;
}

bool hasErrors(const std::vector<Issue>& issues)
{
	for (const auto& i : issues) if (i.level == "error") return true;
	return false;
}

bool loadSettings(const fs::path& file, Json& out, std::string& error)
{
	std::string text;
	if (!krt::readFile(file, text)) { error = "Can't read " + krt::fromPath(file); return false; }
	if (text.size() >= 3 && (unsigned char)text[0] == 0xEF && (unsigned char)text[1] == 0xBB && (unsigned char)text[2] == 0xBF) text.erase(0, 3);
	std::string err;
	if (!Json::parse(text, out, &err)) { error = krt::fromPath(file) + ": " + err; return false; }
	if (!out.isObj()) { error = krt::fromPath(file) + ": not a settings file"; return false; }
	return true;
}

bool saveSettings(const fs::path& file, const Json& settings, std::string& error)
{
	if (!krt::writeFile(file, settings.dump(2) + "\n")) { error = "Can't write " + krt::fromPath(file); return false; }
	return true;
}

} // namespace kr
