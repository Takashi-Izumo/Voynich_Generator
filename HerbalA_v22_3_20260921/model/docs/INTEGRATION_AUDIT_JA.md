# 正式統合監査

実験用 L4-only K16 sampler を standalone 正式ランナーへ移植後、確認済み旧5seedの100ケース（20葉 x 5seed）を再生成した。

比較hash:

- `generated_rows_sha256`: **100/100一致**
- `surface_commits_sha256`: **100/100一致**
- `generation_input_sha256`: **100/100一致**

よって、正式統合による生成ロジック差分は検出されなかった。

詳細: `validation/INTEGRATION_HASH_AUDIT_100.csv`、`validation/INTEGRATION_HASH_AUDIT_SUMMARY.json`。

`code/validate_integration.py --smoke` は source archive hash、Python compile、および fold0/A:2/run91321 の3hash identityを再確認する。
