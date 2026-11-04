# HerbalA v21r Stage 4 — SLOT generator 実装・3-seed screen審判

## 1. 結論

Stage 4 SLOT generatorは仕様どおり実装でき、mechanical invariantsはすべてPASSした。
しかし3-seed screenで `SPACE_RAW` が明瞭に悪化したため、仕様の停止規則に従いSLOTは3-seedで停止した。

最終判定は、

- `SLOT_BT_OFF`: **不採用・3-seed STOP**
- `SAFE_LEFT_BT_OFF`: **v21r候補**
- 91404–91420のSLOT独立validation: **未実行（stop rule）**

である。

## 2. preflight

### V20_COMPAT

Stage 1と同じ5 seeds × 20 bifolia = 100 casesを再生成。

- generated rows: 100/100一致
- surface commits: 100/100一致
- generation input: 100/100一致

合計 `300/300 hash match`。PASS。

### SAFE_LEFT_BT_ON

Stage 2固定hash 100 casesを再生成し、

- 100/100 cases一致
- 300/300 hash fields一致

Stage 2 historical reproductionも23/23。PASS。

### SAFE_LEFT_BT_OFF

W2 exact-4親candidate bankだけbT scoreをOFFにした正式対照を追加した。
他role・他長さのbT挙動は変更しない。

5 historical seeds × 20 bifolia = 100 casesを生成し、
`validation/stage4/SAFE_LEFT_BT_OFF_REFERENCE_HASHES_5SEED.csv` として300 hash fieldsを固定した。

### Stage 3 tables

Stage 3 validatorを再実行。

- 5/5 folds PASS
- target leakage = 0
- training event hashes一致
- 全observed contextでpositive finite probability / sum=1 PASS

## 3. SLOT実装

追加：

- `code/w2_slot_generator.py`
- `integrated_sampler_v21.py` の `V21SlotBtOffSampler`
- `run_model_v21.py` の `SAFE_LEFT_BT_OFF` / `SLOT_BT_OFF`
- `code/run_stage4_modes.py`
- `code/validate_v21_stage4_synthetic.py`
- `validation/code/judge_stage4_slot.py`

適用域：

- role=W2
- board=W2
- exact glyph length=4
- total stable width W in {4,5,6,7,8}

anchorから使用するのはH1, W, previous terminal T, request contextのみ。
anchor H2/H3/H4はSLOT最終候補決定に使用しない。

全stable-22 H2/H3/H4を列挙し、

- total width固定
- H4 width=1
- v20r/SAFE_LEFTと同一のLEFT support `H1-H2-H3 > 0`

だけをhard legalityとした。
RIGHT support、route current、5–6g route hit、known3 residual、leaf bT、terminal prior、anchor H2/H3/H4一致は候補filter/scoreへ入れていない。

scoreは厳密に、

`log P(H2|H1,W,T) + log P(H3|H1,W) + log P_BODY(H4|H3)`

のみ。
fold4ではStage 3 table自体がH1+W depthなのでTは自動的に使われない。

SLOT選択RNG namespaceは `V21_W2_SLOT_SELECT_V1`。
親RNGは消費しない。

fallbackは、

1. SAFE_LEFT_BT_OFF
2. parent anchor

の順。

## 4. synthetic

`validation/stage4/SYNTHETIC.json`。

PASS：

- H1 fixed
- exact length 4
- W fixed
- H4 width=1
- LEFT legal
- RIGHT unused
- probability finite
- probability normalized
- candidate count > 0
- dedicated selection digest present

live samplerでも各SLOT選択時にparent RNG / semantic digest不変をassertしている。

## 5. 3-seed screen

fresh seeds: `91401, 91402, 91403`。
20 bifolia、4 arms：

- V20_COMPAT
- SAFE_LEFT_BT_ON
- SAFE_LEFT_BT_OFF
- SLOT_BT_OFF

各arm 60 cases、合計240 casesを実生成。

### mechanical

SLOT：

- packing: 60/60 PASS
- support violations: 0
- invalid rows: 0
- SLOT proposal events: 310
- final-page committed SLOT events: 158
- fallback: 0 / 310 = 0%
- candidate count mean: 282.84
- W2 exact-4 bT enabled: 0

SLOT全proposalにおけるanchorからの変更率：

- H2: 約43.5%
- H3: 約64.0%
- H4: 約63.2%

## 6. 本命 SAFE_LEFT_BT_OFF vs SLOT_BT_OFF

値はreal-vs-generated absolute judge margin。低いほど良い。

### n-gram

- bigram: `0.046381 -> 0.037795`、約18.5%改善
- ng: `0.038388 -> 0.034575`、約9.9%改善
- trigram: `0.046242 -> 0.046526`、約0.61%悪化

したがってn-gramはscreen条件7を破らない。

### H3 local

個別pageはW2 exact-4が平均2–3語しかなくconditional JSDが極端に疎になるため、正式local judgeは全20 bifolia×3 seedsをpoolした `P(H3|H1,W)` conditional JSDでも監査した。

- SAFE_LEFT_BT_OFF: `0.320282`
- SLOT_BT_OFF: `0.240830`

SLOTが改善。
H3 marginal JSDもpoolで `0.098936 -> 0.040718` と改善した。

### 失敗点：SPACE_RAW

- SAFE_LEFT_BT_OFF: `0.044655`
- SLOT_BT_OFF: `0.051842`
- relative regression: **+16.09%**
- 20葉 paired: SLOT悪化16、改善4
- Wilcoxon: **p≈0.0100**

これは「SPACE重大悪化なし」を明瞭に破る。

length-widthは改善し、route56 / glyph-depth / bT leaf-excessには10%級の重大悪化はない。
したがってscreen failureはSPACEが主因。

## 7. screen判定

8条件中、

1. packing failure=0: PASS
2. support violation=0: PASS
3. invalid rows=0: PASS
4. SPACE重大悪化なし: **FAIL**
5. length-width重大悪化なし: PASS
6. fallback<5%: PASS（0%）
7. bigram/trigram重大悪化なし: PASS
8. H3 local改善または同等: PASS（pooled conditional JSD改善）

よって、

**SLOTは3-seed screenで停止。91404–91420は実行しない。**

## 8. SAFE_LEFT_BT_OFFのv21r候補判定

SLOT停止時のfallback候補としてSAFE_LEFT_BT_OFFをv20rと比較した。

historical 5-seed / 100 casesでは、v20r比の主な相対差は、

- H2_RAW +1.58%
- bigram −5.38%（改善）
- ng −0.47%（改善）
- trigram +2.19%
- SPACE_RAW +3.10%
- route56 −0.42%（改善）
- bT_leaf_excess −0.24%（改善）
- glyph_depth −2.81%（改善）
- length_width −4.59%（改善）

で、10%級の重大regressionはない。

fresh 3-seedでも同様に重大regressionなし。

したがってStage 4終了時点の状態は、

`V21R_CANDIDATE_SAFE_LEFT_BT_OFF`

とする。

## 9. 理論上の更新

SLOT仮説そのものはH3 conditionalと低次n-gramを改善したため、

`(H1,W) -> H3 -> H4`

という局所構造は棄却されない。

しかし、H2/H3/H4をSLOTから同時再選択するとSPACE系列へ波及し、生成全体では安全でない。
したがって次にSLOTを再検討する場合は、Stage 4結果を再チューニングするのではなく、**なぜW2 exact-4の局所改善がSPACE_RAWへ伝播するかを独立に分解**する必要がある。
