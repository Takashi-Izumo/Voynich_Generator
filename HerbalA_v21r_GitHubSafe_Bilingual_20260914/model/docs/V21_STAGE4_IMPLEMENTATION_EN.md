# HerbalA v21r Stage 4 — SLOT generator implementation and 3-seed screen judgment

## 1. Conclusion

The Stage 4 SLOT generator was implemented according to specification, and all mechanical invariants passed.
However, `SPACE_RAW` clearly regressed in the 3-seed screen, so SLOT was stopped after three seeds according to the predefined stop rule.

Final decision:

- `SLOT_BT_OFF`: **rejected / 3-seed STOP**
- `SAFE_LEFT_BT_OFF`: **v21r candidate**
- independent SLOT validation on 91404–91420: **not run (stop rule)**

## 2. Preflight

### V20_COMPAT

Regenerated the same 5 seeds × 20 bifolia = 100 cases used in Stage 1.

- generated rows: 100/100 match
- surface commits: 100/100 match
- generation input: 100/100 match

Total: `300/300 hash match`. PASS.

### SAFE_LEFT_BT_ON

Regenerated the 100 Stage 2 cases with fixed hashes:

- 100/100 cases match
- 300/300 hash fields match

Stage 2 historical reproduction also remains 23/23. PASS.

### SAFE_LEFT_BT_OFF

Added a formal control that disables the bT score only in the parent candidate bank for W2 exact-4.
The bT behavior for all other roles and lengths is unchanged.

Generated 5 historical seeds × 20 bifolia = 100 cases and froze 300 hash fields in
`validation/stage4/SAFE_LEFT_BT_OFF_REFERENCE_HASHES_5SEED.csv`.

### Stage 3 tables

Reran the Stage 3 validator.

- 5/5 folds PASS
- target leakage = 0
- training-event hashes match
- positive finite probabilities / sum=1 on all observed contexts: PASS

## 3. SLOT implementation

Added:

- `code/w2_slot_generator.py`
- `V21SlotBtOffSampler` in `integrated_sampler_v21.py`
- `SAFE_LEFT_BT_OFF` / `SLOT_BT_OFF` modes in `run_model_v21.py`
- `code/run_stage4_modes.py`
- `code/validate_v21_stage4_synthetic.py`
- `validation/code/judge_stage4_slot.py`

Scope of application:

- role=W2
- board=W2
- exact glyph length=4
- total stable width W in {4,5,6,7,8}

Only H1, W, previous terminal T, and request context are taken from the anchor.
Anchor H2/H3/H4 are not used in the final SLOT candidate decision.

All stable-22 H2/H3/H4 combinations are enumerated, with hard legality restricted to:

- fixed total width
- H4 width=1
- the same LEFT support as v20r/SAFE_LEFT: `H1-H2-H3 > 0`

RIGHT support, current route, 5–6g route hit, known3 residual, leaf bT, terminal prior, and anchor H2/H3/H4 identity are not used as candidate filters or scores.

The score is strictly:

`log P(H2|H1,W,T) + log P(H3|H1,W) + log P_BODY(H4|H3)`

In fold 4, T is automatically unused because the Stage 3 table itself selected H1+W depth.

The SLOT-selection RNG namespace is `V21_W2_SLOT_SELECT_V1`.
The parent RNG is not consumed.

Fallback order:

1. SAFE_LEFT_BT_OFF
2. parent anchor

## 4. Synthetic validation

`validation/stage4/SYNTHETIC.json`.

PASS conditions:

- H1 fixed
- exact length 4
- W fixed
- H4 width=1
- LEFT legal
- RIGHT unused
- finite probability
- normalized probability
- candidate count > 0
- dedicated selection digest present

The live sampler also asserts that parent RNG and semantic digest are unchanged at every SLOT selection.

## 5. Three-seed screen

Fresh seeds: `91401, 91402, 91403`.
20 bifolia, four arms:

- V20_COMPAT
- SAFE_LEFT_BT_ON
- SAFE_LEFT_BT_OFF
- SLOT_BT_OFF

Each arm generated 60 cases, for a total of 240 generated cases.

### Mechanical results

SLOT:

- packing: 60/60 PASS
- support violations: 0
- invalid rows: 0
- SLOT proposal events: 310
- final-page committed SLOT events: 158
- fallback: 0 / 310 = 0%
- mean candidate count: 282.84
- W2 exact-4 bT enabled: 0

Change rate from anchor across all SLOT proposals:

- H2: about 43.5%
- H3: about 64.0%
- H4: about 63.2%

## 6. Primary comparison: SAFE_LEFT_BT_OFF vs SLOT_BT_OFF

Values are real-vs-generated absolute judge margins. Lower is better.

### n-gram

- bigram: `0.046381 -> 0.037795`, about 18.5% improvement
- ng: `0.038388 -> 0.034575`, about 9.9% improvement
- trigram: `0.046242 -> 0.046526`, about 0.61% worse

Therefore the n-gram family does not violate screen condition 7.

### H3 local

Because individual pages contain only about 2–3 W2 exact-4 words on average and per-page conditional JSD is extremely sparse, the formal local judge also audits pooled `P(H3|H1,W)` conditional JSD over all 20 bifolia × 3 seeds.

- SAFE_LEFT_BT_OFF: `0.320282`
- SLOT_BT_OFF: `0.240830`

SLOT improves this metric.
Pooled H3 marginal JSD also improves from `0.098936 -> 0.040718`.

### Failure point: SPACE_RAW

- SAFE_LEFT_BT_OFF: `0.044655`
- SLOT_BT_OFF: `0.051842`
- relative regression: **+16.09%**
- paired over 20 leaves: SLOT worse in 16, better in 4
- Wilcoxon: **p≈0.0100**

This clearly violates the requirement of no major SPACE regression.

Length-width improves, and route56 / glyph-depth / bT leaf-excess do not show a 10%-scale major regression.
Thus the screen failure is driven primarily by SPACE.

## 7. Screen decision

Of the eight conditions:

1. packing failure=0: PASS
2. support violation=0: PASS
3. invalid rows=0: PASS
4. no major SPACE regression: **FAIL**
5. no major length-width regression: PASS
6. fallback<5%: PASS (0%)
7. no major bigram/trigram regression: PASS
8. H3 local improved or equivalent: PASS (pooled conditional JSD improves)

Therefore:

**SLOT stops after the 3-seed screen. Seeds 91404–91420 are not run.**

## 8. v21r candidate judgment for SAFE_LEFT_BT_OFF

After SLOT stopped, `SAFE_LEFT_BT_OFF` was compared with v20r as the fallback candidate.

On the historical 5-seed / 100-case set, the main relative differences versus v20r were:

- H2_RAW +1.58%
- bigram −5.38% (improved)
- ng −0.47% (improved)
- trigram +2.19%
- SPACE_RAW +3.10%
- route56 −0.42% (improved)
- bT_leaf_excess −0.24% (improved)
- glyph_depth −2.81% (improved)
- length_width −4.59% (improved)

No metric shows a major regression on the order of 10%.

The fresh 3-seed screen likewise shows no major regression.

Therefore the state at the end of Stage 4 is:

`V21R_CANDIDATE_SAFE_LEFT_BT_OFF`

## 9. Theoretical update

The SLOT hypothesis itself is not rejected, because it improves H3 conditional structure and low-order n-grams:

`(H1,W) -> H3 -> H4`

However, simultaneous SLOT reselection of H2/H3/H4 propagates into the SPACE sequence and is unsafe at the full-generation level.
If SLOT is revisited, the next step should not be to retune the Stage 4 result. Instead, it should independently decompose **why a local improvement at W2 exact-4 propagates into `SPACE_RAW`**.
