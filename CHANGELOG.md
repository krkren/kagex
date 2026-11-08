# Changelog

## 0.27.0

### Added

- **The game's own mouse pointers**: a game lists its pointers in `cursors.csv` (the arrow, over buttons, at a click wait, in auto mode, over a text field, over something to drag, busy) and they're drawn over everything, following the mouse, at the same size on the screen whatever the window's zoom, with the system's pointer hidden over the game; the SDL engine itself shows only the system's arrow (`UPSTREAM.md` 51). Config's Mouse Pointer picks the game's or the system's. The sample has its own, in its colours (`make_ui.py cursors`). Desktops and the browser (`GameCursor.tjs`).
- **Advanced settings**: Help > Show Advanced Settings adds an Advanced menu to the menu bar, and the manual has a page of them on every platform: memory use (Low keeps fewer pictures), the picture cache's size, the drawing threads, the controller and the movies' size, each taking effect at once, and Default. The options the engine reads only as it starts still need its own `-userconf` screen (`UPSTREAM.md` 52). `changeUserConf`, which `standview.tjs` called without it existing, keeps an option for the next start (`Advanced.tjs`).
- **A game's own plugins on Android, without an engine of its own**: kagex-release puts `plugins/android/<ABI>/lib*.so` in the APK beside the engine's libraries, where the engine opens a plugin it hasn't linked in; `check` warns about files and folders that aren't one and refuses a plugin named as an engine library. `tools/release/README.md` has notes for plugin authors (no engine types in globals, the engine's `new` and `delete` on Android, building for Linux in the Steam Runtime).
- **kagex-release measures loudness**: with *Measure every sound* a build reports each sound's EBU R128 loudness as it plays, and with targets for voices, music or sound effects it adds a line to the release's `loudness.csv` for each sound further than the tolerance from its kind's target (the game's own lines win; WAV files, which play without a gain, are only noted). `--cli loudness` prints the measurements without building. The measurement is the tool's own and matches ffmpeg's `ebur128`.
- **Saves that outlast a patch of their script**: a save keeps what its line says and the two before it, and a save made before a patch resumes at that line in the script as it is now, wherever lines added or taken out have moved it, the history's lines too; up to 0.26.1 any change to a script, or to `envinit.tjs`, sent every save in it back to the top of its scene. A line the patch changed is found by the two before it. A compile says in the log how many lines of each scene are new and how many gone since it was last compiled (`KAGEnvPlayer.mapPoint`, `SceneParser.reportTextChanges`, doc/scn.txt).
- **Smaller packages for CGs drawn as whole pictures**: kagex-release keeps a CG that is the one before it with a little changed (a face, an arm) as the rectangle that differs, and the framework draws it back over that one wherever the game loads it by name (`cgpieces.txt`, `KAGCGPieceDraw` in `CGVariations.tjs`). *CG folders* says where to look (`evimage` by default); pictures that become JPEG stay whole. A patch or DLC that brings a `cgpieces.txt` or a `cgvariations.txt` has them read again.
- **Where a question puts the pointer**: Config's Pointer on Questions leaves the pointer where it is as a Yes/No prompt opens, or puts it on No or on Yes (which then has the keys' focus too); About and the controller test follow it.

### Changed

- **The transitions demo shows extNagano's transitions as the plugin draws them**: from 0.18.0 to 0.26.1 kagex drew book, multiripple, rgbfade, zoomfade and spin itself in scripts (`ScriptTransitions.tjs`), under the plugin's names, because krkrz_dev's rebuild of the plugin draws them wrong (`UPSTREAM.md` 42), so the demo passed kagex's drawing off as the plugin's. The scripts are gone, those five are left out of the demo, and it shows the plugin's other seven; a game that uses the five gets the plugin's own.
- **A Yes/No prompt no longer moves the pointer to No by itself** (it did since KAG3: `DialogLayer.setFocusToLink`); Pointer on Questions brings that back.

## 0.26.1

### Fixed

- **A signed game could lose parts of its window at start-up and stop with an error, or hang**: the engine's signature checker looks a member up on the window it was given from its own thread for every per cent it checks, and a member lookup rearranges the window's member table while the game's timers look members up in it. The checks run on an object of their own now (`KAGSignatureChecker`, `SignatureCheck.tjs`), for start-up and for signed DLC. A smoke step runs 60 checks while a timer looks the window's methods up every millisecond (`UPSTREAM.md` 50).
- **The smoke test made the game rebuild its file list on every command**: it deleted its result file before each one, and the engine rebuilds its whole auto path table whenever a script makes a new file (5-7 ms for the sample, at each wait's poll every 50 ms). The file is written over now, with the command's number on its first line; a command takes 51 ms instead of 56. The release's Windows test (`run-kagex.ps1`) did the same, and also wrapped every command in a function of its own, which the engine keeps compiled: its result writer is defined once now.

## 0.26.0

### Added

- **Objects that move with others**: a World layer or character can be attached to another (`attach=`: it moves, zooms, turns and fades with it, `attachbehind=` puts it behind, `attachkeep=` keeps it when the other leaves), follow another's picture as drawn (`follow=`: a reflection, a shadow, a copy that blinks with it), be drawn only where another is (`clipto=`), or be placed once beside one (`relative=name,dx,dy`); `detach` lets go. They're World state, so compiled scenes, saves and Back keep them, and the attached ones leave with the other (`KAGEnvLinks.tjs`). The Character demo has a speech bubble on Pip, a light clipped to Ai and a mirrored copy following her.
- **Pictures and outfits an earlier choice changes**: `imagenamemap.txt` and `dressnamemap.txt` (Wamsoft's tables of a name, its replacement and a condition) are decided as a picture is drawn, so a flag changed later changes it the next time it's drawn, for event pictures, stages and both kinds of characters. In the Character demo the park route gives Pip his beret later on.
- **CG variations from one layered file**: `cgvariations.txt` names pictures that are one layered file's layers shown in different ways (a layer shown with its folders, shown alone in its folder, hidden, everything hidden first; a variation can start from another's), put together as they're shown from the split file kagex-release makes of a `.psd` or `.clip` (or the file itself through its plugin), so a game ships the file once. KAG and World layers, stages, the gallery and its viewer take the names, and the gallery unlocks each by its own (`CGVariations.tjs`). The Animated Character demo shows four of Pip's CG, one tile in the gallery.
- **A manual inside the game**: Help > Contents, F1 and Config's Manual button open pages of help in the game window on every platform, with links between them, Back, Forward and Contents, the keys, the controller, the mouse, touch and screen readers. Links can set an option there and then (with a box showing the one in use), close the manual and open a screen, or copy an address or a path; pages say which keys do what as the player has set them. The framework has ten pages in English and Japanese (the controls, saving, the settings, a slow game, a stretched or blurry picture, sound, movies, accessibility, getting help), which a game adds to or replaces by name (`Manual.tjs`); the sample adds a page about its demos and its own support page.
- **A menu language of its own, and a second language under the story's**: the menus, screens and interface fonts can be in another language than the story (Config's Menu Language), and a second language can show each message again under it, smaller (Second Language; Shift+F9 swaps the two), for language learners or two players. The sample's Config has a Languages page.
- **Checks for translators**: the scene compiler warns about a translated text left empty and a speaker shown by another name in one language only, and `-scncompile` ends with a report for each language of the texts still as written in the script's language and where they are.
- **A playthrough tester**: `tools/playtest.py` plays a game's routes on their own, each in a headless game with its own save folder and log, taking the choices given or every branch in turn, several at once, and reports each route done, stuck, or the first script error with its file, line, tag and trace (`KAGPlaytest` in `DebugTools.tjs`).
- **Debug helpers**: the Debug menu restarts the script, lists its lines to go to any of them, shows the flags to read and set (`flaglist.txt` says what they are), copies the voice's file name or where the game is, writes a bug report with a screenshot, traces every tag into the log and dumps the layers and the World. `-allseen=yes` counts everything as seen for a run; `-instance=` gives a run a lock of its own.
- **Full screen filled part way**: Full Screen Fit's Part Way and How Far to Fill zoom the game from the size that shows all of it with bars to the size that fills the screen, by a percentage. The Screen menu lists the window sizes that fit the screen.

### Fixed

- **The Japanese staging-kit lines were punctuated in English** (`char.ks`'s gestures), which the new translator report found.
- **The smoke test's Sprite Mode check failed on Windows**, whose engine lists file names in lower case.
- **A CG made from a layered file kept the file's layers for the rest of the game** (the last four files): now only the last file, until ten seconds after the last picture drawn from it (`KAGCGVariationLinger`). The browser build has 2 GB in all and ran out of memory late in its smoke test with them kept.
- **The smoke test's own commands no longer pile up in the engine's memory**: each wrapped the step's code in function expressions, and the engine keeps every compiled block with a function in it, some 16 KB a command, which over the thousands of commands of a run came to about 180 MB (the game itself keeps nothing as it goes from scene to scene); the browser build, 2 GB in all, ran out late in its smoke test. Each command's code now goes as a string to a runner defined once. On the desktop the smoke test also logs the engine's memory after each step (pictures, files, sound, scripts and the process, from the REPL's `.mem`).

## 0.25.0

### Added

- **Previews that play the scene**: the card beside a Replay tile, a Search row or a chart node now plays the scene's opening lines in it, as the story would show them (the World as each line leaves it, the speaker's name and the line, the waits by the line's length), with a bar for how far it has gone, "End of the scene" at its end and its last picture kept. Ctrl (a controller's R2) hurries it. The branches of an `[if]` follow the route's flags (`ScenePreview.tjs`). On a touch screen a long press on a tile, a row or a node shows the card, which a mouse shows by resting on it.
- **Sprite Mode: a stage of the player's own**: several characters at once, each dragged into place, turned round, zoomed by the wheel or the buttons and taken on or off the stage; a row for each pose's variations (Pip's arms); a line typed in and shown in a message window, as in the story, with the picked character's name; the panel put away (a right-click brings it back); a screenshot without the panel; and, on a desktop, the player's own pictures from the save folder's `backgrounds/` as backdrops (`SpriteMode.tjs`).
- **Favourite voices from the story**: V (the `favouriteVoice` action) keeps the voiced line on screen with the favourites, and the backlog's star does the same for any line in it. The music room's voices have three playlists besides the favourites, a lock that keeps a line in its list, the speaker's face at the line, a jump to the scene the line came from, and Play all, which plays a list's voices one after another (`Voices.tjs`).
- **The music room's player**: Play turns into Pause (a click on the record, Space or Return does it too), a level meter moves with the music, the tracks play once, in order or shuffled, and three playlists of tracks can be put in order by dragging (`MusicPlayer.tjs`).
- **Spoken greetings, and a choice of greeter**: Config's Title Greeting picks who greets the player on the title (Ai, Pip or no one); Pip greets in his own babble, with his own picture, and a greeting's line can have a voice (`greetings.csv`'s Who column, `KAGGreetingGreeter`).
- **The quick menu's buttons put in order by dragging**: Change Controls has a strip of the quick menu's buttons, each dragged to its place (`KAGQuickOrderStrip`); its rows shrink to fit the screen.
- **Scene moves in KAG's own player**: back to the start of the scene, back to the last choice, rewind and on to the next scene work for scripts KAG plays itself (scripts not in `!scnlist.txt`, or `-scnplay=no`), from the label titles they pass, as they do for compiled scenes.
- **Screen readers read the screens drawn on message layers**: Config, save and load and Extras give each button, link, text box, check box and slider to the screen reader, named by its label or its help line, with the screen's help line as its description; the focus follows the keys, and the screen reader can press them. A scrolling list on such a screen (the music room's tracks) is read with it (`KAGMessageNodes`, `KAGA11yScreenNames`).

### Fixed

- **The music room's progress bar was jittery**: the engine reports where a sound is in steps of 21 or 43 ms, and for half a second after a seek or a loop a buffer ahead, so the bar jumped back and forth. The bar and the time now follow a clock set from the music, set again only when the music really jumps.

## 0.24.0

### Added

- **A flowchart**: the scenes of a game's compiled scripts as a chart, a node for each scene with a title of its own and the jumps and choices between them, the ones the player has read drawn and the others a "?", a NEW badge on those reached since the chart last showed them and a pin on the story's place (`Flowchart.tjs`). The first time the story reaches a node the game keeps its flags, and a node played from the chart starts with them, so the scenes after it find the choices made; a scene after a choice is reached by playing its script from the start unseen, taking the choice that leads there. `flowchart.csv` gives the nodes captions, chapters, places and conditions that open them early; the chart takes drags, flicks, the wheel and pinches to move and zoom, the arrow keys (a controller's D-pad) to go from node to node, and screen readers. The sample's Extras has a Chart tab, its Character demo a choice whose two ways meet again, and its Extras tabs are narrower to make room for six.
- **Scene previews**: Replay's tiles, Search's rows and the chart's nodes show a card beside what the pointer rests on or the keys are on, with the scene as it opens (the World at that line, from the compiled scene's saved state), its title and the line, in the language shown (`ScenePreview.tjs`; any scrolling list or chart with a `preview` function).
- **Favourite voices**: the music room has Music, Voices and Favourites views. Every voiced line the player has heard is listed, a click plays it, its star keeps it with the favourites, and the favourites can be put in any order by dragging their handle or with Shift and the arrow keys (`Voices.tjs`). Any one-column scrolling list can be put in order this way (`KAGScrollList.reorder`), and can take keys on its focused item (`onItemKey`).
- **The music room's player**: a record that turns while the music plays, the track's title, how far it has played of how long, and a bar that seeks by a click, a drag or the left and right keys (`MusicPlayer.tjs`, `KAGNowPlaying`).
- **Title greetings**: Ai greets the player on the title screen in a speech bubble, by the time of day, the weekend, the date, the first start and a return after days away, with the player's name once they've given one (`Greetings.tjs`, `greetings.csv`; an optional voice for each line).
- **Sprite Mode**: the CG screen's Characters button shows every character one at a time in any pose, outfit and face (Pip's and the 3D and Live2D characters' too, where they're drawn), over the street by day, in the evening or at night (`SpriteMode.tjs`, `spritemode.ks`).

### Fixed

- **Replay's Text Effects tile was in English in Japanese.**

## 0.23.1

### Fixed

- **Characters that come in (`[font appear=]`) came in all at once**, as the Text Effects demo's appear line showed on Android (and elsewhere): every character typed set the animation timer's `enabled` again, which starts its interval again, so while the text typed faster than the timer's 33 ms it never fired; when the line was done most of its characters were already past their 400 ms and showed at once, and moving characters stood still until then too. The timer is armed once now, and a character that comes in starts at the first frame it's shown, no sooner than the text's own speed after the one before, so characters drawn together (a slow phone catching up) still come in one after another. The smoke test counts the characters showing while the line types.
- **Android: the opening could hang the game on a slow device**: a movie played once is stopped just before its end there, since stopping one that has reached its end hangs the engine (`UPSTREAM.md` 38), but the check came on a 50 ms timer that a device drawing a frame in half a second ran late, so the movie ended, looped back and hung as it was stopped (0.23.1's first release run, on the emulator). The margin now grows with the longest wait between two checks (300 ms plus twice that, at most 1.5 s).

## 0.23.0

### Added

- **A Text Effects demo**: the sample's demo menu has a ninth demo, a page each for what a message window does with its text: colour, size, weight and slant, another font, outlines and shadows, gradients, ruby, pictures in a line, alignment, letter and line spacing, indents, speed and pauses, characters that move and come in, a name shown as another, `[emb]`, the glossary's marks, a window style and vertical text (`text.ks`, in English and Japanese; Replay lists it under Effects).
- **Characters that move**: `[font anim=shake|wave|pulse|rainbow animsize= animspeed=]` keeps the characters after it moving while the page shows, and `[font appear=fade|rise|drop|slide appeartime=]` brings each in as it's drawn (`[deffont]` for the window's default). Each is drawn on a small layer of its own; `[backlay]` copies them, Reduce Motion holds them still and skipping brings them in at once.

### Fixed

- **The quick menu's buttons showed over the TV static**: the strip was on the primary layer, over the whole fore page, so a World layer at `level=message` (the Effects demo's static) covered the message window but not its buttons. The strip is on the fore page now, at the first message window's level plus 100, with a picture of it on the back page so a transition doesn't fade it out, and a save's thumbnail leaves it out.
- **Vertical text**: KAG put one `@` before the window's face, which is a list, and no font was found, so every character was an arrow 0 wide, drawn on the last; and the SDL engines draw a vertical face upright from the point given, where Windows draws it to the left, so the characters came out a character's width off their line. Each face gets its `@` (`KAGVerticalFace`), the characters are centred on the line, and the full stop and the comma go to the top right of their cell and brackets and dashes are turned a quarter, as vertical forms are.
- **A `[style]` at the start of a line was lost in a line mode**, as a `[font]` was up to 0.22.0: it's kept through the clear before the line's text now (`kag.clearForLine`).
- **A 。 after an `[emb]` could start a line in Japanese**: the line breaker planned the text after the `[emb]` on its own and broke before its 。; a character that may not start a line hangs into the margin in the middle of a line now.
- **A script-drawn transition of the whole page** (zoomfade, rgbfade, book, multiripple, spin) showed the message window's inside black: the page's pictures kept the window's see-through alpha. They're opaque now.
- **A compiled scene's title in the corner** showed in the source language whatever language was shown.
- **The Character demo's flashback jumped into place and back**: Pip faded out first, then the bars, the sepia edge, the memory's window and Ai's move came at once; at its end the screen went black at once and the street faded in from black. The memory's changes now go between `[begintrans]` and `[endtrans trans=normal]`, so it comes in as one crossfade (Ai stays where she stands), and `[env restore]` with a transition (`trans=`, `fade=`, a transition's name, or inside `[begintrans]`) keeps the scene on the screen in front while it draws the kept one behind it, for one crossfade from the one to the other. A message window style set behind a global transition goes on the back page's window first and on the other once the pages are exchanged, so the window changes in the same crossfade.

## 0.22.0

### Added

- **The game's fonts, and one table of text styles**: `fonts.csv` lists the fonts a game uses, with the file it ships, its roles (message, interface, heading, number), the languages it covers, its name for the player and its licence; a role's face list follows from it (`KAGFontFace`), and About lists the licences. Text the framework and the sample draw on their own screens (About, the save slots, the CG and Replay tiles and tabs, Search's rows, the CG counts, the glossary) goes through named styles (`textstyles.tjs`, `KAGDefineTextStyle`, `KAGDrawStyledText`): size, weight, colour, alignment, lines, shrinking to fit, outline, shadow and gradient. The sample ships a second message font, Noto Serif JP cut down to its own characters (`tools/assets/make_fonts.py`).
- **An outline with a shadow, and gradient text**: with `edgeWithShadow` (on in the sample and the template) a message window draws the shadow of the outlined text, then the outline, then the text, where KAG3 drew one or the other; `[selopt edgewithshadow=]` for the choices. `[font gradcolor= edgegradcolor= shadowgradcolor= graddir=]` (and `[deffont]`, `[selopt]`, a text style) shade the text, its outline and its shadow from their colour to another, down the line or along it.
- **Text settings for the player, with a preview**: Config's new Text page (the sample's seventh) has the message font, an outline and a shadow with their colours, and the read text's colour, beside a small message window that types sample lines in the chosen look at the player's speed. The player's outline and shadow take the place of the game's defaults (a scenario's own `[font edge=]` still wins), and the page on the screen is drawn again in them at once (`TextSettings.tjs`).
- **A colour picker**: a wheel, a brightness bar, the colour before and now, by mouse, touch, keys or a controller (`KAGPickColor`); options of kind `color`, and `Other…` on a choice of colours (the read text's colour now has one).
- **Message window styles per scene, in colours the player picks**: `[env msgstyle=<name>]` gives the message window and its name box another frame and tint for a scene (`KAGDefineMessageStyle`; kept in saves, Back and compiled scenes, and on a page drawn again); a style with a label has a row on Config where the player keeps it as drawn or tints it. The Character demo's flashback has a sepia window between letterbox bars (`[memory]`, `[memoryend]`).
- **A glossary of terms marked in the text**: `terms.csv` (a language's own in `lang/<code>/`) names the words the story explains; where the message window draws one it's in the glossary's colour and underlined, and a click or a tap shows its entry as a card without going on. The marks follow the text as drawn, so compiled scenes, translations, a page drawn again in another language and the backlog are marked; Config turns them off or picks their colour. The sample marks KAGEX, the World and Pip, and its Extras has a fifth tab, Glossary, listing the terms met (`Glossary.tjs`, `glossary.ks`).
- **Face windows for Live2D and VRM characters**: a model character's `faceCrop` (in its picture at 100%, or fractions of it) is cut from the picture it has just drawn, and while it's the speaker the window follows the model a few times a second, so its blinks and its mouth show there too. Vee and Hiyori have one.
- **kagex-release: web file names with `%`, `#` or `?`**: `check` lists them for a web build of loose files, which the web engine can't fetch ("xp3" web data avoids it).

### Fixed

- **A `[font]` at the start of a line was lost in a line mode**: the page is cleared as a line's first character comes (the `dispname` tag, KAG's and the World's), and the clear reset the font, so `[font color=...]` or a gradient given before the line's text never showed. A `[font]` given since the last character drawn is now kept through that clear (`kag.clearForLine`).
- **A word in a larger size broke in the middle**: after `[font size=]` in the middle of a line the word wrap measured the next words in the old size (the new one takes effect as a character is drawn), so a large word at the end of a line was split by KAG's character wrap. The size is settled before the words are measured, and a word measured before a font change is measured again in the new font.

### Changed

- The Extras tabs are narrower, to fit a fifth; the Japanese label fonts were cut again for its label.
- `showTextDialog(lines)` shows lines of text in the About screen's frame (the glossary's cards); the framework's text styles add `dialog.text`, a paragraph.
- kagex-release's README says it needs a vcpkg clone (Visual Studio's own vcpkg refuses a manifest without a baseline).

## 0.21.1

### Fixed

- **Q.SAVE no longer shows an error after saving**: the sample's quick save (Q.SAVE on the message window, Shift+S and whatever the player binds to it) saved, then read a global left over from an older notice that no script defines, and TJS refuses a missing member even when it's asked for through `global.`, so every quick save ended with "Member "qsavenotify_object" does not exist". The leftover is gone, and the smoke test makes one of its quick saves through the game's own Q.SAVE action rather than `kag.quickSave()` alone.

## 0.21.0

### Added

- **Save and load in one click from the quick menu**: a right-click or a long press on SAVE opens a panel with a new save in the first empty slot (made at once, with the card a quick save shows) and the newest saves to write over (after asking); on LOAD, the newest saves to load. The wheel over a panel moves the slider under the pointer, or its first (the volume panel's: the music), a twentieth of its range a notch (`QuickPanels.tjs`; `KAGWindow.recentBookMarks`, by the time each was saved, `firstFreeBookMark`, `saveIntoBookMark`).
- **The save and load screens scroll**: all 90 slots in one list two across, scrolled with the wheel, by dragging and flicks, with the bar, the keys or the D-pad, as the Extras lists do, in place of nine pages of ten; the page buttons scroll to their ten (`slotList` in `Override.tjs`).
- **Continue shows the save**: the title's offer to carry on shows the save as a card with its picture, scene and date above the prompt (`showYesNoCard`'s `stay` and `place`).
- **System buttons that fade**: `[position buttonsfade=<ms> buttonsarea=x,y,w,h]` fades a message window's own `[sysbutton]`s out while the pointer is away and back as it comes near, at a touch, or as the keys move to one, for games that keep them rather than the quick menu; kept in saves (`doc/kagex.txt`).
- **Android's Back and a phone browser's Back are the game's Esc**: they close the history, a panel, a prompt or a system screen, and on the sample's title ask whether to quit (also Esc and the right button there). On Android a patch to the kit's activity (applied in CI, so the engine packages for kagex-release carry it) turns Back into Escape; before, the engine got a key it has no name for, and since Android 13 Back left the game. In a phone's browser the page hands Back to the game while there's something for Esc to do, and leaves the page as before at the title (`kagex-web.js`, `KAGWebBack`; `UPSTREAM.md` 46).
- **"Games on Phones and in the Browser"** in `doc/kagex.txt`: the fixed 1920x1080 surface, what stands in for the keys and the right button, movies' sound files on Android, the app's look. On Android and iOS the framework warns at start when the game's screen isn't 1920x1080 (`UPSTREAM.md` 48).

### Changed

- **The quick menu has no pin**: whether the strip stays or fades until the pointer comes near is Config's Quick Menu option alone (Always, or Near the Pointer). On a phone the pin was easy to hit and looked as if it did nothing: a finger resting on it counted as a mouse that stayed near, so on an Android phone the strip never went, and elsewhere it stayed four seconds. With Near the Pointer on Android and iOS the pointer is always a finger's now, so a tap on the handle brings the strip for a few seconds and it goes again. The smoke test taps the handle on the Android emulator with real taps (`adb shell input tap`).
- **The history scrolls by the pixel**: both the sample's history and the framework's draw their text on a layer of their own, cut at the text area's edges, so a drag or a flick moves them smoothly rather than a line at a time; the framework's could not be dragged at all before. The sample's tips name every button of its column.

### Fixed

- **The history couldn't be closed on a phone**: the sample's had no close button (it closed on a right-click, Esc or turning the wheel past the newest line, none of which a phone has). It has one at the top of its button column now, both histories close when the newest line is pulled up past the end (a note says "Let go to close"), and Back closes them (above). The smoke test leaves every screen with taps alone (the history, Config, save, load, a prompt, About, the controls lists, the controller test, a quick menu panel), on every platform.
- **Movies were silent on Android phones**: the engine's Android player flushes a movie's audio decoder as it starts the movie, before the decoder's first output, which Android documents can lose the codec's header (`UPSTREAM.md` 45); the emulator's decoder keeps it, so CI never heard it. On Android a movie with `<name>.opus` or `<name>.ogg` beside it now plays muted with that file alongside, started with its first frame and kept in step with the picture (`KAGMovieSoundFile`, `KAGMovieSoundPlatforms`); the sample's opening has `opening.opus` (`make_opening.py`, the movie's own sound copied out). The smoke test checks it on Android.
- **A movie after a skipped one didn't play**: KAG's `[openvideo]` and `[playvideo]` give a slot that played and was stopped a new movie object with the old one's settings first, since the engine's leaves a frame flag set after a stop mid-frame and its next movie never sent `perPrepare` (`KAGWindow.renewMovie`; `UPSTREAM.md` 47).
- **Android's strip below the game was white**: the window stops above the navigation bar, and the strip there showed the light theme's background. The sample's resource override and every game kagex-release builds give the theme a black window and navigation bar.
- **A card's picture smaller than the card**: a save's thumbnail on a card was shrunk with a shrinking copy that refuses to enlarge, so the card wasn't made; it's stretched now.
- **A movie in a KAG layer left the layer at the movie's size**: the engine sizes a layer to each frame a movie draws there, and KAGEX's layers keep their own picture the size of the screen and draw into it, so an effect or a flip shown on that layer after the movie was cut off at the movie's size (an Effekseer effect after a 960x540 movie threw "Out of Rectangle" when read). A movie in layer mode gives its layers their size back when it stops (`Movie.putLayersBack`).
- **Rewind on the web stopped a message short**: after each step back the player's history ends before the message it went to until that message has been played, which in the browser waits for its pictures to download, and the step after that, landing in between, took the rewind for done. Each step waits for its message now.
- **A flick on the history went on after the player scrolled**: a coast kept moving the history after a button, a key or the wheel moved it; a scroll of the player's own ends it now, in both histories.

## 0.20.0

### Added

- **Panels on the quick menu's buttons**: a right-click or a long press on a button with a panel (or, as Config's new Quick Menu Panels says, the pointer resting on it) opens a small panel over the scene: the volumes with a switch for all sound, the text's settings (text and auto speed, what skip skips, the window's opacity), or the newest quick saves with their pictures, which load after asking. Keys, the D-pad and screen readers work them, and a click outside closes one without going on to the next text (`QuickPanels.tjs`; the sample's Auto, Q.LOAD and Config have them). The quick menu's buttons are given to screen readers beside the message or the choices, and an unpinned strip peeks out for a moment as it can show again.
- **A long press, the mouse's side buttons, and the quick menu's order**: a finger held still on the story runs a gesture of its own (`kag.gestureActions.hold`; the sample's turns auto mode on or off) and makes no click, and over a button it shows the button's tip above the finger while it's held. The mouse's back and forward buttons go back a line and on to the next text (a new action, "Go on"), and Change Controls takes them as keys. Change Controls' new arrows move a quick menu button earlier or later in the strip, kept for the player, and Reset puts the game's order back.
- **Help lines, and tips for every setting**: Config, the save and load screens and Extras say at their bottom what the pointer or the focus is on, or what the screen is for, from the game's `helptexts.csv` (by screen and button name, translated through `lang.json`) and every option's line of help (`KAGOptionHelpTexts`), which Config's rows also show as tips; buttons take `help=` (`kag.tooltips.helpArea`, `doc/kagex.txt`, "Tips").
- **Extras scroll**: the CG and Replay tiles are grids and the music room's tracks a list, which scroll with the wheel, by dragging (a flick coasts), with their bars and the keys or a controller, as Search's lines do, in place of pages of sixteen tiles and twelve track buttons; a tab remembers where it was scrolled to.
- **Cards after a quick save and a screenshot**: the notice shows the save's picture, the scene and the date, or the screenshot and its file's name, where it was words alone (`showYesNoCard`). The sample's quick menu has a screenshot button.
- **Skipping says what it did**: the mark at the top right (it was at the bottom right, where the quick menu is now) says for two seconds that skipping started, read text only or all, and why it stopped: unread text, a choice, or the player.
- **The movie volume's sample**: Config's Movie Volume plays a sample as it's pointed at and moved, at the volume the slider shows, with the game's music paused meanwhile, as the other volumes do (`KAGVolumeSamples.movieStorage`; the sample's is the opening's song).

### Changed

- **The quick menu along the bottom of the message window, as icons**: the sample's strip of buttons sat on the window's top edge and, at the larger size phones start with, ran past the window's end. It now sits along the bottom of the window's panel at its right, inside it at both sizes, and most of its buttons are icons (the scene before, the last choice, rewind, back a line, auto, skip, the next scene, the message history, Config; their tips name them), with Q.SAVE, Q.LOAD, SAVE and LOAD still words: the strip is 950 px wide where it was 1452. The window's text keeps four lines above it (`[initscene]`'s margins). The quick menu's `place` function is given the strip's width and height (`doc/kagex.txt`, "The Quick Menu").

### Fixed

- **A swipe on a phone also went on to the next text**: KAG clicks at a press, so a swipe's press had gone on to the next text before the swipe was one (SDL and the engine send the mouse events a touch makes before the touch's own; in a browser all of a touch's come after its click). On a touch screen, in the story, the press's click is held until the release now: a tap clicks then, a swipe runs its gesture and makes no click, and a drag a swipe's length that took too long for a gesture is neither (`kag.gestures.holdClick`, `releaseClick`; `holdClicks` says whether, void for "on a touch screen"). And in a browser the engine looked for a touch screen only as the window was made, before the page's first touch told it of one, so it sent the game no touches at all: the window asks again at a press until it does (`Window.enableTouch`). The smoke test holds a press and swipes, taps and drags slowly, and with `--target web --touch` swipes and taps with Chrome's touch events.
- **The quick menu's pin on phones did nothing**: a tap leaves the pointer resting where the finger was, so with the strip unpinned a tap on its pin left the pointer "near" it and it never faded, and a tap on its handle brought it back for good. After a touch the resting pointer doesn't count, and a tap on the strip or its handle brings it for four seconds (`touchHideDelay`), after which it fades to its handle.
- **Reduce Motion's stills when it's turned off, and on**: a layer showing its `still=` picture kept it until it was drawn again, and an `.asd` animation stilled on its first frame started again only when it was loaded again (the click glyph at its next wait). Now the effect or movie and its still take turns as the option changes, and animations stop on their frame or go on at once; a save keeps the flip a still stands for.
- **The Effects demo's static over the quick menu**: the strip was stacked over every message window (`absolute` 3500000), so the static the demo draws over the message window (`level=message`) went under its buttons. It stacks just over the first message window now (`absolute` void), under a World layer at `level=message` and the next window.

## 0.19.0

### Added

- **One table of actions, keys the player can change, and gestures**: skip, auto mode, the message history, hiding the window, going back, save and load, quick save and load, playing the voice again, the scene moves of compiled scenes, the next language, the menu and a screenshot are actions (`Actions.tjs`), and keys (`kag.bindKey(key, shift, "@name")`), controller buttons (`kag.padKeyMap[button] = "@name"`) and gestures point into them, so the controls list reads them and a game changes one in one place (`KAGDefineAction`, `KAGActions.quickSave.func`). Change Controls (the controls list's Change… button) lets the player give each action a key or a controller button, or none, and a gesture, kept in the system variables over the game's, with Reset. In the story a swipe on a phone, or a drag with the right mouse button, runs an action and drops the click it would make: up the message history, down hides the window, and in the sample left rewinds and right skips (`doc/kagex.txt`, "Actions, Rebinding and Gestures"). The smoke test swipes, binds a key through Change Controls and resets.
- **A quick menu that keeps out of the way**: a strip of buttons for actions (`QuickMenu.tjs`), shown all the time or fading in when the pointer comes near (a tap on its handle on a phone), with buttons dimmed while their action can't be done and lit while their toggle is on, a pin, and Config's Quick Menu option. The sample's message window buttons are its quick menu now, in the same place with the same pictures, so they follow the actions: a key the player moves, the sample's own save screen behind Save, Voice Replay and the rest. The player can make it larger (as it starts on Android and iOS), fainter, or leave buttons out (`doc/kagex.txt`, "The Quick Menu"); the sample's Config has a sixth page for it and the tips.
- **Tips**: a button's hint (`[button hint=]`, `[link hint=]`, a layer's hint), which the SDL engine's window never showed, appears beside the pointer resting on it, or at once under it when the keys or a controller move the focus there, in the dialogs' look and through `tr()`; a screen with a help line of its own can take them there (`kag.tooltips.helpLine`), and Config's Tips switch turns them off (off at first on phones). The quick menu's buttons tell their actions, and the sample's Config tabs what each page holds (`Tooltips.tjs`, `doc/kagex.txt`, "Tips").
- **Scrolling lists**: a list or grid of items the game draws one at a time, only while in view (`ScrollList.tjs`, `KAGScrollList`), that scrolls with the wheel, by dragging with the mouse or a finger (a flick coasts on and slows down; a finger that stopped before it lifted, judged against the drag's own pace, makes none), with its scroll bar and with the keys or a controller's D-pad, picks an item on a click, a tap or Return, and gives the items in view to screen readers; on a message layer it's one of the links (`addLinkLayer`), so the keys move to it from the buttons and `[backlay]` copies it. The sample's Search shows what it finds in one instead of pages of seven, kept where it was while a line plays, and its backlog coasts after a flick (`doc/kagex.txt`, "Scrolling Lists"). The smoke test scrolls Search's list with the wheel, a flick and the keys, and flicks the backlog.
- **The screen, the controller and screenshots in Config**: the window's size (the sizes that fit the screen), how full screen fills a screen of another shape (black bars, filled with the edges cut, or stretched), smooth or sharp scaling, vertical sync, the controller on or off and a controller test whose picture of the pad lights each button while it's held (`Display.tjs`, `PadTest.tjs`; the controls list has a Test Controller button too); screenshots with the message window or without, PNG or JPEG, and for the game a name pattern with the date and time and a watermark (`kag.screenshotName`, `kag.screenshotWatermark`); and `[screenshot enabled=false]` turns them off for a scene with spoilers, kept in saves (`doc/kagex.txt`, "The Screen, the Controller and Screenshots"). The sample has them on Config's sixth page.
- **Reduce Motion stills actions and `.asd` animations**: with it on, every action ends where it would end on the next frame (a looping one stops), and `.asd` animations, the click glyphs among them, stay on their first frame (`kag.reduceMotionActions`, a layer's `animReduceMotion`).
- **A movie volume of its own**: where a game keeps movies' volume apart from the music's (`kag.independentMovieAudioProperty`), Config's Movie Volume sets it; the sample does, on Config's fifth page.
- **Hover sounds on the engine-drawn screens**: the pointer on a button of the controls list, Change Controls and the other Elements screens plays the interface sound table's `<screen>.<button>.enter`, as on the game's own screens.

### Fixed

- **`[ai far]` and `[ai near]` with an angry or sad face**: Ai's angry and sad pictures were drawn at the middle size only, so after `[ai 103]` the far and near presets showed the picture before in the far or near place (her head above the screen, or her almost wholly below it). A character whose picture is missing at a level is now drawn from the nearest level that has it, a bigger one first, scaled by the levels' zoom, with a note in the log (`KAGEnvCharacter.drawOtherLevel`, `doc/world_inst.txt`); and the sample has the far and near pictures (`ch_1_0_2`, `ch_1_0_3`, `ch_2_0_2`, `ch_2_0_3`, made by `upscale.py` from the middle ones). The smoke test checks every face at every level, and a level without pictures.
- **A screen opened during the title's crossfade**: the title draws itself again with a 300 ms crossfade (after a language switch, or coming back to it), and its old page's buttons still work meanwhile; Config pressed then stopped at its `[wt]` for good, and a Config tab turned while the screen was drawn again for a language switch failed the same way. A jump (`kag.process`, which buttons and tabs go through) now ends a transition still running first, as a click during `[wt]` does, and a `[trans]` the engine refuses (its layer still in a transition) takes back its count instead of leaving `[wt]` waiting, with a note in the log (`KAGWindow.process`, `KAGTransMove.beginTransition`). The smoke test presses Config during the crossfade, at both Effect Speeds.

## 0.18.1

### Fixed

- **rgbfade, zoomfade and spin**: extNagano's, as krkrz_dev rebuilt them, didn't work as they say (`UPSTREAM.md` 42): rgbfade's colours each took the shortest one's time, so red was done at a quarter of the transition and the picture flashed through solid colours, and on a whole scene it drew solid colours (the demo ran it on KAG layer 0 for that); zoomfade sampled the nearest pixel and, by default, didn't zoom a picture that goes; and spin showed the new picture as a flat panel growing from the middle with a gap in it, while the old one didn't turn. kagex now draws all three itself, as it has book and multiripple since 0.18.0 (`ScriptTransitions.tjs`): rgbfade's colours start at their delays and end together, each the old picture over what's behind turning into the new one (a multiplying and an adding layer), so it works on the World's pictures too; zoomfade grows the old picture and shrinks the new one smoothly; and spin turns the pictures as the faces of a box (types 0 and 1) or as doors (4 to 7), in perspective. These five no longer need the plugin, and the transitions demo runs rgbfade on the event picture and gives zoomfade's picture its zoom (`zoom1=200`). The smoke test runs each of them from an empty layer to its end.
- **Face windows keep the character's own colours**: the sample's faces by the message window took the lighting and colour effects of the character's sprite (night's blue, a flashback's grey), since its `envinit.tjs` set `faceApplyColor`; it doesn't now, so a face shows the pose, outfit and expression in its own colours (`doc/world.txt`, "Face Windows").
- **The voice bar fills from the left**: 0.17.0's bar on the message window followed the engine's playing position, which now and then reads another part of the voice (`UPSTREAM.md`), so it jumped back and forth; it now fills smoothly from the left by the time since the voice started (times its speed), starting over with the next voice. The smoke test samples it while a line plays and wants it to only grow.
- **Typing on phones**: the engine opens a phone's keyboard only for its own text boxes, so the name screen's and Search's fields took no text on Android, nor in a phone's browser. On Android and iOS (without a keyboard plugged in) a tap on an `[edit]` field now opens a box at the top of the screen, above the keyboard, with the field's text: what's typed shows in the field, OK or Enter keeps it and runs `enter=`, Cancel or Back puts back what was there; its title is the field's new `prompt=` (`TextEntry.tjs`, `KAGTextEntryMode`). In a phone's or tablet's browser the page's script (`kagex-web.js`) gives a hidden field of its own the keyboard as the tap ends and hands what's typed to the game, and full screen there is the whole page's, since a browser lets nothing outside the full-screen canvas have the keyboard. The smoke test types into the name screen through the box, and with `--target web --touch` (the Pages site's run after each deploy) as a phone's browser (`doc/kagex.txt`, "Typing on Phones").
- **The opening's first frame on Android**: it glitched for a frame as it started on a phone, whose decoder can change its picture format as its first frame comes out; on Android a movie's first two frames aren't shown now (`KAGMovieHideFirst` in `GFX_Movie.tjs`, 66 ms of the backdrop).

## 0.18.0

### Added

- **Faces by the message window that follow the speaker**: each line's speaker shows their face beside the text, cut from their sprite as it looks now (pose, outfit, expression, the time of day's colour), crossfading to the next speaker's; narration and lines over an event CG have none, a character who isn't on stage can speak as a face only (`[pip facewin]`), `[env facewindow=off]` turns them off for a scene, and Config's Face Window for good. A character's `faceCrop` in `envinit.tjs` says which part of its sprite is its face, for characters from pictures and from layers alike; the sample shows Ai's and Pip's, and the Character demo has a Faces scene (`doc/world.txt`, "Face Windows").
- **Characters that make room for each other**: `[pip join]` brings a character on at the right (`join=left`, `join=middle`) while those already on the stage slide over so everyone stands evenly spaced, `[ai leave]` takes one off and the others close the gap, `[env layout]` spaces them again and `[env makeroom=0]` pushes them apart around a spot; the places for one to four characters, a level per count and the sliding time are `envinit.tjs`'s `"layouts"`. The Character demo has a Making Room scene (`doc/world.txt`, "Layouts").
- **Keep a scene and come back to it**: `[env keep]` puts the whole scene away (stage, characters, layers, camera, colour, and with `sound=true` the sounds), and `[env restore]` brings it back exactly while the music plays on, for flashbacks and phone screens; `keep=<name>` and `restore=<name>` keep named copies until `[env drop=<name>]`. Saves, Back and compiled scenes keep the copies. The Character demo has a flashback in grey (`doc/world.txt`, "Keeping a Scene").
- **A staging kit in the sample**: twenty gestures, a word each (`[ai nod]`, `headshake`, `sigh`, `laugh`, `shrug`, `lookaround`, `wobble`, `slump`, `startle`, `tremble`, `bounce`, `leanin`, `stepback`, `sway`, `stomp`, `pop`, `tilt`, `giggle`, `faint` and `nods`), screen shakes (`[quake]`, `[thud]`, `[rumble]`), a close-up that blurs the background (`[closeup]`, `[closeupend]`), a veil for inner thoughts (`[dim]`, `[whiten]`, `[undim]`) and an eyecatch card with Pip that a click skips (`[eyecatch]`), with a Staging Kit scene in the Character demo that plays each with its name (`doc/world.txt`, "The Sample's Staging Kit").
- **Reduce Motion**: a Config switch that stops demanding animation, for slow machines, batteries and players bothered by motion. Looping Effekseer effects show nothing and ones played once end at once, looping layer movies pause, and the TV static, Live2D and 3D layers stop on the frame they show, moving again when it's turned off; an `[image]` or a World layer can name `still=` a picture to show in their place. The Effects demo has stills for its looping effects, put together by `make_effects.py stills` (`doc/kagex.txt`, "Reduce Motion").
- **Moving through the story by scenes and choices**: compiled scenes can go back to the start of the scene (or the one before), rewind a message at a time to it or the last choice (a click stops it), offer the last choice again, and skip on to the next scene (stopping at unread text or a choice, as skipping does); the sample has a button for each by the message window's others. "Skip Read Text on Reaching It" in Config can now Ask: going into a scene read before offers to skip it (`doc/scn.txt`, "Going back").
- **A backlog with faces, previews and scene buttons**: in compiled scenes the sample's backlog shows each speaker's face beside their lines, a picture of the scene as it was while the pointer rests on a message's going-back mark, and buttons to the previous and next scene or choice; dragging it scrolls it on touch screens (`doc/scn.txt`, "Going back").
- **A CG viewer with zoom, pan and pinch**: the sample's CG screen shows a CG full screen in a viewer of its own: the wheel, the bar's − and + buttons, the + and − keys or a pinch zoom it about the point under the pointer, dragging, the arrow keys or the stick move it, the bar's arrows, Page Up and Down or a click step through its variations with a counter, and the bar fades when the pointer rests. The window passes a pinch (the engine's `onTouchScaling`) to `onTouchScalingHook` hooks.
- **Loudness correction**: `loudness.csv` evens out levels without re-recording: a gain in dB per kind of sound (`bgm`, `se`, `voice`, one speaker's `voice:<name>`) or per file, applied as each Ogg Vorbis or Opus file is decoded, so a quiet voice can be raised past 100%. The sample's table brings its synthesized voices up to the others and puts the music under the voices (`doc/kagex.txt`, "Loudness").
- **One table for every interface sound**: every button, page turn, slider, prompt, choice, menu item and the backlog can play its sound from `uisounds.csv`, which names a sound for each tag (`<screen>.<part>.<event>`, such as `title.start.click`, `config.page2.click`, `dialog.no.click`, `menu.open`), with `*` for whole groups (`*.click`, `save.page*.click`) and `@aliases`, so changing the click for the whole game is one line; a button's own `clickse=` and the like still come first. A hover sound right after another sound is left out (a screen redrawn under the pointer), and in debug mode two sounds started within 20 ms are logged with where each came from (usually one sound played twice). Sliders' and check boxes' `changese=` now also plays with `onchangefunc=`. The sample's screens, prompts, choices, backlog, CG viewer and menus had no sounds; they get soft ones from `tools/assets/make_sounds.py` (`doc/kagex.txt`, "Interface Sounds").
- **Hear a setting while changing it, and undo it**: on Config, pointing at the music's volume or moving it plays a few seconds of music at that volume when the game is playing none, letting go of the sound's volume plays a sound, and letting go of the voices' plays a character's line; a fifth page has a volume and a Test button for each character (Ai, Pip, Hiyori and Vee, whose voices now each have their own switch on page 1); and Undo takes back the last change, Revert everything since Config opened. Framework: sliders take `previewfunc=` (called as they're pointed at, moved, let go and left), options take `preview` and `test` and a label by language, the volumes and page-one settings are options (`bgmVolume`, `seVolume`, `voiceVolume`, `textSpeed`, `autoModeSpeed`, `noEffect`, `allSkip`, and `volumeSamples` to turn the samples off), `KAGDefineVoiceOptions` makes a character's volume and on/off from envinit.tjs (`testVoices` names their test lines), `KAGVolumeSamples` plays the samples and `KAGOptionUndo` keeps the steps (`doc/kagex.txt`, "Options and the Config Screen"). Sliders' and check boxes' `changese=` no longer plays when a screen is drawn again.
- **Credits timed to two places in the song**: the credits roll takes `rollfrom=` and `rollto=`, each a time in ms or a label in the loop file (`.sli`) of the music playing: it waits for the music to reach the first and ends as it reaches the second, for a song with an intro or a reprise. The sample's Credits demo rolls from 6 s into bgm01, after the opening bars, to 84.55 s, where the closing chords begin, and fades the chords out after (`doc/kagex.txt`, "Optional parameters for roll"). Prefer times: music with labels can hang the engine now and then (`UPSTREAM.md` 44), which the sample's did in testing, so its `bgm01.ogg.sli` is gone.
- **Alpha movies on Android, iOS and the web**: the AlphaMovie plugin (`.amv` movies with transparency, the `amv` flip type in `GFX_AMovie.tjs`) is built into those engines too (`app-config.json`, `ios-config.json`, `web-plugins.py`), as it was into the Windows, Linux and macOS ones, and the platforms' smoke tests insist on it (`--alphamovie required`).

### Fixed

- **Movies play on the web**: the browser build's movie player asked the site for a movie inside `gamedata/data.xp3` by a URL made from its archive path, which the server doesn't have (`UPSTREAM.md` 41), so the sample's web demo never showed its opening, nor the layer demo's movie: `[movie]` ended them after 3 s. The framework now copies such a movie out of its archive into the page's memory before it opens (`KAGMovieOpenable` in `Utils.tjs`, for `[movie]`, `[image movie=]` and KAG's `[video]`), and the web smoke test insists on a picture there.
- **The book and multiripple transitions**: extNagano's, as krkrz_dev rebuilt them, didn't do what they say (`UPSTREAM.md` 42): book's page stopped three quarters of the way across and the rest of the old picture vanished in its last frame, and multiripple's ripples brought the old picture back halfway and ended with a jump. kagex now draws both itself (`ScriptTransitions.tjs`, hooked in `KAGLayer.beginTransition`): the page turns all the way, shaded as it turns, the ripples spread until they cover the screen at the transition's end, with wave rings riding on them, and both keep each picture's transparency, so a picture coming or going over the World's stage turns or ripples over the stage rather than over a blank. They take the plugin's attributes, end at a click or `[stoptrans]` as before, and need no plugin; `KAGScriptTransitions` lists them, and a game can add its own (`doc/kagex.txt`, "trans"). The sample's 3duniversal gives the old picture's pieces a speed (`accel1=0.4`): without one they stay put and the plugin fades the new picture out. The smoke test runs both, from an empty layer (which an affine layer reports as 32x32) and stopped halfway.
- **English words in the Japanese backlog**: the backlog wraps Japanese a character at a time, and an English word in a Japanese line (`krkrlive2d`, `efkwidth`) could be cut across two lines, which 0.18.0's faces beside the lines made happen in the sample; such a word, with an opening bracket before it, now goes to the next line whole (`KAGHistoryCarryWord` in `HistoryLayer.tjs`, used by the sample's backlog too), as the message window already did. The release's package test caught it.

## 0.17.2

### Changed

- **A new opening for the sample**: the logo plays an opening movie of the sample's own, drawn by `tools/assets/make_opening.py`: the K badge and the wordmark, the street with Ai coming in, three pictures from the demos and the evening title, over the start of "Daily Life" (`bgm01`), which it unlocks in the music room. It's an ordinary WebM without alpha (1920x1080, 3.4 MB, with a 960x540 version for the web and phones) with English and Japanese subtitles, and Replay's Movies tab shows a picture of it. The test movie it replaced stays in the layer demo, whose alpha movie it is.

### Fixed

- **Movies fill the screen**: the smaller version of a movie that the web and phones play (`<name>_sd`) showed at its own size, in the middle of a black screen. `[movie]` now zooms a movie of another size so it fills the screen, keeping its shape (`fit=false` shows it at its own size), and `[image movie=... fit=true]` does the same on any layer. The smaller version also uses the full movie's subtitles when it has none of its own.
- **A movie no longer hangs the game on a computer without a sound device**: there the engine can't start a movie's audio and holds a movie with sound at its first frame for ever (`UPSTREAM.md` 40), so the new opening, which has music, would have hung the game at the logo. `[movie]` now ends a movie whose picture stops for 3 seconds, as it already ended one that showed no picture.
- The smoke test's movie checks accept a movie that shows no picture on the web, where the browser's player can't open a movie inside `data.xp3` (`TODO.md`, "Movies on the web").

## 0.17.1

### Fixed

- **Android: the game no longer hangs after the opening movie**: Android's movie player hangs when a movie that has run to its end is stopped (`UPSTREAM.md` 38), so 0.17.0's `[movie]` stopped its movie 300 ms before the end, going by the movie's position. On a slow phone or emulator the position lags behind the decoder, which can reach the end first, and 0.17.0's sample could hang at start-up after the logo's opening. The movie is now also stopped by the time since it started, which a movie can't outrun (checked on the Android emulator: the opening stopped while it played, 4.97 s into its 5 s).
- **Android: saving no longer crashes the game**: 0.17.0's fix for the shrinkCopy plugin reading past the picture it shrinks (a save's thumbnail) added a row under the copy it shrinks, but the plugin also reads the column right of the last one, which for the bottom right pixel lies past that row, and 0.17.0's Android game still crashed on a quick save. The copy has a column and two rows more now (`UPSTREAM.md` 39); a thumbnail's last column changes a little, since the plugin had blended it with the picture's other side.
- **Movies show instead of a black screen**: `[movie]`'s backdrop (`color=`, which the logo's opening and Replay's Movies tab use) was made over the base layer that KAG's layers and the message windows are on, so it covered the movie, and the movie played behind a black screen with only its subtitles over it. The backdrop is beside the movie's layer now, just under it, and the smoke test checks the screen while a movie plays.
- **A movie's layer goes back under the message window**: `[movie]` plays its movie over everything on a KAG layer (the last one, unless `layer=`), and 0.17.0 left that layer there after the movie, so whatever the game showed on it later covered the message window: after the logo's opening, the layer demo's Vee stood over the text. The layer goes back to its place after the movie, and a save made in 0.17.0 that kept the layer there has it put back when it's loaded.
- The smoke test waits up to 60 s for Vee's one-shot motions, which a slow iOS Simulator took longer than 10 s to play.

## 0.17.0

### Added

- **Settings declared once, and Config pages from them**: the player's settings are a table (`template/system/Options.tjs`): an option has a name, a label (shown through `tr()`), a kind (toggle, choice, slider, button or note), the property or functions it reads and sets and its first value, and a Config screen lays its rows out from the table, so a game adds a setting with `KAGDefineOption` in `AfterInit.tjs` without placing buttons, and Default and saving follow from it (`KAGOptionGet`, `KAGOptionSet`, `KAGResetOptions`, `KAGOptionPage`; `doc/kagex.txt`, "Options and the Config Screen"). The sample's Config has four pages now, with tabs: the first as before, then Voices and Saves, Reading, and Screen and Extras.
- **Reading settings**: the message window's opacity (and a name box that follows it), a colour for text already read and a different click mark after it, text that fades in over a time the player picks, the read-text speed and a text speed of auto mode's own, auto waits that grow with the line, a pause after a voice before auto mode goes on, a dramatic mode in which a voiced line hides the message window while its voice plays (in auto mode, or always), hiding the pointer when it's still (desktops), keeping auto mode or skipping on after a choice, and skipping read text on reaching it (`doc/kagex.txt`, "Reading Settings").
- **"Don't ask again"**: the prompts before overwriting or loading a save, a quick load and returning to the title have a check box; a Yes with it ticked answers that prompt from then on, and Config's Ask Again brings them back.
- **A name box that fits, fades and follows the window**: `[position namefit=squeeze]` draws a name too wide for its box narrower (`shrink`: smaller), `namemargin=` keeps room at its sides, `namefade=` crossfades from one speaker's name to the next and fades the box in and out, and `followopacity=true` makes the box as transparent as the window (`doc/kagex.txt`, "The Name Box").
- **On-screen indicators**: a chapter's title in a corner (`[chapter title="Chapter 1"]`, kept in saves; the sample shows each compiled scene's title as it starts), the music's title when it changes (from `musiclist.csv`), a mark while auto mode or skipping is on, and a bar under the message window for the voice left; Config turns each off (`template/system/Indicators.tjs`; `doc/kagex.txt`, "On-screen Indicators").
- **Naming the hero**: `kag.setHeroName(given, family)` takes the player's names, trimmed, refusing ones too long or holding a word the game lists (`heroNameRefused`, `heroNameCheck`), `kag.heroName()` gives them back, and a character whose `nameAlias` is `"&kag.heroName()"` and `[emb exp="kag.heroName()"]` show them, in compiled scenes, the backlog and Search too. The sample asks the first time START is chosen, and Config's last page has Change (`doc/kagex.txt`, "The Hero's Name").
- **Writers' shorthands**: `envinit.tjs`'s `"shorthands"` turn a word of a character's tag into a pose and a face, through each character's `poseCodes` and `faceCodes`, so `[ai 102]` is pose 1 and face 02; and a position can bring a character to the front of its level or send it back (`"front"`, `"back"`), as the sample's `far` and `near` do at once with the level (`doc/world.txt`, "Writers' Shorthands").
- **Voice files that find their speaker**: `[vo ai000003]` plays the files of the recording script on the next line, and works out whose they are from the characters' `voiceFile` patterns, as if the line began with `【ai】`; compiled scenes do the same (`doc/world.txt`, "Voice Files That Find Their Speaker").
- **A credits roll**: the `roll` flip type scrolls a staff list from a text file (headings, gaps, sizes, pictures beside the text) over the rest of the music playing or a time of its own, drawing only the lines in view; it sends `rollend` at its end, notes that it was seen (so a scenario lets a click skip it only then) and keeps its place in a save (`template/system/GFX_Roll.tjs`; `doc/kagex.txt`, "Optional parameters for roll"). The demo menu has Credits.
- **Movies as commercial games handle them**: `[movie storage=opening alpha=2 song=bgm02 color=0x000000]` plays a movie over the game and waits for it; it can't be skipped until it has been seen (`skip=always` lets it), skip mode stops before a movie not seen yet and passes a seen one, the right button skips a seen one, `song=` unlocks the music it plays in the music room, `color=` fills the screen behind it, and a smaller version (`<name>_sd`) plays on the web and phones or when the player picks it; Config has switches for each. The sample's logo plays the test movie as a short opening, and Replay has a Movies tab (`template/system/Movies.tjs`; `doc/kagex.txt`, "Movies").
- **Subtitles for movies**: a movie shows the cues of `<name>.vtt` (WebVTT; a language's own in `data/lang/<code>/`) at the bottom of the screen, timed from the movie, and screen readers get each one; Config turns them off.
- **Extras touches**: each CG page shows how many of its pictures were found, and the screen all of them ("Found: 1/3"); Extras opens on the tab last used; a track chosen in the music room plays on through the CG and Replay screens, with its title and a Stop button there, and Keep on Title makes it the title's music; finishing every demo unlocks an evening title picture, picked with arrows on the title.
- **kagex-release: additions to the Android manifest**: the app's manifest gets the query that lets it see the system's text-to-speech engines (`platforms.android.ttsQuery`, on by default: apps for Android 11 and later see none without it), and a game's own additions inside `<manifest>` (`manifestAdditions`: permissions, features, queries) and `<application>` (`applicationAdditions`: meta-data, services); `check` refuses XML that doesn't close as it opens.

### Fixed

- **Saving no longer crashes the game now and then on Android**: the shrinkCopy plugin, which shrinks the screen to a save's thumbnail (and the sample's CG and Replay pictures to their tiles), read a row past the bottom of the picture for its last pixel, and where the picture's memory ended at a page the game crashed (seen in 0.17.0's release run, as the Android emulator's game saved; `UPSTREAM.md` 39). The framework shrinks from a copy with one more row now (`KAGShrinkCopy`); 0.17.1 finishes the fix.
- **The music room lights the first track while it plays**: the track that had played before was compared with the one playing, and before any had played that was void, which TJS takes as track 1, so track 1 was never lit.

## 0.16.0

### Added

- **Carry on where you left off**: the game keeps the player's place as it goes, in a bookmark of its own (the continue save): at the first wait for a click after a new script starts and every few save points (`continueEvery`, 5), and when the game quits, so a phone or a browser tab ending the game loses little. The sample's title asks once a run whether to carry on, showing the scene and the date, and Config's second page can turn it off. `continueSlot` in `Config.tjs` names the bookmark; `kag.hasContinue`, `kag.saveContinue()` and `kag.continueOn` are the framework's side (`doc/kagex.txt`, "Carrying On and Quick Saves").
- **Quick saves that go round**: quick saves go round a few bookmarks (`quickSaveSlot`, `quickSaveSlots`: the sample keeps the last three), so one wrong key can't overwrite the only one, and quick load asks, then loads the newest. Shift+S and Shift+L quick save and quick load, and the sample's message window has Q.SAVE and Q.LOAD buttons (Q.LOAD greyed out until there's a quick save). `kag.quickSave()`, `kag.quickLoad()`, `kag.newestQuickSave()`, `kag.quickSaves()`, `kag.quickSaveHook`.
- **Voices that fade out when cut**: a voice cut by the next one, by a click past its line (KAG's `voicecut`) or by a click during `[waitvoice]` fades out over a moment (`kag.voiceFadeTime`, 300 ms) instead of stopping in the middle of a syllable. It fades on a track of its own, so the speaker's next voice starts at once on the other, and the game doesn't wait for it: the voice's stop is told as the fade begins (waits end, the music comes back up). Skipping, auto mode and loading still stop voices at once. Config's second page offers Stop, Fade or Keep (a voice plays on until the next one) and the fade's length.
- **Voices from where the speakers stand**: with `"voice3d" => true` in `envinit.tjs`, a character on the left is heard a little from the left and one further back further away, through the engine's 3D sound as placed sounds are since 0.12.0, and the voice follows the character as it moves; one off the stage or in the face window only is heard from the middle. Config's second page centres them all for players who prefer that.
- **A line's own volume and pan**: `[ai voice=12 vol=35]` makes one line quieter, a whisper, and `pan=` (-100 to 100) puts its voice somewhere of its own; both last for that line only, carry into compiled scenes, and come back with the voice when it's replayed from the backlog (`doc/world.txt`, "Voice Specification").
- The Character demo has a new scene, Voices: Ai on the left and Pip on the right speaking in turn, Pip's voice cutting in on Ai's, and a whisper. Config has a second page (its tabs are beside the title) with the voice and save settings above.

### Fixed

- **Going back to the title works every time**: from the second return to the title in a run on (after loading a save, or after playing a demo, going to the title and playing another), the title showed a black screen with the last scene's text and no buttons. The title's start anchor is saved as the title starts, and the compiled-scene player, which still held the scene it had played, saved that scene into it, so the next return restored the scene over the title. The player now saves only while the game is in its scene. The smoke test only checked which script was running, and now checks the title's buttons too.
- **The web build keeps its saves**: everything a web game saved (bookmarks, read marks, settings, the language chosen) went when the page was closed or reloaded. The engine keeps `/persist` in the browser's IndexedDB, but its save folder (`user://`, SDL's) is in the page's memory (`UPSTREAM.md` 37). The framework now saves to `/persist/<orgname>/<appname>/` on the web (checked across a reload in Chromium).
- **Saves are kept when the game stops on a script error**: a release build that hit an uncaught error showed it and ended, losing the read marks and settings since the last save of the system variables; it now saves those and the continue save first.
- **The music goes down while a voice plays again where `bgmdown` is on**: the World counted playing voices from 1 but lowered the music at 0, so it never went down.
- **A click during `[waitvoice]` waiting for every voice no longer stops on an error**: it named a function the World doesn't have.
- **Save files are named with one slash**: the save folder ends with `/` (`System.dataPath`), and the framework added another; a doubled slash in a `user://` name can hand SDL's storage an absolute path, which it refuses.
- A Yes/No prompt's message can have lines of its own (`\n`).

## 0.15.0

### Added

- **TV static**: the `static` flip type draws moving static over the scene, for a broken screen, a bad signal or a memory breaking up: `[image layer=1 flip=static visible=true opacity=96]` on a KAG layer, `[newlay name=tv static=tv opacity=96 show]` on a World layer. Each frame a picture of noise a grain smaller than the layer is drawn (layerExImage's `generateWhiteNoise`, or `noise` for colour; a tile drawn once where the plugin is missing) and stretched to the layer's size, about 6 ms a frame for the whole screen here; the layer's opacity and blend mode lay it over the scene. Options: `staticgrain` (the grain's size), `staticcolor`, `staticfps`, `staticbar` (a brighter band rolling down), `staticlines` (scanlines), `staticwidth`/`staticheight`; a save keeps them, and a World layer's redraw doesn't start it again (`template/system/GFX_Static.tjs`; `doc/kagex.txt`, "Optional parameters for static"; `doc/world.txt`, `static`). **Over the message window too**: `level=message` puts a World layer over the game's message window and its choices, and under the system screens (the sample's save, load and config screens draw on the second message layer), the backlog and the prompts (`[newlay name=tv static=tv level=message]`; level 9, `KAGEnvMessageLevel`); a KAG layer gets there with `index=1000500`. A layer showing static lets the pointer through, so the window's buttons work under it. It isn't called `noise`: that's the still noise every World image takes (`noise=`); and since `static` is a reserved word in TJS, a script reads the attribute as `elm["static"]`.
- **Pitch and pan for World music and sounds**: `[bgm pitch=35 time=2500]` slows the music down and drops its pitch like a tape running out, `[se name=se_steps pan=100 time=3000]` moves a sound across from left to right; `pitch=` is in % of the recording (1 to 400; the engine's frequency changes speed and pitch together), `pan=` from -100 to 100, each over `time=` (at once while skipping). A play tag starts its sound at the pitch and pan it gives, as recorded and in the middle otherwise; a save keeps them, so compiled scenes, loads and going back carry them; a sound placed on the stage keeps the pan of its place (`KAGEnvSoundShift` in `KAGEnvBGM.tjs`; `doc/world.txt`, "BGM Object Functions" and "SE Object Functions").
- The Effects demo ends with both: static over the road at night and the message window, the music running down and back, and footsteps crossing from one side to the other. A build without Effekseer now skips the effects and plays this step, where it used to end the demo.

### Fixed

- **kagex-release: rule images stay PNG**: with Media > Images set to TLG, or JPEG (which sent rules to TLG6), the transitions' rule images (`data/rule`) became `.tlg`, which the engine refuses as a rule ("Cannot load rule graphics", though the same file loads as a picture; `UPSTREAM.md` 36), so every rule transition in such a build quietly became a crossfade. Rules now become PNG whatever the setting (a TLG rule of the game's too), and the converted-game test runs a universal transition with each of the sample's rules.
- **kagex-release: the game's engine options on Android, iOS and the web**: the options in the game's `krkrz.cf` reached only the Windows, Linux and macOS packages, so on the others an option a game needed (`filepoolsize=none`, for one that filled the file pool with fonts) was missing, and without `debugwin=no` a release ran its debug code. They now go, with `debugwin=no` (unless Engine > Debug), into the `config.cf` those engines read from their resources (the APK's assets, the app, the site's `resource/`), ahead of the engine package's own lines; the web drops the engine package's command-line options the game sets, since the command line comes first. `orgname` and `appname` stay as they were there (on iOS they'd move the saves of a game's earlier builds). Checked in Chromium, in both web data modes.
- **kagex-release: `(const)` arrays and dictionaries in compiled scripts**: TJS bytecode has no form for a constant object, and the engine wrote null for one without a word, so a script that was a `(const)` table, or used one, read null once compiled (Contents > Scripts). Such a script now stays source, with a note in the build. The framework's own `MainWindow.tjs` had one (its menu shortcut table), so it's a plain dictionary now, and the window's script still compiles.
- **kagex-release: "Gradle made no .apk" after a build that made one**: the APK (or bundle) is looked for folder by folder in Gradle's outputs, past folders it can't read; on Windows Gradle's intermediates go past 260 characters, and the search used to stop at the first error.
- **kagex-release: a retry before "Can't remove ... (is it open somewhere?)"**: removing a folder is tried for about 3 s first, for a file a virus scan holds just after it's written.
- **The menu bar shows `File` for a caption `&File`**: it showed `$1ile`, since TJS's `replace` takes `$1` as it is. Only bare `&X` accelerators showed it (the sample's and the template's menus write `(&X)`).
- **`[se name=...]` no longer plays a file called "name"**: the World's SE object addressed by `name=` (`[se name=se_steps stop=300]`, as the Character demo stops its footsteps) also took the attribute as a sound to play, so depending on the order of the attributes the tag either stopped the sound and left its buffer named "name", or started a play of a file of that name.
- **A movie named without its extension finds its `.webm`**, the format the SDL engine plays (`[image movie=test]`, a World layer's `movie=test`), and a `.webm` name is a movie for `flip=`.

## 0.14.0

### Added

- **Live2D models on layers**: the `l2d` flip type plays a Live2D model on a KAG layer (`[image layer=1 flip=hiyori.l2d]`) or a World layer (`[newlay name=mascot l2d=hiyori]`) as it was made: a motion that goes on (`l2dmotion`, by default the Idle group's), its own blinking and physics, an expression (`l2dexpression`), with `l2donce` playing a motion once (the trigger `l2donce` goes when it ends), `l2dparam` adding to parameters, `l2dblink` turning its blinking always on or off, `l2dspeed`, and `l2dlip` opening its mouth with an SE buffer's sound. The model's canvas fills the flip's (`l2dwidth` x `l2dheight`, the screen's by default), and the layer is placed, zoomed and turned like any other; a save keeps the options, and a World layer's redraw doesn't start the model again. The layer demo ends with Hiyori on a layer. Without the krkrlive2d plugin (which a game builds with its own Cubism SDK) the layer shows nothing, and `l2donce` still sends its trigger, so a `[waittrig name=l2donce]` after it goes on. `doc/kagex.txt`, "Optional parameters for l2d", and `doc/world.txt`, `l2d`.
- **3D scenes, glTF models and VRM avatars**, drawn by the krkrthreepp plugin (threepp, a C++ port of three.js), which every engine has: Windows, Linux (the zip and the Steam package), macOS, the web, Android and iOS. The `3d` flip type plays one on a KAG layer (`[image layer=1 flip=vee.vrm]`) or a World layer (`[newlay name=prop 3d=star3d.glb]`) with a transparent background: a VRM avatar standing, framed whole (`3dframe`), blinking, its eyes on the camera, playing a VRM animation that goes on (`3dmotion`), with expressions (`3dexpression`) and its mouth opening with an SE buffer's sound (`3dlip`); a glTF model playing its own animations; or a scene built in script, which `KAGThreeScene("<name>", function(s) { ... })` registers (`s.scene`, `s.camera`, `s.update` each frame, `s.once` for `3donce`). `3donce` plays something once (the trigger `3donce` goes when it ends), and `3dcamera`/`3dtarget`/`3dfov`, `3dangle`/`3dturn` and `3dspeed` place the camera and turn the model. **VRM characters**: a World character whose envinit.tjs entry has `"vrm"` is a VRM avatar, with VRM animations (`.vrma`) as its poses (looping) and motions (once, fading in and out), faces of expression weights (VRM 1.0's preset names find a VRM 0.x avatar's too), blinking through its blink expression and lip-sync through its mouth expressions, a lip track's vowels each their own (`aa`, `ih`, `ou`, `ee`, `oh`). What Live2D and VRM characters share is now `KAGEnvCharacterModel.tjs`. The sample's Animated Character demo ends with Vee, a VRM avatar of its own built from shapes by `tools/assets/make_vrm.py` (which also makes her VRM animations and a glTF star), saying an eSpeak NG line with a lip track, and the layer demo shows a scene built in script (`data/main/Scenes3D.tjs`), the star and Vee on layers. MSAA is off where the engine's offscreen buffer can't take it, and only one 3D picture with lit materials can be on the screen at once (`UPSTREAM.md` 34, 35). Without the plugin or OpenGL ES the layer shows nothing, `3donce` still sends its trigger, and the demos say so. The Steam package links each plugin with its static libraries' symbols kept to itself (`--exclude-libs,ALL` in `linux-config.json`: krkrthreepp had bound to another plugin's copy of the C++ library and crashed on its first shader), and the framework unlinks krkrthreepp before the game exits there, as it does the json plugin (`UPSTREAM.md` 2). `doc/kagex.txt`, "Optional parameters for 3d", and `doc/world.txt`, "VRM Characters".
- **The Live2D tools in the Windows and Linux zips**: `tools/live2d` (`setup.py`, `build.py`, their patches, the driver's CMake) and `tools/assets/make_hiyori.py` go into the zips with kagex-release's `tools/`, so a developer starting from a zip can build the Live2D plugin for their game with their own Cubism SDK. The Live2D sample game zips had them already.

### Changed

- **Releases reuse the platform builds' engines too**: the Steam Linux, web, Android, iOS and macOS builds compiled their engines in every release (iOS took about an hour, Android 45 minutes), though only the game changed. Each platform job now works out a key of what goes into its engine and, when an earlier release's note has that key, takes that release's engine package and adds the game the way the kit does after its build, with the same smoke tests; the release's note keeps every platform's key for the next one. Android's smoke test drives the game through the REPL, which the kit compiles into Debug builds only, so the release adds `kagex_engine_android_debug.zip` (the debug APK's engine), and a reuse builds the debug APK from it and the release APK from `kagex_engine_android.zip`; kagex-release doesn't use it. A release that changes only the game takes about 25 minutes instead of 70. `[rebuild]` in a pushed commit message, the workflow's `rebuild` input or the repository variable `KAGEX_PLATFORM_REBUILD=true` builds them all.

## 0.13.4

### Fixed

- **A window no longer keeps resizing itself** (issue #29): in a window, the window flipped between the game's size and the game plus the menu bar's strip, every few hundred milliseconds, for as long as the game ran. `KAGWindow.setZoom` let the engine size the window to the game alone, then added the strip: two resizes, each reported later through `onResize`, which called `setZoom` again with the same zoom. When the zoom doesn't change, `setZoom` now sizes the window once, strip included, and only when it isn't that size already. The smoke test checks that nothing calls `setZoom` while a window sits still (here it ran about 80 times a second).

## 0.13.3

### Changed

- **Every release gets the Live2D sample game packages**: once a release is out, the release workflow starts `live2d.yml` with its tag, which builds that release's code and adds `kagex_sample_live2d_<windows|linux|macos>.zip`, `kagex_sample_live2d_android.apk` and `kagex_sample_live2d_ios_simulator.zip` to it. 0.13.0's were added by hand, and 0.13.1 and 0.13.2 have none.

### Fixed

- **Android games start on their first run when the phone is held upright**: the Android kit's loading screen asks for landscape, which restarts it on a phone held upright, and each start began copying the game files out of the APK, so two copies ran at once, deleted each other's files, and the engine started without its data (`No project data`) and stopped. It failed the Android smoke tests three times of four, and could stop any player's first run of an APK, kagex-release's included. CI patches the kit (`.github/platforms/kit-android-bootstrap.patch`) so the copy runs once at a time (`UPSTREAM.md` 33).
- **Live2D's Web Core and Hiyori stay out of the web engine package**: 0.13.1 and 0.13.2's `kagex_engine_web.zip` held `live2dcubismcore.min.js` and a copy of Hiyori's model (`hiyori_test.l2d`), so every web game kagex-release built carried both, and the repository held the staged web site (`build/web/site`, with the Core and Hiyori's files). Both releases' engine packages are replaced, the site is gone from the repository and its history, and `/build/` is ignored. `engine-package.py` leaves the Web Core, its script tag and any Live2D model out of the web package, and the three package scripts refuse the Web Core (as the native one) unless given `--with-cubism-core`, and a Live2D model always. A Live2D web game brings its own Core: kagex-release copies `plugins/web/live2dcubismcore.min.js` into the site with its script tag, `check` warns when a game with Live2D models has none, and the web build leaves out a Core an older engine package brought.
- **Live2D on the web: part opacities, released models, and no Core**: the web's Core (`tools/live2d/web/csm_web.cpp`) passes the parts' opacities to the Web Core before each update, so a model's pose groups (Hiyori's two sets of arms) switch as on the other platforms; frees each moc's and model's Web Core objects and copies when the Framework frees them (a call kagex's Framework patch adds), where every load, BACK and scene change used to leave them behind; answers a moc's version after its header is gone; copies a model's indices and masks once and its draw orders every update; and reads no model when the page has no Core, instead of throwing.
- **kagex-release's web games start with 0.13.2's engine package**: that package's `webconfig.js` kept the sample site's `KRKRZ_WEB_PROJECT_XP3 = true` (its data is one `gamedata/data.xp3`), so a web game built with the *files* data opened `web://./data.xp3>` and stopped at `Cannot find storage web://./data.xp3`. kagex-release sets it to false, and `engine-package.py` writes it false into the package.
- The smoke test checks that `idle5` plays the fifth motion of Hiyori's Idle group, not any of hers; the Live2D sample packages' build tools leave out `tools/live2d/build/`; the release tool's web race test can't be stalled by a response nobody reads.

## 0.13.2

### Changed

- **The web demo delivers its data as one archive**: the browser demo's game data ships as `gamedata/data.xp3`, not as loose files: the page makes one request for that instead of a few hundred for the game's parts, the engine's file list lists the archive, and it opens the archive as the web project's own path, `web://./data.xp3>`, which the engine already supports as a project path (desktop engines read their own `data.xp3` the same way). The archive is built and opened by the web kit: `stage_web.py` gains a `delivery: "xp3"` source mode, where a `web-config.json` source goes into that one archive instead of loose files, `pre.js` boots a site packed that way, and `xp3pack.py` learned to stream an archive's index back into the file being packed and orders names the UTF-16 way the engine's archive reader looks them up. The changes ride into the web job as `tools/live2d/web/kit-web-xp3.patch`, applied right after the kit is cloned at its pinned commit; when `KRKRZ_WEB_SHA` moves, rebase the patch onto the newer kit and let the web job run it. The job's smoke test and the Pages check go through the same scenarios as always, packed; the site's `?webbase` and offline-cache paths are unchanged. A game's `web-config.json` sets `delivery: "xp3"` on its sources to ship the same way.

### Fixed

- **kagex-release stamps the Live2D engine's web sidecar**: the release tool's web build stamps the site's script tags with its own build id, but a Live2D engine's (0.13.1+) `live2dcubismcore.min.js` tag was left with the id it carried in the engine package, and the tag sits between `webconfig.js` and `krkrz.js`, which tripped the release tool's own web smoke check (the 0.13.2 release cut ran it against 0.13.1's engine). The sidecar now gets stamped with the rest, and the check tolerates its tag in that position.
- **smoke tests' Chromium starts with `--disable-dev-shm-usage`**: a CI runner's `/dev/shm` is 64 MB, and a web engine's shared memory over that kills the page mid-boot as `Target crashed`, before it logs a line — the 0.13.2 cut's release-tool check died that way on the web-files prefetch race step (the 0.13.1 engine's heap crossed the line, the 0.13.0 one didn't). The launch now points Chromium's shared memory at the regular disk, as CI browser guides always recommend.
- **the web-files race check's storm stays inside the page**: the check slows every OPFS write, and with a released engine (0.13.1's web sidecar fetched its whole file list at once; 0.13.2's kit bounds it at two) every response was held until its slow write finished — the renderer ran the CI runner out of memory and the page died `Target crashed` before the game could start. The check's init script now caps the page's fetches at four, keeping the race honest (concurrent, slow writes under boot reads) at a footprint the runner can take.
- **the web smoke test's engine-start wait waits, it doesn't race**: the loop polled the REPL with `krkrz_repl_eval` while the module was still instantiating — a ccall that lands mid-instantiation re-enters a half-built module and takes the renderer down (`Target crashed`), a real race from 0.13.2 on because one packed archive plus a warm CDN boots fast enough to lose it. The wait now watches the engine's own earliest console line (`TVP Log system`) as the ready signal, and pumps Playwright's event loop while it watches: console lines only arrive during a page call, so a sleep-only wait buffered every line until teardown and saw nothing.

## 0.13.1

### Added

- **Live2D characters in web builds**: the browser engine draws World's Live2D characters like the desktop one does. Live2D's licence keeps the Cubism Core's own code out of kagex's packages, so on web the Core is `tools/live2d/web/csm_web.cpp`, a shim over the Web Core that comes in Live2D's Cubism SDK for the browser: `live2dcubismcore.min.js` runs as a script beside the engine (the page loads it before the engine, and `web-static-host.py` puts the tag in), and the engine talks to it as it does to the native Core, with the same `csm*` calls crossing the wasm/JS border (handles as emval ids, model data as byte copies). `tools/live2d/build.py --web` fetches both SDKs' zips from the private Cubism repository, builds krkrlive2d, the framework and the shim into the shared binary (the plugin's web fixes live in `tools/live2d/patches`), and stages the site with the Web Core beside it. The web job builds it and the smoke gate runs `--live2d required`: Hiyori's Animated Character demo plays in the browser, her picture, motions, faces, blinking and lip-sync, on the real plugin. A game's web engine gets the plugin the same way, with `--kit` readying its config, and as everywhere the Core itself is the game's to carry: `live2dcubismcore.min.js` beside the engine, from the game's own licensed copy of the SDK.

## 0.13.0

### Added

- **Live2D characters**: a World character can be a Live2D Cubism model: an envinit.tjs entry with `live2d` and a `.l2d` file (the folder Cubism Editor exports, zipped), which the krkrlive2d plugin draws into the character's layer through the engine's GLCompositor every frame, at the size of its World level. Its poses are motions that go on (one of a model3.json group after another), its motions play once and go back to the pose (`motionwait` waits for one), its faces are the model's expressions or values for its parameters, fading into each other and held whatever its motions do with them (the motions move its head, body and hair), and it blinks and lip-syncs to its voice as Pip does, a lip track's vowels shaping its mouth; the eye and mouth commands work on it too. Its pose and face are saved, and a model is let go when its character leaves the screen (`KAGEnvCharacterLive2D.tjs`, `GFX_Live2D.tjs`; `doc/world.txt`, "Live2D Characters"). The plugin needs Live2D's Cubism SDK, whose licence keeps its Core out of kagex's own engines, so a game builds the plugin: `tools/live2d/build.py --sdk <the SDK's zip>` fetches it at pinned commits, applies kagex's fixes (`tools/live2d/patches`; `UPSTREAM.md`), builds its driver on Linux, macOS, Android and iOS too (`tools/live2d/driver`) and puts it in `plugin/` (`--steamrt` builds the Linux one in the Steam Runtime, so it loads on every Linux the engines run on; `--kit` readies krkrz_android's or krkrz_ios's config to build it into the engine). Cubism 5's shaders for its newer blend modes compile when a model first uses them, not all 474 before the first frame (a stall of up to 39 s on a Mac). On Android and iOS a game makes its own engine package from such a build, which `android-engine.py` and `ios-engine.py` make only with `--with-cubism-core` (they and `engine-package.py` refuse the Core otherwise, so kagex's own engine packages never carry it), and puts it in `engines/` next to `data/` for kagex-release. `tools/live2d/LIVE2D-NOTICE.txt` holds the terms for a game's players that Live2D's licence asks for. CI builds and tests Live2D on Windows, Linux, macOS, Android and iOS, and goes through what a game does: the desktop sample built with kagex-release with the plugin in `plugins/<platform>/`, and a game's own Android and iOS engine package with the sample built from it (the iOS app gets the smoke test, the Android APK is started and checked by its log). Started with a release's tag, it adds the sample with Live2D to that release as packages of their own (`kagex_sample_live2d_<platform>`), apart from the engine and template packages. Without the plugin, a Live2D character draws nothing and the log says why. The smoke test checks Live2D characters with the plugin (`--live2d required`) or, without it, with a stand-in that does what the plugin's driver does with a model's parameters (`tools/live2d-standin.tjs`).
- **Hiyori** in the Animated Character demo: Live2D Inc.'s sample model (Neuro-sama's first), who joins in after Pip in the middle of the screen with a face for each of her moods, her idle motions, a motion played once and a motion picked by group and number or by file name, a pose of one motion of its own, blinking, a wink and a voiced line. She isn't in the repository, since Live2D's licence for its sample models lets no one but Live2D hand out their files: `tools/assets/make_hiyori.py model --accept-license` fetches her from Live2D's GitHub, and her line, `data/voice/hiyori000001.ogg`, is eSpeak NG's (a formant synthesizer, no voice learned from recordings: `make_hiyori.py speech`), with a lip track from kagex-lipsync. A build without the plugin or her model says so in her place.
- **kagex-release: a game's own plugins**: libraries in `plugins/windows/`, `plugins/linux/` (Steam too) or `plugins/macos/` next to `data/` go into that platform's packages beside the engine's plugins (`plugin/`, or `Contents/MacOS` in the app), all of them whatever `contents.plugins` says, signed with the engine in a signed build and listed in the plan; one with an engine plugin's name replaces it. `check` warns about files there that aren't plugins for the platform, and about `plugins/web`, `plugins/android` or `plugins/ios` when that platform is enabled, since those engines have their plugins linked in. A game builds the Live2D plugin into its folder with `tools/live2d/setup.py` (a guide through Live2D's licences, what the computer needs, the SDK, the build and a check) or `build.py --out plugins/<platform>` (`tools/release/README.md`, "Your own plugins"), and `check` warns about a game with Live2D models whose enabled desktop platforms lack the plugin.

### Fixed

- A Live2D face whose mouth parameter was open kept it open after the voice stopped: a face's mouth value is where the mouth rests between the words, so the sample's smiling face, which talked while she was silent, shuts now (`smile` in the sample's `envinit.tjs` and in `doc/world.txt` gives no `ParamMouthOpenY`). A face that asks for an open mouth, `surprised`, still keeps it open: it is the face that says so.
- The Animated Character demo's text: its lines are short enough for one message window now, so they don't run over into the next page.

### Changed

- Blinking and lip-sync are a class of their own, `KAGEnvCharacterEyeLip.tjs`, which characters drawn from layers and Live2D characters share; world.tjs loads it before either, so Override.tjs changes its settings (`eyeFlipTime`, `lipFlipTime` ...) as before.

## 0.12.1

### Added

- **A line's characters drawn together**: where krkr_richtext draws the message window, each line's characters are laid out and drawn together by its `StyledLayout`, as its line breaker lays them out, instead of one at a time: the line so far is drawn again each time the text stops (after every character at the usual speed, once a line when the text comes all at once, which is as fast as before). So kerning and ligatures run across the line, accents and emoji made of several characters are shaped as one (a combining accent was drawn beside its letter, and a character outside the BMP, an emoji, as two boxes), and the characters sit at fractions of a pixel. KAG still places and times every character, so the text speed, waits, links and the word wrap are as they were; a character with ruby keeps KAG's ruby (`rubySize`, `rubyOffset`), since StyledLayout's can't be sized or moved (`UPSTREAM.md`). Config.tjs's `useStyledLayout` turns it off (`doc/kagex.txt`, "Line breaking").
- **Japanese and Chinese line breaking by krkr_richtext**: Japanese and Chinese lines break where its line breaker plans, filling each line, with the Unicode rules and the languages' own: closing brackets, full stops, commas and small kana don't start a line, and a word in Latin letters (a name, README) isn't split, as KAG's character wrap split it. Nothing hangs into the margin KAG kept at the end of a line for that (`marginRCh`), so a line can end a character earlier. Vertical text, and the builds without krkr_richtext (the browser, iOS), keep KAG's own wrap (`UPSTREAM.md`).

### Fixed

- In a Japanese or Chinese game whose scripts KAG plays (not compiled), a line with a space in it got the English word wrap, which could break it at the space.

## 0.12.0

### Added

- **A menu bar, in a window**: the game's menu (System, Display, the message commands, Help, and Debug in debug mode) shows as a menu bar in a strip above the game, as Kirikiri's Win32 menu bar did and in place of the one the SDL engine doesn't have: the window is the strip taller than the game, which is drawn under it, and full screen has no bar. A click on a title drops its menu down over the game, moving to another title opens that one, resting on a submenu opens it, and F10 (and the controller's START, in a game that leaves it to the framework, and R3) opens the first menu from the keyboard, where the arrows, Return and Esc work as on Windows. It's drawn with the engine's Elements UI in the dialogs' look, shows the items as they are (enabled, checked, the radio groups' choice, the shortcuts), works with a screen reader, and shows a game's own menu (`KAGWindow_createMenus` in `Override.tjs`) as it is, its captions in the language shown (`MenuBar.tjs`; `doc/kagex.txt`, "The menu bar"). Engines without the Elements UI or `Window.setViewport` don't show it.
- **A controls list** (Help > Controls, and a Controls button on the sample's Config screen): what every key, mouse button and controller button does, read from the bindings themselves, with the controller's buttons named for the pad in use (✕ ○ □ △ on a PlayStation pad, A B X Y elsewhere) and the debug keys in debug mode. The window's keys are now a list of bindings that a game adds to with `kag.bindKey` (the sample's F1-F8, in `AfterInit.tjs`), so the list stays right for a game that changes them (`doc/kagex.txt`, "Key bindings" and "The controls list").
- **Screenshots**: F12 (and Print Screen, where the system passes it on) saves the screen as a PNG in the save folder and says so in a corner. Where layerExSave gives the window `startSaveLayerImage` (now linked before the window is made), the PNG is written on another thread, so the game doesn't stop while it's written (`doc/kagex.txt`, "Screenshots").
- **Screen readers**: each message is read out with its speaker's name, and the choices, the Yes/No prompts, About, the menu bar and the controls list are given to the system's screen reader (Narrator, VoiceOver, Orca) to read and press, through the engine's accessibility interface (`Accessibility.tjs`, `KAGA11y`, for a game's own UI too; `doc/kagex.txt`, "Screen readers"). The browser, Android and iOS builds don't have the interface.
- **Positional sound**: `[se storage=... pos=farleft]`, `xpos=`, `level=` or `char=ai` places a sound on a World stage: it's panned to where it is and comes from further away the further back it is, and a looping sound at a character follows it as it moves (the engine's 3D sound; `doc/world.txt`, "SE Object Functions", and envinit.tjs's `se3d`). The Character demo plays a chime at the far left and the far right of the stage and footsteps that follow Ai as she walks (`tools/assets/make_sounds.py`).
- **Line breaking by krkr_richtext**: where krkr_richtext draws the message window, English lines break where its line breaker (minikin's, which its `StyledLayout` uses) puts the breaks for the whole line, evening out ragged lines; Config.tjs's `lineBreakStrategy` chooses `quality`, `balanced` or `greedy` (`doc/kagex.txt`, "Line breaking").

### Fixed

- The word wrap only worked on plain lines of text: a script line that started with a tag or a tab, had `[r]` in it or ran into text from `[emb]` was left to KAG's character wrap, which split words, and a compiled message with a new line in it too. It follows the line as it's drawn now, finds its place again after text the line doesn't have (`[emb]`, text `[if]` leaves out), and doesn't break a line twice at a word that doesn't fit after KAG's own wrap has broken it.

### Changed

- The sample's F1-F8 are key bindings (`kag.bindKey` in `AfterInit.tjs`) instead of a `keyDownHook` function, and its menu captions (`Override.tjs`) have their shortcuts, for the menu bar. The framework's menu has Save Screenshot and Help > Controls.
- The Character demo's music fades out before its positional sound part, so the chimes and footsteps are heard on their own, and the Animated Character demo has no music.

## 0.11.0

### Added

- **Characters straight from PSD and CLIP STUDIO PAINT files**: a pose's layers at a level can be the file the artists draw in, `<files>_<level>.psd` or `.clip`, when there's no `<files>_<level>.txt`. Its layers and folders are the layers and groups `_info.txt` names, read through the psdfile and clipfile plugins on the desktop engines (`doc/world.txt`, "The layers in a PSD or CLIP STUDIO PAINT file"). `psdlayer.tjs` reads CLIP files too (`PSDInfo.loadCLIP`), gives PSD layers without an ID one (`assignAutoIds`) and leaves out empty layers.
- **kagex-release splits PSD and CLIP files into layer pictures**: every `.psd` and `.clip` a build takes in (all the game has, by 0.9.3's defaults) is replaced by its layer structure (`<name>.txt`, psdlayer.tjs's format) and a TLG picture per layer (`<name>_<layer id>`), read with the libraries the plugins are made of, so a release needs neither the files nor the plugins and plays them on the web, Android and iOS too. A file whose layers the game has already, as a layer structure of its name (`<name>.txt`, what psdlayer.tjs's `saveImages` exports), stays out, and one that can't be read goes in as it is, each with a note. With a pattern of yours that leaves them out, a pose `charinit.csv` names goes in (split) all the same, like a file a script names after `psd://` or `clip://`. Splits are cached; a name the split would write that the game already has stops the build. `kagex-release --cli split <file> <folder>` shows what a build makes of one file (`tools/release/README.md`, "Photoshop and CLIP STUDIO PAINT files").
- `psd://name.psd/root/folder/layer.bmp` and `psd://name.psd/id/<LayerId>.bmp` load a Photoshop file's layer into KAG and World layers on every engine with psdfile (the plugin's own BMPs only loaded on Windows), as `clip://` does; both read what kagex-release split the file into where the file or the plugin isn't there.
- **Mouths by vowel**: a mouth group with a layer for each vowel ("Mouth A" ... "Mouth O", or あ ... お) shows the one for the vowel the voice says while it lip-syncs (face groups take `lipa` ... `lipo`). The vowels come from the voice's lip track (below); a voice without one opens and shuts the mouth by its loudness alone, with nothing to prepare (`lipEngineVowels` lets the engine's `WaveSoundBuffer.getVowel` pick vowels instead, but it mostly hears a voice's pitch: `UPSTREAM.md`). Pip's plain face has them.
- **Lip tracks**: a voice can come with `<voice>.lip`, the mouth over time (a vowel, `n` for the lips closed, or `-`, and how open), which then moves the mouth in place of the voice's level, timed from when the voice starts (`lipSyncTracks`; `doc/world.txt`, "Blinking and lip-sync").
- **kagex-lipsync** (`tools/lipsync`, built and shipped with kagex-release): pick the voices whose characters should shape their mouths to the vowels, and it writes each one's lip track from the voice and the line the scripts give it, by forced alignment with existing libraries (PocketSphinx; OpenJTalk reads a Japanese line's sounds, kanji included). Its window lists every voice with its character, its line and its track's state (none, current, out of date, hand-written) and plays a track along with its voice; a line typed in replaces the script's where the voice says something else, and a voice that doesn't fit its line is refused rather than guessed. The lines come from the game's own scenario compiler (the framework's new `-voicelines`), in each of a game's languages: a track is made from the first, the source language's first, that the voice fits, so the sample's Ai, recorded in Japanese, gets hers from the Japanese line. Measured on synthesized lines in four Japanese and four English voices: the right vowel 86% and 87% of the time, against 22% and 39% for the engine's getVowel and a best of 90% with the mouth changing every 120 ms (`tools/lipsync/README.md`). kagex-release's check warns about tracks whose voice has changed since.
- The Animated Character demo's Pip says one line in a synthesized voice (`tools/assets/make_pip.py speech`, Kokoro; English, with the line in Japanese too), whose lip track kagex-lipsync made: the demo's example of mouths by vowel. Its babbled lines move the mouth by loudness.
- `tools/assets/psdwrite.py` writes a layer structure and its pictures as a PSD with folders (standard library only); the smoke tests use it to check that a pose read from a PSD, and one kagex-release split, match the sample's own.

### Fixed

- Lip-sync for a voice with no lip track was out of time now and then: the engine reads a playing voice's level at its own idea of the play position, which runs half a second ahead about a quarter of the time (`UPSTREAM.md`). The mouth now reads the part of the voice the clock says is playing, and keeps readings of the next frames for those moments: measured in the engine on synthesized lines in eight voices, it's open or shut as it should be 72-73% of the time instead of 68-69% (77-81% would be readings without the engine's error, with the mouth changing every `lipFlipTime`). Nothing to prepare: it's the voice file as it is.
- A character drawn from layers kept its eyes and mouth still while its own change (pose, outfit or face: `charTrans`, 300 ms in the sample) faded in, so a line said with a change lost its start. They move during it now.
- `clip://` found a layer inside a folder by its name alone (`root/layer`), not by its folder path, and of two layers of one name took the upper one, unlike the plugin.

### Changed

- kagex-release 0.11.0 downloads the 0.11.0 engines, and the release packages carry kagex-lipsync beside it, with its models and dictionary (`tools/lipsync/`).

## 0.10.0

### Added

- **Languages, switched while playing**: a game lists its languages in `Config.tjs` (`KAGLanguageList`, the language its scenarios are written in first), and the player switches between them at any time with **F9**, the controller's **L2** or a button of the game's: the message on screen (and its speaker's name), the choices on show, the message window's buttons and the screen on show are drawn again in the other language, and the backlog keeps each line in the language it was shown in. The story's other languages are built into the compiled scenarios, as in Wamsoft's multi-language games: each listed script's translation, `data/lang/<code>/scenario/<script>` (the script with its text in that language), is compiled with it, and its texts, display names, choices and scene titles go into the script's `.scn` (`languages`, and per text a list of `[display name, text, length, speech text, search text]`, one a language: compiled format version 3), matched scene by scene and text by text; a scene that doesn't match keeps the script's own text, and the compiler warns. The scene player shows the language shown, the backlog, Search and the save slots' titles included, and a speaker's `nameAlias` in `envinit.tjs` can be a dictionary by language. kagex-release leaves the translations out of the package with the scripts, and converts a language folder's images like the ones they stand in for (files of the same name in different folders get the same new name). Each other language's folder, `data/lang/<code>/`, is on the search path while the game shows it: its interface strings, `lang.json`, and any file that stands in for one of the same name, such as the screens' images with words on them. Scripts KAG plays itself are shown as written. Until the player chooses a language, the game takes the one the system prefers (`System.uiLanguage`, then `System.uiLanguageCandidates`); the choice is saved with the system variables. The framework's own strings (the Yes/No prompts, About, the backlog's "Choice:") are in `system/kagex_ja.json`. `doc/kagex.txt`, "Languages".
- **The sample in Japanese as well as English**: every demo's script translated (`data/lang/ja/scenario/`, the original KAGEX sample's Japanese where it had the line), the speakers' names, the demo menu, scene titles in Replay, Search and the save slots, and the title, Config, save/load and Extras screens and the message window's buttons, drawn in Japanese by `tools/assets/make_ui.py --lang ja` into `data/lang/ja/`. The Config screen has a Language row (English, 日本語); its rows are a little closer together to make room.
- `tools/assets/subset_fonts.py` makes the Japanese subsets of Noto Sans CJK JP that `make_ui.py` draws the Japanese labels with (`tools/assets/fonts/NotoSansCJKjp-*-Japanese.otf`).
- `tools/smoketest.py` switches the title screen, a line of `char.ks`, the demo menu's choices and the Config screen to Japanese and back, and checks that the backlog keeps what was shown. It puts the sample in English first: under a C locale the engine's candidates are Japanese.

### Changed

- **Compiled scenarios are format version 3**: a game's scripts compile again the first time, and a game in more than one language gets its languages in each `.scn`. With one language a compiled file is laid out as before. [scnfile](https://github.com/krkren/scnfile)'s `scn2ks` reads the new layout and writes any of its languages (`--lang=ja`).
- kagex-release 0.10.0 downloads the 0.10.0 engines.

## 0.9.4

### Fixed

- **kagex-release encrypts and hides names on Windows, whatever language the file names are in**: [xp3crypt](https://github.com/krkren/xp3crypt)'s packer took names through Windows' ANSI code page, so a game with a file named in Japanese, built on an English Windows, stopped with "No mapping for the Unicode character exists in the target multi-byte code page". It takes them through UTF-8 now (xp3crypt 08ad5f7).
- **Archives with hidden names match names without regard to case**, as plain archives do: an image stored as `title.PNG` and loaded as `title.png` failed with "Unknown graphic format", because the engine picks an image's decoder by its extension as spelt and the `xpcrypt://` medium handed names back as stored. The 0.9.4 engines have the fixed plugin.
- **A game's own `startup.tjs` runs in a build with hidden names**: kagex-release shipped `system/hashed-bootstrap.tjs` in its place, so anything `startup.tjs` did besides starting `Initialize.tjs` was left out, without a word. It now goes into `data.xp3` as `startup-game.tjs` (its name hashed like the rest), and 0.9.4's `hashed-bootstrap.tjs` runs it once the archives are mounted. Update a game's `data/system/hashed-bootstrap.tjs` from `template/system`; with an older one the check warns that `startup.tjs` won't run.
- **kagex-release's `--engines` (and `KAGEX_RELEASE_ENGINES`) can be relative to the current folder**: with unpacked engine packages, the Windows icon and version step looked for `krkrz.exe` relative to the package's own folder and failed, saying it wasn't a Windows executable.

### Changed

- The release tool's smoke test builds a game with hidden names on Windows as well as Linux (a file named in Japanese, an image with an upper-case extension, and `startup.tjs` run), and a Windows build from an unpacked engine package given by a relative path.
- kagex-release 0.9.4 downloads the 0.9.4 engines.

## 0.9.3

### Added

- **A compiled script starts from the World the scripts that go to it leave**: each compiled file records the World it leaves at every jump and choice to another script, and a script that the listed scripts going to it all leave the same World in is compiled from that World. So a script that carries on from another's screen (a character still standing there, the stage, the music) has it in its saved states, and going back, loading or a thumbnail there shows it. When they leave different ones (the demo menu, which every demo comes back to), the script starts from an empty World as before. `-scncompile=all` compiles again the scripts whose starting World changed, until they all hold. The compiled format is version 2 (`entry`, `exits`; `doc/scn.txt`, "Where a script starts").
- **Going back to the middle of a message window draws the window as it was**: BACK, a backlog mark or a load at a line that carries on a window (layer.ks's lines, which build up in one window) draws that window's earlier lines first, without their voices and without adding them to the backlog again. It used to show the line alone (`doc/scn.txt`, "Going back").
- [krkren/scnfile](https://github.com/krkren/scnfile) tests itself on every push: its PSB codec and encryption on Linux (also with AddressSanitizer and UBSan), macOS and Windows, and the plugin and scn2ks (a compiled scenario back to a script) in the newest kagex release's Linux engine.

### Changed

- **kagex-release no longer leaves out `.psd` and `.clip` files by default**: Contents > *Leave out* is `*.bak`, `*.tmp`, `Thumbs.db`, `desktop.ini` and `.DS_Store`. A `release.json` that has 0.9.2's default list gets the new one; a list you changed stays as it is (and a `.clip` or `.psd` that a script loads layers from still goes in when a pattern of yours matches it).
- kagex-release 0.9.3 downloads the 0.9.3 engines.

## 0.9.2

### Changed

- **The desktop builds are split as Wamsoft's games are**: kagex-release's Windows, Linux, Steam and macOS builds with `xp3` (or `bind`) data ship `data.xp3` (`startup.tjs`, `system/`, `main/`, `init/`, `sysscn/` and the top-level files) and an archive per media folder beside it: `bgimage.xp3`, `bgm.xp3`, `effect.xp3`, `evimage.xp3`, `face.xp3`, `fgimage.xp3`, `image.xp3`, `others.xp3`, `rule.xp3`, `scenario.xp3`, `sound.xp3`, `thum.xp3`, `uipsd.xp3`, `video.xp3`, `voice.xp3` (those the game has), always, with or without encryption and signing. Signing > *Split large archives* is gone. A signed build checks each archive and mounts the media ones once they have. The web, Android and iOS builds keep the whole game in one `data.xp3`.
- **Hidden names are in `data.xp3`**: with Encryption > *Hide names*, the files in `data.xp3` and in the media archives are stored under keyed hashes of their paths, and only `data.xp3`'s `startup.tjs` keeps its name (still encrypted): the engine opens `data.xp3` as usual, runs it, and it mounts the archives through the xp3crypt plugin's `xpcrypt://` medium. No more `data.xpc`, and no `data/` folder: the package is the archives. Signing covers them as it covers any archives.
- Each encrypted archive of a game has its own range of per-file keys ([xp3crypt](https://github.com/krkren/xp3crypt)'s new `saltBase`), so no two files share a keystream.
- The framework finds the media archives beside the `data.xp3` it was read from (`KAGArchivePath`), not beside the executable, so a macOS app's archives go in its `Resources`. kagex-release splits a macOS build only for a framework that does (0.9.2's), and hides names only with 0.9.2's framework (`hashed-bootstrap.tjs`, `Initialize.tjs`, `SignatureCheck.tjs`): update a game's `data/system` from `template/system`.

## 0.9.1

### Fixed

- **kagex-release: signing works with hidden names.** A build can now be signed, encrypted and have its file names hidden at once (0.9.0 refused Signing with *Hide names*). The game checks `data.xpc` and the small plain `data/startup.tjs` that mounts it, each with its own signature (`data.xpc.sig`, `data/startup.tjs.sig`), so replacing either stops it. This needs the 0.9.1 framework (`SignatureCheck.tjs`, `hashed-bootstrap.tjs`): a game with an older `data/system` is told to update it.
- **The sample's web, Android and iOS packages carry its compiled scenarios**, so Search, BACK, the backlog's going-back marks and Replay's scenes work there. Their data is read-only, so the game couldn't compile the scenarios as it went (as the Windows and Linux zips do) and played the demos from the scripts: Search found nothing and Replay had no scenes. CI now compiles them once (`.github/platforms/compile-scenarios.sh`) and every platform job (the Linux folder and macOS too) packs the same files.

### Added

- **Compiled scenarios** (the first stage of [krkren/scnfile](https://github.com/krkren/scnfile)): the scripts listed in `!scnlist.txt` are compiled into `<script>.scn.json` by `SceneParser.tjs`, and the scene player (`KAGEnvPlayer.tjs`, `[scenestart]`) plays those in their place: text, names and voices as a table, tags as steps, and the World's state at every save point. However the game goes to a listed script (a jump, a choice, `kag.process()`, a load), it plays compiled. In debug mode a script is compiled when it has changed; `-scncompile` compiles them from the command line and exits, `-scnplay=no` plays the scripts themselves. `[if]`, `cond=` and `&` entities are decided as the game plays, macros come from `parsermacro.ks`, and the line modes put text together as KAG does (`doc/scn.txt`).
- **The scnfile plugin** ([krkren/scnfile](https://github.com/krkren/scnfile), in every 0.9.0 package and linked at start): compiled scenarios are `.scn` files, M2's binary PSB format, a third the size of the JSON. Without the plugin they're `.scn.json` as before.
- A compiled script plays without its `.ks`.
- The sample's demos and demo menu play compiled.
- **Going back in compiled scenes**: a BACK button in the message window goes back to the message before, and each message in the backlog has a mark that goes back to it (after a Yes/No). The World, the game's flags and the backlog are as they were at that message (`doc/scn.txt`, "Going back").
- **Scene replay**: the Replay screen has a tile for every titled scene of the compiled demos, on tabs named in `replaylist.csv` (a label `*` there means all of a script's scenes), with a picture of the scene and its title; each plays on its own and comes back to Replay. A scene is reached by playing its script from the start without showing it (`KAGEnvPlayer.seek`), so what earlier scenes put on KAG's own layers is there (`doc/scn.txt`, "Replays").
- **Dialogue search**: a Search screen in Extras finds the lines read so far that hold a word (or a speaker's name), shows each with its demo and scene, and plays from the one chosen to the end of its scene (`KAGEnvPlayer.searchTexts`; `doc/scn.txt`, "Search").
- `[edit enter=...]` runs an expression when Return is pressed in the field (`doc/kagex.txt`).
- **kagex-release compiles scenarios** (Scenarios > *Compile*, `scenes.compile`, on when the game has a `!scnlist.txt`): it compiles the listed scripts with this computer's engine and ships the compiled files without the scripts. With Scenarios > *Encrypt* (`scenes.encrypt`) the `.scn` files are encrypted (XChaCha20-Poly1305) with the scenes key of the game's keys file (below), and the key is written into each package's scnfile plugin; a platform whose engine has no plugin then fails to build. The same files and key give the same bytes, so a patch holds only the scripts that changed (`doc/scn.txt`, "Releases").
- **Compiled scripts**: kagex-release compiles every `.tjs` in a package to TJS2 bytecode (Contents > *Scripts*, `contents.compileScripts`, on by default), so the packages carry no readable TJS and load their scripts a little faster. The engine on the computer that builds does it (`Scripts.compileStorage`), and each script keeps its name, so the game loads them as before. A script that is one expression, like `envinit.tjs`, is compiled as one, so `Scripts.evalStorage` still returns its value. `@if` is decided when building. Errors in compiled scripts name the script and function but not the line (the engine's debug information crashes it, `UPSTREAM.md`). On Linux and macOS the engine cuts integer constants beyond 32 bits (`0xff000000`) when it compiles; kagex-release puts them right, and keeps as source the few scripts where it can't (a constant made of others, like `0xff << 24`). The build lists every script it keeps as source and why, and the engine's output is `compile-scripts.log`.
- **The keys file**: every key kagex-release uses is in one file, the game's keys file (*Keys*, `keys.file`, or `KAGEX_KEYS_FILE` for CI), with a key of its own for each kind of protection: the archive key, the scenes key and the signing key (an RSA private key, which krkrsign reads out of the file as it is). *Create keys…* in the window or `kagex-release --cli keygen <file>` writes one, or adds the keys an existing file lacks; it never replaces a key without `--force`. The check refuses a keys file inside `data/`, one without a key the settings use, and one whose archive and scenes keys are the same. See `tools/release/README.md`, "The keys file".
- **Signed game files (tamper checking)**: kagex-release can sign a release, and the game checks the signatures before it starts. With signing on, the Windows, Linux, Steam and macOS builds carry RSA-PSS/SHA-256 signatures of the game archive, the engine and its plugins, any extra archives and each patch; `template/system/SignatureCheck.tjs` verifies them at start-up with the `sigcheck` plugin and the public key written into `data.xp3`, and quits with a message naming the file if any is damaged, edited, or signed with a different key. A signed build also refuses the engine's REPL and debug options. The web, Android and iOS builds have no such plugin, so they skip the check and rely on the platform's own integrity. The private key is the signing key of the game's keys file. See `tools/release/README.md`, "Signing".
- kagex-release can split a large game's media into separate signed archives beside `data.xp3` (*Signing > Split large archives*), forced on when a signed build's data would otherwise cross the engine's 2 GB signature-check limit.
- **Encrypted game files**: kagex-release can pack `data.xp3` (and its split parts) with every file encrypted (XChaCha20, keyed per file). The [xp3crypt](https://github.com/krkren/xp3crypt) plugin, built into the engine, decrypts each read through the engine's XP3 extraction filter, so the archive is read transparently; the game's key is written into each platform's engine when it's packaged. Turn it on with `archive.encrypt`; the key is the archive key of the game's keys file. An engine without a key reads a plain archive, so the same build works either way. Keeps the scripts and assets out of plain view; the key ships with the game, so a determined person can still recover it. Every 0.9.0 package's engine has the plugin built in, and kagex-release 0.9.0 is built with xp3crypt and scnfile.
- **Hidden file names** (Encryption > *Hide names*, `archive.hideNames`): the game ships as one encrypted archive, `data.xpc`, whose file names are a keyed hash of each path, so a generic tool sees neither the files nor their names. The engine reads it through the plugin's own `xpcrypt://` storage medium (the built-in XP3 mount matches plain names), with a tiny plain `startup.tjs` that mounts it; the real names live in an encrypted manifest only the plugin reads. Desktop only so far, and not with signing.
- kagex-release uses engine packages in an `engines/` folder next to the game's `data/` (or next to the tool) before downloading, and its check says whether scenarios will compile to `.scn` or `.scn.json` and marks a platform whose engine can't play `.scn` files.
- `tools/smoketest.py --packaged` runs the sample's steps on a desktop package (kagex-release's build of the sample) with the data it holds.
- The engines of every package (Windows, Linux, Steam, macOS, the web, Android and iOS) have xp3crypt built in and the scnfile plugin, and `tools/smoketest.py --encryption required` checks them on each platform.

### Changed

- `-scncompile` keeps the game's window hidden.
- A character drawn from layers blinks and lip-syncs again right after a load (or going back, or a search jump): it used to stand still until the next command on it.
- Extras has four tabs (CG, Replay, Music, Search); the nav buttons moved left to make room.
- EXIT in a scene played from Replay goes back to Replay (it went to the title).
- In compiled scenes the backlog follows the scene player's history: written again after a jump or a load (it used to be wiped), and kept at choices (wiped too), which it shows as "Choice: ..." lines.
- The backlog's voice marks are a line high (42 px), so redrawing a line doesn't cut them off, and the text starts further right (`marginL` 140) to make room for the going-back marks.

### Fixed

- Web builds: a file the engine read while the page's background prefetch was still writing it to the browser's cache came back empty, which could stop the game at start (a compiled script then failed with "Syntax error at line 1"). `kagex-web.js` makes the engine wait for that write.
- The scene player loads: `KAGEnvPlayer.tjs` had a syntax error from the translation, and needed Wamsoft's psbfile plugin. Its history, read tracking and save code had bugs that couldn't show until now.

## 0.8.0

### Added

- **Characters drawn from layers, with blinking eyes and lip-sync**: a World character listed in `charinit.csv` is put together from layers each time it's shown (Wamsoft's "exstand", `KAGEnvCharacterEx.tjs`, which nothing loaded until now). Its outfits, pose variations ("diffs") and faces are sets of layers named in an `_info.txt`, and each World level can have layers drawn at its own size. A face's eyes blink by themselves, and its mouth moves with the character's voice, measured as it plays with the engine's `WaveSoundBuffer.getSoundLevel`, on every platform. Tags hold, open, close or flip the eyes and mouth (`eyecloseto`, `eyeflip=3`, `lipflip=4`...), `x<face>` changes the face with the eyes closed, and `charanim.csv` defines animations (`doc/world.txt`, "Characters Drawn from Layers").
- The World Extension: Animated Character demo, last in the demo menu, with Pip, a character of the sample's own: two outfits, three arm poses, six faces and babbled voice lines. `tools/assets/make_pip.py` draws its layers at each level's size and makes the voices.

### Changed

- Extras on the title screen unlock once the new demo has been played too.

## 0.7.0

### Added

- **Patches and DLC as zip files**: at start the framework loads `patch.zip`, `patch2.zip` and so on from next to the engine and then from the save folder (the one place the web, Android and iOS builds can add files), after the `patch.xp3` archives. Every folder in a zip is searched, so a patch can hold its files in `data/`'s layout. `KAGMountPatchZip(storage)` mounts another one, such as DLC, at any time. Every build has the minizip plugin; the web, Android and iOS builds gained it.
- **CLIP STUDIO PAINT layers as images**: `clip://name.clip/root/folder/layer.bmp` (or `/id/LayerId.bmp`) on KAG and World layers, through the clipfile plugin, which every build now has (`doc/kagex.txt`, "image (Extension)").
- The KAGEX Extended Layer demo shows the emblem as two layers of a CLIP STUDIO PAINT file, turned separately. `tools/assets/make_clip.py` makes the file from the emblem's art.
- kagex-release writes each build's file list (`<file name>-<version>-files.json`, with SHA-256s) and, given an earlier one (`output.patchFrom`, Output > *Patch from*), `patch.zip` with the files that are new or changed since. A patch alone needs no platform or engines.

### Changed

- kagex-release packs a `.clip` or `.psd` file that a script loads layers from (`clip://name.clip/...`, `psd://name.psd/...`), although the default exclusions (`*.clip`, `*.psd`) match it.

## 0.6.0

### Added

- **SVG vector images**: KAG and World layers show `.svg` images as they do bitmaps (`[image layer=0 storage=emblem.svg]`, `[newlay name=badge file=emblem show]`; a name without an extension finds an SVG when no bitmap has that name). The layerExVector plugin (ThorVG) draws them again at each zoom and angle, so they stay sharp. Every build has the plugin; the Android and iOS builds gained it. SVG text isn't drawn: convert it to outlines.
- The KAGEX Extended Layer demo ends with an SVG emblem beside a PNG of the same picture, both zoomed and turned. `tools/assets/make_vector.py` draws the two from one list of shapes.

### Changed

- An `.emf` or `.wmf` image that doesn't load says it needs GDI+ (layerExDraw, which only the Windows-only engine has) and suggests SVG.

## 0.5.0

### Added

- **Twelve more transitions** from the extNagano plugin, which the framework now links: `3duniversal`, `blurfade`, `scanline`, `zoomfade`, `rgbfade`, `spin`, `flutter`, `book`, `imagewipe`, `honeyturn`, `morphing` and `multiripple`, for KAG's `[trans method=...]` and the World's `trans=` (`doc/kagex.txt`, "trans (Extension)"). All the builds have the plugin.
- The World Extension: Transition demo shows them, with two rule images of its own (`data/rule`, drawn by `tools/assets/make_rules.py`): glass shards for `3duniversal` and a brush stroke for `imagewipe`. Its `morphing` is a swirl registered in `envinit.tjs`, since a tag can't hold the triangle arrays.
- kagex-release keeps rule images (`data/rule`) lossless when it converts images to JPEG: a rule's pixel values are timings.

### Changed

- A transition whose plugin didn't load (extrans's or extNagano's) runs as a crossfade, and the console says so, instead of stopping the game with an error.
- `[trans method=rgbfade]` takes `delayr`, `delayg`, `delayb` and `delaya`: KAG lower-cases attribute names, and the plugin reads `delayR` and the like.

### Fixed

- The transition demo's extrans transitions changed nothing on screen: `[env night]` isn't how the World changes the time of day, so each one went from a picture to the same picture. They use the time tags now (`[night trans=wave]`).

## 0.4.0

### Added

- **Effekseer effects**: the `efk` flip type plays [Effekseer](https://effekseer.github.io/) effects (`.efk`, `.efkefc`, `.efkzip`) on World layers (`[newlay name=fx efk=sparkle show]`) and KAG layers (`[image layer=0 flip=sparkle.efk]`), drawn by the krkreffekseer plugin with OpenGL ES. Options set the size (`efkmag`), canvas, start frame, position, tilt and rotation, zoom, speed, colour, looping, triggers and dynamic inputs; `efkstop` lets an effect wind down, and the `efkdone` trigger goes when every effect has ended (`doc/world.txt`, `doc/kagex.txt`). Effects are kept in save data. Without the plugin or OpenGL ES an effect shows nothing (the console says why). `data/effect` is searched for them.
- The sample's Effects demo (in the demo menu) with five effects of its own: glowing petals, sparkles, fireworks, a magic circle and a shockwave. `tools/assets/make_effects.py` makes them, drawing the textures and writing the effects with `efkformat.py`, a Python reader and writer for Effekseer's runtime format. It replaces the fire effect demo, which needed a plugin the SDL engine doesn't have.
- kagex-release keeps the textures and sounds an effect names in their own format, since the effect can't be rewritten to name converted files.
- The Android and web builds include krkreffekseer, as the desktop builds do. The iOS build doesn't yet (Xcode's project generator fails with it, as with krkr_richtext), so effects show nothing there.

### Changed

- A World layer's redraw (a colour change such as `[env grayscale=true]`) no longer restarts a flip whose type says so (`keepOnRedraw`); effects play on through it.

## 0.3.1

### Added

- Web builds offer Add to Home Screen on phones and tablets, where the game then opens full screen: a bar with an Add button where the browser can install the page (Chrome, Edge, Samsung Internet, Opera on Android) and the steps everywhere else (Share, then Add to Home Screen on every iPhone and iPad browser; the browser menu in Firefox and other Android browsers). Closing it hides it for 30 days. The manifest gained an id, a description, `display_override` and separate maskable icons, and the page a favicon.
- Link previews for web builds in Discord, Slack, X, iMessage and the like: Open Graph and Twitter card tags with the title, a description and a 1200x630 preview image (the sample's is its title screen, drawn by `make_ui.py preview`). kagex-release has *Site address*, *Description* and *Preview image* settings for them.

### Fixed

- Web builds kept showing players the old game after an update. The engine caches every game file in the browser (OPFS) for good, and the page and its scripts could come from the browser's cache too. Each build now has an id (in `kagex-build.json` and the page, whose scripts load with it), and `kagex-web.js` checks it before the game starts: a stale page reloads, a new build empties the engine's file cache, and the game's files are checked with the server.
- Buttons didn't highlight in games packaged by kagex-release with images converted to TLG or JPEG: the framework looked for a button's hover, pressed and focus images (`<name>_over`, `_on`, `_focus`) as `.png`, `.tlg5`, `.tlg6` or `.bmp` only, and converted images are `.tlg` or `.jpg`. It now tries every image format the engine reads. kagex-release refuses TLG and JPEG for a game whose framework (`data/system`) predates this.
- The sample's CG screen shrank the whole CG instead of using its prepared thumbnail once the thumbnail had been converted.

## 0.3.0

### Added

- **kagex-release**, a tool that packages a game for Windows, Linux, Linux for Steam, macOS, the web, Android and iOS (`tools/release`, shipped as `tools/kagex-release` in the Windows and Linux packages and as a download of its own for each system). It opens a window with the settings, which it keeps in `release.json` next to `data/`, and runs from the command line too (`--cli build`).
  - Identity: title, short name, file name, version, copyright, the save folder's names (`orgname`/`appname`; the sample's and the engine's defaults are refused) and one 1024x1024 icon that each platform gets in its own sizes and formats.
  - Windows: the exe renamed, with the game's icon and version info (when the tool runs on Windows), and the data as `data.xp3`, a folder, or bound into the exe. Linux and Steam: the same as a tar.gz, with a desktop entry. macOS: `<title>.app` with the game's bundle ID and icon, signed ad hoc or with a Developer ID and notarized, as a zip or a dmg. Web: the site with the game's files fetched on demand, or one preloaded `data.xp3`, titled and with the home-screen manifest and icons. Android: an APK or an app bundle with the game's application ID, name and icon, built by Gradle from a prebuilt engine (a JDK and the Android SDK, no NDK), signed with your keystore. iOS: an `.ipa` signed with your certificate and provisioning profile, or an app for the Simulator.
  - Media: WAV and FLAC to Opus (by folder: 128 kbps music, 96 sound effects, 64 voices) or Ogg Vorbis, with `.sli` loop points carried over; PNG, BMP and TLG to TLG6, TLG5, PNG or JPEG (with a lossless mask for transparent images). Lossy files are never converted again; files the scripts name with their extension are kept, or their names rewritten. Conversions are cached.
  - It shows what this computer can build for each platform and why not, writes `SHA256SUMS`, and test-runs this computer's build headless, reporting script errors.
- Engine packages for it in each release (`kagex_engine_<platform>.zip`), made from the release builds.

### Changed

- The framework also looks for `.opus` sounds where a script names one without its extension (BGM, sound effects and voices). The engine played Opus, but only `.wav` and `.ogg` were looked for.

### Fixed

- The Android app was named "krkrz" on Japanese and Chinese phones: krkrz_android names it in those languages too, and only the default name was replaced.

## 0.2.2

### Added

- The web demo can be added to a phone's home screen and then opens without the browser's bars: a web app manifest (full screen, landscape) for Android and the home-screen tags for iPhones, whose browsers can't put a page in full screen. Icons drawn by `tools/assets/make_ui.py icons` into `platform/web`; the page is titled with the game's name.

### Fixed

- In the browser and iOS builds the bottoms of g, j, p, q and y (and the shadow under them) were cut off in the message window: the line layer's padding only grew for krkr_richtext's text. It now also grows for the engine's own text drawing.

## 0.2.1

### Fixed

- The web demo on GitHub Pages didn't start:
  - The engine reads its file list from `gamedata/krkrz_files.json`, which only the kit's `serve.py` answered. The web build now has the file there too, so it runs from any static host.
  - On a first visit, coi-serviceworker sometimes reloaded the page before its service worker was ready, which left the page without the cross-origin isolation the engine's threads need until the next reload. The reload now waits for the worker.
  - The Pages deploy makes both changes to 0.2.0's site, then runs the browser smoke test on the live site. The smoke test in the platform builds serves the site with a plain static server, as Pages does.
- In the browser build every text in the game font came out as arrows. The engine bundles Noto Sans JP there and finds a bundled font only in the style asked for, so the bold choices of the demo menu, the first text drawn, left the font on the engine's icon font. Where the engine has a font of that name, `Initialize.tjs` now loads the game's copy of it, which is found for bold text too.
- In the browser build the CG and Replay thumbnails were empty frames: its Photoshop-style blends (`omPs*`) write alpha 0. `setCGImage` keeps the frame's alpha, as the save slots already did.
- The smoke test checks that the demo menu's choices measure as text and that the first CG and Replay tiles are opaque.

## 0.2.0

### Added

- Packages for more platforms, built with Wamsoft's platform kits from the settings in `linux-config.json`, `web-config.json`, `app-config.json` and `ios-config.json`, and for macOS with krkrz_dev's own build:
  - Linux, Steam-ready: built in Valve's Steam Linux Runtime 3.0 (sniper), so it runs on older distributions too, with a desktop entry and an icon.
  - The web: the sample runs in the browser at [krkren.github.io/kagex](https://krkren.github.io/kagex/), and the site comes as a zip to run locally.
  - Android: an APK for Android 10 and later (arm64 and x86_64), signed with a debug key.
  - iOS: an app for the iOS Simulator. A build for iPhones and iPads needs an Apple Developer account.
  - macOS: `KAGEX.app` for Apple silicon, signed ad hoc.
- `.github/workflows/platforms.yml` builds all of them and smoke-tests each one: `tools/smoketest.py --target` drives the Android emulator, the iOS Simulator and headless Chromium as well as the desktop engine. `.github/workflows/pages.yml` puts each release's web build on GitHub Pages.
- App icons, drawn by `tools/assets/make_ui.py icons` into `platform/`.

### Changed

- `data/startup.tjs` runs `data/system/Initialize.tjs` when there is one, so a package can carry the framework inside `data/` (the browser and phone builds have nothing outside it). In this repository the framework stays in `template/system`.
- The web and iOS builds draw text with the engine's own renderer: krkr_richtext doesn't build for them at engine 2.6.5, so their text isn't kerned.

### Fixed

- Saving a game (framework): a PNG thumbnail is shorter than the room kept for it, and the save data goes after that room. Where the save folder can't be written past the end of a file or isn't a local folder (the browser and phone builds), every save failed with "Could not save to file", starting with the title screen's own. The file is now grown to the right size first, or put together in a temporary file and copied over.
- Return and Space close the About screen (framework) even when its Close button doesn't have the keyboard focus. On Android the button lost the focus as soon as the screen opened, so only a tap closed it.

## 0.1.1

### Fixed

- The message window's top corners: the highlight along its top was drawn over the rounded border, so the inside of both corners came out pale. It now stays inside the border.
- The message window and the choices are see-through again. Their shadow was drawn under the whole panel and showed through it, so they were solid except for a lighter strip inside the top and left edges.
- Replay showed the Character demo's scene as a "?", like a locked one, although it could be played. It has a thumbnail now, and an unlocked scene without one shows a play button.

## 0.1.0

### Changed

- The sample's screens are redrawn at 1920x1080 in the look of the Yes/No dialogs: lavender panels, violet borders and hard shadows, and labels in Noto Sans. That covers the title screen (now with Ai and a KAGEX logo), the logo screen, the message window and its buttons, the choices, the click-wait marks, the config, save and load screens, CG Mode, Replay, Music and the message history. Until now most of these were placeholders or 800x600 art resized 1.8x.
- The character sprites, the two backgrounds and the CG are upscaled from the original art with Real-ESRGAN instead of being resized, so their lines are sharp.
- The speaker's name is shown in a name box on the message window's top edge, without the brackets; the message history still brackets it. Saves from earlier versions load with the old message window layout, until the next scene starts.
- The config screen is laid out in two panels, with Default next to Title and Return. The Extras screens' tabs mark the open screen, and the title's Extra button is faded while it's locked.

### Added

- `[position nameframe=...]` (framework): an image drawn behind the name window's text. The name window takes the image's size; `namealign=0 namevalign=0` centre the name on it. `doc/kagex.txt` now lists the name window's `[position]` attributes.
- `tools/assets/`: the scripts that make the sample's images. `make_ui.py` draws the UI, `upscale.py` rebuilds the sprites and backgrounds from the original art in `tools/assets/src` (Real-ESRGAN in NumPy, no PyTorch).

### Fixed

- Pointing at a save or load slot didn't highlight it: the slot's normal image was drawn over its highlighted one.
- The message history's scroll bar wasn't lined up under its page buttons.

## 0.0.5

### Fixed

- A game made from `template/` stopped at start-up with `Member "menu" does not exist` on the SDL engine.
- Games made from the template now get the in-window Yes/No prompts and About screen too; they used to open a separate OS window for every prompt, and the old About window crashed on Linux.
- Closing a Yes/No prompt without picking an answer (Esc, a right-click on it or outside it) answers No. It used to close the prompt without calling either answer's function.
- A Yes/No prompt during a movie threw "not implemented" on the SDL engine: its separate shaped window needs `setMaskRegion`, which only the Windows-only engine has. On the SDL engine it is drawn in the game window like the others.
- A Yes/No question before the game window exists (an error during start-up) uses the system's message box, since the SDL engine can't open the stock dialog window then.
- `[button group=...]` with a group name never set up the radio group.
- Switching to a bitmap font set the default face to `MS Gothic`, which draws as arrows on Linux once the bitmap font is cleared.
- `[mapselopt buttonwidth=...]` never applied (it was checked as `btnwidth`).
- Stand images from `.psd` files didn't load: the plugin is `psdfile` now, not `psd.dll`. The TLG export in `psdlayer.tjs` passed a misspelled file name.
- Japanese text no longer needs a Japanese font on the player's computer. Noto Sans JP ships in `template/system` (SIL OFL 1.1, `notosansjp-OFL.txt`) and is registered at start-up; before, without Noto Sans CJK installed, Japanese showed as boxes on Linux. Yu Gothic still comes first where it's installed, and saves holding the old default font list get the new one.
- Games made from the template were still laid out for 640x480 in places: the message history's buttons were 20 px tall with arrow glyphs for captions on Linux, and choices without images defaulted to 400x50. The history now has 48 px buttons in the game font, and choices default to 720x90.
- The template's `Config.tjs` had an empty `config_version`, so the version check loaded `UpdateConfig.tjs` at every start-up. When it does carry settings over (with a `Config.~new`), it writes them to `Config.tjs.merged` in the save folder, since the SDL engine has no Pad window to show them in.
- The KAGEX log mode (Debug menu) threw `Pad` not found on the SDL engine, including at start-up when it had been left on. It now logs to the console only.
- The Standing Sprite window (a second OS window) no longer reopens at every start-up on the SDL engine because it was open last time.
- Loading an `.emf`/`.wmf` image without GDI+ says it needs the layerExDraw plugin, instead of `GdiPlus` not found.

### Added

- Controller: Y switches auto mode, R1 skips to the next choice or unread text, holding R2 skips like Ctrl, and the left stick moves like the D-pad. In the sample, START opens the config screen, BACK the save screen and L1 the load screen. `-padbtn11` and `-padbtn12` work.
- In KAG's debug mode, Shift+F12 shows the debug window and Shift+F11 switches the debug level, since the SDL engine has no Debug menu. Debug mode is on unless the engine gets `-debugwin=no` (a line `debugwin=no` in `krkrz.cf`), which a released game should set.

### Changed

- Extras unlock once all five demos have been played to the end. The sample used to force them on at every start-up.
- On Linux, saves go to `~/.local/share/krkren/kagex/` (`krkrz.cf` next to the engine sets `orgname`/`appname`) instead of the `~/.local/share/wamsoft/krkrz/` every game on the stock engine shares. To keep saves from earlier versions, move them from the old folder. Windows still saves to `savedata/`.
- The Yes/No and About code and the four dialog images moved from the sample (`data/main/MyYesNoDialog.tjs`, `Override.tjs`, `data/image`) to `template/system/YesNoDialogLayer.tjs`. The About screen also shows the engine version. `aboutInWindow = false` brings back the old About window.
- `tools/smoketest.py` runs the sample and the template headless and checks the title, the demos, save and load, the system and Extras screens, the prompts and the controller; GitHub Actions runs it on every pull request with the engine from the newest release.

## 0.0.4

### Fixed

- Word wrap: after the first wrap that overflowed the message box, every later wrap became a click-to-continue page break with a blank line, and the next page started with a space. A wrap now breaks the page once and carries on normally.
- Word wrap: a line whose only spaces were inside tags (`Wait![wait time=500]`) could crash it before any other line had wrapped.
- Word wrap: two identical lines in a row, and text after a load onto the same line, lost word wrapping; under `[notextmode]` or a no-display skip it could still raise page breaks.
- Letters that hang below the line (g, j, p, q, y) and their shadow were cut off at the bottom of each message line when krkr_richtext draws the text.
- The window/full-screen choice is remembered between launches (the first launch is still full screen), and a windowed start fits the display instead of opening 1920x1080.
- On Linux, the Config screen's Window/Full screen buttons showed the previous mode until a second click, and showed Window at start-up while the game was full screen: the engine switches asynchronously, and the mode was read back too early.
- The Replay screen unlocks a scene once it has been played, instead of only in debug mode.
- The Config screen's Title button failed to load a missing dialog image.
- Music Mode's first track didn't play on Linux (file name case), and two tracks that don't exist were listed.
- Yes/No prompts are redesigned at 1920x1080 and drawn in the game's font for every message, including the save-data and scenario-changed prompts that used to fall back to a separate window with no usable font. The title prompt is in English.
- The message history's text ran under its page buttons (its right margin was overridden in `Config.tjs`), and it didn't scroll with trackpads or high-resolution wheels.
- The save/load and CG/Replay screens freed their thumbnail layers, and CG thumbnails are shrunk smoothly instead of with nearest-neighbour.
- Remaining 800x600 settings: the default message window, `scPositionX`, the logo screen, the About window.
- Plugin link failures are logged instead of hidden; `[scenestart]` explains that it needs the psbfile plugin.

### Changed

- The template's `Config.tjs` is set up for 1920x1080 (message window, text and history sizes, thumbnails), uses Ogg/WAV BGM and the same face list as the sample.
- `template/main/` has commented starting points for `Override.tjs`, `AfterInit.tjs` and `Storages.tjs`.
- The About screen (F1) shows this sample's name and version, and opens inside the game window instead of a second OS window, which crashed the game on Linux.
- Docs: setup notes, `data/readme.txt` and `doc/` updated for the SDL3 port; the README lists what the SDL3 build doesn't support.

### Removed

- The per-message dialog images (`dialog_*_base`) and the `dialog_yes/no_*` buttons, replaced by `dialog_base`, `dialog_wide_base` and `dialog_button_normal/over` with the text drawn at run time, and nine unused 800x600 images.
- `template/update_auto_copy_vars.bat`.

## 0.0.3

- Windows text uses Yu Gothic instead of MS Gothic, fixing English spacing; saves from earlier versions pick up the new default font.
- The choice menu and history log are drawn with krkr_richtext, like the message window, and word wrap measures words as they are drawn.
- krkr_richtext approximates the edge strength and shadow blur settings.
- Fixed `Member "biMinimize" does not exist` when switching between full screen and a window.

## 0.0.2

- 1920x1080.
- krkr_richtext text rendering.

## 0.0.1

- First SDL3 package (tagged `release`).
