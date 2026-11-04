# HerbalA-v22.3 正式昇格審判

## 判定

`PROMOTED_PASS_WITH_RESIDUAL`

昇格条件を **decision-level再現 + 現行law凍結** に正式変更した。旧Stage1/2 component artifactのbit-level一致は、歴史的provenance資料として残すが昇格要件にはしない。

## Decision-level再現

- **D1 PASS** — strict scope decision reproduced (88 terminal events / 20 complete bifolia)
- **D2 PASS** — short selector decision reproduced: L<=3 uses normal middle-LF terminal distribution
- **D3 PASS** — long selector decision reproduced: L>=4 preserves F1 non-l ratios and inherits only normal-LF P(l)
- **D4 PASS** — closure/extra-bias decision reproduced: STOP unchanged; y/n dedicated bias, S_LF, Global6, post-hoc rewrite remain OFF
- **D5 PASS** — whole-bifolium decision reproduces positive and significant teacher-forced improvement
- **D6 PASS** — live mechanics and protected global regressions pass after route-neutral r1 fix
- **D7 PASS** — current law frozen with immutable manifest and aggregate SHA-256

## Current-TL teacher-forced

- 88 events / 20 bifolia
- Base-L NLL: 2.266090394 bit/terminal
- candidate NLL: 2.227623370
- improvement: **+0.038467024 bit/terminal**
- long L>=4 improvement: **+0.067701963 bit/terminal**
- improved bifolia: **18/20**
- exact one-sided sign-flip: **p=0.00753307343**

これは旧Stage2の数値そのものの再現ではなく、採択判断（短語normal-LF、長語F1+LF-l、normal-LF closure、追加biasなし）がwhole-bifolium外部化条件でも同じ方向・有意で再現したことを昇格根拠とする。

## 現行law凍結

- law data SHA-256: `65a166a1235c17e97b0b4dce64d3bff47c1ae692250ec2534601f88d217d3d2e`
- law + interpreter SHA-256: `2e7df79abfbe4f954d34b1966054cfc49476b7d04b955a43b5b956b65a1ab4ab`
- 凍結対象: 20 LOBO law JSON、strict 88-event ledger、Stage3D config、law/sampler/router interpreter
- v22.3では以後変更禁止。1 byteでも変更する場合は新versionとし3E→3F→3Gを再監査する。

## 回帰監査

- Stage3E-r1: **910/910 PASS**
- Stage3F-r1: **410,379 comparisons / failures 0**
- Stage3G-r1: **4,120,232 comparisons / failures 0**
- route trace exact: **200/200**
- route final state exact: **200/200**
- BH-significant protected regression: **0**

## 残差

- Two support-preserving safe fallbacks remain at f7v.6 and f53v.1 when live same-width support and frozen-law support do not intersect.
- Seed 91706 / G:1 is excluded because parent v22.2 and candidate hit the same pre-existing assertion; seed 91711 replaces it in the 10-seed paired set.
- Mean 5-gram/6-gram JSD deltas are slightly positive but no protected metric is BH-significantly regressed.
- Legacy Stage1/2 component artifacts are not bit-level aligned. Under the revised promotion policy this is historical provenance only, not a promotion blocker.

## 正式状態

`current stable model = HerbalA-v22.3`

定義：

`v22.3 = v22.2 + F1-LF length-aware terminal source + normal-LF l inheritance + route-neutral commit r1`
