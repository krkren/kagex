# Upstream issues

kagex never changes krkrz_dev, its submodules or its plugins (`CLAUDE.md`). This file lists the problems in them, and in Wamsoft's platform kits, that kagex can't work around: each one costs a feature or a platform until it's fixed upstream. They're sorted by importance, most important first. Bugs the scripts or the CI work around aren't listed here; `CLAUDE.md` describes them next to their workarounds.

These were found against engine 2.6.5 (krkrz_dev `21d20e9` of 2026-10-20, krkrz-core `7d91ba5`), the plugins it pins (krkr_richtext `52bbb5c`, krkreffekseer `f8197fa` with Effekseer `b6035eb`, extNagano `4b403e2`), and the kits `platforms.yml` pins (krkrz_android `eff2b17`, krkrz_ios `003abad`). When one is fixed upstream, use the fix and delete the entry.

## 1. iOS can't build krkr_richtext or krkreffekseer

- **Where:** the plugins' CMake projects under CMake's Xcode generator (CMake 4.4, Xcode 16.4), which stops with "duplicate object ids not allowed". A bisect of the iOS build's plugin list pinned it to krkr_richtext, and krkreffekseer fails the same way.
- **What it costs:** the iOS build has neither plugin. Text is drawn with the engine's `drawText` (no kerning, no vector edges or shadows), and Effekseer effects show nothing (the console says why).
- **Fix:** not found yet. The error usually means a source file or object library is added to a target twice, or that two targets share an object library in a way the Xcode generator can't represent.

## 2. krkr_richtext doesn't compile for the web (wasm32)

- **Where:** krkr_richtext's `src/main.cpp` casts a `tTJSVariant` to `tjs_intptr_t` to get a layer's image buffer (`static_cast<tjs_intptr_t>(val)` at lines 448, 636 and 1574). tp_stub's `tTJSVariant` only has `operator tjs_intptr_t` on Apple (`#ifdef __APPLE__` in `tjsVariant.h`) or where `intptr_t` is `int64_t`. On wasm32 it's 32 bits, so no conversion exists.
- **What it costs:** the web build has no krkr_richtext, so its text is drawn with `drawText`, as on iOS.
- **Fix:** convert through `tjs_int64` (`(tjs_intptr_t)(tjs_int64)v`), or give tp_stub's `tTJSVariant` the `tjs_intptr_t` conversion on every platform.

## 3. Effects can only add light

- **Where:** two places together. Effekseer blends alpha with `GL_MAX`, so the alpha in a `GLCompositor.capture` of an effect is no coverage mask, and with `premultipliedAlpha` additive nodes leave it at 0. And the engine's `ltAddAlpha`/`omAddAlpha` blend leaves a source pixel whose alpha is 0 alone, instead of adding its colour, so even correctly premultiplied output can't add light where it's transparent.
- **What it costs:** layers that show an effect have to be drawn `ltAdditive` (`GFX_Effekseer.tjs`). Additive effects look as they do in Effekseer's editor, but normally blended nodes can't darken what's behind them: smoke, shadows and dark particles don't work. The same engine behaviour limits any premultiplied image with glows.
- **Fix:** a capture that writes coverage (a separate alpha blend: `glBlendFuncSeparate` with `ONE, ONE_MINUS_SRC_ALPHA` for alpha), together with `ltAddAlpha` adding the colour whatever the alpha, as premultiplied blending does (or a new layer type that does).

## 4. Every frame of every effect is read back from the GPU

- **Where:** `GLCompositor.capture` renders into an offscreen buffer and copies it into a layer's main memory, and each `EffekseerFlip` captures its whole canvas about every 15 ms.
- **What it costs:** the cost grows with the canvas size and the number of effects on screen, which matters most on phones and in the browser. The sample keeps its canvases small (`efkwidth`/`efkheight`).
- **Fix:** let a layer show a GL texture without copying it back (composited by the GL draw device), or render effects directly in the draw device.

## 5. Android can't link the engine with accessibility

- **Where:** with `KRKRZ_USE_A11Y` (the `a11y` plugin), the engine's AccessKit setup can't find its Android library: `find_library` runs inside the NDK's find root. `libkrkrz.so` then doesn't link.
- **What it costs:** the Android build has no screen reader support, which `TODO.md` plans for the other platforms.
- **Fix:** find AccessKit's Android library outside the NDK's find root (an imported target or an explicit path).

## 6. Errors in compiled scripts have no line numbers

- **Where:** `Scripts.compileStorage` with its debug information on (`outputdebug`) writes each function's source positions in `tTJSInterCodeContext::ExportByteCode` (`tjsInterCodeGen.cpp`) with the table's size in bytes (`SourcePosArraySize * 8`) as the count, and then that many entries of each of its two arrays, reading past the end of `SourcePosArray`. An engine that runs such bytecode dumped core as soon as it reported an exception, while it printed the disassembly of the failing function.
- **What it costs:** kagex-release compiles without debug information, so an error in a compiled script names the script and the function at line 1 (`MainWindow.tjs(1)[(function) onKeyDown]`), and players' error reports lose the line.
- **Fix:** write `SourcePosArraySize` as the count, and check that an exception report works for bytecode, which has no source text to show.

## 7. Bytecode compiled on Linux and macOS cuts integer constants to 32 bits

- **Where:** `tjsConstArrayData::GetType` (`tjsConstArrayData.cpp`) puts an integer constant into the 32-bit table when `val >= LONG_MIN && val <= LONG_MAX`. `long` is 32 bits on Windows but 64 on Linux and macOS, so there every constant goes into the 32-bit table, cut (`PutInteger(static_cast<tjs_int32>(...))`): `0xff000000` loads as -16777216, `4294967296` as 0. The loader reads the 64-bit table correctly. `tTJSBinarySerializer::PutInteger` (`tjsBinarySerializer.h`) has the same test for negative numbers.
- **What it costs:** kagex-release compiles each script with such literals a second time to put them right (`tools/release/src/Scripts.h`), but it can't follow a constant the compiler works out from others (`0xff << 24`, a number in `@"${...}"`), so on Linux and macOS a script with one stays source.
- **Fix:** test against `tjs_int32`'s range (`INT32_MIN`, `INT32_MAX`) in both.

## 8. Effects need the GL draw device

- **Where:** `GLCompositor`'s `GLGetProcAddress` (`common/visual/opengl/GLCompositorIntf.cpp`) is 0 on the GPU draw device.
- **What it costs:** krkreffekseer can't draw with the GPU draw device; every effect ends at once there and the console says why.
- **Fix:** expose the GPU device's GL function lookup to `GLCompositor`, or document that it needs the GL draw device.

## 9. rgbfade can't change a whole scene

- **Where:** extNagano's `rgbfade.cpp` (`Process`): where either picture's alpha is 0, it takes a branch meant for transparent pixels that multiplies the colours (`(s1b * opaB) & 0xff`), and it ignores the layer type `StartTransition` is given. The picture the engine composites for a transition with children (a layer with what's on it) has no meaningful alpha: in the World's scenes rgbfade took the transparent branch all over the screen.
- **What it costs:** on a whole scene (any World transition, or KAG's base layer with characters on it) rgbfade shows solid black, green and blue. It only works between two whole pictures on one layer with `children=false`, which is how the sample's `transition.ks` shows it.
- **Fix:** blend the channels as usual for an opaque layer type (`ltOpaque`), and blend rather than multiply the colours in the transparent-pixel branches.

## 10. Plugins KAGEX uses that krkrz_dev doesn't build

Script features that need these log the missing plugin and carry on without the feature.

- `gfxEffect`: the fire effect (`GFX_Fire.tjs`).
- `windowEx`: the extended window events, hiding the menu bar, and the window-control menu icons (`MenuItem.bi*`). `MainWindow.tjs` and `Menus.tjs` skip those paths.
- `flashPlayer`: Flash movies (`GFX_Flash.tjs`). Flash itself is long gone, so this matters only to old games being ported.

## 11. A Yes/No prompt during an overlay movie can open under the movie

- **Where:** the SDL engine's `Window.setMaskRegion` throws "not implemented", so `YesNoFrameDialogWindow`, the shaped window KAG shows over a playing movie, can't be used.
- **What it costs:** on the SDL engine every prompt is a layer of the game window (`YesNoDialogLayer`), which an overlay movie can cover.
- **Fix:** implement `setMaskRegion` (SDL3 has shaped windows: `SDL_SetWindowShape`).

## 12. Full screen in the browser waits for the next tap

- **Where:** the browser build requests full screen from its own main loop rather than from a user event, and browsers only allow it during one.
- **What it costs:** on Android and iPad, choosing full screen in the Config screen takes effect only on the next tap.
- **Fix:** make the request from the input event that triggers it, or queue it to the next pointer event in JavaScript.

## 13. Tests can't hold a key down

- **Where:** keys injected through `Agent` or the REPL don't change `System.getKeyState`.
- **What it costs:** the smoke tests press and release keys over two frames, but can't test anything that needs a key held: skipping while Ctrl or the controller's R2 is held.
- **Fix:** have the injected key events update the key state that `getKeyState` reads.

## 14. Bytecode indexes are 16 bits

- **Where:** `ExportByteCode` writes each function's code words and each constant's table index as 16-bit numbers (`Add2ByteToVector`, `(tjs_int16)constarray.PutVariant(...)`), and `tTJSByteCodeLoader` reads them back signed.
- **What it costs:** a script with a function of more than 32767 code words, or with more than 32767 different strings or numbers, would load wrong, so kagex-release leaves one as source. KAGEX's largest, `MainWindow.tjs`, has 2259 strings and at most 3469 code words in a function.
- **Fix:** 32-bit code words and indexes, in a new version of the bytecode format.
