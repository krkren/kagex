#!/usr/bin/env python3
"""Hiyori, the Live2D character of the sample's "Animated Character" demo (anim.ks): her model
and her voice line.

Hiyori Momose is Live2D Inc.'s sample character (the model Neuro-sama first streamed as), a World
character the krkrlive2d plugin draws (KAGEnvCharacterLive2D.tjs; doc/world.txt, "Live2D
Characters"). Neither her model nor anything drawn from it is in this repository: Live2D's Free
Material License lets no one but Live2D hand out its sample models' files (a work an individual or
a small business makes with them may ship them inside it), so a build that shows her fetches her.

model --accept-license
    Fetches her from Live2D's CubismNativeSamples on GitHub, at the commit HIYORI_COMMIT, and
    packs the model folder's contents (model3.json at the top) into data/fgimage/hiyori.l2d, a
    zip, as krkrlive2d reads a model. The files go in a fixed order with fixed times, so the
    same commit gives the same file. --accept-license says you have read and agree to the Free
    Material License and Hiyori's terms (FREE_MATERIAL_LICENSE, SAMPLE_MODEL_TERMS): an
    individual, or a business with yearly sales under 10 million yen, may use her in its works,
    commercial ones too, with the notice "This content uses sample data owned and copyrighted
    by Live2D Inc."; a bigger business may only use her internally; her design may not be
    changed.

speech
    Makes her line, data/voice/hiyori000001.ogg, with eSpeak NG, a formant synthesizer (rules
    and a model of the vocal tract, not a voice learned from recordings): its US English in the
    "anika" variant, a young woman's voice. Each line is anim.ks's 【hiyori】 line with voice=N
    before it. It needs espeak-ng (ESPEAK_NG names it when it isn't on the PATH; eSpeak NG
    1.52.0 made the committed line) and ffmpeg with libvorbis. Then kagex-lipsync makes the
    line's lip track (tools/lipsync), so her mouth takes the shapes of its vowels:

        kagex-lipsync --cli make hiyori000001.ogg

usage: python3 tools/assets/make_hiyori.py model --accept-license | speech
"""
import io, os, re, shutil, subprocess, sys, tempfile, urllib.error, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL = os.path.join(ROOT, "data", "fgimage", "hiyori.l2d")
VOICE = os.path.join(ROOT, "data", "voice")
SCRIPT = os.path.join(ROOT, "data", "scenario", "anim.ks")

FREE_MATERIAL_LICENSE = "https://www.live2d.com/eula/live2d-free-material-license-agreement_en.html"
SAMPLE_MODEL_TERMS = "https://www.live2d.com/eula/live2d-sample-model-terms_en.html"

# Live2D/CubismNativeSamples (Cubism 5 SDK for Native samples), and Hiyori's folder in it
REPO = "https://github.com/Live2D/CubismNativeSamples"
HIYORI_COMMIT = "a3a64f6cb327aafce380949e0f54fe51c4d773d9"
HIYORI_DIR = "Samples/Resources/Hiyori"
HIYORI_FILES = [
    "Hiyori.model3.json",
    "Hiyori.moc3",
    "Hiyori.physics3.json",
    "Hiyori.pose3.json",
    "Hiyori.userdata3.json",
    "Hiyori.cdi3.json",
    "Hiyori.2048/texture_00.png",
    "Hiyori.2048/texture_01.png",
] + ["motions/Hiyori_m%02d.motion3.json" % i for i in range(1, 11)]

# eSpeak NG's voice for her: US English, the anika variant (pitch 200-300 Hz), a little slower
# than its 175 words a minute
ESPEAK_VOICE = "en-us+anika"
ESPEAK_SPEED = 160


def fetch_raw(path):
    url = "https://raw.githubusercontent.com/Live2D/CubismNativeSamples/%s/%s" % (HIYORI_COMMIT, path)
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def fetch_git(paths):
    """The files at HIYORI_COMMIT through git, where raw downloads are refused"""
    if not shutil.which("git"):
        raise RuntimeError("needs git, or access to raw.githubusercontent.com")
    with tempfile.TemporaryDirectory() as tmp:
        def git(*args, **kw):
            return subprocess.run(["git", "-C", tmp] + list(args), check=True, capture_output=True, **kw)
        git("init", "-q")
        git("remote", "add", "origin", REPO)
        git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", HIYORI_COMMIT)
        return {p: git("show", "%s:%s" % (HIYORI_COMMIT, p)).stdout for p in paths}


def model(argv):
    if "--accept-license" not in argv:
        sys.exit("Hiyori is Live2D Inc.'s, under its Free Material License and her terms:\n"
                 "  %s\n  %s\n"
                 "Run again with --accept-license once you have read and agree to them." %
                 (FREE_MATERIAL_LICENSE, SAMPLE_MODEL_TERMS))
    paths = ["%s/%s" % (HIYORI_DIR, f) for f in HIYORI_FILES]
    try:
        data = {p: fetch_raw(p) for p in paths}
    except (urllib.error.URLError, OSError) as e:
        print("raw.githubusercontent.com: %s; fetching with git" % e)
        data = fetch_git(paths)
    if not data[paths[1]].startswith(b"MOC3"):
        sys.exit("Hiyori.moc3 isn't a model (%r)" % data[paths[1]][:8])
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f, p in zip(HIYORI_FILES, paths):
            info = zipfile.ZipInfo(f, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if f.endswith(".png") else zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data[p])
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    with open(MODEL, "wb") as f:
        f.write(buf.getvalue())
    print("%s: %d files, %d bytes" % (os.path.relpath(MODEL, ROOT), len(HIYORI_FILES), len(buf.getvalue())))


def lines():
    """{voice number: text} of anim.ks's voiced 【hiyori】 lines"""
    out, voice = {}, None
    with open(SCRIPT, encoding="utf-8-sig") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"\[hiyori\b[^\]]*\bvoice=(\d+)", line)
            if m:
                voice = int(m.group(1))
            elif line.startswith("【hiyori】") and voice is not None:
                out[voice] = line[len("【hiyori】"):]
                voice = None
    return out


def speech(argv):
    espeak = os.environ.get("ESPEAK_NG") or shutil.which("espeak-ng")
    if not espeak:
        sys.exit("make_hiyori.py speech needs eSpeak NG (espeak-ng on the PATH, or ESPEAK_NG)")
    if not shutil.which("ffmpeg"):
        sys.exit("make_hiyori.py speech needs ffmpeg (with libvorbis)")
    todo = lines()
    if not todo:
        sys.exit("no voiced 【hiyori】 lines in " + SCRIPT)
    version = subprocess.run([espeak, "--version"], capture_output=True, text=True).stdout.strip()
    print(version)
    with tempfile.TemporaryDirectory() as tmp:
        for n, text in sorted(todo.items()):
            wav = os.path.join(tmp, "line.wav")
            subprocess.run([espeak, "-v", ESPEAK_VOICE, "-s", str(ESPEAK_SPEED), "-w", wav, text], check=True)
            out = os.path.join(VOICE, "hiyori%06d.ogg" % n)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "4",
                            "-ar", "48000", "-ac", "1", "-map_metadata", "-1", "-fflags", "+bitexact",
                            "-flags:a", "+bitexact", out], check=True)
            print("%s: %s" % (os.path.relpath(out, ROOT), text))
    print("Now make their lip tracks: kagex-lipsync --cli make " +
          " ".join("hiyori%06d.ogg" % n for n in sorted(todo)))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    if what == "model":
        model(sys.argv[2:])
    elif what == "speech":
        speech(sys.argv[2:])
    else:
        sys.exit(__doc__)
