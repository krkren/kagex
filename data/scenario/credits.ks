; The credits: a roll timed to the music (the roll flip, GFX_Roll.tjs): the staff list in
; credits.txt (data/lang/<code>/credits.txt in another language) scrolls up over bgm01, from
; its label credits, after the opening bars, to creditsend, where the closing chords begin
; (bgm01.ogg.sli); without the labels, over the rest of the track. A click skips it once it
; has been seen to its end (KAGRollSeen). The closing chords fade out after it
*start|Credits
[initscene]
[bgm01]
[image layer=base page=fore storage=black]
[image layer=0 page=fore flip=credits fliptype=roll rolltime=bgm rollfrom=credits rollto=creditsend rollx=1240 visible=true]
[waittrig name=rollend canskip="&KAGRollSeen('credits')"]
[fadeoutbgm time=3000]
[wb canskip=true]
[freeimage layer=0 page=fore]
[jump storage=s0001.ks]
