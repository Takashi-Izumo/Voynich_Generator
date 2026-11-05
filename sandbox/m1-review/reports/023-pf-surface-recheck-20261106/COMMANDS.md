# コマンドと再現条件

この環境のPythonは `/workspace/.venvs/voynich/bin/python`。checkoutは `/workspace/voynich-results/m1-v2-independent-20261105/checkout`、実行rootは `/workspace/voynich-results/pf-surface-independent-20261106`。

```bash
export NUMBA_NUM_THREADS=2
export NUMBA_CACHE_DIR=/workspace/voynich-results/m1-v2-independent-20261105/numba-cache
export PYTHONPYCACHEPREFIX=/workspace/voynich-results/m1-v2-independent-20261105/pycache
```

各subprocessの正確な引数・終了コード・所要時間は [COMMAND_RESULTS.json](COMMAND_RESULTS.json)。planは `create_plan` / `pf_controls.plan.create` をfreshに実行し、実装020の各封印planと照合した。

検証コードは [review_fix.py](review_fix.py)。今回は期待例外/外側checksumのハーネス修正後、[resume_review.py](resume_review.py)、[finish_review.py](finish_review.py)で未実施の項目だけを実行した。最終版review_fix.pyには訂正を反映した。再実行では実行用コピーのOUTを未使用rootへ変更し、既存出力を上書きしない。過去の正常出力とモデルを参照するため、他環境ではそれらの保存先も対応させる。

通常・逆順・恒等の生成は別processと別出力rootで並行実行した。正監査後のR1/R2はcopy-onlyの独立processで実行。展開設定を一時変更する既定のartifact probeだけは、他のsource依存jobがない状態で単独実行し、復元後に正監査した。生成器・審判のコードは変更していない。

対照のCLI確認はAPIの代替ではなく、次の実CLIをfreshな監査済み生成物・exportへ実行した。正常はreturncode0、不正キーは正しく再封印したうえで同じCLIがreturncode1、内容照合の理由で拒否した。

```bash
python -m experiments.pf_controls verify-export --plan /workspace/voynich-results/pf-surface-independent-20261106/control-plan/plan.json --generated /workspace/voynich-results/pf-surface-independent-20261106/control-generate --exported /workspace/voynich-results/pf-surface-independent-20261106/control-export
```

共有物は集計・hash・非語値の診断・検証コードだけ。raw面、語列、キー、snapshot、donor列は実行rootに保存しGitへ含めない。
