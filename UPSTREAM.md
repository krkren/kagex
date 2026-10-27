# Upstream issues

kagex never changes krkrz_dev, its submodules or its plugins (`CLAUDE.md`). This file lists the problems in them, and in Wamsoft's platform kits, that kagex can't work around: each one costs a feature or a platform until it's fixed upstream. They're sorted by importance, most important first. Bugs the scripts or the CI work around aren't listed here; `CLAUDE.md` describes them next to their workarounds.

These were found against engine 2.6.5 (krkrz_dev `21d20e9` of 2026-10-20, krkrz-core `7d91ba5`), the plugins it pins (krkr_richtext `52bbb5c`, krkreffekseer `f8197fa` with Effekseer `b6035eb`, extNagano `4b403e2`), and the kits `platforms.yml` pins (krkrz_android `eff2b17`, krkrz_ios `003abad`). When one is fixed upstream, use the fix and delete the entry.

## 1. The REPL handles TJS values on its own thread

- **Where:** `tTVPReplFileChannel::Execute` (`common/utils/ReplFileChannel.cpp`) runs a command on the main thread through `TVPReplMainQueue::Submit`, then pretty-prints the result (`TVPPrettyPrint`) and releases it on the channel's own thread; the console REPL does the same (`REPL.cpp`). TJS strings and objects have reference counts that aren't atomic (`tTJSVariantString::RefCount`), and the main thread keeps copies of a returned value in its VM registers after the call (`tTJSVariantArrayStack::Deallocate` doesn't clear them), so both threads change the same counts.
- **What it costs:** an engine driven through the REPL aborts now and then: "double free or corruption", "free(): corrupted unsorted chunks", Windows' 0xC0000374. The busier the main thread, the likelier: about one run in five of the release smoke test on GitHub's runners, mostly during the Animated Character demo, and never on a 2-CPU development machine. Under gdb the aborts were in `tTJSVariantString::Release` (on the main thread or the channel's) and in `TVPPrettyPrint` on the channel's thread. kagex's desktop tests (`run-kagex.ps1`, `smoketest.py`'s file channel) make every command return 0 and have the main thread write the value to a file; the Android, iOS and web tests still read their channels' results.
- **Fix:** pretty-print the result on the main thread, inside the queued task, and hand the channel's thread only a `std::string`.

## 2. In the Linux kit build an exception that crosses a plugin aborts the game

- **Where:** krkrz_linux's engine and plugins each carry a static copy of libgcc's unwinder (in the backtrace below `_Unwind_RaiseException_Phase2` is the engine's and `_Unwind_SetGR` the plugin's). A C++ exception the engine throws that unwinds through a plugin's frame runs the plugin's personality routine, which calls its own copy's `_Unwind_SetGR`, whose register table only that copy's unwinder fills in: it's empty, and `_Unwind_SetGR` aborts. Seen in the json plugin's `V2Unlink`, which looks up `Scripts` (`TVPExecuteExpression`) inside `TVPDoTryBlock` when the engine unlinks its plugins on the way out (`TVPSystemUninit`, `TVPDestroyPluginVector`): by then the lookup throws, and the engine would catch it, but the unwinding never gets there (gdb: `abort` ← `_Unwind_SetGR.cold` ← `__gxx_personality_v0` in `libjson.so` ← `_Unwind_RaiseException_Phase2` in `krkrz`). The zip packages and macOS catch it, as they should.
- **What it costs:** every exit of the kit's Linux build (the Steam package) dumped core while the json plugin was linked: `-scncompile`, `System.exit`, and a player closing the game. kagex unlinks the json plugin while `Scripts` is still there (`KAGUnlinkPluginsBeforeExit` in `Initialize.tjs`, before the framework's exits and from `KAGWindow.finalize`), and `smoketest.py` checks that the game quits with exit code 0. Any other exception that unwinds through a plugin's frame (a script error in a callback a plugin makes into TJS) can still abort the kit build where the other builds show the error.
- **Fix:** link the engine and the plugins against one shared libgcc_s (and libstdc++), as the Steam Linux Runtime provides, or catch exceptions at every plugin boundary (tp_stub's entry points and ncbind's thunks) so none unwinds through another copy's frames; and in the json plugin, don't look up `Scripts` in `V2Unlink` once the engine is shutting down.

## 3. The web build's prefetch makes cache entries before it writes them

- **Where:** krkrz_web's `pre.js` prefetch (`runPrefetch` in `krkrz.js`) creates each OPFS entry with `getFileHandle(key, {create: true})`, an empty file, and only then writes and closes it; the engine's `krkrz_web_fetch` (`HttpStorageMedia.cpp`) opens any entry it finds and takes its contents as the file, with no size or completeness check. And `TVPExecuteStorage` (`ScriptMgnIntf.cpp`) opens a script twice: as bytecode (`LoadByteCode`, which reads the 8-byte tag without checking how much it got) and, when that isn't bytecode, again as text.
- **What it costs:** a file the engine read while the prefetch was writing it came back empty. A compiled script then read empty as bytecode and whole as text: `Syntax error at line 1`, and the error dialog stopped the page (`RuntimeError: unreachable`). Three of five runs of kagex-release's web (files) test on the Linux runner; any web build with a prefetch list could also get an empty image or script. `kagex-web.js` makes a lookup of an entry being written wait for the write (and removes an entry a failed write left).
- **Fix:** write each prefetched file under a temporary name and move it into place (or create it only once its data is ready), and treat an empty entry as a miss; open a script once and look at its first bytes.

## 4. iOS can't build krkr_richtext or krkreffekseer

- **Where:** the plugins' CMake projects under CMake's Xcode generator (CMake 4.4, Xcode 16.4), which stops with "duplicate object ids not allowed". A bisect of the iOS build's plugin list pinned it to krkr_richtext, and krkreffekseer fails the same way.
- **What it costs:** the iOS build has neither plugin. Text is drawn with the engine's `drawText` (no kerning, no vector edges or shadows), and Effekseer effects show nothing (the console says why).
- **Fix:** not found yet. The error usually means a source file or object library is added to a target twice, or that two targets share an object library in a way the Xcode generator can't represent.

## 5. krkr_richtext doesn't compile for the web (wasm32)

- **Where:** krkr_richtext's `src/main.cpp` casts a `tTJSVariant` to `tjs_intptr_t` to get a layer's image buffer (`static_cast<tjs_intptr_t>(val)` at lines 448, 636 and 1574). tp_stub's `tTJSVariant` only has `operator tjs_intptr_t` on Apple (`#ifdef __APPLE__` in `tjsVariant.h`) or where `intptr_t` is `int64_t`. On wasm32 it's 32 bits, so no conversion exists.
- **What it costs:** the web build has no krkr_richtext, so its text is drawn with `drawText`, as on iOS.
- **Fix:** convert through `tjs_int64` (`(tjs_intptr_t)(tjs_int64)v`), or give tp_stub's `tTJSVariant` the `tjs_intptr_t` conversion on every platform.

## 6. Effects can only add light

- **Where:** two places together. Effekseer blends alpha with `GL_MAX`, so the alpha in a `GLCompositor.capture` of an effect is no coverage mask, and with `premultipliedAlpha` additive nodes leave it at 0. And the engine's `ltAddAlpha`/`omAddAlpha` blend leaves a source pixel whose alpha is 0 alone, instead of adding its colour, so even correctly premultiplied output can't add light where it's transparent.
- **What it costs:** layers that show an effect have to be drawn `ltAdditive` (`GFX_Effekseer.tjs`). Additive effects look as they do in Effekseer's editor, but normally blended nodes can't darken what's behind them: smoke, shadows and dark particles don't work. The same engine behaviour limits any premultiplied image with glows.
- **Fix:** a capture that writes coverage (a separate alpha blend: `glBlendFuncSeparate` with `ONE, ONE_MINUS_SRC_ALPHA` for alpha), together with `ltAddAlpha` adding the colour whatever the alpha, as premultiplied blending does (or a new layer type that does).

## 7. Every frame of every effect is read back from the GPU

- **Where:** `GLCompositor.capture` renders into an offscreen buffer and copies it into a layer's main memory, and each `EffekseerFlip` captures its whole canvas about every 15 ms.
- **What it costs:** the cost grows with the canvas size and the number of effects on screen, which matters most on phones and in the browser. The sample keeps its canvases small (`efkwidth`/`efkheight`).
- **Fix:** let a layer show a GL texture without copying it back (composited by the GL draw device), or render effects directly in the draw device.

## 8. Android can't link the engine with accessibility

- **Where:** with `KRKRZ_USE_A11Y` (the `a11y` plugin), the engine's AccessKit setup can't find its Android library: `find_library` runs inside the NDK's find root. `libkrkrz.so` then doesn't link.
- **What it costs:** the Android build has no screen reader support, which `TODO.md` plans for the other platforms.
- **Fix:** find AccessKit's Android library outside the NDK's find root (an imported target or an explicit path).

## 9. Errors in compiled scripts have no line numbers

- **Where:** `Scripts.compileStorage` with its debug information on (`outputdebug`) writes each function's source positions in `tTJSInterCodeContext::ExportByteCode` (`tjsInterCodeGen.cpp`) with the table's size in bytes (`SourcePosArraySize * 8`) as the count, and then that many entries of each of its two arrays, reading past the end of `SourcePosArray`. An engine that runs such bytecode dumped core as soon as it reported an exception, while it printed the disassembly of the failing function.
- **What it costs:** kagex-release compiles without debug information, so an error in a compiled script names the script and the function at line 1 (`MainWindow.tjs(1)[(function) onKeyDown]`), and players' error reports lose the line.
- **Fix:** write `SourcePosArraySize` as the count, and check that an exception report works for bytecode, which has no source text to show.

## 10. Bytecode compiled on Linux and macOS cuts integer constants to 32 bits

- **Where:** `tjsConstArrayData::GetType` (`tjsConstArrayData.cpp`) puts an integer constant into the 32-bit table when `val >= LONG_MIN && val <= LONG_MAX`. `long` is 32 bits on Windows but 64 on Linux and macOS, so there every constant goes into the 32-bit table, cut (`PutInteger(static_cast<tjs_int32>(...))`): `0xff000000` loads as -16777216, `4294967296` as 0. The loader reads the 64-bit table correctly. `tTJSBinarySerializer::PutInteger` (`tjsBinarySerializer.h`) has the same test for negative numbers.
- **What it costs:** kagex-release compiles each script with such literals a second time to put them right (`tools/release/src/Scripts.h`), but it can't follow a constant the compiler works out from others (`0xff << 24`, a number in `@"${...}"`), so on Linux and macOS a script with one stays source.
- **Fix:** test against `tjs_int32`'s range (`INT32_MIN`, `INT32_MAX`) in both.

## 11. Effects need the GL draw device

- **Where:** `GLCompositor`'s `GLGetProcAddress` (`common/visual/opengl/GLCompositorIntf.cpp`) is 0 on the GPU draw device.
- **What it costs:** krkreffekseer can't draw with the GPU draw device; every effect ends at once there and the console says why.
- **Fix:** expose the GPU device's GL function lookup to `GLCompositor`, or document that it needs the GL draw device.

## 12. rgbfade can't change a whole scene

- **Where:** extNagano's `rgbfade.cpp` (`Process`): where either picture's alpha is 0, it takes a branch meant for transparent pixels that multiplies the colours (`(s1b * opaB) & 0xff`), and it ignores the layer type `StartTransition` is given. The picture the engine composites for a transition with children (a layer with what's on it) has no meaningful alpha: in the World's scenes rgbfade took the transparent branch all over the screen.
- **What it costs:** on a whole scene (any World transition, or KAG's base layer with characters on it) rgbfade shows solid black, green and blue. It only works between two whole pictures on one layer with `children=false`, which is how the sample's `transition.ks` shows it.
- **Fix:** blend the channels as usual for an opaque layer type (`ltOpaque`), and blend rather than multiply the colours in the transparent-pixel branches.

## 13. Plugins KAGEX uses that krkrz_dev doesn't build

Script features that need these log the missing plugin and carry on without the feature.

- `gfxEffect`: the fire effect (`GFX_Fire.tjs`).
- `windowEx`: the extended window events, hiding the menu bar, and the window-control menu icons (`MenuItem.bi*`). `MainWindow.tjs` and `Menus.tjs` skip those paths.
- `flashPlayer`: Flash movies (`GFX_Flash.tjs`). Flash itself is long gone, so this matters only to old games being ported.

## 14. A Yes/No prompt during an overlay movie can open under the movie

- **Where:** the SDL engine's `Window.setMaskRegion` throws "not implemented", so `YesNoFrameDialogWindow`, the shaped window KAG shows over a playing movie, can't be used.
- **What it costs:** on the SDL engine every prompt is a layer of the game window (`YesNoDialogLayer`), which an overlay movie can cover.
- **Fix:** implement `setMaskRegion` (SDL3 has shaped windows: `SDL_SetWindowShape`).

## 15. Full screen in the browser waits for the next tap

- **Where:** the browser build requests full screen from its own main loop rather than from a user event, and browsers only allow it during one.
- **What it costs:** on Android and iPad, choosing full screen in the Config screen takes effect only on the next tap.
- **Fix:** make the request from the input event that triggers it, or queue it to the next pointer event in JavaScript.

## 16. Tests can't hold a key down

- **Where:** keys injected through `Agent` or the REPL don't change `System.getKeyState`.
- **What it costs:** the smoke tests press and release keys over two frames, but can't test anything that needs a key held: skipping while Ctrl or the controller's R2 is held.
- **Fix:** have the injected key events update the key state that `getKeyState` reads.

## 17. The sigcheck plugin keeps file sizes and offsets in 32-bit ints

- **Where:** `src/plugins/sigcheck/main.cpp` (`SigChecker::CheckSignatureOfFile` and `CheckKrkrExecutable`) holds the file size, the running byte count and the mark offsets in `int`/`tjs_uint32`. krkrz_tools' `krt::sig` (the signing side) uses 64-bit offsets, so it signs any size correctly; only the engine-side verifier is 32-bit.
- **What it costs:** signatures (`sigcheck`, used by `template/system/SignatureCheck.tjs`) can only be checked on files below 2 GB. From 2 GB the progress byte count overflows (odd or missing progress events, but the hash still verifies); past 4 GB the size is truncated to 32 bits (thousands of spurious progress events); and at an exact multiple of 4 GiB the size reads as 0 and the per-cent calculation divides by it. kagex-release works around it by keeping every signed archive under 2 GB — splitting a large game's media into separate archives (`Build.cpp`, `splitIfNeeded`) — and refusing a single folder of 2 GB or more. Confirmed on the 0.8.0 Linux engine: a 1 GB file verifies in ~12 s; 2.3 GB and 4.1 GB verify but with the byte-count problems above.
- **Fix:** use `tjs_int64` for the size, the running offset and the mark offsets in the plugin, matching `krt::sig`.

## 18. The sigcheck plugin reads each file several times per check

- **Where:** `SigChecker::CheckSignature` calls `CheckKrkrExecutable` three times (searching for the `XOPT_EMBED_AREA_`, `XRELEASE_SIG____` and XP3 marks), each a full scan from the start of the file, before `CheckSignatureOfFile` reads the whole file once more to hash it.
- **What it costs:** start-up of a signed build (`SignatureCheck.tjs`) reads the game archive and every engine file about four times over. For a large archive that is seconds of disk I/O before the game appears; splitting (above) spreads it across several files but doesn't reduce the total. The mark search also has no business running on a plain data file (only an executable carries the marks), but the plugin runs it on everything.
- **Fix:** scan for all three marks in one pass, skip the executable-mark search for a file that isn't an executable, and reuse that read for the hash.

## 19. Bytecode indexes are 16 bits

- **Where:** `ExportByteCode` writes each function's code words and each constant's table index as 16-bit numbers (`Add2ByteToVector`, `(tjs_int16)constarray.PutVariant(...)`), and `tTJSByteCodeLoader` reads them back signed.
- **What it costs:** a script with a function of more than 32767 code words, or with more than 32767 different strings or numbers, would load wrong, so kagex-release leaves one as source. KAGEX's largest, `MainWindow.tjs`, has 2259 strings and at most 3469 code words in a function.
- **Fix:** 32-bit code words and indexes, in a new version of the bytecode format.

## 20. getVowel reads a high voice as o

- **Where:** `tTJSNI_QueueSoundBuffer::GetVowel` (`common/sound/QueueSoundBufferImpl.cpp`) scores each vowel by the energy of a 1024-point FFT within ±15% + 50 Hz of fixed first and second formants (a 800/1200, i 300/2300, u 350/1200, e 500/1900, o 500/900 Hz, a man's Japanese vowels) and divides by the total. A voice's energy is at its harmonics, its pitch apart, most of it in the lowest few, so above about 300 Hz the fundamental and the second harmonic land in o's (and u's) bands whatever the vowel, and the formants, between harmonics, barely count; e almost never wins.
- **What it costs:** mouths by vowel (`KAGEnvCharacterEx.tjs`, `lipSyncVowels`) follow low, clear voices, but a high voice (most female and child voices in games) mostly shows the O mouth. Pip's babble at 440 Hz read as the vowel it said 26% of the time, nearly always as o; the sample now voices Pip breathily at the engine's own formants, which it reads right 87% of the time (`tools/assets/make_pip.py vowels`). A game can turn mouths by vowel off (`lipSyncVowels = false`).
- **Fix:** estimate the formants from the spectral envelope rather than the raw spectrum (cepstral smoothing or LPC), and place them relative to the voice's own range (or scale the table with its pitch), with wider bands.
