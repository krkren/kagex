*start|開始

; Environment initialization process
[initscene]

[road normal]

這是 KAGEX 顯示與隱藏動作的測試示例。

[ai standard showslide]
角色登場（滑動）

[ai hide showslide]
角色退場（滑動）

[ai standard showzoom]
角色登場（縮放）

[ai hide showzoom]
角色退場（縮放）

[ai posleft showslide nosync]
[newchar name=ai2 initname=ai posright showzoom nosync]
同時顯示（指定了 nosync）

這是複合動作的示例。

[ai sequence_test]
多個連續的動作可以作為一個動作來執行。

[ai sequence_test2]
例二：把分別定義的幾個動作組合起來。

結束

[demodone name=action]

[jump storage=s0001.ks]