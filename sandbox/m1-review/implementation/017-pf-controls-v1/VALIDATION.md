# PF能力対照replay v1: 実装・検証記録

2026-11-05。報告015のR2独立PASS、報告016の対照契約を受領し、`experiments/pf_controls/` を追加した。原版・M1・審判・既存 `pf_generation` の生成ソースは変更していない。設計は [017](../../designs/017-pf-controls-v1/DESIGN.md)、独立確認依頼は [018](../../requests/018-pf-controls-independent-check.md)。

**機構smokeと対照の構築・照合はPASS。審判能力・モデル改善は未判定。** 全対照の生成/予測/採点と800面本比較は実装側で開始していない。末字/SPACEには多数の変更不能例があり、全20葉で能力基準を満たすとは主張しない。

## 確認範囲

| 項目 | 結果 |
|---|---|
| unit | controls31 / PF47 / M1 27 / judges56、計161件PASS |
| 新規smoke | A:2/A:3/G:1、第4面、seed92101 |
| BASE無影響 | 観測あり3面とliteral原版3面の全意味出力・最終全state・実main RNG一致 |
| PF入口 | generator PF7イベント、うちFULL atom対象6。FULL対象外1を昇格しない |
| 隔離再生 | 予定7×64=448枝、実生成448枝。支持・同容量packing・末字/PLANT・親state/RNG/rare/route/採番を検査 |
| class control | 継承した実効32項目とH1 baselineを保存、configure前のdata属性へfinally復元 |
| 新規監査 | 提示recordを信頼せず、元入力から全BASE軌道と448枝を再生。全record一致、PASS |
| 対照export | 3family×near/far×3面=18caseを構築。真正側、全選択、入力・キー・mask/layoutを再構成照合、PASS |
| 5fold proxy | 外部16完全葉×4面。PF末尾数96/94/96/98/96。test4葉全体とtarget known3を新表から除外 |
| 全対照plan準備 | 20葉、FULL PF18葉29末尾、SPACE17葉27末尾、全106予定variant。fit/封印のみ |
| 固定審判 | 既存model-set・extractor・protocol hashと20cluster bindingを照合。新しい予測/再fit/fallbackは未実行 |
| 本比較plan | 既存40source・凍結501fileを照合。hash `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17` 維持 |

新規監査の再生は同じ3葉/seedの反復であり、追加の独立真正標本ではない。smokeは6末尾しかatomへ渡らず、独立葉10以上の能力基準の代わりにはならない。

## 変更不能・操作成立の実測

| family | near選択末尾 / 対象6 | far選択末尾 / 対象6 | near対象特徴変更面 / 3 | far対象特徴変更面 / 3 |
|---|---:|---:|---:|---:|
| length_width | 6 | 6 | 3 | 3 |
| terminal | 1 | 1 | 1 | 1 |
| space_T_H1 | 2 | 2 | 0 | 2 |

末字は方向別5末尾、SPACEは方向別4末尾が `NO_MATCH_WITHIN_64`。そのまま未変更の予定variantを含めてexportした。SPACE nearではtextが変わった2面でも、真正原面に対する対象SPACE countの変化は0面だった。生成BASEに対するproxy NLLの操作と、真正面に対する対象feature操作を分けて記録している。

この3葉の末字/SPACE操作成立率は80%未満である。3葉での正式能力合否は判定せず、全cohortで検証側が独立確認する。支持上の不可能とは呼ばず、枝数増加・seed差替え・filter緩和・有利なsubsetへの変更も行っていない。全対照でも成立率不足なら `MANIPULATION_NOT_REALIZED` として停止/報告し、能力不足と混同しない。生NLL順位からCAL順位や正解を作らない。

## 負例

最終コードに対する全負例の完了記録は `probes-summary.json` を参照する。生成物の改変は別copy、展開入力は編集しない。対象は欠落・重複・既存eventへの誤結合・float枝ID・内側要求context・snapshot receipt・選択・support・main RNGの改変、古いPASS、target known3混入、exportのキー漏洩/型違い/正解改変、例外とroute/request/class control/rare clone汚染である。

**20件すべて拒否。** 生成copy11件はreceiptと生成checksumを更新しても古いPASSを受理せず、新規監査も拒否し、失敗後のsealを失効させた。うち内側要求contextとmain RNGの偽造は構造照合だけで済ませず、実際のfresh再生との不一致で拒否した。ほかにtarget known3混入1件、再封印したexport3件、実行中の例外/route/要求採番/class control/rare clone汚染5件を確認した。最後に通常BASEを再生成し、元の全意味record hashと一致させ、正例のsealとexportを再照合した。

## 時間・RSSと保存先

最終版の生成は約106.0秒、同じrecordのfresh再生監査は約155.2秒。単一pipeline processの各段階までの累積最大RSSは生成731.7 MiB、監査876.8 MiB。計画作成・loadも含むprocess高水位であり、処置単独のメモリ量や全対照の予算ではない。ほかの段階は同梱performance JSONを参照する。

最終負例scriptは別processで約364.6秒、最大846.5 MiB。上記smokeと同じケースの繰り返しを含み、20の独立真正標本を意味しない。

- smoke plan: `37bf96f5fae1efe46ff1342f0755b35d0924411d47591460bb9d6df810743135`
- full control plan: `33b7d30a29c3494e4d95fc25fa479df69fa24e10150050f2454d13fb824e3e76`
- 生生成物・snapshot・正解キー: `/workspace/voynich-results/pf-controls-implementation-20261105/handoff-v1/`。Gitへ含めない。
- 共有するのはplan、集計、監査report、hash manifest、unit log、再現手順のみ。各planの `sha256` はcanonical plan hashで、ファイルSHA-256はmanifestに別記する。

実装途中の試運転や中断した負例rootは最終証拠に数えない。環境の再接続で負例processのstdout先が失われたため、負例は新root `probes-final`、durable logへ切り替えて再実行した。正例のsource/plan/生成物/監査sealは復帰後にも照合した。

## 未実行事項と受け渡し

replay・export・auditと評価CLIは実装済み。実データの全106対照の予測/採点、far3channelの能力判定、800面本比較は検証側の作業として未実行。評価の「全予測を先に保存」「固定model相違で予測前拒否」「同点1/2・NA分母・葉bootstrap・nearをgateへ使わない」はunitで確認し、モデルの実体hashも照合したが、全対照での実行確認はまだ行っていない。

`CAPABILITY_RESULTS.json` は計算結果であり、検証側の `PASS_CAPABILITY_REVIEW` を自動発行しない。main merge・正式採用・個別末字/SPACEの生成器本体studyも今回の成果に含めない。[CLIと再現手順](../../../../experiments/pf_controls/README.md)から新rootで独立確認できる。
