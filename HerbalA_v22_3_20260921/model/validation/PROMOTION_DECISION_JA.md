# L4-only H2 splice K16: 20-seed confirmation

## Decision

**CONFIRMED / PROMOTE**

Model under confirmation:

- Parent: PUV + BODY-R4 lambda=0.85 + adaptive leaf-excess
- W2 refinement: exact L4 only
- K=16 sibling proposal pool
- H2-only splice
- H1, H3+, terminal, exact length, physical width unchanged
- no W2 residual table

## Design

The original 5 seeds (91321--91325) were retained. Fifteen new seeds
(91326--91340) were generated independently for both parent/OFF and L4-only/ON.
Statistics are paired within seed and leaf, then averaged over seeds per leaf.
The inferential unit remains the 20 held-out bifolia/leaves; extra seeds only
reduce Monte-Carlo noise.

## Main result

### Independent NEW15 replication

- bigram: -1.6581%, 16/20 leaves improve, sign-flip p=0.016747
- ng: -2.4870%, 14/20, p=0.013617
- trigram: -2.3336%, 14/20, p=0.030052

Holm correction over the three n-gram tests gives q=0.040850 for all three.

### ALL20 seeds

- bigram: -2.1542%, 16/20 leaves improve, p=0.002277
- ng: -2.3367%, 15/20, p=0.013830
- trigram: -2.6271%, 16/20, p=0.005253

Holm over the five regression/safety tests (bigram, ng, trigram, route56,
bT leaf-excess):

- bigram q=0.011387
- ng q=0.041491
- trigram q=0.021011
- route56 q=1
- bT leaf-excess q=1

Thus the three standard n-gram improvements survive the broader family-wise
correction.

## Safety

Across all 20 seeds:

- SPACE_RAW: exactly unchanged
- route56: exactly unchanged
- bT leaf-excess: exactly unchanged
- length/width: exactly unchanged
- glyph-depth: +0.063% (neutral, p=0.793)
- packing: all PASS
- support violations: 0
- invalid rows: 0
- segment retries: 0

## Important qualification

H2_RAW does **not** replicate as an improvement:

- NEW15: +0.289% worse, p=0.602
- ALL20: -0.244% better, p=0.678

Therefore promotion is justified by robust global n-gram improvement and safety,
not by stable improvement of the H2_RAW local judge.

## Final status

The previous `PROMOTION HOLD` can be lifted.

Recommended promoted component:

`W2 exact-L4, K16, legal same-width H2-only splice`

K32 remains rejected.
