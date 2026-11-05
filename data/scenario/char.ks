*start|Start

; Environment initialization process
[initscene]

; BGM Playback
[bgm01]
[road normal]

This is a scripting sample using KAGEX World Extension.
You can perform advanced staging with relatively simple descriptions.
It's easier to understand if you open char.ks and compare it with the actual file.

[ai standard center]
Character appearance

【ai】Name display, text display, and key input wait are automatically performed in the prescribed format.
【ai/???】To change the display name, just write the display name after the slash.
【ai/Ai, Who Has an Unusually Long Name Today】A name too long for its box is squeezed to fit ([[position namefit=squeeze]).
【ai】If a voice number is specified, the voice will be played along with the text.
【ai】Processing wait during auto-play is also automatically adjusted. The voice will play in the next text.

[ai voice=1]
【ai】Ninth-grade antiseptic hell!

[ai voice=clear]
【ai】By the way, you can change the voice playback speed in the debug menu.

; Recollection end point
[endrecollection]

[ai posleft]
Character movement (Left)

[ai backlevel]
Character level change (Back)

[ai center]
Character movement (Center)

[ai frontlevel]
Character level change (Front)

[ai centerlevel]
Character level change (Middle)

[ai hide]
Character removal

[ai posleft fade]
Character appearance/fade control

[ai hide fade]
Character removal/fade control

[ai center]
Character appearance

[ai rotate=30 time=1000][ai zoom=120 time=1000]
Layer rotation/zoom control (when actions are not synchronized)

[ai rotate=0 time=1000 sync][ai zoom=100 time=1000 sync]
Layer rotation/zoom control (when actions are synchronized)

[evening normal]
Evening (Characters are automatically color-corrected)

[night normal]
Night (Characters are automatically color-corrected)

[ai zoom=150 time=1000]
Layer zoom control 

[ai opacity=100 time=1000]
Opacity control

[ai reset]
Reset layer state

; Show event image
[EV file=event1 fade]
The event image has been displayed.

[EV rotate=30 time=1000]
Rotate event image

[EV rotate=@+30 time=1000]
Rotate event image (Relative specification) *The relative specification format has changed. Sorry.

[EV zoom=200 time=1000]
Zoom event image

[EV zoom=@-50 time=1000]
Zoom event image (Relative specification)

[EV hide fade]
Remove event image

[day normal]

[ai happy]
Expression change (Happy)

[ai angry]
Expression change (Angry)

[ai 103]
A writer's shorthand: [[ai 103] is pose 1 and face 03, sad (envinit.tjs's "shorthands")

[ai far]
A preset: [[ai far] sends Ai further back, behind the others

[ai near]
And [[ai near] brings her near, in front

[ai centerlevel happy]

[ai posright time=500]
Movement with time specification (→Right) 

[ai posright:center time=500]
Movement with initial position specified (Center→Right)

[ai posright:center opacity=255:0 time=500]
Movement with initial position specified (Center→Right with opacity control)

; The music fades out here, so the positional sounds below can be heard on their own
[bgm stop=1500]
[ai opacity=255:0 zoom=100:140 time=500]
Combined with zoom

; Positional sound: a sound placed on the stage is panned to where it is (doc/world.txt)
[se storage=se_chime pos=farleft]
A chime at the far left of the stage (positional sound)

[se storage=se_chime pos=farright]
And at the far right

[se storage=se_steps loop=1 char=ai]
[ai posleft time=1500]
Footsteps that go with Ai as she walks
[se name=se_steps stop=300]

*voices|Voices

; Voices from where the speakers stand: with envinit.tjs's "voice3d", Ai on the left is heard
; from the left and Pip on the right from the right (Config's second page centres them). A
; voice cut by the next one fades out, and vol= makes one line quieter (doc/world.txt)
[ai standard posleft opacity=255 zoom=100]
[pip standard posright]
Voices come from where the speakers stand

[ai voice=1]
【ai】Ninth-grade antiseptic hell!
; [vo]: a voice file from the recording script, whose speaker the game works out (Pip's: pip%s%06d)
[pip xsurprised]
[vo pip000003]
Whoa! What was that?
Click while someone is talking: the voice fades out instead of stopping (Config, second page)

[pip neutral voice=4 vol=35]
【pip】(whispering) Is she always like this?
A quieter line, a whisper: [[pip voice=4 vol=35]
[pip hide]
【ai】Oh, and you must be [emb exp="kag.heroName()"]. Nice to meet you!
【hero】Nice to meet you too.

*faces|Faces

; Faces by the message window (since 0.18.0): the speaker's face, cut from their sprite as it
; looks now (envinit.tjs's faceCrop), crossfades to the next speaker's and goes for narration and
; CGs; a speaker who isn't on stage shows a face only ([pip facewin]), [env facewindow=off]
; turns them off for a scene, and Config turns them off for good
[ai standard center]
【ai】The speaker's face shows by the window, just as their sprite looks now.
[ai angry]
【ai】Even when I'm cross!
[pip facewin]
【pip】And I'm not even on stage. I'm calling from somewhere else!
Narration has no face.
[EV file=event1 fade]
【ai】Over a CG, the face steps aside.
[EV hide fade]
[env facewindow=off]
[ai happy]
【ai】A scene can do without faces...
[env facewindow=on]
[pip hide]
【ai】...and have them back.

*layouts|Making Room

; Layouts (since 0.18.0, envinit.tjs's "layouts"): [name join] brings a character on at the
; right (join=left, join=middle) while the others slide over to stand evenly spaced, [name leave]
; takes one off and the others close the gap, and [env makeroom=0] pushes them apart
[ai center time=300]
Ai stands alone.
[pip standard neutral join]
【pip】Room for one more?
[newchar name=ai2 initname=ai]
[ai2 join=middle]
Another Ai cuts in, in the middle, and the others make room.
[ai leave]
The first Ai leaves, and the gap closes.
[env makeroom=0]
They step apart for something in the middle...
[ai2 delete]
[pip leave]
...and everyone goes.

*flashback|A Flashback

; Keeping a scene (since 0.18.0): [env keep] puts the whole World away (stage, characters, layers,
; camera, colour), a flashback plays in grey, and [env restore] brings it all back as it was while
; the music plays on ([env keep sound=true] keeps the sounds too; keep=<name> for named copies)
[bgm01]
[ai standard happy center]
[pip standard neutral posright]
Ai and Pip on the street, as they are now.
[env keep]
[pip hide]
[ai posleft sad]
[env grayscale=true trans=normal]
A memory, in grey: Ai, long ago, on her own.
[env restore trans=normal]
And back to now, just as it was, with the music still playing.
[bgm stop=1500]
[pip hide]
[ai hide]

*label6|Character Action

[newchar name=ai2 initname=ai center opacity=255:0 zoom=100:140 time=300 sync]
[newchar name=ai3 initname=ai posleft opacity=255:0 zoom=100:140 time=300 sync]
Cloning technique

[ai bow]
[ai2 hop]
[ai3 shiver]
Applying Bow/Boing/Shake actions to each respectively

[ai midright time=500]
[ai3 midleft time=500]
Move so they overlap

[ai2 front]
Bring Ai2 to the front

[ai2 back]
Move Ai2 to the back

[ai  xpos=-1920 time=500]
[ai2 xpos=-1920 time=500]
[ai3 xpos=-1920 time=500]
The End

[demodone name=char]

[jump storage=s0001.ks]