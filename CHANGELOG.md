# Changelog

## Unreleased

### Fixed

- Buttons didn't highlight in games packaged by kagex-release with images converted to TLG or JPEG: the framework looked for a button's hover, pressed and focus images (`<name>_over`, `_on`, `_focus`) as `.png`, `.tlg5`, `.tlg6` or `.bmp` only, and converted images are `.tlg` or `.jpg`. It now tries every image format the engine reads. kagex-release refuses TLG and JPEG for a game whose framework (`data/system`) predates this.
- The sample's CG screen shrank the whole CG instead of using its prepared thumbnail once the thumbnail had been converted.

## 0.3.0

### Added

- **kagex-release**, a tool that packages a game for Windows, Linux, Linux for Steam, macOS, the web, Android and iOS (`tools/release`, shipped as `tools/kagex-release` in the Windows and Linux packages and as a download of its own for each system). It opens a window with the settings, which it keeps in `release.json` next to `data/`, and runs from the command line too (`--cli build`).
  - Identity: title, short name, file name, version, copyright, the save folder's names (`orgname`/`appname`; the sample's and the engine's defaults are refused) and one 1024x1024 icon that each platform gets in its own sizes and formats.
  - Windows: the exe renamed, with the game's icon and version info (when the tool runs on Windows), and the data as `data.xp3`, a folder, or bound into the exe. Linux and Steam: the same as a tar.gz, with a desktop entry. macOS: `<title>.app` with the game's bundle ID and icon, signed ad hoc or with a Developer ID and notarized, as a zip or a dmg. Web: the site with the game's files fetched on demand, or one preloaded `data.xp3`, titled and with the home-screen manifest and icons. Android: an APK or an app bundle with the game's application ID, name and icon, built by Gradle from a prebuilt engine (a JDK and the Android SDK, no NDK), signed with your keystore. iOS: an `.ipa` signed with your certificate and provisioning profile, or an app for the Simulator.
  - Media: WAV and FLAC to Opus (by folder: 128 kbps music, 96 sound effects, 64 voices) or Ogg Vorbis, with `.sli` loop points carried over; PNG, BMP and TLG to TLG6, TLG5, PNG or JPEG (with a lossless mask for transparent images). Lossy files are never converted again; files the scripts name with their extension are kept, or their names rewritten. Conversions are cached.
  - It shows what this computer can build for each platform and why not, writes `SHA256SUMS`, and test-runs this computer's build headless, reporting script errors.
- Engine packages for it in each release (`kagex_engine_<platform>.zip`), made from the release builds.

### Changed

- The framework also looks for `.opus` sounds where a script names one without its extension (BGM, sound effects and voices). The engine played Opus, but only `.wav` and `.ogg` were looked for.

### Fixed

- The Android app was named "krkrz" on Japanese and Chinese phones: krkrz_android names it in those languages too, and only the default name was replaced.

## 0.2.2

### Added

- The web demo can be added to a phone's home screen and then opens without the browser's bars: a web app manifest (full screen, landscape) for Android and the home-screen tags for iPhones, whose browsers can't put a page in full screen. Icons drawn by `tools/assets/make_ui.py icons` into `platform/web`; the page is titled with the game's name.

### Fixed

- In the browser and iOS builds the bottoms of g, j, p, q and y (and the shadow under them) were cut off in the message window: the line layer's padding only grew for krkr_richtext's text. It now also grows for the engine's own text drawing.

## 0.2.1

### Fixed

- The web demo on GitHub Pages didn't start:
  - The engine reads its file list from `gamedata/krkrz_files.json`, which only the kit's `serve.py` answered. The web build now has the file there too, so it runs from any static host.
  - On a first visit, coi-serviceworker sometimes reloaded the page before its service worker was ready, which left the page without the cross-origin isolation the engine's threads need until the next reload. The reload now waits for the worker.
  - The Pages deploy makes both changes to 0.2.0's site, then runs the browser smoke test on the live site. The smoke test in the platform builds serves the site with a plain static server, as Pages does.
- In the browser build every text in the game font came out as arrows. The engine bundles Noto Sans JP there and finds a bundled font only in the style asked for, so the bold choices of the demo menu, the first text drawn, left the font on the engine's icon font. Where the engine has a font of that name, `Initialize.tjs` now loads the game's copy of it, which is found for bold text too.
- In the browser build the CG and Replay thumbnails were empty frames: its Photoshop-style blends (`omPs*`) write alpha 0. `setCGImage` keeps the frame's alpha, as the save slots already did.
- The smoke test checks that the demo menu's choices measure as text and that the first CG and Replay tiles are opaque.

## 0.2.0

### Added

- Packages for more platforms, built with Wamsoft's platform kits from the settings in `linux-config.json`, `web-config.json`, `app-config.json` and `ios-config.json`, and for macOS with krkrz_dev's own build:
  - Linux, Steam-ready: built in Valve's Steam Linux Runtime 3.0 (sniper), so it runs on older distributions too, with a desktop entry and an icon.
  - The web: the sample runs in the browser at [krkren.github.io/kagex](https://krkren.github.io/kagex/), and the site comes as a zip to run locally.
  - Android: an APK for Android 10 and later (arm64 and x86_64), signed with a debug key.
  - iOS: an app for the iOS Simulator. A build for iPhones and iPads needs an Apple Developer account.
  - macOS: `KAGEX.app` for Apple silicon, signed ad hoc.
- `.github/workflows/platforms.yml` builds all of them and smoke-tests each one: `tools/smoketest.py --target` drives the Android emulator, the iOS Simulator and headless Chromium as well as the desktop engine. `.github/workflows/pages.yml` puts each release's web build on GitHub Pages.
- App icons, drawn by `tools/assets/make_ui.py icons` into `platform/`.

### Changed

- `data/startup.tjs` runs `data/system/Initialize.tjs` when there is one, so a package can carry the framework inside `data/` (the browser and phone builds have nothing outside it). In this repository the framework stays in `template/system`.
- The web and iOS builds draw text with the engine's own renderer: krkr_richtext doesn't build for them at engine 2.6.5, so their text isn't kerned.

### Fixed

- Saving a game (framework): a PNG thumbnail is shorter than the room kept for it, and the save data goes after that room. Where the save folder can't be written past the end of a file or isn't a local folder (the browser and phone builds), every save failed with "Could not save to file", starting with the title screen's own. The file is now grown to the right size first, or put together in a temporary file and copied over.
- Return and Space close the About screen (framework) even when its Close button doesn't have the keyboard focus. On Android the button lost the focus as soon as the screen opened, so only a tap closed it.

## 0.1.1

### Fixed

- The message window's top corners: the highlight along its top was drawn over the rounded border, so the inside of both corners came out pale. It now stays inside the border.
- The message window and the choices are see-through again. Their shadow was drawn under the whole panel and showed through it, so they were solid except for a lighter strip inside the top and left edges.
- Replay showed the Character demo's scene as a "?", like a locked one, although it could be played. It has a thumbnail now, and an unlocked scene without one shows a play button.

## 0.1.0

### Changed

- The sample's screens are redrawn at 1920x1080 in the look of the Yes/No dialogs: lavender panels, violet borders and hard shadows, and labels in Noto Sans. That covers the title screen (now with Ai and a KAGEX logo), the logo screen, the message window and its buttons, the choices, the click-wait marks, the config, save and load screens, CG Mode, Replay, Music and the message history. Until now most of these were placeholders or 800x600 art resized 1.8x.
- The character sprites, the two backgrounds and the CG are upscaled from the original art with Real-ESRGAN instead of being resized, so their lines are sharp.
- The speaker's name is shown in a name box on the message window's top edge, without the brackets; the message history still brackets it. Saves from earlier versions load with the old message window layout, until the next scene starts.
- The config screen is laid out in two panels, with Default next to Title and Return. The Extras screens' tabs mark the open screen, and the title's Extra button is faded while it's locked.

### Added

- `[position nameframe=...]` (framework): an image drawn behind the name window's text. The name window takes the image's size; `namealign=0 namevalign=0` centre the name on it. `doc/kagex.txt` now lists the name window's `[position]` attributes.
- `tools/assets/`: the scripts that make the sample's images. `make_ui.py` draws the UI, `upscale.py` rebuilds the sprites and backgrounds from the original art in `tools/assets/src` (Real-ESRGAN in NumPy, no PyTorch).

### Fixed

- Pointing at a save or load slot didn't highlight it: the slot's normal image was drawn over its highlighted one.
- The message history's scroll bar wasn't lined up under its page buttons.

## 0.0.5

### Fixed

- A game made from `template/` stopped at start-up with `Member "menu" does not exist` on the SDL engine.
- Games made from the template now get the in-window Yes/No prompts and About screen too; they used to open a separate OS window for every prompt, and the old About window crashed on Linux.
- Closing a Yes/No prompt without picking an answer (Esc, a right-click on it or outside it) answers No. It used to close the prompt without calling either answer's function.
- A Yes/No prompt during a movie threw "not implemented" on the SDL engine: its separate shaped window needs `setMaskRegion`, which only the Windows-only engine has. On the SDL engine it is drawn in the game window like the others.
- A Yes/No question before the game window exists (an error during start-up) uses the system's message box, since the SDL engine can't open the stock dialog window then.
- `[button group=...]` with a group name never set up the radio group.
- Switching to a bitmap font set the default face to `MS Gothic`, which draws as arrows on Linux once the bitmap font is cleared.
- `[mapselopt buttonwidth=...]` never applied (it was checked as `btnwidth`).
- Stand images from `.psd` files didn't load: the plugin is `psdfile` now, not `psd.dll`. The TLG export in `psdlayer.tjs` passed a misspelled file name.
- Japanese text no longer needs a Japanese font on the player's computer. Noto Sans JP ships in `template/system` (SIL OFL 1.1, `notosansjp-OFL.txt`) and is registered at start-up; before, without Noto Sans CJK installed, Japanese showed as boxes on Linux. Yu Gothic still comes first where it's installed, and saves holding the old default font list get the new one.
- Games made from the template were still laid out for 640x480 in places: the message history's buttons were 20 px tall with arrow glyphs for captions on Linux, and choices without images defaulted to 400x50. The history now has 48 px buttons in the game font, and choices default to 720x90.
- The template's `Config.tjs` had an empty `config_version`, so the version check loaded `UpdateConfig.tjs` at every start-up. When it does carry settings over (with a `Config.~new`), it writes them to `Config.tjs.merged` in the save folder, since the SDL engine has no Pad window to show them in.
- The KAGEX log mode (Debug menu) threw `Pad` not found on the SDL engine, including at start-up when it had been left on. It now logs to the console only.
- The Standing Sprite window (a second OS window) no longer reopens at every start-up on the SDL engine because it was open last time.
- Loading an `.emf`/`.wmf` image without GDI+ says it needs the layerExDraw plugin, instead of `GdiPlus` not found.

### Added

- Controller: Y switches auto mode, R1 skips to the next choice or unread text, holding R2 skips like Ctrl, and the left stick moves like the D-pad. In the sample, START opens the config screen, BACK the save screen and L1 the load screen. `-padbtn11` and `-padbtn12` work.
- In KAG's debug mode, Shift+F12 shows the debug window and Shift+F11 switches the debug level, since the SDL engine has no Debug menu. Debug mode is on unless the engine gets `-debugwin=no` (a line `debugwin=no` in `krkrz.cf`), which a released game should set.

### Changed

- Extras unlock once all five demos have been played to the end. The sample used to force them on at every start-up.
- On Linux, saves go to `~/.local/share/krkren/kagex/` (`krkrz.cf` next to the engine sets `orgname`/`appname`) instead of the `~/.local/share/wamsoft/krkrz/` every game on the stock engine shares. To keep saves from earlier versions, move them from the old folder. Windows still saves to `savedata/`.
- The Yes/No and About code and the four dialog images moved from the sample (`data/main/MyYesNoDialog.tjs`, `Override.tjs`, `data/image`) to `template/system/YesNoDialogLayer.tjs`. The About screen also shows the engine version. `aboutInWindow = false` brings back the old About window.
- `tools/smoketest.py` runs the sample and the template headless and checks the title, the demos, save and load, the system and Extras screens, the prompts and the controller; GitHub Actions runs it on every pull request with the engine from the newest release.

## 0.0.4

### Fixed

- Word wrap: after the first wrap that overflowed the message box, every later wrap became a click-to-continue page break with a blank line, and the next page started with a space. A wrap now breaks the page once and carries on normally.
- Word wrap: a line whose only spaces were inside tags (`Wait![wait time=500]`) could crash it before any other line had wrapped.
- Word wrap: two identical lines in a row, and text after a load onto the same line, lost word wrapping; under `[notextmode]` or a no-display skip it could still raise page breaks.
- Letters that hang below the line (g, j, p, q, y) and their shadow were cut off at the bottom of each message line when krkr_richtext draws the text.
- The window/full-screen choice is remembered between launches (the first launch is still full screen), and a windowed start fits the display instead of opening 1920x1080.
- On Linux, the Config screen's Window/Full screen buttons showed the previous mode until a second click, and showed Window at start-up while the game was full screen: the engine switches asynchronously, and the mode was read back too early.
- The Replay screen unlocks a scene once it has been played, instead of only in debug mode.
- The Config screen's Title button failed to load a missing dialog image.
- Music Mode's first track didn't play on Linux (file name case), and two tracks that don't exist were listed.
- Yes/No prompts are redesigned at 1920x1080 and drawn in the game's font for every message, including the save-data and scenario-changed prompts that used to fall back to a separate window with no usable font. The title prompt is in English.
- The message history's text ran under its page buttons (its right margin was overridden in `Config.tjs`), and it didn't scroll with trackpads or high-resolution wheels.
- The save/load and CG/Replay screens freed their thumbnail layers, and CG thumbnails are shrunk smoothly instead of with nearest-neighbour.
- Remaining 800x600 settings: the default message window, `scPositionX`, the logo screen, the About window.
- Plugin link failures are logged instead of hidden; `[scenestart]` explains that it needs the psbfile plugin.

### Changed

- The template's `Config.tjs` is set up for 1920x1080 (message window, text and history sizes, thumbnails), uses Ogg/WAV BGM and the same face list as the sample.
- `template/main/` has commented starting points for `Override.tjs`, `AfterInit.tjs` and `Storages.tjs`.
- The About screen (F1) shows this sample's name and version, and opens inside the game window instead of a second OS window, which crashed the game on Linux.
- Docs: setup notes, `data/readme.txt` and `doc/` updated for the SDL3 port; the README lists what the SDL3 build doesn't support.

### Removed

- The per-message dialog images (`dialog_*_base`) and the `dialog_yes/no_*` buttons, replaced by `dialog_base`, `dialog_wide_base` and `dialog_button_normal/over` with the text drawn at run time, and nine unused 800x600 images.
- `template/update_auto_copy_vars.bat`.

## 0.0.3

- Windows text uses Yu Gothic instead of MS Gothic, fixing English spacing; saves from earlier versions pick up the new default font.
- The choice menu and history log are drawn with krkr_richtext, like the message window, and word wrap measures words as they are drawn.
- krkr_richtext approximates the edge strength and shadow blur settings.
- Fixed `Member "biMinimize" does not exist` when switching between full screen and a window.

## 0.0.2

- 1920x1080.
- krkr_richtext text rendering.

## 0.0.1

- First SDL3 package (tagged `release`).
