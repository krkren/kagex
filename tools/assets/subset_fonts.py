#!/usr/bin/env python3
"""Makes the Noto Sans CJK JP subsets that make_ui.py draws the Japanese labels with
(tools/assets/fonts/NotoSansCJKjp-<weight>-Japanese.otf): Latin, the kana and punctuation,
and every character of make_ui.py's Japanese labels, from the full fonts.

usage: python3 tools/assets/subset_fonts.py [--source DIR]

The full fonts are Noto Sans CJK JP (SIL OFL 1.1): NotoSansCJKjp-<weight>.otf in --source,
or the system's NotoSansCJK-<weight>.ttc (Debian/Ubuntu's fonts-noto-cjk, Arch's
noto-fonts-cjk), whose first font is the JP one. Run it again after adding a label with a
character the subsets don't have: make_ui.py stops on one (missing_glyphs). Needs fontTools.
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
WEIGHTS = ("Medium", "Bold", "Black")
SYSTEM_DIRS = ("/usr/share/fonts/opentype/noto", "/usr/share/fonts/noto-cjk", "/usr/share/fonts/google-noto-cjk",
               "/usr/share/fonts/OTF", "/Library/Fonts", os.path.expanduser("~/Library/Fonts"))


def source_font(weight, source):
    """(path, font number) of the full JP font of this weight"""
    dirs = [source] if source else SYSTEM_DIRS
    for d in dirs:
        for name, number in (("NotoSansCJKjp-%s.otf" % weight, 0), ("NotoSansCJK-%s.ttc" % weight, 0),
                             ("NotoSansCJK%s.ttc" % weight, 0)):
            p = os.path.join(d, name)
            if os.path.exists(p):
                return p, number
    raise SystemExit("no full Noto Sans CJK JP %s font (NotoSansCJKjp-%s.otf or NotoSansCJK-%s.ttc) in %s"
                     % (weight, weight, weight, ", ".join(dirs)))


def characters():
    sys.path.insert(0, HERE)
    import make_ui
    chars = set(chr(c) for c in range(0x20, 0x7f))
    chars |= set("·…―—–「」『』（）［］【】〈〉《》、。・ー～！？：；，．　♪")
    chars |= set(chr(c) for c in range(0x3041, 0x3097))   # hiragana
    chars |= set(chr(c) for c in range(0x30a1, 0x30fb))   # katakana
    chars |= set(chr(c) for c in range(0xff10, 0xff1a))   # full-width digits
    for text in make_ui.all_labels("ja"):
        chars |= set(text)
    return "".join(sorted(chars))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", help="a folder with NotoSansCJKjp-<weight>.otf")
    opts = ap.parse_args()
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError:
        raise SystemExit("subset_fonts.py needs fontTools (pip install fonttools)")
    text = characters()
    for weight in WEIGHTS:
        path, number = source_font(weight, opts.source)
        font = TTFont(path, fontNumber=number, lazy=False)
        options = subset.Options()
        options.name_IDs = ["*"]
        options.notdef_outline = True
        options.hinting = False
        sub = subset.Subsetter(options)
        sub.populate(text=text)
        sub.subset(font)
        out = os.path.join(FONTS, "NotoSansCJKjp-%s-Japanese.otf" % weight)
        font.save(out)
        print("wrote", os.path.relpath(out, os.path.dirname(os.path.dirname(HERE))), "%d characters" % len(text),
              os.path.getsize(out), "bytes", flush=True)


if __name__ == "__main__":
    main()
