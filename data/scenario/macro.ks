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

[position layer=message0 frame="messagewindow" opacity=255 left=60 top=714 width=1800 height=330 marginL=24 marginT=60 marginR=24 marginB=24 nameLeft=48 nameTop=12 nameWidth=225 nameHeight=60 visible=false]

[current layer=message0]

[if exp="tf.recollect"]

[sysbutton name=msg_exit   x=1096 y=0 exp="kag.process('title.ks','*start')"]

[sysbutton name=msg_skip   x=1326 y=0 exp="kag.onSkipToNextStopMenuItemClick()" nostable]

[sysbutton name=msg_auto   x=1441 y=0 exp="kag.onAutoModeMenuItemClick()" nostable]

[sysbutton name=msg_log    x=1556 y=0 exp="kag.onShowHistoryMenuItemClick()"]

[sysbutton name=msg_config x=1671 y=0 exp="startConfig()"]

[else]

[sysbutton name=msg_save   x=1096 y=0 exp="startSave()"]

[sysbutton name=msg_load   x=1211 y=0 exp="startLoad()"]

[sysbutton name=msg_skip   x=1326 y=0 exp="kag.onSkipToNextStopMenuItemClick()" nostable]

[sysbutton name=msg_auto   x=1441 y=0 exp="kag.onAutoModeMenuItemClick()" nostable]

[sysbutton name=msg_log    x=1556 y=0 exp="kag.onShowHistoryMenuItemClick()"]

[sysbutton name=msg_config x=1671 y=0 exp="startConfig()"]

[endif]

[init]

[linemode mode=page]

[craftername mode=true]

[endmacro]



; Marks a demo scene as played to the end; Extras on the title screen unlock once all

; five have been (sf.clear)

[macro name=demodone]

[eval exp="sf['demodone_' + mp.name] = true"]

[eval exp="sf.clear = true" cond="sf.demodone_layer && sf.demodone_char && sf.demodone_envlayer && sf.demodone_transition && sf.demodone_action"]

[endmacro]



@return