*start|开始

; Environment initialization process
[initscene]

[road normal]

这是 KAGEX 显示与隐藏动作的测试示例。

[ai standard showslide]
角色登场（滑动）

[ai hide showslide]
角色退场（滑动）

[ai standard showzoom]
角色登场（缩放）

[ai hide showzoom]
角色退场（缩放）

[ai posleft showslide nosync]
[newchar name=ai2 initname=ai posright showzoom nosync]
同时显示（指定了 nosync）

这是复合动作的示例。

[ai sequence_test]
多个连续的动作可以作为一个动作来执行。

[ai sequence_test2]
例二：把分别定义的几个动作组合起来。

结束

[demodone name=action]

[jump storage=s0001.ks]