# Sample art

The sample's images are generated here rather than edited by hand.

- `make_ui.py` draws the UI in `data/image` (title, logo, message window and its buttons,
  choices, config, save/load, Extras, history), the click-wait glyphs in `template/system`,
  the World demo's star and the app icons in `platform/` (the Linux desktop entry's SVG, the
  iOS and macOS icon, Android's adaptive icon layers, the web build's home-screen icons in `platform/web`), and the web build's link-preview image (`platform/web/preview.jpg`, from `title.png`). Every screen uses the look of the Yes/No dialogs in
  `template/system`: lavender panels, violet borders, hard violet shadows, white buttons that
  turn violet when hovered or selected. The colours, sizes and labels are at the top of each
  function; the positions match the `.ks` files that place the images, so a layout change
  touches both. The images with words on them are drawn again in each other language into
  `data/lang/<code>/` (the game's language folder, `doc/kagex.txt`, "Languages"), with the
  labels from `LABELS` (keyed by the English): `--lang ja` draws only those, `--lang en,ja`
  both; with no `--lang`, every language.
- `subset_fonts.py` makes the Japanese subsets `make_ui.py` draws Japanese labels with
  (`fonts/NotoSansCJKjp-*-Japanese.otf`: Latin, the kana and every character of the Japanese
  labels) from the full Noto Sans CJK JP, the system's (`fonts-noto-cjk`, `noto-fonts-cjk`) or
  `--source <folder>`. Run it after adding a label with a character they don't have:
  `make_ui.py` stops on one.
- `make_effects.py` makes the Effekseer effects in `data/effect` (sparkle, petals, fireworks,
  shockwave, magiccircle) and their textures in `data/effect/Texture` (a glow, a sparkle, a dot,
  a ring band, a petal and a magic circle, drawn in NumPy). Each effect is a function
  that describes its particle nodes with `efkformat.py`, which writes Effekseer's runtime format
  (`.efk`, version 1.6) without the Effekseer editor; its docstring describes the classes.
  Sizes are in Effekseer units, which the game shows at `efkmag` pixels each (50 by default).
- `make_rules.py` draws the transitions' rule images in `data/rule`: `rule_shatter.png` for
  extNagano's 3duniversal (Voronoi shards: red is when each one starts moving, green how fast,
  blue which way, out from the centre) and `wipe_brush.png` for imagewipe (a violet brush stroke
  with a ragged leading edge).
- `make_vector.py` draws the layer demo's vector sprite, an emblem in the theme's colours, as
  `data/fgimage/emblem.svg` and as a PNG of the same picture at its own size
  (`data/fgimage/emblem_bitmap.png`), from one list of shapes; `layer.ks` zooms the two side by
  side. No text in the SVG: layerExVector draws none.
- `make_clip.py` packs the same emblem, as two layers (`badge` and `star`), into a CLIP STUDIO
  PAINT file, `data/fgimage/emblem.clip`, which layer.ks loads layer by layer with `clip://`.
  A `.clip` can't be written from nothing (CLIPWriter edits files, it doesn't create them), so
  it starts from the empty canvas in clipparse (`samples/emptyimage.clip`, MIT, downloaded once
  into `.cache/`, or given with `--template`) and runs the engine, as `tools/smoketest.py` does,
  to edit it with the clipfile plugin: so it needs the engine next to `data/`.
- `make_pip.py` draws Pip, the Animated Character demo's character, as layers (body, outfits,
  arm poses, and faces whose eyes and mouths are groups of three frames, the plain face's mouth
  with one for each vowel too) at the size of each World level, writing each level's layer
  structure (`data/fgimage/pip/pip_<level>.txt`), a PNG per layer, `pip_info.txt`, and
  `data/main/charinit.csv` and `charanim.csv`. Every shape is a signed distance field in NumPy,
  so each level is drawn rather than scaled. `voice` makes its voice lines
  (`data/voice/pip000001.ogg`...): babble, syllables of a glottal pulse through vowel formants,
  encoded with ffmpeg's libvorbis (so it needs ffmpeg); they move Pip's mouth by their loudness.
  `speech` makes its one line in a real voice (`data/voice/pip000009.ogg`), spoken by Kokoro, a
  speech synthesizer (Kokoro-82M, Apache-2.0, run with ONNX Runtime; the model is downloaded
  into `.cache/kokoro` once), which shows the mouths by vowel: its `pip000009.lip` comes from
  kagex-lipsync (`kagex-lipsync --cli make pip000009.ogg`), as any voice's would.
- `psdwrite.py` writes a layer structure in psdlayer.tjs's text format, with its pictures, as a
  PSD with folders (`psdwrite.py data/fgimage/pip/pip_0.txt pip_0.psd`), the other way round
  from kagex-release's split. Standard library only; the smoke tests make Pip's PSDs with it.
- `upscale.py` rebuilds the character sprites and the two backgrounds from the original
  800x600-era art in `src/` with Real-ESRGAN, run in NumPy (no PyTorch). It downloads the
  weights into `.weights/` on first use and takes about half an hour on two cores.

```bash
python3 tools/assets/upscale.py          # sprites, backgrounds, CG thumbnail
python3 tools/assets/make_ui.py          # all UI images; or name groups: title logo message
                                         # config saveload extras history star thumbs icons preview
                                         # (--lang ja: only the Japanese ones)
python3 tools/assets/subset_fonts.py     # the Japanese label fonts (needs fontTools)
python3 tools/assets/make_effects.py     # effect textures and effects; or: textures effects
python3 tools/assets/make_rules.py       # rule images for the transitions
python3 tools/assets/make_vector.py      # the layer demo's SVG emblem and its PNG
python3 tools/assets/make_clip.py        # the emblem as a CLIP STUDIO PAINT file (needs the engine)
python3 tools/assets/make_pip.py         # Pip's layers and voice lines; or: art voice speech
python3 tools/assets/psdwrite.py <structure.txt> [out.psd]   # a layer structure as a PSD
```

Run `upscale.py` first: the title screen and the Replay thumbnail are drawn from the
upscaled background and sprite. Both need NumPy and Pillow; the `icons` group also needs fontTools, for the K's outline. The labels use the subset Noto
Sans CJK JP fonts in `fonts/` (SIL OFL 1.1, `fonts/OFL.txt`), Latin and Japanese; the game
doesn't load them.
