# v21r + PRETERM 検証結果

## 1. 親再現

`fold0 / A:2 / seed 91321 / SAFE_LEFT_BT_OFF` を再生成し、

- generated rows hash
- surface commits hash
- generation input hash

の3項目すべてがStage 4固定値と一致した。

## 2. 3-seed screen

fresh seeds `91601–91603` ×20 bifolia。

literal `PRETERM_R6` は低残幅BODYへの適用14 proposals、最終commit 8、変更0で実質no-op。

`PRETERM_QMAP9` は packing 60/60 PASS、support violation 0、invalid 0。terminal holdingは実測方向へ改善し、全体指標の最大悪化はtrigram約4.9%で10% stop rule内だったため20-seedへ進めた。

## 3. 20-seed validation

seeds `91601–91620` ×20 bifolia、親とPRETERMの各400 cases。

機械的不変量：

- packing: 400/400 PASS
- support violation: 0
- invalid: 0
- PRETERM proposals: 2226
- PRETERM final committed: 1268
- changed proposals: 139
- changed committed words: 81

### global judge

real-vs-generated absolute margin。低いほど良い。

| metric | parent | PRETERM | relative |
|---|---:|---:|---:|
| H2_RAW | 0.049831 | 0.049720 | -0.22% |
| bigram | 0.040984 | 0.041678 | +1.69% |
| ng | 0.039534 | 0.039904 | +0.94% |
| trigram | 0.049170 | 0.049402 | +0.47% |
| SPACE_RAW | 0.050305 | 0.050224 | -0.16% |
| route56 | 0.059412 | 0.060558 | +1.93% |
| bT_leaf_excess | 0.195075 | 0.194419 | -0.34% |
| glyph_depth | 0.025097 | 0.024545 | -2.20% |
| length_width | 0.048593 | 0.049279 | +1.41% |

全指標±2.2%以内。20葉paired比較で有意な悪化なし。

### targeted low-R BODY

実測target：`n/m/y=0.4659`, `l/r=0.4773`, `close=-0.0114`, avg glyph width `1.2633`。

| quantity | parent | PRETERM | observed |
|---|---:|---:|---:|
| low avg glyph width | 1.2725 | 1.2760 | 1.2633 |
| low n/m/y | 0.5191 | 0.4585 | 0.4659 |
| low l/r | 0.3649 | 0.3755 | 0.4773 |
| low close score | 0.1542 | 0.0830 | -0.0114 |

`n/m/y` target誤差は約86%縮小、close-score誤差は約43%縮小。`l/r`も改善するが未回収分が残る。

## 4. 判定

**PRETERM_QMAP9を v21r+PRETERM 候補として昇格。**

ただしこれは「約6で硬い物理スイッチが証明された」という意味ではない。実測5.75は推定容量座標で、runtimeではprevalence matchingによりR<=9へ対応させている。またterminal holdingは改善したが完全一致ではないため、追加チューニングはせずこの係数を固定する。
