#!/usr/bin/env python3
"""A platform job of platforms.yml whose engine didn't change reuses an earlier release's build
of it instead of compiling it again: that release's engine package (kagex_engine_<platform>.zip,
the engine without the game), to which the job adds this commit's game the way the kit adds it
after its own build. What goes into an engine is written down as a key, and the release workflow's
publish job adds every platform's key to the release's note (kagex-engine-build.json, "platforms"),
so a later release finds the same engine by it. A release without the key is never reused.

  platform-engine.py key <platform>          prints the key: the pinned commits (from the job's
                                             environment), the configs without their version and
                                             comments, and the files the build reads
  platform-engine.py find <platform> <out>   the key, then the newest release whose note has that
                                             key and the engine packages; writes key=..., reuse=<tag>
                                             (empty: build) to <out> ($GITHUB_OUTPUT), the key to
                                             $ENGINE_KEY_DIR/<platform>.key, and downloads the
                                             packages to $ENGINE_DIR (kagex_engine_<platform>.zip,
                                             and Android's kagex_engine_android_debug.zip).
                                             REBUILD=true skips the search; REUSE_FROM=<tag> (not
                                             in a release run) takes that release's packages
                                             whatever its key, to test the reuse steps
  platform-engine.py version <zip> <version> rewrites a reused package's engine.json for this
                                             release (Android and iOS: their engine packages are
                                             the jobs' own)

platform: steam (the linux job), web, android, ios, macos. Run from the repository's root.

Android takes the debug engine package too: the smoke test drives the game through the REPL, which
the kit compiles into Debug builds only, so the debug APK is built from the debug package's engine
and the release APK from the release package's.
"""
import hashlib
import json
import os
import subprocess
import sys
import zipfile

FORMAT = "kagex-platform-engine 1"
NOTE = "kagex-engine-build.json"
REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

COMMON_PINS = ["ENGINE_SHA", "XP3CRYPT_SHA", "SCNFILE_SHA"]
# the workflow (every step of every job builds as it says), the clones
COMMON_FILES = [".github/workflows/platforms.yml", ".github/platforms/setup.sh"]
STATIC = [".github/platforms/monocypher-kit.cmake", ".github/platforms/scnfile-monocypher-names.h",
          ".github/platforms/krkrthreepp-kit.cmake", ".github/platforms/threepp-stb-names.h"]
KIT = [".github/platforms/kit-vcpkg.py", ".github/platforms/krkreffekseer-kit.cmake"]

PLATFORMS = {
    "steam": {
        "pins": ["KRKRZ_LINUX_SHA", "STEAMDEV_SHA"],
        "configs": {"linux-config.json": ["version"]},
        "files": ["tools/release/scripts/engine-package.py"],
    },
    "web": {
        "pins": ["KRKRZ_WEB_SHA"],
        "configs": {"web-config.json": []},
        "files": STATIC + [".github/platforms/web-plugins.py", ".github/platforms/live2d-web-kit.cmake",
                           ".github/platforms/krkreffekseer-kit.cmake", ".github/platforms/krkreffekseer-webgl.cpp",
                           "tools/live2d/build.py", "tools/live2d/web", "tools/live2d/patches", "tools/live2d/driver",
                           "tools/release/scripts/engine-package.py"],
    },
    "android": {
        "pins": ["KRKRZ_ANDROID_SHA"],
        "configs": {"app-config.json": ["versionCode", "versionName"]},
        "debug": True,
        "files": STATIC + KIT + [".github/platforms/kit-android-bootstrap.patch", ".github/platforms/krkreffekseer-odr.cpp",
                                 "tools/release/scripts/android-engine.py"],
    },
    "ios": {
        "pins": ["KRKRZ_IOS_SHA"],
        "configs": {"ios-config.json": ["version", "build"]},
        # the icon is compiled into the app (Assets.car), which a reuse keeps
        "files": STATIC + ["platform/icon-1024.png", "tools/release/scripts/ios-engine.py"],
    },
    "macos": {
        "pins": [],
        "configs": {},
        "files": [".github/platforms/krkreffekseer-apple.cmake", "tools/release/scripts/engine-package.py"],
    },
}


def die(message):
    sys.exit("platform-engine: " + message)


def without(value, drop):
    """A config without the keys a release changes (its version) and every comment"""
    if isinstance(value, dict):
        return {k: without(v, drop) for k, v in value.items() if k != "comment" and k not in drop}
    if isinstance(value, list):
        return [without(v, drop) for v in value]
    return value


def tracked(path):
    """The files git tracks at path (a file or a folder), relative to the repository"""
    out = subprocess.run(["git", "-C", REPO_ROOT, "ls-files", "-z", "--", path],
                         capture_output=True, check=True).stdout.decode("utf-8")
    names = sorted(n for n in out.split("\0") if n)
    if not names:
        die("%s isn't in the repository" % path)
    return names


def key_lines(platform):
    spec = PLATFORMS.get(platform)
    if spec is None:
        die("unknown platform %r (%s)" % (platform, ", ".join(PLATFORMS)))
    lines = [FORMAT, "platform " + platform]
    for pin in COMMON_PINS + spec["pins"]:
        value = os.environ.get(pin, "")
        if not value:
            die("%s isn't set: the key can't leave out a commit the build uses" % pin)
        lines.append("pin %s %s" % (pin, value))
    for name, drop in sorted(spec["configs"].items()):
        with open(os.path.join(REPO_ROOT, name), encoding="utf-8") as f:
            config = without(json.load(f), drop)
        text = json.dumps(config, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        lines.append("config %s %s" % (name, hashlib.sha256(text.encode("utf-8")).hexdigest()))
    for path in COMMON_FILES + spec["files"]:
        for name in tracked(path):
            with open(os.path.join(REPO_ROOT, name), "rb") as f:
                lines.append("file %s %s" % (name, hashlib.sha256(f.read()).hexdigest()))
    return lines


def packages(platform):
    """The engine packages a reuse takes"""
    names = ["kagex_engine_%s.zip" % platform]
    if PLATFORMS[platform].get("debug"):
        names.append("kagex_engine_%s_debug.zip" % platform)
    return names


def key(platform):
    return hashlib.sha256("\n".join(key_lines(platform)).encode("utf-8")).hexdigest()


def gh_json(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, check=True).stdout
    return json.loads(out)


def gh_asset(repo, asset_id, dest):
    with open(dest, "wb") as f:
        subprocess.run(["gh", "api", "-H", "Accept: application/octet-stream",
                        "repos/%s/releases/assets/%d" % (repo, asset_id)], stdout=f, check=True)


def find(platform, out_path):
    repo = os.environ.get("REPO") or os.environ.get("GITHUB_REPOSITORY") or die("REPO isn't set")
    k = key(platform)
    wanted = packages(platform)
    key_dir = os.environ.get("ENGINE_KEY_DIR", "engine-key")
    os.makedirs(key_dir, exist_ok=True)
    with open(os.path.join(key_dir, platform + ".key"), "w") as f:
        f.write(k + "\n")
    print("%s engine key %s" % (platform, k))
    for line in key_lines(platform):
        print("  " + line)
    tag = ""
    found = []
    forced = os.environ.get("REUSE_FROM", "").strip()
    in_release = os.environ.get("GITHUB_WORKFLOW", "") == "Release packages"
    if forced and in_release:
        die("REUSE_FROM is for testing the reuse steps, never for a release")
    if os.environ.get("REBUILD", "").lower() == "true" and not forced:
        print("REBUILD: the engine is built")
    else:
        releases = sorted(gh_json("repos/%s/releases?per_page=50" % repo),
                          key=lambda r: r["created_at"], reverse=True)
        for r in releases:
            if r.get("draft"):
                continue
            assets = {a["name"]: a for a in r.get("assets", [])}
            if forced:
                if r["tag_name"] != forced:
                    continue
                missing = [p for p in wanted if p not in assets]
                if missing:
                    die("release %s has no %s" % (forced, ", ".join(missing)))
                tag, found = forced, [assets[p] for p in wanted]
                print("REUSE_FROM: %s's %s, whatever its key (a test of the reuse steps)" % (forced, ", ".join(wanted)))
                break
            if NOTE not in assets or any(p not in assets for p in wanted):
                continue
            note_path = os.path.join(key_dir, "note.json")
            gh_asset(repo, assets[NOTE]["id"], note_path)
            try:
                with open(note_path, encoding="utf-8") as f:
                    note = json.load(f)
            except (OSError, ValueError):
                continue
            finally:
                if os.path.exists(note_path):
                    os.remove(note_path)
            if (note.get("platforms") or {}).get(platform) == k:
                tag, found = r["tag_name"], [assets[p] for p in wanted]
                break
        if forced and not tag:
            die("there's no release %s" % forced)
    if tag:
        engine_dir = os.environ.get("ENGINE_DIR", "engine")
        os.makedirs(engine_dir, exist_ok=True)
        for asset in found:
            gh_asset(repo, asset["id"], os.path.join(engine_dir, asset["name"]))
        print("reusing %s of release %s: the engine isn't built" % (", ".join(wanted), tag))
    else:
        print("no release has this engine: it's built")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(("%s: reusing the engine of release %s (key %s)\n" % (platform, tag, k[:16])) if tag
                    else ("%s: building the engine (key %s)\n" % (platform, k[:16])))
    with open(out_path, "a", encoding="utf-8") as f:
        f.write("key=%s\nreuse=%s\n" % (k, tag))


def version(zip_path, new_version):
    """engine.json's version, every other entry copied as it is"""
    tmp = zip_path + ".tmp"
    with zipfile.ZipFile(zip_path) as zin, zipfile.ZipFile(tmp, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info)
            if info.filename == "engine.json":
                manifest = json.loads(data)
                print("%s: engine.json version %s -> %s" % (zip_path, manifest.get("version"), new_version))
                manifest["version"] = new_version
                data = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
            zout.writestr(info, data, compress_type=info.compress_type)
    os.replace(tmp, zip_path)


def main(argv):
    if len(argv) == 2 and argv[0] == "key":
        print(key(argv[1]))
    elif len(argv) == 3 and argv[0] == "find":
        find(argv[1], argv[2])
    elif len(argv) == 3 and argv[0] == "version":
        version(argv[1], argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
