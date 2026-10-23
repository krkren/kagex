;

; Music Mode

;



[rclick enabled=true jump=true storage="" target=*backtotitle]



[fadeoutbgm time=500]

[wb]



[eval exp='musicInit()']



*loop



; Load base image

[stoptrans]

[backlay]

[position layer=message0 frame="musicmode_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true  transparent=false page=back]

[current layer=message0 page=back]



; Navigation Buttons

[locate x=870 y=78]

[button name="extra_cgmode" storage="cgmode.ks"]

[locate x=1060 y=78]

[button name="extra_replaymode" storage="replay.ks"]

[locate x=1250 y=78]

[button name="extra_musicmode" normal="extra_musicmode_over" disabled]

[locate x=1450 y=78]

[button name="return" target=*backtotitle]



; Function Buttons

[locate x=558 y=800]

[button name="musicmode_play"      exp="startBgm()"]

[locate x=322 y=800]

[button name="musicmode_stop"      exp="stopBgm()"]

[locate x=322 y=876]

[button name="musicmode_repeat"    exp='setRepeat(true)']

[locate x=558 y=876]

[button name="musicmode_allrepeat" exp='setRepeat(false)']



; Music Buttons

[locate x=870 y=291]

[button name="track01" exp='playBgm(0)']

[locate x=870 y=345]

[button name="track02" exp='playBgm(1)']

[locate x=870 y=399]

[button name="track03" exp='playBgm(2)']

[locate x=870 y=453]

[button name="track04" exp='playBgm(3)']

[locate x=870 y=507]

[button name="track05" exp='playBgm(4)']

[locate x=870 y=561]

[button name="track06" exp='playBgm(5)']

[locate x=870 y=615]

[button name="track07" exp='playBgm(6)']

[locate x=870 y=669]

[button name="track08" exp='playBgm(7)']

[locate x=870 y=723]

[button name="track09" exp='playBgm(8)']

[locate x=870 y=777]

[button name="track10" exp='playBgm(9)']

[locate x=870 y=831]

[button name="track11" exp='playBgm(10)']

[locate x=870 y=885]

[button name="track12" exp='playBgm(11)']



[eval exp='setRepeat()']

[eval exp='setMusicmodePageButton()']



[trans method=crossfade time=500]

[wt]

[current layer=message0 page=fore]

[s]



*backtotitle

[rclick enabled=false jump=false]

[eval exp='musicEnd()']

[jump storage="title.ks" target=*backtotitle]