#include "Engine.h"

#include <appserve/json.h>
#include <chrono>

#include "Archive.h"
#include "Host.h"
#include "Subprocess.h"
#include "krt/app/Progress.h"
#include "krt/app/Text.h"

namespace fs = std::filesystem;
using appserve::Json;

namespace kr {

namespace {

bool checkManifest(const fs::path& dir, const std::string& platform, krt::Progress& progress, std::string& error)
{
	std::string text;
	Json m;
	if (!krt::readFile(dir / "engine.json", text) || !Json::parse(text, m) || !m.isObj()) {
		error = krt::fromPath(dir) + " has no engine.json: not a KAGEX engine package";
		return false;
	}
	if (m["platform"].asStr() != platform) {
		error = krt::fromPath(dir) + " is the engine for " + m["platform"].asStr() + ", not " + platform;
		return false;
	}
	if (m["version"].asStr() != KAGEX_RELEASE_VERSION)
		progress.log("Note: the " + platform + " engine is from KAGEX " + m["version"].asStr() + ", this tool from " + KAGEX_RELEASE_VERSION);
	return true;
}

bool unpack(const fs::path& zip, const fs::path& dest, std::string& error)
{
	std::error_code ec;
	const fs::path tmp = dest.parent_path() / (dest.filename().string() + ".part");
	fs::remove_all(tmp, ec);
	fs::create_directories(tmp, ec);
	ZipReader z;
	if (!z.open(zip, error) || !z.extractAll(tmp, error)) {
		fs::remove_all(tmp, ec);
		return false;
	}
	fs::remove_all(dest, ec);
	fs::rename(tmp, dest, ec);
	if (ec) { error = "Can't move the engine into " + krt::fromPath(dest) + ": " + ec.message(); return false; }
	return true;
}

} // namespace

fs::path localEngines(const fs::path& localDir)
{
	if (!localDir.empty()) return localDir;
	const std::string env = getEnv("KAGEX_RELEASE_ENGINES");
	if (!env.empty()) return krt::toPath(env);
	std::error_code ec;
	const fs::path beside = krt::selfPath().parent_path() / "engines";
	if (fs::is_directory(beside, ec)) return beside;
	return {};
}

std::string engineAssetName(const std::string& platform, bool debug)
{
	return "kagex_engine_" + platform + (debug ? "_debug" : "") + ".zip";
}

bool hasDebugEngine(const std::string& platform)
{
	return platform == "windows" || platform == "linux";
}

bool download(const std::string& url, const fs::path& file, krt::Progress& progress, std::string& error)
{
	std::error_code ec;
	fs::create_directories(file.parent_path(), ec);
	const fs::path part = krt::toPath(krt::fromPath(file) + ".part");
	fs::remove(part, ec);
	RunOptions opt;
	opt.timeoutSeconds = 3600;
	opt.canceled = [&progress]() { return progress.canceled(); };
	RunResult r;
	if (!findProgram("curl").empty()) {
		r = run("curl", { "-fL", "--retry", "3", "--connect-timeout", "30", "-sS", "-o", krt::fromPath(part), url }, opt);
	} else {
#ifdef _WIN32
		r = run("powershell", { "-NoProfile", "-NonInteractive", "-Command",
			"$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -UseBasicParsing -Uri '" + url + "' -OutFile '" + krt::fromPath(part) + "'" }, opt);
#else
		error = "Downloading needs curl";
		return false;
#endif
	}
	if (!r.ok()) {
		fs::remove(part, ec);
		error = "Download failed: " + url + (r.output.empty() ? std::string() : "\n" + krt::trim(r.output));
		return false;
	}
	fs::rename(part, file, ec);
	if (ec) { error = "Can't save " + krt::fromPath(file) + ": " + ec.message(); return false; }
	return true;
}

bool ensureEngine(const std::string& platform, bool debug, const fs::path& localDir, krt::Progress& progress,
                  fs::path& dir, std::string& error)
{
	std::error_code ec;
	if (debug && !hasDebugEngine(platform)) debug = false;
	const std::string asset = engineAssetName(platform, debug);
	const std::string stem = asset.substr(0, asset.size() - 4);
	const fs::path cached = cacheDir() / "engines" / KAGEX_RELEASE_VERSION / stem;

	// a folder of engine packages given by the developer (or CI), or beside this tool
	const fs::path local = localEngines(localDir);
	if (!local.empty()) {
		if (fs::is_regular_file(local / stem / "engine.json", ec)) {
			dir = local / stem;
			return checkManifest(dir, platform, progress, error);
		}
		if (fs::is_regular_file(local / asset, ec)) {
			// unpacked into the cache, again whenever the zip is newer
			const fs::path dest = cacheDir() / "engines" / "local" / stem;
			const auto zipTime = fs::last_write_time(local / asset, ec);
			const bool fresh = fs::is_regular_file(dest / "engine.json", ec) && fs::last_write_time(dest / "engine.json", ec) >= zipTime;
			if (!fresh) {
				progress.progress(-1, "Unpacking " + asset);
				if (!unpack(local / asset, dest, error)) return false;
			}
			dir = dest;
			return checkManifest(dir, platform, progress, error);
		}
	}

	if (fs::is_regular_file(cached / "engine.json", ec)) {
		dir = cached;
		return checkManifest(dir, platform, progress, error);
	}

	std::string base = getEnv("KAGEX_RELEASE_ENGINE_URL");
	if (base.empty()) base = std::string("https://github.com/krkren/kagex/releases/download/") + KAGEX_RELEASE_VERSION;
	if (base.back() != '/') base += '/';
	progress.progress(-1, "Downloading " + asset);
	progress.log("Downloading " + base + asset);
	const fs::path zip = cacheDir() / "downloads" / asset;
	if (!download(base + asset, zip, progress, error)) return false;
	progress.progress(-1, "Unpacking " + asset);
	if (!unpack(zip, cached, error)) return false;
	fs::remove(zip, ec);
	dir = cached;
	return checkManifest(dir, platform, progress, error);
}

} // namespace kr
