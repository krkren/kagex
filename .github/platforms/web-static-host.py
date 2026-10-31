#!/usr/bin/env python3
"""Readies a krkrz_web site (stage_web.py's site/ folder) for a static host such as GitHub Pages.

- The engine reads the web:// file list from gamedata/krkrz_files.json. stage_web.py writes it
  to gamedata.krkrz_files.json, and only its serve.py answers that URL with it: copy it there.
- coi-serviceworker reloads the page on the service worker's updatefound, before the worker is
  active, so the reloaded page sometimes isn't controlled by it and stays without
  crossOriginIsolated (the engine can't start until the next reload). window.coi.doReload makes
  the reload wait for navigator.serviceWorker.ready.
- Updates: the site gets a build id (a hash of its files), in kagex-build.json and in index.html
  (<meta name=kagex-build>, and ?v=<id> on its scripts). kagex-web.js (platform/web) compares
  them before the engine starts, reloads a stale page, empties the engine's file cache (OPFS)
  for a new build, and makes the page's fetches revalidate (see that file).
- Home screen: iPhones don't let a web page go full screen, but a page added to the home screen
  opens without Safari's bars when it says it can (apple-mobile-web-app-capable). A web app
  manifest does the same for Android's "Add to Home screen" / "Install app" (full screen,
  landscape) in Chrome, Edge, Samsung Internet, Firefox and Opera. kagex-web.js offers it on
  phones and tablets. The icons come from platform/web (tools/assets/make_ui.py icons), the names
  from linux-config.json and ios-config.json; the page title becomes the game's name.
- Link previews (Discord, Slack, X, iMessage...): Open Graph and Twitter card tags with the
  name, a description and platform/web/preview.jpg (make_ui.py preview). Previews want absolute
  URLs: give the site's address with --url.

The added head tags sit between <!--kagex-head--> and <!--/kagex-head-->, so running this again
(pages.yml does, on a release's zip) replaces them. Usage: web-static-host.py <site> [--url URL]
"""
import argparse
import hashlib
import html as htmlmod
import json
import re
import shutil
import sys
from pathlib import Path

# Live2D (web-plugins.py adds the plugin when the Live2D sources are fetched with build.py --web):
# the Cubism Core's own wasm runs in the page, from the SDK for Web's script loaded before the
# engine, and the engine's C++ calls it (tools/live2d/web/csm_web.cpp)
LIVE2D_CORE_JS = "live2dcubismcore.min.js"
LIVE2D_SRC = ("tools", "live2d", "build", "web", LIVE2D_CORE_JS)
LIVE2D_TAG = '<script src="live2dcubismcore.min.js"></script>'
COI_TAG = '<script src="coi-serviceworker.js"></script>'
COI_CONFIG = ('<script>window.coi={doReload:function(){navigator.serviceWorker.ready'
              '.then(function(){window.location.reload();});}};</script>')
REPO = Path(__file__).resolve().parents[2]
DESCRIPTION = ("The sample game of KAGEX, the visual-novel framework for Kirikiri Z: "
               "play it in your browser, or add it to your home screen.")
# what 0.3.0 and earlier put in the head, without the markers
LEGACY = re.compile(r'<link rel=manifest [^>]*>|<link rel=apple-touch-icon [^>]*>|'
                    r'<meta name=(?:theme-color|mobile-web-app-capable|apple-mobile-web-app-[a-z-]+) [^>]*>')
BLOCK = re.compile(r"<!--kagex-head-->.*?<!--/kagex-head-->", re.S)
SCRIPTS = ("webconfig.js", "krkrz.js", "kagex-web.js")
# the Core before the engine's, when the page carries it (the script tag is added with the sidecar)


def config(name, key, default):
    try:
        return json.loads((REPO / name).read_text(encoding="utf-8"))[key]
    except (OSError, ValueError, KeyError):
        return default


def build_id(site):
    """A hash of every file the page uses (not index.html, which carries it)"""
    h = hashlib.sha256()
    for p in sorted(x for x in site.rglob("*") if x.is_file()):
        rel = p.relative_to(site).as_posix()
        if rel in ("index.html", "kagex-build.json", "serve.py"):
            continue
        h.update(rel.encode() + b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:16]


def head_tags(name, short, description, build, url):
    e = lambda v: htmlmod.escape(v, quote=True)
    image = (url + "preview.jpg") if url else "preview.jpg"
    tags = [
        '<meta name=kagex-build content="%s">' % build,
        '<meta name=description content="%s">' % e(description),
        '<link rel=manifest href=manifest.webmanifest>',
        '<link rel=icon href=icon-192.png>',
        '<meta name=theme-color content="#000000">',
        '<meta name=mobile-web-app-capable content=yes>',
        '<meta name=apple-mobile-web-app-capable content=yes>',
        '<meta name=apple-mobile-web-app-status-bar-style content=black-translucent>',
        '<meta name=apple-mobile-web-app-title content="%s">' % e(short),
        '<link rel=apple-touch-icon href=apple-touch-icon.png>',
        '<meta property=og:type content=website>',
        '<meta property=og:site_name content="%s">' % e(name),
        '<meta property=og:title content="%s">' % e(name),
        '<meta property=og:description content="%s">' % e(description),
    ]
    if url:
        tags.append('<meta property=og:url content="%s">' % e(url))
    tags += [
        '<meta property=og:image content="%s">' % e(image),
        '<meta property=og:image:width content=1200>',
        '<meta property=og:image:height content=630>',
        '<meta property=og:image:alt content="%s">' % e(name),
        '<meta name=twitter:card content=summary_large_image>',
    ]
    return "<!--kagex-head-->" + "".join(tags) + "<!--/kagex-head-->"


def manifest(name, short, description):
    icons = []
    for purpose in ("any", "maskable"):
        icons += [{"src": "icon-%d.png" % s, "sizes": "%dx%d" % (s, s), "type": "image/png", "purpose": purpose}
                  for s in (192, 512)]
    return {
        "id": "./", "name": name, "short_name": short, "description": description,
        "start_url": "./", "scope": "./",
        "display": "fullscreen", "display_override": ["fullscreen", "standalone"],
        "orientation": "landscape", "background_color": "#000000", "theme_color": "#000000",
        "icons": icons,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("--url", default="", help="the site's address, for link previews (https://.../)")
    a = ap.parse_args()
    site = Path(a.site)
    url = a.url
    if url and not url.endswith("/"):
        url += "/"

    lst = site / "gamedata" / "krkrz_files.json"
    if not lst.exists() and (site / "gamedata.krkrz_files.json").exists():
        shutil.copyfile(site / "gamedata.krkrz_files.json", lst)
        print("copied gamedata.krkrz_files.json to gamedata/krkrz_files.json")

    live2d = REPO / Path(*LIVE2D_SRC)
    if live2d.exists():
        shutil.copyfile(live2d, site / LIVE2D_CORE_JS)
        print("copied %s: the Cubism Core, which the Live2D plugin calls from C++" % LIVE2D_CORE_JS)

    index = site / "index.html"
    html = index.read_text(encoding="utf-8")
    if "window.coi=" not in html:
        if COI_TAG not in html:
            sys.exit("index.html has no %s" % COI_TAG)
        html = html.replace(COI_TAG, COI_CONFIG + COI_TAG, 1)
        print("index.html: coi reloads once the service worker is ready")

    name = config("linux-config.json", "name", "KAGEX Sample")
    short = config("ios-config.json", "displayName", "KAGEX")
    web = REPO / "platform" / "web"
    for f in ("apple-touch-icon.png", "icon-192.png", "icon-512.png", "preview.jpg", "kagex-web.js"):
        shutil.copyfile(web / f, site / f)
    (site / "manifest.webmanifest").write_text(json.dumps(manifest(name, short, DESCRIPTION), indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
    build = build_id(site)
    (site / "kagex-build.json").write_text(json.dumps({"build": build}) + "\n", encoding="utf-8")

    start, end = html.find("<title>"), html.find("</title>")
    if start < 0 or end < start:
        sys.exit("index.html has no <title>")
    html = html[:start] + "<title>%s</title>" % htmlmod.escape(name) + html[end + len("</title>"):]
    html = BLOCK.sub("", html)
    html = LEGACY.sub("", html)
    at = html.find("</title>") + len("</title>")
    html = html[:at] + head_tags(name, short, DESCRIPTION, build, url) + html[at:]

    # kagex-web.js right before webconfig.js (after the page's Module, before krkrz.js), and
    # every script with the build id
    html = re.sub(r'<script src=(["\']?)kagex-web\.js[^"\'\s>]*\1></script>', "", html)
    m = re.search(r'<script src=(["\']?)webconfig\.js', html)
    if not m:
        sys.exit("index.html doesn't load webconfig.js")
    html = html[:m.start()] + '<script src="kagex-web.js"></script>' + html[m.start():]
    if (site / LIVE2D_CORE_JS).exists():
        # as with kagex-web.js: whatever tag is already there goes first, the fresh one in front
        # of the engine's. a staged web package brings its own stamped tag, this is run again on it
        html = re.sub(r'<script src="live2dcubismcore\.min\.js(?:\?v=[0-9a-f]*)?"></script>', "", html)
        m = re.search(r'<script src=("|\')?krkrz\.js', html)
        html = html[:m.start()] + LIVE2D_TAG + html[m.start():]
    for s in SCRIPTS + ((LIVE2D_CORE_JS,) if (site / LIVE2D_CORE_JS).exists() else ()):
        html, n = re.subn(r'src=(["\']?)%s(?:\?v=[0-9a-f]*)?\1(?=[\s>])' % re.escape(s), 'src="%s?v=%s"' % (s, build), html)
        if n != 1:
            sys.exit("index.html: expected one script %s, found %d" % (s, n))

    index.write_text(html, encoding="utf-8")
    print("index.html: %s, build %s, with the home-screen manifest and icons, link previews%s and kagex-web.js"
          % (name, build, " (" + url + ")" if url else " (relative: no --url)"))


if __name__ == "__main__":
    main()
