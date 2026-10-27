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
  each shows while they don't. The plain face's mouth also has one for each vowel, "Mouth A"
  ... "Mouth O", which show while the voice says that vowel.
- pip_<level>_<layer id>.png: each layer's picture, trimmed to what it draws.
- pip_info.txt: the outfits ("dress"), arm poses ("diff") and faces, by layer name.

and data/main/charinit.csv, the line that names those files, and data/main/charanim.csv, an
animation (waving: the arm poses in turn). Every shape is a signed distance field evaluated in
NumPy, so each level is drawn at its own size rather than scaled.

With `voice`, it also makes the voice lines, data/voice/pip000001.ogg ... (one for each of
LINES), spoken by Kokoro, a speech synthesizer (Kokoro-82M, Apache-2.0; run with ONNX Runtime,
the model downloaded once from kokoro-onnx's release into tools/assets/.cache/kokoro) and
encoded with ffmpeg's libvorbis, each with a lip track, data/voice/pip000001.lip ...: the mouth
for each vowel (and closed for m, b and p) from when the model says each phoneme, and how open
from the voice's loudness there, which KAGEnvCharacterEx.tjs follows while the voice plays. `vowels` measures how often the engine's
WaveSoundBuffer.getVowel, which a voice without a lip track relies on, hears those vowels.

usage: python3 tools/assets/make_pip.py [art] [voice] [vowels]   (art by default)
"""
import math, os, shutil, subprocess, sys, tempfile, urllib.request, wave

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


def teeth(l, m, cx, y0, y1, half):
    """upper teeth: a white band from y0 down to y1, inside the open mouth m"""
    band = Poly([(cx - half, y0), (cx + half, y0), (cx + half, y1), (cx - half, y1)])
    l.fill(band & m, WHITE, 0.95)


def vowel_frames(group):
    """A mouth for each vowel (KAGEnvCharacterEx.tjs's lipVowelLayerNames): while Pip speaks,
    the one for the vowel its voice says shows in place of the half-open and open mouths"""
    cx, cy = MOUTH_C
    a, i, u, e, o = (Layer("Mouth %s" % v, group) for v in "AIUEO")
    open_mouth(a, cx, cy - 8, 27, 34)                       # wide open
    for l, half, depth, sag in ((i, 32, 9, 5), (e, 28, 17, 5)):
        top = arc(cx, cy - 4, half, sag)
        bottom = bezier((cx + half, cy - 4), (cx + half * 0.9, cy - 4 + depth * 1.3),
                        (cx - half * 0.9, cy - 4 + depth * 1.3), (cx - half, cy - 4))
        m = Poly(list(top) + list(bottom))
        l.fill(m.grow(5), NAVY)
        l.fill(m, MOUTH)
        teeth(l, m, cx, cy - 12, cy - 4 + sag + (5 if l is i else 6), half)
        if l is e:
            l.fill(Ellipse(cx, cy - 4 + depth * 0.95, half * 0.55, depth * 0.38) & m, TONGUE)
    for l, rx, ry, dy in ((u, 9, 10, 2), (o, 17, 23, 6)):   # rounded: a small pout, a big O
        m = Ellipse(cx, cy + dy, rx, ry)
        l.fill(m.grow(5), NAVY)
        l.fill(m, MOUTH)
        if ry > 12:
            l.fill(Ellipse(cx, cy + dy + ry * 0.62, rx * 0.65, ry * 0.36) & m, TONGUE)
    for l in (a, i, u, e, o):
        l.added = True   # numbered after the layers made before them (make_art)
    return [a, i, u, e, o]


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
    layers += mouth_frames("Mouth", "smile") + vowel_frames("Mouth") + mouth_frames("Mouth Grin", "grin")
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
    # layer IDs (the pictures' names) top down, but the layers added later (the vowel mouths)
    # after the others, so the older pictures keep their names
    ids = {}
    for layer in sorted(layers, key=lambda l: getattr(l, "added", False)):
        ids[id(layer)] = len(ids) + 1
    for level, scale in LEVELS:
        lines = [HEADER, "\t\t\t\t%d\t%d" % (round(W * scale), round(H * scale))]
        for layer in layers:
            lid = ids[id(layer)]
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

# The lines, in the order of their voice numbers (data/scenario/anim.ks), each with what Kokoro
# says: phonemes in misaki's notation, which Kokoro was trained on, from misaki's US dictionary
# (A = eɪ, I = aɪ, O = oʊ, W = aʊ, Y = ɔɪ, ᵊ a short schwa, ˈ and ˌ stress the vowel after them)
LINES = [
    ("Hi! I'm Pip.", "hˈI! ˌIm pˈɪp."),
    ("I blink by myself, and my mouth moves with my voice.",
     "ˌI blˈɪŋk bI mIsˈɛlf, ænd mI mˈWθ mˈuvz wɪð mI vˈYs."),
    ("Oh! A new face!", "ˈO! ɐ nˈu fˈAs!"),
    ("Oops, did I startle you?", "ˈups, dˈɪd ˌI stˈɑɹɾᵊl ju?"),
    ("How do I look?", "hˌW dˈu ˌI lˈʊk?"),
    ("Ha ha! I like it!", "hˈɑ hˈɑ! ˌI lˈIk ɪt!"),
    ("Hey! I liked that hat!", "hˈA! ˌI lˈIkt ðæt hˈæt!"),
    ("Bye for now!", "bˈI fɔɹ nˈW!"),
]

# The speech synthesizer: Kokoro (Kokoro-82M v1.0, Apache-2.0), run with ONNX Runtime from
# kokoro-onnx's release of the model (MIT), downloaded once into tools/assets/.cache/kokoro
KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_FILES = ["kokoro-v1.0.onnx", "voices-v1.0.bin"]
KOKORO_VOICE = "af_heart"
KOKORO_SPEED = 1.0
KOKORO_RATE = 24000
KOKORO_FRAME = 600   # samples in each unit of the phoneme durations the model works out
# The sound runs ahead of the durations: a phoneme is heard about 60 ms before they put it (the
# lip tracks match the voices' loudness best that much earlier; Kokoro's own pipeline takes 75 ms
# off its timestamps)
KOKORO_LEAD = 0.06
# the model's token for each phoneme and mark English uses (its vocabulary, config.json "vocab")
KOKORO_TOKENS = {
    ";": 1, ":": 2, ",": 3, ".": 4, "!": 5, "?": 6, "—": 9, "…": 10, '"': 11, "(": 12, ")": 13,
    "“": 14, "”": 15, " ": 16, "A": 24, "I": 25, "O": 31, "W": 39, "Y": 41, "ᵊ": 42, "a": 43,
    "b": 44, "d": 46, "e": 47, "f": 48, "h": 50, "i": 51, "j": 52, "k": 53, "l": 54, "m": 55,
    "n": 56, "o": 57, "p": 58, "s": 61, "t": 62, "u": 63, "v": 64, "w": 65, "z": 68, "ɑ": 69,
    "ɐ": 70, "æ": 72, "ɔ": 76, "ð": 81, "ʤ": 82, "ə": 83, "ɚ": 85, "ɛ": 86, "ɜ": 87, "ɡ": 92,
    "ɪ": 102, "ŋ": 112, "θ": 119, "ɹ": 123, "ɾ": 125, "ʃ": 131, "ʧ": 133, "ʊ": 135, "ʌ": 138,
    "ʒ": 147, "ʔ": 148, "ˈ": 156, "ˌ": 157, "ᵻ": 177,
}

# The mouth each phoneme makes, for the voice's lip track (KAGEnvCharacterEx.tjs reads
# data/voice/<voice>.lip): a vowel, or two for a diphthong (half its time each), "n" where the
# lips close (m, b, p), and for anything else "-", a mouth only as open as the voice is loud
MOUTHS = {"ɑ": "a", "æ": "a", "ʌ": "a", "ɐ": "a", "a": "a", "i": "i", "ɪ": "i", "ᵻ": "i",
          "u": "u", "ʊ": "u", "w": "u", "ɛ": "e", "ɜ": "e", "e": "e", "ɔ": "o", "o": "o",
          "I": "ai", "W": "au", "A": "ei", "O": "ou", "Y": "oi", "m": "n", "b": "n", "p": "n"}


def protobuf_fields(b, i, end):
    """the fields of a protocol buffer message in b[i:end]: (number, wire type, value or start,
    end of a length-delimited one)"""
    def varint(i):
        r = s = 0
        while True:
            c = b[i]
            i += 1
            r |= (c & 0x7f) << s
            s += 7
            if c < 0x80:
                return r, i
    while i < end:
        key, i = varint(i)
        f, wt = key >> 3, key & 7
        if wt == 0:
            v, i = varint(i)
            yield f, wt, v, i
        elif wt == 2:
            n, i = varint(i)
            yield f, wt, i, i + n
            i += n
        elif wt in (1, 5):
            n = 8 if wt == 1 else 4
            yield f, wt, i, i + n
            i += n
        else:
            raise ValueError("not a protocol buffer")


def protobuf_varint(n):
    out = bytearray()
    while True:
        c, n = n & 0x7f, n >> 7
        out.append(c | 0x80 if n else c)
        if not n:
            return bytes(out)


def kokoro_timed(model):
    """The ONNX model (bytes) with the phonemes' durations as a second output: the frames the
    model gives each token (the rounded, clipped durations it builds the audio from), which it
    works out but doesn't return. Edited as a protocol buffer, so the onnx package isn't needed"""
    def ld(f, payload):
        return protobuf_varint(f << 3 | 2) + protobuf_varint(len(payload)) + payload
    mv = memoryview(model)
    i = 0
    while i < len(mv):
        f, wt, s, e = next(protobuf_fields(mv, i, len(mv)))
        if f != 7:   # ModelProto.graph
            i = e
            continue
        # GraphProto.node (1): NodeProto's input (1), output (2) and op_type (4); find the Clip
        # node that takes the output of the Round node
        nodes = []
        for g, gwt, gs, ge in protobuf_fields(mv, s, e):
            if g == 1:
                node = {"in": [], "out": [], "op": ""}
                for h, hwt, hs, he in protobuf_fields(mv, gs, ge):
                    if h in (1, 2):
                        node["in" if h == 1 else "out"].append(bytes(mv[hs:he]).decode())
                    elif h == 4:
                        node["op"] = bytes(mv[hs:he]).decode()
                nodes.append(node)
        rounded = {o for n in nodes if n["op"] == "Round" for o in n["out"]}
        name = next((n["out"][0] for n in nodes if n["op"] == "Clip" and n["in"] and n["in"][0] in rounded), None)
        if name is None:
            sys.exit("make_pip.py: %s isn't the Kokoro model it expects (no rounded durations)" % KOKORO_FILES[0])
        # GraphProto.output (12): ValueInfoProto { name: 1, type: 2 { tensor_type: 1 { elem_type: 1 = FLOAT } } }
        tensor = ld(1, protobuf_varint(1 << 3) + protobuf_varint(1))
        extra = ld(12, ld(1, name.encode()) + ld(2, tensor))
        # the graph again, longer by that
        return b"".join([mv[:i], protobuf_varint(7 << 3 | 2), protobuf_varint(e - s + len(extra)),
                         mv[s:e], extra, mv[e:]])
    sys.exit("make_pip.py: %s has no graph" % KOKORO_FILES[0])


def kokoro():
    """ONNX Runtime's session of Kokoro, timed (kokoro_timed), and its voices"""
    try:
        import onnxruntime as ort
    except ImportError:
        sys.exit("make_pip.py voice needs ONNX Runtime (pip install onnxruntime)")
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "kokoro")
    os.makedirs(folder, exist_ok=True)
    for name in KOKORO_FILES:
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            print("downloading %s%s" % (KOKORO_URL, name), flush=True)
            with urllib.request.urlopen(KOKORO_URL + name) as r, open(path + ".part", "wb") as f:
                shutil.copyfileobj(r, f)
            os.replace(path + ".part", path)
    with open(os.path.join(folder, KOKORO_FILES[0]), "rb") as f:
        model = kokoro_timed(f.read())
    options = ort.SessionOptions()
    options.intra_op_num_threads = 1   # the same samples every time
    sess = ort.InferenceSession(model, options, providers=["CPUExecutionProvider"])
    return sess, np.load(os.path.join(folder, KOKORO_FILES[1]))


def speak(sess, voices, phonemes):
    """the line's samples and, for each phoneme, (phoneme, first sample, sample after it)"""
    missing = sorted(set(c for c in phonemes if c not in KOKORO_TOKENS))
    if missing:
        sys.exit("make_pip.py: no token for %s in %r" % (" ".join(missing), phonemes))
    tokens = [KOKORO_TOKENS[c] for c in phonemes]
    style = voices[KOKORO_VOICE][len(tokens) - 1]   # a style for each length
    y, dur = sess.run(None, {"tokens": np.array([[0, *tokens, 0]], np.int64), "style": style,
                             "speed": np.array([KOKORO_SPEED], np.float32)})
    # the durations include the pads around the tokens (0, first and last)
    edges = np.concatenate([[0], np.cumsum(dur.ravel().astype(np.int64) * KOKORO_FRAME)])
    edges = np.maximum(edges - int(KOKORO_RATE * KOKORO_LEAD), 0)
    return y.ravel().astype(np.float64), [(c, int(edges[i + 1]), int(edges[i + 2])) for i, c in enumerate(phonemes)]


def trim(y, phones):
    """the voice from 60 ms before it starts to 150 ms after it ends"""
    frame = KOKORO_RATE // 100
    rms = np.sqrt(np.convolve(y ** 2, np.ones(frame) / frame, "same"))
    loud = np.nonzero(rms > rms.max() * 0.02)[0]
    a = max(0, loud[0] - int(KOKORO_RATE * 0.06))
    b = min(len(y), loud[-1] + int(KOKORO_RATE * 0.15))
    return y[a:b], [(c, s - a, e - a) for c, s, e in phones]


def normalise(y):
    """the voice at an RMS of 0.1 where it's voiced (KAGEnvCharacterEx.tjs opens the mouth half
    from 0.03 and wide from 0.12), its peaks no higher than 0.95"""
    frame = KOKORO_RATE // 50
    rms = np.array([math.sqrt(float(np.mean(y[i:i + frame] ** 2))) for i in range(0, len(y) - frame, frame)])
    voiced = rms[rms > rms.max() * 0.1]
    gain = min(0.1 / math.sqrt(float(np.mean(voiced ** 2))), 0.95 / float(np.max(np.abs(y))))
    return y * gain


def lip_track(phones, y):
    """[(ms, mouth, open)]: the mouth from each time on and how open it is (0 closed, 1 half, 2
    wide, by the voice's RMS there, at KAGEnvCharacterEx.tjs's lipSyncHalfLevel 0.03 and
    lipSyncOpenLevel 0.12), as a .lip file lists them"""
    # a stress mark gets time of its own, which is the start of the vowel after it
    voiced, start = [], None
    for c, s, e in phones:
        if c in "ˈˌ":
            start = s if start is None else start
            continue
        voiced.append((c, s if start is None else start, e))
        start = None
    marks = [(0, "-")]
    for c, s, e in voiced:
        m = MOUTHS.get(c, "-")
        if len(m) == 2:
            marks += [(s, m[0]), ((s + e) // 2, m[1])]
        else:
            marks.append((s, m))
    marks.append((len(y), "-"))   # after the end: silence
    track = []
    for k, (s, m) in enumerate(marks[:-1]):
        e = marks[k + 1][0]
        s, e = max(0, min(s, len(y))), max(0, min(e, len(y)))
        rms = math.sqrt(float(np.mean(y[s:e] ** 2))) if e > s else 0.0
        level = 0 if m == "n" else 2 if rms > 0.12 else 1 if rms > 0.03 else 0
        ms = round(s * 1000 / KOKORO_RATE)
        while track and track[-1][0] >= ms:   # the later of two at one time
            track.pop()
        if not track or track[-1][1:] != (m, level):
            track.append((ms, m, level))
    return track


def read_lip(path):
    track = []
    with open(path, encoding="ascii") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                ms, mouth = line.split("\t")[:2]
                track.append((int(ms), mouth))   # (how open it is, a third column, isn't needed here)
    return track


def make_voice():
    if not shutil.which("ffmpeg"):
        sys.exit("make_pip.py voice needs ffmpeg (with libvorbis)")
    sess, voices = kokoro()
    work = tempfile.mkdtemp(prefix="make-pip-")
    try:
        for i, (text, phonemes) in enumerate(LINES):
            y, phones = speak(sess, voices, phonemes)
            y, phones = trim(y, phones)
            y = normalise(y)
            name = "pip%06d" % (i + 1)
            wav = os.path.join(work, name + ".wav")
            with wave.open(wav, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(KOKORO_RATE)
                w.writeframes((np.clip(y, -1, 1) * 32767).round().astype("<i2").tobytes())
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "4",
                            "-fflags", "+bitexact", "-flags:a", "+bitexact", "-map_metadata", "-1",
                            os.path.join(VOICE, name + ".ogg")], check=True)
            track = lip_track(phones, y)
            with open(os.path.join(VOICE, name + ".lip"), "w", encoding="ascii", newline="\n") as f:
                f.write("# The mouth over %s.ogg, from when Kokoro says each phoneme (tools/assets/make_pip.py)\n"
                        "# ms, then the mouth from then on (a i u e o, n for the lips closed, - for any other sound)\n"
                        "# and how open it is (0 closed, 1 half, 2 wide), by how loud the voice is there\n"
                        % name)
                for ms, mouth, level in track:
                    f.write("%d\t%s\t%d\n" % (ms, mouth, level))
            print("voice %d: %.1f s, %d mouths, %s" % (i + 1, len(y) / KOKORO_RATE, len(track), text), flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def engine_vowel(x, rate):
    """the engine's WaveSoundBuffer.getVowel (QueueSoundBufferImpl.cpp) on 1024 samples: the
    energy around each vowel's F1 and F2 (+-15% + 50 Hz) of a Hann-windowed FFT, as weights that
    add up to 1, or None for silence"""
    n = 1024
    w = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(n) / (n - 1))
    mag = np.abs(np.fft.rfft(x[:n] * w)) / n

    def around(hz):
        bw = hz * 0.15 + 50
        i0, i1 = max(1, int((hz - bw) * n / rate)), min(n // 2, int((hz + bw) * n / rate))
        return float(np.sum(mag[i0:i1] ** 2)) if i1 > i0 else 0.0
    f1, f2 = (800, 300, 350, 500, 500), (1200, 2300, 1200, 1900, 900)
    sc = [around(f1[v]) + around(f2[v]) for v in range(5)]
    total = sum(sc)
    return None if total <= 1e-9 else [x / total for x in sc]


def measure_vowels():
    """How often the engine's getVowel names the vowel the lip track says, every 30 ms where
    lip-sync opens the mouth (an RMS over lipSyncHalfLevel, 0.03): what a voice without a lip
    track would show"""
    right = total = 0
    picks = [0] * 5
    for i, (text, _) in enumerate(LINES):
        name = os.path.join(VOICE, "pip%06d" % (i + 1))
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", name + ".ogg", "-f", "f32le", "-ac", "1",
                              "-ar", str(KOKORO_RATE), "-"], check=True, capture_output=True).stdout
        y = np.frombuffer(raw, "<f4").astype(np.float64)
        track = read_lip(name + ".lip")
        r = t = 0
        for pos in range(0, len(y) - 1024, int(KOKORO_RATE * 0.03)):
            ms = (pos + 512) * 1000 / KOKORO_RATE
            mouth = [m for s, m in track if s <= ms][-1]
            seg = y[pos:pos + 1024]
            if mouth not in "aiueo" or math.sqrt(float(np.mean(seg ** 2))) <= 0.03:
                continue
            w = engine_vowel(seg, KOKORO_RATE)
            if w is None:
                continue
            pick = int(np.argmax(w))
            picks[pick] += 1
            t += 1
            r += "aiueo"[pick] == mouth
        print("line %d: %d of %d right, %s" % (i + 1, r, t, text), flush=True)
        right, total = right + r, total + t
    print("getVowel names the vowel %d%% of the time (it picked %s)"
          % (100 * right // max(total, 1), ", ".join("%s %d" % (v, n) for v, n in zip("aiueo", picks))), flush=True)


def main():
    what = sys.argv[1:] or ["art"]
    for w in what:
        {"art": make_art, "voice": make_voice, "vowels": measure_vowels}[w]()


if __name__ == "__main__":
    main()
