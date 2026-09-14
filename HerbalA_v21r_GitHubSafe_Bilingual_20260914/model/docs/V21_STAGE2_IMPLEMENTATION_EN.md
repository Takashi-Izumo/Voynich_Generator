# v21r Stage 2 implementation and reproduction audit

## Decision

**PASS** — `SAFE_LEFT` was implemented on the Stage 1 compatibility foundation, and the existing W2 exact-L4 LEFT-only five-seed validation was reproduced exactly.

## Only behavioral change

The v20r W2 exact-L4 H2 splice required both bridge-support conditions for a candidate H2:

- LEFT: `H1-H2-H3 > 0`
- RIGHT: `H2-H3-H4 > 0`

Stage 2 `SAFE_LEFT` removes **only the RIGHT condition**.

Retained behavior:

- W2 only / exact glyph length 4
- K=16, max draws=4096
- H1 fixed
- exact glyph length fixed
- stable physical width fixed
- H2 glyph width fixed
- H3 and later positions plus terminal fixed to the anchor
- sibling multiplicity preserved
- uniform selection from eligible multiplicity
- fallback to anchor if eligible count is 0
- RNG namespaces `W2H2SPLICE_POOL_V1` / `W2H2SPLICE_SELECT_V1`
- parent-side behavior including W2-L4 bT

## Reproduction validation

Five seeds (`91321..91325`) × 20 complete bifolia = 100 cases were regenerated.

Comparison with the earlier LEFT-only validation:

- 9 judges × BOTH/LEFT absolute margin = 18 items
- LEFT mechanical totals = 5 items
- total **23/23 exact matches**

Stage 2 LEFT mechanical totals:

- splice events: 542
- changed: 162
- changed rate: 0.2988929889
- zero fallback: 5
- sibling pool multiplicity: 8640
- eligible multiplicity: 7069
- eligible/event: 13.0424354
- RIGHT-off audit events: 542/542
- support violations: 0
- invalid rows: 0
- packing: 100% PASS

## BOTH vs LEFT on the same five seeds

Lower absolute margin is better. Improvement measured as LEFT−BOTH:

- H2_RAW: -0.0000455, p=.594
- bigram: +0.0005050, p=.0858
- ng: +0.0003110, p=.1386
- trigram: +0.0003044, p=.2604

The benefit of adding RIGHT was not reproduced; mean performance favors LEFT on all three n-gram metrics.

## Stage 1 compatibility

`V20_COMPAT` remains a separate class. After the Stage 2 implementation, smoke case `A:2 / run91321` still matches the official v20r reference hash.

## Conclusion

Stage 2 can be used as the **fixed SAFE_LEFT control**. Stage 3 adds the W2 SLOT table builder without modifying this code path.
