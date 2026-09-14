# GitHub upload guide

## Repository本体

`HerbalA_v21r_GitHubSafe_20260914.zip` を展開し、その中身を通常のGit repositoryとしてpushする。

```bash
git init
git add .
git commit -m "Publish HerbalA v21r GitHub-safe package"
git branch -M main
git remote add origin <YOUR_REPOSITORY_URL>
git push -u origin main
```

`model/sources/*.zip` と `model/runtime/` は `.gitignore` 済みなので、巨大runtimeを誤ってcommitしない。

## GitHub Release assets

同じrelease/tagへ次の2ファイルをassetとして追加する。

- `EHC1_E1GLOBAL_FULL_20260911.zip`
- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`

`SHA256SUMS.txt` も一緒に置くことを推奨する。

## clone後の利用者

Release asset 2本を同じdirectoryへ取得し、次のいずれかを行う。

```bash
export VOYNICH_V21R_SOURCE_DIR=/path/to/assets
```

または2本を `model/sources/` へ置く。

その後：

```bash
python -m pip install -r requirements.txt
cd model
python code/validate_integration.py --smoke
```

`smoke_hash_identity: PASS` が出れば、元Stage 4 referenceとの生成hash整合性が確認できる。
