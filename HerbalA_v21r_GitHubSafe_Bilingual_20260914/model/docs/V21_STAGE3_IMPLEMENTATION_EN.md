# HerbalA v21r Stage 3 — SLOT table builder implementation and audit report

## 1. Objective

Before connecting the v21r structural `SLOT` model to generation, Stage 3 constructs and freezes only the probability tables for W2 exact-4 under outer-bifolium blindness.

**Generation behavior is not changed at this stage.** The Stage 2 `SAFE_LEFT` path remains unchanged as the fixed control.

## 2. Training domain

W2 tables:

- `base_role == W2`
- `board == W2`
- exact glyph length = 4
- total stable physical width `W in {4,5,6,7,8}`
- only `complete_train_bifs` from each outer fold

Shared BODY H4 table:

- `base_role == BODY`
- `board == BODY`
- exact glyph length = 4
- H4 physical width = 1
- only `complete_train_bifs` from each outer fold

Across all 20 target bifolia, the number of target-bifolium training rows is 0.

## 3. H2 table

H2 predicts glyph identity directly.

Hierarchy:

1. `H1`
2. `H1 + W`
3. `H1 + W + previous terminal T`
4. `H1 + W + T + row_phase`

Alpha grid: `{2,4,8,16,32}`.

Within each outer training set, leave-one-bifolium-out CV selects the depth/alpha combination minimizing token log-loss.

Selected values:

| fold | H2 depth | alpha |
|---:|---:|---:|
| 0 | 3 | 8 |
| 1 | 3 | 8 |
| 2 | 3 | 4 |
| 3 | 3 | 4 |
| 4 | 2 | 4 |

Thus `H1+W+T` was selected in 4/5 folds and `H1+W` in 1/5. Row phase was never formally selected.

Diagnostic loss on the 176 outer W2 exact-4 events is `1.82757 bit/H2`.

## 4. H3 table

As specified, H3 uses only

`P(H3 | H1, exact total width W)`.

Widths 4/5/6/7/8 are treated as completely separate categories with no smoothing across neighboring widths.

Alpha grid: `{2,4,8,16,32}`.

Selected values:

| fold | alpha |
|---:|---:|
| 0 | 8 |
| 1 | 8 |
| 2 | 8 |
| 3 | 4 |
| 4 | 8 |

Diagnostic loss on the 176 outer W2 exact-4 events is `2.41831 bit/H3`.

This agrees with the approximately 2.41 bit/H3 obtained in the preceding independent test.

## 5. H4 table

No W2-specific H4 table is created. Instead, the BODY exact-4 table

`P_BODY(H4 | H3)`

is used.

- H4 physical width = 1 only
- alpha fixed at 2
- W2 H1/H2/W/T/row_phase/bT are not included as conditioning variables

Diagnostic loss on the 176 outer W2 exact-4 events is `1.36423 bit/H4`.

This nearly matches the earlier BODY-shared independent result of `1.3684 bit/H4`.

## 6. Smoothing

At the root, training empirical counts are shrunk toward a symmetric stable-22 prior using alpha.

Each child context is recursively shrunk toward its parent distribution using the same alpha.

Therefore probabilities remain positive for unseen contexts and sum to 1 over the 22 glyphs.

## 7. Event counts

Totals over one full pass of the outer holdout:

- W2 exact-4: 176 events
- BODY exact-4 / H4 width1: 596 events

W2 train/test counts by fold:

- fold0: 146 / 30
- fold1: 135 / 41
- fold2: 134 / 42
- fold3: 140 / 36
- fold4: 149 / 27

## 8. Leakage / integrity audit

- target bifolium in training list: 0/20
- target W2 rows in training: 0
- target BODY-H4 rows in training: 0
- training-event SHA-256 fixed in each fold JSON
- re-extracted hashes match under the validator
- probability normalization on observed contexts: PASS
- positive finite probabilities: PASS

## 9. Stage 2 invariance audit

Stage 3 does not change the generation paths in `integrated_sampler_v21.py` or `run_model_v21.py`.

Stage 2 validator rerun:

- historical checks: 23/23
- splice events: 542
- changed: 162
- fallback: 5
- RIGHT off: 542/542
- support violations: 0
- invalid rows: 0
- packing: PASS

Thus SAFE_LEFT remains unchanged as the fixed control.

## 10. Generator connection state

`generator_connected = false`

Stage 3 adds only training, loading, validation code, and fold-specific table JSON files.

Stage 4 is the first stage to implement `w2_slot_generator.py` and connect these tables to candidate enumeration and scoring.

## 11. Decision

**Stage 3 = PASS**.

Fixed items passed to the next stage:

- H2: fold-selected hierarchical W2-only table
- H3: `H1 × exact W(4..8)` table
- H4: BODY-shared `H3→H4`, alpha=2
- target leakage = 0
- SAFE_LEFT unchanged
