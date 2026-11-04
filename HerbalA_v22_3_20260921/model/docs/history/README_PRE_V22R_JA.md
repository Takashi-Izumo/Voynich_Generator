# HerbalA v21r + PRETERM + SHORTBODY-H2-GLOBAL + PARAH1-RUN32

2026-09-17 実装候補です。

親モデル：

`HerbalA_v21r_PRETERM_SHORTBODY_H2GLOBAL_20260916`

追加したのは、BODY H1に対する **paragraph-local continuous running residual** だけです。

## 新規機構

- paragraph開始でneutral reset
- 完了済みprior eligible linesのみ参照
- exact length + previous T + leaf-known-3 baselineからのH1残差を蓄積
- shrinkage `lambda=32`
- decayなし
- BODY、2+ glyph、非paragraph-final、非segment-finalだけ対象

H1介入は親wordのpacking / rare / route commit後にmaterializeするため、H2+、語長、物理幅、route memory、parent RNGは固定されます。

## 審判前self-test

seed 91601 ×20 bifolia：

- parent vs PARAH1_NOOP rows hash: 20/20一致
- parent vs PARAH1_NOOP commits hash: 20/20一致
- RUN32 eligible: 495
- RUN32 applied: 381
- H1 changes: 12
- changed bifolia: 7/20
- packing: 20/20 PASS
- support violations: 0
- invalid: 0
- route state frozen: 20/20

**blind judgeはまだ実行していません。**

## 実行

```bash
cd model
python code/run_model_paragraph_h1.py \
  --fold 0 --bif A:2 --run 91601 \
  --mode PARAH1_RUN \
  --output-root outputs/test
```

no-op：

```bash
python code/run_model_paragraph_h1.py \
  --fold 0 --bif A:2 --run 91601 \
  --mode PARAH1_NOOP \
  --output-root outputs/test
```

親再現：

```bash
python code/run_model_paragraph_h1.py \
  --fold 0 --bif A:2 --run 91601 \
  --mode PARENT \
  --output-root outputs/test
```

保存self-testの検証：

```bash
python code/validate_paragraph_h1_running.py
```

詳細：

- `model/docs/PARAGRAPH_H1_RUNNING_IMPLEMENTATION_JA.md`
- `model/docs/PARAGRAPH_H1_PREJUDGE_VALIDATION_JA.md`
- `model/parameters/PARAGRAPH_H1_CONFIG.json`
- `model/validation/paragraph_h1_running/`
