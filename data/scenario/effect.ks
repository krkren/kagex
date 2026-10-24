*start|Start
; Effekseer effects (template/system/GFX_Effekseer.tjs, drawn by the krkreffekseer plugin). A World
; layer plays one with efk=<file>: the files are in data/effect, their textures and materials in
; folders beside them. See efk in doc/world.txt.
[initscene]
[bgm01]
[road normal]
[night normal]
[if exp="!KAGEffekseerOf(kag).available"]
Effekseer effects need the krkreffekseer plugin and OpenGL ES, which this build doesn't have, so the demo ends here.
[jump target=*done]
[endif]
[newlay name=fw1 efk=Simple_Turbulence_Fireworks efkmag=30 efkx=-480 efky=380 loop show]
This demo plays effects made with Effekseer, drawn by the krkreffekseer plugin.
[newlay name=fw2 efk=Simple_Turbulence_Fireworks efkmag=26 efkx=500 efky=420 loop show]
Each one is a World layer: efk= names the effect, efkmag sizes it and efkx/efky place it.
[ai standard center]
【ai】Oh, fireworks!
[newlay name=flash efk=Laser02 efkmag=40 efky=-200 show]
【ai】Whoa, lightning!
[newlay name=ring efk=Simple_Ring_Shape1 efkmag=110 efkrotx=-65 efky=60 loop show]
【ai】And a ring of light around me...
[newlay name=homing efk=Homing_Laser01 efkmag=60 efky=320 loop show]
The ring is tilted with efkrotx, and loop replays an effect when it ends.
[newlay name=beam efk=Laser03 efkmag=75 efkx=-980 efky=-230 show]
【ai】Look, a beam!
[newlay name=bokeh1 efk=Simple_Sprite_BillBoard efkmag=110 efkx=-360 efky=-280 show]
[newlay name=bokeh2 efk=Simple_Sprite_BillBoard efkmag=110 efkx=380 efky=-240 show]
[newlay name=sparkle efk=Simple_Turbulence_Particles efkmag=90 efkx=-80 efky=-330 show]
【ai】It's like a festival!
[ring flipupdate efkstop]
[homing flipupdate efkstop]
[sparkle flipupdate efkstop]
With efkstop an effect stops making particles, and its layer clears once the last one fades.
[fw1 flipupdate efkstop]
[fw2 flipupdate efkstop]
【ai】Thanks for watching!
[ai hide fade]
[dellay name=fw1]
[dellay name=fw2]
[dellay name=flash]
[dellay name=ring]
[dellay name=homing]
[dellay name=beam]
[dellay name=bokeh1]
[dellay name=bokeh2]
[dellay name=sparkle]
*done
[demodone name=effect]
[jump storage=s0001.ks]
