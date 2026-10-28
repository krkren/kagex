*start|Start
; An animated character. Pip is a World character drawn from layers (KAGEnvCharacterEx.tjs,
; "exstand"): data/main/charinit.csv names its files, data/fgimage/pip holds its layers (made by
; tools/assets/make_pip.py), and its envinit.tjs entry has no poses. See "Characters drawn from
; layers" in doc/world.txt.
[initscene]
[road normal]
[pip standard center]
Pip is drawn from layers, put together as it's shown: a body, two outfits, three arm poses and six faces.
[pip wave voice=1]
【pip】Hi! I'm Pip.
[pip rest voice=2]
【pip】I blink by myself, and my mouth moves with my voice.
Its eyes blink every few seconds, and while it speaks, its mouth opens as wide as its voice is loud.
[pip neutral voice=9]
【pip】Hi again! Listen closely. When I speak with a real voice, my mouth makes the shape of every vowel I say. Ah, ee, ooh, eh, oh. Isn't that so much better than mumbling?
For that line, kagex-lipsync worked out from the voice and its text when each vowel is said, and wrote pip000009.lip beside the voice. Every other voice moves the mouth by its loudness alone.
[pip xsurprised voice=3]
【pip】Oh! A new face!
An x in front of a face, as in xsurprised, closes the eyes while the face changes.
[pip sad voice=4]
【pip】Oops, did I startle you?
[pip beret smile voice=5]
【pip】How do I look?
[pip laugh cheer voice=6]
【pip】Ha ha! I like it!
The laughing face has its eyes drawn shut, so they don't blink, while the mouth still moves.
[pip plain angry rest voice=7]
【pip】Hey! I liked that hat!
Outfits change like faces: beret puts the hat on, and plain takes it off.
[pip neutral frontlevel]
Each World level has its own set of layers, drawn at that size, so Pip stays sharp up close.
[pip centerlevel]
[pip eyecloseto]
The eyes and the mouth also take orders: eyecloseto closes the eyes and waits until they're shut.
[pip eyeopento]
Then eyeopento opens them again.
[pip eyeflip=3]
eyeflip=3 blinks three times.
[pip lipflip=4]
And lipflip=4 moves the mouth four times, without a voice.
[pip smile waving voice=8]
【pip】Bye for now!
That wave is an animation: waving, in data/main/charanim.csv, steps through the arm poses on a timer until something else changes.
[pip hide]
*live2d|Live2D
; A Live2D character: Hiyori, Live2D Inc.'s sample model, drawn by the krkrlive2d plugin
; (KAGEnvCharacterLive2D.tjs). Her model, data/fgimage/hiyori.l2d, comes from
; tools/assets/make_hiyori.py, and her voice too, with its key for Azure's speech service. A
; build without the plugin or the model says so instead. See "Live2D Characters" in
; doc/world.txt.
[if exp="!KAGLive2DCanDraw('hiyori')"]
This build doesn't play Live2D models. That takes the krkrlive2d plugin, built with Live2D's Cubism SDK, and a model: "Live2D Characters" in doc/world.txt says how to add them.
[demodone name=anim]
[jump storage=s0001.ks]
[endif]
[hiyori standard posright]
This is Hiyori, a Live2D model: Live2D Inc.'s sample character, made in Live2D's Cubism Editor, which the krkrlive2d plugin moves and draws thirty times a second. This content uses sample data owned and copyrighted by Live2D Inc.
[hiyori smile]
[if exp="sampleVoiceExists('hiyori000001')"]
[hiyori voice=1]
[endif]
【hiyori】Hello! I'm Hiyori. I blink by myself, and my mouth moves with my voice, just like Pip!
Her pose, standard, plays the motions of the model's Idle group one after another, which move her head and body. Her face is the one the script gives her: values for the model's parameters, set in envinit.tjs, which fade into each other.
[hiyori tap motionwait]
tap plays the model's TapBody motion once, and motionwait waits for it to end. Then her Idle motions go on.
[hiyori xsad]
An x in front of a face makes her blink as it changes.
[hiyori surprised eyeflip=2]
The eye and mouth commands work for her as they do for Pip: eyeflip=2 blinks twice.
[hiyori normal hide]
[demodone name=anim]
[jump storage=s0001.ks]
