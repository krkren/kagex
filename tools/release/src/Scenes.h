//---------------------------------------------------------------------------
// Compiled scenarios (doc/scn.txt): the game's key, encrypting the compiled files and writing
// the key into the engines' scnfile plugin. The encryption is scnfile's own code
// (plugins/scnfile/seal.cpp, built in when CMake finds scnfile: KR_HAVE_SCNFILE)
//
// The key is the scenes key of the game's keys file (Keys.h): 32 bytes.
//---------------------------------------------------------------------------
#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "Settings.h"

namespace kr {

using SceneKey = std::array<uint8_t, 32>;

/// Whether this build of the tool can encrypt (it was built with scnfile)
bool canEncryptScenes();

/// Encrypts a compiled scenario (.scn, a PSB) where it is: removed, then written, as staged
/// files are hard links to the game's own
bool sealScene(const std::filesystem::path& file, const SceneKey& key, std::string& error);

/// The files under root (a platform's folder, app or project) that hold the scnfile plugin's
/// key slot: the plugin, or an engine with it built in. Data (data/, data.xp3, the web build's
/// files) isn't searched
std::vector<std::filesystem::path> sceneKeySlots(const std::filesystem::path& root, std::string& error);

/// Writes the key into a file's key slot (in place: the platform's copy, not the cache's)
bool writeSceneKey(const std::filesystem::path& file, const SceneKey& key, std::string& error);

/// Clears a key from memory
void wipeSceneKey(SceneKey& key);

} // namespace kr
