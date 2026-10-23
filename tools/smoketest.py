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

The platform builds run the sample's steps the same way, through their own REPL channels
(the packages hold the sample only):

  --target android --apk kagex.apk     a debug APK on a running emulator or device (adb):
                                       the socket channel debug builds open (<package>.repl)
  --target ios-sim --app KAGEX.app     a Simulator build on a booted Simulator (xcrun simctl):
                                       the browser REPL's HTTP server (-replweb), which is the
                                       REPL krkrz_ios builds have
  --target web --url http://...        the browser build in headless Chromium (Playwright):
                                       krkrz_web's krkrz_repl_eval bridge (--channel chrome
                                       uses the installed Chrome)
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
    """What the steps drive the game through. A target supplies _eval (one TJS expression in,
    the REPL's %[ok, result, error] out), output (the engine's log) and stop."""
    modals = []
    log_path = "(no log file)"
    workdir = None

    def _eval(self, cmd, timeout):
        raise NotImplementedError

    def tjs(self, body, timeout=30.0):
        """Runs TJS statements on the main thread; 'return x;' gives the result."""
        cmd = "(function() {\n" + body + "\n})()"
        j = self._eval(cmd, timeout)
        if not j.get("ok"):
            raise SmokeError("TJS failed: %s\n%s" % (j.get("error"), body))
        result = j.get("result", "")
        try:
            return json.loads(result)
        except ValueError:
            return result

    def wait(self, what, expr, timeout=60.0, interval=0.25):
        """Polls a TJS expression until it is true."""
        end = time.time() + timeout
        last = None
        while time.time() < end:
            last = self.tjs("return " + expr + ";")
            if last not in (0, "0", "", None, "void", "(void)"):  # the REPL prints void as (void)
                return last
            time.sleep(interval)
        raise SmokeError("timed out waiting for %s (%s); now at %s" % (what, expr, self.where()))

    def where(self):
        try:
            return self.tjs('return kag.conductor.curStorage + ":" + kag.conductor.curLine'
                            ' + " status " + kag.conductor.status + " inStable " + kag.inStable'
                            ' + " inSleep " + kag.inSleep + " transCount " + kag.transCount'
                            ' + " moveCount " + kag.moveCount + " tick " + System.getTickCount();', 5)
        except SmokeError as e:
            return "(unknown: %s)" % e

    def key(self, name):
        """Presses and releases a key over two frames, so getKeyState sees it held. Builds
        without the Agent class (the browser build) post the key events to the window."""
        for ev in ("Down", "Up"):
            self.tjs('if (typeof global.Agent != "undefined") Agent.key%s(%s);'
                     ' else kag.postInputEvent("onKey%s", %%[key: %s, shift: 0]); return 1;'
                     % (ev, name, ev, name))
            time.sleep(0.12)

    def clicker(self, on, until=None):
        """Clicks every 50 ms, to read through scenes. With until (a scenario file name), the
        clicking stops by itself once the game gets there, so it can't click on into whatever
        that screen shows (the demo menu's choices). The clicks go to KAG's click handler
        (onPrimaryClick, what a left click on the game calls): Agent.click takes window
        coordinates, and the game's position in the window differs on every platform."""
        if on:
            self.tjs("""
                global.__smokeStopAt = "%s";
                if (typeof global.__smokeClicker != "Object") {
                    global.__smokeClicker = new Timer(function() {
                        if (global.__smokeStopAt != "" && kag.conductor.curStorage == global.__smokeStopAt) {
                            global.__smokeClicker.enabled = false;
                            return;
                        }
                        kag.onPrimaryClick();
                    }, "");
                    __smokeClicker.interval = 50;
                }
                __smokeClicker.enabled = true;
                return 1;""" % (until or ""))
        else:
            self.tjs('if (typeof global.__smokeClicker == "Object") __smokeClicker.enabled = false; return 1;')

    def output(self):
        return ""

    def alive(self):
        return True

    def snapshot(self, path):
        """Saves what the screen shows, where the target can (for failed steps)."""

    def stop(self):
        pass


class FileChannel(Engine):
    """The REPL file channel (-replfile=<dir>): TJS in cmd, the answer in resp. A native modal
    dialog shows up as a modal file; it is answered and counted as a failure."""
    chan = None

    def alive(self):
        return True

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
        # The engine deletes modal and modalresp once it has read the answer; wait for that,
        # so the next poll doesn't answer the same request again
        end = time.time() + 5
        while time.time() < end and (os.path.exists(path) or
                                     os.path.exists(os.path.join(self.chan, "modalresp"))):
            time.sleep(0.02)

    def _eval(self, cmd, timeout):
        resp = os.path.join(self.chan, "resp")
        if os.path.exists(resp):
            os.remove(resp)
        tmp = os.path.join(self.chan, "cmd.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(cmd)
        os.replace(tmp, os.path.join(self.chan, "cmd"))
        end = time.time() + timeout
        while time.time() < end:
            if not self.alive():
                raise SmokeError("the engine exited")
            self._answer_modal()
            if os.path.exists(resp):
                time.sleep(0.02)
                try:
                    with open(resp, encoding="utf-8") as f:
                        data = f.read()
                except OSError:
                    continue
                os.remove(resp)
                return json.loads(data)
            time.sleep(0.03)
        raise SmokeError("no answer from the REPL within %ss:\n%s" % (timeout, cmd))


class DesktopEngine(FileChannel):
    """The engine as a process here, with SDL's offscreen video driver."""

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
        args = [exe, os.path.abspath(data), "-datapath=" + self.savedir + "/", "-replfile=" + self.chan,
                "-replmodaltimeout=0"]
        self.log = open(self.log_path, "wb")
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=env)

    def alive(self):
        if self.proc.poll() is not None:
            raise SmokeError("the engine exited (code %s)" % self.proc.returncode)
        return True

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


class SimulatorEngine(Engine):
    """A Simulator build on a booted iOS Simulator, through the browser REPL's HTTP server
    (-replweb; krkrz_ios builds have no file channel). The Simulator shares this Mac's
    network, so the server is on 127.0.0.1. POST /pad/exec runs a script and answers with
    the same %[ok, result, error] JSON as the file channel."""

    def __init__(self, app, bundle_id, workdir, verbose, device="booted", port=8931):
        self.workdir = workdir
        self.verbose = verbose
        self.modals = []
        self.device = device
        self.bundle_id = bundle_id
        self.url = "http://127.0.0.1:%d/pad/exec" % port
        self.log_path = os.path.join(workdir, "simulator.log")
        self.simctl("install", device, app)
        self.container = self.simctl("get_app_container", device, bundle_id, "data").strip()
        self.started = time.time()
        self.simctl("launch", "--terminate-running-process", device, bundle_id,
                    "-replweb=%d" % port, "-replwebidle=no", "-replmodaltimeout=0", "-forcelog=yes")
        end = time.time() + 120
        last = None
        while time.time() < end:
            try:
                j = self._eval("1", 10)
                if j.get("ok") and str(j.get("result")) == "1":
                    return
                last = j
            except (OSError, SmokeError, ValueError) as e:
                last = e
            time.sleep(2)
        raise SmokeError("no REPL server from %s: %s" % (bundle_id, last))

    @staticmethod
    def simctl(*args):
        r = subprocess.run(["xcrun", "simctl"] + list(args), capture_output=True, text=True)
        if r.returncode:
            raise SmokeError("simctl %s failed: %s" % (" ".join(args), r.stderr.strip()))
        return r.stdout

    def _eval(self, cmd, timeout):
        import urllib.request, urllib.error
        # /pad/exec runs a whole script; its value is what the script returns
        body = ("return " + cmd + ";").encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST",
                                     headers={"Content-Type": "text/plain; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.URLError, OSError) as e:
            raise SmokeError("no answer from the REPL within %ss (%s):\n%s" % (timeout, e, cmd))

    def output(self):
        text = ""
        for root, dirs, files in os.walk(self.container):
            for name in files:
                if name == "krkr.console.log":
                    with open(os.path.join(root, name), "rb") as f:
                        text += f.read().decode("utf-16-le", "replace")
        if not text:
            # the system log has the engine's output too
            minutes = int((time.time() - self.started) / 60) + 2
            r = subprocess.run(["xcrun", "simctl", "spawn", self.device, "log", "show", "--style", "compact",
                                "--last", "%dm" % minutes, "--predicate", 'process == "krkrz"'],
                               capture_output=True, text=True)
            text = r.stdout
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(text)
        return text

    def snapshot(self, path):
        # simctl's screenshot comes out black for the engine's OpenGL ES view: ask the engine
        try:
            self.tjs('Agent.captureScreen(System.dataPath + "smoke-shot.png"); return 1;', 5)
            time.sleep(1.0)
        except SmokeError:
            return
        for root, dirs, files in os.walk(self.container):
            if "smoke-shot.png" in files:
                shutil.move(os.path.join(root, "smoke-shot.png"), path)
                return

    def stop(self):
        subprocess.run(["xcrun", "simctl", "terminate", self.device, self.bundle_id], capture_output=True)


class AndroidEngine(Engine):
    """A debug APK on an emulator or device, through the REPL socket that debug builds open
    (<applicationId>.repl, forwarded to a local port with adb)."""

    def __init__(self, apk, package, workdir, verbose, adb="adb", port=9099):
        import socket
        self.workdir = workdir
        self.verbose = verbose
        self.modals = []
        self.adb = adb
        self.package = package
        self.port = port
        self.log_path = os.path.join(workdir, "logcat.txt")
        self.run_adb("install", "-r", "-g", apk)
        self.run_adb("shell", "pm", "clear", package)
        self.run_adb("logcat", "-c")
        # a sleeping or locked screen pauses the app
        for cmd in (["input", "keyevent", "KEYCODE_WAKEUP"], ["wm", "dismiss-keyguard"],
                    ["svc", "power", "stayon", "true"]):
            subprocess.run([self.adb, "shell"] + cmd, capture_output=True)
        self.run_adb("shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")
        self.run_adb("forward", "tcp:%d" % port, "localabstract:%s.repl" % package)
        end = time.time() + 120
        last = None
        while time.time() < end:
            try:
                self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
                self.reader = self.sock.makefile("r", encoding="utf-8")
                j = self._eval("1", 10)
                if j.get("ok"):
                    return
            except (OSError, SmokeError, ValueError) as e:
                last = e
            time.sleep(2)
        raise SmokeError("no REPL socket from %s: %s" % (package, last))

    def run_adb(self, *args):
        r = subprocess.run([self.adb] + list(args), capture_output=True, text=True)
        if r.returncode:
            raise SmokeError("adb %s failed: %s" % (" ".join(args), (r.stderr or r.stdout).strip()))
        return r.stdout

    def _eval(self, cmd, timeout):
        # one line in, one line of JSON out
        self.sock.settimeout(timeout)
        try:
            self.sock.sendall((" ".join(cmd.splitlines()) + "\n").encode("utf-8"))
            line = self.reader.readline()
        except OSError as e:
            raise SmokeError("REPL socket: %s" % e)
        if not line:
            raise SmokeError("the REPL socket closed (did the app stop?)")
        return json.loads(line)

    def output(self):
        r = subprocess.run([self.adb, "logcat", "-d"], capture_output=True)
        text = r.stdout.decode("utf-8", "replace")
        with open(self.log_path, "w", encoding="utf-8") as f:
            f.write(text)
        return text

    def alive(self):
        r = subprocess.run([self.adb, "shell", "pidof", self.package], capture_output=True)
        if r.returncode:
            raise SmokeError("%s is not running" % self.package)
        return True

    def snapshot(self, path):
        with open(path, "wb") as f:
            subprocess.run([self.adb, "exec-out", "screencap", "-p"], stdout=f)

    def stop(self):
        subprocess.run([self.adb, "shell", "am", "force-stop", self.package], capture_output=True)
        subprocess.run([self.adb, "forward", "--remove", "tcp:%d" % self.port], capture_output=True)


class WebEngine(Engine):
    """The browser build in headless Chromium, through krkrz_web's krkrz_repl_eval bridge (the
    one the devtools console's tjs() calls).

    The browser build loads scenario and image files on demand, and a load can only wait for
    its download from the engine's own loop: one started inside a krkrz_repl_eval call
    crashed the page. So every command runs from a Timer, and the bridge only starts it and
    reads its result back."""

    def __init__(self, url, workdir, verbose, channel=None):
        from playwright.sync_api import sync_playwright
        self.workdir = workdir
        self.verbose = verbose
        self.modals = []
        self.lines = []
        self.log_path = os.path.join(workdir, "console.txt")
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(channel=channel,
                                               args=["--autoplay-policy=no-user-gesture-required"])
        self.page = self.browser.new_page(viewport={"width": 1280, "height": 720})
        # written as it comes, so a page that hangs still leaves its console behind
        self.console = open(self.log_path, "w", encoding="utf-8")
        self.page.on("console", lambda m: self._line(m.text))
        self.page.on("pageerror", lambda e: self._line("pageerror: %s" % e))
        # the browser's console names no URL for a failed load
        self.page.on("response", lambda r: r.status >= 400 and self._line("HTTP %d %s" % (r.status, r.url)))
        # audiogate=0: start without waiting for a click (Chromium may play audio anyway here)
        self.page.goto(url + ("&" if "?" in url else "?") + "audiogate=0")
        end = time.time() + 180
        last = None
        while time.time() < end:
            try:
                # ccall throws until the runtime is up; then wait for the game window
                if self._raw('typeof global.kag == "Object" && kag !== void').get("result") == "1":
                    return
            except SmokeError as e:
                last = e
            time.sleep(2)
        raise SmokeError("the engine didn't start in the page (%s); console:\n%s"
                         % (last, "\n".join(self.lines[-40:])))

    def _raw(self, cmd):
        js = "c => Module.ccall('krkrz_repl_eval', 'string', ['string'], [c])"
        try:
            j = json.loads(self.page.evaluate(js, cmd))
        except Exception as e:
            raise SmokeError("page: %s" % e)
        j["result"] = str(j.get("result", "")).strip()
        return j

    def _eval(self, cmd, timeout):
        start = self._raw("""(function() {
            global.__smokeRes = void;
            global.__smokeFn = function() { return %s; };
            if (typeof global.__smokeTimer == "undefined") {
                global.__smokeRun = function() {
                    global.__smokeTimer.enabled = false;
                    try { global.__smokeRes = %%[ok: 1, value: global.__smokeFn()]; }
                    catch (e) { global.__smokeRes = %%[ok: 0, error: e.message]; }
                };
                global.__smokeTimer = new Timer(global.__smokeRun, "");
                global.__smokeTimer.interval = 1;
            }
            global.__smokeTimer.enabled = true;
            return 1;
        })()""" % cmd)
        if not start.get("ok"):
            return start
        end = time.time() + timeout
        while time.time() < end:
            if self._raw("global.__smokeRes !== void")["result"] == "1":
                if self._raw("global.__smokeRes.ok")["result"] == "1":
                    return {"ok": True, "result": self._raw("global.__smokeRes.value")["result"]}
                return {"ok": False, "error": self._raw("global.__smokeRes.error")["result"]}
            time.sleep(0.02)
        raise SmokeError("no answer from the engine within %ss:\n%s" % (timeout, cmd))

    def _line(self, text):
        self.lines.append(text)
        if not self.console.closed:
            self.console.write(text + "\n")
            self.console.flush()

    def output(self):
        return "\n".join(self.lines)

    def snapshot(self, path):
        try:
            self.page.screenshot(path=path)
        except Exception:
            pass

    def stop(self):
        try:
            self.browser.close()
        finally:
            self.pw.stop()
            self.console.close()


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
        eng.wait("sf.clear", "sf.clear ? 1 : 0", timeout=5)

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
            if failures <= 3 and eng.workdir:
                eng.snapshot(os.path.join(eng.workdir, "fail-%d.png" % failures))
            try:
                eng.alive()
            except SmokeError as e:
                print("     " + str(e), flush=True)
                break
            try:
                eng.clicker(False)
            except SmokeError:
                pass
    return failures


def start_engine(opts, data, workdir):
    if opts.target == "android":
        return AndroidEngine(opts.apk, opts.package, workdir, opts.verbose, adb=opts.adb)
    if opts.target == "ios-sim":
        return SimulatorEngine(opts.app, opts.bundle_id, workdir, opts.verbose, opts.device)
    if opts.target == "web":
        return WebEngine(opts.url, workdir, opts.verbose, opts.channel)
    return DesktopEngine(opts.engine, data, workdir, opts.verbose)


def run_project(opts, label, data, make_steps):
    print("== %s (%s, %s)" % (label, data, opts.target), flush=True)
    workdir = tempfile.mkdtemp(prefix="kagex-smoke-")
    try:
        eng = start_engine(opts, data, workdir)
    except SmokeError as e:
        print("FAIL starting the engine:", e)
        print("kept", workdir)
        return 1
    failures = 0
    try:
        failures = run_steps(eng, make_steps(eng))
    except Exception as e:  # a bug here still gets the engine's log printed
        failures += 1
        print("FAIL %s: %s" % (type(e).__name__, e))
    finally:
        try:
            eng.tjs('if (typeof global.__smokeClicker == "Object") __smokeClicker.enabled = false; return 1;', 3)
        except Exception:
            pass
        eng.snapshot(os.path.join(workdir, "last.png"))
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
    ap.add_argument("--target", choices=["desktop", "android", "ios-sim", "web"], default="desktop")
    ap.add_argument("--apk", help="android: the APK to install")
    ap.add_argument("--package", default="io.github.krkren.kagex", help="android: its applicationId")
    ap.add_argument("--adb", default="adb")
    ap.add_argument("--app", help="ios-sim: the .app to install")
    ap.add_argument("--bundle-id", default="io.github.krkren.kagex")
    ap.add_argument("--device", default="booted", help="ios-sim: the Simulator (UDID)")
    ap.add_argument("--url", help="web: the page that runs the game")
    ap.add_argument("--channel", help="web: an installed browser for Playwright to use (chrome), "
                    "instead of its own Chromium")
    opts = ap.parse_args()
    if opts.target != "desktop":
        opts.only = "sample"  # the platform packages hold the sample only

    failures = 0
    if opts.only in (None, "sample"):
        failures += run_project(opts, "sample", "data", sample_steps)
    if opts.only in (None, "template"):
        failures += run_project(opts, "template", "template", template_steps)
    print("smoke test:", "FAILED (%d)" % failures if failures else "passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
