# Release notes — v21r Stage 3

- Stage 2 SAFE_LEFTを固定。
- W2 exact-4 SLOT用のfold別target-blind probability tablesを追加。
- H2はW2-only hierarchical model、inner bifolium CVでcontext depth/alpha選択。
- H3は `P(H3|H1,W)`、W=4..8をexact discrete stateとして保持。
- H4はBODY shared `P(H4|H3)`, alpha=2固定。
- 20 target bifoliaすべてでtraining leakage 0。
- SLOT generatorにはまだ接続していない。
- Stage 2 validator 23/23再現を維持。
