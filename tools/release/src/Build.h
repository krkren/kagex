//---------------------------------------------------------------------------
// Building the packages
//
//   1. the game's files, staged in <output>/.work/data (data/, the framework as system/, without
//      the exclusions)
//   2. data.xp3, once, when a platform uses it
//   3. each platform's folder <output>/<file name>-<version>-<platform>/: the engine, renamed, its
//      .cf (the save folder's names, debugwin=no for players), the data, the licenses, icons
//   4. its package (zip / tar.gz / dmg) and SHA256SUMS
//   5. a test run of this computer's build
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <map>
#include <string>
#include <vector>

#include "Settings.h"

namespace krt {
class Progress;
}

namespace kr {

struct BuildOptions {
	std::vector<std::string> only;        ///< these platforms (empty: the enabled ones)
	std::filesystem::path    engines;     ///< a folder of engine packages (--engines)
	bool                     keepWork = false;
	/// passwords for this build only (never saved): androidStorePassword, androidKeyPassword
	std::map<std::string, std::string> secrets;
};

/// { ok, error, outputs: [{ platform, title, ok, error, folder, package, bytes }], notes: [], check: {...} }
Json build(const Json& settings, const Project& project, const BuildOptions& options, krt::Progress& progress);

/// The .cf next to the executable: the project's krkrz.cf without the names, then the names
std::string engineConfig(const Json& settings, const Project& project);

} // namespace kr
