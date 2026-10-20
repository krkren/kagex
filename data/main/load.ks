;

; Load Screen

;



; Call from in-game

*startFromGame

[locksnapshot]

[eval exp='tf.fromTitle = 0']

[rclick enabled=true jump=true storage="" target=*backtogame]

[history enabled=false]

[jump target="*buttons"]



; Call from title

*startFromTitle

[eval exp='tf.fromTitle = 1']

[rclick enabled=true jump=true storage="" target=*backtotitle]



*buttons



; Load base image

[stoptrans]

[backlay]

[position layer=message1 frame="load_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true  transparent=false page=back]

[current layer=message1 page=back]



; Page layout

[locate x=921 y=74]

[button name="page1" exp="setLoadPageButton(1)"]

[locate x=977 y=74]

[button name="page2" exp="setLoadPageButton(2)"]

[locate x=1033 y=74]

[button name="page3" exp="setLoadPageButton(3)"]

[locate x=1089 y=74]

[button name="page4" exp="setLoadPageButton(4)"]

[locate x=1145 y=74]

[button name="page5" exp="setLoadPageButton(5)"]

[locate x=1201 y=74]

[button name="page6" exp="setLoadPageButton(6)"]

[locate x=1257 y=74]

[button name="page7" exp="setLoadPageButton(7)"]

[locate x=1313 y=74]

[button name="page8" exp="setLoadPageButton(8)"]

[locate x=1369 y=74]

[button name="page9" exp="setLoadPageButton(9)"]



; Save data frame

; 1st Column

[locate x=290 y=190]

[button name="load0" normal="sl_win_base" exp="loadAction(0)"]

[locate x=290 y=358]

[button name="load1" normal="sl_win_base" exp="loadAction(1)"]

[locate x=290 y=526]

[button name="load2" normal="sl_win_base" exp="loadAction(2)"]

[locate x=290 y=694]

[button name="load3" normal="sl_win_base" exp="loadAction(3)"]

[locate x=290 y=862]

[button name="load4" normal="sl_win_base" exp="loadAction(4)"]



; 2nd Column

[locate x=980 y=190]

[button name="load5" normal="sl_win_base" exp="loadAction(5)"]

[locate x=980 y=358]

[button name="load6" normal="sl_win_base" exp="loadAction(6)"]

[locate x=980 y=526]

[button name="load7" normal="sl_win_base" exp="loadAction(7)"]

[locate x=980 y=694]

[button name="load8" normal="sl_win_base" exp="loadAction(8)"]

[locate x=980 y=862]

[button name="load9" normal="sl_win_base" exp="loadAction(9)"]



; Return button

[locate x=1476 y=74]

[if exp="tf.fromTitle == 1"]

[button name="return" target=*backtotitle]

[else]

[button name="return" target=*backtogame]

[endif]



; Start dialog processing

[eval exp='setLoadPageButton()']

[trans method=crossfade time=300]

[wt]

[current layer=message1 page=fore]

[s]



*backtogame

[rclick jump=false]

[stoptrans]

[backlay]

[position layer=message1 page=back visible=false frame="" left=0 top=0 width=8 height=8]

[trans method=crossfade time=300]

[wt]

[current layer=message0]

[history enabled=true]

[unlocksnapshot]

[return]



*backtotitle

[rclick enabled=false jump=false]

[jump storage="title.ks" target=*backtotitle]