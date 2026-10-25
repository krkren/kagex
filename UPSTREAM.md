# Upstream issues

kagex never changes krkrz_dev, its submodules or its plugins (`CLAUDE.md`). This file lists the bugs and gaps in them, and in Wamsoft's platform kits, that kagex has had to work around. Each entry gives the place in the upstream code where it's known, what goes wrong, how kagex works around it, and what would fix it upstream.

These were found against engine 2.6.5 (krkrz_dev `21d20e9` of 2026-10-20, krkrz-core `7d91ba5`), the plugins it pins (krkr_richtext `52bbb5c`, krkreffekseer `f8197fa` with Effekseer `b6035eb`), and the kits `platforms.yml` pins: krkrz_web `2fe4616`, krkrz_android `eff2b17`, krkrz_ios `003abad`, krkrz_linux `0360592`. When upstream fixes one, remove its workaround (and its note in `CLAUDE.md`) and delete the entry here.

**A general fix for Linux plugins.** Two of the plugin bugs below (krkr_richtext's link order, Effekseer's static members) produced a `.so` that linked but couldn't load. ELF shared objects link with undefined symbols by default, so these only show up when the engine loads the plugin. Linking the plugins with `-Wl,--no-undefined` would turn both into build errors. Android's linker already does this, which is why the Effekseer bug failed the Android debug build at link time.

## krkr_richtext

### Linux: the plugin links but won't load (`undefined symbol: png_get_valid`)

- **Where:** the link line CMake generates for the plugin, through `richtext_lib` and minikin (the `richtext` submodule and its own). It lists `libfreetype.a` again after harfbuzz, which puts it after the png, zlib, bzip2 and brotli archives that freetype needs. With static archives, the linker only resolves symbols from archives that come later on the line.
- **What happens:** `libkrkr_richtext.so` builds, but the engine can't load it, so text falls back to `drawText`: no kerning, no vector edges or shadows. The 0.4.0 release build still needs the workaround (`richtext-link.log` on `ci/release-results-linux-release`).
- **Workaround:** the release workflow relinks the plugin with the archives added at the end. `linux-config.json` (krkrz_linux) sets `CMAKE_CXX_STANDARD_LIBRARIES` to the same archives so they end every C++ link. `CLAUDE.md` gives the relink command for local builds.
- **Fix:** link freetype through vcpkg's imported target (`Freetype::Freetype`, which carries its dependencies) everywhere it's linked, so they follow its last appearance, or add those archives after harfbuzz.

### Web: doesn't compile for wasm32

- **Where:** the plugin's `src/main.cpp` casts a `tTJSVariant` to `tjs_intptr_t` to get a layer's image buffer (`static_cast<tjs_intptr_t>(val)` at lines 448, 636 and 1574). tp_stub's `tTJSVariant` only has `operator tjs_intptr_t` on Apple (`#ifdef __APPLE__` in `tjsVariant.h`) or where `intptr_t` is `int64_t`. On wasm32 it's 32 bits, so no conversion exists.
- **What happens:** the web build is made without krkr_richtext and draws text with the engine's `drawText`.
- **Workaround:** none in kagex. Without the plugin, `MessageLayer`, `SelectLayer` and the history layers keep the `drawText` path. `updateLineLayerPadding` measures descenders with `getGlyphDrawRect` instead of krkr_richtext.
- **Fix:** convert through `tjs_int64` (`(tjs_intptr_t)(tjs_int64)v`), or give tp_stub's `tTJSVariant` the `tjs_intptr_t` conversion on every platform.

### iOS: CMake's Xcode generator stops with "duplicate object ids not allowed"

- **Where:** the plugin's CMake project under the Xcode generator (CMake 4.4, Xcode 16.4). A bisect of the iOS build's plugin list pinned it to this plugin. krkreffekseer fails the same way (below).
- **What happens:** the iOS build can't include the plugin, so text there is drawn with `drawText`, as on the web.
- **Workaround:** `ios-config.json` leaves krkr_richtext out.
- **Fix:** not found yet. The error usually means the same source or object library is added to a target twice, or that two targets share an object library in a way the Xcode generator can't represent.

### Draws the first face of a `.ttc` instead of the one asked for

- **Where:** font registration or face selection: the plugin loads face 0 of a font collection, ignoring the index of the named face. Seen on Windows.
- **What happens:** MS PGothic, MS UI Gothic, Yu Gothic UI and MS PMincho come out as MS Gothic, Yu Gothic and MS Mincho, the first face in their collections. MS PGothic is proportional, MS Gothic isn't, so English looked gappy. The engine's own `drawText` gets these faces right.
- **Workaround:** the face lists only name fonts that come first in their collection (`"Yu Gothic Medium,Yu Gothic,Noto Sans JP,Roboto"`).
- **Fix:** open the collection's face by the index the engine's font lookup resolved.

### `drawTextEx` only updates the glyphs' ink box

- **Where:** `drawTextEx` calls `update()` on the glyphs' ink rectangle, not on the area the edge and shadow cover.
- **What happens:** shadows and edges outside the ink box didn't reach the screen until something else repainted there. Text looked clipped while it was typed out, then changed when the line was committed.
- **Workaround:** `RichTextFontApp.drawText` (`template/system/MessageLayer.tjs`) updates the whole padded cell itself.
- **Fix:** update the drawn extent: the ink box grown by the edge extent and the shadow offset and blur.

### `RichText.registerFont` with a face name the engine can't resolve deadlocks the engine

See *Searching for an unknown font name deadlocks the file allocator* under the engine below. krkr_richtext triggers it through `RichText.registerFont`.

## krkreffekseer and Effekseer

### Android and web: `<EGL/egl.h>` clashes with the plugin's GL hook macro

- **Where:** `compat/EffekseerGLHook.h` defines `eglGetProcAddress` as `TVPEffekseerGLGetProcAddressGeneric` for Effekseer's GL extension loader. In the kits' static builds, `efk_renderer_gl` then includes `<EGL/egl.h>`, whose declaration of `eglGetProcAddress` the macro rewrites.
- **What happens:** `efk_renderer_gl` doesn't compile in krkrz_android or krkrz_web.
- **Workaround:** `.github/platforms/krkreffekseer-kit.cmake` defines `<EGL/egl.h>`'s include guard (`__egl_h_`) for `efk_renderer_gl`.
- **Fix:** hook the loader without a macro on a system function's name, or include `<EGL/egl.h>` before the macro is defined.

### Android and web: `TVPUtf8ToUtf16` and `TVPUtf16ToUtf8` are defined twice

- **Where:** `src/utils.cpp` defines both functions, which the engine also defines. That's harmless while the plugin is a separate shared library. The kits link plugins statically into the engine.
- **What happens:** duplicate symbols when `libkrkrz.so` (Android) or `krkrz.wasm` links.
- **Workaround:** `krkreffekseer-kit.cmake` renames the plugin's copies with compile definitions (`TVPUtf8ToUtf16=kagex_efk_TVPUtf8ToUtf16`, and the same for `TVPUtf16ToUtf8`). Dropping `utils.cpp` instead broke `TVPU16ToTtstr`.
- **Fix:** make the plugin's helpers `static` or put them in a namespace, or use the engine's functions through tp_stub.

### Effekseer's in-class `static const` members have no definitions

- **Where:** Effekseer's `Effekseer::Gradient::KeyMax`, `Effekseer::MaterialFile::LatestSupportVersion` and `OldestSupportVersion` are initialized in their classes but never defined outside them. An unoptimized build odr-uses them: `std::min` and `BinaryReader::Read` take them by reference.
- **What happens:** the Android debug APK failed to link. The Linux Debug `libkrkreffekseer.so` linked with these three undefined and wouldn't load. 0.3.1's Linux debug package shipped like that; 0.4.0's release check caught it. Optimized builds fold the constants, so release builds are fine.
- **Workaround:** `.github/platforms/krkreffekseer-odr.cpp` defines them. `krkreffekseer-kit.cmake` adds it to `efk_core` in the kits; in the release workflow on `ci/windows-release`, `release-build/krkreffekseer-odr.cmake` adds it through `CMAKE_PROJECT_INCLUDE`.
- **Fix:** in Effekseer, make them `static constexpr` (implicitly inline since C++17) or define them in a source file. Or the plugin adds the definitions to its own build.

### Web: Effekseer maps its vertex buffers with `GL_MAP_UNSYNCHRONIZED_BIT`

- **Where:** `EffekseerRendererGL/GraphicsDevice.cpp` maps with `GL_MAP_WRITE_BIT | GL_MAP_UNSYNCHRONIZED_BIT`. WebGL 2 doesn't allow that bit, so Emscripten's `glMapBufferRange` returns 0, and Effekseer `memcpy`s into the result without checking it.
- **What happens:** nothing draws, and the copy overwrites the engine's low memory in the wasm heap. Later steps of the smoke test hung.
- **Workaround:** `.github/platforms/krkreffekseer-webgl.cpp` replaces the bit with `GL_MAP_INVALIDATE_RANGE_BIT`, through `glad_glMapBufferRange` renamed for `efk_renderer_gl` only (`krkreffekseer-kit.cmake`, under `EMSCRIPTEN`).
- **Fix:** don't ask for unsynchronized maps under Emscripten (or fall back to `glBufferSubData`), and check the map's result before writing to it.

### macOS and iOS: `glMapBufferRange` is `nullptr` unless `GL_ARB_map_buffer_range` is defined

- **Where:** `EffekseerRendererGL/EffekseerRendererGL.GLExtension.cpp`: on `__APPLE__` it calls `::glMapBufferRange` only `#if defined(GL_ARB_map_buffer_range)`, and returns `nullptr` otherwise. The plugin's GLES headers (for ANGLE) don't define that macro.
- **What happens:** the first effect drawn wrote through a null pointer and crashed the engine (SIGSEGV).
- **Workaround:** `.github/platforms/krkreffekseer-apple.cmake`, passed to the macOS configure as `CMAKE_PROJECT_INCLUDE`, defines `GL_ARB_map_buffer_range=1` for `efk_renderer_gl`.
- **Fix:** define it in the plugin's build for ANGLE's GLES 3, which has `glMapBufferRange`, and check the map's result in Effekseer.

### iOS: CMake's Xcode generator stops with "duplicate object ids not allowed"

The same error as krkr_richtext. `ios-config.json` leaves krkreffekseer out, so effects show nothing on iOS (the console says why).

### The captured frame has no usable alpha, so effects can only be drawn additively

- **Where:** Effekseer blends alpha with `GL_MAX`, so the alpha in a `GLCompositor.capture` is no coverage mask. With `premultipliedAlpha`, additive nodes leave alpha at 0. The engine's `ltAddAlpha` and `omAddAlpha` leave a source pixel whose alpha is 0 alone, so even correctly premultiplied output can't add light where alpha is 0 (see the engine entry below).
- **What happens:** layers that show an effect are drawn `ltAdditive`. Additive effects look as they do in Effekseer's editor, but normally blended nodes can't darken what's behind them.
- **Workaround:** `GFX_Effekseer.tjs` switches `ltAlpha` and `ltOpaque` to `ltAdditive`, and keeps any other type the scenario asked for. The sample's effects are all additive (`make_effects.py`).
- **Fix:** a capture that writes coverage (a separate alpha blend, `glBlendFuncSeparate` with `ONE, ONE_MINUS_SRC_ALPHA` for alpha), together with a premultiplied layer type in the engine that adds colour where alpha is 0.

### Every frame of every effect is read back from the GPU

- **Where:** `GLCompositor.capture` renders into an offscreen buffer and copies it into a layer's main memory every frame. Each `EffekseerFlip` captures its whole canvas about every 15 ms.
- **What happens:** the cost grows with the canvas size and the number of effects shown at once. The sample sizes its canvases to the effect (`efkwidth`/`efkheight`) to keep it down.
- **Fix:** let a layer show a GL texture without copying it back (drawing it in the GL draw device's composition), or render effects directly in the draw device.

### `play(startFrame)` runs every frame up to the start frame

- **Where:** Effekseer's runtime starts an effect at a later frame by updating it frame by frame from 0.
- **What happens:** restoring an effect from save data costs as much as playing it to that point.
- **Workaround:** `EffekseerFlip.flipRestore` caps the restored frame at 600 (10 seconds).
- **Fix:** probably not fixable in general: Effekseer's particles are stateful. A cheaper seek for effects that loop would help.

## Engine (krkrz_dev)

### BMP files written on Linux and macOS have the wrong pixel offset

- **Where:** `common/visual/GraphicsLoaderIntf.h` wraps `TVP_WIN_BITMAPFILEHEADER` in `#pragma pack(push, 1)` only `#ifdef _WIN32`. Elsewhere the 14-byte header is padded to 16, so `sizeof` gives 56. The writer puts `bfOffBits = 56` in the header but writes the pixels at byte 54, and the reader trusts the header. This affects every platform but Windows.
- **What happens:** anything saved with `saveLayerImage(..., "bmp")` comes back colour-shifted.
- **Workaround:** bookmarks (`MainWindow.tjs`) save their thumbnails as PNG. The test tools read the engine's BMPs from byte 54.
- **Fix:** apply the `pack` on every compiler (or write the header field by field).

### `Plugins.link("plugin/Foo.dll")` looks for `libplugin/Foo.so`

- **Where:** `TVPResolvePluginSoName` in `generic/base/PluginImpl.cpp` puts `lib` in front of the whole name, path included. Names without `.dll` get the prefix the same way.
- **What happens:** a plugin named with its folder isn't found on Linux, macOS, Android or iOS.
- **Workaround:** on non-Windows engines, `Initialize.tjs` wraps `Plugins.link` to drop the `plugin/` prefix. The engine's own search then finds `plugin/libFoo.so`.
- **Fix:** add `lib` to the file name, after the last `/`.

### An empty string in a boolean context crashes the engine

- **Where:** `tTJSVariant::operator bool` (`common/tjs2/tjsVariant.h`) converts a string with `AsInteger()`, which calls `String->ToInteger()`. An empty string is stored as a null `String`, so `if ("")` dereferences null (in `tTJSVariantString::ToInteger`).
- **What happens:** a segfault. The Replay screen crashed whenever an unlocked entry had no thumbnail. (Converting the string to a number is TJS2's rule, so `"event1"` being false is expected. The crash isn't.)
- **Workaround:** the scripts never test a string as a boolean; they compare it (`if (s != "")`).
- **Fix:** return 0 for a null `String` in `AsInteger` (and in `AsReal`).

### Searching for an unknown font name deadlocks the file allocator

- **Where:** given a face name it can't resolve, the engine opens every system font to search their names. Its pooled file allocator (`common/base/FileAllocator.cpp`) runs the storage cache's memory-pressure callback while holding its own mutex, which it does once the pool reaches 75% of `-filepoolsize` (256 MB by default). Triggered by `RichText.registerFont`, `Font.getFontInfo` and `Font.queryFonts`.
- **What happens:** the engine hangs, and the hung process ignores SIGTERM (it needs `kill -9`).
- **Workaround:** `RichTextFontApp.getFonts` only registers names that `Font.getVarAxes` resolves (the same lookup as `drawText`, without the search), and that the engine actually draws.
- **Fix:** release the allocator's mutex before running the pressure callback. Separately, the name search shouldn't need to keep every font file open.

### An unknown face name draws with the icon font

- **Where:** `common/visual/FreeType.cpp`: a face name the engine has not registered (`MS Gothic` on Linux, say) falls back to the `elements_basic` icon font rather than a text font. The engine's default face (an empty face name) does the same on Linux.
- **What happens:** text shows as arrows (`←←←`).
- **Workaround:** every face in the framework is a list ending in fonts that exist everywhere (`"Yu Gothic Medium,Yu Gothic,Noto Sans JP,Roboto"`), and the framework ships Noto Sans JP.
- **Fix:** fall back to a text font (Roboto, which the engine embeds) and never to the icon font.

### The face chain can get stuck on the icon font

- **Where:** the rasterizer keeps one face chain per face list and rebuilds it only when the list's first face changes. A font bundled in the engine's `resource/` is only found in the exact style asked for.
- **What happens:** in the browser build, where Noto Sans JP is bundled, the first text drawn in the list was bold (the `[select]` choices). The bundled font didn't match, the chain fell to the icon font, and it stayed there: every later text came out as arrows measuring 0 wide.
- **Workaround:** `Initialize.tjs` loads `notosansjp-regular.otf` with `Font.addFont` where the engine already has a font of that name. A loaded font is found in any style.
- **Fix:** let a bundled font match any style, synthesizing bold as for other fonts, and rebuild the chain when the style changes.

### Only Roboto is embedded, so Japanese needs system fonts

- **Where:** since engine 2.5.0 the engine embeds only Roboto. `resource/notosansjp-regular.otf` is in the source, but only the browser build bundles it.
- **What happens:** without system fonts, Japanese text draws as U+FFFD boxes.
- **Workaround:** the framework ships the engine's `notosansjp-regular.otf` (SIL OFL) in `template/system` and registers it with `Font.registerFontFile`.
- **Fix:** embed a CJK fallback, or document that games must ship one.

### A font file that claims a style it isn't can resolve but draw nothing

- **Where:** font matching. On Arch, the Noto Sans CJK JP Light file also claims the Regular style.
- **What happens:** plain `Noto Sans CJK JP` resolves (`Font.getVarAxes` finds it) but draws nothing. The weight-suffixed names (`Noto Sans CJK JP DemiLight`, `Light`) work.
- **Workaround:** `RichTextFontApp.getFonts` checks that a font actually draws before registering it.
- **Fix:** prefer the file whose weight matches the requested style when several claim it.

### The SDL engine lacks several Window features

- **`Window.setMaskRegion`** throws "not implemented", so shaped windows don't work. `askYesNo` uses the layer dialog on the SDL engine instead of `YesNoFrameDialogWindow`.
- **`Window.menu`** doesn't exist. `Menus.tjs` builds the menu items on a stand-in `Menu` class (`kag.menuBarStandIn`), and KAG's debug window gets Shift+F12 and Shift+F11 instead of the Debug menu.
- **Modal windows:** a second `Window` shown with `showModal` crashed the game on Linux (the old F1 About opened a modal `KAGWindow`), and `showModal` can't be used while the window being shown is the only one. The framework keeps all UI in the main window: About is `AboutDialogLayer`, and before the game window exists `askYesNo` uses `System.confirm`.
- **`Pad`** doesn't exist. `initLogPad` returns early, and `UpdateConfig.tjs` writes `Config.tjs.merged` instead of showing a Pad.
- **Full screen** is switched asynchronously, so reading `Window.fullScreen` straight after setting it gives the old mode. `changeFullScreenOrWindow` records the requested mode in `kag.fullScreened`, which everything deciding by the current mode reads. An event when the switch completes, or a getter that reports the requested mode, would remove that.

### `Storages.truncateFile` and seeking fail on non-local storage

- **Where:** `truncateFile` needs a local file name and throws "Cannot get local name" (`TVPCannotGetLocalName`, `common/base/StorageIntf.cpp`) for `user://`, the save folder of the browser, Android and iOS builds. Seeking past the end of a file fails with "Seek error" in the browser.
- **What happens:** every save failed there before the workaround, and the save-failed message blocked the title screen.
- **Workaround:** `saveThumbnailAndData` (`MainWindow.tjs`) puts the file together in `Storages.getTemporaryName()` and copies it over with `Storages.copyFile` where `truncateFile` throws.
- **Fix:** implement `truncateFile` (and seeking past the end, which extends the file) for the SDL storage that backs `user://`.

### The browser build's `omPs*` modes clear the destination's alpha

- **Where:** the layer blend functions without SIMD (`common/visual/gl/blend_function.cpp`), which the browser build uses. The SIMD versions the desktop builds use don't do this.
- **What happens:** drawing into an opaque layer with any `omPs*` mode writes alpha 0, so the CG and Replay thumbnails came out empty in the browser.
- **Workaround:** `setCGImage` (`Override.tjs`) and `fileDataButton` draw with `holdAlpha` set.
- **Fix:** keep the destination alpha in the C versions, as the SIMD versions do.

### `ltAddAlpha` skips source pixels whose alpha is 0

- **Where:** the `ltAddAlpha`/`omAddAlpha` blend leaves the destination alone where the source alpha is 0, instead of adding the source colour.
- **What happens:** premultiplied images can't add light where they're transparent (glows, additive effects). See the krkreffekseer entry above.
- **Fix:** add the colour whatever the alpha, as premultiplied blending does, or a separate layer type that does.

### `GLGetProcAddress` is 0 on a GPU draw device

- **Where:** `common/visual/opengl/GLCompositorIntf.cpp`.
- **What happens:** plugins that draw with GL through `GLCompositor` (krkreffekseer) can't work with the GPU draw device. Effects end at once there, and the console says why.
- **Fix:** expose the GPU device's GL function lookup, or document that `GLCompositor` needs the GL draw device.

### Web: the engine's file cache never updates

- **Where:** the browser build caches every `web://` file in OPFS under a key made from its relative URL alone (`krkrzOpfsKey`: SHA-256 of `gamedata/...`), never checks it with the server again, and shares the cache with every krkrz game on the origin (all of itch.io's HTML5 games share one origin).
- **What happens:** players of an updated site kept getting the old files, or another game's files with the same names.
- **Workaround:** `platform/web/kagex-web.js` and `web-static-host.py` (since 0.3.1): a build id the page checks before the engine starts. A new build empties the cache, and same-origin fetches revalidate.
- **Fix:** put the site's path and a version (the build, or the file's ETag or size) in the key, and revalidate.

### Web: other limits

- There's no `Agent` class, and a scenario load started inside a `krkrz_repl_eval` call crashed the page. The smoke test posts keys with `kag.postInputEvent` and runs commands from a `Timer`.
- Full screen is requested from the engine's own loop rather than a user event, so on Android and iPad the browser defers it to the next tap.

### Logs and test hooks

- The engine logs an `An exception occured at ...` VM dump for every thrown exception, including the ones the scripts catch. The log can't be scanned for real errors by that line, so the smoke tests look for `Script exception raised` and `! trace :` instead. A dump only for uncaught exceptions, or a level that turns it off, would help.
- Keys injected through `Agent` or the REPL don't change `System.getKeyState`, which KAG reads for Return and Space. Tests press, wait a frame, then release, and holding a key can't be simulated.
- Under SDL's offscreen video driver, `Agent.captureScreen` returns a black image with the default GL draw device. Tests render `kag.primaryLayer` with `piledCopy`, or use `-drawdevice=sdl`.

### Building

- **tp_stub.h** uses `ptrdiff_t` without including `<cstddef>`. With GCC 12, plugins that include `tp_stub.h` first (layerExSave, sigcheck, krkreffekseer) don't compile. The release workflow builds with `CXXFLAGS=-include cstddef`.
- **tp_stub's `krkrz.cmake`** caches `NCBIND_DIR` relative to the first plugin folder that includes it. With a kit's own plugin first (krkrz_android's `virtualpad`), that folder has no ncbind and the other plugins fail. The configs list a krkrz_dev plugin first.
- **CMake 4** needs `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`: some `cmake_minimum_required` in the engine's tree (its own or a dependency's) asks for a version CMake 4 dropped.
- **krkrthreepp** fails to build with Arch's newer GCC, so a full build there stops; local builds list the plugins kagex uses as targets.
- **Android, a11y:** with `KRKRZ_USE_A11Y`, the engine's AccessKit setup can't find its Android library (`find_library` inside the NDK's find root), so `libkrkrz.so` doesn't link. kagex's Android build has no `a11y` plugin.
- **Android, ICU:** with krkr_richtext the engine downloads ICU with `DOWNLOAD_EXTRACT_TIMESTAMP`, an option CMake 3.24 added, but krkrz_android asks Gradle for CMake 3.22.1 (see the kit entry below).

### Plugins KAGEX uses that krkrz_dev doesn't build

Script features that need these log the missing plugin and carry on.

- `layerExDraw` (GDI+): `AffineLayer.tjs`'s vector sources. krkrz_dev's `layerExVector` copies part of its API (`TODO.md`).
- `gfxEffect`: the fire effect (`GFX_Fire.tjs`).
- `flashPlayer`: Flash movies (`GFX_Flash.tjs`).
- `windowEx`: the extended window events, the menu-bar hiding and the window-control menu icons (`MenuItem.bi*`). `MainWindow.tjs` and `Menus.tjs` skip those paths without it.
- `layerExSubImage`: partial images in `psdlayer.tjs` (`TODO.md`: `psd://` can stand in).

## Platform kits

### krkrz_web

- **The file list is written where the engine doesn't read it.** The kit writes `gamedata.krkrz_files.json`, and only its `serve.py` answers requests for `gamedata/krkrz_files.json`, where the engine looks. On a static host (GitHub Pages, itch.io) the game stopped at `Config.tjs not found`. `web-static-host.py` copies the file there. Fix: write it to `gamedata/krkrz_files.json`.
- **coi-serviceworker reloads too early.** It reloads the page on `updatefound`, before its worker is active, so the reloaded page was sometimes uncontrolled and not `crossOriginIsolated`: nothing started until the visitor reloaded (`SharedArrayBuffer transfer requires self.crossOriginIsolated`). `web-static-host.py` sets `window.coi.doReload` to wait for `navigator.serviceWorker.ready`. Fix: the same in the kit's copy.
- **The built-in plugin list names Wamsoft's private repositories**, so a public checkout can't build without editing it. `.github/platforms/web-plugins.py` drops those plugins in CI.
- **The page has no manifest, icons or title** of the game's (it says `krkrz`). `web-static-host.py` adds them.

### krkrz_android

- **The fixed vcpkg manifest doesn't take in the plugins' manifests.** krkreffekseer needs minizip-ng, which the kit's manifest lacks. `.github/platforms/kit-vcpkg.py` adds it. Fix: merge the selected plugins' `vcpkg.json` dependencies.
- **It asks for CMake 3.22.1**, but the engine with krkr_richtext needs 3.24 (the ICU download above), and the `richtext` library asks for 3.31 (`cmake_minimum_required`). CI installs the newest SDK CMake 3.x and changes `version` in the kit's `app/build.gradle`.
- **The app is named "krkrz"** in `values`, `values-ja`, `values-zh-rCN` and `values-zh-rTW`, whatever the config says. `platform/android-res` (the `resOverride`) names it. Fix: take the name from the config.
- **The x86_64 build (for the emulator) needs `nasm`** for libvpx, which the kit doesn't mention.
