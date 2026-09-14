# PUV 現行実装・チャット引き継ぎパッケージ

## 現在の正本

**RMW1-BTI2-EHC2-DECOMP1 PUV**

- `eta_U = 0.5`
- `eta_V = 0.5`
- 5/5 outer foldで同一係数をtraining-only inner-LOBOから選択
- 現在の正式状態: **構造部品として支持 / 正式BTI2後継には未昇格**
- RBS1_STRICT: **不採用**
- SEC1: **SEC0 FAILのため未実装**

## このパッケージの目的

次のチャットへ、このZIPひとつを移せば現在地点から再開できるようにする。

含有物:

- `current_model/`: 現行PUV Stage6の全実装コード・係数・5seed confirmation出力
- `parent_runtime/`: 凍結親 `EHC1_E1GLOBAL_FULL_20260911.zip`
- `source_spec/`: EHC2-DECOMP1仕様書
- `provenance_archives/`: Stage4統合監査・Stage5 screeningの完全アーカイブ
- `diagnostics_history/`: bT/RBS1、visitation、state occupancy、SEC0の棄却・診断記録
- `OPEN_ISSUES_JA.md`: 現時点の未解決問題
- `NEXT_CHAT_STARTER_JA.txt`: 次チャット冒頭に貼れる要約
- `REPRODUCTION_GUIDE_JA.md`: 再実行方法
- `SEED_LEDGER.json`: 使用済み/未使用seed

## 最重要な現在結果

Stage6 confirmation (`91321–91325`, 20 bifolia × 5 runs):

BTI2_BASE比:

- SPACE_RAW: **-20.97%改善**, Holm p=0.0240
- H2_RAW: **-13.28%改善**（非有意）
- H1 target JSD: **-9.69%改善**
- T-H1 joint JSD: **-8.74%改善**, p=0.000565

一方:

- ng: +13.62%回帰警告
- bigram: +14.14%回帰警告
- trigram: +16.34%回帰警告
- token count MAE: +17.83%
- mean length MAE: +21.21%
- mean width MAE: +19.60%

よって正式昇格なし。

## 重要な後続診断

1. SHAPE_LOCKでtoken/mean length/mean widthドリフトは消える。
   → 頁平均shape driftはstate/packing feedback由来。

2. しかしn-gram回帰はSHAPE_LOCK/REQUEST_LOCKでも残る。
   → shape/prevT/route feedbackだけが原因ではない。

3. H1-H2語頭bigramはPUVで改善。
   → H1-H2 compatibility不足説は棄却。

4. state occupancy単独はPUVの方がむしろ良い。
   → occupancy-only controllerは不適切。

5. 問題は `PUV occupancy × PUV conditional emission` のinteractionとして現れる。

6. ただしknown3+externalだけでその危険interactionを予測するSEC0はFAIL。
   → SEC1 gateは実装しない。

詳細は `OPEN_ISSUES_JA.md` と `diagnostics_history/` を参照。
