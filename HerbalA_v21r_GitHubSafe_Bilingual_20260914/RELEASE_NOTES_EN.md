# Release notes — v21r Stage 3

- Freeze the Stage 2 `SAFE_LEFT` baseline.
- Add fold-specific, target-blind probability tables for W2 exact-4 SLOT.
- H2 uses a W2-only hierarchical model; context depth and alpha are selected by inner-bifolium CV.
- H3 uses `P(H3|H1,W)`, retaining W=4..8 as exact discrete states.
- H4 uses BODY-shared `P(H4|H3)` with fixed alpha=2.
- Training leakage is 0 for all 20 target bifolia.
- The SLOT generator is not yet connected at this stage.
- Stage 2 validator retains 23/23 reproduction.
