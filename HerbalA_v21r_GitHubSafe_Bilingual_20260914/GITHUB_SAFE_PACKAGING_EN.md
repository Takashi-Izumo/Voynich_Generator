# v21r GitHub-safe packaging

## Purpose

Reduce the Stage 4 model, parameters, and saved validation results to a size suitable for a GitHub repository while preserving reproducibility of the generated output.

## What changed

In the GitHub edition, only the following two archives, which account for about 261 MB, were removed from the repository itself:

- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`
- `EHC1_E1GLOBAL_FULL_20260911.zip`

They are distributed as GitHub Release assets. Their contents, filenames, and SHA-256 hashes are identical to those in the original Stage 4 package.

`model/code/runtime_bootstrap.py` was modified to search for the same archives in the following order:

1. `VOYNICH_V21R_SOURCE_DIR`
2. `model/sources/`
3. repository-root `release_assets/`
4. repository-root `external_sources/`

Before extraction, every archive is checked against the SHA-256 values in `model/SOURCE_ARCHIVES.json`. Execution is refused if a hash does not match.

## What did not change

- `integrated_sampler.py`
- `integrated_sampler_v21.py`
- `run_model.py`
- `run_model_v21.py`
- SLOT tables / model parameters
- Stage 1–4 reference hashes
- saved judge results
- model candidate / stop decision

For the Stage 1/2 smoke validators, only the hard-coded temporary `/mnt/data` location was replaced by the operating system's standard temporary directory. The generation logic was not changed.

## Note on historical scripts

The repository-root `validation/code/` and `contest_200/code/` directories contain historical scripts that record the original working-environment paths under `/mnt/data/...`. To preserve provenance of the saved results, these scripts were not modified. For current reproduction, use `model/code/` and `model/validation/code/`.

## Integrity criteria

The GitHub edition is considered valid only if all of the following hold:

1. SHA-256 matches for both Release assets.
2. Python compile check PASS.
3. `validate_integration.py --smoke` exactly matches all three saved hashes.
4. Stage 1/2 static validators PASS.
5. Stage 3 validator passes 5/5 folds.
6. Stage 4 synthetic validation PASS.

Execution results are saved in `GITHUB_SAFE_AUDIT.json`.
