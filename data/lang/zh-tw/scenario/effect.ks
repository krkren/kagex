*start|開始
; Effekseer effects (template/system/GFX_Effekseer.tjs, drawn by the krkreffekseer plugin). A World
; layer plays one with efk=<name>: the sample's are in data/effect (made by
; tools/assets/make_effects.py), their textures in data/effect/Texture. See efk in doc/world.txt.
[initscene]
[bgm01]
[road normal]
[night normal]
[if exp="!KAGEffekseerOf(kag).available"]
Effekseer 特效需要 krkreffekseer 外掛和 OpenGL ES，這個版本沒有，所以演示會跳過這部分。
[jump target=*static]
[endif]
[newlay name=petals efk=petals efkframe=600 still=petals_still show]
發光的花瓣飄過道路：這是放在世界擴充套件圖層上的 Effekseer 特效，由 krkreffekseer 外掛繪製。
[ai standard center]
【ai】花瓣……還會發光？
[newlay name=sparkle efk=sparkle efkwidth=900 efkheight=900 ypos=-150 still=sparkle_still show]
【ai】還有亮晶晶的光點，就在我身邊！
每個特效都是獨立的圖層：efk= 指定特效，efkmag 決定大小，efkwidth 和 efkheight 設定畫布的尺寸，畫布和普通圖層一樣擺放。
[petals flipupdate efkstop]
[sparkle flipupdate efkstop]
[newlay name=fw1 efk=fireworks efkx=-520 efky=300 level=0 show]
[newlay name=fw2 efk=fireworks efkx=560 efky=260 efkmag=40 level=0 show]
【ai】是煙花！
只要圖層還在播放，大約每秒就會升起一發煙花。
[newlay name=circle efk=magiccircle efkwidth=760 efkheight=560 xpos=-560 ypos=40 still=magiccircle_still show]
【ai】嗯？那邊好像有什麼在發光……
[newlay name=burst efk=shockwave efky=-120 show]
【ai】哇！
像剛才那樣的爆炸只播放一次，結束後圖層也會清除。
[circle flipupdate efkstop]
[fw1 flipupdate efkstop]
[fw2 flipupdate efkstop]
指定 efkstop 後，特效會停止產生粒子並淡出。
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
【ai】接下來是一個故意出故障的特效。
[newlay name=tv static=tv staticbar=40 staticlines=90 opacity=0 level=message show]
[tv opacity=120 time=800]
畫面變成了電視雪花：這是在 level=message 的世界圖層上播放的 static 效果，按圖層的不透明度畫在場景和這個對話方塊之上。
[bgm pitch=35 time=2500]
【ai】還有音樂……越來越慢了，就像磁帶快轉不動了一樣！
pitch= 會同時改變聲音的速度和音高：這裡音樂在兩秒半內降到了 35%。
[se storage=se_steps loop=1 pan=-100]
[se name=se_steps pan=100 time=3000]
【ai】剛才是誰走過去了？
pan= 讓聲音在左右之間移動：這裡的腳步聲從一邊走到了另一邊。
[se name=se_steps stop=300]
[tv opacity=0 time=500]
[bgm pitch=100 time=800]
【ai】呼，一切都恢復正常了。
[dellay name=tv]
【ai】謝謝觀看！
[ai hide fade]
*done
[demodone name=effect]
[jump storage=s0001.ks]
