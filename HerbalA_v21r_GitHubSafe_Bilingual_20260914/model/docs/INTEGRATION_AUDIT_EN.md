# Formal integration audit

After porting the experimental L4-only K16 sampler into the standalone formal runner, the verified original 100 cases from five seeds (20 leaves × 5 seeds) were regenerated.

Hash comparison:

- `generated_rows_sha256`: **100/100 match**
- `surface_commits_sha256`: **100/100 match**
- `generation_input_sha256`: **100/100 match**

Therefore, no generation-logic difference caused by the formal integration was detected.

Details: `validation/INTEGRATION_HASH_AUDIT_100.csv`, `validation/INTEGRATION_HASH_AUDIT_SUMMARY.json`.

`code/validate_integration.py --smoke` rechecks source-archive hashes, Python compilation, and the three-hash identity for fold0/A:2/run91321.
