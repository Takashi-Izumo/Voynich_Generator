# PUV 再現・再実行ガイド

## 1. 展開

このhandoff ZIPを `/mnt/data` 以下へ展開する。

親runtimeは:

`parent_runtime/EHC1_E1GLOBAL_FULL_20260911.zip`

に同梱している。

これを例えば:

`/mnt/data/_parent_ehc1/EHC1_E1GLOBAL_20260911`

となるよう展開する。

## 2. 現行PUVコード

`current_model/RMW1_BTI2_EHC2_DECOMP1_STAGE6_20260911/code/`

主ファイル:

- `e1_decomposed_u.py`
- `e1_decomposed_v.py`
- `e1_decomposed_uv.py`
- `worker_stage6_confirmation.py`
- `judge_stage6_confirmation.py`
- `stage6_env.py`

係数:

`current_model/.../parameters/SELECTED_ETA_BY_OUTER_FOLD.csv`

5foldすべて `eta_U=0.5, eta_V=0.5`。

## 3. 親path

`stage6_env.py` は環境変数 `EHC2_STAGE6_PARENT` を認識する。

例:

```bash
export EHC2_STAGE6_PARENT=/mnt/data/_parent_ehc1/EHC1_E1GLOBAL_20260911
```

親コード `code/entry_global_only.py` が存在することを確認する。

## 4. 現在の正本confirmation

runs:

- 91321
- 91322
- 91323
- 91324
- 91325

arms:

- BTI2_BASE
- A_LEGACY
- PUV

statistical unit:

- 20 bifolia
- 5 runsは葉内平均

既存結果を再審判するだけなら、現行Stage6 package内の保存済み出力を使う。

## 5. 注意

- RBS1は現行モデルに含めない。
- SEC1は実装しない。
- U/V係数をouter testを見て再調整しない。
- H1/H2へ新しい葉補正を直接追加しない。
- `OPEN_ISSUES_JA.md` の棄却済み仮説を先に確認する。
