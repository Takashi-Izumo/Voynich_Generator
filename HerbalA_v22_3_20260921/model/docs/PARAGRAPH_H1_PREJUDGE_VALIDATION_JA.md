# Paragraph H1 RUN32 — 審判前self-test

seed `91601`、20 complete bifoliaでmechanical self-testを実施しました。

## no-op

現行親 `v21r+PRETERM+SHORTBODY-H2-GLOBAL` と `PARAH1_NOOP` を直接再生成比較：

- generated rows hash: **20/20一致**
- surface commits hash: **20/20一致**

## RUN32

- eligible committed BODY events: **495**
- prior-line stateが存在し実際に補正を評価したevents: **381**
- actual H1 changes: **12**
- changed bifolia: **7/20**
- packing exact: **20/20**
- support violation: **0**
- invalid rows: **0**

## intervention audit

親とRUN32の全生成行を比較し、12変更行について：

- H1だけ変更: PASS
- H2+不変: PASS
- exact glyph length不変: PASS
- physical width不変: PASS
- H1以外の構造列不変: 20/20
- route current_before/current_after不変: 20/20
- parent RNG untouched: PASS

変更行一覧は `validation/paragraph_h1_running/H1_CHANGED_ROWS.csv` に保存しています。

## STOP

ここで停止しています。blind judge / contestはまだ実行していません。
