//---------------------------------------------------------------------------
// The game's keys file: every key a build uses, in one file kept outside the game's folder.
//
// Each kind of protection has a key of its own, so knowing one opens nothing else:
//   archive  32 bytes (64 hexadecimal digits): encrypts data.xp3 (xp3crypt)
//   scenes   32 bytes (64 hexadecimal digits): encrypts the compiled scenarios (scnfile)
//   signing  an RSA private key (PEM): signs the release (sigcheck)
//
// The file is text, so the signing key's PEM block in it can also be given to krkrsign as it is:
//
//   # kagex-release keys: ...
//   archive: 0123...cdef
//   scenes: fedc...3210
//   -----BEGIN RSA PRIVATE KEY-----
//   ...
//   -----END RSA PRIVATE KEY-----
//
// release.json names it in keys.file (relative to the game's folder); the KAGEX_KEYS_FILE
// environment variable (a path) wins, for CI. `kagex-release --cli keygen <file>` writes one, or
// adds the keys an existing one lacks.
//---------------------------------------------------------------------------
#pragma once
#include <array>
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "Settings.h"

namespace kr {

struct GameKeys {
	bool hasArchive = false, hasScenes = false, hasSigning = false;
	std::array<uint8_t, 32> archive{}, scenes{};
	std::string signing;   ///< the PEM block of the RSA private key

	/// Clears the keys from memory
	void wipe();
	~GameKeys() { wipe(); }
};

/// Which keys these settings use (archive.encrypt, scenes.compile + scenes.encrypt,
/// signing.enabled)
struct KeysNeeded {
	bool archive = false, scenes = false, signing = false;
	bool any() const { return archive || scenes || signing; }
};
KeysNeeded keysNeeded(const Json& settings);

/// The keys file these settings use: KAGEX_KEYS_FILE, else keys.file relative to the game's
/// folder; empty when neither is set. from says which ("KAGEX_KEYS_FILE" or "keys.file")
std::filesystem::path keysFile(const Json& settings, const Project& project, std::string* from = nullptr);

/// Reads a keys file (see above). false with a reason when it can't be read or a line is wrong
bool readKeys(const std::filesystem::path& file, GameKeys& keys, std::string& error);
bool parseKeys(const std::string& text, GameKeys& keys, std::string& error);

/// The keys the settings need, from their keys file, each checked: present, and the archive and
/// scenario keys not the same. error names what's wrong
bool loadKeys(const Json& settings, const Project& project, const KeysNeeded& need, GameKeys& keys, std::string& error);

/// Writes a keys file with every key, or adds to an existing one the keys it lacks (keeping the
/// rest as they are). With force, every key is new. added gets the names of the keys written;
/// an existing file with all its keys and no force is an error ("already has every key")
bool makeKeys(const std::filesystem::path& file, int bits, bool force, std::vector<std::string>& added, std::string& error);

} // namespace kr
