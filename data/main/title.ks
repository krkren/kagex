*init|Title

[eval exp='tf.recollect = 0']

[startanchor]



*start|

[disablestore]

[clickskip enabled=true]

[cancelskip]

[cancelautomode]

[linemode]

[rclick enabled=false]

[history enabled=false]

[stoprecollection]

[clearhistory]



*dispstart



; Various initialization

[init]

[clearlayers]

; the music room's track kept as the title's music, or none (Override.tjs)

[eval exp="titleMusicStart()"]

[stopvideo]

[video visible=false]



; Flag variable initialization



; Forced transition to recollection mode

[if exp="tf.recollect"]

[eval exp='tf.recollect = 0']

[position page=fore layer=message1 frame="" left=0 top=0 width=8 height=8 visible=false]

[position page=fore layer=message0 frame="" opacity=0 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=false]

[current page=fore layer=message0]

[jump storage="replay.ks"]

[endif]



*titleloop
; the message window's quick menu is the story's (AfterInit.tjs)
[eval exp="f.quickMenu = false"]



[stoptrans]

[backlay]

[position page=back layer=message1 frame="" left=0 top=0 width=1920 height=1080 visible=false]

[position page=back layer=message0 frame="&titlePicture()" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true]

[current page=back layer=message0]



; Button layout

[locate x=150 y=520]

[button name="start" target=*gamestart]

[locate x=150 y=604]

[button name="continue" storage=load.ks target=*startFromTitle]



; Change display based on clear flag

[locate x=150 y=688]

[if exp="sf.clear || tf.allseen"]

[button name="extra" target=*extra]

[else]

[button name="extra" disabled halftone=true]

[endif]

[locate x=150 y=772]

[button name="config" storage=config.ks  target=*startFromTitle]

[locate x=150 y=856]

[button name="exit" exp='kag.close()']

; the arrows that pick the title's picture, once a second one is unlocked

[if exp="titlePictures().count > 1"]

[locate x=1712 y=984]

[button name="title_prev" exp="nextTitlePicture(-1)" target=*titleloop]

[locate x=1800 y=984]

[button name="title_next" exp="nextTitlePicture(1)" target=*titleloop]

[endif]



; Ai's greeting in a bubble beside her: by the time of day, the date, the visit (since 0.24.0;
; titleGreeting in Override.tjs, greetings.csv)

[eval exp="titleGreeting()"]

[trans screen method=crossfade time=300]

[wt]

[current layer=message0 page=fore]

; the greeting's voice, where greetings.csv gives one (since 0.24.0)

[eval exp="titleGreetingVoice()"]

; The first time in a run, offer to carry on where the game left off (Override.tjs)

[eval exp="offerContinue()"]

; Esc, Android's Back or the right button asks whether to quit, as Exit does (since 0.21.0: on a
; phone Back is the way out). Not on the web, where Back leaves the page
[rclick enabled=true jump=true storage="title.ks" target=*askquit cond="!(typeof System.platformTag != 'undefined' && System.platformTag == 'web')"]

[s]



*askquit

[eval exp="kag.close()"]

[s]



*extra

[jump storage="chart.ks" cond='sf.extramode == 6']

[jump storage="glossary.ks" cond='sf.extramode == 5']

[jump storage="searchmode.ks" cond='sf.extramode == 4']

[jump storage="musicmode.ks" cond='sf.extramode == 3']

[jump storage="replay.ks"    cond='sf.extramode == 2']

[jump storage="cgmode.ks"]



*backtotitle

[rclick enabled=false]

; the music room's track stops, unless it's kept as the title's music

[eval exp="extrasLeave()"]

[stoprecollection]

[jump target=*titleloop]



*gamestart

[stoptrans]

[clearlayers page=back]

[trans screen method=crossfade time=500]

[wt]

; the hero's name: the player's from before, or the name screen the first time (namescreen.ks)

[eval exp="heroFromSf()"]

[jump storage=namescreen.ks target=*start cond="!sf.heroNamed"]

[jump storage=s0001.ks]