# 002: M1 v2の独立再検証

状態: CLOSED — 独立再検証報告 `reports/002-independent-v2-20261105/REVIEW.md` を受領。機構・接続の小規模再検証はPASS。本比較は保留のままです。前回R4は検証側の見落としとして撤回され、v2のRNG専用記録・比較は契約の強化として確認されました。

最初に `experiments/m1_pf/REVIEW_FIXES.md`、元設計と実装を読んでください。実装側のPASSをそのまま信用せず、新しい出力ディレクトリで独立再実行してください。

## 特に再確認する4点

1. 展開済み設定・selector・coreの変更/追加/削除が封印済み計画で拒否されるか。入力treeを信頼済みZIPへ照合する方式の範囲・妥当性も確認する。
2. 生成物とchecksum更新後、古い監査PASSがexportで拒否されるか。再監査失敗時の旧seal失効、repeat側の変更拒否も確認する。
3. END_ONLY 19箇所がatom非観測となり、構造ラベル・実atom観測・末尾情報の利用可否を区別しているか。凍結審判のword_eventsと直接照合する。
4. BASEと原版の実最終main RNGを明示記録・比較しているか。最終stateが同じでmain RNGだけが異なる負例も検査する。

救済停止はrequest採番を介して後続補正乱数にも作用します。波及を含む総効果の扱いを維持し、純粋な直接効果を分離したとは主張しないでください。

## 対象と準備

- 原版・審判の基準commit: `c610c2a81e733748e0fb246de89143d6ecda764e`。
- 検証対象はこのsandboxの `experiments/m1_pf/`。レビュー開始commitを記録する。
- `README.md` / `DESIGN.md` / `VALIDATION.md` は同実装ディレクトリ内。
- 原版の `GITHUB_SETUP_JA.md` に従って親ZIP・Python依存を準備する。原版コード・archive・審判のロジックは変更しない。
- 固定CALモデル: 次のv2 ZIPの `cal-models/` が利用可能。実装payloadの上書き用には使わない。

https://raw.githubusercontent.com/Takashi-Izumo/Voynich_Generator/3e6ecc9ad61b13362369e4b1ea79f0ad12146be0/review-packages/m1-independent-review-20261105-v2.zip

ZIP SHA-256: `3886b3ec756137e366b3e203b91e3076a198f681860d319d0247869ec669ead3`

model-set SHA-256: `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`

## 小規模再実行

実装READMEのCLIを使い、A:2/A:3/G:1、seed91701で以下を実施してください。

1. 新規・回帰unitテストと凍結審判テスト。
2. schema-v2の新しいplan、3群と原版REFERENCEの生成。
3. 群の順序を反転して別出力へ再生成し、原版一致とrepeatを監査。
4. 匿名export、固定モデルのJ24.CALで全予測を保存後に採点、2つの対応比較。
5. 上記4指摘の負例を独立に作り、期待する位置で拒否されるか確認。

目安は27＋56テスト、通常順/逆順の実生成24頁、各群3trialです。実装側の自己申告を引用しただけなら、その点を明記してください。200セット本比較や新しいパラメータ選択へは進まないでください。

## 報告

`sandbox/m1-review/templates/REVIEW_REPORT.md` を元に、`reports/<review-id>/REVIEW.md` を追加し、このsandboxブランチへcommit/pushしてください。コードを修正してPASSにするのではなく、問題の再現手順と重要度を報告してください。最後に、本比較へ進む条件が満たされたか・保留条件は何かを記載してください。mainへのmergeは行いません。
