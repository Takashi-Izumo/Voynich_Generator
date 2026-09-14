# RMW1-BTI2-EHC1 Stage 3 審判パッケージ

本パッケージは凍結したEHC1実装を変更せずに評価します。generator修正版ではありません。最初に REPORT_JA.md と MODEL_STATUS.json を参照してください。

## 入力

`input/RMW1_BTI2_EHC1_20260911.zip` が凍結Stage 2です。SHA-256:
`016075e63e7c8a85516d80354ac787908a5c4888fcbc3118da1fb6c0bdd21f3a`

親BTI2、実測データ、5foldのcore、EHC1全設定と機械用run91011が含まれます。実行時にはwork/へ展開します。別の既存展開先を使う場合は環境変数EHC1_ROOTで指定できます。元ZIPは変更しません。

## 実行順序

```bash
python code/screen_candidates.py
python code/generate_frozen_batch.py --stage multirun
python code/judge_frozen_batch.py --stage multirun
python code/select_confirmation.py
python code/generate_frozen_batch.py --stage confirmation
python code/judge_frozen_batch.py --stage confirmation
python code/postprocess_results.py
python code/verify_evaluation.py
python code/smoke_replay.py
```

`screen_candidates.py` はrun91011の固定済み生成物を使います。語頭teacher forcingと6種類の簡易診断だけを行い、一般16審判は候補を絞った後で実行します。規則はSELECTION_RULE_BEFORE_SCREEN.jsonにあります。E12は主介入の比較対照として、警告があっても重い審判へ残します。

多seed比較はBASE/E12/E12_VH・91021–91023（180生成頁）。その後の確認はBASE/E12_VH・91031–91035（200生成頁）。同じ20葉・同じ固定第4面であり、380個の独立した実資料ではありません。

## 審判の定義

`code/frozen_judge_sameinfo.py` は過去RAP4パッケージに保存された数値審判ソースを無変更で収録しています。その16指標に、原位置とPLANT分断を考慮したSPACE_RAW/H2_RAW/H3_HEAD_RAW/HEAD_H1_RAWを補助診断として加えます。独立LLMによる自由判定ではありません。panel多数決は本試験では追加しません。

各対象葉で外側16葉の全64面＋対象known3からvectorizer/参照profileを作り、同じものを全arm/seedへ使います。target第4面と生成候補をfeature fitに入れません。F16を評価するときも審判側を変更しません。

旧SPACE_T_H1はclean物理行の隣接を使い、PLANT跨ぎが含まれます。SPACE_RAWは原位置台帳でPLANT・不明語跨ぎを除外します。互換性のため旧定義は書き換えず両方を報告します。

## 統計

score差は「実測known3適合 − 生成known3適合」。絶対値を各頁・seedで先に取り、その後葉内seed平均・20葉平均を取ります。真正選択回数は記述値です。推測統計は20葉単位のexact sign-flipと20,000回cluster bootstrapを使用します。主2指標、HEAD3指標、回帰指標、一般6指標のHolm補正を別表示します。対照と修正版の差についての非有意は等価性の証明ではありません。

teacher forcingは実測のslot/語位置/segment終了条件を固定したnon-END次字の評価です。停止とpackingを含む全文尤度や、次語数の予測ではありません。support外を0として記録し、表示lossには1e-15のfloorを使います。個別事象を独立葉として検定しません。

## 保存先

- `outputs/screen/`: 全10条件の簡易監査・teacher-forced全事象・first/bank/selected/surface診断。
- `outputs/multirun/generated/`: 180頁のtoken・確率行・候補・commit・機械監査。
- `outputs/multirun/judged/`: 3seedの全審判・実測との差・葉単位検定。
- `outputs/confirmation/generated/`: 固定した候補と親の別5seed・200頁。
- `outputs/confirmation/judged/`: 最終確認の同じ評価。
- `EVALUATION_CONTRACT_AUDIT.json`: 旧16審判との一致、境界と凍結コード照合。
- `sources/`: 過去審判の参考runner。今回の成果ではありません。

Python/NumPy/Numba等の版はStage 2のrequirements.txtに固定されています。同一環境の再現を想定します。新たなネットワークアクセスは不要です。継承された稀字/m/Gのparameter来歴はUNVERIFIEDのままです。
