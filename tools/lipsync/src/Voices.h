//---------------------------------------------------------------------------
// A game's voices and their lip tracks: which voice says which line (the game's own scenario
// compiler, run in the engine with -voicelines), and the .lip beside each voice
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>
#include <vector>

#include "Align.h"
#include "LipTracks.h"
#include "Project.h"

namespace krt {
class Progress;
}

namespace kr {

/// A voiced line, as the game's scripts have it
struct VoiceLine {
	std::string voice;       ///< the voice's file name (ai000001.ogg)
	std::string character;   ///< who says it (the World's name for the character)
	std::string script;      ///< the script it's in
	std::string text;        ///< the line as shown
	std::string reading;     ///< the line as read: a ruby's reading in place of what it's over
	std::string language;    ///< the language it's in (a game in more than one gives a line in each)
};

/// A voice of the game and its track
struct Voice {
	std::string name;          ///< the voice's file name
	std::filesystem::path file;   ///< where it is in the game (empty: not found)
	std::vector<VoiceLine> lines;    ///< the lines it's said with (usually one, in each of the game's languages)
	std::filesystem::path lip;    ///< its .lip (there or not)
	LipHeader header;
	/// "none" (no track), "current", "stale" (the voice changed since), "manual" (a track
	/// kagex-lipsync didn't write), "missing" (the scripts name a voice the game hasn't got)
	std::string status;
};

/// The engine to run the game with: the one next to data/, or else the engine package for this
/// computer (as kagex-release finds it: enginesDir, KAGEX_RELEASE_ENGINES, engines/, the cache,
/// or a download)
bool findGameEngine(const Project& project, const std::filesystem::path& enginesDir, krt::Progress& progress,
                    std::filesystem::path& exe, std::string& error);

/// The voiced lines of every script in the game (each .ks under data/), through the game's own
/// compiler (the framework's -voicelines, since 0.11.0); log is the engine's output
bool readVoiceLines(const Project& project, const std::filesystem::path& engine, krt::Progress& progress,
                    std::vector<VoiceLine>& lines, std::vector<std::string>& problems, std::string& log, std::string& error);

/// The game's voices: those its scripts name, every sound in a voice folder (data/voice and any
/// folder named voice under data/), and the sounds named in extra (file names), with the state
/// of their tracks
std::vector<Voice> listVoices(const Project& project, const std::vector<VoiceLine>& lines,
                              const std::vector<std::string>& extra = {});

/// Every sound in the game that has a track beside it, with the state of the track
std::vector<Voice> voicesWithTracks(const Project& project);

/// The voice's track state again (after a track was made or removed)
void refreshVoice(Voice& v);

/// Writes a voice's track beside it, with the header that says what it was made from
bool writeLip(const Voice& voice, const std::string& text, const AlignResult& r, std::string& error);

/// The texts a voice's track can be made from, the line as read in each of the game's languages
/// (the source language first, no text twice): the voice says one of them, the first that fits it
std::vector<std::string> lineTextsFor(const Voice& v);

} // namespace kr
