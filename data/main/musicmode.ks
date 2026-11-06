;

; Music Mode

;



[rclick enabled=true jump=true storage="" target=*backtotitle]



; the music fades, unless it's the room's own track (playing on from the CG or Replay screen)

[if exp="!roomMusicPlaying()"]

[fadeoutbgm time=500]

[wb]

[endif]



[eval exp='musicInit()']



*loop



; Load base image

[stoptrans]

[backlay]

[position layer=message0 frame="musicmode_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true  transparent=false page=back]

[current layer=message0 page=back]



; Navigation Buttons

[locate x=680 y=78]

[button name="extra_cgmode" storage="cgmode.ks"]

[locate x=870 y=78]

[button name="extra_replaymode" storage="replay.ks"]

[locate x=1060 y=78]

[button name="extra_musicmode" normal="extra_musicmode_over" disabled]

[locate x=1250 y=78]

[button name="extra_searchmode" storage="searchmode.ks"]

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

[locate x=322 y=714]

[button name="musicmode_title"     exp='setTitleMusic(!keepTitleMusic())']



; The tracks: a list that scrolls with the wheel, by dragging, with its bar and with the keys or a
; controller's D-pad, as many as musiclist.csv has (musicTrackList in Override.tjs)
[eval exp='musicTrackList()']
[eval exp='setRepeat()']

[eval exp='setButtonOver("musicmode_title", keepTitleMusic())']

[eval exp='setMusicmodePageButton()']



[trans method=crossfade time=500]

[wt]

[current layer=message0 page=fore]

[s]



*backtotitle

[rclick enabled=false jump=false]

[eval exp='musicEnd()']

[jump storage="title.ks" target=*backtotitle]