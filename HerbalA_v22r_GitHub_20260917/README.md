# HerbalA v22r

Official 2026-09-17 promotion of the Pure Herbal A generator.

**Model:** `v21r SAFE_LEFT_BT_OFF + PRETERM_QMAP9 + SHORTBODY-H2-GLOBAL + PARAH1-RUN32`  
**Status:** `PASS_WITH_RESIDUAL` on fresh seeds 91701–91710.

The promoted addition is a causal paragraph-local continuous running residual applied to BODY H1 only (`lambda=32`, no decay). H2+, exact word length, physical width, route memory, bT, PRETERM, packing and the parent RNG are frozen.

Headline fresh-200 results (20 bifolia are the formal units): combined 7/13, H1→H2 6/14 versus parent 5/15, bigram 4/16 with a 2.21% signed-margin shrink, trigram 7/13, and 200/200 packing PASS. The global bigram residual and an inherited terminal 15/5 asymmetry remain open.

See [README_JA.md](README_JA.md) and `model/docs/V22R_PROMOTION_JA.md` for details.

Large frozen parent source archives are distributed separately as the GitHub Release asset `HerbalA_v22r_Release_Source_20260917.zip`; extract that asset over the repository root before generation runs.
