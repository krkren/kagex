; The credits: a roll timed to the music (the roll flip, GFX_Roll.tjs): the staff list in
; credits.txt (data/lang/<code>/credits.txt in another language) scrolls up over the rest of
; bgm01. A click skips it once it has been seen to its end (KAGRollSeen)
*start|Credits
[initscene]
[bgm01]
[image layer=base page=fore storage=black]
[image layer=0 page=fore flip=credits fliptype=roll rolltime=bgm rollx=1240 visible=true]
[waittrig name=rollend canskip="&KAGRollSeen('credits')"]
[freeimage layer=0 page=fore]
[jump storage=s0001.ks]
