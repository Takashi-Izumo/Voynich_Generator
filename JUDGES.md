# 審判団 — v0.3と開発用ベースライン

v0.3を`python -m judges v03 ...`で利用できます。[実行手順・評価条件](judges/v03/README.md)を参照してください。

原位置を保持するFULL/END_ONLY/NONE入力、J08のscope分離、J11の語長・支持診断、bifolium等重み・同点1/2・NAの分離、外部真正資料による校正、局所対照と能力確認、内部B2監査を実装しています。旧CLIは以下のv0.2として維持します。

理想は、識別力のある審判でも真正面を識別できず50%となる状態です。低い率にも逆方向の識別手掛かりがあり得ます。判定率・不確実性・対照に対する識別力も確認し、弱い審判による50%を生成器の勝利と解釈しません。

コードはリポジトリ直下の [`judges/`](judges/) にあります。v21〜v22.3の凍結コードは変更していません。

参照3面と匿名化した候補A/Bから予測を保存し、その後に別ファイルの正解を開いて集計します。**初版は固定された参照3面プロトタイプとの比較器です。校正済みの最終審判、生成器の昇格判定ではありません。**

パッケージはv0.3.0、以下の旧方式の採点設定は`partition-prototype-jsd-v2`です。監査で指摘された条件付き参照混合、J17の照合面数、共有mask検証、設定重みの適用を修正しています。v1の予測・採点結果はv2へ混ぜず、入力から予測を作り直してください。

## 実行

コアとテストはPython 3.12標準ライブラリだけで動作します。リポジトリ直下で実行します。各出力先は未作成のディレクトリを指定してください。

```bash
python3 -m unittest discover -s judges/tests -v
python3 -m judges validate --input judges/examples/demo.jsonl
python3 -m judges predict --input judges/examples/demo.jsonl --output /tmp/voynich-judges-demo-predictions
python3 -m judges score --predictions /tmp/voynich-judges-demo-predictions \
  --key judges/examples/demo-key.jsonl --output /tmp/voynich-judges-demo-scores
```

demoは作成文書の動作確認用です。真正面を識別できたという実績には数えません。

## v22.3の保存済み生成結果を使う

このアダプターだけは、v22.3のセットアップ済みPython・親ソースZIPを必要とします。ネットワーク取得や再生成は行いません。

```bash
source /workspace/.venvs/voynich/bin/activate
python -m judges export-v223 \
  --generated-root /workspace/voynich-results/v22_3-smoke-verified \
  --run 91701 --bif A:2 --output /tmp/voynich-judges-v223-inputs
python -m judges validate --input /tmp/voynich-judges-v223-inputs/inputs.jsonl
python -m judges predict --input /tmp/voynich-judges-v223-inputs/inputs.jsonl \
  --output /tmp/voynich-judges-v223-predictions
python -m judges score --predictions /tmp/voynich-judges-v223-predictions \
  --key /tmp/voynich-judges-v223-inputs/answer_key.jsonl \
  --output /tmp/voynich-judges-v223-scores
```

`--package`でv22.3ディレクトリを指定できます。`--run`と`--bif`は繰り返し指定でき、`--bif`省略時は20 complete bifoliaが対象です。指定した全生成結果が必要で、不足・不一致を黙って除外しません。

アダプターの評価条件は **共有layout・clean-line mask付きstable22** です。原転写にUNKNOWN、rare等がある行や、scheduleと一致しない行は真正・疑似の両側で同じように評価対象外にし、行位置・段落位置は残します。既知3面も同じclean-line規則で処理します。除外行と元データhashは`export_manifest.json`に記録します。植物前で切れる仕様と、既存のf28v.7例外を保持します。

生成側は見える`surface`を変換します。内部のpre-rare `stable_surface`を正解側だけとは異なる意味で使用しません。`m`はstable文字として保持します。raw/rare審判J21はこのアダプターではNAです。

**旧200ケース審判と前処理が異なるため、旧成績と同じ実験として比較しないでください。** `answer_key.jsonl`と非匿名の`export_manifest.json`は予測器への入力にしません。

## 実装した範囲

- 原位置を保つ共通抽出。植物前P／物理行末L／segment途中Iを分離。UNKNOWN越し・植物図越しのSPACE接続は作りません。
- 候補間の行・段落・segment境界・除外maskを検証します。語数は候補ごとに異なって構いません。各文書に観測語が必要で、比較可能な総合区分がない対決は乱択せず拒否します。
- J01〜J25の表示ID。専門診断には条件付きJSD、語順、段落履歴、長さ×幅、raw表記を含みます。
- 総合のデフォルトは重複しない8区分の等重みです。`registry.CONFIG`の対象区分・重みを検証して適用し、重み0を除き有効区分で再正規化します。25表示項目を25票にはしません。内部同点は中立、有効な最終同点だけ匿名IDから再現可能な二択にします。
- 予測ファイル、設定・コード・入力hashの記録。答え合わせでは予測hashを再確認します。
- 対決ごとの正誤からbifolium等重みの正答率を計算。cluster bootstrapの記述的区間と、seed別・bifolium別の結果を出します。

採点仕様、観測可能な診断と内部機構監査の違い、入力形式は [`judges/SPEC.md`](judges/SPEC.md) を参照してください。J08は広い第一行末、J13/J17は可視情報による代替診断であり、凍結lawや内部stateの厳密再現ではありません。

最終勝利の許容識別率、専門診断の校正、新しい未使用bifoliaでの汎化検証は未実施です。出力は`promotion_verdict: null`とし、非有意性や単発の正答率から昇格を認定しません。
