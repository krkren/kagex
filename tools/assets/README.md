# Sample art

The sample's images are generated here rather than edited by hand.

- `make_ui.py` draws the UI in `data/image` (title, logo, message window and its buttons,
  choices, config, save/load, Extras, history), the click-wait glyphs in `template/system`
  and the World demo's star. Every screen uses the look of the Yes/No dialogs in
  `template/system`: lavender panels, violet borders, hard violet shadows, white buttons that
  turn violet when hovered or selected. The colours, sizes and labels are at the top of each
  function; the positions match the `.ks` files that place the images, so a layout change
  touches both.
- `upscale.py` rebuilds the character sprites and the two backgrounds from the original
  800x600-era art in `src/` with Real-ESRGAN, run in NumPy (no PyTorch). It downloads the
  weights into `.weights/` on first use and takes about half an hour on two cores.

```bash
python3 tools/assets/upscale.py          # sprites, backgrounds, CG thumbnail
python3 tools/assets/make_ui.py          # all UI images; or name groups: title logo message
                                         # config saveload extras history star thumbs
```

Run `upscale.py` first: the title screen and the Replay thumbnail are drawn from the
upscaled background and sprite. Both need NumPy and Pillow. The labels use the subset Noto
Sans CJK JP fonts in `fonts/` (SIL OFL 1.1, `fonts/OFL.txt`); the game doesn't load them.
