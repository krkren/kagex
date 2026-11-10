*start|开始
; An animated character. Pip is a World character drawn from layers (KAGEnvCharacterEx.tjs,
; "exstand"): data/main/charinit.csv names its files, data/fgimage/pip holds its layers (made by
; tools/assets/make_pip.py), and its envinit.tjs entry has no poses. See "Characters drawn from
; layers" in doc/world.txt.
[initscene]
[road normal]
[pip standard center]
皮普由多个图层组成，显示时才拼合起来：一个身体、两套服装、三种手臂姿势和六种表情。
[pip wave voice=1]
【pip】嗨！我是皮普。
[pip rest voice=2]
【pip】我会自己眨眼，嘴巴也会跟着声音动哦。
它的眼睛每隔几秒眨一次；说话时，声音越大，嘴巴张得越大。
[pip neutral voice=9]
【pip】又见面啦！仔细听哦。我用真实的声音说话时，嘴巴会做出每个元音的口型。啊、咿、呜、诶、喔。是不是比含含糊糊地动嘴好多了？
这句台词由 kagex-lipsync 根据语音和文字算出每个元音出现的时间，并在语音旁边写出了 pip000009.lip。其他语音都只按音量来动嘴。
[pip xsurprised voice=3]
【pip】哦！新表情！
在表情前面加上 x，比如 xsurprised，表情变化时就会闭上眼睛。
[pip sad voice=4]
【pip】哎呀，吓到你了吗？
[pip beret smile voice=5]
【pip】我看起来怎么样？
[pip laugh cheer voice=6]
【pip】哈哈！我喜欢！
大笑的表情把眼睛画成闭着的，所以不会眨眼，但嘴巴照样会动。
[pip plain angry rest voice=7]
【pip】喂！我很喜欢那顶帽子的！
服装和表情一样可以更换：beret 戴上帽子，plain 摘掉帽子。
[pip neutral frontlevel]
世界扩展的每个层级都有一套按该尺寸绘制的图层，所以皮普离得再近也很清晰。
[pip centerlevel]
[pip eyecloseto]
眼睛和嘴巴也能听指令：eyecloseto 会闭上眼睛，并等到完全闭上为止。
[pip eyeopento]
然后用 eyeopento 再睁开。
[pip eyeflip=3]
eyeflip=3 会眨三次眼。
[pip lipflip=4]
而 lipflip=4 会在没有语音的情况下让嘴巴动四次。
[pip smile waving voice=8]
【pip】回头见！
那个挥手是动画：data/main/charanim.csv 里的 waving 会用计时器依次切换手臂姿势，直到有别的变化为止。
[pip hide]
*pipcg|用图层拼成的一张图
; CG variations (since 0.26.0, CGVariations.tjs): pictures that are one layered file's layers
; shown in different ways, each with a name of its own, listed in data/main/cgvariations.txt. The
; file is data/evimage/pipcg.txt with a picture per layer, as kagex-release splits a .psd or .clip
; (made by tools/assets/make_pip.py cg); the gallery has all four (cglist.csv). See "CG
; Variations From One Layered File" in doc/kagex.txt.
[EV file=pipcg_day fade]
用一个分层文件做成的 CG：天空、山丘、皮普、它的手臂和表情都是图层，这张图显示了其中的一部分。
[EV file=pipcg_laugh fade]
pipcg_laugh 是同一个文件显示了别的图层：举起的手臂和大笑的表情。
[EV file=pipcg_evening fade]
pipcg_evening 有傍晚的天空、笼罩一切的橙色光芒，还有贝雷帽。
[EV file=pipcg_night fade]
而 pipcg_night 是月亮、星星和一张睡眼惺忪的脸。一个文件，四张图，每张在 CG 鉴赏里都有自己的名字。
[EV hide fade]
*live2d|Live2D
; A Live2D character: Hiyori, Live2D Inc.'s sample model, drawn by the krkrlive2d plugin
; (KAGEnvCharacterLive2D.tjs). Her model, data/fgimage/hiyori.l2d, comes from
; tools/assets/make_hiyori.py; her voice line is eSpeak NG's (make_hiyori.py speech). A
; build without the plugin or the model says so instead. See "Live2D Characters" in
; doc/world.txt.
[if exp="!KAGLive2DCanDraw('hiyori')"]
这个版本无法播放 Live2D 模型。需要用 Live2D 的 Cubism SDK 构建的 krkrlive2d 插件，以及模型：添加方法请看 doc/world.txt 中的“Live2D Characters”。
[jump target=*vrm]
[endif]
[hiyori standard center]
这是日和，一个 Live2D 模型：她是 Live2D Inc. 的示例角色，用 Cubism Editor 制作，由 krkrlive2d 插件绘制。本内容使用了 Live2D Inc. 拥有著作权的示例数据。
[hiyori smile]
[hiyori voice=1]
【hiyori】你好！我是日和。和皮普一样，我会自己眨眼，嘴巴也会跟着声音动！
她的嘴巴跟着 kagex-lipsync 根据她的语音和台词生成的口型轨道动：每个元音都有自己的口型。
[hiyori normal]
表情本身的嘴巴数值就是嘴巴静止时的位置，所以她说完话就会闭上嘴。
[hiyori thinking]
她的表情是 envinit.tjs 为她设定的一组模型参数，表情之间会渐变过渡。
[hiyori xsad]
在表情前面加上 x，比如这里的 xsad，表情变化时会眨一下眼。
[hiyori wink]
表情可以只闭上她的一只眼睛，另一只睁着：wink 就是这样。
[hiyori surprised]
surprised 会让她的嘴巴一直张着，因为这个表情就是这样要求的。
[hiyori normal eyeflip=2 lipflip=3]
眼睛和嘴巴的指令对她和对皮普一样有效：eyeflip=2 眨两次眼，lipflip=3 让她的嘴动三次。
[hiyori tap motionwait]
tap 会把她模型的 TapBody 动作播放一次，motionwait 会等它结束；之后她姿势的动作会继续播放。
[hiyori idle5 motionwait]
动作的名字来自 envinit.tjs，里面写明了组和编号：idle5 是她 Idle 组九个动作中的第五个。
[hiyori m03 motionwait]
而 m03 指的是动作所在的文件 motions/Hiyori_m03.motion3.json，不管它属于哪个组。
[hiyori still]
姿势就是持续播放的动作：standard 依次播放 Idle 组的动作，still 只播放一个动作。
[hiyori standard]
动作会让她的头、身体和手臂动起来，头发和裙子则靠模型自身的物理演算摆动。
[hiyori normal hide]
*vrm|VRM
; A VRM character: Vee, the sample's own avatar, built from shapes by tools/assets/make_vrm.py
; (data/fgimage/vee.vrm, her VRM animations vee_*.vrma) and drawn by the krkrthreepp plugin
; (KAGEnvCharacterVRM.tjs); her voice line is eSpeak NG's (make_vrm.py speech). A build without
; the plugin says so instead. See "VRM Characters" in doc/world.txt.
[if exp="!KAGVRMCanDraw('vee')"]
这个版本无法绘制 3D 模型。需要 krkrthreepp 插件和 OpenGL ES：详情请看 doc/world.txt 中的“VRM Characters”。
[demodone name=anim]
[jump storage=s0001.ks]
[endif]
[vee standard center]
这是薇，一个 VRM 虚拟形象：VRoid Studio 导出的那种格式的 3D 模型，由脚本用简单的形状为这个示例搭建而成，由 krkrthreepp 插件绘制。
[vee smile voice=1]
【vee】嗨！我是薇。我是 3D 模型，所以能转身、挥手、欢呼。而且说话的时候，嘴巴也会做出每个元音的口型哦！
她的嘴巴跟着 kagex-lipsync 根据她的语音生成的口型轨道动：每个元音会设定虚拟形象对应的表情，aa、ih、ou、ee 或 oh。
[vee laugh]
她的表情是虚拟形象各个表情的权重：laugh 是 happy 拉满，smile 则少一些。
[vee xsad]
VRM 为常用的表情规定了名字，比如 happy、sad、angry、relaxed 和 surprised，所以同一个表情可以用在任何带有这些表情的虚拟形象上。
[vee blush]
虚拟形象还可以有自己的表情：blush 就是薇特有的。
[vee normal wave motionwait]
wave 会把 VRM 动画播放一次，motionwait 会等它结束；之后她姿势的动画会继续播放。
[vee think]
姿势是循环播放的 VRM 动画：think 会让她一直托着下巴，直到换成另一个姿势。
[vee standard surprised nod motionwait]
动画之间会渐变过渡，所以 nod 会从姿势留下的姿态直接开始。
[vee laugh cheer motionwait]
她一动，双马尾就跟着摆动：这是 VRM 的弹簧骨骼。
[vee smile bow motionwait]
[vee normal hide]
[demodone name=anim]
[jump storage=s0001.ks]
