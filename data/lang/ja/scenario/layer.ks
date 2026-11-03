*start|スタート

; Disable World Extension special environments
[linemode]
[csysbutton]

[layopt layer=message0 visible]
KAGEX のレイヤ拡張機能のサンプルです。[r]レイヤに対して回転・拡大縮小の制御ができます。
[l][r]

[image layer=base page=fore storage="bg01_01"  visible=true left=0 top=0]
[image layer=0     page=fore storage="ch_0_0_1" visible=true left=960 top=810 dafx=center dafy=center]
[cm]

スタート
[l][r]

*label1|半透明

[layopt layer=0 opacity=200]
半透明
[l][r]

*label2|回転

[layopt layer=0 reset]
[layopt layer=0 rotate=30]
回転
[l][r]

[layopt layer=0 afx=left afy=top]
回転原点変更（左上隅）
[l][r]

[layopt layer=0 afx=180 afy=180]
回転原点変更（座標指定）
[l][r]

[layopt layer=0 afx=center afy=center]
回転原点変更（センターに戻す）
[l][r]

*label3|拡大

[layopt layer=0 reset]
[layopt layer=0 zoom=150]
拡大
[l][r]

*label4|X拡大

[layopt layer=0 reset]
[layopt layer=0 zoomx=200]
X拡大
[l][r]

*label5|合成モード

[layopt layer=0 reset]
[layopt layer=0 type=ltPsDifference5]
合成モード
[l][r]

*label6|ガクブル

[layopt layer=0 reset]
[action layer=0 module=LayerVibrateActionModule vibration=20 waitTime=50]
ガクブル
[l][r]

*label7|縦ゆれ

[layopt layer=0 reset]
[action layer=0 module=LayerJumpActionModule vibration=20 cycle=1000]
縦ゆれ
[l][r]

*label8|横ゆれ

[layopt layer=0 reset]
[action layer=0 module=LayerWaveActionModule vibration=20 cycle=1000]
横ゆれ
[l][r]

*label9|指定角度に

[layopt layer=0 reset]
[action layer=0 module=LayerToRotateModule angle=30 time=1000]
指定角度に
[wact]
[action layer=0 module=LayerToRotateModule angle=-50 time=1000]
移動してみる
[wact]
[action layer=0 module=LayerToRotateModule angle=-0 time=1000]
テストだよ
[wact]
[l][r]

*label10|くるくるまわる

[layopt layer=0 reset]
[action layer=0 module=LayerNormalRotateModule angvel=100]
くるくるまわる
[l][r]

*label11|拡大率

[layopt layer=0 reset]
[action layer=0 module=LayerNormalZoomModule zoom=150 time=1000]
キャラをズーム（時間指定）
[l][r]

*label12|ズーム回転

[layopt layer=0 reset]
[action layer=0 module=LayerVRotateZoomModule angvel=100]
ズームを利用した回転っぽいなにか
[l][r]

*label13|不透明度

[layopt layer=0 reset]
[action layer=0 module=LayerFadeToModeModule opacity=128 time=1000]
指定した不透明度に（時間指定）
[l][r]

*label14|フェード点滅

[layopt layer=0 reset]
[action layer=0 module=LayerFadeModeModule intime=1000 outtime=1000]
フェード点滅
[l][r]

*label15|動画レイヤテスト

[layopt layer=0 reset]
[image layer=1 movie=test.webm alpha=2 loop visible=true dafx=center dafy=center left=960 top=540]
動画ロード
[l][r]

[layopt layer=1 zoom=50 time=1000]
ズーム変更
[l][r]

[layopt layer=1 rotate=120 time=1000]
回転
[l][r]

*label16|ベクター画像

[cm]
[freeimage layer=1]
[layopt layer=0 visible=false]
[image layer=1 page=fore storage="emblem_bitmap" visible=true left=540 top=370 dafx=center dafy=center]
[image layer=2 page=fore storage="emblem" visible=true left=1380 top=370 dafx=center dafy=center]
同じ絵を二つ：左は PNG、右は SVG のベクター画像です。
[l][r]

[layopt layer=1 zoom=210 time=1000]
[layopt layer=2 zoom=210 time=1000]
拡大すると PNG はぼやけますが、SVG は大きさごとに描き直されるのでくっきりしたままです。
[l][r]

[action layer=1 module=LayerNormalRotateModule angvel=60]
[action layer=2 module=LayerNormalRotateModule angvel=60]
どちらもほかのレイヤと同じように回転します。
[l][r]

*label17|CLIP STUDIO PAINT のレイヤ

[cm]
[freeimage layer=1]
[freeimage layer=2]
[image layer=1 page=fore storage="clip://emblem.clip/root/badge.bmp" visible=true left=960 top=370 dafx=156 dafy=156]
[image layer=2 page=fore storage="clip://emblem.clip/root/star.bmp" visible=true left=960 top=374 dafx=156 dafy=160]
CLIP STUDIO PAINT のファイルひとつから、レイヤを二枚それぞれ clip:// で読み込んでいます。
[l][r]

[layopt layer=1 zoom=200 time=800]
[layopt layer=2 zoom=200 time=800]
[action layer=1 module=LayerNormalRotateModule angvel=-30]
[action layer=2 module=LayerNormalRotateModule angvel=120]
なので、パーツごとに別々に動かせます。
[l][r]

[freeimage layer=1]
[freeimage layer=2]

*label18|Live2D モデル

; A Live2D model on a KAG layer: the l2d flip type (GFX_Live2D.tjs; "Optional parameters for
; l2d" in doc/kagex.txt). Hiyori's model comes from tools/assets/make_hiyori.py, and the
; krkrlive2d plugin is built with Live2D's Cubism SDK ("Live2D Characters" in doc/world.txt)
[cm]
[if exp="KAGLive2DCanDraw('hiyori')"]
[image layer=1 page=fore flip=hiyori.l2d l2dwidth=500 l2dheight=680 visible=true left=960 top=350 dafx=center dafy=center]
レイヤでは Live2D のモデルも再生できます。flip=hiyori.l2d で、モーションもまばたきも髪の揺れも、作られたとおりに動きます。このコンテンツは、株式会社 Live2D が著作権を保有するサンプルデータを使用しています。
[l][r]

[layopt layer=1 l2donce=TapBody]
l2donce はモデルのモーションをひとつ一度だけ再生し、そのあとは待機モーションに戻ります。
[l][r]

[layopt layer=1 zoom=70 rotate=-12 time=800]
もちろんふつうのレイヤと同じように、動かしたり、拡大したり、回したりもできます。
[l][r]

[freeimage layer=1]
[else]
このビルドでは Live2D モデルを再生できません。Live2D の Cubism SDK でビルドした krkrlive2d プラグインとモデルが必要です。追加のしかたは doc/world.txt の「Live2D Characters」にあります。
[l][r]
[endif]

*label19|3D モデルとシーン

; 3D on KAG layers: the 3d flip type (GFX_Three.tjs; "Optional parameters for 3d" in
; doc/kagex.txt), drawn by the krkrthreepp plugin. The stage is a scene built in script
; (data/main/Scenes3D.tjs); the star and Vee are the sample's own models (tools/assets/make_vrm.py)
[cm]
[if exp="KAGThreeCanDraw()"]
[image layer=1 page=fore flip=stage3d visible=true left=960 top=400 dafx=center dafy=center]
レイヤには 3D のシーンも表示できます。これはスクリプトで組み立てたシーンで、形とマテリアルとライトがあり、カメラがまわりを回ります。
[l][r]

[layopt layer=1 3donce=jump]
3donce は何かを一度だけ再生します。このシーンのスクリプトでは結び目が跳びます。
[l][r]

[freeimage layer=1]
[image layer=1 page=fore flip=star3d.glb 3dwidth=600 3dheight=600 3dframe="-0.7,0.7" visible=true left=960 top=440 dafx=center dafy=center]
glTF のモデルは自分のアニメーションを再生します。spin がずっと続き、3donce=hop で跳びます。
[layopt layer=1 3donce=hop]
[l][r]

[freeimage layer=1]
[image layer=2 page=fore flip=vee.vrm 3dmotion=vee_idle 3dframe="-0.03,1.47" 3dwidth=520 3dheight=860 visible=true left=960 top=470 dafx=center dafy=center]
VRM のアバターは立って、まばたきして、VRM アニメーションを再生します。3dmotion はずっと続き、3donce=vee_wave で一度手を振ります。
[layopt layer=2 3donce=vee_wave 3dexpression=happy]
[l][r]

[layopt layer=2 3dexpression="" 3dturn=90]
3dturn はモデルを回します。絵はふつうのレイヤと同じように、動かしたり、拡大したり、回したりできます。
[layopt layer=2 zoom=80 rotate=8 time=800]
[l][r]

[freeimage layer=2]
[else]
このビルドでは 3D を描けません。krkrthreepp プラグインと OpenGL ES が必要です。くわしくは doc/kagex.txt の「Optional parameters for 3d」にあります。
[l][r]
[endif]
[layopt layer=0 visible=true]

[demodone name=layer]

[jump storage=s0001.ks]