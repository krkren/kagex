;

; Replay Mode

;



[rclick enabled=true jump=true storage="" target=*backtotitle]



[eval exp='replayInit()']



*loop



; Load base image

[rclick enabled=true jump=true storage="" target=*backtotitle]

[backlay]

[position layer=message0 frame="replaymode_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]

[current layer=message0 page=back]



; Navigation buttons

[locate x=682 y=78]

[button name="extra_cgmode" storage="cgmode.ks"]

[locate x=810 y=78]

[button name="extra_replaymode" normal="extra_replaymode_over" disabled]

[locate x=938 y=78]

[button name="extra_chart" storage="chart.ks"]

[locate x=1066 y=78]

[button name="extra_musicmode" storage="musicmode.ks"]

[locate x=1194 y=78]

[button name="extra_searchmode" storage="searchmode.ks"]

[locate x=1322 y=78]

[button name="extra_glossary" storage="glossary.ks"]

[locate x=1450 y=78]

[button name="return" target=*backtotitle]



; Tabs (replaylist.csv; setReplayPage labels them)

[locate x=290 y=322]

[button name="replay_tab0" normal="replay_tab_normal" exp="tf.replayTab=0, tf.replayPage=0" target="*loop"]

[locate x=290 y=422]

[button name="replay_tab1" normal="replay_tab_normal" exp="tf.replayTab=1, tf.replayPage=0" target="*loop"]

[locate x=290 y=522]

[button name="replay_tab2" normal="replay_tab_normal" exp="tf.replayTab=2, tf.replayPage=0" target="*loop"]

[locate x=290 y=622]

[button name="replay_tab3" normal="replay_tab_normal" exp="tf.replayTab=3, tf.replayPage=0" target="*loop"]

[locate x=290 y=722]

[button name="replay_tab4" normal="replay_tab_normal" exp="tf.replayTab=4, tf.replayPage=0" target="*loop"]

[locate x=290 y=822]

[button name="replay_tab5" normal="replay_tab_normal" exp="tf.replayTab=5, tf.replayPage=0" target="*loop"]



; The tab's scenes: a grid that scrolls with the wheel, by dragging (a flick coasts on), with its

; bar and with the keys or a controller's D-pad (replayList in Override.tjs, ScrollList.tjs)



[eval exp='setReplayPage()']

[eval exp='replayList()']

; the music room's track, playing on, with its Stop button (Override.tjs)

[if exp="roomMusicPlaying()"]

[locate x=654 y=950]

[button name="gallery_stop" normal="musicmode_stop_normal" over="musicmode_stop_over" exp="galleryStop()" target=*loop]

[endif]

[eval exp='galleryPlayer()']


[trans method=crossfade time=500]

[wt]

[current layer=message0 page=fore]

[s]



*backtotitle

[rclick enabled=false jump=false]

[jump storage="title.ks" target=*backtotitle]