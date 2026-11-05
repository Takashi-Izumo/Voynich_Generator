# 再現手順

対象は `a6873a2f3af64b423411dc9daeb14fa43879dea3`。依存関係・展開runtime・parent archiveは既存M1と同じ。以下のpythonは `/workspace/.venvs/voynich/bin/python` を使う。

再実行では必ず未使用のrootに変更する。既存planや生成物を上書きしない。

```bash
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR=/workspace/voynich-results/m1-v2-independent-20261105/numba-cache
export PYTHONPYCACHEPREFIX=/workspace/voynich-results/m1-v2-independent-20261105/pycache
export PF_REVIEW_CHECKOUT=/workspace/voynich-results/m1-v2-independent-20261105/checkout
export PF_REVIEW_ROOT=/workspace/voynich-results/pf-r2-independent-20261105
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
python -m experiments.pf_generation summarize --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --output "$PF_REVIEW_ROOT/summary"
python -m experiments.pf_generation export --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --output "$PF_REVIEW_ROOT/anonymous"
python -m experiments.pf_generation evaluate --plan "$PF_REVIEW_ROOT/plan/plan.json" --inputs "$PF_REVIEW_ROOT/anonymous" --models /workspace/voynich-results/m1-review-received-20261105/cal-models --output "$PF_REVIEW_ROOT/evaluation" --jobs 2 --bootstrap 100
```

今回の採点時には外部wrapperでpredict_file完了とscore開始を観測し、各score開始時に全群の保存済み予測が9件あることをassertした。`evaluation-order.json` 参照。固定モデルhashと予測器のキー未読は各manifestでも照合した。

前回v2との比較は、本報告の `compare_prior.py` を実行した。`PF_REVIEW_PRIOR_ROOT` の既定は `/workspace/voynich-results/pf-tracefix-independent-20261105`。全意味出力に加え、requestsのpfgen情報、PF候補・event・gate/raw記録もそのまま比較する。predictions/channels/measurements/summaryはbyte hashで比較する。

R2/R1の追加負例はそれぞれ別の出力rootにコピーだけを作るので、同時実行できる。今回もこれらは並行し、全process終了を待ってから次の実入力負例へ進んだ。

```bash
python -m experiments.pf_generation.tests.run_context_probes --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/context-probes"
python -m experiments.pf_generation.tests.run_trace_probes --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/r1-probes"
python sandbox/m1-review/reports/013-pf-tracefix-recheck-20261105/probe_raw_candidate_context.py
```

恒等設定の負例は、identity出力を別rootへcopytreeし、`tests.run_context_probes.corrupt_context(copy, 'candidate')` で改変した。manifest検証を通してから、identity-planで新規auditを実行し、`Raw call belongs to another candidate context` の拒否を確認した。失敗後にsealが消え、auditedも拒否し、元identityのauditedが通ることを確認した。`identity-context-probe.json` 参照。

最後に、他の生成・fit・採点・負例processがすべて終了してから、次を単独実行した。実入力と元生成物を一時変更するが、finallyで元bytesへ戻し、最後に新規正監査を実行する。

```bash
python -m experiments.pf_generation.tests.run_artifact_probes --plan "$PF_REVIEW_ROOT/plan/plan.json" --generated "$PF_REVIEW_ROOT/forward" --repeat "$PF_REVIEW_ROOT/reverse" --output "$PF_REVIEW_ROOT/required-probes"
```

正常seal・全manifest checksum・source・runtime inputsを再検証した記録は `final-restoration.json`。時間・最大RSSは各CLIの別Python wrapperからmonotonic clockと `resource.getrusage(RUSAGE_CHILDREN).ru_maxrss` で測定した。生成失敗・seed除外・差替えはない。
