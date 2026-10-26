# Changelog

## 0.9.0

### Added

- **Compiled scenarios** (the first stage of [krkren/scnfile](https://github.com/krkren/scnfile)): the scripts listed in `!scnlist.txt` are compiled into `<script>.scn.json` by `SceneParser.tjs`, and the scene player (`KAGEnvPlayer.tjs`, `[scenestart]`) plays those in their place: text, names and voices as a table, tags as steps, and the World's state at every save point. However the game goes to a listed script (a jump, a choice, `kag.process()`, a load), it plays compiled. In debug mode a script is compiled when it has changed; `-scncompile` compiles them from the command line and exits, `-scnplay=no` plays the scripts themselves. `[if]`, `cond=` and `&` entities are decided as the game plays, macros come from `parsermacro.ks`, and the line modes put text together as KAG does (`doc/scn.txt`).
- **The scnfile plugin** ([krkren/scnfile](https://github.com/krkren/scnfile), linked at start where a build has it; Linux so far): compiled scenarios are `.scn` files, M2's binary PSB format, a third the size of the JSON. Without the plugin they're `.scn.json` as before. The 0.9.0 packages don't have the plugin yet.
- A compiled script plays without its `.ks`.
- The sample's demos and demo menu play compiled.
- **Going back in compiled scenes**: a BACK button in the message window goes back to the message before, and each message in the backlog has a mark that goes back to it (after a Yes/No). The World, the game's flags and the backlog are as they were at that message (`doc/scn.txt`, "Going back").
- **Scene replay**: the Replay screen has a tile for every titled scene of the compiled demos, on tabs named in `replaylist.csv` (a label `*` there means all of a script's scenes), with a picture of the scene and its title; each plays on its own and comes back to Replay. A scene is reached by playing its script from the start without showing it (`KAGEnvPlayer.seek`), so what earlier scenes put on KAG's own layers is there (`doc/scn.txt`, "Replays").
- **Dialogue search**: a Search screen in Extras finds the lines read so far that hold a word (or a speaker's name), shows each with its demo and scene, and plays from the one chosen to the end of its scene (`KAGEnvPlayer.searchTexts`; `doc/scn.txt`, "Search").
- `[edit enter=...]` runs an expression when Return is pressed in the field (`doc/kagex.txt`).
- **kagex-release compiles scenarios** (Scenarios > *Compile*, `scenes.compile`, on when the game has a `!scnlist.txt`): it compiles the listed scripts with this computer's engine and ships the compiled files without the scripts. With Scenarios > *Encrypt* (`scenes.encrypt`) the `.scn` files are encrypted (XChaCha20-Poly1305) with the scenes key of the game's keys file (below), and the key is written into each package's scnfile plugin; a platform whose engine has no plugin then fails to build. The same files and key give the same bytes, so a patch holds only the scripts that changed (`doc/scn.txt`, "Releases").
- **Compiled scripts**: kagex-release compiles every `.tjs` in a package to TJS2 bytecode (Contents > *Scripts*, `contents.compileScripts`, on by default), so the packages carry no readable TJS and load their scripts a little faster. The engine on the computer that builds does it (`Scripts.compileStorage`), and each script keeps its name, so the game loads them as before. A script that is one expression, like `envinit.tjs`, is compiled as one, so `Scripts.evalStorage` still returns its value. `@if` is decided when building. Errors in compiled scripts name the script and function but not the line (the engine's debug information crashes it, `UPSTREAM.md`). On Linux and macOS the engine cuts integer constants beyond 32 bits (`0xff000000`) when it compiles; kagex-release puts them right, and keeps as source the few scripts where it can't (a constant made of others, like `0xff << 24`). The build lists every script it keeps as source and why, and the engine's output is `compile-scripts.log`.
- **The keys file**: every key kagex-release uses is in one file, the game's keys file (*Keys*, `keys.file`, or `KAGEX_KEYS_FILE` for CI), with a key of its own for each kind of protection: the archive key, the scenes key and the signing key (an RSA private key, which krkrsign reads out of the file as it is). *Create keys…* in the window or `kagex-release --cli keygen <file>` writes one, or adds the keys an existing file lacks; it never replaces a key without `--force`. The check refuses a keys file inside `data/`, one without a key the settings use, and one whose archive and scenes keys are the same. See `tools/release/README.md`, "The keys file".
- **Signed game files (tamper checking)**: kagex-release can sign a release, and the game checks the signatures before it starts. With signing on, the Windows, Linux, Steam and macOS builds carry RSA-PSS/SHA-256 signatures of the game archive, the engine and its plugins, any extra archives and each patch; `template/system/SignatureCheck.tjs` verifies them at start-up with the `sigcheck` plugin and the public key written into `data.xp3`, and quits with a message naming the file if any is damaged, edited, or signed with a different key. A signed build also refuses the engine's REPL and debug options. The web, Android and iOS builds have no such plugin, so they skip the check and rely on the platform's own integrity. The private key is the signing key of the game's keys file. See `tools/release/README.md`, "Signing".
- kagex-release can split a large game's media into separate signed archives beside `data.xp3` (*Signing > Split large archives*), forced on when a signed build's data would otherwise cross the engine's 2 GB signature-check limit.
- **Encrypted game files**: kagex-release can pack `data.xp3` (and its split parts) with every file encrypted (XChaCha20, keyed per file). The [xp3crypt](https://github.com/krkren/xp3crypt) plugin, built into the engine, decrypts each read through the engine's XP3 extraction filter, so the archive is read transparently; the game's key is written into each platform's engine when it's packaged. Turn it on with `archive.encrypt`; the key is the archive key of the game's keys file. An engine without a key reads a plain archive, so the same build works either way. Keeps the scripts and assets out of plain view; the key ships with the game, so a determined person can still recover it. Encrypting takes a kagex-release built with xp3crypt and engine packages that have the plugin built in (in `engines/`): the 0.9.0 downloads have neither yet.
- **Hidden file names** (Encryption > *Hide names*, `archive.hideNames`): the game ships as one encrypted archive, `data.xpc`, whose file names are a keyed hash of each path, so a generic tool sees neither the files nor their names. The engine reads it through the plugin's own `xpcrypt://` storage medium (the built-in XP3 mount matches plain names), with a tiny plain `startup.tjs` that mounts it; the real names live in an encrypted manifest only the plugin reads. Desktop only so far, and not with signing.
- kagex-release uses engine packages in an `engines/` folder next to the game's `data/` (or next to the tool) before downloading, and its check says whether scenarios will compile to `.scn` or `.scn.json` and marks a platform whose engine can't play `.scn` files.
- `tools/smoketest.py --packaged` runs the sample's steps on a desktop package (kagex-release's build of the sample) with the data it holds.

### Changed

- `-scncompile` keeps the game's window hidden.
- A character drawn from layers blinks and lip-syncs again right after a load (or going back, or a search jump): it used to stand still until the next command on it.
- Extras has four tabs (CG, Replay, Music, Search); the nav buttons moved left to make room.
- EXIT in a scene played from Replay goes back to Replay (it went to the title).
- In compiled scenes the backlog follows the scene player's history: written again after a jump or a load (it used to be wiped), and kept at choices (wiped too), which it shows as "Choice: ..." lines.
- The backlog's voice marks are a line high (42 px), so redrawing a line doesn't cut them off, and the text starts further right (`marginL` 140) to make room for the going-back marks.

### Fixed

- The scene player loads: `KAGEnvPlayer.tjs` had a syntax error from the translation, and needed Wamsoft's psbfile plugin. Its history, read tracking and save code had bugs that couldn't show until now.

## 0.8.0

### Added

- **Characters drawn from layers, with blinking eyes and lip-sync**: a World character listed in `charinit.csv` is put together from layers each time it's shown (Wamsoft's "exstand", `KAGEnvCharacterEx.tjs`, which nothing loaded until now). Its outfits, pose variations ("diffs") and faces are sets of layers named in an `_info.txt`, and each World level can have layers drawn at its own size. A face's eyes blink by themselves, and its mouth moves with the character's voice, measured as it plays with the engine's `WaveSoundBuffer.getSoundLevel`, on every platform. Tags hold, open, close or flip the eyes and mouth (`eyecloseto`, `eyeflip=3`, `lipflip=4`...), `x<face>` changes the face with the eyes closed, and `charanim.csv` defines animations (`doc/world.txt`, "Characters Drawn from Layers").
- The World Extension: Animated Character demo, last in the demo menu, with Pip, a character of the sample's own: two outfits, three arm poses, six faces and babbled voice lines. `tools/assets/make_pip.py` draws its layers at each level's size and makes the voices.

### Changed

- Extras on the title screen unlock once the new demo has been played too.

## 0.7.0

### Added

- **Patches and DLC as zip files**: at start the framework loads `patch.zip`, `patch2.zip` and so on from next to the engine and then from the save folder (the one place the web, Android and iOS builds can add files), after the `patch.xp3` archives. Every folder in a zip is searched, so a patch can hold its files in `data/`'s layout. `KAGMountPatchZip(storage)` mounts another one, such as DLC, at any time. Every build has the minizip plugin; the web, Android and iOS builds gained it.
- **CLIP STUDIO PAINT layers as images**: `clip://name.clip/root/folder/layer.bmp` (or `/id/LayerId.bmp`) on KAG and World layers, through the clipfile plugin, which every build now has (`doc/kagex.txt`, "image (Extension)").
- The KAGEX Extended Layer demo shows the emblem as two layers of a CLIP STUDIO PAINT file, turned separately. `tools/assets/make_clip.py` makes the file from the emblem's art.
- kagex-release writes each build's file list (`<file name>-<version>-files.json`, with SHA-256s) and, given an earlier one (`output.patchFrom`, Output > *Patch from*), `patch.zip` with the files that are new or changed since. A patch alone needs no platform or engines.

### Changed

- kagex-release packs a `.clip` or `.psd` file that a script loads layers from (`clip://name.clip/...`, `psd://name.psd/...`), although the default exclusions (`*.clip`, `*.psd`) match it.

## 0.6.0

### Added

- **SVG vector images**: KAG and World layers show `.svg` images as they do bitmaps (`[image layer=0 storage=emblem.svg]`, `[newlay name=badge file=emblem show]`; a name without an extension finds an SVG when no bitmap has that name). The layerExVector plugin (ThorVG) draws them again at each zoom and angle, so they stay sharp. Every build has the plugin; the Android and iOS builds gained it. SVG text isn't drawn: convert it to outlines.
- The KAGEX Extended Layer demo ends with an SVG emblem beside a PNG of the same picture, both zoomed and turned. `tools/assets/make_vector.py` draws the two from one list of shapes.

### Changed

- An `.emf` or `.wmf` image that doesn't load says it needs GDI+ (layerExDraw, which only the Windows-only engine has) and suggests SVG.

## 0.5.0

### Added

- **Twelve more transitions** from the extNagano plugin, which the framework now links: `3duniversal`, `blurfade`, `scanline`, `zoomfade`, `rgbfade`, `spin`, `flutter`, `book`, `imagewipe`, `honeyturn`, `morphing` and `multiripple`, for KAG's `[trans method=...]` and the World's `trans=` (`doc/kagex.txt`, "trans (Extension)"). All the builds have the plugin.
- The World Extension: Transition demo shows them, with two rule images of its own (`data/rule`, drawn by `tools/assets/make_rules.py`): glass shards for `3duniversal` and a brush stroke for `imagewipe`. Its `morphing` is a swirl registered in `envinit.tjs`, since a tag can't hold the triangle arrays.
- kagex-release keeps rule images (`data/rule`) lossless when it converts images to JPEG: a rule's pixel values are timings.

### Changed

- A transition whose plugin didn't load (extrans's or extNagano's) runs as a crossfade, and the console says so, instead of stopping the game with an error.
- `[trans method=rgbfade]` takes `delayr`, `delayg`, `delayb` and `delaya`: KAG lower-cases attribute names, and the plugin reads `delayR` and the like.

### Fixed

- The transition demo's extrans transitions changed nothing on screen: `[env night]` isn't how the World changes the time of day, so each one went from a picture to the same picture. They use the time tags now (`[night trans=wave]`).

## 0.4.0

### Added

- **Effekseer effects**: the `efk` flip type plays [Effekseer](https://effekseer.github.io/) effects (`.efk`, `.efkefc`, `.efkzip`) on World layers (`[newlay name=fx efk=sparkle show]`) and KAG layers (`[image layer=0 flip=sparkle.efk]`), drawn by the krkreffekseer plugin with OpenGL ES. Options set the size (`efkmag`), canvas, start frame, position, tilt and rotation, zoom, speed, colour, looping, triggers and dynamic inputs; `efkstop` lets an effect wind down, and the `efkdone` trigger goes when every effect has ended (`doc/world.txt`, `doc/kagex.txt`). Effects are kept in save data. Without the plugin or OpenGL ES an effect shows nothing (the console says why). `data/effect` is searched for them.
- The sample's Effects demo (in the demo menu) with five effects of its own: glowing petals, sparkles, fireworks, a magic circle and a shockwave. `tools/assets/make_effects.py` makes them, drawing the textures and writing the effects with `efkformat.py`, a Python reader and writer for Effekseer's runtime format. It replaces the fire effect demo, which needed a plugin the SDL engine doesn't have.
- kagex-release keeps the textures and sounds an effect names in their own format, since the effect can't be rewritten to name converted files.
- The Android and web builds include krkreffekseer, as the desktop builds do. The iOS build doesn't yet (Xcode's project generator fails with it, as with krkr_richtext), so effects show nothing there.

### Changed

- A World layer's redraw (a colour change such as `[env grayscale=true]`) no longer restarts a flip whose type says so (`keepOnRedraw`); effects play on through it.

## 0.3.1

### Added

- Web builds offer Add to Home Screen on phones and tablets, where the game then opens full screen: a bar with an Add button where the browser can install the page (Chrome, Edge, Samsung Internet, Opera on Android) and the steps everywhere else (Share, then Add to Home Screen on every iPhone and iPad browser; the browser menu in Firefox and other Android browsers). Closing it hides it for 30 days. The manifest gained an id, a description, `display_override` and separate maskable icons, and the page a favicon.
- Link previews for web builds in Discord, Slack, X, iMessage and the like: Open Graph and Twitter card tags with the title, a description and a 1200x630 preview image (the sample's is its title screen, drawn by `make_ui.py preview`). kagex-release has *Site address*, *Description* and *Preview image* settings for them.

### Fixed

- Web builds kept showing players the old game after an update. The engine caches every game file in the browser (OPFS) for good, and the page and its scripts could come from the browser's cache too. Each build now has an id (in `kagex-build.json` and the page, whose scripts load with it), and `kagex-web.js` checks it before the game starts: a stale page reloads, a new build empties the engine's file cache, and the game's files are checked with the server.
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
