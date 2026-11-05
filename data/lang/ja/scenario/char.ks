*start|スタート

; Environment initialization process
[initscene]

; BGM Playback
[bgm01]
[road normal]

KAGEX ワールド拡張を用いたスクリプティングのサンプルです。
比較的シンプルな記述で高度な演出を行うことができます。
char.ks を開いて実際のファイルを比較しながら見るとわかりやすいです。

[ai standard center]
キャラクタ出現

【ai】規定の書式で自動的に名前表示・テキスト表示・キー入力待ちが行われます
【ai/？？？】表示名を変更する場合はスラッシュにつづけて表示名を記載すればＯＫです
【ai/今日はとても長い名前を名乗っているあい】枠に入りきらない長い名前は、縮めて収めます（[[position namefit=squeeze]）。
【ai】ボイス番号が指定されているとテキストにあわせてボイスが再生されます。
【ai】自動再生時の処理待ちも自動的に調整されます。次のテキストでボイスがなります

[ai voice=1]
【ai】中三マキロン地獄

[ai voice=clear]
【ai】ちなみにデバッグメニューでボイス再生速度を変更できます

; Recollection end point
[endrecollection]

[ai posleft]
キャラクタ移動（左）

[ai backlevel]
キャラクタレベル変更（奥）

[ai center]
キャラクタ移動（中）

[ai frontlevel]
キャラクタレベル変更（手前）

[ai centerlevel]
キャラクタレベル変更（中間）

[ai hide]
キャラクタ消去

[ai posleft fade]
キャラクタ出現・フェード制御

[ai hide fade]
キャラクタ消去・フェード制御

[ai center]
キャラクタ出現

[ai rotate=30 time=1000][ai zoom=120 time=1000]
レイヤ回転・ズーム制御（動作シンクロしない場合）

[ai rotate=0 time=1000 sync][ai zoom=100 time=1000 sync]
レイヤ回転・ズーム制御（動作シンクロする場合）

[evening normal]
夕方（キャラクタは自動的に色補正されます）

[night normal]
夜（キャラクタは自動的に色補正されます）

[ai zoom=150 time=1000]
レイヤ拡大制御

[ai opacity=100 time=1000]
透明度制御

[ai reset]
レイヤ状態初期化

; Show event image
[EV file=event1 fade]
イベント絵を表示しました。

[EV rotate=30 time=1000]
イベント絵を回転

[EV rotate=@+30 time=1000]
イベント絵を回転（相対指定）※相対指定書式かわりました。スマヌ

[EV zoom=200 time=1000]
イベント絵をズーム処理

[EV zoom=@-50 time=1000]
イベント絵をズーム処理（相対指定）

[EV hide fade]
イベント絵消去

[day normal]

[ai happy]
表情変更（喜）

[ai angry]
表情変更（怒）

[ai 103]
書き手の短縮記法：[[ai 103] はポーズ 1・表情 03（悲しみ）（envinit.tjs の "shorthands"）

[ai far]
プリセット：[[ai far] で奥へ、ほかのキャラの後ろに

[ai near]
[[ai near] で手前へ、前に出します

[ai centerlevel happy]

[ai posright time=500]
時間指定あり場所移動（→右）

[ai posright:center time=500]
初期位置指定で場所移動（中→右）

[ai posright:center opacity=255:0 time=500]
初期位置指定で場所移動（中→右 透明度制御あり）

; The music fades out here, so the positional sounds below can be heard on their own
[bgm stop=1500]
[ai opacity=255:0 zoom=100:140 time=500]
ズームと複合

; Positional sound: a sound placed on the stage is panned to where it is (doc/world.txt)
[se storage=se_chime pos=farleft]
ステージの左はしで鳴るチャイム（位置のある効果音）

[se storage=se_chime pos=farright]
右はしで鳴るチャイム

[se storage=se_steps loop=1 char=ai]
[ai posleft time=1500]
歩くあいについていく足音
[se name=se_steps stop=300]

*voices|ボイス

; Voices from where the speakers stand: with envinit.tjs's "voice3d", Ai on the left is heard
; from the left and Pip on the right from the right (Config's second page centres them). A
; voice cut by the next one fades out, and vol= makes one line quieter (doc/world.txt)
[ai standard posleft opacity=255 zoom=100]
[pip standard posright]
声は話す人の立ち位置から聞こえます

[ai voice=1]
【ai】中三マキロン地獄
; [vo]: a voice file from the recording script, whose speaker the game works out (Pip's: pip%s%06d)
[pip xsurprised]
[vo pip000003]
わっ！ 今のは何？
話している途中でクリックすると、声はぷつりと止まらずにフェードアウトします（設定の 2 ページ目）

[pip neutral voice=4 vol=35]
【pip】（ひそひそ）いつもこうなの？
小さな声のセリフ、ささやき：[[pip voice=4 vol=35]
[pip hide]
【ai】あ、あなたが[emb exp="kag.heroName()"]さんね。よろしく！
【hero】こちらこそ、よろしく。

*faces|顔

; Faces by the message window (since 0.18.0): the speaker's face, cut from their sprite as it
; looks now (envinit.tjs's faceCrop), crossfades to the next speaker's and goes for narration and
; CGs; a speaker who isn't on stage shows a face only ([pip facewin]), [env facewindow=off]
; turns them off for a scene, and Config turns them off for good
[ai standard center]
【ai】話している人の顔が、立ち絵の今の姿のままウィンドウの横に出ます。
[ai angry]
【ai】怒っているときもね！
[pip facewin]
【pip】ぼくは舞台にもいないよ。よそから電話してるんだ！
地の文には顔が出ません。
[EV file=event1 fade]
【ai】CGの上では、顔は引っ込みます。
[EV hide fade]
[env facewindow=off]
[ai happy]
【ai】顔なしのシーンにもできるし……
[env facewindow=on]
[pip hide]
【ai】……また戻せるよ。

*layouts|立ち位置の調整

; Layouts (since 0.18.0, envinit.tjs's "layouts"): [name join] brings a character on at the
; right (join=left, join=middle) while the others slide over to stand evenly spaced, [name leave]
; takes one off and the others close the gap, and [env makeroom=0] pushes them apart
[ai center time=300]
あいがひとりで立っています。
[pip standard neutral join]
【pip】ぼくも入れて？
[newchar name=ai2 initname=ai]
[ai2 join=middle]
もうひとりのあいが真ん中に割り込み、みんなが場所を空けます。
[ai leave]
最初のあいが去ると、すき間が詰まります。
[env makeroom=0]
真ん中に何かを置けるよう、ふたりが離れます……
[ai2 delete]
[pip leave]
……そして、みんな退場。

*flashback|回想

; Keeping a scene (since 0.18.0): [env keep] puts the whole World away (stage, characters, layers,
; camera, colour), a flashback plays in grey, and [env restore] brings it all back as it was while
; the music plays on ([env keep sound=true] keeps the sounds too; keep=<name> for named copies)
[bgm01]
[ai standard happy center]
[pip standard neutral posright]
いつもの通りにいる、あいとピップ。
[env keep]
[pip hide]
[ai posleft sad]
[env grayscale=true trans=normal]
灰色の思い出：ずっと前の、ひとりきりのあい。
[env restore trans=normal]
そして今へ。音楽は流れたまま、何もかも元どおり。
[bgm stop=1500]
[pip hide]
[ai hide]

*label6|キャラアクション

[newchar name=ai2 initname=ai center opacity=255:0 zoom=100:140 time=300 sync]
[newchar name=ai3 initname=ai posleft opacity=255:0 zoom=100:140 time=300 sync]
分身の術

[ai bow]
[ai2 hop]
[ai3 shiver]
おじぎ／びょんびょん／ガクガク アクションをそれぞれに適用

[ai midright time=500]
[ai3 midleft time=500]
かさなるように移動

[ai2 front]
あい2を前面に出す

[ai2 back]
あい2を後面にさげる

[ai  xpos=-1920 time=500]
[ai2 xpos=-1920 time=500]
[ai3 xpos=-1920 time=500]
おしまい

[demodone name=char]

[jump storage=s0001.ks]