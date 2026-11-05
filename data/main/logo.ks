*logo|
; not a place to save or carry on from (the continue save, MainWindow.tjs)
[disablestore]

[cancelskip]
[rclick enabled=false]
[clickskip enabled=true]
[position layer=message0 frame="" opacity=0 left=0 top=0 width=1920 height=1080 marginT=0 marginL=0 marginR=0 marginB=0 visible=true]

[beginskip]
[begintrans]
[newlay name=logo file=logo level=6 xpos=0 ypos=0]
[endtrans trans=normal time=1000]
[wait time=3000]
[begintrans]
[allimage delete]
[endtrans trans=normal time=1000]
[endskip]
; the opening ([movie], Movies.tjs; tools/assets/make_opening.py draws it, over the start of
; bgm01, which it unlocks in the music room): a click skips it once it has been seen, its subtitles
; are opening.vtt (the Japanese in data/lang/ja), and the web and phones play opening_sd, zoomed to
; fill the screen
[movie storage=opening song=bgm01 color=0x000000]

@return