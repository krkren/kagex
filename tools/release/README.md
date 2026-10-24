# kagex-release

Packages a KAGEX game for Windows, Linux, Linux for Steam, macOS, the web, Android and iOS.
It opens a settings window (a local page in a browser app window, like the engine's own
tools), and everything it does can also run from the command line (`--cli`), for CI.

**Work in progress for 0.3.0.** This version builds every platform's package and converts the
media.

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
kagex-release --cli build [release.json]   # build the packages
```

`check`, `plan` and `build` take `--platform=windows,linux,...` (only those platforms, whatever
release.json enables) and `--json`; `build` also takes `--engines=DIR` (engine packages to use
instead of downloading them) and `--keep-work` (keep the staged files in `<output>/.work`).
Exit codes: 0 fine, 1 problems found (or a platform failed), 2 failed.

### What a build makes

For each platform, `<output>/<file name>-<version>-<platform>/` and its package next to it:

- **Windows**: `<file name>.exe` (with the game's icon, title, version and copyright when the tool
  runs on Windows), `<file name>.cf`, `SDL3.dll`, `plugin/`, and `data.xp3` (or `data/`, or the
  data bound into the exe); a zip.
- **Linux, Steam**: `<file name>`, `<file name>.cf`, `libSDL3.so.0`, `plugin/`, the data, and for
  Linux a `.desktop` file with a 256x256 icon; a tar.gz, which keeps the executable flag.
- **macOS**: `<title>.app` with the game's name, bundle ID, version and icon (`AppIcon.icns`), the
  data in `Contents/Resources`, signed ad hoc or with your Developer ID (and notarized when
  asked); a zip or a dmg.
- **Web**: the krkrz_web site, with `index.html` titled and given the home-screen manifest and
  icons, and the game either as `gamedata/` (each file fetched when the game needs it; names in
  lower case and listed in `gamedata.krkrz_files.json`; scripts and `system/` prefetched) or as
  one `data.xp3`, preloaded as `krkrz.data`; a zip. The engine's own sample data isn't shipped
  (an empty `krkrz.data` in the files mode). It runs from any web server (GitHub Pages works:
  `coi-serviceworker.js` supplies the headers SharedArrayBuffer needs); `serve.py` serves it
  locally.
  - **Updates reach players.** Each build has an id (a hash of its files), in
    `kagex-build.json` and in the page, whose scripts load with `?v=<id>`. `kagex-web.js` checks
    it before the game starts: a page older than the site reloads, and a new build empties the
    engine's file cache (which otherwise keeps the old files for good); the game's files are
    always checked with the server. Upload the whole folder and players get the new version on
    their next visit.
  - **Add to Home Screen.** On phones and tablets a bar offers it until the player closes it
    (for 30 days) or adds the game: a button where the browser can install the page (Chrome,
    Edge, Samsung Internet, Opera on Android), the steps on iPhone and iPad (every browser
    there: Share, then Add to Home Screen) and in Firefox and other Android browsers (their
    menu). From the home screen the game opens full screen, which iPhone browsers otherwise
    can't do; the manifest, icons and Apple tags cover every browser's own way of adding it.
  - **Link previews.** Open Graph and Twitter card tags: the title, the description, and the
    preview image (1200x630 is best; without one, the icon). Discord, Slack, X and others need
    the site's address for the image: set *Site address*.
- **Android**: an APK, or an app bundle (`.aab`) for Google Play, with the game's application
  ID, version (the version code is 1.2.3 -> 10203 unless set), name (in every language) and icon
  (an adaptive icon with the game's icon in its visible square). `data.xp3` or the `data/` folder
  goes into the app's assets, stored uncompressed so the engine reads it in place. It's built by
  Gradle from the Android engine package (krkrz_android's project with the engine prebuilt), so
  it takes a JDK 17 or newer and the Android SDK, but no NDK; the first build downloads Gradle
  and the Android build tools. Without a keystore it is signed with a debug key, for testing;
  with one, the window asks for its passwords (the CLI reads `KAGEX_ANDROID_STORE_PASSWORD` and
  `KAGEX_ANDROID_KEY_PASSWORD`), which are never saved. Gradle's output goes to
  `android-build.log`.
- **iOS** (on a Mac with Xcode): the engine's app with the game's bundle ID, name, version
  (build number from the version unless set) and icon (an asset catalog compiled by `actool`),
  and `data.xp3` or `data/` in the bundle. For devices it is signed with your certificate
  (Apple Development or Apple Distribution) and provisioning profile, whose entitlements it
  takes, as `<file name>-<version>.ipa`; for the Simulator, signed ad hoc, as a zip of the app.
  Identity `-` signs a device build ad hoc, to check the package.

The `.cf` next to the engine carries the developer's own `krkrz.cf` options plus `orgname` and
`appname` (the save folder on Linux and macOS) and, for the release engine, `debugwin=no`. The
licenses (`license.txt`, `licenses/`) go along. `SHA256SUMS` lists the packages, and the test run
starts this computer's build for a few seconds (headless where it can, through the engine's REPL)
and reports script errors; its log is `<output>/test-run.log`.

### Media

Before packing, lossless media in the staged data are converted (the sources are never touched):

- **Sounds**: WAV and FLAC become Opus (by default 128 kbps in `bgm/`, 96 in `sound/`, 64 in
  `voice/`, 96 elsewhere) or Ogg Vorbis. FLAC is only a source (the engine can't play it): it
  becomes WAV when sounds are kept. A `<file>.sli` (loop points) follows its sound, moved to 48 kHz
  for Opus. The framework finds `.opus` files from KAGEX 0.3.0 on; a game with an older
  `data/system` is told to use Vorbis or update it.
- **Images**: PNG, BMP and TLG become TLG6 (or TLG5, PNG, JPEG) when opaque, TLG6 (or TLG5, PNG,
  or a JPEG plus a lossless `<name>_m.png` mask) when transparent. The mask of a main/mask pair
  (`<name>_m.*`) only goes to lossless formats.
  The framework finds a button's converted hover, pressed and focus images from KAGEX 0.3.1 on;
  a game with an older `data/system` is told to convert images to PNG, keep them, or update it.
  A script of your own that looks for an image by adding an extension to its name
  (`Storages.isExistentStorage(name + ".png")`) won't find a converted one: use the framework's
  `getExistImageName(name)`, which tries every image format.
- **Never converted**: Ogg, Opus and JPEG (lossy already), and files the scripts (`.ks`, `.tjs`,
  `.csv`, `.txt`, `.asd`, `.json`, `.func`) name with their extension, including printf patterns
  like `"ai%s%06d.wav"`, unless *Names with extensions* is set to rewrite them; then the staged
  scripts get the new names (UTF-8, UTF-16 and Shift_JIS scripts alike).

Results are cached by content and settings (in the cache folder below), so a later build only
converts what changed.

### Engine packages

The engines come from the KAGEX release of the tool's version: `kagex_engine_<platform>.zip`
(and `_debug` for Windows and Linux), made from the release packages by
`scripts/engine-package.py`; for Android by `scripts/android-engine.py` from krkrz_android
and the release's APK; for iOS by `scripts/ios-engine.py` from krkrz_ios's unsigned device build
and its Simulator build. `--engines=DIR` or `KAGEX_RELEASE_ENGINES` points at a folder of
them instead (zips, or unpacked into folders of the same names), for working offline;
`KAGEX_RELEASE_ENGINE_URL` changes where they are downloaded from.

### release.json

| Section | What it holds |
|---|---|
| `identity` | title, short name (home screens), file name (the executable and its `.cf`), version (`1.2.3`), copyright, organization and app names (the save folder on Linux and macOS; `krkren`/`kagex` is the sample's and is refused), icon (a 1024x1024 PNG) |
| `engine` | `debug`: the debug engine instead of the release one |
| `contents` | `framework` (copy `template/system` in as `data/system` when the game has none), `font` (Noto Sans JP), `licenses`, `exclude` (patterns: `*.psd` anywhere, `bgimage/raw/**`, `work/`), `extraFiles` (beside the executable), `plugins` (`all` or `linked`) |
| `media` | `audio.convert` (`opus`, `vorbis` or `keep`; from WAV and FLAC), `audio.opusKbps` (by folder under `data/`, `*` for the rest), `audio.vorbisQuality` (0-10), `images.opaque` / `images.alpha` (`tlg6`, `tlg5`, `png`, `jpeg` / `jpeg-mask`, `keep`; from PNG, BMP and TLG), `images.jpegQuality`, `references` (`keep` files a script names with their extension, or `rewrite` the scripts) |
| `output` | `folder`, `archive` (`auto`: zip, tar.gz for Linux), `checksums` (SHA256SUMS), `check` (start the build for this computer headless afterwards) |
| `platforms` | for each platform `enabled` and `data` (`xp3` or `folder`; Windows also `bind`, the web `files` or `xp3`), and its own settings: the web's site address (`url`), `description` and `preview` image; macOS bundle ID, signing (`adhoc` or `developer-id`), notarization, zip or dmg; Android format (`apk`/`aab`), application ID, version code, keystore; iOS target (`device`/`simulator`), bundle ID, build number, certificate, provisioning profile |

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

The smoke test also builds when given engine packages (`--engines DIR`; the CI downloads a
release's `kagex_engine_*.zip`).

Source: `src/main.cpp` (CLI and the window's API), `Settings` (release.json: defaults,
validation), `Project` (finding the game, reading its defaults), `Host` (what this computer can
build), `Plan` (the game's files and the outputs), `Build` (the packages), `Engine` (engine
packages), `Archive` (zip, tar.gz, SHA-256), `Icons` (.ico, .icns, PNG sizes), `Subprocess`
(running other programs); `web/` is the window.
