*start|スタート
; Text effects: what a message window can do with its text, a page each. The tags are KAG3's
; ([font], [style], [ruby], [graph], [delay], [nowait], [wait], [l], [indent], [position], [hch],
; [emb]) and KAGEX's (gradients and window styles since 0.22.0, [font anim=] and [font appear=]
; since 0.23.0). See "Text Effects" in doc/kagex.txt.
[initscene]
[road normal]
[ai standard center]
【ai】文字にできることは、言葉を伝えるだけではありません。メッセージウィンドウで文字に何ができるか、一ページにひとつずつお見せしますね。
*style|色・大きさ・書体
言葉は[font color=0xff8080]赤[resetfont]にも[font color=0x80d0ff]青[resetfont]にも[font color=0xffd75e]金[resetfont]にも、[font size=60]大きく[resetfont]も[font size=26]小さく[resetfont]も、[font bold=false]細く[resetfont]も[font italic=true]斜め[resetfont]にもできます。[[font] で変えて、[[resetfont] で元に戻します。
[font face="Noto Serif JP"]手紙や詩、古い本には別の書体を。これはサンプルの明朝体で、ゲームの fonts.csv に載っています。[resetfont]
*outline|縁取り・影・グラデーション
[font edge=true edgecolor=0x5025ff shadow=false]縁取り、[resetfont][font edge=false shadow=true shadowcolor=0x000000]影、[resetfont]あるいは[font edge=true edgecolor=0x2a1a7a shadow=true shadowcolor=0x000000]その両方。[resetfont]それぞれ好きな色にできます。
[font gradcolor=0xffd75e]文字は行の上から下へ、白から金へと色を変えられます。[resetfont][r][font color=0xff80c0 gradcolor=0x80c0ff graddir=horizontal]ウィンドウの左のピンクから右の青へと、横に変えることもできます。[resetfont][r][font edge=true edgecolor=0x5025ff edgegradcolor=0xff4080 shadow=true shadowgradcolor=0x5025ff]縁取りや影にもグラデーションをかけられます。[resetfont]
*ruby|ルビと画像
ルビは文字の上に読みを振ります。[ruby text=かん]漢[ruby text=じ]字の読み方がわかるように、[ruby text=と]東[ruby text=きょう]京や[ruby text=ふ]富[ruby text=じ]士[ruby text=さん]山のように。
画像も文字と同じように行の中に置けます。[graph storage=msg_auto_normal char=false alt="（オート）"]はオートモード、[graph storage=msg_log_normal char=false alt="（履歴）"]は履歴で、ウィンドウのボタンと同じ絵です。
*layout|揃えと間隔
[style align=center]行はウィンドウの真ん中にも、[r][style align=right]右端にも置けます。[r][style align=default]文字と文字の間を[style pitch=8]広げることも[style pitch=default]できます（[[style pitch=]）。
[style linespacing=30]行と行の間も広げられます。[r]一行ずつ、[r][[style linespacing=] で。[style linespacing=default]
・[indent]一行に収まらない行は、[[indent] と [[endindent] で、二行目からの頭を一行目の頭に揃えられます。この行のように。[endindent]
*speed|速さと間
[delay speed=110]文字は一文字ずつゆっくり出すことも、[delay speed=user][delay speed=8]一気に流すことも、[delay speed=user][nowait]一度に全部出すこともできます。[endnowait]途中で間をとって、[wait time=900]また続けたり、行の途中で[l]クリックを待ったりもできます。
*moving|動く文字
文字は表示されている間も動かせます。[font anim=shake]怖くて震えたり、[resetfont][font anim=wave]波のようにうねったり、[resetfont][font anim=pulse]鼓動のように脈打ったり、[resetfont][font anim=rainbow]七色に光ったり。[resetfont]
【ai】[font anim=shake animsize=6 color=0xff9090]きゃっ！[resetfont]　いま何か横切った！
一文字ずつ、描かれるときの現れかたも変えられます。[font appear=fade]ふわっと浮かび出たり、[resetfont][font appear=rise]下からせり上がったり、[resetfont][font appear=drop]上から落ちてきたり、[resetfont][font appear=slide]右から滑り込んだり。[resetfont]
[font appear=drop anim=wave color=0xffd75e]現れたあと、そのまま動き続けることもできます。[resetfont]設定の「動きを減らす」で、動く文字は止まります。
*names|名前と言葉
【ai/謎の声】誰かいるの？　一行だけ、名前を別の表示にすることもできます。この行のように。
【ai】物語が知っていることも、文に入れられます。たとえば、あなたの名前。[emb exp="kag.heroName()"]。
用語集に載っている言葉、たとえばワールドは、描かれるときに印がつきます。クリックするとその説明が出ます。
*window|ウィンドウのスタイル
[env msgstyle=memory]場面ごとに、ウィンドウに独自のスタイルをつけられます。回想ならセピアの枠で、名前の枠もそれに合わせて。
【ai】たとえば、ずっと前の夏の思い出のように。
[env msgstyle=normal]
*vertical|縦書き
文章は、日本の本のように上から下へと流すこともできます。ここでは専用のウィンドウを vertical=true にしています。
[eval exp="tf.textDemoWindow = kag.fore.messages[1].store()"]
[position layer=message1 page=fore vertical=true left=1440 top=30 width=420 height=640 frame="" color=0x1a1040 opacity=210 marginl=30 margint=34 marginr=30 marginb=34 visible=true]
[current layer=message1]
「[ruby text=たて]縦[ruby text=が]書き」は、上から下へ、右から左へと読みます。数字は[hch text="12"]月のように横に並べられます。
[current layer=message0]
[eval exp="kag.fore.messages[1].restore(tf.textDemoWindow)"]
[layopt layer=message1 page=fore visible=false]
*end|プレイヤーの文字
【ai】プレイヤーも自分の好みを選べます。設定の「テキスト」のページで、書体や縁取り、影、色を。文字の紹介はここまでです！
[ai hide fade]
*done
[demodone name=text]
[jump storage=s0001.ks]
