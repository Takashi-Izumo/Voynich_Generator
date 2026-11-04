# v22r B2最小W2-H2修正：多様審判横断評価

## 結論

**総合判定：LOCAL PASS / NO POSITIONAL REGRESSION。**

B2は、意図したW2のH2条件付き分布を改善しつつ、第一行・行頭・BODY・行末・段落末を親v22rから完全に維持した。SPACEの直接境界 `terminal→次語頭` も完全不変。global bigramはわずかに改善するが4/16の残差は残るため、global bigram問題全体の解決とは判定しない。

本評価ではfresh 200（20 bifolia × 10 seeds）を使用。正式統計単位は20 bifolia。raw 200 pairは記述値。カスタム位置審判は、真正第4面・親生成・B2生成を同じknown-3（三面）プロトタイプへ比較するJSD審判。

## 1. 既存global審判

| judge | parent margin | B2 margin | Δ | 葉 higher/lower/same | paired p（改善方向） |
|---|---:|---:|---:|---:|---:|
| word | -0.003920 | -0.003531 | +0.000388 | 10/7/3 | 0.1034 |
| ng | -0.017581 | -0.017796 | -0.000215 | 8/10/2 | 0.6170 |
| bigram | -0.023713 | -0.023551 | +0.000162 | 9/9/2 | 0.3198 |
| trigram | -0.007914 | -0.008206 | -0.000292 | 8/10/2 | 0.6953 |
| route56 | -0.029620 | -0.029803 | -0.000183 | 3/7/10 | 0.8623 |
| combined | -0.010750 | -0.010664 | +0.000087 | 10/8/2 | 0.2086 |

bigramは `-0.023713 → -0.023551` と微小改善だが4/16のまま。trigramは微小悪化だがpairedで有意ではない。combinedは微小改善。

## 2. 位置別ファミリー審判

| family | judges | parent | B2 | |margin|改善 | 葉 toward/away/same | p |
|---|---:|---:|---:|---:|---:|---:|
| FIRST_LINE | 5 | 0.051571 | 0.051571 | +0.000000 | 0/0/20 | 1.0000 |
| LINE_HEAD | 6 | 0.082729 | 0.082729 | +0.000000 | 0/0/20 | 1.0000 |
| W2 | 7 | 0.088243 | 0.085471 | +0.002772 | 14/4/2 | 0.0091 |
| BODY | 4 | 0.036125 | 0.036125 | +0.000000 | 0/0/20 | 1.0000 |
| LINE_END | 8 | 0.102773 | 0.102773 | +0.000000 | 0/0/20 | 1.0000 |
| PARA_FINAL | 2 | 0.071277 | 0.071277 | +0.000000 | 0/0/20 | 1.0000 |
| SPACE | 3 | 0.057228 | 0.057200 | +0.000027 | 8/2/10 | 0.1162 |

**第一行・行頭・BODY・行末・段落末は全judgeで親と完全同一。** W2ファミリーだけが改善し、SPACEは実質中立。

## 3. 第一行審判

- `FIRST_WORD`: **EXACT_INVARIANT**（200 pairでdistance変更 0）
- `FIRST_BIGRAM`: **EXACT_INVARIANT**（200 pairでdistance変更 0）
- `FIRST_TRIGRAM`: **EXACT_INVARIANT**（200 pairでdistance変更 0）
- `PHW_WORD`: **EXACT_INVARIANT**（200 pairでdistance変更 0）
- `F1_WORD`: **EXACT_INVARIANT**（200 pairでdistance変更 0）

B2はMIDDLE W2だけを触るため、第一行の語形・bigram・trigram、PHW、F1が全てbit-levelに不変であることを確認。

## 4. 行頭審判

- `LINEHEAD_WORD`: **EXACT_INVARIANT**（変更 0/200）
- `LINEHEAD_H1`: **EXACT_INVARIANT**（変更 0/200）
- `LINEHEAD_H1H2`: **EXACT_INVARIANT**（変更 0/200）
- `LINEHEAD_LEN`: **EXACT_INVARIANT**（変更 0/200）
- `VERTICAL_HEAD_H1PAIR`: **EXACT_INVARIANT**（変更 0/200）
- `HEAD_MIDDLE_WORD`: **EXACT_INVARIANT**（変更 0/200）

特に縦行頭bigram `VERTICAL_HEAD_H1PAIR` も完全不変。したがってW2-H2修正は行頭第一字の縦依存へ漏れていない。

## 5. W2審判

### 事前指定のstrict conditional審判

| metric | parent margin | B2 margin | parent p | B2 p | parent→B2葉差 |
|---|---:|---:|---:|---:|---:|
| H2|H1_all | -0.206648 | -0.170828 | 0.02826 | 0.06308 | +17/-1/=2 |
| H2|H1_len3_5 | -0.322252 | -0.280990 | 0.00368 | 0.00851 | +17/-1/=2 |
| H3|H1H2_all | 0.013447 | 0.024068 | 0.80773 | 0.65846 | +8/-10/=2 |
| H1H2_joint_JSD | -0.106855 | -0.093335 | 0.00368 | 0.00900 | +18/-0/=2 |

`H2|H1_all` は `-0.20665 → -0.17083`、17/20葉改善、parent→B2 paired p≈2.7e-5。B2ではsign-flip p=.0631となり、全strict W2の有意残差域を抜ける。H3|H1H2は有意な悪化なし。

### 位置JSD審判

- `W2_WORD`: **SLIGHT_IMPROVE_NS**; |margin|改善=+0.000261, toward/away/same=6/2/12, nominal p=0.2734
- `W2_H1`: **EXACT_INVARIANT**; |margin|改善=+0.000000, toward/away/same=0/0/20, nominal p=1.0000
- `W2_H1H2`: **IMPROVED**; |margin|改善=+0.006363, toward/away/same=14/4/2, nominal p=0.0192
- `W2_BIGRAM`: **SLIGHT_IMPROVE_NS**; |margin|改善=+0.002118, toward/away/same=11/7/2, nominal p=0.0770
- `W2STRICT_WORD`: **SLIGHT_IMPROVE_NS**; |margin|改善=+0.003862, toward/away/same=6/1/13, nominal p=0.0547
- `W2STRICT_H1H2`: **IMPROVED**; |margin|改善=+0.006798, toward/away/same=13/5/2, nominal p=0.0216
- `W1_W2_BOUNDARY`: **EXACT_INVARIANT**; |margin|改善=+0.000000, toward/away/same=0/0/20, nominal p=1.0000

W2 H1は完全不変、W1→W2境界も完全不変。変化は狙いどおりH1H2とW2内部bigramへ局在する。探索的な36審判全体にBH補正すると個別W2-JSDのq<.05は残らないため、これらは副次確認と扱う。主要証拠は事前指定されたstrict conditional審判。

## 6. 行末審判

- `LINEEND_WORD`: **EXACT_INVARIANT**（変更 0/200）
- `LINEEND_TERM`: **EXACT_INVARIANT**（変更 0/200）
- `LINEEND_BT`: **EXACT_INVARIANT**（変更 0/200）
- `LINEEND_LEN`: **EXACT_INVARIANT**（変更 0/200）
- `FIRST_LF_WORD`: **EXACT_INVARIANT**（変更 0/200）
- `MIDDLE_LF_WORD`: **EXACT_INVARIANT**（変更 0/200）
- `PF_LF_WORD`: **EXACT_INVARIANT**（変更 0/200）
- `PF_LF_TERM`: **EXACT_INVARIANT**（変更 0/200）

第一行末・通常行末・段落最終行末を分けても全て完全不変。terminal/bT/語長も不変。

## 7. 段落末・BODY・SPACE control

- `FINALROW_WORD`, `PF_W1_WORD`: **完全不変**。
- `BODY_WORD/BIGRAM/TRIGRAM/TERMINAL`: **完全不変**。
- `SPACE_TH1`（前語terminal→次語H1）: **完全不変**。
- `FIRST_SPACE_TH1`: **完全不変**。
- `SPACE_BTH1` はH2が3字語のpenultimateになり得るため14/200で数値が変わるが、平均|margin|は +0.000082改善、悪化検定p=.903。**副作用なし**。

## 8. 多重審判の扱い

今回の位置別パネルは副作用探索のため36審判を同時に走らせた。探索的JSD審判のnominal pは多重比較後に単独有意とは扱わない。一方、strict W2 `H2|H1` はPhase 1–Bを通じて事前指定されたprimary targetであり、今回の横断パネルとは別に評価する。

悪化方向では、36審判のどれにもnominal p<.05の劣化はなく、BH後qは全て1.0。さらに第一行・行頭・BODY・行末・段落末の主要controlは統計的「差なし」ではなく、**parent/B2の抽出分布そのものが完全一致**している。

## 9. 最終判定

\[\\boxed{\\textbf{B2修正はW2局所修正として採用可能}}\]

より正確には：

1. **W2 H2|H1：改善**。
2. **W2 H1・W1→W2境界：不変**。
3. **第一行：完全不変**。
4. **行頭・縦行頭依存：完全不変**。
5. **BODY：完全不変**。
6. **行末・terminal・bT・段落末：完全不変**。
7. **SPACE terminal→次語頭：完全不変**。
8. **global bigram：微小改善だが4/16残差は未解決**。
9. trigramは微小悪化するが葉pairedで有意ではない。

したがって今回の修正は「W2を直す代償として他位置を崩した」ものではなく、**実際にW2だけを局所改善した修正**と評価できる。次のglobal bigram残差はW2以外（既存分解ではF1前半が最有力）として切り離して扱うべき。

