*start|スタート

; Environment initialization process
[initscene]

[road normal]

KAGEX 表示／消去アクションのテストサンプルです

[ai standard showslide]
キャラクタ出現（スライド）

[ai hide showslide]
キャラクタ消去（スライド）

[ai standard showzoom]
キャラクタ出現（ズーム）

[ai hide showzoom]
キャラクタ消去（ズーム）

[ai posleft showslide nosync]
[newchar name=ai2 initname=ai posright showzoom nosync]
同時表示（nosync指定）

複合アクションのサンプルです

[ai sequence_test]
複数の連続アクションを単一のアクションとして実行できます

[ai sequence_test2]
例その２。別個に定義したアクションの組み合わせです

終了

[demodone name=action]

[jump storage=s0001.ks]