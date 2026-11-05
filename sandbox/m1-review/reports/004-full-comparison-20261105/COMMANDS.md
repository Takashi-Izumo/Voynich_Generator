# 本比較の再現手順

基準となる実装は`602c4501ba34792135d585691c005536a341b936`時点のM1 schema v2。原版・審判は`c610c2a81e733748e0fb246de89143d6ecda764e`から変更なし。事前固定計画はcommit `1f45f5add83a6758eeea237ba518f9949e33b3da`で実行前に共有した。

以下は今回の実パス。再実行では**新しい未使用root**へ読み替える。原版・依存・検証済みparent archiveを準備し、既存の生生成物を上書きしない。

```bash
M1_FULL_ROOT=/workspace/voynich-results/m1-full-comparison-20261105
M1_FULL_CHECKOUT=/workspace/voynich-results/m1-v2-independent-20261105/checkout
M1_FULL_PY=/workspace/.venvs/voynich/bin/python
M1_FULL_MODELS=/workspace/voynich-results/m1-review-received-20261105/cal-models
M1_FULL_HISTORICAL=/workspace/voynich-results/jury-v21-v223-20261104/generated/v223
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR=/workspace/voynich-results/m1-v2-independent-20261105/numba-cache
export PYTHONPYCACHEPREFIX=/workspace/voynich-results/m1-v2-independent-20261105/pycache
cd "$M1_FULL_CHECKOUT"

"$M1_FULL_PY" -m experiments.m1_pf plan --output "$M1_FULL_ROOT/plan" --bifolia all --runs 91701,91702,91703,91704,91705,91707,91708,91709,91710,91711 --kind development
"$M1_FULL_PY" "$M1_FULL_ROOT/run_full.py" --checkout "$M1_FULL_CHECKOUT" --root "$M1_FULL_ROOT" --workers 4
"$M1_FULL_PY" "$M1_FULL_ROOT/pipeline.py" --root "$M1_FULL_ROOT" --checkout "$M1_FULL_CHECKOUT" --models "$M1_FULL_MODELS" --historical "$M1_FULL_HISTORICAL"
```

`run_full.py`は4独立processで凍結Runtime.generateを呼び、800ケース全完了後に標準形式のgeneration manifestを作る外部orchestrator。コードhashは`STUDY_PROTOCOL.json`に固定済み。候補の生成処理・選択規則・審判の変更はしない。

helper scriptは本ディレクトリから新rootへ配置する。`study_protocol.json`は`STUDY_PROTOCOL.json`を小文字の名前で配置し、生成前に新planとの対応とscript hashを確認する。新planのsourceや入力が同じなら同じplan hashになる。異なるなら同じ実験だと読み替えず、別計画として扱う。

`pipeline.py`は成功した全800面の完了を待って、次を順に実行する。今回、orchestratorとpipelineは別processで並行起動した。

```bash
"$M1_FULL_PY" -m experiments.m1_pf audit --plan "$M1_FULL_ROOT/plan/plan.json" --generated "$M1_FULL_ROOT/generated" --output "$M1_FULL_ROOT/audit"
"$M1_FULL_PY" "$M1_FULL_ROOT/summarize_full.py" historical --root "$M1_FULL_ROOT" --historical "$M1_FULL_HISTORICAL"
"$M1_FULL_PY" -m experiments.m1_pf export --plan "$M1_FULL_ROOT/plan/plan.json" --generated "$M1_FULL_ROOT/generated" --output "$M1_FULL_ROOT/anonymous"
"$M1_FULL_PY" -m experiments.m1_pf evaluate --plan "$M1_FULL_ROOT/plan/plan.json" --inputs "$M1_FULL_ROOT/anonymous" --models "$M1_FULL_MODELS" --output "$M1_FULL_ROOT/evaluation" --jobs 4 --bootstrap 10000
"$M1_FULL_PY" "$M1_FULL_ROOT/summarize_full.py" results --root "$M1_FULL_ROOT"
```

M1と凍結審判の27＋56テスト、通常順/逆順24面、負例は直前の独立再検証でPASSした。同じ実装を変更せず使用したため、今回のdata-only実行で同じunitテストを再反復してはいない。新たな800面の機構監査と600予測の意味検査・hash確認を完了した。

固定CALのmodel-set hashは`61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。モデルを再fitしない。BASEは過去の200予測ファイルまでbyte一致しており、評価条件の回帰も確認した。
