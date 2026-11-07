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

[locate x=682 y=78]

[button name="extra_cgmode" storage="cgmode.ks"]

[locate x=810 y=78]

[button name="extra_replaymode" storage="replay.ks"]

[locate x=938 y=78]

[button name="extra_chart" storage="chart.ks"]

[locate x=1066 y=78]

[button name="extra_musicmode" normal="extra_musicmode_over" disabled]

[locate x=1194 y=78]

[button name="extra_searchmode" storage="searchmode.ks"]

[locate x=1322 y=78]

[button name="extra_glossary" storage="glossary.ks"]

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



; The music playing (since 0.24.0): the record turns, the track's title, and a bar that seeks
; (a click or a drag, or the left and right keys; nowPlaying in Override.tjs)

[eval exp='nowPlaying()']



; What the list shows (since 0.24.0): the music, the voices heard, or the favourite voices
; (musicView in Override.tjs: the buttons' labels are drawn on them)

[locate x=840 y=192]

[button name="music_view0" normal="music_view_normal" over="music_view_over" exp="musicView(0)" target=*loop]

[locate x=1030 y=192]

[button name="music_view1" normal="music_view_normal" over="music_view_over" exp="musicView(1)" target=*loop]

[locate x=1220 y=192]

[button name="music_view2" normal="music_view_normal" over="music_view_over" exp="musicView(2)" target=*loop]

[eval exp='musicViewTabs()']



; The tracks: a list that scrolls with the wheel, by dragging, with its bar and with the keys or a
; controller's D-pad, as many as musiclist.csv has (musicTrackList in Override.tjs); or the voices
; (voiceList: a click plays one, its star keeps it, the favourites' handle puts them in order)
[eval exp='musicViewList()']
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