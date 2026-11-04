# Change log

## 2026-09-12 — PROMOTED

親 `PUV + BODY-R4 0.85 + adaptive leaf-excess` に、検証済み `W2 exact-L4 K16 legal same-width H2-only splice` を正式統合。

除外した試行:

- W2 known3 residual: probability-level signal はあるが動的生成で昇格せず
- full-word H1-fixed sibling: W2局所改善するが全体n-gramを悪化
- W3 terminal weakening/bridge: terminal feedbackは確認したが全体救済せず
- L3: bT terminal bigramを悪化
- L5/L6+: L4効果を希釈/逆転
- K32: K16より高コストかつ主要指標で劣後

## 2026-09-13 — Stage 4

- `SAFE_LEFT_BT_OFF` を正式対照として追加し100-case hashを固定。
- `w2_slot_generator.py` を追加。
- Stage-3 H2/H3/BODY-H4 tableをW2 exact-4生成へ接続。
- SLOT専用RNG `V21_W2_SLOT_SELECT_V1` を実装。
- fallbackを SAFE_LEFT_BT_OFF → anchor の順に実装。
- 3-seed screen 240 casesを実施。
- mechanical invariantsはPASS、H3 conditionalとbigram/ngは改善。
- `SPACE_RAW` +16.09%, p≈0.010 のためSLOTを3-seedで停止。
- `SAFE_LEFT_BT_OFF` をv21r候補に指定。
