;
; Glossary: the terms the story explains (template/system/Glossary.tjs; Override.tjs, glossaryInit)
;

[rclick enabled=true jump=true storage="" target=*backtotitle]

[eval exp='glossaryInit()']

*loop

; Load base image
[rclick enabled=true jump=true storage="" target=*backtotitle]
[backlay]
[position layer=message0 frame="glossary_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]
[current layer=message0 page=back]

; Buttons for transition
[locate x=680 y=78]
[button name="extra_cgmode" storage="cgmode.ks"]
[locate x=834 y=78]
[button name="extra_replaymode" storage="replay.ks"]
[locate x=988 y=78]
[button name="extra_musicmode" storage="musicmode.ks"]
[locate x=1142 y=78]
[button name="extra_searchmode" storage="searchmode.ks"]
[locate x=1296 y=78]
[button name="extra_glossary" normal="extra_glossary_over" disabled]
[locate x=1450 y=78]
[button name="return" target=*backtotitle]

; The terms: a list that scrolls with the wheel, by dragging, with its bar and with the keys or
; a controller's D-pad (glossaryList in Override.tjs, ScrollList.tjs); the one chosen, on the right
[eval exp='glossaryList()']
[eval exp='glossaryEntry()']

; How many have been met
[locate x=290 y=980]
[font size=28 color=0x5025ff bold=true shadow=false edge=false]
[emb exp="tf.glossaryStatus"]
[resetfont]

[trans method=crossfade time=&tf.glossaryFade]
[wt]
[current layer=message0 page=fore]
[s]

; a term chosen (glossaryPick): the screen again, quickly
*again
[eval exp='tf.glossaryFade = 120']
[jump target=*loop]

*backtotitle
[rclick enabled=false jump=false]
[jump storage="title.ks" target=*backtotitle]
