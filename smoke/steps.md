Engine args: `-datapath=savedata/ -replfile=D:\a\kagex\kagex\smoke\ci-chan`

| Step | Result | s | Note |
|---|---|---|---|
| boot: REPL channel answers | PASS | 5.7 | REPL channel up |
| kag window created | PASS | 0.2 | kag exists |
| SDL window opened | PASS | 0 | no window-creation error in the log |
| load CI helpers | PASS | 0.2 | ok |
| engine / plugin / font info | PASS | 0.2 | System.platformTag => windows / System.versionString => 2.6.5.0 / System.getArgument('-drawdevice') => void / Scripts.getClassNames(kag.drawDevice).join(',') => SDLOGLDrawDevice / typeof global.CSVParser => Object / typeof global.RichText => Object / kag.fore.messages[0].useRichText => 1 / font MS Gothic => resolved, width('Hあ')=30 / font Roboto => resolved, width('Hあ')=35 |
| logo -> title screen | PASS | 9.6 | 01-title.png; buttons: start@150,520/400x68 continue@150,604/400x68 extra@150,688/400x68 config@150,772/400x68 exit@150,856/400x68 |
| title: START -> demo menu | PASS | 3.1 | clicked start (game 350,554 -> window 350,554); 02-demo-menu.png; 7 choices |
| demo: KAGEX layer | PASS | 48.9 | 'KAGEX Extended Layer': 31 clicks back to the menu (choice game 960,231 -> window 960,231) |
| vector: an SVG image draws | PASS | 1.2 | SVG emblem drawn turned: 2073 opaque samples |
| clip and zip: a CLIP STUDIO PAINT layer, a DLC zip | PASS | 0.3 | clip:// badge layer: 2085 opaque samples; a zip written to the save folder mounted and ran |
| demo: World transitions | PASS | 73.5 | 'World Extension: Transition': 25 clicks back to the menu (choice game 960,468 -> window 960,468) |
| transitions: their plugins loaded | PASS | 0.1 | extrans and extNagano loaded |
| demo: Effekseer effects | PASS | 29.3 | 'Effekseer Effects': 11 clicks back to the menu (choice game 960,626 -> window 960,626); effects drawn |
| demo: Animated character | PASS | 61 | 'World Extension: Animated Character': 22 clicks back to the menu (choice game 960,705 -> window 960,705) |
| animated: Pip blinks and lip-syncs | PASS | 65.7 | Pip drawn (959 samples); eyes closed and open: Ee; mouth closed and open while the voice played: L (317 samples at 1 positions, from level); the voice did not play, so the mouth was not checked; 21 clicks back to the menu |
| compiled: the demos play compiled | PASS | 0.2 | the demo menu and the demos were compiled, and the scene player played them |
| history: no word split across lines | PASS | 0.4 | 128 history lines; 57 breaks between letters, none inside a word |
| in game: message window + rich text | PASS | 11.2 | 33-ingame.png; richTextApp ready; faces: 'Yu Gothic Medium,Yu Gothic,Noto Sans JP,Roboto' -> [Yu Gothic Medium, Yu Gothic, Noto Sans JP, Roboto]; 'Yu Gothic UI,Roboto' -> [Yu Gothic UI, Roboto]; buttons: msg_save@904,732/124x42 msg_load@1036,732/124x42 msg_back@1168,732/124x42 msg_skip@1300,732/124x42 msg_auto@1432,732/124x42 msg_log@1564,732/124x42 msg_config@1696,732/124x42 |
| history log (msg_log) | PASS | 2.4 | clicked msg_log (game 1626,753 -> window 1626,753); 34-history.png; closed by right-click (window 960,540) |
| quit | PASS | 0.5 | exit code 0 |
| engine log | PASS | 0 | 0 unexpected script exception(s); 12 expected caught exception(s) (optional plugins, time-of-day backgrounds); 2 engine warning(s); 0 failed capture(s) |
