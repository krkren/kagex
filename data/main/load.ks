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

[locate x=878 y=78]

[button name="page1" exp="setLoadPageButton(1)"]

[locate x=940 y=78]

[button name="page2" exp="setLoadPageButton(2)"]

[locate x=1002 y=78]

[button name="page3" exp="setLoadPageButton(3)"]

[locate x=1064 y=78]

[button name="page4" exp="setLoadPageButton(4)"]

[locate x=1126 y=78]

[button name="page5" exp="setLoadPageButton(5)"]

[locate x=1188 y=78]

[button name="page6" exp="setLoadPageButton(6)"]

[locate x=1250 y=78]

[button name="page7" exp="setLoadPageButton(7)"]

[locate x=1312 y=78]

[button name="page8" exp="setLoadPageButton(8)"]

[locate x=1374 y=78]

[button name="page9" exp="setLoadPageButton(9)"]



; The slots: one scrolling list of all of them, two across (since 0.21.0; slotList in
; Override.tjs). The page buttons scroll it to their ten

[eval exp="slotList('load')"]



; Return button

[locate x=1450 y=78]

[if exp="tf.fromTitle == 1"]

[button name="return" target=*backtotitle]

[else]

[button name="return" target=*backtogame]

[endif]



; Start dialog processing

[eval exp='setLoadPageButton()']

[trans screen method=crossfade time=300]

[wt]

[current layer=message1 page=fore]

[s]



*backtogame

[rclick jump=false]

[stoptrans]

[backlay]

[position layer=message1 page=back visible=false frame="" left=0 top=0 width=8 height=8]

[trans screen method=crossfade time=300]

[wt]

[current layer=message0]

[history enabled=true]

[unlocksnapshot]

[return]



*backtotitle

[rclick enabled=false jump=false]

[jump storage="title.ks" target=*backtotitle]