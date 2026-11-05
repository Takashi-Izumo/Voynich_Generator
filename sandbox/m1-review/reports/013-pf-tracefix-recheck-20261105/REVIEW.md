# 第一案 trace schema v2 独立再検証

2026-11-05。依頼013。対象HEAD: `7db514606b2b77640a3f8454acd4c7b1abbc4a7c`。

**前回のR1（介入ログ欠落の誤受理）は解消を確認した。今回の結論は追加指摘R2により要修正。** 正常生成・恒等対照・固定CAL接続は独立再現でき、修正前の生成挙動も保存されている。問題箇所は第一案の監査コードである。

## R2 — P2: raw記録の候補番号が結合先の候補と矛盾しても監査を通過する

対象: [policy_audit.py のraw/request照合](../../../../experiments/pf_generation/policy_audit.py#L81)（行81–89）と、後段の `key(row) in keys` 検査。

raw行の `request_id`、`gate_query_id`、word_index、残り幅、roleは要求と照合するが、raw行自身のpage/locus/segment/event/candidateを、その要求が属する候補と照合していない。後段のkey検査は「いずれかの既存候補に属する」ことしか確認しない。

独立生成物の別コピーで、次を再現した。

1. `PF_GATE_LENGTH / A:2 / 91701` の最初のraw行（call_id=0、request_id=386、event=0）の `candidate` を0から、同じeventに実在する1へ変更する。
2. 要求側の `pfgen.candidate=0`、gate ID、候補windowはそのまま保持する。raw行と要求側の候補番号は明示的に矛盾する。
3. 要求側receiptの `row_sha256` と、変更した2ファイルのmanifest checksumを更新する。tokens・state・RNG・候補・raw採否・集計値は変更しない。
4. 逆順生成物のコピーにも同じ不整合を入れ、新規の反転付き監査を実行する。

**結果: 監査PASS、評価前チェック `audited()` も受理。** [証拠JSON](raw-candidate-context-probe.json)と[再現script](probe_raw_candidate_context.py)を参照。改変コピーで新しい予測・採点までは実行していない。

本件はraw traceの枝別の帰属整合性を保証するための修正である。現在の記録形式では要求側IDから候補0へ結合される一方、raw行のラベルは候補1を示せるため、raw行の候補ラベルを使う分析に矛盾を持ち込める。正常な12ケースの生成出力・state・実main RNGは、修正前と一致している。

修正案は、receiptを検査しているループ内で、raw行の `(page, locus, segment_id, event, candidate)` と現在のcandidateの同じ組を厳密に一致させること。digest一致や既存候補集合への所属検査だけで代替しない。候補番号だけでなく、他のcontext項目の誤結合も負例へ追加してほしい。checksumとreceipt digestを更新した場合、両順序に同じ不整合を入れた場合も拒否し、正常対照を通す。

## 前回R1の解消確認

新規rootでschema v2のplanをfitし、36面を新たに生成した。旧v1 plan・生成物・PASSは生成・監査の入力として流用していない。v1生成物を使ったのは、挙動保存の比較だけである。

修正はpolicy配列の件数照合から進み、次の独立した記録を結び付けていた。

- 候補のlegacy proposal ID区間と、破棄枝・retryを含む要求。
- 候補側のcounter区間、gate query ID、語開始位置・幅。
- 親Mapが元から記録する `1 + proposal_draws` とraw呼出し数。
- raw call ID・順序・内側draw件数・行digestと、要求側receipt。
- 逆順側の個別coverage監査と、その後の意味出力・policy比較。

親Map実装のanchorと補助drawの呼出しもソースで照合した。候補counterはpolicy行配列の長さから再構築しておらず、配列欠落時にも期待区間が残る。恒等設定でも記録を要求する。

提供された13分類の負例はすべて拒否した。全消去、部分欠落、重複、順序入替、内側draw欠落、要求側link削除、raw link/windowの同時消去、誤ったrequest ID、両順序同じ欠落、逆順側だけの欠落を含む。各失敗後のseal失効と評価前チェック拒否も確認した。

さらに報告010の元scriptをそのまま新planへ適用した2例も拒否し、17ファイルが無変更であることをscript自身が検査した。別の恒等planでも全消去を拒否した。恒等設定では単独監査と、同じ恒等出力のコピーをrepeatにも指定した監査を実施した。このrepeatは新たな逆順生成とは数えない。

## 検証結果

| 確認 | 独立結果 |
|---|---|
| 修正manifest | 48ファイルのサイズ・SHA-256一致 |
| PF / M1 / 審判unit | 39 / 27 / 56件、計122件PASS |
| 新規fit | 対象3foldのlawが修正前と一致。外部16葉・test4葉除外・known3未使用のpayload、凍結source、展開入力も一致 |
| 通常順／逆順 | A:2/A:3/G:1、seed91701、3群+REFERENCE、24面PASS。両順序のcoverageを個別監査 |
| BASE対原版 | 意味出力・最終state・実main RNG一致 |
| 別の恒等plan | 12面。全3群の9比較ケースが原版と一致 |
| packing / support / 不正行 / 末字 / PLANT | 正常生成物の違反0 |
| 修正前との比較 | REFERENCEを含む通常順12ケースの意味出力・state・実main RNG一致。候補とraw/gate記録の元の値も一致 |
| 固定CAL | 9予測を全保存してから採点、2対比へ接続。再fit・fallbackなし |
| 修正前の予測・採点 | predictions/channelsの6ファイル、measurements/summaryの6ファイルがbyte一致 |
| 提供trace負例 | 13/13拒否、seal失効・評価前チェック拒否も確認 |
| 前回の再現script | 通常監査・両順序で拒否。恒等設定の全消去も拒否 |
| 既定の実データ負例 | 6項目を拒否。他process終了後に実行し、元bytesへ復元、最後の新規正監査PASS |
| 追加の候補context負例 | **誤受理。R2** |

意味比較では既存の計測値等の除外に加えて、requestsへ追加した観測用 `pfgen` fieldを除く。そのfieldはcoverage/digestで検査する。候補の新規 `pfgen_trace`、raw/gateの新規IDを除いた元の記録内容も別に比較した。F1LFを含む原版・既存M1・審判のsourceに変更はない。植物前の切断・図後BODYも既存機構を維持している。

正常生成物のraw呼出し6,229回、親draw 20,904回、fallback1回は修正前と同じ。各段階の分布は[diagnostics](diagnostics.json)参照。これは破棄枝・Map補助候補・retryを含む回数である。

## CAL順位条件の訂正

[訂正012](../../designs/012-pf-review-corrections/CAPABILITY_CONTROL_ERRATUM.md)は前回の設計上の指摘に対応している。単語NLLのnear/base/farから普遍的なCAL順位を導かず、旧75%基準の自動適用を撤回している。生特徴の操作確認、scalar校正契約、実テキスト能力対照を分け、操作不成立を審判能力不足と区別する。対象channelの中央/両裾の期待を、J24/ATOM総合得点の順位へ拡張していない。

新planに訂正JSONのhashが封印されていること、旧v1 planが拒否されること、凍結CALを変更していないことも確認した。2 unitが示すのは校正関数の中央/両裾の契約であり、実テキスト能力ではない。64枝replay・能力対照は引き続き未実装・未達成である。

## 保存と次の対応

- study plan: `5dcd7aedf76922e4cba8d87779c54c7692fd7bab9088635757943db53aaa0810`
- identity plan: `62061dc9ff6ff3ad41846c4055af3f78219677b97f85ea7bf473a6194125cced`
- 固定CAL: `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`
- ローカルroot: `/workspace/voynich-results/pf-tracefix-independent-20261105/`

通常順・逆順・恒等のprocess時間は約199 / 240 / 209秒、最大RSSは約424–427 MiB。3processが重なっており、速度の優劣や本比較予算には用いない。

R2の追加検査後にも、元生成物・正常seal・source・展開入力を再検証した。通常順の有効sealは `required-probes/restored-positive-audit/report.json` を指す。改変コピーのPASSは正常生成物へ持ち込んでいない。

実装側へはR1の解消と設計訂正を確認した旨、およびR2の修正と負例追加を返す。原版・審判・生成法則の変更を要する指摘ではない。新本比較、個別末字/SPACE、能力対照実装、正式採用、main mergeは開始していない。改善効果・同等性は判定していない。

本commitはこの報告directoryだけを追加する。生生成物・正解キー・parent archiveを含めず、実装・status・過去報告を変更しない。[再現手順](REPRO.md)と[manifest](MANIFEST.json)を参照。
