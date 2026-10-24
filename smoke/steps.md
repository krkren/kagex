Engine args: `-datapath=savedata/ -replfile=D:\a\kagex\kagex\smoke\ci-chan`

| Step | Result | s | Note |
|---|---|---|---|
| boot: REPL channel answers | PASS | 2.7 | REPL channel up |
| kag window created | PASS | 0.1 | kag exists |
| SDL window opened | PASS | 0 | no window-creation error in the log |
| load CI helpers | PASS | 0.2 | ok |
| engine / plugin / font info | PASS | 0.2 | System.platformTag => windows / System.versionString => 2.6.5.0 / System.getArgument('-drawdevice') => void / Scripts.getClassNames(kag.drawDevice).join(',') => SDLOGLDrawDevice / typeof global.CSVParser => Object / typeof global.RichText => Object / kag.fore.messages[0].useRichText => 1 / font MS Gothic => resolved, width('Hあ')=30 / font Roboto => resolved, width('Hあ')=35 |
| logo -> title screen | PASS | 7.9 | 01-title.png; buttons: start@150,520/400x68 continue@150,604/400x68 extra@150,688/400x68 config@150,772/400x68 exit@150,856/400x68 |
| title: START -> demo menu | PASS | 2.2 | clicked start (game 350,554 -> window 350,554); 02-demo-menu.png; 5 choices |
| demo: World transitions | PASS | 22.4 | 'World Extension: Transition': 12 clicks back to the menu (choice game 960,558 -> window 960,558) |
| history: no word split across lines | PASS | 0.1 | 12 history lines; 11 breaks between letters, none inside a word |
| in game: message window + rich text | PASS | 8.7 | 06-ingame.png; richTextApp ready; faces: 'Yu Gothic Medium,Yu Gothic,Noto Sans JP,Roboto' -> [Yu Gothic Medium, Yu Gothic, Noto Sans JP, Roboto]; 'Yu Gothic UI,Roboto' -> [Yu Gothic UI, Roboto]; buttons: msg_save@1036,732/124x42 msg_load@1168,732/124x42 msg_skip@1300,732/124x42 msg_auto@1432,732/124x42 msg_log@1564,732/124x42 msg_config@1696,732/124x42 |
| history log (msg_log) | PASS | 1.9 | clicked msg_log (game 1626,753 -> window 1626,753); 07-history.png; closed by right-click (window 960,540) |
| quit | PASS | 0.2 | exit code 0 |
| engine log | PASS | 0 | 0 unexpected script exception(s); 4 expected caught exception(s) (optional plugins, time-of-day backgrounds); 2 engine warning(s); 0 failed capture(s) |
