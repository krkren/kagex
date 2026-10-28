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
[demodone name=anim]
[jump storage=s0001.ks]
