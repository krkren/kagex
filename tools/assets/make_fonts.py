#!/usr/bin/env python3
"""Makes the sample's second message font (data/others/notoserifjp-subset.otf, with its
licence, notoserifjp-OFL.txt): Noto Serif CJK JP Regular (SIL OFL 1.1) cut down to Latin,
the kana and punctuation, and every character the sample's scripts, lists and strings use,
so Config's Text page has a font to choose besides Noto Sans JP without adding megabytes to
every build. Characters it lacks (a name the player types) come from the fonts after it in
the face list (fonts.csv).

It also makes the Chinese text fonts (since 0.28.1): data/others/notosanssc-subset.otf and
notosanstc-subset.otf, Noto Sans CJK SC and TC Regular cut down to what the sample shows in
Simplified (data/lang/zh-cn, template/system's *_zh-cn files) and Traditional Chinese (zh-tw)
plus the characters in common use (GB2312's first level, 3755, and Big5's, 5401), so a name the
player types draws too. fonts.csv puts each first for its language.

usage: python3 tools/assets/make_fonts.py [--fonts serif,sc,tc] [--source FILE] [--source-dir DIR] [--check]

--source: NotoSerifCJKjp-Regular.otf; --source-dir: a folder with the full fonts
(NotoSerifCJKjp-Regular.otf, NotoSansCJKsc-Regular.otf, NotoSansCJKtc-Regular.otf); a font not
given is downloaded from the noto-cjk repository on GitHub. Run it again after adding text with
characters a subset doesn't have (a new kanji in a translation): `--check` lists them. Needs
fontTools.
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
SANS_LICENCE_URL = "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/LICENSE"
SANS_LICENCE = os.path.join(OUT_DIR, "notosanscjk-OFL.txt")
# the Chinese fonts: (key, the full font, its download, the subset, the language folder)
CHINESE = [
    ("sc", "NotoSansCJKsc-Regular.otf",
     "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf",
     os.path.join(OUT_DIR, "notosanssc-subset.otf"), "zh-cn"),
    ("tc", "NotoSansCJKtc-Regular.otf",
     "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans/OTF/TraditionalChinese/NotoSansCJKtc-Regular.otf",
     os.path.join(OUT_DIR, "notosanstc-subset.otf"), "zh-tw"),
]
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


def common_characters(key):
    """the characters in common use: GB2312's first level (Simplified), Big5's (Traditional)"""
    chars = set()
    if key == "sc":
        for hi in range(0xb0, 0xd8):
            for lo in range(0xa1, 0xff):
                try:
                    chars.add(bytes([hi, lo]).decode("gb2312"))
                except UnicodeDecodeError:
                    pass
    else:
        for hi in range(0xa4, 0xc7):
            for lo in list(range(0x40, 0x7f)) + list(range(0xa1, 0xff)):
                try:
                    chars.add(bytes([hi, lo]).decode("big5"))
                except UnicodeDecodeError:
                    pass
    return chars


def chinese_characters(key, code):
    """what the Chinese font draws: its language's texts, Latin and punctuation, the common set"""
    chars = set(chr(c) for c in range(0x20, 0x7f))
    chars |= set(chr(c) for c in range(0xa0, 0x100))
    chars |= set(chr(c) for c in range(0x2010, 0x2028))
    chars |= set(chr(c) for c in range(0x3000, 0x3040))
    chars |= set(chr(c) for c in range(0xff01, 0xff5f))
    chars |= set("♪♥★☆○●◆◇□■△▲▽▼→←↑↓")
    chars |= common_characters(key)
    folder = os.path.join(DATA, "lang", code)
    for sub, dirs, files in os.walk(folder):
        for name in files:
            if name.lower().endswith(TEXT_EXT):
                with open(os.path.join(sub, name), "rb") as f:
                    chars |= set(decode(f.read()))
    system = os.path.join(ROOT, "template", "system")
    for name in os.listdir(system):
        if "_%s." % code in name and name.lower().endswith(TEXT_EXT):
            with open(os.path.join(system, name), "rb") as f:
                chars |= set(decode(f.read()))
    return "".join(sorted(c for c in chars if c >= " "))


# The family a subset is named as inside the file: the face fonts.csv gives it. The engine's own
# text (Layer.drawText, getTextWidth) finds a registered file's font by the name in the file, so
# with Noto CJK's own names ("Noto Sans CJK SC") it fell back to a system font and drew every
# character it lacked as "?" (krkr_richtext, which draws the message text, finds it either way).
# The Noto fonts have no Reserved Font Name, so the OFL allows the rename.
FAMILIES = {"serif": "Noto Serif JP", "sc": "Noto Sans SC", "tc": "Noto Sans TC"}


def rename(font, family):
    ps = family.replace(" ", "") + "-Regular"
    names = font["name"]
    for rec in names.names:
        if rec.nameID in (1, 4, 16):
            names.setName(family, rec.nameID, rec.platformID, rec.platEncID, rec.langID)
        elif rec.nameID == 6:
            names.setName(ps, rec.nameID, rec.platformID, rec.platEncID, rec.langID)
        elif rec.nameID == 3:
            names.setName("%s;%s" % (rec.toUnicode().split(";")[0], ps), rec.nameID, rec.platformID,
                          rec.platEncID, rec.langID)
    if "CFF " in font:
        cff = font["CFF "].cff
        cff.fontNames = [ps]
        top = cff.topDictIndex[0]
        top.FullName = family
        top.FamilyName = family


def subset_font(source, text, out, layout=True, family=None):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    font = TTFont(source, lazy=False)
    options = subset.Options()
    options.layout_features = ["*"] if layout else []
    options.name_IDs = ["*"]
    options.name_legacy = True
    options.name_languages = ["*"]
    options.notdef_outline = True
    options.desubroutinize = True
    options.hinting = False
    sub = subset.Subsetter(options)
    sub.populate(text=text)
    sub.subset(font)
    if family:
        rename(font, family)
    font.save(out)
    have = font.getBestCmap()
    missing = [c for c in text if ord(c) not in have and not c.isspace()]
    print("%s: %d bytes, %d characters (%d of the text's not in the font)" %
          (os.path.relpath(out, ROOT), os.path.getsize(out), len(have), len(missing)))


def check(path, text):
    from fontTools.ttLib import TTFont
    have = TTFont(path).getBestCmap()
    missing = [c for c in text if ord(c) not in have and not c.isspace()]
    print("%s: %d characters missing%s" % (os.path.relpath(path, ROOT), len(missing), ": " + "".join(missing) if missing else ""))
    return 1 if missing else 0


def source_font(name, url, source_dir, given=None):
    """(path, downloaded) of a full font"""
    if given:
        return given, False
    if source_dir and os.path.exists(os.path.join(source_dir, name)):
        return os.path.join(source_dir, name), False
    path = os.path.join(OUT_DIR, "." + name + ".download")
    print("downloading", url)
    urllib.request.urlretrieve(url, path)
    return path, True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fonts", default="serif,sc,tc", help="the fonts to make: serif, sc, tc")
    ap.add_argument("--source", help="NotoSerifCJKjp-Regular.otf (downloaded without it)")
    ap.add_argument("--source-dir", help="a folder with the full fonts")
    ap.add_argument("--check", action="store_true", help="list the characters the subsets lack")
    opts = ap.parse_args()
    try:
        from fontTools import subset  # noqa: F401
    except ImportError:
        raise SystemExit("make_fonts.py needs fontTools (pip install fonttools)")
    which = opts.fonts.split(",")
    if opts.check:
        bad = 0
        if "serif" in which:
            bad |= check(OUT, characters())
        for key, name, url, out, code in CHINESE:
            if key in which:
                bad |= check(out, chinese_characters(key, code))
        return bad
    os.makedirs(OUT_DIR, exist_ok=True)
    if "serif" in which:
        source, downloaded = source_font("NotoSerifCJKjp-Regular.otf", URL, opts.source_dir, opts.source)
        subset_font(source, characters(), OUT, family=FAMILIES["serif"])
        os.remove(source) if downloaded else None
        if not os.path.exists(LICENCE):
            urllib.request.urlretrieve(LICENCE_URL, LICENCE)
    for key, name, url, out, code in CHINESE:
        if key not in which:
            continue
        source, downloaded = source_font(name, url, opts.source_dir)
        subset_font(source, chinese_characters(key, code), out, family=FAMILIES[key])
        os.remove(source) if downloaded else None
        if not os.path.exists(SANS_LICENCE):
            urllib.request.urlretrieve(SANS_LICENCE_URL, SANS_LICENCE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
