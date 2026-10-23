*start|Start

[initscene]

[road]
[ai uniform center]
This is a sample of the World Extension's "Environment Layer". It can be applied to staging effects such as cut-ins.

[newlay name=star1 file=star  xpos=0 ypos=0 show]Show Star 1
[newlay name=star2 file=star xpos=-480 ypos=0 show]Show Star 2
[newlay name=star3 file=star xpos=480 ypos=0 show]Show Star 3
[star1 action=LayerNormalRotateModule angvel=400 nowait]Rotate Star 1
[star2 action=LayerNormalRotateModule angvel=200 nowait]Rotate Star 2
[star3 action=LayerNormalRotateModule angvel=600 nowait]Rotate Star 3

[star1 xpos=  -0:960 ypos=0:-720 time=1000 nowait]
[star2 xpos=-480:480 ypos=0:-720 time=1000 nowait]
[star3 xpos= 480:1440 ypos=0:-720 time=1000 nowait]
Move stars

[star1 hide]Clear Star 1
[star2 hide]Clear Star 2
[star3 hide]Clear Star 3

[demodone name=envlayer]

[jump storage=s0001.ks]