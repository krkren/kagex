*start|Start

; Disable World Extension special environments
[linemode]
[csysbutton]

[layopt layer=message0 visible]
This is a sample of KAGEX layer extension functions.[r]You can control rotation and scaling of layers.
[l][r]

[image layer=base page=fore storage="bg01_01"  visible=true left=0 top=0]
[image layer=0     page=fore storage="ch_0_0_1" visible=true left=960 top=810 dafx=center dafy=center]
[cm]

Start
[l][r]

*label1|Translucency

[layopt layer=0 opacity=200]
Translucent
[l][r]

*label2|Rotation

[layopt layer=0 reset]
[layopt layer=0 rotate=30]
Rotate
[l][r]

[layopt layer=0 afx=left afy=top]
Change rotation origin (top-left corner)
[l][r]

[layopt layer=0 afx=180 afy=180]
Change rotation origin (coordinate specification)
[l][r]

[layopt layer=0 afx=center afy=center]
Change rotation origin (back to center)
[l][r]

*label3|Enlarge

[layopt layer=0 reset]
[layopt layer=0 zoom=150]
Enlarge
[l][r]

*label4|X Enlarge

[layopt layer=0 reset]
[layopt layer=0 zoomx=200]
X Enlarge
[l][r]

*label5|Blending Mode

[layopt layer=0 reset]
[layopt layer=0 type=ltPsDifference5]
Blending Mode
[l][r]

*label6|Shaking

[layopt layer=0 reset]
[action layer=0 module=LayerVibrateActionModule vibration=20 waitTime=50]
Shaking
[l][r]

*label7|Vertical Shake

[layopt layer=0 reset]
[action layer=0 module=LayerJumpActionModule vibration=20 cycle=1000]
Vertical Shake
[l][r]

*label8|Horizontal Shake

[layopt layer=0 reset]
[action layer=0 module=LayerWaveActionModule vibration=20 cycle=1000]
Horizontal Shake
[l][r]

*label9|To Specified Angle

[layopt layer=0 reset]
[action layer=0 module=LayerToRotateModule angle=30 time=1000]
To a specified angle. 
[wact]
[action layer=0 module=LayerToRotateModule angle=-50 time=1000]
Let's try moving it. 
[wact]
[action layer=0 module=LayerToRotateModule angle=-0 time=1000]
This is a test.
[wact]
[l][r]

*label10|Spinning Around

[layopt layer=0 reset]
[action layer=0 module=LayerNormalRotateModule angvel=100]
Spinning around
[l][r]

*label11|Scaling Ratio

[layopt layer=0 reset]
[action layer=0 module=LayerNormalZoomModule zoom=150 time=1000]
Zoom character (timed)
[l][r]

*label12|Zoom Rotation

[layopt layer=0 reset]
[action layer=0 module=LayerVRotateZoomModule angvel=100]
Something like a rotation using zoom
[l][r]

*label13|Opacity

[layopt layer=0 reset]
[action layer=0 module=LayerFadeToModeModule opacity=128 time=1000]
To specified opacity (timed)
[l][r]

*label14|Fade Flashing

[layopt layer=0 reset]
[action layer=0 module=LayerFadeModeModule intime=1000 outtime=1000]
Fade flashing
[l][r]

*label15|Video Layer Test

[layopt layer=0 reset]
[image layer=1 movie=test.webm alpha=2 loop visible=true dafx=center dafy=center left=960 top=540]
Loading video
[l][r]

[layopt layer=1 zoom=50 time=1000]
Change zoom
[l][r]

[layopt layer=1 rotate=120 time=1000]
Rotate
[l][r]

*label16|Vector Image

[cm]
[freeimage layer=1]
[layopt layer=0 visible=false]
[image layer=1 page=fore storage="emblem_bitmap" visible=true left=540 top=370 dafx=center dafy=center]
[image layer=2 page=fore storage="emblem" visible=true left=1380 top=370 dafx=center dafy=center]
The same picture twice: a PNG on the left, an SVG vector image on the right.
[l][r]

[layopt layer=1 zoom=210 time=1000]
[layopt layer=2 zoom=210 time=1000]
Zoom in: the PNG blurs, while the SVG is drawn again at each size and stays sharp.
[l][r]

[action layer=1 module=LayerNormalRotateModule angvel=60]
[action layer=2 module=LayerNormalRotateModule angvel=60]
Both turn like any other layer.
[l][r]

*label17|CLIP STUDIO PAINT Layers

[cm]
[freeimage layer=1]
[freeimage layer=2]
[image layer=1 page=fore storage="clip://emblem.clip/root/badge.bmp" visible=true left=960 top=370 dafx=156 dafy=156]
[image layer=2 page=fore storage="clip://emblem.clip/root/star.bmp" visible=true left=960 top=374 dafx=156 dafy=160]
Two layers of one CLIP STUDIO PAINT file, each loaded with clip://.
[l][r]

[layopt layer=1 zoom=200 time=800]
[layopt layer=2 zoom=200 time=800]
[action layer=1 module=LayerNormalRotateModule angvel=-30]
[action layer=2 module=LayerNormalRotateModule angvel=120]
So each part can move on its own.
[l][r]

[freeimage layer=1]
[freeimage layer=2]

*label18|Live2D Model

; A Live2D model on a KAG layer: the l2d flip type (GFX_Live2D.tjs; "Optional parameters for
; l2d" in doc/kagex.txt). Hiyori's model comes from tools/assets/make_hiyori.py, and the
; krkrlive2d plugin is built with Live2D's Cubism SDK ("Live2D Characters" in doc/world.txt)
[cm]
[if exp="KAGLive2DCanDraw('hiyori')"]
[image layer=1 page=fore flip=hiyori.l2d l2dwidth=500 l2dheight=680 visible=true left=960 top=350 dafx=center dafy=center]
A layer can play a Live2D model too: flip=hiyori.l2d moves it as it was made, motions, blinking, hair and all. This content uses sample data owned and copyrighted by Live2D Inc.
[l][r]

[layopt layer=1 l2donce=TapBody]
l2donce plays one of the model's motions once, and then its idle motions go on.
[l][r]

[layopt layer=1 zoom=70 rotate=-12 time=800]
And it is a layer like any other: it moves, zooms and turns.
[l][r]

[freeimage layer=1]
[else]
This build doesn't play Live2D models. That takes the krkrlive2d plugin, built with Live2D's Cubism SDK, and a model: "Live2D Characters" in doc/world.txt says how to add them.
[l][r]
[endif]

*label19|3D Models and Scenes

; 3D on KAG layers: the 3d flip type (GFX_Three.tjs; "Optional parameters for 3d" in
; doc/kagex.txt), drawn by the krkrthreepp plugin. The stage is a scene built in script
; (data/main/Scenes3D.tjs); the star and Vee are the sample's own models (tools/assets/make_vrm.py)
[cm]
[if exp="KAGThreeCanDraw()"]
[image layer=1 page=fore flip=stage3d visible=true left=960 top=400 dafx=center dafy=center]
A layer can show a 3D scene. This one is built in script, with shapes, materials and lights, and its camera goes round them.
[l][r]

[layopt layer=1 3donce=jump]
3donce plays something once: the scene's script makes the knot jump.
[l][r]

[freeimage layer=1]
[image layer=1 page=fore flip=star3d.glb 3dwidth=600 3dheight=600 3dframe="-0.7,0.7" visible=true left=960 top=440 dafx=center dafy=center]
A glTF model plays its own animations: spin goes on, and 3donce=hop makes it jump.
[layopt layer=1 3donce=hop]
[l][r]

[freeimage layer=1]
[image layer=2 page=fore flip=vee.vrm 3dmotion=vee_idle 3dframe="-0.03,1.47" 3dwidth=520 3dheight=860 visible=true left=960 top=470 dafx=center dafy=center]
And a VRM avatar stands, blinks and plays VRM animations: 3dmotion goes on, 3donce=vee_wave waves once.
[layopt layer=2 3donce=vee_wave 3dexpression=happy]
[l][r]

[layopt layer=2 3dexpression="" 3dturn=90]
3dturn turns a model, and the picture is a layer like any other: it moves, zooms and turns.
[layopt layer=2 zoom=80 rotate=8 time=800]
[l][r]

[freeimage layer=2]
[else]
This build doesn't draw 3D. That takes the krkrthreepp plugin and OpenGL ES: "Optional parameters for 3d" in doc/kagex.txt says more.
[l][r]
[endif]
[layopt layer=0 visible=true]

[demodone name=layer]

[jump storage=s0001.ks]