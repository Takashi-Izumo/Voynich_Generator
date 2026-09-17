# HerbalA v22r

Voynich Pure Herbal A生成モデルの2026-09-17正式昇格版です。

## モデル定義

`v22r = v21r SAFE_LEFT_BT_OFF + PRETERM_QMAP9 + SHORTBODY-H2-GLOBAL + PARAH1-RUN32`

今回の昇格点は、BODY H1に対する **paragraph-local continuous running residual** です。paragraph境界でneutral resetし、完了済みの過去行だけからH1残差を更新します。縮約強度は `lambda=32`、decayはありません。介入はH1だけで、H2+、語長、物理幅、route memory、bT、PRETERM、packing、親RNGを固定します。

## fresh 200審判

seeds 91701–91710、20 bifolia ×10 seeds。正式統計単位は20 bifoliaです。

- combined: **7/13** — chance内
- H1→H2: **5/15 → 6/14**、17/20葉が正方向
- bigram: **4/16** — 残差は残るがsigned marginは親から2.21%縮小
- trigram: **6/14 → 7/13**
- terminal: **15/5** — 親から完全不変
- packing 200/200、support violation 0、invalid 0

正式判定は **PASS WITH RESIDUAL** です。詳細は `model/docs/V22R_PROMOTION_JA.md` と `model/validation/v22r_fresh200_judge/` を参照してください。

## GitHub配布構成

このリポジトリ用パッケージはGitHubの単一ファイル制限を避けるため、巨大な凍結親ソースZIPを含みません。GitHub Releaseへ `HerbalA_v22r_Release_Source_20260917.zip` を添付し、実行時にはそれをリポジトリルートへ展開してください。

## 実行

```bash
pip install -r requirements.txt
# Release Source assetをこのリポジトリルートへ展開後
cd model
python code/run_v22r.py --fold 0 --bif A:2 --run 91701 --mode PARAH1_RUN --output-root outputs/test
```

## 検証

```bash
cd model
python code/validate_paragraph_h1_running.py
python code/validate_v22r.py
```

`validate_v22r.py` は保存済みself-testとfresh-200昇格証拠を検査します。

## 既知の残課題

1. global bigram residual: 4/16、sign-flip p=0.002815。
2. terminal: 15/5。margin検定は非有意で、親から完全不変。
3. ng / route56に弱い残差が残るが、今回のH1介入で新たに生じたものではありません。

審判後のチューニングは行っていません。
