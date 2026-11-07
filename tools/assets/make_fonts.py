#!/usr/bin/env python3
"""Makes the sample's second message font (data/others/notoserifjp-subset.otf, with its
licence, notoserifjp-OFL.txt): Noto Serif CJK JP Regular (SIL OFL 1.1) cut down to Latin,
the kana and punctuation, and every character the sample's scripts, lists and strings use,
so Config's Text page has a font to choose besides Noto Sans JP without adding megabytes to
every build. Characters it lacks (a name the player types) come from the fonts after it in
the face list (fonts.csv).

usage: python3 tools/assets/make_fonts.py [--source FILE]

--source: NotoSerifCJKjp-Regular.otf; without it the font is downloaded from the noto-cjk
repository on GitHub. Run it again after adding text with characters the subset doesn't
have (a new kanji in a translation): `--check` lists them. Needs fontTools.
"""
import argparse, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(DATA, "others")
OUT = os.path.join(OUT_DIR, "notoserifjp-subset.otf")
LICENCE = os.path.join(OUT_DIR, "notoserifjp-OFL.txt")
URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/OTF/Japanese/NotoSerifCJKjp-Regular.otf"
LICENCE_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/LICENSE"
TEXT_EXT = (".ks", ".csv", ".json", ".tjs", ".txt", ".vtt")


def decode(raw):
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le", "ignore")
    for enc in ("utf-8-sig", "shift_jis"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "ignore")


def characters():
    """Every character the sample can show: the scripts, lists and strings in data/ and
    template/system's strings, and the ranges any text may need"""
    chars = set(chr(c) for c in range(0x20, 0x7f))
    chars |= set(chr(c) for c in range(0xa0, 0x100))      # Latin-1
    chars |= set(chr(c) for c in range(0x2010, 0x2028))   # dashes, quotes, ellipsis
    chars |= set(chr(c) for c in range(0x3000, 0x3040))   # CJK punctuation
    chars |= set(chr(c) for c in range(0x3041, 0x3097))   # hiragana
    chars |= set(chr(c) for c in range(0x30a0, 0x3100))   # katakana
    chars |= set(chr(c) for c in range(0xff01, 0xff5f))   # full-width forms
    chars |= set("♪♥★☆○●◆◇□■△▲▽▼→←↑↓")
    roots = [DATA, os.path.join(ROOT, "template", "system")]
    for root in roots:
        for folder, dirs, files in os.walk(root):
            for name in files:
                if not name.lower().endswith(TEXT_EXT) or name.endswith(".scn.json"):
                    continue
                if root != DATA and not name.endswith(".json"):
                    continue  # the framework's own strings only
                with open(os.path.join(folder, name), "rb") as f:
                    chars |= set(decode(f.read()))
    return "".join(sorted(c for c in chars if c >= " "))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", help="NotoSerifCJKjp-Regular.otf (downloaded without it)")
    ap.add_argument("--check", action="store_true", help="list the characters the subset lacks")
    opts = ap.parse_args()
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError:
        raise SystemExit("make_fonts.py needs fontTools (pip install fonttools)")
    text = characters()
    if opts.check:
        have = TTFont(OUT).getBestCmap()
        missing = [c for c in text if ord(c) not in have and not c.isspace()]
        print("%d characters missing%s" % (len(missing), ": " + "".join(missing) if missing else ""))
        return 1 if missing else 0
    source = opts.source
    if not source:
        source = os.path.join(OUT_DIR, ".NotoSerifCJKjp-Regular.otf.download")
        print("downloading", URL)
        urllib.request.urlretrieve(URL, source)
    os.makedirs(OUT_DIR, exist_ok=True)
    font = TTFont(source, lazy=False)
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.desubroutinize = True
    sub = subset.Subsetter(options)
    sub.populate(text=text)
    sub.subset(font)
    font.save(OUT)
    if not opts.source:
        os.remove(source)
    have = font.getBestCmap()
    missing = [c for c in text if ord(c) not in have and not c.isspace()]
    print("%s: %d bytes, %d characters (%d of the text's not in the font)" %
          (os.path.relpath(OUT, ROOT), os.path.getsize(OUT), len(have), len(missing)))
    if not os.path.exists(LICENCE):
        urllib.request.urlretrieve(LICENCE_URL, LICENCE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
