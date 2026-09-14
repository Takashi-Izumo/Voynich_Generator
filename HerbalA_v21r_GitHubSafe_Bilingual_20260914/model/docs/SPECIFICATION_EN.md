# Formal integration specification

## Model ID

`RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16`

## Parent

- PUV U/V decomposition
- BODY non-prefix R4 coefficient: `0.85`
- bT leaf-excess: leaf-wise adaptive alpha selected from `{64,128,256}` using the frozen target-blind selection table

## New formal component

Only for **exact 4-glyph W2 words**, reselect H2 from the anchor selected by the parent selector.

1. Let the parent model select the W2 anchor normally.
2. Collect sibling proposals using a request-local SHA-256 side-stream RNG.
3. Reject a sibling unless it has the same `H1 / exact length / stable physical width` as the anchor.
4. Use K=16 and at most 4096 draws. Preserve multiplicity as proposal probability; do not deduplicate.
5. An H2 candidate must additionally have the same glyph width as the anchor H2, and both `H1-H2-H3` and `H2-H3-H4` must have positive support under the parent proposal support.
6. Select uniformly over eligible sibling multiplicity.
7. In the final word, replace **H2 only**. H1, H3 and later positions, terminal, exact length, and physical width must match the anchor exactly.
8. If there are no eligible candidates, fall back to the anchor.

The model does not use a known3 residual table, W2 full-word replacement, or W3 terminal bridge.

## RNG

The sibling pool and H2 selection use dedicated SHA-256 side-streams and do not consume the parent RNG. Therefore downstream differences come from the final word-form difference rather than RNG-position drift.

## Rejected components

- W2 known3 residual reweighting
- full-word sibling replacement
- L3 H2 splice
- L5 H2 splice
- L6+ H2 splice
- K32/K64
- W3 terminal bridge/terminal weakening
