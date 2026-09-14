# v21r Stage 1 implementation and audit report

## Objective

Move v20r onto the common v21 sampler foundation while creating a behavior-preserving `V20_COMPAT` mode.

## Implementation

The logic of `integrated_sampler.py` was transferred unchanged into `integrated_sampler_v21.py`, with only the class names separated:

- `CalibratedPatchSampler` → `V21CalibratedPatchSampler`
- `PromotedW2H2L4K16Sampler` → `V20CompatSampler`

Backward-compatible aliases are retained.

`run_model_v21.py` uses the same configuration, RNG namespaces, fold construction, and leaf-excess alpha as v20r, replacing only the sampler with `V20CompatSampler`.

## Hash audit

Reference: `validation/REFERENCE_HASHES_5SEED.csv`

Five seeds × 20 bifolia = 100 cases were regenerated and three hashes compared.

| hash | matches |
|---|---:|
| generated_rows_sha256 | 100 / 100 |
| surface_commits_sha256 | 100 / 100 |
| generation_input_sha256 | 100 / 100 |
| **total** | **300 / 300** |

Conclusion: **PASS**.

## Components not changed in Stage 1

- BODY R4 lambda=0.85
- bT ACTIVE / leaf-excess
- W2 exact-L4 K16 sibling generation
- LEFT + RIGHT bridge support
- H2 same-width constraint
- SHA-256 side-stream namespaces
- parent RNG consumption
- semantic state

## Decision

No generation difference caused by the port to the common v21 foundation was detected.
Proceed to Stage 2 `SAFE_LEFT`.
