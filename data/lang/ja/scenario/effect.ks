*start|スタート
; Effekseer effects (template/system/GFX_Effekseer.tjs, drawn by the krkreffekseer plugin). A World
; layer plays one with efk=<name>: the sample's are in data/effect (made by
; tools/assets/make_effects.py), their textures in data/effect/Texture. See efk in doc/world.txt.
[initscene]
[bgm01]
[road normal]
[night normal]
[if exp="!KAGEffekseerOf(kag).available"]
Effekseer エフェクトには krkreffekseer プラグインと OpenGL ES が必要ですが、このビルドにはないのでデモはここで終わりです。
[jump target=*done]
[endif]
[newlay name=petals efk=petals efkframe=600 show]
光る花びらが道に舞います。World レイヤに置いた Effekseer エフェクトを krkreffekseer プラグインが描いています。
[ai standard center]
【ai】花びら……光ってる？
[newlay name=sparkle efk=sparkle efkwidth=900 efkheight=900 ypos=-150 show]
【ai】キラキラも、まわりじゅうに！
エフェクトはそれぞれ独立したレイヤです。efk= で指定し、efkmag で大きさを決め、efkwidth と efkheight でキャンバスの大きさを決めます。配置はふつうのレイヤと同じです。
[petals flipupdate efkstop]
[sparkle flipupdate efkstop]
[newlay name=fw1 efk=fireworks efkx=-520 efky=300 level=0 show]
[newlay name=fw2 efk=fireworks efkx=560 efky=260 efkmag=40 level=0 show]
【ai】花火だ！
レイヤが再生されているあいだ、だいたい一秒に一発ずつ打ち上がります。
[newlay name=circle efk=magiccircle efkwidth=760 efkheight=560 xpos=-560 ypos=40 show]
【ai】ん？ あっちで何か光ってる……
[newlay name=burst efk=shockwave efky=-120 show]
【ai】わっ！
今のような爆発は一度だけ再生され、終わるとレイヤも消えます。
[circle flipupdate efkstop]
[fw1 flipupdate efkstop]
[fw2 flipupdate efkstop]
efkstop を指定すると、エフェクトはパーティクルを出すのをやめてフェードアウトします。
【ai】見てくれてありがとう！
[ai hide fade]
[dellay name=petals]
[dellay name=sparkle]
[dellay name=fw1]
[dellay name=fw2]
[dellay name=circle]
[dellay name=burst]
*done
[demodone name=effect]
[jump storage=s0001.ks]
