# 報告019への修正: post-m末字commitと対照CLI

報告019の最終manifest33項目と先行failure/registration manifestを照合し、未変更sourceで2件の不具合を再現した。修正後は **174 unit、60面の生成・監査、R1/R2を含む34項目の負例/失効確認がPASS**。原版・M1・審判の凍結501fileと展開入力は保存している。全800面の新source実行・採点は開始していない。

## 修正した動作

`surface_commit.py` を候補2群のsamplerにだけ重ねた。W2 H2またはBODY H1の既に選択済みの補正が、m削除後に実際の物理末字になる場合、親のsemantic surface commitへ渡すvisible列を先に確定する。routeの `commit_word` には従来のanchorを渡し、m/rareとpackingもanchor上の既存処理を保持する。既存親のstable child書込み、H1のpending統計は実行し、追加乱数は使わない。

H2が非末字の3→3、H2無変更、rare suffix、F1LF/Stage3Dのroute/visible二段処理は元の経路へ委譲する。BASE/REFERENCEにはwrapperを適用しない。原版のassertを削除したり、生成後にprev_terminalや監査値だけを合わせたりしていない。

新 `surface_commit_policy` とsourceをplanへ封印し、`pfgen_terminal_precommit` receiptを残す。監査はpost-m anchorと準備済み補正からreceiptの必要性を導き、全最終surface→semantic末字→次の要求のprev_terminalをsegment単位で照合する。receipt除去/件数0化、次の要求だけの改変、ログを誤状態へ合わせる偽造も拒否する。

`verify-export` CLIは `--exported` を照合APIの第3位置引数へ接続した。APIの検査と既存引数契約を保持し、実CLIをfresh artifactへ実行してreturncode0を確認した。再封印した偽の正解キーは実CLIでも拒否する。

## 再現と検証

| 確認 | 結果 |
|---|---|
| 修正前 | 同じA:3/91711/PF_GATE_LENGTHでoriginal terminal assertを再現。旧CLIのunexpected `exported` TypeErrorも再現 |
| unit | PF58 / controls33 / M1 27 / judges56 = 174件PASS |
| 境界fixture | original chainの3→2 W2不整合を再現し、修正側でsemantic commit時点から最終H2。BODY 2→1、pending H1、3→3、変更なし、rare prefix/suffix、複合glyph幅、実PLANT begin、F1LF/Stage3Dを確認 |
| 通常順・逆順 | A:2/A:3/G:1 × seed91701/91711 × 3群+原版 × 2順序 = 48面、全監査PASS |
| 恒等設定 | 3葉×seed91701×4群 = 12面、3群と原版の全意味出力・全state・実main RNG一致 |
| 問題の実ケース | f6v.10 / W2 / proposal630、stable3→visible2、物理幅3。可視末字a(ID12)をsemantic stateにcommitし、次のrequest631もprev_terminal=12。terminal_mismatches=0 |
| 正常経路の保存 | 前回R2の12ケースと、意味出力・最終state/main RNGおよび全request/candidate/event/gate/raw記録が完全一致 |
| R1/R2回帰 | copy-onlyの13+11ケース、すべて新規監査で拒否。古いseal失効と評価前チェック拒否を含む |
| 新たな負例 | 両順序のreceipt除去+件数0化、次語状態、偽造commit chainの3件を拒否。実CLIで再封印wrong keyも拒否 |
| 既定6項目 | law/展開設定/生成物+checksum/可視commit/失敗seal/REFERENCE RNGを確認。単独実行しfinallyで復元、最後の新規正監査PASS |
| 対照CLI | fresh A:2/92101、2入口×64=128枝と通常BASE2面。fresh replay監査→export→実CLIで照合PASS |
| 対照データ保存 | その128枝・snapshot・BASE・選択recordは前回v1と完全一致。異なるのはplan bindingだけ |

60面は小規模の機構検証であり、順序・恒等設定の反復を独立した真正標本として数えない。旧421面は新sourceへ継ぎ足していない。固定CAL/モデルは変更せず、この修正の品質・同等性・採用は判定していない。

## 新しい封印plan

- smoke: `589cbc4d1c148910c7346ba3562df2a71ff2b378aef479ec2b284265cde71e74`
- full: `5f0e657be62f5541ef16b40737d44f86bca70cdf990985154693a7fbacb6954a`
- 旧full `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17` は新sourceで拒否する。

新fullは同じ20葉・10seed・4群=800面の準備だけ。外部16葉のlaw payload、known3/layout/mask/scope、展開入力は旧fullと完全一致し、source41fileとsurface commit契約を新しく結合した。PF効果の後続経路で顕在化する補正整合性修復も候補側に含む版として、sourceを混ぜず比較する。再開には検証側で独立確認し、記述的実行登録も新plan/sourceへ更新して、全800面を新rootへ生成する。

## 審判能力と別設計

報告019の106対照・2,240枝の独立機構PASSを受領する。能力結論は **CAPABILITY_NOT_VERIFIED** のまま。length_widthのraw JSD飽和、末字/SPACEの操作実現率不足をこのcommit修正やCLI修正で解決したとは扱わない。

[設計021](../../designs/021-pf-measurement-controls-v2/DESIGN.md)へ、joint energy distanceの新genuine-only校正と支持を広げない条件付きreplayの実現性検証を分けて記録した。新審判・donor方式は未実装・未fit・未予測。旧106組の値、閾値、NA、分母、bootstrap区間を変更しない。

## 保存物

生の語列・生成物・key・snapshotは `/workspace/voynich-results/pf-review019-fix-20261105/` に保存しGitへ入れない。共有するのはplan/scope、非語値の診断、hash、集計・unit/監査記録だけ。

通常順+逆順の48面と監査は約308秒・最大451.4 MiB、恒等12面は同梱performanceを参照。対照128枝の生成/再生/実CLIは約116秒・最大583.3 MiB。独立processを並行実行した値で、群間速度差や本比較予算を示さない。
