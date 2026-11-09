;
; The hero's name: given and family names, from the title's START the first time and from
; Config (Override.tjs: nameInit, nameOK; the framework's kag.setHeroName)
;
*start
[eval exp="tf.nameFrom = 'start', nameStart()"]
[rclick enabled=false]
[jump target=*screen]

*fromConfig
[eval exp="tf.nameFrom = 'config'"]
[rclick enabled=false]

*screen
[backlay]
[position layer=message1 frame="name_base" left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true transparent=false page=back]
[current layer=message1 page=back]
; the rows' titles, the fields' backgrounds, a refused name's reason
[eval exp="nameInit()"]
[locate x=330 y=274]
[edit name="tf.heroGiven" prompt="Given Name" length=600 fontheight=36 fontbold=true color=0x24107a bgcolor=0xffffff opacity=0 noborder=true maxchars=12 enter="nameOK()"]
[locate x=1030 y=274]
[edit name="tf.heroFamily" prompt="Family Name" length=560 fontheight=36 fontbold=true color=0x24107a bgcolor=0xffffff opacity=0 noborder=true maxchars=12 enter="nameOK()"]
[locate x=1118 y=470]
[button name="name_default" normal="config_choice240_normal" over="config_choice240_over" exp="nameDefault()"]
[locate x=1374 y=470]
[button name="name_ok" normal="config_choice240_normal" over="config_choice240_over" exp="nameOK()"]
[eval exp="nameButtons()"]
[trans screen method=crossfade time=300]
[wt]
[current layer=message1 page=fore]
[eval exp="nameFocus()"]
[s]

*done
[backlay]
[position layer=message1 page=back visible=false frame="" left=0 top=0 width=8 height=8]
[trans screen method=crossfade time=300]
[wt]
[current layer=message0]
[jump storage=config.ks target=*fromName cond="tf.nameFrom == 'config'"]
[jump storage=s0001.ks]
