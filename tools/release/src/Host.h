//---------------------------------------------------------------------------
// What this computer can build: for each platform, the programs and files it needs
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>
#include <vector>

#include "Settings.h"

namespace kr {

struct Requirement {
	std::string name;      ///< "Java 17 or newer"
	bool        ok = false;
	std::string detail;    ///< what was found, or how to get it
};

struct PlatformStatus {
	std::string id;
	bool        possible = true;          ///< every requirement is met
	std::vector<Requirement> requirements;
	std::vector<std::string> notes;       ///< things that work differently on this computer
};

/// "windows" / "macos" / "linux"
const char* hostId();

/// Where downloaded engines and converted media are kept (KAGEX_RELEASE_CACHE overrides it)
std::filesystem::path cacheDir();

/// The status of one platform for these settings (signing identities and keystores come from
/// them). Runs a few programs (java -version, xcrun, security), so it takes a moment
PlatformStatus checkPlatform(const std::string& id, const Json& settings, const Project& project);

} // namespace kr
