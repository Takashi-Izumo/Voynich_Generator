# 第一案R2・raw候補帰属の修正

依頼013の独立再検証は、R1の解消、通常生成・fit・恒等対照・CAL接続、設計訂正012を確認した上で、追加R2により要修正となった。受領reportの27ファイルのサイズ・SHA-256を照合した。

## 問題の再現と修正

修正前に、報告者の `probe_raw_candidate_context.py` をそのまま実行した。実在する候補0から候補1へ最初のraw行のcandidateを付け替え、要求側の候補番号は0のまま、receipt digestとchecksumを更新すると、両順序付きの新規監査と評価前チェックが誤ってPASSした。元生成物は変更せずコピーだけを使った。

問題は、ID・幅・role・digestの結合と「いずれかの候補集合に属する」ことの検査だけでは、結合先候補とraw行のラベルが同一であることを保証できない点だった。

`policy_audit.context_key()` で次の組を共通の厳密なidentityとして扱う。

```text
(page: str, locus: str, segment_id: int, event: int, candidate: int)
```

PF候補の要求区間をauthorityとし、要求側link・gate行・raw行の同じ組を直接照合する。raw行はreceiptループ内で、その要求が属する候補との完全一致を検査する。別の実在候補へlabelを付けても、receiptとchecksumを更新しても拒否する。欠けたfield、bool/float/stringをinteger IDの代わりにする型違いも拒否する。

記録形式はtrace schema v2のまま。生成・fit・RNG・審判の変更はなく、production codeの変更は監査moduleだけ。ただしsource hashが変わるので、旧plan/PASSを再利用せず、新planから生成し直した。

## 検証

| 項目 | 結果 |
|---|---|
| PF unit | 47件PASS（前回39件＋context回帰8件） |
| 既存M1 / 審判 | 27 / 56件PASS、計130テスト |
| 通常順/逆順 | A:2/A:3/G:1、seed91701、3群+REFERENCE、24面PASS |
| 別の恒等plan | 12面、全3群・9ケースが原版と出力・state・実main RNGで一致 |
| BASE対原版・反転 | 意味出力・state・RNGと、両順序の個別coverageがPASS |
| 支持・packing・不正行・末字・PLANT | 全36面で違反0 |
| 前回v2との比較 | fitしたlawと、REFERENCEを含む12ケースの意味出力・最終state・実main RNGが一致 |
| 固定CAL | 9予測・2対比へ接続、再学習/fallbackなし。予測/channelsとmeasurements/summaryの計12ファイルが前回v2とbyte一致 |

## 実データ負例

`tests/run_context_probes.py`で次の11ケースを実行した。tokens・state・RNG・候補・rawの採否やuniform等は変更せず、raw contextと要求側receipt digest、2ファイルのchecksumだけを変更する。

- 実在する別候補へのcandidate付け替え。
- page、locus、segment_id、eventそれぞれの誤結合。
- 別の実在eventのcontext全体への付け替え。
- candidateのfloat/bool/stringへの型変更。
- 両順序に同じ候補誤結合、逆順側だけの候補誤結合。

すべて新規監査が拒否し、失敗後のseal失効と評価前チェック拒否も確認した。各ケースで変更した2ファイル以外の18ファイルがbyte無変更であることを確認している。さらに、報告者の元scriptそのままの両順序ケースと、恒等設定での候補誤結合も拒否した。R2の実データ負例は合計13実行。

前回R1の提供13ケースも再度拒否し、既定の実データ負例6項目も実行した。展開設定と元生成物の改変は元bytesへ復元し、最後の新規正監査・評価前チェックはPASS。R2/R1の追加probeはコピーだけに適用した。

## 受け渡し

本修正は帰属整合性の保証を強めるもの。モデルの改善・同等性・正式採用を主張しない。R1と設計訂正012は独立に確認済みだが、R2修正版の独立再検証は依頼015待ち。

実行root: `/workspace/voynich-results/pf-generation-r2-contextfix-20261105/`。

- study plan: `70ea87ef554bb6114dad8bb5f2aa2ca5d1bac883424f596e1950dd8c1f441b47`
- identity plan: `787e7c1fda748a87483dd9b65dc67bcd785d0cc18cb21e8d1ff55a0109b55335`
- 現在の通常順seal: `required-probes/restored-positive-audit/report.json`

通常順12面のprocessは約83.4秒、最大RSS約423.8 MiB。並行実行を含むsmokeであり、速度優劣や本比較予算には使わない。性能測定・CAL比較・現sealの情報は同梱JSONへ保存。生生成物・正解キー・parent archiveはGitへ含めない。

個別末字/SPACE、能力対照64枝replay、新本比較、正式採用、main mergeは行っていない。原版・既存M1・審判・過去の報告は保持する。
