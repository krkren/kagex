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

[ai posright time=500]
Movement with time specification (→Right) 

[ai posright:center time=500]
Movement with initial position specified (Center→Right)

[ai posright:center opacity=255:0 time=500]
Movement with initial position specified (Center→Right with opacity control)

[ai opacity=255:0 zoom=100:140 time=500]
Combined with zoom

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