#!/usr/bin/env python3
"""Tests kagex-lipsync: aligning English (the sample's pip000009) and Japanese (ja_sample.ogg,
kanji read by OpenJTalk) against the tracks committed for them, refusing a voice that doesn't say
its line (Pip's babble), a track's state (current, then out of date when the voice changes,
also in kagex-release's check), and, with an engine, the voices' lines read from the sample's
scripts, in English and Japanese, and Ai's Japanese voice aligned to its Japanese line.

usage: smoke.py <kagex-lipsync> [--release <kagex-release>] [--engines DIR] [--out DIR]
"""
import argparse, difflib, json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SPEECH = ("Hi again! Listen closely. When I speak with a real voice, my mouth makes the shape of every vowel I say. "
          "Ah, ee, ooh, eh, oh. Isn't that so much better than mumbling?")
JA_TEXT = "急げば、まだ最後の電車に間に合うよ。"


class Failed(Exception):
    pass


def run(args, ok=(0,), timeout=900):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if r.returncode not in ok:
        raise Failed("%s exited %d:\n%s%s" % (" ".join(args), r.returncode, r.stdout, r.stderr))
    return r


def marks(text):
    """a track's marks: [(ms, mouth, open)]"""
    out = []
    for line in text.splitlines():
        f = line.strip().split("\t")
        if len(f) >= 3 and not line.startswith("#"):
            out.append((int(f[0]), f[1], int(f[2])))
    return out


def vowels(ms):
    return "".join(m for _, m, _ in ms if m in "aiueo")


def same_track(got, want, what):
    """the vowels in the same order (allowing a little difference between platforms' arithmetic)"""
    a, b = vowels(got), vowels(want)
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    print("  %s: %d marks, vowels %s (%.0f%% like the committed track's)" % (what, len(got), a, 100 * ratio), flush=True)
    if len(got) < len(want) // 2 or ratio < 0.85:
        raise Failed("%s: the track isn't like the committed one:\n  got  %s\n  want %s" % (what, a, b))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tool")
    ap.add_argument("--release", help="kagex-release, to check its warning about out-of-date tracks")
    ap.add_argument("--engines", help="engine packages, to read the sample's scripts")
    ap.add_argument("--out", default=None)
    o = ap.parse_args()
    tool = os.path.abspath(o.tool)
    out = o.out or tempfile.mkdtemp(prefix="lipsync-smoke-")
    os.makedirs(out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="lipsync-work-")
    try:
        print("English: pip000009.ogg", flush=True)
        r = run([tool, "--cli", "align", os.path.join(ROOT, "data", "voice", "pip000009.ogg"), SPEECH])
        open(os.path.join(out, "pip000009.lip"), "w").write(r.stdout)
        same_track(marks(r.stdout), marks(open(os.path.join(ROOT, "data", "voice", "pip000009.lip"), encoding="utf-8").read()), "pip000009")

        print("Japanese: ja_sample.ogg", flush=True)
        r = run([tool, "--cli", "align", os.path.join(HERE, "ja_sample.ogg"), JA_TEXT])
        open(os.path.join(out, "ja_sample.lip"), "w").write(r.stdout)
        same_track(marks(r.stdout), marks(open(os.path.join(HERE, "ja_sample.lip"), encoding="utf-8").read()), "ja_sample")

        print("A voice that doesn't say its line (Pip's babble)", flush=True)
        r = run([tool, "--cli", "align", os.path.join(ROOT, "data", "voice", "pip000001.ogg"), "Hi! I'm Pip."], ok=(2,))
        print("  refused: %s" % r.stderr.strip(), flush=True)

        print("A track's state", flush=True)
        game = os.path.join(work, "game")
        os.makedirs(os.path.join(game, "data", "voice"))
        open(os.path.join(game, "data", "startup.tjs"), "w").close()
        voice = os.path.join(game, "data", "voice", "pip000009.ogg")
        shutil.copy(os.path.join(ROOT, "data", "voice", "pip000009.ogg"), voice)
        run([tool, "--cli", "make", "--project=" + game, "pip000009.ogg", "--text=" + SPEECH])
        r = run([tool, "--cli", "check", game, "--json"])
        tracks = json.loads(r.stdout)["tracks"]
        if [t["status"] for t in tracks] != ["current"]:
            raise Failed("a track just made isn't current: %s" % r.stdout)
        with open(voice, "ab") as f:
            f.write(b"\0")
        r = run([tool, "--cli", "check", game], ok=(1,))
        print("  after the voice changed: %s" % r.stdout.strip().splitlines()[-1], flush=True)
        if "out of date" not in r.stdout:
            raise Failed("a changed voice's track isn't out of date: %s" % r.stdout)
        if o.release:
            r = run([os.path.abspath(o.release), "--cli", "check", game], ok=(0, 1))
            if "lip track" not in r.stdout:
                raise Failed("kagex-release's check didn't warn about the out-of-date track:\n%s" % r.stdout)
            print("  kagex-release warns about it", flush=True)

        if o.engines:
            print("The sample's lines, from its scripts", flush=True)
            r = run([tool, "--cli", "list", ROOT, "--json", "--engines=" + os.path.abspath(o.engines)], ok=(0, 1))
            open(os.path.join(out, "list.json"), "w").write(r.stdout)
            voices = {v["name"]: v for v in json.loads(r.stdout)["voices"]}
            pip = voices.get("pip000009.ogg")
            if pip is None or not pip["lines"] or not pip["lines"][0]["text"].startswith("Hi again!"):
                raise Failed("the sample's scripts don't give pip000009.ogg its line: %s" % json.dumps(pip))
            if pip["status"] != "current":
                raise Failed("pip000009.lip isn't current: %s" % pip["status"])
            if not voices.get("ai000001.ogg", {}).get("lines"):
                raise Failed("the sample's scripts don't give ai000001.ogg a line")
            print("  %d voices; pip000009.ogg: %s, \"%s\"" % (len(voices), pip["status"], pip["lines"][0]["text"][:40]), flush=True)
            langs = [l.get("language") for l in voices["ai000001.ogg"]["lines"]]
            if langs != ["en", "ja"]:
                raise Failed("ai000001.ogg's lines aren't in English, then Japanese: %s" % langs)

            print("A voice recorded in another of the game's languages (Ai's, in Japanese)", flush=True)
            game = os.path.join(work, "sample")
            shutil.copytree(os.path.join(ROOT, "data"), os.path.join(game, "data"))
            shutil.copytree(os.path.join(ROOT, "template"), os.path.join(game, "template"))
            shutil.copy(os.path.join(ROOT, "krkrz.cf"), game)
            r = run([tool, "--cli", "make", "--project=" + game, "ai000001.ogg", "--json", "--engines=" + os.path.abspath(o.engines)])
            made = json.loads(r.stdout)["results"]
            lip = os.path.join(game, "data", "voice", "ai000001.lip")
            header = open(lip, encoding="utf-8").read() if os.path.exists(lip) else ""
            if not made or not made[0].get("ok") or made[0].get("language") != "ja" or "# language: ja" not in header:
                raise Failed("ai000001.ogg's track wasn't made from its Japanese line: %s" % r.stdout)
            print("  made from the Japanese line, after the English one didn't fit: %d marks" % made[0]["marks"], flush=True)
        print("kagex-lipsync: all fine", flush=True)
        return 0
    except Failed as e:
        print("FAILED: %s" % e, flush=True)
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
