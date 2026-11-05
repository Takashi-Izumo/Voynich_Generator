# PF生成改善・第1比較の実装側検証

日付: 2026-11-05（日本時間）。ユーザーの「実装」に基づき、設計007の最初の対象である `BASE / PF_GATE / PF_GATE_LENGTH` を実装しました。依頼008の設計レビューが未到着でも、今回の明示的な実装指示を優先しています。設計を独立検証済みとは扱っていません。

## 実装したもの

- 外部16葉・外側test4葉除外によるPF gate offsetと、通常LINE_ENDへ縮約した長さ重みのfit。
- case-local gate adapter、支持内raw再標本化、32回上限とanchor fallback、恒等設定の追加乱数なし経路。
- 凍結原版のPF2候補・LEN1・state/RNG commitを継承したoverlayと、一時的なsampler factoryの復元。
- law・policy・実装・展開済み入力・scopeの封印、生成物と監査receiptのbinding。
- 現在のtraceから確率・採否を再計算する監査、可視/物理幅を区別した診断、固定CALの匿名化・予測保存後の採点。

## 結果

| 検証 | 結果 |
|---|---|
| 新packageのunit | 20件PASS |
| 既存M1 unit | 27件PASS |
| 凍結審判unit | 56件PASS |
| 新生成・通常順/逆順 | 3葉×1seed×4条件×2順序、24面PASS |
| 恒等対照 | 同じ3葉×1seed×4条件、12面PASS |
| 実行予算測定 | 同じ12面を別processで再生成。時間・最大RSSを記録し、通常順と再比較 |
| BASE/原版 | 出力・最終state・実最終main RNGが一致 |
| 恒等設定の全3群/原版 | 9ケースすべてで意味出力・最終state・main RNGが一致 |
| 順序反転 | 9比較ケースの意味出力・state・main RNG・追加policyログが一致 |
| packing・support・不正確率行・末字不整合・PLANT再開 | 監査上の違反0 |
| 固定CAL | 各群3、計9予測を保存後に採点、2対比へ接続 |
| 全外側foldのfit | 5foldで外部16葉の法則を構築。smokeの3foldは再fitして一致 |

予算測定の12面は、入力検査・3fold core読込を含め約73.9秒、生成終了時までの最大RSSは約426.1 MiBでした。各群のengine時間はwarm-upや順序の影響もあるため、速度優劣の比較には使いません。計48面の実行記録と測定値は `summary.json` と `performance.json` に保存しています。

通常順のPF_GATE_LENGTHでraw法則を呼び出した回数は6,229回、親raw drawは20,904回、32回打切りのanchor fallbackは1回（約0.0161%）でした。これは破棄候補・Map内候補・再試行を含む数で、採用語の数ではありません。可視PFは各群6末尾、3葉のみです。能力や改善・採用を結論する標本ではありません。

gate確率は変化しましたが、このsmokeのPF_GATEはBASEと同じ可視PF分布でした。PF_GATE_LENGTHの可視分布は変化しました。これは介入経路と採点接続の確認であり、長語不足の解消・識別率の改善を示す結果とは扱いません。

## 実データ負例

`tests/run_artifact_probes.py`で次を確認しました。

1. 封印後のlaw変更を拒否。
2. 展開済みFROZEN_FOLD_CONFIGSのbeta変更を拒否。
3. 生成tokenを変更しmanifestのchecksumも更新した時、旧PASSによる評価を拒否。
4. 同じtoken改変を新たに監査するとcommit不整合でFAIL。
5. そのFAILで旧AUDIT sealが消えることを確認。
6. 原版REFERENCEの最終RNGと自己hash・MECHANICAL・checksumを整合的に変更しても、BASEとの専用比較で拒否。

すべての入力・生成物は元bytesへ復元しました。最後に通常順/逆順を再監査してPASSとし、現在の有効sealは `probes/restored-positive-audit/report.json` を指しています。旧PASSを復活させてはいません。

## 保存と範囲

実行rootは `/workspace/voynich-results/pf-generation-implementation-v1-20261105/`。このディレクトリには機構smokeの生生成物、全trace、匿名候補、正解キー、予測、採点を分離して保存しています。共有sandboxには計画・集計・監査・テスト結果・hashだけを追加します。正解キーと生生成物は同梱しません。

study plan hashは `32537fffbcb53f9a5cfa03545650cde3fabe816cd19292aa5bd01743e5289152`、identity plan hashは `de01514c5e869b9667e223aec5262f8afa4b704020879adc323736a9edffb131`。実装中に失敗seedの除外・補充や、原版・M1・審判の変更は行っていません。bootstrap100は採点接続smokeだけに用いました。

個別末字とSPACEは後続studyです。審判能力対照の64枝replayは未実装。性能測定は3葉・3fold coreのsmokeであり、全20葉の予算を保証しません。能力対照・本比較の予算と事前計画を整えてから新本比較へ進む必要があります。今回の `promotion=null`。main mergeは行っていません。
