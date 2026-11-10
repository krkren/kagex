*start|开始
; Effekseer effects (template/system/GFX_Effekseer.tjs, drawn by the krkreffekseer plugin). A World
; layer plays one with efk=<name>: the sample's are in data/effect (made by
; tools/assets/make_effects.py), their textures in data/effect/Texture. See efk in doc/world.txt.
[initscene]
[bgm01]
[road normal]
[night normal]
[if exp="!KAGEffekseerOf(kag).available"]
Effekseer 特效需要 krkreffekseer 插件和 OpenGL ES，这个版本没有，所以演示会跳过这部分。
[jump target=*static]
[endif]
[newlay name=petals efk=petals efkframe=600 still=petals_still show]
发光的花瓣飘过道路：这是放在世界扩展图层上的 Effekseer 特效，由 krkreffekseer 插件绘制。
[ai standard center]
【ai】花瓣……还会发光？
[newlay name=sparkle efk=sparkle efkwidth=900 efkheight=900 ypos=-150 still=sparkle_still show]
【ai】还有亮晶晶的光点，就在我身边！
每个特效都是独立的图层：efk= 指定特效，efkmag 决定大小，efkwidth 和 efkheight 设定画布的尺寸，画布和普通图层一样摆放。
[petals flipupdate efkstop]
[sparkle flipupdate efkstop]
[newlay name=fw1 efk=fireworks efkx=-520 efky=300 level=0 show]
[newlay name=fw2 efk=fireworks efkx=560 efky=260 efkmag=40 level=0 show]
【ai】是烟花！
只要图层还在播放，大约每秒就会升起一发烟花。
[newlay name=circle efk=magiccircle efkwidth=760 efkheight=560 xpos=-560 ypos=40 still=magiccircle_still show]
【ai】嗯？那边好像有什么在发光……
[newlay name=burst efk=shockwave efky=-120 show]
【ai】哇！
像刚才那样的爆炸只播放一次，结束后图层也会清除。
[circle flipupdate efkstop]
[fw1 flipupdate efkstop]
[fw2 flipupdate efkstop]
指定 efkstop 后，特效会停止产生粒子并淡出。
[dellay name=petals]
[dellay name=sparkle]
[dellay name=fw1]
[dellay name=fw2]
[dellay name=circle]
[dellay name=burst]
*static
; TV static and a tape running down: a World layer with static= draws static over the scene at the
; layer's opacity, and at level=message over the message window too (template/system/GFX_Static.tjs);
; pitch= and pan= change the World's music and sounds over time= (KAGEnvBGM.tjs). See static, level,
; and the BGM and SE Object Functions, in doc/world.txt.
[ai standard center]
【ai】接下来是一个故意出故障的特效。
[newlay name=tv static=tv staticbar=40 staticlines=90 opacity=0 level=message show]
[tv opacity=120 time=800]
画面变成了电视雪花：这是在 level=message 的世界图层上播放的 static 效果，按图层的不透明度画在场景和这个对话框之上。
[bgm pitch=35 time=2500]
【ai】还有音乐……越来越慢了，就像磁带快转不动了一样！
pitch= 会同时改变声音的速度和音高：这里音乐在两秒半内降到了 35%。
[se storage=se_steps loop=1 pan=-100]
[se name=se_steps pan=100 time=3000]
【ai】刚才是谁走过去了？
pan= 让声音在左右之间移动：这里的脚步声从一边走到了另一边。
[se name=se_steps stop=300]
[tv opacity=0 time=500]
[bgm pitch=100 time=800]
【ai】呼，一切都恢复正常了。
[dellay name=tv]
【ai】谢谢观看！
[ai hide fade]
*done
[demodone name=effect]
[jump storage=s0001.ks]
