# To do

Planned features. Each needs changes to the builds as well as work in this repository; krkrz_dev itself isn't changed (`CLAUDE.md`), and what its plugins can't do yet is in `UPSTREAM.md`. The last section lists the plugins and features looked at and left out, and why.

## Needing more than scripts

These change the builds too: native code for every platform, including the web, Android and iOS engines in kagex-release's engine packages (the web build links its plugins into `krkrz.wasm`).

- [ ] **3D on Android, iOS and the web** (`krkrthreepp`): the 3d flip type and VRM characters (`GFX_Three.tjs`, `KAGEnvCharacterVRM.tjs`) draw with the Windows, Linux and macOS engines, which ship the plugin; the Android, iOS and web engines don't have it, so 3D layers show nothing there and the demos say so. Android's kit and the web's plugin list would take it as they take krkreffekseer (`app-config.json`, `web-plugins.py`; threepp has an Emscripten path), and iOS may stop at the Xcode generator's duplicate object ids as krkr_richtext and krkreffekseer do (`UPSTREAM.md` 32), though threepp's folders have a `project()` of their own.

## Looked at, not planned

- M2's E-mote characters (`emoteplayer`): E-mote's player comes only from M2, through an application and a contract for its SDK (even the plan for small developers), and no player for SDL3 Kirikiri Z is public: Wamsoft's krkrz plugin is private, and M2's Kirikiri one is a closed DirectX DLL for Kirikiri 2. A player of our own, written from the reverse-engineered format, would get around M2's licence (FreeMote, the work on that format, is noncommercial only). Live2D covers the same ground (`doc/world.txt`, "Live2D Characters"; the `l2d` flip). If M2's SDK is ever in hand, the plan is Live2D's: a krkrz plugin around its player library drawing through `GLCompositor`, World characters on `KAGEnvCharacterEyeLip.tjs`, an `emote` flip type, a stand-in for the smoke test, and the SDK in a private repository for CI.
- `layerExAreaAverage`: shrinks by area averaging, which `shrinkCopy` already does, in half the time and without the glitches `stretchCopyAA` left in text.
- `layerExLongExposure`: averages frames into one image, an authoring tool for rule images, which `tools/assets/make_rules.py` makes.
- `lineParser`: `[].load()` already reads a file line by line, and the framework parses with KAGParserEx and csvParser.
- `expat`: XML parsing; nothing in kagex reads XML, and only the desktop builds have it.
- krkr_richtext's per-character timing (`StyledLayout`'s `<delay>`, `<wait>` and `calcShowCount`): it times a text laid out whole, while KAG's conductor gives the message window a character at a time with its own waits, skipping and auto mode, so KAG keeps timing the characters (krkr_richtext lays out and draws each line of them: `useStyledLayout`).
- `krkrgles` (Windows only): an OpenGL ES context through ANGLE, for engines without one. The SDL engine draws with OpenGL ES, and krkreffekseer, krkrthreepp and krkrlive2d use its context.
