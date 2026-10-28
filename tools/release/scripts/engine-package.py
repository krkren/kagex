#!/usr/bin/env python3
"""Makes a kagex-release engine package (kagex_engine_<platform>[_debug].zip) from a KAGEX
package: the engine, its plugins and its licenses, without the sample game.

  engine-package.py <platform> <package> <out.zip> --version 0.3.0 [--debug]
                    [--licenses-from <another package>]

  windows  kagex_sdl3_windows_{release,debug}.zip  krkrz.exe, *.dll, plugin/
  linux    kagex_sdl3_linux_{release,debug}.zip    krkrz, libSDL3.so.0, plugin/
  steam    kagex_sdl3_linux_steam.tar.gz           the same, from the Steam Runtime build
  macos    kagex_sdl3_macos.zip                    KAGEX.app without data, signature and .cf files
  web      kagex_sdl3_web.zip                      the site without gamedata/, its lists, the build id and preview

Symbolic links are stored as the files they point to (only libSDL3.so.0 is needed by name).
The macOS app and the web site have no license files of their own: --licenses-from takes them
from another package.
"""
import argparse
import json
import stat
import sys
import tarfile
import zipfile
from pathlib import PurePosixPath


def read_package(path):
    """{name: (data, mode)} for the files in a zip or tar.gz, without a single top folder"""
    files = {}
    if path.endswith((".tar.gz", ".tgz")):
        with tarfile.open(path) as t:
            members = {m.name: m for m in t.getmembers()}
            for m in t.getmembers():
                if m.isdir():
                    continue
                target = m
                while target is not None and target.issym():
                    target = members.get(str(PurePosixPath(target.name).parent / target.linkname))
                if target is None or not target.isfile():
                    continue
                files[m.name] = (t.extractfile(target).read(), m.mode if m.isfile() else target.mode)
    else:
        with zipfile.ZipFile(path) as z:
            for i in z.infolist():
                if i.is_dir():
                    continue
                mode = (i.external_attr >> 16) & 0o7777 if i.create_system == 3 else 0o644
                if stat.S_ISLNK(i.external_attr >> 16):
                    target = str(PurePosixPath(i.filename).parent / z.read(i).decode())
                    files[i.filename] = (z.read(target), 0o755)
                    continue
                files[i.filename] = (z.read(i), mode or 0o644)
    # a single top folder (krkrz/ in the Steam tarball) is dropped
    tops = {n.split("/", 1)[0] for n in files}
    if len(tops) == 1 and all("/" in n for n in files) and not next(iter(tops)).endswith(".app"):
        top = next(iter(tops)) + "/"
        files = {n[len(top):]: v for n, v in files.items()}
    return files


# Live2D's Cubism Core (the Live2D plugin, or an engine with it linked in) may go out inside a
# game only, never in an engine package handed to other developers (tools/live2d/README.md):
# this string is the Core's own
CUBISM_CORE_MARK = b"Live2D Cubism SDK Core Version"


def refuse_cubism_core(files, allowed):
    """Stops when a file holds the Cubism Core, unless the package is the game's own
    (--with-cubism-core): files is {name: (data, mode)}"""
    held = sorted(n for n, (data, _mode) in files.items() if CUBISM_CORE_MARK in data)
    if not held:
        return
    if not allowed:
        sys.exit("%s hold%s Live2D's Cubism Core, which may go out inside a game only, never in an engine "
                 "package for other developers. For your own game's engine package (engines/ next to data/), "
                 "add --with-cubism-core" % (", ".join(held), "s" if len(held) == 1 else ""))
    print("note: %s hold%s Live2D's Cubism Core: this package is for your game's own builds only"
          % (", ".join(held), "s" if len(held) == 1 else ""))


def keep(platform, name):
    parts = name.split("/")
    leaf = parts[-1]
    if leaf.startswith("._") or leaf == ".DS_Store":
        return False
    if name in ("license.txt",) or parts[0] == "licenses":
        return True
    if platform == "windows":
        return name == "krkrz.exe" or (len(parts) == 1 and leaf.lower().endswith(".dll")) or parts[0] == "plugin"
    if platform in ("linux", "steam"):
        return name == "krkrz" or name == "libSDL3.so.0" or parts[0] == "plugin"
    if platform == "web":
        # the game's files and lists, and what belongs to the sample's build (its id and preview)
        return parts[0] != "gamedata" and name not in ("gamedata.krkrz_files.json", "krkrz_prefetch.json", "README.md",
                                                       "kagex-build.json", "preview.jpg")
    if platform == "macos":
        if not parts[0].endswith(".app"):
            return False
        inner = "/".join(parts[1:])
        if inner.startswith(("Contents/Resources/data/", "Contents/_CodeSignature/")):
            return False
        return inner not in ("Contents/MacOS/krkrz.cf", "Contents/Resources/krkrz.cf", "Contents/Resources/data.xp3")
    raise SystemExit("unknown platform " + platform)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("platform", choices=["windows", "linux", "steam", "macos", "web"])
    ap.add_argument("package")
    ap.add_argument("out")
    ap.add_argument("--version", required=True)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--licenses-from")
    ap.add_argument("--with-cubism-core", action="store_true",
                    help="a package for your own game's builds may hold Live2D's Cubism Core (the Live2D plugin)")
    a = ap.parse_args()

    files = {n: v for n, v in read_package(a.package).items() if keep(a.platform, n)}
    if a.licenses_from and not any(n.startswith("licenses/") for n in files):
        for n, v in read_package(a.licenses_from).items():
            if n == "license.txt" or n.startswith("licenses/"):
                files[n] = v
    exe = {"windows": "krkrz.exe", "linux": "krkrz", "steam": "krkrz"}.get(a.platform)
    if exe and exe not in files:
        sys.exit("%s has no %s" % (a.package, exe))
    if a.platform == "macos" and not any(n.endswith(".app/Contents/MacOS/krkrz") for n in files):
        sys.exit("%s has no .app with Contents/MacOS/krkrz" % a.package)
    if a.platform == "web" and not {"index.html", "krkrz.js", "krkrz.wasm", "webconfig.js"} <= set(files):
        sys.exit("%s isn't a krkrz_web site" % a.package)
    manifest = {"format": 1, "platform": a.platform, "version": a.version, "debug": a.debug}
    refuse_cubism_core(files, a.with_cubism_core)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        info = zipfile.ZipInfo("engine.json", date_time=(2026, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        z.writestr(info, json.dumps(manifest, indent=2) + "\n")
        for name in sorted(files):
            data, mode = files[name]
            if name in (exe,) or name.endswith("/Contents/MacOS/krkrz") or name.endswith(".dylib"):
                mode = 0o755
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | (mode & 0o777)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    print("%s: %d files" % (a.out, len(files) + 1))


if __name__ == "__main__":
    main()
