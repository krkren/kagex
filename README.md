# kagex

An English translation of KAGEX, Wamsoft's extension of the Kirikiri KAG3 visual novel framework (affine layers, layer ordering, automatic actions and the "World" environment system), ported to the SDL3 version of [Kirikiri Z](https://github.com/wamsoft/krkrz_dev) and updated to 1920x1080.

## Branches

- **`main`**: the SDL3 version. It's more modern and in active development, supports multiple platforms (Windows, Linux, macOS, Android, iOS and the web) and modern codecs, but has a less mature ecosystem.
- **`legacy`**: the Windows-only version. It has more resources, but supports Windows only and doesn't support modern codecs. For reference, the best video codec it supports out of the box is WMV3, which came out in 2003.

## Running the sample

In a browser: **[krkren.github.io/kagex](https://krkren.github.io/kagex/)** runs the newest release.

Or download a package from [Releases](https://github.com/krkren/kagex/releases):

- **Windows** (`kagex_sdl3_windows_*.zip`): unzip and run `krkrz.exe`. The engine needs OpenGL ES: a graphics driver that supports it, or ANGLE's `libEGL.dll` and `libGLESv2.dll` next to `krkrz.exe`.
- **Linux** (`kagex_sdl3_linux_*.zip`): unzip and run `./krkrz`. Saves go to `~/.local/share/krkren/kagex/` (set by `krkrz.cf` next to the engine) unless you pass `-datapath=savedata/`. Up to 0.0.4 they went to `~/.local/share/wamsoft/krkrz/`; move them over to keep them.
- **Linux, Steam-ready** (`kagex_sdl3_linux_steam.tar.gz`): the same game built in Valve's Steam Linux Runtime 3.0 (sniper), so it runs on older distributions too and can be shipped on Steam as it is. Extract it and run `krkrz/krkrz`; it comes with a desktop entry (`io.github.krkren.kagex.desktop`) and icon.
- **macOS** (`kagex_sdl3_macos.zip`, Apple silicon): unzip and open `KAGEX.app`. It's signed ad hoc, without an Apple Developer ID, so macOS blocks it the first time: open it from the context menu (Open), or allow it under System Settings > Privacy & Security, or run `xattr -dr com.apple.quarantine KAGEX.app`. Saves go to `~/Library/Application Support/krkren/kagex/`.
- **Android** (`kagex_sdl3_android.apk`, Android 10 or later, arm64 and x86_64): install it on the device, allowing installs from unknown sources, or with `adb install kagex_sdl3_android.apk`. It's a release build signed with a debug key rather than a Play Store key, so a build of the app signed with another key can't update it in place: uninstall it first.
- **iOS Simulator** (`kagex_sdl3_ios_simulator.zip`): a debug build for Xcode's iOS Simulator on a Mac with Apple silicon. Unzip it and run `xcrun simctl install booted krkrz.app` with a Simulator running; it shows up as KAGEX. A build for iPhones and iPads needs an Apple Developer account to sign it, which this project doesn't have.
- **Web** (`kagex_sdl3_web.zip`): the site above. Run `python3 serve.py` in it and open `http://localhost:8100/` to play it locally. It also runs from any static web host, such as GitHub Pages; for 0.2.0's zip, run `.github/platforms/web-static-host.py` on the folder first. On a phone: Android browsers switch to full screen from Config (Screen Mode > Full Screen, then tap once more); iPhone browsers can't, so add the site to the Home Screen (Share > Add to Home Screen) and open it from there, which shows the game without Safari's bars. Android's Add to Home screen opens it full screen too.

On the desktop the game starts full screen the first time; after that it remembers whether you left it in a window (F5 switches). The `_release` and `_debug` zips hold the same game files with a release or a debug build of the engine. The game font (Noto Sans JP) comes with it, so no fonts need installing. The web and iOS builds draw text with the engine's own renderer instead of krkr_richtext, which doesn't build for them yet, so lines aren't kerned there.

The demo menu's Effekseer Effects plays [Effekseer](https://effekseer.github.io/) particle effects (petals, sparkles, fireworks, a magic circle, a shockwave) with the krkreffekseer plugin and OpenGL ES, on Windows, Linux, macOS, Android and the web. The iOS build doesn't have the plugin yet, so the demo says so there. A game plays them on World or KAG layers (`efk` in `doc/world.txt` and `doc/kagex.txt`).

The World Extension: Transition demo ends with the twelve transitions of the extNagano plugin: book, flutter, blurfade, zoomfade, scanline, rgbfade, spin, multiripple, imagewipe, 3duniversal (shards flying from the centre), honeyturn and morphing (a swirl). A game uses them like extrans's, with `[trans method=...]` or the World's `trans=` (`doc/kagex.txt`, "trans (Extension)"); a transition whose plugin is missing runs as a crossfade.

With a controller: the D-pad or left stick moves between buttons, A confirms and advances, B cancels or hides the message window, X shows the message history, Y switches auto mode, R1 skips to the next choice or unread text and holding R2 skips. START opens the config screen, BACK the save screen and L1 the load screen.

## Releasing a game

`tools/kagex-release` packages a game for Windows, Linux, Linux for Steam, macOS, the web, Android and iOS. It's in the Windows and Linux packages (`tools/kagex-release.exe`, `tools/kagex-release`), and each system's tool is also a download of its own (`kagex-release-windows.zip`, `-linux.tar.gz`, `-macos.zip`). Run it next to (or in `tools/` below) the folder with your game's `data/`: it opens a window with the settings, saves them to `release.json`, shows what this computer can build, and builds each platform's package into `release/`. It can convert the game's WAV and FLAC sounds to Opus or Ogg Vorbis and its PNG, BMP and TLG images to TLG6, TLG5, PNG or JPEG on the way (lossy files are never converted again). `kagex-release --cli build` does the same without the window, for CI.

Windows, Linux, Steam and the web build on any of the three systems; macOS and iOS need a Mac (iOS also Xcode, and your certificate and provisioning profile for devices); Android needs a JDK 17 and the Android SDK, no NDK. The engines come from the KAGEX release of the tool's version and are downloaded once. [`tools/release/README.md`](tools/release/README.md) describes every setting and what each package holds.

The macOS tool isn't notarized: after unzipping, run `xattr -d com.apple.quarantine kagex-release` (or allow it under System Settings > Privacy & Security).

## Layout

- `data/`: the sample game. It loads the framework from `../template/system`, or from `data/system` where a package puts a copy there.
- `template/`: the KAGEX framework (`template/system`) and empty folders for a new game, with `template/main/` holding empty versions of the game-side hooks (`Override.tjs`, `AfterInit.tjs`, `Storages.tjs`). To ship a game, copy `template/system` and `template/startup.tjs` into `data/`, and `krkrz.cf` next to the engine with your own `orgname`/`appname`: without it, every game on the stock engine saves to the same `~/.local/share/wamsoft/krkrz/` folder on Linux.
- `linux-config.json`, `web-config.json`, `app-config.json`, `ios-config.json`: the settings for Wamsoft's platform kits ([krkrz_linux](https://github.com/wamsoft/krkrz_linux), [krkrz_web](https://github.com/wamsoft/krkrz_web), [krkrz_android](https://github.com/wamsoft/krkrz_android), [krkrz_ios](https://github.com/wamsoft/krkrz_ios)), which build the Linux (Steam), web, Android and iOS packages from krkrz_dev without changing it. `.github/workflows/platforms.yml` shows the steps, and `platform/` holds the icons and the Android app name.
- `doc/`: the KAGEX reference: `kagex.txt` (new and changed tags), `action.txt` (actions), `world*.txt` (the World extension).
- `TODO.md`: planned features.
- `tools/assets/`: the scripts that make the sample's images and effects (`make_ui.py` for the screens, `upscale.py` for the characters and backgrounds, `make_effects.py` for the Effekseer effects in `data/effect`, written with `efkformat.py`, `make_rules.py` for the transitions' rule images in `data/rule`), with the original art they start from.
- `tools/release/`: kagex-release (above): its source, `scripts/` that make the engine packages it uses from the release builds, and its smoke test. `.github/workflows/release-tool.yml` builds it for all three systems.
- `tools/smoketest.py`: a headless smoke test. With the engine next to `data/`, `python3 tools/smoketest.py` plays through the sample and starts the template, and fails on a script error. GitHub Actions runs it on pull requests with the engine from the newest release. `--target android|ios-sim|web` runs the sample's part in the platform builds: on an emulator, the iOS Simulator or headless Chromium.

The engine isn't part of this repository. It's built from [wamsoft/krkrz_dev](https://github.com/wamsoft/krkrz_dev); `CLAUDE.md` has the build steps and the outputs to copy next to `data/`.

## Not available on the SDL3 build

These KAGEX features depend on Windows plugins the SDL3 engine doesn't include. The scripts load without them; using one either falls back to something simpler or stops with an error:

- The menu bar (`menu.dll`, `windowEx.dll`). The sample puts its player commands on keys (F1-F8), buttons and the controller instead; in KAG's debug mode (on unless the engine gets `-debugwin=no`), Shift+F12 shows the debug window and Shift+F11 switches the debug level.
- Scene playback with `[scenestart]` (`psbfile.dll`).
- The fire and Flash effects (`gfxEffect.dll`, `flashPlayer.dll`). Effekseer effects (`efk`) can take the fire effect's place.
- GDI+ outlined text (`layerExDraw.dll`); krkr_richtext draws outlines and shadows instead.
- Native Windows dialogs (`win32dialog.dll`), used by the stand-picture viewer tool.
- `.emf`/`.wmf` vector images (`layerExDraw.dll`).

## License

KAGEX is licensed under the same terms as Kirikiri 2 and KAG3 (`doc/license.txt`). The release packages include the engine's `license.txt` and the licenses of the libraries it uses in `licenses/`. Noto Sans JP is under the SIL Open Font License 1.1 (`template/system/notosansjp-OFL.txt`), as are the Noto Sans CJK JP subsets in `tools/assets/fonts` (`tools/assets/fonts/OFL.txt`) that the image scripts draw labels with. `tools/assets/upscale.py` downloads the Real-ESRGAN weights (BSD 3-Clause) when it runs; they aren't in this repository.
