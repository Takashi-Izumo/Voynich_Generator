# Change log

## 2026-09-12 — PROMOTED

Formally integrated the validated `W2 exact-L4 K16 legal same-width H2-only splice` into the parent `PUV + BODY-R4 0.85 + adaptive leaf-excess`.

Rejected trials:

- W2 known3 residual: probability-level signal exists, but it did not qualify for promotion under dynamic generation
- full-word H1-fixed sibling: improves W2 locally but worsens global n-grams
- W3 terminal weakening/bridge: terminal feedback was confirmed but did not rescue the global model
- L3: worsens bT terminal bigram
- L5/L6+: dilutes or reverses the L4 effect
- K32: higher cost than K16 and inferior on the main metrics

## 2026-09-13 — Stage 4

- Added `SAFE_LEFT_BT_OFF` as the formal control and fixed its 100-case hashes.
- Added `w2_slot_generator.py`.
- Connected the Stage-3 H2/H3/BODY-H4 tables to W2 exact-4 generation.
- Implemented SLOT-specific RNG namespace `V21_W2_SLOT_SELECT_V1`.
- Implemented fallback in the order SAFE_LEFT_BT_OFF → anchor.
- Ran a 3-seed screen over 240 cases.
- Mechanical invariants passed; H3 conditional and bigram/ng improved.
- Stopped SLOT at 3 seeds because `SPACE_RAW` regressed by +16.09%, p≈0.010.
- Designated `SAFE_LEFT_BT_OFF` as the v21r candidate.
