//---------------------------------------------------------------------------
// The mouth over a voice, from the voice and its line: forced alignment (PocketSphinx) of the
// line's sounds to the voice, a Japanese line's sounds read from its text by OpenJTalk
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace kr {

/// A mark of a lip track (KAGEnvCharacterEx.tjs, .lip): from ms on, the mouth (a, i, u, e, o,
/// n for the lips closed, - for any other sound) and how open it is (0 closed, 1 half, 2 wide)
struct LipMark {
	int ms = 0;
	std::string mouth;
	int open = 0;
};

struct AlignResult {
	std::vector<LipMark> marks;
	std::string language;               ///< "ja" or "en", by the text
	std::string sounds;                 ///< the sounds aligned (ARPAbet), for the record
	std::vector<std::string> warnings;  ///< words left out (not in the dictionary) and the like
	double seconds = 0;                 ///< the voice's length
};

/// The models and the dictionary: KAGEX_LIPSYNC_DATA, or else lipsync/ beside the tool
std::filesystem::path lipsyncDataDir();

/// Whether text is Japanese (has kana or kanji); otherwise it's read as English
bool isJapaneseText(const std::string& text);

class Aligner {
public:
	explicit Aligner(std::filesystem::path dataDir);
	~Aligner();
	Aligner(const Aligner&) = delete;
	Aligner& operator=(const Aligner&) = delete;

	/// Loads the models (once); false with error when they aren't there
	bool open(std::string& error);

	/// The marks for a voice (WAV, Ogg Vorbis, Opus or FLAC) saying text
	bool align(const std::filesystem::path& voice, const std::string& text, AlignResult& out, std::string& error);

private:
	struct Impl;
	std::unique_ptr<Impl> impl_;
};

} // namespace kr
