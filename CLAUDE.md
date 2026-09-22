# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

`kagex` (origin: https://github.com/krkren/kagex) is an English-translated, SDL3/Linux-ported fork of **KAGEX** — Wamsoft's extension of the Kirikiri **KAG3** visual-novel framework (affine layers, layer level ordering, automatic actions, and the "World" environment system). It is pure script and asset content: TJS2 (`.tjs`), KAG scenario (`.ks`), CSV, and images/audio. There is **no build step, no test suite, and no linter** here.

The engine that runs it is not part of this repo. `krkrz.exe`, `SDL3.dll`, `plugin/`, and `savedata/` are all gitignored local artifacts, built from the sibling `../krkrz_dev` umbrella repo (the SDL3 variant of 吉里吉里Z; see `../krkrz_dev/CLAUDE.md`), with `extrans.dll` coming from https://github.com/krkren/SamplePlugin. `KAGEX Initial Setup.txt` still mentions a `setup.bat`; that script (and `setup.sh`) was removed in commit `f6d1767` — `git show f6d1767^:setup.bat` is the reference for which build outputs get copied where (`krkrz64.exe` → `krkrz.exe`, `core/plugins/*/*.dll` + `krmovie.dll` → `plugin/`).

## Running

```bash
./krkrz.exe            # from the repo root; project dir defaults to data/
```

- The engine treats the first positional argument as the project directory, and looks for `startup.tjs` in it. With no argument it uses `data/` next to the exe. Engine options are `-name=value`; a bare word gets taken as the project path (a past run with a stray `usepseudo` token failed with "Cannot find storage startup.tjs").
- The only feedback loop is running the game and reading **`savedata/krkr.console.log`**. It is **UTF-16LE** and appended across runs — read it with `iconv -f UTF-16LE -t UTF-8 savedata/krkr.console.log | tail -n 200`, and look for `Script exception raised` / `An exception occured at <file>(<line>)`. Filenames in traces are lowercased.
- `savedata/*.ksd` persists system/scenario variables (`sf.*`, `scflags`) between runs, including things like the saved full-screen preference. When a config change appears to have no effect, stale savedata is a likely cause.

## Layout and load order

- `template/` — the reusable KAGEX framework. `template/system/*.tjs` is the whole runtime (~60 files); the other `template/*` folders are empty placeholders for a new game.
- `data/` — the sample game. `data/startup.tjs` does **not** have its own `system/`; it adds `../template/system/` to the auto path and executes `../template/system/Initialize.tjs`. Shipping a real game means copying `template/system` + `template/startup.tjs` into `data/`.
- `doc/` — the KAGEX reference, in English: `kagex.txt` (new/changed tags vs. stock KAG3), `action.txt` (action system), `world.txt` / `world_inst.txt` / `world_use.txt` (World extension: `envinit.tjs` schema, character/stage/time tags). Read these before changing tag behavior; stock KAG3 knowledge alone is not enough.

`template/system/Initialize.tjs` drives everything, in this order:

1. Registers auto paths: `data/` then a fixed list of subfolders (`video, others, rule, sound, bgm, fgimage, bgimage, scenario, image, system, voice, face, init, sysscn, main, evimage, thum, uipsd`), each also accepted as a `<name>.xp3` archive. **Later-registered paths win**, so anything under `data/*` shadows the same filename in `template/system/`. Storage lookup is by bare filename across all auto paths — filenames must be globally unique unless shadowing is intended.
2. Runs `Storages.tjs` (`data/main/Storages.tjs`) — add nested asset folders there via `setupSubFolders([...])`; a new top-level folder outside the fixed list is not searched.
3. Links plugins (see below), then loads `AppConfig.tjs` (optional) and `Config.tjs`.
4. Loads the system classes, then `Override.tjs`, creates the `kag` window, attaches `KAGWorldPlugin` (`world.tjs` + `KAGEnv*.tjs`, configured by `envinit.tjs`), runs `AfterInit.tjs`, and finally `kag.process("first.ks")`.

In the sample, the game-side hooks all live in `data/main/`: `Config.tjs`, `Override.tjs` (class/function overrides, loads `MyHistoryLayer.tjs` / `MyYesNoDialog.tjs`), `AfterInit.tjs` (key bindings etc.), `envinit.tjs` (World definitions: times, stages, characters, poses), `first.ks` → `logo.ks` → `title.ks`, the system-menu scenarios (`config.ks`, `save.ks`, `load.ks`, `cgmode.ks`, `musicmode.ks`, `replay.ks`) and their CSV lists. Story/demo scripts are in `data/scenario/` (`s0001.ks` is the demo menu). Prefer these hooks over editing `template/system/` when a change is game-specific.

## Conventions and gotchas

- **Two `Config.tjs` files.** `data/main/Config.tjs` is the one in effect (it shadows `template/system/Config.tjs`). Recent commits keep both in sync for settings like `scWidth`/`scHeight` (currently 1920x1080); do the same. Setting lines use the `;name = value;` form, and the `//[start-...-additionals]` / `//[end-...]` markers must stay — `UpdateConfig.tjs` parses both when migrating configs. The `KAGWindow_config` etc. functions run `incontextof` the target object, so settings like `scWidth` become **members of `kag`**, not globals.
- **Plugin linking.** Plugins are linked by explicit relative path with a `.dll` name on every platform — `Plugins.link("plugin/foo.dll")` — wrapped in `try {} catch {}` and, where possible, guarded by a `typeof` check on a symbol the plugin provides (avoids double-loading on case-sensitive Linux, and tolerates plugins the SDL3 build provides natively or lacks). Follow this pattern; bare `Plugins.link("foo.dll")` was deliberately removed in `0710553`.
- **Linux compatibility.** Storage names in scripts must match file case exactly, and use `/` separators. `template/update_auto_copy_vars.bat` is a legacy Windows/perl helper; ignore it.
- **SDL3 port patches.** The end of `Initialize.tjs` forces the window inner size from `kag.scWidth/scHeight` unless full-screen, and `data/main/Config.tjs` shadows `getInitialFullScreenState` to always start full-screen. Be careful reordering anything around window creation and `kag.process("first.ks")`.
- **File encoding.** Most scripts are UTF-8 **with BOM**, but not all (e.g. `template/system/Config.tjs` has none); line endings and a doubled-blank-line artifact (left over from a CRLF conversion) vary by file. Preserve whatever the file already uses and keep diffs minimal — do not normalize whitespace, strip BOMs, or collapse the blank lines as a drive-by. `◆`/`●` markers and some Japanese comments are intentional.
- UI coordinates in `.ks` files (`title.ks`, `config.ks`, …) and the images in `data/image/` are authored for a specific resolution; a resolution change means touching both. `title.ks`/`title.png` are at 1920x1080; the other menu screens have not been verified at that size.
- Never commit `krkrz.exe`, DLLs/`.so`, `plugin/`, or `savedata/` (all in `.gitignore`).
