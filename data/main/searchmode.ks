;
; Search: the lines read so far in the compiled scenes (Override.tjs, doc/scn.txt)
;

[rclick enabled=true jump=true storage="" target=*backtotitle]

[eval exp='searchInit()']

*loop

; Load base image
[rclick enabled=true jump=true storage="" target=*backtotitle]
[backlay]
[position layer=message0 frame="searchmode_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]
[current layer=message0 page=back]

; Buttons for transition
[locate x=682 y=78]
[button name="extra_cgmode" storage="cgmode.ks"]
[locate x=810 y=78]
[button name="extra_replaymode" storage="replay.ks"]
[locate x=938 y=78]
[button name="extra_chart" storage="chart.ks"]
[locate x=1066 y=78]
[button name="extra_musicmode" storage="musicmode.ks"]
[locate x=1194 y=78]
[button name="extra_searchmode" normal="extra_searchmode_over" disabled]
[locate x=1322 y=78]
[button name="extra_glossary" storage="glossary.ks"]
[locate x=1450 y=78]
[button name="return" target=*backtotitle]

; What to look for: Return or the button searches
[locate x=306 y=218]
[edit name="tf.searchText" prompt="Search" length=868 fontheight=32 fontbold=true color=0x24107a bgcolor=0xffffff opacity=0 noborder=true maxchars=40 enter="searchRun()"]
[locate x=1210 y=206]
[button name="search_go" normal="search_go_normal" over="search_go_over" exp="searchFromField()"]

; The lines found: a list that scrolls with the wheel, by dragging (a flick coasts on), with its
; bar and with the keys or a controller's D-pad (searchList in Override.tjs, ScrollList.tjs)
[eval exp='searchList()']

; What was found
[locate x=290 y=956]
[font size=28 color=0x5025ff bold=true shadow=false edge=false]
[emb exp="tf.searchStatus"]
[resetfont]

[trans method=crossfade time=300]
[wt]
[current layer=message0 page=fore]
[eval exp='searchFocus()']
[s]

*backtotitle
[rclick enabled=false jump=false]
[jump storage="title.ks" target=*backtotitle]
