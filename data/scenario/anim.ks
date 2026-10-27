*start|Start
; An animated character. Pip is a World character drawn from layers (KAGEnvCharacterEx.tjs,
; "exstand"): data/main/charinit.csv names its files, data/fgimage/pip holds its layers (made by
; tools/assets/make_pip.py), and its envinit.tjs entry has no poses. See "Characters drawn from
; layers" in doc/world.txt.
[initscene]
[bgm01]
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
[demodone name=anim]
[jump storage=s0001.ks]
