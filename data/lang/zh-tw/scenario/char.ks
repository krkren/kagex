*start|開始

; Environment initialization process
[initscene]

; BGM Playback
[bgm01]
[road normal]

這是使用 KAGEX 世界擴充套件編寫的指令碼示例。
用比較簡單的寫法，就能做出高階的演出效果。
開啟 char.ks，對照實際的檔案來看，會更容易理解。

[ai standard center]
角色登場

【ai】按規定的格式書寫，就會自動顯示名字、顯示文字並等待按鍵。
【ai/？？？】想更改顯示的名字，只要在斜槓後面寫上顯示名就行。
【ai/今天名字特別特別長的愛】名字太長、名字框放不下時，會被壓縮到剛好放下（[[position namefit=squeeze]）。
【ai】指定了語音編號的話，就會在顯示文字的同時播放語音。
【ai】自動播放時的等待時間也會自動調整。下一句會播放語音。

[ai voice=1]
【ai】初三消毒水地獄！

[ai voice=clear]
【ai】順帶一提，在除錯選單裡可以更改語音的播放速度。

; Recollection end point
[endrecollection]

[ai posleft]
角色移動（左）

[ai backlevel]
角色層級變更（後方）

[ai center]
角色移動（中央）

[ai frontlevel]
角色層級變更（前方）

[ai centerlevel]
角色層級變更（中間）

[ai hide]
角色退場

[ai posleft fade]
角色登場／淡入淡出控制

[ai hide fade]
角色退場／淡入淡出控制

[ai center]
角色登場

[ai rotate=30 time=1000][ai zoom=120 time=1000]
圖層旋轉／縮放控制（動作不同步時）

[ai rotate=0 time=1000 sync][ai zoom=100 time=1000 sync]
圖層旋轉／縮放控制（動作同步時）

[evening normal]
傍晚（角色會自動進行色彩校正）

[night normal]
夜晚（角色會自動進行色彩校正）

[ai zoom=150 time=1000]
圖層縮放控制

[ai opacity=100 time=1000]
不透明度控制

[ai reset]
重置圖層狀態

; Show event image
[EV file=event1 fade]
顯示了事件圖。

[EV rotate=30 time=1000]
旋轉事件圖

[EV rotate=@+30 time=1000]
旋轉事件圖（相對指定）※相對指定的寫法改了，抱歉。

[EV zoom=200 time=1000]
縮放事件圖

[EV zoom=@-50 time=1000]
縮放事件圖（相對指定）

[EV hide fade]
清除事件圖

[day normal]

[ai happy]
表情變化（開心）

[ai angry]
表情變化（生氣）

[ai 103]
作者用的簡寫：[[ai 103] 就是姿勢 1、表情 03，也就是悲傷（envinit.tjs 的 "shorthands"）

[ai far]
預設：[[ai far] 把愛送到更遠的後方，站在其他人後面

[ai near]
而 [[ai near] 把她拉近到前面

[ai centerlevel happy]

[ai posright time=500]
指定時間的移動（→右）

[ai posright:center time=500]
指定初始位置的移動（中→右）

[ai posright:center opacity=255:0 time=500]
指定初始位置的移動（中→右，帶不透明度控制）

; The music fades out here, so the positional sounds below can be heard on their own
[bgm stop=1500]
[ai opacity=255:0 zoom=100:140 time=500]
與縮放組合

; Positional sound: a sound placed on the stage is panned to where it is (doc/world.txt)
[se storage=se_chime pos=farleft]
舞臺最左邊響起的鈴聲（定位音效）

[se storage=se_chime pos=farright]
還有最右邊

[se storage=se_steps loop=1 char=ai]
[ai posleft time=1500]
跟著愛一起走的腳步聲
[se name=se_steps stop=300]

*voices|語音

; Voices from where the speakers stand: with envinit.tjs's "voice3d", Ai on the left is heard
; from the left and Pip on the right from the right (Config's second page centres them). A
; voice cut by the next one fades out, and vol= makes one line quieter (doc/world.txt)
[ai standard posleft opacity=255 zoom=100]
[pip standard posright]
語音會從說話人所站的位置傳來

[ai voice=1]
【ai】初三消毒水地獄！
; [vo]: a voice file from the recording script, whose speaker the game works out (Pip's: pip%s%06d)
[pip xsurprised]
[vo pip000003]
哇！剛才那是什麼？
在有人說話時點選：語音會淡出，而不是戛然而止（設定第二頁）

[pip neutral voice=4 vol=35]
【pip】（小聲）她一直都這樣嗎？
更輕的臺詞，悄悄話：[[pip voice=4 vol=35]
[pip hide]
【ai】對了，你就是[emb exp="kag.heroName()"]吧。很高興認識你！
【hero】我也很高興認識你。

*faces|頭像

; Faces by the message window (since 0.18.0): the speaker's face, cut from their sprite as it
; looks now (envinit.tjs's faceCrop), crossfades to the next speaker's and goes for narration and
; CGs; a speaker who isn't on stage shows a face only ([pip facewin]), [env facewindow=off]
; turns them off for a scene, and Config turns them off for good
[ai standard center]
【ai】說話人的頭像會顯示在對話方塊旁邊，和立繪現在的樣子一模一樣。
[ai angry]
【ai】就算我在生氣也一樣！
; a voice effect (since 0.28.0, the voicefx plugin): Pip's voice through the phone, until
; [pip voicefx=default] has it follow [env voicefx] again (VoiceEffects.tjs, voicefx.csv)
[pip facewin voicefx=phone voice=5]
【pip】我都不在舞臺上哦。我是從別的地方打電話過來的！
[pip voicefx=default]
旁白沒有頭像。
[EV file=event1 fade]
【ai】在 CG 上面時，頭像會讓開。
[EV hide fade]
[env facewindow=off]
[ai happy]
【ai】一個場景可以不顯示頭像……
[env facewindow=on]
[pip hide]
【ai】……也可以再顯示回來。

*layouts|騰出位置

; Layouts (since 0.18.0, envinit.tjs's "layouts"): [name join] brings a character on at the
; right (join=left, join=middle) while the others slide over to stand evenly spaced, [name leave]
; takes one off and the others close the gap, and [env makeroom=0] pushes them apart
[ai center time=300]
愛一個人站著。
[pip standard neutral join]
【pip】還能再加一個嗎？
[newchar name=ai2 initname=ai]
[ai2 join=middle]
另一個愛從中間插了進來，其他人為她騰出位置。
[ai leave]
第一個愛離開了，空出來的地方隨即合攏。
[env makeroom=0]
大家向兩邊散開，給中間的東西留出空間……
[ai2 delete]
[pip leave]
……然後大家都走了。

*flashback|回憶

; Keeping a scene (since 0.18.0): [env keep] puts the whole World away (stage, characters, layers,
; camera, colour), a flashback plays in grey, and [env restore] brings it all back as it was while
; the music plays on ([env keep sound=true] keeps the sounds too; keep=<name> for named copies).
; [memory] (macro.ks, since 0.22.0) gives it bars, a sepia edge and the memories' message window
; ([env msgstyle=memory], the style AfterInit.tjs defines), which [env restore] takes away again.
; The changes go between [begintrans] and [endtrans trans=normal], so the memory fades in as one,
; window included, and [env restore trans=normal] fades from the memory back to the street (0.23.0)
[bgm01]
[ai standard happy center]
[pip standard neutral posright]
現在，愛和皮普在街上。
[env keep]
[begintrans]
[pip hide]
[ai sad]
[memory]
[env grayscale=true]
[endtrans trans=normal]
一段灰色的回憶：很久以前，獨自一人的愛。
; [memory] also gives the voices the memories' echo ([env voicefx=memory], since 0.28.0)
[ai voice=1]
【ai】初三消毒水地獄！
當年她說過的話，在耳邊迴響。
[env restore trans=normal]
然後回到現在，一切照舊，音樂也還在播放。
[bgm stop=1500]
[pip hide]
[ai hide]

*crossroads|選擇

; A choice that parts the demo for a moment (since 0.24.0): the flowchart (Extras) draws both
; ways and where they meet again, and plays either one from its start with the choice made
[ai standard happy center]
【ai】進入下一部分之前：我們是經過公園，還是經過車站？
[seladd text="經過公園" target=*park exp="f.charRoute = 'park'"]
[seladd text="經過車站" target=*station exp="f.charRoute = 'station'"]
[select]

*park|經過公園
【ai】那就走公園吧。每年這個時候，樹都特別好看。
[jump target=*staging]

*station|經過車站
【ai】那就走車站吧。聽，火車的聲音！
[jump target=*staging]

*staging|演出工具包

; The staging kit (since 0.18.0): twenty gestures, three screen shakes, a close-up, a veil for
; inner thoughts and an eyecatch card, a word each (envinit.tjs's actions, macro.ks's macros)
[ai standard happy center]
身體動作，一個詞一種：[ai nod][wact]nod、[ai nods][wact]nods、[ai headshake][wact]headshake、[ai sigh][wact]sigh、[ai laugh][wact]laugh。
[ai shrug][wact]shrug、[ai lookaround][wact]lookaround、[ai wobble][wact]wobble、[ai slump][wact]slump、[ai startle][wact]startle。
[ai tremble][wact]tremble、[ai bounce][wact]bounce、[ai leanin][wact]leanin、[ai stepback][wact]stepback、[ai sway][wact]sway。
[ai stomp][wact]stomp、[ai pop][wact]pop、[ai tilt][wact]tilt、[ai giggle][wact]giggle、[ai faint][wact]faint。
畫面：[quake][wact]quake、[thud][wact]thud、[rumble][wact]rumble。
[closeup]
[[closeup]：鏡頭拉近，她身後的背景變得模糊。
[closeupend]
[dim]
【ai】（[[dim]：給只在心裡想的話罩上一層暗紗……）
[undim]
[whiten]
……或者一層白紗（[[whiten]）。
[undim]
[pip standard neutral posright trans=showslide]
皮普一邊淡入一邊滑進來（trans=showslide）。
[eyecatch]
[pip hide]
[ai hide]
過了 [[eyecatch] 之後，下一個場景開始。

*together|一起行動

; Objects that move with others (since 0.26.0, KAGEnvLinks.tjs): a prop attached to a character,
; a light clipped to one's outline, and a picture that follows another's; doc/world.txt
[ai standard happy posleft]
[pip standard plain neutral posright]
[newlay name=bubble file=prop_bubble attach=pip xpos=210 ypos=330 show]
貼在皮普身上的對話氣泡（attach=pip）會跟著他走……
[pip center time=800][pip zoom=112 time=800][pip rotate=-12 time=800]
……和他一起移動、變大、旋轉。
如果你剛才經過的是公園，這裡的皮普會戴著貝雷帽，雖然指令碼里寫的仍是 plain：dressnamemap.txt 會根據之前的選擇，把一套服裝換成另一套。
[newlay name=light file=prop_light attach=ai clipto=ai xpos=180 ypos=760 opacity=220 show]
按愛的輪廓裁剪的暖光（clipto=ai）只照在她身上，不會照到她身後的東西。
[newlay name=view follow=ai zoom=38 flipx=true xpos=1180 ypos=1020 opacity=235 show]
一個小小的副本跟著她的畫面（follow=ai），左右翻轉，她眨眼時它也跟著眨。
[pip hide]
皮普離開時，他的氣泡也跟著離開。
[ai hide]
愛的燈光和副本也一樣。

*label6|角色動作

[newchar name=ai2 initname=ai center opacity=255:0 zoom=100:140 time=300 sync]
[newchar name=ai3 initname=ai posleft opacity=255:0 zoom=100:140 time=300 sync]
分身術

[ai bow]
[ai2 hop]
[ai3 shiver]
分別執行鞠躬／蹦跳／發抖動作

[ai midright time=500]
[ai3 midleft time=500]
移動到重疊的位置

[ai2 front]
把愛2移到前面

[ai2 back]
把愛2移到後面

[ai  xpos=-1920 time=500]
[ai2 xpos=-1920 time=500]
[ai3 xpos=-1920 time=500]
完

[demodone name=char]

[jump storage=s0001.ks]