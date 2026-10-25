#!/usr/bin/env python3
"""Draws Pip, the animated character of the sample's "Animated Character" demo, and makes its
voice lines.

Pip is a World character drawn from layers (KAGEnvCharacterEx, "exstand"; doc/world.txt): a
lavender mochi with an antenna, two outfits, three arm poses and six faces, whose eyes blink
and whose mouth follows its voice. This writes, into data/fgimage/pip:

- pip_<level>.txt: the layer structure, one per World level ("1" 60%, "0" 100%, "2" 150%), in
  psdlayer.tjs's text format (the first line after the canvas size is the top layer). The eyes
  and mouths are groups holding "Open Eyes"/"Half-closed Eyes"/"Closed Eyes" and
  "Closed Mouth"/"Half-open Mouth"/"Open Mouth", which is what makes them move; the top one of
  each shows while they don't.
- pip_<level>_<layer id>.png: each layer's picture, trimmed to what it draws.
- pip_info.txt: the outfits ("dress"), arm poses ("diff") and faces, by layer name.

and data/main/charinit.csv, the line that names those files, and data/main/charanim.csv, an
animation (waving: the arm poses in turn). Every shape is a signed distance field evaluated in
NumPy, so each level is drawn at its own size rather than scaled.

The voice lines (data/voice/pip000001.ogg ...) are babble: syllables of a glottal pulse through
vowel formants, in a high voice, with a consonant before most, one line for each of LINES,
encoded with ffmpeg's libvorbis.

usage: python3 tools/assets/make_pip.py [art] [voice]
"""
import math, os, shutil, subprocess, sys, tempfile, wave

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "fgimage", "pip")
VOICE = os.path.join(ROOT, "data", "voice")
CHARINIT = os.path.join(ROOT, "data", "main", "charinit.csv")
CHARANIM = os.path.join(ROOT, "data", "main", "charanim.csv")

# World levels (envinit.tjs "levels": name and zoom)
LEVELS = [("1", 0.6), ("0", 1.0), ("2", 1.5)]

# The canvas at 100%. The World puts its centre where it puts the character (the screen's centre,
# with "yoffset" => 0 in envinit.tjs), so Pip stands on GROUND, 172 below it: on the message
# window's top edge.
W, H = 640, 1168
GROUND = 756
CX = W / 2

# the theme (make_ui.py)
VIOLET = (80, 37, 255)
LAV = (166, 144, 255)
NAVY = (1, 0, 98)
WHITE = (255, 255, 255)
LINE = (46, 20, 140)          # outlines
BODY_TOP = (232, 224, 255)
BODY_BOTTOM = (184, 164, 255)
SHADE = (128, 100, 246)
PINK = (255, 140, 196)
MOUTH = (78, 18, 92)
TONGUE = (255, 124, 164)


# ---------------------------------------------------------------- shapes (signed distances)

class Shape:
    """A signed distance field: sdf(X, Y) is negative inside, in design units (100% pixels)"""
    def bbox(self):
        raise NotImplementedError

    def sdf(self, X, Y):
        raise NotImplementedError

    def grow(self, r):
        return Offset(self, r)

    def __or__(self, o):
        return Union(self, o)

    def __and__(self, o):
        return Inter(self, o)

    def __sub__(self, o):
        return Inter(self, Invert(o))


class Ellipse(Shape):
    def __init__(self, cx, cy, rx, ry=None):
        self.cx, self.cy, self.rx, self.ry = cx, cy, rx, ry if ry is not None else rx

    def bbox(self):
        return (self.cx - self.rx, self.cy - self.ry, self.cx + self.rx, self.cy + self.ry)

    def sdf(self, X, Y):
        px, py = X - self.cx, Y - self.cy
        if self.rx == self.ry:
            return np.hypot(px, py) - self.rx
        # Inigo Quilez's approximation, close enough near the edge
        k0 = np.hypot(px / self.rx, py / self.ry)
        k1 = np.hypot(px / self.rx ** 2, py / self.ry ** 2)
        return np.where(k1 > 1e-9, k0 * (k0 - 1) / np.maximum(k1, 1e-9), -min(self.rx, self.ry))


class Poly(Shape):
    """A closed polygon (exact distance, even-odd inside)"""
    def __init__(self, pts):
        self.pts = np.asarray(pts, dtype=np.float64)

    def bbox(self):
        p = self.pts
        return (p[:, 0].min(), p[:, 1].min(), p[:, 0].max(), p[:, 1].max())

    def sdf(self, X, Y):
        p = self.pts
        q = np.roll(p, -1, axis=0)
        d2 = np.full(X.shape, np.inf)
        inside = np.zeros(X.shape, dtype=bool)
        for (ax, ay), (bx, by) in zip(p, q):
            ex, ey = bx - ax, by - ay
            wx, wy = X - ax, Y - ay
            t = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-12), 0, 1)
            dx, dy = wx - ex * t, wy - ey * t
            np.minimum(d2, dx * dx + dy * dy, out=d2)
            c = ((ay > Y) != (by > Y)) & (X < (bx - ax) * (Y - ay) / (by - ay + 1e-12) + ax)
            inside ^= c
        d = np.sqrt(d2)
        return np.where(inside, -d, d)


class Stroke(Shape):
    """A line through points, width wide, with round ends and joins"""
    def __init__(self, pts, width):
        self.pts = np.asarray(pts, dtype=np.float64)
        self.r = width / 2

    def bbox(self):
        p, r = self.pts, self.r
        return (p[:, 0].min() - r, p[:, 1].min() - r, p[:, 0].max() + r, p[:, 1].max() + r)

    def sdf(self, X, Y):
        p = self.pts
        d2 = np.full(X.shape, np.inf)
        for (ax, ay), (bx, by) in zip(p[:-1], p[1:]):
            ex, ey = bx - ax, by - ay
            wx, wy = X - ax, Y - ay
            t = np.clip((wx * ex + wy * ey) / max(ex * ex + ey * ey, 1e-12), 0, 1)
            dx, dy = wx - ex * t, wy - ey * t
            np.minimum(d2, dx * dx + dy * dy, out=d2)
        return np.sqrt(d2) - self.r


class HalfPlane(Shape):
    """The side of the line a->b on the right hand (y down: below a line drawn left to right)"""
    def __init__(self, a, b):
        self.a, self.b = a, b

    def bbox(self):
        return (-1e9, -1e9, 1e9, 1e9)

    def sdf(self, X, Y):
        (ax, ay), (bx, by) = self.a, self.b
        nx, ny = by - ay, -(bx - ax)
        n = math.hypot(nx, ny)
        return ((X - ax) * nx + (Y - ay) * ny) / n


class Offset(Shape):
    def __init__(self, s, r):
        self.s, self.r = s, r

    def bbox(self):
        x0, y0, x1, y1 = self.s.bbox()
        return (x0 - self.r, y0 - self.r, x1 + self.r, y1 + self.r)

    def sdf(self, X, Y):
        return self.s.sdf(X, Y) - self.r


class Union(Shape):
    def __init__(self, *s):
        self.s = s

    def bbox(self):
        b = [s.bbox() for s in self.s]
        return (min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b))

    def sdf(self, X, Y):
        return np.minimum.reduce([s.sdf(X, Y) for s in self.s])


class Inter(Shape):
    def __init__(self, *s):
        self.s = s

    def bbox(self):
        b = [s.bbox() for s in self.s]
        return (max(x[0] for x in b), max(x[1] for x in b), min(x[2] for x in b), min(x[3] for x in b))

    def sdf(self, X, Y):
        return np.maximum.reduce([s.sdf(X, Y) for s in self.s])


class Rotated(Shape):
    """shape turned by deg degrees (clockwise on screen) around (cx, cy)"""
    def __init__(self, s, cx, cy, deg):
        self.s, self.cx, self.cy = s, cx, cy
        self.c, self.sn = math.cos(math.radians(deg)), math.sin(math.radians(deg))

    def bbox(self):
        x0, y0, x1, y1 = self.s.bbox()
        r = math.hypot(max(abs(x0 - self.cx), abs(x1 - self.cx)), max(abs(y0 - self.cy), abs(y1 - self.cy)))
        return (self.cx - r, self.cy - r, self.cx + r, self.cy + r)

    def sdf(self, X, Y):
        dx, dy = X - self.cx, Y - self.cy
        return self.s.sdf(self.cx + dx * self.c + dy * self.sn, self.cy - dx * self.sn + dy * self.c)


class Invert(Shape):
    def __init__(self, s):
        self.s = s

    def bbox(self):
        return (-1e9, -1e9, 1e9, 1e9)

    def sdf(self, X, Y):
        return -self.s.sdf(X, Y)


def bezier(*ctrl, n=24):
    """Points along a quadratic or cubic Bezier curve"""
    t = np.linspace(0, 1, n)[:, None]
    c = [np.asarray(p, dtype=np.float64) for p in ctrl]
    if len(c) == 3:
        return (1 - t) ** 2 * c[0] + 2 * (1 - t) * t * c[1] + t ** 2 * c[2]
    return (1 - t) ** 3 * c[0] + 3 * (1 - t) ** 2 * t * c[1] + 3 * (1 - t) * t ** 2 * c[2] + t ** 3 * c[3]


def arc(cx, cy, half, sag, n=24):
    """A smooth curve from (cx-half, cy) to (cx+half, cy) through (cx, cy+sag): sag > 0 dips"""
    return bezier((cx - half, cy), (cx, cy + 2 * sag), (cx + half, cy), n=n)


def star_points(cx, cy, outer, inner, n=5, rot=-90):
    pts = []
    for i in range(n * 2):
        a = math.radians(rot + i * 180 / n)
        r = outer if i % 2 == 0 else inner
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# ---------------------------------------------------------------- painting

def vgrad(top, bottom, y0, y1):
    """A vertical gradient as a colour function"""
    top, bottom = np.array(top, dtype=np.float64), np.array(bottom, dtype=np.float64)

    def f(X, Y):
        t = np.clip((Y - y0) / (y1 - y0), 0, 1)[..., None]
        return top * (1 - t) + bottom * t
    return f


class Layer:
    """One picture layer: paint operations, composited in order"""
    def __init__(self, name, group=None, opacity=255):
        self.name, self.group, self.opacity = name, group, opacity
        self.ops = []

    def fill(self, shape, colour, alpha=1.0, feather=1.0):
        self.ops.append((shape, colour, alpha, feather))
        return self

    def outlined(self, shape, colour, width=6, line=LINE, alpha=1.0):
        """shape with an outline width wide around it"""
        self.fill(shape.grow(width), line, alpha)
        self.fill(shape, colour, alpha)
        return self

    def bbox(self):
        b = [Offset(s, 2 + f).bbox() for s, c, a, f in self.ops]
        return (min(x[0] for x in b), min(x[1] for x in b), max(x[2] for x in b), max(x[3] for x in b))

    def render(self, scale):
        """the layer at scale: (left, top, RGBA image) in that level's pixels"""
        x0, y0, x1, y1 = self.bbox()
        x0 = max(0, math.floor(x0 * scale))
        y0 = max(0, math.floor(y0 * scale))
        x1 = min(math.ceil(W * scale), math.ceil(x1 * scale))
        y1 = min(math.ceil(H * scale), math.ceil(y1 * scale))
        xs = (np.arange(x0, x1) + 0.5) / scale
        ys = (np.arange(y0, y1) + 0.5) / scale
        X, Y = np.meshgrid(xs, ys)
        rgb = np.zeros(X.shape + (3,))
        a = np.zeros(X.shape)
        for shape, colour, alpha, feather in self.ops:
            cov = np.clip(0.5 - shape.sdf(X, Y) * scale / feather, 0, 1) * alpha
            if callable(colour):
                c = colour(X, Y)
            else:
                c = np.array(colour[:3], dtype=np.float64)
            # premultiplied "over"
            rgb = c * cov[..., None] + rgb * (1 - cov[..., None])
            a = cov + a * (1 - cov)
        out = np.zeros(X.shape + (4,), dtype=np.uint8)
        nz = a > 1e-6
        out[..., :3] = np.where(nz[..., None], np.clip(rgb / np.maximum(a, 1e-6)[..., None], 0, 255), 0).round()
        out[..., 3] = np.clip(a * 255, 0, 255).round()
        img = Image.fromarray(out, "RGBA")
        box = img.getbbox()
        if box is None:
            return x0, y0, None
        return x0 + box[0], y0 + box[1], img.crop(box)


# ---------------------------------------------------------------- Pip

def body_outline(n=180):
    """The body: round on top, squarer at the bottom (a superellipse whose exponent grows
    downwards)"""
    cx, cy, rx, ry = CX, 512, 246, 236
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        e = 2.0 + 1.3 * max(0.0, s)
        x = cx + rx * math.copysign(abs(c) ** (2 / e), c)
        y = cy + ry * math.copysign(abs(s) ** (2 / e), s)
        pts.append((x, y))
    return Poly(pts)


BODY = body_outline()
BODY_FILL = vgrad(BODY_TOP, BODY_BOTTOM, 280, 748)
EYE_L, EYE_R = (240, 474), (400, 474)
EYE_Y = 474
MOUTH_C = (CX, 566)
BROW_Y = 392


def body_layer():
    l = Layer("Body")
    l.outlined(BODY, BODY_FILL, 7)
    # shade on the lower right, a crescent
    l.fill(BODY - Ellipse(CX - 34, 488, 250, 238), SHADE, 0.35, feather=6)
    # soft rim light on the upper left, and a shine
    l.fill(BODY - Ellipse(CX + 16, 524, 246, 236), WHITE, 0.45, feather=4)
    l.fill(Ellipse(214, 352, 46, 26), WHITE, 0.75, feather=10)
    l.fill(Ellipse(262, 330, 14, 9), WHITE, 0.9, feather=2)
    return l


def feet_layer():
    l = Layer("Feet")
    for x in (236, 404):
        foot = Ellipse(x, 738, 64, 30)
        l.outlined(foot, vgrad(LAV, (150, 126, 250), 712, 768), 6)
    return l


def shadow_layer():
    return Layer("Shadow").fill(Ellipse(CX, GROUND + 6, 214, 22), NAVY, 0.22, feather=14)


def antenna_layer():
    l = Layer("Antenna")
    stalk = bezier((CX + 6, 300), (CX - 8, 230), (CX + 40, 190), (CX + 34, 142), n=30)
    l.fill(Stroke(stalk, 14 + 12), LINE)
    l.fill(Stroke(stalk, 14), (200, 186, 255))
    x, y = CX + 34, 128
    star = Poly(star_points(x, y, 44, 20))
    l.fill(Ellipse(x, y, 62), WHITE, 0.35, feather=24)     # glow
    l.outlined(star, vgrad(WHITE, (226, 216, 255), y - 44, y + 36), 6, VIOLET)
    l.fill(Ellipse(x - 12, y - 10, 7, 5), WHITE, 1.0)
    return l


def cheeks_layer(name="Cheeks", alpha=0.32, lines=False):
    l = Layer(name)
    for x in (172, 468):
        l.fill(Ellipse(x, 556, 40, 22), PINK, alpha, feather=8)
        if lines:
            for k in (-16, 0, 16):
                l.fill(Stroke([(x + k - 5, 566), (x + k + 7, 546)], 5), (255, 96, 160), 0.8)
    return l


def sweat_layer():
    l = Layer("Sweat")
    x, y = 508, 318
    drop = Ellipse(x, y + 10, 18, 22) | Poly([(x - 15, y + 2), (x, y - 34), (x + 15, y + 2)])
    l.outlined(drop, vgrad((236, 248, 255), (150, 210, 255), y - 34, y + 32), 4, (40, 110, 200))
    l.fill(Ellipse(x - 6, y + 6, 4, 7), WHITE, 0.9)
    return l


def arm(name, shoulder, hand):
    l = Layer(name)
    limb = Stroke([shoulder, hand], 56)
    l.outlined(limb, vgrad(BODY_TOP, BODY_BOTTOM, 300, 760), 6)
    l.fill(limb - Stroke([(shoulder[0] - 7, shoulder[1] - 9), (hand[0] - 7, hand[1] - 9)], 56), SHADE, 0.3, feather=4)
    l.fill(Ellipse(hand[0] - 8, hand[1] - 10, 9, 6), WHITE, 0.6, feather=3)
    return l


def mirror(p):
    return (W - p[0], p[1])


def arms():
    rest = ((118, 590), (82, 664))
    up = ((116, 566), (64, 474))
    wave = ((116, 560), (80, 464))
    return [
        arm("Arm L Rest", *rest),
        arm("Arm R Rest", mirror(rest[0]), mirror(rest[1])),
        arm("Arm R Wave", mirror(wave[0]), mirror(wave[1])),
        arm("Arm L Up", *up),
        arm("Arm R Up", mirror(up[0]), mirror(up[1])),
    ]


def beret_layer():
    """the second outfit: a beret, tilted, that the antenna comes out of"""
    l = Layer("Beret")
    cx, cy, ang = CX + 40, 300, -12
    band = Rotated(Ellipse(cx - 8, cy + 26, 120, 26), cx, cy, ang)
    crown = Rotated(Poly(list(bezier((cx - 140, cy + 14), (cx - 150, cy - 70), (cx + 120, cy - 96), (cx + 146, cy + 4), n=40))
                         + list(bezier((cx + 146, cy + 4), (cx + 120, cy + 34), (cx - 110, cy + 44), (cx - 140, cy + 14), n=30))),
                    cx, cy, ang)
    fill = vgrad((140, 106, 255), (70, 30, 230), cy - 70, cy + 40)
    l.outlined(band, (60, 24, 200), 6, NAVY)
    l.outlined(crown, fill, 6, NAVY)
    l.fill(crown - Rotated(Ellipse(cx + 20, cy + 24, 150, 66), cx, cy, ang), (40, 10, 170), 0.35, feather=4)
    l.fill(Rotated(Ellipse(cx - 56, cy - 34, 40, 12), cx - 56, cy - 34, ang - 10), WHITE, 0.5, feather=6)
    # the stalk on top
    l.outlined(Rotated(Ellipse(cx + 18, cy - 66, 10, 14), cx, cy, ang), (90, 50, 240), 5, NAVY)
    return l


# eyes: three frames each (Closed, Half-closed, Open) ------------------------------------

EYE_RX, EYE_RY = 42, 56


def dark_eye(l, cx, cy, clip=None, rx=EYE_RX, ry=EYE_RY):
    eye = Ellipse(cx, cy, rx, ry)
    if clip is not None:
        eye = eye & clip
    l.fill(eye.grow(5), NAVY)
    l.fill(eye, vgrad((26, 10, 92), (70, 40, 210), cy - ry, cy + ry))
    l.fill(eye & Ellipse(cx, cy + ry * 0.55, rx * 0.8, ry * 0.42), (130, 100, 255), 0.85, feather=6)
    l.fill(Ellipse(cx - rx * 0.32, cy - ry * 0.38, rx * 0.36) & eye, WHITE)
    l.fill(Ellipse(cx + rx * 0.34, cy + ry * 0.36, rx * 0.16) & eye, WHITE, 0.95)


def eye_frames(group, lid=None):
    """lid(cx, side, half) -> (a, b) for the upper lid line, side -1 left eye, +1 right eye;
    None for straight lids"""
    def lid_line(cx, side, half):
        if lid is not None:
            return lid(cx, side, half)
        y = EYE_Y - (2 if half else 26)
        return (cx - 60, y), (cx + 60, y)

    closed = Layer("Closed Eyes", group)
    half = Layer("Half-closed Eyes", group)
    opened = Layer("Open Eyes", group)
    for (cx, cy), side in ((EYE_L, -1), (EYE_R, 1)):
        closed.fill(Stroke(arc(cx, cy + 4, 40, 10), 10), NAVY)
        a, b = lid_line(cx, side, True)
        dark_eye(half, cx, cy, HalfPlane(a, b))
        half.fill(Stroke([a, b], 9) & Ellipse(cx, cy, EYE_RX + 8, EYE_RY + 8), NAVY)
        if lid is None:
            dark_eye(opened, cx, cy)
        else:
            a, b = lid_line(cx, side, False)
            dark_eye(opened, cx, cy, HalfPlane(a, b))
            opened.fill(Stroke([a, b], 9) & Ellipse(cx, cy, EYE_RX + 8, EYE_RY + 8), NAVY)
    return [opened, half, closed]   # the top one shows when blinking is off


def wide_eye_frames(group):
    closed = Layer("Closed Eyes", group)
    half = Layer("Half-closed Eyes", group)
    opened = Layer("Open Eyes", group)
    for cx, cy in (EYE_L, EYE_R):
        closed.fill(Stroke(arc(cx, cy + 4, 42, 10), 10), NAVY)
        ball = Ellipse(cx, cy, 50, 54)
        for l, clip in ((opened, None), (half, HalfPlane((cx - 60, cy - 4), (cx + 60, cy - 4)))):
            b = ball if clip is None else ball & clip
            l.fill(b.grow(6), NAVY)
            l.fill(b, vgrad(WHITE, (226, 220, 255), cy - 54, cy + 54))
            l.fill(Ellipse(cx, cy + 4, 17) & b, (26, 10, 92))
            l.fill(Ellipse(cx - 5, cy - 2, 5) & b, WHITE)
        half.fill(Stroke([(cx - 60, cy - 4), (cx + 60, cy - 4)], 9) & Ellipse(cx, cy, 58, 62), NAVY)
    return [opened, half, closed]   # the top one shows when blinking is off


def droop_lid(cx, side, half):
    # sad: the outer end lower
    inner, outer = (cx - side * 60, cx + side * 60)
    yi, yo = (EYE_Y - 8, EYE_Y + 6) if half else (EYE_Y - 40, EYE_Y - 8)
    a, b = (inner, yi), (outer, yo)
    return (a, b) if a[0] < b[0] else (b, a)


def glare_lid(cx, side, half):
    # angry: the inner end lower
    inner, outer = (cx - side * 60, cx + side * 60)
    yi, yo = (EYE_Y + 6, EYE_Y - 8) if half else (EYE_Y - 6, EYE_Y - 40)
    a, b = (inner, yi), (outer, yo)
    return (a, b) if a[0] < b[0] else (b, a)


def happy_eyes():
    l = Layer("Eyes Happy")
    for cx, cy in (EYE_L, EYE_R):
        l.fill(Stroke(arc(cx, cy + 8, 40, -16), 11), NAVY)
    return l


# mouths ----------------------------------------------------------------------------------

def open_mouth(l, cx, cy, half, depth, sag=3, frown=False):
    """a D-shaped open mouth (upside down for frown): the flat side at cy"""
    if not frown:
        top = arc(cx, cy, half, sag)
        bottom = bezier((cx + half, cy), (cx + half * 0.9, cy + depth * 1.3), (cx - half * 0.9, cy + depth * 1.3),
                        (cx - half, cy))
    else:
        top = arc(cx, cy, half, -sag)
        bottom = bezier((cx + half, cy), (cx + half * 0.9, cy - depth * 1.3), (cx - half * 0.9, cy - depth * 1.3),
                        (cx - half, cy))
    m = Poly(list(top) + list(bottom))
    l.fill(m.grow(5), NAVY)
    l.fill(m, MOUTH)
    ty = cy + depth * 0.95 if not frown else cy - depth * 0.15
    l.fill(Ellipse(cx, ty, half * 0.62, max(depth * 0.42, 6)) & m, TONGUE)


def mouth_frames(group, kind):
    cx, cy = MOUTH_C
    closed = Layer("Closed Mouth", group)
    half = Layer("Half-open Mouth", group)
    opened = Layer("Open Mouth", group)
    if kind == "smile":
        closed.fill(Stroke(arc(cx, cy, 24, 8), 7), NAVY)
        open_mouth(half, cx, cy - 4, 20, 13)
        open_mouth(opened, cx, cy - 6, 25, 28)
    elif kind == "grin":
        closed.fill(Stroke(arc(cx, cy - 4, 40, 14), 7), NAVY)
        open_mouth(half, cx, cy - 6, 36, 18, sag=6)
        open_mouth(opened, cx, cy - 8, 42, 34, sag=8)
    elif kind == "o":
        for l, rx, ry in ((closed, 11, 9), (half, 15, 17), (opened, 21, 28)):
            m = Ellipse(cx, cy + ry * 0.4, rx, ry)
            l.fill(m.grow(5), NAVY)
            l.fill(m, MOUTH)
            if ry > 12:
                l.fill(Ellipse(cx, cy + ry * 1.05, rx * 0.65, ry * 0.4) & m, TONGUE)
    elif kind == "frown":
        closed.fill(Stroke(arc(cx, cy + 8, 22, -8), 7), NAVY)
        open_mouth(half, cx, cy + 12, 20, 13, frown=True)
        open_mouth(opened, cx, cy + 18, 25, 26, frown=True)
    return [closed, half, opened]   # the top one shows when lip-sync is off


# brows -----------------------------------------------------------------------------------

def brows(name, kind):
    l = Layer(name)
    for (cx, cy), side in ((EYE_L, -1), (EYE_R, 1)):
        inner, outer = cx - side * 30, cx + side * 30
        y = BROW_Y
        if kind == "neutral":
            pts = bezier((outer, y + 4), (cx, y - 10), (inner, y + 2), n=16)
        elif kind == "raised":
            pts = bezier((outer, y - 10), (cx, y - 30), (inner, y - 14), n=16)
        elif kind == "worried":
            pts = bezier((outer, y + 8), (cx, y), (inner, y - 16), n=16)
        else:  # angry
            pts = bezier((outer, y - 10), (cx, y - 4), (inner, y + 14), n=16)
        l.fill(Stroke(pts, 10), NAVY)
    return l


# ---------------------------------------------------------------- the layer tree

def build():
    """[(group name or None, Layer)], top to bottom, and the group names"""
    groups = ["Mouth", "Mouth Grin", "Mouth O", "Mouth Frown", "Eyes", "Eyes Wide", "Eyes Droop", "Eyes Glare"]
    layers = [sweat_layer(), cheeks_layer("Blush", 0.62, True),
              brows("Brows Neutral", "neutral"), brows("Brows Raised", "raised"),
              brows("Brows Worried", "worried"), brows("Brows Angry", "angry")]
    layers += mouth_frames("Mouth", "smile") + mouth_frames("Mouth Grin", "grin")
    layers += mouth_frames("Mouth O", "o") + mouth_frames("Mouth Frown", "frown")
    layers += eye_frames("Eyes") + wide_eye_frames("Eyes Wide")
    layers += eye_frames("Eyes Droop", droop_lid) + eye_frames("Eyes Glare", glare_lid)
    layers += [happy_eyes(), cheeks_layer()]
    layers += arms()
    layers += [beret_layer(), body_layer(), antenna_layer(), feet_layer(), shadow_layer()]
    return groups, layers


INFO = """# Pip (make_pip.py): outfits, arm poses and faces, by layer name
common\tShadow
common\tFeet
common\tAntenna
common\tBody
common\tCheeks
dress\tplain\tdiff\trest\tArm L Rest
dress\tplain\tdiff\trest\tArm R Rest
dress\tplain\tdiff\twave\tArm L Rest
dress\tplain\tdiff\twave\tArm R Wave
dress\tplain\tdiff\tcheer\tArm L Up
dress\tplain\tdiff\tcheer\tArm R Up
dress\tberet\tbase\tBeret
dress\tberet\tdiff\trest\tArm L Rest
dress\tberet\tdiff\trest\tArm R Rest
dress\tberet\tdiff\twave\tArm L Rest
dress\tberet\tdiff\twave\tArm R Wave
dress\tberet\tdiff\tcheer\tArm L Up
dress\tberet\tdiff\tcheer\tArm R Up
face\tneutral\tbase\tBrows Neutral
face\tneutral\teye\tEyes
face\tneutral\tlip\tMouth
face\tsmile\tbase\tBrows Neutral
face\tsmile\teye\tEyes
face\tsmile\tlip\tMouth Grin
face\tlaugh\tbase\tBrows Raised
face\tlaugh\tbase\tBlush
face\tlaugh\teyeimage\tEyes Happy
face\tlaugh\tlip\tMouth Grin
face\tsurprised\tbase\tBrows Raised
face\tsurprised\teye\tEyes Wide
face\tsurprised\tlip\tMouth O
face\tsad\tbase\tBrows Worried
face\tsad\tbase\tSweat
face\tsad\teye\tEyes Droop
face\tsad\tlip\tMouth Frown
face\tangry\tbase\tBrows Angry
face\tangry\teye\tEyes Glare
face\tangry\tlip\tMouth Frown
"""

HEADER = "#layer_type\tname\tleft\ttop\twidth\theight\ttype\topacity\tvisible\tlayer_id\tgroup_layer_id\tbase\timages"
LT_PSNORMAL = 13   # what psdfile reports for a normal layer; psdlayer.tjs draws it as ltAlpha


def make_art():
    groups, layers = build()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    gid = {g: 1000 + i for i, g in enumerate(groups)}
    for level, scale in LEVELS:
        lines = [HEADER, "\t\t\t\t%d\t%d" % (round(W * scale), round(H * scale))]
        for i, layer in enumerate(layers):
            lid = i + 1
            left, top, img = layer.render(scale)
            if img is None:
                sys.exit("layer %s draws nothing" % layer.name)
            img.save(os.path.join(OUT, "pip_%s_%d.png" % (level, lid)), optimize=True)
            group = str(gid[layer.group]) if layer.group else ""
            lines.append("0\t%s\t%d\t%d\t%d\t%d\t%d\t%d\t1\t%d\t%s" % (
                layer.name, left, top, img.width, img.height, LT_PSNORMAL, layer.opacity, lid, group))
        for g in groups:
            lines.append("2\t%s\t0\t0\t0\t0\t%d\t255\t1\t%d\t" % (g, LT_PSNORMAL, gid[g]))
        with open(os.path.join(OUT, "pip_%s.txt" % level), "w", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        print("level %s: %d layers" % (level, len(layers)), flush=True)
    with open(os.path.join(OUT, "pip_info.txt"), "w", newline="\n") as f:
        f.write(INFO)
    # character, pose, files, x and y offset (at 100%, from the canvas centre to the anchor)
    with open(CHARINIT, "w", newline="\n") as f:
        f.write("# Characters drawn from layers (doc/world.txt; made by tools/assets/make_pip.py):\n"
                "# character,pose,files,xoffset,yoffset\n")
        f.write("pip,standard,pip,0,0\n")
    # animations, steps of a command (or wait, or loop back to a step) and how long it lasts (ms)
    with open(CHARANIM, "w", newline="\n") as f:
        f.write("# Animations of characters drawn from layers (doc/world.txt; made by tools/assets/make_pip.py):\n"
                "# character,animation,command,time\n")
        f.write("pip,waving,wave,280\npip,waving,rest,280\npip,waving,loop,0\n")


# ---------------------------------------------------------------- voice

RATE = 44100

# the lines, in the order of their voice numbers (data/scenario/anim.ks)
LINES = [
    "Hi! I'm Pip.",
    "I blink by myself, and my mouth moves with my voice.",
    "Oh! A new face!",
    "Oops, did I startle you?",
    "How do I look?",
    "Ha ha! I like it!",
    "Hey! I liked that hat!",
    "Bye for now!",
]

# vowel formants (Hz), raised for a small voice
VOWELS = {"a": (850, 1350, 2700), "i": (330, 2600, 3300), "u": (380, 1200, 2500),
          "e": (560, 2100, 2900), "o": (520, 950, 2600)}


def resonator(x, f, bw):
    """a two-pole resonator at f Hz"""
    r = math.exp(-math.pi * bw / RATE)
    a1, a2 = 2 * r * math.cos(2 * math.pi * f / RATE), -r * r
    g = 1 - r
    y = np.zeros_like(x)
    y1 = y2 = 0.0
    for i in range(len(x)):
        v = g * x[i] + a1 * y1 + a2 * y2
        y[i] = v
        y2, y1 = y1, v
    return y


def syllable_count(text):
    words = [w.strip(".,!?'").lower() for w in text.split()]
    n = 0
    for w in words:
        groups, prev = 0, False
        for ch in w:
            v = ch in "aeiouy"
            if v and not prev:
                groups += 1
            prev = v
        n += max(1, groups)
    return n, len(words)


def bandpass_noise(rng, n, f, bw):
    return resonator(rng.standard_normal(n), f, bw)


def consonant(rng):
    """a short consonant: a plosive's burst, a fricative's hiss or a nasal's hum"""
    kind = rng.choice(["p", "t", "k", "s", "sh", "m", "n", ""], p=[.15, .15, .12, .12, .08, .14, .12, .12])
    if kind == "":
        return np.zeros(0)
    if kind in ("p", "t", "k"):
        n = int(RATE * rng.uniform(0.012, 0.02))
        f = {"p": 1200, "t": 4200, "k": 2400}[kind]
        x = bandpass_noise(rng, n, f, 1800) * np.exp(-np.arange(n) / (n / 4))
        return np.concatenate([np.zeros(int(RATE * 0.012)), x * 0.5])
    if kind in ("s", "sh"):
        n = int(RATE * rng.uniform(0.05, 0.08))
        f = 6200 if kind == "s" else 3200
        return bandpass_noise(rng, n, f, 2200) * np.hanning(n) * 0.22
    n = int(RATE * rng.uniform(0.04, 0.06))   # m, n: a low hum
    t = np.arange(n) / RATE
    hum = np.sin(2 * math.pi * 260 * t) + 0.3 * np.sin(2 * math.pi * 520 * t)
    return hum * np.hanning(n) * 0.18


def babble(text, seed):
    rng = np.random.default_rng(seed)
    nsyl, nwords = syllable_count(text)
    question = text.rstrip().endswith("?")
    exclaim = text.rstrip().endswith("!")
    # words of roughly the text's syllables
    sizes = [1] * nwords
    for _ in range(nsyl - nwords):
        sizes[rng.integers(nwords)] += 1
    out = [np.zeros(int(RATE * 0.08))]
    k = 0
    for wi, size in enumerate(sizes):
        for si in range(size):
            prog = k / max(nsyl - 1, 1)
            dur = rng.uniform(0.09, 0.14)
            if si == size - 1 and wi == len(sizes) - 1:
                dur *= 1.7
            n = int(RATE * dur)
            t = np.arange(n) / RATE
            # pitch: a high voice, falling, rising at a question, bright on an exclamation
            f0 = 440 + 50 * math.sin(k * 1.7) - 60 * prog
            if question:
                f0 += 160 * prog ** 2
            if exclaim and prog > 0.7:
                f0 += 40
            f0 = f0 * (1 + 0.03 * np.sin(2 * math.pi * 5.5 * t) + 0.04 * (t / dur) * (-1 if si == size - 1 else 1))
            phase = np.cumsum(f0 / RATE) % 1.0
            # a glottal pulse (open for 60% of each period, then closed) and a little breath
            open_q = 0.6
            src = np.where(phase < open_q, np.sin(math.pi * phase / open_q) ** 2, 0.0)
            src = np.diff(src, prepend=0.0) * 20 + 0.02 * rng.standard_normal(n)
            vowel = "aiueo"[rng.integers(5)]
            fs = VOWELS[vowel]
            v = (resonator(src, fs[0] * 1.15, 80) + 1.1 * resonator(src, fs[1] * 1.15, 110)
                 + 0.7 * resonator(src, fs[2] * 1.1, 160) + 0.3 * resonator(src, 4300, 250))
            env = np.minimum(1, t / 0.012) * np.minimum(1, (dur - t) / 0.035).clip(0)
            env *= 0.8 + 0.2 * np.sin(math.pi * t / dur)
            v = v / (np.max(np.abs(v)) + 1e-9) * env * rng.uniform(0.45, 1.0)   # some syllables softer
            out.append(np.concatenate([consonant(rng), v]))
            k += 1
        out.append(np.zeros(int(RATE * rng.uniform(0.06, 0.11))))
    out.append(np.zeros(int(RATE * 0.12)))
    y = np.concatenate(out)
    # soften the very top (above 9 kHz) and normalise
    y = np.convolve(y, np.array([0.25, 0.5, 0.25]), "same")
    y = y / np.max(np.abs(y)) * 0.6
    return y


def make_voice():
    if not shutil.which("ffmpeg"):
        sys.exit("make_pip.py voice needs ffmpeg (with libvorbis)")
    work = tempfile.mkdtemp(prefix="make-pip-")
    try:
        for i, text in enumerate(LINES):
            y = babble(text, 20261025 + i)
            wav = os.path.join(work, "%d.wav" % i)
            with wave.open(wav, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(RATE)
                w.writeframes((y * 32767).astype("<i2").tobytes())
            out = os.path.join(VOICE, "pip%06d.ogg" % (i + 1))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "3",
                            "-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1", out],
                           check=True)
            print("voice %d: %.1f s, %s" % (i + 1, len(y) / RATE, text), flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    what = sys.argv[1:] or ["art", "voice"]
    for w in what:
        {"art": make_art, "voice": make_voice}[w]()


if __name__ == "__main__":
    main()
