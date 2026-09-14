# RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16

Formal promoted edition, 2026-09-12.

This self-contained model package formally integrates **W2 exact-L4 / K16 / legal same-width H2-only splice** into the parent model `PUV + BODY-R4 lambda=0.85 + adaptive leaf-excess`.

## Status

**PROMOTED**

It passed an independent 15-seed replication and the full 20-seed judgment, producing stable improvements in the standard bigram/ng/trigram metrics while leaving `SPACE_RAW`, route56, bT leaf-excess, and length/width unchanged.

## Normal execution

On first use, the two archives placed in the GitHub Release assets or `sources/` directory are SHA-256 verified and automatically extracted into `runtime/`. In the GitHub edition an external directory can also be specified through `VOYNICH_V21R_SOURCE_DIR`.

```bash
python code/run_model.py --fold 0 --bif A:2 --run 91321
```

All folds with five seeds:

```bash
python code/run_all_folds.py --runs 91321,91322,91323,91324,91325
```

## Integration audit

```bash
python code/validate_integration.py
python code/validate_integration.py --smoke
```

`--smoke` regenerates fold0 / A:2 / run91321 and compares three hashes against the verified experimental version.

## Key specification

- activation: W2, exact 4 glyphs only
- K=16, max draws=4096
- replace H2 only
- H1/H3+/terminal/exact length/physical width remain fixed
- legal parent bridge support required
- no known3 residual table
- dedicated SHA-256 RNG side-stream
- anchor fallback when there are 0 eligible candidates

See `docs/SPECIFICATION_EN.md` and `docs/VALIDATION_EN.md` for details.
