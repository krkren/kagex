#!/usr/bin/env python3
"""Makes kagex-release's Android engine package (kagex_engine_android.zip): krkrz_android's Gradle
project with the engine prebuilt, so a game is packaged with a JDK and the Android SDK only (no
NDK, CMake or vcpkg).

  android-engine.py <krkrz_android checkout, after a build> <its release APK> <out.zip>
                    --version 0.3.0 [--licenses-from <a package with licenses/>]

  engine.json
  license.txt, licenses/
  project/                     the Gradle project
    app/src/main/jniLibs/      the APK's lib/<abi>/*.so (but what the kit's .aar files bring)
    engine-assets/             the APK's assets, without the game (data/, data.xp3)
    app-config.json            the kit's settings; kagex-release writes the game's over it
    app/build.gradle           without the native build: no ndkVersion, externalNativeBuild,
                               prefab or native debug symbols; xp3 and media stored uncompressed
                               (the engine reads them in place), lint not run for releases

The patches are checked: a kit whose build.gradle no longer matches stops this script.
"""
import argparse
import json
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

SKIP_TOP = {".git", ".github", "build", ".gradle", ".idea", ".cxx", "docs", "scripts", "tools",
            "local.properties", "Makefile", "CLAUDE.md", "README.md", "README_en.md"}


def remove_block(text, opener):
    """Removes every 'opener {...}' block (braces balanced), with its line"""
    count = 0
    while True:
        m = re.search(r"^[ \t]*" + re.escape(opener) + r"\s*\{", text, re.M)
        if not m:
            return text, count
        depth = 0
        i = m.end() - 1
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        end = text.find("\n", i)
        text = text[:m.start()] + text[end + 1 if end >= 0 else len(text):]
        count += 1


def patch_build_gradle(text):
    def sub(pattern, repl, expect, flags=re.M):
        nonlocal text
        text, n = re.subn(pattern, repl, text, flags=flags)
        if n != expect:
            sys.exit("app/build.gradle: expected %d of %r, found %d" % (expect, pattern, n))

    sub(r"^[ \t]*ndkVersion\s*=.*\n", "", 1)
    text, n = remove_block(text, "externalNativeBuild")
    if n != 2:
        sys.exit("app/build.gradle: expected 2 externalNativeBuild blocks, found %d" % n)
    sub(r"^[ \t]*ndk\s*\{\s*debugSymbolLevel[^}]*\}\s*\n", "", 1)
    sub(r"prefab\s*=\s*true", "prefab = false", 1)
    sub(r"^([ \t]*)namespace = 'jp\.wamsoft\.krkrz'\n",
        "\\1namespace = 'jp.wamsoft.krkrz'\n\n"
        "\\1// kagex-release: the engine is prebuilt (src/main/jniLibs): no NDK, CMake or vcpkg.\n"
        "\\1// data.xp3 and media are read in place by the engine, so they stay uncompressed\n"
        "\\1androidResources { noCompress.addAll(['xp3', 'tlg', 'opus', 'ogg', 'png', 'jpg', 'webm', 'mp4']) }\n"
        "\\1packaging { jniLibs { useLegacyPackaging = false; pickFirsts.addAll(['**/libc++_shared.so', '**/libSDL3.so']) } }\n"
        "\\1lint { checkReleaseBuilds = false; abortOnError = false }\n", 1)
    return text


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("apk")
    ap.add_argument("out")
    ap.add_argument("--version", required=True)
    ap.add_argument("--licenses-from")
    ap.add_argument("--app-config", help="the app-config.json the APK was built with (default: <kit>/app-config.json)")
    ap.add_argument("--with-cubism-core", action="store_true",
                    help="a package for your own game's builds may hold Live2D's Cubism Core (the Live2D plugin)")
    a = ap.parse_args()
    kit = Path(a.kit)
    files = {}   # name in the zip -> (bytes, mode)

    def add(name, data, mode=0o644):
        files[name] = (data, mode)

    # the Gradle project, without the native sources and the kit's tooling
    for p in sorted(kit.rglob("*")):
        rel = p.relative_to(kit)
        if not p.is_file() or rel.parts[0] in SKIP_TOP:
            continue
        if rel.parts[:4] == ("app", "src", "main", "cpp") or (len(rel.parts) > 1 and rel.parts[1] in ("build", ".cxx")):
            continue
        mode = 0o755 if rel.name == "gradlew" else 0o644
        add("project/" + rel.as_posix(), p.read_bytes(), mode)

    bg = patch_build_gradle((kit / "app" / "build.gradle").read_text(encoding="utf-8"))
    add("project/app/build.gradle", bg.encode("utf-8"))
    props = (kit / "gradle.properties").read_text(encoding="utf-8")
    add("project/gradle.properties", re.sub(r"-Xmx\d+m", "-Xmx4g", props).encode("utf-8"))

    # what the kit's .aar files bring (SDL3) stays out of jniLibs
    from_aars = set()
    for aar in (kit / "app" / "libs").glob("*.aar"):
        with zipfile.ZipFile(aar) as z:
            from_aars |= {Path(n).name for n in z.namelist() if n.startswith("jni/") and n.endswith(".so")}

    with zipfile.ZipFile(a.apk) as apk:
        libs = assets = 0
        for i in apk.infolist():
            n = i.filename
            if n.startswith("lib/") and n.endswith(".so"):
                abi, so = n.split("/")[1], n.split("/")[-1]
                if so in from_aars:
                    continue
                add("project/app/src/main/jniLibs/%s/%s" % (abi, so), apk.read(i))
                libs += 1
            elif n.startswith("assets/") and not n.endswith("/"):
                rel = n[len("assets/"):]
                # the game, and what the Android Gradle plugin puts in (baseline profiles)
                if rel == "data.xp3" or rel.startswith(("data/", "dexopt/")):
                    continue
                add("project/engine-assets/" + rel, apk.read(i))
                assets += 1
    if not any(n.endswith("/libkrkrz.so") for n in files):
        sys.exit("%s has no libkrkrz.so" % a.apk)

    # the settings the engine was built with; kagex-release writes the game's over them
    cfg = json.loads(Path(a.app_config or kit / "app-config.json").read_text(encoding="utf-8"))
    keep = {k: cfg[k] for k in ("compileSdk", "targetSdk", "minSdk", "cmake", "manifestPlaceholders") if k in cfg}
    keep["cmake"] = {"plugins": cfg.get("cmake", {}).get("plugins", [])}
    add("project/app-config.json", (json.dumps(keep, indent=2) + "\n").encode("utf-8"))

    if a.licenses_from:
        with zipfile.ZipFile(a.licenses_from) as z:
            for n in z.namelist():
                if (n == "license.txt" or n.startswith("licenses/")) and not n.endswith("/"):
                    add(n, z.read(n))

    manifest = {"format": 1, "platform": "android", "version": a.version, "debug": False,
                "aar": sorted(from_aars)}
    refuse_cubism_core(files, a.with_cubism_core)
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        info = zipfile.ZipInfo("engine.json", date_time=(2026, 1, 1, 0, 0, 0))
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        z.writestr(info, json.dumps(manifest, indent=2) + "\n")
        for name in sorted(files):
            data, mode = files[name]
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    print("%s: %d files (%d native libraries, %d engine assets)" % (a.out, len(files) + 1, libs, assets))


if __name__ == "__main__":
    main()
