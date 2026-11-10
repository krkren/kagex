*start|開始
; An animated character. Pip is a World character drawn from layers (KAGEnvCharacterEx.tjs,
; "exstand"): data/main/charinit.csv names its files, data/fgimage/pip holds its layers (made by
; tools/assets/make_pip.py), and its envinit.tjs entry has no poses. See "Characters drawn from
; layers" in doc/world.txt.
[initscene]
[road normal]
[pip standard center]
皮普由多個圖層組成，顯示時才拼合起來：一個身體、兩套服裝、三種手臂姿勢和六種表情。
[pip wave voice=1]
【pip】嗨！我是皮普。
[pip rest voice=2]
【pip】我會自己眨眼，嘴巴也會跟著聲音動哦。
它的眼睛每隔幾秒眨一次；說話時，聲音越大，嘴巴張得越大。
[pip neutral voice=9]
【pip】又見面啦！仔細聽哦。我用真實的聲音說話時，嘴巴會做出每個母音的口型。啊、咿、嗚、誒、喔。是不是比含含糊糊地動嘴好多了？
這句臺詞由 kagex-lipsync 根據語音和文字算出每個母音出現的時間，並在語音旁邊寫出了 pip000009.lip。其他語音都只按音量來動嘴。
[pip xsurprised voice=3]
【pip】哦！新表情！
在表情前面加上 x，比如 xsurprised，表情變化時就會閉上眼睛。
[pip sad voice=4]
【pip】哎呀，嚇到你了嗎？
[pip beret smile voice=5]
【pip】我看起來怎麼樣？
[pip laugh cheer voice=6]
【pip】哈哈！我喜歡！
大笑的表情把眼睛畫成閉著的，所以不會眨眼，但嘴巴照樣會動。
[pip plain angry rest voice=7]
【pip】喂！我很喜歡那頂帽子的！
服裝和表情一樣可以更換：beret 戴上帽子，plain 摘掉帽子。
[pip neutral frontlevel]
世界擴充套件的每個層級都有一套按該尺寸繪製的圖層，所以皮普離得再近也很清晰。
[pip centerlevel]
[pip eyecloseto]
眼睛和嘴巴也能聽指令：eyecloseto 會閉上眼睛，並等到完全閉上為止。
[pip eyeopento]
然後用 eyeopento 再睜開。
[pip eyeflip=3]
eyeflip=3 會眨三次眼。
[pip lipflip=4]
而 lipflip=4 會在沒有語音的情況下讓嘴巴動四次。
[pip smile waving voice=8]
【pip】回頭見！
那個揮手是動畫：data/main/charanim.csv 裡的 waving 會用計時器依次切換手臂姿勢，直到有別的變化為止。
[pip hide]
*pipcg|用圖層拼成的一張圖
; CG variations (since 0.26.0, CGVariations.tjs): pictures that are one layered file's layers
; shown in different ways, each with a name of its own, listed in data/main/cgvariations.txt. The
; file is data/evimage/pipcg.txt with a picture per layer, as kagex-release splits a .psd or .clip
; (made by tools/assets/make_pip.py cg); the gallery has all four (cglist.csv). See "CG
; Variations From One Layered File" in doc/kagex.txt.
[EV file=pipcg_day fade]
用一個分層檔案做成的 CG：天空、山丘、皮普、它的手臂和表情都是圖層，這張圖顯示了其中的一部分。
[EV file=pipcg_laugh fade]
pipcg_laugh 是同一個檔案顯示了別的圖層：舉起的手臂和大笑的表情。
[EV file=pipcg_evening fade]
pipcg_evening 有傍晚的天空、籠罩一切的橙色光芒，還有貝雷帽。
[EV file=pipcg_night fade]
而 pipcg_night 是月亮、星星和一張睡眼惺忪的臉。一個檔案，四張圖，每張在 CG 鑑賞裡都有自己的名字。
[EV hide fade]
*live2d|Live2D
; A Live2D character: Hiyori, Live2D Inc.'s sample model, drawn by the krkrlive2d plugin
; (KAGEnvCharacterLive2D.tjs). Her model, data/fgimage/hiyori.l2d, comes from
; tools/assets/make_hiyori.py; her voice line is eSpeak NG's (make_hiyori.py speech). A
; build without the plugin or the model says so instead. See "Live2D Characters" in
; doc/world.txt.
[if exp="!KAGLive2DCanDraw('hiyori')"]
這個版本無法播放 Live2D 模型。需要用 Live2D 的 Cubism SDK 構建的 krkrlive2d 外掛，以及模型：新增方法請看 doc/world.txt 中的“Live2D Characters”。
[jump target=*vrm]
[endif]
[hiyori standard center]
這是日和，一個 Live2D 模型：她是 Live2D Inc. 的示例角色，用 Cubism Editor 製作，由 krkrlive2d 外掛繪製。本內容使用了 Live2D Inc. 擁有著作權的示例資料。
[hiyori smile]
[hiyori voice=1]
【hiyori】你好！我是日和。和皮普一樣，我會自己眨眼，嘴巴也會跟著聲音動！
她的嘴巴跟著 kagex-lipsync 根據她的語音和臺詞生成的口型軌道動：每個母音都有自己的口型。
[hiyori normal]
表情本身的嘴巴數值就是嘴巴靜止時的位置，所以她說完話就會閉上嘴。
[hiyori thinking]
她的表情是 envinit.tjs 為她設定的一組模型引數，表情之間會漸變過渡。
[hiyori xsad]
在表情前面加上 x，比如這裡的 xsad，表情變化時會眨一下眼。
[hiyori wink]
表情可以只閉上她的一隻眼睛，另一隻睜著：wink 就是這樣。
[hiyori surprised]
surprised 會讓她的嘴巴一直張著，因為這個表情就是這樣要求的。
[hiyori normal eyeflip=2 lipflip=3]
眼睛和嘴巴的指令對她和對皮普一樣有效：eyeflip=2 眨兩次眼，lipflip=3 讓她的嘴動三次。
[hiyori tap motionwait]
tap 會把她模型的 TapBody 動作播放一次，motionwait 會等它結束；之後她姿勢的動作會繼續播放。
[hiyori idle5 motionwait]
動作的名字來自 envinit.tjs，裡面寫明瞭組和編號：idle5 是她 Idle 組九個動作中的第五個。
[hiyori m03 motionwait]
而 m03 指的是動作所在的檔案 motions/Hiyori_m03.motion3.json，不管它屬於哪個組。
[hiyori still]
姿勢就是持續播放的動作：standard 依次播放 Idle 組的動作，still 只播放一個動作。
[hiyori standard]
動作會讓她的頭、身體和手臂動起來，頭髮和裙子則靠模型自身的物理演算擺動。
[hiyori normal hide]
*vrm|VRM
; A VRM character: Vee, the sample's own avatar, built from shapes by tools/assets/make_vrm.py
; (data/fgimage/vee.vrm, her VRM animations vee_*.vrma) and drawn by the krkrthreepp plugin
; (KAGEnvCharacterVRM.tjs); her voice line is eSpeak NG's (make_vrm.py speech). A build without
; the plugin says so instead. See "VRM Characters" in doc/world.txt.
[if exp="!KAGVRMCanDraw('vee')"]
這個版本無法繪製 3D 模型。需要 krkrthreepp 外掛和 OpenGL ES：詳情請看 doc/world.txt 中的“VRM Characters”。
[demodone name=anim]
[jump storage=s0001.ks]
[endif]
[vee standard center]
這是薇，一個 VRM 虛擬形象：VRoid Studio 匯出的那種格式的 3D 模型，由指令碼用簡單的形狀為這個示例搭建而成，由 krkrthreepp 外掛繪製。
[vee smile voice=1]
【vee】嗨！我是薇。我是 3D 模型，所以能轉身、揮手、歡呼。而且說話的時候，嘴巴也會做出每個母音的口型哦！
她的嘴巴跟著 kagex-lipsync 根據她的語音生成的口型軌道動：每個母音會設定虛擬形象對應的表情，aa、ih、ou、ee 或 oh。
[vee laugh]
她的表情是虛擬形象各個表情的權重：laugh 是 happy 拉滿，smile 則少一些。
[vee xsad]
VRM 為常用的表情規定了名字，比如 happy、sad、angry、relaxed 和 surprised，所以同一個表情可以用在任何帶有這些表情的虛擬形象上。
[vee blush]
虛擬形象還可以有自己的表情：blush 就是薇特有的。
[vee normal wave motionwait]
wave 會把 VRM 動畫播放一次，motionwait 會等它結束；之後她姿勢的動畫會繼續播放。
[vee think]
姿勢是迴圈播放的 VRM 動畫：think 會讓她一直託著下巴，直到換成另一個姿勢。
[vee standard surprised nod motionwait]
動畫之間會漸變過渡，所以 nod 會從姿勢留下的姿態直接開始。
[vee laugh cheer motionwait]
她一動，雙馬尾就跟著擺動：這是 VRM 的彈簧骨骼。
[vee smile bow motionwait]
[vee normal hide]
[demodone name=anim]
[jump storage=s0001.ks]
