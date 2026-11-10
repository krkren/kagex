*start|開始

; Disable World Extension special environments
[linemode]
[csysbutton]

[layopt layer=message0 visible]
這是 KAGEX 圖層擴充套件功能的示例。[r]可以控制圖層的旋轉和縮放。
[l][r]

[image layer=base page=fore storage="bg01_01"  visible=true left=0 top=0]
[image layer=0     page=fore storage="ch_0_0_1" visible=true left=960 top=810 dafx=center dafy=center]
[cm]

開始
[l][r]

*label1|半透明

[layopt layer=0 opacity=200]
半透明
[l][r]

*label2|旋轉

[layopt layer=0 reset]
[layopt layer=0 rotate=30]
旋轉
[l][r]

[layopt layer=0 afx=left afy=top]
更改旋轉原點（左上角）
[l][r]

[layopt layer=0 afx=180 afy=180]
更改旋轉原點（指定座標）
[l][r]

[layopt layer=0 afx=center afy=center]
更改旋轉原點（回到中心）
[l][r]

*label3|放大

[layopt layer=0 reset]
[layopt layer=0 zoom=150]
放大
[l][r]

*label4|X 方向放大

[layopt layer=0 reset]
[layopt layer=0 zoomx=200]
X 方向放大
[l][r]

*label5|混合模式

[layopt layer=0 reset]
[layopt layer=0 type=ltPsDifference5]
混合模式
[l][r]

*label6|震動

[layopt layer=0 reset]
[action layer=0 module=LayerVibrateActionModule vibration=20 waitTime=50]
震動
[l][r]

*label7|縱向搖晃

[layopt layer=0 reset]
[action layer=0 module=LayerJumpActionModule vibration=20 cycle=1000]
縱向搖晃
[l][r]

*label8|橫向搖晃

[layopt layer=0 reset]
[action layer=0 module=LayerWaveActionModule vibration=20 cycle=1000]
橫向搖晃
[l][r]

*label9|轉到指定角度

[layopt layer=0 reset]
[action layer=0 module=LayerToRotateModule angle=30 time=1000]
轉到指定角度。
[wact]
[action layer=0 module=LayerToRotateModule angle=-50 time=1000]
再轉一轉看看。
[wact]
[action layer=0 module=LayerToRotateModule angle=-0 time=1000]
這是測試。
[wact]
[l][r]

*label10|轉圈圈

[layopt layer=0 reset]
[action layer=0 module=LayerNormalRotateModule angvel=100]
轉圈圈
[l][r]

*label11|縮放比例

[layopt layer=0 reset]
[action layer=0 module=LayerNormalZoomModule zoom=150 time=1000]
縮放角色（指定時間）
[l][r]

*label12|縮放旋轉

[layopt layer=0 reset]
[action layer=0 module=LayerVRotateZoomModule angvel=100]
利用縮放做出的類似旋轉的效果
[l][r]

*label13|不透明度

[layopt layer=0 reset]
[action layer=0 module=LayerFadeToModeModule opacity=128 time=1000]
變為指定的不透明度（指定時間）
[l][r]

*label14|淡入淡出閃爍

[layopt layer=0 reset]
[action layer=0 module=LayerFadeModeModule intime=1000 outtime=1000]
淡入淡出閃爍
[l][r]

*label15|影片圖層測試

[layopt layer=0 reset]
[image layer=1 movie=test.webm alpha=2 loop visible=true dafx=center dafy=center left=960 top=540]
載入影片
[l][r]

[layopt layer=1 zoom=50 time=1000]
改變縮放
[l][r]

[layopt layer=1 rotate=120 time=1000]
旋轉
[l][r]

*label16|向量影象

[cm]
[freeimage layer=1]
[layopt layer=0 visible=false]
[image layer=1 page=fore storage="emblem_bitmap" visible=true left=540 top=370 dafx=center dafy=center]
[image layer=2 page=fore storage="emblem" visible=true left=1380 top=370 dafx=center dafy=center]
同一張圖顯示兩次：左邊是 PNG，右邊是 SVG 向量影象。
[l][r]

[layopt layer=1 zoom=210 time=1000]
[layopt layer=2 zoom=210 time=1000]
放大看看：PNG 會變模糊，而 SVG 會按每個尺寸重新繪製，始終清晰。
[l][r]

[action layer=1 module=LayerNormalRotateModule angvel=60]
[action layer=2 module=LayerNormalRotateModule angvel=60]
兩張圖都能像普通圖層一樣旋轉。
[l][r]

*label17|CLIP STUDIO PAINT 圖層

[cm]
[freeimage layer=1]
[freeimage layer=2]
[image layer=1 page=fore storage="clip://emblem.clip/root/badge.bmp" visible=true left=960 top=370 dafx=156 dafy=156]
[image layer=2 page=fore storage="clip://emblem.clip/root/star.bmp" visible=true left=960 top=374 dafx=156 dafy=160]
同一個 CLIP STUDIO PAINT 檔案中的兩個圖層，分別用 clip:// 載入。
[l][r]

[layopt layer=1 zoom=200 time=800]
[layopt layer=2 zoom=200 time=800]
[action layer=1 module=LayerNormalRotateModule angvel=-30]
[action layer=2 module=LayerNormalRotateModule angvel=120]
所以每個部件都能各自活動。
[l][r]

[freeimage layer=1]
[freeimage layer=2]

*label18|Live2D 模型

; A Live2D model on a KAG layer: the l2d flip type (GFX_Live2D.tjs; "Optional parameters for
; l2d" in doc/kagex.txt). Hiyori's model comes from tools/assets/make_hiyori.py, and the
; krkrlive2d plugin is built with Live2D's Cubism SDK ("Live2D Characters" in doc/world.txt)
[cm]
[if exp="KAGLive2DCanDraw('hiyori')"]
[image layer=1 page=fore flip=hiyori.l2d l2dwidth=500 l2dheight=680 visible=true left=960 top=350 dafx=center dafy=center]
圖層也能播放 Live2D 模型：用 flip=hiyori.l2d，模型會按製作時的樣子動起來，動作、眨眼、頭髮擺動一樣不少。本內容使用了 Live2D Inc. 擁有著作權的示例資料。
[l][r]

[layopt layer=1 l2donce=TapBody]
l2donce 會把模型的某個動作播放一次，之後繼續播放待機動作。
[l][r]

[layopt layer=1 zoom=70 rotate=-12 time=800]
而且它和普通圖層一樣，可以移動、縮放和旋轉。
[l][r]

[freeimage layer=1]
[else]
這個版本無法播放 Live2D 模型。需要用 Live2D 的 Cubism SDK 構建的 krkrlive2d 外掛，以及模型：新增方法請看 doc/world.txt 中的“Live2D Characters”。
[l][r]
[endif]

*label19|3D 模型與場景

; 3D on KAG layers: the 3d flip type (GFX_Three.tjs; "Optional parameters for 3d" in
; doc/kagex.txt), drawn by the krkrthreepp plugin. The stage is a scene built in script
; (data/main/Scenes3D.tjs); the star and Vee are the sample's own models (tools/assets/make_vrm.py)
[cm]
[if exp="KAGThreeCanDraw()"]
[image layer=1 page=fore flip=stage3d visible=true left=960 top=400 dafx=center dafy=center]
圖層還能顯示 3D 場景。這個場景是用指令碼搭建的，有形狀、材質和燈光，攝像機繞著它們轉。
[l][r]

[layopt layer=1 3donce=jump]
3donce 會把某個動作播放一次：這個場景的指令碼會讓紐結跳起來。
[l][r]

[freeimage layer=1]
[image layer=1 page=fore flip=star3d.glb 3dwidth=600 3dheight=600 3dframe="-0.7,0.7" visible=true left=960 top=440 dafx=center dafy=center]
glTF 模型會播放自帶的動畫：spin 一直持續，3donce=hop 讓它跳一下。
[layopt layer=1 3donce=hop]
[l][r]

[freeimage layer=1]
[image layer=2 page=fore flip=vee.vrm 3dmotion=vee_idle 3dframe="-0.03,1.47" 3dwidth=520 3dheight=860 visible=true left=960 top=470 dafx=center dafy=center]
VRM 虛擬形象也能站立、眨眼、播放 VRM 動畫：3dmotion 一直持續，3donce=vee_wave 讓她揮一次手。
[layopt layer=2 3donce=vee_wave 3dexpression=happy]
[l][r]

[layopt layer=2 3dexpression="" 3dturn=90]
3dturn 讓模型轉身，而畫面本身就是普通圖層：可以移動、縮放和旋轉。
[layopt layer=2 zoom=80 rotate=8 time=800]
[l][r]

[freeimage layer=2]
[else]
這個版本無法繪製 3D。需要 krkrthreepp 外掛和 OpenGL ES：詳情請看 doc/kagex.txt 中的“Optional parameters for 3d”。
[l][r]
[endif]
[layopt layer=0 visible=true]

[demodone name=layer]

[jump storage=s0001.ks]