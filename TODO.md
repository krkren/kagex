# To do

Planned features, in two groups. Each needs only script and data work in this repository: the plugins below are already in krkrz_dev's default build and ship in the Linux package, and krkrz_dev itself isn't changed (`CLAUDE.md`).

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
- [ ] Line breaking with krkr_richtext's `StyledLayout` (`breakStrategy`, ruby, vertical text, per-character timing), in place of this fork's `needsToBeWrapped()` word wrap and its page-break edge cases.
- [ ] Menus built with Elements panels (`ElementsPanel`), which draw into a game layer and work with a controller, in place of the Win32 menu bar on every platform.
- [ ] Positional sound effects on World stages (`WaveSoundBuffer.use3D`, `SoundListener`).
