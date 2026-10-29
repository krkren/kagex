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
; tools/assets/make_hiyori.py; her voice line is eSpeak NG's (make_hiyori.py speech). A
; build without the plugin or the model says so instead. See "Live2D Characters" in
; doc/world.txt.
[if exp="!KAGLive2DCanDraw('hiyori')"]
This build doesn't play Live2D models. That takes the krkrlive2d plugin, built with Live2D's Cubism SDK, and a model: "Live2D Characters" in doc/world.txt says how to add them.
[demodone name=anim]
[jump storage=s0001.ks]
[endif]
[hiyori standard center]
This is Hiyori, a Live2D model: Live2D Inc.'s sample character, made in Cubism Editor and drawn by the krkrlive2d plugin. This content uses sample data owned and copyrighted by Live2D Inc.
[hiyori smile]
[hiyori voice=1]
【hiyori】Hello! I'm Hiyori. I blink by myself, and my mouth moves with my voice, just like Pip!
Her mouth follows the lip track kagex-lipsync made from her voice and its words: every vowel gets its own shape.
[hiyori normal]
A face's own mouth value is where the mouth rests, so she shuts it when she is done speaking.
[hiyori thinking]
Her face is the set of the model's parameters envinit.tjs gives her, and one face fades into the next.
[hiyori xsad]
An x in front of a face, as in xsad here, blinks while the face changes.
[hiyori wink]
A face can shut one of her eyes and leave the other open: that is what wink does.
[hiyori surprised]
surprised leaves her mouth open, since that is what the face asks for.
[hiyori normal eyeflip=2 lipflip=3]
The eye and mouth commands work for her as they do for Pip: eyeflip=2 blinks twice, and lipflip=3 moves her mouth three times.
[hiyori tap motionwait]
tap plays her model's TapBody motion once, and motionwait waits for it to end; then her pose's motions go on again.
[hiyori idle5 motionwait]
A motion's name comes from envinit.tjs, which says its group and number: idle5 is the fifth of her Idle group's nine.
[hiyori m03 motionwait]
And m03 names the file it comes from, motions/Hiyori_m03.motion3.json, whatever group holds it.
[hiyori still]
A pose is the motions that go on: standard takes her Idle group's, one after another, and still plays one motion only.
[hiyori standard]
Her motions move her head, body and arms, and her hair and skirt move by the model's own physics.
[hiyori normal hide]
[demodone name=anim]
[jump storage=s0001.ks]
