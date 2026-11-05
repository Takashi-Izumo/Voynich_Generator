# v2独立再検証コマンド

検証開始時のsandbox commitは`6c1dbcd72e942ac3d675df43dbc7872105249bf8`。原版・審判の基準は`c610c2a81e733748e0fb246de89143d6ecda764e`。

元の検証環境を保存するため独立worktreeを使用し、展開runtimeを独立コピーした。原版・審判・候補実装に修正なし。下記rootは今回の記録用であり、再実行では未使用の出力先と対応するcheckoutへ読み替える。

```bash
M1_V2_ROOT=/workspace/voynich-results/m1-v2-independent-20261105
M1_V2_PY=/workspace/.venvs/voynich/bin/python
M1_V2_MODELS=/workspace/voynich-results/m1-review-received-20261105/cal-models
cd "$M1_V2_ROOT/checkout"
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR="$M1_V2_ROOT/numba-cache"
export PYTHONPYCACHEPREFIX="$M1_V2_ROOT/pycache"

"$M1_V2_PY" -m unittest discover -s experiments/m1_pf/tests -v
"$M1_V2_PY" -m unittest discover -s judges/tests -v
"$M1_V2_PY" -m experiments.m1_pf plan --output "$M1_V2_ROOT/plan" --bifolia A:2,A:3,G:1 --runs 91701
"$M1_V2_PY" "$M1_V2_ROOT/probes.py" inputs --root "$M1_V2_ROOT"
"$M1_V2_PY" -m experiments.m1_pf generate --plan "$M1_V2_ROOT/plan/plan.json" --output "$M1_V2_ROOT/forward" --reference
"$M1_V2_PY" -m experiments.m1_pf generate --plan "$M1_V2_ROOT/plan/plan.json" --output "$M1_V2_ROOT/reverse" --reference --arm-order PF_ANCHOR,PF_NO_RESCUE,BASE
"$M1_V2_PY" "$M1_V2_ROOT/probes.py" scope --root "$M1_V2_ROOT"
"$M1_V2_PY" -m experiments.m1_pf audit --plan "$M1_V2_ROOT/plan/plan.json" --generated "$M1_V2_ROOT/forward" --repeat "$M1_V2_ROOT/reverse" --output "$M1_V2_ROOT/audit"
"$M1_V2_PY" -m experiments.m1_pf export --plan "$M1_V2_ROOT/plan/plan.json" --generated "$M1_V2_ROOT/forward" --output "$M1_V2_ROOT/anonymous"
"$M1_V2_PY" -m experiments.m1_pf evaluate --plan "$M1_V2_ROOT/plan/plan.json" --inputs "$M1_V2_ROOT/anonymous" --models "$M1_V2_MODELS" --output "$M1_V2_ROOT/evaluation" --jobs 2 --bootstrap 100
"$M1_V2_PY" "$M1_V2_ROOT/probes.py" artifacts --root "$M1_V2_ROOT"
```

通常順と逆順のgenerateは別processで並行実行。入力を変更する`inputs`の負例はそれより前に単独で実行し、復元とplanの再通過を確認した。`artifacts`は正常生成物のコピーだけを変更する。

モデルはこの環境に既にあった固定CALを使用する。内容は元releaseと一致し、canonical model-set SHA-256は`61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。モデルの再学習・調整・PROTO fallbackは行わない。

小規模な検証用プローブのファイル探索を調整した際、重複実行を検知して片方をSIGINTで停止した。候補実装の不具合には数えていない。両process終了後、最終版の`inputs`を単独で最初から再実行し、入力全復元とplan再通過を確認した。実生成にはその後の正常な入力だけを使用した。
