# v21r+PRETERM+SHORTBODY-H2-GLOBAL
## H1 paragraph state parameterization contest — 2026-09-17

## 結論

三方式を同一の外部保留条件で対決させた。

1. finite discrete selector（2–K状態候補。感度ではK=10まで）
2. continuous running residual state
3. exponentially decaying memory

最終判定は、**continuous running residual stateを採用候補**とする。

- finite discrete selector: 棄却
- decaying memory: continuousとほぼ同等だが、追加パラメータrhoの利得が外部保留で有意ではない
- continuous running residual: 最小で、頑健にbaselineを改善

したがって現時点の最小実装像は、paragraph境界でresetし、同paragraphですでに観測された行のH1 residualを連続量として蓄積する方式である。

---

## 1. 共通条件

対象はPure Herbal Aのcomplete bifolia 20葉。

対象事象は、

- BODY
- paragraph line >= 2
- paragraph-final除外
- segment-end除外
- 2 glyph以上

である。

baselineは前回と同じ、

`exact glyph length + previous terminal T + leaf-known-3 H1`

とした。

同paragraphの最初の適格行はstate推定にだけ使い、2本目以降の適格行を順次予測した。target行以降はstate推定に使わない。

- target lines: 513
- target H1 events: 1,483
- leaves: 20

全方式で完全に同じtargetを使用した。

ハイパーパラメータは、対象葉自身を使わず、残り葉の外部保留成績だけから選んだ。

---

## 2. 主結果

| model | loss bits/event | baselineからのΔ | 改善葉 | p vs baseline | bits saved |
|---|---:|---:|---:|---:|---:|
| **continuous running residual** | **2.958902** | **-0.051530** | **16/20** | **0.001356** | **76.42** |
| fine nested decay | 2.960225 | -0.050206 | 14/20 | 0.004154 | 74.46 |
| baseline | 3.010432 | — | — | — | — |
| finite discrete family | 3.059379 | **+0.048947** | 3/20 | 0.999933 | -72.59 |

continuousとdecayはいずれもparagraph stateの存在を再確認した。一方、有限離散stateは外部保留で明瞭に悪化した。

---

## 3. continuous vs decay

continuous - decay のpaired差は、

- weighted difference: **-0.001324 bit/event**
- continuous優位: 14/20葉
- decay優位: 6/20葉
- two-sided Wilcoxon: **p=0.4091**
- continuous優位片側: p=0.2045

したがって、decayを入れることで有意な改善は確認できない。

粗い探索ではrho=0.95が最良だったが、rhoを細かくするとnested選択は主に、

- rho=0.85: 4葉
- rho=0.88: 13葉
- rho=0.92: 3葉

となった。lambdaは17/20葉で24、3/20葉で32。

数値上は「数行スケールの弱い減衰」を示唆するが、continuousに対する外部利得は頑健ではない。追加機構として採用しない。

---

## 4. finite discrete selector

主探索ではK=1–5、alpha=32をnested選択した。さらに感度として、

- K=6,8,10
- alpha=8,16,32,64,128

まで拡張した。

それでも、全20葉を見て後から一つだけ固定候補を選ぶという楽観的な比較ですら最良は、

`K=6, alpha=64`

で、

- loss = **3.017273**
- baselineより **+0.006841 bit/event悪化**

だった。

完全target-blind nested selectionでは、

- loss = **3.059379**
- baselineより **+0.048947**
- 改善は3/20葉のみ

となる。

continuousとの差は、

- weighted: **+0.100477 bit/event**
- continuous優位: 17/20葉
- two-sided p = **2.67e-5**

である。

したがって、paragraph H1 stateを少数の固定離散クラスへ量子化する仮説は棄却する。

---

## 5. 理論更新

前回までの

`H1 = leaf-shared + T→H1 + paragraph-shared bias`

を維持する。

ただしparagraph biasの表現は、

`finite selector`

ではなく、

`continuous running residual`

が最小である。

現時点の実装候補は、

`P(H1) ∝ P_leaf(H1 | length,T) × G_paragraph_running(H1)`

である。

`G_paragraph_running` はparagraph開始でneutralへresetし、生成済みの同paragraph過去行からH1 residualを縮約付きで更新する。今回のnested選択ではcontinuous側のlambdaは20/20葉で32だった。

減衰rhoはまだ入れない。

---

## 6. 実装判断

この検定だけなら、次段階へ進む候補は、

**continuous running paragraph H1 residual, lambda=32, paragraph reset**

である。

ただし今回の作業ではまだ親モデルへ実装していない。blind judgeも未実施。

H2 page-local補正は引き続き実装しない。
