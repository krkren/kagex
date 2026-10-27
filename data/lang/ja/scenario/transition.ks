*start|スタート

[initscene]

World 機能におけるトランジション記述の例

; Specify transitions individually
; When the tag is closed, the following processes are performed:
; 1. Copy the entire screen to the back buffer
; 2. Update only the target layer in the back buffer
; 3. Transition
[road trans=normal]個別更新
[ai uniform center trans=normal]個別更新

[ai hop]
びょんびょんアクション

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
一気に更新

[night trans=wave time=1000]wave
[evening trans=mosaic time=1000]mosaic
[day trans=turn time=1000]turn
[night trans=rotatezoom time=1000]rotatezoom
[evening trans=rotatevanish time=1000]rotatevanish
[day trans=rotateswap time=1000]rotateswap
[night trans=ripple time=1000]ripple

*nagano|extNagano
; extNagano's twelve transitions, in daylight without the character: the event picture comes
; and goes, so each one changes the whole screen. Without the plugin (KAGPluginTransitions
; says which loaded), each one runs as a crossfade.
[ai hide trans=normal][day trans=normal]
extNagano プラグインでトランジションがさらに12種類増えます。
[if exp="KAGPluginTransitions.book != 'linked'"]
このビルドにはないので、ここではどれもクロスフェードになります。
[endif]
[EV file=event1 trans=book time=1500 dir=1]book：ページがめくれる
[EV hide trans=flutter time=1500]flutter：絵が紙のようにはがれていく
[EV file=event1 trans=blurfade time=1500 blur1=48 blur2=48]blurfade：ぼかしを通したクロスフェード
[EV hide trans=zoomfade time=1500]zoomfade：消えながら拡大する
[EV file=event1 trans=scanline time=1200]scanline：線が左右交互にすべり込む
; rgbfade blends alpha as well as colour and takes a pixel of alpha 0 as transparent, so on a
; screen of composited layers (alpha is meaningless there) it shows solid colours. Run it on one
; layer between two whole pictures: layer 0 takes over from the event picture, and the road
; under it looks the same as layer 0's daytime road
[image layer=0 page=fore storage=event1 visible=true][image layer=0 page=back storage=bg01_01 visible=true][EV hide trans=notrans]
[trans layer=0 method=rgbfade time=1800 delayr=0 delayg=96 delayb=192 children=false][wt]
[freeimage layer=0 page=fore][freeimage layer=0 page=back]rgbfade：赤・緑・青が順番に切り替わる
[EV file=event1 trans=spin time=1500]spin：箱の側面のように絵が回る
[EV hide trans=multiripple time=2000 count=5 wavecount=3 rwidth=64 maxdrift=48]multiripple：五か所から波紋が広がる
[EV file=event1 trans=imagewipe time=1500 rule=wipe_brush]imagewipe：画像に沿ったワイプ（ここでは筆のストローク）
[EV hide trans=3duniversal time=2000 rule=rule_shatter]3duniversal：ルール画像で破片が飛び散る（ここではガラス片）
[EV file=event1 trans=honeyturn time=1500 size=80]honeyturn：六角形がひとつずつ裏返る
[EV hide trans=swirl]morphing：三角形で絵をゆがめる（ここでは渦巻き、envinit.tjs）

[demodone name=transition]

[jump storage=s0001.ks]