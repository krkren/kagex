#!/usr/bin/env python3
"""Makes the sample's sound effects in data/sound. The Character demo (char.ks) plays two on
the stage to show positional sound (doc/world.txt, "SE Object Functions"):

  se_chime.ogg   a short two-note chime, played at the stage's far left and far right
  se_steps.ogg   footsteps, two to a second, which loop seamlessly and follow Ai as she walks

and the screens play the interface's sounds through data/main/uisounds.csv (doc/kagex.txt,
"Interface Sounds"), short and soft, in one family of soft bell tones:

  ui_hover.ogg   the pointer or the keys reach a button: a faint high tick
  ui_click.ogg   a button pressed: a short pop
  ui_ok.ogg      going on (Start, Yes, a choice): two notes up
  ui_cancel.ogg  going back (Return, No, closing): two notes down
  ui_page.ogg    a page or tab turned: a soft brush of noise
  ui_open.ogg    a prompt, menu or the backlog opening: three quick rising notes
  ui_slide.ogg   a slider let go: a soft wooden tick
  ui_toggle.ogg  a switch turned: two ticks

usage: python3 tools/assets/make_sounds.py [stage|ui]   (both by default)

Drawn with NumPy (fixed random seeds, so they rebuild the same) and encoded with ffmpeg's
libvorbis, mono at 44.1 kHz: a positional sound is panned by the engine, so each is one
channel.
"""
import os, shutil, subprocess, sys, tempfile, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(REPO, "data", "sound")
RATE = 44100


def write_ogg(name, samples, quality=4):
    """samples: floats in -1..1"""
    os.makedirs(OUT, exist_ok=True)
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, name + ".wav")
        with wave.open(wav, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm.tobytes())
        out = os.path.join(OUT, name + ".ogg")
        # -fflags +bitexact and a fixed serial keep the file the same from one run to the next
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", str(quality),
                        "-fflags", "+bitexact", "-flags:a", "+bitexact", "-serial_offset", "1", out], check=True)
    print("wrote data/sound/%s.ogg (%.2f s)" % (name, len(samples) / RATE), flush=True)


def chime():
    """two bell notes a fifth apart (E6, then A5), each a few partials decaying at their own rates"""
    n = int(RATE * 1.4)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for start, f0 in ((0.0, 1318.5), (0.22, 880.0)):
        tt = t - start
        on = tt >= 0
        tt = np.where(on, tt, 0)
        note = np.zeros(n)
        for ratio, amp, decay in ((1.0, 1.0, 3.2), (2.0, 0.45, 5.0), (3.01, 0.22, 7.5), (4.17, 0.12, 10.0)):
            note += amp * np.sin(2 * np.pi * f0 * ratio * tt) * np.exp(-decay * tt)
        attack = np.clip(tt / 0.004, 0, 1)
        out += np.where(on, note * attack, 0)
    out *= 0.5 / np.max(np.abs(out))
    fade = int(RATE * 0.05)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def steps():
    """a second of two footsteps on a wooden floor: a low thump and a click of filtered noise
    each, quiet between them, so the loop has no seam"""
    rng = np.random.default_rng(7)
    n = RATE
    out = np.zeros(n)
    for start, gain in ((0.08, 1.0), (0.58, 0.85)):
        s = int(RATE * start)
        length = int(RATE * 0.18)
        tt = np.arange(length) / RATE
        thump = np.sin(2 * np.pi * 95 * tt) * np.exp(-tt * 38)
        noise = rng.standard_normal(length)
        # a short moving average makes the click duller (a soft sole)
        kernel = np.ones(6) / 6
        click = np.convolve(noise, kernel, mode="same") * np.exp(-tt * 70)
        out[s:s + length] += gain * (0.9 * thump + 0.35 * click)
    out *= 0.6 / np.max(np.abs(out))
    return out


def bell(f0, length, decay=18.0, partials=((1.0, 1.0), (2.0, 0.3), (3.0, 0.1)), attack=0.002):
    """a soft bell note: a few partials, each decaying faster than the one below"""
    n = int(RATE * length)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for i, (ratio, amp) in enumerate(partials):
        out += amp * np.sin(2 * np.pi * f0 * ratio * t) * np.exp(-decay * (1 + 0.6 * i) * t)
    out *= np.clip(t / attack, 0, 1)
    return out


def place(notes, length):
    """notes: (start in s, samples, gain); mixed into length seconds, ending in a short fade"""
    n = int(RATE * length)
    out = np.zeros(n)
    for start, note, gain in notes:
        s = int(RATE * start)
        m = min(len(note), n - s)
        out[s:s + m] += gain * note[:m]
    fade = int(RATE * 0.01)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


def peak(out, level):
    return out * (level / np.max(np.abs(out)))


def ui_hover():
    return peak(place([(0, bell(2637.0, 0.06, decay=70), 1)], 0.07), 0.16)


def ui_click():
    """a pop: a falling sine over a breath of noise"""
    n = int(RATE * 0.08)
    t = np.arange(n) / RATE
    f = 1500 * np.exp(-t * 30) + 600
    phase = 2 * np.pi * np.cumsum(f) / RATE
    rng = np.random.default_rng(11)
    noise = np.convolve(rng.standard_normal(n), np.ones(4) / 4, mode="same") * np.exp(-t * 300)
    out = np.sin(phase) * np.exp(-t * 55) + 0.25 * noise
    out *= np.clip(t / 0.001, 0, 1)
    return peak(place([(0, out, 1)], 0.09), 0.32)


def ui_ok():
    return peak(place([(0, bell(1174.7, 0.25), 0.8), (0.07, bell(1760.0, 0.3), 1)], 0.36), 0.32)


def ui_cancel():
    return peak(place([(0, bell(1318.5, 0.22), 0.9), (0.07, bell(880.0, 0.3), 1)], 0.36), 0.3)


def ui_page():
    """a brush: noise through a band that sweeps up and fades"""
    rng = np.random.default_rng(23)
    n = int(RATE * 0.16)
    t = np.arange(n) / RATE
    noise = rng.standard_normal(n)
    smooth = np.convolve(noise, np.ones(3) / 3, mode="same")
    band = smooth - np.convolve(smooth, np.ones(24) / 24, mode="same")  # takes the lows out
    env = np.sin(np.pi * np.clip(t / 0.16, 0, 1)) ** 2
    return peak(place([(0, band * env, 1)], 0.17), 0.2)


def ui_open():
    notes = [(0, bell(1046.5, 0.25), 0.7), (0.05, bell(1318.5, 0.25), 0.8), (0.1, bell(1568.0, 0.35), 1)]
    return peak(place(notes, 0.45), 0.3)


def ui_slide():
    return peak(place([(0, bell(1760.0, 0.05, decay=80, partials=((1.0, 1.0), (2.76, 0.4))), 1)], 0.06), 0.22)


def ui_toggle():
    tick = bell(1975.5, 0.05, decay=80, partials=((1.0, 1.0), (2.76, 0.3)))
    return peak(place([(0, tick, 0.8), (0.05, tick, 1)], 0.11), 0.24)


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("make_sounds.py needs ffmpeg (with libvorbis)")
    what = sys.argv[1:] or ["stage", "ui"]
    if "stage" in what:
        write_ogg("se_chime", chime())
        write_ogg("se_steps", steps())
    if "ui" in what:
        for name, make in (("ui_hover", ui_hover), ("ui_click", ui_click), ("ui_ok", ui_ok), ("ui_cancel", ui_cancel),
                           ("ui_page", ui_page), ("ui_open", ui_open), ("ui_slide", ui_slide), ("ui_toggle", ui_toggle)):
            write_ogg(name, make())


if __name__ == "__main__":
    main()
