# To do

Planned features, in three groups. The first two need only script and data work in this repository: the plugins they use are already in krkrz_dev's default build and ship in the Linux package, and krkrz_dev itself isn't changed (`CLAUDE.md`). The third needs plugins of our own.

## New plugins from krkrz_dev

- [ ] **Animated characters** (`psdfile`, `getSample`): eye blinks and lip-sync through `KAGEnvCharacterEx.tjs` and `psdlayer.tjs`, which nothing loads yet. Loading layers with `psd://` can also stand in for the missing `layerExSubImage` plugin that `psdlayer.tjs` uses for partial images.
- [ ] **Vector sprites** (`layerExVector`): it copies part of the GDI+ plugin's `GdiPlus` API, including `Image` and `drawImageAffine`, so `VectorAffineSourceLayer` in `AffineLayer.tjs` can work again. It loads SVG, in place of the `.emf`/`.wmf` images that `doc/kagex.txt` documents (those stop with an error on the SDL engine).
- [ ] **Particle effects** (`krkreffekseer`): Effekseer effects to replace the fire effect (`GFX_Fire.tjs` needs `gfxEffect`, which isn't built), with a demo in place of `effect.ks`.
- [ ] **More transitions** (`extNagano`): 12 more, such as blurfade, book and morphing, alongside extrans's 7, shown in `transition.ks`.
- [ ] **Smaller plugins:**
  - `layerExSave`: saves without a pause.
  - `layerExAreaAverage`: smoother thumbnails than `shrinkCopy`.
  - `minizip`: zip archives (`zip://`) for patches or DLC.
  - `clipfile`: loading CLIP STUDIO PAINT files directly.

## Interface, accessibility and languages

- [ ] Screen readers: KAG has no support of its own, so the message window should pass its text to `ElementsDialog.announce`, and the choice menu should expose its choices with `ElementsDialog.setGameA11y` (engine guide: Accessibility).
- [ ] Japanese and English in one build, choosing the language from `System.uiLanguageCandidates`.
- [ ] A hotkey (and a controller button) that switches the language while playing: the current message, the choices and the menus redraw in the other language, and the history keeps what was shown. Needs the item above; the framework has no language support yet.
- [ ] Line breaking with krkr_richtext's `StyledLayout` (`breakStrategy`, ruby, vertical text, per-character timing), in place of this fork's `needsToBeWrapped()` word wrap and its page-break edge cases.
- [ ] Menus built with Elements panels (`ElementsPanel`), which draw into a game layer and work with a controller, in place of the Win32 menu bar on every platform.
- [ ] Positional sound effects on World stages (`WaveSoundBuffer.use3D`, `SoundListener`).

## Needing plugins of our own

Native code that krkrz_dev doesn't have, built outside it (in this repository or next to it, as `extrans` once was in krkren/SamplePlugin) for every platform, including the web, Android and iOS engines in kagex-release's engine packages. The web build links its plugins into `krkrz.wasm`, so those are built with the engine.

- [ ] **Live2D**: a plugin on the Cubism SDK for Native that loads `.model3.json` models and plays their motions and expressions into a layer, drawn with OpenGL ES the way `krkreffekseer` draws Effekseer. Then a World character whose poses and faces are motions and expressions, blinking by itself and lip-syncing to voices through `getSample`. The SDK isn't open source: Cubism Core is a prebuilt library under Live2D's proprietary license, and releasing a game with it can need Live2D's SDK release license, which the documentation should say.
- [ ] **Archive encryption**: kagex-release encrypts `data.xp3` with the game's key, and a plugin decrypts it as the engine reads, through the engine's XP3 extraction filter (`TVPSetXP3ArchiveExtractionFilter` in tp_stub; check the SDL engine still calls it). krkrz_dev has neither half: krkrz_tools' xp3 writer only sets the "protect" flag, a notice to extraction tools, and `sigcheck` checks signatures against tampering. The key has to ship with the game, so this keeps out casual extraction, not a determined one.
