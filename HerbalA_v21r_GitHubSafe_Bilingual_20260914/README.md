# HerbalA v21r — GitHub-safe package

This repository is the lightweight GitHub distribution of **HerbalA v21r Stage 4 — SLOT SCREEN**.
The scientific/model state is unchanged: Stage 4 stopped SLOT at the three-seed screen, and the active v21r candidate remains `SAFE_LEFT_BT_OFF`.

## Documentation languages

- English overview: [`README_EN.md`](README_EN.md)
- 日本語概要: [`README_JA.md`](README_JA.md)
- English GitHub packaging notes: [`GITHUB_SAFE_PACKAGING_EN.md`](GITHUB_SAFE_PACKAGING_EN.md)
- 日本語 GitHub packaging notes: [`GITHUB_SAFE_PACKAGING_JA.md`](GITHUB_SAFE_PACKAGING_JA.md)
- English upload guide: [`GITHUB_UPLOAD_GUIDE_EN.md`](GITHUB_UPLOAD_GUIDE_EN.md)
- 日本語 upload guide: [`GITHUB_UPLOAD_GUIDE_JA.md`](GITHUB_UPLOAD_GUIDE_JA.md)

Every Japanese Markdown document in this repository has a corresponding `_EN.md` companion. Numerical results, code identifiers, hashes, and filenames are preserved exactly across the translations.

## External runtime archives

The repository intentionally excludes two large runtime ZIP archives. Download them from the matching GitHub Release and either place them in `model/sources/` or point `VOYNICH_V21R_SOURCE_DIR` to their directory. Their SHA-256 hashes are fixed in `model/SOURCE_ARCHIVES.json` and are verified before extraction.

Required Release assets:

- `EHC1_E1GLOBAL_FULL_20260911.zip`
- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`

## Quick verification

```bash
python -m pip install -r requirements.txt
cd model
python code/validate_integration.py --smoke
python code/validate_v21_stage1.py
python code/validate_v21_stage2.py
python code/validate_v21_stage3.py
python code/validate_v21_stage4_synthetic.py
```

The GitHub-safe packaging changes only dependency discovery / validation plumbing and documentation. The generation logic and saved scientific reference state remain unchanged.
