# 再現

対象codeは `7db514606b2b77640a3f8454acd4c7b1abbc4a7c`。依存関係・展開runtime・parent archiveは既存M1と同じ。`python` は `/workspace/.venvs/voynich/bin/python` を指す。

下記rootを別の未使用pathへ変えて再実行する。出力を上書きしない。

```bash
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR=/workspace/voynich-results/m1-v2-independent-20261105/numba-cache
export PYTHONPYCACHEPREFIX=/workspace/voynich-results/m1-v2-independent-20261105/pycache
export PF_REVIEW_CHECKOUT=/workspace/voynich-results/m1-v2-independent-20261105/checkout
export PF_REVIEW_ROOT=/workspace/voynich-results/pf-tracefix-independent-20261105
cd "$PF_REVIEW_CHECKOUT"
python -m unittest discover -s experiments/pf_generation/tests -v
python -m unittest discover -s experiments/m1_pf/tests -v
python -m unittest discover -s judges/tests -v
python -m experiments.pf_generation plan --output "$PF_REVIEW_ROOT/plan"
python -m experiments.pf_generation plan --identity --output "$PF_REVIEW_ROOT/identity-plan"
python -m experiments.pf_generation generate --plan "$PF_REVIEW_ROOT/plan/plan.json" --output "$PF_REVIEW_ROOT/forward"
python -m experiments.pf_generation generate --plan "$PF_REVIEW_ROOT/plan/plan.json" --output "$PF_REVIEW_ROOT/reverse" --reverse
python -m experiments.pf_generation generate --plan "$PF_REVIEW_ROOT/identity-plan/plan.json" --output "$PF_REVIEW_ROOT/identity"
python -m experiments.pf_generation audit --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/audit"
python -m experiments.pf_generation audit --plan "$PF_REVIEW_ROOT/identity-plan/plan.json" --generated "$PF_REVIEW_ROOT/identity" --output "$PF_REVIEW_ROOT/identity-audit"
python -m experiments.pf_generation export --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --output "$PF_REVIEW_ROOT/anonymous"
python -m experiments.pf_generation evaluate --plan "$PF_REVIEW_ROOT/plan/plan.json" --inputs "$PF_REVIEW_ROOT/anonymous" --models /workspace/voynich-results/m1-review-received-20261105/cal-models --output "$PF_REVIEW_ROOT/evaluation" --jobs 2 --bootstrap 100
```

今回のfitは旧法則・入力・凍結sourceと一致し、共有v2 planともJSON内容が一致した。実行ログと新規rootを用いており、共有planをコピーしたものではない。

採点時には外部wrapperで `predict_file()` 完了と `score()` 開始を記録し、各scoreの開始時に保存済み全群予測数が9であることをassertした。`evaluation-order.json` を参照。`compare_v1.py` は環境変数 `PF_REVIEW_V1_ROOT`（既定は前回の独立実行root）を使い、意味出力・state・RNG・既存policy値・予測/採点の保存を照合する。

trace負例はコピーだけを変更する。

```bash
python -m experiments.pf_generation.tests.run_trace_probes --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/trace-probes"
python sandbox/m1-review/reports/010-pf-generation-check-20261105/probe_missing_policy_traces.py
```

前回scriptはこのrootで通常監査と両順序を検査する。恒等設定については別の未使用rootにplan/forward/reverseのsymlinkを作り、identity-plan/identity/identityをそれぞれ指したうえで同じscriptを実行した。恒等設定のrepeat指定は同じ生成物のコピーであり、逆順生成したと扱わない。

既定の実データ負例は、他の生成・fit・採点processがすべて終了した後、単独で実行した。対象入力と元生成物はfinallyで復元し、最後に新規正監査を実行する。

```bash
python -m experiments.pf_generation.tests.run_artifact_probes --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/required-probes"
```

今回追加で見つかったR2は、上記process終了後に次のscriptで再現した。通常順と逆順のコピーに同じ候補context不整合を入れる。現対象codeでは `UNEXPECTED_ACCEPTANCE` になる。元生成物は変更しない。

```bash
python sandbox/m1-review/reports/013-pf-tracefix-recheck-20261105/probe_raw_candidate_context.py
```

最後に正常生成物の全manifest checksum、正常seal、実装source、展開入力が一致することを再確認した。`after-extra-probe-original-check.json` 参照。

実行計測はPythonのmonotonic clockと、CLIを子processとして実行したwrapperの `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` を使用した。post-check runnerの初回起動は逆順生成の終了receiptがまだないため、監査や出力作成の前に停止した。全生成終了を確認してから再起動し、全工程を完了した。生成失敗・seed除外・差替えはない。
