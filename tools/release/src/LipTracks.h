//---------------------------------------------------------------------------
// Lip tracks: the .lip beside a voice (KAGEnvCharacterEx.tjs), as kagex-lipsync writes them,
// with a header that names the voice they were made for (its SHA-256). kagex-release warns
// about a track whose voice changed since, which no longer fits it
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>
#include <vector>

#include "Project.h"

namespace kr {

/// What a .lip's header says (the comment lines kagex-lipsync writes at its top)
struct LipHeader {
	bool exists = false;
	bool ours = false;         ///< written by kagex-lipsync (a hand-written track has no header)
	std::string voiceHash;     ///< the voice's SHA-256 when the track was made
	std::string text;          ///< the line it was made from
	std::string language;
	int marks = 0;
};

LipHeader readLipHeader(const std::filesystem::path& lip);

/// The sound a track is beside (the same name with .wav, .ogg, .opus or .flac), or empty
std::filesystem::path voiceOfLip(const std::filesystem::path& lip);

/// The tracks in the game's data (not the framework's) that kagex-lipsync made for a voice
/// that has changed since (or is gone)
std::vector<std::filesystem::path> staleLipTracks(const Project& project);

} // namespace kr
