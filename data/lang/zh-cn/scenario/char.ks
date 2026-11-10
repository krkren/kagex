*start|开始

; Environment initialization process
[initscene]

; BGM Playback
[bgm01]
[road normal]

这是使用 KAGEX 世界扩展编写的脚本示例。
用比较简单的写法，就能做出高级的演出效果。
打开 char.ks，对照实际的文件来看，会更容易理解。

[ai standard center]
角色登场

【ai】按规定的格式书写，就会自动显示名字、显示文字并等待按键。
【ai/？？？】想更改显示的名字，只要在斜杠后面写上显示名就行。
【ai/今天名字特别特别长的爱】名字太长、名字框放不下时，会被压缩到刚好放下（[[position namefit=squeeze]）。
【ai】指定了语音编号的话，就会在显示文字的同时播放语音。
【ai】自动播放时的等待时间也会自动调整。下一句会播放语音。

[ai voice=1]
【ai】初三消毒水地狱！

[ai voice=clear]
【ai】顺带一提，在调试菜单里可以更改语音的播放速度。

; Recollection end point
[endrecollection]

[ai posleft]
角色移动（左）

[ai backlevel]
角色层级变更（后方）

[ai center]
角色移动（中央）

[ai frontlevel]
角色层级变更（前方）

[ai centerlevel]
角色层级变更（中间）

[ai hide]
角色退场

[ai posleft fade]
角色登场／淡入淡出控制

[ai hide fade]
角色退场／淡入淡出控制

[ai center]
角色登场

[ai rotate=30 time=1000][ai zoom=120 time=1000]
图层旋转／缩放控制（动作不同步时）

[ai rotate=0 time=1000 sync][ai zoom=100 time=1000 sync]
图层旋转／缩放控制（动作同步时）

[evening normal]
傍晚（角色会自动进行色彩校正）

[night normal]
夜晚（角色会自动进行色彩校正）

[ai zoom=150 time=1000]
图层缩放控制

[ai opacity=100 time=1000]
不透明度控制

[ai reset]
重置图层状态

; Show event image
[EV file=event1 fade]
显示了事件图。

[EV rotate=30 time=1000]
旋转事件图

[EV rotate=@+30 time=1000]
旋转事件图（相对指定）※相对指定的写法改了，抱歉。

[EV zoom=200 time=1000]
缩放事件图

[EV zoom=@-50 time=1000]
缩放事件图（相对指定）

[EV hide fade]
清除事件图

[day normal]

[ai happy]
表情变化（开心）

[ai angry]
表情变化（生气）

[ai 103]
作者用的简写：[[ai 103] 就是姿势 1、表情 03，也就是悲伤（envinit.tjs 的 "shorthands"）

[ai far]
预设：[[ai far] 把爱送到更远的后方，站在其他人后面

[ai near]
而 [[ai near] 把她拉近到前面

[ai centerlevel happy]

[ai posright time=500]
指定时间的移动（→右）

[ai posright:center time=500]
指定初始位置的移动（中→右）

[ai posright:center opacity=255:0 time=500]
指定初始位置的移动（中→右，带不透明度控制）

; The music fades out here, so the positional sounds below can be heard on their own
[bgm stop=1500]
[ai opacity=255:0 zoom=100:140 time=500]
与缩放组合

; Positional sound: a sound placed on the stage is panned to where it is (doc/world.txt)
[se storage=se_chime pos=farleft]
舞台最左边响起的铃声（定位音效）

[se storage=se_chime pos=farright]
还有最右边

[se storage=se_steps loop=1 char=ai]
[ai posleft time=1500]
跟着爱一起走的脚步声
[se name=se_steps stop=300]

*voices|语音

; Voices from where the speakers stand: with envinit.tjs's "voice3d", Ai on the left is heard
; from the left and Pip on the right from the right (Config's second page centres them). A
; voice cut by the next one fades out, and vol= makes one line quieter (doc/world.txt)
[ai standard posleft opacity=255 zoom=100]
[pip standard posright]
语音会从说话人所站的位置传来

[ai voice=1]
【ai】初三消毒水地狱！
; [vo]: a voice file from the recording script, whose speaker the game works out (Pip's: pip%s%06d)
[pip xsurprised]
[vo pip000003]
哇！刚才那是什么？
在有人说话时点击：语音会淡出，而不是戛然而止（设置第二页）

[pip neutral voice=4 vol=35]
【pip】（小声）她一直都这样吗？
更轻的台词，悄悄话：[[pip voice=4 vol=35]
[pip hide]
【ai】对了，你就是[emb exp="kag.heroName()"]吧。很高兴认识你！
【hero】我也很高兴认识你。

*faces|头像

; Faces by the message window (since 0.18.0): the speaker's face, cut from their sprite as it
; looks now (envinit.tjs's faceCrop), crossfades to the next speaker's and goes for narration and
; CGs; a speaker who isn't on stage shows a face only ([pip facewin]), [env facewindow=off]
; turns them off for a scene, and Config turns them off for good
[ai standard center]
【ai】说话人的头像会显示在对话框旁边，和立绘现在的样子一模一样。
[ai angry]
【ai】就算我在生气也一样！
; a voice effect (since 0.28.0, the voicefx plugin): Pip's voice through the phone, until
; [pip voicefx=default] has it follow [env voicefx] again (VoiceEffects.tjs, voicefx.csv)
[pip facewin voicefx=phone voice=5]
【pip】我都不在舞台上哦。我是从别的地方打电话过来的！
[pip voicefx=default]
旁白没有头像。
[EV file=event1 fade]
【ai】在 CG 上面时，头像会让开。
[EV hide fade]
[env facewindow=off]
[ai happy]
【ai】一个场景可以不显示头像……
[env facewindow=on]
[pip hide]
【ai】……也可以再显示回来。

*layouts|腾出位置

; Layouts (since 0.18.0, envinit.tjs's "layouts"): [name join] brings a character on at the
; right (join=left, join=middle) while the others slide over to stand evenly spaced, [name leave]
; takes one off and the others close the gap, and [env makeroom=0] pushes them apart
[ai center time=300]
爱一个人站着。
[pip standard neutral join]
【pip】还能再加一个吗？
[newchar name=ai2 initname=ai]
[ai2 join=middle]
另一个爱从中间插了进来，其他人为她腾出位置。
[ai leave]
第一个爱离开了，空出来的地方随即合拢。
[env makeroom=0]
大家向两边散开，给中间的东西留出空间……
[ai2 delete]
[pip leave]
……然后大家都走了。

*flashback|回忆

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
现在，爱和皮普在街上。
[env keep]
[begintrans]
[pip hide]
[ai sad]
[memory]
[env grayscale=true]
[endtrans trans=normal]
一段灰色的回忆：很久以前，独自一人的爱。
; [memory] also gives the voices the memories' echo ([env voicefx=memory], since 0.28.0)
[ai voice=1]
【ai】初三消毒水地狱！
当年她说过的话，在耳边回响。
[env restore trans=normal]
然后回到现在，一切照旧，音乐也还在播放。
[bgm stop=1500]
[pip hide]
[ai hide]

*crossroads|选择

; A choice that parts the demo for a moment (since 0.24.0): the flowchart (Extras) draws both
; ways and where they meet again, and plays either one from its start with the choice made
[ai standard happy center]
【ai】进入下一部分之前：我们是经过公园，还是经过车站？
[seladd text="经过公园" target=*park exp="f.charRoute = 'park'"]
[seladd text="经过车站" target=*station exp="f.charRoute = 'station'"]
[select]

*park|经过公园
【ai】那就走公园吧。每年这个时候，树都特别好看。
[jump target=*staging]

*station|经过车站
【ai】那就走车站吧。听，火车的声音！
[jump target=*staging]

*staging|演出工具包

; The staging kit (since 0.18.0): twenty gestures, three screen shakes, a close-up, a veil for
; inner thoughts and an eyecatch card, a word each (envinit.tjs's actions, macro.ks's macros)
[ai standard happy center]
身体动作，一个词一种：[ai nod][wact]nod、[ai nods][wact]nods、[ai headshake][wact]headshake、[ai sigh][wact]sigh、[ai laugh][wact]laugh。
[ai shrug][wact]shrug、[ai lookaround][wact]lookaround、[ai wobble][wact]wobble、[ai slump][wact]slump、[ai startle][wact]startle。
[ai tremble][wact]tremble、[ai bounce][wact]bounce、[ai leanin][wact]leanin、[ai stepback][wact]stepback、[ai sway][wact]sway。
[ai stomp][wact]stomp、[ai pop][wact]pop、[ai tilt][wact]tilt、[ai giggle][wact]giggle、[ai faint][wact]faint。
画面：[quake][wact]quake、[thud][wact]thud、[rumble][wact]rumble。
[closeup]
[[closeup]：镜头拉近，她身后的背景变得模糊。
[closeupend]
[dim]
【ai】（[[dim]：给只在心里想的话罩上一层暗纱……）
[undim]
[whiten]
……或者一层白纱（[[whiten]）。
[undim]
[pip standard neutral posright trans=showslide]
皮普一边淡入一边滑进来（trans=showslide）。
[eyecatch]
[pip hide]
[ai hide]
过了 [[eyecatch] 之后，下一个场景开始。

*together|一起行动

; Objects that move with others (since 0.26.0, KAGEnvLinks.tjs): a prop attached to a character,
; a light clipped to one's outline, and a picture that follows another's; doc/world.txt
[ai standard happy posleft]
[pip standard plain neutral posright]
[newlay name=bubble file=prop_bubble attach=pip xpos=210 ypos=330 show]
贴在皮普身上的对话气泡（attach=pip）会跟着他走……
[pip center time=800][pip zoom=112 time=800][pip rotate=-12 time=800]
……和他一起移动、变大、旋转。
如果你刚才经过的是公园，这里的皮普会戴着贝雷帽，虽然脚本里写的仍是 plain：dressnamemap.txt 会根据之前的选择，把一套服装换成另一套。
[newlay name=light file=prop_light attach=ai clipto=ai xpos=180 ypos=760 opacity=220 show]
按爱的轮廓裁剪的暖光（clipto=ai）只照在她身上，不会照到她身后的东西。
[newlay name=view follow=ai zoom=38 flipx=true xpos=1180 ypos=1020 opacity=235 show]
一个小小的副本跟着她的画面（follow=ai），左右翻转，她眨眼时它也跟着眨。
[pip hide]
皮普离开时，他的气泡也跟着离开。
[ai hide]
爱的灯光和副本也一样。

*label6|角色动作

[newchar name=ai2 initname=ai center opacity=255:0 zoom=100:140 time=300 sync]
[newchar name=ai3 initname=ai posleft opacity=255:0 zoom=100:140 time=300 sync]
分身术

[ai bow]
[ai2 hop]
[ai3 shiver]
分别执行鞠躬／蹦跳／发抖动作

[ai midright time=500]
[ai3 midleft time=500]
移动到重叠的位置

[ai2 front]
把爱2移到前面

[ai2 back]
把爱2移到后面

[ai  xpos=-1920 time=500]
[ai2 xpos=-1920 time=500]
[ai3 xpos=-1920 time=500]
完

[demodone name=char]

[jump storage=s0001.ks]