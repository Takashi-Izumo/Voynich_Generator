# 報告015・依頼016の受領とPF対照実装

報告015は22file、依頼016は15fileについて、manifestのサイズとSHA-256を確認しました。015の独立結果は `PASS_R2_INDEPENDENT_RECHECK`、R1回帰もPASS、追加要修正なしです。第一案本体のR2は解消として受領します。

依頼016の能力対照を独立package `experiments/pf_controls/` へ実装しました。原版・M1・審判・現在の `pf_generation` ソースは変更していません。本比較準備planもhashを維持してload可能です。実装設計は [017](../designs/017-pf-controls-v1/DESIGN.md)、実行証拠は [VALIDATION](../implementation/017-pf-controls-v1/VALIDATION.md)、次の依頼は [018](../requests/018-pf-controls-independent-check.md)。

入口の全状態保存・64枝隔離再生・外部16葉proxy・支持内donor選択・真正面対改変面export・全record新規再生監査・固定CAL/3channel能力判定のCLIを揃えています。生NLL順位をCALの正解にせず、nearは診断、far3channelを独立に判定します。全予測の保存を採点より先に要求し、結果は独立確認書と区別します。

実装側で行ったのは3葉の機構smokeと負例までです。全対照の予測/採点、能力PASS、800面比較、採用は未実行です。検証側が独立確認後に全対照と本比較を担う分担を維持します。
