//---------------------------------------------------------------------------
// Measuring the game's sounds' loudness (since 0.27.0): EBU R128's integrated loudness (ITU-R
// BS.1770-4: K-weighting, 400 ms blocks a 100 ms step apart, the absolute gate at -70 LUFS and
// the relative one 10 LU under), as the engine plays a file (an Opus file's header gain applied).
// The build reports every sound's (loudness.measure) and, given targets for its kinds
// (loudness.targets), adds a line to the staged loudness.csv for each file further than
// loudness.tolerance from its kind's target, which the framework applies as the file is decoded
// (template/system/Loudness.tjs). WAV files get no gain from the framework (the engine applies the
// gain only to Ogg Vorbis and Opus), which the report says.
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <functional>
#include <map>
#include <string>
#include <vector>

namespace kr {

/// The integrated loudness of interleaved samples, in LUFS; -1000 for silence (or nothing above
/// the gates). Shorter than one 400 ms block, the whole is measured as one block.
double integratedLoudness(const float* interleaved, size_t frames, int channels, int rate);

/// A sound file's integrated loudness as the engine plays it: false with error when it can't be
/// decoded (FLAC through dr_flac; Ogg Vorbis, Opus and WAV through krt::audio)
bool measureLoudness(const std::filesystem::path& file, double& lufs, std::string& error);

/// The kind loudness.csv gives a sound by the folder it's in (voice, bgm, se), or "": the
/// framework's KAGLoudnessTable.kindOf
std::string loudnessKind(const std::string& relativePath);

/// Whether a file is a sound the measurement looks at (.ogg, .opus, .wav, .flac)
bool isMeasuredSound(const std::filesystem::path& file);

/// loudness.csv's lines (key in lower case -> dB), as the framework reads them
std::map<std::string, double> readLoudnessTable(const std::string& text);

/// A sound as the report has it
struct LoudnessEntry {
	std::string path;          ///< relative to the folder measured, with /
	std::string name;          ///< the file's name, as loudness.csv names a file
	std::string kind;          ///< voice, bgm, se or ""
	bool measured = false;
	std::string error;         ///< why it wasn't measured
	double lufs = -1000;       ///< its integrated loudness (-1000: silence)
	double gainNow = 0;        ///< the gain loudness.csv gives it now (its own line or its kind's)
	bool ownLine = false;      ///< loudness.csv has a line for this file
	bool gainApplies = true;   ///< false for WAV: the engine applies no gain to it
	bool hasTarget = false;    ///< its kind has a target (loudness.targets)
	double target = 0;
	bool far = false;          ///< further than the tolerance from its kind's target, as it plays
	double newGain = 0;        ///< the gain that brings it to the target
};

/// Measures every sound under root (in parallel; each file's loudness cached by content in
/// cache when it isn't empty), with the gains table gives it and, for the kinds targets has, how
/// far each plays from its target
std::vector<LoudnessEntry> loudnessReport(const std::filesystem::path& root, const std::map<std::string, double>& table,
                                          const std::map<std::string, double>& targets, double tolerance,
                                          const std::filesystem::path& cache, const std::function<bool()>& canceled = {});

/// The game's loudness.csv under data (the first of that name, as the auto path finds it), or ""
std::filesystem::path findLoudnessTable(const std::filesystem::path& data);

/// The report as a tab-separated table (file, kind, LUFS, as played, target, gain, note)
std::string loudnessReportText(const std::vector<LoudnessEntry>& entries);

} // namespace kr
