#!/usr/bin/env python3
"""Smoke test of kagex-release on a copy of the sample game.

  smoke.py <kagex-release executable> [--browser] [--out DIR] [--engines DIR]

- the CLI: init, check, plan (and --json), on a copy of data/, template/system, krkrz.cf and
  platform/ in a temporary folder
- the window's server, without a browser: the page and the API (state, check, host, save)
- --browser: the screen in headless Chromium (Playwright): no script errors, the sections and
  the check filled in, a setting changed and saved with Ctrl+S; screenshots go to --out
- --engines: builds with those engine packages (kagex_engine_*.zip): Windows, Linux and Steam
  (and macOS on a Mac), with the test run; then data bound into the exe, a data folder and only
  the linked plugins; the packages are checked. Then the media: WAV, FLAC (with loop points) and
  images converted, files the scripts name kept and then rewritten, the conversion cache, and on
  Linux the converted build in the engine (a button's hover image found, the button highlighted)
"""
import argparse
import hashlib
import json
import os
import platform as hostplatform
import re
import tarfile
import zipfile
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
failures = []


def step(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (": " + detail if detail else ""), flush=True)
    if not ok:
        failures.append(name)


def run(exe, *args, cwd=None):
    r = subprocess.run([str(exe), *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    return r.returncode, r.stdout + r.stderr


def make_project(tmp):
    proj = tmp / "My Game"
    shutil.copytree(REPO / "data", proj / "data")
    shutil.copytree(REPO / "template" / "system", proj / "template" / "system")
    shutil.copytree(REPO / "platform", proj / "platform")
    shutil.copyfile(REPO / "krkrz.cf", proj / "krkrz.cf")
    (proj / "data" / "work").mkdir()
    (proj / "data" / "work" / "draft.txt").write_text("left out by the exclusions")
    (proj / "data" / "image" / "layers.psd").write_bytes(b"8BPS")
    return proj


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def api(port, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data,
                                 headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8")
        return json.loads(text) if r.headers.get("Content-Type", "").startswith("application/json") else text


def cli_tests(exe, proj):
    code, out = run(exe, "--help")
    step("--help", code == 0 and "--cli" in out and "--platform" in out, out.splitlines()[0] if out else "")
    code, out = run(exe, "--version")
    step("--version", code == 0 and "0." in out, out.strip())

    code, out = run(exe, "--cli", "plan", str(proj))
    step("plan before init (defaults)", code == 0 and "Game files:" in out, out.splitlines()[0] if out else "")

    code, out = run(exe, "--cli", "init", str(proj))
    rel = proj / "release.json"
    step("init writes release.json", code == 0 and rel.exists(), out.strip())
    s = json.loads(rel.read_text(encoding="utf-8"))
    ident = s["identity"]
    step("defaults from first.ks", ident["title"] == "KAGEX Sample" and ident["version"] and ident["exeName"] == "kagex-sample",
         "%s / %s / %s" % (ident["title"], ident["version"], ident["exeName"]))
    step("the sample's save-folder names aren't taken over", (ident["orgName"], ident["appName"]) != ("krkren", "kagex"),
         ident["orgName"] + "/" + ident["appName"])
    step("icon found", ident["icon"] == "platform/icon-1024.png", ident["icon"])
    code, out = run(exe, "--cli", "init", str(proj))
    step("init refuses to replace", code == 2 and "already" in out, out.strip())

    code, out = run(exe, "--cli", "check", str(rel), "--json")
    try:
        chk = json.loads(out)
    except ValueError:
        chk = {"issues": [{"level": "error", "message": out}], "platforms": []}
    errors = [i for i in chk["issues"] if i["level"] == "error"]
    step("check: the defaults have no errors", not errors, "; ".join(i["message"] for i in errors))
    step("check: the host platform is listed", len(chk["platforms"]) == 1, ", ".join(p["id"] for p in chk["platforms"]))

    # a broken setting is reported, with exit code 1
    bad = dict(s)
    bad["identity"] = dict(ident, version="1.0 beta", orgName="krkren", appName="kagex")
    bad_file = proj / "bad.json"
    bad_file.write_text(json.dumps(bad), encoding="utf-8")
    code, out = run(exe, "--cli", "check", str(bad_file), "--json")
    fields = [i["field"] for i in json.loads(out)["issues"] if i["level"] == "error"]
    step("check: reports a bad version and reserved names", code == 1 and "identity.version" in fields and "identity.appName" in fields, ", ".join(fields))
    bad_file.unlink()

    # a framework from before 0.3.0 (no .opus) and 0.3.1 (button images found as .png, .tlg5,
    # .tlg6 and .bmp only) is told to keep its sounds and images in formats it finds
    fw = proj / "template" / "system"
    saved = {n: (fw / n).read_bytes() for n in ("BGM.tjs", "MessageLayer.tjs")}
    (fw / "BGM.tjs").write_bytes(saved["BGM.tjs"].replace(b'"opus", ', b""))
    (fw / "MessageLayer.tjs").write_bytes(saved["MessageLayer.tjs"].replace(b"global.Layer.SupportedExtensions", b'[ "png", "tlg5", "tlg6", "bmp" ]'))
    code, out = run(exe, "--cli", "check", str(rel), "--json")
    for n, b in saved.items():
        (fw / n).write_bytes(b)
    fields = [i["field"] for i in json.loads(out)["issues"] if i["level"] == "error"]
    step("check: an older framework refuses Opus and TLG", code == 1 and "media.audio.convert" in fields and "media.images.alpha" in fields, ", ".join(fields))

    code, out = run(exe, "--cli", "plan", str(rel), "--json", "--platform=windows,linux,web,android,ios")
    plan = json.loads(out)
    step("plan: the chosen platforms", [o["platform"] for o in plan["outputs"]] == ["windows", "linux", "web", "android", "ios"],
         ", ".join(o["platform"] for o in plan["outputs"]))
    d = plan["data"]
    step("plan: exclusions (work/ isn't excluded by default, *.psd is)", d["excluded"] >= 1, "%d files, %d excluded" % (d["files"], d["excluded"]))
    step("plan: images and sounds to convert", d["convertImages"] > 50, "%d images, %d sounds" % (d["convertImages"], d["convertAudio"]))
    step("plan: framework copied in", "template/system" in d["framework"], d["framework"])
    code, out = run(exe, "--cli", "plan", str(rel), "--platform=nowhere")
    step("an unknown platform is refused", code != 0, out.strip().splitlines()[0] if out.strip() else "")


def server_tests(exe, proj, args):
    port = free_port()
    env = dict(os.environ)
    if args.engines:
        env["KAGEX_RELEASE_ENGINES"] = str(Path(args.engines).resolve())
    proc = subprocess.Popen([str(exe), str(proj), "--no-browser", "--no-token", "--port=%d" % port, "--idle-timeout=0"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env)
    try:
        for _ in range(100):
            try:
                html = api(port, "/")
                break
            except OSError:
                time.sleep(0.1)
        else:
            step("the server starts", False)
            return
        step("the page is served", "KAGEX Release" in html)
        step("the client library is embedded", "class Appserve" in api(port, "/lib/appserve.js"))
        st = api(port, "/api/release/state")
        step("state", st.get("exists") is True and st["settings"]["identity"]["title"] == "KAGEX Sample" and len(st["platforms"]) == 7,
             st.get("file", st.get("error", "")))
        s = st["settings"]
        s["platforms"]["android"]["enabled"] = True
        s["platforms"]["android"]["applicationId"] = "1bad"
        chk = api(port, "/api/release/check", {"settings": s})
        step("check from the screen", any(i["field"] == "platforms.android.applicationId" for i in chk["issues"]) and chk["plan"]["outputs"],
             "; ".join(i["field"] for i in chk["issues"]))
        host = api(port, "/api/release/host", {"settings": s})
        step("host status for every platform", sorted(h["id"] for h in host) == sorted(p["id"] for p in st["platforms"]),
             ", ".join("%s=%s" % (h["id"], h["possible"]) for h in host))
        s["platforms"]["android"]["applicationId"] = "com.example.mygame"
        api(port, "/api/release/save", {"settings": s})
        saved = json.loads((proj / "release.json").read_text(encoding="utf-8"))
        step("save", saved["platforms"]["android"]["applicationId"] == "com.example.mygame")
        if args.browser:
            browser_tests(port, proj, args)
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
        if args.out:
            (Path(args.out) / "server.log").write_text(out, encoding="utf-8")


def browser_tests(port, proj, args):
    from playwright.sync_api import sync_playwright
    out = Path(args.out or tempfile.mkdtemp())
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch()
        for scheme in ("light", "dark"):
            page = b.new_page(viewport={"width": 1280, "height": 900}, color_scheme=scheme)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.goto("http://127.0.0.1:%d/" % port)
            page.wait_for_selector("#sec-plan .output", timeout=30000)
            page.wait_for_function("!document.querySelector('.status.pending')", timeout=60000)
            page.screenshot(path=str(out / ("screen-%s.png" % scheme)), full_page=True)
            step("screen (%s): no script errors" % scheme, not errors, "; ".join(errors))
            if scheme == "dark":
                break
            step("screen: every section", page.locator("section.card").count() == 6)
            step("screen: the title field", page.locator("#sec-game input").first.input_value() == "KAGEX Sample")
            # turn on the web build and save with Ctrl+S
            page.locator("#pl-web").check()
            page.wait_for_selector("#sec-plan .output >> text=Web")
            page.keyboard.press("Control+s")
            page.wait_for_function("document.querySelector('#saveState').textContent === 'Saved'", timeout=10000)
            saved = json.loads((proj / "release.json").read_text(encoding="utf-8"))
            step("screen: a platform turned on and saved", saved["platforms"]["web"]["enabled"] is True)
            # a bad value shows next to its field
            ver = page.locator("#sec-game input").nth(3)
            ver.fill("one")
            page.wait_for_selector("#sec-game .issue.error", timeout=10000)
            step("screen: a bad version is shown at its field", "numbers" in page.locator("#sec-game .issue.error").first.text_content())
            page.screenshot(path=str(out / "screen-error.png"), full_page=False)
            if args.engines:
                # build this computer's platform from the window
                ver.fill(saved["identity"]["version"])
                page.locator("#pl-web").uncheck()
                page.locator("#pl-android").uncheck()
                page.wait_for_function("!document.querySelector('#sec-game .issue.error')", timeout=10000)
                page.wait_for_timeout(500)
                page.click("#build")
                page.wait_for_function("(document.querySelector('.build-dialog .dialog-title') || {}).textContent?.startsWith('Built')", timeout=600000)
                page.screenshot(path=str(out / "screen-build.png"), full_page=False)
                title = page.locator(".build-dialog .dialog-title").text_content()
                results = page.locator(".build-dialog .results").text_content()
                step("screen: build from the window", title == "Built" and "Linux" in results and "Test run" in results, title + ": " + results[:300])
            page.close()
        b.close()


XP3_MARK = b"XP3\r\n \n\x1a\x8b\x67\x01"


def host_id():
    return {"Windows": "windows", "Darwin": "macos"}.get(hostplatform.system(), "linux")


def build_tests(exe, proj, args):
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    names = ["windows", "linux", "steam"] + (["macos"] if host_id() == "macos" else [])
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = p in names
    s["output"]["check"] = True
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json")
    try:
        r = json.loads(out[out.index("{"):])
    except ValueError:
        step("build", False, out[-2000:])
        return
    if args.out:
        (Path(args.out) / "build.json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    outs = {o["platform"]: o for o in r["outputs"]}
    step("build: every platform", all(outs.get(n, {}).get("ok") for n in names),
         "; ".join("%s=%s" % (n, outs.get(n, {}).get("ok") or outs.get(n, {}).get("error")) for n in names) + (" " + r.get("error", "")))
    base = "kagex-sample-%s-" % s["identity"]["version"]
    outdir = proj / "release"
    cf_ok = lambda t: "orgname=krkren\n" in t and "appname=kagex-sample\n" in t and "debugwin=no\n" in t

    w = outdir / (base + "windows.zip")
    if w.exists():
        z = zipfile.ZipFile(w)
        n = base + "windows/"
        step("windows: zip with the exe, .cf, SDL3.dll, plugins and data.xp3",
             z.testzip() is None and {n + "kagex-sample.exe", n + "kagex-sample.cf", n + "SDL3.dll", n + "data.xp3"} <= set(z.namelist())
             and any(x.startswith(n + "plugin/") for x in z.namelist()))
        step("windows: the .cf", cf_ok(z.read(n + "kagex-sample.cf").decode()), z.read(n + "kagex-sample.cf").decode().replace("\n", " | "))
        if host_id() == "windows":
            exe_data = z.read(n + "kagex-sample.exe")
            step("windows: the icon and version info", "KAGEX Sample".encode("utf-16-le") in exe_data)
    for p in ("linux", "steam"):
        t = outdir / (base + p + ".tar.gz")
        if not t.exists():
            continue
        with tarfile.open(t) as tf:
            m = {x.name: x for x in tf.getmembers()}
            n = base + p + "/"
            step(p + ": tar.gz with an executable engine", n + "kagex-sample" in m and m[n + "kagex-sample"].mode & 0o111 != 0
                 and n + "libSDL3.so.0" in m and n + "data.xp3" in m, oct(m[n + "kagex-sample"].mode) if n + "kagex-sample" in m else "missing")
            step(p + ": the .cf", cf_ok(tf.extractfile(n + "kagex-sample.cf").read().decode()))
            if p == "linux":
                step("linux: menu entry and icon", n + "kagex-sample.desktop" in m and n + "kagex-sample.png" in m)
    if "macos" in names:
        mz = outdir / (base + "macos.zip")
        if mz.exists():
            z = zipfile.ZipFile(mz)
            app = "KAGEX Sample.app/Contents/"
            nl = set(z.namelist())
            plist = z.read(app + "Info.plist").decode() if app + "Info.plist" in nl else ""
            step("macos: the app with data.xp3, its icon and .cf",
                 {app + "Resources/data.xp3", app + "Resources/AppIcon.icns", app + "MacOS/krkrz.cf", app + "MacOS/krkrz"} <= nl)
            step("macos: Info.plist", "com.krkren.kagexsample" in plist and "<string>KAGEX Sample</string>" in plist)
            app_dir = outdir / (base + "macos") / "KAGEX Sample.app"
            c, o = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app_dir)], capture_output=True, text=True).returncode, ""
            step("macos: the signature verifies", c == 0)
    sums = (outdir / "SHA256SUMS").read_text().splitlines() if (outdir / "SHA256SUMS").exists() else []
    good = all(hashlib.sha256((outdir / l.split("  ", 1)[1]).read_bytes()).hexdigest() == l.split("  ", 1)[0] for l in sums)
    step("SHA256SUMS", len(sums) == len(names) and good, "%d lines" % len(sums))
    if args.out and (outdir / "test-run.log").exists():
        shutil.copyfile(outdir / "test-run.log", Path(args.out) / "test-run.log")
    chk = r.get("check", {})
    step("test run of this computer's build", chk.get("ok") is True, chk.get("message", "") + " " + "; ".join(chk.get("errors", [])))

    # variants: data bound into the executables (the test run shows the engine finds it), a data
    # folder in a zip, only the linked plugins
    s["platforms"]["windows"]["data"] = "bind"
    s["platforms"]["linux"]["data"] = "bind"
    s["platforms"]["steam"]["data"] = "folder"
    s["platforms"]["macos"]["enabled"] = False
    s["output"]["archive"] = "zip"
    s["contents"]["plugins"] = "linked"
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--platform=windows,linux,steam", "--json")
    try:
        r = json.loads(out[out.index("{"):])
    except ValueError:
        step("build variants", False, out[-2000:])
        return
    step("build variants", r["ok"], r.get("error", "") + "; ".join(o.get("error", "") for o in r["outputs"]))
    w = outdir / (base + "windows.zip")
    if w.exists():
        z = zipfile.ZipFile(w)
        n = base + "windows/"
        data = z.read(n + "kagex-sample.exe")
        with zipfile.ZipFile(Path(args.engines) / "kagex_engine_windows.zip") as ez:
            original = ez.getinfo("krkrz.exe").file_size
        # the exe's own size changes with its icon and version info: the xp3 is the last mark
        at = data.rfind(XP3_MARK)
        step("windows: data bound into the exe", at > original // 2 and at % 16 == 0 and n + "data.xp3" not in z.namelist(),
             "engine %d bytes, xp3 at %d of %d" % (original, at, len(data)))
        plugins = [x for x in z.namelist() if x.startswith(n + "plugin/") and not x.endswith("/")]
        step("windows: only the linked plugins", 0 < len(plugins) < 27, "%d plugins" % len(plugins))
    lz = outdir / (base + "steam.zip")
    if lz.exists():
        z = zipfile.ZipFile(lz)
        n = base + "steam/"
        info = z.getinfo(n + "kagex-sample")
        step("steam: zip with a data folder and the executable flag", n + "data/startup.tjs" in z.namelist() and n + "data/system/Initialize.tjs" in z.namelist()
             and (info.external_attr >> 16) & 0o111 != 0)
    if args.out and (outdir / "test-run.log").exists():
        shutil.copyfile(outdir / "test-run.log", Path(args.out) / "test-run-bound.log")
    if host_id() in ("windows", "linux"):
        chk = r.get("check", {})
        step("test run with the data bound into the executable", chk.get("ok") is True, chk.get("message", "") + " " + "; ".join(chk.get("errors", [])))


def web_tests(exe, proj, args):
    """The web build, as files and as one data.xp3; with --browser, each runs in Chromium"""
    import functools
    import http.server
    import threading
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = p == "web"
    s["output"]["archive"] = "zip"
    s["output"]["check"] = False
    site = proj / "release" / ("kagex-sample-%s-web" % s["identity"]["version"])
    s["platforms"]["web"]["url"] = "https://studio.example/game"
    s["platforms"]["web"]["description"] = "A test & a <preview>"
    builds = {}
    for mode in ("files", "xp3"):
        s["platforms"]["web"]["data"] = mode
        rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
        code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json")
        try:
            r = json.loads(out[out.index("{"):])
        except ValueError:
            r = {"ok": False, "error": out[-2000:], "outputs": []}
        step("web (%s): build" % mode, r["ok"], r.get("error", "") + "; ".join(o.get("error", "") for o in r["outputs"]))
        if not r["ok"]:
            continue
        cfg = (site / "webconfig.js").read_text(encoding="utf-8")
        html = (site / "index.html").read_text(encoding="utf-8")
        js = (site / "krkrz.js").read_text(encoding="utf-8", errors="replace")
        data_size = (site / "krkrz.data").stat().st_size
        step("web (%s): engine options" % mode, "-appname=kagex-sample" in cfg and "-debugwin=no" in cfg and "-bitmappoolsize=" in cfg, cfg.replace("\n", " | ")[-300:])
        step("web (%s): title, manifest and icons" % mode, "<title>KAGEX Sample</title>" in html and "window.coi=" in html and "manifest.webmanifest" in html
             and json.loads((site / "manifest.webmanifest").read_text())["name"] == "KAGEX Sample" and (site / "icon-512.png").exists())
        build = json.loads((site / "kagex-build.json").read_text())["build"] if (site / "kagex-build.json").exists() else ""
        builds[mode] = build
        scripts = re.findall(r'<script src="?([^" >]+)', html)
        step("web (%s): the build's id in the page and its scripts" % mode,
             len(build) == 16 and ('<meta name=kagex-build content="%s">' % build) in html and (site / "kagex-web.js").exists()
             and scripts[-3:] == ["kagex-web.js?v=" + build, "webconfig.js?v=" + build, "krkrz.js?v=" + build], "%s %s" % (build, scripts))
        step("web (%s): link previews" % mode,
             '<meta property=og:image content="https://studio.example/game/preview.jpg">' in html and (site / "preview.jpg").exists()
             and '<meta property=og:description content="A test &amp; a &lt;preview&gt;">' in html
             and "<meta name=twitter:card content=summary_large_image>" in html and html.count("<!--kagex-head-->") == 1
             and html.count("apple-mobile-web-app-capable") == 1)
        step("web (%s): krkrz.data is what krkrz.js expects" % mode, ("end:%d}],remote_package_size:%d" % (data_size, data_size)) in js, "%d bytes" % data_size)
        if mode == "files":
            files = json.loads((site / "gamedata.krkrz_files.json").read_text())
            step("web (files): the files, in lower case", "startup.tjs" in files and "system/initialize.tjs" in files and "image/title.tlg" in files
                 and (site / "gamedata" / "system" / "initialize.tjs").exists() and (site / "gamedata" / "krkrz_files.json").exists()
                 and 'KRKRZ_WEB_DEFAULT_WEBBASE = "gamedata/"' in cfg and data_size == 0, "%d files" % len(files))
        else:
            step("web (xp3): data.xp3 preloaded", data_size > 1000000 and not (site / "gamedata").exists() and "KRKRZ_WEB_DATA_XP3 = true" in cfg)
        if not args.browser:
            continue
        sys.path.insert(0, str(REPO / "tools"))
        import smoketest
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):
                pass
        handler = functools.partial(Quiet, directory=str(site))
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        work = Path(tempfile.mkdtemp())
        eng = None
        try:
            eng = smoketest.WebEngine("http://127.0.0.1:%d/" % httpd.server_address[1], str(work), False)
            res = eng._eval('kag.conductor.curStorage', 60)
            time.sleep(5)
            errors = [l for l in eng.lines if "Script exception raised" in l or "! trace :" in l]
            step("web (%s): the game starts in the browser" % mode, res.get("ok") and not errors, str(res.get("result")) + " " + "; ".join(errors[:3]))
            if args.out:
                eng.snapshot(str(Path(args.out) / ("web-%s.png" % mode)))
        except Exception as e:
            step("web (%s): the game starts in the browser" % mode, False, str(e)[:1500])
        finally:
            if eng:
                if args.out:
                    shutil.copyfile(eng.log_path, Path(args.out) / ("web-%s-console.txt" % mode))
                eng.stop()
            httpd.shutdown()
    step("web: another build, another id (players' pages and caches update)", builds.get("files") and builds.get("xp3") and builds["files"] != builds["xp3"],
         "%s / %s" % (builds.get("files"), builds.get("xp3")))


def android_tests(exe, proj, args):
    """An APK (debug-signed, data.xp3) and an app bundle (data folder), with the JDK and SDK here"""
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk or not shutil.which("java"):
        print("skip android: no JDK or Android SDK here")
        return
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = p == "android"
    s["output"]["check"] = False
    a = s["platforms"]["android"]
    a.update({"format": "apk", "data": "xp3", "applicationId": "com.example.kagexsample", "versionCode": 0, "keystore": "", "keyAlias": ""})
    version = s["identity"]["version"]
    for fmt, data in (("apk", "xp3"), ("aab", "folder")):
        a["format"], a["data"] = fmt, data
        rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
        code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json")
        try:
            r = json.loads(out[out.index("{"):])
        except ValueError:
            r = {"ok": False, "error": out[-2000:], "outputs": []}
        if args.out and (proj / "release" / "android-build.log").exists():
            shutil.copyfile(proj / "release" / "android-build.log", Path(args.out) / ("android-%s.log" % fmt))
        step("android (%s): build" % fmt, r["ok"], r.get("error", "") + "; ".join(o.get("error", "") for o in r["outputs"]))
        pkg = proj / "release" / ("kagex-sample-%s.%s" % (version, fmt))
        if not pkg.exists():
            continue
        with zipfile.ZipFile(pkg) as z:
            names = set(z.namelist())
            prefix = "base/" if fmt == "aab" else ""
            libs = [n for n in names if n.startswith(prefix + "lib/") and n.endswith("libkrkrz.so")]
            if data == "xp3":
                info = z.getinfo(prefix + "assets/data.xp3") if prefix + "assets/data.xp3" in names else None
                step("android (%s): data.xp3, stored uncompressed, and the engine" % fmt, info is not None and info.compress_type == zipfile.ZIP_STORED and len(libs) == 2,
                     "%s; %s" % (info and info.compress_type, libs))
            else:
                step("android (%s): the data folder and the engine" % fmt, prefix + "assets/data/startup.tjs" in names and len(libs) == 2, "; ".join(libs))
        if fmt == "apk":
            tools = sorted(Path(sdk, "build-tools").glob("*"))
            aapt2 = next((t / "aapt2" for t in reversed(tools) if (t / "aapt2").exists()), None)
            if aapt2:
                badging = subprocess.run([str(aapt2), "dump", "badging", str(pkg)], capture_output=True, text=True).stdout
                step("android: package name, version and label", "name='com.example.kagexsample'" in badging and "versionCode='%d'" % (
                    int(version.split(".")[0]) * 10000 + int(version.split(".")[1]) * 100 + int((version.split(".") + ["0"])[2])) in badging
                     and "application-label:'KAGEX Sample'" in badging, badging.splitlines()[0] if badging else "no output")


def ios_tests(exe, proj, args):
    """The Simulator app (installed and started in a Simulator) and a device .ipa, signed ad hoc
    with a stand-in profile (an unsigned plist), on a Mac with Xcode"""
    if host_id() != "macos" or not shutil.which("xcrun"):
        return
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = p == "ios"
    s["output"]["check"] = False
    profile = proj / "test.mobileprovision"
    import plistlib
    profile.write_bytes(plistlib.dumps({"Name": "kagex-release test", "Entitlements": {
        "application-identifier": "ABCDE12345.com.example.kagexsample", "get-task-allow": True}}))
    i = s["platforms"]["ios"]
    i.update({"bundleId": "com.example.kagexsample", "buildNumber": 0, "identity": "-", "profile": "test.mobileprovision", "data": "xp3"})
    version = s["identity"]["version"]
    for target in ("simulator", "device"):
        i["target"] = target
        rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
        code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json")
        try:
            r = json.loads(out[out.index("{"):])
        except ValueError:
            r = {"ok": False, "error": out[-2000:], "outputs": []}
        step("ios (%s): build" % target, r["ok"], r.get("error", "") + "; ".join(o.get("error", "") for o in r["outputs"]))
        pkg = proj / "release" / (("kagex-sample-%s-ios-simulator.zip" % version) if target == "simulator" else ("kagex-sample-%s.ipa" % version))
        if not pkg.exists():
            continue
        work = Path(tempfile.mkdtemp())
        subprocess.run(["ditto", "-x", "-k", str(pkg), str(work)], check=False)
        app = work / ("Payload" if target == "device" else "") / "kagex-sample.app"
        info = plistlib.loads((app / "Info.plist").read_bytes()) if (app / "Info.plist").exists() else {}
        step("ios (%s): Info.plist" % target, info.get("CFBundleIdentifier") == "com.example.kagexsample" and info.get("CFBundleShortVersionString") == version
             and info.get("CFBundleDisplayName") == s["identity"]["shortName"], str({k: info.get(k) for k in ("CFBundleIdentifier", "CFBundleDisplayName", "CFBundleVersion")}))
        step("ios (%s): data.xp3 and the icon" % target, (app / "data.xp3").exists() and (app / "Assets.car").exists() and "CFBundleIcons" in info)
        v = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], capture_output=True, text=True)
        step("ios (%s): the signature verifies" % target, v.returncode == 0, v.stderr.strip()[:300])
        if target == "device":
            ents = subprocess.run(["codesign", "-d", "--entitlements", ":-", str(app)], capture_output=True, text=True).stdout
            step("ios (device): the profile and its entitlements", (app / "embedded.mobileprovision").exists() and "ABCDE12345.com.example.kagexsample" in ents)
            continue
        # the Simulator app starts
        devs = json.loads(subprocess.run(["xcrun", "simctl", "list", "devices", "available", "-j"], capture_output=True, text=True).stdout)["devices"]
        udid = next((d["udid"] for k, v in devs.items() if "iOS" in k for d in v if "iPhone" in d["name"]), None)
        if not udid:
            step("ios (simulator): a Simulator to run it in", False)
            continue
        subprocess.run(["xcrun", "simctl", "boot", udid], capture_output=True)
        subprocess.run(["xcrun", "simctl", "bootstatus", udid, "-b"], capture_output=True, timeout=600)
        inst = subprocess.run(["xcrun", "simctl", "install", udid, str(app)], capture_output=True, text=True)
        launch = subprocess.run(["xcrun", "simctl", "launch", udid, "com.example.kagexsample"], capture_output=True, text=True)
        time.sleep(15)
        running = subprocess.run(["xcrun", "simctl", "spawn", udid, "launchctl", "list"], capture_output=True, text=True).stdout
        alive = any("com.example.kagexsample" in l and l.split()[0] != "-" for l in running.splitlines())
        step("ios (simulator): installs and keeps running", inst.returncode == 0 and launch.returncode == 0 and alive,
             (inst.stderr + launch.stdout + launch.stderr).strip()[:300])
        subprocess.run(["xcrun", "simctl", "shutdown", udid], capture_output=True)


def write_wav(path, frames, rate=44100):
    import math
    import struct
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<hh", int(6000 * math.sin(i / 17)), int(6000 * math.sin(i / 23))) for i in range(frames)))


def write_flac(path, frames, rate=44100):
    """A 16-bit stereo FLAC with verbatim subframes (enough to test the decoder)"""
    import math
    import struct

    def crc8(data):
        c = 0
        for b in data:
            c ^= b
            for _ in range(8):
                c = ((c << 1) ^ 0x07) & 0xFF if c & 0x80 else (c << 1) & 0xFF
        return c

    def crc16(data):
        c = 0
        for b in data:
            c ^= b << 8
            for _ in range(8):
                c = ((c << 1) ^ 0x8005) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
        return c

    left = [int(6000 * math.sin(i / 19)) for i in range(frames)]
    right = [int(6000 * math.sin(i / 29)) for i in range(frames)]
    block = 4096
    out = bytearray(b"fLaC")
    info = struct.pack(">HH", block, block) + b"\0\0\0" + b"\0\0\0"
    v = (rate << 44) | (1 << 41) | (15 << 36) | frames   # rate 20 bits, channels-1 3, bps-1 5, samples 36
    info += v.to_bytes(8, "big") + b"\0" * 16
    out += bytes([0x80, 0, 0, 34]) + info
    for n, start in enumerate(range(0, frames, block)):
        size = min(block, frames - start)
        h = bytearray([0xFF, 0xF8])
        bs_code = 0b1100 if size == block else 0b0111
        h.append((bs_code << 4) | 0b1001)          # block size, 44.1 kHz
        h.append((0b0001 << 4) | (0b100 << 1))     # two channels, 16 bits
        h += bytes([n]) if n < 0x80 else bytes([0xC0 | (n >> 6), 0x80 | (n & 63)])
        if bs_code == 0b0111:
            h += struct.pack(">H", size - 1)
        h.append(crc8(h))
        frame = bytearray(h)
        for ch in (left, right):
            frame.append(0x02)                     # verbatim
            frame += b"".join(struct.pack(">h", x) for x in ch[start:start + size])
        frame += struct.pack(">H", crc16(frame))
        out += frame
    path.write_bytes(bytes(out))


def converted_game_tests(game, args):
    """The build with converted images, in the engine here (headless on Linux): a button finds its hover
    image (start_over is a .tlg now; up to 0.3.0 the framework looked for .png, .tlg5, .tlg6 and
    .bmp only, so no button highlighted), hovering changes the button, and the CG screen finds
    its prepared thumbnails"""
    sys.path.insert(0, str(REPO / "tools"))
    import smoketest

    class Built(smoketest.FileChannel):
        def __init__(self, exe, work):
            self.chan = str(work / "repl")
            self.modals = []
            os.makedirs(self.chan)
            os.makedirs(work / "save")
            env = dict(os.environ)
            if os.name != "nt":   # Windows: a real window, GLES from ANGLE (as the tool's own test run)
                env.setdefault("SDL_VIDEO_DRIVER", "offscreen")
            env.setdefault("SDL_AUDIO_DRIVER", "dummy")
            self.log_path = str(work / "engine.log")
            self.log = open(self.log_path, "wb")
            self.proc = subprocess.Popen([str(exe), "-datapath=%s/" % (work / "save"), "-replfile=" + self.chan, "-replmodaltimeout=0"],
                                         cwd=str(exe.parent), stdout=self.log, stderr=subprocess.STDOUT, env=env)

        def alive(self):
            if self.proc.poll() is not None:
                raise smoketest.SmokeError("the engine exited (code %s)" % self.proc.returncode)
            return True

        def stop(self):
            if self.proc.poll() is None:
                self.proc.kill()  # a hung engine ignores SIGTERM
                self.proc.wait()
            self.log.close()

    work = Path(tempfile.mkdtemp())
    eng = None
    try:
        eng = Built(game, work)
        eng.wait("the title screen", 'typeof global.kag != "undefined" && global.kag !== void && kag.conductor.curStorage == "title.ks" && kag.inStable', 120)
        found = eng.tjs('var m = kag.fore.messages[0]; return m.getExistName("start_over") + "|" + getExistImageName("thum_event1");')
        step("converted game: a button finds its hover image, the CG screen its thumbnail", found == "start_over.tlg|thum_event1.tlg", str(found))
        # the button's look before and after the pointer enters it
        look = """
            var b = kag.fore.messages[0].names["start"], l = new Layer(kag, kag.primaryLayer), sum = 0;
            l.setImageSize(b.width, b.height);
            l.piledCopy(0, 0, kag.primaryLayer, b.left, b.top, b.width, b.height);
            for (var y = 0; y < b.height; y += 4) for (var x = 0; x < b.width; x += 4) sum += l.getMainPixel(x, y) & 0xffffff;
            invalidate l;
            %s
            return sum;"""
        before = eng.tjs(look % "b.onMouseEnter();")
        time.sleep(1)
        after = eng.tjs(look % "")
        hover = "changed" if before != after else "unchanged"
        step("converted game: hovering a button highlights it", hover == "changed", str(hover))
        # Effekseer effects name their textures (effect/Texture/*.png) inside the effect file,
        # which can't be rewritten, so those keep their format; and where this engine draws
        # effects, one plays
        kept = eng.tjs('var dir = Storages.extractStoragePath(Storages.getPlacedPath("sparkle.efk"));'
                       ' return Storages.isExistentStorage(dir + "Texture/glow.png") ? "png" : "missing";')
        step("converted game: an effect's textures stay PNG", kept == "png", str(kept))
        drawn = eng.tjs("""
            var s = KAGEffekseerOf(kag);
            if (!s.available) return "unavailable: " + s.reason;
            kag.tagHandlers.image(%[layer:"0", page:"fore", flip:"sparkle.efk", visible:"true"]);
            return "started";""")
        if drawn == "started":
            time.sleep(1.5)
            drawn = eng.tjs('var l = kag.fore.layers[0], n = 0; for (var y = 0; y < l.height; y += 8)'
                            ' for (var x = 0; x < l.width; x += 8) if (l.getMainPixel(x, y)) n++; return n > 0 ? "drawn" : "empty";')
            step("converted game: an effect draws", drawn == "drawn", str(drawn))
        else:
            print("  (effects: %s)" % drawn)
    except Exception as e:
        step("converted game: the title screen", False, str(e)[:1500])
    finally:
        if eng:
            eng.stop()
            if args.out:
                shutil.copyfile(eng.log_path, Path(args.out) / "converted-game.log")


def media_tests(exe, proj, args):
    d = proj / "data"
    for sub in ("voice", "sound", "bgm", "scenario"):
        (d / sub).mkdir(exist_ok=True)
    write_wav(d / "sound" / "kr_tone.wav", 44100 * 3)
    (d / "sound" / "kr_tone.wav.sli").write_text("#2.00\nLink { From=88200; To=44100; Smooth=False; Condition=no; RefValue=0; CondVar=0; }\n")
    write_wav(d / "sound" / "kr_ref.wav", 22050)
    write_wav(d / "voice" / "tv001.wav", 22050)
    write_wav(d / "voice" / "tv002.wav", 22050)
    write_flac(d / "bgm" / "kr_flac.flac", 44100 * 2)
    (d / "scenario" / "kr_test.ks").write_text('*start\n[playse storage="kr_ref.wav"]\n[eval exp="tf.v = \'tv%03d.wav\'"]\n[s]\n', encoding="utf-8")

    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    host = host_id()
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = p == host
    s["platforms"][host]["data"] = "folder"
    s["output"]["archive"] = "none"
    s["output"]["check"] = True
    s["contents"]["plugins"] = "all"
    s["media"]["references"] = "keep"
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")

    def build():
        code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json")
        try:
            return json.loads(out[out.index("{"):])
        except ValueError:
            return {"ok": False, "error": out[-2000:], "outputs": []}

    r = build()
    step("media: build", r["ok"], r.get("error", "") + "; ".join(o.get("error", "") for o in r["outputs"]) + " " + json.dumps(r.get("media")))
    base = proj / "release" / ("kagex-sample-%s-%s" % (s["identity"]["version"], host))
    data = base / "KAGEX Sample.app" / "Contents" / "Resources" / "data" if host == "macos" else base / "data"
    have = lambda rel_: (data / rel_).exists()
    step("media: WAV to Opus, its loop points at 48 kHz", have("sound/kr_tone.opus") and not have("sound/kr_tone.wav") and have("sound/kr_tone.opus.sli")
         and "From=96000" in (data / "sound/kr_tone.opus.sli").read_text() and "To=48000" in (data / "sound/kr_tone.opus.sli").read_text(),
         (data / "sound/kr_tone.opus.sli").read_text().strip() if have("sound/kr_tone.opus.sli") else "no .sli")
    step("media: FLAC to Opus", have("bgm/kr_flac.opus") and not have("bgm/kr_flac.flac"))
    step("media: a file the scripts name is kept", have("sound/kr_ref.wav") and not have("sound/kr_ref.opus"))
    step("media: files a name pattern covers are kept", have("voice/tv001.wav") and have("voice/tv002.wav"))
    step("media: images to TLG", have("image/title.tlg") and not have("image/title.png") and have("fgimage/ch_0_0_1.tlg"))
    step("media: the framework's images too", have("system/LineBreak.tlg") or have("system/linebreak.tlg") or any((data / "system").glob("*.tlg")))
    step("media: textures an Effekseer effect names are kept", have("effect/Texture/glow.png") and not have("effect/Texture/glow.tlg")
         and r.get("media", {}).get("keptForEffects", 0) >= 6, "kept for effects: %s" % r.get("media", {}).get("keptForEffects"))
    m = r.get("media", {})
    step("media: sizes", m.get("bytesAfter", 0) < m.get("bytesBefore", 0), "%s -> %s bytes" % (m.get("bytesBefore"), m.get("bytesAfter")))
    chk = r.get("check", {})
    if args.out and (proj / "release" / "test-run.log").exists():
        shutil.copyfile(proj / "release" / "test-run.log", Path(args.out) / "test-run-media.log")
    step("media: the test run with converted media", chk.get("ok") is True, chk.get("message", "") + " " + "; ".join(chk.get("errors", [])))
    if host in ("linux", "windows"):
        converted_game_tests(base / ("kagex-sample.exe" if host == "windows" else "kagex-sample"), args)

    s["media"]["references"] = "rewrite"
    s["output"]["check"] = False
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    r = build()
    step("media: build with the names rewritten", r["ok"], r.get("error", ""))
    ks = (data / "scenario" / "kr_test.ks").read_text(encoding="utf-8") if have("scenario/kr_test.ks") else ""
    step("media: the script names the new files", 'storage="kr_ref.opus"' in ks and "tv%03d.opus" in ks, ks.replace("\n", " | "))
    step("media: the source script is untouched", "kr_ref.wav" in (d / "scenario" / "kr_test.ks").read_text(encoding="utf-8"))
    step("media: those files converted", have("sound/kr_ref.opus") and have("voice/tv001.opus"))
    m = r.get("media", {})
    # all but the files the scripts name (converted for the first time now) come from the cache
    step("media: the cache", m.get("images", 0) > 100 and m.get("fromCache", 0) >= m.get("images", 0) + m.get("sounds", 0) - 6,
         "%s from the cache, of %s images and %s sounds" % (m.get("fromCache"), m.get("images"), m.get("sounds")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--browser", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--engines")
    args = ap.parse_args()
    exe = Path(args.exe).resolve()
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        proj = make_project(Path(t))
        cli_tests(exe, proj)
        server_tests(exe, proj, args)
        if args.engines:
            os.environ["KAGEX_RELEASE_CACHE"] = str(Path(t) / "cache")
            build_tests(exe, proj, args)
            if (Path(args.engines) / "kagex_engine_web.zip").exists():
                web_tests(exe, proj, args)
            if (Path(args.engines) / "kagex_engine_android.zip").exists():
                android_tests(exe, proj, args)
            if (Path(args.engines) / "kagex_engine_ios.zip").exists():
                ios_tests(exe, proj, args)
            media_tests(exe, proj, args)
    print("%d failed" % len(failures) if failures else "all passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
