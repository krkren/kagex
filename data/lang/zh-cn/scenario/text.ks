*start|开始
; Text effects: what a message window can do with its text, a page each. The tags are KAG3's
; ([font], [style], [ruby], [graph], [delay], [nowait], [wait], [l], [indent], [position], [hch],
; [emb]) and KAGEX's (gradients and window styles since 0.22.0, [font anim=] and [font appear=]
; since 0.23.0). See "Text Effects" in doc/kagex.txt.
[initscene]
[road normal]
[ai standard center]
【ai】文字能做的可不只是说话。我来给你看看对话框能拿文字做些什么，一页展示一种。
*style|颜色、大小与样式
文字可以是[font color=0xff8080]红色[resetfont]、[font color=0x80d0ff]蓝色[resetfont]或[font color=0xffd75e]金色[resetfont]；可以[font size=60]很大[resetfont]，也可以[font size=26]很小[resetfont]；可以[font bold=false]细一些[resetfont]，也可以[font italic=true]倾斜[resetfont]。[[font] 改变它们，[[resetfont] 恢复原样。
[font face="Noto Serif JP"]书信、诗歌或古书可以换一种字体：这里用的是示例自带的衬线字体，游戏在 fonts.csv 中列出了它。[resetfont]
*outline|描边、阴影与渐变
[font edge=true edgecolor=0x5025ff shadow=false]描边、[resetfont][font edge=false shadow=true shadowcolor=0x000000]阴影，[resetfont]或者[font edge=true edgecolor=0x2a1a7a shadow=true shadowcolor=0x000000]两者同时使用，[resetfont]每种都能用自己的颜色。
[font gradcolor=0xffd75e]文字可以在一行内从上到下由白渐变为金，[resetfont][r][font color=0xff80c0 gradcolor=0x80c0ff graddir=horizontal]也可以沿着对话框，从左边的粉色渐变到右边的蓝色，[resetfont][r][font edge=true edgecolor=0x5025ff edgegradcolor=0xff4080 shadow=true shadowgradcolor=0x5025ff]描边和阴影同样可以渐变。[resetfont]
*ruby|注音与图片
注音可以把读音标在字的上方，比如给[ruby text=hàn]汉[ruby text=zì]字标上拼音，让读者知道[ruby text=chóng]重[ruby text=qìng]庆、[ruby text=huáng]黄[ruby text=hè]鹤[ruby text=lóu]楼该怎么念。
图片也能像文字一样放在行内：[graph storage=msg_auto_normal char=false alt="（自动）"]是自动模式，[graph storage=msg_log_normal char=false alt="（历史记录）"]是历史记录，和对话框上的按钮一样。
*layout|对齐与间距
[style align=center]一行文字可以放在对话框的正中间，[r][style align=right]也可以靠右。[r][style align=default]字与字之间也可以[style pitch=8]拉得更开，[style pitch=default]只要用 [[style pitch=]。
[style linespacing=30]行与行之间也可以拉开，[r]一行接着一行，[r]用 [[style linespacing=] 就行。[style linespacing=default]
• [indent]一句话长到一行放不下时，可以用 [[indent] 和 [[endindent] 让第二行起的开头和第一行的开头对齐，就像这一句一样。[endindent]
*speed|速度与停顿
[delay speed=110]文字可以一个字一个字慢慢出现，[delay speed=user][delay speed=8]也可以飞快地涌出来，[delay speed=user][nowait]还可以一下子全部显示。[endnowait]它可以停顿一下，[wait time=900]再接着往下，也可以在一行的中途等待点击[l]，然后继续。
*moving|会动的文字
文字显示时也能动起来：[font anim=shake]害怕得发抖，[resetfont][font anim=wave]像海浪一样起伏，[resetfont][font anim=pulse]像心跳一样跳动，[resetfont][font anim=rainbow]或者闪耀出七彩的光芒。[resetfont]
【ai】[font anim=shake animsize=6 color=0xff9090]呀！[resetfont]刚才有什么东西从我身边跑过去了！
每个字在显示时都可以有入场效果：[font appear=fade]慢慢浮现，[resetfont][font appear=rise]从下方升起，[resetfont][font appear=drop]从上方落下，[resetfont][font appear=slide]从右边滑进来。[resetfont]
[font appear=drop anim=wave color=0xffd75e]还可以先入场，再一直动下去。[resetfont]在设置里打开“减少动态效果”，会动的文字就会静止。
*names|名字与词语
【ai/神秘的声音】是谁在那里？名字可以在某一句里显示成别的，就像这一句。
【ai】文字里还能放进故事所知道的信息，比如你的名字：[emb exp="kag.heroName()"]。
词汇表里解释过的词，比如“世界”，在显示时会加上标记：点击它就能看到解释。
*window|对话框样式
[env msgstyle=memory]场景可以给对话框换上专属的样式：回忆用的是旧照片般的棕褐色边框，名字框也一起换。
【ai】就像这段很久以前那个夏天的回忆。
[env msgstyle=normal]
*vertical|竖排文字
文字也可以像竖排印刷的书那样从上往下排。这里用的是一个设为 vertical=true 的专用对话框。
[eval exp="tf.textDemoWindow = kag.fore.messages[1].store()"]
[position layer=message1 page=fore vertical=true left=1440 top=30 width=420 height=640 frame="" color=0x1a1040 opacity=210 marginl=30 margint=34 marginr=30 marginb=34 visible=true]
[current layer=message1]
「[ruby text=shù]竖[ruby text=pái]排」的文字从上往下、从右往左读。数字可以像[hch text="12"]月这样横着排。
[current layer=message0]
[eval exp="kag.fore.messages[1].restore(tf.textDemoWindow)"]
[layopt layer=message1 page=fore visible=false]
*end|玩家的文字设置
【ai】玩家也能做主：在设置的“文字”页，可以选择字体、描边、阴影和颜色。文字的介绍就到这里！
[ai hide fade]
*done
[demodone name=text]
[jump storage=s0001.ks]
