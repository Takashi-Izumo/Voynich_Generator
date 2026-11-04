# Stage 3D source-law provenance note

Status: `CURRENT-TL RECONSTRUCTION / EXACT PRIOR STAGE1 TABLE ARTIFACT NOT MOUNTED`

Stage 3Dのselector式・strict gate・LOBO除外・tau=20・support invariantsは引き継ぎ仕様から実装した。
一方、引き継ぎで列挙された以下の旧Stage 1/2成果物そのものは、この計算ランタイムには存在しなかった。

- `F1LF_terminal_source_contest_20260920.zip`
- `F1LF_selector_STOP_contest_20260920.zip`
- `17_SHARED_CONTEXT_TAU20_COMPONENT_EVENTS.csv`
- `01_TARGET_F1LF_STRICT.csv` / `01_TARGETS.csv`

そのため、このパッケージの `f1lf_length_terminal_law.py` は、親v22.2の凍結event/schedule metadataとZL3b入力から、
whole-bifolium LOBOでsource lawを再構成している。strict targetは88 events / 20 complete bifoliaを正確に再現した。

引き継ぎに記録された旧contestの full source counts は：

- A_F1 = 490
- B_BODY = 1312
- C_MID_LF = 460

現在TLのStage3D law builderは、selectorの長さ分岐に合わせてsourceをshort/longへ直接分けるため、これら旧contestの
`shared-context source-gain` 集計値とは同一定義のカウントではない。したがって、この3数値の単純一致を主張しない。

## Stage 3Dで確定してよいもの

- strict gate = 88 events / 20 complete bifolia
- target bifoliumはsource lawから丸ごと除外
- L<=3: normal middle-LF selector
- L>=4: F1 selector + normal-LF `P(l)` inheritance
- non-l比とy/n比保存
- support changes=0
- STOP / candidate-bank mechanism / packing / retry / route clockは変更しない
- final childはcommit前に確定し、semantic / visible terminalを一致させる

## 次段階での確認

Stage 3Eの冒頭で、旧Stage1/2 component artifactが取得できる場合は、現在TLで再構成したsource lawと照合する。
照合なしに正式 `HerbalA-v22.3` へ昇格しない。
