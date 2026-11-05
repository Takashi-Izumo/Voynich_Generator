# M1: PF候補選択とLEN1追加救済の分離実験

基準commitは `c610c2a81e733748e0fb246de89143d6ecda764e`。v22.3・v21・親archive・審判v0.3は編集せず、独立runner/overlayとして実装しています。モデル昇格ではありません。

独立検証の指摘を受けたschema v2です。変更点は [REVIEW_FIXES.md](REVIEW_FIXES.md)。旧plan・旧監査PASSは再利用せず、新しい計画から再生成してください。本比較への移行は引き続き保留です。

| arm | 採用する枝 | 救済探索 | 次のmain RNG |
|---|---|---|---|
| BASE | 最初の2枝のargmax、適格LEN1があれば救済枝 | 原版の追加8枝 | **最初の2枝のargmax**の終了状態 |
| PF_NO_RESCUE | 最初の2枝のargmax | なし | argmaxの終了状態 |
| PF_ANCHOR | 候補0。候補1も生成・採点・記録 | なし | **候補0**の終了状態 |

最終語だけを差し替える処理ではなく、採用枝のsegment全体・rare予算・履歴をcommitします。語長・幅・語数を全群で固定する制約は追加していません。

**原版の採番契約:** `next_proposal_id`は破棄された枝でも進み、PRETERM/H1等の既存side RNGのキーにも使われます。観測専用カウンタではありません。BASEを完全再現するためこの規則を維持し、各枝の開始/終了番号を記録します。救済探索の削除は後続side RNGのキーにも波及するため、対比はこの経路を含む総効果です。候補選択・救済の純粋な直接効果や相互作用を分離したとは主張しません。

詳細は [DESIGN.md](DESIGN.md)。

## 実行

リポジトリ直下でセットアップ済みPythonを使います。別環境では先に `HerbalA_v22_3_20260921/GITHUB_SETUP_JA.md` の親ソース取得・依存導入を行ってください。

```bash
source /workspace/.venvs/voynich/bin/activate
export PYTHONPYCACHEPREFIX=/workspace/voynich-setup/pycache
export NUMBA_NUM_THREADS=2
python -m experiments.m1_pf plan \
  --output /workspace/voynich-results/m1/plan \
  --bifolia A:2,A:3,G:1 --runs 91701
python -m experiments.m1_pf generate \
  --plan /workspace/voynich-results/m1/plan/plan.json \
  --output /workspace/voynich-results/m1/generated --reference
python -m experiments.m1_pf audit \
  --plan /workspace/voynich-results/m1/plan/plan.json \
  --generated /workspace/voynich-results/m1/generated \
  --output /workspace/voynich-results/m1/audit
python -m experiments.m1_pf export \
  --plan /workspace/voynich-results/m1/plan/plan.json \
  --generated /workspace/voynich-results/m1/generated \
  --output /workspace/voynich-results/m1/anonymous
```

`--reference`はoverlayを通さない原版engineも生成し、BASEと意味のある出力全体を比較します。生成順の確認には新しい出力先へ `--arm-order PF_ANCHOR,PF_NO_RESCUE,BASE` で再生成し、`audit --repeat <再生成先>` を使います。runner内部は逐次実行し、同一processの生成API呼出しはlockで直列化します。独立processで並行実行する場合も出力先を分けてください。

全20葉の計画は `--bifolia all`、大きい計画は `plan --kind development` を明示します。デフォルトは小規模機構確認で、結果を見たseed除外や補充は行いません。失敗時はそのまま停止・部分出力を保存し、原因を記録して同じ計画を**新規の出力先**へ再実行します。実験成果物の既存ディレクトリは上書きしません。

planには原版・審判・overlayのhash、元コーパス/品質台帳のhash、seed・群・盲検seedを固定します。overlayを変更したら、新しいplanを作成してください。`scope_ledger.json`はPF介入集合と審判のPARA_END集合、FULL/END_ONLY/NONEの差を記録します。

展開済みruntimeも、設定・selector・coreを含む信頼済み親ZIP全体の非コンパイラcacheファイルと照合します。既存treeの欠落・追加・改変を計画の検査中に自動で修復しません。END_ONLYの末尾情報が使えても、FULL行の`word_events`を使うatomでは非観測です。ledgerは構造上の末尾atom、実観測atom、末尾情報利用可否を別々に記録します。

## 審判への受け渡し

exportは既存の `judges.v03.adapter` をそのまま使い、3群を同じprofile・mask・盲検化規則で匿名化します。各群に `inputs.jsonl`、別の `answer_key.jsonl`、真正資料のみの `corpus.json`、非匿名の `export_manifest.json` が出ます。予測器に渡すのは `inputs.jsonl` と固定モデルだけです。

```bash
python -m experiments.m1_pf evaluate \
  --plan /workspace/voynich-results/m1/plan/plan.json \
  --inputs /workspace/voynich-results/m1/anonymous \
  --models /path/to/frozen/jury-v03-models \
  --output /workspace/voynich-results/m1/evaluation --jobs 2
```

主判定は常に **J24.CAL**、主要局所判定は **ATOM.PARA_END.CAL**。必要なmodel-set hashは仕様書指定の `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79` です。指定モデルがない/一致しないときは、再学習・PROTOへのfallbackをせず停止します。

全群の予測保存後に初めて正解を使って採点します。既存の対応比較に加え、共通の比較可能trialに限ったbifolium等重みの率、50%からの距離の差、方向反転、NA/TIE遷移と記述bootstrap区間を出します。NAは0.5で埋めません。J24以外のPROTO/CAL・J07/J19/J20/J25・各atom/channelも既存審判の出力に残ります。

許容幅・採用規則・多重比較の推論方針は未合意なので、結果は記述・開発用とし、自動昇格・有意差による選抜は実装していません。局所対照による段落末の審判能力確認と、独立bifoliaでの一般化確認も、この機構確認の成功とは別です。

## 出力

```text
plan/
  plan.json                  # 固定した比較条件・コード/データhash
  scope_ledger.json          # PF対象と審判atom/maskの対応
generated/
  BASE|PF_NO_RESCUE|PF_ANCHOR/runSEED/HerbalA_v22_3_M1_ARM/BIF/
    tokens.csv.gz            # 既存export互換
    MECHANICAL.json          # 元のpacking/支持/PLANT等の監査
    requests.jsonl.gz        # committed_to_final_pageで最終採用を識別
    m1_events.jsonl.gz       # 採用/argmax/乱数継続/rare/state hash
    m1_candidates.jsonl.gz   # 非採用枝も含む長さ・幅・末字族・m・適格性
    M1_FINAL.json            # 完全な最終state hashとparent source hash
  REFERENCE/...              # --reference時だけの原版出力
  manifest.json              # 全生成物のhash
  STATUS.json                # 失敗・完了状態
audit/report.json
anonymous/ARM/...            # 匿名入力と正解を別ファイルに保存
evaluation/{predictions,scores,paired}/ARM_OR_CONTRAST/...
```

`m1_candidates`のstate hashは、旧digestにないrare、route trace・attempts、surface commit、採用request ID、段落H1のpending/完了履歴を含みます。`correction`は共有read-onlyとして別のcontent fingerprintで固定します。未知のsampler制御フィールドが現れた場合は、未監査のまま共有せず停止します。

`M1_FINAL.json`には最終main RNGの実state/hashも明示保存します。監査report/sealは対象generation manifest等のhashへ結び付け、export時に再照合します。生成物とchecksumを更新した場合も、前のPASSではexportできません。

## テスト

```bash
python -m unittest discover -s experiments/m1_pf/tests -v
python -m unittest discover -s judges/tests -v
```

この環境での具体的な検証記録は [VALIDATION.md](VALIDATION.md) にまとめます。原版コードやruntimeの直接編集、GitHubへのcommit/push、正式昇格はこの実装段階では行いません。
