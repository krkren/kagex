Engine args: `-datapath=savedata/ -replfile=/home/runner/work/kagex/kagex/smoke/ci-chan`

| Step | Result | s | Note |
|---|---|---|---|
| boot: REPL channel answers | PASS | 1.1 | REPL channel up |
| kag window created | PASS | 0.8 | kag exists |
| SDL window opened | PASS | 0 | no window-creation error in the log |
| load CI helpers | PASS | 0.1 | ok |
| engine / plugin / font info | PASS | 0.1 | System.platformTag => linux / System.versionString => 2.6.5.0 / System.getArgument('-drawdevice') => void / Scripts.getClassNames(kag.drawDevice).join(',') => SDLOGLDrawDevice / typeof global.CSVParser => Object / typeof global.RichText => Object / kag.fore.messages[0].useRichText => 1 / font MS Gothic => unresolved / font Roboto => resolved, width('Hあ')=35 |
| logo -> title screen | PASS | 6.5 | 01-title.png; buttons: start@150,520/400x68 continue@150,604/400x68 extra@150,688/400x68 config@150,772/400x68 exit@150,856/400x68 |
| title: START -> demo menu | PASS | 2.2 | clicked start (game 350,554 -> window 262,415); 02-demo-menu.png; 7 choices |
| demo: KAGEX layer | PASS | 27.4 | 'KAGEX Extended Layer': 31 clicks back to the menu (choice game 960,231 -> window 720,173) |
| vector: an SVG image draws | PASS | 1 | SVG emblem drawn turned: 2073 opaque samples |
| clip and zip: a CLIP STUDIO PAINT layer, a DLC zip | PASS | 0.2 | clip:// badge layer: 2085 opaque samples; a zip written to the save folder mounted and ran |
| demo: World transitions | PASS | 54.9 | 'World Extension: Transition': 25 clicks back to the menu (choice game 960,468 -> window 720,351) |
| transitions: their plugins loaded | PASS | 0.1 | extrans and extNagano loaded |
| demo: Effekseer effects | PASS | 18.8 | 'Effekseer Effects': 11 clicks back to the menu (choice game 960,626 -> window 720,469); effects drawn |
| demo: Animated character | PASS | 35.8 | 'World Extension: Animated Character': 22 clicks back to the menu (choice game 960,705 -> window 720,528) |
| animated: Pip blinks and lip-syncs | PASS | 38.1 | Pip drawn (959 samples); eyes closed and open: Ee; mouth closed and open while the voice played: Ll (53 samples at 45 positions, from level); 21 clicks back to the menu |
| compiled: the demos play compiled | PASS | 0.1 | the demo menu and the demos were compiled, and the scene player played them |
| history: no word split across lines | PASS | 0.2 | 130 history lines; 7 breaks between letters, none inside a word |
| in game: message window + rich text | PASS | 6 | 33-ingame.png; richTextApp ready; faces: 'Noto Sans JP,Roboto' -> [Noto Sans JP, Roboto]; 'Yu Gothic Medium,Yu Gothic,Noto Sans JP,Roboto' -> [Noto Sans JP, Roboto]; buttons: msg_save@904,732/124x42 msg_load@1036,732/124x42 msg_back@1168,732/124x42 msg_skip@1300,732/124x42 msg_auto@1432,732/124x42 msg_log@1564,732/124x42 msg_config@1696,732/124x42 |
| history log (msg_log) | PASS | 1.9 | clicked msg_log (game 1626,753 -> window 1219,564); 34-history.png; closed by right-click (window 720,405) |
| quit | PASS | 0.2 | exit code 0 |
| engine log | PASS | 0 | 0 unexpected script exception(s); 0 expected caught exception(s) (optional plugins, time-of-day backgrounds); 0 engine warning(s); 0 failed capture(s) |
