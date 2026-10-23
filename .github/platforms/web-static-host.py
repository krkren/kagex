#!/usr/bin/env python3
"""Readies a krkrz_web site (stage_web.py's site/ folder) for a static host such as GitHub Pages.

- The engine reads the web:// file list from gamedata/krkrz_files.json. stage_web.py writes it
  to gamedata.krkrz_files.json, and only its serve.py answers that URL with it: copy it there.
- coi-serviceworker reloads the page on the service worker's updatefound, before the worker is
  active, so the reloaded page sometimes isn't controlled by it and stays without
  crossOriginIsolated (the engine can't start until the next reload). window.coi.doReload makes
  the reload wait for navigator.serviceWorker.ready.

Safe to run again on a site that has both. Usage: web-static-host.py <site folder>
"""
import shutil
import sys
from pathlib import Path

COI_TAG = '<script src="coi-serviceworker.js"></script>'
COI_CONFIG = ('<script>window.coi={doReload:function(){navigator.serviceWorker.ready'
              '.then(function(){window.location.reload();});}};</script>')

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
    index.write_text(html.replace(COI_TAG, COI_CONFIG + COI_TAG, 1), encoding="utf-8")
    print("index.html: coi reloads once the service worker is ready")
