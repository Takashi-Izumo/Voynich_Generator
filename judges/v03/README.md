# 審判団 v0.3

匿名の既知3面・候補2面から予測を保存し、別の正解ファイルで採点します。標準ライブラリで動作します。凍結されたv21/v22.3生成器は変更しません。

旧CLIはv0.2として利用でき、新版は`python -m judges v03 ...`です。旧結果と新しい入力profileの成績は別の実験として扱います。

## 変更点

- 原行・段落位置と共有品質台帳。候補A/Bの語数は一致不要です。
- FULL / END_ONLY / NONEを別の型にし、読める末尾から行頭・W2・SPACEを作りません。
- J08をWIDE / F1LF / POSTPLANTと語長別に表示します。J11もL3/L4/L5とSUPPORTを別表示します。
- 全専門診断にbifolium等重み、pooled、同点1/2の期待正答率、NA・同点・coverageと区間を出します。NAを50%で埋めません。
- 外側4 bifoliaを除外し、事前分布学習8・null校正8を分けます。近すぎる距離と遠すぎる距離の両方を扱います。
- 独立した局所変形対照、能力確認、B2機構監査を用意します。

PROTOは固定された参照3面への近さ、CALは外部真正資料で校正した中央性scoreです。CAL scoreは真正確率や厳密なp値ではありません。追加診断を総合の独立票として数えません。

## 標準ライブラリだけの確認

リポジトリ直下で、未作成の出力先を指定します。demoは型と実行の確認用の作成文書です。

```bash
python3 -m unittest discover -s judges/tests -v
python3 -m judges v03 validate --input judges/examples/v03-demo.jsonl
python3 -m judges v03 predict --input judges/examples/v03-demo.jsonl --output /tmp/judges-v03-demo-pred
python3 -m judges v03 score --predictions /tmp/judges-v03-demo-pred \
  --key judges/examples/v03-demo-key.jsonl --output /tmp/judges-v03-demo-score
```

## 保存済み生成物のexport

この段階だけは、v22.3のセットアップ済みPython・検証済み親runtimeを必要とします。v21の保存物にも同じ原文書・品質規則を適用でき、`model_dir`を明示して指定します。ネットワーク取得や再生成は行いません。

export planの必須フィールドは次の6個です。

```json
{
  "package": "/workspace/Voynich_Generator/HerbalA_v22_3_20260921",
  "generated_root": "/workspace/voynich-results/jury-v21-v223-20261104/generated/v223",
  "model_dir": "HerbalA_v22_3_STAGE3D_R1_CANDIDATE",
  "runs": [91701,91702,91703,91704,91705,91707,91708,91709,91710,91711],
  "bifolia": null,
  "blinding_seed": 20261104
}
```

`bifolia:null`は20 complete bifoliaを意味します。指定した全生成物が必要です。元のスケジュールにない不明行はNONEで保持します。末尾の原語が直接照合できる場合だけEND_ONLYを使います。現在のパッケージでは構造から抽出したF1LF集合と凍結ledgerの全88か所を照合し、不一致なら停止します。

```bash
python -m judges v03 export --plan plan-v223.json --output /tmp/v03-v223-inputs
python -m judges v03 validate --input /tmp/v03-v223-inputs/inputs.jsonl
```

出力は`inputs.jsonl`、別の`answer_key.jsonl`、真正80面の匿名`corpus.json`、非匿名の`export_manifest.json`です。最後のmanifestと正解・内部生成ログは予測器へ渡しません。

## 学習・予測・集計

```bash
python -m judges v03 fit --corpus /tmp/v03-v223-inputs/corpus.json --output /tmp/v03-models
python -m judges v03 predict --input /tmp/v03-v223-inputs/inputs.jsonl \
  --models /tmp/v03-models --primary J24.CAL --output /tmp/v03-v223-pred
python -m judges v03 score --predictions /tmp/v03-v223-pred \
  --key /tmp/v03-v223-inputs/answer_key.jsonl --output /tmp/v03-v223-score
```

fitは真正資料だけを読み、生成器の疑似面・正解・採点結果を訓練に使いません。8学習bifoliaの内側LOBOでlambda/rhoを選び、別の8 bifoliaの各4面からnull表を作ります。nullは6 bifolia・12 target面以上を要求し、size-binからALL_SIZESへ固定順でbackoffします。不足はNAです。モデル・null表・コードのhashと対象clusterの外側holdout結合を検査します。

`--models`を指定するとPROTO/CAL双方を保存します。既定の主判定はJ24.PROTOで、J24.CALには明示指定が必要です。CALを要求してモデルがない場合はエラーです。J24.CALの共通区分が4未満ならNAとして保存します。

同じモデルセットを使ってv21も予測・採点し、次で比較します。

```bash
python -m judges v03 compare --scores-v21 /tmp/v03-v21-score \
  --scores-v223 /tmp/v03-v223-score --output /tmp/v03-comparison
```

比較は同じtrial・mask・known3・真正面・model・primaryを要求します。両版とも比較可能な集合での期待率の差、両版とも判定した集合の差、NA/TIEの移行を別に出します。

## 対照検証と機構監査

```bash
python -m judges v03 controls --corpus /tmp/v03-v223-inputs/corpus.json --output /tmp/v03-controls
python -m judges v03 predict --input /tmp/v03-controls/inputs.jsonl \
  --models /tmp/v03-models --primary J24.CAL --jobs 4 --output /tmp/v03-controls-pred
python -m judges v03 capability --predictions /tmp/v03-controls-pred \
  --controls /tmp/v03-controls --output /tmp/v03-capability
python -m judges v03 audit-b2 --export-manifest /tmp/v03-v223-inputs/export_manifest.json \
  --generator-results /workspace/voynich-results/jury-v21-v223-20261104/generated/v223 \
  --output /tmp/v03-mechanism
```

局所対照は同じglyph幅でterminalまたはH2だけを変えます。参照へ寄せる/離す方向、25/50/100%強度、5反復を固定しています。変更できない条件もplanに残し、成功に数えません。語彙・Markov支持まで保証した対照ではありません。全反復・持ち回りはbifoliumにまとめて集計します。

100%対照の各方向について、10 bifolia以上・比較可能率80%以上・期待率75%以上・記述区間下限50%超を開発上の能力確認基準にしています。基準未達はLOW_POWER、資料不足はINSUFFICIENT_DATAです。これで生成器の同等性・勝利を判定しません。

## 記録と制約

- 予測行の厳密な契約は[contracts](contracts/)にあります。実装は標準ライブラリの意味検証を行い、jsonschemaはruntime依存にしません。
- `channels.jsonl`に各channelのscore・空/context不足・生の機会数・校正被覆を保存します。viewのイベント数は対象語・末尾・接続等の重複しない観測数で、channelを足した独立標本数ではありません。`source_slots`の単位はENDPOINTS / MIDDLE_LINES / FULL_SEGMENTSです。
- `predict --jobs 1..4`はキーを読まない子processに分割し、入力順に再結合します。単一実行と並列実行の予測・channelファイルが一致することを検査します。浮動小数点の集計順序も固定しています。
- J17の正規化後の質量を1観測とせず、非空の2面subsetの最小機会数を校正size-binに使います。
- 区間は利用可能bifoliaと固定モデルを条件とした記述値で、学習不確実性や欠測bifoliaを補いません。
- 現在の20 bifoliaは開発・監査に再利用されています。新seedを独立した真正標本とは数えません。
- stable22-visible条件のためJ21はNA。`promotion_verdict`は常にnullです。
- スキーマ・protocol・コード・入力・予測・model/null表のhashを保存し、既存出力を上書きしません。
