//---------------------------------------------------------------------------
// release.json: how to package the game. Kept as JSON (the screen edits it as is); members
// that are missing take their defaults, so an old or hand-written file still loads.
//
//   {
//     "format": 1,
//     "identity": { title, shortName, exeName, version, copyright, orgName, appName, icon },
//     "engine":   { debug },
//     "contents": { framework, font, licenses, exclude: [...], extraFiles: [...], plugins },
//     "media":    { audio: { convert, opusKbps: { folder: kbps, "*": kbps }, vorbisQuality },
//                   images: { opaque, alpha, jpegQuality }, references },
//     "scenes":   { compile, keyFile },
//     "output":   { folder, archive, checksums, check, patchFrom },
//     "platforms": { windows: { enabled, data, ... }, linux, steam, macos, web, android, ios }
//   }
//
// Paths are relative to the folder release.json is in (the project folder).
//---------------------------------------------------------------------------
#pragma once
#include <appserve/json.h>
#include <filesystem>
#include <string>
#include <vector>

#include "Project.h"

namespace kr {

using appserve::Json;

constexpr int kSettingsFormat = 1;

struct PlatformInfo {
	const char* id;
	const char* title;
};
/// windows, linux, steam, macos, web, android, ios
const std::vector<PlatformInfo>& platforms();

/// The defaults for a project (identity from its first.ks and krkrz.cf)
Json defaultSettings(const Project& project);
/// settings with every missing member filled in from defaults (objects are merged, anything
/// else is taken from settings when present there)
Json withDefaults(const Json& settings, const Json& defaults);

struct Issue {
	std::string level;     ///< "error" (can't build) / "warning"
	std::string field;     ///< "identity.version", "platforms.android.applicationId", ...
	std::string message;
};
/// Checks values that would make a broken package. Platform-specific checks only for enabled
/// platforms
std::vector<Issue> validate(const Json& settings, const Project& project);
bool hasErrors(const std::vector<Issue>& issues);

bool loadSettings(const std::filesystem::path& file, Json& out, std::string& error);
bool saveSettings(const std::filesystem::path& file, const Json& settings, std::string& error);

/// "a.b.c" in settings (null when missing)
const Json& at(const Json& settings, const std::string& dotted);
inline const Json& at(const Json& settings, const char* dotted) { return at(settings, std::string(dotted)); }
std::string str(const Json& settings, const std::string& dotted);
bool flag(const Json& settings, const std::string& dotted);

/// The Android versionCode / iOS build number for a version: major*10000 + minor*100 + patch
long long versionNumber(const std::string& version);

} // namespace kr
