*start|スタート

[initscene]

[road]
[ai uniform center]
ワールド拡張機能の「環境レイヤ」のサンプルです。カットインなどの演出に応用できます。

[newlay name=star1 file=star  xpos=0 ypos=0 show]星１表示
[newlay name=star2 file=star xpos=-480 ypos=0 show]星２表示
[newlay name=star3 file=star xpos=480 ypos=0 show]星３表示
[star1 action=LayerNormalRotateModule angvel=400 nowait]星１回転
[star2 action=LayerNormalRotateModule angvel=200 nowait]星２回転
[star3 action=LayerNormalRotateModule angvel=600 nowait]星３回転

[star1 xpos=  -0:960 ypos=0:-720 time=1000 nowait]
[star2 xpos=-480:480 ypos=0:-720 time=1000 nowait]
[star3 xpos= 480:1440 ypos=0:-720 time=1000 nowait]
星を移動

[star1 hide]星１消去
[star2 hide]星２消去
[star3 hide]星３消去

[demodone name=envlayer]

[jump storage=s0001.ks]