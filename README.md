# kagex

An English translation of KAGEX, Wamsoft's extension of the Kirikiri KAG3 visual novel framework (affine layers, layer ordering, automatic actions and the "World" environment system), ported to the SDL3 version of [Kirikiri Z](https://github.com/wamsoft/krkrz_dev) and updated to 1920x1080.

## Branches

- **`main`**: the SDL3 version. It's more modern and in active development, supports multiple operating systems (Windows and Linux) and modern codecs, but has a less mature ecosystem.
- **`legacy`**: the Windows-only version. It has more resources, but supports Windows only and doesn't support modern codecs. For reference, the best video codec it supports out of the box is WMV3, which came out in 2003.

## Running the sample

Download a package from [Releases](https://github.com/krkren/kagex/releases), unzip it, and run:

- **Windows:** `krkrz.exe`. The engine needs OpenGL ES: a graphics driver that supports it, or ANGLE's `libEGL.dll` and `libGLESv2.dll` next to `krkrz.exe`.
- **Linux:** `./krkrz`. Saves go to `~/.local/share/wamsoft/krkrz/` unless you pass `-datapath=savedata/`. Japanese text needs Noto Sans CJK JP (`noto-fonts-cjk` on Arch, `fonts-noto-cjk` on Debian and Ubuntu); English text works without it.

The game starts full screen the first time; after that it remembers whether you left it in a window (F5 switches). The `_release` and `_debug` packages hold the same game files with a release or a debug build of the engine.

## Layout

- `data/`: the sample game. It loads the framework from `../template/system`.
- `template/`: the KAGEX framework (`template/system`) and empty folders for a new game, with `template/main/` holding empty versions of the game-side hooks (`Override.tjs`, `AfterInit.tjs`, `Storages.tjs`). To ship a game, copy `template/system` and `template/startup.tjs` into `data/`. On Linux, give your game its own `dataName` in `Config.tjs`: every game on the stock engine saves to the same `~/.local/share/wamsoft/krkrz/` folder.
- `doc/`: the KAGEX reference: `kagex.txt` (new and changed tags), `action.txt` (actions), `world*.txt` (the World extension).

The engine isn't part of this repository. It's built from [wamsoft/krkrz_dev](https://github.com/wamsoft/krkrz_dev); `CLAUDE.md` has the build steps and the outputs to copy next to `data/`.

## Not available on the SDL3 build

These KAGEX features depend on Windows plugins the SDL3 engine doesn't include. The scripts load without them; using one either falls back to something simpler or stops with an error:

- The menu bar (`menu.dll`, `windowEx.dll`). The sample puts its player commands on keys (F1-F8) and buttons instead.
- Scene playback with `[scenestart]` (`psbfile.dll`).
- The fire, Flash and alpha-movie effects (`gfxEffect.dll`, `flashPlayer.dll`, `AlphaMovie.dll`).
- GDI+ outlined text (`layerExDraw.dll`); krkr_richtext draws outlines and shadows instead.
- Native Windows dialogs (`win32dialog.dll`), used by the stand-picture viewer tool.

## License

KAGEX is licensed under the same terms as Kirikiri 2 and KAG3 (`doc/license.txt`). The release packages include the engine's `license.txt` and the licenses of the libraries it uses in `licenses/`.
