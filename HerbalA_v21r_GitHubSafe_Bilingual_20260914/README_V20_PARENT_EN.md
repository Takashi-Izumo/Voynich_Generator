# HerbalA v20r — 2026-09-12

Official model: `RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16`

This ZIP is the formal release containing the **complete code, configuration, dependent source archives, 20-seed promotion-judgment results, and all results from the 200-set contest** required to rerun and audit v20r.

## Contents

- `model/`: the formal model package, including code, configuration, dependent source archives, integration-hash audit, and promotion validation.
- `validation/code/`: code for the final 20-seed judgment and aggregation.
- `validation/results/`: all final judgment tables for 20 leaves × 20 seeds, together with multiple-comparison and convergence tables.
- `contest_200/`: execution code for the 200-set contest, blind key, all scores, leaf/seed-level results, and decision record.
- `MANIFEST_SHA256.csv`: file sizes and SHA-256 hashes for every file included in the ZIP.

## v20r mechanism

Only for W2 words of exact length 4, the model builds a K=16 sibling pool and reselects H2 within legal support while preserving H1, H3 and later positions, the terminal, exact length, and physical width.

## 20-seed promotion results

Relative to the parent: bigram about -2.15%, ng about -2.34%, and trigram about -2.63%.
All three remain significant after Holm correction across the five REGRESSION metrics. `SPACE_RAW`, `route56`, `bT leaf-excess`, and `length-width` are effectively unchanged.

## 200-set contest

Fresh seeds 10 × 20 leaves = 200 sets. The combined judge selected real 96 times and synthetic 104 times; at the leaf level the result was 10/20 vs 10/20, i.e. chance level.

Note: very large archives of raw generated pages are not duplicated in this ZIP because of distribution size. The full result tables used by the judges, code, blind key, and dependent sources are included.
