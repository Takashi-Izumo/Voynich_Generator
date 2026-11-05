# 前回v1レビューのR4を訂正

日付: 2026-11-05（日本時間）

前回の独立レビューで「BASEと原版の最終main RNGを記録・比較していない」としたR4は不正確でした。レビュー側の見落としです。この指摘を撤回します。

v1でも、凍結parentの`run_bti2_ehc1.generate()`が実際の終了RNGを`MECHANICAL.json`の`rng_end`に保存していました。M1の`audit.semantic_case()`は`elapsed_seconds`を除くMECHANICAL全体を比較しており、`rng_end`もBASE対REFERENCE・順序反転の比較に含まれていました。元の独立生成物でも実RNGの記録を確認しています。

`M1_FINAL.json`にRNG専用fieldがないことと、RNGを記録・比較していないことを混同したのが誤りでした。v2の専用field、採取元の明示、MECHANICALとの整合確認、RNGだけ異なる負例の専用検証は、契約を明確にする強化として評価します。

R1（展開済み入力の固定）、R2（旧監査PASSと生成物の結合）、R3（END_ONLYのatom観測表示）の負例はv1で独立再現しており、この訂正の対象外です。request採番を介したside RNGへの波及も、独立再生成で確認した総効果の解釈として維持します。

以前の報告・ZIPは履歴として残します。以後はこの訂正と同じディレクトリのv2独立検証報告を合わせて参照してください。
