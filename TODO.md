# To do

Planned features, in three groups. The first two need only script and data work in this repository: the plugins they use are already in krkrz_dev's default build and ship in the Linux package, and krkrz_dev itself isn't changed (`CLAUDE.md`). The third needs changes to the builds as well.

## New plugins from krkrz_dev

- [ ] **Animated characters** (`psdfile`, `getSample`): eye blinks and lip-sync through `KAGEnvCharacterEx.tjs` and `psdlayer.tjs`, which nothing loads yet. Loading layers with `psd://` can also stand in for the missing `layerExSubImage` plugin that `psdlayer.tjs` uses for partial images. Outside Windows `psd://` doesn't load (psdfile writes the BMP it serves with a padded file header, as clipfile does), so read the layers with `PSD.getLayerData`, as `affineLoadClipLayer` does for `clip://`. `psdlayer.tjs` also uses `layerExSave` (exporting layers as TLG, trimming transparent edges, `oozeColor` against colour fringes when shrinking), which only the Windows, Linux and macOS packages have: check which of those calls run in the game rather than while authoring, and add the plugin to the web, Android and iOS builds if any do.
- [ ] **Patch zips from kagex-release**: the framework loads `patch.zip` and the like (`minizip`); the tool should build one of the files that changed since an earlier build.

## Interface, accessibility and languages

- [ ] Screen readers: KAG has no support of its own, so the message window should pass its text to `ElementsDialog.announce`, and the choice menu should expose its choices with `ElementsDialog.setGameA11y` (engine guide: Accessibility).
- [ ] Japanese and English in one build, choosing the language from `System.uiLanguageCandidates`.
- [ ] A hotkey (and a controller button) that switches the language while playing: the current message, the choices and the menus redraw in the other language, and the history keeps what was shown. Needs the item above; the framework has no language support yet.
- [ ] Line breaking with krkr_richtext's `StyledLayout` (`breakStrategy`, ruby, vertical text, per-character timing), in place of this fork's `needsToBeWrapped()` word wrap and its page-break edge cases.
- [ ] Menus built with Elements panels (`ElementsPanel`), which draw into a game layer and work with a controller, in place of the Win32 menu bar on every platform.
- [ ] A screenshot key that saves the screen as a PNG without a hitch: writing a 1920x1080 PNG takes about 90 ms, which shows, and `layerExSave`'s `startSaveLayerImage` writes it in the background (the plugin has to be linked before the game window is made, or the window lacks the method).
- [ ] A controls list: a screen that shows what every key, mouse button and controller button does (F1-F8, Shift+F11/F12 in debug mode, the D-pad and face buttons, R1/R2, START/BACK/L1), opened from Config and the menu above. It should read the bindings themselves (`AfterInit.tjs`'s `processKeys` hook and `padKeyMap`, `initialPadKeyMap` in `MainWindow.tjs`), so a game that changes them gets a correct list, and name the controller's buttons by the pad in use (✕/○ on a PlayStation pad, A/B elsewhere).
- [ ] Positional sound effects on World stages (`WaveSoundBuffer.use3D`, `SoundListener`).

## Needing more than scripts

These change the builds too: native code for every platform, including the web, Android and iOS engines in kagex-release's engine packages (the web build links its plugins into `krkrz.wasm`).

- [ ] **Live2D** (`krkrlive2d`): krkrz_dev has the plugin (`Live2DDevice`, `Live2DModel`, `Live2DPlayer`, `Live2DMatrix`), but builds it only with the Live2D Cubism SDK (the `CUBISM_SDK` environment variable), so the release workflow and `platforms.yml` would need the SDK, which Live2D distributes under its own license rather than as open source. Releasing a game with it can need Live2D's SDK release license, which the documentation should say. Then a World character whose poses and faces are motions and expressions, blinking by itself and lip-syncing to voices through `getSample`.
- [ ] **Archive encryption**: kagex-release encrypts `data.xp3` with the game's key, and a plugin of our own decrypts it as the engine reads, through the engine's XP3 extraction filter (`TVPSetXP3ArchiveExtractionFilter`; the engine at `21d20e9` still calls it for every read). krkrz_dev has neither half: krkrz_tools' xp3 writer only sets the "protect" flag, a notice to extraction tools, and doesn't read or write the Kirikiri 2 Releaser's `xp3enc.dll` encryption either; `sigcheck` checks signatures against tampering. The key has to ship with the game, so this keeps out casual extraction, not a determined one.
