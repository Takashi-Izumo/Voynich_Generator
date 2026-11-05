# 011: 独立検証010への対応

報告commit `d30c376bf9ae55c5080290b1b22e050f8cbedd6c` の24ファイルを照合し、R1と設計上の指摘を受領した。通常生成・fit・恒等対照・CALは独立再現されていたが、必要な介入ログの欠落を新規監査が見逃す問題があり、独立結論は要修正だった。

R1は修正前にこちらでも通常順・両順序で誤受理を再現した。修正版はPF候補/要求/gate/raw IDを結合し、END要求の元Mapの `1+proposal_draws` からraw呼出しの完全性を検査する。候補counter・要求receipt・policy行を照合し、反転側も独立に監査する。旧schema v1のplan/PASSは受理しない。

新unit39件、既存M1 27件、審判56件、計122テストがPASS。新規36面、原版/恒等/順序再現、16回のtrace改変と既存6項目の負例を確認した。修正前と12ケースの意味出力・state/RNG、9予測・channelsが一致し、生成法則は保持されている。

能力対照のCAL順位は[訂正012](../designs/012-pf-review-corrections/CAPABILITY_CONTROL_ERRATUM.md)へ分離した。単語NLLが小さいほどCALが高いとは扱わず、旧75%判定を無条件に使わない。凍結審判は変更しない。

[検証記録](../implementation/011-pf-tracefix-v2/VALIDATION.md)と[依頼013](../requests/013-pf-tracefix-recheck.md)を追加した。R1は実装側の負例では解消したが、独立再検証は未完了。本比較・正式採用・main mergeは開始していない。
