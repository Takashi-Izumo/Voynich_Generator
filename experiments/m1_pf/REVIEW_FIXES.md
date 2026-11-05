# 独立検証後の修正（schema v2）

入力はこのチャットへ返された4点の指摘です。別クラウド側の `REVIEW.md` / findings ZIP自体はこの環境に存在せず、本文の指摘を基に再現・修正しています。本比較への移行は引き続き保留です。

| 指摘 | 修正 | 回帰確認 |
|---|---|---|
| 展開済み設定が計画に固定されない | `inputs.py`で信頼済み親ZIPの全非コンパイラcacheファイルと展開treeを照合。設定・selector・pickle core・データ・codeを含む15,632ファイルのtree hashをplanへ固定し、計画読込時・各生成開始時に再検証。差分を自動修復しない。 | 同サイズの設定変更を拒否。実runtimeのfold0.beta変更でも封印済みplanが拒否し、原バイト復元後に再通過。 |
| 古い監査PASSが再利用される | reportとAUDIT sealの両方に、監査したmanifest・copied plan・generation statusのhashを結合。export前に全case checksumを再検査し、現在のreceiptと照合。repeat側もbindingを再検証。再監査開始時に旧sealを無効化。 | tokensとmanifest checksumを更新しても旧PASSを拒否。seal側だけbindingを差し替えても旧reportを拒否。失敗した再監査はsealを残さない。 |
| END_ONLYをatomの観測対象と誤表示 | 凍結審判の`word_events`をそのまま使いatom観測集合を定義。`structural_end_atom`は構造上の候補、`judge_atom`は実観測atom（なければnull）、`judge_observed`は実集合の所属。`endpoint_usable`はEND_ONLYを含む末尾情報の利用可能性として別に保持。 | 3葉のEND_ONLY 19箇所は全件atom非観測。FULL/END_ONLY/NONEとPLANT末尾のテストを追加。 |
| 最終main RNGの専用記録・比較がない | overlayと原版REFERENCEの実`rand.bit_generator.state`を終了時にdeepcopyし、M1_FINALへstate/hashを明示保存。MECHANICAL.rng_endとの整合、BASE対REFERENCE、repeatを専用条件で比較。 | state最終hashが同じでもmain RNGが違えば専用比較で拒否。M1_FINALとMECHANICALのRNG不整合も拒否。 |

旧版でもMECHANICALの`rng_end`は一般の意味出力比較に含まれていましたが、今回、main RNGの採取元・記録・専用比較を明示し、欠落時に拒否する契約にしました。

v1のplan/生成物/監査PASSをv2へ読み替えません。新しいplanから再生成・再監査・再exportが必要です。原版v22.3、親archive、審判v0.3のロジックは変更していません。

## 比較の解釈

救済停止は、破棄枝を含むrequest採番を介して後続補正乱数にも作用します。原版再現のためこの規則を保ち、比較はその波及を含む総効果とします。直接効果の分離・独立した一般化確認・能力検証・正式昇格を主張しません。

v2の実行結果は`VALIDATION.md`と`validation/`に記録します。v1の公開ZIPは履歴として残り、再検証には修正版ZIPを指定してください。
