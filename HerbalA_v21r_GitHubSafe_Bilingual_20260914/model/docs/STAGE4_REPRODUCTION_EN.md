# Stage 4 reproduction procedure

## 1. Runtime extraction

Each runner automatically extracts the two source ZIP archives from `model/sources/` into `model/runtime/`.

## 2. Static / synthetic validation

```bash
cd model
python code/validate_v21_stage1.py --smoke
python code/validate_v21_stage2.py --smoke
python code/validate_v21_stage3.py
python code/validate_v21_stage4_synthetic.py
```

## 3. SAFE_LEFT_BT_OFF

Single case:

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SAFE_LEFT_BT_OFF --output-root outputs/example
```

## 4. SLOT_BT_OFF

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SLOT_BT_OFF --output-root outputs/example
```

## 5. Three-seed screen

Each fold can be run independently.

```bash
for f in 0 1 2 3 4; do
  python code/run_stage4_modes.py --fold "$f" \
    --runs 91401,91402,91403 \
    --output-root outputs/stage4_screen &
done
wait
```

Judgment:

```bash
python validation/code/judge_stage4_slot.py \
  --root outputs/stage4_screen \
  --runs 91401,91402,91403 \
  --out validation/stage4/recomputed_screen
```

In the saved result, `SPACE_RAW` violated the screen stop condition, so SLOT validation for seeds 91404 and later should not be run as part of the formal Stage 4 protocol.
