# v21r GitHub-safe packaging

## 目的

Stage 4 のモデル・パラメータ・保存済み検証結果を GitHub repository に置けるサイズへ縮小しつつ、生成結果の再現性を維持する。

## 変更したもの

GitHub版では、約261 MBを占める次の2 archiveだけをrepository本体から外した。

- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`
- `EHC1_E1GLOBAL_FULL_20260911.zip`

これらはGitHub Release assetとして配布する。内容・ファイル名・SHA-256は元Stage 4 packageと同一である。

`model/code/runtime_bootstrap.py` は、次の順に同じarchiveを探索するように変更した。

1. `VOYNICH_V21R_SOURCE_DIR`
2. `model/sources/`
3. repository直下 `release_assets/`
4. repository直下 `external_sources/`

archiveは展開前に `model/SOURCE_ARCHIVES.json` のSHA-256と照合し、不一致なら実行を拒否する。

## 変更していないもの

- `integrated_sampler.py`
- `integrated_sampler_v21.py`
- `run_model.py`
- `run_model_v21.py`
- SLOT table / model parameters
- Stage 1–4 reference hashes
- 保存済み審判結果
- model candidate / stop decision

Stage 1/2 smoke validatorについては、一時ディレクトリの固定 `/mnt/data` 指定だけを外してOS標準tempへ変更した。生成ロジックには変更がない。

## 注意：historical scripts

rootの `validation/code/` と `contest_200/code/` には、当時の作業環境 `/mnt/data/...` を記録したhistorical scriptが含まれる。保存済み結果のprovenanceを守るため、これらは改変していない。現在の再実行には `model/code/` と `model/validation/code/` を使用する。

## 完全性判定

GitHub版の正式判定は以下を満たすこと。

1. release asset 2本のSHA-256一致。
2. Python compile PASS。
3. `validate_integration.py --smoke` が保存済み3hashと完全一致。
4. Stage 1/2 static validator PASS。
5. Stage 3 validator 5/5 fold PASS。
6. Stage 4 synthetic PASS。

`GITHUB_SAFE_AUDIT.json` に実行結果を保存する。
