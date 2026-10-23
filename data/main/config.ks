; 
; Configuration Settings
;

; Call from within the game
*startFromGame
[rclick enabled=true jump=true storage="" target=*backtogame]
[eval exp='tf.fromTitle = 0']
[history enabled=false]
[jump target=*buttons]

; Call from title
*startFromTitle
[rclick enabled=true jump=true storage="" target=*backtotitle]
[eval exp='tf.fromTitle = 1']

*buttons

; Load base image
[backlay]
[position layer=message1 frame="config_base" left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true  transparent=false page=back]
[current layer=message1 page=back]

; Button placement

; Screen Mode
[locate x=322 y=278]
[button name="config_window"     exp='setScreenButton(true)']
[locate x=578 y=278]
[button name="config_fullscreen" exp='setScreenButton(false)']

; Text Speed
[locate x=402 y=428]
[slider width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=10 value=kag.textspeed nohilight]

; Auto Speed
[locate x=402 y=578]
[slider width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=10 value=kag.autospeed nohilight]

; Screen Effects
[locate x=322 y=728]
[button name=config_effecton exp="setNoEffectButton(false)"]
[locate x=578 y=728]
[button name=config_effectoff exp="setNoEffectButton(true)"]

; Skip
[locate x=322 y=878]
[button name="config_skipall" exp="setSkipButton(true)"]
[locate x=578 y=878]
[button name="config_skipalrdy" exp="setSkipButton(false)"]

; BGM Volume
[locate x=1102 y=278]
[slider width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=100 value=kag.bgmvolume nohilight]

; SE Volume
[locate x=1102 y=428]
[slider width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=100 value=kag.sevolume nohilight]

; VOICE Volume
[locate x=1102 y=578]
[slider width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=100 value=kag.voicevolume nohilight]

; Voice Buttons
[locate x=1022 y=728]
[button name="config_voice0" normal="config_voice0_on" exp="setVoiceOnButton('voice0')"]
[locate x=1218 y=728]
[button name="config_voice1" normal="config_voice1_on" exp="setVoiceOnButton('voice1')"]
[locate x=1414 y=728]
[button name="config_voice2" normal="config_voice2_on" exp="setVoiceOnButton('voice2')"]
[locate x=1022 y=804]
[button name="config_voice3" normal="config_voice3_on" exp="setVoiceOnButton('voice3')"]
[locate x=1218 y=804]
[button name="config_voice4" normal="config_voice4_on" exp="setVoiceOnButton('voice4')"]
[locate x=1414 y=804]
[button name="config_voice5" normal="config_voice5_on" exp="setVoiceOnButton('voice5')"]

; Default, Title and Return, right-aligned in the header
[if exp="tf.fromTitle"]
[locate x=1260 y=78]
[button name="config_initial" exp="initial()"]
[locate x=1450 y=78]
[button name="config_title" target=*backtotitle]
[else]
[locate x=1070 y=78]
[button name="config_initial" exp="initial()"]
[locate x=1260 y=78]
[button name="config_title" exp="gotoTitle()"]
[locate x=1450 y=78]
[button name="return" target=*backtogame]
[endif]

[eval exp='configInit()']
[trans method=crossfade time=300]
[wt]
[current layer=message1 page=fore]
[s]

*backtogame
[rclick jump=false]
[stoptrans]
[backlay]
[position layer=message1 page=back visible=false frame="" left=0 top=0 width=8 height=8]
[trans method=crossfade time=300]
[wt]
[current layer=message0]
[history enabled=true]
[return]

*backtotitle
[rclick enabled=false jump=false]
[current layer=message0]
[jump storage="title.ks" target=*backtotitle]