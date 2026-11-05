# M1 schema v2の検証記録

独立検証の4指摘に対応して再生成・再検証しました。本比較への移行は引き続き保留です。v1のplan/監査PASSをv2へ読み替えません。詳細は `REVIEW_FIXES.md` を参照してください。

## 独立検証後の回帰確認

- 実runtimeのfold0.beta変更を封印済みplanが拒否し、原バイト復元後に再通過しました。
- 実tokensとmanifest checksumを変更しても古いPASSのexportゲートは拒否されました。
- REFERENCEの最終main RNGとchecksumを変更すると専用比較で拒否され、失敗した再監査は旧sealを残しません。復元後に新しい監査を実施しました。
- END_ONLY 19箇所は全件atom非観測です。構造上の末尾区分、実atom観測、末尾情報利用可否を分離しました。
- 信頼済み親ZIPの展開treeの15,632ファイルを照合し、planへtree hashを固定しています。
- 以下の24頁を新しく再生成し、tokens・最終main RNGはv1の全9群ケースと一致しました。固定CALの予測ファイルもv1とバイト単位で一致しました。生成アルゴリズム・審判は変更していません。


基準: `c610c2a81e733748e0fb246de89143d6ecda764e`。これは実装と接続のsmokeであり、候補の優位性・正式昇格を判断する実験ではありません。

- 新規・回帰unitテスト27件: PASS。救済stateと乱数継続元の分離、救済停止、候補0固定、同点、隠れたmutable state汚染、main RNG汚染、未知pending、mと複合glyph、plan封印、NA/TIE/50%距離、異なるCALモデルの拒否を確認しました。
- 凍結審判の既存56テスト: PASS。
- A:2 / A:3 / G:1、seed 91701を事前固定。3群各3頁＋原版REFERENCE3頁を、通常順と逆順で別processから並行実行しました。最終検証の実生成は計24頁です。
- BASEと原版は3/3ケースでtokens・packing・全commit/request・確率行・PF/PHW候補・route trace・意味のあるMECHANICAL・完全な最終stateが一致。経過秒数とgzipヘッダは比較対象外です。
- 3群とも通常順と逆順で意味出力が完全一致。状態混入を検出しませんでした。
- BASEのPFイベントは計7、追加救済探索24枝、救済採用1回。非救済2群は追加探索・救済採用とも0。PF_ANCHORは全イベントで候補0を採用し、元argmaxからの変更が2回ありました。
- 全ケースでpacking正常、支持外・不正行・末字不整合・植物再開の偽HEAD/W2は0。候補branchの全segmentが実出力と一致し、rareとRNG継続元も監査しました。
- PF介入集合とPARA_ENDの対応、FULL/END_ONLY/NONE、非介入理由を `validation/scope_ledger.json` と `mechanical_report.json` に保存しています。

## 固定CALモデルとend-to-end接続

仕様書に記載された別チャットのモデルファイルは当初この環境にありませんでした。凍結v0.3の `fit` を、変更していないadapterが作る真正80面だけのcorpusへ適用して復元したところ、**指定model-set hashと完全一致**しました。

```text
extractor  5b74ed23eda0cad35377e0786f0c3aa8cc7375a033bb6cdc7ed81b98e343bc37
protocol   007d2c9556c5f19a72aa044aa01cf6bf6cbe60f7296e50504112242cf97896f0
model_set  61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79
```

一致したこのモデルのみを使用し、3群各3trialについて匿名化→形式検査→全予測の保存→正解による採点→2つの対応比較まで成功しました。primaryは明示的なJ24.CALで、PROTOへのfallbackはありません。原版のCAL/PROTO各viewとchannelも保存されています。予測は `--jobs 2`、smokeの記述bootstrapは100反復です。

3葉×1seedの値から改善・悪化・有意性を結論しません。能力対照、全20葉×10seed、独立一般化、採否の許容幅・多重比較方針の合意は未実施です。出典Stage1表の照合も未解決のままです。

## 成果物

- `validation/plan.json`: 実行前に封印した比較条件、凍結source・overlay・元データhash。
- `validation/scope_ledger.json`: 機構対象と審判対象の対応。
- `validation/mechanical_report.json`: 原版一致、順序反転一致、各群の機構・mask集計。
- `validation/summary.json`: テスト数、実行数、モデル照合、CAL接続の記録。
- `validation/input_probe.json` と `regression_probes.json`: 設定変更・古いPASS・RNG改変の拒否を実データで確認した記録。

v1の記録は新しい成果物rootの `v1-records/` と旧公開ZIPに保存しています。
- 生の生成物、モデル、匿名入力、正解、予測、採点・対比は `/workspace/voynich-results/m1-pf-reviewfix-v2/` に分離して保存しました。これらの大きな成果物や正解はGitへ追加していません。

原版v22.3・親runtimeのコード・審判v0.3に差分はありません。作業ブランチは `experiment/m1-pf-ablation`。この段階ではcommit/pushしていません。
