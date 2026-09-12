# RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16

2026-09-12 正式昇格版。

親モデル `PUV + BODY-R4 lambda=0.85 + adaptive leaf-excess` に、**W2 exact-L4 / K16 / legal same-width H2-only splice** を正式統合した自己完結パッケージです。

## 状態

**PROMOTED**

独立15seed再現と全20seed審判を通過し、標準 bigram/ng/trigram を安定改善。SPACE_RAW、route56、bT leaf-excess、length/width は不変です。

## 通常実行

初回のみ `sources/` の2 archiveを `runtime/` へ自動展開します。

```bash
python code/run_model.py --fold 0 --bif A:2 --run 91321
```

5seed全fold:

```bash
python code/run_all_folds.py --runs 91321,91322,91323,91324,91325
```

## 統合監査

```bash
python code/validate_integration.py
python code/validate_integration.py --smoke
```

`--smoke` は fold0 / A:2 / run91321 を再生成し、確認済み実験版と3hashを照合します。

## 重要仕様

- 発火: W2、exact 4 glyphのみ
- K=16、max draws=4096
- H2だけ置換
- H1/H3+/terminal/exact length/physical widthは固定
- legal parent bridge support必須
- known3 residual tableなし
- dedicated SHA-256 RNG side-stream
- 0 eligibleならanchor fallback

詳細は `docs/SPECIFICATION_JA.md` と `docs/VALIDATION_JA.md` を参照してください。
