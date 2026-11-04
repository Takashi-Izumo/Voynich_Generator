# Release notes — PARAH1-RUN32 — 2026-09-17

親 `HerbalA_v21r_PRETERM_SHORTBODY_H2GLOBAL_20260916` へ、外部保留対決で採用された paragraph-local continuous running H1 residual を追加しました。

## 追加

- `model/code/paragraph_h1_state.py`
- `model/code/paragraph_h1_sampler.py`
- `model/code/run_model_paragraph_h1.py`
- `model/code/build_paragraph_h1_baseline.py`
- `model/code/validate_paragraph_h1_running.py`
- `model/parameters/PARAGRAPH_H1_CONFIG.json`
- `model/parameters/PARAGRAPH_H1_BASELINE.json`
- `model/validation/paragraph_h1_running/`

## 固定事項

変更するのはBODY H1だけです。H2+、exact length、physical width、packing、rare glyph logic、route memory、PRETERM、SHORTBODY-H2-GLOBAL、parent RNGは固定しています。

H1 writeはparent wordのpacking/rare/route commit後にmaterializeします。

## self-test

seed 91601 ×20 bifolia：

- parent/no-op rows: 20/20一致
- parent/no-op commits: 20/20一致
- eligible commits: 495
- state-applied events: 381
- actual H1 changes: 12
- changed bifolia: 7/20
- packing: 20/20 PASS
- support violation: 0
- invalid: 0
- route state freeze: 20/20

## STOP

blind judgeは未実行です。
