# HerbalA-v22.3 Stage3D-r1 candidate — Stage 3G-r1 full regression audit

## 判定

`STAGE3G_FULL_REGRESSION_PASS_WITH_RESIDUAL_AND_PROVENANCE_BLOCK`

### 実行範囲
- 有効paired seeds: **10** = [91701, 91702, 91703, 91704, 91705, 91707, 91708, 91709, 91710, 91711]
- paired bifolium runs: **200**
- parent + candidate live generations: **400**
- mechanical comparisons: **4,120,232**
- mechanical failures: **0**
- surface terminal diffs: **95** (all must be strict F1-LF terminal-only)

seed 91706 は G:1 で親v22.2自身とcandidateの双方が同じ既存assertに停止したため、比較集合から除外し seed 91711 で置換した。

## Frozen mechanics / protected regimes

- result: **PASS**
- linehead / W2 / BODY / normal LF / PF-LF / plant-boundary / segment>0: paired exact checks included
- packing / remaining-width trajectory / request clock / parent RNG / route trace / route final state: paired exact checks included

## Global frequency regression (candidate error - parent error; negative is better)

- types abs error: -3.1 (10/10 better, p_worse=1, q=1)
- hapax abs error: -2.6 (9/10 better, p_worse=1, q=1)
- F2 abs error: +0.8 (0/10 better, p_worse=0.0625, q=0.4062)
- F3-5 abs error: +0.2 (1/10 better, p_worse=0.3125, q=0.6771)
- F6-10 abs error: +0.4 (1/10 better, p_worse=0.1094, q=0.474)
- F11+ abs error: -0.5 (5/10 better, p_worse=1, q=1)
- frequency L1: -4.8 (9/10 better, p_worse=1, q=1)
- frequency SSE: -1284.2 (10/10 better, p_worse=1, q=1)

## Word-internal n-gram JSD regression

- bigram: -0.000212187 (8/10 better, p_worse=0.9863, q=1)
- trigram: -0.000172132 (5/10 better, p_worse=0.8008, q=1)
- 4-gram: +0.000191038 (5/10 better, p_worse=0.2959, q=0.6771)
- 5-gram: +0.000427843 (2/10 better, p_worse=0.01465, q=0.1904)
- 6-gram: +0.000607878 (1/10 better, p_worse=0.1562, q=0.5078)

Protected metrics with BH-significant regression: **[]**.

## Strict F1-LF live activity

- strict live requests: **180**
- applied: **178**
- terminal changed: **95**
- safe fallbacks: **2**
- unique fallback loci: ['f53v f53v.1', 'f7v f7v.6']
- live base terminal NMY/LR: 3.2285714285714286
- live final terminal NMY/LR: 3.0526315789473686

## Teacher-forced current-TL 88-event result

{
  "events": 88,
  "bifolia": 20,
  "baseL_nll_bits_per_terminal": 2.2660903939451966,
  "candidate_nll_bits_per_terminal": 2.2276233696198955,
  "improvement_bits_per_terminal": 0.03846702432530031,
  "long_improvement_bits_per_terminal": 0.06770196281252855,
  "bifolia_improved": 18,
  "exact_signflip_p_one_sided": 0.007533073425292969
}

## Promotion

Stage3G mechanics/regressionがPASSしても、旧Stage1/2 component artifactとのsource-law provenance照合が未解決なので、この監査だけでは正式 `HerbalA-v22.3` へ昇格しない。
