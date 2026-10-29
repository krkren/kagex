#!/usr/bin/env python3
"""Live2D setup: adds Live2D characters to this copy of KAGEX and to your game's builds.

kagex's packages can't carry Live2D's Cubism Core (its licence lets it go out inside a game only),
so the plugin that draws Live2D characters, krkrlive2d, is built here with your own copy of
Live2D's Cubism SDK for Native. This walks you through it, one question at a time:

  1. Live2D's licences, which you agree to.
  2. What this computer needs (git, CMake, a C++ compiler; docker or podman for a Linux release),
     and how to get what's missing.
  3. What the game has already (models, the engine next to data/, the plugin).
  4. The Cubism SDK for Native (you download it from Live2D).
  5. The plugin, built (build.py) into plugins/<platform>/ for kagex-release to put into your
     game's packages for this platform, and beside the engine next to data/, so this copy plays
     Live2D characters. Run it again on each platform you release for (Windows, Linux, macOS);
     Android and iOS build it into the engine with their kits, and this says how.
  6. Hiyori (the sample's Live2D character), if you want her, and Live2D's notice for your
     players (LIVE2D-NOTICE.txt, added to release.json's extra files).
  7. A quick check that the engine draws Live2D characters.

It asks before doing anything; the options answer its questions ahead (and --yes takes the
answer it would suggest for the rest), so it can run unattended:

  python3 tools/live2d/setup.py
  python3 tools/live2d/setup.py --sdk ~/Downloads/CubismSdkForNative-5-r.5.zip --accept-license --yes
  python3 tools/live2d/setup.py --check           # only report what's there and what's missing
"""
import argparse, glob, json, os, platform, re, shutil, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data")
SDK_URL = "https://www.live2d.com/en/sdk/download/native/"
LICENSES = [
    ("Live2D Proprietary Software License Agreement (the Cubism Core)",
     "https://www.live2d.com/eula/live2d-proprietary-software-license-agreement_en.html"),
    ("Live2D Open Software License Agreement (the Cubism Native Framework)",
     "https://www.live2d.com/eula/live2d-open-software-license-agreement_en.html"),
    ("Live2D Free Material License Agreement (Live2D's sample models: Hiyori)",
     "https://www.live2d.com/eula/live2d-free-material-license-agreement_en.html"),
]
NOTICE = "LIVE2D-NOTICE.txt"


def host():
    return {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")


def plugin_name(h):
    return {"windows": "krkrlive2d.dll", "macos": "libkrkrlive2d.dylib"}.get(h, "libkrkrlive2d.so")


class Ui:
    def __init__(self, opts):
        self.opts = opts

    def say(self, text=""):
        print(text, flush=True)

    def step(self, n, title):
        print("\n== %d. %s" % (n, title), flush=True)

    def ask(self, question, default=True, answer=None):
        """yes or no: the option's answer when given, the default with --yes or no terminal"""
        if answer is not None:
            self.say("%s %s" % (question, "yes" if answer else "no"))
            return answer
        if self.opts.yes or not sys.stdin.isatty():
            self.say("%s %s" % (question, "yes" if default else "no"))
            return default
        while True:
            r = input("%s [%s] " % (question, "Y/n" if default else "y/N")).strip().lower()
            if not r:
                return default
            if r in ("y", "yes"):
                return True
            if r in ("n", "no"):
                return False


def run_text(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def cmake_version():
    m = re.search(r"cmake version (\d+)\.(\d+)", run_text(["cmake", "--version"]))
    return (int(m.group(1)), int(m.group(2))) if m else None


def visual_studio():
    """Visual Studio's folder when it has the C++ tools (vswhere)"""
    vswhere = os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                           "Microsoft Visual Studio", "Installer", "vswhere.exe")
    if not os.path.exists(vswhere):
        return ""
    return run_text([vswhere, "-latest", "-products", "*", "-requires",
                     "Microsoft.VisualStudio.Component.VC.Tools.x86.x64", "-property", "installationPath"]).strip()


def container_tool():
    for t in ("docker", "podman"):
        if shutil.which(t) and subprocess.run([t, "info"], capture_output=True).returncode == 0:
            return t
    return ""


def check_computer(ui):
    """[(what, ok, how to get it)] for this computer; the build needs all but the container tool"""
    h = host()
    cm = cmake_version()
    rows = [
        ("Python 3.8+", sys.version_info >= (3, 8), "https://www.python.org/downloads/"),
        ("git", bool(shutil.which("git")), "https://git-scm.com/downloads"),
        ("CMake 3.22+", bool(cm and cm >= (3, 22)), "https://cmake.org/download/ (or pip install cmake)"),
    ]
    if h == "windows":
        rows.append(("Visual Studio with C++ (Desktop development with C++)", bool(shutil.which("cl") or visual_studio()),
                     "https://visualstudio.microsoft.com/downloads/ (the Community edition, with \"Desktop development with C++\")"))
    elif h == "macos":
        rows.append(("Xcode's command line tools", bool(run_text(["xcrun", "--find", "clang++"]).strip()),
                     "xcode-select --install"))
    else:
        rows.append(("a C++ compiler (g++ or clang++)", bool(shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")),
                     "your distribution's build tools (build-essential, base-devel, ...)"))
    return rows


def find_sdk(ui, given):
    if given:
        p = os.path.abspath(os.path.expanduser(given))
        return p if os.path.exists(p) else ""
    places = [os.path.expanduser("~/Downloads"), os.path.expanduser("~/Desktop"), ROOT, os.getcwd()]
    found = []
    for d in places:
        found += glob.glob(os.path.join(d, "CubismSdkForNative-*.zip")) + glob.glob(os.path.join(d, "CubismSdkForNative-*", "Core"))
    found = sorted(set(found), key=lambda p: os.path.getmtime(p), reverse=True)
    if found:
        ui.say("Found the Cubism SDK: " + found[0])
        return found[0]
    if ui.opts.yes or not sys.stdin.isatty():
        return ""
    p = input("Where is the Cubism SDK for Native (its zip, or the folder it unzips to)? ").strip().strip('"')
    return os.path.abspath(os.path.expanduser(p)) if p and os.path.exists(os.path.expanduser(p)) else ""


def engine_here(h):
    """(the engine next to data/, the folder its plugins go in) when this copy of KAGEX has one"""
    if h == "windows" and os.path.exists(os.path.join(ROOT, "krkrz.exe")):
        return os.path.join(ROOT, "krkrz.exe"), os.path.join(ROOT, "plugin")
    if h == "linux" and os.path.exists(os.path.join(ROOT, "krkrz")):
        return os.path.join(ROOT, "krkrz"), os.path.join(ROOT, "plugin")
    if h == "macos":
        for app in glob.glob(os.path.join(ROOT, "*.app")):
            exe = os.path.join(app, "Contents", "MacOS", "krkrz")
            if os.path.exists(exe):
                return exe, os.path.dirname(exe)
    return "", ""


def build(ui, sdk, out, steamrt):
    args = [sys.executable, "-B", os.path.join(HERE, "build.py"), "--sdk", sdk, "--out", out]
    if steamrt:
        # its own build folder: the container's compiler isn't this computer's
        args += ["--steamrt", "--work", os.path.join(HERE, "build", "steamrt")]
    ui.say("+ " + " ".join(args))
    return subprocess.run(args).returncode == 0


def sign_app(ui, folder):
    """A macOS app whose files changed needs signing again (ad hoc) to start"""
    app = folder
    while app and not app.endswith(".app"):
        app = os.path.dirname(app)
    if app:
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app], check=False)
        ui.say("Signed %s again (ad hoc), as it changed" % os.path.basename(app))


def quick_check(ui, exe):
    """Starts the engine on data/ for a moment and asks whether it can draw Live2D characters"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import smoketest as st
    except ImportError:
        ui.say("(tools/smoketest.py isn't here: play the sample's Animated Character demo to see Hiyori)")
        return None
    os.environ.setdefault("SDL_VIDEO_DRIVER", {"windows": "windows", "macos": "cocoa"}.get(host(), "offscreen"))
    workdir = tempfile.mkdtemp(prefix="kagex-live2d-")
    eng = None
    try:
        eng = st.DesktopEngine(exe, DATA, workdir, False)
        eng.wait("the engine", "typeof global.kag != 'undefined'", timeout=90)
        r = str(eng.tjs('var s = KAGLive2DOf(kag); return s.available ? "ok" : s.reason;'))
        return r
    except Exception as e:
        return "the check didn't run: %s" % e
    finally:
        if eng is not None:
            eng.stop()
        shutil.rmtree(workdir, ignore_errors=True)


def add_notice(ui):
    """LIVE2D-NOTICE.txt next to data/, and in release.json's contents.extraFiles"""
    dest = os.path.join(ROOT, NOTICE)
    if not os.path.exists(dest):
        shutil.copyfile(os.path.join(HERE, NOTICE), dest)
        ui.say("Wrote %s: the terms your players agree to for the Cubism Core (edit it to fit your game's terms)" % NOTICE)
    rel = os.path.join(ROOT, "release.json")
    if os.path.exists(rel):
        with open(rel, encoding="utf-8") as f:
            s = json.load(f)
        extra = s.setdefault("contents", {}).setdefault("extraFiles", [])
        if NOTICE not in extra:
            extra.append(NOTICE)
            with open(rel, "w", encoding="utf-8") as f:
                json.dump(s, f, indent=2, ensure_ascii=False)
                f.write("\n")
            ui.say("Added %s to release.json's extra files: it goes into the Windows, Linux, macOS and web packages" % NOTICE)
    else:
        ui.say("When you make release.json (kagex-release), add %s to contents.extraFiles" % NOTICE)
    ui.say("Android and iOS apps take no extra files: put these terms where players agree to your game's terms")
    ui.say("there (the store listing's licence agreement, or a screen in the game).")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--sdk", help="the Cubism SDK for Native's zip, the folder it unzips to, or its Core folder")
    ap.add_argument("--accept-license", action="store_true", help="you have read and agree to Live2D's licences")
    ap.add_argument("--here", action="store_true", default=None, help="build the plugin for the engine next to data/")
    ap.add_argument("--no-here", dest="here", action="store_false")
    ap.add_argument("--release", action="store_true", default=None, help="build it into plugins/<platform>/ for kagex-release")
    ap.add_argument("--no-release", dest="release", action="store_false")
    ap.add_argument("--hiyori", action="store_true", default=None, help="fetch Hiyori, the sample's Live2D character")
    ap.add_argument("--no-hiyori", dest="hiyori", action="store_false")
    ap.add_argument("--yes", "-y", action="store_true", help="take the suggested answer to every question not answered")
    ap.add_argument("--check", action="store_true", help="only report what's there and what's missing")
    opts = ap.parse_args()
    ui = Ui(opts)
    h = host()
    exe, here_dir = engine_here(h)

    ui.say("Live2D setup for KAGEX (%s, %s)" % (ROOT, h))

    ui.step(1, "Live2D's licences")
    ui.say("The plugin holds Live2D's Cubism Core. You may put it in your game's packages, never in anything")
    ui.say("handed to other developers (an engine, a template, a toolkit), and your game's terms must protect it")
    ui.say("(LIVE2D-NOTICE.txt is a start). A business with yearly sales of 10 million yen or more needs Live2D's")
    ui.say("release licence; an \"Expandable Application\" (one that takes any number of models, as avatar and")
    ui.say("streaming apps do) needs Live2D's approval. Read them:")
    for name, url in LICENSES:
        ui.say("  %s\n    %s" % (name, url))
    if not opts.check:
        if not opts.accept_license:
            if opts.yes or not sys.stdin.isatty():
                sys.exit("Give --accept-license once you have read and agree to Live2D's licences.")
            if input("Type yes if you have read and agree to them: ").strip().lower() != "yes":
                sys.exit("Nothing was done.")

    ui.step(2, "This computer")
    rows = check_computer(ui)
    for what, ok, how in rows:
        ui.say("  %s %s%s" % ("ok     " if ok else "MISSING", what, "" if ok else "\n          " + how))
    ctool = container_tool() if h == "linux" else ""
    if h == "linux":
        ui.say("  %s docker or podman (a release build that loads on every Linux, in the Steam Runtime)%s"
               % ("ok     " if ctool else "missing", "" if ctool else "\n          https://docs.docker.com/engine/install/ (without it the plugin needs this system's glibc)"))
    missing = [r for r in rows if not r[1]]

    ui.step(3, "This game")
    l2d = [os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(DATA, "**", "*.l2d"), recursive=True)]
    ui.say("  Live2D models in data/: %s" % (", ".join(l2d) if l2d else "none yet"))
    ui.say("  the engine next to data/: %s" % (os.path.relpath(exe, ROOT) if exe else "none (a repository checkout: build the engine, or use a KAGEX package)"))
    here_plugin = os.path.join(here_dir, plugin_name(h)) if here_dir else ""
    ui.say("  its plugin: %s" % ("there" if here_plugin and os.path.exists(here_plugin) else "not yet"))
    rel_plugin = os.path.join(ROOT, "plugins", h, plugin_name(h))
    ui.say("  plugins/%s/ for kagex-release: %s" % (h, "there" if os.path.exists(rel_plugin) else "not yet"))
    if opts.check:
        sys.exit(1 if missing else 0)
    if missing:
        sys.exit("\nGet what's missing above, then run this again.")

    ui.step(4, "The Cubism SDK for Native")
    sdk = find_sdk(ui, opts.sdk)
    if not sdk:
        sys.exit("No Cubism SDK. Download the Cubism SDK for Native from %s\n(you agree to its licences there), then run\n"
                 "this again with --sdk <the zip>." % SDK_URL)

    ui.step(5, "The plugin")
    built_release = False
    if ui.ask("Build it into plugins/%s/, for kagex-release to put into your game's %s packages?" % (h, h),
              True, opts.release):
        out = os.path.join(ROOT, "plugins", h)
        if not build(ui, sdk, out, steamrt=bool(ctool)):
            sys.exit("The build failed: see above.")
        built_release = True
        if h == "linux" and not ctool:
            ui.say("Built without the Steam Runtime: the plugin needs this system's glibc (or newer) on your players' computers.")
    if here_dir and ui.ask("Put it beside the engine next to data/ (%s), so this copy plays Live2D characters?"
                           % os.path.relpath(here_dir, ROOT), True, opts.here):
        if built_release:
            os.makedirs(here_dir, exist_ok=True)
            shutil.copy2(rel_plugin, here_plugin)
            ui.say("Copied it to " + os.path.relpath(here_plugin, ROOT))
        elif not build(ui, sdk, here_dir, steamrt=False):
            sys.exit("The build failed: see above.")
        if h == "macos":
            sign_app(ui, here_dir)
    ui.say("\nOn the other platforms you release for:")
    others = [p for p in ("windows", "linux", "macos") if p != h]
    ui.say("  %s: run this there too (the plugin is built on the platform it's for)." % ", ".join(others))
    ui.say("  Android, iOS: their engines have the plugin linked in. With krkrz_android or krkrz_ios set up")
    ui.say("    (as .github/workflows/platforms.yml does), run")
    ui.say("      python3 tools/live2d/build.py --sdk <the SDK> --kit app-config.json   (ios-config.json)")
    ui.say("    and the kit's build with tools/live2d/build/kit.env's variables set, then make your game's")
    ui.say("    engine package from it (tools/release/scripts/android-engine.py or ios-engine.py, with")
    ui.say("    --with-cubism-core) into engines/ next to data/: tools/live2d/README.md.")
    ui.say("  The web: not yet (no Cubism Core for it: TODO.md).")

    ui.step(6, "Models and your players")
    hiyori = os.path.join(DATA, "fgimage", "hiyori.l2d")
    envinit = os.path.join(DATA, "main", "envinit.tjs")
    # the sample's envinit.tjs names her model ("model" => "hiyori"), and make_hiyori.py fetches it
    fetcher = os.path.join(ROOT, "tools", "assets", "make_hiyori.py")
    wants_hiyori = os.path.exists(envinit) and \
        re.search(r'"model"\s*=>\s*"hiyori"', open(envinit, encoding="utf-8", errors="replace").read()) is not None
    if not os.path.exists(hiyori) and wants_hiyori and not os.path.exists(fetcher):
        ui.say("The sample's Hiyori isn't here, and neither is tools/assets/make_hiyori.py, which fetches her: copy it")
        ui.say("from the repository (at this release's tag) and run this again to fetch her.")
    elif not os.path.exists(hiyori) and wants_hiyori and \
            ui.ask("Fetch Hiyori, the sample's Live2D character (Live2D's Free Material License)?", True, opts.hiyori):
        r = subprocess.run([sys.executable, "-B", os.path.join(ROOT, "tools", "assets", "make_hiyori.py"), "model", "--accept-license"])
        ui.say("Hiyori: " + ("data/fgimage/hiyori.l2d" if r.returncode == 0 else "couldn't be fetched (see above)"))
    add_notice(ui)

    ui.step(7, "A quick check")
    if exe and os.path.exists(here_plugin):
        r = quick_check(ui, exe)
        if r == "ok":
            ui.say("The engine draws Live2D characters. Play the sample's Animated Character demo to see Hiyori.")
        elif r is not None:
            ui.say("Not yet: " + r)
    else:
        ui.say("(no engine next to data/ with the plugin to check)")
    ui.say("\nDone. tools/live2d/README.md has the details; doc/world.txt, \"Live2D Characters\", how to use them.")


if __name__ == "__main__":
    main()
