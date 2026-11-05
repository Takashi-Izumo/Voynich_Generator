# 013: 第一案R1・trace schema v2の独立再検証

状態: OPEN。対象は独立報告010のR1修正。開始HEADを記録し、[修正manifest](../implementation/011-pf-tracefix-v2/MANIFEST.json)、[検証記録](../implementation/011-pf-tracefix-v2/VALIDATION.md)、[設計訂正012](../designs/012-pf-review-corrections/CAPABILITY_CONTROL_ERRATUM.md)を確認してください。

旧v1 plan・生成物・PASSを再利用せず、新規rootにschema v2のplanをfitして再生成してください。原版・既存M1・審判・過去の報告・statusは変更しません。

1. PF unit39件、M1 27件、審判56件を実行。
2. A:2/A:3/G:1・seed91701、3群+REFERENCEの通常順/逆順24面、別の恒等planの12面を生成・監査。BASE対原版、最終state・実main RNG、順序、scope、packing/supportを確認。
3. PF候補のlegacy要求区間、gate query ID、全要求、Mapのanchor+proposal_draws、raw call ID/順序/draw数/digestの結合を確認。retry、Map補助候補、破棄枝、恒等設定でも欠落を拒否すること。counterをpolicy配列から数えるだけの保証へ戻っていないか確認。
4. `tests/run_trace_probes.py`の13ケースを実行。集計/checksum更新後の全消去・部分欠落・重複・並替・内側draw欠落・誤結合、両順序同じ欠落、反転側だけの欠落を新規監査が拒否し、失敗でsealが失効することを確認。
5. 報告010の元 `probe_missing_policy_traces.py` も新planへそのまま適用し、通常順と両順序で拒否すること。別の恒等planの全消去も確認。
6. 既定の `run_artifact_probes.py` 6項目を他process停止後に実行し、元bytesへの復元・最後の新規正監査PASSを確認。
7. 固定CALで9予測・2対比へ接続。再学習/fallbackなし。可能なら修正前と意味出力・state/RNG、予測/scoreが保持されることを別途照合。追加request field `pfgen`は意味比較から除くが、coverage/digestでは検査する。
8. 設計007のnear/base/far CAL順位と無条件75%能力基準が訂正されたことを文書確認。これは能力対照の実装・能力PASSではなく、凍結CALを変更する依頼でもない。

詳細な生成/監査/負例コマンドは[実装README](../../../experiments/pf_generation/README.md)。固定CALモデルは依頼010と同じv2 bundleを使えます。新しい本比較、個別末字/SPACE、64枝能力対照、正式採用、main mergeは含みません。

結果は `reports/013-pf-tracefix-recheck-<unique-id>/REVIEW.md` と小さい証拠へ追加し、通常のsandbox commit/pushで返してください。生生成物・正解キー・parent archiveはcommitしません。再検証PASSを新本比較や採用の自動開始にはしません。
