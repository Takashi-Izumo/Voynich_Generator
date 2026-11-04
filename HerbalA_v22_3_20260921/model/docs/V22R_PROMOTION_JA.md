# HerbalA v22r 昇格記録

## 正式モデル

`v22r = v21r SAFE_LEFT_BT_OFF + PRETERM_QMAP9 + SHORTBODY-H2-GLOBAL + PARAH1-RUN32`

2026-09-17にfresh seeds 91701–91710、20 bifolia × 10 seeds = 200生成セットで凍結審判を実施し、事前昇格条件を満たしたためv22rへ昇格した。審判後に係数・枝・規則の変更は行っていない。

## 主審

- word: 10/10
- ng: 8/12
- bigram: 4/16
- trigram: 7/13
- route56: 7/13
- combined: 7/13, binomial p=0.263176, sign-flip p=0.152370

## 専用審判

- H1: 9/11。signed margin -0.011995 → -0.009041。20/20葉が正方向、paired p=0.000002。
- H1→H2: 5/15 → 6/14。signed margin -0.024924 → -0.021823。17/20葉が正方向、paired p=0.000261。
- H1→H2→H3: 8/12 → 9/11。微改善だがpaired効果は非有意。
- terminal: 15/5。親から完全不変。binomial p=0.041389、margin sign-flip p=0.295460。
- bT: 13/7。実質不変。
- LF: 9/11。親から完全不変。

## 機械監査

- packing 200/200 PASS
- support violation 0
- invalid 0
- segment retry 0
- H1変更 136語、92/200頁、20/20葉
- 親との差136語は136/136すべてH1-only
- H2+ / exact length / physical width / route final state / parent RNG は凍結

## 判定

`PASS_WITH_RESIDUAL`。

昇格条件は満たしたが、global bigram residualは4/16、sign-flip p=0.002815で残る。signed marginは親から2.21%縮小した。terminal 15/5も残課題だが、PARAH1導入前後で完全不変のためv22rの副作用ではない。

次の解析対象はterminal residual decompositionと残存global bigram residualであり、v22r自体の係数は凍結する。
