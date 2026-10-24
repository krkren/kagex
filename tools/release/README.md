# kagex-release

Packages a KAGEX game for Windows, Linux, Linux for Steam, macOS, the web, Android and iOS.
It opens a settings window (a local page in a browser app window, like the engine's own
tools), and everything it does can also run from the command line (`--cli`), for CI.

**Work in progress for 0.3.0.** This version edits and checks the settings and shows what a
build would make; building the packages comes in the next steps.

## Using it

A KAGEX package keeps the tool in `tools/`. Start it, and it opens the game in the folder above
(the one with `data/`); `Open…` picks another. The settings are saved to `release.json` next to
`data/`.

```bash
kagex-release                              # the window, for the game here or above the tool
kagex-release path/to/game                 # the window, for that game
kagex-release --cli init  [path]           # write release.json with the defaults (--force replaces it)
kagex-release --cli check [release.json]   # problems in the settings, and what this computer can build
kagex-release --cli plan  [release.json]   # what a build would make
```

`check` and `plan` take `--platform=windows,linux,...` (only those platforms, whatever
release.json enables) and `--json`. Exit codes: 0 fine, 1 problems found, 2 failed.

### release.json

| Section | What it holds |
|---|---|
| `identity` | title, short name (home screens), file name (the executable and its `.cf`), version (`1.2.3`), copyright, organization and app names (the save folder on Linux and macOS; `krkren`/`kagex` is the sample's and is refused), icon (a 1024x1024 PNG) |
| `engine` | `debug`: the debug engine instead of the release one |
| `contents` | `framework` (copy `template/system` in as `data/system` when the game has none), `font` (Noto Sans JP), `licenses`, `exclude` (patterns: `*.psd` anywhere, `bgimage/raw/**`, `work/`), `extraFiles` (beside the executable), `plugins` (`all` or `linked`) |
| `media` | `audio.convert` (`opus`, `vorbis` or `keep`; from WAV and FLAC), `audio.opusKbps` (by folder under `data/`, `*` for the rest), `audio.vorbisQuality` (0-10), `images.opaque` / `images.alpha` (`tlg6`, `tlg5`, `png`, `jpeg` / `jpeg-mask`, `keep`; from PNG, BMP and TLG), `images.jpegQuality`, `references` (`keep` files a script names with their extension, or `rewrite` the scripts) |
| `output` | `folder`, `archive` (`auto`: zip, tar.gz for Linux), `checksums` (SHA256SUMS), `check` (start the build for this computer headless afterwards) |
| `platforms` | for each platform `enabled` and `data` (`xp3` or `folder`; Windows also `bind`, the web `files` or `xp3`), and its own settings: macOS bundle ID, signing (`adhoc` or `developer-id`), notarization, zip or dmg; Android format (`apk`/`aab`), application ID, version code, keystore; iOS target (`device`/`simulator`), bundle ID, build number, certificate, provisioning profile |

Missing members take their defaults, which come from the game: `sf.software_title`,
`sf.software_version` and `sf.software_maker` in its `first.ks`, and `krkrz.cf`. Passwords
(keystores, Apple accounts) are never stored in it.

### What each platform needs

The engine for each platform comes from the KAGEX release of the tool's version and is cached
(`%LOCALAPPDATA%\kagex-release`, `~/Library/Caches/kagex-release`, `~/.cache/kagex-release`, or
`KAGEX_RELEASE_CACHE`). Windows, Linux, Steam and the web build anywhere. macOS and iOS need a Mac
(iOS also Xcode, and for devices your certificate and provisioning profile). Android needs a JDK
17 or newer and the Android SDK. The window shows, for each platform, what this computer has.

## Building it

It uses krkrz_tools' libraries (xp3, audio, images) from krkrz_dev's submodule, unchanged:
`KRKRZ_TOOLS_DIR` defaults to `../krkrz_dev/src/tools/krkrz_tools` next to this repository (or
`$KRKRZ_BASE/krkrz_dev/...`). It needs CMake 3.21, Ninja and vcpkg (`VCPKG_ROOT`).

```bash
cd tools/release
cmake --preset linux                 # windows (Developer Command Prompt), macos (Apple Silicon)
cmake --build --preset linux-rel     # -> build/linux/Release/kagex-release
python3 test/smoke.py build/linux/Release/kagex-release --browser   # --browser needs Playwright
```

`.github/workflows/release-tool.yml` builds it on all three systems and runs the smoke test.

Source: `src/main.cpp` (CLI and the window's API), `Settings` (release.json: defaults,
validation), `Project` (finding the game, reading its defaults), `Host` (what this computer can
build), `Plan` (the game's files and the outputs), `Process` (running other programs);
`web/` is the window.
