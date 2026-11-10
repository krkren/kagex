# kagex-release

Packages a KAGEX game for Windows, Linux, Linux for Steam, macOS, the web, Android and iOS.
It opens a settings window (a local page in a browser app window, like the engine's own
tools), and everything it does can also run from the command line (`--cli`), for CI.

## Using it

A KAGEX package keeps the tool in `tools/`. Start it, and it opens the game in the folder above
(the one with `data/`); `Open…` picks another. The settings are saved to `release.json` next to
`data/`.

```bash
kagex-release                              # the window, for the game here or above the tool
kagex-release path/to/game                 # the window, for that game
kagex-release --cli init  [path]           # write release.json with the defaults (--force replaces it)
kagex-release --cli check [release.json]   # problems in the settings, and what this computer can build
kagex-release --cli icon <png|ico|exe> <out.png>  # the icon a build takes from that file (--size=N)
kagex-release --cli plan  [release.json]   # what a build would make
kagex-release --cli build [release.json]   # build the packages
kagex-release --cli keygen <keys file>     # write the game's keys file, or add the keys it lacks
kagex-release --cli split <file> <folder>  # what a build splits a .psd or .clip into
```

`check`, `plan` and `build` take `--platform=windows,linux,...` (only those platforms, whatever
release.json enables) and `--json`; `build` also takes `--engines=DIR` (engine packages to use
instead of downloading them; `KAGEX_RELEASE_ENGINES` does the same, and without either an
`engines/` folder next to the game's `data/`, or else next to the tool, is used when there is one) and `--keep-work` (keep the staged
files in `<output>/.work`).
`keygen` takes `--bits=1024|2048|3072|4096` (the signing key's length, default 2048) and `--force`
(every key new); `split` takes `--format=tlg6|tlg5|png` (the pictures' format, default TLG6). Exit codes: 0 fine, 1 problems found (or a platform failed), 2 failed.

### The keys file

Encrypting the archive, encrypting the compiled scenarios and signing each use a key of their
own, and all three live in one file, the game's **keys file** (*Keys*, `keys.file`; the
`KAGEX_KEYS_FILE` environment variable names it instead, for CI). So one key never opens
another kind of protection, and there is one file to keep safe:

```text
# kagex-release keys. ...
archive: 64 hexadecimal digits      (data.xp3, xp3crypt)
scenes: 64 hexadecimal digits       (compiled scenarios, scnfile)
signing:
-----BEGIN RSA PRIVATE KEY-----      (signing, sigcheck)
...
-----END RSA PRIVATE KEY-----
```

*Create keys…* in the window (it starts outside the game's folder) or
`kagex-release --cli keygen <file>` writes one with all three, or adds to an existing file the
keys it lacks and keeps the rest; it never replaces a key unless given `--force`. Keep the file
secret, outside the game's folder and out of its repository, and back it up: a game's patches and
later builds need the keys it was released with, and anyone who has the file can read its
encrypted files and sign files as the game. The check refuses a keys file inside `data/` (it
would be packed into the game), one that lacks a key the settings use, and one whose archive and
scenes keys are the same; it warns about one inside the game's folder. Nothing from the file is
stored in `release.json`, and only what a game needs to read its files goes into its engines.
The signing key is a PEM block that krkrz_tools' `krkrsign` reads out of the file as it is
(`krkrsign --cli sign --key=<keys file> dlc.zip` signs a DLC zip for `KAGMountSignedPatchZip`).

### What a build makes

For each platform, `<output>/<file name>-<version>-<platform>/` and its package next to it:

- **The desktops' archives.** With `xp3` data (or `bind`), the Windows, Linux, Steam and macOS
  builds split the game the way Wamsoft's games ship: `data.xp3` holds `startup.tjs`, the framework
  (`system/`), `main/`, `init/`, `sysscn/` and the files at the top of `data/`, and each media
  folder gets an archive of its own beside it: `bgimage.xp3`, `bgm.xp3`, `effect.xp3`,
  `evimage.xp3`, `face.xp3`, `fgimage.xp3`, `image.xp3`, `others.xp3`, `rule.xp3`,
  `scenario.xp3`, `sound.xp3`, `thum.xp3`, `uipsd.xp3`, `video.xp3`, `voice.xp3` (those the game
  has). The framework (`Initialize.tjs`) finds each beside `data.xp3`; a subfolder named in
  `Storages.tjs` stays a folder inside its archive. There's no `data/` folder. On macOS this needs
  KAGEX 0.9.2's framework (an older one looks beside the executable, so its macOS build keeps one
  `data.xp3`). The web, Android and iOS builds get the whole game in one `data.xp3`.
- **Windows**: `<file name>.exe` (with the game's icon, title, version and copyright when the tool
  runs on Windows), `<file name>.cf`, `SDL3.dll`, `plugin/`, and the archives (or `data/`, or
  `data.xp3` bound into the exe with the media archives beside it); a zip.
- **Linux, Steam**: `<file name>`, `<file name>.cf`, `libSDL3.so.0`, `plugin/`, the data, and for
  Linux a `.desktop` file with a 256x256 icon; a tar.gz, which keeps the executable flag.
- **macOS**: `<title>.app` with the game's name, bundle ID, version and icon (`AppIcon.icns`), the
  data in `Contents/Resources`, signed ad hoc or with your Developer ID (and notarized when
  asked); a zip or a dmg.
- **Web**: the krkrz_web site, with `index.html` titled and given the home-screen manifest and
  icons, and the game either as `gamedata/` (each file fetched when the game needs it; names in
  lower case and listed in `gamedata.krkrz_files.json`; scripts and `system/` prefetched) or as
  one `data.xp3`, preloaded as `krkrz.data`; a zip. The engine's own sample data isn't shipped
  (an empty `krkrz.data` in the files mode). It runs from any web server (GitHub Pages works:
  `coi-serviceworker.js` supplies the headers SharedArrayBuffer needs); `serve.py` serves it
  locally.
  - **Updates reach players.** Each build has an id (a hash of its files), in
    `kagex-build.json` and in the page, whose scripts load with `?v=<id>`. `kagex-web.js` checks
    it before the game starts: a page older than the site reloads, and a new build empties the
    engine's file cache (which otherwise keeps the old files for good); the game's files are
    always checked with the server. Upload the whole folder and players get the new version on
    their next visit.
  - **Add to Home Screen.** On phones and tablets a bar offers it until the player closes it
    (for 30 days) or adds the game: a button where the browser can install the page (Chrome,
    Edge, Samsung Internet, Opera on Android), the steps on iPhone and iPad (every browser
    there: Share, then Add to Home Screen) and in Firefox and other Android browsers (their
    menu). From the home screen the game opens full screen, which iPhone browsers otherwise
    can't do; the manifest, icons and Apple tags cover every browser's own way of adding it.
  - **Link previews.** Open Graph and Twitter card tags: the title, the description, and the
    preview image (1200x630 is best; without one, the icon). Discord, Slack, X and others need
    the site's address for the image: set *Site address*.
- **Android**: an APK, or an app bundle (`.aab`) for Google Play, with the game's application
  ID, version (the version code is 1.2.3 -> 10203 unless set), name (in every language) and icon
  (an adaptive icon with the game's icon in its visible square). `data.xp3` or the `data/` folder
  goes into the app's assets, stored uncompressed so the engine reads it in place. It's built by
  Gradle from the Android engine package (krkrz_android's project with the engine prebuilt), so
  it takes a JDK 17 or newer and the Android SDK, but no NDK; the first build downloads Gradle
  and the Android build tools. Without a keystore it is signed with a debug key, for testing;
  with one, the window asks for its passwords (the CLI reads `KAGEX_ANDROID_STORE_PASSWORD` and
  `KAGEX_ANDROID_KEY_PASSWORD`), which are never saved. Gradle's output goes to
  `android-build.log`. The app's `AndroidManifest.xml` gets a `<queries>` entry for the system's
  text-to-speech engines (`ttsQuery`, on by default: on Android 11 and later an app sees none
  without it), and the game's own additions: `manifestAdditions`, XML that goes inside
  `<manifest>` (permissions, features, more queries), and `applicationAdditions`, inside
  `<application>` (meta-data, services, receivers). `check` refuses XML that doesn't close as it
  opens or brings a `<manifest>` or `<application>` of its own.
- **iOS** (on a Mac with Xcode): the engine's app with the game's bundle ID, name, version
  (build number from the version unless set) and icon (an asset catalog compiled by `actool`),
  and `data.xp3` or `data/` in the bundle, and `photosUsage` as `NSPhotoLibraryAddUsageDescription`
  (what iOS shows as it asks the player to let screenshots into Photos; empty leaves it out, and
  the game then keeps its screenshots in the save folder). For devices it is signed with your certificate
  (Apple Development or Apple Distribution) and provisioning profile, whose entitlements it
  takes, as `<file name>-<version>.ipa`; for the Simulator, signed ad hoc, as a zip of the app.
  Identity `-` signs a device build ad hoc, to check the package.

The `.cf` next to the engine carries the developer's own `krkrz.cf` options plus `orgname` and
`appname` (the save folder on Linux and macOS) and, for the release engine, `debugwin=no`. Android,
iOS and the web get the same options, but `orgname` and `appname`, at the top of the `config.cf` they
read from their resources (the APK's assets, the app, the site's `resource/`), ahead of the engine
package's own; on the web an option the game sets is taken off the page's command line, which
the engine would read first. The licenses (`license.txt`, `licenses/`) go along. `SHA256SUMS` lists the packages, and the test run
starts this computer's build for a few seconds (headless where it can, through the engine's REPL;
a signed build refuses the REPL, so its test run reads the log for the "signatures verified" line)
and reports script errors; its log is `<output>/test-run.log`.

Every build also writes `<output>/<file name>-<version>-files.json`, the list of the game's files
(as packed, after the media conversion) with their SHA-256. A later build makes a **patch** from
it (Output > *Patch from*, `output.patchFrom`): `<output>/<file name>-<version>-patch/patch.zip`
holds the files that are new or changed since, in `data/`'s layout, and KAGEX loads it from next
to the game or from the save folder (`patch.zip`, then `patch2.zip` and on). Make each patch from
the full release's list, so it holds every change since then and replaces the one before. A patch
can't remove files, or change what the game reads before it loads patches (`Initialize.tjs`,
`Storages.tjs`, `startup.tjs`, the engine and its `.cf`); the build says so. A build with
*Patch from* set needs no platform, and a patch alone needs no engines but this computer's, for
compiling the scripts (none with *Scripts* off). Compiling gives the same bytecode each time, so
a patch holds only the scripts that changed.

### Signing (checking for tampering)

With signing on, the Windows, Linux, Steam and macOS builds carry RSA-PSS/SHA-256 signatures
(the same format as the engine's key-and-signing tool), and the game checks them with the
`sigcheck` plugin before it starts (`template/system/SignatureCheck.tjs`): it verifies the game
archive it loaded from, the engine and its plugins (a signed list, `<file name>.sigfiles`, sits
beside the executable), and every extra archive and patch. If any file is damaged, edited, or
signed with a different key, the game shows a message naming the file and quits. A signed build
also refuses the engine's REPL and debug options, so no console can be opened into it.

- **The key** is the signing key of the keys file (above): its **private key signs**, and the
  **public key**, worked out from it, is written into `data.xp3` so the game can check itself.
  Lose the keys file and you can't make updates that verify against the same public key, so keep a
  backup. A signed desktop build must ship archives (`data.xp3` or bound into the executable),
  not a loose `data/` folder.
- **The archives** each have a signature (`data.xp3.sig`, `bgimage.xp3.sig`...). The game checks
  `data.xp3` first; the media archives are mounted only once they have verified, so everything
  the game reads before that (the framework, `main/`, `init/`) is in `data.xp3`. With hidden names
  (*Hide names*, below) it's the same files and the same check.
- **Patches and extra archives** are signed too (`patch.zip` gets a `patch.zip.sig`). In a signed
  build they are verified and mounted only after the framework and `Config` load, so a patch can
  change scenarios, images and other assets, but the framework, `Config` and `Override` need a
  full release. An unsigned or wrongly signed patch stops the game.
- **The web, Android and iOS builds aren't checked** (there's no plugin for them): they rely on
  the app store's or your site's own integrity. They carry the key harmlessly and run as unsigned.
- **macOS**: the in-app check is a backup to the bundle's own code signature; a Developer ID build
  is still sealed by `codesign` as usual.
- **What it does and doesn't stop.** It catches a damaged download, dropped-in or modified files,
  unofficial patches and mods, and a swapped engine or plugin. It can't protect the code that runs
  the check: anyone who can rebuild `data.xp3` (or the engine itself) can take the check out. It
  raises the effort to tamper with a release; it isn't DRM.
- **Large games.** The engine's check uses 32-bit sizes, so no single archive may reach 2 GB.
  The media folders each have their own archive, so that's per folder: a signed build stops when
  one folder (or what stays in `data.xp3`) is 2 GB or more. Split such a folder's contents across
  subfolders of another media folder (`voice/` and `bgm/`, say), or move them to a folder the
  framework packs on its own.

### Encrypted game files

With *Encrypt the archive* on (`archive.encrypt`), `data.xp3` is packed with every file encrypted
(XChaCha20, a separate key per file). The [xp3crypt](https://github.com/krkren/xp3crypt) plugin,
built into the engine, decrypts each file as the engine reads it, so the game runs the same; the
scripts and assets are no longer readable in the shipped archive.

The key is the archive key of the keys file (above).

**Hide names** (`archive.hideNames`, desktop only, `xp3` data) goes further: every file in
`data.xp3` and in the media archives is stored under a keyed hash of its path, so a generic tool
sees neither the files nor their names. Only `data.xp3`'s `startup.tjs` keeps its name (encrypted
like the rest): the engine opens `data.xp3` as usual and runs it, and it mounts the archives
through the plugin's `xpcrypt://` storage medium, which finds each file by its hash. The package
looks like any other: the archives, and no `data/` folder. It needs KAGEX 0.9.2's framework
(`hashed-bootstrap.tjs`, `Initialize.tjs`, `SignatureCheck.tjs`); 0.9.0 and 0.9.1 shipped a
`data.xpc` with a loose `data/startup.tjs` instead, and the check asks an older `data/system` to be
updated. It can be signed (above).

The game's own `startup.tjs` goes into `data.xp3` as `startup-game.tjs` (its name hashed too),
and 0.9.4's `hashed-bootstrap.tjs` runs it once the archives are mounted, so the game starts as it
does from plain archives. With an older framework (0.9.2's or 0.9.3's) the bootstrap runs
`Initialize.tjs` in its place, and whatever else `startup.tjs` does is left out: the check warns
about that; update `data/system/hashed-bootstrap.tjs` from 0.9.4's `template/system`.

In such a build a name with a folder (`system/Initialize.tjs`) isn't found where it is, since the
archive's own names are hashed: the engine looks its file name up in the auto paths instead
(`system/` and the folders `Initialize.tjs` adds). A script in a folder that isn't an auto path
needs its full name: `global.kagexHashedArchive + "folder/name.tjs"` (`xpcrypt://data/...`).
File names in any language can be hidden, on every host (up to 0.9.3 a Windows host couldn't
encrypt a name outside its ANSI code page), and names are matched without regard to case, as in a
plain archive (`image.PNG` loads as `image.png`).

The build packs the encrypted archives (each with its own range of per-file keys, so no two files
share a keystream) and writes the key into each platform's engine; the engine
must have the xp3crypt plugin built in (the build stops with a clear message if it doesn't). The
key ships inside the game, so this keeps the files out of casual view rather than making them
unrecoverable to a determined person. Encryption applies to files inside `data.xp3`, so a platform
has to use `xp3` (or `bind`) data, not loose `folder`/`files`; the build warns otherwise. An engine
with no key reads a plain archive, so the same engine works with encryption off.

### Compiled scenarios

With *Compile* on (Scenarios, `scenes.compile`; on by default when the game has a
`!scnlist.txt`), the build compiles the scripts that list names into `.scn` files after the
media conversion, by running this computer's engine on the staged data with
`-scncompile=all` (its window stays hidden; the log is `<output>/compile-scenarios.log`). The
compiled scripts and the compiler's `parsermacro.ks` and `parseroption.txt` are left out of the
package, and the game plays the compiled files (`doc/scn.txt`).

- **Languages.** A game in more than one language (`KAGLanguageList` in `Config.tjs`) has each
  script's translations, `lang/<code>/scenario/<script>`, built into its `.scn` file as Wamsoft's
  multi-language games have them: every language's text, names, choices and titles in one file,
  the language shown picked as the game plays (`doc/scn.txt`, "Languages"). The translations are
  left out of the package with the scripts. A translation that doesn't fit its script (a scene
  with other texts or choices) is a warning in `compile-scenarios.log`, and that scene shows the
  script's own text in that language.

- **The scnfile plugin.** An engine with the scnfile plugin compiles to `.scn`, and then every
  platform's engine needs the plugin to play them: a platform whose engine package lacks it
  fails to build. Without the plugin the scripts compile to `.scn.json`, which every engine
  reads (in plain text). The check says which it will be (a note on this computer's platform,
  and *To compile: ... to .scn* in the plan) once the engine is here, and marks a platform whose
  engine lacks the plugin as one that can't be built.
- **Encryption.** With *Encrypt* on (`scenes.encrypt`), the `.scn` files are encrypted with the
  scenes key of the keys file (above; XChaCha20-Poly1305, scnfile's `docs/format.md`) and the key
  is written into each package's copy of the plugin, before signing and before the web build's
  id. A patch has to be built with the same key, and since the same file and key always encrypt
  to the same bytes, a patch holds only the scripts that changed. The key is in the game too, as it must be for the game to read its
  files: this keeps the scripts from plain view, not from a determined person.

### Media

Before packing, lossless media in the staged data are converted (the sources are never touched):

- **Sounds**: WAV and FLAC become Opus (by default 128 kbps in `bgm/`, 96 in `sound/`, 64 in
  `voice/`, 96 elsewhere) or Ogg Vorbis. FLAC is only a source (the engine can't play it): it
  becomes WAV when sounds are kept. A `<file>.sli` (loop points) follows its sound, moved to 48 kHz
  for Opus. The framework finds `.opus` files from KAGEX 0.3.0 on; a game with an older
  `data/system` is told to use Vorbis or update it.
- **Images**: PNG, BMP and TLG become TLG6 (or TLG5, PNG, JPEG) when opaque, TLG6 (or TLG5, PNG,
  or a JPEG plus a lossless `<name>_m.png` mask) when transparent. The mask of a main/mask pair
  (`<name>_m.*`) only goes to lossless formats, and the transitions' rule images (`data/rule`)
  become PNG whatever the setting (unless images are kept): the engine loads no TLG as a rule, so
  up to 0.14.0 a TLG or JPEG build turned every rule transition into a crossfade.
  The framework finds a button's converted hover, pressed and focus images from KAGEX 0.3.1 on;
  a game with an older `data/system` is told to convert images to PNG, keep them, or update it.
  A script of your own that looks for an image by adding an extension to its name
  (`Storages.isExistentStorage(name + ".png")`) won't find a converted one: use the framework's
  `getExistImageName(name)`, which tries every image format.
- **Movies** (since 0.28.0, through ffmpeg: on `PATH`, *ffmpeg* (`media.movies.ffmpeg`) or
  `KAGEX_RELEASE_FFMPEG`): MP4, MOV, AVI, WMV, MPEG, OGV, MKV and FLV become WebM (VP9 and Opus;
  `media.movies.convert`), which the engine plays; a movie named without its extension finds its
  `.webm`. And a movie a `[movie]` tag plays (its `storage=` written out; *For every movie*,
  `media.movies.smaller: "all"`, takes every WebM, alpha movies included, side-by-side ones too)
  gets a smaller version beside it, `<name>_sd.webm`, 540 lines high (`sdHeight`) at about 1200
  kbps (`sdKbps`), which `[movie]` plays on the web, Android and iOS and where the player picks
  the smaller movies (doc/kagex.txt, "Movies"); not for a movie that has one already, nor one no
  taller than that. Both are bit-exact, so a movie that didn't change makes the same file (and no
  patch carries it), and cached. Without ffmpeg the movies stay as they are, with a note.
- **Never converted**: Ogg, Opus and JPEG (lossy already), and files the scripts (`.ks`, `.tjs`,
  `.csv`, `.txt`, `.asd`, `.json`, `.func`) name with their extension, including printf patterns
  like `"ai%s%06d.wav"`, unless *Names with extensions* is set to rewrite them; then the staged
  scripts get the new names (UTF-8, UTF-16 and Shift_JIS scripts alike).

Results are cached by content and settings (in the cache folder below), so a later build only
converts what changed.

**CG pieces** (since 0.27.0): before the images are converted, the lossless pictures of the CG
folders (*CG folders*, `media.images.cgPieces`: folder names, by default `evimage`) are compared in
name order, each with the first of its run (its base). A picture of the base's size that differs
from it in at most half its area is staged as just the rectangle that differs (in its own format,
converted with the rest), and a line in the release's `cgpieces.txt` (`<name>`, `<base>`, `<x>`,
`<y>`, tab-separated) has the framework draw it back over the base wherever the game loads it by
name: a KAG or World layer, the gallery, `KAGLoadPicture` (doc/kagex.txt, "CG Variations From One
Layered File"). So `ev01b` to `ev01f`, the same scene with five faces, ship as one picture and five
faces. A picture that differs more starts a run of its own, as does one of another size. Left whole:
pictures in `lang/`, pictures whose name another picture of the game has too (a language's
version), names `cgvariations.txt` lists, masks and the pictures that have them, a layered file's
layer pictures, and pictures that become JPEG (each would be compressed on its own, and the
rectangle's edges would show). A script of your own that loads a CG into a plain `Layer` with
`loadImages` gets only the piece: use `KAGLoadPicture(layer, name)`. A framework from before 0.27.0
doesn't read `cgpieces.txt`, so with one every picture goes in whole. The comparisons are cached
by content.

**Loudness** (since 0.27.0): with *Measure every sound* (`loudness.measure`) a build measures the
staged sounds' loudness (EBU R128 integrated loudness, as the engine plays them: an Opus file's
header gain included) into `<name>-<version>-loudness.csv` beside the packages: each sound's LUFS,
how loud it plays with the game's `loudness.csv` (the framework's table of gains: doc/kagex.txt,
"Loudness"), and notes. With targets for kinds (`loudness.targets`: `voice`, `bgm`, `se`, each a
LUFS value; a sound's kind is the folder it's in, as the framework has it), each sound of those
kinds further than `loudness.tolerance` (1 LU) from its target gets a line in the release's
`loudness.csv` (the staged copy; the game's own file is left as it is) that brings it there. A
line the game has for that file wins; a speaker's line (`voice:<name>`) doesn't, since the tool
doesn't know whose a voice is. WAV files play without a gain (the engine applies one only as it
decodes Ogg Vorbis and Opus), so a far one is only noted: convert it or level it by hand. A sound
shorter than a 400 ms block is measured as one block (ffmpeg's `ebur128` gives such sounds no
value); longer ones measure as ffmpeg does (0.5 LU at most apart on a second-long sound, where a
few samples' difference in decoding moves the blocks). `kagex-release --cli loudness [<path>]`
prints the same measurements of the project's `data/` without building; measurements are cached
by content.

### Photoshop and CLIP STUDIO PAINT files

A game can keep layers in the files they're drawn in: a character's poses as `.psd` or `.clip`
files (`doc/world.txt`, "The layers in a PSD or CLIP STUDIO PAINT file"), and single layers named
with `psd://name.psd/root/folder/layer.bmp` or `clip://name.clip/...` (`doc/kagex.txt`). The
engine reads them through the psdfile and clipfile plugins, which only the desktop engines have,
and they're large, so every build splits them, each in place of the file, into what the framework
reads on every platform:

- `<name>.txt`: the layer structure, in `psdlayer.tjs`'s text format: the layers (top first) and
  folders, with their names (a `/` in one as `_`), places, blend modes, opacity, visibility and
  IDs, as the plugins report them.
- `<name>_<layer id>`: a picture of each layer that draws something, with its mask, in TLG6 (or
  the format *Media* gives pictures, TLG5 or PNG; with JPEG the media conversion makes that from
  the TLG6). Hidden layers are kept, and adjustment layers, a PSD's text layers and empty layers
  left out, as the framework leaves them out when it reads the file.

The layers are read with the libraries the plugins are made of (psdparse and clipparse), so they
come out as the game reads them during development. Files are split again only when they change
(the results are cached like the media's).

Which files go in: every `.psd` and `.clip` the game has (Contents > *Leave out* keeps them by
default), except one whose layers the game has already: a layer structure of its name,
`<name>.txt` (what `psdlayer.tjs`'s `saveImages` exports, or an earlier split), which the
framework reads in its place. A pattern of yours that leaves them out (`*.psd`) still lets a file
in when a script names it after `psd://` or `clip://`, or when it's a pose `charinit.csv` names
(`<files>.psd`, or `<files>_<level>.psd`, and the same with `.clip`). A file that can't be read
goes in as it is, with a note. A name the split would write that the game already has (a
`<name>.txt` that isn't a layer structure, or `<name>_<number>` as a picture) stops the build, as
do two such files of one name. Splitting needs a framework that reads the split files (KAGEX
0.11.0's or later: `AffineLayer.tjs`'s `affineLoadLayeredLayer`, `KAGEnvCharacterEx.tjs`'s
`findStandLayerFile`); with an older `data/system` the files go in as they are, which only the
desktop builds can read.

`kagex-release --cli split <file.psd|.clip> <folder> [--format=tlg6|tlg5|png]` writes what a
build would make of one file, to look at.

### Lip tracks

A voice's `.lip` beside it (the mouths' vowels for a character drawn from layers) goes in like any
file, and still applies once the voice is converted to Opus (the game looks for it by the voice's
name without the extension). kagex-lipsync (`../lipsync`), which ships beside this tool, makes
them; the check warns about a track kagex-lipsync made for a voice that has changed since, which
no longer fits it (make it again: *Out of date* in kagex-lipsync, or `--cli make --stale`).

### Compiled scripts

After the media conversion (which rewrites names in scripts), every `.tjs` in the staged data is
compiled to TJS2 bytecode (Contents > *Scripts*, `contents.compileScripts`, on by default). This
computer's engine does it, run headless with a script of the tool's (`Scripts.compileStorage`),
so the tool gets the engine package for this computer even when it builds no package for it.
Each script keeps its name; the engine tells bytecode by its header wherever it runs a script
(`startup.tjs`, `Scripts.execStorage`, `Scripts.evalStorage`), so nothing in the game changes.
A package then carries no readable TJS, and the scripts load a little faster. Strings and names
still show in the bytecode, so this keeps out casual reading, not a determined person.

- A script that is one expression (`envinit.tjs`'s `%[ ... ];`, a file holding a function) is
  compiled as one, so `Scripts.evalStorage` still returns its value. Others are compiled as
  statements, as `Scripts.execStorage` runs them.
- `@if` is decided when compiling: with `PACKED` set, `DEBUG` set for the debug engine (as the
  framework sets them), and the `@set` lines of the scripts the game reads first, which are
  compiled first (`startup.tjs`, `Initialize.tjs`, `Storages.tjs`, `AppConfig.tjs`,
  `Config.tjs`). A switch the game sets later with `Scripts.exec("@set (...)")` doesn't reach the
  compiled scripts: put it in `AppConfig.tjs` as a `@set` line instead.
- Errors in compiled scripts name the script and the function, at line 1: the engine's debug
  information makes it crash when it reports an exception, so the bytecode has none. With the
  debug engine chosen, the check warns about it: testers' builds are easier with *Scripts* off.
- The engines for Linux and macOS store integer constants beyond 32 bits (`0xff000000`) cut to 32
  bits. On those computers the tool compiles each script that has such numbers a second time
  with marker numbers in their place, and puts the real values where the markers are. A
  constant the compiler works out from others (`0xff << 24`, or `@"${0x100000000}"`) can't be
  followed that way: such a script stays as it is. Windows' engine keeps them.
- A script that doesn't compile stays as it is, and so does one too large for the bytecode's
  16-bit indexes (a function of more than 32767 code words, or more than 32767 different
  strings), and one with a `(const)` array or dictionary, which the bytecode has no form for (it
  would read as null); the build lists each one and why. The engine's output is
  `<output>/compile-scripts.log`.

### Engine packages

The engines come from the KAGEX release of the tool's version: `kagex_engine_<platform>.zip`
(and `_debug` for Windows and Linux), made from the release packages by
`scripts/engine-package.py`; for Android by `scripts/android-engine.py` from krkrz_android
and the release's APK; for iOS by `scripts/ios-engine.py` from krkrz_ios's unsigned device build
and its Simulator build. `--engines=DIR` or `KAGEX_RELEASE_ENGINES` points at a folder of
them instead (zips, or unpacked into folders of the same names; absolute, or relative to the
current folder), for working offline;
`KAGEX_RELEASE_ENGINE_URL` changes where they are downloaded from. Without either, an `engines/`
folder next to the game's `data/` is used when there is one (engine packages of your own, such
as ones with the scnfile or xp3crypt plugin), or else one next to the tool.

### Your own plugins

A plugin built for your game, which the engine packages can't carry (krkrlive2d, built with your
own Cubism SDK: `tools/live2d`), goes in `plugins/<platform>/` next to `data/`: `.dll` files in
`plugins/windows/`, `lib*.so` in `plugins/linux/` (Steam uses them too), `.dylib` in
`plugins/macos/`. Each build copies them into its `plugin/` folder (into `Contents/MacOS` in the
app) after the engine's, so one with the name of an engine plugin replaces it; they're all copied,
whatever `contents.plugins` says, and a signed build signs them with the engine. The plan lists
them. On Android (since 0.27.0) a plugin built for each ABI goes in `plugins/android/<ABI>/`
(`arm64-v8a`, `x86_64`, `armeabi-v7a`, `x86`) as `lib<name>.so`: the build puts it in the APK
beside the engine's libraries, where the engine opens a plugin it hasn't linked in
(`Plugins.link("plugin/<name>.dll")` finds `lib<name>.so` there); an ABI the engine package
hasn't got is left out with a note, and a plugin with the name of one of the engine's libraries
(`libkrkrz.so` ...) stops the build. The web and iOS engines have their plugins linked in and open
none at run time, so there a plugin of your own means an engine package built with it
(`engines/`); `check` warns about a `plugins/ios` folder for an enabled iOS, and about files in
the other folders that aren't plugins for them. On the web the one file of your own is Live2D's Web Core: the web
engine has the Live2D plugin, and a Live2D game's page loads `live2dcubismcore.min.js` (from your
Cubism SDK for Web) before the engine, so put it in `plugins/web/`: the build copies it into the
site and adds its script tag. An engine package never brings one (0.13.1 and 0.13.2's did, and
the build leaves theirs out). A game with Live2D models (`.l2d`) gets a warning for each enabled
platform that lacks what draws them: the Live2D plugin in a desktop's folder
(`tools/live2d/setup.py` builds it), the Web Core in `plugins/web/`.

Writing a plugin of your own, for the engines kagex-release uses:

- **No engine type in a global at namespace scope.** A `ttstr` (or anything that calls the
  engine) built as the library loads runs before `V2Link` has handed the engine's functions over,
  and the engine stops with "A dynamic link library (DLL) initialization routine failed". Make
  such values on first use, or in `V2Link`.
- **On Android, take the engine's `new` and `delete`.** The engine (`libkrkrz.so`) defines and
  exports its own `operator new` and `delete`, which `libc++_shared.so` uses for what it
  allocates, while a plugin opened later with `dlopen` binds its own `delete` to the C++
  library's plain one: the first `std::string` the plugin frees then stops the game ("Scudo ERROR:
  corrupted chunk header"). Define `operator new`/`delete` in the plugin to call the engine's
  (look them up in `libkrkrz.so` with `dlsym`), as kagex's ShellExecute, SpeechSynth and
  WaveFilters plugins do in their `AndroidAllocator.cpp` (UPSTREAM.md). A plugin linked into the
  engine (an engine package of your own) doesn't need this.
- **On Linux, build in the Steam Linux Runtime.** A plugin needs the glibc it was built against:
  one built with GCC 13 on glibc 2.38 asks for `__isoc23_sscanf`, which the runtime's 2.31 lacks.
  `tools/live2d/build.py --steamrt` shows how (Debian 11's GCC 10 in the `sniper` SDK image), and
  `-Wl,--exclude-libs,ALL` keeps a static libstdc++ inside the plugin.

### release.json

| Section | What it holds |
|---|---|
| `identity` | title, short name (home screens), file name (the executable and its `.cf`), version (`1.2.3`), copyright, organization and app names (the save folder on Linux and macOS; `krkren`/`kagex` is the sample's and is refused), icon (a 1024x1024 PNG; since 0.28.1 also an `.ico`, or a Windows game's old `.exe`, whose largest icon is taken: `--cli icon <file> <out.png>` shows it) |
| `engine` | `debug`: the debug engine instead of the release one |
| `contents` | `framework` (copy `template/system` in as `data/system` when the game has none), `font` (Noto Sans JP), `licenses`, `exclude` (patterns: `*.bak` anywhere, `bgimage/raw/**`, `work/`; the defaults are `*.bak`, `*.tmp`, `Thumbs.db`, `desktop.ini` and `.DS_Store`; a `.clip` or `.psd` that a script loads layers from, `clip://name.clip/...` or `psd://name.psd/...`, or that is a pose `charinit.csv` names, goes in all the same; every `.psd` and `.clip` that goes in is split into its layers: see "Photoshop and CLIP STUDIO PAINT files"), `extraFiles` (beside the executable), `plugins` (`all` or `linked`), `compileScripts` (TJS to bytecode) |
| `scenes` | `compile` (the scripts in `!scnlist.txt` into `.scn` files, without the scripts), `encrypt` (with the keys file's scenes key) |
| `media` | `audio.convert` (`opus`, `vorbis` or `keep`; from WAV and FLAC), `audio.opusKbps` (by folder under `data/`, `*` for the rest), `audio.vorbisQuality` (0-10), `images.opaque` / `images.alpha` (`tlg6`, `tlg5`, `png`, `jpeg` / `jpeg-mask`, `keep`; from PNG, BMP and TLG), `images.jpegQuality`, `images.cgPieces` (CG folders whose variations are kept as the part that differs; `[]` for none), `references` (`keep` files a script names with their extension, or `rewrite` the scripts) |
| `output` | `folder`, `archive` (`auto`: zip, tar.gz for Linux), `checksums` (SHA256SUMS), `check` (start the build for this computer headless afterwards), `patchFrom` (an earlier build's file list: also make `patch.zip` of what changed since) |
| `keys` | `file`: the game's keys file (the archive, scenes and signing keys; `KAGEX_KEYS_FILE` overrides it) |
| `signing` | `enabled` (sign with the keys file's signing key, and check for tampering before the game starts) |
| `archive` | `encrypt` (pack `data.xp3` encrypted with the keys file's archive key; the engine needs the xp3crypt plugin), `hideNames` (store the files in `data.xp3` and the media archives under hashed names; desktop only) |
| `platforms` | for each platform `enabled` and `data` (`xp3` or `folder`; Windows also `bind`, the web `files` or `xp3`), and its own settings: the web's site address (`url`), `description` and `preview` image; macOS bundle ID, signing (`adhoc` or `developer-id`), notarization, zip or dmg; Android format (`apk`/`aab`), application ID, version code, keystore, the speech engines' query (`ttsQuery`) and the manifest's additions (`manifestAdditions`, `applicationAdditions`); iOS target (`device`/`simulator`), bundle ID, build number, the photo library's reason (`photosUsage`), certificate, provisioning profile |

Missing members take their defaults, which come from the game: `sf.software_title`,
`sf.software_version` and `sf.software_maker` in its `first.ks`, and `krkrz.cf`. Passwords
(keystores, Apple accounts) are never stored in it.

### What each platform needs

The engine for each platform comes from the KAGEX release of the tool's version and is cached
(`%LOCALAPPDATA%\kagex-release`, `~/Library/Caches/kagex-release`, `~/.cache/kagex-release`, or
`KAGEX_RELEASE_CACHE`). Windows, Linux, Steam and the web build anywhere. macOS and iOS need a Mac
(iOS also Xcode, and for devices your certificate and provisioning profile). Android needs a JDK
17 or newer and the Android SDK. The window shows, for each platform, what this computer has.

## Building it

It uses krkrz_tools' libraries (xp3, audio, images) from krkrz_dev's submodule, unchanged:
`KRKRZ_TOOLS_DIR` defaults to `../krkrz_dev/src/tools/krkrz_tools` next to this repository (or
`$KRKRZ_BASE/krkrz_dev/...`). It needs CMake 3.21, Ninja and vcpkg (`VCPKG_ROOT`).

vcpkg has to be a clone of https://github.com/microsoft/vcpkg (as the CI uses), with
`VCPKG_ROOT` pointing at it: the vcpkg that comes with Visual Studio refuses a manifest without a
`builtin-baseline`, and `vcpkg.json` has none, so the libraries follow the clone. vcpkg's first
build also downloads its own CMake and PowerShell (about 165 MB) besides the libraries.

```bash
cd tools/release
cmake --preset linux                 # windows (Developer Command Prompt), macos (Apple Silicon)
cmake --build --preset linux-rel     # -> build/linux/Release/kagex-release, kagex-lipsync and lipsync/
python3 test/smoke.py build/linux/Release/kagex-release --browser   # --browser needs Playwright
```

`.github/workflows/release-tool.yml` builds it on all three systems and runs the smoke test.

The smoke test also builds when given engine packages (`--engines DIR`; the CI downloads a
release's `kagex_engine_*.zip`). `--tests scenes,patch` (any of `cli`, `server`, `build`, `web`,
`android`, `ios`, `media`, `scenes`, `patch`) runs some of its parts.

Encrypting scenarios uses scnfile's own code (https://github.com/krkren/scnfile,
`plugins/scnfile`): `SCNFILE_DIR` defaults to `../scnfile` next to this repository. Without it the
tool still builds and compiles scenarios, but refuses a key.

Source: `src/main.cpp` (CLI and the window's API), `Settings` (release.json: defaults,
validation), `Project` (finding the game, reading its defaults), `Host` (what this computer can
build), `Plan` (the game's files and the outputs), `Build` (the packages), `Engine` (engine
packages), `Scenes` (the scenario key, encrypting, the plugin's key slot), `Archive` (zip,
tar.gz, SHA-256), `Icons` (.ico, .icns, PNG sizes), `Sign` (key generation and signing, through
krkrz_tools' krt::sig), `Subprocess` (running other programs);
`web/` is the window.
