#!/usr/bin/env python3
"""Headless smoke test for the KAGEX sample.

Starts the engine with SDL's offscreen video driver and drives the sample through the
engine's REPL file channel (-replfile, see krkrz_dev src/core/doc/REPL.md): the title screen,
each demo scene (compiled from the scripts in !scnlist.txt where the data folder is writable,
doc/scn.txt), save and load, the config and extras screens, a Yes/No prompt and the About
screen. On the desktop it also compiles the scripts with -scncompile=all. It fails when a step doesn't reach the state it expects, when the engine raises a
script exception, or when the engine opens a native modal dialog (an error message box or a
Yes/No that should have been drawn in the game window).

It then runs template/ as a game of its own, the way a new game starts out, and checks that
it starts and that its prompts are drawn in the game window too.

usage: python3 tools/smoketest.py [--engine ./krkrz] [--only sample|template] [--keep] [--verbose]
                                 [--effekseer required|optional] [--vector required|optional]
                                 [--zip required|optional] [--clip required|optional]

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

  --engine <exe> --packaged            a desktop package (kagex-release's Windows or Linux
                                       build of the sample): the exe with the data it was
                                       packaged with, without a project folder
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


def storage_name(path):
    """A local path as the engine names it: file://./home/... or file://./c/Users/..."""
    path = os.path.abspath(path).replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", path):
        return "file://./" + path[0].lower() + path[2:]
    return "file://." + path


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

    def tjs(self, body, timeout=30.0):
        """As Engine.tjs, but the main thread writes the result to a file. The file channel
        pretty-prints a result on its own thread, and a TJS string or object handled there races
        the main thread's reference counts: engine 2.6.5 aborted with "double free or corruption"
        now and then (UPSTREAM.md). So the REPL only gets the number 0 back."""
        out = os.path.join(self.chan, "result.txt")
        if os.path.exists(out):
            os.remove(out)
        cmd = ("(function(r) { var t = typeof r; var a = [ t == 'String' ? 'S' + r"
               " : (t == 'Integer' || t == 'Real') ? 'N' + r : t == 'void' ? 'V' : 'O' + (string)r ];"
               " a.save('%s'); return 0; })((function() {\n%s\n})())") % (storage_name(out), body)
        j = self._eval(cmd, timeout)
        if not j.get("ok"):
            raise SmokeError("TJS failed: %s\n%s" % (j.get("error"), body))
        with open(out, encoding="utf-16") as f:   # Array.save: UTF-16 with a BOM
            text = f.read()
        text = text[:-1] if text.endswith("\n") else text
        text = text[:-1] if text.endswith("\r") else text
        kind, value = text[:1], text[1:]
        if kind == "N":
            try:
                return int(value)
            except ValueError:
                return float(value)
        if kind == "V":
            return "(void)"
        return value

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
        os.makedirs(self.savedir, exist_ok=True)  # it may already hold the boot patches
        self.log_path = os.path.join(workdir, "engine.log")
        self.verbose = verbose
        self.modals = []
        env = dict(os.environ)
        env.setdefault("SDL_VIDEO_DRIVER", "offscreen")
        env.setdefault("SDL_AUDIO_DRIVER", "dummy")
        # without data: a package, which runs the data it holds
        args = [exe] + ([os.path.abspath(data)] if data else []) + \
            ["-datapath=" + self.savedir + "/", "-replfile=" + self.chan, "-replmodaltimeout=0"]
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

    def __init__(self, url, workdir, verbose, channel=None, init_script=None):
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
        if init_script:
            self.page.add_init_script(init_script)
        # written as it comes, so a page that hangs still leaves its console behind
        self.console = open(self.log_path, "w", encoding="utf-8")
        self.page.on("console", lambda m: self._line(m.text))
        self.page.on("pageerror", lambda e: self._line("pageerror: %s" % e))
        # the browser's console names no URL for a failed load
        self.page.on("response", lambda r: r.status >= 400 and self._line("HTTP %d %s" % (r.status, r.url)))
        # audiogate=0: start without waiting for a click (Chromium may play audio anyway here)
        self.page.goto(url + ("&" if "?" in url else "?") + "audiogate=0")
        start = time.time()
        end = start + 180
        last = None
        while time.time() < end:
            try:
                # ccall throws until the runtime is up; then wait for the game window
                if self._raw('typeof global.kag == "Object" && kag !== void').get("result") == "1":
                    return
            except SmokeError as e:
                last = e
                # in the console file only, so a page that never starts shows where it stopped
                if not self.console.closed:
                    self.console.write("(smoke test, %.1f s) %s\n" % (time.time() - start, str(e).split("\n")[0][:200]))
            time.sleep(2)
        err = SmokeError("the engine didn't start in the page (%s); console:\n%s"
                         % (last, "\n".join(self.lines[-40:])))
        # a Playwright left running made the next WebEngine fail ("Sync API inside the
        # asyncio loop"), hiding whether that page would have started
        self.stop()
        raise err

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


DEMOS = ["layer.ks", "char.ks", "envlayer.ks", "transition.ks", "action.ks", "effect.ks", "anim.ks"]


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


def effekseer_framework(eng):
    """Whether the framework plays Effekseer effects (0.4.0 and later): pages.yml runs this test
    on a release's site, which may be older"""
    return eng.tjs('return typeof global.KAGEffekseerOf != "undefined" ? 1 : 0;') == 1


def page_framework(eng):
    """Whether the scene player draws a message window's earlier lines again after a jump
    (KAGEnvPlayer.redrawPage, 0.9.3)"""
    return eng.tjs('return typeof world_object.player.redrawPage != "undefined" ? 1 : 0;') == 1


def animated_framework(eng):
    """Whether the sample has the Animated Character demo (0.8.0 and later; pages.yml may test an
    older release's site)"""
    # a package compiled by kagex-release has anim.ks.scn and no anim.ks
    return eng.tjs('return Storages.isExistentStorage("anim.ks") || (typeof global.scnFindCompiled != "undefined"'
                   ' && scnFindCompiled("anim.ks") !== void) ? 1 : 0;') == 1


def compiled_framework(eng):
    """Whether the framework compiles scenarios (SceneParser.tjs; pages.yml may test an older
    release's site)"""
    return eng.tjs('return typeof global.KAGCompileScenarios != "undefined" ? 1 : 0;') == 1


def sample_steps(eng):
    steps, step = collector()
    eng.compiled = False

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

    @step("the scripts in !scnlist.txt compile, so the demos play compiled")
    def _():
        # SceneParser.tjs writes <script>.scn.json next to each script, where that's a local
        # folder; a package (web, phones, an archive) plays the scripts themselves
        if not compiled_framework(eng):
            print("     (skipped: this build's framework predates compiled scenarios)", flush=True)
            return
        # a package compiled by kagex-release (doc/scn.txt) holds the compiled files and not the
        # scripts
        if eng.tjs('world_object.initPlayer(); return !Storages.isExistentStorage("s0001.ks") &&'
                   ' scnFindCompiled("s0001.ks") !== void ? 1 : 0;') == 1:
            print("     (a package with compiled scenarios: the demos play those)", flush=True)
            eng.compiled = True
            return
        if eng.tjs("return world_object.player.readonlydb ? 1 : 0;") == 1:
            # the platform packages (web, phones) carry the sample's scenarios compiled by CI
            if eng.tjs('return scnFindCompiled("s0001.ks") !== void ? 1 : 0;') == 1:
                print("     (a read-only package with the scenarios compiled into it: the demos play those)", flush=True)
                eng.compiled = True
                return
            print("     (skipped: this build can't write compiled scenarios, so the demos play from the scripts)",
                  flush=True)
            return
        r = str(eng.tjs('var r = KAGCompileScenarios(true), p = world_object.player.parser;'
                        ' var kind = typeof p.writesPsb != "undefined" && p.writesPsb ? ".scn" : ".scn.json";'
                        ' return [r.compiled, r.failed, r.warnings, kind, r.errors.join(" / ")].join(",");',
                        timeout=120)).split(",", 4)
        print("     %s compiled to %s, %s warning(s)" % (r[0], r[3], r[2]), flush=True)
        if r[1] != "0" or r[0] == "0":
            raise SmokeError("compiling failed: " + r[4])
        eng.compiled = True

    @step("a compiled script starts from the World the script that goes to it leaves")
    def _():
        if not eng.compiled or eng.tjs('return typeof world_object.player.compileList != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no compiled scenes here, or a framework from before entry states)", flush=True)
            return
        # the web and the phones play the scenarios CI compiled: they don't compile (readonlydb),
        # and their save folder isn't on the auto path
        if eng.tjs("return world_object.player.readonlydb ? 1 : 0;") == 1:
            print("     (skipped: a read-only package doesn't compile)", flush=True)
            return
        # two scripts in the save folder: A puts Ai on the road and jumps to B, which shows
        # text only. Compiled B before A (round two compiles B again), B's first save point holds
        # what A left (SceneParser.entryFor), as playing the scripts would
        r = str(eng.tjs(r'''
            var dir = System.dataPath;
            [ "*start|Carry A", "[initscene]", "[road normal]", "[ai standard center]", "Ai is here.[p]",
              "[jump storage=zz_carry_b.ks]" ].save(dir + "zz_carry_a.ks");
            [ "*start|Carry B", "Still here.[p]" ].save(dir + "zz_carry_b.ks");
            Storages.addAutoPath(dir);
            var p = world_object.player;
            var c = p.compileList([ "zz_carry_b.ks", "zz_carry_a.ks" ], true);
            if (c.failed > 0) return "failed: " + c.errors.join(" / ");
            var d = new StorageData("zz_carry_b.ks");
            var sp = d.root.scenes[0].lines[0], st = sp[1], ai = 0, stage = "";
            if (typeof st == "Object" && st.characters !== void)
                for (var i = 0; i < st.characters.count; i++) if (st.characters[i].name == "ai") ai++;
            if (typeof st == "Object" && st.stage !== void) stage = "yes";
            var again = p.parser.isNeedParse("zz_carry_b.ks") || p.parser.isNeedParse("zz_carry_a.ks");
            var ret = [ c.compiled, ai, stage, d.root.entry, again ? 1 : 0 ].join(",");
            invalidate d;
            return ret;''', timeout=120))
        print("     compiled, Ai in B's first state, its stage, B's entry key, still to compile: " + r, flush=True)
        f = r.split(",")
        if len(f) < 5 or f[0] != "2" or f[1] != "1" or f[2] == "" or f[3] == "" or f[4] != "0":
            raise SmokeError("B didn't start from what A left: " + r)

    for demo in DEMOS:
        @step("demo " + demo + " plays to the end")
        def _(demo=demo):
            if demo == "effect.ks" and not effekseer_framework(eng):
                print("     (skipped: this build's framework predates the Effekseer demo)", flush=True)
                return
            if demo == "anim.ks" and not animated_framework(eng):
                print("     (skipped: this build predates the Animated Character demo)", flush=True)
                return
            eng.tjs('kag.process("%s", "*start"); return 1;' % demo)
            eng.wait(demo, 'kag.conductor.curStorage == "%s"' % demo, timeout=10)
            if eng.compiled:
                eng.wait(demo + " played compiled", 'world_object.player !== void && world_object.player.working'
                         ' && world_object.player.curStorage == "%s"' % demo, timeout=10)
            eng.clicker(True, until="s0001.ks")
            eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks"', timeout=180)
            eng.clicker(False)

    @step("finishing every demo unlocks Extras")
    def _():
        eng.wait("sf.clear", "sf.clear ? 1 : 0", timeout=5)

    @step("compiled text gets the word wrap")
    def _():
        if not eng.compiled:
            print("     (skipped: the demos play from the scripts here)", flush=True)
            return
        # The word wrap reads the conductor's scenario line, which is the stand-in's
        # [sceneplay] while the player shows text: the player's ch tags bring the message
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks's first text", 'world_object.player !== void && world_object.player.working'
                 ' && world_object.player.curTextId >= 1 && kag.inStable', timeout=20)
        r = str(eng.tjs('var t = world_object.player.curText.text, w = kag.wrapSplitLine;'
                        ' return [kag.wrapKey, w !== void ? w.count : -1, t.split(" ").count, t].join("|");'))
        key, words, expected, text = r.split("|", 3)
        if not key.startswith("scene:") or words != expected:
            raise SmokeError("the word wrap didn't take the compiled text (%s): %s" % (r, text))

    @step("a compiled scene saves in the middle and loads where it was")
    def _():
        if not eng.compiled:
            print("     (skipped: the demos play from the scripts here)", flush=True)
            return
        state = ('var p = world_object.player, c = world_object.env.characters["ai"];'
                 ' return [p.curSceneName, p.curTextId, p.curPoint, c !== void && c.isShowBU() ? 1 : 0].join(",");')
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'world_object.player !== void && world_object.player.working', timeout=20)
        # read on to its sixth text: Ai is on the screen, under another name
        eng.tjs("""
            global.__smokeToText = new Timer(function() {
                if (world_object.player.curTextId >= 6) { global.__smokeToText.enabled = false; return; }
                kag.onPrimaryClick();
            }, "");
            __smokeToText.interval = 50;
            __smokeToText.enabled = true;
            return 1;""")
        eng.wait("the sixth text", "world_object.player.curTextId >= 6 && kag.inStable", timeout=60)
        eng.tjs("invalidate global.__smokeToText; return 1;")
        before = str(eng.tjs(state))
        print("     saved at", before, flush=True)
        if not before.endswith(",1"):
            raise SmokeError("Ai isn't on the screen at the sixth text: " + before)
        eng.tjs("kag.saveBookMark(1); return 1;")
        eng.wait("data1 to be written",
                 "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(1))", timeout=10)
        eng.tjs('kag.goToStart(); return 1;')
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)
        eng.tjs("loadFunction(1); return 1;")
        text = before.split(",")[1]
        eng.wait("the save to load", 'world_object.player.working && world_object.player.curTextId == %s'
                 ' && kag.inStable' % text, timeout=30)
        after = str(eng.tjs(state))
        if after != before:
            raise SmokeError("loaded at %s, saved at %s" % (after, before))

    @step("BACK goes back a message, and the backlog's marks go back to theirs")
    def _():
        if not eng.compiled or eng.tjs('return typeof global.rollBack != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no compiled scenes, or a framework from before going back)", flush=True)
            return
        # where the last step left the game: the sixth text of char.ks, Ai on the screen, its
        # backlog written again from the history the save had
        state = ('var p = world_object.player, hl = kag.historyLayer, c = world_object.env.characters["ai"], marks = 0;'
                 ' for (var i = 0; i < hl.dataLines; i++) if (hl.jumpInfo[hl.jumpIndex(i)] !== void) marks++;'
                 ' return [p.curTextId, p.getHistoryCount(), marks, c !== void && c.isShowBU() ? 1 : 0].join(",");')
        before = str(eng.tjs(state)).split(",")
        if before[1] != before[2]:
            raise SmokeError("after loading, the backlog has %s marks for %s messages" % (before[2], before[1]))
        eng.wait("BACK to be enabled", 'canRollBack()', timeout=10)
        eng.tjs("rollBack(); return 1;")
        eng.wait("the message before", 'world_object.player.curTextId == %d && kag.inStable' % (int(before[0]) - 1),
                 timeout=20)
        back = str(eng.tjs(state)).split(",")
        print("     text, history, backlog marks, Ai shown: %s, then BACK: %s" % (",".join(before), ",".join(back)),
              flush=True)
        if back[1] != str(int(before[1]) - 1) or back[2] != back[1]:
            raise SmokeError("BACK left the history and backlog at %s (from %s)" % (back, before))
        # the first message's mark in the backlog, and Yes: the start of the scene, before Ai
        eng.tjs("kag.showHistory(); return 1;")
        eng.wait("the backlog", "kag.historyShowing", timeout=10)
        eng.tjs("var hl = kag.historyLayer; Scripts.eval(hl.jumpInfo[hl.jumpIndex(0)]); return 1;")
        eng.wait("the prompt", "kag.currentDialog !== void", timeout=10)
        eng.key("VK_LEFT")  # the focus starts on No
        eng.key("VK_RETURN")
        eng.wait("the first message", '!kag.historyShowing && world_object.player.curTextId == 1 && kag.inStable',
                 timeout=20)
        first = str(eng.tjs(state)).split(",")
        if first[1:] != ["1", "1", "0"]:
            raise SmokeError("the first message's mark went to %s (text, history, marks, Ai shown)" % first)

    @step("a demo chosen from the menu: BACK goes back to the menu, and another choice plays")
    def _():
        if not eng.compiled or eng.tjs('return typeof global.rollBack != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no compiled scenes, or a framework from before going back)", flush=True)
            return
        # the menu's choice is in the history: what BACK and the backlog read has to cope with it
        menu = ('kag.inStable && kag.selectShowing && kag._selectLayer !== void && kag._selectLayer.selects.count > 0')
        eng.tjs('kag.process("s0001.ks"); return 1;')
        eng.wait("the demo menu", menu, timeout=30)
        eng.tjs("kag._selectLayer.onButtonClick(kag._selectLayer.selects[0]); return 1;")
        eng.wait("layer.ks", 'world_object.player !== void && world_object.player.curStorage == "layer.ks" && kag.inStable',
                 timeout=30)
        first = str(eng.tjs('var p = world_object.player; return [p.getHistoryCount(), p.histories[0].text].join("|");'))
        if not first.startswith("2|Choice: "):
            raise SmokeError("the history at the demo's first text is %s" % first)
        eng.wait("BACK to be enabled", 'canRollBack()', timeout=10)
        eng.tjs("rollBack(); return 1;")
        eng.wait("the demo menu again", menu, timeout=30)
        eng.tjs("kag._selectLayer.onButtonClick(kag._selectLayer.selects[1]); return 1;")
        eng.wait("char.ks", 'world_object.player !== void && world_object.player.curStorage == "char.ks" && kag.inStable',
                 timeout=30)
        then = str(eng.tjs('var p = world_object.player; return [p.getHistoryCount(), p.histories[0].text].join("|");'))
        if then != "2|Choice: World Extension: Character":
            raise SmokeError("after going back and choosing again, the history is %s" % then)

    @step("BACK in a scene on KAG's own layers brings them back as they were")
    def _():
        if not eng.compiled or eng.tjs('return typeof global.rollBack != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no compiled scenes, or a framework from before going back)", flush=True)
            return
        # layer.ks's pictures are on KAG layer 0, which the compiled save points don't hold:
        # going back restores KAG's state from the click it goes to (KAGEnvPlayer.storeKagState)
        eng.tjs('kag.process("layer.ks", "*start"); return 1;')
        eng.wait("layer.ks", 'world_object.player !== void && world_object.player.working', timeout=20)
        # the timer also notes where each text left the message window's pen (kag.current.y):
        # layer.ks's lines build up in one window, each on a line of its own
        eng.tjs("""
            global.__smokePen = %[];
            global.__smokeToText = new Timer(function() {
                var p = world_object.player;
                if (kag.inStable && p.curTextId !== void) global.__smokePen[p.curLabel + ":" + p.curTextId] = kag.current.y;
                if (p.curLabel == "*label2") { global.__smokeToText.enabled = false; return; }
                kag.onPrimaryClick();
            }, "");
            __smokeToText.interval = 50;
            __smokeToText.enabled = true;
            return 1;""")
        eng.wait("Rotation", 'world_object.player.curLabel == "*label2" && kag.inStable', timeout=60)
        eng.tjs("invalidate global.__smokeToText; return 1;")
        layer = ('var l = kag.fore.layers[0], p = world_object.player;'
                 ' return [p.curLabel, p.curTextId, l.visible ? 1 : 0, l.opacity, kag.current.y].join(",");')
        at = str(eng.tjs(layer))
        eng.wait("BACK to be enabled", 'canRollBack()', timeout=10)
        eng.tjs("rollBack(); return 1;")
        eng.wait("Translucency", 'world_object.player.curLabel == "*label1" && kag.inStable', timeout=20)
        back = str(eng.tjs(layer))
        print("     layer 0 at %s, after BACK %s (label, text, visible, opacity, pen y)" % (at, back), flush=True)
        if back.split(",")[2:4] != ["1", "200"]:
            raise SmokeError("after BACK, layer 0 is %s, not the translucent picture of *label1" % back)
        # "Translucent" is the second line of its window ("Start" above it): going back draws
        # "Start" again, so the pen is where playing left it (KAGEnvPlayer.redrawPage)
        if page_framework(eng):
            pens = str(eng.tjs('var a = [], d = global.__smokePen; return [d["*start:2"], d["*label1:1"]].join(",");')).split(",")
            print("     the pen at Start and Translucent while playing: %s" % ",".join(pens), flush=True)
            if pens[1] == "" or pens[0] == pens[1]:
                raise SmokeError("while playing, Translucent wasn't below Start (%s)" % pens)
            if back.split(",")[4] != pens[1]:
                raise SmokeError("after BACK the pen is at %s, not at %s where Translucent was drawn below Start"
                                 % (back.split(",")[4], pens[1]))
            # drawn again without writing to the backlog, which has it once already
            starts = eng.tjs('var hl = kag.historyLayer, n = 0; for (var i = 0; i < hl.dataLines; i++)'
                             ' { var l = hl.getLine(i); if (typeof l == "String" && l == "Start") n++; } return n;')
            if starts != 1:
                raise SmokeError("after BACK the backlog has %s lines \"Start\"" % starts)
            # a load there draws the page again too
            eng.tjs("kag.saveBookMark(2); return 1;")
            eng.wait("data2 to be written",
                     "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(2))", timeout=10)
            eng.tjs('kag.goToStart(); return 1;')
            eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)
            eng.tjs("loadFunction(2); return 1;")
            eng.wait("the save to load", 'world_object.player.working && world_object.player.curLabel == "*label1"'
                     ' && world_object.player.curTextId == 1 && kag.inStable', timeout=30)
            loaded = str(eng.tjs(layer))
            starts = eng.tjs('var hl = kag.historyLayer, n = 0; for (var i = 0; i < hl.dataLines; i++)'
                             ' { var l = hl.getLine(i); if (typeof l == "String" && l == "Start") n++; } return n;')
            print("     loaded there: %s, %s line(s) \"Start\" in the backlog" % (loaded, starts), flush=True)
            if loaded.split(",")[4] != pens[1] or starts != 1:
                raise SmokeError("after a load at Translucent the pen is at %s (not %s), the backlog has %s lines \"Start\""
                                 % (loaded.split(",")[4], pens[1], starts))

    @step("the animated character blinks, and its mouth follows its voice")
    def _():
        if not animated_framework(eng):
            print("     (skipped: this build predates the Animated Character demo)", flush=True)
            return
        pip = 'var c = world_object.env.characters["pip"]; '
        eng.tjs('kag.process("anim.ks", "*start"); return 1;')
        eng.wait("Pip", 'world_object.env.characters["pip"] !== void && kag.inStable', timeout=20)
        # drawn, and on the screen: Pip's picture has its anchor on the canvas centre, which the
        # World puts at the centre of the screen
        drawn = eng.tjs(pip + 'var l = c.standlayer, n = 0; for (var y = 0; y < l.imageHeight; y += 16)'
                        ' for (var x = 0; x < l.imageWidth; x += 16) if (l.getMaskPixel(x, y) > 0) n++;'
                        ' var t = c.targetLayer; return [n, t.visible ? 1 : 0, (int)(t._affinetop - t.afy),'
                        ' (int)(t._affinetop - t.afy + l.imageHeight)].join(",");')
        n, visible, top, bottom = [int(v) for v in str(drawn).split(",")]
        print("     Pip: %d of its samples drawn, from y %d to %d" % (n, top, bottom), flush=True)
        if n < 300 or not visible or bottom < 200 or top > 900:
            raise SmokeError("Pip isn't drawn on the screen: %s" % drawn)
        # blinking: make every eye frame start a blink, and watch the eyes close. A timer in the
        # game notes the eyes every 20 ms: the eyes are open for a frame between blinks, which
        # asking through the REPL missed on the macOS runner
        eng.tjs('global.__smokeBlink = eyeFlipFreq; eyeFlipFreq = 1.0; global.__smokeEyes = %[];'
                ' global.__smokeEyeTimer = new Timer(function() {'
                ' var c = world_object.env.characters["pip"]; if (c === void) return;'
                ' global.__smokeEyes[c.eyeLevel === void ? "-1" : (string)c.eyeLevel] = 1;'
                ' }, ""); __smokeEyeTimer.interval = 20; __smokeEyeTimer.enabled = true; return 1;')
        end = time.time() + 3
        while time.time() < end:
            time.sleep(0.5)
            if eng.tjs('return __smokeEyes["0"] && __smokeEyes["2"] ? 1 : 0;') == 1:
                break
        seen = str(eng.tjs('__smokeEyeTimer.enabled = false; invalidate __smokeEyeTimer;'
                           ' eyeFlipFreq = global.__smokeBlink; var a = []; a.assign(__smokeEyes);'
                           ' var k = []; for (var i = 0; i < a.count; i += 2) k.add(a[i]); return k.join(" ");')).split()
        if not {"0", "2"} <= set(seen):
            raise SmokeError("Pip's eyes didn't blink (eye levels seen: %s)" % sorted(seen))
        # lip-sync: its first line plays a voice. A timer in the game notes the mouth every 20 ms
        # while it plays (asking through the REPL is too slow on some targets)
        eng.tjs('global.__smokeLips = [], global.__smokeVoice = [];'
                ' global.__smokeLipTimer = new Timer(function() {'
                ' var c = world_object.env.characters["pip"], b = c !== void ? c.soundBuffer : void;'
                ' if (b !== void && b.status == "play") { global.__smokeLips.add(c.lipLevel); global.__smokeVoice.add(b.position); }'
                ' }, ""); __smokeLipTimer.interval = 20; __smokeLipTimer.enabled = true; return 1;')
        eng.tjs('kag.onPrimaryClick(); return 1;')
        end = time.time() + 6
        while time.time() < end:
            time.sleep(0.5)
            if eng.tjs('return __smokeLips.count > 0 && world_object.env.characters["pip"].soundBuffer.status != "play" ? 1 : 0;') == 1:
                break
        r = str(eng.tjs('__smokeLipTimer.enabled = false; invalidate __smokeLipTimer;'
                        ' var p = %[]; for (var i = 0; i < __smokeVoice.count; i++) p[__smokeVoice[i]] = 1;'
                        ' var n = []; n.assign(p);'
                        ' return [__smokeLips.join(" "), n.count \\ 2, lipSyncSource].join(",");')).split(",")
        levels = [int(v) for v in r[0].split()] if r[0].strip() else []
        positions, source = int(r[1]), r[2]
        print("     lip-sync from %s: %d mouth samples while the voice played (%s), at %d positions"
              % (source or "(random)", len(levels), " ".join(str(v) for v in levels[:60]), positions), flush=True)
        if positions <= 1:
            print("     (the voice doesn't play here, so the mouth isn't checked)", flush=True)
        elif not {0, 2} <= set(levels):
            raise SmokeError("Pip's mouth didn't open and close with its voice (levels seen: %s)" % sorted(set(levels)))
        eng.clicker(True, until="s0001.ks")
        eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks"', timeout=180)
        eng.clicker(False)

    @step("extrans's and extNagano's transitions are there, not crossfades")
    def _():
        # transition.ks plays all of them; without their plugin they'd quietly be crossfades
        if eng.tjs('return typeof global.KAGPluginTransitions != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the extNagano transitions)", flush=True)
            return
        missing = eng.tjs('var a = []; foreach(KAGPluginTransitions, function(k, v, d, a) {'
                          ' if (v != "linked") a.add(k); }, a); return a.join(" ");')
        if missing:
            raise SmokeError("these transitions' plugin isn't loaded: " + missing)

    @step("an Effekseer effect draws (--effekseer required), or the build says why not")
    def _():
        if not effekseer_framework(eng):
            print("     (skipped: this build's framework predates Effekseer effects)", flush=True)
            return
        why = eng.tjs('var s = KAGEffekseerOf(kag); return s.available ? "" : "unavailable: " + s.reason;')
        print("     Effekseer:", why or "available", flush=True)
        if why:
            if eng.opts.effekseer == "required":
                raise SmokeError("Effekseer effects are " + why)
            return
        eng.tjs('kag.tagHandlers.image(%[layer:"0", page:"fore", flip:"sparkle.efk", visible:"true"]); return 1;')
        time.sleep(1.5)
        n = eng.tjs('var l = kag.fore.layers[0], n = 0; for (var y = 0; y < l.height; y += 8)'
                    ' for (var x = 0; x < l.width; x += 8) if (l.getMainPixel(x, y)) n++;'
                    ' kag.tagHandlers.freeimage(%[layer:"0", page:"fore"]); return n;')
        if n <= 0:
            raise SmokeError("sparkle.efk drew nothing")

    @step("an SVG image draws, zoomed and turned too (--vector required), or the build says why not")
    def _():
        if eng.tjs('return typeof global.affineVectorImages != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates SVG images)", flush=True)
            return
        if eng.tjs("return affineVectorImages ? 1 : 0;") != 1:
            if eng.opts.vector == "required":
                raise SmokeError("SVG images are unavailable: no layerExVector")
            print("     SVG: unavailable (no layerExVector)", flush=True)
            return
        # The emblem (tools/assets/make_vector.py) is an opaque disc in the theme's violets on a
        # clear square. Count its opaque pixels and their average colour as drawn plain, zoomed
        # and turned: layerExVector once drew turned pictures cut off (AffineLayer.tjs)
        eng.tjs('kag.tagHandlers.image(%[layer:"0", page:"fore", storage:"emblem", visible:"true",'
                ' left:"960", top:"540", dafx:"center", dafy:"center"]); return 1;')
        counts = {}
        for name, opts in (("plain", ""), ("zoomed", 'zoom:"200"'), ("turned", 'rotate:"30"')):
            eng.tjs('kag.tagHandlers.layopt(%%[layer:"0", page:"fore", reset:"true"]);%s return 1;'
                    % (' kag.tagHandlers.layopt(%%[layer:"0", page:"fore", %s]);' % opts if opts else ""))
            time.sleep(0.5)
            n, r, b = [int(v) for v in eng.tjs(
                # an AffineLayer's width and pixels are its source image's; assignImages copies
                # what it drew (the layer's own buffer, the size of the screen)
                'var t = new global.Layer(kag, kag.primaryLayer), n = 0, r = 0, b = 0;'
                ' t.assignImages(kag.fore.layers[0]);'
                ' for (var y = 2; y < t.imageHeight; y += 6) for (var x = 2; x < t.imageWidth; x += 6)'
                ' if (t.getMaskPixel(x, y) > 200) { var p = t.getMainPixel(x, y); n++; r += (p >> 16) & 255;'
                ' b += p & 255; } invalidate t; return "%d %d %d".sprintf(n, n ? r \\ n : 0, n ? b \\ n : 0);').split()]
            print("     %s: %d opaque samples, average red %d, blue %d" % (name, n, r, b), flush=True)
            if n < 1500 or b < 200 or r > b:
                raise SmokeError("the SVG emblem %s doesn't look drawn: %d opaque samples, red %d, blue %d"
                                 % (name, n, r, b))
            counts[name] = n
        eng.tjs('kag.tagHandlers.freeimage(%[layer:"0", page:"fore"]); return 1;')
        if not 3.4 < counts["zoomed"] / counts["plain"] < 4.6:
            raise SmokeError("zoomed 200%%, the SVG covers %.2f times the area" % (counts["zoomed"] / counts["plain"]))
        if not 0.9 < counts["turned"] / counts["plain"] < 1.1:
            raise SmokeError("turned 30 degrees, the SVG covers %.2f times the area (cut off?)"
                             % (counts["turned"] / counts["plain"]))

    @step("a CLIP STUDIO PAINT layer loads through clip:// and turns (--clip required)")
    def _():
        if eng.tjs('return typeof global.affineLoadClipLayer != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates clip:// images)", flush=True)
            return
        if eng.tjs('return typeof global.CLIP != "undefined" ? 1 : 0;') != 1:
            if eng.opts.clip == "required":
                raise SmokeError("clip:// images are unavailable: no clipfile plugin")
            print("     clip://: unavailable (no clipfile plugin)", flush=True)
            return
        # emblem.clip (tools/assets/make_clip.py): the badge and the star, drawn as in emblem.svg.
        # The plugin's own clip:// BMPs don't load outside Windows (AffineLayer.tjs reads the
        # layer through CLIP.getLayerData instead)
        counts = {}
        for name, layer, opts in (("badge", "root/badge.bmp", ""), ("star", "root/star.bmp", ""),
                                  ("star by id, turned", "id/5.bmp", 'rotate:"30"')):
            eng.tjs('kag.tagHandlers.image(%%[layer:"0", page:"fore", storage:"clip://emblem.clip/%s", visible:"true",'
                    ' left:"960", top:"540", dafx:"center", dafy:"center"]);%s return 1;'
                    % (layer, ' kag.tagHandlers.layopt(%%[layer:"0", page:"fore", %s]);' % opts if opts else ""))
            time.sleep(0.5)
            n = eng.tjs('var t = new global.Layer(kag, kag.primaryLayer), n = 0; t.assignImages(kag.fore.layers[0]);'
                        ' for (var y = 2; y < t.imageHeight; y += 6) for (var x = 2; x < t.imageWidth; x += 6)'
                        ' if (t.getMaskPixel(x, y) > 200) n++; invalidate t; return n;')
            print("     %s: %d opaque samples" % (name, n), flush=True)
            counts[name] = n
        eng.tjs('kag.tagHandlers.freeimage(%[layer:"0", page:"fore"]); return 1;')
        if counts["badge"] < 1800 or counts["star"] < 150:
            raise SmokeError("emblem.clip's layers didn't draw (badge %d, star %d samples)" % (counts["badge"], counts["star"]))
        if not 0.85 < counts["star by id, turned"] / counts["star"] < 1.15:
            raise SmokeError("the star by its LayerId, turned, covers %d samples, not about %d"
                             % (counts["star by id, turned"], counts["star"]))

    @step("encryption: xp3crypt is in the engine and scnfile reads compiled scenarios (--encryption required)")
    def _():
        # xp3crypt is built into the engine (its XP3 filter in place before startup.tjs) and decrypts
        # data.xp3; scnfile reads .scn files, which kagex-release encrypts. Both take their keys from
        # the slots kagex-release writes; the sample's own packages carry none, so this checks the
        # plugins are there and work, and tool-check builds and runs an encrypted game
        r = eng.tjs('var x = "no xp3crypt", s = "no scnfile";'
                    ' if (typeof global.XP3Crypt != "undefined") { try { x = XP3Crypt.installed ? "" : "xp3crypt\'s filter isn\'t installed"; } catch (e) { x = "XP3Crypt: " + e.message; } }'
                    ' if (typeof global.SCNFile != "undefined") { try { var f = new SCNFile(SCNFile.toOctet(%[a:1, b:"scn"]));'
                    ' s = f.root.a == 1 && f.root.b == "scn" ? "" : "SCNFile doesn\'t read back what it wrote"; invalidate f; }'
                    ' catch (e) { s = "SCNFile: " + e.message; } }'
                    ' return [x, s].join("|");')
        x, sc = (r.split("|") + ["", ""])[:2]
        print("     xp3crypt: %s; scnfile: %s" % (x or "built in, filter installed", sc or "reads what it writes"), flush=True)
        if (x or sc) and eng.opts.encryption == "required":
            raise SmokeError("; ".join(m for m in (x, sc) if m))

    @step("zip patches: the ones in the save folder were mounted at start, and DLC mounts later")
    def _():
        if eng.tjs('return typeof global.KAGMountPatchZip != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates zip patches)", flush=True)
            return
        if eng.tjs('return typeof Storages.mountZip != "undefined" && typeof global.Zip != "undefined" ? 1 : 0;') != 1:
            if eng.opts.zip == "required":
                raise SmokeError("zip patches are unavailable: no minizip plugin")
            print("     zip patches: unavailable (no minizip plugin)", flush=True)
            return
        if getattr(eng, "boot_patches", False):
            # write_boot_patches: patch.zip and patch2.zip, which both hold zz_bootpatch.txt
            mounted = eng.tjs('return KAGPatchZips.count;')
            placed = eng.tjs('return Storages.getPlacedPath("zz_bootpatch.txt");')
            text = eng.tjs('return [].load("zz_bootpatch.txt")[0];')
            about = eng.tjs('return Storages.getPlacedPath("about.ks");')
            deep = eng.tjs('return Storages.getPlacedPath("zz_deep.txt");')
            print("     at start: %s zip(s); zz_bootpatch.txt %s (%r), about.ks %s, zz_deep.txt %s"
                  % (mounted, placed, text, about, deep), flush=True)
            if mounted < 2 or text != "from patch2":
                raise SmokeError("patch.zip and patch2.zip in the save folder weren't both mounted, patch2 last")
            if not about.startswith("zip://kagexpatch0/main/"):
                raise SmokeError("patch.zip's main/about.ks doesn't take the place of data/main/about.ks")
            if not deep.startswith("zip://kagexpatch0/scenario/deep/"):
                raise SmokeError("a file in a folder of a folder of patch.zip isn't found")
        # DLC: a zip the game writes with minizip's Zip class and mounts while running
        n = eng.tjs('["global.__zipcheck = 42;"].save(System.dataPath + "zz_dlcsrc.txt");'
                    ' var z = new Zip(); z.open(System.dataPath + "zz_dlc.zip", 1);'
                    ' z.add(System.dataPath + "zz_dlcsrc.txt", "scenario/zz_zipcheck.tjs"); z.close();'
                    ' invalidate z; if (!KAGMountPatchZip(System.dataPath + "zz_dlc.zip")) return -1;'
                    ' Scripts.execStorage("zz_zipcheck.tjs"); return global.__zipcheck;')
        print("     DLC zip in the save folder: zz_zipcheck.tjs ran: %s" % (n == 42), flush=True)
        if n != 42:
            raise SmokeError("a zip mounted while running didn't serve its script (%s)" % n)

    @step("the demo menu's choices are drawn in a text font")
    def _():
        # A face the engine can't draw falls back to its icon font, which measures 0 and
        # draws arrows (the browser build did that to all bold text)
        eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks" && kag.inStable', timeout=20)
        w = eng.tjs('var s = kag._selectLayer; if (s === void || s.selects.count == 0) return -1;'
                    ' return s.selects[0].font.getTextWidth("KAGEX");')
        if w == -1:
            raise SmokeError("the demo menu shows no choices")
        if w <= 0:
            raise SmokeError("the choices' font measures %s: the text is drawn with the icon font" % w)

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
            if screen != "musicmode.ks":
                # The demos unlock the first CG and Replay entry, whose tile shows a picture;
                # the browser build once drew it transparent (an empty frame)
                a = eng.tjs('var b = kag.current.names["cg0"]; if (b === void || !b.visible || !b.enabled)'
                            ' return -1; return b.getMaskPixel(b.width >> 1, b.height >> 1);')
                if a == -1:
                    raise SmokeError("the first entry is still locked")
                if a != 255:
                    raise SmokeError("the first entry's picture is transparent (alpha %s)" % a)
            eng.key("VK_ESCAPE")
            eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("a Replay tile plays its scene from the script's start, and comes back to Replay")
    def _():
        if not eng.compiled or eng.tjs('return typeof global.replayTile != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no compiled scenes, or a framework from before scene replays)", flush=True)
            return
        eng.tjs('tf.extramode = 2; kag.process("title.ks", "*extra"); return 1;')
        eng.wait("replay.ks", 'kag.conductor.curStorage == "replay.ks" && kag.inStable', timeout=20)
        # the Layers tab: a tile for each scene of layer.ks, which the demos have read
        titles = str(eng.tjs('var t = replayTabs.find("Layers"); setReplayPage(t, 0); var r = [];'
                             ' for (var i = 0; i < tf.cgbtnnum; i++) r.add(tf.replaylist[i] !== void ? tf.replaylist[i].title : "");'
                             ' return r.join("|");')).split("|")
        if "Blending Mode" not in titles:
            raise SmokeError("no Blending Mode tile on the Layers tab: %s" % titles)
        # layer.ks played unseen up to *label5: its picture on KAG layer 0, blended, which the
        # compiled save points don't hold
        eng.tjs("replayTile(%d); return 1;" % titles.index("Blending Mode"))
        eng.wait("Blending Mode", 'world_object.player !== void && world_object.player.curLabel == "*label5"'
                 ' && !kag.skipNoDisp && kag.inStable', timeout=60)
        layer = str(eng.tjs('var l = kag.fore.layers[0]; return [l.visible ? 1 : 0, l.type == ltPsDifference5 ? 1 : 0,'
                            ' world_object.player.getHistoryCount()].join(",");'))
        if layer != "1,1,1":
            raise SmokeError("the scene started with layer 0 at %s (visible, blended, history)" % layer)
        eng.clicker(True, until="replay.ks")
        eng.wait("Replay again, at the scene's end", 'kag.conductor.curStorage == "replay.ks" && kag.inStable', timeout=60)
        eng.clicker(False)
        if eng.tjs('return tf.replayTab == replayTabs.find("Layers") && !kag.isRecollection ? 1 : 0;') != 1:
            raise SmokeError("back in Replay on another tab, or still replaying")
        eng.key("VK_ESCAPE")
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("Search finds a word typed in the lines read, and plays from one")
    def _():
        if not eng.compiled or eng.tjs('return typeof global.searchInit != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no compiled scenes, or a framework from before Search)", flush=True)
            return
        eng.tjs('tf.searchText = ""; tf.extramode = 4; kag.process("title.ks", "*extra"); return 1;')
        eng.wait("searchmode.ks", 'kag.conductor.curStorage == "searchmode.ks" && kag.inStable', timeout=20)
        # typed into the field: the characters as the engine hands typed text to the focused
        # layer (onKeyPress; injected keys make none), then Return ([edit enter=])
        eng.tjs('var e = kag.fore.messages[0].names["tf.searchText"]; e.focus();'
                ' for (var i = 0; i < "layer".length; i++) e.onKeyPress("layer".charAt(i)); return 1;')
        eng.key("VK_RETURN")
        eng.wait("what it found", 'kag.conductor.curStorage == "searchmode.ks" && kag.inStable && searchFound.count > 0',
                 timeout=20)
        found = str(eng.tjs('var r = []; for (var i = 0; i < searchFound.count; i++) r.add(searchFound[i].title);'
                            ' return [tf.searchText, r.join("|")].join("~");'))
        text, titles = found.split("~")
        titles = titles.split("|")
        print("     \"%s\": %d lines" % (text, len(titles)), flush=True)
        if text != "layer" or "Vector Image" not in titles:
            raise SmokeError("searching for \"%s\" found %s" % (text, titles))
        # the line in layer.ks's *label16, played from: the script played unseen up to it
        k = titles.index("Vector Image")
        eng.tjs("tf.searchPage = %d; searchPlay(%d); return 1;" % (k // 7, k % 7))
        eng.wait("the line", 'world_object.player !== void && world_object.player.curLabel == "*label16"'
                 ' && !kag.skipNoDisp && kag.inStable', timeout=60)
        line = str(eng.tjs("return world_object.player.curText.text;"))
        if "layer" not in line.lower():
            raise SmokeError("it played from \"%s\"" % line)
        eng.clicker(True, until="searchmode.ks")
        eng.wait("Search again, at the scene's end", 'kag.conductor.curStorage == "searchmode.ks" && kag.inStable',
                 timeout=60)
        eng.clicker(False)
        if eng.tjs('return tf.searchText == "layer" && searchFound.count > 0 ? 1 : 0;') != 1:
            raise SmokeError("back in Search without what it found")
        eng.key("VK_ESCAPE")
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("after a search jump into Pip's scene he still blinks and lip-syncs")
    def _():
        if not eng.compiled or not animated_framework(eng) or \
                eng.tjs('return typeof global.searchInit != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no compiled scenes, Pip or Search here)", flush=True)
            return
        # a character put back from a saved state (a seek's end, a load, going back) has to start
        # its blinking and lip-sync again (KAGEnvCharacterEx.onRestore)
        eng.tjs('tf.searchText = "blink"; tf.extramode = 4; kag.process("title.ks", "*extra"); return 1;')
        eng.wait("what it found", 'kag.conductor.curStorage == "searchmode.ks" && kag.inStable && searchFound.count > 0',
                 timeout=20)
        k = eng.tjs('for (var i = 0; i < searchFound.count; i++) if (searchFound[i].storage == "anim.ks") return i;'
                    ' return -1;')
        if k < 0:
            raise SmokeError("searching for \"blink\" found nothing in anim.ks")
        eng.tjs('global.__smokeFace = []; global.__smokeFaceTimer = new Timer(function() {'
                ' var c = world_object.env.characters["pip"], b = c !== void ? c.soundBuffer : void;'
                ' if (c !== void && !kag.skipNoDisp) __smokeFace.add([c.eyeLevel, b !== void && b.status == "play" ? c.lipLevel : "-"]);'
                ' }, ""); __smokeFaceTimer.interval = 20; __smokeFaceTimer.enabled = true; return 1;')
        eng.tjs("tf.searchPage = %d; searchPlay(%d); return 1;" % (k // 7, k % 7))
        eng.wait("Pip's line", 'world_object.player !== void && world_object.player.curStorage == "anim.ks"'
                 ' && !kag.skipNoDisp && kag.inStable', timeout=60)
        time.sleep(3.0)
        seen = str(eng.tjs('__smokeFaceTimer.enabled = false; var eyes = %[], lips = %[];'
                           ' for (var i = 0; i < __smokeFace.count; i++) { eyes["k" + __smokeFace[i][0]] = 1; lips["k" + __smokeFace[i][1]] = 1; }'
                           ' invalidate __smokeFaceTimer; var e = [], l = []; e.assign(eyes); l.assign(lips);'
                           ' var re = [], rl = []; for (var i = 0; i < e.count; i += 2) re.add(e[i].substr(1)); for (var i = 0; i < l.count; i += 2) rl.add(l[i].substr(1));'
                           ' return re.join(" ") + "|" + rl.join(" ");')).split("|")
        eyes, lips = seen[0].split(), [x for x in seen[1].split() if x != "-"]
        print("     eye levels %s, mouth levels while the voice played %s" % (eyes, lips), flush=True)
        if "0" not in eyes and "1" not in eyes:
            raise SmokeError("Pip didn't blink (eye levels %s)" % eyes)
        if lips and not any(x in ("1", "2") for x in lips):
            raise SmokeError("Pip's mouth didn't move while he spoke (levels %s)" % lips)
        eng.tjs("kag.goToStart(); return 1;")
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


def write_boot_patches(savedir, data):
    """Zip patches for the engine to mount at start (KAGMountPatchZip in Initialize.tjs):
    patch.zip with a copy of main/about.ks in data/'s layout and a file two folders down, and
    patch2.zip, which wins over it for zz_bootpatch.txt"""
    import zipfile
    os.makedirs(savedir, exist_ok=True)
    with zipfile.ZipFile(os.path.join(savedir, "patch.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("zz_bootpatch.txt", "from patch\n")
        z.write(os.path.join(data, "main", "about.ks"), "main/about.ks")
        z.writestr("scenario/deep/zz_deep.txt", "deep\n")
    with zipfile.ZipFile(os.path.join(savedir, "patch2.zip"), "w") as z:
        z.writestr("zz_bootpatch.txt", "from patch2\n")


def start_engine(opts, data, workdir):
    if opts.target == "android":
        return AndroidEngine(opts.apk, opts.package, workdir, opts.verbose, adb=opts.adb)
    if opts.target == "ios-sim":
        return SimulatorEngine(opts.app, opts.bundle_id, workdir, opts.verbose, opts.device)
    if opts.target == "web":
        return WebEngine(opts.url, workdir, opts.verbose, opts.channel)
    return DesktopEngine(opts.engine, None if opts.packaged else data, workdir, opts.verbose)


def run_project(opts, label, data, make_steps):
    print("== %s (%s, %s)" % (label, data, opts.target), flush=True)
    workdir = tempfile.mkdtemp(prefix="kagex-smoke-")
    boot_patches = opts.target == "desktop" and label == "sample" and not opts.packaged
    if boot_patches:
        write_boot_patches(os.path.join(workdir, "savedata"), data)
    try:
        eng = start_engine(opts, data, workdir)
    except SmokeError as e:
        print("FAIL starting the engine:", e)
        print("kept", workdir)
        return 1
    eng.opts = opts
    eng.boot_patches = boot_patches
    failures = 0
    try:
        failures = run_steps(eng, make_steps(eng))
        if isinstance(eng, DesktopEngine):
            failures += quit_check(eng)
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


def quit_check(eng):
    """The game closes the way a player closes it (kag.shutdown(), as Exit does) and the engine
    exits with 0. The Linux kit build aborted on every exit (the json plugin's unlink,
    KAGUnlinkPluginsBeforeExit in Initialize.tjs), which the other steps never saw: the smoke
    test stops the engine with a signal"""
    what = "quit: the game closes and the engine exits with 0"
    t = time.time()
    try:
        eng.tjs("kag.shutdown(); return 1;", 5)
    except SmokeError:
        pass  # it may be gone before it answers
    try:
        code = eng.proc.wait(30)
    except subprocess.TimeoutExpired:
        code = "none: still running after 30 s"
    if code != 0:
        print("FAIL %s (exit code %s)" % (what, code))
        return 1
    print("ok   %-62s %5.1fs" % (what, time.time() - t), flush=True)
    return 0


def scncompile_check(opts, data):
    """-scncompile=all compiles every script in !scnlist.txt from the command line and exits:
    how kagex-release will compile a game's scripts"""
    print("== %s: -scncompile" % data, flush=True)
    if not os.path.exists(os.path.join(data, "..", "template", "system", "SceneParser.tjs")) and \
            not os.path.exists(os.path.join(data, "system", "SceneParser.tjs")):
        print("     (skipped: this framework predates compiled scenarios)", flush=True)
        return 0
    workdir = tempfile.mkdtemp(prefix="kagex-smoke-")
    env = dict(os.environ)
    env.setdefault("SDL_VIDEO_DRIVER", "offscreen")
    env.setdefault("SDL_AUDIO_DRIVER", "dummy")
    t = time.time()
    try:
        p = subprocess.run([opts.engine, os.path.abspath(data), "-datapath=" + workdir + "/", "-scncompile=all"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=180)
        out = p.stdout.decode("utf-8", "replace")
        code = p.returncode
    except subprocess.TimeoutExpired:
        out, code = "", "timeout"
    done = [l for l in out.splitlines() if "Compiled scenarios:" in l]
    errors = [l for l in out.splitlines() if ERROR_PATTERNS.search(l)]
    shutil.rmtree(workdir, ignore_errors=True)
    if code != 0 or not done or " 0 failed" not in done[-1] or errors:
        print("FAIL -scncompile=all compiles the listed scripts and exits (exit code %s)" % code)
        for l in (done + errors)[:20] or out.splitlines()[-30:]:
            print("     " + l)
        if code != 0 and done:
            # it compiled, then stopped on the way out: what the engine said last
            print("     last lines:")
            for l in out.splitlines()[-30:]:
                print("     " + l)
        return 1
    print("ok   %-62s %5.1fs" % ("-scncompile=all compiles the listed scripts and exits", time.time() - t))
    print("     " + done[-1].split("Compiled scenarios:")[-1].strip(), flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    default_exe = "krkrz.exe" if os.name == "nt" else "./krkrz"
    ap.add_argument("--engine", default=default_exe)
    ap.add_argument("--only", choices=["sample", "template"],
                    help="run one project (default: the sample in data/, then template/)")
    ap.add_argument("--keep", action="store_true", help="keep the temporary folders")
    ap.add_argument("--verbose", action="store_true", help="print the engine log at the end")
    ap.add_argument("--target", choices=["desktop", "android", "ios-sim", "web"], default="desktop")
    ap.add_argument("--packaged", action="store_true",
                    help="desktop: --engine is a package of the sample, run with the data it holds")
    ap.add_argument("--apk", help="android: the APK to install")
    ap.add_argument("--package", default="io.github.krkren.kagex", help="android: its applicationId")
    ap.add_argument("--adb", default="adb")
    ap.add_argument("--app", help="ios-sim: the .app to install")
    ap.add_argument("--bundle-id", default="io.github.krkren.kagex")
    ap.add_argument("--device", default="booted", help="ios-sim: the Simulator (UDID)")
    ap.add_argument("--url", help="web: the page that runs the game")
    ap.add_argument("--channel", help="web: an installed browser for Playwright to use (chrome), "
                    "instead of its own Chromium")
    ap.add_argument("--effekseer", choices=["required", "optional"], default="optional",
                    help="whether the build must draw Effekseer effects (the krkreffekseer plugin "
                    "and OpenGL ES): required fails when it can't; optional reports it")
    ap.add_argument("--vector", choices=["required", "optional"], default="optional",
                    help="whether the build must draw SVG images (the layerExVector plugin): "
                    "required fails when it can't; optional reports it")
    ap.add_argument("--zip", choices=["required", "optional"], default="optional",
                    help="whether the build must mount zip patches (the minizip plugin): "
                    "required fails when it can't; optional reports it")
    ap.add_argument("--clip", choices=["required", "optional"], default="optional",
                    help="whether the build must load CLIP STUDIO PAINT layers (the clipfile plugin): "
                    "required fails when it can't; optional reports it")
    ap.add_argument("--encryption", choices=["required", "optional"], default="optional",
                    help="whether the engine must have the xp3crypt plugin built in and the scnfile plugin "
                    "(encrypted data.xp3 and compiled scenarios): required fails without them; optional reports it")
    opts = ap.parse_args()
    if opts.target != "desktop" or opts.packaged:
        opts.only = "sample"  # the platform packages hold the sample only

    failures = 0
    if opts.only in (None, "sample"):
        failures += run_project(opts, "sample", "data", sample_steps)
        if opts.target == "desktop" and not opts.packaged:
            failures += scncompile_check(opts, "data")
    if opts.only in (None, "template"):
        failures += run_project(opts, "template", "template", template_steps)
    print("smoke test:", "FAILED (%d)" % failures if failures else "passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
