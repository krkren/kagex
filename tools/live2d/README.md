# tools/live2d

Builds the krkrlive2d plugin, which draws Live2D characters (`doc/world.txt`, "Live2D
Characters"), with your own copy of Live2D's Cubism SDK for Native. kagex holds no part of the
SDK: download it from Live2D (https://www.live2d.com/en/sdk/download/native/), which agrees to its
licences, and keep it, and the plugin built with it, out of the repository.

```sh
python3 tools/live2d/build.py --sdk ~/Downloads/CubismSdkForNative-5-r.5.zip
```

puts `libkrkrlive2d.so` (Linux), `libkrkrlive2d.dylib` (macOS) or `krkrlive2d.dll` (Windows) in
`plugin/`. It needs git, CMake 3.22+ and a C++17 compiler (Visual Studio on Windows, from its
developer command prompt when Ninja is there); `--arch` picks the engine's architecture on macOS
(arm64, x86_64) and Windows (Win32, x64). Tested on Linux; the macOS and Windows builds are
written but haven't been run yet. It builds as krkrlive2d's own presets do (C++17, and on Windows
the static runtime the Core's library is made for).

- `build.py` fetches the sources at the commits kagex is tested with (krkrlive2d, its driver
  wtnbgo/live2d with its submodules, tp_stub and ncbind) into `tools/live2d/build/`
  (gitignored), applies `patches/`, and builds with `KRKRZ_VARIANT=SDL`.
- `patches/krkrlive2d.patch` and `patches/live2d.patch` fix what stops the plugin compiling
  with GCC and Clang, and the plugin's file reader throwing for a file the driver only looks
  for, which kept every model without a `.vmotion3.json` from loading (`UPSTREAM.md`). They're
  kept byte for byte (CRLF where the sources have it).
- `driver/CMakeLists.txt` is the driver's build on Linux and macOS, which its own CMake doesn't
  have: the Cubism Native Framework's OpenGL ES 2 renderer through GLAD, the Core's static
  library from the SDK, minizip-ng and KTX (read only). On Windows, Android and iOS it hands
  over to the driver's own.

CI (`.github/workflows/live2d.yml`) builds it on Windows, Linux and macOS with the SDK from the
private repository krkren/cubism-sdk (the `CUBISM_SDK_TOKEN` secret) and runs the smoke test
with Live2D required; only logs leave the runner.

The plugin holds the Cubism Core, which Live2D's licence lets a game ship inside the game, not
in anything handed to other developers: put it in your game's packages only, with terms for
your players that protect it as the licence says. A business with yearly sales of 10 million
yen or more also needs Live2D's release licence, and an "Expandable Application" (one that can
show any number of models) needs Live2D's approval (`doc/world.txt`).
