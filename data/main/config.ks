; 
; Configuration Settings
;

; Call from within the game
*startFromGame
[rclick enabled=true jump=true storage="" target=*backtogame]
[eval exp='tf.fromTitle = 0, tf.configPage = 1']
; Undo and Revert take back what's changed from here (KAGOptionUndo, Options.tjs)
[eval exp="KAGOptionUndo.begin()"]
[history enabled=false]
[jump target=*buttons]

; Call from title
*startFromTitle
[rclick enabled=true jump=true storage="" target=*backtotitle]
[eval exp='tf.fromTitle = 1, tf.configPage = 1']
[eval exp="KAGOptionUndo.begin()"]

; Back from the hero's name (namescreen.ks), on the page it was opened from
*fromName
[rclick enabled=true jump=true storage="" target=*backtotitle cond="tf.fromTitle"]
[rclick enabled=true jump=true storage="" target=*backtogame cond="!tf.fromTitle"]

*buttons

; Load base image: the page shown (tf.configPage; its tabs are below). Pages 2 and on are the
; options table's rows (template/system/Options.tjs, configPages in Override.tjs)
[backlay]
[position layer=message1 frame="config_base" left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true  transparent=false page=back cond="tf.configPage <= 1"]
[position layer=message1 frame="config_pages_base" left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true  transparent=false page=back cond="tf.configPage > 1"]
[current layer=message1 page=back]
[jump target=*options cond="tf.configPage > 1"]

; Button placement

; Screen Mode
[locate x=322 y=266]
[button name="config_window"     exp='setScreenButton(true)']
[locate x=578 y=266]
[button name="config_fullscreen" exp='setScreenButton(false)']

; The settings are options (Options.tjs), so Undo and Revert take them back; the volumes'
; sliders play a sample as they're pointed at and moved (KAGVolumeSamples)

; Text Speed
[locate x=402 y=396]
[slider name=textspeed width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=10 position="&KAGOptionGet('textSpeed')" onchangefunc=KAGOptionSlide onchangefuncdata="'textSpeed'" nohilight]

; Auto Speed
[locate x=402 y=526]
[slider name=autospeed width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=10 position="&KAGOptionGet('autoModeSpeed')" onchangefunc=KAGOptionSlide onchangefuncdata="'autoModeSpeed'" nohilight]

; Screen Effects
[locate x=322 y=656]
[button name=config_effecton exp="setNoEffectButton(false)"]
[locate x=578 y=656]
[button name=config_effectoff exp="setNoEffectButton(true)"]

; Skip
[locate x=322 y=786]
[button name="config_skipall" exp="setSkipButton(true)"]
[locate x=578 y=786]
[button name="config_skipalrdy" exp="setSkipButton(false)"]

; Language: the screen is drawn again in the one chosen (setLanguageButton, Override.tjs)
[locate x=322 y=916]
[button name="config_lang_en" exp="setLanguageButton('en')"]
[locate x=578 y=916]
[button name="config_lang_ja" exp="setLanguageButton('ja')"]

; BGM Volume
[locate x=1102 y=266]
[slider name=bgmvolume width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=100 position="&KAGOptionGet('bgmVolume')" onchangefunc=KAGOptionSlide onchangefuncdata="'bgmVolume'" previewfunc=KAGOptionPreview previewfuncdata="'bgmVolume'" nohilight]

; SE Volume
[locate x=1102 y=396]
[slider name=sevolume width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=100 position="&KAGOptionGet('seVolume')" onchangefunc=KAGOptionSlide onchangefuncdata="'seVolume'" previewfunc=KAGOptionPreview previewfuncdata="'seVolume'" nohilight]

; VOICE Volume
[locate x=1102 y=526]
[slider name=voicevolume width=416 height=60 opacity=0 normal="slidebar" over="slidebar_over" min=0 max=100 position="&KAGOptionGet('voiceVolume')" onchangefunc=KAGOptionSlide onchangefuncdata="'voiceVolume'" previewfunc=KAGOptionPreview previewfuncdata="'voiceVolume'" nohilight]

; Voice Buttons: a character's each (envinit.tjs's voiceName); page 5 has their volumes
[locate x=1022 y=656]
[button name="config_voice0" normal="config_voice0_on" exp="setVoiceOnButton('voice0')"]
[locate x=1218 y=656]
[button name="config_voice1" normal="config_voice1_on" exp="setVoiceOnButton('voice1')"]
[locate x=1414 y=656]
[button name="config_voice2" normal="config_voice2_on" exp="setVoiceOnButton('voice2')"]
[locate x=1022 y=732]
[button name="config_voice3" normal="config_voice3_on" exp="setVoiceOnButton('voice3')"]
[jump target=*nav]

*options
; the page's options, laid out from the table: their titles, buttons and sliders
[eval exp="configOptionsPage()"]

*nav
; The pages' tabs (the save screens' page buttons), each with a tip of what it holds; nine of
; them fit between the title and Default 3 px apart
[locate x=584 y=78]
[button name="page1" exp="setConfigPage(1)" hint="Sound and Text"]
[locate x=643 y=78]
[button name="page2" exp="setConfigPage(2)" hint="Voices, Saves and Screenshots"]
[locate x=702 y=78]
[button name="page3" exp="setConfigPage(3)" hint="Reading"]
[locate x=761 y=78]
[button name="page4" exp="setConfigPage(4)" hint="On the Screen"]
[locate x=820 y=78]
[button name="page5" exp="setConfigPage(5)" hint="Each Character's Voice"]
[locate x=879 y=78]
[button name="page6" exp="setConfigPage(6)" hint="Screen and Controls"]
[locate x=938 y=78]
[button name="page7" exp="setConfigPage(7)" hint="How Text Looks"]
[if exp="kag.languageAvailable"]
[locate x=997 y=78]
[button name="page8" exp="setConfigPage(8)" hint="Languages"]
[endif]
[locate x=1056 y=78]
[button name="page9" exp="setConfigPage(9)" hint="Reading Aloud, the Background and Screenshots"]

; Under the panels: the manual (Manual.tjs, since 0.26.0), Controls, the list of what each key and
; button does (Controls.tjs), where the engine can show it; Undo (the last change) and Revert
; (every change since the screen opened)
[if exp="KAGManualAvailable()"]
[locate x=880 y=1002]
[button name="config_manual" exp="KAGShowManual()"]
[endif]
[if exp="KAGElementsScreenAvailable()"]
[locate x=1070 y=1002]
[button name="config_controls" exp="kag.showControls()"]
[endif]
[locate x=1260 y=1002]
[button name="config_undo" exp="configUndo()"]
[locate x=1450 y=1002]
[button name="config_revert" exp="configRevert()"]

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
[trans screen method=crossfade time=300]
[wt]
[current layer=message1 page=fore]
[s]

*backtogame
[rclick jump=false]
[eval exp="configLeave()"]
[stoptrans]
[backlay]
[position layer=message1 page=back visible=false frame="" left=0 top=0 width=8 height=8]
[trans screen method=crossfade time=300]
[wt]
[current layer=message0]
[history enabled=true]
[return]

*backtotitle
[rclick enabled=false jump=false]
[eval exp="configLeave()"]
[current layer=message0]
[jump storage="title.ks" target=*backtotitle]