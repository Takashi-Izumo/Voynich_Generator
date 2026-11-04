# GitHub版v22.3のセットアップ

このディレクトリは、公開済み `HerbalA_v22_3_FULL_EXPORT.zip` のコード・設定・検証資料をそのまま収録しています。ZIP内の462ファイルのうち、大きな親ソースZIP2本だけをGit管理から除外しています。収録した460ファイルは完全版ZIPとバイト単位で一致します。凍結されたコード、設定、マニフェスト、過去の審判結果は変更していません。

この案内と `requirements-cloud.txt` はGitHub向けの追加ファイルです。正式版の説明は [README_V22_3_JA.md](README_V22_3_JA.md) を参照してください。旧READMEにあるv22.2や候補版の説明は保存された履歴です。

## Python環境

Python 3.12を使用します。以下の作業ディレクトリはこのv22.3ディレクトリです。

```bash
cd /workspace/Voynich_Generator/HerbalA_v22_3_20260921
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-cloud.txt
```

クラウド環境で用意済みのPythonを使う場合は `source /workspace/.venvs/voynich/bin/activate` を実行してください。`.venv` を作成した場合はGitへ追加しないでください。

## 親ソースZIP

完全版ZIPを[公開Release](https://github.com/Takashi-Izumo/Voynich_Generator/releases/tag/HerbalA_v22_3_20260921)から取得し、展開します。既に持っている場合は再取得不要です。

```bash
curl -fL --max-time 180 \
  https://github.com/Takashi-Izumo/Voynich_Generator/releases/download/HerbalA_v22_3_20260921/HerbalA_v22_3_FULL_EXPORT.zip \
  -o /tmp/HerbalA_v22_3_FULL_EXPORT.zip
echo '9ae7718a0725c7918ed9355166e976957def8d50d0ac042716019fdd15020315  /tmp/HerbalA_v22_3_FULL_EXPORT.zip' | sha256sum --check
python -m zipfile -e /tmp/HerbalA_v22_3_FULL_EXPORT.zip /workspace/voynich-release
cp -n /workspace/voynich-release/HerbalA_v22_3_20260921/model/sources/*.zip model/sources/
python model/code/verify_release_sources.py
```

必要なソースは次の2本です。保存先は元ランタイムが参照する `model/sources/` です。どちらも既存の `.gitignore` で除外されます。

- `EHC1_E1GLOBAL_FULL_20260911.zip`
- `RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912.zip`

## 検証と実行

```bash
export NUMBA_NUM_THREADS=2
python validate_v22_3_promotion.py
python model/code/validate_v22r.py
python run_v22_3_stage3d.py --fold 0 --bif A:2 --run 91701 \
  --output-root /workspace/voynich-results/v22_3-smoke
```

最初の2コマンドは固定法則・保存済み昇格資料の検証です。3つ目が実際の生成です。出力先の `MECHANICAL.json` で `packing_exact=true`、`invalid_rows=0`、`support_violations=0` を確認します。検証時はA:2 / seed 91701で生成でき、3項目すべて成功しました。全200ケースの審判の再実行は、このブランチの公開確認では行っていません。

実装IDに `HerbalA-v22.3-STAGE3D-R1-CANDIDATE` が残るのは、正式昇格時に監査済み実行コードを変更しないという配布元の方針によるものです。正式なリリースIDは `HerbalA-v22.3` です。
