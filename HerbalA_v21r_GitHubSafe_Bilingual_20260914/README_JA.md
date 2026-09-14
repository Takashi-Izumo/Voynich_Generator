# HerbalA v21r Stage 4 — SLOT SCREEN

Stage 3のouter-bifolium blind SLOT tableを実際のW2 exact-4生成へ接続し、正式な `SAFE_LEFT_BT_OFF` 対照と比較したStage 4パッケージです。

## 結論

- Stage 1 `V20_COMPAT`: **300/300 hash match PASS**
- Stage 2 `SAFE_LEFT_BT_ON`: **300/300 hash match PASS**
- Stage 3 table leakage/probability audit: **5/5 fold PASS**
- `SAFE_LEFT_BT_OFF`: 100-case固定hashを新規作成
- SLOT synthetic: PASS
- 91401–91403 screen: 4 arms × 60 casesを完走
- SLOT mechanical: packing 100%, support violation 0, invalid 0, fallback 0%
- pooled `P(H3|H1,W)` conditional JSD: **0.320282 → 0.240830 改善**
- bigram: **約18.5%改善**
- ng: **約9.9%改善**
- trigram: 約0.61%悪化
- `SPACE_RAW`: **約16.1%悪化、paired p≈0.010**

したがって仕様のscreen stop ruleに従い、**SLOTは3-seedで停止**しました。91404–91420は実行していません。

Stage 4終了時点のv21r候補は、

`SAFE_LEFT_BT_OFF`

です。historical 5-seedおよびfresh 3-seedでv20rに対する10%級の重大regressionはありません。

詳細：`model/docs/V21_STAGE4_IMPLEMENTATION_JA.md`

## GitHub-safe版について

GitHub版では、モデル状態・パラメータ・検証結果はそのまま保持し、巨大なruntime source ZIP 2本だけをrepository外のRelease assetへ分離しています。再実行時は `model/SOURCE_ARCHIVES.json` のSHA-256で必ず検証されます。

詳細は `GITHUB_SAFE_PACKAGING_JA.md`、再実行は `model/docs/STAGE4_REPRODUCTION_GITHUB_JA.md` を参照してください。
