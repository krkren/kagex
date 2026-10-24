*start|Start
; Effekseer effects (template/system/GFX_Effekseer.tjs, drawn by the krkreffekseer plugin). A World
; layer plays one with efk=<name>: the sample's are in data/effect (made by
; tools/assets/make_effects.py), their textures in data/effect/Texture. See efk in doc/world.txt.
[initscene]
[bgm01]
[road normal]
[night normal]
[if exp="!KAGEffekseerOf(kag).available"]
Effekseer effects need the krkreffekseer plugin and OpenGL ES, which this build doesn't have, so the demo ends here.
[jump target=*done]
[endif]
[newlay name=petals efk=petals efkframe=600 show]
Glowing petals drift over the road: an Effekseer effect on a World layer, drawn by the krkreffekseer plugin.
[ai standard center]
【ai】Petals... that glow?
[newlay name=sparkle efk=sparkle efky=-150 show]
【ai】And sparkles, all around me!
Each effect is a layer of its own: efk= names it, efkx and efky place it, efkmag sizes it.
[petals flipupdate efkstop]
[sparkle flipupdate efkstop]
[newlay name=fw1 efk=fireworks efkx=-520 efky=300 level=0 show]
[newlay name=fw2 efk=fireworks efkx=560 efky=260 efkmag=40 level=0 show]
【ai】Fireworks!
Their rockets go up about once a second, for as long as the layer plays.
[newlay name=circle efk=magiccircle efkx=-560 efky=40 show]
【ai】Hm? Something's glowing over there...
[newlay name=burst efk=shockwave efky=-120 show]
【ai】Whoa!
A burst like that one plays once, and its layer clears when it's over.
[circle flipupdate efkstop]
[fw1 flipupdate efkstop]
[fw2 flipupdate efkstop]
With efkstop, an effect stops making particles and fades out.
【ai】Thanks for watching!
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
