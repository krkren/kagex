# Changelog

## 0.13.2

### Changed

- **The web demo delivers its data as one archive**: the browser demo's game data ships as `gamedata/data.xp3`, not as loose files: the page makes one request for that instead of a few hundred for the game's parts, the engine's file list lists the archive, and it opens the archive as the web project's own path, `web://./data.xp3>`, which the engine already supports as a project path (desktop engines read their own `data.xp3` the same way). The archive is built and opened by the web kit: `stage_web.py` gains a `delivery: "xp3"` source mode, where a `web-config.json` source goes into that one archive instead of loose files, `pre.js` boots a site packed that way, and `xp3pack.py` learned to stream an archive's index back into the file being packed and orders names the UTF-16 way the engine's archive reader looks them up. The changes ride into the web job as `tools/live2d/web/kit-web-xp3.patch`, applied right after the kit is cloned at its pinned commit; when `KRKRZ_WEB_SHA` moves, rebase the patch onto the newer kit and let the web job run it. The job's smoke test and the Pages check go through the same scenarios as always, packed; the site's `?webbase` and offline-cache paths are unchanged. A game's `web-config.json` sets `delivery: "xp3"` on its sources to ship the same way.

### Fixed

- **kagex-release stamps the Live2D engine's web sidecar**: the release tool's web build stamps the site's script tags with its own build id, but a Live2D engine's (0.13.1+) `live2dcubismcore.min.js` tag was left with the id it carried in the engine package, and the tag sits between `webconfig.js` and `krkrz.js`, which tripped the release tool's own web smoke check (the 0.13.2 release cut ran it against 0.13.1's engine). The sidecar now gets stamped with the rest, and the check tolerates its tag in that position.
- **smoke tests' Chromium starts with `--disable-dev-shm-usage`**: a CI runner's `/dev/shm` is 64 MB, and a web engine's shared memory over that kills the page mid-boot as `Target crashed`, before it logs a line — the 0.13.2 cut's release-tool check died that way on the web-files prefetch race step (the 0.13.1 engine's heap crossed the line, the 0.13.0 one didn't). The launch now points Chromium's shared memory at the regular disk, as CI browser guides always recommend.
- **the web-files race check's storm stays inside the page**: the check slows every OPFS write, and with a released engine (0.13.1's web sidecar fetched its whole file list at once; 0.13.2's kit bounds it at two) every response was held until its slow write finished — the renderer ran the CI runner out of memory and the page died `Target crashed` before the game could start. The check's init script now caps the page's fetches at four, keeping the race honest (concurrent, slow writes under boot reads) at a footprint the runner can take.

## 0.13.1

### Added

- **Live2D characters in web builds**: the browser engine draws World's Live2D characters like the desktop one does. Live2D's licence keeps the Cubism Core's own code out of kagex's packages, so on web the Core is `tools/live2d/web/csm_web.cpp`, a shim over the Web Core that comes in Live2D's Cubism SDK for the browser: `live2dcubismcore.min.js` runs as a script beside the engine (the page loads it before the engine, and `web-static-host.py` puts the tag in), and the engine talks to it as it does to the native Core, with the same `csm*` calls crossing the wasm/JS border (handles as emval ids, model data as byte copies). `tools/live2d/build.py --web` fetches both SDKs' zips from the private Cubism repository, builds krkrlive2d, the framework and the shim into the shared binary (the plugin's web fixes live in `tools/live2d/patches`), and stages the site with the Web Core beside it. The web job builds it and the smoke gate runs `--live2d required`: Hiyori's Animated Character demo plays in the browser, her picture, motions, faces, blinking and lip-sync, on the real plugin. A game's web engine gets the plugin the same way, with `--kit` readying its config, and as everywhere the Core itself is the game's to carry: `live2dcubismcore.min.js` beside the engine, from the game's own licensed copy of the SDK.

## 0.13.0

### Added

- **Live2D characters**: a World character can be a Live2D Cubism model: an envinit.tjs entry with `live2d` and a `.l2d` file (the folder Cubism Editor exports, zipped), which the krkrlive2d plugin draws into the character's layer through the engine's GLCompositor every frame, at the size of its World level. Its poses are motions that go on (one of a model3.json group after another), its motions play once and go back to the pose (`motionwait` waits for one), its faces are the model's expressions or values for its parameters, fading into each other and held whatever its motions do with them (the motions move its head, body and hair), and it blinks and lip-syncs to its voice as Pip does, a lip track's vowels shaping its mouth; the eye and mouth commands work on it too. Its pose and face are saved, and a model is let go when its character leaves the screen (`KAGEnvCharacterLive2D.tjs`, `GFX_Live2D.tjs`; `doc/world.txt`, "Live2D Characters"). The plugin needs Live2D's Cubism SDK, whose licence keeps its Core out of kagex's own engines, so a game builds the plugin: `tools/live2d/build.py --sdk <the SDK's zip>` fetches it at pinned commits, applies kagex's fixes (`tools/live2d/patches`; `UPSTREAM.md`), builds its driver on Linux, macOS, Android and iOS too (`tools/live2d/driver`) and puts it in `plugin/` (`--steamrt` builds the Linux one in the Steam Runtime, so it loads on every Linux the engines run on; `--kit` readies krkrz_android's or krkrz_ios's config to build it into the engine). Cubism 5's shaders for its newer blend modes compile when a model first uses them, not all 474 before the first frame (a stall of up to 39 s on a Mac). On Android and iOS a game makes its own engine package from such a build, which `android-engine.py` and `ios-engine.py` make only with `--with-cubism-core` (they and `engine-package.py` refuse the Core otherwise, so kagex's own engine packages never carry it), and puts it in `engines/` next to `data/` for kagex-release. `tools/live2d/LIVE2D-NOTICE.txt` holds the terms for a game's players that Live2D's licence asks for. CI builds and tests Live2D on Windows, Linux, macOS, Android and iOS, and goes through what a game does: the desktop sample built with kagex-release with the plugin in `plugins/<platform>/`, and a game's own Android and iOS engine package with the sample built from it (the iOS app gets the smoke test, the Android APK is started and checked by its log). Started with a release's tag, it adds the sample with Live2D to that release as packages of their own (`kagex_sample_live2d_<platform>`), apart from the engine and template packages. Without the plugin, a Live2D character draws nothing and the log says why. The smoke test checks Live2D characters with the plugin (`--live2d required`) or, without it, with a stand-in that does what the plugin's driver does with a model's parameters (`tools/live2d-standin.tjs`).
- **Hiyori** in the Animated Character demo: Live2D Inc.'s sample model (Neuro-sama's first), who joins in after Pip in the middle of the screen with a face for each of her moods, her idle motions, a motion played once and a motion picked by group and number or by file name, a pose of one motion of its own, blinking, a wink and a voiced line. She isn't in the repository, since Live2D's licence for its sample models lets no one but Live2D hand out their files: `tools/assets/make_hiyori.py model --accept-license` fetches her from Live2D's GitHub, and her line, `data/voice/hiyori000001.ogg`, is eSpeak NG's (a formant synthesizer, no voice learned from recordings: `make_hiyori.py speech`), with a lip track from kagex-lipsync. A build without the plugin or her model says so in her place.
- **kagex-release: a game's own plugins**: libraries in `plugins/windows/`, `plugins/linux/` (Steam too) or `plugins/macos/` next to `data/` go into that platform's packages beside the engine's plugins (`plugin/`, or `Contents/MacOS` in the app), all of them whatever `contents.plugins` says, signed with the engine in a signed build and listed in the plan; one with an engine plugin's name replaces it. `check` warns about files there that aren't plugins for the platform, and about `plugins/web`, `plugins/android` or `plugins/ios` when that platform is enabled, since those engines have their plugins linked in. A game builds the Live2D plugin into its folder with `tools/live2d/setup.py` (a guide through Live2D's licences, what the computer needs, the SDK, the build and a check) or `build.py --out plugins/<platform>` (`tools/release/README.md`, "Your own plugins"), and `check` warns about a game with Live2D models whose enabled desktop platforms lack the plugin.

### Fixed

- A Live2D face whose mouth parameter was open kept it open after the voice stopped: a face's mouth value is where the mouth rests between the words, so the sample's smiling face, which talked while she was silent, shuts now (`smile` in the sample's `envinit.tjs` and in `doc/world.txt` gives no `ParamMouthOpenY`). A face that asks for an open mouth, `surprised`, still keeps it open: it is the face that says so.
- The Animated Character demo's text: its lines are short enough for one message window now, so they don't run over into the next page.

### Changed

- Blinking and lip-sync are a class of their own, `KAGEnvCharacterEyeLip.tjs`, which characters drawn from layers and Live2D characters share; world.tjs loads it before either, so Override.tjs changes its settings (`eyeFlipTime`, `lipFlipTime` ...) as before.

## 0.12.1

### Added

- **A line's characters drawn together**: where krkr_richtext draws the message window, each line's characters are laid out and drawn together by its `StyledLayout`, as its line breaker lays them out, instead of one at a time: the line so far is drawn again each time the text stops (after every character at the usual speed, once a line when the text comes all at once, which is as fast as before). So kerning and ligatures run across the line, accents and emoji made of several characters are shaped as one (a combining accent was drawn beside its letter, and a character outside the BMP, an emoji, as two boxes), and the characters sit at fractions of a pixel. KAG still places and times every character, so the text speed, waits, links and the word wrap are as they were; a character with ruby keeps KAG's ruby (`rubySize`, `rubyOffset`), since StyledLayout's can't be sized or moved (`UPSTREAM.md`). Config.tjs's `useStyledLayout` turns it off (`doc/kagex.txt`, "Line breaking").
- **Japanese and Chinese line breaking by krkr_richtext**: Japanese and Chinese lines break where its line breaker plans, filling each line, with the Unicode rules and the languages' own: closing brackets, full stops, commas and small kana don't start a line, and a word in Latin letters (a name, README) isn't split, as KAG's character wrap split it. Nothing hangs into the margin KAG kept at the end of a line for that (`marginRCh`), so a line can end a character earlier. Vertical text, and the builds without krkr_richtext (the browser, iOS), keep KAG's own wrap (`UPSTREAM.md`).

### Fixed

- In a Japanese or Chinese game whose scripts KAG plays (not compiled), a line with a space in it got the English word wrap, which could break it at the space.

## 0.12.0

### Added

- **A menu bar, in a window**: the game's menu (System, Display, the message commands, Help, and Debug in debug mode) shows as a menu bar in a strip above the game, as Kirikiri's Win32 menu bar did and in place of the one the SDL engine doesn't have: the window is the strip taller than the game, which is drawn under it, and full screen has no bar. A click on a title drops its menu down over the game, moving to another title opens that one, resting on a submenu opens it, and F10 (and the controller's START, in a game that leaves it to the framework, and R3) opens the first menu from the keyboard, where the arrows, Return and Esc work as on Windows. It's drawn with the engine's Elements UI in the dialogs' look, shows the items as they are (enabled, checked, the radio groups' choice, the shortcuts), works with a screen reader, and shows a game's own menu (`KAGWindow_createMenus` in `Override.tjs`) as it is, its captions in the language shown (`MenuBar.tjs`; `doc/kagex.txt`, "The menu bar"). Engines without the Elements UI or `Window.setViewport` don't show it.
- **A controls list** (Help > Controls, and a Controls button on the sample's Config screen): what every key, mouse button and controller button does, read from the bindings themselves, with the controller's buttons named for the pad in use (✕ ○ □ △ on a PlayStation pad, A B X Y elsewhere) and the debug keys in debug mode. The window's keys are now a list of bindings that a game adds to with `kag.bindKey` (the sample's F1-F8, in `AfterInit.tjs`), so the list stays right for a game that changes them (`doc/kagex.txt`, "Key bindings" and "The controls list").
- **Screenshots**: F12 (and Print Screen, where the system passes it on) saves the screen as a PNG in the save folder and says so in a corner. Where layerExSave gives the window `startSaveLayerImage` (now linked before the window is made), the PNG is written on another thread, so the game doesn't stop while it's written (`doc/kagex.txt`, "Screenshots").
- **Screen readers**: each message is read out with its speaker's name, and the choices, the Yes/No prompts, About, the menu bar and the controls list are given to the system's screen reader (Narrator, VoiceOver, Orca) to read and press, through the engine's accessibility interface (`Accessibility.tjs`, `KAGA11y`, for a game's own UI too; `doc/kagex.txt`, "Screen readers"). The browser, Android and iOS builds don't have the interface.
- **Positional sound**: `[se storage=... pos=farleft]`, `xpos=`, `level=` or `char=ai` places a sound on a World stage: it's panned to where it is and comes from further away the further back it is, and a looping sound at a character follows it as it moves (the engine's 3D sound; `doc/world.txt`, "SE Object Functions", and envinit.tjs's `se3d`). The Character demo plays a chime at the far left and the far right of the stage and footsteps that follow Ai as she walks (`tools/assets/make_sounds.py`).
- **Line breaking by krkr_richtext**: where krkr_richtext draws the message window, English lines break where its line breaker (minikin's, which its `StyledLayout` uses) puts the breaks for the whole line, evening out ragged lines; Config.tjs's `lineBreakStrategy` chooses `quality`, `balanced` or `greedy` (`doc/kagex.txt`, "Line breaking").

### Fixed

- The word wrap only worked on plain lines of text: a script line that started with a tag or a tab, had `[r]` in it or ran into text from `[emb]` was left to KAG's character wrap, which split words, and a compiled message with a new line in it too. It follows the line as it's drawn now, finds its place again after text the line doesn't have (`[emb]`, text `[if]` leaves out), and doesn't break a line twice at a word that doesn't fit after KAG's own wrap has broken it.

### Changed

- The sample's F1-F8 are key bindings (`kag.bindKey` in `AfterInit.tjs`) instead of a `keyDownHook` function, and its menu captions (`Override.tjs`) have their shortcuts, for the menu bar. The framework's menu has Save Screenshot and Help > Controls.
- The Character demo's music fades out before its positional sound part, so the chimes and footsteps are heard on their own, and the Animated Character demo has no music.

## 0.11.0

### Added

- **Characters straight from PSD and CLIP STUDIO PAINT files**: a pose's layers at a level can be the file the artists draw in, `<files>_<level>.psd` or `.clip`, when there's no `<files>_<level>.txt`. Its layers and folders are the layers and groups `_info.txt` names, read through the psdfile and clipfile plugins on the desktop engines (`doc/world.txt`, "The layers in a PSD or CLIP STUDIO PAINT file"). `psdlayer.tjs` reads CLIP files too (`PSDInfo.loadCLIP`), gives PSD layers without an ID one (`assignAutoIds`) and leaves out empty layers.
- **kagex-release splits PSD and CLIP files into layer pictures**: every `.psd` and `.clip` a build takes in (all the game has, by 0.9.3's defaults) is replaced by its layer structure (`<name>.txt`, psdlayer.tjs's format) and a TLG picture per layer (`<name>_<layer id>`), read with the libraries the plugins are made of, so a release needs neither the files nor the plugins and plays them on the web, Android and iOS too. A file whose layers the game has already, as a layer structure of its name (`<name>.txt`, what psdlayer.tjs's `saveImages` exports), stays out, and one that can't be read goes in as it is, each with a note. With a pattern of yours that leaves them out, a pose `charinit.csv` names goes in (split) all the same, like a file a script names after `psd://` or `clip://`. Splits are cached; a name the split would write that the game already has stops the build. `kagex-release --cli split <file> <folder>` shows what a build makes of one file (`tools/release/README.md`, "Photoshop and CLIP STUDIO PAINT files").
- `psd://name.psd/root/folder/layer.bmp` and `psd://name.psd/id/<LayerId>.bmp` load a Photoshop file's layer into KAG and World layers on every engine with psdfile (the plugin's own BMPs only loaded on Windows), as `clip://` does; both read what kagex-release split the file into where the file or the plugin isn't there.
- **Mouths by vowel**: a mouth group with a layer for each vowel ("Mouth A" ... "Mouth O", or あ ... お) shows the one for the vowel the voice says while it lip-syncs (face groups take `lipa` ... `lipo`). The vowels come from the voice's lip track (below); a voice without one opens and shuts the mouth by its loudness alone, with nothing to prepare (`lipEngineVowels` lets the engine's `WaveSoundBuffer.getVowel` pick vowels instead, but it mostly hears a voice's pitch: `UPSTREAM.md`). Pip's plain face has them.
- **Lip tracks**: a voice can come with `<voice>.lip`, the mouth over time (a vowel, `n` for the lips closed, or `-`, and how open), which then moves the mouth in place of the voice's level, timed from when the voice starts (`lipSyncTracks`; `doc/world.txt`, "Blinking and lip-sync").
- **kagex-lipsync** (`tools/lipsync`, built and shipped with kagex-release): pick the voices whose characters should shape their mouths to the vowels, and it writes each one's lip track from the voice and the line the scripts give it, by forced alignment with existing libraries (PocketSphinx; OpenJTalk reads a Japanese line's sounds, kanji included). Its window lists every voice with its character, its line and its track's state (none, current, out of date, hand-written) and plays a track along with its voice; a line typed in replaces the script's where the voice says something else, and a voice that doesn't fit its line is refused rather than guessed. The lines come from the game's own scenario compiler (the framework's new `-voicelines`), in each of a game's languages: a track is made from the first, the source language's first, that the voice fits, so the sample's Ai, recorded in Japanese, gets hers from the Japanese line. Measured on synthesized lines in four Japanese and four English voices: the right vowel 86% and 87% of the time, against 22% and 39% for the engine's getVowel and a best of 90% with the mouth changing every 120 ms (`tools/lipsync/README.md`). kagex-release's check warns about tracks whose voice has changed since.
- The Animated Character demo's Pip says one line in a synthesized voice (`tools/assets/make_pip.py speech`, Kokoro; English, with the line in Japanese too), whose lip track kagex-lipsync made: the demo's example of mouths by vowel. Its babbled lines move the mouth by loudness.
- `tools/assets/psdwrite.py` writes a layer structure and its pictures as a PSD with folders (standard library only); the smoke tests use it to check that a pose read from a PSD, and one kagex-release split, match the sample's own.

### Fixed

- Lip-sync for a voice with no lip track was out of time now and then: the engine reads a playing voice's level at its own idea of the play position, which runs half a second ahead about a quarter of the time (`UPSTREAM.md`). The mouth now reads the part of the voice the clock says is playing, and keeps readings of the next frames for those moments: measured in the engine on synthesized lines in eight voices, it's open or shut as it should be 72-73% of the time instead of 68-69% (77-81% would be readings without the engine's error, with the mouth changing every `lipFlipTime`). Nothing to prepare: it's the voice file as it is.
- A character drawn from layers kept its eyes and mouth still while its own change (pose, outfit or face: `charTrans`, 300 ms in the sample) faded in, so a line said with a change lost its start. They move during it now.
- `clip://` found a layer inside a folder by its name alone (`root/layer`), not by its folder path, and of two layers of one name took the upper one, unlike the plugin.

### Changed

- kagex-release 0.11.0 downloads the 0.11.0 engines, and the release packages carry kagex-lipsync beside it, with its models and dictionary (`tools/lipsync/`).

## 0.10.0

### Added

- **Languages, switched while playing**: a game lists its languages in `Config.tjs` (`KAGLanguageList`, the language its scenarios are written in first), and the player switches between them at any time with **F9**, the controller's **L2** or a button of the game's: the message on screen (and its speaker's name), the choices on show, the message window's buttons and the screen on show are drawn again in the other language, and the backlog keeps each line in the language it was shown in. The story's other languages are built into the compiled scenarios, as in Wamsoft's multi-language games: each listed script's translation, `data/lang/<code>/scenario/<script>` (the script with its text in that language), is compiled with it, and its texts, display names, choices and scene titles go into the script's `.scn` (`languages`, and per text a list of `[display name, text, length, speech text, search text]`, one a language: compiled format version 3), matched scene by scene and text by text; a scene that doesn't match keeps the script's own text, and the compiler warns. The scene player shows the language shown, the backlog, Search and the save slots' titles included, and a speaker's `nameAlias` in `envinit.tjs` can be a dictionary by language. kagex-release leaves the translations out of the package with the scripts, and converts a language folder's images like the ones they stand in for (files of the same name in different folders get the same new name). Each other language's folder, `data/lang/<code>/`, is on the search path while the game shows it: its interface strings, `lang.json`, and any file that stands in for one of the same name, such as the screens' images with words on them. Scripts KAG plays itself are shown as written. Until the player chooses a language, the game takes the one the system prefers (`System.uiLanguage`, then `System.uiLanguageCandidates`); the choice is saved with the system variables. The framework's own strings (the Yes/No prompts, About, the backlog's "Choice:") are in `system/kagex_ja.json`. `doc/kagex.txt`, "Languages".
- **The sample in Japanese as well as English**: every demo's script translated (`data/lang/ja/scenario/`, the original KAGEX sample's Japanese where it had the line), the speakers' names, the demo menu, scene titles in Replay, Search and the save slots, and the title, Config, save/load and Extras screens and the message window's buttons, drawn in Japanese by `tools/assets/make_ui.py --lang ja` into `data/lang/ja/`. The Config screen has a Language row (English, 日本語); its rows are a little closer together to make room.
- `tools/assets/subset_fonts.py` makes the Japanese subsets of Noto Sans CJK JP that `make_ui.py` draws the Japanese labels with (`tools/assets/fonts/NotoSansCJKjp-*-Japanese.otf`).
- `tools/smoketest.py` switches the title screen, a line of `char.ks`, the demo menu's choices and the Config screen to Japanese and back, and checks that the backlog keeps what was shown. It puts the sample in English first: under a C locale the engine's candidates are Japanese.

### Changed

- **Compiled scenarios are format version 3**: a game's scripts compile again the first time, and a game in more than one language gets its languages in each `.scn`. With one language a compiled file is laid out as before. [scnfile](https://github.com/krkren/scnfile)'s `scn2ks` reads the new layout and writes any of its languages (`--lang=ja`).
- kagex-release 0.10.0 downloads the 0.10.0 engines.

## 0.9.4

### Fixed

- **kagex-release encrypts and hides names on Windows, whatever language the file names are in**: [xp3crypt](https://github.com/krkren/xp3crypt)'s packer took names through Windows' ANSI code page, so a game with a file named in Japanese, built on an English Windows, stopped with "No mapping for the Unicode character exists in the target multi-byte code page". It takes them through UTF-8 now (xp3crypt 08ad5f7).
- **Archives with hidden names match names without regard to case**, as plain archives do: an image stored as `title.PNG` and loaded as `title.png` failed with "Unknown graphic format", because the engine picks an image's decoder by its extension as spelt and the `xpcrypt://` medium handed names back as stored. The 0.9.4 engines have the fixed plugin.
- **A game's own `startup.tjs` runs in a build with hidden names**: kagex-release shipped `system/hashed-bootstrap.tjs` in its place, so anything `startup.tjs` did besides starting `Initialize.tjs` was left out, without a word. It now goes into `data.xp3` as `startup-game.tjs` (its name hashed like the rest), and 0.9.4's `hashed-bootstrap.tjs` runs it once the archives are mounted. Update a game's `data/system/hashed-bootstrap.tjs` from `template/system`; with an older one the check warns that `startup.tjs` won't run.
- **kagex-release's `--engines` (and `KAGEX_RELEASE_ENGINES`) can be relative to the current folder**: with unpacked engine packages, the Windows icon and version step looked for `krkrz.exe` relative to the package's own folder and failed, saying it wasn't a Windows executable.

### Changed

- The release tool's smoke test builds a game with hidden names on Windows as well as Linux (a file named in Japanese, an image with an upper-case extension, and `startup.tjs` run), and a Windows build from an unpacked engine package given by a relative path.
- kagex-release 0.9.4 downloads the 0.9.4 engines.

## 0.9.3

### Added

- **A compiled script starts from the World the scripts that go to it leave**: each compiled file records the World it leaves at every jump and choice to another script, and a script that the listed scripts going to it all leave the same World in is compiled from that World. So a script that carries on from another's screen (a character still standing there, the stage, the music) has it in its saved states, and going back, loading or a thumbnail there shows it. When they leave different ones (the demo menu, which every demo comes back to), the script starts from an empty World as before. `-scncompile=all` compiles again the scripts whose starting World changed, until they all hold. The compiled format is version 2 (`entry`, `exits`; `doc/scn.txt`, "Where a script starts").
- **Going back to the middle of a message window draws the window as it was**: BACK, a backlog mark or a load at a line that carries on a window (layer.ks's lines, which build up in one window) draws that window's earlier lines first, without their voices and without adding them to the backlog again. It used to show the line alone (`doc/scn.txt`, "Going back").
- [krkren/scnfile](https://github.com/krkren/scnfile) tests itself on every push: its PSB codec and encryption on Linux (also with AddressSanitizer and UBSan), macOS and Windows, and the plugin and scn2ks (a compiled scenario back to a script) in the newest kagex release's Linux engine.

### Changed

- **kagex-release no longer leaves out `.psd` and `.clip` files by default**: Contents > *Leave out* is `*.bak`, `*.tmp`, `Thumbs.db`, `desktop.ini` and `.DS_Store`. A `release.json` that has 0.9.2's default list gets the new one; a list you changed stays as it is (and a `.clip` or `.psd` that a script loads layers from still goes in when a pattern of yours matches it).
- kagex-release 0.9.3 downloads the 0.9.3 engines.

## 0.9.2

### Changed

- **The desktop builds are split as Wamsoft's games are**: kagex-release's Windows, Linux, Steam and macOS builds with `xp3` (or `bind`) data ship `data.xp3` (`startup.tjs`, `system/`, `main/`, `init/`, `sysscn/` and the top-level files) and an archive per media folder beside it: `bgimage.xp3`, `bgm.xp3`, `effect.xp3`, `evimage.xp3`, `face.xp3`, `fgimage.xp3`, `image.xp3`, `others.xp3`, `rule.xp3`, `scenario.xp3`, `sound.xp3`, `thum.xp3`, `uipsd.xp3`, `video.xp3`, `voice.xp3` (those the game has), always, with or without encryption and signing. Signing > *Split large archives* is gone. A signed build checks each archive and mounts the media ones once they have. The web, Android and iOS builds keep the whole game in one `data.xp3`.
- **Hidden names are in `data.xp3`**: with Encryption > *Hide names*, the files in `data.xp3` and in the media archives are stored under keyed hashes of their paths, and only `data.xp3`'s `startup.tjs` keeps its name (still encrypted): the engine opens `data.xp3` as usual, runs it, and it mounts the archives through the xp3crypt plugin's `xpcrypt://` medium. No more `data.xpc`, and no `data/` folder: the package is the archives. Signing covers them as it covers any archives.
- Each encrypted archive of a game has its own range of per-file keys ([xp3crypt](https://github.com/krkren/xp3crypt)'s new `saltBase`), so no two files share a keystream.
- The framework finds the media archives beside the `data.xp3` it was read from (`KAGArchivePath`), not beside the executable, so a macOS app's archives go in its `Resources`. kagex-release splits a macOS build only for a framework that does (0.9.2's), and hides names only with 0.9.2's framework (`hashed-bootstrap.tjs`, `Initialize.tjs`, `SignatureCheck.tjs`): update a game's `data/system` from `template/system`.

## 0.9.1

### Fixed

- **kagex-release: signing works with hidden names.** A build can now be signed, encrypted and have its file names hidden at once (0.9.0 refused Signing with *Hide names*). The game checks `data.xpc` and the small plain `data/startup.tjs` that mounts it, each with its own signature (`data.xpc.sig`, `data/startup.tjs.sig`), so replacing either stops it. This needs the 0.9.1 framework (`SignatureCheck.tjs`, `hashed-bootstrap.tjs`): a game with an older `data/system` is told to update it.
- **The sample's web, Android and iOS packages carry its compiled scenarios**, so Search, BACK, the backlog's going-back marks and Replay's scenes work there. Their data is read-only, so the game couldn't compile the scenarios as it went (as the Windows and Linux zips do) and played the demos from the scripts: Search found nothing and Replay had no scenes. CI now compiles them once (`.github/platforms/compile-scenarios.sh`) and every platform job (the Linux folder and macOS too) packs the same files.

### Added

- **Compiled scenarios** (the first stage of [krkren/scnfile](https://github.com/krkren/scnfile)): the scripts listed in `!scnlist.txt` are compiled into `<script>.scn.json` by `SceneParser.tjs`, and the scene player (`KAGEnvPlayer.tjs`, `[scenestart]`) plays those in their place: text, names and voices as a table, tags as steps, and the World's state at every save point. However the game goes to a listed script (a jump, a choice, `kag.process()`, a load), it plays compiled. In debug mode a script is compiled when it has changed; `-scncompile` compiles them from the command line and exits, `-scnplay=no` plays the scripts themselves. `[if]`, `cond=` and `&` entities are decided as the game plays, macros come from `parsermacro.ks`, and the line modes put text together as KAG does (`doc/scn.txt`).
- **The scnfile plugin** ([krkren/scnfile](https://github.com/krkren/scnfile), in every 0.9.0 package and linked at start): compiled scenarios are `.scn` files, M2's binary PSB format, a third the size of the JSON. Without the plugin they're `.scn.json` as before.
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
- **Encrypted game files**: kagex-release can pack `data.xp3` (and its split parts) with every file encrypted (XChaCha20, keyed per file). The [xp3crypt](https://github.com/krkren/xp3crypt) plugin, built into the engine, decrypts each read through the engine's XP3 extraction filter, so the archive is read transparently; the game's key is written into each platform's engine when it's packaged. Turn it on with `archive.encrypt`; the key is the archive key of the game's keys file. An engine without a key reads a plain archive, so the same build works either way. Keeps the scripts and assets out of plain view; the key ships with the game, so a determined person can still recover it. Every 0.9.0 package's engine has the plugin built in, and kagex-release 0.9.0 is built with xp3crypt and scnfile.
- **Hidden file names** (Encryption > *Hide names*, `archive.hideNames`): the game ships as one encrypted archive, `data.xpc`, whose file names are a keyed hash of each path, so a generic tool sees neither the files nor their names. The engine reads it through the plugin's own `xpcrypt://` storage medium (the built-in XP3 mount matches plain names), with a tiny plain `startup.tjs` that mounts it; the real names live in an encrypted manifest only the plugin reads. Desktop only so far, and not with signing.
- kagex-release uses engine packages in an `engines/` folder next to the game's `data/` (or next to the tool) before downloading, and its check says whether scenarios will compile to `.scn` or `.scn.json` and marks a platform whose engine can't play `.scn` files.
- `tools/smoketest.py --packaged` runs the sample's steps on a desktop package (kagex-release's build of the sample) with the data it holds.
- The engines of every package (Windows, Linux, Steam, macOS, the web, Android and iOS) have xp3crypt built in and the scnfile plugin, and `tools/smoketest.py --encryption required` checks them on each platform.

### Changed

- `-scncompile` keeps the game's window hidden.
- A character drawn from layers blinks and lip-syncs again right after a load (or going back, or a search jump): it used to stand still until the next command on it.
- Extras has four tabs (CG, Replay, Music, Search); the nav buttons moved left to make room.
- EXIT in a scene played from Replay goes back to Replay (it went to the title).
- In compiled scenes the backlog follows the scene player's history: written again after a jump or a load (it used to be wiped), and kept at choices (wiped too), which it shows as "Choice: ..." lines.
- The backlog's voice marks are a line high (42 px), so redrawing a line doesn't cut them off, and the text starts further right (`marginL` 140) to make room for the going-back marks.

### Fixed

- Web builds: a file the engine read while the page's background prefetch was still writing it to the browser's cache came back empty, which could stop the game at start (a compiled script then failed with "Syntax error at line 1"). `kagex-web.js` makes the engine wait for that write.
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
