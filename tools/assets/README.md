# Sample art

The sample's images are generated here rather than edited by hand.

- `make_ui.py` draws the UI in `data/image` (title, logo, message window and its buttons,
  choices, config, save/load, Extras, history), the click-wait glyphs and the panel the menu
  and the controls list stretch (`dialog_panel.png`) in `template/system`,
  the World demo's star and the app icons in `platform/` (the Linux desktop entry's SVG, the
  iOS and macOS icon, Android's adaptive icon layers, the web build's home-screen icons in `platform/web`), and the web build's link-preview image (`platform/web/preview.jpg`, from `title.png`). Every screen uses the look of the Yes/No dialogs in
  `template/system`: lavender panels, violet borders, hard violet shadows, white buttons that
  turn violet when hovered or selected. The colours, sizes and labels are at the top of each
  function; the positions match the `.ks` files that place the images, so a layout change
  touches both. The images with words on them are drawn again in each other language into
  `data/lang/<code>/` (the game's language folder, `doc/kagex.txt`, "Languages"), with the
  labels from `LABELS` (keyed by the English): `--lang ja` draws only those, `--lang en,ja`
  both; with no `--lang`, every language.
- `subset_fonts.py` makes the subsets `make_ui.py` draws Japanese and Chinese labels with
  (`fonts/NotoSansCJKjp-*-Japanese.otf`, `NotoSansCJKsc-*-SC.otf`, `NotoSansCJKtc-*-TC.otf`:
  Latin, the kana or punctuation, and every character of that language's labels) from the full
  Noto Sans CJK, the system's (`fonts-noto-cjk`, `noto-fonts-cjk`) or `--source <folder>`;
  `--lang ja,zh-cn,zh-tw` picks which. Run it after adding a label with a character they
  don't have: `make_ui.py` stops on one.
- `make_fonts.py` makes the fonts the game itself draws with that the engine lacks
  (`data/others`, listed in `data/main/fonts.csv`): the second message font (Noto Serif JP) and
  the Chinese faces (Noto Sans SC and TC), each cut down to the characters the sample's texts use
  plus the common ones (GB2312's first level, Big5's), so a typed name mostly finds its
  characters. `--check` lists what the subsets lack after the texts change; `--source-dir`
  takes a folder of the full fonts instead of downloading them.
- `make_zhtw.py` makes the Traditional Chinese (`data/lang/zh-tw`,
  `template/system/*_zh-tw.*`) from the Simplified (`zh-cn`) with OpenCC's `s2twp` and a table of
  the words Taiwan's menus use (`pip install opencc-python-reimplemented`); run it after
  changing a `zh-cn` file, then `make_ui.py --lang zh-tw` for the pictures.
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
- `make_hiyori.py` gets the demo's Live2D character, Hiyori (Live2D Inc.'s sample model), whose
  files aren't in the repository: Live2D's Free Material License lets no one but Live2D hand out
  its sample models' files (a work an individual or a small business makes with them may ship them
  inside it). `model --accept-license` fetches her from Live2D's CubismNativeSamples on GitHub, at
  a pinned commit, into `data/fgimage/hiyori.l2d` (gitignored): her folder's contents in a zip
  with fixed times, so it's the same file every time. `--accept-license` says you agree to that
  licence and her terms. `speech` makes her voice line (`data/voice/hiyori000001.ogg`, the
  `【hiyori】` line after `voice=1` in anim.ks) with eSpeak NG, a formant synthesizer (rules and a
  model of the vocal tract, no voice learned from recordings), in US English's `anika` variant at
  160 words a minute, and ffmpeg (`ESPEAK_NG` names espeak-ng when it isn't on the PATH; 1.52.0
  made the committed line, the same bytes each time); kagex-lipsync then makes its lip track
  (`kagex-lipsync --cli make hiyori000001.ogg`).
- `make_vrm.py` builds the Animated Character demo's 3D character, Vee, as a VRM 1.0 avatar
  (`data/fgimage/vee.vrm`): a girl in a lavender dress with twin tails, every part a surface of
  revolution, an ellipsoid or a capsule in NumPy, skinned to a VRM humanoid skeleton, coloured by
  MToon materials with the theme's navy outline, her face shapes on her head that her expressions
  move (VRM's presets, the mouths aa ... oh, blink, and blush of her own), her twin tails on
  spring bones. `motions` writes her VRM animations (`vee_<motion>.vrma`: idle and think loop,
  wave, nod, bow and cheer play once), `prop` the layer demo's glTF star (`star3d.glb`, with its
  spin and hop animations), and `speech` her voice line (`data/voice/vee000001.ogg`) with eSpeak
  NG, as `make_hiyori.py` does Hiyori's; kagex-lipsync makes its lip track. glTF's colour factors
  are linear, but krkrthreepp's MToon shader draws them as given, so they're written as they
  should look.
- `make_opening.py` draws the opening movie the logo plays (`data/video/opening.webm`,
  1920x1080, and `opening_sd.webm`, 960x540, for the web and phones), 14 s in the sample's look:
  the K badge and the wordmark on the lavender screen, the street with Ai coming in, three framed
  pictures from the demos and the evening title with its stars, over the start of `bgm01`
  (Opus), with no alpha (VP9 WebM; a side-by-side alpha movie is only needed where something
  shows through). It also writes Replay's tile for it, `data/thum/thum_opening.png`. The words
  are in its subtitles, `data/video/opening.vtt` and `data/lang/ja/opening.vtt`, not in the
  picture. It uses `make_ui.py`'s drawing (so fontTools) and its title pictures, and Pip's
  layers; ffmpeg's bitexact flags keep the files the same from run to run.
- `make_sounds.py` makes the Character demo's positional sound effects in `data/sound`: a
  two-note chime (`se_chime.ogg`, played at the far left and far right of the stage) and
  footsteps that loop (`se_steps.ogg`, following Ai as she walks), drawn in NumPy with fixed
  seeds and encoded with ffmpeg's libvorbis, in mono: the engine pans a placed sound itself.
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
                                         # dialog
                                         # (--lang ja: only the Japanese ones)
python3 tools/assets/subset_fonts.py     # the Japanese and Chinese label fonts (needs fontTools)
python3 tools/assets/make_fonts.py       # the serif and Chinese fonts the game draws with
python3 tools/assets/make_zhtw.py        # Traditional Chinese from Simplified (needs OpenCC)
python3 tools/assets/make_effects.py     # effect textures and effects; or: textures effects
python3 tools/assets/make_rules.py       # rule images for the transitions
python3 tools/assets/make_vector.py      # the layer demo's SVG emblem and its PNG
python3 tools/assets/make_clip.py        # the emblem as a CLIP STUDIO PAINT file (needs the engine)
python3 tools/assets/make_pip.py         # Pip's layers and voice lines; or: art voice speech
python3 tools/assets/make_hiyori.py model --accept-license   # Hiyori's model (Live2D's licence)
python3 tools/assets/make_hiyori.py speech  # her voice line (needs espeak-ng and ffmpeg)
python3 tools/assets/make_sounds.py      # the Character demo's sound effects (needs ffmpeg)
python3 tools/assets/make_opening.py     # the opening movie, its smaller version and Replay tile
                                         # (needs ffmpeg with libvpx-vp9 and libopus)
python3 tools/assets/make_vrm.py         # Vee's VRM avatar, her VRM animations and the glTF star;
                                         # or: model motions prop; speech (espeak-ng, ffmpeg)
python3 tools/assets/psdwrite.py <structure.txt> [out.psd]   # a layer structure as a PSD
```

Run `upscale.py` first: the title screen and the Replay thumbnail are drawn from the
upscaled background and sprite. Both need NumPy and Pillow; the `icons` group also needs fontTools, for the K's outline. The labels use the subset Noto
Sans CJK JP fonts in `fonts/` (SIL OFL 1.1, `fonts/OFL.txt`), Latin and Japanese; the game
doesn't load them.
