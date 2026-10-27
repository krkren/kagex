//---------------------------------------------------------------------------
// Converting the game's lossless media in the staged data
//
//   sounds:  WAV and FLAC -> Opus (bitrate by the folder under data/) or Ogg Vorbis, or FLAC ->
//            WAV when sounds are kept. <file>.sli (loop points) goes along, rescaled to 48 kHz
//            for Opus.
//   images:  PNG, BMP and TLG -> TLG6, TLG5, PNG or JPEG for opaque images; TLG6, TLG5, PNG, or a
//            JPEG with a lossless mask (<name>_m.png) for transparent ones. Masks of separate
//            main/mask pairs (<name>_m.*) and transition rules (rule/) are only converted to
//            lossless formats.
//   never:   Ogg, Opus, JPEG (lossy already), and files whose names the scripts write with their
//            extension, unless the references are rewritten.
//
// Results are cached by content and settings (cacheDir()/media), so unchanged files are converted
// once. Staged files are hard links to the sources: they are replaced, never written to.
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>
#include <vector>

#include "Settings.h"

namespace krt {
class Progress;
}

namespace kr {

struct MediaResult {
	int images = 0, sounds = 0;      ///< converted
	int fromCache = 0;
	int keptByReference = 0;         ///< named with their extension in a script
	int keptForEffects = 0;          ///< textures and sounds of Effekseer effects (.efk, .efkefc)
	int rewrittenScripts = 0;
	uint64_t bytesBefore = 0, bytesAfter = 0;
	std::vector<std::string> notes;
};

/// Converts the files in stage (the staged data/). false only on errors that stop the build
bool convertMedia(const Json& settings, const std::filesystem::path& stage, krt::Progress& progress,
                  MediaResult& result, std::string& error);

/// Whether a framework folder (data/system or template/system) finds .opus files
bool frameworkPlaysOpus(const std::filesystem::path& framework);

/// Whether a framework folder finds a button's state images (<name>_over etc.) in every image
/// format: up to 0.3.0, MessageLayer.getExistName tried .png, .tlg5, .tlg6 and .bmp only, so
/// converted (.tlg, .jpg) hover, pressed and focus images never showed
bool frameworkFindsConvertedImages(const std::filesystem::path& framework);

/// Whether a framework folder can verify signatures (it has SignatureCheck.tjs): the signing
/// support added in KAGEX 0.9.0. A signed build needs it, or it would ship with no check.
bool frameworkSupportsSigning(const std::filesystem::path& framework);
/// Whether a framework folder runs a game whose file names are hidden in data.xp3 and the folders'
/// archives (KAGEX 0.9.2's hashed-bootstrap.tjs, Initialize.tjs and SignatureCheck.tjs; 0.9.0
/// and 0.9.1 shipped a data.xpc with a loose data/startup.tjs instead)
bool frameworkHidesNamesInXp3(const std::filesystem::path& framework);
/// Whether a framework folder's hashed-bootstrap.tjs runs the game's own startup.tjs, which a
/// build with hidden names keeps in data.xp3 as startup-game.tjs (KAGEX 0.9.4); an older one runs
/// Initialize.tjs in its place
bool frameworkRunsGameStartup(const std::filesystem::path& framework);
/// Whether a framework folder looks for the folders' archives (bgimage.xp3...) beside the
/// data.xp3 it was read from (KAGEX 0.9.2's KAGArchivePath), which a macOS app's Resources
/// needs; an older one looks beside the executable
bool frameworkFindsSplitArchives(const std::filesystem::path& framework);

} // namespace kr
