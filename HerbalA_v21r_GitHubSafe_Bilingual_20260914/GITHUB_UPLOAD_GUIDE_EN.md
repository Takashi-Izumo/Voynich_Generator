# GitHub upload guide

## Repository

Extract `HerbalA_v21r_GitHubSafe_20260914.zip` and push its contents as a normal Git repository.

```bash
git init
git add .
git commit -m "Publish HerbalA v21r GitHub-safe package"
git branch -M main
git remote add origin <YOUR_REPOSITORY_URL>
git push -u origin main
```

`model/sources/*.zip` and `model/runtime/` are already covered by `.gitignore`, so the large runtime files are not accidentally committed.

## GitHub Release assets

Attach the following two files as assets to the same release/tag:

- `EHC1_E1GLOBAL_FULL_20260911.zip`
- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`

It is also recommended to attach `SHA256SUMS.txt`.

## After cloning

Download the two Release assets into the same directory and use either of the following approaches.

```bash
export VOYNICH_V21R_SOURCE_DIR=/path/to/assets
```

Alternatively, place both files in `model/sources/`.

Then run:

```bash
python -m pip install -r requirements.txt
cd model
python code/validate_integration.py --smoke
```

If `smoke_hash_identity: PASS` is reported, the generated output hashes match the original Stage 4 reference.
