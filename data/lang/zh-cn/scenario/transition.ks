*start|开始

[initscene]

世界扩展功能中的转场写法示例

; Specify transitions individually
; When the tag is closed, the following processes are performed:
; 1. Copy the entire screen to the back buffer
; 2. Update only the target layer in the back buffer
; 3. Transition
[road trans=normal]单独更新
[ai uniform center trans=normal]单独更新

[ai hop]
蹦蹦跳跳的动作

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
一次性全部更新

[night trans=wave time=1000]wave
[evening trans=mosaic time=1000]mosaic
[day trans=turn time=1000]turn
[night trans=rotatezoom time=1000]rotatezoom
[evening trans=rotatevanish time=1000]rotatevanish
[day trans=rotateswap time=1000]rotateswap
[night trans=ripple time=1000]ripple

*nagano|extNagano
; extNagano's transitions, in daylight without the character: the event picture comes and goes,
; so each one changes the whole screen. Every one is the plugin's own; without the plugin
; (KAGPluginTransitions says which loaded), each one runs as a crossfade. The plugin has five
; more, book, zoomfade, rgbfade, spin and multiripple, which krkrz_dev's rebuild of it draws
; wrong (UPSTREAM.md 42), so they're left out here.
; 3duniversal's pieces fly only with a speed: accel1 (or speed1) for the old picture's pieces,
; accel2 (speed2) for the new one's (with none at all, the plugin fades the new picture out).
[ai hide trans=normal][day trans=normal]
extNagano 插件还能增加更多转场，这里展示其中的七种。
[if exp="KAGPluginTransitions.flutter != 'linked'"]
这个版本没有该插件，所以这里全部以交叉淡化代替。
[endif]
[EV file=event1 trans=blurfade time=1500 blur1=48 blur2=48]blurfade：经过模糊的交叉淡化
[EV hide trans=flutter time=1500]flutter：画面像纸一样被揭下
[EV file=event1 trans=scanline time=1200]scanline：一条条线从左右两侧交替滑入
[EV hide trans=3duniversal time=2000 rule=rule_shatter accel1=0.4]3duniversal：用规则图像让碎块飞散，这里是玻璃碎片
[EV file=event1 trans=imagewipe time=1500 rule=wipe_brush]imagewipe：沿着图像推进的擦除，这里是一道笔刷痕
[EV hide trans=swirl]morphing：用三角形扭曲画面，这里扭成漩涡（envinit.tjs）
[EV file=event1 trans=honeyturn time=1500 size=80]honeyturn：六边形一个接一个翻过来
[EV hide trans=normal]

*glitch|故障效果
; kagex's own glitch transition (the glitchtrans plugin, since 0.28.0): the picture breaks up as a
; damaged stream or signal would, in stages (a datamosh, a broken JPEG, damaged blocks, sorted
; pixels, a rolling analog picture, frames of signal failure), and the new one arrives in patches;
; style= picks which faults lead. [glitch] (macro.ks) breaks up what's on the screen for a moment.
; Without the plugin the transition is a crossfade, and [glitch] a short pause
kagex 自带的 glitch 转场会在切换到下一张画面的途中把画面打乱。
[EV file=event1 trans=glitch time=1400]glitch：数据错乱、损坏的数据流、崩坏的方块，轮番出现
[EV hide trans=glitch time=1400 style=mosh]style=mosh：旧画面顺着新画面的运动融化
[EV file=event1 trans=glitch time=1100 style=digital]style=digital：缺失的方块、损坏的 JPEG、被重新排序的像素
[EV hide trans=glitch time=1100 style=analog]style=analog：会滚动、倾斜、拖影的劣质信号
[glitch strength=60 seed=7]
还有 [[glitch]：让同一个画面瞬间乱一下，这里效果更轻，而且每次都一样。

[demodone name=transition]

[jump storage=s0001.ks]