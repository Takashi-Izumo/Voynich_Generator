# 014: 独立再検証013・R2への回答

R1の解消と設計訂正012の独立確認を受領した。追加R2は妥当で、こちらでも元scriptを使い、raw候補ラベルと要求側の候補番号が矛盾したまま、新規監査・評価前チェックがPASSすることを再現した。

R2は、監査の結合先候補とraw行のpage/locus/segment/event/candidateを直接一致させることで修正した。同じ共通キーを要求・gate・rawへ適用し、型の取り違えやfield欠落も拒否する。receipt digestや既存候補集合への所属だけで代替しない。記録形式はv2のまま、生成法則・RNG・fit・審判は変更していない。

新planから通常順/逆順24面、恒等対照12面を生成し、130テスト、R2の実データ13実行、R1の13ケース、既定の負例6項目を確認した。前回と12ケースの意味出力・state・実main RNGとfit lawが一致している。

[検証記録](../implementation/014-pf-r2-contextfix/VALIDATION.md)、[manifest](../implementation/014-pf-r2-contextfix/MANIFEST.json)、[独立再検証依頼015](../requests/015-pf-r2-context-recheck.md)を追加した。R2の独立PASSはまだ付けず、本比較・正式採用・main mergeは開始していない。
