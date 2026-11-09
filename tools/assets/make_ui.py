#!/usr/bin/env python3
"""Draws the sample's UI images (title, logo, message window, choices, config, save/load,
Extras, history) at 1920x1080 in one style: the lavender panels, violet borders and hard
shadows of the Yes/No dialogs in template/system.

usage: python3 tools/assets/make_ui.py [--lang en,ja] [group ...]    (no groups: all of them)

With --lang, only those languages: English goes to data/image, another language's images with
words on them to data/lang/<code>/ (LABELS below). Without it, English and then every language
LABELS has.

Needs NumPy and Pillow. Labels use the Noto Sans CJK JP subsets in tools/assets/fonts. The
title screen and the Replay thumbnail are drawn from data/bgimage/bg01_01.png and
data/fgimage/ch_0_0_1.png, so run upscale.py first when those change. Everything is drawn 4x and averaged down, so edges are
smooth; sizes and positions below are in screen pixels and match the .ks files that place
the images (title.ks, config.ks, save.ks, load.ks, cgmode.ks, replay.ks, musicmode.ks,
macro.ks's [initscene]) and MyHistoryLayer.tjs.
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
IMAGE = os.path.join(REPO, "data", "image")
SYSTEM = os.path.join(REPO, "template", "system")
SS = 4  # supersampling

# --- the palette (the Yes/No dialog's colours) -----------------------------------------
VIOLET = (80, 37, 255)        # borders, shadows, selected buttons
LAV = (166, 144, 255)         # panels
LAV_SOFT = (214, 204, 255)
LAV_PALE = (243, 240, 255)    # screen backgrounds
NAVY = (1, 0, 98)             # text outlines
DEEP = (34, 12, 120)          # the history's backdrop, latched buttons
INK = (36, 16, 122)           # dark text on white
WHITE = (255, 255, 255)


def rgba(c, a=255):
    return tuple(c[:3]) + (a,)


# --- languages -------------------------------------------------------------------------
# The images are drawn in English into data/image, and those with words on them again in each
# other language into data/lang/<code>/, which the game puts on its search path while it shows
# that language (Initialize.tjs, KAGLanguage): `make_ui.py --lang ja config`. Labels are
# translated through LABELS, keyed by the English; the Japanese ones are drawn with the
# Japanese subsets in fonts/ (subset_fonts.py makes them).
LANG = "en"
LANGUAGE_NAMES = [("en", "English"), ("ja", "日本語")]   # the Config screen's language buttons
LABELS = {
    "ja": {
        # title
        "START": "はじめから", "CONTINUE": "つづきから", "EXTRA": "おまけ", "CONFIG": "設定", "EXIT": "終了",
        # the message window's buttons
        "SAVE": "セーブ", "LOAD": "ロード", "BACK": "戻る", "SKIP": "スキップ", "AUTO": "オート", "LOG": "ログ",
        "HIDE": "消す", "Q.SAVE": "Qセーブ", "Q.LOAD": "Qロード",
        # config
        "Config": "設定", "Screen Mode": "画面モード", "Text Speed": "文字速度", "Auto Speed": "オート速度",
        "Effect Speed": "演出速度", "Skip Mode": "スキップ", "Language / 言語": "言語 / Language", "BGM Volume": "BGM 音量",
        "SE Volume": "効果音 音量", "Voice Volume": "ボイス 音量", "Voice Settings": "ボイス設定",
        "Slow": "遅い", "Fast": "速い", "Min": "小", "Max": "大",
        "Click a name to mute or unmute their voice.": "名前をクリックすると消音／解除します。",
        "Each one's volume and a test: page 5.": "音量とテストは 5 ページ。",
        "Ai": "あい", "Pip": "ピップ", "Hiyori": "ひより", "Vee": "ヴィー", "Undo": "前に戻す", "Revert": "すべて戻す",
        "Window": "ウィンドウ", "Full Screen": "フルスクリーン", "Normal": "通常", "Skip": "スキップ",
        "All": "すべて", "Read Only": "既読のみ",
        "Default": "初期設定", "Title": "タイトル", "Return": "戻る", "Controls": "操作方法", "Manual": "マニュアル",
        "Your Name": "名前",
        # save / load
        "Save": "セーブ", "Load": "ロード", "NO DATA": "データなし",
        # Extras
        "CG Mode": "CG モード", "Replay": "回想", "Music": "音楽", "Search": "検索", "CG": "CG", "Glossary": "用語集",
        "Chart": "チャート", "Characters": "キャラクタ",
        "Character 1": "キャラクタ 1", "Character 2": "キャラクタ 2", "Character 3": "キャラクタ 3",
        "Character 4": "キャラクタ 4", "Character 5": "キャラクタ 5", "Other": "その他",
        "Track %02d": "トラック %02d", "Stop": "停止", "Play": "再生", "Repeat": "リピート",
        "Repeat All": "全曲リピート", "Keep on Title": "タイトルでも流す",
        "One": "1曲", "In Order": "全曲", "Shuffle": "ランダム", "Pause": "一時停止",
    },
}


def L(label):
    """a label in the language being drawn"""
    if LANG == "en":
        return label
    table = LABELS[LANG]
    if label not in table:
        raise SystemExit("no %s label for %r (LABELS in make_ui.py)" % (LANG, label))
    return table[label]


def all_labels(lang):
    """every label drawn in a language (subset_fonts.py: the characters its fonts need)"""
    return list(LABELS.get(lang, {}).values()) + [name for _, name in LANGUAGE_NAMES] + ["0123456789"]


def out(name, words=True):
    """where an image goes: data/image in English; in another language, data/lang/<code>/ for
    an image with words on it and nowhere for one without (the English one serves every language)"""
    if LANG == "en":
        return name if os.path.isabs(name) else os.path.join(IMAGE, name)
    if not words:
        return None
    folder = os.path.join(REPO, "data", "lang", LANG)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, os.path.basename(name))


_fonts = {}


def font(weight, size):
    key = (weight, size, LANG)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(font_file(weight, LANG != "en"), int(round(size * SS)))
    return _fonts[key]


def font_file(weight, japanese=False):
    return os.path.join(HERE, "fonts", "NotoSansCJKjp-%s-%s.otf" % (weight, "Japanese" if japanese else "Latin"))


def missing_glyphs(f, s):
    """the characters of s that font f draws as .notdef"""
    from fontTools.ttLib import TTFont
    path = f.path
    if path not in _cmaps:
        _cmaps[path] = TTFont(path).getBestCmap()
    cmap = _cmaps[path]
    return [ch for ch in s if ord(ch) not in cmap and not ch.isspace()]


_cmaps = {}


def glyph_font(f, s):
    """f, or its Japanese subset when the text has a character the Latin one lacks (the
    language buttons' names); stops when neither has it: run subset_fonts.py"""
    if not missing_glyphs(f, s):
        return f
    if f.path.endswith("-Latin.otf"):
        j = ImageFont.truetype(f.path.replace("-Latin.otf", "-Japanese.otf"), f.size)
        if not missing_glyphs(j, s):
            return j
        f = j
    raise SystemExit("%s has no %s: run tools/assets/subset_fonts.py" % (os.path.basename(f.path),
                                                                        "".join(missing_glyphs(f, s))))


def px(v):
    return int(round(v * SS))


# --- drawing ---------------------------------------------------------------------------
class Canvas:
    """An RGBA image drawn at SS times its size. Every shape is drawn on a layer of its own
    and alpha-composited, so translucent shapes blend with what is under them."""

    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.im = Image.new("RGBA", (w * SS, h * SS), bg)

    def comp(self, lay, x, y):
        """composites a layer at SS-pixel position x, y, clipped to the canvas"""
        sx, sy = max(0, -x), max(0, -y)
        x, y = max(0, x), max(0, y)
        w = min(lay.width - sx, self.im.width - x)
        h = min(lay.height - sy, self.im.height - y)
        if w > 0 and h > 0:
            self.im.alpha_composite(lay, (x, y), (sx, sy, sx + w, sy + h))

    def rrect(self, box, r, fill=None, outline=None, width=0):
        x0, y0, x1, y1 = (px(v) for v in box)
        lay = Image.new("RGBA", (x1 - x0, y1 - y0))
        ImageDraw.Draw(lay).rounded_rectangle([0, 0, x1 - x0 - 1, y1 - y0 - 1], radius=px(r), fill=fill,
                                              outline=outline, width=px(width))
        self.comp(lay, x0, y0)

    def panel(self, box, r=14, fill=LAV, border=VIOLET, bw=5, shadow=12, shadow_color=VIOLET):
        """the dialog's panel: a border and a hard shadow down and to the right. The shadow
        is only drawn outside the panel, so a translucent panel doesn't show it through."""
        x0, y0, x1, y1 = box
        if shadow:
            sx0, sy0, sx1, sy1 = (px(v) for v in (x0, y0, x1 + shadow, y1 + shadow))
            lay = Image.new("RGBA", (sx1 - sx0, sy1 - sy0))
            d = ImageDraw.Draw(lay)
            o = px(shadow)
            d.rounded_rectangle([o, o, sx1 - sx0 - 1, sy1 - sy0 - 1], radius=px(r), fill=rgba(shadow_color))
            # cut the panel's own shape out of it (ImageDraw replaces pixels, so this erases)
            d.rounded_rectangle([0, 0, px(x1) - px(x0) - 1, px(y1) - px(y0) - 1], radius=px(r), fill=(0, 0, 0, 0))
            self.comp(lay, sx0, sy0)
        self.rrect(box, r, fill=rgba(fill) if len(fill) == 3 else fill,
                   outline=rgba(border) if border else None, width=bw if border else 0)

    def ellipse(self, box, fill=None, outline=None, width=0):
        x0, y0, x1, y1 = (px(v) for v in box)
        lay = Image.new("RGBA", (x1 - x0, y1 - y0))
        ImageDraw.Draw(lay).ellipse([0, 0, x1 - x0 - 1, y1 - y0 - 1], fill=fill, outline=outline, width=px(width))
        self.comp(lay, x0, y0)

    def polygon(self, pts, fill):
        xs = [px(p[0]) for p in pts]
        ys = [px(p[1]) for p in pts]
        x0, y0 = min(xs) - 2, min(ys) - 2
        lay = Image.new("RGBA", (max(xs) - x0 + 3, max(ys) - y0 + 3))
        ImageDraw.Draw(lay).polygon([(x - x0, y - y0) for x, y in zip(xs, ys)], fill=fill)
        self.comp(lay, x0, y0)

    def stroke(self, pts, width, color, closed=False):
        """a polyline with round joins and caps"""
        if closed:
            pts = list(pts) + [pts[0], pts[1]]
        w = px(width)
        xs = [px(p[0]) for p in pts]
        ys = [px(p[1]) for p in pts]
        x0, y0 = min(xs) - w, min(ys) - w
        lay = Image.new("RGBA", (max(xs) - x0 + w + 1, max(ys) - y0 + w + 1))
        d = ImageDraw.Draw(lay)
        q = [(x - x0, y - y0) for x, y in zip(xs, ys)]
        d.line(q, fill=color, width=w, joint="curve")
        for x, y in q:
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=color)
        self.comp(lay, x0, y0)

    def text(self, xy, s, f, fill, anchor="la", stroke=0, stroke_fill=None, tracking=0, shadow=None):
        """text at 1x position xy; tracking adds space between letters; shadow=(dx, dy, colour)
        draws a hard copy behind it (with the same stroke)"""
        if shadow:
            dx, dy, col = shadow
            self.text((xy[0] + dx, xy[1] + dy), s, f, col, anchor, stroke, col, tracking)
        f = glyph_font(f, s)
        x, y = px(xy[0]), px(xy[1])
        sw = px(stroke)
        tr = px(tracking)
        widths = [f.getlength(ch) for ch in s]
        total = sum(widths) + tr * (len(s) - 1)
        h_anchor, v_anchor = anchor[0], anchor[1]
        if h_anchor == "m":
            x -= total / 2
        elif h_anchor == "r":
            x -= total
        a = "l" + v_anchor
        tmp = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        boxes = []
        cx = x
        for ch, w in zip(s, widths):
            boxes.append(tmp.textbbox((cx, y), ch, font=f, anchor=a, stroke_width=sw))
            cx += w + tr
        bx0 = int(min(b[0] for b in boxes)) - 2
        by0 = int(min(b[1] for b in boxes)) - 2
        bx1 = int(max(b[2] for b in boxes)) + 2
        by1 = int(max(b[3] for b in boxes)) + 2
        lay = Image.new("RGBA", (bx1 - bx0, by1 - by0))
        d = ImageDraw.Draw(lay)
        # outlines first, then the letters, so a letter's outline never covers its neighbour
        for pass_sw, pass_fill in (((sw, stroke_fill),) if stroke else ()) + ((0, fill),):
            cx = x
            for ch, w in zip(s, widths):
                d.text((cx - bx0, y - by0), ch, font=f, fill=pass_fill, anchor=a, stroke_width=pass_sw,
                       stroke_fill=pass_fill)
                cx += w + tr
        self.comp(lay, bx0, by0)

    def text_width(self, s, f, tracking=0):
        f = glyph_font(f, s)
        return (sum(f.getlength(ch) for ch in s) + px(tracking) * (len(s) - 1)) / SS

    def pattern(self, box, spacing, r, color, fade=False):
        """a grid of dots, offset every other row; fade thins them out to the right"""
        x0, y0, x1, y1 = (px(v) for v in box)
        sp = px(spacing)
        tile = Image.new("RGBA", (sp, sp * 2))
        d = ImageDraw.Draw(tile)
        rr = px(r)
        for cx, cy in ((sp / 2, sp / 2), (0, sp * 1.5), (sp, sp * 1.5)):
            d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=color)
        t = np.asarray(tile)
        reps = ((y1 - y0) // t.shape[0] + 1, (x1 - x0) // t.shape[1] + 1, 1)
        full = np.tile(t, reps)[: y1 - y0, : x1 - x0]
        if fade:
            k = np.linspace(1, 0, x1 - x0, dtype=np.float32)
            k = k * k * (3 - 2 * k)
            full = full.copy()
            full[:, :, 3] = (full[:, :, 3] * k[None, :] + 0.5).astype(np.uint8)
        self.comp(Image.fromarray(np.ascontiguousarray(full), "RGBA"), x0, y0)

    def gradient(self, box, c0, c1, horizontal=False, ease=False, clip=None):
        """a linear gradient between two RGBA colours; clip=(box, radius) keeps it inside a
        rounded rectangle"""
        x0, y0, x1, y1 = (px(v) for v in box)
        n = (x1 - x0) if horizontal else (y1 - y0)
        t = np.linspace(0, 1, n, dtype=np.float32)
        if ease:
            t = t * t * (3 - 2 * t)
        cols = np.array(c0, np.float32)[None] * (1 - t[:, None]) + np.array(c1, np.float32)[None] * t[:, None]
        cols = (cols + 0.5).astype(np.uint8)
        if horizontal:
            arr = np.broadcast_to(cols[None, :, :], (y1 - y0, n, 4))
        else:
            arr = np.broadcast_to(cols[:, None, :], (n, x1 - x0, 4))
        arr = np.ascontiguousarray(arr)
        if clip:
            (cx0, cy0, cx1, cy1), r = clip
            mask = Image.new("L", (x1 - x0, y1 - y0))
            ImageDraw.Draw(mask).rounded_rectangle([px(cx0) - x0, px(cy0) - y0, px(cx1) - x0 - 1, px(cy1) - y0 - 1],
                                                   radius=px(r), fill=255)
            arr[:, :, 3] = (arr[:, :, 3].astype(np.uint16) * np.asarray(mask) // 255).astype(np.uint8)
        self.comp(Image.fromarray(arr, "RGBA"), x0, y0)

    def paste(self, other, x, y):
        """composites another Canvas at 1x position x, y"""
        self.comp(other.im, px(x), px(y))

    def image(self):
        """averages the SS x SS blocks down to 1x, in premultiplied alpha"""
        rows = []
        h, w = self.h, self.w
        src = np.asarray(self.im)
        step = 64
        for y in range(0, h, step):
            yy = min(h, y + step)
            a = src[y * SS: yy * SS].astype(np.float32)
            al = a[:, :, 3:4] / 255
            pre = np.concatenate([a[:, :, :3] * al, al], 2)
            pre = pre.reshape(yy - y, SS, w, SS, 4).mean((1, 3))
            al = pre[:, :, 3:4]
            rgb = np.where(al > 0, pre[:, :, :3] / np.maximum(al, 1e-6), 0)
            rows.append(np.concatenate([rgb, al * 255], 2))
        return Image.fromarray(np.clip(np.concatenate(rows, 0) + 0.5, 0, 255).astype(np.uint8), "RGBA")

    def save(self, path, opaque=False, under=None):
        if path is None:  # an image without words, drawn for another language (out())
            return
        img = self.image()
        if under is not None:
            base = under.convert("RGBA")
            base.alpha_composite(img)
            img = base
        if opaque:
            img = img.convert("RGB")
        img.save(path, optimize=True)
        print("wrote", os.path.relpath(path, REPO), img.size, flush=True)


# --- components ------------------------------------------------------------------------
# a button's look per state: fill, border, label colour, shadow colour
STYLE = {
    "normal": (rgba(WHITE), VIOLET, VIOLET, VIOLET),
    "over": (rgba(VIOLET), VIOLET, WHITE, NAVY),
    "on": (rgba(DEEP), VIOLET, WHITE, NAVY),
    "muted": (rgba(WHITE, 200), LAV, LAV, LAV),
}


def button(w, h, label, state, size=28, weight="Bold", r=10, bw=4, shadow=0, tracking=0,
           icon=None, icon_size=None, label_dx=0):
    """a button image w x h (any shadow included); icon(c, cx, cy, size, colour) draws a
    symbol left of the label"""
    fill, border, fg, sh = STYLE[state]
    c = Canvas(w, h)
    c.panel((0, 0, w - shadow, h - shadow), r=r, fill=fill, border=border, bw=bw, shadow=shadow,
            shadow_color=sh)
    f = font(weight, size)
    cx = (w - shadow) / 2 + label_dx
    cy = (h - shadow) / 2
    if icon:
        isz = icon_size or size * 0.7
        tw = c.text_width(label, f, tracking) if label else 0
        gap = size * 0.4 if label else 0
        left = cx - (isz + gap + tw) / 2
        icon(c, left + isz / 2, cy, isz, rgba(fg))
        cx = left + isz + gap + tw / 2
    if label:
        c.text((cx, cy), label, f, rgba(fg), anchor="mm", tracking=tracking)
    return c


def save_states(name_fmt, states, make, folder=IMAGE):
    for st in states:
        make(st).save(os.path.join(folder, name_fmt % st))


def header(c, title, x=290, y=150):
    """a screen's title and the rule under it"""
    c.text((x, y), title, font("Black", 84), rgba(VIOLET), anchor="ls", shadow=(6, 6, rgba(LAV)))
    c.rrect((x, 170, 1630, 176), 3, fill=rgba(VIOLET))


def screen_bg(c, alpha=255):
    c.rrect((0, 0, c.w, c.h), 0, fill=rgba(LAV_PALE, alpha))
    c.pattern((0, 0, c.w, c.h), 36, 2.2, rgba(LAV, 90 if alpha == 255 else 110))


def outlined(c, xy, s, size, weight="Bold", anchor="la", fill=WHITE, stroke=4, stroke_fill=NAVY, tracking=1):
    """white text with a navy outline, like the dialog's message"""
    c.text(xy, s, font(weight, size), rgba(fill), anchor=anchor, stroke=stroke, stroke_fill=rgba(stroke_fill),
           tracking=tracking)


# icons, centred on cx, cy within size
def ic_play(c, cx, cy, s, col):
    c.polygon([(cx - s * 0.36, cy - s * 0.46), (cx + s * 0.5, cy), (cx - s * 0.36, cy + s * 0.46)], col)


def ic_stop(c, cx, cy, s, col):
    c.rrect((cx - s * 0.38, cy - s * 0.38, cx + s * 0.38, cy + s * 0.38), s * 0.08, fill=col)


def ic_note(c, cx, cy, s, col):
    c.text((cx, cy + s * 0.05), "♪", font("Black", s * 1.15), col, anchor="mm")


def ic_pause(c, cx, cy, s, col):
    for dx in (-0.22, 0.22):
        c.rrect((cx + s * (dx - 0.12), cy - s * 0.38, cx + s * (dx + 0.12), cy + s * 0.38), s * 0.05, fill=col)


def ic_shuffle(c, cx, cy, s, col):
    """two crossing arrows: tracks in no order"""
    x0, x1 = cx - s * 0.5, cx + s * 0.3
    for y0, y1 in ((-0.3, 0.3), (0.3, -0.3)):
        pts = [(x0 + (x1 - x0) * t, cy + s * (y0 + (y1 - y0) * (3 * t * t - 2 * t * t * t))) for t in np.linspace(0, 1, 16)]
        c.stroke(pts, s * 0.1, col)
        ey = cy + s * y1
        c.polygon([(x1 - s * 0.04, ey - s * 0.17), (x1 + s * 0.22, ey), (x1 - s * 0.04, ey + s * 0.17)], col)


def ic_repeat_one(c, cx, cy, s, col):
    ic_repeat(c, cx, cy, s, col)
    c.text((cx, cy + s * 0.02), "1", font("Black", s * 0.5), col, anchor="mm")


def ic_repeat(c, cx, cy, s, col):
    r = s * 0.42
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(math.radians(-60), math.radians(230), 24)]
    c.stroke(pts, s * 0.12, col)
    ex, ey = pts[0]
    c.polygon([(ex - s * 0.2, ey - s * 0.08), (ex + s * 0.13, ey - s * 0.1), (ex + s * 0.02, ey + s * 0.22)], col)


def ic_back(c, cx, cy, s, col):
    """an arrow curving back over the top: going back to an earlier line"""
    r = s * 0.36
    ox, oy = cx + s * 0.04, cy + s * 0.08
    pts = [(ox + r * math.cos(a), oy + r * math.sin(a)) for a in np.linspace(math.radians(40), math.radians(-180), 28)]
    c.stroke(pts, s * 0.12, col)
    ex, ey = pts[-1]
    c.polygon([(ex - s * 0.2, ey - s * 0.04), (ex + s * 0.2, ey - s * 0.04), (ex, ey + s * 0.24)], col)


def tri(c, cx, cy, s, col, left):
    """a triangle pointing left or right, s high"""
    d = -1 if left else 1
    c.polygon([(cx - d * s * 0.3, cy - s * 0.5), (cx + d * s * 0.36, cy), (cx - d * s * 0.3, cy + s * 0.5)], col)


def ic_rewind(c, cx, cy, s, col):
    """two triangles pointing back: rewind to the scene's start or the last choice"""
    tri(c, cx - s * 0.3, cy, s * 0.8, col, True)
    tri(c, cx + s * 0.3, cy, s * 0.8, col, True)


def ic_prevscene(c, cx, cy, s, col):
    """a bar and a triangle pointing back: the start of the scene before"""
    c.rrect((cx - s * 0.5, cy - s * 0.42, cx - s * 0.3, cy + s * 0.42), s * 0.04, fill=col)
    tri(c, cx + s * 0.12, cy, s * 0.84, col, True)


def ic_nextscene(c, cx, cy, s, col):
    """a triangle pointing on and a bar: skip to the next scene"""
    tri(c, cx - s * 0.12, cy, s * 0.84, col, False)
    c.rrect((cx + s * 0.3, cy - s * 0.42, cx + s * 0.5, cy + s * 0.42), s * 0.04, fill=col)


def ic_prevchoice(c, cx, cy, s, col):
    """a branch (a choice) with a triangle pointing back: the last choice again"""
    tri(c, cx - s * 0.3, cy, s * 0.7, col, True)
    x0, y0 = cx + s * 0.05, cy
    c.stroke([(x0, y0), (cx + s * 0.5, cy - s * 0.38)], s * 0.12, col)
    c.stroke([(x0, y0), (cx + s * 0.5, cy + s * 0.38)], s * 0.12, col)
    c.ellipse((x0 - s * 0.1, y0 - s * 0.1, x0 + s * 0.1, y0 + s * 0.1), fill=col)


def ic_skip(c, cx, cy, s, col):
    """two triangles pointing on: skipping (rewind's mirror)"""
    tri(c, cx - s * 0.3, cy, s * 0.8, col, False)
    tri(c, cx + s * 0.3, cy, s * 0.8, col, False)


def ic_auto(c, cx, cy, s, col):
    """a play triangle in a circling arrow: the text going on by itself"""
    r = s * 0.48
    pts = [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(math.radians(-50), math.radians(250), 30)]
    c.stroke(pts, s * 0.1, col)
    ex, ey = pts[0]
    c.polygon([(ex - s * 0.2, ey - s * 0.12), (ex + s * 0.14, ey - s * 0.12), (ex + s * 0.02, ey + s * 0.2)], col)
    c.polygon([(cx - s * 0.13, cy - s * 0.22), (cx + s * 0.22, cy), (cx - s * 0.13, cy + s * 0.22)], col)


def ic_log(c, cx, cy, s, col):
    """lines of text, the last one short: the message history"""
    for i, (y, w) in enumerate(((-0.34, 0.92), (-0.11, 0.92), (0.12, 0.92), (0.35, 0.56))):
        x0 = cx - s * 0.46
        c.rrect((x0, cy + s * (y - 0.06), x0 + s * w, cy + s * (y + 0.06)), s * 0.05, fill=col)


def ic_config(c, cx, cy, s, col):
    """a cog: the settings"""
    teeth = 8
    for k in range(teeth):
        a = 2 * math.pi * k / teeth
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for (r, t) in ((0.3, -0.13), (0.52, -0.09), (0.52, 0.09), (0.3, 0.13)):
            # t is sideways (along the tangent), r out from the centre
            pts.append((cx + s * (r * ca - t * sa), cy + s * (r * sa + t * ca)))
        c.polygon(pts, col)
    c.ellipse((cx - s * 0.36, cy - s * 0.36, cx + s * 0.36, cy + s * 0.36), outline=col, width=s * 0.17)


def ic_camera(c, cx, cy, s, col):
    """a camera, in outline: a screenshot"""
    c.rrect((cx - s * 0.2, cy - s * 0.42, cx + s * 0.2, cy - s * 0.2), s * 0.05, fill=col)
    c.rrect((cx - s * 0.52, cy - s * 0.26, cx + s * 0.52, cy + s * 0.42), s * 0.12, outline=col, width=s * 0.1)
    c.ellipse((cx - s * 0.2, cy - s * 0.12, cx + s * 0.2, cy + s * 0.28), outline=col, width=s * 0.1)


def ic_close(c, cx, cy, s, col):
    """a cross: closing a screen"""
    r = s * 0.36
    c.stroke([(cx - r, cy - r), (cx + r, cy + r)], s * 0.14, col)
    c.stroke([(cx - r, cy + r), (cx + r, cy - r)], s * 0.14, col)


def ic_plus(c, cx, cy, s, col):
    r = s * 0.38
    c.stroke([(cx - r, cy), (cx + r, cy)], s * 0.14, col)
    c.stroke([(cx, cy - r), (cx, cy + r)], s * 0.14, col)


def ic_minus(c, cx, cy, s, col):
    r = s * 0.38
    c.stroke([(cx - r, cy), (cx + r, cy)], s * 0.14, col)


def ic_here(c, cx, cy, s, col):
    """a ring round a dot, with ticks: where the story is"""
    r = s * 0.3
    c.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=s * 0.1)
    c.ellipse((cx - s * 0.11, cy - s * 0.11, cx + s * 0.11, cy + s * 0.11), fill=col)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        c.stroke([(cx + dx * s * 0.34, cy + dy * s * 0.34), (cx + dx * s * 0.5, cy + dy * s * 0.5)], s * 0.1, col)


def ic_person(c, cx, cy, s, col):
    """a head and shoulders: a character"""
    c.ellipse((cx - s * 0.17, cy - s * 0.46, cx + s * 0.17, cy - s * 0.12), fill=col)
    c.rrect((cx - s * 0.36, cy - s * 0.04, cx + s * 0.36, cy + s * 0.46), s * 0.18, fill=col)


def ic_person_plus(c, cx, cy, s, col):
    """a character with a plus: onto the stage"""
    ic_person(c, cx - s * 0.14, cy + s * 0.04, s * 0.92, col)
    r = s * 0.16
    c.stroke([(cx + s * 0.36 - r, cy - s * 0.3), (cx + s * 0.36 + r, cy - s * 0.3)], s * 0.1, col)
    c.stroke([(cx + s * 0.36, cy - s * 0.3 - r), (cx + s * 0.36, cy - s * 0.3 + r)], s * 0.1, col)


def ic_person_minus(c, cx, cy, s, col):
    """a character with a minus: off the stage"""
    ic_person(c, cx - s * 0.14, cy + s * 0.04, s * 0.92, col)
    r = s * 0.16
    c.stroke([(cx + s * 0.36 - r, cy - s * 0.3), (cx + s * 0.36 + r, cy - s * 0.3)], s * 0.1, col)


def ic_flip(c, cx, cy, s, col):
    """two triangles either side of a dashed line: turned round"""
    c.polygon([(cx - s * 0.1, cy - s * 0.36), (cx - s * 0.1, cy + s * 0.36), (cx - s * 0.52, cy + s * 0.36)], col)
    c.polygon([(cx + s * 0.1, cy - s * 0.36), (cx + s * 0.1, cy + s * 0.36), (cx + s * 0.52, cy + s * 0.36)], col)
    for y in (-0.5, -0.24, 0.02, 0.28):
        c.rrect((cx - s * 0.03, cy + s * y, cx + s * 0.03, cy + s * (y + 0.14)), s * 0.02, fill=col)


def ic_hide_panel(c, cx, cy, s, col):
    """two chevrons pointing left: the panel away"""
    for o in (-0.16, 0.16):
        x = cx + s * o
        c.stroke([(x + s * 0.14, cy - s * 0.34), (x - s * 0.14, cy), (x + s * 0.14, cy + s * 0.34)], s * 0.12, col)


def ic_show_panel(c, cx, cy, s, col):
    """two chevrons pointing right: the panel back"""
    for o in (-0.16, 0.16):
        x = cx + s * o
        c.stroke([(x - s * 0.14, cy - s * 0.34), (x + s * 0.14, cy), (x - s * 0.14, cy + s * 0.34)], s * 0.12, col)


def ic_dot(c, cx, cy, s, col):
    c.ellipse((cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), fill=col)


def ic_ring(c, cx, cy, s, col):
    c.ellipse((cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), outline=col, width=s * 0.2)


def chevron(c, cx, cy, s, col, up, double=False):
    dy = -1 if up else 1
    offs = (-s * 0.16, s * 0.16) if double else (0,)
    for o in offs:
        y = cy + o
        c.stroke([(cx - s * 0.36, y - dy * s * 0.18), (cx, y + dy * s * 0.18), (cx + s * 0.36, y - dy * s * 0.18)],
                 s * 0.13, col)


# --- the title screen and the logo -----------------------------------------------------
def wordmark(c, x, y, size, anchor="ls"):
    """'KAGEX' in white with a violet outline and hard shadow"""
    f = font("Black", size)
    o = size * 0.055
    c.text((x + size * 0.07, y + size * 0.07), "KAGEX", f, rgba(VIOLET), anchor=anchor, stroke=o,
           stroke_fill=rgba(VIOLET), tracking=size * 0.02)
    c.text((x, y), "KAGEX", f, rgba(WHITE), anchor=anchor, stroke=o, stroke_fill=rgba(VIOLET), tracking=size * 0.02)


def emblem(c, x, y, s):
    """the K badge"""
    c.panel((x, y, x + s, y + s), r=s * 0.2, fill=VIOLET, border=WHITE, bw=s * 0.045, shadow=s * 0.07,
            shadow_color=NAVY)
    c.text((x + s / 2, y + s * 0.52), "K", font("Black", s * 0.74), rgba(WHITE), anchor="mm")


TITLE_BUTTONS = [("start", "START"), ("continue", "CONTINUE"), ("extra", "EXTRA"), ("config", "CONFIG"),
                 ("exit", "EXIT")]


def make_title():
    bg = Image.open(os.path.join(REPO, "data", "bgimage", "bg01_01.png")).convert("RGBA")
    ch = Image.open(os.path.join(REPO, "data", "fgimage", "ch_0_0_1.png")).convert("RGBA")
    under = bg.copy()
    # the character on the right, cut off at the thighs
    under.alpha_composite(ch, (1200, 60))
    c = Canvas(1920, 1080)
    # a lavender wash over the left half, for the logo and the menu
    c.gradient((0, 0, 1240, 1080), rgba(LAV_PALE, 245), rgba(LAV_PALE, 0), horizontal=True, ease=True)
    c.pattern((0, 0, 1240, 1080), 36, 2.2, rgba(LAV, 90), fade=True)
    wordmark(c, 150, 330, 190)
    c.text((160, 430), "Sample", font("Black", 66), rgba(VIOLET), anchor="ls", stroke=5,
           stroke_fill=rgba(WHITE), tracking=2)
    c.text((440, 428), "for Kirikiri Z · SDL3", font("Bold", 30), rgba(INK), anchor="ls")
    c.save(out("title.png", False), opaque=True, under=under)

    for name, label in TITLE_BUTTONS:
        for st in ("normal", "over"):
            button(400, 68, L(label), st, size=30, weight="Black", r=12, shadow=8, tracking=4).save(
                out("%s_%s.png" % (name, st)))

    make_title_evening(bg, ch)
    # the arrows that pick the title's picture once there's more than one (title.ks)
    for st in ("normal", "over"):
        for name, left in (("prev", True), ("next", False)):
            fill, border, fg, sh = STYLE[st]
            b = Canvas(72, 72)
            b.panel((0, 0, 66, 66), r=12, fill=fill, border=border, bw=4, shadow=6, shadow_color=sh)
            d = -1 if left else 1
            b.stroke([(33 - d * 6, 21), (33 + d * 6, 33), (33 - d * 6, 45)], 4.5, rgba(fg))
            b.save(out("title_%s_%s.png" % (name, st), False))


def make_title_evening(bg, ch):
    """the second title picture, which finishing every demo unlocks (sf.clear): the same street
    at sunset, with stars coming out"""
    a = np.asarray(bg.convert("RGB")).astype(np.float32) / 255
    h, w = a.shape[:2]
    y = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    lum = (a @ np.array([0.3, 0.59, 0.11], np.float32))[..., None]
    sky = np.array([0.42, 0.30, 0.78], np.float32) * (1 - y) + np.array([1.0, 0.60, 0.42], np.float32) * y
    graded = np.clip((a * 0.35 + lum * 0.65) * sky * 1.12, 0, 1)
    under = Image.fromarray((graded * 255 + 0.5).astype(np.uint8), "RGB").convert("RGBA")
    # a few stars over the street's far end, where the sky shows
    star = Image.open(os.path.join(REPO, "data", "fgimage", "star.png")).convert("RGBA")
    for sx, sy, size, alpha in ((1010, 70, 54, 230), (1130, 170, 34, 200), (880, 210, 26, 170),
                                (1720, 90, 40, 210), (1580, 40, 24, 160), (1820, 260, 30, 180)):
        s = star.resize((size, size), Image.LANCZOS)
        s.putalpha(s.getchannel("A").point(lambda v, k=alpha: v * k // 255))
        under.alpha_composite(s, (sx - size // 2, sy - size // 2))
    # Ai in the evening light
    c_arr = np.asarray(ch).astype(np.float32)
    c_arr[..., :3] *= np.array([1.0, 0.86, 0.80], np.float32)
    under.alpha_composite(Image.fromarray(np.clip(c_arr + 0.5, 0, 255).astype(np.uint8), "RGBA"), (1200, 60))
    c = Canvas(1920, 1080)
    c.gradient((0, 0, 1240, 1080), rgba(DEEP, 215), rgba(DEEP, 0), horizontal=True, ease=True)
    c.pattern((0, 0, 1240, 1080), 36, 2.2, rgba(LAV, 60), fade=True)
    wordmark(c, 150, 330, 190)
    c.text((160, 430), "Sample", font("Black", 66), rgba(WHITE), anchor="ls", stroke=5,
           stroke_fill=rgba(VIOLET), tracking=2)
    c.text((440, 428), "for Kirikiri Z · SDL3", font("Bold", 30), rgba(LAV_SOFT), anchor="ls")
    c.save(out("title_evening.png", False), opaque=True, under=under)


def make_logo():
    c = Canvas(1920, 1080)
    screen_bg(c)
    s = 200
    gap = 48
    f = font("Black", 168)
    ww = c.text_width("KAGEX", f, 168 * 0.02)
    x0 = (1920 - (s + gap + ww)) / 2
    emblem(c, x0, 430, s)
    wordmark(c, x0 + s + gap, 600, 168)
    c.text((960, 730), "A KAG3 extension for Kirikiri Z", font("Bold", 36), rgba(INK), anchor="ms")
    c.save(out("logo.png", False), opaque=True)

    # about.ks's 400x200 window (only with aboutInWindow = false); the text goes bottom right
    c = Canvas(400, 200)
    c.rrect((0, 0, 400, 200), 0, fill=rgba(LAV_PALE))
    emblem(c, 24, 22, 76)
    wordmark(c, 118, 90, 60)
    c.save(out("about_logo.png", False), opaque=True)


# --- the message window ----------------------------------------------------------------
MSG_BUTTONS = ["save", "load", "exit", "hide", "qsave", "qload"]
MSG_LABELS = {"qsave": "Q.SAVE", "qload": "Q.LOAD"}   # the others' are their names in capitals
# the quick menu's other buttons are icons (since 0.20.0), so no language needs its own
MSG_ICONS = (("rewind", ic_rewind), ("prevscene", ic_prevscene), ("prevchoice", ic_prevchoice),
             ("nextscene", ic_nextscene), ("back", ic_back), ("skip", ic_skip), ("auto", ic_auto),
             ("log", ic_log), ("config", ic_config), ("screenshot", ic_camera))


def make_message():
    w, h = 1800, 330
    c = Canvas(w, h)
    c.panel((0, 0, w - 12, h - 12), r=18, fill=rgba(LAV, 228), border=VIOLET, bw=5, shadow=12)
    # a highlight along the top, inside the border (its inner edge is rounded too: 18 - 5)
    c.gradient((5, 5, w - 17, 90), (255, 255, 255, 60), (255, 255, 255, 0), clip=((5, 5, w - 17, h - 17), 13))
    c.save(out("messagewindow.png", False))

    # the speaker's name, behind NameLayer's text ([position nameframe=namebox])
    c = Canvas(300, 64)
    c.panel((0, 0, 292, 56), r=14, fill=VIOLET, border=WHITE, bw=4, shadow=8, shadow_color=NAVY)
    c.save(out("namebox.png", False))

    # the "memory" window style (MessageStyles.tjs, AfterInit.tjs; [env msgstyle=memory]):
    # the same shapes in sepia, for flashbacks
    sepia_fill, sepia_border, sepia_dark = (238, 226, 204), (128, 96, 62), (84, 60, 34)
    c = Canvas(w, h)
    c.panel((0, 0, w - 12, h - 12), r=18, fill=rgba(sepia_dark, 214), border=sepia_border, bw=5, shadow=12,
            shadow_color=sepia_dark)
    c.gradient((5, 5, w - 17, 90), (255, 236, 200, 50), (255, 236, 200, 0), clip=((5, 5, w - 17, h - 17), 13))
    c.save(out("messagewindow_memory.png", False))
    c = Canvas(300, 64)
    c.panel((0, 0, 292, 56), r=14, fill=sepia_border, border=sepia_fill, bw=4, shadow=8, shadow_color=sepia_dark)
    c.save(out("namebox_memory.png", False))

    # bars over the scene, for the [letterbox] macro (macro.ks): black, 110 px top and bottom
    if LANG == "en":
        img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rectangle((0, 0, 1919, 109), fill=(0, 0, 0, 255))
        d.rectangle((0, 970, 1919, 1079), fill=(0, 0, 0, 255))
        img.save(out("letterbox.png", False))
        # a soft sepia edge round the scene, for the [memoryframe] macro: clear in the middle
        yy, xx = np.mgrid[0:1080, 0:1920].astype(np.float64)
        dx, dy = (xx - 959.5) / 960, (yy - 539.5) / 540
        r = np.sqrt(dx * dx * 0.85 + dy * dy)
        a = np.clip((r - 0.62) / 0.5, 0, 1) ** 1.6 * 200
        rgba_ = np.zeros((1080, 1920, 4), np.uint8)
        rgba_[..., 0], rgba_[..., 1], rgba_[..., 2] = 74, 52, 28
        rgba_[..., 3] = a.round().astype(np.uint8)
        Image.fromarray(rgba_, "RGBA").save(out("memoryframe.png", False))

    for name in MSG_BUTTONS:
        for st in ("normal", "over"):
            button(100, 42, L(MSG_LABELS.get(name, name.upper())), st, size=19, r=10, bw=3, tracking=1.5).save(
                out("msg_%s_%s.png" % (name, st)))
    for name, icon in MSG_ICONS:
        for st in ("normal", "over"):
            button(42, 42, "", st, r=10, bw=3, icon=icon, icon_size=22).save(out("msg_%s_%s.png" % (name, st), False))
    for name in ("auto", "skip"):  # latched while auto mode / skipping is on
        button(42, 42, "", "on", r=10, bw=3, icon=dict(MSG_ICONS)[name], icon_size=22).save(
            out("msg_%s_on.png" % name, False))

    # the choices ([selopt] in first.ks)
    for st, fill, border, sh in (("normal", rgba(LAV, 238), VIOLET, VIOLET), ("over", rgba(VIOLET), WHITE, NAVY)):
        c = Canvas(900, 74)
        c.panel((0, 0, 892, 66), r=16, fill=fill, border=border, bw=4, shadow=8, shadow_color=sh)
        c.save(out("select_%s.png" % st, False))

    # click-wait glyphs: 43x43 cells, 16 frames that the .asd plays forwards and back
    for name, direction in (("LineBreak", "down"), ("PageBreak", "right")):
        frames = Canvas(43 * 16, 43)
        for i in range(16):
            t = i / 15
            e = math.sin(t * math.pi / 2)
            frames.paste(break_glyph(direction, e), 43 * i, 0)
        frames.save(out(os.path.join(SYSTEM, name + "_a.png"), False))
        break_glyph(direction, 1.0).save(out(os.path.join(SYSTEM, name + ".png"), False))
        # the same for text read before (kag.readMark; MessageLayer.readGlyph): lavender
        frames = Canvas(43 * 16, 43)
        for i in range(16):
            frames.paste(break_glyph(direction, math.sin(i / 15 * math.pi / 2), read=True), 43 * i, 0)
        frames.save(out(os.path.join(SYSTEM, name + "_read_a.png"), False))
        break_glyph(direction, 1.0, read=True).save(out(os.path.join(SYSTEM, name + "_read.png"), False))


def break_glyph(direction, e, read=False):
    """a white triangle with a violet outline, fading in and moving 5 px as e goes 0 -> 1
    (lavender for text read before)"""
    c = Canvas(43, 43)
    a = int(255 * (0.3 + 0.7 * e))
    m = 5 * e
    if direction == "down":
        pts = [(9, 11 + m), (34, 11 + m), (21.5, 27 + m)]
    else:
        pts = [(13 + m, 8.5), (13 + m, 33.5), (29 + m, 21)]
    c.stroke(pts, 6, rgba(VIOLET, a), closed=True)
    c.polygon(pts, rgba(LAV if read else WHITE, a))
    return c


# --- config ----------------------------------------------------------------------------
# six rows of 130 a column (config.ks: a row's buttons at its top + 60, a slider at top + 60 and
# its track's centre at top + 90); the right column's last three rows are the voice buttons
CFG_L, CFG_R, CFG_TOP, CFG_ROW, CFG_W = 290, 990, 206, 130, 640


def make_config():
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, L("Config"))
    left = ["Screen Mode", "Text Speed", "Auto Speed", "Effect Speed", "Skip Mode", "Language / 言語"]
    right = ["BGM Volume", "SE Volume", "Voice Volume", "Voice Settings"]
    sliders = {(CFG_L, 1): ("Slow", "Fast"), (CFG_L, 2): ("Slow", "Fast"),
               (CFG_R, 0): ("Min", "Max"), (CFG_R, 1): ("Min", "Max"), (CFG_R, 2): ("Min", "Max")}
    bottom = CFG_TOP + CFG_ROW * 6
    for x0, labels in ((CFG_L, left), (CFG_R, right)):
        c.panel((x0, CFG_TOP, x0 + CFG_W, bottom))
        for i, label in enumerate(labels):
            top = CFG_TOP + CFG_ROW * i
            if i:
                c.rrect((x0 + 24, top - 1, x0 + CFG_W - 24, top + 1), 1, fill=rgba(WHITE, 120))
            outlined(c, (x0 + 32, top + 8), L(label), 33)
            if (x0, i) in sliders:
                lo, hi = sliders[(x0, i)]
                sx, cy = x0 + 112, top + 90
                outlined(c, (sx - 12, cy), L(lo), 26, anchor="rm", stroke=2.5)
                outlined(c, (sx + 416 + 12, cy), L(hi), 26, anchor="lm", stroke=2.5)
                # the slider's tab centre travels from sx + 15 to sx + 416 - 15 (SliderLayer)
                c.rrect((sx + 6, cy - 7, sx + 410, cy + 7), 7, fill=rgba(WHITE), outline=rgba(VIOLET), width=3)
    outlined(c, (CFG_R + 32, CFG_TOP + CFG_ROW * 3 + 220), L("Click a name to mute or unmute their voice."), 26,
             stroke=2.5)
    outlined(c, (CFG_R + 32, CFG_TOP + CFG_ROW * 3 + 264), L("Each one's volume and a test: page 5."), 26,
             stroke=2.5)
    c.save(out("config_base.png"), opaque=True)

    # the slider's tab
    for st, fill, border in (("", WHITE, VIOLET), ("_over", VIOLET, WHITE)):
        t = Canvas(30, 44)
        t.rrect((0, 0, 30, 44), 10, fill=rgba(border))
        t.rrect((4, 4, 26, 40), 7, fill=rgba(fill))
        t.save(out("slidebar%s.png" % st, False))

    toggles = [("window", "Window"), ("fullscreen", "Full Screen"), ("effecton", "Normal"), ("effectoff", "Skip"),
               ("skipall", "All"), ("skipalrdy", "Read Only")]
    for name, label in toggles:
        for st in ("normal", "over"):
            button(240, 60, L(label), st, size=28).save(out("config_%s_%s.png" % (name, st)))
    # a language's button says its name in that language, the same in every language
    for code, label in LANGUAGE_NAMES:
        for st in ("normal", "over"):
            button(240, 60, label, st, size=28).save(out("config_lang_%s_%s.png" % (code, st), False))
    # the voices' switches, a character's each (envinit.tjs's voiceName voice0 to voice3)
    for i, name in enumerate(("Ai", "Pip", "Hiyori", "Vee")):
        button(180, 60, L(name), "over", size=26, icon=ic_dot, icon_size=14).save(
            out("config_voice%d_on.png" % i))
        button(180, 60, L(name), "muted", size=26, icon=ic_ring, icon_size=14).save(
            out("config_voice%d_off.png" % i))
    for name, label in (("config_initial", "Default"), ("config_title", "Title"), ("return", "Return"),
                        ("config_controls", "Controls"), ("config_undo", "Undo"), ("config_revert", "Revert"),
                        ("config_manual", "Manual")):
        for st in ("normal", "over"):
            nav_button(L(label), st).save(out("%s_%s.png" % (name, st)))
    make_config_pages()


# the pages of options (config.ks *options: pages 2 to 4): two empty panels of six rows; the
# rows' titles, buttons' labels and dividers are drawn at run time from the options table
# (template/system/Options.tjs), on blank buttons and the slider's track
def make_config_pages():
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, L("Config"))
    for x0 in (CFG_L, CFG_R):
        c.panel((x0, CFG_TOP, x0 + CFG_W, CFG_TOP + CFG_ROW * 6))
    c.save(out("config_pages_base.png"), opaque=True)
    # the hero's name (namescreen.ks): one wide panel; its titles, fields and buttons are drawn
    # at run time (Override.tjs, nameInit)
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, L("Your Name"))
    c.panel((CFG_L, CFG_TOP, CFG_R + CFG_W, CFG_TOP + CFG_ROW * 3))
    c.save(out("name_base.png"), opaque=True)
    if LANG != "en":
        return
    # Config's page tabs (config.ks), narrower than the save screens' page buttons: nine 50 wide,
    # 52 apart from x 584, end at 1050, before Default (1070 when Config opens from the story)
    for i in range(1, 10):
        for st in ("normal", "over"):
            button(50, 64, str(i), st, size=28, weight="Black", r=10, bw=3).save(
                out("config_tab%d_%s.png" % (i, st), False))
    for w in (240, 180, 130):
        for st in ("normal", "over"):
            button(w, 60, "", st).save(out("config_choice%d_%s.png" % (w, st), False))
    # the slider's track (Options.tjs draws it under a slider), as page 1's
    t = Canvas(416, 20)
    t.rrect((6, 3, 410, 17), 7, fill=rgba(WHITE), outline=rgba(VIOLET), width=3)
    t.save(out("config_track.png", False))


def nav_button(label, st, w=180, size=28):
    return button(w, 64, label, st, size=size, weight="Black", r=12, shadow=6)


# --- save / load -----------------------------------------------------------------------
def make_saveload():
    for name, title in (("save", "Save"), ("load", "Load")):
        c = Canvas(1920, 1080)
        screen_bg(c, alpha=234)
        header(c, L(title))
        c.save(out("%s_base.png" % name))

    def slot(over):
        c = Canvas(650, 149)
        c.rrect((0, 0, 650, 149), 12, fill=rgba(VIOLET if over else LAV))
        c.rrect((4 + over, 4 + over, 646 - over, 145 - over), 9, fill=rgba(WHITE if not over else (250, 248, 255), 245))
        # the thumbnail well (fileDataButton draws a 234x132 thumbnail at 9, 9)
        c.rrect((9, 9, 243, 141), 4, fill=rgba(LAV_SOFT))
        c.text((126, 75), L("NO DATA"), font("Black", 22), rgba(WHITE), anchor="mm", tracking=2)
        c.rrect((260, 74, 626, 76), 1, fill=rgba(LAV_SOFT))
        return c
    slot(0).save(out("sl_win_base.png"))
    for name in ("save", "load"):
        slot(1).save(out("%s_win_over.png" % name))

    c = Canvas(95, 40)
    c.rrect((0, 0, 95, 40), 20, fill=rgba(WHITE))
    c.rrect((3, 3, 92, 37), 17, fill=rgba(VIOLET))
    c.text((47.5, 20), "NEW", font("Black", 21), rgba(WHITE), anchor="mm", tracking=2)
    c.save(out("newdata.png", False))

    for i in range(1, 10):
        for st in ("normal", "over"):
            button(56, 64, str(i), st, size=30, weight="Black", r=10, bw=3).save(
                out("page%d_%s.png" % (i, st), False))


# --- Extras ----------------------------------------------------------------------------
# six tabs 120 wide, 8 apart, from x 682 (the screens' titles end before it; Return at 1450:
# the screens' .ks files put them at 682, 810, 938, 1066, 1194, 1322); every label in one size,
# the largest at which each fits
EXTRA_TABS = [("extra_cgmode", "CG"), ("extra_replaymode", "Replay"), ("extra_chart", "Chart"),
              ("extra_musicmode", "Music"), ("extra_searchmode", "Search"), ("extra_glossary", "Glossary")]
EXTRA_TAB_W = 120


def extra_tab_size():
    probe = Canvas(8, 8)
    room = EXTRA_TAB_W - 6 - 2 * 4 - 2 * 6  # the shadow, the border, a margin
    size = 26
    while size > 14 and max(probe.text_width(L(t), font("Black", size), 0) for _, t in EXTRA_TABS) > room:
        size -= 1
    return size


def make_extras():
    for name, title in (("cgmode", "CG Mode"), ("replaymode", "Replay")):
        c = Canvas(1920, 1080)
        screen_bg(c)
        header(c, L(title))
        # behind the 4x4 thumbnails (681 + 245 x, 322 + 154 y, 214x123)
        c.panel((652, 294, 1630 + 26, 907 + 28), r=18, fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
        c.save(out("%s_base.png" % name), opaque=True)

    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, L("Music"))
    c.panel((290, 262, 800, 960))
    c.panel((840, 262, 1630, 960), fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
    c.save(out("musicmode_base.png"), opaque=True)
    # the record, above the player buttons: a picture of its own, which turns while the music
    # plays (KAGNowPlaying, template/system/MusicPlayer.tjs; a mark on its label shows it turn)
    c = Canvas(260, 260)
    cx, cy = 130, 130
    c.ellipse((cx - 128, cy - 128, cx + 128, cy + 128), fill=rgba(VIOLET))
    for r in (112, 96, 80):
        c.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgba(WHITE, 40), width=2)
    c.ellipse((cx - 54, cy - 54, cx + 54, cy + 54), fill=rgba(WHITE))
    ic_note(c, cx, cy, 60, rgba(VIOLET))
    c.ellipse((cx - 7, cy - 46, cx + 7, cy - 32), fill=rgba(LAV))
    c.save(out("musicmode_record.png", False))

    # Search: the field (searchmode.ks puts an [edit] in it), its button, and the results'
    # panel with 7 rows of 1314x76 (316 + 86 y) and the replay arrows beside them
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, L("Search"))
    c.panel((290, 206, 1190, 270), r=12, fill=rgba(WHITE), border=VIOLET, bw=4, shadow=6)
    c.panel((290, 300, 1656, 936), r=18, fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
    c.save(out("searchmode_base.png"), opaque=True)
    for st in ("normal", "over"):
        nav_button(L("Search"), st).save(out("search_go_%s.png" % st))
    for st, fill, border in (("normal", rgba(WHITE, 235), LAV), ("over", rgba(VIOLET), VIOLET)):
        c = Canvas(1314, 76)
        c.rrect((0, 0, 1314, 76), 12, fill=rgba(border))
        c.rrect((3, 3, 1311, 73), 9, fill=fill)
        c.save(out("search_row_%s.png" % st, False))

    # the glossary (glossary.ks): the terms on the left, 9 rows of 470x76 (230 + 82 y), the
    # entry met on the right
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, L("Glossary"))
    c.panel((290, 206, 800, 960), r=18, fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
    c.panel((840, 206, 1630, 960))
    c.save(out("glossary_base.png"), opaque=True)
    for st, fill, border in (("normal", rgba(WHITE, 235), LAV), ("over", rgba(VIOLET), VIOLET)):
        c = Canvas(470, 76)
        c.rrect((0, 0, 470, 76), 12, fill=rgba(border))
        c.rrect((3, 3, 467, 73), 9, fill=fill)
        c.save(out("glossary_row_%s.png" % st, False))

    # the flowchart (chart.ks, template/system/Flowchart.tjs): the chart in a panel, the zoom
    # buttons and the one that goes back to the story's place under it
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, L("Chart"))
    c.panel((290, 206, 1630, 940), r=18, fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
    c.save(out("chart_base.png"), opaque=True)
    for name, icon in (("chart_zoomout", ic_minus), ("chart_zoomin", ic_plus), ("chart_here", ic_here)):
        for st in ("normal", "over"):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(64, 64)
            b.rrect((0, 0, 64, 64), 12, fill=rgba(border))
            b.rrect((3, 3, 61, 61), 9, fill=fill)
            icon(b, 32, 32, 34, rgba(fg))
            b.save(out("%s_%s.png" % (name, st), False))

    # the music room's views (Music, Voices, Favourites: labelled at run time) and the voice
    # rows' star and handle (Override.tjs, voiceList)
    for st in ("normal", "over"):
        button(180, 56, "", st, size=26, weight="Black", r=12, shadow=6).save(out("music_view_%s.png" % st, False))
    for name, on in (("voice_star_on", True), ("voice_star_off", False)):
        c = Canvas(44, 44)
        pts = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            r = 19 if k % 2 == 0 else 8
            pts.append((22 + r * math.cos(a), 23 - r * math.sin(a)))
        if on:
            c.polygon(pts, rgba((255, 176, 32)))
        else:
            c.stroke(pts, 3, rgba(LAV_SOFT), closed=True)
        c.save(out("%s.png" % name, False))
    c = Canvas(44, 44)
    for y in (14, 21, 28):
        c.rrect((9, y, 35, y + 3), 1.5, fill=rgba(LAV_SOFT))
    c.save(out("voice_handle.png", False))
    # (since 0.25.0) a favourite protected (a closed lock) or not (open), and the jump to its scene
    for name, on in (("voice_lock_on", True), ("voice_lock_off", False)):
        c = Canvas(44, 44)
        col = rgba(VIOLET) if on else rgba(LAV_SOFT)
        c.rrect((11, 20, 33, 38), 4, fill=col)
        if on:
            c.stroke([(16, 21), (16, 14), (17, 10), (22, 7), (27, 10), (28, 14), (28, 21)], 3.5, col)
        else:
            # open: lifted, its left leg out of the body
            c.stroke([(16, 15), (16, 9), (17, 5), (22, 2), (27, 5), (28, 9), (28, 21)], 3.5, col)
        c.ellipse((20, 25, 24, 29), fill=rgba(WHITE))
        c.save(out("%s.png" % name, False))
    c = Canvas(44, 44)
    c.ellipse((3, 3, 41, 41), fill=rgba(WHITE), outline=rgba(VIOLET), width=2.5)
    ic_back(c, 22, 22, 22, rgba(VIOLET))
    c.save(out("voice_jump.png", False))

    # Sprite Mode (spritemode.ks, from the CG screen's Characters button): a panel on the left
    # with its title, the rest clear for the World's stage and character; its rows' arrows
    c = Canvas(1920, 1080)
    c.rrect((0, 0, 680, 1080), 0, fill=rgba(LAV_PALE))
    c.pattern((0, 0, 680, 1080), 36, 2.2, rgba(LAV, 90))
    c.rrect((674, 0, 680, 1080), 0, fill=rgba(VIOLET))
    c.text((60, 150), L("Characters"), font("Black", 84), rgba(VIOLET), anchor="ls", shadow=(6, 6, rgba(LAV)))
    c.rrect((60, 170, 620, 176), 3, fill=rgba(VIOLET))
    # the line's field (an [edit] over it)
    c.rrect((60, 830, 620, 890), 12, fill=rgba(LAV))
    c.rrect((63, 833, 617, 887), 9, fill=rgba(WHITE))
    c.save(out("sprite_base.png"))
    for st in ("normal", "over"):
        for name, sign in (("sprite_prev", -1), ("sprite_next", 1)):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(64, 64)
            b.rrect((0, 0, 64, 64), 12, fill=rgba(border))
            b.rrect((3, 3, 61, 61), 9, fill=fill)
            b.stroke([(32 - sign * 6, 18), (32 + sign * 8, 32), (32 - sign * 6, 46)], 7, rgba(fg))
            b.save(out("%s_%s.png" % (name, st), False))
        button(330, 80, "", st, size=30, r=12).save(out("sprite_open_%s.png" % st, False))
        # the stage's tools: a character on and off the stage, turned round, a screenshot, the
        # panel away and back (the zoom's are the chart's)
        for name, icon in (("sprite_add", ic_person_plus), ("sprite_remove", ic_person_minus), ("sprite_flip", ic_flip),
                           ("sprite_shot", ic_camera), ("sprite_hide", ic_hide_panel), ("sprite_show", ic_show_panel)):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(64, 64)
            b.rrect((0, 0, 64, 64), 12, fill=rgba(border))
            b.rrect((3, 3, 61, 61), 9, fill=fill)
            icon(b, 32, 32, 36, rgba(fg))
            b.save(out("%s_%s.png" % (name, st), False))

    size = extra_tab_size()
    for name, label in EXTRA_TABS:
        for st in ("normal", "over"):
            nav_button(L(label), st, w=EXTRA_TAB_W, size=size).save(out("%s_%s.png" % (name, st)))
    pages = ["Character 1", "Character 2", "Character 3", "Character 4", "Character 5", "Other"]
    for i, label in enumerate(pages):
        for st in ("normal", "over"):
            button(330, 80, L(label), st, size=30, r=12).save(out("cgmode_page%d_%s.png" % (i, st)))

    # Replay's tabs, labelled at run time from replaylist.csv (Override.tjs), and the arrows
    # beside its tiles for a tab with more than one page of them (replay.ks)
    for st in ("normal", "over"):
        button(330, 80, "", st, size=30, r=12).save(out("replay_tab_%s.png" % st, False))
        for name, up in (("prev", True), ("next", False)):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(64, 64)
            b.rrect((0, 0, 64, 64), 12, fill=rgba(border))
            b.rrect((3, 3, 61, 61), 9, fill=fill)
            chevron(b, 32, 32, 30, rgba(fg), up)
            b.save(out("replay_%s_%s.png" % (name, st), False))

    for st, border in (("normal", LAV), ("over", VIOLET)):
        c = Canvas(214, 123)
        c.rrect((0, 0, 214, 123), 4, fill=rgba(border))
        c.rrect((3, 3, 211, 120), 2, fill=rgba(LAV_PALE))
        c.text((107, 62), "?", font("Black", 56), rgba(LAV_SOFT), anchor="mm")
        c.save(out("cgmode_thum_%s.png" % st, False))
        # an unlocked Replay scene that has no thumbnail (replaylist.csv): playable, so not a "?"
        c = Canvas(214, 123)
        c.rrect((0, 0, 214, 123), 4, fill=rgba(border))
        c.rrect((3, 3, 211, 120), 2, fill=rgba(LAV_PALE))
        c.ellipse((107 - 30, 61.5 - 30, 107 + 30, 61.5 + 30), fill=rgba(VIOLET))
        ic_play(c, 110, 61.5, 26, rgba(WHITE))
        c.save(out("replay_thum_%s.png" % st, False))

    for i in range(12):
        for st in ("normal", "over"):
            button(730, 46, L("Track %02d") % (i + 1), st, size=24, r=10, bw=3, icon=ic_note, icon_size=24).save(
                out("track%02d_%s.png" % (i + 1, st)))
    for name, label, icon in (("stop", "Stop", ic_stop), ("play", "Play", ic_play), ("pause", "Pause", ic_pause)):
        for st in ("normal", "over"):
            button(210, 60, L(label), st, size=26, icon=icon, icon_size=24).save(
                out("musicmode_%s_%s.png" % (name, st)))
    # what comes after a track (since 0.25.0, three in the row the two repeats had): the track
    # again, every track in turn, or any other at random
    for name, label, icon in (("repeat", "One", ic_repeat_one), ("allrepeat", "In Order", ic_repeat),
                              ("shuffle", "Shuffle", ic_shuffle)):
        for st in ("normal", "over"):
            button(140, 60, L(label), st, size=24, icon=icon, icon_size=22).save(
                out("musicmode_%s_%s.png" % (name, st)))
    # a switch: the track playing stays as the title's music (Override.tjs, setTitleMusic)
    for st in ("normal", "over"):
        button(446, 60, L("Keep on Title"), st, size=26, icon=ic_note, icon_size=24).save(
            out("musicmode_title_%s.png" % st))


# --- the message history ---------------------------------------------------------------
def make_history():
    c = Canvas(1920, 1080)
    c.rrect((0, 0, 1920, 1080), 0, fill=rgba(DEEP, 222))
    c.pattern((0, 0, 1920, 1080), 36, 2.2, rgba(WHITE, 16))
    # the rail for the page buttons and the scroll bar (MyHistoryLayer.tjs: x 1766-1881)
    c.rrect((1750, 42, 1898, 1037), 20, fill=rgba(WHITE, 26))
    # the scroll bar's track: its 43x48 tab moves over x 1802-1845, y 294-847 (since 0.18.0 the
    # scene buttons sit above and below it, since 0.21.0 the close button at the top of the rail)
    c.rrect((1817, 314, 1830, 827), 6, fill=rgba(WHITE, 70))
    c.save(out("log_base.png", False))

    # closing the history (since 0.21.0: a phone has no right button, Esc or wheel to close it)
    for st in ("normal", "over"):
        fill, border, fg, _ = STYLE[st]
        b = Canvas(115, 58)
        b.rrect((0, 0, 115, 54), 12, fill=rgba(border))
        b.rrect((3, 3, 112, 51), 9, fill=fill)
        ic_close(b, 57.5, 27, 30, rgba(fg))
        b.save(out("log_close_%s.png" % st, False))

    for name, up, double in (("first", True, True), ("uppage", True, False), ("downpage", False, False),
                             ("last", False, True)):
        for st in ("normal", "over"):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(115, 58)
            b.rrect((0, 0, 115, 54), 12, fill=rgba(border))
            b.rrect((3, 3, 112, 51), 9, fill=fill)
            chevron(b, 57.5, 27, 30, rgba(fg), up, double)
            b.save(out("log_%s_%s.png" % (name, st), False))
    # to the previous and the next scene or choice (since 0.18.0): a chevron and a bar
    for name, up in (("prevscene", True), ("nextscene", False)):
        for st in ("normal", "over"):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(115, 58)
            b.rrect((0, 0, 115, 54), 12, fill=rgba(border))
            b.rrect((3, 3, 112, 51), 9, fill=fill)
            chevron(b, 57.5, 31 if up else 23, 24, rgba(fg), up)
            bar_y = 12 if up else 38
            b.rrect((37, bar_y, 78, bar_y + 5), 2, fill=rgba(fg))
            b.save(out("log_%s_%s.png" % (name, st), False))
    for st, fill, border in (("normal", WHITE, VIOLET), ("over", VIOLET, WHITE)):
        t = Canvas(43, 48)
        t.rrect((0, 0, 43, 48), 12, fill=rgba(border))
        t.rrect((4, 4, 39, 44), 9, fill=rgba(fill))
        for y in (18, 24, 30):
            t.rrect((14, y - 1, 29, y + 1), 1, fill=rgba(border))
        t.save(out("log_bar_%s.png" % st, False))
    # the marks left of a line, a line high (MyHistoryLayer.tjs: lineHeight 42): playing its
    # voice, and going back to the message (compiled scenes)
    for st, fill, fg in (("normal", VIOLET, WHITE), ("over", WHITE, VIOLET)):
        p = Canvas(42, 42)
        p.ellipse((2, 2, 40, 40), fill=rgba(fill), outline=rgba(WHITE if st == "normal" else VIOLET), width=2.5)
        ic_play(p, 22.5, 21, 16, rgba(fg))
        p.save(out("log_play_%s.png" % st, False))
    for st, fill, fg in (("normal", WHITE, VIOLET), ("over", VIOLET, WHITE)):
        p = Canvas(42, 42)
        p.ellipse((2, 2, 40, 40), fill=rgba(fill), outline=rgba(VIOLET if st == "normal" else WHITE), width=2.5)
        ic_back(p, 21, 21, 22, rgba(fg))
        p.save(out("log_jump_%s.png" % st, False))
    # a voiced line kept with the favourite voices (a gold star) or not (an outline; since 0.25.0)
    for name, on in (("log_star_on", True), ("log_star_off", False)):
        p = Canvas(42, 42)
        pts = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            r = 18 if k % 2 == 0 else 7.5
            pts.append((21 + r * math.cos(a), 22 - r * math.sin(a)))
        if on:
            p.polygon(pts, rgba((255, 176, 32)))
            p.stroke(pts, 2, rgba(WHITE), closed=True)
        else:
            p.stroke(pts, 3, rgba(LAV), closed=True)
        p.save(out("%s.png" % name, False))


# --- thumbnails drawn from the upscaled art --------------------------------------------
def make_thumbs():
    """the Character demo's Replay thumbnail (replaylist.csv): its first scene, Ai in the
    middle of the street (char.ks puts her at 690, 180), shrunk to setCGImage's 208x117"""
    scene = Image.open(os.path.join(REPO, "data", "bgimage", "bg01_01.png")).convert("RGBA")
    scene.alpha_composite(Image.open(os.path.join(REPO, "data", "fgimage", "ch_0_0_1.png")).convert("RGBA"), (690, 180))
    path = os.path.join(REPO, "data", "thum", "thum_replay_char.png")
    scene.convert("RGB").resize((208, 117), Image.LANCZOS, reducing_gap=3.0).save(path, optimize=True)
    print("wrote", os.path.relpath(path, REPO), (208, 117), flush=True)


# --- app icons for the platform builds (platform/) -------------------------------------
PLATFORM = os.path.join(REPO, "platform")


def k_outline():
    """the K of the Black subset font as an SVG path in font units (y up), with its bounds"""
    try:
        from fontTools.ttLib import TTFont
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.boundsPen import BoundsPen
    except ImportError:
        raise SystemExit("the icons group needs fontTools (pip install fonttools)")
    f = TTFont(os.path.join(HERE, "fonts", "NotoSansCJKjp-Black-Latin.otf"))
    gs = f.getGlyphSet()
    name = f.getBestCmap()[ord("K")]
    pen = SVGPathPen(gs)
    gs[name].draw(pen)
    bpen = BoundsPen(gs)
    gs[name].draw(bpen)
    return pen.getCommands(), bpen.bounds


def k_transform(bounds, cx, cy, height):
    """scale and offset that put the K's bounding box centred on cx, cy, height tall, y down"""
    x0, y0, x1, y1 = bounds
    k = height / (y1 - y0)
    return k, cx - (x0 + x1) / 2 * k, cy + (y0 + y1) / 2 * k


def make_icons():
    os.makedirs(PLATFORM, exist_ok=True)
    path, bounds = k_outline()
    violet = "#%02x%02x%02x" % VIOLET

    # Linux desktop entry (linux-config.json): a rounded badge
    k, tx, ty = k_transform(bounds, 128, 128, 150)
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">\n'
           '  <rect x="8" y="8" width="240" height="240" rx="52" fill="%s"/>\n'
           '  <path transform="translate(%.3f %.3f) scale(%.5f %.5f)" fill="#ffffff" d="%s"/>\n'
           '</svg>\n' % (violet, tx, ty, k, -k, path))
    with open(os.path.join(PLATFORM, "icon.svg"), "w") as f:
        f.write(svg)
    print("wrote platform/icon.svg", flush=True)

    # iOS (ios-config.json) and the macOS .icns: square and opaque; the system rounds it
    c = Canvas(1024, 1024)
    c.rrect((0, 0, 1024, 1024), 0, fill=rgba(VIOLET))
    c.text((512 + 28, 512 + 28), "K", font("Black", 640), rgba(NAVY), anchor="mm")
    c.text((512, 512), "K", font("Black", 640), rgba(WHITE), anchor="mm")
    c.save(os.path.join(PLATFORM, "icon-1024.png"), opaque=True)

    # The web build's home-screen icons (web-static-host.py): the same square, which iOS rounds
    # and Android masks (the K stays inside a maskable icon's safe zone)
    web = os.path.join(PLATFORM, "web")
    os.makedirs(web, exist_ok=True)
    full = Image.open(os.path.join(PLATFORM, "icon-1024.png")).convert("RGB")
    for name, size in (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
        full.resize((size, size), Image.LANCZOS, reducing_gap=3.0).save(os.path.join(web, name), optimize=True)
        print("wrote platform/web/%s" % name, (size, size), flush=True)

    # Android adaptive icon (app-config.json's resOverride): the K inside the 66 dp safe zone
    # of a 108 dp foreground, on the violet background colour (values/colors.xml)
    res = os.path.join(PLATFORM, "android-res", "drawable")
    os.makedirs(res, exist_ok=True)
    k, tx, ty = k_transform(bounds, 54, 54, 40)
    for name, colour in (("ic_launcher_foreground", "#FFFFFFFF"), ("ic_launcher_monochrome", "#FF000000")):
        xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
               '<!-- drawn by tools/assets/make_ui.py icons -->\n'
               '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
               '    android:width="108dp" android:height="108dp"\n'
               '    android:viewportWidth="108" android:viewportHeight="108">\n'
               '    <group android:translateX="%.3f" android:translateY="%.3f"\n'
               '        android:scaleX="%.5f" android:scaleY="%.5f">\n'
               '        <path android:fillColor="%s" android:pathData="%s"/>\n'
               '    </group>\n'
               '</vector>\n' % (tx, ty, k, -k, colour, path))
        with open(os.path.join(res, name + ".xml"), "w") as f:
            f.write(xml)
        print("wrote platform/android-res/drawable/%s.xml" % name, flush=True)


def make_preview():
    """The web build's link-preview image (web-static-host.py: og:image): the title screen,
    1200x630 as Discord, Slack and X show it. Run after title (it reads data/image/title.png)."""
    src = Image.open(os.path.join(IMAGE, "title.png")).convert("RGB")
    w, h = 1200, 630
    k = max(w / src.width, h / src.height)
    sw, sh = round(src.width * k), round(src.height * k)
    img = src.resize((sw, sh), Image.LANCZOS, reducing_gap=3.0)
    x, y = (sw - w) // 2, (sh - h) // 2
    out = os.path.join(PLATFORM, "web", "preview.jpg")
    img.crop((x, y, x + w, y + h)).save(out, quality=88, optimize=True, progressive=True)
    print("wrote platform/web/preview.jpg", (w, h), flush=True)


# --- the dialogs' panel, to stretch -----------------------------------------------------
def make_dialog():
    """template/system/dialog_panel.png: the Yes/No dialog's panel (lavender, a violet border, a
    hard shadow down and to the right) on a transparent ground, small, for the screens drawn at
    run time (the menu and the controls list, ElementsScreen.tjs) to stretch by its middle: its
    corners, 24 px in from the top left and 36 from the bottom right with the shadow, stay as
    they are (yesnoPanelInsets in YesNoDialogLayer.tjs)"""
    c = Canvas(128, 128)
    c.panel((0, 0, 116, 116), r=14, shadow=12)
    c.save(os.path.join(SYSTEM, "dialog_panel.png"))

    # the Yes/No prompt's "Don't ask again" box (drawYesNoCheck draws its label and its tick)
    for st, border in (("normal", VIOLET), ("over", NAVY)):
        c = Canvas(360, 44)
        if st == "over":
            c.rrect((0, 0, 44, 44), 10, fill=rgba(WHITE, 110))
        c.rrect((4, 4, 40, 40), 8, fill=rgba(WHITE), outline=rgba(border), width=4)
        c.save(os.path.join(SYSTEM, "dialog_check_%s.png" % st))

    # the colour picker's wheel (ColorPicker.tjs): hue round it from red at the right,
    # counterclockwise, saturation from white at the middle to the full colour at the rim, at
    # full brightness (the picker darkens it for a lower one); clear outside the circle
    n, rad = 320, 156.0
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64) + 0.5
    dx, dy = xx - n / 2, n / 2 - yy
    r = np.hypot(dx, dy)
    h = (np.degrees(np.arctan2(dy, dx)) % 360) / 60.0
    sat = np.clip(r / rad, 0, 1)
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p_, q, t = 1 - sat, 1 - sat * f, 1 - sat * (1 - f)
    v = np.ones_like(sat)
    rgb = np.zeros((n, n, 3))
    for k, (rr, gg, bb) in enumerate(((v, t, p_), (q, v, p_), (p_, v, t), (p_, q, v), (t, p_, v), (v, p_, q))):
        m = i == k
        rgb[m, 0], rgb[m, 1], rgb[m, 2] = rr[m], gg[m], bb[m]
    alpha = np.clip(rad - r + 0.5, 0, 1)
    img = np.dstack([rgb * 255, alpha * 255]).round().astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(SYSTEM, "color_wheel.png"))


# --- the star in the World demo --------------------------------------------------------
def make_star():
    w, h = 371, 351
    c = Canvas(w, h)
    cx, cy = w / 2, h * 0.53
    R, r = 168, 70
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    c.stroke(pts, 18, rgba((255, 146, 0)), closed=True)
    c.polygon(pts, rgba((255, 236, 0)))
    c.save(os.path.join(REPO, "data", "fgimage", "star.png"))


# --- props for the World demo's objects that move with others (0.26.0) ----------------------
def make_props():
    """prop_bubble: a speech bubble with three dots (attached to Pip, its tail at the bottom left);
    prop_light: warm light falling from the top left, to clip to a character's outline"""
    w, h = 300, 236
    c = Canvas(w, h)
    body = (14, 14, w - 14, 176)
    tail = [(60, 146), (136, 146), (36, 224)]
    # outline first (the body and the tail, a little larger), then the white over it
    c.ellipse((body[0] - 7, body[1] - 7, body[2] + 7, body[3] + 7), fill=rgba(NAVY))
    c.stroke(tail, 14, rgba(NAVY), closed=True)
    c.polygon(tail, rgba(NAVY))
    c.ellipse(body, fill=rgba(WHITE))
    c.polygon([(72, 140), (124, 140), (50, 204)], rgba(WHITE))
    for i in range(3):
        x = 98 + i * 52
        c.ellipse((x - 15, 80, x + 15, 110), fill=rgba(VIOLET))
    c.save(os.path.join(REPO, "data", "fgimage", "prop_bubble.png"))
    # the light: 1200 x 1800, an orange glow strongest at the top left, gone by the middle
    w, h = 600, 900
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = (xx / w * 0.8 + yy / h * 0.6)
    a = np.clip(1.0 - d / 0.9, 0, 1) ** 1.6
    arr = np.zeros((h, w, 4), np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2] = 255, 176, 84
    arr[:, :, 3] = (a * 235 + 0.5).astype(np.uint8)
    Image.fromarray(arr, "RGBA").resize((w * 2, h * 2), Image.BILINEAR).save(os.path.join(REPO, "data", "fgimage", "prop_light.png"), optimize=True)


# --- the mouse pointers (0.27.0) ------------------------------------------------------------
def make_cursors():
    """cursor_<kind>.png, the game's own mouse pointers (template/system/GameCursor.tjs, the
    sample's data/main/cursors.csv): 44 px squares, each its size on the screen. default: a
    white arrow outlined in navy with a hard violet shadow; pointed (a button or a link): the
    arrow in violet, outlined in white; click (a click wait): the arrow with a lavender ring
    by its tail; text (a text field): an I-beam; drag (a draggable area): four arrows"""
    n = 44
    arrow = [(3, 3), (3, 33), (11, 26), (17, 39), (23, 36), (17, 24), (28, 24)]

    def draw_arrow(c, fill, line, shadow):
        c.polygon([(x + 3, y + 3) for x, y in arrow], rgba(shadow, 170))
        c.stroke(arrow, 4.5, rgba(line), closed=True)
        c.polygon(arrow, rgba(fill))

    c = Canvas(n, n)
    draw_arrow(c, WHITE, NAVY, VIOLET)
    c.save(os.path.join(IMAGE, "cursor_default.png"))
    c = Canvas(n, n)
    draw_arrow(c, VIOLET, WHITE, NAVY)
    c.save(os.path.join(IMAGE, "cursor_pointed.png"))
    c = Canvas(n, n)
    draw_arrow(c, WHITE, NAVY, VIOLET)
    c.ellipse((26, 26, 42, 42), fill=rgba(NAVY))
    c.ellipse((28.5, 28.5, 39.5, 39.5), fill=rgba(LAV))
    c.ellipse((32, 32, 36, 36), fill=rgba(WHITE))
    c.save(os.path.join(IMAGE, "cursor_click.png"))
    c = Canvas(n, n)
    beam = [(15, 6), (29, 6), (29, 10), (24, 10), (24, 34), (29, 34), (29, 38), (15, 38), (15, 34),
            (20, 34), (20, 10), (15, 10)]
    c.stroke(beam, 4, rgba(NAVY), closed=True)
    c.polygon(beam, rgba(WHITE))
    c.save(os.path.join(IMAGE, "cursor_text.png"))
    c = Canvas(n, n)
    m, a, b, d, w = 22, 19, 2.5, 7, 7.5   # the middle, an arm's reach, the bar's half width, a head's depth and half width
    cross = []
    for k in range(4):   # each arm, turned a quarter at a time: up, right, down, left
        arm = [(-b, -b), (-b, -a + d), (-w, -a + d), (0, -a), (w, -a + d), (b, -a + d), (b, -b)]
        for x, y in arm[:-1]:   # its last corner is the next arm's first
            for _ in range(k):
                x, y = -y, x
            cross.append((m + x, m + y))
    c.stroke(cross, 4, rgba(NAVY), closed=True)
    c.polygon(cross, rgba(WHITE))
    c.save(os.path.join(IMAGE, "cursor_drag.png"))


GROUPS = {"title": make_title, "logo": make_logo, "message": make_message, "config": make_config,
          "saveload": make_saveload, "extras": make_extras, "history": make_history, "star": make_star,
          "thumbs": make_thumbs, "icons": make_icons, "preview": make_preview, "dialog": make_dialog,
          "props": make_props, "cursors": make_cursors}


# the groups whose images have words on them, drawn again for each other language
LANGUAGE_GROUPS = ["title", "message", "config", "saveload", "extras"]


def main():
    global LANG
    args = sys.argv[1:]
    langs = None
    if "--lang" in args:
        i = args.index("--lang")
        langs = args[i + 1].split(",")
        del args[i:i + 2]
    for lang in langs or ["en"] + sorted(LABELS):
        if lang != "en" and lang not in LABELS:
            raise SystemExit("no labels for %s; languages: en %s" % (lang, " ".join(LABELS)))
        LANG = lang
        names = args or (list(GROUPS) if lang == "en" else LANGUAGE_GROUPS)
        for n in names:
            if n not in GROUPS:
                raise SystemExit("unknown group %s; groups: %s" % (n, " ".join(GROUPS)))
            if lang != "en" and n not in LANGUAGE_GROUPS:
                continue
            GROUPS[n]()


if __name__ == "__main__":
    main()
