# Sample art

The sample's images are generated here rather than edited by hand.

- `make_ui.py` draws the UI in `data/image` (title, logo, message window and its buttons,
  choices, config, save/load, Extras, history), the click-wait glyphs in `template/system`,
  the World demo's star and the app icons in `platform/` (the Linux desktop entry's SVG, the
  iOS and macOS icon, Android's adaptive icon layers, the web build's home-screen icons in `platform/web`), and the web build's link-preview image (`platform/web/preview.jpg`, from `title.png`). Every screen uses the look of the Yes/No dialogs in
  `template/system`: lavender panels, violet borders, hard violet shadows, white buttons that
  turn violet when hovered or selected. The colours, sizes and labels are at the top of each
  function; the positions match the `.ks` files that place the images, so a layout change
  touches both.
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
- `upscale.py` rebuilds the character sprites and the two backgrounds from the original
  800x600-era art in `src/` with Real-ESRGAN, run in NumPy (no PyTorch). It downloads the
  weights into `.weights/` on first use and takes about half an hour on two cores.

```bash
python3 tools/assets/upscale.py          # sprites, backgrounds, CG thumbnail
python3 tools/assets/make_ui.py          # all UI images; or name groups: title logo message
                                         # config saveload extras history star thumbs icons preview
python3 tools/assets/make_effects.py     # effect textures and effects; or: textures effects
python3 tools/assets/make_rules.py       # rule images for the transitions
```

Run `upscale.py` first: the title screen and the Replay thumbnail are drawn from the
upscaled background and sprite. Both need NumPy and Pillow; the `icons` group also needs fontTools, for the K's outline. The labels use the subset Noto
Sans CJK JP fonts in `fonts/` (SIL OFL 1.1, `fonts/OFL.txt`); the game doesn't load them.
