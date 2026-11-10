*start|開始
; Text effects: what a message window can do with its text, a page each. The tags are KAG3's
; ([font], [style], [ruby], [graph], [delay], [nowait], [wait], [l], [indent], [position], [hch],
; [emb]) and KAGEX's (gradients and window styles since 0.22.0, [font anim=] and [font appear=]
; since 0.23.0). See "Text Effects" in doc/kagex.txt.
[initscene]
[road normal]
[ai standard center]
【ai】文字能做的可不只是說話。我來給你看看對話方塊能拿文字做些什麼，一頁展示一種。
*style|顏色、大小與樣式
文字可以是[font color=0xff8080]紅色[resetfont]、[font color=0x80d0ff]藍色[resetfont]或[font color=0xffd75e]金色[resetfont]；可以[font size=60]很大[resetfont]，也可以[font size=26]很小[resetfont]；可以[font bold=false]細一些[resetfont]，也可以[font italic=true]傾斜[resetfont]。[[font] 改變它們，[[resetfont] 恢復原樣。
[font face="Noto Serif JP"]書信、詩歌或古書可以換一種字型：這裡用的是示例自帶的襯線字型，遊戲在 fonts.csv 中列出了它。[resetfont]
*outline|描邊、陰影與漸變
[font edge=true edgecolor=0x5025ff shadow=false]描邊、[resetfont][font edge=false shadow=true shadowcolor=0x000000]陰影，[resetfont]或者[font edge=true edgecolor=0x2a1a7a shadow=true shadowcolor=0x000000]兩者同時使用，[resetfont]每種都能用自己的顏色。
[font gradcolor=0xffd75e]文字可以在一行內從上到下由白漸變為金，[resetfont][r][font color=0xff80c0 gradcolor=0x80c0ff graddir=horizontal]也可以沿著對話方塊，從左邊的粉色漸變到右邊的藍色，[resetfont][r][font edge=true edgecolor=0x5025ff edgegradcolor=0xff4080 shadow=true shadowgradcolor=0x5025ff]描邊和陰影同樣可以漸變。[resetfont]
*ruby|注音與圖片
注音可以把讀音標在字的上方，比如給[ruby text=hàn]漢[ruby text=zì]字標上拼音，讓讀者知道[ruby text=chóng]重[ruby text=qìng]慶、[ruby text=huáng]黃[ruby text=hè]鶴[ruby text=lóu]樓該怎麼念。
圖片也能像文字一樣放在行內：[graph storage=msg_auto_normal char=false alt="（自動）"]是自動模式，[graph storage=msg_log_normal char=false alt="（歷史紀錄）"]是歷史紀錄，和對話方塊上的按鈕一樣。
*layout|對齊與間距
[style align=center]一行文字可以放在對話方塊的正中間，[r][style align=right]也可以靠右。[r][style align=default]字與字之間也可以[style pitch=8]拉得更開，[style pitch=default]只要用 [[style pitch=]。
[style linespacing=30]行與行之間也可以拉開，[r]一行接著一行，[r]用 [[style linespacing=] 就行。[style linespacing=default]
• [indent]一句話長到一行放不下時，可以用 [[indent] 和 [[endindent] 讓第二行起的開頭和第一行的開頭對齊，就像這一句一樣。[endindent]
*speed|速度與停頓
[delay speed=110]文字可以一個字一個字慢慢出現，[delay speed=user][delay speed=8]也可以飛快地湧出來，[delay speed=user][nowait]還可以一下子全部顯示。[endnowait]它可以停頓一下，[wait time=900]再接著往下，也可以在一行的中途等待點選[l]，然後繼續。
*moving|會動的文字
文字顯示時也能動起來：[font anim=shake]害怕得發抖，[resetfont][font anim=wave]像海浪一樣起伏，[resetfont][font anim=pulse]像心跳一樣跳動，[resetfont][font anim=rainbow]或者閃耀出七彩的光芒。[resetfont]
【ai】[font anim=shake animsize=6 color=0xff9090]呀！[resetfont]剛才有什麼東西從我身邊跑過去了！
每個字在顯示時都可以有入場效果：[font appear=fade]慢慢浮現，[resetfont][font appear=rise]從下方升起，[resetfont][font appear=drop]從上方落下，[resetfont][font appear=slide]從右邊滑進來。[resetfont]
[font appear=drop anim=wave color=0xffd75e]還可以先入場，再一直動下去。[resetfont]在設定裡開啟“減少動態效果”，會動的文字就會靜止。
*names|名字與詞語
【ai/神秘的聲音】是誰在那裡？名字可以在某一句裡顯示成別的，就像這一句。
【ai】文字裡還能放進故事所知道的資訊，比如你的名字：[emb exp="kag.heroName()"]。
詞彙表裡解釋過的詞，比如“世界”，在顯示時會加上標記：點選它就能看到解釋。
*window|對話方塊樣式
[env msgstyle=memory]場景可以給對話方塊換上專屬的樣式：回憶用的是舊照片般的棕褐色邊框，名字框也一起換。
【ai】就像這段很久以前那個夏天的回憶。
[env msgstyle=normal]
*vertical|豎排文字
文字也可以像豎排印刷的書那樣從上往下排。這裡用的是一個設為 vertical=true 的專用對話方塊。
[eval exp="tf.textDemoWindow = kag.fore.messages[1].store()"]
[position layer=message1 page=fore vertical=true left=1440 top=30 width=420 height=640 frame="" color=0x1a1040 opacity=210 marginl=30 margint=34 marginr=30 marginb=34 visible=true]
[current layer=message1]
「[ruby text=shù]豎[ruby text=pái]排」的文字從上往下、從右往左讀。數字可以像[hch text="12"]月這樣橫著排。
[current layer=message0]
[eval exp="kag.fore.messages[1].restore(tf.textDemoWindow)"]
[layopt layer=message1 page=fore visible=false]
*end|玩家的文字設定
【ai】玩家也能做主：在設定的“文字”頁，可以選擇字型、描邊、陰影和顏色。文字的介紹就到這裡！
[ai hide fade]
*done
[demodone name=text]
[jump storage=s0001.ks]
