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

[sysbutton name=msg_exit   x=1408 y=0 exp="kag.process('title.ks','*start')"]

[sysbutton name=msg_skip   x=1536 y=0 exp="kag.onSkipToNextStopMenuItemClick()" nostable]

[sysbutton name=msg_auto   x=1600 y=0 exp="kag.onAutoModeMenuItemClick()" nostable]

[sysbutton name=msg_log    x=1664 y=0 exp="kag.onShowHistoryMenuItemClick()"]

[sysbutton name=msg_config x=1728 y=0 exp="startConfig()"]

[else]

[sysbutton name=msg_save   x=1408 y=0 exp="startSave()"]

[sysbutton name=msg_load   x=1472 y=0 exp="startLoad()"]

[sysbutton name=msg_skip   x=1536 y=0 exp="kag.onSkipToNextStopMenuItemClick()" nostable]

[sysbutton name=msg_auto   x=1600 y=0 exp="kag.onAutoModeMenuItemClick()" nostable]

[sysbutton name=msg_log    x=1664 y=0 exp="kag.onShowHistoryMenuItemClick()"]

[sysbutton name=msg_config x=1728 y=0 exp="startConfig()"]

[endif]

[init]

[linemode mode=page]

[craftername mode=true]

[endmacro]



@return