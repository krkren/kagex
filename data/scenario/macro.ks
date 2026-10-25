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

[position layer=message0 frame="messagewindow" opacity=255 left=60 top=714 width=1800 height=330 marginL=48 marginT=76 marginR=60 marginB=36 nameLeft=36 nameTop=-30 nameWidth=300 nameHeight=64 nameframe="namebox" namealign=0 namevalign=0 visible=false]

[current layer=message0]

[if exp="tf.recollect"]

[sysbutton name=msg_exit   x=1108 y=18 exp="kag.process('title.ks','*start')"]

[sysbutton name=msg_skip   x=1240 y=18 exp="kag.onSkipToNextStopMenuItemClick()" nostable]

[sysbutton name=msg_auto   x=1372 y=18 exp="kag.onAutoModeMenuItemClick()" nostable]

[sysbutton name=msg_log    x=1504 y=18 exp="kag.onShowHistoryMenuItemClick()"]

[sysbutton name=msg_config x=1636 y=18 exp="startConfig()"]

[else]

[sysbutton name=msg_save   x=976 y=18 exp="startSave()"]

[sysbutton name=msg_load   x=1108 y=18 exp="startLoad()"]

[sysbutton name=msg_skip   x=1240 y=18 exp="kag.onSkipToNextStopMenuItemClick()" nostable]

[sysbutton name=msg_auto   x=1372 y=18 exp="kag.onAutoModeMenuItemClick()" nostable]

[sysbutton name=msg_log    x=1504 y=18 exp="kag.onShowHistoryMenuItemClick()"]

[sysbutton name=msg_config x=1636 y=18 exp="startConfig()"]

[endif]

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



@return