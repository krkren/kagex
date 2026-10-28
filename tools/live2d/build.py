#!/usr/bin/env python3
"""Builds the krkrlive2d plugin, which draws Live2D characters (doc/world.txt, "Live2D
Characters"), with your copy of Live2D's Cubism SDK for Native, for the engine on this computer.

    python3 tools/live2d/build.py --sdk ~/Downloads/CubismSdkForNative-5-r.5.zip

It fetches the plugin's sources at the commits kagex is tested with (SOURCES below), applies
kagex's fixes to them (patches/; UPSTREAM.md says what they fix), builds them with the SDK's
Cubism Core, and puts the plugin in plugin/ (libkrkrlive2d.so on Linux, libkrkrlive2d.dylib on
macOS, krkrlive2d.dll on Windows), where KAGLive2D (GFX_Live2D.tjs) links it.

The Cubism Core is Live2D's, under its Proprietary Software License: a game may ship it inside
the game, so the plugin goes into your game's packages, but not into anything handed to other
developers (an engine package, a template), and the game's terms for its players protect it as
the licence says. Download the SDK from Live2D yourself, which agrees to its licences; kagex
never holds a copy. A business with yearly sales of 10 million yen or more needs Live2D's release
licence for the game, and an "Expandable Application" (one that can show any number of models,
as an avatar or streaming app does) needs Live2D's approval whoever makes it.

--sdk is the SDK's zip, the folder it unzips to, or its Core folder (the CUBISM_SDK_CORE
environment variable, when there's no --sdk). It needs git, CMake 3.22 or newer (KTX-Software's
minimum) and a C++17 compiler: on Windows, Visual Studio, run from its developer command prompt
for the engine's architecture when Ninja is used (else --arch picks it).

A Linux plugin needs the glibc of the system it's built on: --steamrt builds it in Valve's Steam
Linux Runtime (sniper) SDK container (docker or podman; glibc 2.31, as krkrz_linux's Steam
engine), so it loads on every Linux the engines run on and inside the Steam Runtime. Use it for a
release.

Linux, macOS, Android and iOS build the driver through tools/live2d/driver (its own CMake builds
for Windows, Android and iOS only, and its iOS build wants the Core's libraries where Cubism 5
R5 no longer has them); Windows builds it with its own. Android and iOS link every plugin into
the engine, so there the plugin is built with the engine by the platform's kit (krkrz_android,
krkrz_ios): --kit <the kit config> fetches and patches the sources, adds the plugin to the
config and writes the environment the kit's build needs to <work>/kit.env.

usage: python3 tools/live2d/build.py [--sdk PATH] [--out DIR] [--work DIR] [--arch ARCH] [--jobs N] [--steamrt]
       python3 tools/live2d/build.py --sdk PATH --kit app-config.json|ios-config.json [--work DIR]
"""
import argparse, glob, os, platform, shutil, subprocess, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

# name: repository, commit, its submodules too
SOURCES = {
    "krkrlive2d": ("https://github.com/wamsoft/krkrlive2d", "8edeb8e6d83345764b10f7f05cfd45bb530a1fc5", False),
    "live2d":     ("https://github.com/wtnbgo/live2d",      "58c4c66f672b3a60521a7a820ef29f0ce006d6a1", True),
    "tp_stub":    ("https://github.com/wamsoft/tp_stub",    "35ef31ad063023198346d8c57f2c411d8d597a9d", False),
    "ncbind":     ("https://github.com/wamsoft/ncbind",     "256502b817e6627c1491b916938448470df395fd", False),
}

# patches to a source's submodules: name: {its folder: the patch}. The Cubism Native
# Framework's compiles each blend-mode shader set the first time it's drawn with, rather than all
# 474 up front (UPSTREAM.md)
SUBMODULE_PATCHES = {
    "live2d": {"external/CubismNativeFramework": "live2d-CubismNativeFramework.patch"},
}

# the oldest Cubism Core the driver was made for (its CMakeLists.txt checks it too)
CORE_VERSION = (6, 0, 1)


def run(args, cwd=None, env=None):
    print("+ " + " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)


def git(path, *args):
    return subprocess.run(["git", "-C", path] + list(args), check=True,
                          capture_output=True, text=True).stdout.strip()


def find_core(sdk, work):
    """The SDK's Core folder (include/Live2DCubismCore.h), from its zip, its folder or itself"""
    if not sdk:
        sys.exit("No Cubism SDK: give --sdk (the SDK's zip or folder) or set CUBISM_SDK_CORE.\n"
                 "Download the Cubism SDK for Native from https://www.live2d.com/en/sdk/download/native/")
    sdk = os.path.abspath(os.path.expanduser(sdk))
    if os.path.isfile(sdk) and zipfile.is_zipfile(sdk):
        dest = os.path.join(work, "sdk")
        stamp = os.path.join(dest, ".from")
        if not (os.path.exists(stamp) and open(stamp).read() == sdk):
            shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(dest)
            with zipfile.ZipFile(sdk) as z:
                # only its Core folder
                for n in z.namelist():
                    parts = n.split("/")
                    if "Core" in parts[:2] and not n.endswith("/") and ".." not in parts:
                        z.extract(n, dest)
            with open(stamp, "w") as f:
                f.write(sdk)
        sdk = dest
    for cand in [sdk, os.path.join(sdk, "Core")] + glob.glob(os.path.join(sdk, "*", "Core")):
        if os.path.exists(os.path.join(cand, "include", "Live2DCubismCore.h")):
            return cand
    sys.exit("%s isn't the Cubism SDK for Native, its zip or its Core folder" % sdk)


def core_version(core):
    import re
    with open(os.path.join(core, "CHANGELOG.md"), encoding="utf-8") as f:
        m = re.search(r"Upgrade Core version to (\d+)\.(\d+)\.(\d+)", f.read())
    return tuple(int(x) for x in m.groups()) if m else None


def fetch(work, name):
    """A clean checkout of a source at its commit, with kagex's patch for it applied"""
    url, commit, submodules = SOURCES[name]
    path = os.path.join(work, "src", name)
    if not os.path.isdir(os.path.join(path, ".git")):
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path)
        git(path, "init", "-q")
        git(path, "remote", "add", "origin", url)
    git(path, "remote", "set-url", "origin", url)
    # the sources byte for byte, so kagex's patches (CRLF where the sources have it) apply
    git(path, "config", "core.autocrlf", "false")
    try:
        have = git(path, "rev-parse", "HEAD")
    except subprocess.CalledProcessError:
        have = ""
    if have != commit:
        print("fetching %s at %s" % (name, commit[:7]), flush=True)
        git(path, "fetch", "-q", "--depth", "1", "origin", commit)
        git(path, "checkout", "-q", "--force", commit)
    # as fetched, without an earlier build's patch
    git(path, "reset", "-q", "--hard", commit)
    git(path, "clean", "-q", "-fdx")
    if submodules:
        # its own (the build needs none of theirs: KTX-Software's tests, the samples' Framework),
        # byte for byte too, and --force to undo an earlier build's patch in them
        print("fetching %s's submodules" % name, flush=True)
        run(["git", "-c", "core.autocrlf=false", "-C", path, "submodule", "update", "--init", "--force", "--depth", "1"])
    patch = os.path.join(HERE, "patches", name + ".patch")
    if os.path.exists(patch):
        run(["git", "-C", path, "apply", "--whitespace=nowarn", patch])
    # its submodules' (SUBMODULE_PATCHES)
    for sub, sub_patch in SUBMODULE_PATCHES.get(name, {}).items():
        run(["git", "-C", os.path.join(path, sub), "apply", "--whitespace=nowarn",
             os.path.join(HERE, "patches", sub_patch)])
    return path


def kit(config, work, core, src):
    """Readies an Android or iOS kit (krkrz_android, krkrz_ios), which links every plugin into the
    engine, to build krkrlive2d with it: the folder that holds the plugin's checkout goes first in
    the config's pluginFolders (krkrz_dev has an older krkrlive2d, and the first folder with the
    plugin wins), krkrlive2d at the end of its plugins (and staticPlugins, where it has them),
    and <work>/kit.env gets the environment the plugin's and the driver's CMake read
    (LIVE2DLIB_FOLDER, LIVE2D_DRIVER_SOURCE, CUBISM_SDK_CORE), one NAME=value a line, for the
    kit's build. The engine built so holds the Cubism Core: it goes into the game's packages
    only, never into an engine package for other developers"""
    import json
    with open(config, encoding="utf-8") as f:
        cfg = json.load(f)
    cm = cfg.setdefault("cmake", {})
    folder = os.path.dirname(src["krkrlive2d"]).replace("\\", "/")
    cm["pluginFolders"] = [folder] + [x for x in cm.get("pluginFolders", []) if x != folder]
    for key in ("plugins", "staticPlugins"):
        if key in cm or key == "plugins":
            cm[key] = [x for x in cm.get(key, []) if x != "krkrlive2d"] + ["krkrlive2d"]
    with open(config, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)
        f.write("\n")
    envfile = os.path.join(work, "kit.env")
    with open(envfile, "w", encoding="utf-8") as f:
        f.write("LIVE2DLIB_FOLDER=%s\n" % os.path.join(HERE, "driver").replace("\\", "/"))
        f.write("LIVE2D_DRIVER_SOURCE=%s\n" % src["live2d"].replace("\\", "/"))
        f.write("CUBISM_SDK_CORE=%s\n" % core.replace("\\", "/"))
    print("%s: krkrlive2d from %s; the kit's build needs the environment in %s" % (config, folder, envfile))


# --steamrt: Valve's Steam Linux Runtime 3.0 (sniper) SDK, Debian 11 with glibc 2.31 and a
# backported GCC 14, which krkrz_linux builds the Steam engine in: a plugin built there loads on
# every Linux the engines run on and inside the Steam Runtime; one built on a newer system needs
# that system's glibc. Its CMake is too old for KTX-Software, so a newer one is fetched
STEAMRT_IMAGE = "registry.gitlab.steamos.cloud/steamrt/sniper/sdk:latest"
STEAMRT_CMAKE = "3.31.7"
STEAMRT_NINJA = "1.12.1"


def steamrt(opts):
    """Runs this build again in the Steam Runtime's SDK container (docker or podman), with the
    folders it reads and writes at the same paths inside"""
    tool = shutil.which("docker") or shutil.which("podman")
    if not tool:
        sys.exit("--steamrt needs docker or podman")
    work, out = os.path.abspath(opts.work), os.path.abspath(opts.out)
    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    sdk = os.path.abspath(os.path.expanduser(opts.sdk)) if opts.sdk else ""
    paths = [ROOT, work, out] + ([sdk if os.path.isdir(sdk) else os.path.dirname(sdk)] if sdk else [])
    mounts = []
    for m in sorted(set(paths), key=len):
        if not any(m == x or m.startswith(x + os.sep) for x in mounts):
            mounts.append(m)
    args = [tool, "run", "--rm", "--user", "%d:%d" % (os.getuid(), os.getgid()),
            "-e", "HOME=/tmp", "-e", "CC=gcc-14", "-e", "CXX=g++-14"]
    for m in mounts:
        args += ["-v", "%s:%s" % (m, m)]
    args += ["-w", ROOT, STEAMRT_IMAGE, "python3", "-B", os.path.join(HERE, "build.py"), "--in-steamrt",
             "--work", work, "--out", out, "--jobs", str(opts.jobs)] + (["--sdk", sdk] if sdk else [])
    run([tool, "pull", "-q", STEAMRT_IMAGE])
    run(args)


def steamrt_tools(work):
    """Inside the Steam Runtime: CMake and Ninja new enough, from their GitHub releases, cached
    in <work>/steamrt-tools, ahead of the image's on the PATH"""
    import io, tarfile, urllib.request
    base = os.path.join(work, "steamrt-tools")
    cmake_dir = os.path.join(base, "cmake-%s-linux-x86_64" % STEAMRT_CMAKE)
    if not os.path.exists(os.path.join(cmake_dir, "bin", "cmake")):
        url = "https://github.com/Kitware/CMake/releases/download/v%s/cmake-%s-linux-x86_64.tar.gz" % (STEAMRT_CMAKE, STEAMRT_CMAKE)
        print("fetching " + url, flush=True)
        with urllib.request.urlopen(url) as r, tarfile.open(fileobj=io.BytesIO(r.read()), mode="r:gz") as t:
            t.extractall(base)
    ninja_dir = os.path.join(base, "ninja-" + STEAMRT_NINJA)
    if not os.path.exists(os.path.join(ninja_dir, "ninja")):
        url = "https://github.com/ninja-build/ninja/releases/download/v%s/ninja-linux.zip" % STEAMRT_NINJA
        print("fetching " + url, flush=True)
        with urllib.request.urlopen(url) as r, zipfile.ZipFile(io.BytesIO(r.read())) as z:
            os.makedirs(ninja_dir, exist_ok=True)
            z.extract("ninja", ninja_dir)
        os.chmod(os.path.join(ninja_dir, "ninja"), 0o755)
    os.environ["PATH"] = os.pathsep.join([os.path.join(cmake_dir, "bin"), ninja_dir, os.environ.get("PATH", "")])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--sdk", default=os.environ.get("CUBISM_SDK_CORE"),
                    help="the Cubism SDK for Native's zip, its folder or its Core folder")
    ap.add_argument("--out", default=os.path.join(ROOT, "plugin"), help="where the plugin goes (plugin/)")
    ap.add_argument("--work", default=os.path.join(HERE, "build"), help="sources and build (tools/live2d/build)")
    ap.add_argument("--arch", help="macOS: arm64 or x86_64; Windows: Win32 or x64 (the engine's)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--kit", metavar="CONFIG",
                    help="Android and iOS: don't build; ready the sources for a kit's engine build "
                         "instead, adding the plugin to the kit config (app-config.json or "
                         "ios-config.json) and writing the environment it needs to <work>/kit.env")
    ap.add_argument("--steamrt", action="store_true",
                    help="Linux: build in the Steam Linux Runtime's SDK container (docker or podman), "
                         "so the plugin loads on every Linux the engines run on, Steam's runtime too")
    ap.add_argument("--in-steamrt", action="store_true", help=argparse.SUPPRESS)
    opts = ap.parse_args()
    if opts.steamrt:
        if not sys.platform.startswith("linux"):
            sys.exit("--steamrt builds the Linux plugin, on Linux")
        return steamrt(opts)
    if opts.in_steamrt:
        steamrt_tools(os.path.abspath(opts.work))

    for tool in ("git", "cmake"):
        if not shutil.which(tool):
            sys.exit("build.py needs %s" % tool)
    work = os.path.abspath(opts.work)
    os.makedirs(work, exist_ok=True)

    core = find_core(opts.sdk, work)
    version = core_version(core)
    if version is None or version < CORE_VERSION:
        sys.exit("Cubism Core %s is older than the driver needs (%d.%d.%d or newer): use a newer SDK"
                 % ((".".join(str(v) for v in version) if version else "(unknown)",) + CORE_VERSION))
    print("Cubism Core %s at %s" % (".".join(str(v) for v in version), core), flush=True)

    src = {name: fetch(work, name) for name in SOURCES}
    if opts.kit:
        return kit(opts.kit, work, core, src)

    build = os.path.join(work, "build-" + (opts.arch or platform.machine() or "host"))
    env = dict(os.environ)
    env["CUBISM_SDK_CORE"] = core
    env["LIVE2DLIB_FOLDER"] = os.path.join(HERE, "driver")
    env["LIVE2D_DRIVER_SOURCE"] = src["live2d"]
    # as krkrlive2d's own presets: C++17, and on Windows the static runtime the driver's Core
    # library (Live2DCubismCore_MT.lib) is built for
    args = ["cmake", "-S", src["krkrlive2d"], "-B", build,
            "-DCMAKE_BUILD_TYPE=Release", "-DKRKRZ_VARIANT=SDL",
            "-DCMAKE_CXX_STANDARD=17", "-DCMAKE_CXX_STANDARD_REQUIRED=ON",
            "-DTPSTUB_DIR=" + src["tp_stub"], "-DNCBIND_DIR=" + src["ncbind"],
            "-DLIVE2DLIB_FOLDER=" + env["LIVE2DLIB_FOLDER"],
            "-DLIVE2D_DRIVER_SOURCE=" + src["live2d"], "-DCUBISM_SDK_CORE=" + core]
    if sys.platform == "win32":
        args += ["-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded$<$<CONFIG:Debug>:Debug>"]
        if shutil.which("ninja") and shutil.which("cl"):
            args += ["-G", "Ninja", "-DCMAKE_C_COMPILER=cl", "-DCMAKE_CXX_COMPILER=cl"]
        elif opts.arch:
            args += ["-A", opts.arch]
    else:
        if shutil.which("ninja"):
            args += ["-G", "Ninja"]
        if sys.platform == "darwin" and opts.arch:
            args += ["-DCMAKE_OSX_ARCHITECTURES=" + opts.arch]
    run(args, env=env)
    run(["cmake", "--build", build, "--config", "Release", "--parallel", str(opts.jobs)], env=env)

    names = {"win32": "krkrlive2d.dll", "darwin": "libkrkrlive2d.dylib"}.get(sys.platform, "libkrkrlive2d.so")
    found = [p for p in glob.glob(os.path.join(build, "**", names), recursive=True) if os.path.isfile(p)]
    if not found:
        sys.exit("the build made no %s" % names)
    os.makedirs(opts.out, exist_ok=True)
    out = os.path.join(opts.out, names)
    shutil.copy2(found[0], out)
    shown = os.path.relpath(out, ROOT) if os.path.abspath(out).startswith(ROOT + os.sep) else out
    print("%s: %d bytes. It holds the Cubism Core: it goes into your game's packages, and into "
          "nothing handed to other developers." % (shown, os.path.getsize(out)))


if __name__ == "__main__":
    main()
