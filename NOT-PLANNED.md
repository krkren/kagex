# Looked at, not planned

Plugins and features of Wamsoft's games and Kirikiri's plugins that were looked at for KAGEX and left out, and why. Planned features and known bugs are [GitHub issues labelled `todo`](https://github.com/krkren/kagex/issues?q=is%3Aissue+is%3Aopen+label%3Atodo); what krkrz_dev and its plugins can't do yet is in `UPSTREAM.md`.


- M2's E-mote characters (`emoteplayer`): E-mote's player comes only from M2, through an application and a contract for its SDK (even the plan for small developers), and no player for SDL3 Kirikiri Z is public: Wamsoft's krkrz plugin is private, and M2's Kirikiri one is a closed DirectX DLL for Kirikiri 2. A player of our own, written from the reverse-engineered format, would get around M2's licence (FreeMote, the work on that format, is noncommercial only). Live2D covers the same ground (`doc/world.txt`, "Live2D Characters"; the `l2d` flip). If M2's SDK is ever in hand, the plan is Live2D's: a krkrz plugin around its player library drawing through `GLCompositor`, World characters on `KAGEnvCharacterEyeLip.tjs`, an `emote` flip type, a stand-in for the smoke test, and the SDK in a private repository for CI.
- `layerExAreaAverage`: shrinks by area averaging, which `shrinkCopy` already does, in half the time and without the glitches `stretchCopyAA` left in text.
- `layerExLongExposure`: averages frames into one image, an authoring tool for rule images, which `tools/assets/make_rules.py` makes.
- `lineParser`: `[].load()` already reads a file line by line, and the framework parses with KAGParserEx and csvParser.
- `expat`: XML parsing; nothing in kagex reads XML, and only the desktop builds have it.
- krkr_richtext's per-character timing (`StyledLayout`'s `<delay>`, `<wait>` and `calcShowCount`): it times a text laid out whole, while KAG's conductor gives the message window a character at a time with its own waits, skipping and auto mode, so KAG keeps timing the characters (krkr_richtext lays out and draws each line of them: `useStyledLayout`).
- `krkrgles` (Windows only): an OpenGL ES context through ANGLE, for engines without one. The SDL engine draws with OpenGL ES, and krkreffekseer, krkrthreepp and krkrlive2d use its context.
- BISHAMON particles and Direct3D: another company's particle middleware, on Windows' Direct3D only; KAGEX has Effekseer for particles, and krkrthreepp's 3D on every engine since 0.14.0.
- Windows-only features of Wamsoft's games: stay on top, the taskbar preview, the panic key, the Windows display methods, full screen across several monitors, the mouse wheel through DirectInput, the movie display modes, the bitmap allocator, Win32 dialogs and launcher programs. They're tied to Windows, and KAGEX's engines run on seven platforms.
- Comments typed on saves: Wamsoft's games take them in a Win32 dialog, and Elements screens have no multi-line text field for them yet ([#32](https://github.com/krkren/kagex/issues/32)).
