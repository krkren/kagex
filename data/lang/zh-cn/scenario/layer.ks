*start|开始

; Disable World Extension special environments
[linemode]
[csysbutton]

[layopt layer=message0 visible]
这是 KAGEX 图层扩展功能的示例。[r]可以控制图层的旋转和缩放。
[l][r]

[image layer=base page=fore storage="bg01_01"  visible=true left=0 top=0]
[image layer=0     page=fore storage="ch_0_0_1" visible=true left=960 top=810 dafx=center dafy=center]
[cm]

开始
[l][r]

*label1|半透明

[layopt layer=0 opacity=200]
半透明
[l][r]

*label2|旋转

[layopt layer=0 reset]
[layopt layer=0 rotate=30]
旋转
[l][r]

[layopt layer=0 afx=left afy=top]
更改旋转原点（左上角）
[l][r]

[layopt layer=0 afx=180 afy=180]
更改旋转原点（指定坐标）
[l][r]

[layopt layer=0 afx=center afy=center]
更改旋转原点（回到中心）
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

*label6|震动

[layopt layer=0 reset]
[action layer=0 module=LayerVibrateActionModule vibration=20 waitTime=50]
震动
[l][r]

*label7|纵向摇晃

[layopt layer=0 reset]
[action layer=0 module=LayerJumpActionModule vibration=20 cycle=1000]
纵向摇晃
[l][r]

*label8|横向摇晃

[layopt layer=0 reset]
[action layer=0 module=LayerWaveActionModule vibration=20 cycle=1000]
横向摇晃
[l][r]

*label9|转到指定角度

[layopt layer=0 reset]
[action layer=0 module=LayerToRotateModule angle=30 time=1000]
转到指定角度。
[wact]
[action layer=0 module=LayerToRotateModule angle=-50 time=1000]
再转一转看看。
[wact]
[action layer=0 module=LayerToRotateModule angle=-0 time=1000]
这是测试。
[wact]
[l][r]

*label10|转圈圈

[layopt layer=0 reset]
[action layer=0 module=LayerNormalRotateModule angvel=100]
转圈圈
[l][r]

*label11|缩放比例

[layopt layer=0 reset]
[action layer=0 module=LayerNormalZoomModule zoom=150 time=1000]
缩放角色（指定时间）
[l][r]

*label12|缩放旋转

[layopt layer=0 reset]
[action layer=0 module=LayerVRotateZoomModule angvel=100]
利用缩放做出的类似旋转的效果
[l][r]

*label13|不透明度

[layopt layer=0 reset]
[action layer=0 module=LayerFadeToModeModule opacity=128 time=1000]
变为指定的不透明度（指定时间）
[l][r]

*label14|淡入淡出闪烁

[layopt layer=0 reset]
[action layer=0 module=LayerFadeModeModule intime=1000 outtime=1000]
淡入淡出闪烁
[l][r]

*label15|视频图层测试

[layopt layer=0 reset]
[image layer=1 movie=test.webm alpha=2 loop visible=true dafx=center dafy=center left=960 top=540]
载入视频
[l][r]

[layopt layer=1 zoom=50 time=1000]
改变缩放
[l][r]

[layopt layer=1 rotate=120 time=1000]
旋转
[l][r]

*label16|矢量图像

[cm]
[freeimage layer=1]
[layopt layer=0 visible=false]
[image layer=1 page=fore storage="emblem_bitmap" visible=true left=540 top=370 dafx=center dafy=center]
[image layer=2 page=fore storage="emblem" visible=true left=1380 top=370 dafx=center dafy=center]
同一张图显示两次：左边是 PNG，右边是 SVG 矢量图像。
[l][r]

[layopt layer=1 zoom=210 time=1000]
[layopt layer=2 zoom=210 time=1000]
放大看看：PNG 会变模糊，而 SVG 会按每个尺寸重新绘制，始终清晰。
[l][r]

[action layer=1 module=LayerNormalRotateModule angvel=60]
[action layer=2 module=LayerNormalRotateModule angvel=60]
两张图都能像普通图层一样旋转。
[l][r]

*label17|CLIP STUDIO PAINT 图层

[cm]
[freeimage layer=1]
[freeimage layer=2]
[image layer=1 page=fore storage="clip://emblem.clip/root/badge.bmp" visible=true left=960 top=370 dafx=156 dafy=156]
[image layer=2 page=fore storage="clip://emblem.clip/root/star.bmp" visible=true left=960 top=374 dafx=156 dafy=160]
同一个 CLIP STUDIO PAINT 文件中的两个图层，分别用 clip:// 载入。
[l][r]

[layopt layer=1 zoom=200 time=800]
[layopt layer=2 zoom=200 time=800]
[action layer=1 module=LayerNormalRotateModule angvel=-30]
[action layer=2 module=LayerNormalRotateModule angvel=120]
所以每个部件都能各自活动。
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
图层也能播放 Live2D 模型：用 flip=hiyori.l2d，模型会按制作时的样子动起来，动作、眨眼、头发摆动一样不少。本内容使用了 Live2D Inc. 拥有著作权的示例数据。
[l][r]

[layopt layer=1 l2donce=TapBody]
l2donce 会把模型的某个动作播放一次，之后继续播放待机动作。
[l][r]

[layopt layer=1 zoom=70 rotate=-12 time=800]
而且它和普通图层一样，可以移动、缩放和旋转。
[l][r]

[freeimage layer=1]
[else]
这个版本无法播放 Live2D 模型。需要用 Live2D 的 Cubism SDK 构建的 krkrlive2d 插件，以及模型：添加方法请看 doc/world.txt 中的“Live2D Characters”。
[l][r]
[endif]

*label19|3D 模型与场景

; 3D on KAG layers: the 3d flip type (GFX_Three.tjs; "Optional parameters for 3d" in
; doc/kagex.txt), drawn by the krkrthreepp plugin. The stage is a scene built in script
; (data/main/Scenes3D.tjs); the star and Vee are the sample's own models (tools/assets/make_vrm.py)
[cm]
[if exp="KAGThreeCanDraw()"]
[image layer=1 page=fore flip=stage3d visible=true left=960 top=400 dafx=center dafy=center]
图层还能显示 3D 场景。这个场景是用脚本搭建的，有形状、材质和灯光，摄像机绕着它们转。
[l][r]

[layopt layer=1 3donce=jump]
3donce 会把某个动作播放一次：这个场景的脚本会让纽结跳起来。
[l][r]

[freeimage layer=1]
[image layer=1 page=fore flip=star3d.glb 3dwidth=600 3dheight=600 3dframe="-0.7,0.7" visible=true left=960 top=440 dafx=center dafy=center]
glTF 模型会播放自带的动画：spin 一直持续，3donce=hop 让它跳一下。
[layopt layer=1 3donce=hop]
[l][r]

[freeimage layer=1]
[image layer=2 page=fore flip=vee.vrm 3dmotion=vee_idle 3dframe="-0.03,1.47" 3dwidth=520 3dheight=860 visible=true left=960 top=470 dafx=center dafy=center]
VRM 虚拟形象也能站立、眨眼、播放 VRM 动画：3dmotion 一直持续，3donce=vee_wave 让她挥一次手。
[layopt layer=2 3donce=vee_wave 3dexpression=happy]
[l][r]

[layopt layer=2 3dexpression="" 3dturn=90]
3dturn 让模型转身，而画面本身就是普通图层：可以移动、缩放和旋转。
[layopt layer=2 zoom=80 rotate=8 time=800]
[l][r]

[freeimage layer=2]
[else]
这个版本无法绘制 3D。需要 krkrthreepp 插件和 OpenGL ES：详情请看 doc/kagex.txt 中的“Optional parameters for 3d”。
[l][r]
[endif]
[layopt layer=0 visible=true]

[demodone name=layer]

[jump storage=s0001.ks]