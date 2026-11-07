;
; Sprite Mode: the characters one at a time, in any pose, outfit and face, over the stage at any
; time of day (template/system/SpriteMode.tjs; Override.tjs, spriteInit). The CG screen's
; Characters button opens it, and it goes back there
;

[rclick enabled=true jump=true storage="" target=*back]

[eval exp='spriteInit()']

*loop

; the panel and the World change together on the back page, and fade in as one ([begintrans] is
; the World's [backlay])
[rclick enabled=true jump=true storage="" target=*back]
[begintrans]
[position layer=message0 frame="sprite_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]
[current layer=message0 page=back]

; a row each for the character, its pose, outfit and face, and the background: the arrows
; either side of what it shows go through them (spriteStep); spriteRows draws the words
[locate x=60 y=262]
[button name="sprite_prev0" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(0, -1)" target=*again]
[locate x=556 y=262]
[button name="sprite_next0" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(0, 1)" target=*again]
[locate x=60 y=392]
[button name="sprite_prev1" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(1, -1)" target=*again]
[locate x=556 y=392]
[button name="sprite_next1" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(1, 1)" target=*again]
[locate x=60 y=522]
[button name="sprite_prev2" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(2, -1)" target=*again]
[locate x=556 y=522]
[button name="sprite_next2" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(2, 1)" target=*again]
[locate x=60 y=652]
[button name="sprite_prev3" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(3, -1)" target=*again]
[locate x=556 y=652]
[button name="sprite_next3" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(3, 1)" target=*again]
[locate x=60 y=782]
[button name="sprite_prev4" normal="sprite_prev_normal" over="sprite_prev_over" exp="spriteStep(4, -1)" target=*again]
[locate x=556 y=782]
[button name="sprite_next4" normal="sprite_next_normal" over="sprite_next_over" exp="spriteStep(4, 1)" target=*again]
[eval exp='spriteRows()']

[locate x=60 y=960]
[button name="return" target=*back]

; the stage and the character as the rows say
[eval exp='spriteApply()']

[endtrans trans=crossfade time=&tf.spriteFade]
[wt]
[current layer=message0 page=fore]
[s]

; a step: the panel again, quickly
*again
[eval exp='tf.spriteFade = 100']
[jump target=*loop]

*back
[rclick enabled=false jump=false]
[eval exp='spriteLeave()']
[jump storage="cgmode.ks"]
