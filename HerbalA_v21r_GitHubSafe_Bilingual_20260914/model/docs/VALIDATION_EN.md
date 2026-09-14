# Promotion validation

## Independent 15-seed replication

Seeds 91326--91340, separate from the original five seeds, were added and re-judged with within-leaf pairing and the 20 leaves as the inferential units.

- bigram: **-1.6581%**, 16/20 leaves improve, sign-flip p=0.016747
- ng: **-2.4870%**, 14/20, p=0.013617
- trigram: **-2.3336%**, 14/20, p=0.030052

After Holm correction across the three n-gram families, all three metrics remain at q<=0.040850.

## All 20 seeds

- bigram: **-2.1542%**, 16/20, p=0.002277
- ng: **-2.3367%**, 15/20, p=0.013830
- trigram: **-2.6271%**, 16/20, p=0.005253

After Holm correction across five regression/safety metrics (bigram/ng/trigram/route56/bT leaf-excess):

- bigram q=0.011387
- ng q=0.041491
- trigram q=0.021011
- route56 q=1
- bT leaf-excess q=1

## Safety

Across all 20 seeds:

- SPACE_RAW: exactly unchanged
- route56: exactly unchanged
- bT leaf-excess: exactly unchanged
- length/width: exactly unchanged
- glyph-depth: +0.063%, p=0.793 (neutral)
- packing: all PASS
- support violations: 0
- invalid rows: 0
- segment retries: 0

H2_RAW did not show a stable improvement, so it is not used as the basis for promotion.
