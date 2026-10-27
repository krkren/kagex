//---------------------------------------------------------------------------
// What a build would make: the game's files after the exclusions, what gets converted, and
// each platform's package
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>
#include <vector>

#include "Settings.h"

namespace kr {

/// One file of the game, as it goes into the packages
struct GameFile {
	std::filesystem::path source;   ///< where it is
	std::string           name;     ///< its path inside data/ ('/' separators)
	uint64_t              size = 0;
};

/// The game's files: data/ (without the exclusions and the output folder) plus, when the game
/// has no data/system, the framework as system/
std::vector<GameFile> collectGameFiles(const Json& settings, const Project& project, int* excluded = nullptr);

/// Glob match on a '/' path: '*' and '?' stay within a folder name, "**" spans folders. A
/// pattern without '/' is matched against the file name only; one ending in '/' names a folder
bool matchExclude(const std::string& pattern, const std::string& path, bool isDir);

/// The top-level folders a desktop build packs into archives of their own beside data.xp3
/// (bgimage.xp3, voice.xp3..., as Wamsoft's games ship): those the framework looks for as
/// <folder>.xp3 (Initialize.tjs), but for the framework, the main scripts and the start-up data,
/// which a signed build reads before it has checked the archives and so stay in data.xp3.
/// Matched by exact (lower-case) name, as the framework asks for them
const std::vector<std::string>& splitFolderNames();

/// The plan as JSON (shown by the screen and by --cli plan)
Json makePlan(const Json& settings, const Project& project);

/// release/<exe>-<version>-<platform>
std::string packageBaseName(const Json& settings, const std::string& platform);

} // namespace kr
