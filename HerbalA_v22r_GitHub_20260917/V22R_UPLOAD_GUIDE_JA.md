# HerbalA v22r — GitHub / Release 配布手順

## 1. GitHubリポジトリ本体

`HerbalA_v22r_GitHub_20260917.zip` の内容をリポジトリルートへ配置します。

この本体にはコード、parameter、仕様書、履歴、self-test、fresh-200審判証拠、SHA-256台帳が入っています。

巨大な凍結親ソースZIPはGitHub通常リポジトリへ入れません。

## 2. GitHub Release

タグ例：`v22r`

Release assetとして次をアップロードします。

- `HerbalA_v22r_Release_Source_20260917.zip`
- `HerbalA_v22r_Release_Source_20260917.zip.sha256`

必要ならGitHub本体ZIPとそのSHA-256も同じReleaseへ添付できます。

## 3. 再実行環境の復元

GitHub本体をclone / 展開後、Release Source ZIPを**リポジトリルートへ重ねて展開**します。

すると、

```text
model/sources/RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip
model/sources/EHC1_E1GLOBAL_FULL_20260911.zip
```

が復元されます。

確認：

```bash
python model/code/verify_release_sources.py
```

実行：

```bash
cd model
python code/run_v22r.py --fold 0 --bif A:2 --run 91701 --mode PARAH1_RUN --output-root outputs/test
```

昇格証拠検証：

```bash
python code/validate_paragraph_h1_running.py
python code/validate_v22r.py
```

## 4. 凍結条件

v22rはfresh-200審判後にparameter tuningをしていません。

既知残差はglobal bigramとterminalです。これらは今後の版で検定対象とし、v22rのparameterは変更しません。
