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

TEX = ["Texture/glow.png", "Texture/spark.png", "Texture/dot.png", "Texture/band.png",
       "Texture/streak.png", "Texture/petal.png", "Texture/circle.png"]
GLOW, SPARK, DOT, BAND, STREAK, PETAL, CIRCLE = range(len(TEX))


def fx_sparkle(e):
    """twinkling sparkles and slow motes around a point, for ever"""
    twinkle = e.Sprite(
        texture=SPARK, blend=e.ADD,
        max_generation=e.INFINITE, generation_time=(1.5, 3), life=(40, 75),
        spawn=e.Circle(division=128, radius=(0.0, 6.0), axis=e.AXIS_Z),
        translation=e.PVA(velocity=((-0.004, 0.004), (0.004, 0.012), 0)),
        rotation=e.PVA(value=(0, 0, (0, 6.28)), velocity=(0, 0, (-0.03, 0.03))),
        scale=e.Easing(start=(0, 0, 1), middle=((1.0, 2.4), (1.0, 2.4), 1), end=(0, 0, 1),
                       ease=e.EASE_IN_OUT_QUAD, channels=0),
        color=e.ColorRandom(min=(200, 170, 255, 255), max=(255, 245, 255, 255)),
    )
    motes = e.Sprite(
        texture=GLOW, blend=e.ADD,
        max_generation=e.INFINITE, generation_time=(6, 9), life=(90, 150),
        spawn=e.Circle(division=128, radius=(0.0, 6.0), axis=e.AXIS_Z),
        translation=e.PVA(velocity=((-0.006, 0.006), (0.005, 0.015), 0)),
        scale=e.SinglePVA(value=(0.3, 0.6)),
        color=e.ColorRandom(min=(150, 120, 255, 110), max=(220, 200, 255, 170)),
        fade_in=e.Fade(30), fade_out=e.Fade(40),
    )
    return e.Effect(textures=TEX, nodes=[motes, twinkle])


def fx_petals(e):
    """glowing petals drifting down across the whole screen and tumbling, for ever (start it
    with efkframe=600 to have the screen already full)"""
    petal = e.Sprite(
        texture=PETAL, blend=e.ADD, billboard=e.BILLBOARD_FIXED,
        max_generation=e.INFINITE, generation_time=(4, 7), life=(560, 700),
        spawn=e.Line(division=64, start=((-26, -26), (12, 12), (-4, 4)), end=((18, 18), (12, 12), (-4, 4))),
        translation=e.PVA(velocity=((0.015, 0.045), (-0.05, -0.035), 0)),
        rotation=e.PVA(value=((0, 6.28), (0, 6.28), (0, 6.28)),
                       velocity=((-0.04, 0.04), (-0.05, 0.05), (-0.02, 0.02))),
        scale=e.SinglePVA(value=(0.6, 1.0)),
        color=e.ColorRandom(min=(255, 190, 220, 170), max=(255, 235, 245, 230)),
        fade_in=e.Fade(30), fade_out=e.Fade(60),
    )
    return e.Effect(textures=TEX, nodes=[petal])


def fx_fireworks(e):
    """rockets that rise from a line 16 units wide and burst in the colour they rose in, about
    one a second, for ever. The bursts are about 9 units above the origin: place the effect's
    origin low (efky=400 at efkmag 50)"""
    rise = 54   # frames from launch to burst
    flash = e.Sprite(
        texture=GLOW, blend=e.ADD,
        max_generation=1, generation_offset=rise - 2, life=20,
        bind_translation=e.BIND_WHEN_CREATING, bind_rotation=e.BIND_NOT, bind_scale=e.BIND_NOT,
        color_bind=e.BIND_WHEN_CREATING,
        scale=e.Easing(start=(1, 1, 1), end=(7, 7, 1), ease=e.EASE_OUT_CUBIC),
        color=e.ColorEasing(start=(255, 255, 255, 200), end=(255, 255, 255, 0)),
    )
    crackle = e.Sprite(
        texture=SPARK, blend=e.ADD,
        max_generation=1, generation_offset=(45, 75), life=(10, 18),
        bind_translation=e.BIND_WHEN_CREATING, bind_rotation=e.BIND_NOT, bind_scale=e.BIND_NOT,
        remove_when_parent_removed=False,
        scale=e.Easing(start=(0.9, 0.9, 1), end=(0, 0, 1)),
        color=(255, 250, 230, 255),
    )
    star = e.Sprite(
        texture=DOT, blend=e.ADD,
        max_generation=72, generation_time=0, generation_offset=rise - 2, life=(70, 95),
        bind_translation=e.BIND_WHEN_CREATING, bind_rotation=e.BIND_NOT, bind_scale=e.BIND_NOT,
        color_bind=e.BIND_WHEN_CREATING,
        spawn=e.Sphere(radius=(0.05, 0.05), rotation_x=(-3.1416, 3.1416), rotation_y=(-3.1416, 3.1416)),
        spawn_rotation=True,
        translation=e.PVA(velocity=(0, (0.15, 0.19), 0), acceleration=(0, -0.0024, 0)),
        force_fields=[e.ForceField(type=e.FF_GRAVITY, gravity=(0, -0.0016, 0))],
        scale=e.SinglePVA(value=(0.32, 0.45)),
        fade_out=e.Fade(40),
        children=[crackle],
    )
    trail = e.Sprite(
        texture=DOT, blend=e.ADD,
        max_generation=e.INFINITE, generation_time=1.5, life=(16, 26),
        bind_translation=e.BIND_WHEN_CREATING, bind_rotation=e.BIND_NOT, bind_scale=e.BIND_NOT,
        translation=e.PVA(velocity=((-0.006, 0.006), (-0.012, -0.004), 0)),
        scale=e.FloatEasing(start=(0.28, 0.34), end=0.0),
        color=(255, 215, 170, 190),
    )
    rocket = e.Sprite(
        texture=GLOW, blend=e.ADD,
        max_generation=e.INFINITE, generation_time=(40, 75), life=rise,
        spawn=e.Line(division=32, start=(-8, 0, 0), end=(8, 0, 0)),
        translation=e.PVA(velocity=((-0.025, 0.025), (0.28, 0.31), 0), acceleration=(0, -0.0042, 0)),
        scale=e.SinglePVA(value=0.45),
        color=e.ColorRandom(min=(170, 110, 170, 255), max=(255, 235, 255, 255)),
        children=[trail, star, flash],
    )
    return e.Effect(textures=TEX, nodes=[rocket])


def fx_shockwave(e):
    """a burst of light: a flash, two rings and sparks flying out (once, about a second)"""
    flash = e.Sprite(
        texture=GLOW, blend=e.ADD, life=42,
        scale=e.Easing(start=(2, 2, 1), end=(12, 12, 1), ease=e.EASE_OUT_CUBIC),
        color=e.ColorEasing(start=(255, 255, 255, 255), end=(190, 150, 255, 0)),
    )
    def ring(offset, life, outer, inner, color):
        return e.Ring(
            texture=BAND, blend=e.ADD, billboard=e.BILLBOARD, vertex_count=72,
            generation_offset=offset, life=life,
            outer=e.RingEasing(start=((outer[0], outer[0]), (0, 0)), end=((outer[1], outer[1]), (0, 0)),
                               params=e.speed(30, -5)),
            inner=e.RingEasing(start=((inner[0], inner[0]), (0, 0)), end=((inner[1], inner[1]), (0, 0)),
                               params=e.speed(30, -5)),
            outer_color=e.ColorEasing(start=color, end=color[:3] + (0,)),
            center_color=e.ColorEasing(start=color, end=color[:3] + (0,)),
            inner_color=e.ColorEasing(start=color, end=color[:3] + (0,)),
        )
    rings = [ring(0, 72, (1.0, 11.5), (0.6, 9.6), (240, 225, 255, 255)),
             ring(8, 64, (0.8, 8.0), (0.5, 7.0), (190, 150, 255, 255))]
    sparks = e.Sprite(
        texture=SPARK, blend=e.ADD,
        max_generation=28, generation_time=0, life=(26, 42),
        spawn=e.Circle(division=96, radius=(0.3, 0.3), axis=e.AXIS_Z), spawn_rotation=True,
        translation=e.PVA(velocity=(0, (0.28, 0.42), 0), acceleration=(0, -0.008, 0)),
        scale=e.FloatEasing(start=(0.7, 1.1), end=0.1),
        color=e.ColorRandom(min=(220, 200, 255, 255), max=(255, 255, 255, 255)),
        fade_out=e.Fade(12),
    )
    motes = e.Sprite(
        texture=GLOW, blend=e.ADD,
        max_generation=24, generation_time=0, life=(40, 60),
        spawn=e.Circle(division=96, radius=(0.2, 0.6), axis=e.AXIS_Z), spawn_rotation=True,
        translation=e.PVA(velocity=(0, (0.08, 0.16), 0), acceleration=(0, -0.0015, 0)),
        scale=e.SinglePVA(value=(0.4, 0.7)),
        color=e.ColorRandom(min=(160, 120, 255, 160), max=(230, 210, 255, 220)),
        fade_out=e.Fade(25),
    )
    return e.Effect(textures=TEX, nodes=[flash] + rings + [motes, sparks])


def fx_magiccircle(e):
    """a magic circle on the ground, turning, with light rising from its rim, for ever. It's
    tilted as if lying on the ground (no efkrotx needed); efkstop fades it out"""
    keep = dict(remove_when_life_ends=False, remove_when_parent_removed=True,
                fade_out=e.Fade(45, mode=e.FADEOUT_AFTER_REMOVED))
    outer = e.Sprite(
        texture=CIRCLE, blend=e.ADD, billboard=e.BILLBOARD_FIXED, fade_in=e.Fade(40),
        scale=e.SinglePVA(value=9.0),
        rotation=e.PVA(velocity=(0, 0, 0.006)),
        color=(205, 175, 255, 255), **keep)
    inner = e.Sprite(
        texture=CIRCLE, blend=e.ADD, billboard=e.BILLBOARD_FIXED, fade_in=e.Fade(70),
        scale=e.SinglePVA(value=5.0),
        rotation=e.PVA(value=(0, 0, 0.5), velocity=(0, 0, -0.011)),
        color=(255, 215, 250, 210), **keep)
    glow = e.Sprite(
        texture=GLOW, blend=e.ADD, billboard=e.BILLBOARD_FIXED, fade_in=e.Fade(60),
        scale=e.SinglePVA(value=12.0),
        color=(110, 70, 255, 110), **keep)
    # in the circle's plane, local +Z is up on the screen
    rising = e.Sprite(
        texture=GLOW, blend=e.ADD,
        max_generation=e.INFINITE, generation_time=(1.5, 3), life=(50, 90),
        bind_translation=e.BIND_WHEN_CREATING, bind_rotation=e.BIND_WHEN_CREATING, bind_scale=e.BIND_NOT,
        spawn=e.Circle(division=120, radius=(3.9, 4.4), axis=e.AXIS_Z),
        translation=e.PVA(velocity=(0, 0, (0.035, 0.07))),
        scale=e.FloatEasing(start=(0.35, 0.6), end=0.0),
        color=e.ColorRandom(min=(170, 140, 255, 200), max=(240, 225, 255, 255)),
        fade_in=e.Fade(10),
    )
    plane = e.Node(
        rotation=e.Fixed(e.deg((-72, 0, 0))), remove_when_life_ends=False,
        remove_when_parent_removed=True,
        children=[glow, outer, inner, rising],
    )
    return e.Effect(textures=TEX, nodes=[plane])


EFFECTS = {"sparkle": fx_sparkle, "petals": fx_petals, "fireworks": fx_fireworks,
           "shockwave": fx_shockwave, "magiccircle": fx_magiccircle}


def make_effects():
    import efkformat as e
    os.makedirs(EFFECT, exist_ok=True)
    for name, make in EFFECTS.items():
        data = e.write_efk(make(e))
        e.read_efk(data)   # it reads back
        with open(os.path.join(EFFECT, name + ".efk"), "wb") as f:
            f.write(data)
        print(name + ".efk", len(data), "bytes")


def main():
    groups = sys.argv[1:] or ["textures", "effects"]
    if "textures" in groups:
        for t in TEXTURES:
            t()
    if "effects" in groups:
        make_effects()


if __name__ == "__main__":
    main()
