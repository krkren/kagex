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

[locate x=886 y=74]

[button name="extra_cgmode" storage="cgmode.ks"]

[locate x=1119 y=74]

[button name="extra_replaymode" disabled]

[locate x=1309 y=74]

[button name="extra_musicmode" storage="musicmode.ks"]

[locate x=1476 y=74]

[button name="return" target=*backtotitle]



; Character selection

[locate x=290 y=322]

[button name="cgmode_page0" exp="tf.cgmodepage=0" target="*loop"]

[locate x=290 y=422]

[button name="cgmode_page1" exp="tf.cgmodepage=1" target="*loop"]

[locate x=290 y=522]

[button name="cgmode_page2" exp="tf.cgmodepage=2" target="*loop"]

[locate x=290 y=622]

[button name="cgmode_page3" exp="tf.cgmodepage=3" target="*loop"]

[locate x=290 y=722]

[button name="cgmode_page4" exp="tf.cgmodepage=4" target="*loop"]

[locate x=290 y=822]

[button name="cgmode_page5" exp="tf.cgmodepage=5" target="*loop"]



; Replay selection

; 1st Row

[locate x=681 y=322]

[button name="cg0" normal="cgmode_thum_normal" exp='recollect(0)']

[locate x=926 y=322]

[button name="cg1" normal="cgmode_thum_normal" exp='recollect(1)']

[locate x=1171 y=322]

[button name="cg2" normal="cgmode_thum_normal" exp='recollect(2)']

[locate x=1416 y=322]

[button name="cg3" normal="cgmode_thum_normal" exp='recollect(3)']

; 2nd Row

[locate x=681 y=476]

[button name="cg4" normal="cgmode_thum_normal" exp='recollect(4)']

[locate x=926 y=476]

[button name="cg5" normal="cgmode_thum_normal" exp='recollect(5)']

[locate x=1171 y=476]

[button name="cg6" normal="cgmode_thum_normal" exp='recollect(6)']

[locate x=1416 y=476]

[button name="cg7" normal="cgmode_thum_normal" exp='recollect(7)']

; 3rd Row

[locate x=681 y=630]

[button name="cg8" normal="cgmode_thum_normal" exp='recollect(8)']

[locate x=926 y=630]

[button name="cg9" normal="cgmode_thum_normal" exp='recollect(9)']

[locate x=1171 y=630]

[button name="cg10" normal="cgmode_thum_normal" exp='recollect(10)']

[locate x=1416 y=630]

[button name="cg11" normal="cgmode_thum_normal" exp='recollect(11)']

; 4th Row

[locate x=681 y=784]

[button name="cg12" normal="cgmode_thum_normal" exp='recollect(12)']

[locate x=926 y=784]

[button name="cg13" normal="cgmode_thum_normal" exp='recollect(13)']

[locate x=1171 y=784]

[button name="cg14" normal="cgmode_thum_normal" exp='recollect(14)']

[locate x=1416 y=784]

[button name="cg15" normal="cgmode_thum_normal" exp='recollect(15)']



[eval exp='setReplaymodePageButton()']

[trans method=crossfade time=500]

[wt]

[current layer=message0 page=fore]

[s]



*backtotitle

[rclick enabled=false jump=false]

[jump storage="title.ks" target=*backtotitle]