# 第一案R1修正・trace schema v2の検証

受領報告: `d30c376bf9ae55c5080290b1b22e050f8cbedd6c`、独立検証010。報告manifestの24ファイルのサイズ・SHA-256を照合した。通常生成・fit・恒等対照・固定CAL接続は独立再現されていたが、R1により独立結論は `REQUEST_CHANGES`。本修正後も独立PASSを自動で付けない。

## 再現した問題

修正前のcodeと初版の正常生成物を使い、報告者の `probe_missing_policy_traces.py` をそのまま実行した。PF_GATE_LENGTH/A:2のgate57行、raw呼出し1,954行・親draw4,084件を削除し、集計とchecksumを更新すると、新規監査と評価前チェックが誤ってPASSした。両順序から同じ記録を削除しても誤受理した。元生成物は変更せず、コピーだけを使った。

## 修正した照合

```text
PF候補のlegacy proposal_id_start/end
  → 全生成要求（破棄枝・retryを含む）
      → gate query ID・word_index・残り幅
      → END要求: 親Mapの1 + proposal_draws件のraw呼出し
          → call ID・順序・draw件数・raw行digest
  ↔ 候補側のgate/raw counter区間
  ↔ policy traceの全行
```

候補側counter区間はpolicy行配列の長さから作らない。各要求へgateのIDを付け、各raw呼出しのreceiptを既存requestsへ追加する。END raw呼出しの期待数には、元からあるMapのanchor+proposal_drawsを使う。実際の適用範囲はPF END、board LFであり、W2 spliceの別候補数を混ぜない。

欠落・重複・並び替え・範囲外・誤った要求への結合、内側drawの欠落を検査する。gate queryは各候補の語開始と全要求をカバーしなければならず、恒等設定でも記録が必要。complete-segment retryで同じword_index/幅が再登場しても、異なるquery IDで区別する。

反転側も独立にcoverageを監査してから意味出力とpolicy digestを比較する。requestに追加した `pfgen` は生成の意味比較から除くが、coverageとpolicy digestでは検査する。生成法則・乱数の消費は変更していない。

plan・trace・監査/receiptをschema v2へ更新した。旧v1 plan/PASSを再利用せず、全生成を新planから行った。

## 検証結果

| 項目 | 結果 |
|---|---|
| 新package unit | 39件PASS（旧20件＋coverage15件＋CAL契約2件＋旧schema拒否1件＋segment retry1件） |
| 既存M1 / 凍結審判 | 27 / 56件PASS、計122テスト |
| 通常順/逆順 | A:2/A:3/G:1、seed91701、3群+REFERENCE、24面PASS |
| 別の恒等plan | 同じ3葉・4条件、12面。全3群・9ケースが原版と意味出力・state・実main RNGで一致 |
| BASE/原版・順序反転 | 出力・最終state・実main RNG一致、両順序のcoverage PASS |
| 支持/packing/不正行/末字/PLANT | 全36面で違反0 |
| 修正前との比較 | REFERENCEを含む12ケースの元の意味出力・全最終state・実main RNGが一致。fitしたlaw payloadも一致 |
| 固定CAL | 各群3、計9予測と2対比。予測・channelsの6ファイルが初版とbyte一致 |

raw/gateのlogだけでなくrequests側の結合、候補側counter区間もpolicy比較へ含めている。通常PF_GATE_LENGTHの6,229 raw呼出し・20,904 draw・fallback1回は初版と同じ。変化したのは観測・監査契約であり、改善効果を示す比較は行っていない。

## 実データの負例

`tests/run_trace_probes.py`で、コピーへの改変とchecksum更新を行った13ケースをすべて新規監査が拒否した。

- 全消去、gateのみ全消去、gate部分欠落、raw部分欠落、gate/raw重複、raw順序入替。
- 外側raw行を残した内側draw欠落、要求側の結合削除、raw結合とcounter区間もゼロにする改変、誤った要求ID。
- 両順序に同じ全消去、反転側だけの全消去。

加えて、報告者の元scriptそのままの2ケースも拒否した。こちらはtokens・requests・候補・state・RNG等17ファイルが無変更であることを元scriptが検査している。別の恒等planでも全消去を拒否した。合計16回のtrace改変検査すべてが新規監査で拒否された。13ケースでは、各FAIL後のseal失効と評価前チェック拒否も明示的に確認した。

既存の実データ負例6項目（law、展開beta、token+checksumと古いPASS、commit不整合、失敗後seal、自己整合したREFERENCE RNG改変）も再実行した。入力・元生成物は元bytesへ戻し、最後の新規正監査・評価前チェックはPASS。trace負例は元生成物に触れずコピーだけを使った。

## 能力対照の設計訂正

報告の設計上の指摘も妥当。CALは `1-2*abs(F-.5)` で中央が高く両裾が低く、単語NLLのnear/base/farは実descriptorとも同一ではない。旧設計の普遍的な `near > base > far` のCAL順位、無条件75%能力判定は撤回する。

[設計訂正012](../../designs/012-pf-review-corrections/CAPABILITY_CONTROL_ERRATUM.md)で、生特徴の操作確認、scalar校正契約、実テキスト能力対照を分けた。元007は履歴として保存し、修正planには訂正JSONのhashも封印した。凍結typicalityを使った2 unitで、中央/両裾と、距離増加でCALが上がる反例を確認した。審判そのものは変更していない。64枝replayと実テキスト能力対照は未実装・未達成のまま。

## 保存と次の確認

実行root: `/workspace/voynich-results/pf-generation-tracefix-v2-20261105/`。

- study plan: `5dcd7aedf76922e4cba8d87779c54c7692fd7bab9088635757943db53aaa0810`
- identity plan: `62061dc9ff6ff3ad41846c4055af3f78219677b97f85ea7bf473a6194125cced`
- 現在の通常順sealは `required-probes/restored-positive-audit/report.json` を参照。

通常順12面のprocess測定は約89.6秒、最大RSS約426.7 MiB。ほかの生成processと並行したsmokeであり、初版との速度比較や本比較予算には使わない。全20葉×10seedの新本比較、個別末字/SPACE、正式採用、main mergeは実施していない。`promotion=null`。

共有するのは計画・集計・監査・負例・テスト・hashのみ。生生成物・正解キー・親archiveはGitへ入れない。[依頼013](../../requests/013-pf-tracefix-recheck.md)で修正後の独立再検証へ渡す。
