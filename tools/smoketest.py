#!/usr/bin/env python3
"""Headless smoke test for the KAGEX sample.

Starts the engine with SDL's offscreen video driver and drives the sample through the
engine's REPL file channel (-replfile, see krkrz_dev src/core/doc/REPL.md): the title screen,
each demo scene, save and load, the config and extras screens, a Yes/No prompt and the About
screen. It fails when a step doesn't reach the state it expects, when the engine raises a
script exception, or when the engine opens a native modal dialog (an error message box or a
Yes/No that should have been drawn in the game window).

It then runs template/ as a game of its own, the way a new game starts out, and checks that
it starts and that its prompts are drawn in the game window too.

usage: python3 tools/smoketest.py [--engine ./krkrz] [--only sample|template] [--keep] [--verbose]

Run it from the repository root with the engine next to data/, the same layout the game runs
in (CLAUDE.md, "Running"). Saves go to temporary folders, so it doesn't touch savedata/.
"""

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

# Uncaught script errors only. The engine also logs a VM dump ("An exception occured at
# ...") for every exception thrown, including the ones the scripts catch on purpose (a plugin
# the SDL engine doesn't have, a time-of-day background that falls back), so those aren't
# matched. The message is English or Japanese depending on the system language.
ERROR_PATTERNS = re.compile(
    r"Script exception raised|スクリプトで例外が発生しました|script exception :|! trace :")


class SmokeError(Exception):
    pass


class Engine:
    def __init__(self, exe, data, workdir, verbose):
        self.workdir = workdir
        self.chan = os.path.join(workdir, "repl")
        self.savedir = os.path.join(workdir, "savedata")
        os.makedirs(self.chan)
        os.makedirs(self.savedir)
        self.log_path = os.path.join(workdir, "engine.log")
        self.verbose = verbose
        self.modals = []
        env = dict(os.environ)
        env.setdefault("SDL_VIDEO_DRIVER", "offscreen")
        env.setdefault("SDL_AUDIO_DRIVER", "dummy")
        args = [exe, data, "-datapath=" + self.savedir + "/", "-replfile=" + self.chan,
                "-replmodaltimeout=0"]
        self.log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=env)

    # --- REPL channel -------------------------------------------------------------------

    def _answer_modal(self):
        """Answers a native modal dialog the engine opened, and records it as a failure."""
        path = os.path.join(self.chan, "modal")
        if not os.path.exists(path):
            return
        time.sleep(0.05)
        try:
            with open(path, encoding="utf-8") as f:
                req = f.read()
        except OSError:
            return
        self.modals.append(req)
        try:
            kind = json.loads(req).get("type", "")
        except ValueError:
            kind = ""
        answer = "no" if kind == "confirm" else ""
        with open(os.path.join(self.chan, "modalresp.tmp"), "w", encoding="utf-8") as f:
            f.write(answer)
        os.replace(os.path.join(self.chan, "modalresp.tmp"), os.path.join(self.chan, "modalresp"))
        print("  ! the engine opened a native dialog:", req.strip(), flush=True)

    def tjs(self, body, timeout=30.0):
        """Runs TJS statements on the main thread; 'return x;' gives the result."""
        cmd = "(function() {\n" + body + "\n})()"
        resp = os.path.join(self.chan, "resp")
        if os.path.exists(resp):
            os.remove(resp)
        tmp = os.path.join(self.chan, "cmd.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(cmd)
        os.replace(tmp, os.path.join(self.chan, "cmd"))
        end = time.time() + timeout
        while time.time() < end:
            if self.proc.poll() is not None:
                raise SmokeError("the engine exited (code %s)" % self.proc.returncode)
            self._answer_modal()
            if os.path.exists(resp):
                time.sleep(0.02)
                try:
                    with open(resp, encoding="utf-8") as f:
                        data = f.read()
                except OSError:
                    continue
                os.remove(resp)
                j = json.loads(data)
                if not j.get("ok"):
                    raise SmokeError("TJS failed: %s\n%s" % (j.get("error"), body))
                result = j.get("result", "")
                try:
                    return json.loads(result)
                except ValueError:
                    return result
            time.sleep(0.03)
        raise SmokeError("no answer from the REPL within %ss:\n%s" % (timeout, body))

    def wait(self, what, expr, timeout=60.0, interval=0.25):
        """Polls a TJS expression until it is true."""
        end = time.time() + timeout
        last = None
        while time.time() < end:
            last = self.tjs("return " + expr + ";")
            if last not in (0, "0", "", None, "void"):
                return last
            time.sleep(interval)
        raise SmokeError("timed out waiting for %s (%s); now at %s" % (what, expr, self.where()))

    def where(self):
        try:
            return self.tjs('return kag.conductor.curStorage + ":" + kag.conductor.curLine;', 5)
        except SmokeError as e:
            return "(unknown: %s)" % e

    def key(self, name):
        """Presses and releases a key over two frames, so getKeyState sees it held."""
        self.tjs("Agent.keyDown(%s); return 1;" % name)
        time.sleep(0.12)
        self.tjs("Agent.keyUp(%s); return 1;" % name)
        time.sleep(0.12)

    def clicker(self, on, until=None):
        """Clicks the middle of the screen every 50 ms, to read through scenes. With until (a
        scenario file name), the clicking stops by itself once the game gets there, so it
        can't click on into whatever that screen shows (the demo menu's choices)."""
        if on:
            self.tjs("""
                global.__smokeStopAt = "%s";
                if (typeof global.__smokeClicker != "Object") {
                    global.__smokeClicker = new Timer(function() {
                        if (global.__smokeStopAt != "" && kag.conductor.curStorage == global.__smokeStopAt) {
                            global.__smokeClicker.enabled = false;
                            return;
                        }
                        Agent.click(kag.innerWidth \\ 2, kag.innerHeight \\ 2);
                    }, "");
                    __smokeClicker.interval = 50;
                }
                __smokeClicker.enabled = true;
                return 1;""" % (until or ""))
        else:
            self.tjs('if (typeof global.__smokeClicker == "Object") __smokeClicker.enabled = false; return 1;')

    def output(self):
        if not self.log.closed:
            self.log.flush()
        with open(self.log_path, "rb") as f:
            text = f.read().decode("utf-8", "replace")
        console = os.path.join(self.savedir, "krkr.console.log")
        if os.path.exists(console):
            with open(console, "rb") as f:
                text += f.read().decode("utf-16-le", "replace")
        return text

    def stop(self):
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()  # a hung engine ignores SIGTERM (CLAUDE.md)
                self.proc.wait()
        self.log.close()


DEMOS = ["layer.ks", "char.ks", "envlayer.ks", "transition.ks", "action.ks"]


def collector():
    steps = []

    def step(name):
        def deco(fn):
            steps.append((name, fn))
            return fn
        return deco
    return steps, step


def prompt_steps(eng, step):
    """The Yes/No prompt and the About screen, which every game gets from template/system."""

    @step("a Yes/No prompt is drawn in the game window, Esc answers No")
    def _():
        eng.tjs('global.__smokeAnswer = ""; askYesNo("Smoke test?", "Confirm",'
                ' function() { global.__smokeAnswer = "yes"; },'
                ' function() { global.__smokeAnswer = "no"; }); return 1;')
        eng.wait("the prompt", 'typeof kag.currentDialog == "Object" && kag.currentDialog !== void',
                 timeout=10)
        eng.key("VK_ESCAPE")
        eng.wait("the answer", '__smokeAnswer == "no"', timeout=10)

    @step("the About screen opens in the game window and closes")
    def _():
        eng.tjs("kag.onHelpAboutMenuItemClick(kag); return 1;")
        eng.wait("About", 'typeof kag.currentDialog == "Object" && kag.currentDialog !== void',
                 timeout=10)
        eng.key("VK_RETURN")
        eng.wait("About to close", "kag.currentDialog === void", timeout=10)


def template_steps(eng):
    """template/ run as a game of its own: it has to start without the sample's hooks."""
    steps, step = collector()

    @step("start-up reaches first.ks")
    def _():
        eng.wait("the REPL", "1", timeout=60)
        eng.wait("first.ks", 'kag.conductor.curStorage == "first.ks" && kag.inStable', timeout=60)

    prompt_steps(eng, step)
    return steps


def sample_steps(eng):
    steps, step = collector()

    @step("start-up reaches the title screen")
    def _():
        eng.wait("the REPL", "1", timeout=60)
        eng.clicker(True, until="title.ks")  # clicks through the logo
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=60)
        eng.clicker(False)

    @step("Extras start locked")
    def _():
        if eng.tjs("return sf.clear ? 1 : 0;") != 0:
            raise SmokeError("sf.clear is already set on a fresh start")

    for demo in DEMOS:
        @step("demo " + demo + " plays to the end")
        def _(demo=demo):
            eng.tjs('kag.process("%s", "*start"); return 1;' % demo)
            eng.wait(demo, 'kag.conductor.curStorage == "%s"' % demo, timeout=10)
            eng.clicker(True, until="s0001.ks")
            eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks"', timeout=180)
            eng.clicker(False)

    @step("finishing every demo unlocks Extras")
    def _():
        eng.wait("sf.clear", "sf.clear", timeout=5)

    @step("save and load a bookmark")
    def _():
        eng.tjs('kag.process("layer.ks", "*start"); return 1;')
        eng.wait("a stable point in layer.ks",
                 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=20)
        line = eng.tjs("return kag.conductor.curLine;")
        eng.tjs("kag.saveBookMark(0); return 1;")
        eng.wait("data0 to be written",
                 "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(0))", timeout=10)
        eng.tjs('kag.goToStart(); return 1;')
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)
        eng.tjs("loadFunction(0); return 1;")
        eng.wait("the bookmark to load",
                 'kag.conductor.curStorage == "layer.ks" && kag.conductor.curLine == %d && kag.inStable'
                 % line, timeout=30)

    for screen, start in (("save.ks", "startSave()"), ("load.ks", "startLoad()"),
                          ("config.ks", "startConfig()")):
        @step("the " + screen + " screen opens from the game and closes with Esc")
        def _(screen=screen, start=start):
            eng.wait("a stable point", "kag.inStable", timeout=20)
            eng.tjs(start + "; return 1;")
            eng.wait(screen, 'kag.conductor.curStorage == "%s" && kag.inStable' % screen, timeout=20)
            eng.key("VK_ESCAPE")
            eng.wait("the game", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=20)

    @step("controller: Y switches auto mode, X shows the history, B closes it")
    def _():
        eng.wait("a stable point", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=20)
        eng.key("VK_PAD4")
        eng.wait("auto mode on", "kag.autoMode", timeout=5)
        eng.key("VK_PAD4")
        eng.wait("auto mode off", "!kag.autoMode", timeout=5)
        eng.wait("a stable point", "kag.inStable", timeout=20)
        eng.key("VK_PAD3")
        eng.wait("the history", "kag.historyShowing", timeout=5)
        eng.key("VK_PAD2")
        eng.wait("the history to close", "!kag.historyShowing", timeout=5)

    for button, screen in (("START", "config.ks"), ("BACK", "save.ks"), ("L1", "load.ks")):
        @step("controller: " + button + " opens " + screen + " and B closes it")
        def _(button=button, screen=screen):
            key = {"START": "VK_PAD10", "BACK": "VK_PAD9", "L1": "VK_PAD5"}[button]
            eng.wait("a stable point", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=20)
            eng.key(key)
            eng.wait(screen, 'kag.conductor.curStorage == "%s" && kag.inStable' % screen, timeout=20)
            eng.key("VK_PAD2")
            eng.wait("the game", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=20)

    prompt_steps(eng, step)

    @step("back to the title through the Yes/No prompt")
    def _():
        eng.tjs("kag.goToStartWithAsk(); return 1;")
        eng.wait("the prompt", 'typeof kag.currentDialog == "Object" && kag.currentDialog !== void',
                 timeout=10)
        eng.key("VK_LEFT")  # the focus starts on No
        eng.key("VK_RETURN")
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    for screen, mode in (("cgmode.ks", 1), ("replay.ks", 2), ("musicmode.ks", 3)):
        @step("Extras: " + screen + " opens and returns to the title")
        def _(screen=screen, mode=mode):
            eng.tjs('tf.extramode = %d; kag.process("title.ks", "*extra"); return 1;' % mode)
            eng.wait(screen, 'kag.conductor.curStorage == "%s" && kag.inStable' % screen, timeout=20)
            eng.key("VK_ESCAPE")
            eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    return steps


def run_steps(eng, steps):
    failures = 0
    for name, fn in steps:
        t = time.time()
        try:
            fn()
            print("ok   %-62s %5.1fs" % (name, time.time() - t), flush=True)
        except SmokeError as e:
            failures += 1
            print("FAIL %s\n     %s" % (name, str(e).replace("\n", "\n     ")), flush=True)
            if eng.proc.poll() is not None:
                break
            try:
                eng.clicker(False)
            except SmokeError:
                pass
    return failures


def run_project(opts, label, data, make_steps):
    print("== %s (%s)" % (label, data), flush=True)
    workdir = tempfile.mkdtemp(prefix="kagex-smoke-")
    eng = Engine(opts.engine, data, workdir, opts.verbose)
    failures = 0
    try:
        failures = run_steps(eng, make_steps(eng))
    except SmokeError as e:
        failures += 1
        print("FAIL", e)
    finally:
        try:
            eng.tjs('if (typeof global.__smokeClicker == "Object") __smokeClicker.enabled = false; return 1;', 3)
        except SmokeError:
            pass
        eng.stop()

    text = eng.output()
    errors = [l for l in text.splitlines() if ERROR_PATTERNS.search(l)]
    if errors:
        failures += 1
        print("FAIL the engine log has script errors:")
        for l in errors[:40]:
            print("     " + l)
    if eng.modals:
        failures += 1
        print("FAIL the engine opened %d native dialog(s)" % len(eng.modals))
    if opts.verbose or failures:
        print("--- end of the engine log (%s) ---" % eng.log_path)
        print("\n".join(text.splitlines()[-80:]))
    if opts.keep or failures:
        print("kept", workdir)
    else:
        shutil.rmtree(workdir, ignore_errors=True)
    return failures


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    default_exe = "krkrz.exe" if os.name == "nt" else "./krkrz"
    ap.add_argument("--engine", default=default_exe)
    ap.add_argument("--only", choices=["sample", "template"],
                    help="run one project (default: the sample in data/, then template/)")
    ap.add_argument("--keep", action="store_true", help="keep the temporary folders")
    ap.add_argument("--verbose", action="store_true", help="print the engine log at the end")
    opts = ap.parse_args()

    failures = 0
    if opts.only in (None, "sample"):
        failures += run_project(opts, "sample", "data", sample_steps)
    if opts.only in (None, "template"):
        failures += run_project(opts, "template", "template", template_steps)
    print("smoke test:", "FAILED (%d)" % failures if failures else "passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
