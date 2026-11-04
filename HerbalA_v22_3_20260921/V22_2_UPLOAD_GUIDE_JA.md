# HerbalA-v22.2 アップロードガイド

次チャットでこの版を親として使う場合は、`HerbalA_v22_2_F1LF_ROUTER_OFF_20260920.zip` をアップロードする。

正本：

```text
model_id = HerbalA-v22.2
parent   = HerbalA-v22r-W2B2
status   = IMPLEMENTED_PREJUDGE_NOT_JUDGED
```

実行：

```bash
python run_v22_2.py --fold 0 --run 91701
```

preflight：

```bash
python validate_v22_2.py
```

このパッケージに含まれるv22.2結果はmechanical smokeのみ。審判結果はまだ存在しない。
