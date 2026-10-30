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

[locate x=680 y=78]

[button name="extra_cgmode" storage="cgmode.ks"]

[locate x=870 y=78]

[button name="extra_replaymode" normal="extra_replaymode_over" disabled]

[locate x=1060 y=78]

[button name="extra_musicmode" storage="musicmode.ks"]

[locate x=1250 y=78]

[button name="extra_searchmode" storage="searchmode.ks"]

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



; The tab's pages of tiles

[locate x=1676 y=322]

[button name="replay_prev" normal="replay_prev_normal" over="replay_prev_over" exp="tf.replayPage--" target="*loop"]

[locate x=1676 y=843]

[button name="replay_next" normal="replay_next_normal" over="replay_next_over" exp="tf.replayPage++" target="*loop"]



; Replay selection

; 1st Row

[locate x=681 y=322]

[button name="cg0" normal="cgmode_thum_normal" exp='replayTile(0)']

[locate x=926 y=322]

[button name="cg1" normal="cgmode_thum_normal" exp='replayTile(1)']

[locate x=1171 y=322]

[button name="cg2" normal="cgmode_thum_normal" exp='replayTile(2)']

[locate x=1416 y=322]

[button name="cg3" normal="cgmode_thum_normal" exp='replayTile(3)']

; 2nd Row

[locate x=681 y=476]

[button name="cg4" normal="cgmode_thum_normal" exp='replayTile(4)']

[locate x=926 y=476]

[button name="cg5" normal="cgmode_thum_normal" exp='replayTile(5)']

[locate x=1171 y=476]

[button name="cg6" normal="cgmode_thum_normal" exp='replayTile(6)']

[locate x=1416 y=476]

[button name="cg7" normal="cgmode_thum_normal" exp='replayTile(7)']

; 3rd Row

[locate x=681 y=630]

[button name="cg8" normal="cgmode_thum_normal" exp='replayTile(8)']

[locate x=926 y=630]

[button name="cg9" normal="cgmode_thum_normal" exp='replayTile(9)']

[locate x=1171 y=630]

[button name="cg10" normal="cgmode_thum_normal" exp='replayTile(10)']

[locate x=1416 y=630]

[button name="cg11" normal="cgmode_thum_normal" exp='replayTile(11)']

; 4th Row

[locate x=681 y=784]

[button name="cg12" normal="cgmode_thum_normal" exp='replayTile(12)']

[locate x=926 y=784]

[button name="cg13" normal="cgmode_thum_normal" exp='replayTile(13)']

[locate x=1171 y=784]

[button name="cg14" normal="cgmode_thum_normal" exp='replayTile(14)']

[locate x=1416 y=784]

[button name="cg15" normal="cgmode_thum_normal" exp='replayTile(15)']



[eval exp='setReplayPage()']

[trans method=crossfade time=500]

[wt]

[current layer=message0 page=fore]

[s]



*backtotitle

[rclick enabled=false jump=false]

[jump storage="title.ks" target=*backtotitle]