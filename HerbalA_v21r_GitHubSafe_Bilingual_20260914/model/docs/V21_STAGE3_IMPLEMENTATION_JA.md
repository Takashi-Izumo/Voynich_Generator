# HerbalA v21r Stage 3 — SLOT table builder 実装・監査報告

## 1. 目的

Stage 3では、v21r構造版 `SLOT` の生成器へ接続する前に、W2 exact-4用の確率表だけをouter-bifolium blindで構築・固定した。

この段階では**生成挙動を変更しない**。Stage 2 `SAFE_LEFT` は固定対照としてそのまま保持する。

## 2. 学習domain

W2表:

- `base_role == W2`
- `board == W2`
- exact glyph length = 4
- total stable physical width `W in {4,5,6,7,8}`
- 各outer foldの `complete_train_bifs` のみ

BODY H4共有表:

- `base_role == BODY`
- `board == BODY`
- exact glyph length = 4
- H4 physical width = 1
- 各outer foldの `complete_train_bifs` のみ

20 target bifoliaすべてについて、target bifoliumのtraining row混入は0件。

## 3. H2 table

H2はglyph identityそのものを予測する。

階層:

1. `H1`
2. `H1 + W`
3. `H1 + W + previous terminal T`
4. `H1 + W + T + row_phase`

alpha grid: `{2,4,8,16,32}`。

各outer training set内でleave-one-bifolium-out CVを行い、token log-loss最小のdepth/alphaを選択する。

選択結果:

| fold | H2 depth | alpha |
|---:|---:|---:|
| 0 | 3 | 8 |
| 1 | 3 | 8 |
| 2 | 3 | 4 |
| 3 | 3 | 4 |
| 4 | 2 | 4 |

したがって4/5 foldで `H1+W+T`、1/5 foldで `H1+W` が選択された。row phaseは正式選択されなかった。

外部176 W2 exact-4での診断lossは `1.82757 bit/H2`。

## 4. H3 table

H3は仕様通り

`P(H3 | H1, exact total width W)`

のみを使用する。

Wは4/5/6/7/8を完全に別カテゴリとして扱い、隣接幅の平滑共有は行わない。

alpha grid: `{2,4,8,16,32}`。

選択結果:

| fold | alpha |
|---:|---:|
| 0 | 8 |
| 1 | 8 |
| 2 | 8 |
| 3 | 4 |
| 4 | 8 |

外部176 W2 exact-4での診断lossは `2.41831 bit/H3`。

これは前段独立検定で得られた約2.41 bit/H3と整合する。

## 5. H4 table

H4はW2専用表を作らず、BODY exact-4の

`P_BODY(H4 | H3)`

を使用する。

- H4 physical width = 1のみ
- alpha = 2固定
- W2のH1/H2/W/T/row_phase/bTを条件へ入れない

外部176 W2 exact-4での診断lossは `1.36423 bit/H4`。

前段のBODY-shared独立検定 `1.3684 bit/H4` とほぼ一致する。

## 6. 平滑化

rootはtraining empirical countをstable-22対称priorへalphaで縮約する。

各child contextは、同じalphaで親分布へ再帰的に縮約する。

このため未知contextでも確率は常に正で、22 glyph上で総和1となる。

## 7. event counts

outer holdoutを一巡した合計:

- W2 exact-4: 176 events
- BODY exact-4 / H4 width1: 596 events

各foldのW2 train/test:

- fold0: 146 / 30
- fold1: 135 / 41
- fold2: 134 / 42
- fold3: 140 / 36
- fold4: 149 / 27

## 8. leakage / integrity audit

- target bifolium in training list: 0/20
- target W2 rows in training: 0
- target BODY-H4 rows in training: 0
- training event SHA-256をfold JSONへ固定
- validatorで再抽出hash一致
- observed context上のprobability normalization: PASS
- positive finite probabilities: PASS

## 9. Stage 2不変監査

Stage 3では `integrated_sampler_v21.py` / `run_model_v21.py` の生成経路を変更していない。

Stage 2 validator再実行:

- historical checks: 23/23
- splice events: 542
- changed: 162
- fallback: 5
- RIGHT off: 542/542
- support violations: 0
- invalid rows: 0
- packing: PASS

したがってSAFE_LEFTは固定対照のまま維持されている。

## 10. 生成器接続状態

`generator_connected = false`

Stage 3で追加したのは学習・ロード・検証コードとfold別table JSONのみ。

Stage 4で初めて `w2_slot_generator.py` を実装し、これらの表を候補列挙・scoreへ接続する。

## 11. 判定

**Stage 3 = PASS**。

次段階へ渡す固定事項:

- H2: fold-selected hierarchical W2-only table
- H3: `H1 × exact W(4..8)` table
- H4: BODY-shared `H3→H4`, alpha=2
- target leakage = 0
- SAFE_LEFT unchanged
