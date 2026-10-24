#!/usr/bin/env python3
"""Readies a krkrz_web site (stage_web.py's site/ folder) for a static host such as GitHub Pages.

- The engine reads the web:// file list from gamedata/krkrz_files.json. stage_web.py writes it
  to gamedata.krkrz_files.json, and only its serve.py answers that URL with it: copy it there.
- coi-serviceworker reloads the page on the service worker's updatefound, before the worker is
  active, so the reloaded page sometimes isn't controlled by it and stays without
  crossOriginIsolated (the engine can't start until the next reload). window.coi.doReload makes
  the reload wait for navigator.serviceWorker.ready.
- Home screen: iPhones don't let a web page go full screen, but a page added to the home screen
  opens without Safari's bars when it says it can (apple-mobile-web-app-capable). A web app
  manifest does the same for Android's "Add to Home screen" / "Install app" (full screen,
  landscape). The icons come from platform/web (tools/assets/make_ui.py icons), the names from
  linux-config.json and ios-config.json; the page title becomes the game's name.

Safe to run again on a site that has these. Usage: web-static-host.py <site folder>
"""
import html as htmlmod
import json
import shutil
import sys
from pathlib import Path

COI_TAG = '<script src="coi-serviceworker.js"></script>'
COI_CONFIG = ('<script>window.coi={doReload:function(){navigator.serviceWorker.ready'
              '.then(function(){window.location.reload();});}};</script>')
HOME_MARK = 'apple-mobile-web-app-capable'
REPO = Path(__file__).resolve().parents[2]


def config(name, key, default):
    try:
        return json.loads((REPO / name).read_text(encoding="utf-8"))[key]
    except (OSError, ValueError, KeyError):
        return default


site = Path(sys.argv[1])
manifest = site / "gamedata" / "krkrz_files.json"
if not manifest.exists():
    shutil.copyfile(site / "gamedata.krkrz_files.json", manifest)
    print("copied gamedata.krkrz_files.json to gamedata/krkrz_files.json")

index = site / "index.html"
html = index.read_text(encoding="utf-8")
if "window.coi=" not in html:
    if COI_TAG not in html:
        sys.exit("index.html has no %s" % COI_TAG)
    html = html.replace(COI_TAG, COI_CONFIG + COI_TAG, 1)
    print("index.html: coi reloads once the service worker is ready")

if HOME_MARK not in html:
    name = config("linux-config.json", "name", "KAGEX Sample")
    short = config("ios-config.json", "displayName", "KAGEX")
    icons = REPO / "platform" / "web"
    for f in ("apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        shutil.copyfile(icons / f, site / f)
    app = {
        "name": name, "short_name": short, "start_url": "./", "scope": "./",
        "display": "fullscreen", "orientation": "landscape",
        "background_color": "#000000", "theme_color": "#000000",
        "icons": [{"src": "icon-%d.png" % s, "sizes": "%dx%d" % (s, s), "type": "image/png",
                   "purpose": "any maskable"} for s in (192, 512)],
    }
    (site / "manifest.webmanifest").write_text(json.dumps(app, indent=2) + "\n", encoding="utf-8")
    e = htmlmod.escape
    head = ('<link rel=manifest href=manifest.webmanifest>'
            '<meta name=theme-color content="#000000">'
            '<meta name=mobile-web-app-capable content=yes>'
            '<meta name=%s content=yes>' % HOME_MARK +
            '<meta name=apple-mobile-web-app-status-bar-style content=black-translucent>'
            '<meta name=apple-mobile-web-app-title content="%s">' % e(short) +
            '<link rel=apple-touch-icon href=apple-touch-icon.png>')
    start, end = html.find("<title>"), html.find("</title>")
    if start < 0 or end < start:
        sys.exit("index.html has no <title>")
    html = html[:start] + "<title>%s</title>" % e(name) + head + html[end + len("</title>"):]
    print("index.html: %s, with a manifest and home-screen icons" % name)

index.write_text(html, encoding="utf-8")
