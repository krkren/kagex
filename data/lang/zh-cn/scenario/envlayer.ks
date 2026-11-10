*start|开始

[initscene]

[road]
[ai uniform center]
这是世界扩展“环境图层”的示例，可以用来制作切入画面之类的演出。

[newlay name=star1 file=star  xpos=0 ypos=0 show]显示星星1
[newlay name=star2 file=star xpos=-480 ypos=0 show]显示星星2
[newlay name=star3 file=star xpos=480 ypos=0 show]显示星星3
[star1 action=LayerNormalRotateModule angvel=400 nowait]旋转星星1
[star2 action=LayerNormalRotateModule angvel=200 nowait]旋转星星2
[star3 action=LayerNormalRotateModule angvel=600 nowait]旋转星星3

[star1 xpos=  -0:960 ypos=0:-720 time=1000 nowait]
[star2 xpos=-480:480 ypos=0:-720 time=1000 nowait]
[star3 xpos= 480:1440 ypos=0:-720 time=1000 nowait]
移动星星

[star1 hide]清除星星1
[star2 hide]清除星星2
[star3 hide]清除星星3

[demodone name=envlayer]

[jump storage=s0001.ks]