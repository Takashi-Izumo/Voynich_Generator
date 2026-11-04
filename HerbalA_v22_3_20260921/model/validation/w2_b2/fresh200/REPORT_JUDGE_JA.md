# v22r B2 minimal — fresh 200 blind judge

## 判定

**PASS WITH RESIDUAL**

B2はW2 H2補正としては採用可。ただしglobal bigram残差の解消とは判定しない。

## strict W2 本命

- H2|H1 all: parent margin -0.206648 -> child -0.170828
- sign-flip: 0.028255 -> 0.063082
- paired delta: +0.035820 bit/event; 17/20 leaves positive, Wilcoxon one-sided p=0.00002670
- intervention scope len3-5: child margin -0.280990, sign-flip p=0.008512; residual remains.
- H1H2 joint JSD also moves toward zero in 18/20 leaves, paired p=3.81e-6.
- H3|H1H2 control has no reliable paired deterioration (one-sided p=0.123).

## Standard frozen judges

| judge | parent real/gen | B2 real/gen | parent margin | B2 margin | paired delta | paired p (desired direction) |
|---|---:|---:|---:|---:|---:|---:|
| bigram | 4/16 | 4/16 | -0.023713 | -0.023551 | +0.000162 | 0.3198 |
| trigram | 7/13 | 6/14 | -0.007914 | -0.008206 | -0.000292 | 0.3198 (worsening test) |
| combined | 7/13 | 7/13 | -0.010750 | -0.010664 | +0.000087 | 0.2086 |

Global bigramはわずかに0へ近づくが、4/16・sign-flip p=0.003071で残差は明瞭に残る。trigramはわずかに負方向へ動くが、paired deteriorationは有意でない。

BODY specialized H1/H1H2/terminal/bT/LFはB2がW2のみを触るためv22rと同値。

## fresh 200 mechanical

- 200/200 packing exact
- support violations 0
- invalid rows 0
- segment retries 0
- B2 applied 1793 requests
- actual H2 changes 81 words, 55/200 pages, 20/20 bifolia

## 最終解釈

B2は狙ったW2 H2|H1過近似を外部blindで有意に緩和し、機械的不変性も保つため、W2局所修正として採用してよい。一方、global bigram 4/16は変わらず、次の主残差はF1前半など別セルにある。
