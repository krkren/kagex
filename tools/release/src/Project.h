//---------------------------------------------------------------------------
// The game project: the folder that holds data/ (and, in a KAGEX package, template/ and the
// engine), and what can be read from it for the default settings
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>

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
	/// the engine next to data/ (krkrz.exe or krkrz), when there is one
	std::filesystem::path engine;
};

/// Looks for the project at dir, then in its parents (up to 3 levels): a folder with
/// data/startup.tjs. false when none is found (error says where it looked)
bool findProject(const std::filesystem::path& dir, Project& out, std::string& error);

/// Lower case letters, digits and single '-' (for file and folder names)
std::string slug(const std::string& s);

} // namespace kr
