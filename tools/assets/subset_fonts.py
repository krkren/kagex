#!/usr/bin/env python3
"""Makes the Noto Sans CJK subsets that make_ui.py draws the labels of other languages with
(tools/assets/fonts/NotoSansCJKjp-<weight>-Japanese.otf, and since 0.28.1
NotoSansCJKsc-<weight>-SC.otf and NotoSansCJKtc-<weight>-TC.otf for Simplified and Traditional
Chinese): Latin, the punctuation (and for Japanese the kana), and every character of make_ui.py's
labels in that language, from the full fonts.

usage: python3 tools/assets/subset_fonts.py [--source DIR] [--lang ja,zh-cn,zh-tw]

The full fonts are Noto Sans CJK (SIL OFL 1.1): NotoSansCJK<jp|sc|tc>-<weight>.otf in --source,
or the system's NotoSansCJK-<weight>.ttc (Debian/Ubuntu's fonts-noto-cjk, Arch's
noto-fonts-cjk), whose fonts are JP, KR, SC, TC and HK in that order. Run it again after adding a label with a
character the subsets don't have: make_ui.py stops on one (missing_glyphs). Needs fontTools.
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
WEIGHTS = ("Medium", "Bold", "Black")
SYSTEM_DIRS = ("/usr/share/fonts/opentype/noto", "/usr/share/fonts/noto-cjk", "/usr/share/fonts/google-noto-cjk",
               "/usr/share/fonts/OTF", "/Library/Fonts", os.path.expanduser("~/Library/Fonts"))


# each language: the full fonts' region code, the font's number in the .ttc, the subset's name
LANGS = {"ja": ("jp", 0, "NotoSansCJKjp-%s-Japanese.otf"), "zh-cn": ("sc", 2, "NotoSansCJKsc-%s-SC.otf"),
         "zh-tw": ("tc", 3, "NotoSansCJKtc-%s-TC.otf")}


def source_font(weight, source, lang="ja"):
    """(path, font number) of the full font of this weight for the language"""
    region, ttc_number = LANGS[lang][0], LANGS[lang][1]
    dirs = [source] if source else SYSTEM_DIRS
    for d in dirs:
        for name, number in (("NotoSansCJK%s-%s.otf" % (region, weight), 0), ("NotoSansCJK-%s.ttc" % weight, ttc_number),
                             ("NotoSansCJK%s.ttc" % weight, ttc_number)):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p, number
    raise SystemExit("no full Noto Sans CJK %s %s font (NotoSansCJK%s-%s.otf or NotoSansCJK-%s.ttc) in %s"
                     % (region.upper(), weight, region, weight, weight, ", ".join(dirs)))


def characters(lang="ja"):
    sys.path.insert(0, HERE)
    import make_ui
    chars = set(chr(c) for c in range(0x20, 0x7f))
    chars |= set("·…―—–「」『』（）［］【】〈〉《》、。・ー～！？：；，．　♪")
    if lang == "ja":
        chars |= set(chr(c) for c in range(0x3041, 0x3097))   # hiragana
        chars |= set(chr(c) for c in range(0x30a1, 0x30fb))   # katakana
    else:
        chars |= set("“”‘’、")
    chars |= set(chr(c) for c in range(0xff10, 0xff1a))   # full-width digits
    for text in make_ui.all_labels(lang):
        chars |= set(text)
    return "".join(sorted(chars))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", help="a folder with NotoSansCJK<jp|sc|tc>-<weight>.otf")
    ap.add_argument("--lang", default="ja,zh-cn,zh-tw", help="the languages to make subsets for")
    opts = ap.parse_args()
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError:
        raise SystemExit("subset_fonts.py needs fontTools (pip install fonttools)")
    for lang in opts.lang.split(","):
        text = characters(lang)
        for weight in WEIGHTS:
            path, number = source_font(weight, opts.source, lang)
            font = TTFont(path, fontNumber=number, lazy=False)
            options = subset.Options()
            options.name_IDs = ["*"]
            options.notdef_outline = True
            options.hinting = False
            sub = subset.Subsetter(options)
            sub.populate(text=text)
            sub.subset(font)
            out = os.path.join(FONTS, LANGS[lang][2] % weight)
            font.save(out)
            print("wrote", os.path.relpath(out, os.path.dirname(os.path.dirname(HERE))), "%d characters" % len(text),
                  os.path.getsize(out), "bytes", flush=True)


if __name__ == "__main__":
    main()
