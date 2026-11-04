# HerbalA-v22.3 Stage 3D Candidate

親は正式stable `HerbalA-v22.2`。このパッケージはStage 3D実装候補であり、まだ正式なv22.3ではありません。

## 実装

- `L<=3` → normal middle-LF terminal selector
- `L>=4` → F1 terminal selector + normal middle-LF `P(l)` inheritance
- STOP/CONTINUE → 親v22.2のまま
- y bias / n bias / S_LF / post-hoc terminal rewrite → OFF

strict gateは保存metadataから再構成した88 terminal events / 20 complete bifoliaです。

## 実行

static/logical validation:

```bash
python validate_v22_3_stage3d.py
```

live generation runner（Stage 3E以降で使用）:

```bash
python run_v22_3_stage3d.py --fold 0 --bif A:2 --run 91701
```

## 現在状態

`STAGE3D_IMPLEMENTED / STATIC+LOGICAL 21/21 PASS / LIVE NOT RUN`

正式昇格はしません。次はStage 3Eです。

詳細: `model/docs/V22_3_STAGE3D_IMPLEMENTATION_JA.md`
