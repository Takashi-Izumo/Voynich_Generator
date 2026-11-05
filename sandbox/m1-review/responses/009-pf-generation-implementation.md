# 009: PF生成改善・第1比較の実装

ユーザーの「実装」に基づき、設計007の最優先案を `experiments/pf_generation/` へ実装しました。BASE / PF_GATE / PF_GATE_LENGTHを独立して扱います。個別末字とSPACEは後続studyのため混在させていません。

新unit20件、既存M1の27件、審判56件がPASS。通常順/逆順24面、恒等対照12面、予算測定12面の計48面を生成し、原版再現・最終state/RNG・順序再現・支持/packing・境界を検査しました。固定CALの9予測・2対比へ接続しています。

実入力・law・生成物/checksum・REFERENCE RNGを変更する6項目の負例を確認し、元bytesへ復元後に新たな監査PASSを得ました。5外側foldでfitでき、smokeの3foldは再fit一致。全体の学習資料は既存開発資料であり、改善や一般化の主張はありません。

[検証記録](../implementation/009-pf-generation-v1/VALIDATION.md)、[実装manifest](../implementation/009-pf-generation-v1/MANIFEST.json)、[新しい独立検証依頼010](../requests/010-pf-generation-independent-check.md)を追加しました。依頼008の文書レビューが既にPASSしたという意味ではありません。新たなユーザーの実装指示を受け、現在の受け渡しを実装検証へ進めています。

審判能力対照64枝replayと新本比較は次段階です。main・凍結原版・既存M1・審判・過去の報告は変更していません。
