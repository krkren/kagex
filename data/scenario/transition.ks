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

[env night trans=wave time=1000]wave
[env evening trans=mosaic time=1000]mosaic
[env day trans=turn time=1000]turn
[env night trans=rotatezoom time=1000]rotatezoom
[env evening trans=rotatevanish time=1000]rotatevanish
[env day trans=rotateswap time=1000]rotateswap
[env night trans=ripple time=1000]ripple

*nagano|extNagano
; extNagano's twelve transitions, in daylight without the character: the event picture comes
; and goes, so each one changes the whole screen. Without the plugin (KAGPluginTransitions
; says which loaded), each one runs as a crossfade.
[ai hide trans=normal][env day trans=normal]
The extNagano plugin adds twelve more transitions.
[if exp="KAGPluginTransitions.book != 'linked'"]
This build doesn't have it, so they all run as crossfades here.
[endif]
[EV file=event1 trans=book time=1500 dir=1]book: a page turns
[EV hide trans=flutter time=1500]flutter: the picture peels away like paper
[EV file=event1 trans=blurfade time=1500 blur1=48 blur2=48]blurfade: a crossfade through a blur
[EV hide trans=zoomfade time=1500]zoomfade: the picture zooms in as it fades
[EV file=event1 trans=scanline time=1200]scanline: lines slide in from alternate sides
; rgbfade blends alpha as well as colour and takes a pixel of alpha 0 as transparent, so on a
; screen of composited layers (alpha is meaningless there) it shows solid colours. Run it on one
; layer between two whole pictures: layer 0 takes over from the event picture, and the road
; under it looks the same as layer 0's daytime road
[image layer=0 page=fore storage=event1 visible=true][image layer=0 page=back storage=bg01_01 visible=true][EV hide trans=notrans]
[trans layer=0 method=rgbfade time=1800 delayr=0 delayg=96 delayb=192 children=false][wt]
[freeimage layer=0 page=fore][freeimage layer=0 page=back]rgbfade: red, green and blue change one after another
[EV file=event1 trans=spin time=1500]spin: the picture turns like the side of a box
[EV hide trans=multiripple time=2000 count=5 wavecount=3 rwidth=64 maxdrift=48]multiripple: ripples spread from five points
[EV file=event1 trans=imagewipe time=1500 rule=wipe_brush]imagewipe: a wipe led by a picture, here a brush stroke
[EV hide trans=3duniversal time=2000 rule=rule_shatter]3duniversal: a rule picture sends pieces flying, here shards
[EV file=event1 trans=honeyturn time=1500 size=80]honeyturn: hexagons flip over one by one
[EV hide trans=swirl]morphing: triangles warp the picture, here into a swirl (envinit.tjs)

[demodone name=transition]

[jump storage=s0001.ks]