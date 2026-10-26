//---------------------------------------------------------------------------
// Encrypted data.xp3 (the xp3crypt plugin decrypts it at run time). The encryption is
// xp3crypt's own library (../../xp3crypt/lib, built in when CMake finds it: KR_HAVE_XP3CRYPT).
//
// The key is the archive key of the game's keys file (Keys.h): 32 bytes. kagex-release packs the
// staged data into an encrypted data.xp3 and writes the key into each platform's engine (the
// engine must have the xp3crypt plugin, which holds the key slot).
//---------------------------------------------------------------------------
#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "Settings.h"

namespace kr {

using ArchiveKey = std::array<uint8_t, 32>;

/// Whether this build of the tool can encrypt (it was built with xp3crypt)
bool canEncryptArchive();

/// Packs the staged folder into an encrypted archive at `output`. hashNames also hashes the file
/// names (the game runs it through the xpcrypt:// medium). files/bytes get the counts
bool packEncrypted(const std::filesystem::path& stageDir, const std::filesystem::path& output, const ArchiveKey& key,
                   bool hashNames, int& files, uint64_t& bytes, std::string& error);

/// The files under root (a platform's folder, app or project) that hold the xp3crypt key slot:
/// the engine with the plugin built in (or a plugin shipped beside it). Data folders aren't searched
std::vector<std::filesystem::path> archiveKeySlots(const std::filesystem::path& root, std::string& error);

/// Writes the key into a binary's key slot (in place: the platform's copy)
bool writeArchiveKey(const std::filesystem::path& file, const ArchiveKey& key, std::string& error);

/// Clears a key from memory
void wipeArchiveKey(ArchiveKey& key);

} // namespace kr
