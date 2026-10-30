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
[locate x=680 y=78]
[button name="extra_cgmode" storage="cgmode.ks"]
[locate x=870 y=78]
[button name="extra_replaymode" storage="replay.ks"]
[locate x=1060 y=78]
[button name="extra_musicmode" storage="musicmode.ks"]
[locate x=1250 y=78]
[button name="extra_searchmode" normal="extra_searchmode_over" disabled]
[locate x=1450 y=78]
[button name="return" target=*backtotitle]

; What to look for: Return or the button searches
[locate x=306 y=218]
[edit name="tf.searchText" length=868 fontheight=32 fontbold=true color=0x24107a bgcolor=0xffffff opacity=0 noborder=true maxchars=40 enter="searchRun()"]
[locate x=1210 y=206]
[button name="search_go" normal="search_go_normal" over="search_go_over" exp="searchFromField()"]

; The lines found: 7 a page
[locate x=316 y=322]
[button name="row0" normal="search_row_normal" over="search_row_over" exp="searchPlay(0)"]
[locate x=316 y=408]
[button name="row1" normal="search_row_normal" over="search_row_over" exp="searchPlay(1)"]
[locate x=316 y=494]
[button name="row2" normal="search_row_normal" over="search_row_over" exp="searchPlay(2)"]
[locate x=316 y=580]
[button name="row3" normal="search_row_normal" over="search_row_over" exp="searchPlay(3)"]
[locate x=316 y=666]
[button name="row4" normal="search_row_normal" over="search_row_over" exp="searchPlay(4)"]
[locate x=316 y=752]
[button name="row5" normal="search_row_normal" over="search_row_over" exp="searchPlay(5)"]
[locate x=316 y=838]
[button name="row6" normal="search_row_normal" over="search_row_over" exp="searchPlay(6)"]
[locate x=1676 y=322]
[button name="search_prev" normal="replay_prev_normal" over="replay_prev_over" exp="tf.searchPage--" target="*loop"]
[locate x=1676 y=850]
[button name="search_next" normal="replay_next_normal" over="replay_next_over" exp="tf.searchPage++" target="*loop"]

[eval exp='setSearchPage()']

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
