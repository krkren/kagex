#!/usr/bin/env python3
"""Makes the sample's sound effects in data/sound, which the Character demo (char.ks) plays on
the stage to show positional sound (doc/world.txt, "SE Object Functions"):

  se_chime.ogg   a short two-note chime, played at the stage's far left and far right
  se_steps.ogg   footsteps, two to a second, which loop seamlessly and follow Ai as she walks

usage: python3 tools/assets/make_sounds.py

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


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("make_sounds.py needs ffmpeg (with libvorbis)")
    write_ogg("se_chime", chime())
    write_ogg("se_steps", steps())


if __name__ == "__main__":
    main()
