# Stage 4 reproduction procedure for the GitHub edition

## 1. Obtain the Release assets

Download the following two files from the matching GitHub Release:

- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`
- `EHC1_E1GLOBAL_FULL_20260911.zip`

Either place them in `model/sources/`, or store them in any directory and set the environment variable:

```bash
export VOYNICH_V21R_SOURCE_DIR=/path/to/v21r-release-assets
```

Windows PowerShell:

```powershell
$env:VOYNICH_V21R_SOURCE_DIR = "C:\path\to\v21r-release-assets"
```

They are extracted into `model/runtime/` only on first use. Each archive is SHA-256 verified before extraction.

## 2. Integrity smoke test

```bash
cd model
python code/validate_integration.py --smoke
```

Expected result: `smoke_hash_identity = PASS`.

## 3. Stage validators

```bash
python code/validate_v21_stage1.py
python code/validate_v21_stage2.py
python code/validate_v21_stage3.py
python code/validate_v21_stage4_synthetic.py
```

## 4. Stage 4 generation

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SAFE_LEFT_BT_OFF --output-root outputs/example
```

To reproduce SLOT:

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SLOT_BT_OFF --output-root outputs/example
```

In the saved Stage 4 result, SLOT was stopped after the three-seed screen by the `SPACE_RAW` stop rule, and the formal candidate therefore remains `SAFE_LEFT_BT_OFF`.
