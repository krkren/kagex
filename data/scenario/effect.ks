*start|Start
; Effekseer effects (template/system/GFX_Effekseer.tjs, drawn by the krkreffekseer plugin). A World
; layer plays one with efk=<name>: the sample's are in data/effect (made by
; tools/assets/make_effects.py), their textures in data/effect/Texture. See efk in doc/world.txt.
[initscene]
[bgm01]
[road normal]
[night normal]
[if exp="!KAGEffekseerOf(kag).available"]
Effekseer effects need the krkreffekseer plugin and OpenGL ES, which this build doesn't have, so the demo skips them.
[jump target=*static]
[endif]
[newlay name=petals efk=petals efkframe=600 show]
Glowing petals drift over the road: an Effekseer effect on a World layer, drawn by the krkreffekseer plugin.
[ai standard center]
【ai】Petals... that glow?
[newlay name=sparkle efk=sparkle efkwidth=900 efkheight=900 ypos=-150 show]
【ai】And sparkles, all around me!
Each effect is a layer of its own: efk= names it, efkmag sizes it, and efkwidth and efkheight set the size of its canvas, which is placed like any layer.
[petals flipupdate efkstop]
[sparkle flipupdate efkstop]
[newlay name=fw1 efk=fireworks efkx=-520 efky=300 level=0 show]
[newlay name=fw2 efk=fireworks efkx=560 efky=260 efkmag=40 level=0 show]
【ai】Fireworks!
Their rockets go up about once a second, for as long as the layer plays.
[newlay name=circle efk=magiccircle efkwidth=760 efkheight=560 xpos=-560 ypos=40 show]
【ai】Hm? Something's glowing over there...
[newlay name=burst efk=shockwave efky=-120 show]
【ai】Whoa!
A burst like that one plays once, and its layer clears when it's over.
[circle flipupdate efkstop]
[fw1 flipupdate efkstop]
[fw2 flipupdate efkstop]
With efkstop, an effect stops making particles and fades out.
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
【ai】Now for an effect that goes wrong on purpose.
[newlay name=tv static=tv staticbar=40 staticlines=90 opacity=0 level=message show]
[tv opacity=120 time=800]
The picture breaks up into TV static: a static flip on a World layer at level=message, drawn over the scene and this window at the layer's opacity.
[bgm pitch=35 time=2500]
【ai】And the music... it's slowing down, like a tape running out!
pitch= changes a sound's speed and pitch together: here the music goes down to 35% over two and a half seconds.
[se storage=se_steps loop=1 pan=-100]
[se name=se_steps pan=100 time=3000]
【ai】Who just walked past?
pan= moves a sound between left and right: here footsteps cross from one side to the other.
[se name=se_steps stop=300]
[tv opacity=0 time=500]
[bgm pitch=100 time=800]
【ai】Phew, everything's back to normal.
[dellay name=tv]
【ai】Thanks for watching!
[ai hide fade]
*done
[demodone name=effect]
[jump storage=s0001.ks]
