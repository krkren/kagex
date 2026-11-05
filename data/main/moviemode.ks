; A movie from Replay's Movies tab (Override.tjs, replayTile): played as [movie] plays it,
; skippable, then back to Replay
*start
[rclick enabled=false]
[backlay]
[position layer=message0 page=back visible=false]
[trans method=crossfade time=300]
[wt]
[movie storage="&tf.movieName" alpha="&tf.movieAlpha" skip=always color=0x000000]
[jump storage=replay.ks]
