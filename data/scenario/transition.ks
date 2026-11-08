*start|Start

[initscene]

Example of transition description in the World function

; Specify transitions individually
; When the tag is closed, the following processes are performed:
; 1. Copy the entire screen to the back buffer
; 2. Update only the target layer in the back buffer
; 3. Transition
[road trans=normal]Individual Update
[ai uniform center trans=normal]Individual Update

[ai hop]
Boing Boing action

; Specify transition for the whole screen
; Declare the start of transition.
; - The current screen becomes the back buffer
; - The drawing target becomes the back buffer
[begintrans]
; Individual state changes. All are applied to the back buffer
[evening]
[ai shiver]
; Execute transition process
; From here on, the drawing target returns to the front
[endtrans trans=normal]
Update all at once

[night trans=wave time=1000]wave
[evening trans=mosaic time=1000]mosaic
[day trans=turn time=1000]turn
[night trans=rotatezoom time=1000]rotatezoom
[evening trans=rotatevanish time=1000]rotatevanish
[day trans=rotateswap time=1000]rotateswap
[night trans=ripple time=1000]ripple

*nagano|extNagano
; extNagano's transitions, in daylight without the character: the event picture comes and goes,
; so each one changes the whole screen. Every one is the plugin's own; without the plugin
; (KAGPluginTransitions says which loaded), each one runs as a crossfade. The plugin has five
; more, book, zoomfade, rgbfade, spin and multiripple, which krkrz_dev's rebuild of it draws
; wrong (UPSTREAM.md 42), so they're left out here.
; 3duniversal's pieces fly only with a speed: accel1 (or speed1) for the old picture's pieces,
; accel2 (speed2) for the new one's (with none at all, the plugin fades the new picture out).
[ai hide trans=normal][day trans=normal]
The extNagano plugin adds more transitions. Here are seven of them.
[if exp="KAGPluginTransitions.flutter != 'linked'"]
This build doesn't have it, so they all run as crossfades here.
[endif]
[EV file=event1 trans=blurfade time=1500 blur1=48 blur2=48]blurfade: a crossfade through a blur
[EV hide trans=flutter time=1500]flutter: the picture peels away like paper
[EV file=event1 trans=scanline time=1200]scanline: lines slide in from alternate sides
[EV hide trans=3duniversal time=2000 rule=rule_shatter accel1=0.4]3duniversal: a rule picture sends pieces flying, here shards
[EV file=event1 trans=imagewipe time=1500 rule=wipe_brush]imagewipe: a wipe led by a picture, here a brush stroke
[EV hide trans=swirl]morphing: triangles warp the picture, here into a swirl (envinit.tjs)
[EV file=event1 trans=honeyturn time=1500 size=80]honeyturn: hexagons flip over one by one
[EV hide trans=normal]

[demodone name=transition]

[jump storage=s0001.ks]