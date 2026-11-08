;
; Sprite Mode: the characters in any pose, outfit and face over the stage at any time of day, or a
; picture of the player's own, several at once, moved, zoomed and turned round, with a line said
; in a message window (template/system/SpriteMode.tjs; Override.tjs, spriteInit). The CG
; screen's Characters button opens it, and it goes back there
;

[rclick enabled=true jump=true storage="" target=*rclick]

[eval exp='spriteInit()']

*loop

; the panel and the World change together on the back page, and fade in as one ([begintrans] is
; the World's [backlay]); the camera's turn has no panel and no button to bring it back
[rclick enabled=true jump=true storage="" target=*rclick]
[begintrans]
[if exp="tf.spritePanel && !tf.spriteShot"]
[position layer=message0 frame="sprite_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]
[else]
[position layer=message0 frame="" opacity=0 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=true page=back]
[endif]
[current layer=message0 page=back]

; the stage first, so the panel's buttons are over it: a drag moves a character, the wheel zooms it
[eval exp='spriteStage()']

[if exp="tf.spritePanel && !tf.spriteShot"]
; a row each for the character, its pose, outfit, face and variation, and the background: the
; arrows either side of what it shows go through them (spriteStep); spriteRows draws the words
[locate x=60 y=230]
[button name="sprite_prev0" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(0, -1)" target=*again]
[locate x=556 y=230]
[button name="sprite_next0" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(0, 1)" target=*again]
[locate x=60 y=326]
[button name="sprite_prev1" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(1, -1)" target=*again]
[locate x=556 y=326]
[button name="sprite_next1" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(1, 1)" target=*again]
[locate x=60 y=422]
[button name="sprite_prev2" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(2, -1)" target=*again]
[locate x=556 y=422]
[button name="sprite_next2" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(2, 1)" target=*again]
[locate x=60 y=518]
[button name="sprite_prev3" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(3, -1)" target=*again]
[locate x=556 y=518]
[button name="sprite_next3" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(3, 1)" target=*again]
[locate x=60 y=614]
[button name="sprite_prev4" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(4, -1)" target=*again]
[locate x=556 y=614]
[button name="sprite_next4" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(4, 1)" target=*again]
[locate x=60 y=710]
[button name="sprite_prev5" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(5, -1)" target=*again]
[locate x=556 y=710]
[button name="sprite_next5" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(5, 1)" target=*again]

; the line the character picked says (Enter shows it)
[locate x=72 y=836]
[edit name="tf.spriteLine" length=536 fontheight=30 color=0x24107a bgcolor=0xffffff opacity=0 noborder=true maxchars=80 enter="spriteLineSet()"]

; the stage's tools: the character onto the stage or off it, turned round, zoomed out and in, the
; camera, the panel away
[locate x=60 y=912]
[button name="sprite_toggle" normal="&spriteToggleImage('normal')" over="&spriteToggleImage('over')" exp="spriteToggle()" target=*again]
[locate x=140 y=912]
[button name="sprite_flip" normal="sprite_flip_normal" over="sprite_flip_over" exp="spriteFlip()" target=*again]
[locate x=220 y=912]
[button name="sprite_zoomout" normal="chart_zoomout_normal" over="chart_zoomout_over" exp="spriteZoomBy(-1)" target=*again]
[locate x=300 y=912]
[button name="sprite_zoomin" normal="chart_zoomin_normal" over="chart_zoomin_over" exp="spriteZoomBy(1)" target=*again]
[locate x=380 y=912]
[button name="sprite_shot" normal="sprite_shot_normal" over="sprite_shot_over" exp="tf.spriteShot = true" target=*again]
[locate x=556 y=912]
[button name="sprite_hide" normal="sprite_hide_normal" over="sprite_hide_over" exp="spritePanelShow(false)" target=*again]
[eval exp='spriteRows()']

[locate x=60 y=996]
[button name="return" target=*back]
[elsif exp="!tf.spriteShot"]
; the panel away: a button brings it back (a right-click too)
[locate x=24 y=24]
[button name="sprite_show" normal="sprite_show_normal" over="sprite_show_over" exp="spritePanelShow(true)" target=*again]
[endif]

; the stage and the characters as the settings say
[eval exp='spriteApply()']

[endtrans trans=crossfade time=&tf.spriteFade]
[wt]
[current layer=message0 page=fore]
; the camera's turn: the stage as it is, then the panel again
[if exp="tf.spriteShot"]
[eval exp='spriteShot()']
[jump target=*again]
[endif]
[s]

; a step: the screen again, quickly
*again
[eval exp='tf.spriteFade = 100' cond="tf.spriteFade > 150"]
[jump target=*loop]

; a right-click: the panel back when it's away, else back to the CG screen
*rclick
[jump target=*again cond="spritePanelShow(true)"]

*back
[rclick enabled=false jump=false]
[eval exp='spriteLeave()']
[jump storage="cgmode.ks"]
