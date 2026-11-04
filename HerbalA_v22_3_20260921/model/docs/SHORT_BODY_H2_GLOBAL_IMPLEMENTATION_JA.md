# v21r+PRETERM — short BODY H2 global化

## 目的

blind bigram残差分解で、残差が5/6-route本体ではなく **4 glyph以下のBODY語頭 H1→H2** に集中した。
別LOBOでは、同葉known-3はH1 marginalには予測力を持つ一方、`P(H2|H1)` には安定した予測力を持たなかった。

そのため本版では、

- H1の葉known-3情報は保持
- 短BODY (`len=2..4`) の H2|H1 だけ、target-leaf known-3 residualをOFF
- Pure Herbal Aの外部学習残差は保持

とする。

## 実装上の切り分け

親EHCテーブルのH2 gainは、概念的に

`base P0 -> external Pure-A residual -> target-leaf known-3 residual`

の順で作られる。

本版では最後の **target-leaf known-3 residualだけ** を取り除く。したがって「H2を完全一様化」「葉情報を全部OFF」ではない。

## 不変量

介入時も以下を固定する。

- role = BODY / board = BODY
- 非LF / non-END
- exact glyph length
- H1
- H3以降
- H2 glyph physical width
- total physical word width
- route / BODY-R4 score
- bT terminal calibration
- PRETERM QMAP9
- parent RNG stream
- semantic state

H2候補選択はparent conditionalとexternal-only conditionalの最大結合で行う。

## len=2

len=2ではH2がterminalでもあるため、既存PRETERM terminal tiltをparent/targetの双方へ同じように掛けて保持する。

## RNG

専用namespace:

`V21_SHORT_BODY_H2_EXTERNAL_ONLY_V1`

親RNGを消費しない。

## 審判

このパッケージではblind judgeはまだ実行しない。状態は `IMPLEMENTED_PREJUDGE_NOT_JUDGED`。
