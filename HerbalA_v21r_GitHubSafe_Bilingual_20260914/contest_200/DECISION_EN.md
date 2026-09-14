# Formal 200-set blind primary contest

Date: 2026-09-12

Model: `RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16`

## Decision

**PASS**.

For the primary `combined` judge, using fresh seeds 99001–99010 across 20 leaves × 10 seeds = 200 sets:

- real selected: 96/200
- synthetic selected: 104/200
- ties: 0
- descriptive binomial p=.6207

However, the same 20 real fourth surfaces are reused ten times each, so the 200 cases must not be treated as 200 independent real pages. As in the earlier primary contest, seeds are averaged within leaves and the 20 bifolia are used as the inferential units:

- real wins: 10/20
- synthetic wins: 10/20
- binomial p=1.000
- exact sign-flip p=.3291

Thus the frozen combined judge could not identify the genuine page above chance in the fresh 200-set contest.

## Protocol

- The formally promoted model was frozen; no parameter changes or best-of-N selection were allowed during the contest.
- Fresh seeds 99001–99010 were used rather than the existing validation seeds 91321–91340.
- For each leaf, the three known surfaces were used as judge references, and the fixed real fourth surface was compared one-to-one with the synthetically generated page.
- Under 5-fold evaluation, leaves outside the target fold were used for vectorizer training.
- Left/right placement was fixed before scoring with random seed 202609120200, producing 100 real-left and 100 real-right cases.
- The primary judge was the same as in the earlier 3-surfaces-to-fourth-surface contest: `combined = .5*(word+ng)`.
- Diagnostic judges: word, ng (2–4gram), bigram, trigram, route56.
- presentation SHA-256: `806008b4f073e4c7f08d3f64308118fbd6e4b1651c72bdf1359314f2e20b8ac6`

## Mechanical audit

Across all 200 pages:

- packing PASS 200/200
- segment retry 0
- support violation 0
- invalid row 0
- max normalization error 8.881784197001252e-16

## Descriptive results for 200 sets

| judge | real wins / 200 | synthetic wins / 200 | real rate | descriptive binomial p |
|---|---:|---:|---:|---:|
| word | 98 | 102 | 49.0% | .8321 |
| ng (2–4gram) | 77 | 123 | 38.5% | .00140 |
| bigram | 63 | 137 | 31.5% | 1.79e-7 |
| trigram | 97 | 103 | 48.5% | .7238 |
| route56 | 71 | 129 | 35.5% | 4.97e-5 |
| **combined** | **96** | **104** | **48.0%** | **.6207** |

The 200-case binomial p-values above are descriptive, not formal inferential statistics, because they treat the 20 repeatedly used real pages as if they were independent.

## 20-leaf cluster results

| judge | real wins / 20 | synthetic wins / 20 | binom p | sign-flip p |
|---|---:|---:|---:|---:|
| word | 11 | 9 | .8238 | .7824 |
| ng | 9 | 11 | .8238 | .1037 |
| bigram | 6 | 14 | .1153 | **.00220** |
| trigram | 10 | 10 | 1.0000 | .6735 |
| route56 | 7 | 13 | .2632 | .1164 |
| **combined** | **10** | **10** | **1.0000** | **.3291** |

## Interpretation

The primary combined judge is exactly at chance level, confirming the primary PASS with fresh seeds.

This does not mean every feature is identical to the real data. In particular, the bigram signed margin is significantly negative: generated pages tend to lie too close to the known-three profile relative to the real target. ng and route56 show the same direction. Therefore, although the current frozen judge is strongly fooled, another adversarial judge trained in advance to detect the direction "generated pages are too close to known3" might exploit this residual.

This does not invalidate the present contest result, but it is an important next attack surface.

## Leaf-level combined results

Leaves for which the real page was selected 10/10 times: C:3, G:3.

Leaves for which the synthetic page was selected 10/10 times: A:4, B:1, D:3, D:4, G:4.

Substantial leaf-specific bias remains; the result is not "uniform indistinguishability across all leaves."

## Conclusion

**Formal 200-set contest: PASS.**

The frozen combined judge selected the genuine page only 96/200 times, and only 10/20 at the 20-leaf cluster level. The model achieved the stated contest objective.

If a next improvement target is chosen, the first candidate should be the `bigram known3 overfit`, which becomes a strong discrimination signal when its direction is reversed post hoc.
