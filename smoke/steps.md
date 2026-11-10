Engine args: `-datapath=savedata/ -replfile=/home/runner/work/kagex/kagex/smoke/ci-chan`

| Step | Result | s | Note |
|---|---|---|---|
| boot: REPL channel answers | PASS | 4 | REPL channel up |
| kag window created | PASS | 0.1 | kag exists |
| SDL window opened | PASS | 0 | no window-creation error in the log |
| load CI helpers | PASS | 0.2 | ok |
| engine / plugin / font info | PASS | 0.1 | System.platformTag => linux / System.versionString => 2.6.5.0 / System.getArgument('-drawdevice') => void / Scripts.getClassNames(kag.drawDevice).join(',') => SDLOGLDrawDevice / typeof global.CSVParser => Object / typeof global.RichText => Object / kag.fore.messages[0].useRichText => 1 / font MS Gothic => unresolved / font Roboto => resolved, width('Hあ')=35 |
| logo -> title screen | PASS | 21.8 | 01-title.png; buttons: start@150,520/400x68 continue@150,604/400x68 extra@150,688/400x68 config@150,772/400x68 exit@150,856/400x68 |
| title: START -> demo menu | PASS | 4.8 | clicked start (game 350,554 -> window 350,554); 02-name-screen.png; clicked name_ok (game 1494,500 -> window 1494,500); 03-demo-menu.png; 9 choices |
| demo: KAGEX layer | PASS | 52.9 | 'KAGEX Extended Layer': 40 clicks back to the menu (choice game 960,215 -> window 960,215) |
| vector: an SVG image draws | PASS | 1.1 | SVG emblem drawn turned: 2073 opaque samples |
| clip and zip: a CLIP STUDIO PAINT layer, a DLC zip | PASS | 0.2 | clip:// badge layer: 2085 opaque samples; a zip written to the save folder mounted and ran |
| demo: World transitions | PASS | 63.3 | 'World Extension: Transition': 26 clicks back to the menu (choice game 960,404 -> window 960,404) |
| transitions: their plugins loaded | PASS | 0.1 | extrans and extNagano loaded |
| demo: Effekseer effects | PASS | 33.7 | 'Effekseer Effects': 18 clicks back to the menu (choice game 960,531 -> window 960,531); effects drawn |
| demo: Animated character | PASS | 89.6 | 'World Extension: Animated Character': 36 clicks back to the menu (choice game 960,594 -> window 960,594) |
| animated: Pip blinks and lip-syncs | PASS | 89.8 | Pip drawn (959 samples); eyes closed and open: Ee; mouth closed and open while the voice played: Ll (57 samples at 35 positions, from level); 35 clicks back to the menu |
| compiled: the demos play compiled | PASS | 0.1 | the demo menu and the demos were compiled, and the scene player played them |
| history: no word split across lines | PASS | 0.1 | 207 history lines; 7 breaks between letters, none inside a word |
| in game: message window + rich text | PASS | 9.7 | 44-ingame.png; richTextApp ready; faces: 'Noto Sans JP,Noto Serif JP,Roboto' -> [Noto Sans JP, Noto Serif JP]; 'Noto Sans JP,Roboto' -> [Noto Sans JP, Roboto]; 'Yu Gothic Medium,Yu Gothic,Noto Sans JP,Roboto' -> [Noto Sans JP, Roboto]; buttons: |
| history log (msg_log) | PASS | 2.4 | clicked msg_log (the quick menu's backlog: game 1706,1000 -> window 1706,1000); 45-history.png; closed by right-click (window 960,540) |
| quit | PASS | 0.4 | exit code 0 |
| engine log | PASS | 0 | 0 unexpected script exception(s); 0 expected caught exception(s) (optional plugins, time-of-day backgrounds); 0 engine warning(s); 0 failed capture(s) |
