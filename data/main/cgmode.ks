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
[locate x=834 y=78]
[button name="extra_replaymode" storage="replay.ks"]
[locate x=988 y=78]
[button name="extra_musicmode" storage="musicmode.ks"]
[locate x=1142 y=78]
[button name="extra_searchmode" storage="searchmode.ks"]
[locate x=1296 y=78]
[button name="extra_glossary" storage="glossary.ks"]
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

; The tab's pictures: a grid that scrolls with the wheel, by dragging (a flick coasts on), with
; its bar and with the keys or a controller's D-pad (cgList in Override.tjs, ScrollList.tjs)
[eval exp='setCgmodePageButton()']
[eval exp='cgList()']
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

*cgview
; the CG viewer (Override.tjs, CGViewer): zoom, pan and the variations, until it closes
[eval exp='cgViewInit()']
[eval exp='cgViewerOpen()']
[waittrig name=cgviewer]
[jump target=*loop]

*backtotitle
[rclick enabled=false jump=false]
[jump storage="title.ks" target=*backtotitle]