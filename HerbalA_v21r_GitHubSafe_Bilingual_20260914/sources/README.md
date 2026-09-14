# External source archives

The two large runtime archives are intentionally **not tracked in the GitHub repository**.
They are release assets and their exact SHA-256 values are declared in `../SOURCE_ARCHIVES.json`.

Required files:

- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`
- `EHC1_E1GLOBAL_FULL_20260911.zip`

Use any one of these layouts:

1. Put both files in this directory (`model/sources/`).
2. Put both files in repository-level `release_assets/`.
3. Put both files anywhere and set `VOYNICH_V21R_SOURCE_DIR=/path/to/directory`.

Every archive is SHA-256 verified before first extraction. A mismatching archive is rejected.
`model/runtime/` is generated locally and should not be committed.
