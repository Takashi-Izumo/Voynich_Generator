# Stage 4 GitHub版 再実行手順

## 1. Release assetを用意

GitHub Releaseから次の2ファイルを取得する。

- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`
- `EHC1_E1GLOBAL_FULL_20260911.zip`

`model/sources/`へ置くか、任意のディレクトリへ置いて環境変数を設定する。

```bash
export VOYNICH_V21R_SOURCE_DIR=/path/to/v21r-release-assets
```

Windows PowerShell:

```powershell
$env:VOYNICH_V21R_SOURCE_DIR = "C:\path\to\v21r-release-assets"
```

初回実行時だけ `model/runtime/` へ展開される。archiveは展開前にSHA-256検証される。

## 2. 整合性smoke

```bash
cd model
python code/validate_integration.py --smoke
```

期待値：`smoke_hash_identity = PASS`。

## 3. Stage validators

```bash
python code/validate_v21_stage1.py
python code/validate_v21_stage2.py
python code/validate_v21_stage3.py
python code/validate_v21_stage4_synthetic.py
```

## 4. Stage 4生成

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SAFE_LEFT_BT_OFF --output-root outputs/example
```

SLOTを再現する場合：

```bash
python code/run_model_v21.py --fold 0 --bif A:2 --run 91401 \
  --mode SLOT_BT_OFF --output-root outputs/example
```

Stage 4保存結果ではSLOTはSPACE_RAW stop ruleにより3-seedで停止しており、正式candidateは `SAFE_LEFT_BT_OFF` のままである。
