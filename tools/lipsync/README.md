# kagex-lipsync

Makes the vowel data for the voices a game picks, so the characters drawn from layers shape
their mouths to the vowels those voices say (mouths by vowel, `doc/world.txt`, "Blinking and
lip-sync"). It ships beside kagex-release, and works the same way: a window (a local page in a
browser app window), and everything from the command line too (`--cli`).

Every voice already opens and shuts its character's mouth by how loud it is, as it plays, with
nothing to prepare. A voice picked here also gets a **lip track**: `<voice>.lip` beside it (for
`ai000001.ogg`, `ai000001.lip`), the mouth over time. The game reads it while developing and in
a release (kagex-release packs it like any file, and a voice converted to Opus keeps it), and
shows the mouth for each vowel when the voice says it.

## How it works

The track comes from the voice and its line. The tool runs the game's own scenario compiler in
its engine (the framework's `-voicelines`, so a voice is matched to its line exactly as the game
plays it: `【ai】` names, `[ai voice=12]`, numbering, rubies), then lines the line up with the
voice by **forced alignment**, with existing libraries and nothing trained for KAGEX:

- [PocketSphinx](https://github.com/cmusphinx/pocketsphinx) (BSD) aligns the line's sounds to
  the voice, with its US English acoustic model and CMUdict for English words;
- for a Japanese line (any kana or kanji in it), [OpenJTalk](https://github.com/r9y9/open_jtalk)
  (BSD, with MeCab and NAIST-jdic) reads the line's sounds from its text, kanji included, a
  ruby's reading in place of what it's over, and they're aligned as the English sounds nearest
  them.

Each sound's mouth is then the track: a, i, u, e or o for a vowel (an English diphthong is two),
n where the lips close (m, b, p), `-` for anything else, and how open from how loud the voice
is there (`lipSyncHalfLevel` 0.03, `lipSyncOpenLevel` 0.12).

How well it does was measured on synthesized lines in eight voices (four Japanese, four English,
women's and men's), whose sounds' times are known, as the share of the time the face shows the
mouth the voice is making, with the mouth changing every 120 ms as the game changes it:

| | right vowel, of the time both show one | vowel shown, of the time the voice says one | open or shut as it should be |
|---|---|---|---|
| Japanese | 86% | 69% | 79% |
| English | 87% | 75% | 82% |
| the best 120 ms changes allow | 90% | 78-82% | 86% |
| without a track (the engine's `getVowel`, `lipEngineVowels`) | 22% (Japanese), 39% (English) | | |

Aligning takes about a tenth of a second for a second of voice.

## Using it

A KAGEX package keeps the tool in `tools/`, with its `lipsync/` folder (the models and the
dictionary, 112 MB). Start it, and it opens the game in the folder above (the one with `data/`);
`Open…` picks another. It reads the scripts' lines straight away, with the engine next to
`data/` or else this computer's engine package, as kagex-release finds it (`--engines`,
`KAGEX_RELEASE_ENGINES`, `engines/`, the cache, or a download).

The window lists every voice the scripts name, and every sound in a folder named `voice`, with
its character, its line and its state: no vowel data, vowel data, out of date (the voice has
changed since its track was made), hand-written (a `.lip` the tool didn't write), or voice not
found (the scripts name a voice the game hasn't got). Pick voices one by one, by character or
with the filter, and *Make vowel data*. Where a voice doesn't say its line as written (a line
translated from the language it's recorded in, an ad-lib), type what it says in the line's box:
the tool aligns that instead, and refuses a voice that doesn't fit its line rather than guess.
In a game in more than one language (`KAGLanguageList`), the scripts give each voice its line in
each of them, and the tool aligns the voice to the first one it fits, the source language's
first: in the sample, written in English, Ai's voice, recorded in Japanese, gets its track from
the Japanese line. The track says which (`# language:`).
*Show* draws a track's mouths over time and plays the voice along.

```bash
kagex-lipsync                                    # the window, for the game here or above the tool
kagex-lipsync path/to/game                       # the window, for that game
kagex-lipsync --cli list  [path]                 # the voices, their lines and their tracks
kagex-lipsync --cli make  ai000001.ogg ...       # make these voices' tracks from their lines
kagex-lipsync --cli make  --character=ai         # ... a character's (--all: every voice with a line)
kagex-lipsync --cli make  --stale                # ... the ones whose voice changed
kagex-lipsync --cli make  ai000001.ogg --text="おはよう。今起きたところ？"   # with the line it says
kagex-lipsync --cli check [path]                 # the tracks whose voice changed (exit code 1)
kagex-lipsync --cli align <voice file> <text> [<out.lip>]   # one file and a line, no game
```

`make` takes `--project=DIR` (the game; otherwise the current folder, or the folder above the
tool) and `--force` (remake current tracks too, and replace hand-written ones); `list` and
`make` take `--engines=DIR`; `list`, `make` and `check` take `--json`. Exit codes: 0 fine,
1 problems found, 2 failed. `KAGEX_LIPSYNC_DATA` names the models' folder instead of
`lipsync/` beside the tool.

kagex-release's check warns about tracks that are out of date.

## The .lip file

```text
# kagex-lipsync 0.11.0: the mouth over pip000009.ogg, from its line (tools/lipsync)
# voice: <the voice's SHA-256>
# text: Hi again! Listen closely. ...
# language: en
# ms, the mouth from then on (a i u e o, n for the lips closed, - for any other sound), how open (0-2)
0	-	0
130	a	2
200	i	2
...
```

Lines starting with `#` are comments to the game; the tool reads its header to tell a track's
state. A track can also be written by hand (no header: "hand-written").

## Building

It's built with kagex-release (`tools/release/CMakeLists.txt` adds `tools/lipsync`, and
`-DKAGEX_LIPSYNC=OFF` leaves it out), into the same folder: `kagex-lipsync(.exe)` and
`lipsync/`. PocketSphinx and OpenJTalk come from GitHub at fixed commits (CMake's FetchContent;
`FETCHCONTENT_SOURCE_DIR_KAGEX_POCKETSPHINX` / `_KAGEX_OPENJTALK` use checkouts already here),
and the build compiles NAIST-jdic into OpenJTalk's dictionary with MeCab's own compiler. Their
licenses go into `lipsync/licenses/`.
