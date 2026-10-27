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
  Linux the converted build in the engine (a button's hover image found, the button highlighted).
  Then compiled scripts: a small game of its own whose scripts check, when it runs, the
  constants beyond 32 bits, expression scripts, UTF-16LE and Shift_JIS scripts; and a patch of
  compiled scripts holds only the one that changed.
  Then compiled scenarios: the scripts compiled and left out, encrypted with a key that's
  written into the engine's scnfile plugin (where the host's engine package has it, else the
  .scn.json the engine writes without it), a patch of one changed script, and on Linux the
  sample played from the package by tools/smoketest.py --packaged
- --tests cli,keys,signing,server,build,web,android,ios,media,scripts,scenes,patch picks some of these (default: all)
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
    (proj / "data" / "image" / "layers.bak").write_bytes(b"8BPS")
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
    psd = sum(e["files"] for e in d["byExtension"] if e["ext"] == ".psd")
    step("plan: exclusions (*.bak by default; work/ and *.psd aren't)", d["excluded"] >= 1 and psd == 1,
         "%d files, %d excluded, %d .psd" % (d["files"], d["excluded"], psd))
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
        # a release's tool is built with xp3crypt and scnfile (release-tool.yml sets this)
        enc = "archive %s, scenarios %s" % (st.get("canEncrypt"), st.get("scnfile"))
        if os.environ.get("KAGEX_RELEASE_REQUIRE_ENCRYPTION") == "1":
            step("state: the tool encrypts archives and scenarios", st.get("canEncrypt") is True and st.get("scnfile") is True, enc)
        else:
            print("     encryption built in: " + enc, flush=True)
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
            step("screen: every section", page.locator("section.card").count() == 10, str(page.locator("section.card").count()))
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
        step("windows: an archive per media folder beside data.xp3, and no data folder",
             {n + f for f in SPLIT_PARTS} <= set(z.namelist()) and not any(x.startswith(n + "data/") for x in z.namelist()),
             " ".join(sorted(x[len(n):] for x in z.namelist() if x.startswith(n) and x.endswith(".xp3"))))
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
            step(p + ": an archive per media folder beside data.xp3", {n + f for f in SPLIT_PARTS} <= set(m))
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
            step("macos: an archive per media folder beside data.xp3 in Resources", {app + "Resources/" + f for f in SPLIT_PARTS} <= nl)
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
        step("windows: the media archives beside the bound exe", {n + f for f in SPLIT_PARTS} <= set(z.namelist()))
        plugins = [x for x in z.namelist() if x.startswith(n + "plugin/") and not x.endswith("/")]
        step("windows: only the linked plugins", 0 < len(plugins) < 27, "%d plugins" % len(plugins))
    lz = outdir / (base + "steam.zip")
    if lz.exists():
        z = zipfile.ZipFile(lz)
        n = base + "steam/"
        info = z.getinfo(n + "kagex-sample")
        step("steam: zip with a data folder and the executable flag", n + "data/startup.tjs" in z.namelist() and n + "data/system/Initialize.tjs" in z.namelist()
             and (info.external_attr >> 16) & 0o111 != 0)
        step("steam: the data folder has the media folders the other platforms' archives took",
             all(any(x.startswith(n + "data/" + f[:-4] + "/") for x in z.namelist()) for f in SPLIT_PARTS)
             and not any(x.endswith(".xp3") for x in z.namelist()))
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
            # the console, also from a page that never started (WebEngine writes it as it comes)
            if args.out and (work / "console.txt").exists():
                shutil.copyfile(work / "console.txt", Path(args.out) / ("web-%s-console.txt" % mode))
            if eng:
                eng.stop()
            httpd.shutdown()
    if args.browser and builds.get("files"):
        web_prefetch_race(exe, proj, args)
    step("web: another build, another id (players' pages and caches update)", builds.get("files") and builds.get("xp3") and builds["files"] != builds["xp3"],
         "%s / %s" % (builds.get("files"), builds.get("xp3")))


# Each OPFS write the page makes commits 1.5 s late: krkrz.js's prefetch makes an entry (empty)
# before it writes it, and the engine took any entry it found as the file, so a script it read in
# that window came back empty and a compiled one failed to load ("Syntax error at line 1").
# kagex-web.js makes such a lookup wait for the write; without that this failed every time
SLOW_OPFS_WRITES = """(() => {
  const W = globalThis.FileSystemWritableFileStream && FileSystemWritableFileStream.prototype;
  if (!W) return;
  const close = W.close;
  W.close = function () { const s = this; return new Promise(r => setTimeout(r, 1500)).then(() => close.call(s)); };
})();"""


def web_prefetch_race(exe, proj, args):
    """The files build again, its cache writes slowed: the game still starts"""
    import functools
    import http.server
    import threading
    s = json.loads((proj / "release.json").read_text(encoding="utf-8"))
    s["platforms"]["web"]["data"] = "files"
    (proj / "release.json").write_text(json.dumps(s, indent=2), encoding="utf-8")
    site = proj / "release" / ("kagex-sample-%s-web" % s["identity"]["version"])
    code, out = run(exe, "--cli", "build", str(proj / "release.json"), "--engines=" + str(args.engines), "--json")
    if code != 0:
        step("web (files): starts while the prefetch's cache writes are slow", False, "the build failed: " + out[-500:])
        return
    sys.path.insert(0, str(REPO / "tools"))
    import smoketest
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    class Server(http.server.ThreadingHTTPServer):
        def handle_error(self, *a):
            pass  # the browser drops connections it no longer needs
    httpd = Server(("127.0.0.1", 0), functools.partial(Quiet, directory=str(site)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    work = Path(tempfile.mkdtemp())
    eng = None
    try:
        eng = smoketest.WebEngine("http://127.0.0.1:%d/" % httpd.server_address[1], str(work), False, init_script=SLOW_OPFS_WRITES)
        res = eng._eval('kag.conductor.curStorage', 60)
        time.sleep(5)
        errors = [l for l in eng.lines if "Script exception raised" in l or "! trace :" in l or "Syntax error" in l or "pageerror" in l]
        step("web (files): starts while the prefetch's cache writes are slow", res.get("ok") and not errors, str(res.get("result")) + " " + "; ".join(errors[:3]))
    except Exception as e:
        step("web (files): starts while the prefetch's cache writes are slow", False, str(e)[:1500])
    finally:
        if args.out and (work / "console.txt").exists():
            shutil.copyfile(work / "console.txt", Path(args.out) / "web-files-slow-console.txt")
        if eng:
            eng.stop()
        httpd.shutdown()


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

    # a rule's pixels are timings (and for 3duniversal speeds and directions): JPEG would scatter them
    s["media"]["images"]["opaque"] = "jpeg"
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    r = build()
    step("media: build with JPEG for opaque images", r["ok"], r.get("error", ""))
    step("media: rule images stay lossless", have("bgimage/bg01_01.jpg") and have("rule/rule_shatter.tlg")
         and not have("rule/rule_shatter.jpg"), ", ".join(sorted(p.name for p in (data / "rule").glob("*"))) if (data / "rule").is_dir() else "no rule/")


SLOT_MARKER = b"KSCN-KEY-SLOT-v1"


def engine_has_scnfile(engines, host):
    """Whether the host's engine package (a zip or a folder) has the scnfile plugin"""
    names = ("plugin/libscnfile.so", "plugin/scnfile.dll", "libscnfile.dylib")
    z = Path(engines) / ("kagex_engine_%s.zip" % host)
    if z.exists():
        with zipfile.ZipFile(z) as zf:
            return any(n.endswith(names) for n in zf.namelist())
    d = Path(engines) / ("kagex_engine_%s" % host)
    return d.is_dir() and any(str(f).replace(os.sep, "/").endswith(names) for f in d.rglob("*"))


def scenes_tests(exe, proj, args):
    """Compiled scenarios (doc/scn.txt): the scripts in !scnlist.txt compiled by the host's
    engine during the build and left out of the package"""
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    host = host_id()
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = p == host
    s["platforms"][host]["data"] = "folder"
    s["output"].update(archive="none", check=True, patchFrom="")
    s["contents"]["plugins"] = "all"
    s["media"]["audio"]["convert"] = "keep"
    s["media"]["images"].update(opaque="keep", alpha="keep")

    key = proj.parent / "keys" / "scenes-keys.txt"
    code, out = run(exe, "--cli", "keygen", str(key))
    step("scenes: keygen writes the keys file", code == 0 and "scenes" in (keys_of(key) if key.exists() else {}), out.strip())
    s["scenes"] = {"compile": True, "encrypt": True}
    s["keys"] = {"file": os.path.relpath(key, proj)}
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    code, out = run(exe, "--cli", "plan", str(rel), "--json")
    sc = json.loads(out)["data"].get("scenes", {})
    step("scenes: plan lists the scripts to compile", sc.get("compile") and sc.get("scripts", 0) >= 7 and sc.get("encrypted"), json.dumps(sc))

    def build():
        code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json")
        try:
            return json.loads(out[out.index("{"):]), ""
        except ValueError:
            return None, out[-2000:]

    # engine packages in engines/ next to data/ are used without --engines, and check and plan
    # say which format the scenarios compile to
    has_plugin = engine_has_scnfile(args.engines, host)
    link = proj / "engines"
    try:
        os.symlink(Path(args.engines).resolve(), link, target_is_directory=True)
    except OSError:
        link = None   # Windows without the right to make links
    if link:
        code, out = run(exe, "--cli", "check", str(rel), "--json")
        st = [p for p in json.loads(out)["platforms"] if p["id"] == host]
        notes = " ".join(st[0]["notes"]) if st else ""
        engine = " ".join(r["detail"] for r in st[0]["requirements"] if r["name"] == "Engine") if st else ""
        code, out = run(exe, "--cli", "plan", str(rel), "--json")
        fmt = json.loads(out)["data"]["scenes"].get("format")
        want = ".scn" if has_plugin else ".scn.json"
        said = ("compile to .scn " in notes) if has_plugin else ("no scnfile plugin" in notes)
        # the engine is known when it's a folder, or a zip a build has unpacked
        step("scenes: engines/ next to data/ is used, and check and plan name the format",
             "engines" in engine and (fmt == "" or (fmt == want and said)), "%s | %s | %s" % (engine, fmt, notes))
        link.unlink()

    base = "kagex-sample-%s-" % s["identity"]["version"]
    folder = proj / "release" / (base + host)
    data = folder / "data" if host != "macos" else next(folder.glob("*.app")) / "Contents" / "Resources" / "data"
    listed = [l.strip() for l in (proj / "data" / "scenario" / "!scnlist.txt").read_text(encoding="utf-8").splitlines()
              if l.strip() and not l.strip().startswith("#")]
    if has_plugin:
        r, err = build()
        step("scenes: an encrypted build", r is not None and r.get("ok"), err or (r or {}).get("error", "") + " " +
             "; ".join(o.get("error", "") for o in (r or {}).get("outputs", [])))
        if not r or not r.get("ok"):
            return
        scn = sorted((data / "scenario").glob("*.scn"))
        step("scenes: a .scn for each listed script, encrypted", len(scn) == len(listed) and
             all(f.read_bytes()[:4] == b"KSCN" for f in scn), ", ".join(f.name for f in scn))
        left = [n for n in listed if (data / "scenario" / n).exists()] + \
               [n for n in ("parsermacro.ks", "parseroption.txt") if (data / "scenario" / n).exists()] + \
               [f.relative_to(data).as_posix() for f in (data / "lang").glob("*/scenario/*") if f.name in listed]
        step("scenes: the compiled scripts, their translations (built into them) and the compiler's files are left out",
             not left, ", ".join(left))
        want = bytes.fromhex(keys_of(key)["scenes"])
        holders = [f for f in folder.rglob("*") if f.is_file() and not f.is_symlink() and "data" not in f.relative_to(folder).parts
                   and SLOT_MARKER in f.read_bytes()]
        keyed = [f for f in holders if f.read_bytes().split(SLOT_MARKER, 1)[1][:32] == want]
        step("scenes: the key is in the package's plugin", len(holders) == 1 and keyed == holders, ", ".join(f.name for f in holders))
        chk = r.get("check", {})
        step("scenes: test run", chk.get("ok") is True, chk.get("message", "") + " " + "; ".join(chk.get("errors", [])))
        if host == "linux":
            exe_path = folder / s["identity"]["exeName"]
            p = subprocess.run([sys.executable, str(REPO / "tools" / "smoketest.py"), "--engine", str(exe_path), "--packaged"],
                               cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
            fails = [l for l in p.stdout.splitlines() if l.startswith("FAIL")]
            step("scenes: the sample plays from the encrypted package (smoketest.py --packaged)", p.returncode == 0,
                 "; ".join(fails) or p.stdout.strip().splitlines()[-1] if p.stdout.strip() else p.stderr[-500:])
        ext = ".scn"
    else:
        r, err = build()
        msg = err or (r or {}).get("error", "")
        # refused when compiling gives .scn.json, or up front by a tool built without scnfile
        step("scenes: without the scnfile plugin an encrypted build is refused", r is not None and not r.get("ok")
             and (".scn.json" in msg or "without scnfile" in msg), msg)
        s["scenes"]["encrypt"] = False
        rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
        r, err = build()
        step("scenes: without the plugin the scripts compile to .scn.json", r is not None and r.get("ok") and
             len(list((data / "scenario").glob("*.scn.json"))) == len(listed) and not any((data / "scenario" / n).exists() for n in listed),
             err or (r or {}).get("error", ""))
        chk = (r or {}).get("check", {})
        step("scenes: test run", chk.get("ok") is True, chk.get("message", "") + " " + "; ".join(chk.get("errors", [])))
        ext = ".scn.json"

    # a patch of one changed script holds its compiled file only (compiling and encrypting give
    # the same bytes for the same script)
    files = proj / "release" / ("kagex-sample-%s-files.json" % s["identity"]["version"])
    since = proj / "release" / "scenes-files.json"
    shutil.copyfile(files, since)
    layer = proj / "data" / "scenario" / "layer.ks"
    layer.write_bytes(layer.read_bytes() + b"\n; changed for the scenes test\n")
    s["output"]["patchFrom"] = "release/scenes-files.json"
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = False
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    r, err = build()
    zip_path = proj / "release" / ("kagex-sample-%s-patch" % s["identity"]["version"]) / "patch.zip"
    names = {n for n in zipfile.ZipFile(zip_path).namelist() if not n.endswith("/")} if zip_path.exists() else set()
    step("scenes: a patch after one script changed holds its compiled file only", names == {"scenario/layer.ks" + ext},
         ", ".join(sorted(names)) or err or (r or {}).get("error", ""))
    s["output"]["patchFrom"] = ""
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")


def patch_tests(exe, proj):
    """A build with output.patchFrom: the file list each build writes, then patch.zip of what
    changed since an earlier list. A patch alone needs no platform (and so no engines)"""
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = False
    s["output"]["check"] = False
    s["contents"]["compileScripts"] = False   # compiling takes this computer's engine
    # the scripts as they are: compiling them needs an engine (scenes_tests)
    s["scenes"] = {"compile": False, "encrypt": False}
    out = proj / "release"
    out.mkdir(exist_ok=True)
    (out / "nothing-files.json").write_text(json.dumps({"format": 1, "version": "0", "files": {}}), encoding="utf-8")

    def build(version, since):
        s["identity"]["version"] = version
        s["output"]["patchFrom"] = since
        rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
        code, text = run(exe, "--cli", "build", str(rel), "--json")
        try:
            r = json.loads(text[text.index("{"):])
        except ValueError:
            return None, text[-2000:]
        return r, ""

    r, err = build("1.0.0", "release/nothing-files.json")
    files = out / "kagex-sample-1.0.0-files.json"
    zip_path = out / "kagex-sample-1.0.0-patch" / "patch.zip"
    ok = r is not None and r.get("ok") and files.exists() and zip_path.exists()
    step("patch: a build of a patch alone writes the file list and patch.zip", ok, err or (r or {}).get("error", ""))
    if not ok:
        return
    listed = json.loads(files.read_text(encoding="utf-8"))["files"]
    names = {n for n in zipfile.ZipFile(zip_path).namelist() if not n.endswith("/")}
    step("patch: from an empty list it holds every file", names == set(listed), "%d in the zip, %d listed" % (len(names), len(listed)))
    step("patch: the defaults keep .clip and .psd files", "fgimage/emblem.clip" in listed and "image/layers.psd" in listed)

    # *.psd and *.clip in the list: a .clip a script loads layers from goes in all the same, a
    # .psd nothing names doesn't. The list up to 0.9.2's defaults is taken as the new defaults
    old_defaults = ["*.psd", "*.clip", "*.bak", "*.tmp", "Thumbs.db", "desktop.ini", ".DS_Store"]
    for exclude, kept in ((old_defaults + ["*.zzz"], False), (old_defaults, True)):
        s["contents"]["exclude"] = exclude
        r, err = build("1.0.0", "release/nothing-files.json")
        listed = json.loads(files.read_text(encoding="utf-8"))["files"] if r is not None and r.get("ok") else {}
        if kept:
            step("patch: a release.json with 0.9.2's default exclusions keeps .psd files",
                 "image/layers.psd" in listed and "image/layers.bak" not in listed, err)
        else:
            step("patch: with *.psd and *.clip left out, a .clip a script loads layers from is kept, a .psd nothing names isn't",
                 "fgimage/emblem.clip" in listed and "image/layers.psd" not in listed, err)
    s["contents"]["exclude"] = old_defaults[2:]

    layer = proj / "data" / "scenario" / "layer.ks"
    layer.write_bytes(layer.read_bytes() + b"\n; changed for the patch test\n")
    (proj / "data" / "others").mkdir(exist_ok=True)
    (proj / "data" / "others" / "zz_patch.txt").write_text("new in 1.1.0", encoding="utf-8")
    (proj / "data" / "fgimage" / "emblem_bitmap.png").unlink()
    r, err = build("1.1.0", "release/kagex-sample-1.0.0-files.json")
    zip_path = out / "kagex-sample-1.1.0-patch" / "patch.zip"
    names = {n for n in zipfile.ZipFile(zip_path).namelist() if not n.endswith("/")} if zip_path.exists() else set()
    step("patch: only what changed since 1.0.0", names == {"scenario/layer.ks", "others/zz_patch.txt"}, ", ".join(sorted(names)) or err)
    notes = " ".join((r or {}).get("notes", []))
    step("patch: says a file removed since stays in the game", "1 file removed since then stays" in notes, notes)
    pkg = [o for o in (r or {}).get("outputs", []) if o.get("platform") == "patch"]
    step("patch: listed with the outputs", len(pkg) == 1 and pkg[0].get("ok") and pkg[0].get("package", "").endswith("patch.zip"))


def run_engine(pkgdir, exe_rel, extra_args, seconds=20):
    """Starts a built engine headless, waits (polling its console log) for the signature check to
    pass or fail or for the time limit, kills it, and returns (verified, log_text)."""
    import signal as _signal
    save = pkgdir / "_test_save"
    if save.exists():
        shutil.rmtree(save)
    save.mkdir(parents=True)
    exe = pkgdir / exe_rel
    env = dict(os.environ)
    env.setdefault("SDL_VIDEO_DRIVER", "offscreen")
    env.setdefault("SDL_AUDIO_DRIVER", "dummy")
    logf = open(pkgdir / "_test_out.txt", "wb")
    proc = subprocess.Popen([str(exe), "-datapath=" + str(save) + "/", *extra_args],
                            cwd=str(exe.parent), stdout=logf, stderr=subprocess.STDOUT, env=env)
    console = save / "krkr.console.log"
    deadline = time.time() + seconds
    decided = None
    while time.time() < deadline and proc.poll() is None:
        time.sleep(0.4)
        if console.exists():
            try:
                text = console.read_bytes().decode("utf-16-le", "replace")
            except OSError:
                continue
            if "Signatures verified; starting the game" in text:
                decided = True
                break
            if "Signature check:" in text:
                decided = False
                break
    if proc.poll() is None:
        proc.send_signal(_signal.SIGKILL)
    proc.wait()
    logf.close()
    log = ""
    if console.exists():
        log = console.read_bytes().decode("utf-16-le", "replace")
    if not log:
        log = (pkgdir / "_test_out.txt").read_bytes().decode("utf-8", "replace")
    verified = ("Signatures verified; starting the game" in log) if decided is None else decided
    return verified, log


KEYS_ENV = ("KAGEX_KEYS_FILE",)


def keys_of(path):
    """The keys in a keys file: {"archive": hex, "scenes": hex, "signing": PEM}"""
    text = Path(path).read_text(encoding="utf-8")
    out = {}
    for name in ("archive", "scenes"):
        m = re.search(r"^%s:\s*([0-9a-fA-F]{64})\s*$" % name, text, re.M)
        if m:
            out[name] = m.group(1).lower()
    m = re.search(r"-----BEGIN RSA PRIVATE KEY-----.*?-----END RSA PRIVATE KEY-----", text, re.S)
    if m:
        out["signing"] = m.group(0)
    return out


def check_issues(exe, proj, settings, env_extra=None):
    """--cli check of these settings: (exit code, {field: [messages]} of errors, ... of warnings)"""
    f = proj / "keys-check.json"
    f.write_text(json.dumps(settings), encoding="utf-8")
    env = dict(os.environ)
    for k in KEYS_ENV:
        env.pop(k, None)
    env.update(env_extra or {})
    r = subprocess.run([str(exe), "--cli", "check", str(f), "--json"], capture_output=True, text=True, env=env, timeout=120)
    f.unlink()
    errs, warns = {}, {}
    try:
        for i in json.loads(r.stdout)["issues"]:
            (errs if i["level"] == "error" else warns).setdefault(i["field"], []).append(i["message"])
    except ValueError:
        pass
    return r.returncode, errs, warns


def keys_tests(exe, proj, tmp):
    """The keys file (no engines needed): keygen writes a key of its own for each kind of
    protection, adds the ones a file lacks, and the check finds a missing, shared or misplaced key"""
    kf = tmp / "keys" / "game-keys.txt"
    code, out = run(exe, "--cli", "keygen", str(kf), "--bits=2048")
    k = keys_of(kf) if kf.exists() else {}
    step("keys: keygen writes the archive, scenes and signing keys", code == 0 and set(k) == {"archive", "scenes", "signing"}, out.strip())
    step("keys: each kind of protection has a key of its own", k.get("archive") and k.get("archive") != k.get("scenes"), "")
    if os.name == "posix":
        step("keys: only the owner can read the file", kf.exists() and (kf.stat().st_mode & 0o077) == 0, oct(kf.stat().st_mode) if kf.exists() else "")
    code, out = run(exe, "--cli", "keygen", str(kf))
    step("keys: keygen won't replace keys", code == 2 and "already" in out and keys_of(kf) == k, out.strip())
    # a file that lacks a key gets that one, and keeps the others
    kf.write_text("".join(l for l in kf.read_text(encoding="utf-8").splitlines(True) if not l.startswith("scenes:")), encoding="utf-8")
    code, out = run(exe, "--cli", "keygen", str(kf))
    k2 = keys_of(kf)
    step("keys: keygen adds the key a file lacks and keeps the rest", code == 0 and "scenes key" in out and k2.get("scenes")
         and k2.get("scenes") != k["scenes"] and k2.get("archive") == k["archive"] and k2.get("signing") == k["signing"], out.strip())
    code, out = run(exe, "--cli", "keygen", str(kf), "--force")
    k3 = keys_of(kf)
    step("keys: keygen --force makes every key new", code == 0 and k3.get("archive") != k2.get("archive") and k3.get("signing") != k2.get("signing"), out.strip())

    rel = proj / "release.json"
    base = json.loads(rel.read_text(encoding="utf-8"))
    host = host_id()

    def signed(keys_file=""):
        st = json.loads(json.dumps(base))
        for p in st["platforms"]:
            st["platforms"][p]["enabled"] = p == host
        st["signing"]["enabled"] = True
        st["keys"] = {"file": keys_file}
        return st

    code, errs, _ = check_issues(exe, proj, signed())
    step("keys: signing without a keys file is an error", "keys.file" in errs, json.dumps(errs))
    code, errs, _ = check_issues(exe, proj, signed(os.path.relpath(kf, proj)))
    step("keys: a keys file outside the game's folder passes", "keys.file" not in errs, json.dumps(errs))
    code, errs, _ = check_issues(exe, proj, signed(), {"KAGEX_KEYS_FILE": str(kf)})
    step("keys: KAGEX_KEYS_FILE names the keys file", "keys.file" not in errs, json.dumps(errs))
    inside = proj / "data" / "game-keys.txt"
    shutil.copyfile(kf, inside)
    code, errs, _ = check_issues(exe, proj, signed("data/game-keys.txt"))
    step("keys: a keys file inside data/ is an error", any("inside data/" in m for m in errs.get("keys.file", [])), json.dumps(errs))
    inside.unlink()
    nosign = tmp / "keys" / "no-signing.txt"
    nosign.write_text("archive: %s\nscenes: %s\n" % (k3["archive"], k3["scenes"]), encoding="utf-8")
    code, errs, _ = check_issues(exe, proj, signed(os.path.relpath(nosign, proj)))
    step("keys: a keys file without the key a setting needs is an error", any("no signing key" in m for m in errs.get("keys.file", [])), json.dumps(errs))
    same = tmp / "keys" / "same.txt"
    same.write_text(kf.read_text(encoding="utf-8").replace(k3["scenes"], k3["archive"]), encoding="utf-8")
    code, errs, _ = check_issues(exe, proj, signed(os.path.relpath(same, proj)))
    step("keys: the archive and scenes keys can't be the same", any("the same" in m for m in errs.get("keys.file", [])), json.dumps(errs))
    bad = tmp / "keys" / "bad.txt"
    bad.write_text("archve: %s\n" % k3["archive"], encoding="utf-8")
    code, errs, _ = check_issues(exe, proj, signed(os.path.relpath(bad, proj)))
    step("keys: a misspelt key name is an error", any("archve" in m for m in errs.get("keys.file", [])), json.dumps(errs))
    old = signed(os.path.relpath(kf, proj))
    old["signing"]["privateKey"] = "private.txt"
    code, errs, warns = check_issues(exe, proj, old)
    step("keys: a release.json from before the keys file is told", "signing.privateKey" in warns, json.dumps(warns))


def signing_validation_tests(exe, proj):
    rel = proj / "release.json"
    base = json.loads(rel.read_text(encoding="utf-8"))
    host = host_id()

    def check(mut):
        s = json.loads(json.dumps(base))
        mut(s)
        f = proj / "sign-check.json"
        f.write_text(json.dumps(s), encoding="utf-8")
        env = dict(os.environ)
        for k in KEYS_ENV:
            env.pop(k, None)
        r = subprocess.run([str(exe), "--cli", "check", str(f), "--json"], capture_output=True, text=True, env=env, timeout=120)
        f.unlink()
        try:
            data = json.loads(r.stdout)
        except ValueError:
            return r.returncode, [], []
        errs = [i["field"] for i in data["issues"] if i["level"] == "error"]
        warns = [i["field"] for i in data["issues"] if i["level"] == "warning"]
        return r.returncode, errs, warns

    keys = proj.parent / "keys" / "game-keys.txt"
    if not keys.exists():
        run(exe, "--cli", "keygen", str(keys))

    def on(s, keys_file=None):
        for k in s["platforms"]:
            s["platforms"][k]["enabled"] = (k == host)
        s["signing"]["enabled"] = True
        s["keys"] = {"file": os.path.relpath(keys, proj) if keys_file is None else keys_file}

    code, errs, warns = check(lambda s: on(s, ""))
    step("signing: no keys file is an error", "keys.file" in errs, ", ".join(errs))
    # a folder data mode for a signed desktop build is refused
    if host != "macos":
        code, errs, warns = check(lambda s: (on(s), s["platforms"].__setitem__(host, {**s["platforms"][host], "data": "folder"})))
        step("signing: a signed desktop build can't use a data folder", ("platforms.%s.data" % host) in errs, ", ".join(errs))
    # web enabled under signing warns that it isn't checked
    code, errs, warns = check(lambda s: (on(s), s["platforms"]["web"].__setitem__("enabled", True)))
    step("signing: web build warns it isn't signature-checked", "signing.enabled" in warns, "warns=" + ", ".join(warns))
    # a framework without SignatureCheck.tjs is refused
    sc = proj / "template" / "system" / "SignatureCheck.tjs"
    saved = sc.read_bytes()
    sc.unlink()
    code, errs, warns = check(lambda s: on(s))
    sc.write_bytes(saved)
    step("signing: a framework without SignatureCheck.tjs is refused", "signing.enabled" in errs, ", ".join(errs))


def signing_build_tests(exe, proj, args):
    """A signed Linux build, then the tampering scenarios against the built engine (Linux host).
    release.json is put back afterwards: the groups after this one build unsigned"""
    rel = proj / "release.json"
    saved = rel.read_bytes()
    try:
        _signing_build_tests(exe, proj, args)
    finally:
        rel.write_bytes(saved)


def _signing_build_tests(exe, proj, args):
    if host_id() != "linux":
        print("skip signing build tests: not a Linux host")
        return
    keydir = Path(tempfile.mkdtemp())
    keys = keydir / "game-keys.txt"
    code, out = run(exe, "--cli", "keygen", str(keys), "--bits=2048")
    if code != 0:
        step("signing build: keygen", False, out)
        return
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = (p == "linux")
    s["platforms"]["linux"]["data"] = "xp3"
    s["output"]["check"] = True
    s["output"]["archive"] = "none"
    s["signing"]["enabled"] = True
    s["keys"] = {"file": ""}
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    env = dict(os.environ)
    env["KAGEX_KEYS_FILE"] = str(keys)
    r = subprocess.run([str(exe), "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json"],
                       capture_output=True, text=True, env=env, timeout=1800)
    try:
        res = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        step("signing build: build", False, r.stdout[-2000:] + r.stderr[-500:])
        return
    if args.out:
        (Path(args.out) / "signing-build.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    step("signing build: built", res.get("ok"), res.get("error", "") + "; ".join(o.get("error", "") for o in res.get("outputs", [])))
    pkg = proj / "release" / ("kagex-sample-%s-linux" % s["identity"]["version"])
    if not pkg.exists():
        step("signing build: package folder", False)
        return
    # the signed build's own test run (log-based) passed
    chk = res.get("check", {})
    step("signing build: the signed test run verifies", chk.get("ok") is True, chk.get("message", "") + " " + "; ".join(chk.get("errors", [])))
    # the files that signing produced
    names = set(p.name for p in pkg.iterdir())
    step("signing build: data.xp3.sig, the engine list and its sig, engine .sig files",
         "data.xp3.sig" in names and "kagex-sample.sigfiles" in names and "kagex-sample.sigfiles.sig" in names
         and "kagex-sample.sig" in names and (pkg / "plugin").exists(), ", ".join(sorted(n for n in names if n.endswith(".sig") or n.endswith(".sigfiles"))[:6]))
    step("signing build: every media folder's archive, signed", all(f in names and f + ".sig" in names for f in SPLIT_PARTS),
         " ".join(sorted(n for n in names if n.endswith(".xp3"))))
    # SignatureKey.tjs is inside data.xp3, not loose in the package
    needle = keys_of(keys)["signing"].splitlines()[1].strip().encode()   # a line of the private key
    step("signing build: no keys shipped", not any(n.endswith("keys.txt") for n in names)
         and not any(needle in f.read_bytes() for f in pkg.rglob("*") if f.is_file() and f.stat().st_size < 50_000_000))

    exe_rel = "kagex-sample"
    # 1. the untouched build starts, with its archives mounted once verified
    ok, log = run_engine(pkg, exe_rel, [])
    step("signing run: the untouched build starts", ok, "mounted %d archives" % log.count("Signed archive mounted"))

    def tamper_case(label, mutate, restore):
        mutate()
        verified, log = run_engine(pkg, exe_rel, [])
        restore()
        failed = (not verified) and ("Signature check:" in log)
        step("signing run: %s stops the game" % label, failed, "verified=%s" % verified)

    data = pkg / "data.xp3"
    orig = data.read_bytes()
    # a byte added at the end: the engine still reads the archive (its index is found from the
    # header), so it's the signature check that stops it. (A changed script that the game reads
    # before the check, the framework in data.xp3, stops it with that script's error instead.)
    tamper_case("a changed data.xp3",
                lambda: data.write_bytes(orig + b"\x00"),
                lambda: data.write_bytes(orig))
    sig = pkg / "data.xp3.sig"
    sbak = sig.read_bytes()
    tamper_case("a deleted .sig", lambda: sig.unlink(), lambda: sig.write_bytes(sbak))
    # a changed engine file: append a byte to a plugin (ELF ignores trailing bytes, so the engine
    # still loads and runs — the signature check, not a load failure, is what must catch it)
    plug = next((p for p in (pkg / "plugin").glob("*json*.so")), None) or next(iter((pkg / "plugin").glob("*.so")), None)
    if plug:
        porig = plug.read_bytes()
        tamper_case("a changed engine file",
                    lambda: plug.write_bytes(porig + b"\x00"),
                    lambda: plug.write_bytes(porig))
    # a changed folder archive
    part = pkg / "bgimage.xp3"
    porig2 = part.read_bytes()
    tamper_case("a changed bgimage.xp3",
                lambda: part.write_bytes(porig2[:len(porig2) // 2] + bytes([porig2[len(porig2) // 2] ^ 0xFF]) + porig2[len(porig2) // 2 + 1:]),
                lambda: part.write_bytes(porig2))
    # a stray unsigned archive beside the engine (a folder the game has no archive for)
    tamper_case("an unsigned extra archive",
                lambda: shutil.copyfile(data, pkg / "uipsd.xp3"),
                lambda: (pkg / "uipsd.xp3").unlink())
    # -replfile is refused
    verified, log = run_engine(pkg, exe_rel, ["-replfile=" + str(pkg / "_ch")])
    step("signing run: -replfile is refused", (not verified) and "not allowed" in log, "verified=%s" % verified)

    # a patch signed with the developer's key mounts; one signed with another key stops the game.
    # Needs krkrsign (krkrz_tools' signing tool); it isn't always built, so skip these if absent.
    import zipfile as _zip
    patch = pkg / "patch.zip"
    z = _zip.ZipFile(patch, "w"); z.writestr("scenario/zz_sig_patch.ks", "*start\n[s]\n"); z.close()
    ks = None
    for root in (exe.parents[1] if len(exe.parents) > 1 else exe.parent,):
        for cand in root.rglob("krkrsign*"):
            if cand.is_file() and os.access(cand, os.X_OK):
                ks = cand
                break
    if ks:
        # krkrsign reads the signing key's PEM block out of the keys file as it is
        subprocess.run([str(ks), "--cli", "sign", "--key=" + str(keys), str(patch)], capture_output=True)
        ok, log = run_engine(pkg, exe_rel, [])
        step("signing run: a correctly signed patch mounts", ok and "Patch mounted" in log, "verified=%s; mounted=%s" % (ok, "Patch mounted" in log))
        otherkeys = Path(tempfile.mkdtemp()) / "other-keys.txt"
        run(exe, "--cli", "keygen", str(otherkeys))
        subprocess.run([str(ks), "--cli", "sign", "--key=" + str(otherkeys), str(patch)], capture_output=True)
        verified, log = run_engine(pkg, exe_rel, [])
        step("signing run: a patch signed with another key stops the game", (not verified) and "Signature check:" in log, "verified=%s" % verified)
    patch.unlink(missing_ok=True)
    (pkg / "patch.zip.sig").unlink(missing_ok=True)

    # signed, encrypted, with the file names hidden in data.xp3 and the folders' archives (engines
    # with xp3crypt built in: 0.9.0 and later)
    if engine_has_xp3crypt(args.engines):
        hidden_signing_tests(exe, proj, args, s, env)
    else:
        print("skip signed hidden-names build: these engine packages have no xp3crypt")
    shutil.rmtree(keydir, ignore_errors=True)


XP3CRYPT_MARKER = bytes(~b & 0xFF for b in (0xA7, 0xAF, 0xCC, 0xBC, 0xAD, 0xA6, 0xAF, 0xAB, 0xD2, 0xB4, 0xBA, 0xA6, 0xAC, 0xB3, 0xB0, 0xAB))


def engine_has_xp3crypt(engines):
    """Whether the Linux engine package has xp3crypt built in (its key slot's marker)"""
    import zipfile as _zip
    folder = Path(engines) / "kagex_engine_linux" / "krkrz"
    if folder.is_file():
        return XP3CRYPT_MARKER in folder.read_bytes()
    pkg = Path(engines) / "kagex_engine_linux.zip"
    if not pkg.is_file():
        return False
    with _zip.ZipFile(pkg) as z:
        names = [n for n in z.namelist() if n.split("/")[-1] == "krkrz"]
        return bool(names) and XP3CRYPT_MARKER in z.read(names[0])


# The sample's media folders, each packed into an archive of its own beside data.xp3 on the
# desktops (Plan.cpp's splitFolderNames, those of them the sample has)
SPLIT_PARTS = ["bgimage.xp3", "bgm.xp3", "effect.xp3", "fgimage.xp3", "image.xp3", "rule.xp3",
               "scenario.xp3", "thum.xp3", "video.xp3", "voice.xp3"]


def xp3_names(path):
    """The stored names in an XP3 archive's (uncompressed or zlib) index"""
    import zlib
    d = path.read_bytes()
    pos = 11
    index = b""
    for _ in range(16):
        ofs = int.from_bytes(d[pos:pos + 8], "little")
        flag = d[ofs]
        if flag & 7 == 1:
            clen = int.from_bytes(d[ofs + 1:ofs + 9], "little")
            index += zlib.decompress(d[ofs + 17:ofs + 17 + clen])
            ip = ofs + 17 + clen
        else:
            ilen = int.from_bytes(d[ofs + 1:ofs + 9], "little")
            index += d[ofs + 9:ofs + 9 + ilen]
            ip = ofs + 9 + ilen
        if flag & 0x80:
            pos = ip
            continue
        break
    names, i = [], 0
    while i + 12 <= len(index):
        tag, size = index[i:i + 4], int.from_bytes(index[i + 4:i + 12], "little")
        body = index[i + 12:i + 12 + size]
        if tag == b"File":
            j = 0
            while j + 12 <= len(body):
                t, sz = body[j:j + 4], int.from_bytes(body[j + 4:j + 12], "little")
                if t == b"info":
                    n = int.from_bytes(body[j + 12 + 20:j + 12 + 22], "little")
                    names.append(body[j + 12 + 22:j + 12 + 22 + n * 2].decode("utf-16-le"))
                j += 12 + sz
        i += 12 + size
    return names


def hidden_signing_tests(exe, proj, args, s, env):
    rel = proj / "release.json"
    s["archive"]["encrypt"] = True
    s["archive"]["hideNames"] = True
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    r = subprocess.run([str(exe), "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json"],
                       capture_output=True, text=True, env=env, timeout=1800)
    try:
        res = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        step("signed hidden-names build: built", False, r.stdout[-2000:] + r.stderr[-500:])
        return
    if args.out:
        (Path(args.out) / "signing-hidden-build.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    prot = res.get("protection", {})
    step("signed hidden-names build: built, encrypted with the names hidden and signed",
         res.get("ok") and prot.get("archive") == "encrypted, names hidden" and prot.get("signed") is True,
         res.get("error", "") + "; ".join(o.get("error", "") for o in res.get("outputs", [])) + " %s" % prot)
    pkg = proj / "release" / ("kagex-sample-%s-linux" % s["identity"]["version"])
    if not res.get("ok") or not pkg.exists():
        return
    chk = res.get("check", {})
    step("signed hidden-names build: the signed test run verifies", chk.get("ok") is True, chk.get("message", "") + " " + "; ".join(chk.get("errors", [])))
    archives = ["data.xp3"] + SPLIT_PARTS
    step("signed hidden-names build: data.xp3 and the folders' archives, signed, and no data folder or data.xpc",
         all((pkg / a).exists() and (pkg / (a + ".sig")).exists() for a in archives)
         and not (pkg / "data").exists() and not (pkg / "data.xpc").exists(),
         " ".join(sorted(p.name for p in pkg.iterdir() if ".xp" in p.name)))
    # every name in every archive is a hash, but data.xp3's startup.tjs
    plain = {}
    for a in archives:
        names = xp3_names(pkg / a)
        plain[a] = [n for n in names if not re.fullmatch(r"[0-9a-f]{32}", n)]
    step("signed hidden-names build: only data.xp3's startup.tjs keeps its name",
         plain["data.xp3"] == ["startup.tjs"] and all(not v for k, v in plain.items() if k != "data.xp3"), "%s" % {k: v for k, v in plain.items() if v})
    ok, log = run_engine(pkg, "kagex-sample", [])
    step("signed hidden-names run: the untouched build starts", ok, "mounted %d archives" % log.count("Signed archive mounted"))

    def tamper_case(label, mutate, restore):
        mutate()
        verified, log = run_engine(pkg, "kagex-sample", [])
        restore()
        step("signed hidden-names run: %s stops the game" % label, (not verified) and "Signature check:" in log, "verified=%s" % verified)

    for a in ("data.xp3", "fgimage.xp3"):
        f = pkg / a
        orig = f.read_bytes()
        tamper_case("a changed " + a, lambda f=f, orig=orig: f.write_bytes(orig[:len(orig) // 2] + bytes([orig[len(orig) // 2] ^ 0xFF]) + orig[len(orig) // 2 + 1:]),
                    lambda f=f, orig=orig: f.write_bytes(orig))


# A game whose Initialize.tjs checks, as it runs, what the compiled scripts give: constants
# beyond 32 bits (with values equal to theirs cut to 32 bits beside them), strings and regular
# expressions that look like them, expression scripts read with Scripts.evalStorage, UTF-16LE and
# Shift_JIS scripts (krkrz.cf's readencoding), and folded constants, which stay source where the
# engine would cut them. It writes "name<TAB>ok|FAIL<TAB>value" lines to check.txt
SCRIPT_GAME = {
    "startup.tjs": 'Scripts.execStorage("system/Initialize.tjs");\n',
    "system/Initialize.tjs": r"""var r = [];
function check(name, got, want) { r.add(name + "\t" + (got === want ? "ok" : "FAIL") + "\t" + got + " (want " + want + ")"); }
try {
	Scripts.execStorage("main/consts.tjs");
	check("0xff000000", c1, 4278190080);
	check("4294967296", c2, 4294967296);
	check("-2147483649", c3, -2147483649);
	check("0xffffffff", c4, 4294967295);
	check("-1 beside 0xffffffff", c5, -1);
	check("-16777216 beside 0xff000000", c6, -16777216);
	check("in a function", f(), 3355443201);
	check("a class member", (new K()).m(), 0x123456789ab);
	check("a string", c8, "0xff000000 and 4294967296");
	check("a regular expression", c9.test("x0xff000000y"), true);
	check("negated", c10, -4278190080);
	check("in a dictionary", c11.v, 4278190080);
	check("octal", c14, 0x100000000);
	check("binary", c15, 4294967296);
	check("after a nested comment", c16, 4294967297);
	var d = Scripts.evalStorage("main/data.tjs");
	check("an expression script", typeof d == "Object" ? d.c : "void", 4278190080);
	check("a function script", Scripts.evalStorage("main/func.tjs")(21), 42);
	Scripts.execStorage("main/fold.tjs");
	check("folded", f1, 4278190080);
	check("folded into a string", f3, "4294967296");
	Scripts.execStorage("main/utf16.tjs");
	check("UTF-16LE", u1, 4278190080);
	check("UTF-16LE string", u2.length + " " + #u2, "13 26085");
	Scripts.execStorage("main/sjis.tjs");
	check("Shift_JIS", s1, 4278190080);
	check("Shift_JIS string", s2.length, 4);
} catch (e) {
	r.add("exception\tFAIL\t" + e.message);
}
r.save(System.dataPath + "check.txt");
System.exit();
""",
    "main/consts.tjs": r"""// constants beyond 32 bits
global.c1 = 0xff000000;
global.c2 = 4294967296;
global.c3 = -2147483649;
global.c4 = 0xffffffff;
global.c5 = -1;
global.c6 = -16777216;
function f() { return 0xc8000001; }
class K {
	var v = 0x123456789ab;
	function K() {}
	function m() { return v; }
}
global.c8 = "0xff000000 and 4294967296";
global.c9 = /0xff000000/;
global.c10 = -0xff000000;
global.c11 = %[ "v" => 0xff000000 ];
global.c14 = 040000000000;
global.c15 = 0b100000000000000000000000000000000;
/* a /* nested */ comment 0xdeadbeef00 */
global.c16 = 4294967297;
""",
    "main/data.tjs": '%[\n\t"c" => 0xff000000,\n]; // the end\n',
    "main/func.tjs": "function (a) { return a * 2; }\n",
    "main/fold.tjs": 'global.f1 = 0xff << 24;\nglobal.f3 = @"${0x100000000}";\n',
}


def script_tests(exe, tmp, args):
    proj = tmp / "Scripts Game"
    for name, text in SCRIPT_GAME.items():
        (proj / "data" / name).parent.mkdir(parents=True, exist_ok=True)
        (proj / "data" / name).write_text(text, encoding="utf-8")
    (proj / "data" / "main" / "utf16.tjs").write_bytes(
        b"\xff\xfe" + 'global.u1 = 0xff000000;\nglobal.u2 = "\u65e5\u672c 0xff000000";\n'.encode("utf-16-le"))
    # a Shift_JIS string whose characters' second bytes are backslashes (\u30bd is 0x83 0x5c)
    (proj / "data" / "main" / "sjis.tjs").write_bytes('global.s2 = "\u30bd\u30bd\u30bd\u30bd";\nglobal.s1 = 0xff000000;\n'.encode("shift_jis"))
    (proj / "krkrz.cf").write_text("readencoding=Shift_JIS\n")
    code, out = run(exe, "--cli", "init", str(proj))
    rel = proj / "release.json"
    s = json.loads(rel.read_text(encoding="utf-8"))
    host = host_id()
    s["identity"].update({"orgName": "kagex-test", "appName": "scripts", "exeName": "scripts"})
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = p == host
    s["platforms"][host]["data"] = "folder"
    s["output"].update({"archive": "none", "check": False})
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")

    def build():
        code, out = run(exe, "--cli", "build", str(rel), "--engines=" + str(args.engines), "--json")
        try:
            return json.loads(out[out.index("{"):])
        except ValueError:
            return {"ok": False, "error": out[-2000:], "outputs": []}

    r = build()
    sc = r.get("scripts", {})
    step("scripts: build", r["ok"], r.get("error", "") + "; ".join(o.get("error", "") for o in r["outputs"]))
    if args.out and (proj / "release" / "compile-scripts.log").exists():
        shutil.copyfile(proj / "release" / "compile-scripts.log", Path(args.out) / "compile-scripts.log")
    # where the engine cuts constants to 32 bits (Linux, macOS), folded ones stay source
    kept = {k["name"] for k in sc.get("kept", [])}
    want_kept = {"main/fold.tjs"} if sc.get("truncates") else set()
    step("scripts: compiled, and kept as source only where needed", sc.get("compiled") == 8 - len(want_kept) and kept == want_kept,
         json.dumps(sc))
    step("scripts: the expression scripts", sc.get("expressions", 0) >= 2, "%s as expressions" % sc.get("expressions"))
    base = proj / "release" / ("scripts-1.0.0-" + host)
    data = base / "Scripts Game.app" / "Contents" / "Resources" / "data" if host == "macos" else base / "data"
    names = sorted(str(p.relative_to(data)).replace("\\", "/") for p in data.rglob("*.tjs"))
    bytecode = [n for n in names if (data / n).read_bytes()[:8] == b"TJS2100\0"]
    step("scripts: the packaged scripts are bytecode", set(names) - set(bytecode) == want_kept and len(names) == 8, ", ".join(bytecode))
    if host == "macos":
        game = base / "Scripts Game.app" / "Contents" / "MacOS" / "krkrz"
    else:
        game = base / ("scripts.exe" if host == "windows" else "scripts")
    save = tmp / "scripts-save"
    save.mkdir(exist_ok=True)
    env = dict(os.environ, SDL_AUDIO_DRIVER="dummy")
    if host == "linux":
        env["SDL_VIDEO_DRIVER"] = "offscreen"
    try:
        subprocess.run([str(game), "-datapath=" + str(save) + "/"], cwd=str(game.parent), env=env, capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        step("scripts: the game runs", False, str(e))
        return
    raw = (save / "check.txt").read_bytes() if (save / "check.txt").exists() else b""
    lines = [l for l in raw.decode("utf-16", errors="replace").splitlines() if l]
    bad = [l for l in lines if "\tok\t" not in l]
    step("scripts: the compiled game's checks", len(lines) == 23 and not bad, "; ".join(bad) or "%d checks" % len(lines))

    # a patch of compiled scripts: compiling again gives the same bytes, so only the script that
    # changed is in it
    files = proj / "release" / "scripts-1.0.0-files.json"
    consts = proj / "data" / "main" / "consts.tjs"
    consts.write_text(consts.read_text(encoding="utf-8") + "global.c17 = 0x200000000;\n", encoding="utf-8")
    for p in s["platforms"]:
        s["platforms"][p]["enabled"] = False
    s["identity"]["version"] = "1.0.1"
    s["output"]["patchFrom"] = "release/" + files.name
    rel.write_text(json.dumps(s, indent=2), encoding="utf-8")
    r = build()
    zip_path = proj / "release" / "scripts-1.0.1-patch" / "patch.zip"
    names = {n for n in zipfile.ZipFile(zip_path).namelist() if not n.endswith("/")} if zip_path.exists() else set()
    step("scripts: a patch holds only the script that changed, compiled", names == {"main/consts.tjs"}
         and zipfile.ZipFile(zip_path).read("main/consts.tjs")[:8] == b"TJS2100\0", ", ".join(sorted(names)) or r.get("error", ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--browser", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--engines")
    ap.add_argument("--tests", help="some of cli,keys,signing,server,build,web,android,ios,media,scripts,scenes,patch (default: all)")
    args = ap.parse_args()
    chosen = set(args.tests.split(",")) if args.tests else None
    want = lambda name: chosen is None or name in chosen
    exe = Path(args.exe).resolve()
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        proj = make_project(Path(t))
        # init (in cli_tests) writes the release.json every other group starts from
        if want("cli") or not (proj / "release.json").exists():
            cli_tests(exe, proj)
        if want("keys"):
            keys_tests(exe, proj, Path(t))
        if want("signing"):
            signing_validation_tests(exe, proj)
        if want("server"):
            server_tests(exe, proj, args)
        if args.engines:
            os.environ["KAGEX_RELEASE_CACHE"] = str(Path(t) / "cache")
            if want("build"):
                build_tests(exe, proj, args)
            if want("web") and (Path(args.engines) / "kagex_engine_web.zip").exists():
                web_tests(exe, proj, args)
            if want("android") and (Path(args.engines) / "kagex_engine_android.zip").exists():
                android_tests(exe, proj, args)
            if want("ios") and (Path(args.engines) / "kagex_engine_ios.zip").exists():
                ios_tests(exe, proj, args)
            if want("media"):
                media_tests(exe, proj, args)
            if want("signing"):
                signing_build_tests(exe, proj, args)
            if want("scripts"):
                script_tests(exe, Path(t), args)
            if want("scenes"):
                scenes_tests(exe, proj, args)
        if want("patch"):
            patch_tests(exe, proj)
    print("%d failed" % len(failures) if failures else "all passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
