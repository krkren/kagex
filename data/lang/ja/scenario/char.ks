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