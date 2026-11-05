#!/usr/bin/env python3
"""Headless smoke test for the KAGEX sample.

Starts the engine with SDL's offscreen video driver and drives the sample through the
engine's REPL file channel (-replfile, see krkrz_dev src/core/doc/REPL.md): the title screen,
each demo scene (compiled from the scripts in !scnlist.txt where the data folder is writable,
doc/scn.txt), save and load, the config and extras screens, a Yes/No prompt and the About
screen, and on the desktop the menu bar (in a window), the controls list, the screenshot key
and what a screen reader is given. On the desktop it also compiles the scripts with -scncompile=all. It fails when a step doesn't reach the state it expects, when the engine raises a
script exception, or when the engine opens a native modal dialog (an error message box or a
Yes/No that should have been drawn in the game window).

The Animated Character demo's Live2D character, and the same model on a KAG layer and a World
layer (the l2d flip), need the krkrlive2d plugin, built with Live2D's Cubism SDK, which kagex's
own builds don't have: without it the test puts a stand-in for the plugin in its place
(tools/live2d-standin.tjs), which draws through OpenGL ES as the plugin does, so the
framework's part is tested all the same; --live2d required wants the real one.

It then runs template/ as a game of its own, the way a new game starts out, and checks that
it starts and that its prompts are drawn in the game window too.

usage: python3 tools/smoketest.py [--engine ./krkrz] [--only sample|template] [--keep] [--verbose]
                                 [--effekseer required|optional] [--vector required|optional]
                                 [--zip required|optional] [--clip required|optional]
                                 [--live2d required|optional]

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
        """Runs TJS statements on the main thread; 'return x;' gives the result. The REPLs print a
        string result as a TJS literal (EscapeC), where an apostrophe is \\', which JSON refuses
        (the web build's language step failed on "It's"), so a string comes back as the hex of
        its UTF-16 code units"""
        cmd = ("(function(r) { if (typeof r != 'String') return r; var a = [];"
               " for (var i = 0; i < r.length; i++) a.add('%04x'.sprintf(#(r.charAt(i))));"
               " return 'S:' + a.join(''); })((function() {\n" + body + "\n})())")
        j = self._eval(cmd, timeout)
        if not j.get("ok"):
            raise SmokeError("TJS failed: %s\n%s" % (j.get("error"), body))
        result = j.get("result", "")
        try:
            value = json.loads(result)
        except ValueError:
            return result
        if isinstance(value, str) and value.startswith("S:"):
            h = value[2:]
            return b"".join(int(h[i:i + 4], 16).to_bytes(2, "little") for i in range(0, len(h) - 3, 4)).decode("utf-16-le", "replace")
        return value

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
        # the log says why (a crash, the engine's error): the workflows keep logcat.txt
        log = self.output()
        died = [l for l in log.splitlines() if " F DEBUG" in l or "FATAL" in l or "Script exception" in l]
        raise SmokeError("no REPL socket from %s: %s%s" % (package, last, "".join("\n  " + l for l in died[:12])))

    def run_adb(self, *args):
        r = subprocess.run([self.adb] + list(args), capture_output=True, text=True)
        if r.returncode:
            raise SmokeError("adb %s failed: %s" % (" ".join(args), (r.stderr or r.stdout).strip()))
        return r.stdout

    def _eval(self, cmd, timeout):
        # one line in, one line of JSON out: a // comment on a line of its own would comment
        # out the rest
        self.sock.settimeout(timeout)
        try:
            lines = [l for l in cmd.splitlines() if not l.lstrip().startswith("//")]
            self.sock.sendall((" ".join(lines) + "\n").encode("utf-8"))
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
                                               args=["--autoplay-policy=no-user-gesture-required",
                                                     # the classic runner fix: a runner's /dev/shm is
                                                     # 64 MB, and the prefetch storm plus the engine's
                                                     # heap put the renderer's shared memory over it —
                                                     # the page dies as "Target crashed" mid-boot
                                                     "--disable-dev-shm-usage"])
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
                # wait for the module to fully instantiate before entering it: a ccall
                # that races the running wasm (packed sites boot fast: one archive, warm
                # CDN) re-enters a half-built module and crashes the renderer outright.
                # The engine's own boot banner is printed from inside main(), so once it
                # is in the console the exports are usable; touching no wasm itself.
                if not any("TVP Log system" in l for l in self.lines):
                    # pump the Playwright event loop (console lines are only dispatched
                    # during a page call; a sleep-only loop would buffer them all until
                    # teardown and this wait would time out with the page very much alive)
                    try:
                        self.page.evaluate("1")  # plain JS: no wasm exports, can't crash
                    except Exception:
                        pass  # mid-navigation (COI reload); events pump next call
                    time.sleep(1)
                    continue
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


def a11y_framework(eng):
    """Whether screen readers are given the game's text and UI (Accessibility.tjs, since
    0.12.0) and the engine lets the test see what they get (Agent.a11yTree: the desktop REPLs)"""
    return eng.tjs('return typeof global.KAGA11y == "Object" && KAGA11y !== void && KAGA11y.available'
                   ' && typeof global.Agent != "undefined" && typeof Agent.a11yTree != "undefined" ? 1 : 0;') == 1


def a11y_nodes(eng):
    """The nodes a screen reader sees in the game window (Agent.a11yTree)"""
    t = json.loads(str(eng.tjs("return Agent.a11yTree();")))
    return ((t.get("game") or {}).get("tree") or {}).get("nodes") or []


def a11y_find(eng, role, prefix, timeout=5.0):
    """The first node of the role whose name starts with prefix, once there is one"""
    end = time.time() + timeout
    while True:
        nodes = a11y_nodes(eng)
        for n in nodes:
            # the tree spells the roles setGameA11y takes (list_item) its own way (list item)
            if (n.get("role") or "").replace(" ", "_") == role and (n.get("name") or "").startswith(prefix):
                return n
        if time.time() > end:
            raise SmokeError("screen readers get no %s \"%s...\": %s"
                             % (role, prefix, [(n.get("role"), n.get("name")) for n in nodes if n.get("name")]))
        time.sleep(0.2)


def a11y_click(eng, node):
    """Presses a node the way a screen reader does (Agent.a11yAction)"""
    if eng.tjs('return Agent.a11yAction("%s", "click") ? 1 : 0;' % node["id"]) != 1:
        raise SmokeError("the screen reader's click on %s did nothing" % node)


def a11y_said(eng, since):
    """What a screen reader was given to say since a point of the speech log (Agent.a11yLog),
    and the next point"""
    r = json.loads(str(eng.tjs('var l = Agent.a11yLog(%d); return Scripts.toJSONString(%%[lines:l.lines, next:l.next]);'
                               % since)))
    return r.get("lines") or [], r.get("next") or since


def elements_screens(eng):
    """Whether the steps for the menu bar and the controls list run here: on the desktop engines
    (where they've been checked), with a framework that has them (since 0.12.0) and an engine
    with ElementsPanel. Says why not"""
    if not isinstance(eng, DesktopEngine):
        print("     (skipped: checked on the desktop engines)", flush=True)
        return False
    if eng.tjs('return typeof global.KAGElementsScreenAvailable != "undefined" ? 1 : 0;') != 1:
        print("     (skipped: this build's framework predates the Elements screens)", flush=True)
        return False
    if eng.tjs("return KAGElementsScreenAvailable() ? 1 : 0;") != 1:
        print("     (skipped: this engine has no ElementsPanel)", flush=True)
        return False
    return True


def controls_list(eng):
    """KAGControlsList(kag): [(section title, [(keys, action)...])...]"""
    sections = json.loads(str(eng.tjs("return Scripts.toJSONString(KAGControlsList(kag));")))
    return [(sec.get("title"), [(r.get("keys") or "", r.get("action") or "") for r in sec.get("rows") or []])
            for sec in sections]


def controls_action(sections, title, key):
    """The action of the row in a section whose keys include key ("F2" in "F2 / S")"""
    for t, rows in sections:
        if t != title:
            continue
        for keys, action in rows:
            if key in [k.strip() for k in keys.split("/")]:
                return action


def interface_steps(eng, step):
    """The menu bar (in a window), the controls list, the screenshot key and the screen
    reader's view of a Yes/No prompt, which every game gets from template/system"""

    @step("screen readers: a Yes/No prompt's buttons are read, and one pressed through it answers")
    def _():
        if not a11y_framework(eng):
            print("     (skipped: no screen reader interface here, or a framework without it)", flush=True)
            return
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        eng.tjs('global.__smokeAnswer = ""; askYesNo("Smoke test?", "Confirm",'
                ' function() { global.__smokeAnswer = "yes"; },'
                ' function() { global.__smokeAnswer = "no"; }); return 1;')
        eng.wait("the prompt", 'typeof kag.currentDialog == "Object" && kag.currentDialog !== void', timeout=10)
        a11y_find(eng, "button", "No")
        a11y_click(eng, a11y_find(eng, "button", "Yes"))
        eng.wait("the answer", '__smokeAnswer == "yes"', timeout=10)
        eng.wait("the prompt to close", "kag.currentDialog === void", timeout=10)

    @step("in a window the menu bar sits above the game: F10 and a click on a title drop its"
          " menus down, Help > Controls works, and full screen has no bar")
    def _():
        if not elements_screens(eng):
            return
        if eng.tjs('return typeof global.KAGMenuBar != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the menu bar)", flush=True)
            return
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        if eng.tjs("return KAGMenuBarAvailable(kag) ? 1 : 0;") != 1:
            raise SmokeError("the menu bar can't be shown (KAGMenuBarAvailable: Window.setViewport, the stand-in menu)")
        # captions lose their accelerators: "(&F)", a bare "&F" ("$1ile" up to 0.14.0) and "&&"
        labels = str(eng.tjs(
            'var r = []; with (KAGMenuItemText(%[caption:"&File\\tCtrl+F"])) r.add(.label + "|" + .shortcut);'
            ' r.add(KAGMenuItemText(%[caption:"Save(&S)"]).label); r.add(KAGMenuItemText(%[caption:"Q&&A"]).label);'
            ' return r.join("/");'))
        if labels != "File|Ctrl+F/Save/Q&A":
            raise SmokeError("menu captions come out as %s, not File|Ctrl+F/Save/Q&A" % labels)
        full = eng.tjs("return kag.fullScreened ? 1 : 0;") == 1
        try:
            if full:
                eng.tjs("kag.onWindowedMenuItemClick(); return 1;")
            eng.wait("the menu bar", "kag.menuBarShown && kag.menuBarView !== void && kag.menuBarView.shown",
                     timeout=10)
            # the window is the strip taller than the game, which is drawn under it (once the
            # window has its size: leaving full screen takes a moment on some systems)
            end = time.time() + 10
            while True:
                size = [int(v) for v in str(eng.tjs(
                    'var z = kag.zoomNumer / kag.zoomDenom; return [kag.innerWidth, kag.innerHeight,'
                    ' int(kag.primaryLayer.width * z + 0.5), int(kag.primaryLayer.height * z + 0.5),'
                    ' kag.menuStripHeight].join(",");')).split(",")]
                sized = size[4] > 0 and abs(size[0] - size[2]) <= 1 and abs(size[1] - size[3] - size[4]) <= 1
                if sized or time.time() > end:
                    break
                time.sleep(0.25)
            print("     window %dx%d, the game %dx%d under a %d px strip" % tuple(size), flush=True)
            if not sized:
                raise SmokeError("the window isn't the game plus the strip: %s" % size)
            # and it stays that size: setZoom sized the window to the game alone, then added the
            # strip, and each resize came back through onResize, which called setZoom again, for
            # ever (issue 29: about 80 calls a second here)
            time.sleep(1)
            eng.tjs("global.__smokeZooms = 0; kag.__smokeSetZoom = kag.setZoom; kag.setZoom = function(n, d, r = true)"
                    " { global.__smokeZooms++; __smokeSetZoom(n, d, r); } incontextof kag; return 1;")
            time.sleep(1.5)
            zooms = eng.tjs("var n = __smokeZooms; kag.setZoom = kag.__smokeSetZoom; delete kag.__smokeSetZoom;"
                            " return n;")
            if zooms >= 5:
                raise SmokeError("the window keeps being sized again with nothing happening: setZoom ran %s times"
                                 " in 1.5 s (onResize and setZoom in a loop)" % zooms)
            # F10: the first menu, from the keyboard; Esc closes it
            eng.key("VK_F10")
            eng.wait("the first menu", 'kag.currentDialog instanceof "KAGMenuDropDown" && kag.menuBarView.openIndex >= 0'
                     ' && kag.menuDropDown !== void', timeout=10)
            eng.key("VK_ESCAPE")
            eng.wait("the menu to close", "kag.currentDialog === void && kag.menuDropDown === void"
                     " && kag.menuBarView.openIndex < 0", timeout=10)
            # a click on Help's title, in the strip (the title of the menu Help > Controls is in)
            at = str(eng.tjs(
                'var b = kag.menuBarView; for (var i = 0; i < b.titles.count; i++) with (b.titles[i])'
                ' if (.menu && .item.children.find(kag.controlsMenuItem) >= 0)'
                ' return i + "," + (.x + .w \\ 2) + "," + (kag.menuStripHeight \\ 2); return "";'))
            if at == "":
                raise SmokeError("the menu bar has no title for Help (with Controls)")
            index, x, y = at.split(",")
            help_open = 'kag.currentDialog instanceof "KAGMenuDropDown" && kag.menuBarView.openIndex == %s' % index
            eng.tjs("Agent.click(%s, %s); return 1;" % (x, y))
            try:
                eng.wait("Help's menu", help_open, timeout=4)
            except SmokeError:
                # Agent.click's coordinates are the window's in points, which a scaled display
                # (a Mac's) may not match: open it as a click on its title does
                print("     (the click at %s,%s didn't reach Help's title here: opened through"
                      " onMenuBarTitle, as a click does)" % (x, y), flush=True)
                eng.tjs("kag.onMenuBarTitle(%s); return 1;" % index)
                eng.wait("Help's menu", help_open, timeout=10)
            if a11y_framework(eng):
                # screen readers get the bar's titles and the menu's items
                titles = [n.get("name") for d in json.loads(str(eng.tjs("return Agent.a11yTree();"))).get("dialogs") or []
                          for n in ((d.get("tree") or {}).get("nodes") or [])
                          if (n.get("role") or "").replace(" ", "_") == "menu_item"]
                if len(titles) < 2:
                    raise SmokeError("screen readers get the menu bar's titles as %s" % titles)
                a11y_click(eng, a11y_find(eng, "menu_item", eng.tjs(
                    "return KAGMenuItemText(kag.controlsMenuItem).label;")))
            else:
                print("     (Controls chosen with the keys: no screen reader interface here)", flush=True)
                eng.tjs("var d = kag.menuDropDown, b = d.boxes[0]; for (var i = 0; i < b.entries.count; i++)"
                        " if (b.entries[i].item === kag.controlsMenuItem) d.activate(0, i, true); return 1;")
            eng.wait("the controls list", 'kag.currentDialog instanceof "KAGControlsPanel"', timeout=10)
            eng.key("VK_ESCAPE")
            eng.wait("the controls list to close", "kag.currentDialog === void", timeout=10)
            # full screen: no bar, and the game fills the window again
            eng.tjs("kag.onFullScreenMenuItemClick(); return 1;")
            eng.wait("the bar to go", "!kag.menuBarShown && !kag.menuBarView.shown && kag.menuStripHeight == 0",
                     timeout=10)
        finally:
            eng.tjs("kag.closeMenuDropDown(); kag.changeFullScreenOrWindow(%s); return 1;"
                    % ("true" if full else "false"))

    @step("the controls list reads the window's key and controller bindings, and opens and closes")
    def _():
        if not elements_screens(eng):
            return
        sections = controls_list(eng)
        titles = [t for t, rows in sections]
        print("     sections: %s" % ", ".join("%s (%d)" % (t, len(rows)) for t, rows in sections), flush=True)
        if "Keyboard" not in titles or "Mouse" not in titles:
            raise SmokeError("the controls list has no keyboard or mouse section: %s" % sections)
        # F10 opens the menu bar's first menu, so it's listed only while there's a bar (windowed)
        bar = eng.tjs('return typeof kag.menuBarShown != "undefined" && kag.menuBarShown ? 1 : 0;') == 1
        for key, action in (("F10", "Menu" if bar else None), ("F12", "Save a screenshot")):
            if controls_action(sections, "Keyboard", key) != action:
                raise SmokeError("the controls list doesn't say %s is %s: %s" % (key, action, sections[0]))
        if eng.tjs('return typeof global.VK_PAD1 == "Integer" ? 1 : 0;') == 1 and "Controller" not in titles:
            raise SmokeError("the controls list has no controller section: %s" % titles)
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        eng.tjs("kag.showControls(); return 1;")
        eng.wait("the controls list", 'kag.currentDialog instanceof "KAGControlsPanel"', timeout=10)
        eng.key("VK_ESCAPE")
        eng.wait("the controls list to close", "kag.currentDialog === void", timeout=10)

    @step("F12 saves the screen as a PNG and says so")
    def _():
        if not isinstance(eng, DesktopEngine) or eng.tjs('return typeof kag.saveScreenshot != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: checked on the desktop engines, with a framework that has it)", flush=True)
            return
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        # the notice shows for 2 s, which a slow runner's next commands can take (macOS), so the
        # hook notes whether it's up: the hook runs right after the notice is shown
        eng.tjs('global.__smokeShot = ""; global.__smokeShotNotice = 0; global.__smokeShotHook = function(name) {'
                ' var n = kag.screenshotNoticeLayer;'
                ' global.__smokeShotNotice = n !== void && (isvalid n) && n.visible ? 1 : 0;'
                ' global.__smokeShot = name === void ? "(failed)" : name; };'
                ' kag.screenshotHook.add(__smokeShotHook); return 1;')
        try:
            eng.key("VK_F12")
            name = eng.wait("the screenshot", "__smokeShot", timeout=10)
        finally:
            eng.tjs("kag.screenshotHook.remove(__smokeShotHook); return 1;")
        if name == "(failed)":
            raise SmokeError("the screenshot wasn't saved (see the log)")
        size = eng.tjs('var l = new Layer(kag, kag.primaryLayer); l.loadImages(__smokeShot);'
                       ' var r = l.imageWidth + "x" + l.imageHeight; invalidate l; return r;')
        want = eng.tjs('return kag.primaryLayer.width + "x" + kag.primaryLayer.height;')
        background = eng.tjs('return typeof kag.startSaveLayerImage == "Object" ? 1 : 0;') == 1
        print("     %s, %s (%s)" % (name.split("/")[-1], size,
                                    "written in the background" if background else "written at once"), flush=True)
        if size != want:
            raise SmokeError("the screenshot is %s, the screen %s" % (size, want))
        if eng.tjs("return __smokeShotNotice;") != 1:
            raise SmokeError("no notice said the screenshot was saved")


def template_steps(eng):
    """template/ run as a game of its own: it has to start without the sample's hooks."""
    steps, step = collector()

    @step("start-up reaches first.ks")
    def _():
        eng.wait("the REPL", "1", timeout=60)
        eng.wait("first.ks", 'kag.conductor.curStorage == "first.ks" && kag.inStable', timeout=60)

    @step("one language (KAGLanguageList): F9 leaves it as it is")
    def _():
        if eng.tjs('return typeof global.KAGLanguage == "Object" && KAGLanguage !== void ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates languages)", flush=True)
            return
        eng.key("VK_F9")
        time.sleep(0.5)
        r = str(eng.tjs('return KAGLanguage.list.join(",") + "|" + KAGLanguage.current + "|" + (KAGLanguage.chosen ? 1 : 0);'))
        if r != "en|en|0":
            raise SmokeError("languages, the one shown, chosen: %s" % r)

    prompt_steps(eng, step)
    interface_steps(eng, step)
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


LIVE2D_STANDIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live2d-standin.tjs")


def live2d_steps(eng):
    """The Animated Character demo's Live2D character, Hiyori (KAGEnvCharacterLive2D.tjs). With the
    krkrlive2d plugin and her model (tools/assets/make_hiyori.py) it checks her picture as the
    plugin draws it; without them (every build kagex ships: the plugin needs Live2D's Cubism SDK)
    the demo has said so as the demos played, and the stand-in plugin (live2d-standin.tjs) takes
    the plugin's place, doing what the plugin's driver does with a model's parameters, so the
    framework's part is checked all the same: her picture where the World puts her, upright, the
    model's copy in step with her player, the pose's motions, a motion played once, a face fading
    in and holding over her motions', blinking, lip-sync to a voice with a lip track, a save and
    a load, and letting the model go when she leaves"""
    if eng.tjs('return typeof global.KAGEnvCharacterLive2D != "undefined" && typeof global.KAGLive2DOf != "undefined"'
               ' && world_object.env.characterInits["hiyori"] !== void ? 1 : 0;') != 1:
        if eng.opts.live2d == "required":
            raise SmokeError("--live2d required, but this build's framework or sample predates Live2D characters")
        print("     (skipped: this build's framework or sample predates Live2D characters)", flush=True)
        return
    why = str(eng.tjs('var s = KAGLive2DOf(kag); return !s.available ? s.reason : s.findModel("hiyori") == ""'
                      ' ? "no fgimage/hiyori.l2d (tools/assets/make_hiyori.py model)" : "";'))
    standin = why != ""
    if standin:
        print("     Live2D: unavailable (%s): the stand-in plugin plays her" % why, flush=True)
        if eng.opts.live2d == "required":
            raise SmokeError("Live2D characters can't be drawn here: " + why)
        with open(LIVE2D_STANDIN, encoding="utf-8") as f:
            src = f.read()
        # the window's Live2D device, made without the plugin, goes; the stand-in's classes
        # take the plugin's place; and a file stands in for her model where it isn't there
        r = eng.tjs('var s = kag.live2dSystem; kag.removePlugin(s); invalidate s; kag.live2dSystem = void;'
                    ' Scripts.exec(%s);'
                    ' if (KAGLive2DOf(kag).findModel("hiyori") == "") {'
                    '  if (typeof global.Zip == "undefined" || typeof global.KAGMountPatchZip == "undefined") return "no minizip";'
                    '  ["stand-in"].save(System.dataPath + "zz_hiyori.txt");'
                    '  var z = new Zip(); z.open(System.dataPath + "zz_live2d.zip", 1);'
                    '  z.add(System.dataPath + "zz_hiyori.txt", "fgimage/hiyori.l2d"); z.close(); invalidate z;'
                    '  if (!KAGMountPatchZip(System.dataPath + "zz_live2d.zip")) return "the zip didn\'t mount"; }'
                    ' var s2 = KAGLive2DOf(kag); return s2.available ? (KAGLive2DCanDraw("hiyori") ? "" : "no model") : s2.reason;'
                    % tjs_string(src))
        if r == "no minizip":
            print("     (skipped: no minizip plugin to stand in a model file with)", flush=True)
            return
        if r:
            if "OpenGL" in str(r) or "GLCompositor" in str(r):
                print("     (skipped: the stand-in draws through OpenGL ES, which isn't here: %s)" % r, flush=True)
                return
            raise SmokeError("the stand-in plugin can't draw Hiyori: %s" % r)
    else:
        print("     Live2D: the krkrlive2d plugin and Hiyori's model", flush=True)
        # an error the plugin reports reaches the script: the engine's exception unwinds through
        # the plugin's frames, which aborts the game where the two have unwinders of their own
        # (UPSTREAM.md 2)
        r = str(eng.tjs('try { new Live2DDevice(1); return "no error"; } catch (e) { return "caught: " + e.message; }'))
        print("     an error through the plugin: %s" % r[:60], flush=True)
        if not r.startswith("caught"):
            raise SmokeError("Live2DDevice given a number didn't report an error: %s" % r)
        # how long its first use took, as the Animated Character demo played (the device, its
        # shaders, Hiyori's model and the first picture)
        print("     first use (ms): %s" % eng.tjs('var t = KAGLive2DOf(kag).timings, a = [], k = []; k.assign(t);'
                                                 ' for (var i = 0; i < k.count; i += 2) a.add(k[i] + " " + k[i + 1]);'
                                                 ' return a.join(", ");'), flush=True)
    hiyori = 'var c = world_object.env.characters["hiyori"]; '
    eng.tjs('global.__smokeL2DBlink = eyeFlipFreq; eyeFlipFreq = 1.0; kag.process("anim.ks", "*start"); return 1;')
    eng.wait("Pip", 'world_object.env.characters["pip"] !== void && kag.inStable', timeout=20)
    eng.tjs('kag.process("anim.ks", "*live2d"); return 1;')
    eng.wait("Hiyori", 'world_object.env.characters["hiyori"] !== void && world_object.env.characters["hiyori"].player !== void'
             ' && kag.inStable', timeout=30)
    time.sleep(1.5)
    # drawn, and on the screen: the World puts her canvas's centre at center (the screen's own
    # centre), 300 below it
    drawn = str(eng.tjs(hiyori + 'var t = c.targetLayer, l = c.renderLayer, n = 0;'
                        ' for (var y = 0; y < l.imageHeight; y += 16) for (var x = 0; x < l.imageWidth; x += 16)'
                        ' if (l.getMaskPixel(x, y) > 0) n++;'
                        ' var left = (int)(t._affineleft - t.afx), top = (int)(t._affinetop - t.afy);'
                        ' return [n, t.visible ? 1 : 0, left, top, l.imageWidth, l.imageHeight, c.lastDraw !== void ? 1 : 0].join(",");'))
    n, visible, left, top, width, height, ticking = [int(v) for v in drawn.split(",")]
    print("     Hiyori: %d of her picture's samples drawn, %dx%d at (%d, %d)" % (n, width, height, left, top), flush=True)
    if n < 100 or not visible:
        raise SmokeError("Hiyori isn't drawn: %s" % drawn)
    if abs(left + width / 2 - 960) > 2 or abs(top + height / 2 - 840) > 2:
        raise SmokeError("Hiyori's picture is centred at (%d, %d), not at center's (960, 840)"
                         % (left + width / 2, top + height / 2))
    # it goes on drawing: the model moves by itself
    eng.tjs(hiyori + 'global.__smokeL2DDraw = c.lastDraw; return 1;')
    time.sleep(1.0)
    if eng.tjs(hiyori + 'return c.lastDraw != global.__smokeL2DDraw ? 1 : 0;') != 1:
        raise SmokeError("Hiyori was drawn once, and not again as her model moved")
    # upright: a player of her model, with no motion, drawn with its eyes open and shut, differs
    # where her eyes are, in the top part of the picture (her head's)
    r = str(eng.tjs('var s = KAGLive2DOf(kag), file = s.findModel("hiyori"), p = s.newPlayer(file);'
                    ' var w = 300, h = 420, a = new Layer(kag, kag.fore.base), b = new Layer(kag, kag.fore.base);'
                    ' a.setImageSize(w, h); b.setImageSize(w, h);'
                    ' p.progress(33); s.render(a, p);'
                    ' p.setParameterValue("ParamEyeLOpen", 0); p.setParameterValue("ParamEyeROpen", 0);'
                    ' p.progress(33); s.render(b, p); s.releasePlayer(p);'
                    ' var n = 0, sy = 0;'
                    ' for (var y = 0; y < h; y += 2) for (var x = 0; x < w; x += 2) {'
                    '  var pa = a.getMainPixel(x, y), pb = b.getMainPixel(x, y), d = 0;'
                    '  for (var k = 0; k < 32; k += 8) d += Math.abs(((pa >> k) & 255) - ((pb >> k) & 255));'
                    '  if (d > 60) { n++; sy += y; } }'
                    ' invalidate a; invalidate b; return [n, n > 0 ? sy / n / h : -1].join(",");')).split(",")
    changed, eyes_at = int(r[0]), float(r[1])
    print("     upright: shutting her eyes changes %d samples, %.0f%% of the way down" % (changed, eyes_at * 100), flush=True)
    if changed < 10 or not 0.0 < eyes_at < 0.4:
        raise SmokeError("Hiyori's eyes aren't near the top of her picture (upside down?): %s" % r)
    # her copy without OpenGL (the shadow) plays the motions in step with her player
    r = str(eng.tjs(hiyori + 'var d = 0; for (var i = 0; i < c.faceParams.count; i++) {'
                    ' var p = c.faceParams[i], x = Math.abs(c.shadow.getParameterValue(p) - c.player.getParameterValue(p));'
                    ' d = x if x > d; } return [c.faceParams.count, d].join(",");')).split(",")
    print("     the World's parameters: %s; her copy is off by at most %s" % (r[0], r[1]), flush=True)
    if int(r[0]) < 4 or float(r[1]) > 0.0001:
        raise SmokeError("Hiyori's copy doesn't play her motions in step with her: %s" % r)
    # blinking (eyeFlipFreq 1: a blink every frame or so), the eyes open the rest of the time, and
    # a face that fades in
    eng.tjs('global.__smokeL2D = %[ eyes : 9.0, eyesOpen : 0.0, open : 0.0, forms : %[], vowels : %[], voice : %[],'
            '  apart : 0.0, drawnOff : 0.0, samples : 0,'
            '  from : typeof global.Live2DStandIn != "undefined" ? Live2DStandIn.eyes.count : 0 ];'
            ' global.__smokeL2DTimer = new Timer(function() {'
            '  var c = world_object.env.characters["hiyori"]; if (c === void || c.player === void) return; var s = global.__smokeL2D;'
            '  var e = c.faceTargets.ParamEyeLOpen; if (e !== void) { s.eyes = e if e < s.eyes; s.eyesOpen = e if e > s.eyesOpen; }'
            '  s.samples++;'
            '  for (var i = 0; i < c.faceParams.count; i++) { var p = c.faceParams[i];'
            '   var d = Math.abs(c.shadow.getParameterValue(p) - c.player.getParameterValue(p)); s.apart = d if d > s.apart;'
            '   if (typeof global.Live2DStandIn != "undefined" && c.faceTargets[p] !== void) {'
            '    d = Math.abs(Live2DStandIn.last[p] - c.faceTargets[p]); s.drawnOff = d if d > s.drawnOff; } }'
            '  var b = c.soundBuffer; if (b !== void && b.status == "play") {'
            '   s.open = c.mouthOpen if c.mouthOpen > s.open; s.forms["%.1f".sprintf(c.faceTargets.ParamMouthForm)] = 1;'
            '   s.voice[b.position] = 1; if (c.lipVowel !== void) s.vowels[c.lipVowel] = 1; }'
            ' }, ""); __smokeL2DTimer.interval = 20; __smokeL2DTimer.enabled = true;'
            ' var c = world_object.env.characters["hiyori"]; c.setFace("smile", %[]);'
            ' global.__smokeL2DMid = c.currentFaceValues(c.faceStart + live2dFaceFade / 2).ParamEyeLSmile; return 1;')
    time.sleep(1.5)
    r = str(eng.tjs(hiyori + 'var s = global.__smokeL2D;'
                    ' return [s.eyes, s.eyesOpen, global.__smokeL2DMid, c.faceTargets.ParamEyeLSmile, c.face].join(",");')).split(",")
    print("     blinking: the eyes from %s down to %s; the smile face: ParamEyeLSmile %s halfway through its fade, then %s"
          % (r[1], r[0], r[2], r[3]), flush=True)
    if float(r[0]) > 0.2:
        raise SmokeError("Hiyori's eyes didn't close to blink (down to %s)" % r[0])
    if float(r[1]) < 0.95:
        raise SmokeError("the World didn't open Hiyori's eyes between blinks (at most %s)" % r[1])
    if not 0.3 < float(r[2]) < 0.7 or abs(float(r[3]) - 1.0) > 0.01 or r[4] != "smile":
        raise SmokeError("Hiyori's smile face didn't fade in: %s" % r)
    # lip-sync to a voice with a lip track (Pip's synthesized line, which has pip000009.lip): her
    # mouth opens, shaped by its vowels, and closes to the face's when it ends
    eng.tjs(hiyori + 'c.playVoice("pip000009"); return 1;')
    end = time.time() + 14
    while time.time() < end:
        time.sleep(0.5)
        if eng.tjs(hiyori + 'var b = c.soundBuffer; return b !== void && b.status != "play" ? 1 : 0;') == 1:
            break
    time.sleep(0.5)
    r = str(eng.tjs(hiyori + 'var s = global.__smokeL2D, f = [], v = [], p = []; f.assign(s.forms); v.assign(s.vowels); p.assign(s.voice);'
                    ' var fs = [], vs = []; for (var i = 0; i < f.count; i += 2) fs.add(f[i]);'
                    ' for (var i = 0; i < v.count; i += 2) vs.add(v[i]);'
                    ' return [s.open, fs.join(" "), vs.join(" "), p.count \\ 2, c.faceTargets.ParamMouthOpenY,'
                    ' c.faceValuesOf(c.face).ParamMouthOpenY].join(",");')).split(",")
    opened, forms, vowels, positions = float(r[0]), r[1].split(), r[2].split(), int(r[3])
    after, face_mouth = float(r[4]), float(r[5]) if r[5] not in ("", "void") else 0.0
    print("     lip-sync: the mouth open up to %.2f, vowels %s, mouth forms %s; after it %.2f (the face's %.2f)"
          % (opened, " ".join(vowels) or "none", " ".join(forms), after, face_mouth), flush=True)
    if positions <= 1:
        print("     (the voice doesn't play here, so the mouth isn't checked)", flush=True)
    elif opened < 0.3 or len(vowels) < 2 or len(set(forms)) < 2:
        raise SmokeError("Hiyori's mouth didn't follow pip000009.lip (open %.2f, vowels %s, forms %s)" % (opened, vowels, forms))
    if abs(after - face_mouth) > 0.01:
        raise SmokeError("Hiyori's mouth is at %.2f after the voice, not the face's %.2f" % (after, face_mouth))
    r = str(eng.tjs('var s = global.__smokeL2D; return [s.samples, s.apart, s.drawnOff].join(",");')).split(",")
    print("     over %s samples: her copy off by at most %s%s" % (r[0], r[1], ", the drawn values off the World's by at most %s" % r[2] if standin else ""), flush=True)
    if int(r[0]) < 50 or float(r[1]) > 0.0001:
        raise SmokeError("Hiyori's copy didn't play her motions in step with her: %s" % r)
    if standin and float(r[2]) > 0.001:
        raise SmokeError("the stand-in didn't draw the values the World set (off by %s): the motions' showed through" % r[2])
    if standin:
        # what the stand-in drew while the World blinked and spoke: the World's eyes and mouth,
        # not its motions' (eyes half shut, the mouth open)
        r = str(eng.tjs('var s = Live2DStandIn, n = s.eyes.count, e = 9, eo = 0;'
                        ' for (var i = global.__smokeL2D.from; i < n; i++) { e = s.eyes[i] if s.eyes[i] < e; eo = s.eyes[i] if s.eyes[i] > eo; }'
                        ' return [e, eo, s.mouths[n - 1]].join(",");')).split(",")
        print("     the stand-in drew the eyes from %s down to %s, and the mouth last at %s" % (r[1], r[0], r[2]), flush=True)
        if float(r[0]) > 0.2 or float(r[1]) < 0.95 or abs(float(r[2]) - face_mouth) > 0.01:
            raise SmokeError("the stand-in didn't draw the World's eyes and mouth over its motions': %s" % r)
    # a motion played once (tap: TapBody), then the pose's again
    eng.tjs(hiyori + 'c.playOnce("tap", %[]); return 1;')
    eng.wait("the tap motion", 'world_object.env.characters["hiyori"].oneShotPlaying', timeout=5)
    eng.wait("the pose's motions again", '!world_object.env.characters["hiyori"].oneShotPlaying', timeout=20)
    # a motion of a group's number (idle5: "Idle:4", the fifth the player lists in that group),
    # and one named by its file (m03, which the driver keeps as Hiyori_m03), which is in the Idle
    # group here
    fifth = str(eng.tjs(hiyori + 'return c.player.getMotionName("Idle", 4);'))
    for name, want in (("idle5", fifth), ("m03", "Hiyori_m03")):
        eng.tjs(hiyori + 'c.playOnce("' + name + '", %[]); return 1;')
        eng.wait(name + " to play", 'world_object.env.characters["hiyori"].oneShotPlaying', timeout=5)
        got = str(eng.tjs(hiyori + 'return c.poseMotion;'))
        if want in ("", "void") or got != want:
            raise SmokeError("%s (%s) didn't play a motion of %s: %s" % (name, want, want, got))
        print("     %s: %s" % (name, got), flush=True)
        eng.wait("the pose's motions again", '!world_object.env.characters["hiyori"].oneShotPlaying', timeout=20)
    # a pose of one motion of its own (still: ":Hiyori_m03") plays that one, looping
    eng.tjs(hiyori + 'c.setPose("still", %[]); return 1;')
    eng.wait("the still pose", 'world_object.env.characters["hiyori"].pose == "still"'
             ' && world_object.env.characters["hiyori"].poseMotion == "Hiyori_m03"', timeout=10)
    eng.tjs(hiyori + 'c.setPose("standard", %[]); return 1;')
    eng.wait("the Idle pose again", 'world_object.env.characters["hiyori"].pose == "standard"', timeout=10)
    eng.tjs('__smokeL2DTimer.enabled = false; invalidate __smokeL2DTimer; eyeFlipFreq = global.__smokeL2DBlink; return 1;')
    if standin:
        r = str(eng.tjs('var s = Live2DStandIn; return [s.started.join(";"), s.players, s.drawn].join(",");')).split(",")
        started = r[0].split(";")
        print("     the stand-in: %s pictures drawn; motions started: %s" % (r[2], " ".join(started[:8])), flush=True)
        if not [m for m in started if m.startswith("main/Hiyori_m") and m != "main/Hiyori_m04"]:
            raise SmokeError("the pose's motions (the Idle group) didn't play: %s" % started)
        if "main/Hiyori_m04" not in started:
            raise SmokeError("tap didn't play the TapBody motion: %s" % started)
        if "main/Hiyori_m03" not in started:
            raise SmokeError("m03 (':Hiyori_m03') didn't play that motion once: %s" % started)
        if "main/Hiyori_m03 loop" not in started:
            raise SmokeError('the still pose (":Hiyori_m03") did not play it as one motion looping: %s' % started)
    # with effects off (the sample's Config) the update handler stops and nothing moves her on:
    # a face and the eyes' commands still show, drawn as their tag runs, the face at once
    eng.tjs('global.__smokeNoeffect = [kag.noeffect, kag.noeffectEnabled]; kag.noeffect = true; kag.noeffectEnabled = true; return 1;')
    time.sleep(0.3)
    eng.tjs(hiyori + 'global.__smokeL2DEyes = c.eyestate; global.__smokeL2DDraw = c.lastDraw;'
            ' world_object.env.unknown("hiyori", %["surprised" => "true", "eyeclose" => "true"]); return 1;')
    eng.wait("Hiyori drawn with effects off", 'world_object.env.characters["hiyori"].lastDraw != global.__smokeL2DDraw', timeout=5)
    # (the brows: only the face sets them, within their range; the eyes and mouth have more to them)
    r = str(eng.tjs(hiyori + 'var f = c.faceValuesOf("surprised");'
                    ' var off = Math.max(Math.abs(c.faceTargets.ParamBrowLY - f.ParamBrowLY), Math.abs(c.faceTargets.ParamBrowRY - f.ParamBrowRY));'
                    ' return [c.face, off, c.faceTargets.ParamEyeLOpen].join(",");')).split(",")
    eng.tjs(hiyori + 'kag.noeffect = global.__smokeNoeffect[0]; kag.noeffectEnabled = global.__smokeNoeffect[1];'
            ' c.setEyeState(global.__smokeL2DEyes, %[]); world_object.env.unknown("hiyori", %["smile" => "true"]);'
            ' c.startUpdateHandler(); return 1;')
    print("     with effects off: face %s, off the face's values by at most %s, the eyes' target %s"
          % (r[0], r[1], r[2]), flush=True)
    if r[0] != "surprised" or float(r[1]) > 0.01 or float(r[2]) > 0.05:
        raise SmokeError("with effects off, Hiyori's face and eyes didn't change as their tag ran: %s" % r)
    # a save and a load with her on the screen: she's drawn again, her model made again (smiling,
    # as she was, or with the face the script gives her there: a compiled scene keeps the World as
    # it was at its save points)
    eng.tjs("kag.saveBookMark(3); return 1;")
    eng.wait("data3 to be written", "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(3))", timeout=10)
    eng.tjs('kag.goToStart(); return 1;')
    eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)
    if standin and eng.tjs("return Live2DStandIn.players + Live2DStandIn.models;") != 0:
        raise SmokeError("Hiyori's model wasn't let go when the game went back to the title: %s"
                         % eng.tjs('return [Live2DStandIn.players, Live2DStandIn.models].join(",");'))
    eng.tjs("loadFunction(3); return 1;")
    eng.wait("Hiyori after the load", 'world_object.env.characters["hiyori"] !== void'
             ' && world_object.env.characters["hiyori"].player !== void && kag.inStable', timeout=30)
    r = str(eng.tjs(hiyori + 'return [c.pose, c.face, c.isShow() ? 1 : 0, c.targetLayer.visible ? 1 : 0].join(",");'))
    print("     after a load: pose, face, shown: %s" % r, flush=True)
    pose_, face_, shown_, visible_ = r.split(",")
    if pose_ != "standard" or face_ not in ("normal", "smile") or shown_ != "1" or visible_ != "1":
        raise SmokeError("after a load Hiyori is %s, not standard and shown" % r)
    # she leaves at the demo's end and lets her model go
    eng.clicker(True, until="s0001.ks")
    eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks"', timeout=180)
    eng.clicker(False)
    if standin and eng.tjs("return Live2DStandIn.players + Live2DStandIn.models;") != 0:
        raise SmokeError("Hiyori's model wasn't let go when she left: %s"
                         % eng.tjs('return [Live2DStandIn.players, Live2DStandIn.models].join(",");'))
    live2d_flip_steps(eng, standin)


def live2d_flip_steps(eng, standin):
    """The l2d flip type (Live2DFlip, GFX_Live2D.tjs): Hiyori's model on a KAG layer ([image
    flip=hiyori.l2d]) and on a World layer ([newlay l2d=hiyori]), with the plugin or the stand-in
    as live2d_steps has it: drawn into its canvas, playing its idle motions, a motion played once
    (l2donce, and its trigger, also for a motion it doesn't have), an expression, a parameter
    added, blinking off, lip-sync to an SE buffer, kept through a store and a restore, played on
    through a World layer's redraw, and let go with its layer"""
    if eng.tjs('return typeof global.Live2DFlip != "undefined" ? 1 : 0;') != 1:
        print("     (the l2d flip: skipped, this build's framework predates Live2D models on layers)", flush=True)
        return
    lay = 'var l = kag.fore.layers[0], f = l.flip; '
    eng.tjs('kag.tagHandlers.image(%[layer:"0", page:"fore", flip:"hiyori.l2d", visible:"true", left:"100", top:"100",'
            ' l2dwidth:"480", l2dheight:"640", l2dparam:"ParamCheek:0.5", l2dexpression:"F01"]); return 1;')
    time.sleep(1.0)
    r = str(eng.tjs(lay + 'var t = new global.Layer(kag, kag.primaryLayer), n = 0; t.assignImages(f);'
                    ' for (var y = 0; y < t.imageHeight; y += 8) for (var x = 0; x < t.imageWidth; x += 8)'
                    ' if (t.getMaskPixel(x, y) > 0) n++; invalidate t;'
                    ' return [l.flipType, n, f.canvasWidth, f.canvasHeight, f.frames, f.poseMotion, l.type == ltAlpha ? 1 : 0,'
                    ' f.player !== void ? 1 : 0].join(",");')).split(",")
    kind, n, frames, motion = r[0], int(r[1]), int(r[4]), r[5]
    print("     on a KAG layer: %s, %d of its samples drawn in %sx%s, %d frames, motion %s"
          % (kind, n, r[2], r[3], frames, motion), flush=True)
    if kind != "l2d" or r[7] != "1":
        raise SmokeError("[image flip=hiyori.l2d] didn't start the l2d flip with a player: %s" % r)
    if n < 50 or r[2:4] != ["480", "640"] or r[6] != "1":
        raise SmokeError("the l2d flip didn't draw the model into a 480x640 ltAlpha picture: %s" % r)
    if frames < 10 or not motion.startswith("Hiyori_m") or motion == "Hiyori_m04":
        raise SmokeError("the l2d flip isn't playing the model's idle motions (%d frames, %s)" % (frames, motion))
    if standin:
        r = str(eng.tjs(lay + 'var s = Live2DStandIn; return [s.last.ParamCheek, s.expressions.find("F01") >= 0 ? 1 : 0,'
                        ' f.player.blinkingMode].join(",");')).split(",")
        print("     the stand-in drew ParamCheek %s, the expression set %s, blinking mode %s" % tuple(r), flush=True)
        if abs(float(r[0]) - 0.5) > 0.001 or r[1] != "1" or r[2] != "1":
            raise SmokeError("l2dparam, l2dexpression or the model's own blinking didn't reach the model: %s" % r)
    # a motion played once, then the idle ones again; l2donce's trigger as it ends
    eng.tjs('kag.tagHandlers.layopt(%[layer:"0", page:"fore", l2donce:"TapBody", l2dblink:"false"]); return 1;')
    kf = 'kag.fore.layers[0].flip'
    eng.wait("TapBody once", kf + '.oncePlaying && ' + kf + '.poseMotion == "Hiyori_m04"', timeout=5)
    eng.wait("the idle motions again", '!' + kf + '.oncePlaying && ' + kf + '.onceDone == 1', timeout=20)
    eng.tjs('kag.tagHandlers.layopt(%[layer:"0", page:"fore", l2donce:"NoSuchMotion"]); return 1;')
    eng.wait("l2donce for a motion it doesn't have", kf + '.onceDone == 2', timeout=5)
    if standin and eng.tjs(lay + 'return f.player.blinkingMode;') != 0:
        raise SmokeError("l2dblink=false didn't turn the model's blinking off")
    print("     l2donce: TapBody played once, the idle motions went on, and a missing motion ended at once", flush=True)
    # lip-sync to SE buffer 0
    eng.tjs('global.__smokeFlipLip = %[ max : 0.0, pos : %[] ]; global.__smokeFlipTimer = new Timer(function() {'
            '  var f = kag.fore.layers[0].flip; if (f === void) return; var s = global.__smokeFlipLip;'
            '  s.max = f.voice if f.voice > s.max; s.pos[kag.se[0].position] = 1; }, "");'
            ' __smokeFlipTimer.interval = 20; __smokeFlipTimer.enabled = true;'
            ' kag.tagHandlers.layopt(%[layer:"0", page:"fore", l2dlip:"0"]); kag.se[0].play(%[storage:"pip000009"]); return 1;')
    time.sleep(3.0)
    r = str(eng.tjs('__smokeFlipTimer.enabled = false; invalidate __smokeFlipTimer; kag.se[0].stop();'
                    ' kag.tagHandlers.layopt(%[layer:"0", page:"fore", l2dlip:""]); var p = []; p.assign(__smokeFlipLip.pos);'
                    ' return [__smokeFlipLip.max, p.count \\ 2, kag.fore.layers[0].flip.voice].join(",");')).split(",")
    print("     l2dlip: the mouth open up to %.2f over %s positions of the sound, then %s" % (float(r[0]), r[1], r[2]), flush=True)
    if int(r[1]) <= 1:
        print("     (the sound doesn't play here, so the mouth isn't checked)", flush=True)
    elif float(r[0]) < 0.3:
        raise SmokeError("l2dlip=0 didn't open the model's mouth with the sound: %s" % r)
    if float(r[2]) != 0.0:
        raise SmokeError("l2dlip= (none) didn't shut the model's mouth: %s" % r)
    # kept through a store and a restore (a save and a load); let go with its layer
    eng.tjs(lay + 'global.__smokeFlipStore = %[]; l.storeFlip(__smokeFlipStore);'
            ' kag.tagHandlers.freeimage(%[layer:"0", page:"fore"]); return 1;')
    eng.wait("the flip to go", 'KAGLive2DOf(kag).players.count == 0', timeout=5)
    eng.tjs('var l = kag.fore.layers[0]; l.restoreFlip(__smokeFlipStore); l.visible = true; return 1;')
    time.sleep(0.5)
    r = str(eng.tjs(lay + 'return [f.file, f.canvasWidth, f.canvasHeight, f.options.l2dexpression, f.options.l2dparam,'
                    ' f.player !== void ? 1 : 0, f.frames > 0 ? 1 : 0].join(",");'))
    print("     restored: %s" % r, flush=True)
    if r != "hiyori.l2d,480,640,F01,ParamCheek:0.5,1,1":
        raise SmokeError("the l2d flip wasn't restored as it was stored: %s" % r)
    eng.tjs('kag.tagHandlers.freeimage(%[layer:"0", page:"fore"]); return 1;')
    eng.wait("the flip to go", 'KAGLive2DOf(kag).players.count == 0', timeout=5)
    # on a World layer: options from newlay and flipupdate, a redraw that keeps it playing
    env = 'var e = world_object.env, t = e.layers["smokel2d"] !== void ? e.layers["smokel2d"].targetLayer : void,'\
          ' f = t !== void ? t.flip : void; '
    wl = 'world_object.env.layers["smokel2d"]'
    wf = wl + '.targetLayer.flip'
    eng.tjs('world_object.env.unknown("newlay", %[name:"smokel2d", l2d:"hiyori", l2dwidth:"450", l2dheight:"600", show:"true"]); return 1;')
    eng.wait("the World layer's model", wl + ' !== void && ' + wl + '.targetLayer !== void && ' + wf + ' !== void && '
             + wf + '.frames > 5', timeout=10)
    r = str(eng.tjs(env + 'return [t.flipType, f.canvasWidth, f.canvasHeight, t.visible ? 1 : 0].join(",");'))
    if r != "l2d,450,600,1":
        raise SmokeError("[newlay l2d=hiyori] didn't show the model as asked: %s" % r)
    eng.tjs('world_object.env.unknown("smokel2d", %[flipupdate:"true", l2donce:"TapBody"]); return 1;')
    eng.wait("TapBody on the World layer", wf + '.oncePlaying', timeout=5)
    eng.tjs(env + 'global.__smokeFlipObj = f; e.unknown("smokel2d", %[grayscale:"true"]); return 1;')
    time.sleep(0.5)
    r = str(eng.tjs(env + 'return [f === global.__smokeFlipObj ? 1 : 0, e.layers["smokel2d"].flipInfo.l2donce === void ? 1 : 0].join(",");'))
    print("     on a World layer: 450x600, l2donce through flipupdate, the same flip after a redraw: %s" % r, flush=True)
    if r != "1,1":
        raise SmokeError("a World layer's l2d flip didn't play on through a redraw, or kept l2donce to play again: %s" % r)
    eng.tjs('global.__smokeFlipObj = void; world_object.env.delLayer(%[name:"smokel2d"]); world_object.env.destroy(); return 1;')
    eng.wait("the World layer's model to go", 'KAGLive2DOf(kag).players.count == 0', timeout=5)
    # in a scenario, [layopt l2donce=...][waittrig name=l2donce] goes on when the motion ends: the
    # motion starts with the next frame, never inside the tag (a trigger sent while nothing waits
    # is lost); and so it does where the model can't be drawn (a Live2D device without the plugin)
    if isinstance(eng, DesktopEngine):
        with open(os.path.join(eng.savedir, "zz_l2dwait.ks"), "w", encoding="utf-8") as f:
            f.write('*start\n[image layer=1 page=fore flip=hiyori.l2d visible=true]\n'
                    '[layopt layer=1 page=fore l2donce=TapBody]\n[waittrig name=l2donce]\n'
                    '[eval exp="global.__smokeL2DWaited = 1"]\n[freeimage layer=1 page=fore]\n[s]\n')
        dirname = tjs_string(storage_name(eng.savedir) + "/")
        eng.tjs('global.__smokeL2DWaited = 0; Storages.addAutoPath(%s); kag.process("zz_l2dwait.ks"); return 1;' % dirname)
        eng.wait("[waittrig name=l2donce] after TapBody", "global.__smokeL2DWaited", timeout=20)
        eng.tjs('global.__smokeL2DSys = kag.live2dSystem; var u = new KAGLive2D(kag); u.release(); kag.live2dSystem = u;'
                ' global.__smokeL2DWaited = 0; kag.process("zz_l2dwait.ks"); return 1;')
        eng.wait("[waittrig name=l2donce] where the model can't be drawn", "global.__smokeL2DWaited", timeout=10)
        time.sleep(0.3)
        eng.tjs('var u = kag.live2dSystem; kag.live2dSystem = global.__smokeL2DSys; invalidate u;'
                ' Storages.removeAutoPath(%s); kag.process("s0001.ks"); return 1;' % dirname)
        eng.wait("the demo menu again", "kag.inStable && kag.selectShowing", timeout=30)
        print("     [layopt l2donce=TapBody][waittrig name=l2donce] went on, with the model drawn and without", flush=True)
    if standin and eng.tjs("return Live2DStandIn.players + Live2DStandIn.models;") != 0:
        raise SmokeError("the l2d flips' models weren't let go: %s"
                         % eng.tjs('return [Live2DStandIn.players, Live2DStandIn.models].join(",");'))


def three_framework(eng):
    return eng.tjs('return typeof global.KAGThreeOf != "undefined" && typeof global.ThreeFlip != "undefined" ? 1 : 0;') == 1


def three_why(eng):
    """Why 3D can't be drawn here ("" when it can): the krkrthreepp plugin, OpenGL ES, Vee's model"""
    return str(eng.tjs('var s = KAGThreeOf(kag); return !s.available ? s.reason : s.findFile("vee", "vrm") == ""'
                       ' ? "no fgimage/vee.vrm (tools/assets/make_vrm.py)" : "";'))


def vrm_steps(eng):
    """The Animated Character demo's VRM character, Vee (KAGEnvCharacterVRM.tjs, drawn by the
    krkrthreepp plugin; her model and motions are tools/assets/make_vrm.py's): her picture where
    the World puts her, upright, drawn again as she moves, blinking, a face fading in and reaching
    the avatar's expressions, lip-sync to her voice through its lip track (the expression of each
    vowel), a motion played once and the pose's again, another pose, a save and a load, and the
    avatar let go when she leaves. Where 3D can't be drawn the demo says so (checked as the demos
    played)."""
    if not three_framework(eng) or eng.tjs('return typeof global.KAGEnvCharacterVRM != "undefined"'
                                           ' && world_object.env.characterInits["vee"] !== void ? 1 : 0;') != 1:
        if eng.opts.three == "required":
            raise SmokeError("--three required, but this build's framework or sample predates VRM characters")
        print("     (skipped: this build's framework or sample predates VRM characters)", flush=True)
        return
    why = three_why(eng)
    if why:
        if eng.opts.three == "required":
            raise SmokeError("3D can't be drawn here: " + why)
        print("     (skipped: 3D can't be drawn here: %s)" % why, flush=True)
        return
    vee = 'var c = world_object.env.characters["vee"]; '
    eng.tjs('global.__smokeVRMBlink = eyeFlipFreq; eyeFlipFreq = 1.0; kag.process("anim.ks", "*start"); return 1;')
    eng.wait("Pip", 'world_object.env.characters["pip"] !== void && kag.inStable', timeout=20)
    eng.tjs('kag.process("anim.ks", "*vrm"); return 1;')
    eng.wait("Vee", 'world_object.env.characters["vee"] !== void && world_object.env.characters["vee"].vrm !== void'
             ' && kag.inStable', timeout=60)
    time.sleep(1.5)
    print("     first use (ms): %s" % eng.tjs('var t = KAGThreeOf(kag).timings, a = [], k = []; k.assign(t);'
                                             ' for (var i = 0; i < k.count; i += 2) a.add(k[i] + " " + k[i + 1]);'
                                             ' return a.join(", ") + "; MSAA " + KAGThreeOf(kag).samples;'), flush=True)
    # drawn, and on the screen: the World puts her picture's centre at center, 190 below the
    # screen's centre; upright: her head and twin tails (the top quarter) are wider than her legs
    drawn = str(eng.tjs(vee + 'var t = c.targetLayer, l = c.renderLayer, n = 0, top = 0, bottom = 0, h = l.imageHeight;'
                        ' for (var y = 0; y < h; y += 8) for (var x = 0; x < l.imageWidth; x += 8)'
                        ' if (l.getMaskPixel(x, y) > 0) { n++; top++ if y < h / 4; bottom++ if y >= h * 3 / 4; }'
                        ' var left = (int)(t._affineleft - t.afx), tp = (int)(t._affinetop - t.afy);'
                        ' return [n, t.visible ? 1 : 0, left, tp, l.imageWidth, l.imageHeight, top, bottom].join(",");'))
    n, visible, left, top, width, height, upper, lower = [int(v) for v in drawn.split(",")]
    print("     Vee: %d of her picture's samples drawn, %dx%d at (%d, %d); %d in its top quarter, %d in its bottom one"
          % (n, width, height, left, top, upper, lower), flush=True)
    if n < 300 or not visible:
        raise SmokeError("Vee isn't drawn: %s" % drawn)
    if abs(left + width / 2 - 960) > 2 or abs(top + height / 2 - 730) > 2:
        raise SmokeError("Vee's picture is centred at (%d, %d), not at center's (960, 730)" % (left + width / 2, top + height / 2))
    if upper < lower * 1.5:
        raise SmokeError("Vee's head isn't at the top of her picture (upside down?): %s" % drawn)
    eng.tjs(vee + 'global.__smokeVRMDraw = c.lastDraw; return 1;')
    time.sleep(1.0)
    if eng.tjs(vee + 'return c.lastDraw != global.__smokeVRMDraw ? 1 : 0;') != 1:
        raise SmokeError("Vee was drawn once, and not again as she moved")
    # blinking (eyeFlipFreq 1: a blink every frame or so) and open eyes between; a face that
    # fades in and reaches the avatar
    eng.tjs('global.__smokeVRM = %[ blinkMin : 9.0, blinkMax : 0.0, mouth : %[], samples : 0, after : 0 ];'
            ' global.__smokeVRMTimer = new Timer(function() {'
            '  var c = world_object.env.characters["vee"]; if (c === void || c.vrm === void) return; var s = global.__smokeVRM;'
            '  var b = c.weights.blink; if (b !== void) { s.blinkMin = b if b < s.blinkMin; s.blinkMax = b if b > s.blinkMax; }'
            '  s.samples++;'
            '  var v = c.soundBuffer; if (v !== void && v.status == "play") {'
            '   var k = []; k.assign(c.mouth); for (var i = 0; i < k.count; i += 2) {'
            '    var w = c.vrm.getExpression(c.expressions.find(k[i]));'
            '    s.mouth[k[i]] = w if s.mouth[k[i]] === void || w > s.mouth[k[i]]; } }'
            ' }, ""); __smokeVRMTimer.interval = 20; __smokeVRMTimer.enabled = true; return 1;')
    # a blink first (the iOS Simulator draws 3 to 6 frames a second), then the laugh, which is
    # all of happy and fades blinking out
    blinked = True
    try:
        eng.wait("Vee to blink, with her eyes open between", 'global.__smokeVRM.blinkMax >= 0.8 && global.__smokeVRM.blinkMin <= 0.05',
                 timeout=15)
    except SmokeError:
        blinked = False
    eng.tjs('var c = world_object.env.characters["vee"]; c.setFace("laugh", %[]);'
            ' global.__smokeVRMMid = c.currentFaceValues(c.faceStart + vrmFaceFade / 2).happy; return 1;')
    try:
        ch = 'world_object.env.characters["vee"]'
        eng.wait("the laugh to fade in", ch + '.weights.happy > 0.99 && ' + ch + '.vrm.getExpression("happy") > 0.99',
                 timeout=15)
    except SmokeError:
        pass  # the check below says what it was
    r = str(eng.tjs(vee + 'var s = global.__smokeVRM;'
                    ' return [s.blinkMin, s.blinkMax, global.__smokeVRMMid, c.weights.happy, c.vrm.getExpression("happy"), c.face].join(",");')).split(",")
    print("     blinking: blink from %s up to %s; laugh: happy %s halfway through its fade, then %s (the avatar's %s)"
          % (r[0], r[1], r[2], r[3], r[4]), flush=True)
    # (laugh is all of happy, which fades blinking out: the blink was seen before it)
    if not blinked or float(r[1]) < 0.8 or float(r[0]) > 0.05:
        raise SmokeError("Vee didn't blink, or her eyes didn't open between blinks: %s" % r)
    if not 0.3 < float(r[2]) < 0.7 or abs(float(r[3]) - 1.0) > 0.01 or abs(float(r[4]) - 1.0) > 0.01 or r[5] != "laugh":
        raise SmokeError("Vee's laugh face didn't fade in and reach her avatar: %s" % r)
    # lip-sync to her voice (vee000001, which has a lip track): each vowel's expression opens
    eng.tjs(vee + 'c.setFace("normal", %[]); c.playVoice("vee000001"); return 1;')
    end = time.time() + 14
    while time.time() < end:
        time.sleep(0.5)
        if eng.tjs(vee + 'var b = c.soundBuffer; return b !== void && b.status != "play" ? 1 : 0;') == 1:
            break
    time.sleep(0.6)
    r = str(eng.tjs(vee + 'var m = [], k = []; k.assign(global.__smokeVRM.mouth); for (var i = 0; i < k.count; i += 2) m.add(k[i] + ":" + "%.2f".sprintf(k[i + 1]));'
                    ' var after = 0.0; k.assign(c.mouth); for (var i = 0; i < k.count; i += 2) after = k[i + 1] if k[i + 1] > after;'
                    ' return [m.join(" "), after, c.lipTrack === void ? 0 : c.lipTrack.times.count, c.soundBuffer.position].join(",");')).split(",")
    opened = dict((kv.split(":")[0], float(kv.split(":")[1])) for kv in r[0].split()) if r[0] else {}
    print("     lip-sync: the mouth's expressions at most %s; after the voice %s; a lip track of %s marks"
          % (r[0] or "none", r[1], r[2]), flush=True)
    if int(r[2]) == 0:
        raise SmokeError("vee000001.lip wasn't read for Vee's line")
    if not opened:
        print("     (the voice doesn't play here, so the mouth isn't checked)", flush=True)
    elif len([v for v in opened.values() if v > 0.3]) < 2:
        raise SmokeError("Vee's mouth didn't make the expressions of her lip track's vowels: %s" % r[0])
    if float(r[1]) > 0.05:
        raise SmokeError("Vee's mouth stayed open after her voice: %s" % r[1])
    # a motion played once (wave), fading in from the pose and back; another pose (think)
    eng.tjs(vee + 'c.playOnce("wave", %[]); return 1;')
    eng.wait("the wave", 'world_object.env.characters["vee"].oneShotPlaying', timeout=5)
    r = str(eng.tjs(vee + 'return [c.onceAnim !== void ? c.onceAnim.getDuration() : 0, c.fromAnim !== void ? 1 : 0].join(",");'))
    # (her motions' clock moves at most 100 ms a frame, so a Simulator drawing a few frames a
    # second takes several times the wave's 4 s: the release runs' Live2D iOS job ran out at 10)
    eng.wait("the pose again", '!world_object.env.characters["vee"].oneShotPlaying', timeout=60)
    print("     wave: a VRM animation of %s s, faded in from the pose: %s" % tuple(r.split(",")), flush=True)
    if abs(float(r.split(",")[0]) - 2.6) > 0.05:
        raise SmokeError("wave didn't play vee_wave.vrma: %s" % r)
    eng.tjs(vee + 'c.setPose("think", %[]); return 1;')
    eng.wait("the think pose", 'world_object.env.characters["vee"].poseAnim !== void && world_object.env.characters["vee"].poseAnim'
             ' === KAGThreeOf(kag).animation(KAGThreeOf(kag).findFile("vee_think", "vrma"))', timeout=5)
    eng.tjs(vee + 'c.setPose("standard", %[]); __smokeVRMTimer.enabled = false; invalidate __smokeVRMTimer;'
            ' eyeFlipFreq = global.__smokeVRMBlink; return 1;')
    print("     think: the pose's VRM animation changed", flush=True)
    # a save and a load with her on the screen: drawn again from a new avatar
    eng.tjs("kag.saveBookMark(4); return 1;")
    eng.wait("data4 to be written", "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(4))", timeout=10)
    eng.tjs('kag.goToStart(); return 1;')
    eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)
    if eng.tjs('return KAGThreeOf(kag).users.count;') != 0:
        raise SmokeError("Vee's avatar wasn't let go when the game went back to the title")
    eng.tjs("loadFunction(4); return 1;")
    eng.wait("Vee after the load", 'world_object.env.characters["vee"] !== void'
             ' && world_object.env.characters["vee"].vrm !== void && kag.inStable', timeout=30)
    r = str(eng.tjs(vee + 'return [c.pose, c.isShow() ? 1 : 0, c.targetLayer.visible ? 1 : 0].join(",");'))
    print("     after a load: pose, shown: %s" % r, flush=True)
    if r != "standard,1,1":
        raise SmokeError("after a load Vee is %s, not standard and shown" % r)
    eng.clicker(True, until="s0001.ks")
    eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks"', timeout=180)
    eng.clicker(False)
    if eng.tjs('return KAGThreeOf(kag).users.count;') != 0:
        raise SmokeError("Vee's avatar wasn't let go when she left")


def three_flip_steps(eng):
    """The 3d flip type (ThreeFlip, GFX_Three.tjs) on KAG layers and a World layer: Vee's avatar
    (its VRM animation, one played once and its trigger, expressions, lip-sync to an SE buffer, a
    store and a restore), the glTF star (its clip, another once, a missing one ending at once),
    the sample's scene built in script (3donce through its script), [layopt 3donce=...]
    [waittrig name=3donce] going on in a scenario, and everything let go; where 3D can't be drawn,
    the flip shows nothing and 3donce still ends."""
    if not three_framework(eng):
        print("     (skipped: this build's framework predates 3D)", flush=True)
        return
    why = three_why(eng)
    kf = 'kag.fore.layers[1].flip'
    lay = 'var l = kag.fore.layers[1], f = l.flip; '
    count = ('var t = new global.Layer(kag, kag.primaryLayer), n = 0; t.assignImages(f);'
             ' for (var y = 0; y < t.imageHeight; y += 8) for (var x = 0; x < t.imageWidth; x += 8)'
             ' if (t.getMaskPixel(x, y) > 0) n++; invalidate t; ')
    if why:
        if eng.opts.three == "required":
            raise SmokeError("3D can't be drawn here: " + why)
        # nothing drawn, and 3donce ends a frame later
        eng.tjs('kag.tagHandlers.image(%[layer:"1", page:"fore", flip:"vee.vrm", visible:"true", "3dwidth" => "100", "3dheight" => "100"]);'
                ' kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3donce" => "vee_wave"]); return 1;')
        eng.wait("3donce where 3D can't be drawn", kf + '.onceDone == 1', timeout=5)
        eng.tjs('kag.tagHandlers.freeimage(%[layer:"1", page:"fore"]); return 1;')
        print("     3D can't be drawn here (%s): the flip showed nothing, and 3donce ended at once" % why, flush=True)
        return
    # Vee's avatar
    eng.tjs('kag.tagHandlers.image(%[layer:"1", page:"fore", flip:"vee.vrm", visible:"true", left:"100", top:"100",'
            ' "3dwidth" => "400", "3dheight" => "640", "3dmotion" => "vee_idle", "3dframe" => "-0.03,1.47",'
            ' "3dexpression" => "happy:1"]); return 1;')
    # ten frames: the iOS Simulator draws 6 a second
    eng.wait("ten frames of the avatar", kf + ' !== void && ' + kf + '.frames >= 10', timeout=15)
    r = str(eng.tjs(lay + count + 'return [l.flipType, n, f.canvasWidth, f.canvasHeight, f.frames, f.kind, l.type == ltAlpha ? 1 : 0,'
                    ' f.vrm.getExpression("happy"), f.motionAnim !== void ? f.motionAnim.getDuration() : 0].join(",");')).split(",")
    print("     a VRM avatar on a KAG layer: %s %s, %s of its samples drawn in %sx%s, %s frames, happy %s, its motion %s s"
          % (r[0], r[5], r[1], r[2], r[3], r[4], r[7], r[8]), flush=True)
    if r[0] != "3d" or r[5] != "vrm" or int(r[1]) < 100 or r[2:4] != ["400", "640"] or r[6] != "1":
        raise SmokeError("[image flip=vee.vrm] didn't draw the avatar into a 400x640 ltAlpha picture: %s" % r)
    if int(r[4]) < 10 or abs(float(r[7]) - 1) > 0.01 or abs(float(r[8]) - 4.0) > 0.05:
        raise SmokeError("the 3d flip isn't playing vee_idle with happy set: %s" % r)
    eng.tjs('kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3donce" => "vee_wave", "3dexpression" => ""]); return 1;')
    eng.wait("vee_wave once", kf + '.oncePlaying', timeout=5)
    eng.wait("the idle motion again", '!' + kf + '.oncePlaying && ' + kf + '.onceDone == 1', timeout=60)
    eng.tjs('kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3donce" => "no_such_motion"]); return 1;')
    eng.wait("3donce for a motion it doesn't have", kf + '.onceDone == 2', timeout=5)
    # as a string: the Android, iOS and web REPLs print a real with a comment ("+0.0 /* +0.0 */")
    if float(eng.tjs(lay + 'return "%f".sprintf(f.vrm.getExpression("happy"));')) != 0.0:
        raise SmokeError('3dexpression="" didn\'t take happy off the avatar')
    print("     3donce: vee_wave played once, the idle motion went on, a missing one ended at once", flush=True)
    # lip-sync to SE buffer 0
    eng.tjs('global.__smoke3DLip = %[ max : 0.0, aa : 0.0, pos : %[] ]; global.__smoke3DTimer = new Timer(function() {'
            '  var f = kag.fore.layers[1].flip; if (f === void || f.vrm === void) return; var s = global.__smoke3DLip;'
            '  s.max = f.voice if f.voice > s.max; var a = f.vrm.getExpression("aa"); s.aa = a if a > s.aa;'
            '  s.pos[kag.se[0].position] = 1; }, "");'
            ' __smoke3DTimer.interval = 20; __smoke3DTimer.enabled = true;'
            ' kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3dlip" => "0"]); kag.se[0].play(%[storage:"vee000001"]); return 1;')
    time.sleep(3.0)
    r = str(eng.tjs('__smoke3DTimer.enabled = false; invalidate __smoke3DTimer; kag.se[0].stop();'
                    ' kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3dlip" => ""]); var p = []; p.assign(__smoke3DLip.pos);'
                    ' return [__smoke3DLip.max, __smoke3DLip.aa, p.count \\ 2, kag.fore.layers[1].flip.voice].join(",");')).split(",")
    print("     3dlip: the mouth open up to %.2f (aa %.2f) over %s positions of the sound, then %s"
          % (float(r[0]), float(r[1]), r[2], r[3]), flush=True)
    if int(r[2]) <= 1:
        print("     (the sound doesn't play here, so the mouth isn't checked)", flush=True)
    elif float(r[0]) < 0.3 or float(r[1]) < 0.3:
        raise SmokeError("3dlip=0 didn't open the avatar's mouth with the sound: %s" % r)
    if float(r[3]) != 0.0:
        raise SmokeError("3dlip= (none) didn't shut the avatar's mouth: %s" % r)
    # kept through a store and a restore; let go with its layer
    eng.tjs(lay + 'global.__smoke3DStore = %[]; l.storeFlip(__smoke3DStore); kag.tagHandlers.freeimage(%[layer:"1", page:"fore"]); return 1;')
    eng.wait("the flip to go", 'KAGThreeOf(kag).users.count == 0', timeout=5)
    eng.tjs('var l = kag.fore.layers[1]; l.restoreFlip(__smoke3DStore); l.visible = true; return 1;')
    time.sleep(0.5)
    r = str(eng.tjs(lay + 'return [f.file, f.canvasWidth, f.canvasHeight, f.options["3dmotion"], f.options["3dframe"],'
                    ' f.vrm !== void ? 1 : 0, f.frames > 0 ? 1 : 0].join(",");'))
    print("     restored: %s" % r, flush=True)
    if r != "vee.vrm,400,640,vee_idle,-0.03,1.47,1,1":
        raise SmokeError("the 3d flip wasn't restored as it was stored: %s" % r)
    eng.tjs('kag.tagHandlers.freeimage(%[layer:"1", page:"fore"]); return 1;')
    eng.wait("the flip to go", 'KAGThreeOf(kag).users.count == 0', timeout=5)
    # the glTF star: its first clip (spin) goes on; hop once; a clip it doesn't have
    eng.tjs('kag.tagHandlers.image(%[layer:"1", page:"fore", flip:"star3d.glb", visible:"true",'
            ' "3dwidth" => "300", "3dheight" => "300", "3dframe" => "-0.7,0.7"]); return 1;')
    eng.wait("frames of the star", kf + ' !== void && ' + kf + '.frames >= 5', timeout=15)
    r = str(eng.tjs(lay + count + 'return [f.kind, n, f.frames, f.action !== void ? 1 : 0, f.model.getAnimationCount(),'
                    ' f.model.getAnimationName(0)].join(",");')).split(",")
    print("     a glTF model: %s, %s samples drawn, %s frames, a clip playing %s, clips %s (%s first)" % tuple(r), flush=True)
    if r[0] != "gltf" or int(r[1]) < 50 or r[3] != "1" or r[4] != "2":
        raise SmokeError("[image flip=star3d.glb] didn't draw the star playing its clip: %s" % r)
    eng.tjs('kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3donce" => "hop"]); return 1;')
    eng.wait("hop once", kf + '.oncePlaying', timeout=5)
    eng.wait("spin again", '!' + kf + '.oncePlaying && ' + kf + '.onceDone == 1', timeout=10)
    eng.tjs('kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3donce" => "nothing"]); return 1;')
    eng.wait("3donce for a clip it doesn't have", kf + '.onceDone == 2', timeout=5)
    eng.tjs('kag.tagHandlers.freeimage(%[layer:"1", page:"fore"]); return 1;')
    eng.wait("the flip to go", 'KAGThreeOf(kag).users.count == 0', timeout=5)
    print("     glTF: hop played once, spin went on, a missing clip ended at once", flush=True)
    # the scene built in script (Scenes3D.tjs: stage3d)
    if eng.tjs('return KAGThreeScenes["stage3d"] !== void ? 1 : 0;') == 1:
        eng.tjs('kag.tagHandlers.image(%[layer:"1", page:"fore", flip:"stage3d", visible:"true", "3dwidth" => "480", "3dheight" => "270"]); return 1;')
        eng.wait("ten frames of the scene", kf + ' !== void && ' + kf + '.frames >= 10', timeout=15)
        r = str(eng.tjs(lay + count + 'return [f.kind, n, f.frames, f.ctx.knot !== void ? 1 : 0, "%.2f".sprintf(f.time)].join(",");')).split(",")
        print("     a scene built in script: %s, %s samples drawn, %s frames, %s s played" % (r[0], r[1], r[2], r[4]), flush=True)
        if r[0] != "scene" or int(r[1]) < 50 or int(r[2]) < 10 or r[3] != "1":
            raise SmokeError("[image flip=stage3d] didn't build and draw the scene: %s" % r)
        eng.tjs('kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3donce" => "jump"]); return 1;')
        eng.wait("the knot's jump", kf + '.oncePlaying && ' + kf + '.ctx.jump > 0', timeout=5)
        eng.wait("its end", '!' + kf + '.oncePlaying && ' + kf + '.onceDone == 1', timeout=5)
        eng.tjs('kag.tagHandlers.layopt(%[layer:"1", page:"fore", "3donce" => "dance"]); return 1;')
        eng.wait("3donce the scene doesn't know", kf + '.onceDone == 2', timeout=5)
        eng.tjs('kag.tagHandlers.freeimage(%[layer:"1", page:"fore"]); return 1;')
        eng.wait("the flip to go", 'KAGThreeOf(kag).users.count == 0', timeout=5)
        print("     the scene: 3donce=jump through its script, an unknown one ended at once", flush=True)
    # on a World layer: options from newlay and flipupdate, a redraw that keeps it playing
    env = 'var e = world_object.env, t = e.layers["smoke3d"] !== void ? e.layers["smoke3d"].targetLayer : void,'\
          ' f = t !== void ? t.flip : void; '
    wl = 'world_object.env.layers["smoke3d"]'
    wf = wl + '.targetLayer.flip'
    eng.tjs('world_object.env.unknown("newlay", %[name:"smoke3d", "3d" => "vee", "3dwidth" => "300", "3dheight" => "480",'
            ' "3dmotion" => "vee_idle", show:"true"]); return 1;')
    eng.wait("the World layer's avatar", wl + ' !== void && ' + wl + '.targetLayer !== void && ' + wf + ' !== void && '
             + wf + '.frames > 5', timeout=10)
    r = str(eng.tjs(env + 'return [t.flipType, f.kind, f.canvasWidth, f.canvasHeight, t.visible ? 1 : 0].join(",");'))
    if r != "3d,vrm,300,480,1":
        raise SmokeError("[newlay 3d=vee] didn't show the avatar as asked: %s" % r)
    eng.tjs('world_object.env.unknown("smoke3d", %[flipupdate:"true", "3donce" => "vee_nod"]); return 1;')
    eng.wait("the nod on the World layer", wf + '.oncePlaying', timeout=5)
    eng.tjs(env + 'global.__smoke3DObj = f; e.unknown("smoke3d", %[grayscale:"true"]); return 1;')
    time.sleep(0.5)
    r = str(eng.tjs(env + 'return [f === global.__smoke3DObj ? 1 : 0, e.layers["smoke3d"].flipInfo["3donce"] === void ? 1 : 0].join(",");'))
    print("     on a World layer: 300x480, 3donce through flipupdate, the same flip after a redraw: %s" % r, flush=True)
    if r != "1,1":
        raise SmokeError("a World layer's 3d flip didn't play on through a redraw, or kept 3donce to play again: %s" % r)
    eng.tjs('global.__smoke3DObj = void; world_object.env.delLayer(%[name:"smoke3d"]); world_object.env.destroy(); return 1;')
    eng.wait("the World layer's avatar to go", 'KAGThreeOf(kag).users.count == 0', timeout=5)
    # in a scenario, [layopt 3donce=...][waittrig name=3donce] goes on when the motion ends, as
    # it does where 3D can't be drawn (a 3D system without the plugin)
    if isinstance(eng, DesktopEngine):
        with open(os.path.join(eng.savedir, "zz_3dwait.ks"), "w", encoding="utf-8") as f:
            f.write('*start\n[image layer=1 page=fore flip=star3d.glb 3dwidth=200 3dheight=200 visible=true]\n'
                    '[layopt layer=1 page=fore 3donce=hop]\n[waittrig name=3donce]\n'
                    '[eval exp="global.__smoke3DWaited = 1"]\n[freeimage layer=1 page=fore]\n[s]\n')
        dirname = tjs_string(storage_name(eng.savedir) + "/")
        eng.tjs('global.__smoke3DWaited = 0; Storages.addAutoPath(%s); kag.process("zz_3dwait.ks"); return 1;' % dirname)
        eng.wait("[waittrig name=3donce] after hop", "global.__smoke3DWaited", timeout=20)
        eng.tjs('global.__smoke3DSys = kag.threeSystem; var u = new KAGThree(kag); u.release(); kag.threeSystem = u;'
                ' global.__smoke3DWaited = 0; kag.process("zz_3dwait.ks"); return 1;')
        eng.wait("[waittrig name=3donce] where 3D can't be drawn", "global.__smoke3DWaited", timeout=10)
        time.sleep(0.3)
        eng.tjs('var u = kag.threeSystem; kag.threeSystem = global.__smoke3DSys; invalidate u;'
                ' Storages.removeAutoPath(%s); kag.process("s0001.ks"); return 1;' % dirname)
        eng.wait("the demo menu again", "kag.inStable && kag.selectShowing", timeout=30)
        print("     [layopt 3donce=hop][waittrig name=3donce] went on, with the model drawn and without", flush=True)
    if eng.tjs('return KAGThreeOf(kag).users.count;') != 0:
        raise SmokeError("the 3d flips' models weren't let go")


def compiled_framework(eng):
    """Whether the framework compiles scenarios (SceneParser.tjs; pages.yml may test an older
    release's site)"""
    return eng.tjs('return typeof global.KAGCompileScenarios != "undefined" ? 1 : 0;') == 1


def language_framework(eng):
    """Whether the game can be shown in Japanese as well as English (Language.tjs, KAGLanguageList;
    pages.yml may test an older release's site)"""
    return eng.tjs('return typeof global.KAGLanguage == "Object" && KAGLanguage !== void && KAGLanguage.available'
                   ' && KAGLanguage.has("ja") ? 1 : 0;') == 1


# The text the message window shows (MessageLayer.redrawTextStates, Language.tjs): the speaker's
# name as drawn, and each text unit, a compiled scenario's text with what it says in every
# language (texts, by code) and what was drawn, as JSON (the json plugin reads the language
# tables, so it's there)
PAGE_TJS = r"""
    var ops = kag.current.redrawTextStates, units = [], name = "", unit = void, drawn = "";
    for (var i = 0; ops !== void && i < ops.count; i++) {
        var op = ops[i];
        if (op[0] == "processName") name = op[1];
        else if (op[0] == "beginTextUnit") { unit = op[1]; drawn = ""; }
        else if (op[0] == "processCh" && unit !== void) drawn += op[1];
        else if (op[0] == "endTextUnit" && unit !== void) { units.add(%[texts:unit.texts, drawn:drawn]); unit = void; }
    }
    if (unit !== void) units.add(%[texts:unit.texts, drawn:drawn]);
    return Scripts.toJSONString(%[name:name, units:units]);"""


# The word wrap on a message layer of its own (MainWindow.tjs needsToBeWrapped): each character
# of a text goes through it and the layer as the ch tag sends it, with the page cleared where it
# fills; the lines drawn come back as JSON (lines: %[text, end (x where it ends), kag (KAG's own
# character wrap ended it)], limit: where the wrap breaks, planning: krkr_richtext planned it,
# rich: krkr_richtext draws there, pages)
WRAP_TJS = r"""
// global.__smokeWrap(texts, strategy, startX, lines, words): draws each text through the word wrap
// on a message layer of its own, lines high (words: its language has spaces between words), and
// returns what it drew as JSON
global.__smokeWrap = function(text, strategy, startX, lineCount, words = 1) {
	var lay = new MessageLayer(kag, kag.back.base, "smoke line breaking", 99, true);
	var r = %[ lines:[], pages:0 ];
	var cur = kag.current, saved = kag.saveWordWrap(), strat = kag.lineBreakStrategy;
	var hist = kag.historyWriteEnabled, tw = kag.textWriteEnabled;
	try {
		lay.useRichText = kag.fore.messages[0].useRichText;
		// the font size from the settings (a comment of its own line: the Android harness sends
		// the command as one line and leaves out lines that are only a comment)
		lay.clear();
		lay.setPosition(%[ left:0, top:0, width:1800, height:40 + lineCount * (lay.fontSize + lay.lineSpacing) + (lay.fontSize >> 1),
			marginl:48, margint:20, marginr:60, marginb:20 ]);
		lay.clear();
		kag.current = lay, kag.lineBreakStrategy = strategy;
		kag.historyWriteEnabled = false, kag.textWriteEnabled = true;
		if (startX >= 0) lay.x = startX;
		r.limit = lay.relinexpos;
		var w = %[ wrap:%[ key:"smoke:" + System.getTickCount() + ":" + Math.random(), line:text, wordWrap:words ] ];
		var line = "", y = lay.y, x = lay.x;
		for (var i = 0; i < text.length; i++) {
			var ch = text[i];
			if (ch == "\n") {
				r.lines.add(%[ text:line, end:x ]), line = "";
				if (lay.processReturn()) r.pages++, lay.clear();
				y = lay.y, x = lay.x;
				continue;
			}
			if (kag.needsToBeWrapped(ch, w)) {
				// the page is full: the conductor would clear it and run this ch again
				r.lines.add(%[ text:line, end:x ]), line = "", r.pages++;
				lay.clear();
				y = lay.y;
				kag.needsToBeWrapped(ch, w);
			}
			if (lay.y != y) r.lines.add(%[ text:line, end:x ]), line = "", y = lay.y;
			if (kag.wrapDropSpace && ch == " ") continue;
			if (lay.processCh(ch, 0)) {
				// KAG's own wrap filled the page
				r.lines.add(%[ text:line, end:x ]), line = "", r.pages++;
				lay.clear();
				y = lay.y;
				kag.wrapResume = true, kag.wrapResumeDropHist = false;
				i--;
				continue;
			}
			if (lay.y != y) r.lines.add(%[ text:line, end:x, kag:1 ]), line = "", y = lay.y;
			line += ch, x = lay.x;
		}
		r.lines.add(%[ text:line, end:x ]);
		r.planning = kag.wrapPlanning ? 1 : 0;
		r.rich = lay.getRichTextApp(lay.lineLayer) !== void ? 1 : 0;
		r.runs = typeof lay.styledRunCount != "undefined" ? lay.styledRunCount : -1;
	} catch (e) {
		r.error = e.message;
	}
	kag.current = cur, kag.lineBreakStrategy = strat;
	kag.historyWriteEnabled = hist, kag.textWriteEnabled = tw;
	kag.restoreWordWrap(saved);
	invalidate lay;
	return Scripts.toJSONString(r);
};
"""


STYLED_TJS = r"""
// global.__smokeStyled(text, styled): draws text a character at a time on a message layer of its
// own, its characters together (useStyledLayout) or one at a time, and returns as JSON where each
// character went, the runs drawn and how far the line layer's ink reaches
global.__smokeStyled = function(text, styled) {
	var lay = new MessageLayer(kag, kag.back.base, "smoke text drawing", 98, true);
	var r = %[];
	try {
		lay.useRichText = kag.fore.messages[0].useRichText;
		lay.useStyledLayout = styled;
		lay.clear();
		lay.setPosition(%[ left:0, top:0, width:1200, height:200, marginl:30, margint:40, marginr:30, marginb:20 ]);
		lay.clear();
		var xs = [];
		for (var i = 0; i < text.length; i++) {
			lay.processCh(text[i], 0);
			xs.add(lay.x);
		}
		r.xs = xs.join(",");
		r.runs = lay.styledRunCount;
		r.rich = lay.getRichTextApp(lay.lineLayer) !== void ? 1 : 0;
		// the run is drawn once the conductor stops: now, for this test
		if (typeof lay.flushStyledRun != "undefined") lay.flushStyledRun();
		var ll = lay.lineLayer, w = ll.imageWidth, h = ll.imageHeight, right = -1, ink = 0;
		for (var x = 0; x < w; x++) {
			var col = 0;
			for (var y = 0; y < h; y += 2) col += ll.getMaskPixel(x, y);
			if (col > 0) right = x, ink += col;
		}
		r.right = right, r.ink = ink;
	} catch (e) {
		r.error = e.message;
	}
	invalidate lay;
	return Scripts.toJSONString(r);
};
"""


def tjs_string(text):
    """text as a TJS string literal"""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def page_text(eng):
    """(name, [(texts by language code, drawn)...]) of the message window"""
    page = json.loads(str(eng.tjs(PAGE_TJS)))
    units = [((u.get("texts") or {}), u.get("drawn") or "") for u in (page.get("units") or [])]
    return page.get("name") or "", units


def switch_language(eng, lang, where):
    """F9 (the sample has two languages) when the game isn't in lang, then waits for the screen
    at where (a script) drawn again in it"""
    if eng.tjs("return KAGLanguage.current;") != lang:
        eng.key("VK_F9")
    eng.wait(lang + " shown", 'KAGLanguage.current == "%s" && kag.languagePending === void'
             ' && kag.conductor.curStorage == "%s" && kag.inStable && kag.transCount == 0' % (lang, where), timeout=20)


def sample_steps(eng):
    steps, step = collector()
    eng.compiled = False

    @step("start-up reaches the title screen")
    def _():
        eng.wait("the REPL", "1", timeout=60)
        eng.clicker(True, until="title.ks")  # clicks through the logo
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=60)
        eng.clicker(False)

    @step("the sample is in English for the steps that read its text (KAGLanguageList)")
    def _():
        # the game takes the system's language until the player chooses one: under a C locale
        # the engine's candidates are Japanese first
        if not language_framework(eng):
            print("     (skipped: this build has one language)", flush=True)
            return
        shown = eng.tjs("return KAGLanguage.current;")
        print("     the system's language here: %s (System.uiLanguage \"%s\", candidates %s)"
              % (shown, eng.tjs("return System.uiLanguage;"),
                 eng.tjs('return System.uiLanguageCandidates.join(",");')), flush=True)
        if shown != "en":
            eng.tjs('kag.setLanguage("en"); return 1;')
        switch_language(eng, "en", "title.ks")

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
        # what A left (SceneParser.entryFor), as playing the scripts would. Android's save folder
        # doesn't serve scripts through the auto path: "skip"
        r = str(eng.tjs(r'''
            var dir = System.dataPath;
            [ "*start|Carry A", "[initscene]", "[road normal]", "[ai standard center]", "Ai is here.[p]",
              "[jump storage=zz_carry_b.ks]" ].save(dir + "zz_carry_a.ks");
            [ "*start|Carry B", "Still here.[p]" ].save(dir + "zz_carry_b.ks");
            try { Storages.addAutoPath(dir); } catch (e) { }
            if (!Storages.isExistentStorage("zz_carry_a.ks") || !Storages.isExistentStorage("zz_carry_b.ks")) return "skip";
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
        if r == "skip":
            print("     (skipped: the save folder isn't a script folder here)", flush=True)
            return
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
        # (wrapText, the line as drawn, since 0.12.0; wrapSplitLine, its words, before)
        r = str(eng.tjs('var t = world_object.player.curText.text, w = typeof kag.wrapText != "undefined"'
                        ' ? (kag.wrapText != "" ? kag.wrapText.split(" ").count : -1)'
                        ' : kag.wrapSplitLine !== void ? kag.wrapSplitLine.count : -1;'
                        ' return [kag.wrapKey, w, t.split(" ").count, t].join("|");'))
        key, words, expected, text = r.split("|", 3)
        if not key.startswith("scene:") or words != expected:
            raise SmokeError("the word wrap didn't take the compiled text (%s): %s" % (r, text))

    @step("English lines break between words, where krkr_richtext draws as its line breaker plans them")
    def _():
        if eng.tjs('return typeof kag.saveWordWrap != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's word wrap predates the line breaking plan)", flush=True)
            return
        clean = eng.tjs('return kag.wrapCleanLine("\\t[ai face=smile]【ai】Hello there,[r]friend [[1].");')
        if clean != "Hello there,\nfriend [1].":
            raise SmokeError("a scenario line with tags isn't read as it's drawn: %r" % clean)
        eng.tjs(WRAP_TJS + "return 1;")
        para = ("Kirikiri Z draws this message with krkr_richtext, which lays out text with minikin: its line"
                " breaker looks at the whole paragraph, so lines come out more even than when each one is"
                " filled as far as it goes.")
        steps = " ".join("Step %d of a long passage goes on for a few words more." % i for i in range(1, 21))
        cases = [(para, how, -1, 20) for how in ("greedy", "quality", "balanced")]
        cases += [(para, "quality", 900, 20), (para + "\n" + para, "balanced", -1, 20), (steps, "quality", 600, 3)]
        for text, how, start, lines in cases:
            r = json.loads(str(eng.tjs("return __smokeWrap(%s, \"%s\", %d, %d);" % (tjs_string(text), how, start, lines))))
            if r.get("error"):
                raise SmokeError("the word wrap failed: %s" % r["error"])
            drawn = [l.get("text") or "" for l in r.get("lines") or []]
            what = "%s from %s, %d lines a page" % (how, "the line's start" if start < 0 else "x %d" % start, lines)
            print("     %s: %d lines, %d page(s), %s" % (what, len(drawn), r.get("pages", 0),
                  "planned by krkr_richtext" if r.get("planning") else "a word at a time"), flush=True)
            if " ".join(" ".join(drawn).split()) != " ".join(text.split()):
                raise SmokeError("%s: words were split or lost: %s" % (what, drawn))
            for l in r["lines"]:
                if (l.get("text") or "").startswith(" ") or l.get("kag"):
                    raise SmokeError("%s: a line starts with a space, or KAG's character wrap broke it: %s" % (what, drawn))
                if (l.get("text") or "").strip() != "" and l.get("end", 0) >= r.get("limit", 0):
                    raise SmokeError("%s: a line runs past %s: %s" % (what, r.get("limit"), l))
            if r.get("rich") and not r.get("planning"):
                raise SmokeError("%s: krkr_richtext draws the text, but didn't plan its lines" % what)
            if "\n" in text and not any(drawn[i].rstrip().endswith("goes.") and drawn[i + 1].startswith("Kirikiri")
                                        for i in range(len(drawn) - 1)):
                raise SmokeError("%s: the new line isn't where the text has it: %s" % (what, drawn))
            if lines == 3 and r.get("pages", 0) < 1:
                raise SmokeError("%s: the text didn't fill a page: %s" % (what, drawn))

    @step("Japanese lines break where krkr_richtext's line breaker plans them, with its rules for Japanese")
    def _():
        # (since 0.12.1; KAG's own character wrap before, and where krkr_richtext doesn't draw)
        if eng.tjs('return typeof kag.wrapBeforeWord != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's Japanese keeps KAG's character wrap)", flush=True)
            return
        eng.tjs(WRAP_TJS + "return 1;")
        latin = "\u3042" * 30 + "\u3053\u308c\u306fREADMEFILE\u306e\u8aac\u660e\u3067\u3059\u3002" * 4
        # each: the text, where it starts, a character no line may start with, one no line may end with
        cases = [("\u3042\u3002" * 60, -1, "\u3002", None),    # a full stop
                 ("\u3042\u300c\u3044\u300d" * 30, -1, "\u300d", "\u300c"),  # brackets
                 ("\u304d\u3083" * 60, -1, "\u3083", None),    # a small kana
                 (latin, -1, None, None), (latin, 900, None, None)]
        for text, start, nostart, noend in cases:
            r = json.loads(str(eng.tjs("return __smokeWrap(%s, \"quality\", %d, 20, 0);" % (tjs_string(text), start))))
            if r.get("error"):
                raise SmokeError("the line breaking failed: %s" % r["error"])
            drawn = [l.get("text") or "" for l in r.get("lines") or []]
            what = "%r... from %s" % (text[:6], "the line's start" if start < 0 else "x %d" % start)
            print("     %s: %d lines (%s), %s" % (what, len(drawn), ", ".join(str(len(l)) for l in drawn),
                  "planned by krkr_richtext" if r.get("planning") else "KAG's character wrap"), flush=True)
            if "".join(drawn) != text:
                raise SmokeError("%s: characters were lost: %s" % (what, drawn))
            if not r.get("rich"):
                continue
            if not r.get("planning"):
                raise SmokeError("%s: krkr_richtext draws the text, but didn't plan its lines" % what)
            for i, l in enumerate(r["lines"]):
                t = l.get("text") or ""
                if l.get("kag"):
                    raise SmokeError("%s: KAG's character wrap broke a line the plan had: %s" % (what, drawn))
                if t != "" and l.get("end", 0) >= r.get("limit", 0):
                    raise SmokeError("%s: a line runs past %s: %s" % (what, r.get("limit"), l))
                if nostart and i > 0 and t.startswith(nostart):
                    raise SmokeError("%s: a line starts with %r: %s" % (what, nostart, drawn))
                if noend and i < len(drawn) - 1 and t.endswith(noend):
                    raise SmokeError("%s: a line ends with %r: %s" % (what, noend, drawn))
            if "READMEFILE" in text and sum(l.count("READMEFILE") for l in drawn) != text.count("READMEFILE"):
                raise SmokeError("%s: a word in Latin letters was split: %s" % (what, drawn))

    @step("krkr_richtext draws a line's characters together, where KAG put them")
    def _():
        # (useStyledLayout, since 0.12.1)
        if eng.tjs('return typeof MessageLayer.drawStyledRun != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build draws a character at a time)", flush=True)
            return
        eng.tjs(STYLED_TJS + "return 1;")
        text = "AVAWAY Tolkien's office: fi fl ffi, cafe\u0301, nai\u0308ve, \u4e8c\u884c\u76ee\u3002 HHH"
        runs = json.loads(str(eng.tjs("return __smokeStyled(%s, 1);" % tjs_string(text))))
        each = json.loads(str(eng.tjs("return __smokeStyled(%s, 0);" % tjs_string(text))))
        for r in (runs, each):
            if r.get("error"):
                raise SmokeError("drawing the text failed: %s" % r["error"])
        if not runs.get("rich"):
            print("     (skipped: krkr_richtext doesn't draw here)", flush=True)
            return
        print("     %d run(s); ink to x %d (%d) together, %d (%d) a character at a time" % (
            runs.get("runs", 0), runs.get("right", -1), runs.get("ink", 0), each.get("right", -1), each.get("ink", 0)),
            flush=True)
        if runs.get("runs", 0) < 1 or each.get("runs", 0) != 0:
            raise SmokeError("useStyledLayout didn't choose how the text is drawn: %s, %s" % (runs, each))
        if runs.get("xs") != each.get("xs"):
            raise SmokeError("the characters went elsewhere: %s against %s" % (runs.get("xs"), each.get("xs")))
        if abs(runs.get("right", -1) - each.get("right", -1)) > 3 or each.get("right", -1) < 0:
            raise SmokeError("the line drawn together doesn't reach as far (its last character is missing?):"
                             " x %s against %s" % (runs.get("right"), each.get("right")))
        if not 0.85 * each.get("ink", 0) <= runs.get("ink", 0) <= 1.15 * each.get("ink", 0):
            raise SmokeError("the line drawn together has %s of ink against %s" % (runs.get("ink"), each.get("ink")))

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
        # while it plays (asking through the REPL is too slow on some targets). Pip's babble has
        # no lip track, so its mouth opens and shuts by loudness alone: no vowel mouths
        eng.tjs('global.__smokeLips = [], global.__smokeVoice = [], global.__smokeVowels = %[];'
                ' global.__smokeLipTimer = new Timer(function() {'
                ' var c = world_object.env.characters["pip"], b = c !== void ? c.soundBuffer : void;'
                ' if (b !== void && b.status == "play") { global.__smokeLips.add(c.lipLevel); global.__smokeVoice.add(b.position);'
                ' if (typeof c.lipVowel != "undefined" && c.lipVowel !== void) global.__smokeVowels[c.lipVowel] = 1; }'
                ' }, ""); __smokeLipTimer.interval = 20; __smokeLipTimer.enabled = true; return 1;')
        eng.tjs('kag.onPrimaryClick(); return 1;')
        end = time.time() + 6
        while time.time() < end:
            time.sleep(0.5)
            if eng.tjs('return __smokeLips.count > 0 && world_object.env.characters["pip"].soundBuffer.status != "play" ? 1 : 0;') == 1:
                break
        r = str(eng.tjs('__smokeLipTimer.enabled = false; invalidate __smokeLipTimer;'
                        ' var p = %[]; for (var i = 0; i < __smokeVoice.count; i++) p[__smokeVoice[i]] = 1;'
                        ' var n = []; n.assign(p); var v = []; v.assign(__smokeVowels); var vs = [];'
                        ' for (var i = 0; i < v.count; i += 2) vs.add(v[i]);'
                        ' var c = world_object.env.characters["pip"];'
                        ' return [__smokeLips.join(" "), n.count \\ 2, lipSyncSource, vs.join(" "),'
                        ' typeof global.lipEngineVowels != "undefined" && lipEngineVowels ? 1 : 0,'
                        ' typeof c.lipTrack == "undefined" ? -1 : c.lipTrack !== void ? c.lipTrack.times.count : 0].join(",");')).split(",")
        levels = [int(v) for v in r[0].split()] if r[0].strip() else []
        positions, source = int(r[1]), r[2]
        vowels, engine_vowels, track = r[3].split(), r[4] == "1", int(r[5])
        print("     lip-sync from %s: %d mouth samples while the voice played (%s), at %d positions"
              % ("its lip track (%d marks)" % track if track > 0 else source or "(random)", len(levels),
                 " ".join(str(v) for v in levels[:60]), positions), flush=True)
        if positions <= 1:
            print("     (the voice doesn't play here, so the mouth isn't checked)", flush=True)
        elif not {0, 2} <= set(levels):
            raise SmokeError("Pip's mouth didn't open and close with its voice (levels seen: %s)" % sorted(set(levels)))
        elif track == 0 and not engine_vowels and vowels:
            raise SmokeError("Pip's babble has no lip track, but its mouth made vowels (%s)" % " ".join(sorted(vowels)))
        # its one synthesized line (anim.ks, voice=9) has a lip track kagex-lipsync made from the
        # voice and its text (pip000009.lip): its mouths follow the track's vowels
        speech = eng.tjs('return typeof world_object.env.characters["pip"].lipTrackAt != "undefined"'
                         ' && (Storages.isExistentStorage("pip000009.ogg") || Storages.isExistentStorage("pip000009.opus")) ? 1 : 0;') == 1
        if speech and eng.tjs('return Storages.isExistentStorage("pip000009.lip") ? 1 : 0;') != 1:
            raise SmokeError("Pip's synthesized line (pip000009) has no lip track here (pip000009.lip)")
        if positions > 1 and speech:
            eng.tjs('global.__smokeVowels2 = %[]; global.__smokeLips3 = [];'
                    ' global.__smokeLipTimer3 = new Timer(function() {'
                    ' var c = world_object.env.characters["pip"], b = c.soundBuffer;'
                    ' if (b !== void && b.status == "play") { global.__smokeLips3.add(c.lipLevel);'
                    ' if (c.lipVowel !== void) global.__smokeVowels2[c.lipVowel] = 1; }'
                    ' }, ""); __smokeLipTimer3.interval = 20; __smokeLipTimer3.enabled = true;'
                    ' world_object.env.characters["pip"].playVoice("pip000009"); return 1;')
            end = time.time() + 14
            seen = []
            while time.time() < end:
                time.sleep(0.5)
                seen = str(eng.tjs('var v = []; v.assign(__smokeVowels2); var vs = []; for (var i = 0; i < v.count; i += 2) vs.add(v[i]); return vs.join(" ");')).split()
                if len(seen) >= 3 or eng.tjs('return __smokeLips3.count > 0 && world_object.env.characters["pip"].soundBuffer.status != "play" ? 1 : 0;') == 1:
                    break
            r = str(eng.tjs('__smokeLipTimer3.enabled = false; invalidate __smokeLipTimer3; var c = world_object.env.characters["pip"];'
                            ' var said = %[]; if (c.lipTrack !== void) for (var i = 0; i < c.lipTrack.mouths.count; i++) said[c.lipTrack.mouths[i]] = 1;'
                            ' var s = []; s.assign(said); var ss = []; for (var i = 0; i < s.count; i += 2) ss.add(s[i]);'
                            ' c.soundBuffer.stop();'
                            ' return [c.lipTrack === void ? 0 : c.lipTrack.times.count, ss.join(" "), __smokeLips3.count].join(",");')).split(",")
            marks, said = int(r[0]), set(r[1].split()) & set("aiueo")
            print("     its synthesized line: a lip track of %d marks; vowel mouths shown: %s" % (marks, " ".join(sorted(seen)) or "none"), flush=True)
            if marks == 0:
                raise SmokeError("pip000009.lip wasn't read for Pip's synthesized line")
            if len(seen) < 2 or not set(seen) <= said:
                raise SmokeError("Pip's mouth didn't follow pip000009.lip's vowels (%s; seen: %s)" % (" ".join(sorted(said)), " ".join(sorted(seen)) or "none"))
        # a voice with no lip track (Ai's, said by Pip): its level read where the clock says it
        # is playing (KAGEnvCharacterEyeLip.readVoice), the mouth opening and closing with it
        if positions > 1 and eng.tjs('return typeof world_object.env.characters["pip"].readVoice != "undefined" ? 1 : 0;') == 1:
            eng.tjs('global.__smokeLips2 = []; var c = world_object.env.characters["pip"];'
                    ' global.__smokeLipTimer2 = new Timer(function() {'
                    ' var c = world_object.env.characters["pip"], b = c.soundBuffer;'
                    ' if (b !== void && b.status == "play") global.__smokeLips2.add(c.lipLevel);'
                    ' }, ""); __smokeLipTimer2.interval = 20; __smokeLipTimer2.enabled = true;'
                    ' c.playVoice("ai000001"); return 1;')
            end = time.time() + 8
            while time.time() < end:
                time.sleep(0.5)
                if eng.tjs('return __smokeLips2.count > 0 && world_object.env.characters["pip"].soundBuffer.status != "play" ? 1 : 0;') == 1:
                    break
            r = str(eng.tjs('__smokeLipTimer2.enabled = false; invalidate __smokeLipTimer2; var c = world_object.env.characters["pip"];'
                            ' return [__smokeLips2.join(" "), c.lipTrack === void ? 1 : 0, c.lipReadings !== void && c.lipReadings.last !== void ? 1 : 0].join(",");')).split(",")
            levels2 = [int(v) for v in r[0].split()] if r[0].strip() else []
            print("     a voice with no lip track: %d mouth samples (%s)" % (len(levels2), " ".join(str(v) for v in levels2[:60])), flush=True)
            if r[1] != "1" or r[2] != "1" or not ({0} < set(levels2)):
                raise SmokeError("Pip's mouth didn't follow a voice with no lip track (levels %s, no track %s, read %s)"
                                 % (sorted(set(levels2)), r[1], r[2]))
        eng.clicker(True, until="s0001.ks")
        eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks"', timeout=180)
        eng.clicker(False)

    @step("a Live2D character draws, moves, blinks and lip-syncs (--live2d required), or does with the stand-in plugin")
    def _():
        live2d_steps(eng)

    @step("a VRM character draws, moves, blinks and lip-syncs (--three required)")
    def _():
        vrm_steps(eng)

    @step("3D on layers: a VRM avatar, a glTF model and a scene built in script (the 3d flip)")
    def _():
        three_flip_steps(eng)

    @step("a character's layers read from a PSD match its layer structure, vowel mouths included")
    def _():
        if not isinstance(eng, DesktopEngine) or not animated_framework(eng):
            print("     (skipped: it writes a PSD beside a desktop engine's save data)", flush=True)
            return
        if eng.tjs('return typeof global.findStandLayerFile != "undefined" && typeof global.allStandInfoMap != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates characters from PSD files)", flush=True)
            return
        if eng.tjs('if (typeof global.PSD == "undefined") { try { Plugins.link("plugin/psdfile.dll"); } catch (e) {} }'
                   ' return typeof global.PSD != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: no psdfile plugin)", flush=True)
            return
        # Pip's pose at level "0" (data/fgimage/pip/pip_0.txt and its pictures), written as a PSD
        # with folders (tools/assets/psdwrite.py), as smokepip_0.psd in the save folder: then
        # findStandLayerFile finds the PSD for "smokepip_0", which has no .txt
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
        import psdwrite
        pip = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "fgimage", "pip", "pip_0.txt")
        psdwrite.structure_to_psd(pip, os.path.join(eng.savedir, "smokepip_0.psd"))
        r = str(eng.tjs(
            'var base = "%s"; var found = findStandLayerFile(base + "_0");'
            ' var info = %%[]; (Dictionary.assign incontextof info)(allStandInfoMap.pip.map.standard); info.filename = base;'
            ' var levels = [%%[name:"0"]], a = new StandPSDInfo(kag, info, 0, levels),'
            ' b = new StandPSDInfo(kag, allStandInfoMap.pip.map.standard, 0, levels);'
            ' var structure = 0;'
            ' if (a.layers.count != b.layers.count || a.groups.count != b.groups.count) structure = -1;'
            ' else for (var i = 0; i < a.layers.count; i++) { var x = a.layers[i], y = b.layers[i];'
            ' if (x.name != y.name || x.layer_id != y.layer_id || x.left != y.left || x.top != y.top || x.group_layer_id != y.group_layer_id) structure++; }'
            ' var res = [];'
            ' for (var v = 0; v < 2; v++) { var ls = [];'
            ' for (var k = 0; k < 2; k++) { var l = new StandLayer(kag, k ? b : a, "standard", 0);'
            ' l.setDress("plain"); l.setDiff("rest"); l.setLipLevel(2); l.setLipVowel(v ? "o" : void); l.setEyeLevel(2);'
            ' l.setFace("neutral"); l.updateImage(); ls.add(l); }'
            ' var d = 0, n = 0; for (var y = 0; y < ls[0].imageHeight; y += 3) for (var x = 0; x < ls[0].imageWidth; x += 3) {'
            ' n++; if (ls[0].getMainPixel(x, y) != ls[1].getMainPixel(x, y) || ls[0].getMaskPixel(x, y) != ls[1].getMaskPixel(x, y)) d++; }'
            ' res.add([d, n, ls[0].getVisible("Mouth/Mouth O") ? 1 : 0, ls[0].getVisible("Mouth/Open Mouth") ? 1 : 0].join(" "));'
            ' invalidate ls[0]; invalidate ls[1]; }'
            ' var count = a.layers.count; invalidate a; invalidate b;'
            ' return [found, count, structure, res[0], res[1]].join(",");' % storage_name(os.path.join(eng.savedir, "smokepip"))))
        found, count, structure, plain, vowel = r.split(",")
        print("     found %s: %s layers, %s differing from pip_0.txt" % (found.rsplit("/", 1)[-1], count, structure), flush=True)
        d0, n0, o0, open0 = [int(v) for v in plain.split()]
        d1, n1, o1, open1 = [int(v) for v in vowel.split()]
        print("     composited: %d of %d samples differ with the open mouth, %d of %d with the O mouth" % (d0, n0, d1, n1), flush=True)
        if not found.endswith(".psd") or structure != "0" or int(count) < 40:
            raise SmokeError("the PSD didn't read as Pip's layer structure: %s" % r)
        if d0 or d1:
            raise SmokeError("Pip drawn from the PSD doesn't look as drawn from pip_0.txt: %s" % r)
        if not (open0 and not o0 and o1 and not open1):
            raise SmokeError("the vowel mouth didn't replace the open mouth (open %d/%d, O %d/%d)" % (open0, open1, o0, o1))
        # psd:// (what a KAG or World layer loads, AffineLayer.tjs): from the PSD through psdfile
        # (by folder and name, and by ID), and from a split layer structure, pip_0.txt, as if
        # pip_0.psd had been split (Mouth O is 47); the clip:// step shows such a layer drawn
        r = str(eng.tjs(
            'var dir = "%s/"; Storages.addAutoPath(dir); var res = [];'
            ' var want = new global.Layer(kag, kag.primaryLayer); want.loadImages("pip_0_47");'
            ' var names = ["psd://smokepip_0.psd/root/mouth/mouth o.bmp", "psd://smokepip_0.psd/id/47.bmp", "psd://pip_0.psd/root/Mouth/Mouth O.bmp"];'
            ' for (var i = 0; i < names.count; i++) { var d = -1, t = new global.Layer(kag, kag.primaryLayer);'
            ' try { affineLoadLayeredLayer(t, names[i]);'
            ' if (t.imageWidth == want.imageWidth && t.imageHeight == want.imageHeight) { d = 0;'
            ' for (var y = 0; y < t.imageHeight; y++) for (var x = 0; x < t.imageWidth; x++)'
            ' if (t.getMaskPixel(x, y) != want.getMaskPixel(x, y) || (want.getMaskPixel(x, y) && t.getMainPixel(x, y) != want.getMainPixel(x, y))) d++; }'
            ' else dm("psd:// " + names[i] + ": " + t.imageWidth + "x" + t.imageHeight + ", not " + want.imageWidth + "x" + want.imageHeight);'
            ' } catch (e) { dm("psd:// " + names[i] + ": " + e.message); }'
            ' invalidate t; res.add(d); }'
            ' invalidate want; Storages.removeAutoPath(dir);'
            ' return res.join(",");' % storage_name(eng.savedir)))
        print("     psd:// Mouth O differs in %s pixels (by name, by ID, from the split pip_0.txt; -1: didn't load)" % r, flush=True)
        if r != "0,0,0":
            raise SmokeError("psd:// didn't load the layer: %s" % r)

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

    @step("a movie named without its extension is found as .webm, the format the engine plays")
    def _():
        found = str(eng.tjs('if (!Storages.isExistentStorage("test.webm")) return "none";'
                            ' return [GenericFlip.GetType("test.webm"), GenericFlip.GetType("test"),'
                            ' Storages.extractStorageName(getExistFileNameAutoExtFill("test", GenericFlip.GetEntry("movie", "ext")*))].join(",");'))
        if found == "none":
            print("     (skipped: no video/test.webm here)", flush=True)
            return
        if found != "movie,movie,test.webm":
            raise SmokeError("test.webm and test are taken as %s, not movie,movie,test.webm" % found)

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
        # from emblem.clip through the clipfile plugin, or, in a build kagex-release made, from the
        # pictures it split the file into (emblem.txt and emblem_<layer id>), with or without it
        split = eng.tjs('return typeof global.affineLoadLayeredLayer != "undefined"'
                        ' && Storages.isExistentStorage("emblem.txt") && !Storages.isExistentStorage("emblem.clip") ? 1 : 0;') == 1
        if not split and eng.tjs('return typeof global.CLIP != "undefined" ? 1 : 0;') != 1:
            if eng.opts.clip == "required":
                raise SmokeError("clip:// images are unavailable: no clipfile plugin")
            print("     clip://: unavailable (no clipfile plugin)", flush=True)
            return
        print("     from %s" % ("the pictures kagex-release split emblem.clip into" if split else "emblem.clip, through clipfile"), flush=True)
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

    @step("screen readers: the demo menu's choices are a list, one picked through it plays, and its text is read")
    def _():
        if not a11y_framework(eng):
            print("     (skipped: no screen reader interface here, or a framework without it)", flush=True)
            return
        eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks" && kag.inStable', timeout=20)
        a11y_find(eng, "list", "Choices")
        choice = a11y_find(eng, "list_item", "World Extension: Character")
        _, since = a11y_said(eng, 0)
        a11y_click(eng, choice)
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable && kag.clickWaiting', timeout=30)
        first = "This is a scripting sample using KAGEX World Extension."
        end = time.time() + 5
        while True:
            said, _ = a11y_said(eng, since)
            if any(first in l for l in said):
                break
            if time.time() > end:
                raise SmokeError("the first text wasn't read out: %s" % said[-6:])
            time.sleep(0.2)

    @step("save and load a bookmark")
    def _():
        # the web build's saves go where the browser keeps them (/persist), not to SDL's user://
        # in the page's memory, which went with the page
        place = str(eng.tjs('return [typeof System.platformTag != "undefined" ? System.platformTag : "", kag.saveDataLocation].join(" ");'))
        if place.startswith("web ") and "file://./persist/" not in place and eng.tjs('return typeof kag.saveDataFile != "undefined" ? 1 : 0;') == 1:
            raise SmokeError("the web build saves to %s, which the browser doesn't keep" % place.split(" ", 1)[1])
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
    interface_steps(eng, step)

    @step("the controls list has the sample's own keys and buttons (AfterInit.tjs)")
    def _():
        if not elements_screens(eng):
            return
        sections = controls_list(eng)
        for key, action in (("F1", "About"), ("F2", "Save"), ("F3", "Load"), ("F4", "Config"),
                            ("F6", "Skip to the next choice or unread text"), ("F7", "Message history"), ("F8", "Auto mode on or off")):
            got = controls_action(sections, "Keyboard", key)
            if got != action:
                raise SmokeError("the controls list says %s is %s, not %s" % (key, got, action))
        names = json.loads(str(eng.tjs("return Scripts.toJSONString(KAGPadButtonNames().shown);")))
        for button, action in ((10, "Config"), (9, "Save"), (5, "Load")):
            got = controls_action(sections, "Controller", names[button - 1])
            if got != action:
                raise SmokeError("the controls list says %s is %s, not %s" % (names[button - 1], got, action))

    @step("positional sound: an SE placed at the stage's far left or right is panned there (World pos=, xpos=)")
    def _():
        if eng.tjs('return typeof world_object.env.se3DPosition != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates positional sound)", flush=True)
            return
        if eng.tjs('return typeof kag.se[0].use3D != "undefined" && typeof global.SoundListener != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this engine has no 3D sound)", flush=True)
            return
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        got = []
        for attrs in ('pos:"farleft"', 'pos:"farright"', 'xpos:"0"', ''):
            got.append(str(eng.tjs('var env = world_object.env, i = env.getSeId(void);'
                                   ' world_object.onUnknown("se", %%[tagname:"se", buf:"" + i, storage:"se_chime"%s]);'
                                   ' var b = env.getSEOBJ(i);'
                                   ' return b.use3D ? "%%.2f".sprintf(b.posX) : "off";' % ((", " + attrs) if attrs else ""))))
        print("     x: far left %s, far right %s, xpos=0 %s, unplaced %s" % tuple(got), flush=True)
        try:
            left, right, mid = float(got[0]), float(got[1]), float(got[2])
        except ValueError:
            raise SmokeError("a placed sound isn't positional: %s" % got)
        if not (left < -0.5 and right > 0.5 and abs(mid) < 0.01) or got[3] != "off":
            raise SmokeError("the sounds aren't where they were put: %s" % got)

    @step("World sound: pitch= and pan= move the music and a sound over time=, a play starts as recorded, a save keeps them")
    def _():
        if eng.tjs('return typeof global.KAGEnvSoundShift != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates pitch and pan)", flush=True)
            return
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        bgm = 'var b = kag.bgm.currentBuffer, w = world_object.env.bgm; '
        base = eng.tjs('world_object.onUnknown("bgm", %[tagname:"bgm", storage:"bgm01", loop:"true"]);'
                       ' return kag.bgm.currentBuffer.frequency;')
        try:
            eng.tjs('world_object.onUnknown("bgm", %[tagname:"bgm", pitch:"50", pan:"-80", time:"1500"]); return 1;')
            mid = [int(v) for v in str(eng.tjs(bgm + 'return [b.frequency, w.shift.moving ? 1 : 0].join(",");')).split(",")]
            eng.wait("the change to end", "!world_object.env.bgm.shift.moving", timeout=10)
            end = str(eng.tjs(bgm + 'var d = %[]; w.onStore(d); return [b.frequency, b.pan, d.pitch, d.pan].join(",");'))
            print("     the music at %s Hz, then %s Hz (%s), then %s" % (base, mid[0], "moving" if mid[1] else "already there", end), flush=True)
            want = "%d,-80000,50,-80" % (base // 2)
            if end != want or (mid[1] and not (base // 2 < mid[0] <= base)):
                raise SmokeError("pitch=50 pan=-80 time=1500 didn't take the music to %s: %s, %s" % (want, mid, end))
            # the same track played again: as recorded and centred, at once
            again = str(eng.tjs('world_object.onUnknown("bgm", %[tagname:"bgm", storage:"bgm01", loop:"true"]); ' + bgm
                                + 'var d = %[]; w.onStore(d); return [b.frequency, b.pan, d.pitch === void ? 1 : 0].join(",");'))
            if again != "%d,0,1" % base:
                raise SmokeError("playing the music again didn't put it back as recorded: %s" % again)
            # a sound starts at the pitch and pan its play tag gives, and is centred when it stops
            se = str(eng.tjs('var e = world_object.env, i = e.getSeId(void); global.__smokeShiftSe = i;'
                             ' world_object.onUnknown("se", %[tagname:"se", buf:"" + i, storage:"se_steps", loop:"true"]);'
                             ' var b = kag.se[i], f0 = b.frequency;'
                             ' world_object.onUnknown("se", %[tagname:"se", buf:"" + i, storage:"se_steps", loop:"true", pitch:"150", pan:"60"]);'
                             ' var d = %[]; e.ses[i].onStore(d); var r = [f0, b.frequency, b.pan, d.pitch, d.pan];'
                             ' world_object.onUnknown("se", %[tagname:"se", buf:"" + i, stop:"0"]); r.add(b.pan); return r.join(",");')).split(",")
            print("     a sound at %s Hz, with pitch=150 pan=60 at %s Hz and pan %s (saved %s, %s), centred when it stops: %s" % tuple(se), flush=True)
            if int(se[1]) != int(int(se[0]) * 1.5) or se[2:] != ["60", "150", "60", "0"]:
                raise SmokeError("the sound didn't start at pitch=150 pan=60: %s" % se)
            # a sound named by name= (as the demos stop their footsteps), panned, then stopped: the
            # name only says which sound (up to 0.14.0 the SE also took it for a file to play)
            named = str(eng.tjs('var e = world_object.env, i = e.getSeId(void), r = [];'
                                ' world_object.onUnknown("se", %[tagname:"se", buf:"" + i, storage:"se_steps", loop:"true"]);'
                                ' world_object.onUnknown("se", %[tagname:"se", name:"se_steps", pan:"-100"]);'
                                ' r.add(kag.se[i].status); r.add(e.ses[i].filename); r.add(kag.se[i].pan);'
                                ' world_object.onUnknown("se", %[tagname:"se", name:"se_steps", stop:"0"]);'
                                ' r.add(kag.se[i].status); r.add(e.ses[i].filename === void ? "-" : e.ses[i].filename); return r.join(",");'))
            if named != "play,se_steps,-100,stop,-":
                raise SmokeError("[se name=se_steps pan=-100] and [se name=se_steps stop=0] didn't pan and stop that sound: %s" % named)
        finally:
            eng.tjs('world_object.onUnknown("bgm", %[tagname:"bgm", stop:"0"]); return 1;')

    @step("TV static: the static flip draws new static every frame, on a KAG layer and a World layer, and a save keeps it")
    def _():
        if eng.tjs('return typeof global.StaticFlip != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the static flip)", flush=True)
            return
        # the flip's own picture (a KAG layer's pixels read its source): samples' mean, how many
        # changed since the last look, whether all are opaque, and whether any is coloured
        look = ('var p = [], o = 1, s = 0, c = 0; for (var y = 4; y < f.imageHeight; y += 37) for (var x = 3; x < f.imageWidth; x += 41)'
                ' { var v = f.getMainPixel(x, y); p.add(v); s += v & 0xff; if (f.getMaskPixel(x, y) != 255) o = 0;'
                ' if (((v >> 16) & 0xff) != (v & 0xff)) c++; }'
                ' var last = global.__smokeNoise, d = 0; if (last !== void) for (var i = 0; i < p.count; i++) if (p[i] != last[i]) d++;'
                ' global.__smokeNoise = p; return [f.frames, p.count, s \\ p.count, d, o, c].join(",");')
        kag_flip = 'var l = kag.fore.layers[0], f = l.flip; '
        eng.tjs('global.__smokeNoise = void; kag.tagHandlers.image(%[layer:"0", page:"fore", flip:"static", visible:"true",'
                ' staticbar:"60", staticlines:"80"]); return 1;')
        first = [int(v) for v in str(eng.tjs(kag_flip + 'if (l.flipType != "static" || f === void) return "0,0,0,0,0,0"; ' + look)).split(",")]
        time.sleep(0.6)
        later = [int(v) for v in str(eng.tjs(kag_flip + look)).split(",")]
        print("     on a KAG layer: %d frames in 0.6 s, mean %d, %d of %d samples changed, opaque %d"
              % (later[0] - first[0], later[2], later[3], later[1], later[4]), flush=True)
        if first[0] < 1 or later[0] - first[0] < 3 or later[3] < later[1] // 2 or later[4] != 1 or not 30 < later[2] < 225:
            raise SmokeError("[image flip=static] isn't drawing new opaque static every frame: %s, %s" % (first, later))
        # colour and a coarser grain through [layopt]; kept through a store and a restore
        colour = eng.tjs(kag_flip + 'return typeof f.grain.noise != "undefined" ? 1 : 0;') == 1
        eng.tjs('kag.tagHandlers.layopt(%[layer:"0", page:"fore", staticcolor:"true", staticgrain:"8"]); return 1;')
        time.sleep(0.3)
        r = [int(v) for v in str(eng.tjs(kag_flip + look)).split(",")]
        grain = eng.tjs(kag_flip + 'return f.grain.imageWidth;')
        if (colour and r[5] < r[1] // 2) or grain != (eng.tjs("return kag.fore.layers[0].flip.canvasWidth;") + 7) // 8:
            raise SmokeError("staticcolor and staticgrain=8 didn't reach the flip: %s, grain %s wide" % (r, grain))
        eng.tjs(kag_flip + 'global.__smokeFlipStore = %[]; l.storeFlip(__smokeFlipStore); kag.tagHandlers.freeimage(%[layer:"0", page:"fore"]);'
                ' l.restoreFlip(__smokeFlipStore); l.visible = true; return 1;')
        time.sleep(0.3)
        r = str(eng.tjs(kag_flip + 'return [l.flipType, f.options.staticbar, f.options.staticgrain, f.options.staticcolor, f.frames > 1 ? 1 : 0].join(",");'))
        if r != "static,60,8,true,1":
            raise SmokeError("the static flip wasn't restored as it was stored: %s" % r)
        hit = str(eng.tjs('var l = kag.fore.layers[0], r = [l.hitThreshold]; kag.tagHandlers.freeimage(%[layer:"0", page:"fore"]);'
                          ' r.add(l.hitThreshold); return r.join(",");'))
        if hit.split(",")[0] != "256" or hit.split(",")[1] == "256":
            raise SmokeError("a layer showing static should let the pointer through and get its own hitThreshold back: %s" % hit)
        # on a World layer over the message window (level=message): newlay static=, flipupdate,
        # and a redraw that keeps the same flip going
        wl = 'world_object.env.layers["smokestatic"]'
        env = 'var e = world_object.env, t = ' + wl + '.targetLayer, f = t.flip; '
        eng.tjs('world_object.env.unknown("newlay", %[name:"smokestatic", "static" => "tv", staticgrain:"4", opacity:"128", level:"message", show:"true"]); return 1;')
        eng.wait("the World layer's static", wl + ' !== void && ' + wl + '.targetLayer !== void && ' + wl + '.targetLayer.flip !== void && '
                 + wl + '.targetLayer.flip.frames > 3', timeout=10)
        eng.tjs(env + 'global.__smokeFlipObj = f; e.unknown("smokestatic", %[flipupdate:"true", staticfps:"10"]);'
                ' e.unknown("smokestatic", %[grayscale:"true"]); return 1;')
        time.sleep(0.5)
        r = str(eng.tjs(env + 'var m = kag.fore.messages; return [t.flipType, f === global.__smokeFlipObj ? 1 : 0, f.options.staticfps, f.grainSize,'
                        ' f.canvasWidth == kag.primaryLayer.width ? 1 : 0,'
                        ' t.absolute > m[0].absolute && (m.count < 2 || t.absolute < m[1].absolute) && t.hitThreshold == 256 ? 1 : 0].join(",");'))
        print("     on a World layer: %s" % r, flush=True)
        eng.tjs('global.__smokeFlipObj = void; world_object.env.delLayer(%[name:"smokestatic"]); world_object.env.destroy(); return 1;')
        if r != "static,1,10,4,1,1":
            raise SmokeError("[newlay static=tv level=message] didn't play on as asked through flipupdate and a redraw,"
                             " over the message window and letting the pointer through: %s" % r)

    @step("Config's option pages: rows drawn from the options table, a pick sets the option, Default puts them back")
    def _():
        if eng.tjs('return typeof global.KAGOptionPage != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the options table)", flush=True)
            return
        eng.tjs('kag.process("config.ks", "*startFromTitle"); return 1;')
        eng.wait("config.ks", 'kag.conductor.curStorage == "config.ks" && kag.inStable', timeout=20)
        for page in (2, 3):
            eng.tjs("setConfigPage(%d); return 1;" % page)
            eng.wait("page %d" % page, "tf.configPage == %d && kag.inStable && typeof kag.current.optionControls == \"Object\"" % page, timeout=20)
            n = str(eng.tjs('var a = []; a.assign(kag.current.optionControls); return [a.count \\ 2, kag.current.numLinks].join(",");'))
            print("     page %d: %s options, %s controls" % (page, n.split(",")[0], n.split(",")[1]), flush=True)
            if int(n.split(",")[0]) < 8:
                raise SmokeError("Config's page %d has too few option rows: %s" % (page, n))
        got = str(eng.tjs('KAGOptionPick("readColor", 1); KAGOptionPick("readMark", 0); var r = [kag.readTextColor, kag.readMark];'
                          ' var b = kag.current.names.option_readColor_1; r.add(b !== void ? b.getMainPixel(b.width \\ 2, 4) : "none");'
                          ' KAGResetOptions(); KAGOptionRefresh(kag.current); r.add(kag.readTextColor); r.add(kag.readMark); return r.join(",");'))
        print("     read colour and mark picked, then Default: %s" % got, flush=True)
        v = got.split(",")
        if v[0] == "-1" or v[1] != "1" or v[3] != "-1" or v[4] != "0":
            raise SmokeError("a pick didn't set the option, or Default didn't put it back: %s" % got)
        eng.key("VK_ESCAPE")
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=20)

    @step("reading settings: window opacity, text that fades in, dramatic mode, the pause after a voice, Don't ask again")
    def _():
        if eng.tjs('return typeof kag.applyWindowOpacity != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the reading settings)", flush=True)
            return
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable && kag.currentDialog === void', timeout=30)
        m = "kag.fore.messages[0]"
        op = str(eng.tjs('var m = %s, r = [m.followOpacity ? 1 : 0, m.getMaskPixel(m.width \\ 2, 200)]; KAGOptionSet("windowOpacity", 100);'
                         ' r.add(m.shownFrameOpacity); r.add(m.getMaskPixel(m.width \\ 2, 200)); KAGOptionSet("windowOpacity", 255);'
                         ' r.add(m.getMaskPixel(m.width \\ 2, 200)); return r.join(",");' % m)).split(",")
        print("     the window's frame: alpha %s, at opacity 100 %s, back %s" % (op[1], op[3], op[4]), flush=True)
        if op[0] != "1" or op[2] != "100" or not int(op[3]) < int(op[1]) or op[4] != op[1]:
            raise SmokeError("the message window doesn't follow the window opacity: %s" % op)
        fade = str(eng.tjs('KAGOptionSet("textFade", 400); var m = %s; return [m.hasChFadeLayer ? 1 : 0, m.chFadeTime].join(",");' % m))
        eng.tjs("kag.onPrimaryClick(); return 1;")
        time.sleep(0.2)
        layers = eng.tjs("return %s.chFadeLayers.count;" % m)
        off = str(eng.tjs('KAGOptionSet("textFade", 0); var m = %s; return [m.hasChFadeLayer ? 1 : 0, m.chFadeLayers.count].join(",");' % m))
        print("     text fade 400 ms: %s, %s layers taking turns, off: %s" % (fade, layers, off), flush=True)
        if fade != "1,400" or int(layers) < 2 or off != "0,0":
            raise SmokeError("text that fades in over 400 ms didn't take turns on its fade layers: %s, %s, %s" % (fade, layers, off))
        # dramatic mode: a voiced line with the window hidden, a click shows it
        eng.tjs('KAGOptionSet("dramaticMode", "always"); kag.noteVoicedLine(true); return 1;')
        hidden = str(eng.tjs('return [kag.dramaticHidden ? 1 : 0, %s.visible ? 1 : 0].join(",");' % m))
        eng.tjs("kag.onPrimaryClick(); return 1;")
        shown = str(eng.tjs('var r = [kag.dramaticHidden ? 1 : 0, %s.visible ? 1 : 0]; KAGOptionSet("dramaticMode", "never"); return r.join(",");' % m))
        if hidden != "1,0" or shown != "0,1":
            raise SmokeError("dramatic mode didn't hide the window for a voiced line and show it on a click: %s, %s" % (hidden, shown))
        # auto mode goes on autoVoiceWait ms after the voices end
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        after = str(eng.tjs('kag.autoVoiceWait = 400; var e = world_object.env; e.stopAllVoice(); e.playVoice("ai", "ai000001", true);'
                            ' e.stopAllVoice(); return [e.playVoiceCount, e.voiceAfterTimer !== void && e.voiceAfterTimer.enabled ? 1 : 0].join(",");'))
        time.sleep(0.6)
        later = eng.tjs("var t = world_object.env.voiceAfterTimer; kag.autoVoiceWait = 0; return t !== void && t.enabled ? 1 : 0;")
        if after != "0,1" or later != 0:
            raise SmokeError("the pause after a voice didn't wait its 400 ms: %s, then %s" % (after, later))
        # Don't ask again: checked and answered Yes, the prompt answers Yes by itself; Ask Again brings it back
        eng.tjs('global.__smokeYes = 0; askYesNo("Load?", "Confirmation", function { global.__smokeYes++; }); return 1;')
        eng.wait("the prompt", 'typeof kag.currentDialog == "Object" && kag.currentDialog !== void', timeout=10)
        box = str(eng.tjs('var d = kag.currentDialog; var r = [d.names.skip !== void ? 1 : 0]; d.processLink(2); r.add(d.skipChecked ? 1 : 0);'
                          ' d.processLink(0); return r.join(",");'))
        again = str(eng.tjs('askYesNo("Load?", "Confirmation", function { global.__smokeYes++; });'
                            ' var r = [__smokeYes, kag.currentDialog === void ? 1 : 0]; KAGOptionPick("askAgain", 0);'
                            ' r.add(typeof sf.yesnoSkip == "Object" && sf.yesnoSkip !== void ? 1 : 0); return r.join(",");'))
        if box != "1,1" or again != "2,1,0":
            raise SmokeError("Don't ask again didn't turn the prompt off, or Ask Again didn't bring it back: %s, %s" % (box, again))
        eng.tjs('kag.process("layer.ks", "*start"); return 1;')
        eng.wait("layer.ks", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=30)

    @step("the name box: a long name squeezed into it, crossfades between speakers, fades away, follows the window's opacity")
    def _():
        if eng.tjs('return typeof kag.fore.messages[0].nameLayer.fitMode != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates names that fit their box)", flush=True)
            return
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable && kag.currentDialog === void', timeout=30)
        n = "kag.fore.messages[0].nameLayer"
        got = str(eng.tjs('var n = %s; n.processName("Ai, Who Has an Unusually Long Name Today");'
                          ' return [n.fitMode, n.squeezeLayer !== void ? 1 : 0, n.visible ? 1 : 0].join(",");' % n))
        if got != "squeeze,1,1":
            raise SmokeError("a long name wasn't squeezed into the name box (namefit=squeeze): %s" % got)
        eng.tjs('var n = %s; n.processName("Pip"); global.__smokeCross = n.crossLayer !== void && n.crossLayer.visible ? 1 : 0; return 1;' % n)
        time.sleep(0.5)
        cross = str(eng.tjs('var n = %s; return [__smokeCross, n.crossLayer.visible ? 1 : 0].join(",");' % n))
        eng.tjs('%s.processName(""); return 1;' % n)
        time.sleep(0.5)
        gone = str(eng.tjs('var n = %s; return [n.visible ? 1 : 0, n.fade].join(",");' % n))
        if cross != "1,0" or gone != "0,255":
            raise SmokeError("the name box didn't crossfade to the next speaker and fade away: %s, %s" % (cross, gone))
        # through the message layer, which records the name with its page: the opacity change
        # draws the page again, name and all
        frame = str(eng.tjs('var m = kag.fore.messages[0], n = m.nameLayer; m.processName("Pip"); var a = n.getMaskPixel(20, 20);'
                            ' KAGOptionSet("windowOpacity", 100); var b = n.getMaskPixel(20, 20); KAGOptionSet("windowOpacity", 255);'
                            ' m.processName(""); return [a, b].join(",");')).split(",")
        if not int(frame[1]) < int(frame[0]):
            raise SmokeError("the name box's frame didn't follow the window opacity: %s" % frame)
        eng.tjs('kag.process("layer.ks", "*start"); return 1;')
        eng.wait("layer.ks", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=30)

    @step("indicators: a compiled scene's title and the music's title show in the corners, auto mode's mark, the voice bar, [chapter stay=true] kept in saves")
    def _():
        if eng.tjs('return typeof kag.indicators == "Object" && kag.indicators !== void ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the indicators)", flush=True)
            return
        # (the music may play on from an earlier step: lastBgm forgotten, it shows as new)
        eng.tjs('KAGResetOptions(["chapterTitles", "nowPlaying", "modeMark", "voiceBar"]); kag.indicators.lastScene = void; kag.indicators.lastBgm = void;'
                ' kag.process("char.ks", "*start"); return 1;')
        eng.wait("the scene's title and the music's", 'kag.indicators.chapter == "Start" && kag.indicators.chapterLayer.visible'
                 ' && kag.indicators.playingLayer !== void && kag.indicators.playingLayer.visible', timeout=20)
        eng.wait("a stable point", "kag.inStable && kag.currentDialog === void", timeout=20)
        mode = str(eng.tjs('kag.enterAutoMode(); return 1;'))
        time.sleep(0.3)
        mode = str(eng.tjs('var i = kag.indicators, r = [i.modeShown, i.modeLayer.visible ? 1 : 0]; kag.cancelAutoMode(); return r.join(",");'))
        if mode != "AUTO,1":
            raise SmokeError("auto mode's mark didn't show: %s" % mode)
        play = eng.tjs('world_object.env.playVoice("ai", "ai000001", true); return world_object.env.characters.ai.soundBuffer.status == "play" ? 1 : 0;')
        if play == 1:
            eng.wait("the voice bar", "kag.indicators.voiceLayer !== void && kag.indicators.voiceLayer.visible", timeout=5)
        eng.tjs("world_object.env.stopAllVoice(); return 1;")
        kept = str(eng.tjs('KAGChapterTag(%[title:"Chapter One", stay:"true"]); var d = %[]; kag.indicators.onStore(d, void);'
                           ' kag.indicators.onRestore(%[], true, void); var gone = kag.indicators.chapterLayer.visible ? 0 : 1;'
                           ' kag.indicators.onRestore(d, true, void); var i = kag.indicators;'
                           ' var r = [gone, i.chapter, i.chapterLayer.visible ? 1 : 0]; KAGChapterTag(%[]); return r.join(",");'))
        if kept != "1,Chapter One,1":
            raise SmokeError("a chapter title with stay=true wasn't kept in the save data: %s" % kept)

    @step("naming the hero: the name screen refuses and trims names, the name shows in the text and the name box, and Search finds it")
    def _():
        if eng.tjs('return typeof kag.setHeroName != "undefined" && Storages.isExistentStorage("namescreen.ks") ? 1 : 0;') != 1:
            print("     (skipped: this build predates naming the hero)", flush=True)
            return
        eng.tjs('sf.heroNamed = false; kag.process("title.ks", "*gamestart"); return 1;')
        eng.wait("the name screen", 'kag.conductor.curStorage == "namescreen.ks" && kag.inStable'
                 ' && kag.current.names["tf.heroGiven"] !== void', timeout=30)
        eng.tjs('kag.current.names["tf.heroGiven"].text = "Stupid Bob"; nameOK(); return 1;')
        eng.wait("the reason", 'kag.conductor.curStorage == "namescreen.ks" && kag.inStable && tf.nameError != ""', timeout=20)
        eng.tjs('kag.current.names["tf.heroGiven"].text = "  Alex "; kag.current.names["tf.heroFamily"].text = ""; nameOK(); return 1;')
        eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks"', timeout=30)
        named = str(eng.tjs('return [sf.heroName, sf.heroFamily, f.name, world_object.env.isDefaultName() ? 1 : 0].join(",");'))
        if named != "Alex,%s,Alex,0" % eng.tjs("return kag.defaultFamily;"):
            raise SmokeError("the name screen didn't trim the name and keep the default family name: %s" % named)
        # the hero speaks in the Character demo's Voices scene: the name box says the name, and
        # Ai's line has it ([emb]); the backlog keeps it
        eng.tjs('kag.process("char.ks", "*voices"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable', timeout=30)
        for i in range(24):
            if eng.tjs('return kag.fore.messages[0].nameLayer.lastName == "Alex" ? 1 : 0;') == 1:
                break
            eng.tjs("kag.onPrimaryClick(); return 1;")
            time.sleep(0.3)
            eng.wait("the next stop", "kag.inStable", timeout=20)
        if eng.tjs('return kag.fore.messages[0].nameLayer.lastName == "Alex" ? 1 : 0;') != 1:
            raise SmokeError("the hero's line didn't show the name Alex in the name box")
        if eng.compiled:
            found = str(eng.tjs('var r = world_object.player.searchTexts("Alex", false); return r.count;'))
            print("     Search finds Alex in %s lines" % found, flush=True)
            if int(found) < 1:
                raise SmokeError("Search doesn't find the hero's name in Ai's line ([emb])")
            log = eng.tjs('world_object.player.rebuildBacklog(); var h = kag.historyLayer, s = "";'
                          ' for (var i = 0; i < h.dataLines; i++) s += h.getLine(i) + "\\n"; return s.indexOf("Alex") >= 0 ? 1 : 0;')
            if log != 1:
                raise SmokeError("the backlog written again from the history lost the hero's name ([emb])")
        eng.tjs('kag.process("layer.ks", "*start"); return 1;')
        eng.wait("layer.ks", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=30)

    @step("writers' shorthands: a code sets a pose and a face, and presets move a character back or forward at once")
    def _():
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable', timeout=30)
        if eng.tjs('var ai = world_object.env.getCharacter("ai"); return ai !== void && typeof ai.doShorthand != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the shorthands)", flush=True)
            return
        got = str(eng.tjs('var e = world_object.env, ai = e.getCharacter("ai"), r = [];'
                          ' e.unknown("ai", %[tagname:"ai", "103" => "true"]); r.add(ai.face);'
                          ' e.unknown("ai", %[tagname:"ai", "101" => "true"]); r.add(ai.face);'
                          ' e.unknown("ai", %[tagname:"ai", "far" => "true"]); r.add(ai.level);'
                          ' e.unknown("ai", %[tagname:"ai", "near" => "true"]); r.add(ai.level); return r.join(",");'))
        if got != "sad,happy,0,2":
            raise SmokeError("[ai 103], [ai 101], [ai far] and [ai near] didn't set face sad, happy, level 0 and 2: %s" % got)

    @step("[vo]: a voice file's speaker worked out from the characters' voiceFile patterns, in the compiled scene too")
    def _():
        if eng.tjs('return typeof world_object.env.voiceSpeaker != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates [vo])", flush=True)
            return
        who = str(eng.tjs('var e = world_object.env; return [e.voiceSpeaker("pip000003"), e.voiceSpeaker("ai000001.ogg"),'
                          ' e.voiceSpeaker("nobody0001") === void ? "-" : "?"].join(",");'))
        if who != "pip,ai,-":
            raise SmokeError("the speakers of pip000003, ai000001.ogg and nobody0001 aren't pip, ai and no one: %s" % who)
        if eng.compiled:
            found = str(eng.tjs('var r = world_object.player.searchTexts("Whoa", false); return r.count > 0 ? r[0].name : "none";'))
            if found != "Pip":
                raise SmokeError("[vo pip000003] didn't make Pip the speaker of the compiled line: %s" % found)

    @step("the credits roll over the rest of the music, keep their place in a save, and send rollend when seen to the end")
    def _():
        if eng.tjs('return typeof global.RollFlip != "undefined" && Storages.isExistentStorage("credits.ks") ? 1 : 0;') != 1:
            print("     (skipped: this build predates the credits roll)", flush=True)
            return
        eng.tjs('sf["roll:credits"] = void; kag.process("credits.ks", "*start"); return 1;')
        eng.wait("the roll", 'kag.fore.layers[0].flipType == "roll" && kag.fore.layers[0].flip.items.count > 5', timeout=20)
        # its first frames can take a moment to come (the web build's did)
        eng.wait("the roll to move", 'kag.fore.layers[0].flipType == "roll" && kag.fore.layers[0].flip.elapsed > 0', timeout=20)
        info = str(eng.tjs('var f = kag.fore.layers[0].flip; return [f.items.count, f.total, f.duration, f.elapsed > 0 ? 1 : 0].join(",");'))
        print("     %s lines and pictures, %s px, over %s ms" % tuple(info.split(",")[:3]), flush=True)
        v = info.split(",")
        if int(v[2]) < 30000 or v[3] != "1":
            raise SmokeError("the roll isn't timed to the music playing (rolltime=bgm) or isn't moving: %s" % info)
        kept = str(eng.tjs('var l = kag.fore.layers[0], f = l.flip; f.elapsed = 12345; var d = %[]; l.storeFlip(d);'
                           ' l.restoreFlip(d); return [l.flip.elapsed >= 12345 ? 1 : 0, KAGRollSeen("credits") ? 1 : 0].join(",");'))
        if kept != "1,0":
            raise SmokeError("a save didn't keep how far the roll had got, or it was seen already: %s" % kept)
        eng.tjs('var f = kag.fore.layers[0].flip; f.elapsed = f.duration - 100; return 1;')
        eng.wait("the demo menu after the roll", 'kag.conductor.curStorage == "s0001.ks" && KAGRollSeen("credits")', timeout=20)

    @step("[movie]: the opening was noted as seen, its subtitles come from opening.vtt, a seen movie skips with a click, Replay's Movies tab plays it, its smaller version fills the screen, and a movie whose picture stops ends")
    def _():
        if eng.tjs('return typeof global.KAGMovieTag != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates [movie])", flush=True)
            return
        cues = str(eng.tjs('var c = KAGParseVTT("opening.vtt"); return [c.count, c.count > 0 ? c[0].from : -1, c.count > 0 ? c[0].to : -1].join(",");'))
        if cues != "4,600,2900":
            raise SmokeError("opening.vtt's cues weren't read as four, the first from 600 to 2900 ms: %s" % cues)
        seen = eng.tjs('return KAGMovieSeen("opening") ? 1 : 0;')
        print("     the opening seen at start: %s" % seen, flush=True)
        # the movie's layer goes over everything while it plays, and back under the message window
        # after (0.17.0 left it there, and the layer demo's Vee covered the text)
        under = 'var l = kag.fore.layers[kag.fore.layers.count - 1]; return l.absolute < kag.fore.messages[0].absolute ? 1 : 0;'
        if seen == 1 and eng.tjs(under) != 1:
            raise SmokeError("after the opening movie its layer stayed over the message window")
        eng.tjs('tf.replayTab = void; sf.extramode = 2; kag.process("title.ks", "*extra"); return 1;')
        eng.wait("replay.ks", 'kag.conductor.curStorage == "replay.ks" && kag.inStable', timeout=20)
        tab = eng.tjs('return replayTabs.find("Movies");')
        if tab < 0:
            raise SmokeError("Replay has no Movies tab")
        eng.tjs('sf["movie:opening"] = true; setReplayPage(%d, 0); return 1;' % tab)
        if eng.tjs("return tf.replaylist[0] !== void && tf.replaylist[0].movie == \"opening\" ? 1 : 0;") != 1:
            raise SmokeError("the Movies tab's first tile isn't the opening, or it's locked though seen")
        eng.tjs("replayTile(0); return 1;")
        eng.wait("the movie", 'KAGMoviePlaying !== void', timeout=20)
        sub = str(eng.tjs('var l = kag.fore.layers[+KAGMoviePlaying.layer], f = l.flip;'
                          ' return [l.flipType, f.subtitles !== void ? f.subtitles.cues.count : 0].join(",");'))
        if sub != "movie,4":
            raise SmokeError("[movie] didn't play on a layer with its subtitles: %s" % sub)
        # the movie on the screen, not the backdrop (color=) over it: 0.17.0 made the backdrop a child
        # of the primary layer, which covered the base layer the movie is on, so it was a black screen
        eng.wait("the movie's first frames", 'KAGMoviePlaying === void || (kag.fore.layers[+KAGMoviePlaying.layer].flip !== void'
                 ' && kag.fore.layers[+KAGMoviePlaying.layer].flip.frames > 3)', timeout=10)
        shown = eng.tjs('if (KAGMoviePlaying === void) return -1; var w = new global.Layer(kag, kag.primaryLayer);'
                        ' w.setImageSize(kag.primaryLayer.width, kag.primaryLayer.height);'
                        ' w.piledCopy(0, 0, kag.primaryLayer, 0, 0, w.imageWidth, w.imageHeight); var n = 0;'
                        ' for (var y = 60; y < w.imageHeight - 60; y += 40) for (var x = 60; x < w.imageWidth - 60; x += 40)'
                        ' n++ if (w.getMainPixel(x, y) & 0xffffff) != 0; invalidate w; return n;')
        print("     the movie on the screen: %s of its samples not the black backdrop" % shown, flush=True)
        if shown == 0:
            raise SmokeError("the movie didn't show: the screen was the backdrop's colour all over")
        time.sleep(0.6)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        eng.wait("Replay again (a seen movie skips with a click)", 'kag.conductor.curStorage == "replay.ks" && KAGMoviePlaying === void && kag.inStable', timeout=20)
        if eng.tjs(under) != 1:
            raise SmokeError("after a movie from Replay its layer stayed over the message window")
        # the smaller version (Movie Quality "Smaller"; the web and phones choose it themselves),
        # zoomed to fill the screen, with the full movie's subtitles
        eng.tjs('tf.smokeMovieQuality = KAGOptionGet("movieQuality"); KAGOptionSet("movieQuality", "small"); replayTile(0); return 1;')
        try:
            eng.wait("the smaller movie", 'KAGMoviePlaying !== void && kag.fore.layers[+KAGMoviePlaying.layer].flip !== void', timeout=20)
            picked = str(eng.tjs('var f = kag.fore.layers[+KAGMoviePlaying.layer].flip;'
                                 ' return [f.file, f.subtitles !== void ? f.subtitles.cues.count : 0].join(",");'))
            if picked != "opening_sd,4":
                raise SmokeError("Smaller didn't play opening_sd with opening.vtt's cues: %s" % picked)
            # where it shows (the web's player can't open a movie inside data.xp3: it ends, no picture)
            eng.wait("the smaller movie's first frames, or its end", 'KAGMoviePlaying === void'
                     ' || kag.fore.layers[+KAGMoviePlaying.layer].flip.frames > 1', timeout=20)
            small = str(eng.tjs('if (KAGMoviePlaying === void) return "none"; var l = kag.fore.layers[+KAGMoviePlaying.layer], f = l.flip;'
                                ' return [(int)(l.zoom * f.targetLayer.width / 100 + 0.5), (int)(l.zoom * f.targetLayer.height / 100 + 0.5)].join(",");'))
            print("     the smaller movie: %s, shown at %s" % (picked, small), flush=True)
            want = eng.tjs('return "%d,%d".sprintf(kag.primaryLayer.width, kag.primaryLayer.height);')
            if small != "none" and small != want:
                raise SmokeError("the smaller movie didn't fill the screen: shown at %s, not %s" % (small, want))
            if small != "none":
                time.sleep(0.4)
                eng.tjs("kag.onPrimaryClick(); return 1;")
            eng.wait("Replay again", 'kag.conductor.curStorage == "replay.ks" && KAGMoviePlaying === void && kag.inStable', timeout=20)
            zoom = eng.tjs('return (int)kag.fore.layers[kag.fore.layers.count - 1].zoom;')
            if zoom != 100:
                raise SmokeError("the movie's layer kept its zoom (%s) after the movie" % zoom)
        finally:
            eng.tjs('KAGOptionSet("movieQuality", tf.smokeMovieQuality); return 1;')
        # a movie whose picture stops ends 3 s later: without a sound device the engine holds a
        # movie with sound at its first frame (UPSTREAM.md 40), and 0.17.2's first release run
        # hung at the opening on the Windows runner; a pause stands in for that here
        eng.tjs("replayTile(0); return 1;")
        eng.wait("the movie's frames, or its end", 'KAGMoviePlaying !== void && kag.fore.layers[+KAGMoviePlaying.layer].flip !== void'
                 ' && (kag.fore.layers[+KAGMoviePlaying.layer].flip.frames > 2 || System.getTickCount() - KAGMoviePlaying.started > 4000)'
                 ' || KAGMoviePlaying === void && kag.conductor.curStorage == "replay.ks"', timeout=20)
        if eng.tjs('return KAGMoviePlaying !== void && kag.fore.layers[+KAGMoviePlaying.layer].flip.frames > 2 ? 1 : 0;') == 1:
            eng.tjs("kag.fore.layers[+KAGMoviePlaying.layer].flip.pause(); tf.smokePausedAt = System.getTickCount(); return 1;")
            eng.wait("the stopped movie to end", 'KAGMoviePlaying === void', timeout=15)
            took = eng.tjs("return System.getTickCount() - tf.smokePausedAt;")
            print("     a movie whose picture stopped ended %s ms later" % took, flush=True)
            if took < 2500:
                raise SmokeError("a movie whose picture stopped ended too soon (%s ms)" % took)
        else:
            print("     (the movie shows no picture here: the check of a picture that stops is skipped)", flush=True)
        eng.wait("Replay again", 'kag.conductor.curStorage == "replay.ks" && KAGMoviePlaying === void && kag.inStable', timeout=20)
        eng.key("VK_ESCAPE")
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("face windows: the speaker's face cut from the sprite, a face-only speaker, none for narration, a CG or a scene that turns them off, Config's switch, a load")
    def _():
        if eng.tjs('return typeof global.KAGFaceCropInto != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates face windows)", flush=True)
            return
        # the face layer's opaque samples and the speaker, from one expression
        state = ('(function() { var fl = kag.fore.messages[0].faceLayer, a = 0, e = world_object.env;'
                 ' if (fl !== void && fl.visible) for (var y = 10; y < fl.height; y += 20) for (var x = 10; x < fl.width; x += 20) a++ if fl.getMaskPixel(x, y) > 0;'
                 ' return [e.currentNameTarget !== void ? e.currentNameTarget.name : "-", a, kag.inStable ? 1 : 0].join(","); })()')
        def line(what, who, face):
            want = '(function() { var s = (string)%s; var p = s.split(","); return p[0] == "%s" && (%s) && p[2] == "1"; })()' % (
                state, who, "+p[1] > 20" if face else "+p[1] == 0")
            try:
                eng.wait(what, want, timeout=20)
            except SmokeError:
                raise SmokeError("%s: not as expected (speaker, face samples, stable): %s" % (what, eng.tjs("return " + state + ";")))
            print("     %s: %s" % (what, eng.tjs("return " + state + ";")), flush=True)
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks with its face window", 'kag.conductor.curStorage == "char.ks" && kag.fore.messages[0].faceLayer !== void'
                 ' && kag.back.messages[0].faceLayer !== void', timeout=30)
        eng.tjs('kag.process("char.ks", "*faces"); return 1;')
        line("Ai speaks", "ai", True)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("Ai, cross", "ai", True)
        eng.tjs("kag.saveBookMark(4); return 1;")
        eng.wait("data4 to be written", "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(4))", timeout=10)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("Pip, a face only (not on stage)", "pip", True)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("narration", "-", False)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("Ai over a CG", "ai", False)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[env facewindow=off]", "ai", False)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[env facewindow=on]", "ai", True)
        # Config's switch: off takes the face away at once, on brings it with the next speaker
        eng.tjs('tf.smokeFace = KAGOptionGet("faceWindow"); KAGOptionSet("faceWindow", false); return 1;')
        line("Config's Face Window off", "ai", False)
        eng.tjs('KAGOptionSet("faceWindow", tf.smokeFace); return 1;')
        # a load: the face of the line loaded
        eng.tjs("kag.loadBookMark(4); return 1;")
        line("loaded at Ai's cross line", "ai", True)
        eng.tjs('kag.process("title.ks", "*backtotitle"); return 1;')
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("layouts: a character joining at the right and in the middle, one leaving, [env makeroom], everyone evenly spaced on the screen")
    def _():
        if eng.tjs('return typeof world_object.env.layoutPlace != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates layouts)", flush=True)
            return
        # the shown characters left to right, name@xpos, once each has slid to where the World says
        state = ('(function() { var e = world_object.env, r = [], moving = 0;'
                 ' for (var i = 0; i < e.characterList.count; i++) { var c = e.characterList[i]; if (!c.isShowBU()) continue;'
                 ' r.add(%[ x:+c.xpos, s:c.name + "@" + c.xpos ]);'
                 ' moving++ if c.targetLayer === void || (int)c.targetLayer.left != (int)c.xpos; }'
                 ' r.sort(function(a, b) { return a.x < b.x; }, true); var t = []; for (var i = 0; i < r.count; i++) t.add(r[i].s);'
                 ' return t.join(" ") + (moving ? " (moving)" : "") + (kag.inStable ? "" : " (busy)"); })()')
        def line(what, want):
            try:
                eng.wait(what, '(string)%s == "%s"' % (state, want), timeout=20)
            except SmokeError:
                raise SmokeError("%s: the characters stand at %s, not %s" % (what, eng.tjs("return " + state + ";"), want))
            print("     %s: %s" % (what, want), flush=True)
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable', timeout=30)
        eng.tjs('kag.process("char.ks", "*layouts"); return 1;')
        line("Ai alone", "ai@0")
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[pip join]", "ai@-420 pip@420")
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[ai2 join=middle]", "ai@-660 ai2@0 pip@660")
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[ai leave]", "ai2@-420 pip@420")
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[env makeroom=0]", "ai2@-840 pip@840")
        eng.tjs('kag.process("title.ks", "*backtotitle"); return 1;')
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("keeping a scene: [env keep], a grey flashback, a save and a load in it, [env restore] back to the scene as it was with the music playing on")
    def _():
        if eng.tjs('return typeof world_object.env.keepScene != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates [env keep])", flush=True)
            return
        state = ('(function() { var e = world_object.env, r = [];'
                 ' for (var i = 0; i < e.characterList.count; i++) { var c = e.characterList[i]; if (c.isShowBU()) r.add(c.name + "@" + c.xpos + ":" + c.face); }'
                 ' r.sort(function(a, b) { return a < b; }, true);'
                 ' return r.join(" ") + " grey=" + (e.grayscale !== void ? e.grayscale : "-") + " kept=" + e.keptScenes.count'
                 ' + " bgm=" + e.bgm.filename + (kag.inStable ? "" : " (busy)"); })()')
        def line(what, want):
            try:
                eng.wait(what, '(string)%s == "%s"' % (state, want), timeout=20)
            except SmokeError:
                raise SmokeError("%s: the World is %s, not %s" % (what, eng.tjs("return " + state + ";"), want))
            print("     %s: %s" % (what, want), flush=True)
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable', timeout=30)
        eng.tjs('kag.process("char.ks", "*flashback"); return 1;')
        now = "ai@0:happy pip@480:neutral grey=- kept=0 bgm=bgm01"
        memory = "ai@-480:sad grey=true kept=1 bgm=bgm01"
        line("the scene", now)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[env keep], a grey flashback", memory)
        eng.tjs("kag.saveBookMark(5); return 1;")
        eng.wait("data5 to be written", "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(5))", timeout=10)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[env restore]", now)
        eng.tjs("kag.loadBookMark(5); return 1;")
        line("loaded in the flashback, the kept scene with it", memory)
        eng.tjs("kag.onPrimaryClick(); return 1;")
        line("[env restore] after the load", now)
        eng.tjs('kag.process("title.ks", "*backtotitle"); return 1;')
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("the staging kit: twenty gestures ending where they began, the screen shakes, a close-up, a dim and a white veil, an eyecatch card")
    def _():
        if eng.tjs('return typeof world_object.env.envinfo.actions.nod != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this sample predates the staging kit)", flush=True)
            return
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable', timeout=30)
        eng.tjs('kag.process("char.ks", "*staging"); return 1;')
        ai = 'world_object.env.characters["ai"]'
        eng.wait("Ai", '%s !== void && %s.targetLayer !== void && kag.inStable' % (ai, ai), timeout=60)
        home = eng.tjs('var l = %s.targetLayer; return "%%d,%%d".sprintf(l.left, l.top);' % ai)
        # click on until each part shows, in the scene's order
        def until(what, expr, clicks=12):
            for i in range(clicks):
                eng.wait("the line", "kag.inStable", timeout=60)
                if eng.tjs("return (%s) ? 1 : 0;" % expr) == 1:
                    print("     %s" % what, flush=True)
                    return
                eng.tjs("kag.onPrimaryClick(); return 1;")
            raise SmokeError("%s didn't come in the Staging Kit scene" % what)
        e = "world_object.env"
        for row in range(4):
            eng.wait("a row of gestures", "kag.inStable", timeout=60)
            at = eng.tjs('var l = %s.targetLayer; return "%%d,%%d".sprintf(l.left, l.top);' % ai)
            if at != home:
                raise SmokeError("after row %d of gestures Ai stands at %s, not %s" % (row + 1, at, home))
            eng.tjs("kag.onPrimaryClick(); return 1;")
        until("the screen shakes, the camera back where it was", '+%s.cprops.camerax == 0 && +%s.cprops.cameray == 0' % (e, e))
        until("[closeup]: the camera at 140% and the background blurred", '+%s.cprops.camerazoom == 140 && +%s.stage.blurx > 0' % (e, e))
        until("[dim]: a black veil", '%s.layers["veil"] !== void && %s.layers["veil"].isShowBU() && +%s.cprops.camerazoom == 100' % (e, e, e))
        until("[whiten]: a white veil", '%s.layers["veil"] !== void && %s.layers["veil"].isShowBU() && %s.layers["veil"].imageFile == "white"' % (e, e, e))
        until("Pip slid in (showslide)", '%s.layers["veil"] === void && %s.characters["pip"] !== void && %s.characters["pip"].isShowBU()' % (e, e, e))
        eng.tjs("kag.onPrimaryClick(); return 1;")
        eng.wait("the eyecatch card", '%s.layers["eyecatchcard"] !== void && %s.layers["eyecatchcard"].isShowBU()' % (e, e), timeout=30)
        eng.tjs("kag.onPrimaryClick(); return 1;")  # a click skips it
        eng.wait("the card gone, and the next scene", '%s.layers["eyecatchcard"] === void && kag.inStable' % e, timeout=30)
        print("     [eyecatch]: the card came and a click took it away", flush=True)
        eng.tjs('kag.process("title.ks", "*backtotitle"); return 1;')
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("Extras: CG counts, the last tab, the music room's track playing on through CG and Replay and kept on the title, the evening title")
    def _():
        if eng.tjs('return typeof global.roomMusicPlaying != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this sample predates the Extras touches)", flush=True)
            return
        eng.tjs('sf.clear = true; sf.bgm_BGM01 = true; sf.titleMusic = void; sf.titlePicture = void;'
                ' kag.process("title.ks", "*titleloop"); return 1;')
        eng.wait("the title with its picture's arrows", 'kag.conductor.curStorage == "title.ks" && kag.inStable'
                 ' && kag.fore.messages[0].names.title_next !== void', timeout=30)
        eng.tjs('nextTitlePicture(1); kag.process("title.ks", "*titleloop"); return 1;')
        eng.wait("the evening title", 'kag.conductor.curStorage == "title.ks" && kag.inStable && sf.titlePicture == "title_evening"', timeout=30)
        # the music room: a track, kept on the title
        eng.tjs('sf.extramode = 3; kag.process("title.ks", "*extra"); return 1;')
        eng.wait("musicmode.ks", 'kag.conductor.curStorage == "musicmode.ks" && kag.inStable', timeout=20)
        eng.tjs("playBgm(0); setTitleMusic(true); return 1;")
        playing = True
        try:
            eng.wait("the track to play", "roomMusicPlaying()", timeout=10)
        except SmokeError:
            playing = False
            print("     (the music doesn't play here: the checks of the music playing on are skipped)", flush=True)
        if playing:
            lit = eng.tjs('var b = kag.fore.messages[0].names.track01; return b.getMainPixel(100, 23) != 0xffffff ? 1 : 0;')
            if lit != 1:
                raise SmokeError("the track playing isn't lit in the music room")
        # the CG screen: the track plays on, with its Stop button; the counts
        eng.tjs('kag.process("cgmode.ks"); return 1;')
        eng.wait("cgmode.ks", 'kag.conductor.curStorage == "cgmode.ks" && kag.inStable', timeout=20)
        got = str(eng.tjs('var c = cgCounts(); return [roomMusicPlaying() ? 1 : 0, kag.fore.messages[0].names.gallery_stop !== void ? 1 : 0,'
                          ' c.all[1], c.page0 !== void ? c.page0[1] : -1].join(",");'))
        print("     CG screen (playing, Stop button, pictures, on page 1): %s" % got, flush=True)
        if got.split(",")[2] in ("0", "-1") or (playing and not got.startswith("1,1,")):
            raise SmokeError("the CG screen doesn't play the room's track on with a Stop button, or counts nothing: %s" % got)
        # Extras opens on the tab last used
        eng.tjs('kag.process("title.ks", "*backtotitle"); return 1;')
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)
        if playing and eng.tjs("return roomMusicPlaying() ? 1 : 0;") != 1:
            raise SmokeError("the track kept as the title's music stopped when Extras was left")
        eng.tjs('kag.process("title.ks", "*extra"); return 1;')
        eng.wait("Extras on the CG tab, as left", 'kag.conductor.curStorage == "cgmode.ks" && kag.inStable', timeout=20)
        eng.tjs('galleryStop(); setTitleMusic(false); kag.process("title.ks", "*backtotitle"); return 1;')
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable && !roomMusicPlaying()', timeout=30)
        eng.tjs('sf.titlePicture = void; kag.process("title.ks", "*titleloop"); return 1;')
        eng.wait("the title", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("quick saves go round their bookmarks, and quick load asks, then loads the newest")
    def _():
        if eng.tjs('return typeof kag.quickSave != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates quick saves that go round)", flush=True)
            return
        eng.tjs('kag.process("layer.ks", "*start"); return 1;')
        eng.wait("a stable point in layer.ks", 'kag.conductor.curStorage == "layer.ks" && kag.inStable && kag.currentDialog === void', timeout=20)
        line = eng.tjs("return kag.conductor.curLine;")
        got = str(eng.tjs('var r = []; for (var i = 0; i < 4; i++) r.add(kag.quickSave());'
                          ' return r.join(",") + "|" + kag.newestQuickSave() + "|" + kag.quickSaves().join(",");'))
        print("     four quick saves went to %s; the newest %s, newest first %s" % tuple(got.split("|")), flush=True)
        if got != "90,91,92,90|90|90,92,91":
            raise SmokeError("the quick saves didn't go round bookmarks 90 to 92: %s" % got)
        for n in (90, 91, 92):
            eng.wait("quick save %d to be written" % n, "Storages.isExistentStorage(kag.getBookMarkFileNameAtNum(%d))" % n, timeout=10)
        keys = str(eng.tjs('var s = kag.findKeyBinding(#\'S\', ssShift, false), l = kag.findKeyBinding(#\'L\', ssShift, false);'
                           ' return [s !== void ? s.label : "-", l !== void ? l.label : "-"].join(",");'))
        if keys != "Quick save,Quick load":
            raise SmokeError("Shift+S and Shift+L aren't quick save and quick load: %s" % keys)
        # Q.LOAD asks first (the focus starts on No), then loads the newest where it was saved;
        # from the title, here
        eng.tjs("kag.goToStart(); return 1;")
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable && kag.currentDialog === void', timeout=30)
        eng.tjs("quickloadAction(); return 1;")
        eng.wait("the prompt", 'typeof kag.currentDialog == "Object" && kag.currentDialog !== void', timeout=10)
        eng.key("VK_LEFT")
        eng.key("VK_RETURN")
        eng.wait("the quick save to load", 'kag.conductor.curStorage == "layer.ks" && kag.conductor.curLine == %d && kag.inStable' % line, timeout=30)

    @step("the continue save: kept as the game goes, and the title offers to carry on from it")
    def _():
        if eng.tjs('return typeof kag.saveContinue != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates the continue save)", flush=True)
            return
        eng.wait("a stable point in layer.ks", 'kag.conductor.curStorage == "layer.ks" && kag.inStable && kag.currentDialog === void', timeout=20)
        if eng.tjs("return kag.saveContinue() ? 1 : 0;") != 1:
            raise SmokeError("the continue save wasn't written at a stable point in a scene")
        before = eng.tjs("return kag.readBookMark(kag.continueSlot).core.storeTime;")
        time.sleep(0.05)
        # a save point in a script the continue save isn't from: written at the next stable state
        # (now: the game is waiting for a click)
        eng.tjs('kag.continueStorage = ""; kag.noteContinuePoint(); return 1;')
        eng.wait("the continue save to be written again", "!kag.continueWanted && kag.continuePoints == 0 && kag.inStable"
                 " && kag.readBookMark(kag.continueSlot).core.storeTime != %s" % before, timeout=30)
        line = eng.tjs("return kag.conductor.curLine;")
        # turned off in Config, the title doesn't offer it; on, it does, and Yes loads it
        eng.tjs("kag.continueOn = false; return 1;")
        if eng.tjs("return kag.hasContinue ? 1 : 0;") != 0:
            raise SmokeError("Config's switch off, there's still a place to carry on from")
        eng.tjs("kag.continueOn = true; tf.continueAsked = false; kag.goToStart(); return 1;")
        eng.wait("the title's offer", 'kag.conductor.curStorage == "title.ks" && typeof kag.currentDialog == "Object"'
                 ' && kag.currentDialog !== void', timeout=30)
        eng.key("VK_LEFT")  # the focus starts on No
        eng.key("VK_RETURN")
        eng.wait("the place to load", 'kag.conductor.curStorage == "layer.ks" && kag.conductor.curLine == %d && kag.inStable' % line,
                 timeout=30)

    @step("voices: a cut voice fades out on a track of its own, voices come from where their speakers stand, and vol= makes a line quieter")
    def _():
        if eng.tjs('return typeof world_object.env.voiceFadeTime != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build's framework predates voices that fade)", flush=True)
            return
        eng.tjs('kag.process("char.ks", "*voices"); return 1;')
        eng.wait("Ai and Pip on the stage", 'kag.conductor.curStorage == "char.ks" && kag.inStable && kag.currentDialog === void'
                 ' && world_object.env.characters.pip !== void && world_object.env.characters.pip.isShowBU()', timeout=30)
        ch = 'var e = world_object.env, ai = e.characters.ai, pip = e.characters.pip; '
        # the line's own volume and pan, through the compiled scene ([pip voice=4 vol=35])
        eng.tjs("kag.voicecut = false; kag.voiceFadeOn = true; kag.voiceFadeTime = 400; kag.voicePlacement = true; return 1;")
        for i in range(12):
            if eng.tjs(ch + 'var b = pip.soundBuffer; return b !== void && b.storage !== void && b.storage.indexOf("pip000004") == 0 ? 1 : 0;') == 1:
                break
            eng.tjs("kag.onPrimaryClick(); return 1;")
            time.sleep(0.3)
            eng.wait("the next stop", "kag.inStable", timeout=20)
        whisper = str(eng.tjs(ch + 'var b = pip.soundBuffer; return b === void ? "none" : [b.storage, b.lineVolume].join(",");'))
        if not whisper.startswith("pip000004") or not whisper.endswith(",35"):
            raise SmokeError("the whispered line ([pip voice=4 vol=35]) didn't play at 35%%: %s" % whisper)
        # a cut fades out on the voice's own track while the next starts at once on the other
        play = str(eng.tjs(ch + 'e.stopAllVoice(); e.playVoice("ai", "ai000001", true); return ai.soundBuffer.status;'))
        if play != "play":
            print("     (the fade's checks skipped: the voice didn't start, %s)" % play, flush=True)
        else:
            cut = str(eng.tjs(ch + 'var old = ai.soundBuffer; e.stopAllVoice(true); e.playVoice("ai", "ai000001", true);'
                              ' var f = ai.fadingVoice, b = ai.soundBuffer; return [f === old ? 1 : 0, f.status, f.fading ? 1 : 0,'
                              ' f.canWait() ? 1 : 0, b !== old ? 1 : 0, b.status, e.playVoiceCount].join(",");'))
            print("     cut: %s" % cut, flush=True)
            if cut != "1,play,1,0,1,play,1":
                raise SmokeError("the cut voice isn't fading on its own track while the next plays: %s" % cut)
            fv = "world_object.env.characters.ai.fadingVoice"
            eng.wait("the fade to end", '%s.status == "stop" && !%s.fading && %s.volume == 100000' % (fv, fv, fv), timeout=5)
            eng.tjs(ch + 'e.stopAllVoice(); return 1;')
            # Config's Stop: the cut is at once
            now = str(eng.tjs(ch + 'e.playVoice("ai", "ai000001", true); kag.voiceFadeOn = false; e.stopAllVoice(true);'
                              ' kag.voiceFadeOn = true; return [ai.soundBuffer.status, ai.fadingVoice.status].join(",");'))
            if now != "stop,stop":
                raise SmokeError("with fading off, a cut voice should stop at once: %s" % now)
        # where the speakers stand: Ai on the left, Pip on the right; pan= and the switch centre them
        if eng.tjs('return typeof kag.se[0].use3D != "undefined" && typeof global.SoundListener != "undefined" ? 1 : 0;') == 1:
            got = str(eng.tjs(ch + 'var r = []; e.playVoice("ai", "ai000001", true); r.add(ai.soundBuffer.use3D ? "%.2f".sprintf(ai.soundBuffer.posX) : "off");'
                              ' e.playVoice("pip", "pip000003", true); r.add(pip.soundBuffer.use3D ? "%.2f".sprintf(pip.soundBuffer.posX) : "off");'
                              ' e.playVoice("pip", "pip000003", true, %[pan:-100, vol:50]); var b = pip.soundBuffer; r.add(b.use3D ? "3d" : b.pan); r.add(b.lineVolume);'
                              ' kag.voicePlacement = false; e.playVoice("ai", "ai000001", true); r.add(ai.soundBuffer.use3D ? "3d" : ai.soundBuffer.pan);'
                              ' kag.voicePlacement = true; e.stopAllVoice(); return r.join(",");'))
            print("     Ai at x %s, Pip at x %s; pan=-100 vol=50: %s; centred: %s" % tuple(got.split(",")[:2] + [",".join(got.split(",")[2:4]), got.split(",")[4]]), flush=True)
            v = got.split(",")
            try:
                left, right = float(v[0]), float(v[1])
            except ValueError:
                raise SmokeError("the voices aren't placed: %s" % got)
            if not (left < -0.2 and right > 0.2) or v[2:] != ["-100000", "50", "0"]:
                raise SmokeError("the voices aren't where their speakers stand, or pan= and the switch don't centre them: %s" % got)
        else:
            print("     (placement skipped: this engine has no 3D sound)", flush=True)
        eng.tjs('kag.process("layer.ks", "*start"); return 1;')
        eng.wait("layer.ks", 'kag.conductor.curStorage == "layer.ks" && kag.inStable', timeout=30)

    @step("back to the title through the Yes/No prompt")
    def _():
        eng.tjs("kag.goToStartWithAsk(); return 1;")
        eng.wait("the prompt", 'typeof kag.currentDialog == "Object" && kag.currentDialog !== void',
                 timeout=10)
        eng.key("VK_LEFT")  # the focus starts on No
        eng.key("VK_RETURN")
        # with its buttons: up to 0.15.0, from the second return on (after a compiled scene had
        # played), the title's start anchor held that scene and its text came back instead
        eng.wait("the title with its buttons", 'kag.conductor.curStorage == "title.ks" && kag.inStable'
                 ' && kag.fore.messages[0].numLinks >= 5', timeout=30)

    for screen, mode in (("cgmode.ks", 1), ("replay.ks", 2), ("musicmode.ks", 3)):
        @step("Extras: " + screen + " opens and returns to the title")
        def _(screen=screen, mode=mode):
            eng.tjs('sf.extramode = %d; kag.process("title.ks", "*extra"); return 1;' % mode)
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
        eng.tjs('sf.extramode = 2; kag.process("title.ks", "*extra"); return 1;')
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
        eng.tjs('tf.searchText = ""; sf.extramode = 4; kag.process("title.ks", "*extra"); return 1;')
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
        # its blinking and lip-sync again (KAGEnvCharacterEx.onRestore, restoreEyeLip)
        eng.tjs('tf.searchText = "blink"; sf.extramode = 4; kag.process("title.ks", "*extra"); return 1;')
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

    @step("languages: F9 shows the title screen in Japanese, with its own images, then English again")
    def _():
        if not language_framework(eng):
            print("     (skipped: this build has one language)", flush=True)
            return
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable && kag.transCount == 0', timeout=30)
        # the Start button against its image as the language's search path finds it now: the
        # Japanese one from data/lang/ja/ (the image cache would give the English one again)
        check = ('var b = kag.current.names["start"], t = new global.Layer(kag, kag.primaryLayer);'
                 ' t.loadImages("start_normal"); var diff = 0;'
                 ' for (var y = 4; y < t.imageHeight; y += 4) for (var x = 4; x < t.imageWidth; x += 4)'
                 ' if ((b.getMainPixel(x, y) & 0xffffff) != (t.getMainPixel(x, y) & 0xffffff)) diff++;'
                 ' invalidate t; return Storages.getPlacedPath(getExistImageName("start_normal")) + "|" + diff;')
        switch_language(eng, "ja", "title.ks")
        placed, diff = str(eng.tjs(check)).split("|")
        print("     Japanese: start_normal from %s, %s samples unlike it" % (placed, diff), flush=True)
        # (any format: a release converts the pictures; in an archive the path follows its ">")
        in_lang = lambda p, code: re.search(r"(^|[/>])lang/%s/" % code, p.replace("\\", "/")) is not None
        if not in_lang(placed, "ja") or diff != "0":
            raise SmokeError("the title's Start button isn't data/lang/ja's image (%s, %s samples differ)" % (placed, diff))
        switch_language(eng, "en", "title.ks")
        placed, diff = str(eng.tjs(check)).split("|")
        if in_lang(placed, "[^/]+") or diff != "0":
            raise SmokeError("back in English, the Start button isn't data/image's (%s, %s samples differ)" % (placed, diff))

    @step("languages: the line on screen is drawn again in the other language, and the backlog keeps what was shown")
    def _():
        if not language_framework(eng):
            print("     (skipped: this build has one language)", flush=True)
            return
        # the other languages are in the compiled scenarios (doc/scn.txt, "Languages")
        if eng.tjs('KAGLoadScript("KAGEnvPlayer.tjs") if typeof global.scnFindCompiled == "undefined";'
                   ' return scnFindCompiled("char.ks") !== void && world_object.scenePlayEnabled ? 1 : 0;') != 1:
            print("     (skipped: char.ks isn't played compiled here)", flush=True)
            return
        eng.tjs('kag.process("char.ks", "*start"); return 1;')
        eng.wait("char.ks", 'kag.conductor.curStorage == "char.ks" && kag.inStable && kag.clickWaiting', timeout=30)
        # click on to Ai's first line
        for _ in range(12):
            name, units = page_text(eng)
            if name == "Ai" and units:
                break
            eng.tjs("kag.onPrimaryClick(); return 1;")
            time.sleep(0.2)
            eng.wait("a click wait", 'kag.inStable && kag.clickWaiting && kag.transCount == 0', timeout=30)
        else:
            raise SmokeError("no line of Ai's in char.ks's first lines (the page: %s %s)" % (name, units))
        texts = units[-1][0]
        source, ja = texts.get("en", ""), texts.get("ja", "")
        print("     English: [%s] %s" % (name, units[-1][1]), flush=True)
        # the space a line breaks at isn't drawn (the word wrap)
        squeeze = lambda t: "".join(t.split())
        if source == "" or ja == "" or ja == source or squeeze(units[-1][1]) != squeeze(source):
            raise SmokeError("the line isn't drawn in English as written, with its Japanese in the compiled scene: %s" % (units,))
        switch_language(eng, "ja", "char.ks")
        name, units = page_text(eng)
        print("     Japanese: [%s] %s" % (name, units[-1][1] if units else ""), flush=True)
        if name != "あい" or not units or units[-1][0].get("en") != source or squeeze(units[-1][1]) != squeeze(ja):
            raise SmokeError("after F9 the line isn't drawn again in Japanese: [%s] %s (the scene has %s)" % (name, units, ja))
        if eng.tjs("return kag.clickWaiting && kag.lineBreak.visible || kag.pageBreak.visible ? 1 : 0;") != 1:
            raise SmokeError("the click-wait glyph is gone after the redraw")
        # the backlog has the line in English, as it was shown, and the next line in Japanese
        eng.tjs("kag.onPrimaryClick(); return 1;")
        eng.wait("the next line", 'kag.inStable && kag.clickWaiting && kag.transCount == 0', timeout=30)
        name2, units2 = page_text(eng)
        backlog = str(eng.tjs('var h = kag.historyLayer, r = [];'
                              ' for (var i = 0; i < h.dataLines; i++) r.add(h.getLine(i)); r.add(h.currentLine);'
                              ' return r.join("\\n");'))
        print("     next: [%s] %s" % (name2, units2[-1][1] if units2 else ""), flush=True)
        if squeeze(source) not in squeeze(backlog) or squeeze(ja) in squeeze(backlog):
            raise SmokeError("the backlog doesn't keep the line as it was shown in English:\n" + backlog[-600:])
        if not units2 or squeeze(units2[-1][1]) != squeeze(units2[-1][0].get("ja", "")) or \
                squeeze(units2[-1][1]) not in squeeze(backlog):
            raise SmokeError("the next line isn't in Japanese, in the window and the backlog: %s\n%s" % (units2, backlog[-600:]))
        switch_language(eng, "en", "char.ks")
        name3, units3 = page_text(eng)
        if not units3 or squeeze(units3[-1][1]) != squeeze(units3[-1][0].get("en", "")):
            raise SmokeError("F9 again didn't draw the line in English: %s" % (units3,))
        eng.tjs("kag.goToStart(); return 1;")
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("languages: the demo menu's choices are drawn again in the other language")
    def _():
        if not language_framework(eng):
            print("     (skipped: this build has one language)", flush=True)
            return
        # the choices' other languages are in the compiled scenario (KAG's own player shows them as written)
        if eng.tjs('KAGLoadScript("KAGEnvPlayer.tjs") if typeof global.scnFindCompiled == "undefined";'
                   ' return scnFindCompiled("s0001.ks") !== void && world_object.scenePlayEnabled ? 1 : 0;') != 1:
            print("     (skipped: s0001.ks isn't played compiled here)", flush=True)
            return
        eng.tjs('kag.process("s0001.ks", "*start"); return 1;')
        eng.wait("the demo menu", 'kag.conductor.curStorage == "s0001.ks" && kag.inStable && kag.selectShowing'
                 ' && kag.transCount == 0', timeout=30)
        labels = ('var s = kag.selectLayer, r = []; for (var i = 0; i < s.selects.count; i++)'
                  ' r.add(s.selects[i].text + "=" + s.selects[i].message); return r.join("|");')
        switch_language(eng, "ja", "s0001.ks")
        ja = [x.split("=", 1) for x in str(eng.tjs(labels)).split("|")]
        print("     %s" % ", ".join(m for _, m in ja[:3]), flush=True)
        if not ja or any(t == m for t, m in ja):
            raise SmokeError("a choice kept its English label: %s" % ja)
        switch_language(eng, "en", "s0001.ks")
        en = [x.split("=", 1) for x in str(eng.tjs(labels)).split("|")]
        if any(t != m for t, m in en):
            raise SmokeError("a choice isn't back in English: %s" % en)
        eng.tjs("kag.goToStart(); return 1;")
        eng.wait("title.ks", 'kag.conductor.curStorage == "title.ks" && kag.inStable', timeout=30)

    @step("languages: Config's buttons choose one, the screen is drawn in it, and the choice is saved")
    def _():
        if not language_framework(eng) or eng.tjs('return typeof global.setLanguageButton != "undefined" ? 1 : 0;') != 1:
            print("     (skipped: this build has one language)", flush=True)
            return
        eng.tjs('kag.process("config.ks", "*startFromTitle"); return 1;')
        eng.wait("config.ks", 'kag.conductor.curStorage == "config.ks" && kag.inStable && kag.transCount == 0', timeout=20)
        eng.tjs('kag.current.names["config_lang_ja"].onExecute(); return 1;'
                if eng.tjs('return typeof kag.current.names["config_lang_ja"] == "Object" ? 1 : 0;') == 1
                else 'setLanguageButton("ja"); return 1;')
        eng.wait("Japanese", 'KAGLanguage.current == "ja" && kag.conductor.curStorage == "config.ks" && kag.inStable'
                 ' && kag.transCount == 0', timeout=20)
        r = str(eng.tjs('return [KAGLanguage.chosen ? 1 : 0, kag.scflags.language, Storages.getPlacedPath(getExistImageName("config_base"))].join("|");'))
        print("     chosen, saved, config_base: %s" % r, flush=True)
        chosen, saved, placed = r.split("|")
        if chosen != "1" or saved != "ja" or not re.search(r"(^|[/>])lang/ja/", placed.replace("\\", "/")):
            raise SmokeError("Config's 日本語 button didn't choose Japanese and keep it: %s" % r)
        eng.tjs('setLanguageButton("en"); return 1;')
        eng.wait("English", 'KAGLanguage.current == "en" && kag.conductor.curStorage == "config.ks" && kag.inStable'
                 ' && kag.transCount == 0', timeout=20)
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
    # A Windows console's code page (cp1252) has no Japanese: the line-breaking steps' text
    # stopped the whole run there with a UnicodeEncodeError. Write what it can't show escaped
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
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
    ap.add_argument("--live2d", choices=["required", "optional"], default="optional",
                    help="whether the build must draw Live2D characters (the krkrlive2d plugin, OpenGL ES "
                    "and Hiyori's model, tools/assets/make_hiyori.py): required fails when it can't; "
                    "optional tests the framework with a stand-in for the plugin (tools/live2d-standin.tjs)")
    ap.add_argument("--three", choices=["required", "optional"], default="optional",
                    help="whether the build must draw 3D (the krkrthreepp plugin and OpenGL ES: the 3d flip "
                    "and VRM characters): required fails when it can't; optional skips those checks")
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
