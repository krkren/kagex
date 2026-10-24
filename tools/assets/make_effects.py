#!/usr/bin/env python3
"""Draws the sample's Effekseer effects: the textures in data/effect/Texture and the effects
(.efk, Effekseer's runtime format, version 1.6) in data/effect, written with efkformat.py.

The effects are white or lightly tinted textures coloured by the effects' own colour settings,
drawn additively. Sizes are in Effekseer units: the game shows them at efkmag pixels per unit
(50 unless efkmag says), so 10 units are about half the screen's height.

usage: python3 tools/assets/make_effects.py [textures] [effects]   (both when none is named)
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
EFFECT = os.path.join(REPO, "data", "effect")
TEXTURE = os.path.join(EFFECT, "Texture")
sys.path.insert(0, HERE)


# --------------------------------------------------------------------------------------------
# textures
# --------------------------------------------------------------------------------------------

def grid(n):
    """coordinates from -1 to 1 across an n x n image (pixel centres)"""
    v = (np.arange(n) + 0.5) / n * 2 - 1
    return np.meshgrid(v, v)


def save(name, rgb, alpha):
    """rgb: (h, w, 3) floats 0-1 (or one colour), alpha: (h, w) floats 0-1"""
    alpha = np.clip(alpha, 0, 1)
    h, w = alpha.shape
    rgb = np.broadcast_to(np.asarray(rgb, dtype=float), (h, w, 3))
    a = np.dstack([np.clip(rgb, 0, 1), alpha])
    os.makedirs(TEXTURE, exist_ok=True)
    Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGBA").save(os.path.join(TEXTURE, name), optimize=True)
    print("Texture/" + name)


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def tex_glow():
    """a soft round glow"""
    x, y = grid(128)
    r = np.hypot(x, y)
    a = smooth(1 - r) ** 2.2
    save("glow.png", (1, 1, 1), a)


def tex_spark():
    """a four-pointed sparkle: a small bright core, long thin horizontal and vertical rays and
    shorter diagonal ones"""
    x, y = grid(192)
    r = np.hypot(x, y)
    core = smooth(1 - r / 0.22) ** 2
    halo = smooth(1 - r / 0.6) ** 3 * 0.35
    def ray(u, v, length, width):
        return smooth(1 - np.abs(u) / length) ** 1.5 * np.exp(-(v / width) ** 2)
    rays = ray(x, y, 1.0, 0.035) + ray(y, x, 1.0, 0.035)
    d1, d2 = (x + y) / math.sqrt(2), (x - y) / math.sqrt(2)
    rays += 0.45 * (ray(d1, d2, 0.55, 0.03) + ray(d2, d1, 0.55, 0.03))
    save("spark.png", (1, 1, 1), core + halo + rays)


def tex_dot():
    """a small round particle with a hard-ish edge, for fireworks and embers"""
    x, y = grid(48)
    r = np.hypot(x, y)
    save("dot.png", (1, 1, 1), smooth((1 - r) / 0.45) * 0.85 + smooth(1 - r) ** 3 * 0.15)


def tex_band():
    """a soft band for rings: U runs around the ring, V across it (inner edge to outer edge)"""
    w, h = 64, 64
    v = (np.arange(h) + 0.5) / h
    prof = np.exp(-((v - 0.5) / 0.2) ** 2) * 0.75 + np.exp(-((v - 0.5) / 0.06) ** 2) * 0.25
    a = np.repeat(prof[:, None], w, axis=1)
    save("band.png", (1, 1, 1), a)


def tex_streak():
    """a trail: U runs along it (0 at the tail, 1 at the head), V across it"""
    w, h = 128, 32
    u = (np.arange(w) + 0.5) / w
    v = (np.arange(h) + 0.5) / h
    along = smooth(u / 0.9) * smooth((1 - u) / 0.1)
    across = np.exp(-((v - 0.5) / 0.22) ** 2) * 0.7 + np.exp(-((v - 0.5) / 0.07) ** 2) * 0.3
    save("streak.png", (1, 1, 1), across[:, None] * along[None, :])


def tex_petal():
    """a cherry blossom petal, pale pink with a white base and a notch at its tip"""
    n = 96
    x, y = grid(n)
    # an ellipse narrowing towards the base (y = 1) and notched at the tip (y = -1)
    yy = (y + 0.05) / 0.92
    half = np.sqrt(np.clip(1 - yy * yy, 0, 1)) * (0.62 - 0.22 * np.clip(yy, 0, 1))
    inside = half - np.abs(x)
    notch = np.hypot(x / 0.5, (y + 1.02) / 0.3) - 1
    edge = np.minimum(inside / 0.05, notch / 0.08)
    a = smooth(edge)
    # colour: white at the base, pink towards the tip, a little darker at the edges
    t = np.clip((1 - y) / 2, 0, 1)
    pink = np.array([1.0, 0.72, 0.84])
    white = np.array([1.0, 0.97, 0.98])
    rgb = white[None, None, :] * (1 - t[..., None] ** 1.5) + pink[None, None, :] * t[..., None] ** 1.5
    rgb = rgb * (0.88 + 0.12 * smooth(inside / 0.25)[..., None])
    vein = np.exp(-(x / 0.02) ** 2) * np.clip(y + 0.3, 0, 1) * 0.12
    rgb = rgb + vein[..., None] * np.array([0.3, 0.1, 0.15])
    save("petal.png", rgb, a)


def tex_circle():
    """a magic circle: rings, a six-pointed star and small marks, drawn white at 4x and reduced"""
    n, s = 256, 4
    big = Image.new("L", (n * s, n * s), 0)
    d = ImageDraw.Draw(big)
    c = n * s / 2
    def ring(r, w):
        d.ellipse([c - r, c - r, c + r, c + r], outline=255, width=int(w))
    R = c * 0.96
    ring(R, 10 * s / 4 * 4 / 4 * 2)
    ring(R * 0.9, 4 * s / 2)
    ring(R * 0.62, 6 * s / 2)
    ring(R * 0.56, 3 * s / 2)
    ring(R * 0.16, 4 * s / 2)
    # the star: two triangles in the inner circle
    for k in range(2):
        pts = [(c + R * 0.62 * math.sin(a), c - R * 0.62 * math.cos(a))
               for a in [k * math.pi / 3 + i * 2 * math.pi / 3 for i in range(3)]]
        d.line(pts + [pts[0]], fill=255, width=int(3 * s / 2 * 1.5), joint="curve")
    # marks between the two outer rings: alternating dots and short bars
    for i in range(36):
        a = i * 2 * math.pi / 36
        rr = R * 0.83
        px, py = c + rr * math.sin(a), c - rr * math.cos(a)
        if i % 3 == 0:
            q = 7 * s
            d.ellipse([px - q, py - q, px + q, py + q], fill=255)
        else:
            ux, uy = math.sin(a), -math.cos(a)
            q = 9 * s
            d.line([(px - ux * q, py - uy * q), (px + ux * q, py + uy * q)], fill=255, width=int(3 * s))
    # six small circles at the star's points
    for i in range(6):
        a = i * math.pi / 3
        px, py = c + R * 0.62 * math.sin(a), c - R * 0.62 * math.cos(a)
        q = 12 * s
        d.ellipse([px - q, py - q, px + q, py + q], outline=255, width=int(3 * s))
    small = big.resize((n, n), Image.LANCZOS)
    glow = small.filter(ImageFilter.GaussianBlur(5))
    a = np.asarray(small, dtype=float) / 255 + np.asarray(glow, dtype=float) / 255 * 0.6
    save("circle.png", (1, 1, 1), a)


TEXTURES = [tex_glow, tex_spark, tex_dot, tex_band, tex_streak, tex_petal, tex_circle]


# --------------------------------------------------------------------------------------------
# effects
# --------------------------------------------------------------------------------------------

def make_effects():
    import efkformat  # noqa: F401  (the effects are defined once the codec is in place)
    raise SystemExit("effects: not written yet")


def main():
    groups = sys.argv[1:] or ["textures", "effects"]
    if "textures" in groups:
        for t in TEXTURES:
            t()
    if "effects" in groups:
        make_effects()


if __name__ == "__main__":
    main()
