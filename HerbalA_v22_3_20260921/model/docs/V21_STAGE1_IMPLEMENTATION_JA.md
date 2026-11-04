# v21r Stage 1 実装・監査報告

## 目的

v20rをv21共通sampler基盤へ移し、挙動を変えない `V20_COMPAT` を作る。

## 実装

`integrated_sampler.py` のロジックをそのまま `integrated_sampler_v21.py` へ移し、以下のクラス名だけを分離した。

- `CalibratedPatchSampler` → `V21CalibratedPatchSampler`
- `PromotedW2H2L4K16Sampler` → `V20CompatSampler`

後方互換aliasも保持している。

`run_model_v21.py` はv20rと同じ設定・同じRNG namespace・同じfold構築・同じleaf-excess alphaを使い、samplerだけ `V20CompatSampler` に差し替える。

## hash audit

参照: `validation/REFERENCE_HASHES_5SEED.csv`

5 seed × 20 bifolia = 100ケースについて再生成し、3 hashを比較した。

| hash | 一致 |
|---|---:|
| generated_rows_sha256 | 100 / 100 |
| surface_commits_sha256 | 100 / 100 |
| generation_input_sha256 | 100 / 100 |
| **合計** | **300 / 300** |

結論: **PASS**。

## Stage 1で変更していないもの

- BODY R4 lambda=0.85
- bT ACTIVE / leaf-excess
- W2 exact-L4 K16 sibling generation
- LEFT + RIGHT bridge support
- H2 same-width制約
- SHA-256 side-stream namespaces
- parent RNG消費
- semantic state

## 判定

v21共通基盤への移植による生成差は検出されない。
Stage 2 `SAFE_LEFT` へ進行可能。
