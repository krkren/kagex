# tools/live2d

Builds the krkrlive2d plugin, which draws Live2D characters (`doc/world.txt`, "Live2D
Characters"), with your own copy of Live2D's Cubism SDK for Native. kagex holds no part of the
SDK: download it from Live2D (https://www.live2d.com/en/sdk/download/native/), which agrees to its
licences, and keep it, and the plugin built with it, out of the repository.

`setup.py` walks you through it: Live2D's licences, what this computer needs (and how to get
what's missing), the SDK, the plugin built for the engine next to `data/` and into
`plugins/<platform>/` for your game's packages, Hiyori if you want her, the notice for your
players (`LIVE2D-NOTICE.txt`, added to release.json's extra files) and a quick check that the
engine draws Live2D characters. It asks before each step; `--check` only reports.

```sh
python3 tools/live2d/setup.py
```

What it does, by hand:

## Windows, Linux and macOS

```sh
python3 tools/live2d/build.py --sdk ~/Downloads/CubismSdkForNative-5-r.5.zip
```

puts `libkrkrlive2d.so` (Linux), `libkrkrlive2d.dylib` (macOS) or `krkrlive2d.dll` (Windows) in
`plugin/`, where the engine next to `data/` finds it. It needs git, CMake 3.22+ and a C++17
compiler (Visual Studio on Windows, from its developer command prompt when Ninja is there);
`--arch` picks the engine's architecture on macOS (arm64, x86_64) and Windows (Win32, x64). It
builds as krkrlive2d's own presets do (C++17, and on Windows the static runtime the Core's
library is made for).

For a release, build it into `plugins/<platform>/` instead (`--out plugins/linux`,
`plugins/windows`, `plugins/macos`), which kagex-release copies into that platform's packages
(`tools/release/README.md`, "Your own plugins"). Build the Linux one with `--steamrt`: a Linux
plugin needs the glibc of the system it's built on, and `--steamrt` builds it in Valve's Steam
Linux Runtime (sniper) SDK container (docker or podman; glibc 2.31, which krkrz_linux's Steam
engine is built in too), with Debian's own GCC 10, so it loads on every Linux the engines run on
and inside the Steam Runtime, and errors it reports reach your scripts (the SDK's newer GCC links
an unwinder into the plugin, and an error crossing it stops the game: `UPSTREAM.md` 2). In
Steam's own engine (krkrz_linux's), whose engine and plugins each have an unwinder of their own,
such an error can still stop the game, as with every plugin there.

## Android and iOS

These engines have their plugins linked in, so the plugin is built with the engine, by the
platform's kit (krkrz_android, krkrz_ios), as `.github/workflows/platforms.yml` builds the
sample's apps:

```sh
python3 tools/live2d/build.py --sdk <the SDK> --kit app-config.json     # or ios-config.json
set -a; . tools/live2d/build/kit.env; set +a                             # then the kit's build
```

`--kit` fetches and patches the sources, puts the plugin's folder first among the config's
`pluginFolders` (krkrz_dev has an older krkrlive2d, and the first folder with the plugin wins),
adds `krkrlive2d` to its plugins, and writes the environment the plugin's and the driver's CMake
read to `kit.env`. An engine built so holds the Cubism Core: for kagex-release, make your game's
own engine package of it (`tools/release/scripts/android-engine.py` or `ios-engine.py`, which
refuse a package holding the Core unless given `--with-cubism-core`) and put it in `engines/`
next to `data/`. The web has no Cubism Core for Native: it would need Live2D's Cubism Core for
Web bridged into the engine (`TODO.md`).

## What's here

- `build.py` fetches the sources at the commits kagex is tested with (krkrlive2d, its driver
  wtnbgo/live2d with its submodules, tp_stub and ncbind) into `tools/live2d/build/`
  (gitignored), applies `patches/`, and builds with `KRKRZ_VARIANT=SDL`.
- `patches/krkrlive2d.patch` and `patches/live2d.patch` fix what stops the plugin compiling
  with GCC and Clang, and the plugin's file reader throwing for a file the driver only looks
  for, which kept every model without a `.vmotion3.json` from loading (`UPSTREAM.md`).
  `patches/live2d-CubismNativeFramework.patch` (applied in the driver's CubismNativeFramework
  submodule) compiles each of Cubism 5.3's blend-mode shaders the first time a model draws with
  it, rather than all 474 before the first frame, which stood the game still for seconds when
  its first Live2D character appeared (`UPSTREAM.md`). They're kept byte for byte (CRLF where
  the sources have it).
- `driver/CMakeLists.txt` builds the driver on Linux, macOS, Android and iOS, which its own
  CMake doesn't do (it has no Linux or macOS build, and its iOS build looks for the Core's
  libraries where Cubism 5 R5 no longer puts them): the Core's static library from the SDK, the
  Cubism Native Framework's OpenGL ES 2 renderer (through GLAD on Linux and macOS, the system's
  GLES on Android and iOS), minizip-ng (the engine's on Android and iOS, where one binary can't
  hold two) and KTX (read only). On Windows it hands over to the driver's own.

CI (`.github/workflows/live2d.yml`) builds it on Windows, Linux (in the Steam Runtime) and macOS,
and into the Android and iOS engines, with the SDK from the private repository krkren/cubism-sdk
(the `CUBISM_SDK_TOKEN` secret), and runs the smoke test with Live2D required on each. It also
does what this page describes for a game: the desktop jobs build the sample with the plugin in
`plugins/<platform>/`, and the Android and iOS jobs make a game's own engine package
(`--with-cubism-core`) into `engines/` and build the sample from it, all with kagex-release, and
test what comes out. Only logs leave the runners, but for the sample game packages a run started
with a release's tag adds to that release.

## The licence

The plugin holds the Cubism Core, which Live2D's licence lets a game ship inside the game, not
in anything handed to other developers: put it in your game's packages only, with terms for
your players that protect it as the licence says. A business with yearly sales of 10 million
yen or more also needs Live2D's release licence, and an "Expandable Application" (one that can
show any number of models) needs Live2D's approval (`doc/world.txt`).
