# Stage 4 再実行手順

## 1. runtime展開

各runnerは `model/sources/` の2つのsource ZIPを `model/runtime/` へ自動展開する。

## 2. static / synthetic

```bash
cd model
python code/validate_v21_stage1.py --smoke
python code/validate_v21_stage2.py --smoke
python code/validate_v21_stage3.py
python code/validate_v21_stage4_synthetic.py
```

## 3. SAFE_LEFT_BT_OFF

単例：

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SAFE_LEFT_BT_OFF --output-root outputs/example
```

## 4. SLOT_BT_OFF

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SLOT_BT_OFF --output-root outputs/example
```

## 5. 3-seed screen

各foldを独立実行できる。

```bash
for f in 0 1 2 3 4; do
  python code/run_stage4_modes.py --fold "$f" \
    --runs 91401,91402,91403 \
    --output-root outputs/stage4_screen &
done
wait
```

審判：

```bash
python validation/code/judge_stage4_slot.py \
  --root outputs/stage4_screen \
  --runs 91401,91402,91403 \
  --out validation/stage4/recomputed_screen
```

今回の保存結果ではSPACE_RAWがscreen stop条件を破ったため、91404以降のSLOT validationは実行しない。
