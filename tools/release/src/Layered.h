//---------------------------------------------------------------------------
// Splitting Photoshop (.psd) and CLIP STUDIO PAINT (.clip) files into layer pictures
//
// A game can keep its characters' layers (KAGEnvCharacterEx.tjs, psdlayer.tjs) and the layers
// psd:// and clip:// name (AffineLayer.tjs) in the files the artists edit, which the engine reads
// through the psdfile and clipfile plugins. Only the desktop engines have those, and the files
// are large, so a release has each one split, as the framework reads it from anywhere:
//
//   <name>.txt            psdlayer.tjs's layer structure (tab-separated, the top layer first;
//                         folders as layer type 2), as its loadPSD / loadCLIP would read it
//   <name>_<layer id>.tlg one picture per layer that draws something (TLG6, or the format the
//                         media settings convert pictures to: TLG5, PNG; JPEG comes later)
//
// The layers are read as the plugins read them (the same libraries: psdparse and clipparse):
// names with "/" as "_", the picture with its mask, the plugins' layer types and opacities, and
// PSD layers without an ID numbered as psdfile's assignAutoIds numbers them.
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

struct LayeredResult {
	int files = 0;      ///< .psd and .clip files split
	int pictures = 0;   ///< layer pictures written
	uint64_t bytesBefore = 0, bytesAfter = 0;
	std::vector<std::string> notes;
};

/// Splits every .psd and .clip in stage (the staged data/), each in place of the file. false only
/// on errors that stop the build
bool splitLayeredFiles(const Json& settings, const std::filesystem::path& stage, krt::Progress& progress,
                       LayeredResult& result, std::string& error);

/// One file's layer structure and pictures, written beside it into dir as <stem>.txt and
/// <stem>_<id><ext> (for tests and the CLI). false with error when it can't be read
bool splitLayeredFile(const std::filesystem::path& file, const std::filesystem::path& dir, const Json& settings,
                      std::vector<std::filesystem::path>& written, std::string& error);

/// Whether a framework folder reads layers from such pictures: its AffineLayer.tjs finds psd://
/// and clip:// layers in them (affineLayeredFromPieces) and KAGEnvCharacterEx.tjs looks for a
/// pose's .txt before its .psd or .clip (findStandLayerFile), as KAGEX does from 0.11.0 on
bool frameworkReadsSplitLayers(const std::filesystem::path& framework);

} // namespace kr
