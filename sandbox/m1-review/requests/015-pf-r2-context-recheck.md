# 015: 第一案R2・raw候補context修正の独立再検証

状態: OPEN。[検証記録](../implementation/014-pf-r2-contextfix/VALIDATION.md)と[manifest](../implementation/014-pf-r2-contextfix/MANIFEST.json)を確認し、開始HEADとファイルhashを記録してください。元の依頼013、独立報告013、訂正012も背景として参照できます。

R1と訂正012は前回独立確認済みです。今回の修正対象は、raw記録の5項目 `(page, locus, segment_id, event, candidate)` と、その要求が属する候補との厳密な一致です。記録形式はschema v2のままですがsource hashが変わったため、旧plan/PASSを使わず、新しいrootで再fit・再生成してください。

1. PF unit47件、M1 27件、審判56件を実行。
2. A:2/A:3/G:1、seed91701、3群+REFERENCEを通常順/逆順に生成して24面を監査。別の恒等planで12面を監査。BASE/原版、最終state・実main RNG、両順序の個別coverage、支持/packing/末字/PLANTを確認。
3. `tests/run_context_probes.py` の11ケースを実行。5項目個別、別の実在候補/event、型違い、両順序同じ改変、逆順側だけの改変を、receiptとchecksum更新後の新規監査が拒否すること。失敗後sealと評価前チェックも確認。
4. 報告013の `probe_raw_candidate_context.py` をそのまま新rootへ適用し、元の再現ケースが拒否されること。別の恒等planでも候補誤結合を拒否すること。
5. R1の提供 `run_trace_probes.py` 13ケースを回帰確認。既定 `run_artifact_probes.py` 6項目は他process終了後に実行し、元bytesへの復元と最後の正監査PASSを確認。
6. 固定CALで9予測・2対比へ接続。全予測保存後に採点し、再学習/fallbackは行わない。可能なら前回v2と意味出力・state/RNG、予測・採点を比較する。

実装手順は[README](../../../experiments/pf_generation/README.md)。固定CAL model-setは従来の `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。生成法則・原版・M1・審判・status・過去の報告は変更しません。

結果は `reports/015-pf-r2-context-recheck-<unique-id>/REVIEW.md` と小さい証拠へ追加し、通常のsandbox commit/pushで返してください。生生成物・正解キー・parent archiveはcommitしません。新本比較、個別末字/SPACE、能力対照実装、正式採用、main mergeはこの依頼に含めません。
