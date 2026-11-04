# 現在状態 引き継ぎ — 2026-09-17

## このパッケージに正式マージ済み

- 親 `HerbalA-v22r`
- W2-B2 H2-only local repair

実行上のactive modelは `HerbalA-v22r-W2B2`。

## W2-B2

機械監査・fresh blind 200・多様審判をPASS済み。今回の再マージ監査で保存済みB2と20/20葉hashおよび130/130 requestが完全一致した。

## F1について

F1修正は**一切このパッケージにマージしていない**。

F1解析では `H3|H2` 残差を発見したが、以下は未採用／棄却：

- selector単純弱化
- FIRST_GENERIC raw H3全面差し替え

最後のraw upstream prototypeはFAILであり、本パッケージには含まない。

次の研究候補は、H1/H2/H4+/terminal/length/widthを固定しH3だけを交換する `H3-only constrained sibling` feasibility audit。

## global残差

W2修正後もglobal bigramは4/16で残る。したがって本版は `PASS_WITH_RESIDUAL`。
