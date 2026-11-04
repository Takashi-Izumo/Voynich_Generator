# HerbalA v20r — 2026-09-12

正式モデル: `RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16`

このZIPは v20r の再実行・監査に必要な**全コード、設定、依存source archive、20-seed昇格審判結果、200セット勝負の全結果**をまとめた正式リリースです。

## 構成
- `model/`: 正式モデル本体。コード、設定、依存source archive、統合hash監査、昇格検証。
- `validation/code/`: 20-seed最終審判・集計コード。
- `validation/results/`: 20葉×20seedの全最終審判表、多重比較・収束表。
- `contest_200/`: 200セット勝負の実行コード、blind key、全スコア、葉別/seed別結果、判定。
- `MANIFEST_SHA256.csv`: 本ZIP収録全ファイルのサイズとSHA-256。

## v20r機構
W2 exact length=4 のときだけ K=16 sibling pool を構築し、H1/H3以降/terminal/exact length/physical widthを保持したまま、合法support内でH2だけを再選択します。

## 20-seed昇格結果
親比: bigram 約 -2.15%、ng 約 -2.34%、trigram 約 -2.63%。
REGRESSION 5指標のHolm補正後も3指標は有意。SPACE_RAW / route56 / bT leaf-excess / length-width は実質不変。

## 200セット勝負
fresh seed 10 × 20葉 = 200セット。combined judge は実測96 / 疑似104、葉単位10/20 vs 10/20でchance水準。

注: 生生成頁の巨大アーカイブは配布容量の都合で本ZIPには重複収録していません。審判に使用した全結果表・コード・blind key・依存ソースは収録済みです。
