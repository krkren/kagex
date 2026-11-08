//---------------------------------------------------------------------------
// CG pieces (since 0.27.0): a CG drawn as a whole picture that's another one with a little
// changed (a face, an arm, a blush) is kept as the rectangle that differs. In each CG folder
// (media.images.cgPieces, by default evimage/), the lossless pictures are taken in name order and
// each is compared with the first of its run, the base: a picture of the base's size that differs
// from it in at most half its area is replaced by that rectangle, and a line in the staged
// cgpieces.txt (<name>, <base>, <x>, <y>, tab-separated) tells the framework where it goes
// (template/system/CGVariations.tjs, KAGCGPieceDraw). A picture that differs more starts a run
// of its own.
//
// Left whole: pictures in lang/ (a language's own), pictures whose name another picture of the
// game also has (a language's picture would be drawn over the wrong base) or that cgvariations.txt
// names, masks and the pictures that have them (<name>_m), a layered file's layer pictures
// (<file>_<id> beside <file>.txt), pictures a game's own cgpieces.txt lists, and pictures that
// become JPEG (each would be compressed on its own, and the edges would show).
//---------------------------------------------------------------------------
#pragma once
#include <cstdint>
#include <filesystem>
#include <string>
#include <vector>

#include "Settings.h"

namespace krt {
class Progress;
namespace image {
struct Image;
}
} // namespace krt

namespace kr {

struct PiecesResult {
	int folders = 0;      ///< CG folders looked at
	int pictures = 0;     ///< pictures compared
	int pieces = 0;       ///< stored as the rectangle that differs
	int fromCache = 0;
	uint64_t bytesBefore = 0, bytesAfter = 0;   ///< the pieces' files, whole and as pieces
	std::vector<std::string> notes;
};

/// Makes the pieces in stage (the staged data/), in place of the pictures, and writes
/// cgpieces.txt. false only on errors that stop the build
bool makeCgPieces(const Json& settings, const std::filesystem::path& stage, krt::Progress& progress,
                  PiecesResult& result, std::string& error);

/// The smallest rectangle holding every pixel (BGRA) where a and b differ; both the same size.
/// false when they're the same picture
bool differingRect(const krt::image::Image& a, const krt::image::Image& b, int& x, int& y, int& w, int& h);

/// Whether a framework folder draws such pieces (its CGVariations.tjs reads cgpieces.txt), as
/// KAGEX does from 0.27.0 on
bool frameworkDrawsCgPieces(const std::filesystem::path& framework);

} // namespace kr
