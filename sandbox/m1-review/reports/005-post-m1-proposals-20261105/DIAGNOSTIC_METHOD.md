# 追加診断の方法と範囲

新たなモデルfit・生成・審判変更は行っていない。既存のM1本比較結果から読み取りで集計した探索的な設計診断。

入力root: `/workspace/voynich-results/m1-full-comparison-20261105/`。事前計画hashは`6b185bf56e043efa0180753f63cc15206c7d1b59238a87d4cc85272693a2c4a4`。

## 可視PF語の記述量

`anonymous/ARM/inputs.jsonl`、別の正解keyを使い、真正/生成の候補を識別。凍結`judges.v03.observations.word_events()`から`atom == PARA_END`を選ぶ。主に`pline > 1`を使用する。今回、観測されたALLとMULTILINEのPF記述量は一致した。

- 長さは凍結glyph tokenizerの長さ。複合glyphは1、rare6字は除去、mは保持。
- 可視glyph換算幅は`sum(judges.schema.WIDTH[g])`。生成器の記録物理幅や元の容量と同一視しない。
- 各候補面内でPF語の平均/比率を計算し、seedをbifolium内で平均、その後bifoliumを等重みで平均。
- 長さ区分は1〜3 / 4〜6 / 7+。幅閾値は7+ / 9+。末字はn/m/y/l/rを記録。
- 真正面はseedごとに同じ語列が再登場するので独立標本として数えない。可視PFは18 target面、29箇所。生成側は各arm180比較可能面に290個のPF観測を持つ。

## 個別channel

`evaluation/predictions/ARM/channels.jsonl`のCAL内の`ATOM.PARA_END/`各channelを使用。正解候補scoreが生成候補より大きければ1、小さければ0、差が1e-12以下なら0.5。どちらかNAは除外。各bifolium内でseed平均し、bifolium等重みで平均した。channelは重複し、多重比較や能力検証は行っていない。

## 候補bank

BASEの`pf_candidates.csv.gz`を、planのscope ledgerにある`generator_pf and judge_observed`の29箇所へ対応させた。各eventの初期候補0・1の可視長さを計算。

- `first_two_pool_visible_7plus`: 各eventで2候補の7+率を平均してから、面・seed・bifoliumを等重み集計。
- `first_two_any_visible_7plus`: 各eventで初期2候補の少なくとも一方が7+か。
- `selected_visible_7plus`: 実際の採用候補。救済採用を含む。
- stable長の7+も別記録した。今回の採用候補では可視7+と一致した。

真正のその語を見て候補を選び直すことはしていない。4.49%対4.72%という集計は、選択効果を完全に分離した推定ではない。candidate bankにはbranch採番・side RNGの依存があり、条件付き救済候補もある。生成段階の不足を調べる根拠として使う。
