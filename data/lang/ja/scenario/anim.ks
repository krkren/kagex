*start|スタート
; An animated character. Pip is a World character drawn from layers (KAGEnvCharacterEx.tjs,
; "exstand"): data/main/charinit.csv names its files, data/fgimage/pip holds its layers (made by
; tools/assets/make_pip.py), and its envinit.tjs entry has no poses. See "Characters drawn from
; layers" in doc/world.txt.
[initscene]
[road normal]
[pip standard center]
ピップは表示するときにレイヤを組み合わせて描かれます。体がひとつ、衣装がふたつ、腕のポーズが三つ、表情が六つです。
[pip wave voice=1]
【pip】やあ！ ぼくはピップ。
[pip rest voice=2]
【pip】ひとりでまばたきするし、声にあわせて口も動くよ。
目は数秒ごとにまばたきし、しゃべっているあいだは声の大きさに応じて口が開きます。
[pip neutral voice=9]
【pip】もう一回こんにちは！ よく聞いてね。本物の声でしゃべると、ぼくの口は言った母音ひとつひとつの形になるんだ。あー、いー、うー、えー、おー。もごもご言うより、ずっといいでしょ？
このせりふでは、kagex-lipsync が声とその文からそれぞれの母音を言うタイミングを割り出し、声の隣に pip000009.lip を書きました。ほかの声はどれも、声の大きさだけで口を動かします。
[pip xsurprised voice=3]
【pip】おっ！ 新しい顔だ！
xsurprised のように表情の前に x をつけると、表情が変わるあいだ目を閉じます。
[pip sad voice=4]
【pip】おっと、びっくりさせちゃった？
[pip beret smile voice=5]
【pip】どうかな、似合う？
[pip laugh cheer voice=6]
【pip】あはは！ 気に入った！
笑い顔は目を閉じた絵なのでまばたきはしませんが、口は動きます。
[pip plain angry rest voice=7]
【pip】ちょっと！ あの帽子、気に入ってたのに！
衣装も表情と同じように変わります。beret で帽子をかぶり、plain で脱ぎます。
[pip neutral frontlevel]
World のレベルごとにその大きさで描いたレイヤがあるので、近づいてもピップはくっきりしたままです。
[pip centerlevel]
[pip eyecloseto]
目と口は命令でも動かせます。eyecloseto は目を閉じ、閉じ終わるまで待ちます。
[pip eyeopento]
そして eyeopento でまた開きます。
[pip eyeflip=3]
eyeflip=3 で三回まばたきします。
[pip lipflip=4]
lipflip=4 なら、声なしで口を四回動かします。
[pip smile waving voice=8]
【pip】またね！
あの手を振る動きはアニメーションです。data/main/charanim.csv の waving が、ほかの変化があるまでタイマーで腕のポーズを切り替えています。
[pip hide]
*pipcg|レイヤーから作る一枚絵
[EV file=pipcg_day fade]
ひとつのレイヤーファイルから作った CG です。空、丘、ピップ、その腕や表情がそれぞれレイヤーで、この絵はその一部を見せています。
[EV file=pipcg_laugh fade]
pipcg_laugh は同じファイルの別のレイヤーを見せたもの。ばんざいの腕と笑顔です。
[EV file=pipcg_evening fade]
pipcg_evening は夕方の空と、全体にかかるオレンジ色の光、それにベレー帽。
[EV file=pipcg_night fade]
pipcg_night は月と星と眠そうな顔。ファイルはひとつ、絵は四枚で、ギャラリーではそれぞれの名前で並びます。
[EV hide fade]
*live2d|Live2D
[if exp="!KAGLive2DCanDraw('hiyori')"]
このビルドでは Live2D モデルを再生できません。Live2D の Cubism SDK でビルドした krkrlive2d プラグインとモデルが必要です。追加のしかたは doc/world.txt の「Live2D Characters」にあります。
[jump target=*vrm]
[endif]
[hiyori standard center]
こちらはひより、Live2D のモデルです。株式会社 Live2D のサンプルキャラクターで、Cubism Editor で作られ、krkrlive2d プラグインが描いています。このコンテンツは、株式会社 Live2D が著作権を保有するサンプルデータを使用しています。
[hiyori smile]
[hiyori voice=1]
【hiyori】こんにちは！ひよりです。ピップと同じように、ひとりでにまばたきして、声に合わせて口が動きます！
口は、声とその台本から kagex-lipsync が作ったリップトラックに従って動きます。母音ひとつひとつに、形のちがう口があたります。
[hiyori normal]
表情がもともと持っている口の値が声を抜けたあとに休む形なので、話し終われば口は閉じます。
[hiyori thinking]
顔は envinit.tjs がそのモデルのパラメータについて決めた集まりで、表情から表情へはフェードします。
[hiyori xsad]
表情の前の x、ここでいう xsad は、表情が変わるときにまばたきします。
[hiyori wink]
表情は片方の目だけ閉じて、もう一方は開けたままにできます。wink がそれです。
[hiyori surprised]
surprised はその表情のとおりに口を開けたままにします。
[hiyori normal eyeflip=2 lipflip=3]
目と口のコマンドはピップと同じように使えます。eyeflip=2 は二回まばたきし、lipflip=3 は口を三度動かします。
[hiyori tap motionwait]
tap はモデルの TapBody モーションを一度だけ再生し、motionwait はその終わりを待ちます。そのあとはポーズのモーションに戻ります。
[hiyori idle5 motionwait]
モーションの名前は envinit.tjs で、グループと番号で決めます。idle5 は Idle グループの九個なかの五番めです。
[hiyori m03 motionwait]
m03 は来るファイルの名前で決めています。motions/Hiyori_m03.motion3.json のもので、どのグループに入っていても構いません。
[hiyori still]
ポーズは続いて再生されるモーションです。standard は Idle グループのモーションを次々に、still は一つのモーションだけ再生します。
[hiyori standard]
モーションは頭や体や腕を動かし、髪やスカートはモデル自身の物理演算で動きます。
[hiyori normal hide]
*vrm|VRM
[if exp="!KAGVRMCanDraw('vee')"]
このビルドでは 3D モデルを描けません。krkrthreepp プラグインと OpenGL ES が必要です。くわしくは doc/world.txt の「VRM Characters」にあります。
[demodone name=anim]
[jump storage=s0001.ks]
[endif]
[vee standard center]
こちらはヴィー、VRM のアバターです。VRoid Studio が書き出すのと同じ形式の 3D モデルで、このサンプルのためにスクリプトが簡単な形から組み立て、krkrthreepp プラグインが描いています。
[vee smile voice=1]
【vee】こんにちは！ヴィーです。3D モデルだから、向きを変えたり、手を振ったり、跳びはねたりできます。話すときは、母音ごとに口の形も変わるんですよ！
口は、声から kagex-lipsync が作ったリップトラックに従います。母音ごとに、アバター自身の aa、ih、ou、ee、oh の表情が使われます。
[vee laugh]
顔はアバターの表情の重みの組み合わせです。laugh は happy をいっぱいに、smile はそれより少なめにしたものです。
[vee xsad]
happy、sad、angry、relaxed、surprised のようなよく使う表情は VRM が名前を決めているので、同じ顔がそれを持つどのアバターにも使えます。
[vee blush]
アバターは自分だけの表情も持てます。blush はヴィーのものです。
[vee normal wave motionwait]
wave は VRM アニメーションを一度だけ再生し、motionwait はその終わりを待ちます。そのあとはポーズのアニメーションに戻ります。
[vee think]
ポーズはループする VRM アニメーションです。think は、次のポーズが来るまで手をあごに当てたままにします。
[vee standard surprised nod motionwait]
アニメーションは次のアニメーションへフェードするので、nod はポーズのとちゅうの姿勢からそのまま始まります。
[vee laugh cheer motionwait]
動くとツインテールが揺れます。VRM のスプリングボーンです。
[vee smile bow motionwait]
[vee normal hide]
[demodone name=anim]
[jump storage=s0001.ks]
