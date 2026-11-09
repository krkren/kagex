# To do

Planned features and fixes. The first section's entries wait on the engine: krkrz_dev itself isn't changed (`CLAUDE.md`), and what it and its plugins can't do yet is in `UPSTREAM.md`. Many entries came from moving a commercial game made with Wamsoft's framework to KAGEX's engines; they describe what such games do, for KAGEX to write again from scratch with its own names, formats and assets, taking none of that game's code, data or art. The last section lists the plugins and features looked at and left out, and why.

## Needing krkrz_dev

These wait on the engine, which kagex doesn't change (`CLAUDE.md`): each gets an `UPSTREAM.md` entry (where, what it costs, the fix) once it's confirmed at the engine `ENGINE_SHA` pins, and the framework works around it meanwhile where it can.

- [ ] **A multi-line text field for Elements screens**: ElementsDialog's `input_box` is one line, so a save comment, a note or anything longer needs one field per line.

## The message window and text

- [ ] **Chinese for the sample**: the framework shows any language a game lists (with a menu language of its own and a second one under the story's since 0.26.0), but Chinese needs SC and TC fonts, too large for the web build's download, so they'd ship as language packs (`KAGMountPatchZip`).

## Screens, menus and controls

- [ ] **Screenshots into a phone's photo gallery**: since 0.28.0 a screenshot goes to the save folder or the player's pictures folder, can be copied to the clipboard and its folder opened (`Display.tjs`, the sdlsystem plugin), but on Android and iOS the pictures folder isn't the gallery: that needs native code in kagex's sdlsystem plugin (Android's `MediaStore` through JNI, iOS's `PHPhotoLibrary` with `NSPhotoLibraryAddUsageDescription` in the app's `Info.plist`, which kagex-release would write), and a Config choice that appears only there.

## The World and staging

- [ ] **Android sometimes freezes in the first demo's rotation**: reported on Android: the game now and then stops responding in the KAGEX Extended Layer demo (`layer.ks`, the demo menu's first choice) at its rotation section, `*label2|Rotation` (`[layopt layer=0 rotate=30]`, then the rotation origin moved with `afx`/`afy`); the later angle and spinning sections (`*label9`, `LayerToRotateModule`; `*label10`, `LayerNormalRotateModule`; `*label12`) rotate the same layer, so the report may mean one of those. `platforms.yml`'s Android smoke test plays `layer.ks` to the end on the emulator with a clicking `Timer` and hasn't hung there, so it's intermittent or needs a player's pace. It isn't the sound threads' deadlock (`UPSTREAM.md` 44): `layer.ks` plays nothing before its movie section, and the sample's music has no labels since 0.18.0. The hunt for it (`smoketest.py --hunt`, `platforms.yml`'s `hunt` input: `layer.ks` from `*label2` to `*label13` over and over at a player's changing pace, with the game's thread stacks taken through `debuggerd` if it stops answering) ran it 50 times on the emulator without a hang (run 42168118362), so it may need a real phone's GPU or timing. Next: the same hunt on a phone (`--target android` with the debug APK over adb), or the reporter's logcat (`SDL/APP`) and `debuggerd -b` while it's frozen, then decide whether it's the framework (the affine layer's drawing, `AffineLayer.tjs`; the actions) or the engine (then an `UPSTREAM.md` entry and a workaround here).

## Tools for developers

- [ ] **Stand-ins for older Kirikiri games' plugins**: since 0.28.0 `doc/porting.txt` lists what differs on KAGEX's engines, `Porting.tjs` sends `Plugins.link` through a table (renamed, built in, skipped, missing or a script stand-in) with stubs for Windows-only calls and fstat's `copyFile`, and kagex-release turns other movie formats into WebM. What's left are the stand-ins worth having for any old game, written from what scripts ask of each API: win32dialog.dll's dialog templates drawn as Elements panels (many games' config and save dialogs are built on it; the largest piece), the original engine's data packs (`Scripts.saveDataPack`, `loadDataPack`, `Storages.saveOctet`) and getLangName.dll's system language name; and the game's icon taken from its old `.exe` as kagex-release's `identity.icon`. Stand-ins written for a port copy no plugin code and can be a start, but one for textrender.dll would follow a Wamsoft DLL's interface, so KAGEX would want its own design there.

## Looked at, not planned

- M2's E-mote characters (`emoteplayer`): E-mote's player comes only from M2, through an application and a contract for its SDK (even the plan for small developers), and no player for SDL3 Kirikiri Z is public: Wamsoft's krkrz plugin is private, and M2's Kirikiri one is a closed DirectX DLL for Kirikiri 2. A player of our own, written from the reverse-engineered format, would get around M2's licence (FreeMote, the work on that format, is noncommercial only). Live2D covers the same ground (`doc/world.txt`, "Live2D Characters"; the `l2d` flip). If M2's SDK is ever in hand, the plan is Live2D's: a krkrz plugin around its player library drawing through `GLCompositor`, World characters on `KAGEnvCharacterEyeLip.tjs`, an `emote` flip type, a stand-in for the smoke test, and the SDK in a private repository for CI.
- `layerExAreaAverage`: shrinks by area averaging, which `shrinkCopy` already does, in half the time and without the glitches `stretchCopyAA` left in text.
- `layerExLongExposure`: averages frames into one image, an authoring tool for rule images, which `tools/assets/make_rules.py` makes.
- `lineParser`: `[].load()` already reads a file line by line, and the framework parses with KAGParserEx and csvParser.
- `expat`: XML parsing; nothing in kagex reads XML, and only the desktop builds have it.
- krkr_richtext's per-character timing (`StyledLayout`'s `<delay>`, `<wait>` and `calcShowCount`): it times a text laid out whole, while KAG's conductor gives the message window a character at a time with its own waits, skipping and auto mode, so KAG keeps timing the characters (krkr_richtext lays out and draws each line of them: `useStyledLayout`).
- `krkrgles` (Windows only): an OpenGL ES context through ANGLE, for engines without one. The SDL engine draws with OpenGL ES, and krkreffekseer, krkrthreepp and krkrlive2d use its context.
- BISHAMON particles and Direct3D: another company's particle middleware, on Windows' Direct3D only; KAGEX has Effekseer for particles, and krkrthreepp's 3D on every engine since 0.14.0.
- Windows-only features of Wamsoft's games: stay on top, the taskbar preview, the panic key, the Windows display methods, full screen across several monitors, the mouse wheel through DirectInput, the movie display modes, the bitmap allocator, Win32 dialogs and launcher programs. They're tied to Windows, and KAGEX's engines run on seven platforms.
- Comments typed on saves: Wamsoft's games take them in a Win32 dialog, and Elements screens have no multi-line text field for them (above).
