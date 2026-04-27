*start|Start

; Disable World Extension special environments
[linemode]
[csysbutton]

[layopt layer=message0 visible]
This is a sample of KAGEX layer extension functions. You can control rotation and scaling of layers.
[l][r]

[image layer=base page=fore storage="bg01_01"  visible=true left=0 top=0]
[image layer=0     page=fore storage="ch_0_0_1" visible=true left=400 top=450 dafx=center dafy=center]
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

[layopt layer=0 afx=100 afy=100]
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
To specified angle
[wact]
[action layer=0 module=LayerToRotateModule angle=-50 time=1000]
Let's try moving
[wact]
[action layer=0 module=LayerToRotateModule angle=-0 time=1000]
This is a test
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
[image layer=1 movie=test.webm alpha=2 loop visible=true dafx=center dafy=center left=400 top=300]
Loading video
[l][r]

[layopt layer=1 zoom=50 time=1000]
Change zoom
[l][r]

[layopt layer=1 rotate=120 time=1000]
Rotate
[l][r]

[jump storage=s0001.ks]