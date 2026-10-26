//---------------------------------------------------------------------------
// Engine packages: the engine for each platform, without a game
//
// kagex_engine_<platform>[_debug].zip, a KAGEX release asset (made by
// tools/release/scripts/engine-package.py):
//   engine.json            { "format": 1, "platform", "version", "debug" }
//   license.txt, licenses/ the engine's licenses
//   windows:     krkrz.exe, SDL3.dll, plugin/*.dll
//   linux/steam: krkrz, libSDL3.so.0, plugin/lib*.so
//   macos:       KAGEX.app (no data, unsigned)
//
// Looked for in a folder given with --engines / KAGEX_RELEASE_ENGINES (zips, or the same
// unpacked into folders of those names), then in the cache, then downloaded from the KAGEX
// release of this tool's version (KAGEX_RELEASE_ENGINE_URL overrides where from).
//---------------------------------------------------------------------------
#pragma once
#include <filesystem>
#include <string>

namespace krt {
class Progress;
}

namespace kr {

/// kagex_engine_windows.zip, kagex_engine_linux_debug.zip, ...
std::string engineAssetName(const std::string& platform, bool debug);
/// Whether a debug engine is published for the platform (Windows and Linux)
bool hasDebugEngine(const std::string& platform);

/// The folder of engine packages to use before the cache: dir when given (--engines), else
/// KAGEX_RELEASE_ENGINES, else engines/ next to the game's data/ when there is one; else empty
std::filesystem::path localEngines(const std::filesystem::path& dir, const std::filesystem::path& projectRoot);

/// The unpacked engine for platform when it's here already (unpacked in localDir, or in the
/// cache), without downloading or unpacking anything; empty otherwise
std::filesystem::path engineIfPresent(const std::string& platform, bool debug, const std::filesystem::path& localDir);

/// Whether an unpacked desktop engine (Windows, Linux, Steam, macOS) has the scnfile plugin,
/// which compiles and plays scenarios as .scn files
bool engineHasScnfile(const std::filesystem::path& engineDir);

/// The unpacked engine for platform. localDir may be empty
bool ensureEngine(const std::string& platform, bool debug, const std::filesystem::path& localDir,
                  krt::Progress& progress, std::filesystem::path& dir, std::string& error);

/// Downloads url to file with curl (or PowerShell on Windows)
bool download(const std::string& url, const std::filesystem::path& file, krt::Progress& progress, std::string& error);

} // namespace kr
