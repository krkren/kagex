//---------------------------------------------------------------------------
// The game project: the folder that holds data/ (and, in a KAGEX package, template/ and the
// engine), and what can be read from it for the default settings
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>
#include <vector>

namespace kr {

struct Project {
	std::filesystem::path root;        ///< the folder with data/
	std::filesystem::path data;        ///< root/data
	/// the framework the game runs on: data/system when the game has its own copy, otherwise
	/// template/system (data/startup.tjs falls back to ../template/system)
	std::filesystem::path framework;
	bool frameworkInData = false;

	// from data/main/first.ks (sf.software_*), when the game sets them
	std::string title, version, maker, year;
	// from krkrz.cf next to the engine
	std::string orgName, appName;
	/// a 1024x1024 icon, when the project has one (platform/icon-1024.png)
	std::filesystem::path icon;
	/// a link-preview image for the web build (platform/web/preview.jpg or .png), when it has one
	std::filesystem::path preview;
	/// the engine next to data/ (krkrz.exe or krkrz), when there is one
	std::filesystem::path engine;
	/// the list of scripts to compile (data/.../!scnlist.txt, doc/scn.txt), when the game has one
	std::filesystem::path sceneList;
	/// whether the framework compiles scripts (it has SceneParser.tjs: KAGEX 0.9.0 and later)
	bool frameworkCompiles = false;
};

/// Looks for the project at dir, then in its parents (up to 3 levels): a folder with
/// data/startup.tjs. false when none is found (error says where it looked)
bool findProject(const std::filesystem::path& dir, Project& out, std::string& error);

/// Lower case letters, digits and single '-' (for file and folder names)
std::string slug(const std::string& s);

/// Where the game keeps its own plugins for a desktop platform: plugins/<platform>/ next to
/// data/ ("windows", "linux", "macos"; Steam takes Linux's). Plugins built for the game, such as
/// krkrlive2d with its own Cubism SDK (tools/live2d), which the engine packages can't carry
std::filesystem::path gamePluginFolder(const Project& project, const std::string& platform);

/// Whether a file name is a plugin library for a desktop platform: a .dll (Windows), lib*.so
/// (Linux, Steam), a .dylib (macOS); on the web, whose engine links its plugins in, Live2D's Web
/// Core (live2dcubismcore.min.js), which a Live2D game's page loads; false for Android and iOS
bool isPluginFor(const std::string& platform, const std::string& name);

/// The game's own plugins for a platform (gamePluginFolder's libraries for it), by name; a build
/// copies them in after the engine's, so one of a name the engine has replaces it
std::vector<std::filesystem::path> gamePlugins(const Project& project, const std::string& platform);

/// The Android ABIs a game's own plugins may be built for (plugins/android/<abi>/)
bool isAndroidAbi(const std::string& name);

/// The libraries the Android engine package has itself (libkrkrz.so, libSDL3.so ...): a game's own
/// plugin of one of those names would replace the engine's
bool isAndroidEngineLibrary(const std::string& name);

/// The game's own Android plugins (since 0.27.0): plugins/android/<abi>/lib*.so, by ABI and name.
/// The Android engine opens a plugin it hasn't linked in as lib<name>.so from the app's
/// libraries, so a build puts them in the Gradle project's jniLibs/<abi>/ beside the engine's
std::vector<std::pair<std::string, std::filesystem::path>> gameAndroidPlugins(const Project& project);

} // namespace kr
