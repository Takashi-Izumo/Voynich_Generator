# HerbalA v21r Stage 4 — SLOT SCREEN

This Stage 4 package connects the outer-bifolium-blind SLOT tables constructed in Stage 3 to actual W2 exact-4 generation and compares them against the formal `SAFE_LEFT_BT_OFF` control.

## Conclusion

- Stage 1 `V20_COMPAT`: **300/300 hash match PASS**
- Stage 2 `SAFE_LEFT_BT_ON`: **300/300 hash match PASS**
- Stage 3 table leakage/probability audit: **5/5 fold PASS**
- `SAFE_LEFT_BT_OFF`: a new fixed 100-case hash reference was created
- SLOT synthetic validation: PASS
- 91401–91403 screen: completed 4 arms × 60 cases
- SLOT mechanical: packing 100%, support violations 0, invalid 0, fallback 0%
- pooled `P(H3|H1,W)` conditional JSD: **0.320282 → 0.240830 improvement**
- bigram: **about 18.5% improvement**
- ng: **about 9.9% improvement**
- trigram: about 0.61% worse
- `SPACE_RAW`: **about 16.1% worse, paired p≈0.010**

Therefore, according to the predefined screen stop rule, **SLOT was stopped after three seeds**. Seeds 91404–91420 were not run.

The v21r candidate at the end of Stage 4 is:

`SAFE_LEFT_BT_OFF`

Across the historical five seeds and the fresh three-seed screen, it shows no v20r regression on the order of 10% in the major monitored metrics.

Details: `model/docs/V21_STAGE4_IMPLEMENTATION_EN.md`

## GitHub-safe edition

The GitHub edition preserves the model state, parameters, and validation results while moving only the two large runtime source ZIP archives outside the repository into GitHub Release assets. On reproduction, their SHA-256 hashes are always verified against `model/SOURCE_ARCHIVES.json`.

See `GITHUB_SAFE_PACKAGING_EN.md` for packaging details and `model/docs/STAGE4_REPRODUCTION_GITHUB_EN.md` for reproduction instructions.
