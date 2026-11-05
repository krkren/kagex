#!/usr/bin/env python3
"""Draws the sample's opening movie, data/video/opening.webm (1920x1080) and opening_sd.webm
(960x540, which [movie] plays on the web and phones, zoomed to fill the screen) and Replay's tile for
it, data/thum/thum_opening.png (208x117), in the sample's look: the K badge and the
KAGEX wordmark on the lavender screen, the street with Ai coming in, three framed pictures from
the demos, and the evening title with its stars, over the first 14 s of bgm01 ("Daily Life"),
which logo.ks's [movie song=bgm01] unlocks in the music room. The words are in the subtitles
(data/video/opening.vtt and data/lang/ja/opening.vtt), not in the picture.

usage: python3 tools/assets/make_opening.py [--frames DIR]    (--frames: also keep every 30th frame)
       python3 tools/assets/make_opening.py eyecatch          (only the eyecatch card)

It also draws the staging kit's eyecatch card, data/image/eyecatch.png ([eyecatch] in macro.ks):
Pip waving on the lavender screen, with the badge and a few stars.

Needs NumPy, Pillow, ffmpeg (libvpx-vp9, libopus) and what make_ui.py needs (fontTools for its
fonts). The title pictures it uses are make_ui.py's (title, evening title), so run that first.
Everything is drawn the same each time: the stars' places come from a fixed seed.
"""
import math, os, subprocess, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_ui as ui  # noqa: E402

REPO = ui.REPO
DATA = os.path.join(REPO, "data")
W, H, FPS, SECONDS = 1920, 1080, 30, 14.0
FRAMES = int(SECONDS * FPS)
THUMB_FRAME = int(2.4 * FPS)  # Replay's tile: the badge and the wordmark, settled


def load(*parts):
    return Image.open(os.path.join(DATA, *parts)).convert("RGBA")


def clamp(t):
    return 0.0 if t < 0 else 1.0 if t > 1 else t


def span(t, a, b):
    """0 before a, 1 after b, smooth between"""
    x = clamp((t - a) / (b - a))
    return x * x * (3 - 2 * x)


def back_out(t):
    """overshoots a little, then settles"""
    t = clamp(t)
    c1 = 1.70158
    return 1 + (c1 + 1) * (t - 1) ** 3 + c1 * (t - 1) ** 2


def with_alpha(img, a):
    if a >= 1:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v, k=a: int(v * k + 0.5)))
    return out


def paste(dst, img, x, y, a=1.0):
    if a <= 0:
        return
    dst.alpha_composite(with_alpha(img, a), (int(round(x)), int(round(y))))


def scaled(img, s):
    w, h = max(1, int(img.width * s)), max(1, int(img.height * s))
    return img.resize((w, h), Image.LANCZOS)


def zoomed(img, z, cx=0.5, cy=0.5):
    """img (the screen's size) zoomed by z about (cx, cy), cropped back to the screen"""
    if abs(z - 1) < 1e-4:
        return img
    w, h = img.size
    cw, ch = w / z, h / z
    x0, y0 = (w - cw) * cx, (h - ch) * cy
    return img.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


# ---- the pieces, drawn once ----------------------------------------------------------
def make_pieces():
    p = {}
    c = ui.Canvas(W, H)
    ui.screen_bg(c)
    p["lavender"] = c.image()
    # the badge and the wordmark, as on the title
    c = ui.Canvas(300, 300)
    ui.emblem(c, 20, 20, 240)
    p["badge"] = c.image()
    c = ui.Canvas(760, 330)
    ui.wordmark(c, 20, 210, 190)
    c.text((30, 300), "Sample", ui.font("Black", 66), ui.rgba(ui.VIOLET), anchor="ls", stroke=5,
           stroke_fill=ui.rgba(ui.WHITE), tracking=2)
    p["wordmark"] = c.image()
    p["street"] = load("bgimage", "bg01_01.png")
    p["ai"] = load("fgimage", "ch_0_0_1.png")
    p["star"] = load("fgimage", "star.png")
    p["evening"] = load("image", "title_evening.png")
    # three framed pictures: the event CG, the street at sunset, and Pip waving
    pics = []
    ev = load("bgimage", "event1.jpg").resize((560, 315), Image.LANCZOS)
    pics.append(ev)
    pics.append(p["evening"].crop((900, 0, 1920, 574)).resize((560, 315), Image.LANCZOS))
    pip = Image.new("RGBA", (560, 315), ui.rgba(ui.LAV_SOFT))
    figure = pip_waving()
    figure = figure.resize((int(figure.width * 290 / figure.height), 290), Image.LANCZOS)
    pip.alpha_composite(figure, ((560 - figure.width) // 2, 315 - figure.height - 4))
    pics.append(pip)
    cards = []
    for pic in pics:
        c = ui.Canvas(560 + 40, 315 + 40)
        c.panel((4, 4, 560 + 28, 315 + 28), r=14, fill=ui.WHITE, border=ui.VIOLET, bw=5, shadow=10)
        card = c.image()
        card.alpha_composite(pic, (16, 16))
        cards.append(card)
    p["cards"] = cards
    return p


def pip_waving():
    """Pip from his level 0 layers (data/fgimage/pip, make_pip.py's): happy eyes, the grin, raised
    brows, cheeks and a wave, composited bottom up as the layer list (top first) orders them"""
    want = {("Shadow", ""), ("Feet", ""), ("Body", ""), ("Antenna", ""), ("Beret", ""), ("Arm L Rest", ""),
            ("Arm R Wave", ""), ("Cheeks", ""), ("Eyes Happy", ""), ("Brows Raised", ""), ("Open Mouth", "1001")}
    rows = []
    with open(os.path.join(DATA, "fgimage", "pip", "pip_0.txt"), encoding="utf-8-sig") as f:
        lines = [l.rstrip("\n").split("\t") for l in f if not l.startswith("#")]
    canvas_w, canvas_h = int(lines[0][4]), int(lines[0][5])
    for c in lines[1:]:
        if c[0] == "0" and (c[1], c[10]) in want:
            rows.append(c)
    img = Image.new("RGBA", (canvas_w, canvas_h))
    for c in reversed(rows):
        piece = load("fgimage", "pip", "pip_0_%s.png" % c[9])
        img.alpha_composite(piece, (int(c[2]), int(c[3])))
    return img.crop(img.getbbox())


# ---- one frame ----------------------------------------------------------------------
def frame(p, t, stars):
    out = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    # A (0-3.4 s): the badge drops in, the wordmark slides in beside it
    a_alpha = 1 - span(t, 3.0, 3.4)
    if a_alpha > 0:
        out.alpha_composite(p["lavender"])
        grow = 1 + 0.06 * span(t, 2.4, 3.4)
        s = back_out((t - 0.2) / 0.7) * grow
        if s > 0.02:
            b = scaled(p["badge"], s)
            paste(out, b, 610 - b.width / 2, 480 - b.height / 2, a_alpha)
        wm_t = span(t, 0.8, 1.5)
        if wm_t > 0:
            wm = scaled(p["wordmark"], grow)
            paste(out, wm, 760 + 60 * (1 - wm_t), 470 - wm.height / 2 - 40, wm_t * a_alpha)

    # B (3-7.4 s): the street, slowly closer, and Ai coming in from the right
    b_alpha = span(t, 3.0, 3.4) * (1 - span(t, 7.0, 7.4))
    if b_alpha > 0:
        scene = zoomed(p["street"], 1 + 0.06 * clamp((t - 3.0) / 4.4), 0.35, 0.5)
        ai_x = 1920 - 720 * back_out((t - 3.6) / 0.9) if t > 3.6 else 1920
        bob = 6 * math.sin((t - 3.6) * 2.4)
        scene.alpha_composite(p["ai"], (int(ai_x), int(60 + bob)))
        paste(out, scene, 0, 0, b_alpha)

    # C (7-11 s): three framed pictures come up and settle, one after another
    c_alpha = span(t, 7.0, 7.4) * (1 - span(t, 10.6, 11.2))
    if c_alpha > 0:
        scene = p["lavender"].copy()
        for i, (card, x, y, rot) in enumerate(zip(p["cards"], (120, 680, 1240), (300, 380, 260), (-4, 2.5, -2))):
            k = back_out((t - 7.4 - i * 0.5) / 0.7)
            if t < 7.4 + i * 0.5:
                continue
            drift = 8 * math.sin((t - 7.4) * 1.3 + i)
            r = card.rotate(rot * k + 0.6 * math.sin((t - 7.4) * 1.1 + i), resample=Image.BICUBIC, expand=True)
            paste(scene, r, x - (r.width - card.width) / 2, y + 760 * (1 - k) + drift - (r.height - card.height) / 2)
        paste(out, scene, 0, 0, c_alpha)

    # D (10.6-14 s): the evening title, its stars twinkling, then out to black
    d_alpha = span(t, 10.6, 11.2)
    if d_alpha > 0:
        scene = zoomed(p["evening"], 1.06 - 0.06 * clamp((t - 10.6) / 3.4), 0.5, 0.4)
        for sx, sy, size, phase in stars:
            pulse = 0.5 + 0.5 * math.sin(t * 4 + phase * 9)
            st = scaled(p["star"], size * (0.6 + 0.4 * pulse) / p["star"].width)
            # the sky between the wordmark and her, and over the shops on the right
            x = 760 + sx * 520 if sx < 0.7 else 1760 + (sx - 0.7) / 0.3 * 140
            paste(scene, st, x - st.width / 2, 20 + sy * 230 - st.height / 2, 0.4 + 0.6 * pulse)
        paste(out, scene, 0, 0, d_alpha)
        fade = span(t, 13.0, 14.0)
        if fade > 0:
            out.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
    return out.convert("RGB")


def make_eyecatch(p):
    """the card [eyecatch] shows between scenes, 1920x1080"""
    out = p["lavender"].copy()
    figure = pip_waving()
    figure = figure.resize((int(figure.width * 720 / figure.height), 720), Image.LANCZOS)
    out.alpha_composite(figure, ((W - figure.width) // 2, (H - figure.height) // 2 + 40))
    badge = scaled(p["badge"], 0.6)
    out.alpha_composite(badge, (60, 40))
    rng = np.random.default_rng(2207)
    for _ in range(9):
        size = float(rng.uniform(36, 72))
        st = scaled(p["star"], size / p["star"].width)
        x = float(rng.choice([rng.uniform(260, 640), rng.uniform(1280, 1820)]))
        y = float(rng.uniform(120, 900))
        out.alpha_composite(st, (int(x - st.width / 2), int(y - st.height / 2)))
    path = os.path.join(DATA, "image", "eyecatch.png")
    out.convert("RGB").save(path, optimize=True)
    print("wrote", os.path.relpath(path, REPO))


def encode(path, width, crf, keep=None):
    """the frames through ffmpeg, with the first SECONDS of bgm01 faded in and out"""
    music = os.path.join(DATA, "bgm", "bgm01.ogg")
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
           "-i", music,
           "-filter_complex", "[0:v]scale=%d:-2:flags=lanczos,format=yuv420p[v];"
           "[1:a]atrim=0:%g,afade=t=in:d=0.3,afade=t=out:st=%g:d=1.6[a]" % (width, SECONDS, SECONDS - 1.6),
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0", "-row-mt", "1", "-deadline", "good", "-cpu-used", "2",
           "-g", "60", "-c:a", "libopus", "-b:a", "96k", "-t", str(SECONDS),
           # no muxing date or encoder version in the file, so it comes out the same each time
           "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact", path]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE)


def main():
    keep = None
    if "--frames" in sys.argv:
        keep = sys.argv[sys.argv.index("--frames") + 1]
        os.makedirs(keep, exist_ok=True)
    rng = np.random.default_rng(1707)
    stars = [(float(rng.random()), float(rng.random()), float(rng.uniform(30, 64)), float(rng.random())) for _ in range(16)]
    p = make_pieces()
    make_eyecatch(p)
    if "eyecatch" in sys.argv[1:]:
        return
    video = os.path.join(DATA, "video")
    full = encode(os.path.join(video, "opening.webm"), W, 33)
    sd = encode(os.path.join(video, "opening_sd.webm"), W // 2, 36)
    for i in range(FRAMES):
        img = frame(p, i / FPS, stars)
        raw = img.tobytes()
        full.stdin.write(raw)
        sd.stdin.write(raw)
        if keep and i % FPS == 0:
            img.save(os.path.join(keep, "frame%03d.png" % i))
        if i == THUMB_FRAME:
            thumb = os.path.join(DATA, "thum", "thum_opening.png")
            img.resize((208, 117), Image.LANCZOS).save(thumb, optimize=True)
            print("wrote", os.path.relpath(thumb, REPO))
    for proc in (full, sd):
        proc.stdin.close()
        if proc.wait() != 0:
            raise SystemExit("ffmpeg failed")
    for n in ("opening.webm", "opening_sd.webm"):
        f = os.path.join(video, n)
        print("wrote", os.path.relpath(f, REPO), "%.1f MB" % (os.path.getsize(f) / 1e6))


if __name__ == "__main__":
    main()
