# 本比較用の実行

能力対照の独立確認後に検証側で実行する。現時点では対照が未実装で、pending記録は開始条件を満たさない。ユーザーへの再度の承認質問を要求する手順ではない。

`python` は `/workspace/.venvs/voynich/bin/python`。計画とスクリプトの位置、出力先は実行環境に合わせる。新規出力rootを指定し、既存出力を上書きしない。

```bash
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR=/workspace/voynich-results/m1-v2-independent-20261105/numba-cache
export PYTHONPYCACHEPREFIX=/workspace/voynich-results/m1-v2-independent-20261105/pycache
export PF_STUDY_CHECKOUT=/workspace/voynich-results/m1-v2-independent-20261105/checkout
export PF_STUDY_REPORT="$PF_STUDY_CHECKOUT/sandbox/m1-review/reports/016-controls-and-main-comparison-20261105"
export PF_STUDY_OUTPUT=/workspace/voynich-results/pf-first-full-comparison-20261105
```

割当確認だけなら能力確認書を使わず実行できる。800件、workerごと200件、generation_started=falseを返す。

```bash
python "$PF_STUDY_REPORT/run_comparison.py" --checkout "$PF_STUDY_CHECKOUT" --plan "$PF_STUDY_REPORT/full-plan/plan.json" --output "$PF_STUDY_OUTPUT/generated" --purpose main --workers 4 --dry-run
```

独立確認後に検証側が作る `CAPABILITY_REVIEW.json` の最小形:

```json
{
  "schema_version": 1,
  "status": "PASS_CAPABILITY_REVIEW",
  "comparison_plan_hash": "262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17",
  "model_set_hash": "61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79",
  "required_channels": ["ATOM.PARA_END/length_width", "ATOM.PARA_END/terminal", "ATOM.PARA_END/space_T_H1"],
  "channel_results": {
    "ATOM.PARA_END/length_width": {"status": "PASS"},
    "ATOM.PARA_END/terminal": {"status": "PASS"},
    "ATOM.PARA_END/space_T_H1": {"status": "PASS"}
  }
}
```

これはschemaの例であり、対照PASSの実測記録ではない。実際の確認書にはcontrol plan・実装・予測・採点・独立報告のhashと各channelの実測値も添える。現時点の確認書をこの文字列へ書き換えて実行条件を満たしたことにしない。

```bash
python "$PF_STUDY_REPORT/run_comparison.py" --checkout "$PF_STUDY_CHECKOUT" --plan "$PF_STUDY_REPORT/full-plan/plan.json" --output "$PF_STUDY_OUTPUT/generated" --purpose main --workers 4 --capability-review "$PF_STUDY_OUTPUT/CAPABILITY_REVIEW.json"
cd "$PF_STUDY_CHECKOUT"
python -m experiments.pf_generation audit --plan "$PF_STUDY_REPORT/full-plan/plan.json" --generated "$PF_STUDY_OUTPUT/generated" --output "$PF_STUDY_OUTPUT/audit"
python -m experiments.pf_generation summarize --plan "$PF_STUDY_REPORT/full-plan/plan.json" --generated "$PF_STUDY_OUTPUT/generated" --output "$PF_STUDY_OUTPUT/diagnostics"
python -m experiments.pf_generation export --plan "$PF_STUDY_REPORT/full-plan/plan.json" --generated "$PF_STUDY_OUTPUT/generated" --output "$PF_STUDY_OUTPUT/anonymous"
python -m experiments.pf_generation evaluate --plan "$PF_STUDY_REPORT/full-plan/plan.json" --inputs "$PF_STUDY_OUTPUT/anonymous" --models /workspace/voynich-results/m1-review-received-20261105/cal-models --output "$PF_STUDY_OUTPUT/evaluation" --jobs 4 --bootstrap 10000
```

各工程の成功を確認してから次へ進む。上記を失敗後も続ける単純なshell列として実行しない。実行中の進捗はworkersのjournalから表示する。最初のworker失敗時は他workerもケース境界で停止し、STATUSはFAILED、部分出力を保存する。途中状態を監査PASSへ昇格させない。

試運転は既存3葉smoke planで `--purpose smoke` を使って12面を生成し、独立監査で既存smokeをrepeatに指定して一致を確認した。full planをsmoke扱いする操作と、能力確認書のないmain実行は出力root作成前に拒否された。証拠は `driver-prechecks.json` と `orchestrator-smoke-audit.json`。
