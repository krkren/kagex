*start|Start
; Text effects: what a message window can do with its text, a page each. The tags are KAG3's
; ([font], [style], [ruby], [graph], [delay], [nowait], [wait], [l], [indent], [position], [hch],
; [emb]) and KAGEX's (gradients and window styles since 0.22.0, [font anim=] and [font appear=]
; since 0.23.0). See "Text Effects" in doc/kagex.txt.
[initscene]
[road normal]
[ai standard center]
【ai】Text can do a lot more than say things. Let me show you what a message window can do with it, one thing a page.
*style|Colour, Size and Style
Words can be [font color=0xff8080]red[resetfont], [font color=0x80d0ff]blue[resetfont] or [font color=0xffd75e]gold[resetfont]; [font size=60]big[resetfont] or [font size=26]small[resetfont]; [font bold=false]light[resetfont] or [font italic=true]slanted[resetfont]. [[font] changes them and [[resetfont] puts them back.
[font face="Noto Serif JP"]Another font for a letter, a poem or an old book: here the sample's own serif face, which the game lists in fonts.csv.[resetfont]
*outline|Outlines, Shadows and Gradients
[font edge=true edgecolor=0x5025ff shadow=false]An outline, [resetfont][font edge=false shadow=true shadowcolor=0x000000]a shadow, [resetfont]or [font edge=true edgecolor=0x2a1a7a shadow=true shadowcolor=0x000000]both at once,[resetfont] each in a colour of its own.
[font gradcolor=0xffd75e]Text can shade down its line from white to gold,[resetfont][r][font color=0xff80c0 gradcolor=0x80c0ff graddir=horizontal]or along the window, from pink at its left to blue at its right,[resetfont][r][font edge=true edgecolor=0x5025ff edgegradcolor=0xff4080 shadow=true shadowgradcolor=0x5025ff]and so can its outline and its shadow.[resetfont]
*ruby|Ruby and Pictures
Ruby puts a reading over a character, as Japanese does over its [ruby text=かん]漢[ruby text=じ]字, so a reader knows how to say [ruby text=と]東[ruby text=きょう]京 or [ruby text=ふ]富[ruby text=じ]士[ruby text=さん]山.
A picture can sit in a line like a character: [graph storage=msg_auto_normal char=false alt="(auto)"] is auto mode and [graph storage=msg_log_normal char=false alt="(history)"] the history, as on the window's own buttons.
*layout|Alignment and Spacing
[style align=center]A line can sit in the middle of the window,[r][style align=right]or at its right.[r][style align=default]Its letters can [style pitch=8]stand further apart,[style pitch=default] with [[style pitch=].
[style linespacing=30]And its lines can stand further apart too,[r]one from the next,[r]with [[style linespacing=].[style linespacing=default]
• [indent]A line that runs on over more than one line can keep its later lines in step with its first, as this one does, with [[indent] and [[endindent].[endindent]
*speed|Speed and Pauses
[delay speed=110]Text can come slowly, a letter at a time, [delay speed=user][delay speed=8]or rush out, [delay speed=user][nowait]or all be there at once.[endnowait] It can pause,[wait time=900] then go on, or wait for a click[l] in the middle of a line.
*moving|Moving Text
Text can move while it shows: [font anim=shake]it shakes with fear, [resetfont][font anim=wave]it rolls like the sea, [resetfont][font anim=pulse]it beats like a heart, [resetfont][font anim=rainbow]or it shines in every colour.[resetfont]
【ai】[font anim=shake animsize=6 color=0xff9090]Eek![resetfont] Something just ran past me!
Each character can come in as it's drawn: [font appear=fade]fading in, [resetfont][font appear=rise]rising up, [resetfont][font appear=drop]dropping down, [resetfont][font appear=slide]sliding in from the right.[resetfont]
[font appear=drop anim=wave color=0xffd75e]And it can come in and then keep moving.[resetfont] Reduce Motion, in Config, holds moving text still.
*names|Names and Words
【ai/A Voice】Who's there? A name can show as something else for a line, as this one does.
【ai】Text can also carry what the story knows, such as your name: [emb exp="kag.heroName()"].
Words the glossary explains, such as the World, are marked as they're drawn: a click on one shows its entry.
*window|Window Styles
[env msgstyle=memory]A scene can give the window a style of its own: a memory's sepia frame, its name box too.
【ai】Like this memory of a summer long ago.
[env msgstyle=normal]
*vertical|Vertical Text
Text can also run down the screen, as Japanese books are printed. It goes in a window of its own here, set to vertical=true.
[eval exp="tf.textDemoWindow = kag.fore.messages[1].store()"]
[position layer=message1 page=fore vertical=true left=1440 top=30 width=420 height=640 frame="" color=0x1a1040 opacity=210 marginl=30 margint=34 marginr=30 marginb=34 visible=true]
[current layer=message1]
「[ruby text=たて]縦[ruby text=が]書き」は、上から下へ、右から左へと読みます。数字は[hch text="12"]月のように横に並べられます。
[current layer=message0]
[eval exp="kag.fore.messages[1].restore(tf.textDemoWindow)"]
[layopt layer=message1 page=fore visible=false]
*end|The Player's Text
【ai】And the player has a say too: Config's Text page picks their font, its outline, shadow and colour. That's all for text!
[ai hide fade]
*done
[demodone name=text]
[jump storage=s0001.ks]
