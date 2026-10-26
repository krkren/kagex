# Upstream issues

kagex never changes krkrz_dev, its submodules or its plugins (`CLAUDE.md`). This file lists the problems in them, and in Wamsoft's platform kits, that kagex can't work around: each one costs a feature or a platform until it's fixed upstream. They're sorted by importance, most important first. Bugs the scripts or the CI work around aren't listed here; `CLAUDE.md` describes them next to their workarounds.

These were found against engine 2.6.5 (krkrz_dev `21d20e9` of 2026-10-20, krkrz-core `7d91ba5`), the plugins it pins (krkr_richtext `52bbb5c`, krkreffekseer `f8197fa` with Effekseer `b6035eb`, extNagano `4b403e2`), and the kits `platforms.yml` pins (krkrz_android `eff2b17`, krkrz_ios `003abad`). When one is fixed upstream, use the fix and delete the entry.

## 1. The REPL handles TJS values on its own thread

- **Where:** `tTVPReplFileChannel::Execute` (`common/utils/ReplFileChannel.cpp`) runs a command on the main thread through `TVPReplMainQueue::Submit`, then pretty-prints the result (`TVPPrettyPrint`) and releases it on the channel's own thread; the console REPL does the same (`REPL.cpp`). TJS strings and objects have reference counts that aren't atomic (`tTJSVariantString::RefCount`), and the main thread keeps copies of a returned value in its VM registers after the call (`tTJSVariantArrayStack::Deallocate` doesn't clear them), so both threads change the same counts.
- **What it costs:** an engine driven through the REPL aborts now and then: "double free or corruption", "free(): corrupted unsorted chunks", Windows' 0xC0000374. The busier the main thread, the likelier: about one run in five of the release smoke test on GitHub's runners, mostly during the Animated Character demo, and never on a 2-CPU development machine. Under gdb the aborts were in `tTJSVariantString::Release` (on the main thread or the channel's) and in `TVPPrettyPrint` on the channel's thread. kagex's desktop tests (`run-kagex.ps1`, `smoketest.py`'s file channel) make every command return 0 and have the main thread write the value to a file; the Android, iOS and web tests still read their channels' results.
- **Fix:** pretty-print the result on the main thread, inside the queued task, and hand the channel's thread only a `std::string`.

## 2. iOS can't build krkr_richtext or krkreffekseer

- **Where:** the plugins' CMake projects under CMake's Xcode generator (CMake 4.4, Xcode 16.4), which stops with "duplicate object ids not allowed". A bisect of the iOS build's plugin list pinned it to krkr_richtext, and krkreffekseer fails the same way.
- **What it costs:** the iOS build has neither plugin. Text is drawn with the engine's `drawText` (no kerning, no vector edges or shadows), and Effekseer effects show nothing (the console says why).
- **Fix:** not found yet. The error usually means a source file or object library is added to a target twice, or that two targets share an object library in a way the Xcode generator can't represent.

## 3. krkr_richtext doesn't compile for the web (wasm32)

- **Where:** krkr_richtext's `src/main.cpp` casts a `tTJSVariant` to `tjs_intptr_t` to get a layer's image buffer (`static_cast<tjs_intptr_t>(val)` at lines 448, 636 and 1574). tp_stub's `tTJSVariant` only has `operator tjs_intptr_t` on Apple (`#ifdef __APPLE__` in `tjsVariant.h`) or where `intptr_t` is `int64_t`. On wasm32 it's 32 bits, so no conversion exists.
- **What it costs:** the web build has no krkr_richtext, so its text is drawn with `drawText`, as on iOS.
- **Fix:** convert through `tjs_int64` (`(tjs_intptr_t)(tjs_int64)v`), or give tp_stub's `tTJSVariant` the `tjs_intptr_t` conversion on every platform.

## 4. Effects can only add light

- **Where:** two places together. Effekseer blends alpha with `GL_MAX`, so the alpha in a `GLCompositor.capture` of an effect is no coverage mask, and with `premultipliedAlpha` additive nodes leave it at 0. And the engine's `ltAddAlpha`/`omAddAlpha` blend leaves a source pixel whose alpha is 0 alone, instead of adding its colour, so even correctly premultiplied output can't add light where it's transparent.
- **What it costs:** layers that show an effect have to be drawn `ltAdditive` (`GFX_Effekseer.tjs`). Additive effects look as they do in Effekseer's editor, but normally blended nodes can't darken what's behind them: smoke, shadows and dark particles don't work. The same engine behaviour limits any premultiplied image with glows.
- **Fix:** a capture that writes coverage (a separate alpha blend: `glBlendFuncSeparate` with `ONE, ONE_MINUS_SRC_ALPHA` for alpha), together with `ltAddAlpha` adding the colour whatever the alpha, as premultiplied blending does (or a new layer type that does).

## 5. Every frame of every effect is read back from the GPU

- **Where:** `GLCompositor.capture` renders into an offscreen buffer and copies it into a layer's main memory, and each `EffekseerFlip` captures its whole canvas about every 15 ms.
- **What it costs:** the cost grows with the canvas size and the number of effects on screen, which matters most on phones and in the browser. The sample keeps its canvases small (`efkwidth`/`efkheight`).
- **Fix:** let a layer show a GL texture without copying it back (composited by the GL draw device), or render effects directly in the draw device.

## 6. Android can't link the engine with accessibility

- **Where:** with `KRKRZ_USE_A11Y` (the `a11y` plugin), the engine's AccessKit setup can't find its Android library: `find_library` runs inside the NDK's find root. `libkrkrz.so` then doesn't link.
- **What it costs:** the Android build has no screen reader support, which `TODO.md` plans for the other platforms.
- **Fix:** find AccessKit's Android library outside the NDK's find root (an imported target or an explicit path).

## 7. Effects need the GL draw device

- **Where:** `GLCompositor`'s `GLGetProcAddress` (`common/visual/opengl/GLCompositorIntf.cpp`) is 0 on the GPU draw device.
- **What it costs:** krkreffekseer can't draw with the GPU draw device; every effect ends at once there and the console says why.
- **Fix:** expose the GPU device's GL function lookup to `GLCompositor`, or document that it needs the GL draw device.

## 8. rgbfade can't change a whole scene

- **Where:** extNagano's `rgbfade.cpp` (`Process`): where either picture's alpha is 0, it takes a branch meant for transparent pixels that multiplies the colours (`(s1b * opaB) & 0xff`), and it ignores the layer type `StartTransition` is given. The picture the engine composites for a transition with children (a layer with what's on it) has no meaningful alpha: in the World's scenes rgbfade took the transparent branch all over the screen.
- **What it costs:** on a whole scene (any World transition, or KAG's base layer with characters on it) rgbfade shows solid black, green and blue. It only works between two whole pictures on one layer with `children=false`, which is how the sample's `transition.ks` shows it.
- **Fix:** blend the channels as usual for an opaque layer type (`ltOpaque`), and blend rather than multiply the colours in the transparent-pixel branches.

## 9. Plugins KAGEX uses that krkrz_dev doesn't build

Script features that need these log the missing plugin and carry on without the feature.

- `gfxEffect`: the fire effect (`GFX_Fire.tjs`).
- `windowEx`: the extended window events, hiding the menu bar, and the window-control menu icons (`MenuItem.bi*`). `MainWindow.tjs` and `Menus.tjs` skip those paths.
- `flashPlayer`: Flash movies (`GFX_Flash.tjs`). Flash itself is long gone, so this matters only to old games being ported.

## 10. A Yes/No prompt during an overlay movie can open under the movie

- **Where:** the SDL engine's `Window.setMaskRegion` throws "not implemented", so `YesNoFrameDialogWindow`, the shaped window KAG shows over a playing movie, can't be used.
- **What it costs:** on the SDL engine every prompt is a layer of the game window (`YesNoDialogLayer`), which an overlay movie can cover.
- **Fix:** implement `setMaskRegion` (SDL3 has shaped windows: `SDL_SetWindowShape`).

## 11. Full screen in the browser waits for the next tap

- **Where:** the browser build requests full screen from its own main loop rather than from a user event, and browsers only allow it during one.
- **What it costs:** on Android and iPad, choosing full screen in the Config screen takes effect only on the next tap.
- **Fix:** make the request from the input event that triggers it, or queue it to the next pointer event in JavaScript.

## 12. Tests can't hold a key down

- **Where:** keys injected through `Agent` or the REPL don't change `System.getKeyState`.
- **What it costs:** the smoke tests press and release keys over two frames, but can't test anything that needs a key held: skipping while Ctrl or the controller's R2 is held.
- **Fix:** have the injected key events update the key state that `getKeyState` reads.
