# RBS1_STRICT 実装・監査報告

## 判定

- 実装: **PASS**
- RBS1 OFF anchor: **PASS**
- seed 91293 / 40頁機械監査: **PASS**
- H1 teacher-forcing identity: **PASS**
- 性能昇格: **未判定**（debug seedは選抜に使用しない）

## 実装

6+ glyphかつbt-enabledのbank選択で、元softmax draw `j0` の後に決定論的Pareto rescueを行う。
救済候補は `route_score >= before`, `bt_active >= before`, `bt_profile > before` をすべて満たすものだけ。
候補が無ければ元選択を保持。新しい乱数drawは追加しない。

実際のPUV生成器では候補選択が `PatchSampler` に複製されているため、RBS1処理はそのsoftmax直後へ実装した。`MapConfig`には `rbs1=False` のtoggleだけを追加した。

## OFF anchor

既存Stage5 PUV（A:2, run 91311）に対しRBS1 OFFで、

- generated rows SHA: 完全一致
- RNG end: 完全一致
- route final state: 完全一致
- surface commits SHA: 完全一致

## seed 91293 40頁機械監査

- PUV 20頁 + PUV-RBS1 20頁
- exact packing: 40/40
- retries: 0
- support violation: 0
- invalid row: 0
- max normalization error: 8.882e-16
- max END error: 0.000e+00
- U/V table cache key: 20/20完全一致
- learning object: 20/20完全一致

RBS1 request:

- enabled bank requests: 2697
- 6+ eligible: 253
- rescue実行: 17
- final pageへcommit: 17/17
- 変更頁: 8/20

17件の救済すべてで、

- 6+ glyphのみ: PASS
- 5 glyph以下の直接変更: 0
- route score低下: 0
- bT active低下: 0
- bT profileは必ず上昇: PASS
- 追加RNG draw: 0
- rescue時の平均route score差: 0.000000
- rescue時の平均bT profile上昇: 0.482602

## H1 teacher-forcing

Stage5凍結PUVとのH1確率を全4,790 eventで照合。
最大絶対誤差は 1.110e-16。したがってRBS1はH1確率系を変更していない。

## debug seedの記述診断

これは採用判定には使わない。

| metric          |   PUV_abs |   RBS1_abs |   improvement |   change_pct |   leaves_improved |     p_two |
|:----------------|----------:|-----------:|--------------:|-------------:|------------------:|----------:|
| SPACE_RAW       | 0.0557409 |  0.0512809 |   0.00445996  |     -8.00123 |                 6 | 0.203125  |
| H2_RAW          | 0.0418294 |  0.0482171 |  -0.0063877   |     15.2709  |                 2 | 0.0703125 |
| route56         | 0.0610255 |  0.0691579 |  -0.00813245  |     13.3263  |                 3 | 0.0625    |
| bT_LL           | 0.439255  |  0.468677  |  -0.0294217   |      6.69809 |                 2 | 0.101562  |
| bT_leaf_excess  | 0.2126    |  0.204742  |   0.00785828  |     -3.69627 |                 4 | 0.648438  |
| bT_active       | 0.10537   |  0.113647  |  -0.00827779  |      7.85596 |                 2 | 0.21875   |
| bT_presence_log | 0.564603  |  0.594786  |  -0.0301826   |      5.3458  |                 2 | 0.390625  |
| ng              | 0.0416138 |  0.0410026 |   0.000611253 |     -1.46887 |                 3 | 0.945312  |
| bigram          | 0.0314575 |  0.0335376 |  -0.00208007  |      6.6123  |                 4 | 0.804688  |
| trigram         | 0.0533702 |  0.0494002 |   0.00397007  |     -7.43873 |                 5 | 0.453125  |

### 読み方

狙った `bT_leaf_excess` はこのseedでは改善し、SPACE_RAWも改善した。一方、route56とH2_RAWは+10%を超える悪化を示した。
RBS1の局所制約ではroute scoreを一切落としていないため、この悪化は救済語の末尾・route stateが次語以降へ伝播した**二次的な軌跡効果**と解釈される。

したがって、RBS1_STRICTは**機械実装としては合格**だが、このdebug runだけで昇格させてはいけない。次に進む場合は未使用 `91314–91316` のStage5R repair screeningで、元の回帰guardをそのまま適用する必要がある。
