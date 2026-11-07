; For initializing each scene

[macro name=initscene]

[clearlayers]

[stopse buf=1]

[stopse buf=2]

[stopbgm]

[stopvideo]

[video visible=false]

[history enabled=true]

[rclick enabled=true jump=false]

[position layer=message0 frame="messagewindow" opacity=255 left=60 top=714 width=1800 height=330 marginL=&faceWindowMargin() faceleft=40 facetop=56 facewidth=250 faceheight=250 marginT=66 marginR=60 marginB=92 nameLeft=36 nameTop=-30 nameWidth=300 nameHeight=64 nameframe="namebox" namealign=0 namevalign=0 namefit=squeeze namemargin=14 namefade=150 followopacity=true visible=false]

[current layer=message0]

; the window's buttons are the quick menu (since 0.19.0; AfterInit.tjs: kag.quickMenu), drawn over its top edge
[eval exp="f.quickMenu = true"]

[init]

[linemode mode=page]

[craftername mode=true]

[endmacro]



; Marks a demo scene as played to the end; Extras on the title screen unlock once all

; six have been (sf.clear; not the Effekseer demo, which some builds can't show)

[macro name=demodone]

[eval exp="sf['demodone_' + mp.name] = true"]

[eval exp="sf.clear = true" cond="sf.demodone_layer && sf.demodone_char && sf.demodone_envlayer && sf.demodone_transition && sf.demodone_action && sf.demodone_anim"]

[endmacro]



; The staging kit (since 0.18.0), a word each. The gestures are envinit.tjs's actions ([ai nod],

; [ai headshake] ...); these are the rest:

;   [quake] [thud] [rumble]   the screen shakes (camera actions in envinit.tjs)

;   [closeup] [closeupend]    the camera closes in (zoom=, y=, x=, time=) and the background blurs

;   [dim] [whiten] [undim]    a translucent veil over the scene for inner thoughts (opacity=)

;   [eyecatch]                a card between scenes (time= ms; a click skips it)

[macro name=quake][env actioncamera=quake][endmacro]

[macro name=thud][env actioncamera=thud][endmacro]

[macro name=rumble][env actioncamera=rumble][endmacro]

[macro name=closeup]

[bg blur=%blur|8]

[env camerazoom=%zoom|140 camerax=%x|0 cameray=%y|60 time=%time|500]

[endmacro]

[macro name=closeupend]

[bg resetcolor]

[env resetcamera time=%time|500]

[endmacro]

[macro name=dim][newlay name=veil file=black level=5 opacity=%opacity|110 trans=normal][endmacro]

[macro name=whiten][newlay name=veil file=white level=5 opacity=%opacity|140 trans=normal][endmacro]

[macro name=undim][veil delete trans=normal][endmacro]

; A memory (since 0.22.0): bars at the top and the bottom, a sepia edge and the memories' window
; style (AfterInit.tjs, MessageStyles.tjs), shown with the next transition (between [begintrans] and
; [endtrans trans=...], with the scene's other changes, all in one); [memoryend] takes them off
[macro name=letterbox][newlay name=letterbox file=letterbox level=6][endmacro]

[macro name=memoryframe][newlay name=memoryframe file=memoryframe level=6][endmacro]

[macro name=memory][letterbox][memoryframe][env msgstyle=memory][endmacro]

[macro name=memoryend][letterbox delete][memoryframe delete][env msgstyle=normal][endmacro]

[macro name=eyecatch]

[newlay name=eyecatchcard file=eyecatch level=message trans=normal]

[wait time=%time|2000 canskip=true]

[eyecatchcard delete trans=normal]

[endmacro]



@return