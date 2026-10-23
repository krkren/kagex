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

[demodone name=transition]

[jump storage=s0001.ks]