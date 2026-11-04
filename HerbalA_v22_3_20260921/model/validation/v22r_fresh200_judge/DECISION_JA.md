# PARAH1-RUN32 fresh 200 blind judge

Date: 2026-09-17

## Decision

**PASS_WITH_RESIDUAL**

The pre-specified minimum promotion conditions are all satisfied on fresh seeds 91701–91710, but the global bigram residual remains statistically detectable. No parameter was changed after judging.

## Formal unit

20 bifolia are the formal statistical units. The 200 pair results reuse each real held-out page across 10 seeds and are descriptive only.

## Primary frozen judges (20-leaf cluster)

| judge | parent real/gen | child real/gen | parent mean margin | child mean margin | child sign-flip p |
|---|---:|---:|---:|---:|---:|
| word | 10/10 | 10/10 | -0.004285 | -0.003920 | 0.696579 |
| ng | 8/12 | 8/12 | -0.017814 | -0.017581 | 0.037697 |
| bigram | 4/16 | 4/16 | -0.024248 | -0.023713 | 0.002815 |
| trigram | 6/14 | 7/13 | -0.008106 | -0.007914 | 0.494947 |
| route56 | 7/13 | 7/13 | -0.029544 | -0.029620 | 0.035971 |
| combined | 7/13 | 7/13 | -0.011049 | -0.010750 | 0.152370 |

Combined stays inside chance: child 7/13, binomial p=0.263176, sign-flip p=0.152370.

Global bigram remains a residual: child 4/16 with sign-flip p=0.002815. However its signed mean margin moves from -0.024248 to -0.023713, a 2.21% shrink. The paired correction is in the desired direction in 13/20 leaves, but is not conventionally significant (Wilcoxon p=0.0897).

## Dedicated diagnostics

The dedicated diagnostics use JSD to the known-three profile, with identical definitions for parent and child.

| judge | parent real/gen | child real/gen | parent mean margin | child mean margin | paired leaves corrected | paired p |
|---|---:|---:|---:|---:|---:|---:|
| H1 | 9/11 | 9/11 | -0.011995 | -0.009041 | 20/20 | 0.000002 |
| H1H2 | 5/15 | 6/14 | -0.024924 | -0.021823 | 17/20 | 0.000261 |
| H1H2H3 | 8/12 | 9/11 | -0.012213 | -0.011092 | 10/20 | 0.308788 |
| terminal | 15/5 | 15/5 | 0.012853 | 0.012853 | 0/20 | nan |
| bT | 13/7 | 13/7 | 0.007873 | 0.007922 | 6/20 | 0.959354 |
| LF | 9/11 | 9/11 | -0.009388 | -0.009388 | 0/20 | nan |

H1 is corrected in the desired signed direction in 20/20 leaves (-0.011995 -> -0.009041). H1->H2 improves from 5/15 to 6/14, with signed margin -0.024924 -> -0.021823; 17/20 leaves move in the desired direction (Wilcoxon p=0.000261). H1->H2->H3 also moves slightly toward zero (-0.012213 -> -0.011092) but without a reliable paired effect. Terminal and LF are exactly unchanged; bT changes only minutely.

## Mechanical audit

- 200/200 packing exact
- support violations: 0
- invalid rows: 0
- segment retries: 0
- maximum normalization error: 8.882e-16
- paragraph-H1 eligible events: 4939
- applied: 3797
- actual H1 changes: 136 across 92/200 generated pages and all 20/20 bifolia
- fresh parent/child direct diff: 136 changed words, all 136 H1-only, bad diffs 0
- route final state identical in 200/200 cases

## Promotion judgment

The stated minimum conditions are met:

1. combined remains within chance;
2. H1->H2 improves versus the parent;
3. global bigram signed residual shrinks, although only slightly and it remains significant;
4. trigram does not worsen;
5. packing/support/invalid safety is perfect.

Therefore the implementation passes promotion under the predeclared rule, but the appropriate label is **PASS WITH RESIDUAL** rather than a clean closure. The remaining attack surface is still the global bigram/known-three over-closeness.
