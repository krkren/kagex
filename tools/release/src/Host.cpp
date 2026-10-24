#include "Host.h"

#include <regex>

#include "Subprocess.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;

namespace kr {

namespace {

Requirement req(std::string name, bool ok, std::string detail)
{
	return Requirement{ std::move(name), ok, std::move(detail) };
}

fs::path homeDir()
{
#ifdef _WIN32
	return krt::toPath(getEnv("USERPROFILE"));
#else
	return krt::toPath(getEnv("HOME"));
#endif
}

// java from JAVA_HOME, else from PATH; its major version (0 when unknown)
Requirement checkJava()
{
	std::string java;
	const std::string javaHome = getEnv("JAVA_HOME");
	if (!javaHome.empty()) {
		fs::path p = krt::toPath(javaHome) / "bin" / "java";
#ifdef _WIN32
		p += ".exe";
#endif
		std::error_code ec;
		if (fs::exists(p, ec)) java = krt::fromPath(p);
	}
	if (java.empty()) java = krt::fromPath(findProgram("java"));
	if (java.empty())
		return req("Java 17 or newer (JDK)", false, "Not found. Install a JDK 17 or newer (Android Studio includes one) and set JAVA_HOME");
	RunOptions opt;
	opt.timeoutSeconds = 30;
	const RunResult r = run(java, { "-version" }, opt);
	std::smatch m;
	static const std::regex re(R"(version "(\d+)(?:\.(\d+))?)");
	if (!std::regex_search(r.output, m, re))
		return req("Java 17 or newer (JDK)", false, java + " didn't say its version");
	int major = std::stoi(m[1]);
	if (major == 1 && m[2].matched) major = std::stoi(m[2]);   // 1.8 = Java 8
	const bool ok = major >= 17;
	return req("Java 17 or newer (JDK)", ok, "Java " + std::to_string(major) + " (" + java + ")" + (ok ? "" : ": too old"));
}

fs::path findAndroidSdkImpl()
{
	std::error_code ec;
	for (const char* var : { "ANDROID_HOME", "ANDROID_SDK_ROOT" }) {
		const std::string v = getEnv(var);
		if (!v.empty() && fs::is_directory(krt::toPath(v), ec)) return krt::toPath(v);
	}
#if defined(_WIN32)
	const fs::path def = krt::toPath(getEnv("LOCALAPPDATA")) / "Android" / "Sdk";
#elif defined(__APPLE__)
	const fs::path def = homeDir() / "Library" / "Android" / "sdk";
#else
	const fs::path def = homeDir() / "Android" / "Sdk";
#endif
	if (fs::is_directory(def, ec)) return def;
	return {};
}

bool isMac()
{
#ifdef __APPLE__
	return true;
#else
	return false;
#endif
}

Requirement needMac(const char* what)
{
	return req("A Mac", isMac(), isMac() ? "macOS" : std::string(what) + " are built and signed with Apple's tools, which run only on macOS");
}

Requirement checkProgram(const std::string& name, const std::string& program, const std::string& missing)
{
	const fs::path p = findProgram(program);
	return req(name, !p.empty(), p.empty() ? missing : krt::fromPath(p));
}

// xcrun --find <tool>: some of Xcode's tools (actool for the icons) are in Xcode, not in the
// command line tools alone
Requirement checkXcodeTool(const std::string& name, const std::string& tool)
{
	if (!isMac()) return req(name, false, "Needs a Mac");
	RunOptions opt;
	opt.timeoutSeconds = 30;
	const RunResult r = run("xcrun", { "--find", tool }, opt);
	if (r.ok()) return req(name, true, krt::trim(r.output));
	return req(name, false, "Install Xcode from the App Store and open it once (xcrun can't find " + tool + ")");
}

// A signing identity in the keychain (security find-identity)
Requirement checkIdentity(const std::string& identity, const std::string& label)
{
	if (!isMac()) return req(label, false, "Needs a Mac");
	if (identity.empty()) return req(label, false, "Not set");
	RunOptions opt;
	opt.timeoutSeconds = 30;
	const RunResult r = run("security", { "find-identity", "-v", "-p", "codesigning" }, opt);
	const bool ok = r.ok() && r.output.find(identity) != std::string::npos;
	return req(label, ok, ok ? identity : "\"" + identity + "\" isn't in the keychain (security find-identity -v -p codesigning)");
}

Requirement checkEngine(const std::string& platform)
{
	std::error_code ec;
	const fs::path cached = cacheDir() / "engines" / KAGEX_RELEASE_VERSION / platform;
	if (fs::is_directory(cached, ec))
		return req("Engine", true, "Downloaded before (" + krt::fromPath(cached) + ")");
#ifdef _WIN32
	const bool canDownload = !findProgram("curl").empty() || !findProgram("powershell").empty();
#else
	const bool canDownload = !findProgram("curl").empty();
#endif
	return req("Engine", canDownload, canDownload
		? std::string("Downloaded from the KAGEX ") + KAGEX_RELEASE_VERSION + " release on the first build"
		: "Needs curl to download it from the KAGEX release");
}

} // namespace

const char* hostId()
{
#if defined(_WIN32)
	return "windows";
#elif defined(__APPLE__)
	return "macos";
#else
	return "linux";
#endif
}

fs::path cacheDir()
{
	const std::string override = getEnv("KAGEX_RELEASE_CACHE");
	if (!override.empty()) return krt::toPath(override);
#if defined(_WIN32)
	return krt::toPath(getEnv("LOCALAPPDATA")) / "kagex-release";
#elif defined(__APPLE__)
	return homeDir() / "Library" / "Caches" / "kagex-release";
#else
	const std::string xdg = getEnv("XDG_CACHE_HOME");
	return (xdg.empty() ? homeDir() / ".cache" : krt::toPath(xdg)) / "kagex-release";
#endif
}

fs::path androidSdk() { return findAndroidSdkImpl(); }

fs::path javaHome()
{
	const std::string env = getEnv("JAVA_HOME");
	if (!env.empty()) return krt::toPath(env);
	fs::path java = findProgram("java");
	std::error_code ec;
	if (java.empty()) return {};
	java = fs::canonical(java, ec);   // /usr/bin/java is usually a link into the JDK
	return java.parent_path().parent_path();
}

PlatformStatus checkPlatform(const std::string& id, const Json& s, const Project& project)
{
	PlatformStatus st;
	st.id = id;
	const std::string base = "platforms." + id + ".";
	const std::string host = hostId();
	auto& rq = st.requirements;
	rq.push_back(checkEngine(id));

	if (id == "windows") {
		if (host != "windows")
			st.notes.push_back("The exe keeps the KAGEX icon and version info: they can be changed only when this tool runs on Windows");
	} else if (id == "linux" || id == "steam") {
		if (host == "windows")
			st.notes.push_back("Built on Windows, the package is a tar.gz or zip that keeps the engine's executable permission; a plain folder copied off Windows loses it");
		if (id == "steam")
			st.notes.push_back("For Steam's Linux Runtime 3.0 (sniper): set the game's launch to run the engine through it in Steamworks");
	} else if (id == "macos") {
		rq.push_back(needMac("macOS apps"));
		if (isMac()) {
			rq.push_back(checkProgram("codesign", "codesign", "Install Xcode or its command line tools (xcode-select --install)"));
			if (str(s, base + "signing") == "developer-id")
				rq.push_back(checkIdentity(str(s, base + "identity"), "Developer ID certificate"));
			if (flag(s, base + "notarize"))
				rq.push_back(checkXcodeTool("notarytool", "notarytool"));
			if (str(s, base + "format") == "dmg")
				rq.push_back(checkProgram("hdiutil", "hdiutil", "hdiutil is part of macOS"));
		}
	} else if (id == "web") {
		st.notes.push_back("The site needs a web server (GitHub Pages works); it doesn't run from a local folder opened in a browser");
	} else if (id == "android") {
		rq.push_back(checkJava());
		const fs::path sdk = findAndroidSdkImpl();
		rq.push_back(req("Android SDK", !sdk.empty(), sdk.empty()
			? "Not found. Install Android Studio (or the command line tools) and set ANDROID_HOME" : krt::fromPath(sdk)));
		st.notes.push_back("The first build downloads Gradle and the Android build tools it needs (several hundred MB)");
	} else if (id == "ios") {
		rq.push_back(needMac("iOS apps"));
		if (isMac()) {
			rq.push_back(checkXcodeTool("Xcode", "actool"));
			if (str(s, base + "target") == "device") {
				rq.push_back(checkIdentity(str(s, base + "identity"), "Signing certificate"));
				const std::string prof = str(s, base + "profile");
				std::error_code ec;
				const bool ok = !prof.empty() && fs::exists(project.root / krt::toPath(prof), ec);
				rq.push_back(req("Provisioning profile", ok, ok ? prof : prof.empty() ? "Not set" : prof + " doesn't exist"));
			}
		}
	}
	for (const auto& r : rq) if (!r.ok) st.possible = false;
	return st;
}

} // namespace kr
