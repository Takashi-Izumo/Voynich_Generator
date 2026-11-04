# v22r 外部ソースアーカイブ

GitHubリポジトリ本体では、100 MBを超える凍結親ソースZIPを追跡しません。
GitHub Release asset `HerbalA_v22r_Release_Source_20260917.zip` をリポジトリルートへ展開すると、次の2ファイルがこのディレクトリへ復元されます。

- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`
- `EHC1_E1GLOBAL_FULL_20260911.zip`

SHA-256は `SOURCE_ARCHIVES_SHA256.csv` を参照してください。
これら2ファイルが存在すれば `model/code/runtime_bootstrap.py` が初回実行時に `model/runtime/` へ展開します。
