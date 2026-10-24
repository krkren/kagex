#!/usr/bin/env python3
"""Adds the vcpkg ports kagex's plugins need to a platform kit's fixed vcpkg manifest, in the CI
checkout only. krkrz_android's manifest lists the engine's own dependencies and doesn't merge
the plugins' manifests (krkrz_dev, krkrz_web and krkrz_ios do), so krkreffekseer's minizip-ng
(for .efkzip effects) was missing there. Only zlib's codec is needed: an .efkzip is a plain deflate zip.
usage: kit-vcpkg.py <kit's vcpkg.json>"""
import json, sys

ADD = [{"name": "minizip-ng", "default-features": False, "features": ["zlib"]}]

path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    manifest = json.load(f)
deps = manifest.setdefault("dependencies", [])
names = {d if isinstance(d, str) else d.get("name") for d in deps}
for dep in ADD:
    if dep["name"] not in names:
        deps.append(dep)
        print("%s: added %s" % (path, dep["name"]))
with open(path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
