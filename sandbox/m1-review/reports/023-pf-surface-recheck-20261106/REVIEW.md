# 修正022の独立確認

**PASS_INDEPENDENT_MECHANISM_RECHECK。生成器の末字commit不整合と対照CLIの修正を独立に確認した。審判能力は未確認のまま。** 開始source HEADは `43a6895`。実装・原版・審判・status・requestは変更していない。

## 実行結果

| 確認 | 独立結果 |
|---|---|
| manifest/source | 実装020の77項目をサイズ/SHA-256で照合。凍結501file、生成source41fileも一致 |
| unit | PF58 / controls33 / M1 27 / judges56 = **174件PASS**。literal parent commit chainの境界fixtureを含む |
| fresh plan | smoke/identity/fullをfitし直し、実装020と完全一致。新full `5f0e657be62f5541ef16b40737d44f86bca70cdf990985154693a7fbacb6954a`。旧fullは新sourceで拒否 |
| 通常順・逆順 | A:2/A:3/G:1×seed91701/91711×4群×2順序＝48面を新規生成。意味出力・全最終state・実main RNG・policy traceが一致し、監査PASS |
| 恒等設定 | 3葉×seed91701×4群＝12面を新規生成。原版REFERENCEと一致し、監査PASS |
| 問題の実ケース | **A:3/91711/PF_GATE_LENGTH** のf6v.10、proposal630のsemantic末字と次のrequest631のprev_terminalがともに**ID12**。原版assertもPASS |
| 既存正常経路 | 以前の独立R2検証12ケースと、意味出力・全最終state・実main RNGが完全一致。さらに54ファイルの全request/candidate/event/gate/raw記録が一致 |
| 末字負例 | receipt除去＋件数0化、次語の古い状態、誤状態に合わせたcommit鎖偽造を両順序のcopyへ入れ、3種類すべて意図した理由で拒否。seal失効と評価前チェック拒否も確認 |
| R1/R2回帰 | copy-onlyの13＋11件を拒否。元の生成物を保存し、失敗した監査の旧PASSは失効 |
| 既定の6項目 | law/展開設定/生成物＋checksum/可視commit/失敗seal/REFERENCE RNGを確認。展開設定を触る検査は排他実行し、finallyで復元。最後の正監査PASS |
| 対照の実CLI | fresh A:2/92101の128枝を生成・全枝再生監査・exportし、**実際のverify-export CLIが成功**。正解を改変して適切に再封印したexportは、同じ実CLIが内容不一致として拒否 |
| 対照生成の保存 | BASE・snapshot・128donor・選択recordは旧全対照のA:2と完全一致。異なるのはplan bindingとそれに伴う外側sha256だけ |
| 固定モデル | 凍結CAL model set `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79` の実payloadを照合。refitなし |

新規PF検証面は60面であり、反復を独立した真正標本とは数えない。拒否・失効確認は13＋11＋3＋6＋実CLI1の34項目。raw語は共有せず、問題ケースは [FIXED_CASE.json](FIXED_CASE.json) に位置・末字ID・hash・receiptだけを保存した。

## コード確認

候補2群だけにsurface commit境界のadapterを重ね、m/rare後の最終可視H1/H2を親のsemantic commitへ渡す。routeへ渡すanchor・stable_seqを保持し、元のH1/H2処理とpending H1統計を実行する。追加の乱数はない。非末字のH2、変更なし、rare suffix、F1LF/Stage3Dは親へ委譲する。BASE/REFERENCEはliteral原版のまま。

新監査は、準備済み補正とpost-m anchorからreceiptの必要性を導き、最終surface→semantic末字→次の要求の鎖を検査する。検証した実ケースと負例では、生成後のログだけを合わせる処理ではないことを確認できた。

## 検証側スクリプトの復旧記録

途中に検証側ハーネスの2点を訂正した。失効したsealを評価前チェックが読む際のFileNotFoundErrorを期待例外へ加えたことと、`unseal()`が検証済みsha256を保持するため、plan変更に伴う外側sha256も意味内容の比較から除いたことである。不正exportの再封印でも旧sha256を除いてから新checksumを作った。

生成器や監査を変更せず、完了した60面・unit・正監査は保存し、未完了の検査から再開した。最終的な不正キー拒否は、checksumの誤りではなく**Export assignment/text/key/diagnostic mismatch**による拒否である。[HARNESS_RECOVERY.json](HARNESS_RECOVERY.json) と各command結果を残す。

## 結論と後続

末字commitとCLIの修正を受理できる。**CAPABILITY_NOT_VERIFIEDは変更しない。** 報告019のJSD飽和、末字/SPACE操作不足は未解消で、新審判・donorは設計021だけ。[設計コメント](DESIGN_021_REVIEW.md)を実装側へ返す。

既存の本比較指示と記述的実行方針を継承し、[新実行登録024](../024-pf-repaired-full-comparison-20261106/PROTOCOL.md)を新source/planへ結合して全800面を新rootへ生成する。旧421面は継ぎ足さず、全予測保存前の採点、seed差替え、品質・同等性・採用の主張は行わない。
