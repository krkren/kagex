;
; The flowchart: the demos' scenes and the ways between them (template/system/Flowchart.tjs;
; Override.tjs, chartInit)
;

[rclick enabled=true jump=true storage="" target=*backtotitle]

[eval exp='chartInit()']

*loop

; Load base image
[rclick enabled=true jump=true storage="" target=*backtotitle]
[backlay]
[position layer=message0 frame="chart_base" opacity=255 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]
[current layer=message0 page=back]

; Buttons for transition
[locate x=682 y=78]
[button name="extra_cgmode" storage="cgmode.ks"]
[locate x=810 y=78]
[button name="extra_replaymode" storage="replay.ks"]
[locate x=938 y=78]
[button name="extra_chart" normal="extra_chart_over" disabled]
[locate x=1066 y=78]
[button name="extra_musicmode" storage="musicmode.ks"]
[locate x=1194 y=78]
[button name="extra_searchmode" storage="searchmode.ks"]
[locate x=1322 y=78]
[button name="extra_glossary" storage="glossary.ks"]
[locate x=1450 y=78]
[button name="return" target=*backtotitle]

; The chart: a drag moves it, the wheel or a pinch zooms, the arrow keys (a controller's D-pad) go
; from scene to scene, and a scene seen plays from its start, with the choices made on the way
; there (chartView, chartPick in Override.tjs)
[eval exp='chartView()']

; Zooming, and back to where the story is
[locate x=1408 y=962]
[button name="chart_zoomout" exp="chartZoom(-1)"]
[locate x=1487 y=962]
[button name="chart_zoomin" exp="chartZoom(1)"]
[locate x=1566 y=962]
[button name="chart_here" exp="chartHere()"]

; How many have been seen
[locate x=290 y=980]
[font size=28 color=0x5025ff bold=true shadow=false edge=false]
[emb exp="tf.chartStatus"]
[resetfont]

[trans method=crossfade time=300]
[wt]
[current layer=message0 page=fore]
[s]

*backtotitle
[rclick enabled=false jump=false]
[jump storage="title.ks" target=*backtotitle]
