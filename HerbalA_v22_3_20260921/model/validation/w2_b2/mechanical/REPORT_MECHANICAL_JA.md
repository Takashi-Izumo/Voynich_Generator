# v22r W2 H1→H2 B2 最小実装 — 機械監査

## 判定

**MECHANICAL PASS。まだv22r正式昇格はしていない。blind審判も未実行。**

実装は strict W2 のうち段落中間行・non-LF、長さ3–5に限定し、H2だけを B2 law（W2POS維持・external OFF・known-3 τ=128）へ最大結合で弱く移す。長さ2はH2=terminalなので除外、長さ6+は予測感度で改善しなかったため除外した。

## 全20葉機械監査

|項目|結果|
|---|---:|
|葉|20|
|適用request|130|
|実変更request|6 (4.62%)|
|committed変更|6|
|support violation|0|
|invalid row|0|
|terminal mismatch|0|
|segment retry変化葉|0|
|平均types差|+0.000|
|平均hapax差|-0.050|

全20葉で token数、tokenwise語長、tokenwise物理幅、packing trace が親と一致。H1/H3+/terminal/H2物理幅も全適用requestで固定。parent RNG と precommit semantic state は不変。NO-OPは保存済み正式監査では各5 fold代表で親hash完全一致。さらに途中の全葉走査では実行上限に達するまで19/20葉で親hash完全一致を確認した。NO-OPはsuper()の出力を無変更で返す実装である。

## 変更が発生した6語

| bif   | page   | locus   | b2_h2_anchor   | b2_h2_selected   |   b2_h2_anchor_len |
|:------|:-------|:--------|:---------------|:-----------------|-------------------:|
| A:2   | f7v    | f7v.2   | dar            | dor              |                  3 |
| F:2   | f47v   | f47v.11 | choiin         | chaiin           |                  5 |
| D:4   | f29v   | f29v.8  | otod           | ochod            |                  4 |
| G:1   | f49v   | f49v.40 | shocthy        | shecthy          |                  4 |
| B:2   | f15v   | f15v.10 | otchor         | okchor           |                  5 |
| C:4   | f21v   | f21v.7  | daiin          | doiin            |                  5 |

## 連鎖監査

変更のあった6葉を親/B2で再生成した結果、各葉とも surface差は変更語1語だけ。terminal sequence、head sequence、SPACE boundary sequence、route final state、segment retry はすべて親と一致した。

|   fold | bif   | page   |   surface_diff_tokens | terminal_sequence_equal   | head_sequence_equal   | space_boundary_sequence_equal   | route_final_equal   | surface_commit_hash_equal   | segment_retries_equal   |   first_diff_index |   last_diff_index |
|-------:|:------|:-------|----------------------:|:--------------------------|:----------------------|:--------------------------------|:--------------------|:----------------------------|:------------------------|-------------------:|------------------:|
|      0 | A:2   | f7v    |                     1 | True                      | True                  | True                            | True                | False                       | True                    |                  9 |                 9 |
|      0 | F:2   | f47v   |                     1 | True                      | True                  | True                            | True                | False                       | True                    |                 56 |                56 |
|      2 | D:4   | f29v   |                     1 | True                      | True                  | True                            | True                | False                       | True                    |                 58 |                58 |
|      2 | G:1   | f49v   |                     1 | True                      | True                  | True                            | True                | False                       | True                    |                100 |               100 |
|      4 | B:2   | f15v   |                     1 | True                      | True                  | True                            | True                | False                       | True                    |                 50 |                50 |
|      4 | C:4   | f21v   |                     1 | True                      | True                  | True                            | True                | False                       | True                    |                 47 |                47 |

## 留保

長さ3–5へのscope縮小は機械安全性と既存感度分析に基づく engineering refinement であり、新しい独立した予測証拠としては数えない。したがって次段階では、このscopeを凍結したまま副作用指標を確認し、その後にのみfresh blindへ進む。