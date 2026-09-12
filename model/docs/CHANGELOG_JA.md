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
