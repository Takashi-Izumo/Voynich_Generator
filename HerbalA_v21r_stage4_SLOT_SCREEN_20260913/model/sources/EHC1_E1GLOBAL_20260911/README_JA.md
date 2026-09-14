# EHC1 E1GLOBAL — ①だけの実装・審判

状態: JUDGED_NOT_PROMOTED。正式基準BTI2は変更しない。

## 再実行

完全版ZIPを新しいディレクトリへ展開し、同梱環境に必要なライブラリを用意する。`inputs/RMW1_BTI2_EHC1_20260911/requirements.txt`も参照。

```bash
python -B code/run_generation.py
python -B code/teacher_audit.py
python -B code/judge_experiment.py
python -B code/smoke_relocation.py
python -B code/build_report_and_validate.py
```

生成runnerは既存出力を再利用する。最初から再生成するには別展開先で`outputs/generated`を削除する。旧入力は変更しない。`freeze_plan.py`は今回の固定計画を作った履歴コードであり、再実行のたびにseedや計画を変更する必要はない。

結果版ZIPは`inputs/`を含まない。同名のEHC1・旧審判・DIAG1結果ZIPを`inputs/`へ展開するか、完全版を使う。結果版に完全再現できる全入力があるとは主張しない。

通常SPACEとH2が主指標。1字の予測loss、known3参照の真偽得点、target JSDは別物として読む。すべての出力を保存し、勝つseedだけを選んでいない。文字列が違う版の同じ語番号を同一文脈介入とみなさない。

別展開先試験は同じPython/NumPy/Numba等の環境での試験であり、異なるバージョンでbit-level一致する保証ではない。
