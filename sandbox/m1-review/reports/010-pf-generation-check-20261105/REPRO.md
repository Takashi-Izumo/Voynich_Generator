# 再現手順

検証対象は `fd1fa286671962ab768886597a82b167e7dcb52f`。codeを変更せず、未使用の実行rootを用意する。必要な依存関係・展開runtime・parent archiveは従来M1と同じ。固定CALを再学習しない。

この環境のPythonは `/workspace/.venvs/voynich/bin/python`。以下の `python` はそのPythonを指す。

```bash
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR=/workspace/voynich-results/m1-v2-independent-20261105/numba-cache
export PYTHONPYCACHEPREFIX=/workspace/voynich-results/m1-v2-independent-20261105/pycache
export PF_REVIEW_CHECKOUT=/workspace/voynich-results/m1-v2-independent-20261105/checkout
# 別の再実行では必ず新しいrootに変える。
export PF_REVIEW_ROOT=/workspace/voynich-results/pf-generation-independent-20261105
cd "$PF_REVIEW_CHECKOUT"
python -m unittest discover -s experiments/pf_generation/tests -v
python -m unittest discover -s experiments/m1_pf/tests -v
python -m unittest discover -s judges/tests -v
python -m experiments.pf_generation plan --output "$PF_REVIEW_ROOT/plan"
python -m experiments.pf_generation plan --identity --output "$PF_REVIEW_ROOT/identity-plan"
python -m experiments.pf_generation plan --bifolia all --kind development --output "$PF_REVIEW_ROOT/all-folds-plan"
python -m experiments.pf_generation generate --plan "$PF_REVIEW_ROOT/plan/plan.json" --output "$PF_REVIEW_ROOT/forward"
python -m experiments.pf_generation generate --plan "$PF_REVIEW_ROOT/plan/plan.json" --output "$PF_REVIEW_ROOT/reverse" --reverse
python -m experiments.pf_generation generate --plan "$PF_REVIEW_ROOT/identity-plan/plan.json" --output "$PF_REVIEW_ROOT/identity"
python -m experiments.pf_generation audit --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/audit"
python -m experiments.pf_generation audit --plan "$PF_REVIEW_ROOT/identity-plan/plan.json" --generated "$PF_REVIEW_ROOT/identity" --output "$PF_REVIEW_ROOT/identity-audit"
```

独立fit計算と段階集計は、本報告の `check_fit_independently.py` と `check_stages_and_scope.py` をこの環境変数で実行する。fitのthetaはcandidateのNewton法を呼ばず、元表から作った正則化gradientをBrent法で解く。

```bash
python sandbox/m1-review/reports/010-pf-generation-check-20261105/check_fit_independently.py
python sandbox/m1-review/reports/010-pf-generation-check-20261105/check_stages_and_scope.py
python -m experiments.pf_generation summarize --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --output "$PF_REVIEW_ROOT/summary"
python -m experiments.pf_generation export --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --output "$PF_REVIEW_ROOT/anonymous"
python -m experiments.pf_generation evaluate --plan "$PF_REVIEW_ROOT/plan/plan.json" --inputs "$PF_REVIEW_ROOT/anonymous" --models /workspace/voynich-results/m1-review-received-20261105/cal-models --output "$PF_REVIEW_ROOT/evaluation" --jobs 2 --bootstrap 100
```

今回の採点では外部wrapperで `predict_file()` の完了と `score()` の開始を観測した。各scoreの開始時に、全群の保存済み予測件数が9であることをassertした。順序は `evaluation-order.json`、固定モデル・予測hashは `cal-smoke.json` に保存している。予測器がキーを読まない既存56テストも通過した。

以下の既定負例は、すべての生成・fit・採点processが終了してから単独で実行する。展開入力を一時変更するが、script内のfinallyで復元し、最後に新規正監査を行う。

```bash
python -m experiments.pf_generation.tests.run_artifact_probes --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/probes"
```

R1は、正常生成物のコピーだけを変更する次のscriptで再現する。既存の同名コピー・監査出力があるrootでは再実行しない。`UNEXPECTED_ACCEPTANCE` が現行実装の再現結果である。反転側にも同じ欠落を施したケースを含む。

```bash
python sandbox/m1-review/reports/010-pf-generation-check-20261105/probe_missing_policy_traces.py
```

追加の境界fixtureは `terminal_facts()` にstable `choiiin`、visible `choiiinm` を渡し、複合chを1glyphと数えて長さ6→7、crossings `[6]` を確認した。これは合成入力であり、真正資料・実生成の観測例には数えない。

計測は各CLIを別Python wrapperからsubprocessとして実行し、`time.monotonic()` と `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` を保存した。初回の計測準備時に `/usr/bin/time` 不在を検出し、生成開始前にPython wrapperへ変更した。生成失敗によるseed除外・差替えはない。通常順／逆順とfitは最大4processで重なり、恒等fitの完了後に恒等生成を開始した。

元生成物は最後に全manifest checksumと新規sealを検証し、展開入力・実装sourceもplanと再照合した。最終sealは `probes/restored-positive-audit/report.json` を指す。`final-restoration-check.json` 参照。R1のコピーに付いたPASSを正常系へ持ち込んでいない。
