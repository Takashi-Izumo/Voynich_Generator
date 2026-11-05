# 依頼022: 報告019のcommit順序/CLI修正を独立確認

開始HEADを記録し、[実装020](../implementation/020-pf-surface-commit-fix/VALIDATION.md) とそのMANIFESTを照合してください。報告019の修正依頼に対応したもので、原版・M1・審判の凍結fileは変更していません。今回の修正は `experiments/pf_generation/surface_commit.py`、sampler接続、plan/監査契約、および対照CLIです。

## 独立に確認してほしい点

1. 原版anchorのroute commitを保ち、m/rare後の最終visible H2/H1をsemantic surface commit前へ渡すこと。後付けでログ/prev_terminalを直す処理ではなく、追加乱数もないこと。PF候補2群だけへ適用し、BASE/REFERENCEはliteral原版であること。
2. **A:3 / seed91711 / PF_GATE_LENGTH** を新planと新rootで生成・監査すること。f6v.10/proposal630のstable3→visible2で末字ID12、surface_commitsの末字状態、次のrequest631のprev_terminalが一致すること。raw語を報告へ貼らず、ID/長さ/幅/hashで記録すること。
3. literal parent chainを呼ぶ追加fixtureで、m保持3→3、H2不変、rare prefix/suffix、BODY H1の2→1とpending統計、PLANTの実begin、F1LF/Stage3Dのroute/visible二段処理を確認すること。
4. 通常/恒等の意味出力・全state・実main RNG保存、支持/packing/末字/PLANT、元2候補/LEN1、R1/R2の13/11負例と既定6項目を再確認すること。新receipt除去+件数0化、次語状態、ログを誤状態へ合わせた偽造も拒否すること。
5. **実CLI** `python -m experiments.pf_controls verify-export --plan ... --generated ... --exported ...` の成功を確認すること。APIだけの代替で済ませず、再封印したwrong keyを同じCLIが拒否すること。

CLIとunitは各package READMEにあります。最小の問題ケースは `python -m experiments.pf_generation plan --bifolia A:3 --runs 91711 --output <fresh-plan>` → `generate` → `audit` で、全3群+REFERENCEを作れます。通常/逆順と恒等の検査にはA:2/A:3/G:1を使ってください。旧報告のreproduce_failure.pyは旧plan hashを固定した修正前の再現器なので、新sourceの確認には新しいplanを使います。

`surface_commit_policy` とsourceが追加されたため、旧plan/PASSは拒否します。新fullは [full-plan/plan.json](../implementation/020-pf-surface-commit-fix/full-plan/plan.json)、hash `5f0e657be62f5541ef16b40737d44f86bca70cdf990985154693a7fbacb6954a`。law payload・known3/layout/mask・20葉/10seedは旧版と一致します。

## 本比較と測定設計

この依頼はまず修正の独立確認です。旧421面の再利用・seed除外/差替え・assert無効化で継続しません。検証側の既存実行指示と報告019の記述的方針に従って再実行する場合は、独立確認後に新plan/sourceへ実行登録を更新し、全800面を新rootで生成・全予測保存後に採点してください。旧 `DESCRIPTIVE_EXECUTION.json` を新hashに見せかけて流用しません。

対照の能力は **未確認/基準未達のまま** です。報告019の値と区間は保存し、この修正から品質改善・同等性・採用を主張しません。JSD飽和と操作不足には [設計021](../designs/021-pf-measurement-controls-v2/DESIGN.md) / [JSON](../designs/021-pf-measurement-controls-v2/PROPOSAL.json) を返しています。新距離のgenuine-only fit/校正、支持内条件付きreplayの成立性、予測前操作80%gateについて設計意見もください。**新審判/新donorはこの修正に未実装**であり、現行v0.3への混入や旧106組の合格への付け替えはしません。

報告は新しい `reports/<unique-id>/` のみへ追加・commit/pushし、source HEAD、全コマンド/予定数/成功失敗数、hash manifestを記録してください。raw生成語・真正語・keys・snapshot・archiveをGitへ含めず、既存報告、実装、status、requestは変更しません。main merge/正式採用は対象外です。
