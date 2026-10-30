;
; CG Mode
;

[rclick enabled=true jump=true target=*backtotitle]

[eval exp='cgInit()']

*loop

; Load base image
[rclick enabled=true jump=true storage="" target=*backtotitle]
[backlay]
[position layer=message0 frame="cgmode_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]
[current layer=message0 page=back]

; Buttons for transition
[locate x=680 y=78]
[button name="extra_cgmode" normal="extra_cgmode_over" disabled]
[locate x=870 y=78]
[button name="extra_replaymode" storage="replay.ks"]
[locate x=1060 y=78]
[button name="extra_musicmode" storage="musicmode.ks"]
[locate x=1250 y=78]
[button name="extra_searchmode" storage="searchmode.ks"]
[locate x=1450 y=78]
[button name="return" target=*backtotitle]

; Character Selection
[locate x=290 y=322]
[button name="cgmode_page0" exp="tf.cgmodepage=0" target=*loop]
[locate x=290 y=422]
[button name="cgmode_page1" exp="tf.cgmodepage=1" target=*loop]
[locate x=290 y=522]
[button name="cgmode_page2" exp="tf.cgmodepage=2" target=*loop]
[locate x=290 y=622]
[button name="cgmode_page3" exp="tf.cgmodepage=3" target=*loop]
[locate x=290 y=722]
[button name="cgmode_page4" exp="tf.cgmodepage=4" target=*loop]
[locate x=290 y=822]
[button name="cgmode_page5" exp="tf.cgmodepage=5" target=*loop]

; CG Selection
; 1st Row
[locate x=681 y=322]
[button name="cg0" normal="cgmode_thum_normal" exp="tf.cgnum=0" target=*cgview]
[locate x=926 y=322]
[button name="cg1" normal="cgmode_thum_normal" exp="tf.cgnum=1" target=*cgview]
[locate x=1171 y=322]
[button name="cg2" normal="cgmode_thum_normal" exp="tf.cgnum=2" target=*cgview]
[locate x=1416 y=322]
[button name="cg3" normal="cgmode_thum_normal" exp="tf.cgnum=3" target=*cgview]
; 2nd Row
[locate x=681 y=476]
[button name="cg4" normal="cgmode_thum_normal" exp="tf.cgnum=4" target=*cgview]
[locate x=926 y=476]
[button name="cg5" normal="cgmode_thum_normal" exp="tf.cgnum=5" target=*cgview]
[locate x=1171 y=476]
[button name="cg6" normal="cgmode_thum_normal" exp="tf.cgnum=6" target=*cgview]
[locate x=1416 y=476]
[button name="cg7" normal="cgmode_thum_normal" exp="tf.cgnum=7" target=*cgview]
; 3rd Row
[locate x=681 y=630]
[button name="cg8" normal="cgmode_thum_normal" exp="tf.cgnum=8" target=*cgview]
[locate x=926 y=630]
[button name="cg9" normal="cgmode_thum_normal" exp="tf.cgnum=9" target=*cgview]
[locate x=1171 y=630]
[button name="cg10" normal="cgmode_thum_normal" exp="tf.cgnum=10" target=*cgview]
[locate x=1416 y=630]
[button name="cg11" normal="cgmode_thum_normal" exp="tf.cgnum=11" target=*cgview]
; 4th Row
[locate x=681 y=784]
[button name="cg12" normal="cgmode_thum_normal" exp="tf.cgnum=12" target=*cgview]
[locate x=926 y=784]
[button name="cg13" normal="cgmode_thum_normal" exp="tf.cgnum=13" target=*cgview]
[locate x=1171 y=784]
[button name="cg14" normal="cgmode_thum_normal" exp="tf.cgnum=14" target=*cgview]
[locate x=1416 y=784]
[button name="cg15" normal="cgmode_thum_normal" exp="tf.cgnum=15" target=*cgview]

[eval exp='setCgmodePageButton()']
[trans method=crossfade time=500]
[wt]
[current layer=message0 page=fore]
[s]

*cgview
[eval exp='cgViewInit()']

*cgviewloop
[rclick enabled=true jump=true storage="" target=*loop]
[if exp='isCgView()']
[stoptrans]
[backlay]
[position page=back layer=message0 frame="" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true]
[current page=back layer=message0]
[eval exp='cgView()']
[trans method=crossfade time=500]
[wt]
[current page=fore layer=message0]
[click target=*cgviewloop]
[s]
[endif]
[jump target=*loop]

*backtotitle
[rclick enabled=false jump=false]
[jump storage="title.ks" target=*backtotitle]