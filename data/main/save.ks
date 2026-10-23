;

; Save Screen

;



; Call from in-game

*startFromGame

[locksnapshot]

[rclick enabled=true jump=true storage="" target=*backtogame]

[history enabled=false]



; Load base image

[stoptrans]

[backlay]

[position layer=message1 frame="save_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true  transparent=false page=back]

[current layer=message1 page=back]



; Button layout



; Page layout

[locate x=878 y=78]

[button name="page1" exp="setSavePageButton(1)"]

[locate x=940 y=78]

[button name="page2" exp="setSavePageButton(2)"]

[locate x=1002 y=78]

[button name="page3" exp="setSavePageButton(3)"]

[locate x=1064 y=78]

[button name="page4" exp="setSavePageButton(4)"]

[locate x=1126 y=78]

[button name="page5" exp="setSavePageButton(5)"]

[locate x=1188 y=78]

[button name="page6" exp="setSavePageButton(6)"]

[locate x=1250 y=78]

[button name="page7" exp="setSavePageButton(7)"]

[locate x=1312 y=78]

[button name="page8" exp="setSavePageButton(8)"]

[locate x=1374 y=78]

[button name="page9" exp="setSavePageButton(9)"]



; Save data frame

; 1st Column

[locate x=290 y=190]

[button name="save0" normal="sl_win_base" exp="saveAction(0)"]

[locate x=290 y=358]

[button name="save1" normal="sl_win_base" exp="saveAction(1)"]

[locate x=290 y=526]

[button name="save2" normal="sl_win_base" exp="saveAction(2)"]

[locate x=290 y=694]

[button name="save3" normal="sl_win_base" exp="saveAction(3)"]

[locate x=290 y=862]

[button name="save4" normal="sl_win_base" exp="saveAction(4)"]



; 2nd Column

[locate x=980 y=190]

[button name="save5" normal="sl_win_base" exp="saveAction(5)"]

[locate x=980 y=358]

[button name="save6" normal="sl_win_base" exp="saveAction(6)"]

[locate x=980 y=526]

[button name="save7" normal="sl_win_base" exp="saveAction(7)"]

[locate x=980 y=694]

[button name="save8" normal="sl_win_base" exp="saveAction(8)"]

[locate x=980 y=862]

[button name="save9" normal="sl_win_base" exp="saveAction(9)"]



; Top-right return button

[locate x=1450 y=78]

[button name="return" target=*backtogame]



; Start dialog processing

[eval exp='setSavePageButton()']

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

[current layer=message0 page=fore]

[history enabled=true]

[unlocksnapshot]

[return]