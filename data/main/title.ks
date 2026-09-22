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

[stopbgm]

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



[stoptrans]

[backlay]

[position page=back layer=message1 frame="" left=0 top=0 width=1920 height=1080 visible=false]

[position page=back layer=message0 frame="title" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true]

[current page=back layer=message0]



; Button layout

[locate x=811 y=500]

[button name="start" target=*gamestart]

[locate x=811 y=572]

[button name="continue" storage=load.ks target=*startFromTitle]



; Change display based on clear flag

[locate x=811 y=644]

[if exp="sf.clear || tf.allseen"]

[button name="extra" target=*extra]

[else]

[button name="extra" disabled]

[endif]

[locate x=811 y=716]

[button name="config" storage=config.ks  target=*startFromTitle]

[locate x=811 y=788]

[button name="exit" exp='kag.close()']



[trans method=crossfade time=300]

[wt]

[current layer=message0 page=fore]

[s]



*extra

[jump storage="musicmode.ks" cond='tf.extramode == 3']

[jump storage="replay.ks"    cond='tf.extramode == 2']

[jump storage="cgmode.ks"]



*backtotitle

[rclick enabled=false]

[stoprecollection]

[jump target=*titleloop]



*gamestart

[stoptrans]

[clearlayers page=back]

[trans method=crossfade time=500]

[wt]

[jump storage=s0001.ks]