# 第一案R2・raw候補context修正の独立再検証

2026-11-05。依頼015。対象HEAD: `a6873a2f3af64b423411dc9daeb14fa43879dea3`。

**PASS。R2の修正を独立確認した。R1の再発も認めない。** 130テスト、新planからの36面の生成・監査、固定CAL接続が通過し、前回v2の生成挙動が保存されている。今回の範囲で追加の要修正事項はない。

## R2の確認

[policy_audit.py](../../../../experiments/pf_generation/policy_audit.py#L29) の `context_key()` は、page/locusをstr、segment_id/event/candidateをintとして厳密に検査する。要求・gate・raw行の5項目を、要求区間のauthorityである現在の候補へ直接一致させている。raw行の照合はreceiptループ内で行い、digest一致や既存候補集合への所属だけで代替していない。boolやfloatをintとして扱わず、field欠落も拒否する。

前回の `probe_raw_candidate_context.py` を変更せず新rootへ適用した。要求側候補0・raw側候補1の矛盾を入れ、receipt digestとchecksumを更新し、両順序に同じ改変を施したケースは、今回は **`Raw call belongs to another candidate context`** で拒否された。

提供されたcontext負例11ケースもすべて拒否した。5項目それぞれ、別の実在候補/event、float/bool/string、両順序同じ改変、逆順側だけの改変を含む。各ケースで採否・uniform等を変更せず、2ファイル以外の18ファイルがbyte無変更であることもscriptが確認している。失敗後のseal失効と評価前チェック拒否も通過した。

別の恒等planの生成物にも候補誤結合を入れ、単独の新規監査で同じ理由の拒否を確認した。R2に関する実データ負例は11+1+1の計13実行であり、独立した真正面の数ではない。

## 検証結果

| 確認 | 独立結果 |
|---|---|
| 修正manifest | 47ファイルのサイズ・SHA-256一致 |
| PF / M1 / 審判unit | 47 / 27 / 56件、計130件PASS |
| 新規fit | 対象3foldのlaw、外部16葉・test4葉除外・known3未使用のpayload、展開入力・凍結sourceが前回v2と一致 |
| 通常順／逆順 | A:2/A:3/G:1、seed91701、3群+REFERENCE、24面PASS。両順序のcoverageを個別監査 |
| BASE対原版 | 意味出力・最終state・実main RNG一致 |
| 別の恒等plan | 12面。全3群・9比較ケースが原版と一致 |
| 支持 / packing / 不正行 / 末字 / PLANT | 正常生成物の違反0 |
| 前回v2との比較 | REFERENCEを含む12ケースの意味出力・state・実main RNG一致。全要求・candidate・event・gate/raw記録もJSON内容が一致 |
| 固定CAL | 9予測を全保存してから採点、2対比へ接続。再fit・fallbackなし |
| 前回の予測・採点 | predictions/channels 6ファイル、measurements/summary 6ファイルがbyte一致 |
| R2 context負例 | 提供11件＋前回script1件＋恒等設定1件、すべて拒否 |
| R1回帰 | 提供13ケースすべて拒否。seal失効・評価前チェック拒否も確認 |
| 既定の実データ負例 | 6項目を拒否。元bytesへ復元し、最後の新規正監査PASS |

旧plan・生成物・PASSを生成や監査へ流用せず、新規rootで実際にfit・再生成した。前回生成物は挙動保存の比較だけに用いた。新規fitのJSON内容は共有planとも一致した。記録形式はschema v2を維持し、新source hashで封印されている。

原版・既存M1・審判、fit・生成・RNGのproduction codeに差分はなく、変更は監査moduleである。F1LF、PF2候補とLEN1、採用stateと初期argmax由来のmain RNG継続、植物前の切断・図後BODYを維持している。正常生成物のraw呼出し6,229回、親draw20,904回、fallback1回も前回と同じ。

意味比較は既存の計測値等の除外とrequestの観測用 `pfgen` field除外を使用する一方、そのfieldを含む全要求・policy記録も別途そのまま比較した。[比較証拠](prior-comparison.json)参照。

## 入力復元・再現情報

copy-onlyの負例は出力rootを分けて並行実行し、元生成物へ変更を加えなかった。展開入力を一時変更する既定のartifact負例は、それ以外の生成・採点・負例processがすべて終了してから単独実行した。finallyで元bytesへ戻し、新規正監査を実行した。その後、正常seal・全生成manifest・実装source・展開入力を再照合した。

- study plan: `70ea87ef554bb6114dad8bb5f2aa2ca5d1bac883424f596e1950dd8c1f441b47`
- identity plan: `787e7c1fda748a87483dd9b65dc67bcd785d0cc18cb21e8d1ff55a0109b55335`
- 固定CAL: `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`
- ローカルroot: `/workspace/voynich-results/pf-r2-independent-20261105/`
- 通常順の有効seal: `required-probes/restored-positive-audit/report.json`

通常順・逆順・恒等設定のprocess時間は約129 / 133 / 117秒、各最大RSSは約425 MiB。並行実行であり、前回との速度優劣や本比較予算を示さない。

## このPASSの範囲

これは第一案の監査修正と機構の小規模再検証であり、生成品質の改善・同等性・正式採用の判定ではない。可視PF6末尾・3葉・1seedのsmokeから識別性能を推定しない。

前回確認した設計訂正012は維持され、CALの両側性と旧75%能力基準の撤回も継続する。64枝replay・実テキスト能力対照は引き続き未実装・未達成であり、本比較前の未完了事項である。本報告を新本比較・個別末字/SPACE・能力対照実装・正式採用・main mergeの自動開始と扱わない。

本commitは報告directoryだけを追加する。生生成物・正解キー・parent archiveは含めず、実装・status・過去報告を変更しない。[再現手順](REPRO.md)、[概要](SUMMARY.json)、[manifest](MANIFEST.json)を参照。
