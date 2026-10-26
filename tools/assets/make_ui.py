#!/usr/bin/env python3
"""Draws the sample's UI images (title, logo, message window, choices, config, save/load,
Extras, history) at 1920x1080 in one style: the lavender panels, violet borders and hard
shadows of the Yes/No dialogs in template/system.

usage: python3 tools/assets/make_ui.py [group ...]    (no groups: all of them)

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


_fonts = {}


def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(HERE, "fonts", "NotoSansCJKjp-%s-Latin.otf" % weight),
                                         int(round(size * SS)))
    return _fonts[key]


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
    c.save(os.path.join(IMAGE, "title.png"), opaque=True, under=under)

    for name, label in TITLE_BUTTONS:
        for st in ("normal", "over"):
            button(400, 68, label, st, size=30, weight="Black", r=12, shadow=8, tracking=4).save(
                os.path.join(IMAGE, "%s_%s.png" % (name, st)))


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
    c.save(os.path.join(IMAGE, "logo.png"), opaque=True)

    # about.ks's 400x200 window (only with aboutInWindow = false); the text goes bottom right
    c = Canvas(400, 200)
    c.rrect((0, 0, 400, 200), 0, fill=rgba(LAV_PALE))
    emblem(c, 24, 22, 76)
    wordmark(c, 118, 90, 60)
    c.save(os.path.join(IMAGE, "about_logo.png"), opaque=True)


# --- the message window ----------------------------------------------------------------
MSG_BUTTONS = ["save", "load", "back", "skip", "auto", "log", "config", "exit", "hide"]


def make_message():
    w, h = 1800, 330
    c = Canvas(w, h)
    c.panel((0, 0, w - 12, h - 12), r=18, fill=rgba(LAV, 228), border=VIOLET, bw=5, shadow=12)
    # a highlight along the top, inside the border (its inner edge is rounded too: 18 - 5)
    c.gradient((5, 5, w - 17, 90), (255, 255, 255, 60), (255, 255, 255, 0), clip=((5, 5, w - 17, h - 17), 13))
    c.save(os.path.join(IMAGE, "messagewindow.png"))

    # the speaker's name, behind NameLayer's text ([position nameframe=namebox])
    c = Canvas(300, 64)
    c.panel((0, 0, 292, 56), r=14, fill=VIOLET, border=WHITE, bw=4, shadow=8, shadow_color=NAVY)
    c.save(os.path.join(IMAGE, "namebox.png"))

    for name in MSG_BUTTONS:
        for st in ("normal", "over"):
            button(124, 42, name.upper(), st, size=19, r=10, bw=3, tracking=1.5).save(
                os.path.join(IMAGE, "msg_%s_%s.png" % (name, st)))
    for name in ("auto", "skip"):  # latched while auto mode / skipping is on
        button(124, 42, name.upper(), "on", size=19, r=10, bw=3, tracking=1.5, icon=ic_dot,
               icon_size=8).save(os.path.join(IMAGE, "msg_%s_on.png" % name))

    # the choices ([selopt] in first.ks)
    for st, fill, border, sh in (("normal", rgba(LAV, 238), VIOLET, VIOLET), ("over", rgba(VIOLET), WHITE, NAVY)):
        c = Canvas(900, 74)
        c.panel((0, 0, 892, 66), r=16, fill=fill, border=border, bw=4, shadow=8, shadow_color=sh)
        c.save(os.path.join(IMAGE, "select_%s.png" % st))

    # click-wait glyphs: 43x43 cells, 16 frames that the .asd plays forwards and back
    for name, direction in (("LineBreak", "down"), ("PageBreak", "right")):
        frames = Canvas(43 * 16, 43)
        for i in range(16):
            t = i / 15
            e = math.sin(t * math.pi / 2)
            frames.paste(break_glyph(direction, e), 43 * i, 0)
        frames.save(os.path.join(SYSTEM, name + "_a.png"))
        break_glyph(direction, 1.0).save(os.path.join(SYSTEM, name + ".png"))


def break_glyph(direction, e):
    """a white triangle with a violet outline, fading in and moving 5 px as e goes 0 -> 1"""
    c = Canvas(43, 43)
    a = int(255 * (0.3 + 0.7 * e))
    m = 5 * e
    if direction == "down":
        pts = [(9, 11 + m), (34, 11 + m), (21.5, 27 + m)]
    else:
        pts = [(13 + m, 8.5), (13 + m, 33.5), (29 + m, 21)]
    c.stroke(pts, 6, rgba(VIOLET, a), closed=True)
    c.polygon(pts, rgba(WHITE, a))
    return c


# --- config ----------------------------------------------------------------------------
CFG_L, CFG_R, CFG_TOP, CFG_ROW, CFG_W = 290, 990, 206, 150, 640


def make_config():
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, "Config")
    left = ["Screen Mode", "Text Speed", "Auto Speed", "Effect Speed", "Skip Mode"]
    right = ["BGM Volume", "SE Volume", "Voice Volume", "Voice Settings"]
    sliders = {(CFG_L, 1): ("Slow", "Fast"), (CFG_L, 2): ("Slow", "Fast"),
               (CFG_R, 0): ("Min", "Max"), (CFG_R, 1): ("Min", "Max"), (CFG_R, 2): ("Min", "Max")}
    bottom = CFG_TOP + CFG_ROW * 5
    for x0, labels in ((CFG_L, left), (CFG_R, right)):
        c.panel((x0, CFG_TOP, x0 + CFG_W, bottom))
        for i, label in enumerate(labels):
            top = CFG_TOP + CFG_ROW * i
            if i:
                c.rrect((x0 + 24, top - 1, x0 + CFG_W - 24, top + 1), 1, fill=rgba(WHITE, 120))
            outlined(c, (x0 + 32, top + 16), label, 36)
            if (x0, i) in sliders:
                lo, hi = sliders[(x0, i)]
                sx, cy = x0 + 112, top + 102
                outlined(c, (sx - 12, cy), lo, 26, anchor="rm", stroke=2.5)
                outlined(c, (sx + 416 + 12, cy), hi, 26, anchor="lm", stroke=2.5)
                # the slider's tab centre travels from sx + 15 to sx + 416 - 15 (SliderLayer)
                c.rrect((sx + 6, cy - 7, sx + 410, cy + 7), 7, fill=rgba(WHITE), outline=rgba(VIOLET), width=3)
    outlined(c, (CFG_R + 32, CFG_TOP + CFG_ROW * 3 + 236), "Click a voice to mute or unmute it.", 26,
             stroke=2.5)
    c.save(os.path.join(IMAGE, "config_base.png"), opaque=True)

    # the slider's tab
    for st, fill, border in (("", WHITE, VIOLET), ("_over", VIOLET, WHITE)):
        t = Canvas(30, 44)
        t.rrect((0, 0, 30, 44), 10, fill=rgba(border))
        t.rrect((4, 4, 26, 40), 7, fill=rgba(fill))
        t.save(os.path.join(IMAGE, "slidebar%s.png" % st))

    toggles = [("window", "Window"), ("fullscreen", "Full Screen"), ("effecton", "Normal"), ("effectoff", "Skip"),
               ("skipall", "All"), ("skipalrdy", "Read Only")]
    for name, label in toggles:
        for st in ("normal", "over"):
            button(240, 60, label, st, size=28).save(os.path.join(IMAGE, "config_%s_%s.png" % (name, st)))
    for i in range(6):
        button(180, 60, "Voice %d" % i, "over", size=26, icon=ic_dot, icon_size=14).save(
            os.path.join(IMAGE, "config_voice%d_on.png" % i))
        button(180, 60, "Voice %d" % i, "muted", size=26, icon=ic_ring, icon_size=14).save(
            os.path.join(IMAGE, "config_voice%d_off.png" % i))
    for name, label in (("config_initial", "Default"), ("config_title", "Title"), ("return", "Return")):
        for st in ("normal", "over"):
            nav_button(label, st).save(os.path.join(IMAGE, "%s_%s.png" % (name, st)))


def nav_button(label, st, w=180):
    return button(w, 64, label, st, size=28, weight="Black", r=12, shadow=6)


# --- save / load -----------------------------------------------------------------------
def make_saveload():
    for name, title in (("save", "Save"), ("load", "Load")):
        c = Canvas(1920, 1080)
        screen_bg(c, alpha=234)
        header(c, title)
        c.save(os.path.join(IMAGE, "%s_base.png" % name))

    def slot(over):
        c = Canvas(650, 149)
        c.rrect((0, 0, 650, 149), 12, fill=rgba(VIOLET if over else LAV))
        c.rrect((4 + over, 4 + over, 646 - over, 145 - over), 9, fill=rgba(WHITE if not over else (250, 248, 255), 245))
        # the thumbnail well (fileDataButton draws a 234x132 thumbnail at 9, 9)
        c.rrect((9, 9, 243, 141), 4, fill=rgba(LAV_SOFT))
        c.text((126, 75), "NO DATA", font("Black", 22), rgba(WHITE), anchor="mm", tracking=2)
        c.rrect((260, 74, 626, 76), 1, fill=rgba(LAV_SOFT))
        return c
    slot(0).save(os.path.join(IMAGE, "sl_win_base.png"))
    for name in ("save", "load"):
        slot(1).save(os.path.join(IMAGE, "%s_win_over.png" % name))

    c = Canvas(95, 40)
    c.rrect((0, 0, 95, 40), 20, fill=rgba(WHITE))
    c.rrect((3, 3, 92, 37), 17, fill=rgba(VIOLET))
    c.text((47.5, 20), "NEW", font("Black", 21), rgba(WHITE), anchor="mm", tracking=2)
    c.save(os.path.join(IMAGE, "newdata.png"))

    for i in range(1, 10):
        for st in ("normal", "over"):
            button(56, 64, str(i), st, size=30, weight="Black", r=10, bw=3).save(
                os.path.join(IMAGE, "page%d_%s.png" % (i, st)))


# --- Extras ----------------------------------------------------------------------------
EXTRA_TABS = [("extra_cgmode", "CG"), ("extra_replaymode", "Replay"), ("extra_musicmode", "Music"),
              ("extra_searchmode", "Search")]


def make_extras():
    for name, title in (("cgmode", "CG Mode"), ("replaymode", "Replay")):
        c = Canvas(1920, 1080)
        screen_bg(c)
        header(c, title)
        # behind the 4x4 thumbnails (681 + 245 x, 322 + 154 y, 214x123)
        c.panel((652, 294, 1630 + 26, 907 + 28), r=18, fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
        c.save(os.path.join(IMAGE, "%s_base.png" % name), opaque=True)

    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, "Music")
    c.panel((290, 262, 800, 960))
    c.panel((840, 262, 1630, 960), fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
    # a record, above the player buttons
    cx, cy = 545, 500
    c.ellipse((cx - 170, cy - 170, cx + 170, cy + 170), fill=rgba(VIOLET))
    for r in (150, 128, 106):
        c.ellipse((cx - r, cy - r, cx + r, cy + r), outline=rgba(WHITE, 40), width=2)
    c.ellipse((cx - 70, cy - 70, cx + 70, cy + 70), fill=rgba(WHITE))
    ic_note(c, cx, cy, 80, rgba(VIOLET))
    c.save(os.path.join(IMAGE, "musicmode_base.png"), opaque=True)

    # Search: the field (searchmode.ks puts an [edit] in it), its button, and the results'
    # panel with 7 rows of 1314x76 (316 + 86 y) and the replay arrows beside them
    c = Canvas(1920, 1080)
    screen_bg(c)
    header(c, "Search")
    c.panel((290, 206, 1190, 270), r=12, fill=rgba(WHITE), border=VIOLET, bw=4, shadow=6)
    c.panel((290, 300, 1656, 936), r=18, fill=rgba(WHITE, 170), border=LAV, bw=4, shadow=0)
    c.save(os.path.join(IMAGE, "searchmode_base.png"), opaque=True)
    for st in ("normal", "over"):
        nav_button("Search", st).save(os.path.join(IMAGE, "search_go_%s.png" % st))
    for st, fill, border in (("normal", rgba(WHITE, 235), LAV), ("over", rgba(VIOLET), VIOLET)):
        c = Canvas(1314, 76)
        c.rrect((0, 0, 1314, 76), 12, fill=rgba(border))
        c.rrect((3, 3, 1311, 73), 9, fill=fill)
        c.save(os.path.join(IMAGE, "search_row_%s.png" % st))

    for name, label in EXTRA_TABS:
        for st in ("normal", "over"):
            nav_button(label, st).save(os.path.join(IMAGE, "%s_%s.png" % (name, st)))
    pages = ["Character 1", "Character 2", "Character 3", "Character 4", "Character 5", "Other"]
    for i, label in enumerate(pages):
        for st in ("normal", "over"):
            button(330, 80, label, st, size=30, r=12).save(os.path.join(IMAGE, "cgmode_page%d_%s.png" % (i, st)))

    # Replay's tabs, labelled at run time from replaylist.csv (Override.tjs), and the arrows
    # beside its tiles for a tab with more than one page of them (replay.ks)
    for st in ("normal", "over"):
        button(330, 80, "", st, size=30, r=12).save(os.path.join(IMAGE, "replay_tab_%s.png" % st))
        for name, up in (("prev", True), ("next", False)):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(64, 64)
            b.rrect((0, 0, 64, 64), 12, fill=rgba(border))
            b.rrect((3, 3, 61, 61), 9, fill=fill)
            chevron(b, 32, 32, 30, rgba(fg), up)
            b.save(os.path.join(IMAGE, "replay_%s_%s.png" % (name, st)))

    for st, border in (("normal", LAV), ("over", VIOLET)):
        c = Canvas(214, 123)
        c.rrect((0, 0, 214, 123), 4, fill=rgba(border))
        c.rrect((3, 3, 211, 120), 2, fill=rgba(LAV_PALE))
        c.text((107, 62), "?", font("Black", 56), rgba(LAV_SOFT), anchor="mm")
        c.save(os.path.join(IMAGE, "cgmode_thum_%s.png" % st))
        # an unlocked Replay scene that has no thumbnail (replaylist.csv): playable, so not a "?"
        c = Canvas(214, 123)
        c.rrect((0, 0, 214, 123), 4, fill=rgba(border))
        c.rrect((3, 3, 211, 120), 2, fill=rgba(LAV_PALE))
        c.ellipse((107 - 30, 61.5 - 30, 107 + 30, 61.5 + 30), fill=rgba(VIOLET))
        ic_play(c, 110, 61.5, 26, rgba(WHITE))
        c.save(os.path.join(IMAGE, "replay_thum_%s.png" % st))

    for i in range(12):
        for st in ("normal", "over"):
            button(730, 46, "Track %02d" % (i + 1), st, size=24, r=10, bw=3, icon=ic_note, icon_size=24).save(
                os.path.join(IMAGE, "track%02d_%s.png" % (i + 1, st)))
    for name, label, icon in (("stop", "Stop", ic_stop), ("play", "Play", ic_play), ("repeat", "Repeat", ic_repeat_one),
                              ("allrepeat", "Repeat All", ic_repeat)):
        for st in ("normal", "over"):
            button(210, 60, label, st, size=26, icon=icon, icon_size=24).save(
                os.path.join(IMAGE, "musicmode_%s_%s.png" % (name, st)))


# --- the message history ---------------------------------------------------------------
def make_history():
    c = Canvas(1920, 1080)
    c.rrect((0, 0, 1920, 1080), 0, fill=rgba(DEEP, 222))
    c.pattern((0, 0, 1920, 1080), 36, 2.2, rgba(WHITE, 16))
    # the rail for the page buttons and the scroll bar (MyHistoryLayer.tjs: x 1766-1881)
    c.rrect((1750, 42, 1898, 1037), 20, fill=rgba(WHITE, 26))
    # the scroll bar's track: its 43x48 tab moves over x 1802-1845, y 178-905
    c.rrect((1817, 198, 1830, 885), 6, fill=rgba(WHITE, 70))
    c.save(os.path.join(IMAGE, "log_base.png"))

    for name, up, double in (("first", True, True), ("uppage", True, False), ("downpage", False, False),
                             ("last", False, True)):
        for st in ("normal", "over"):
            fill, border, fg, _ = STYLE[st]
            b = Canvas(115, 58)
            b.rrect((0, 0, 115, 54), 12, fill=rgba(border))
            b.rrect((3, 3, 112, 51), 9, fill=fill)
            chevron(b, 57.5, 27, 30, rgba(fg), up, double)
            b.save(os.path.join(IMAGE, "log_%s_%s.png" % (name, st)))
    for st, fill, border in (("normal", WHITE, VIOLET), ("over", VIOLET, WHITE)):
        t = Canvas(43, 48)
        t.rrect((0, 0, 43, 48), 12, fill=rgba(border))
        t.rrect((4, 4, 39, 44), 9, fill=rgba(fill))
        for y in (18, 24, 30):
            t.rrect((14, y - 1, 29, y + 1), 1, fill=rgba(border))
        t.save(os.path.join(IMAGE, "log_bar_%s.png" % st))
    # the marks left of a line, a line high (MyHistoryLayer.tjs: lineHeight 42): playing its
    # voice, and going back to the message (compiled scenes)
    for st, fill, fg in (("normal", VIOLET, WHITE), ("over", WHITE, VIOLET)):
        p = Canvas(42, 42)
        p.ellipse((2, 2, 40, 40), fill=rgba(fill), outline=rgba(WHITE if st == "normal" else VIOLET), width=2.5)
        ic_play(p, 22.5, 21, 16, rgba(fg))
        p.save(os.path.join(IMAGE, "log_play_%s.png" % st))
    for st, fill, fg in (("normal", WHITE, VIOLET), ("over", VIOLET, WHITE)):
        p = Canvas(42, 42)
        p.ellipse((2, 2, 40, 40), fill=rgba(fill), outline=rgba(VIOLET if st == "normal" else WHITE), width=2.5)
        ic_back(p, 21, 21, 22, rgba(fg))
        p.save(os.path.join(IMAGE, "log_jump_%s.png" % st))


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


GROUPS = {"title": make_title, "logo": make_logo, "message": make_message, "config": make_config,
          "saveload": make_saveload, "extras": make_extras, "history": make_history, "star": make_star,
          "thumbs": make_thumbs, "icons": make_icons, "preview": make_preview}


def main():
    names = sys.argv[1:] or list(GROUPS)
    for n in names:
        if n not in GROUPS:
            raise SystemExit("unknown group %s; groups: %s" % (n, " ".join(GROUPS)))
        GROUPS[n]()


if __name__ == "__main__":
    main()
