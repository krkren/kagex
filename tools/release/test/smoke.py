#!/usr/bin/env python3
"""Smoke test of kagex-release on a copy of the sample game.

  smoke.py <kagex-release executable> [--browser] [--out DIR]

- the CLI: init, check, plan (and --json), on a copy of data/, template/system, krkrz.cf and
  platform/ in a temporary folder
- the window's server, without a browser: the page and the API (state, check, host, save)
- --browser: the screen in headless Chromium (Playwright): no script errors, the sections and
  the check filled in, a setting changed and saved with Ctrl+S; screenshots go to --out
"""
import argparse
import json
import os
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
    proc = subprocess.Popen([str(exe), str(proj), "--no-browser", "--no-token", "--port=%d" % port, "--idle-timeout=0"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
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
            page.close()
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--browser", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    exe = Path(args.exe).resolve()
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        proj = make_project(Path(t))
        cli_tests(exe, proj)
        server_tests(exe, proj, args)
    print("%d failed" % len(failures) if failures else "all passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
