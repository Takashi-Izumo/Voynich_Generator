# 末字commit修正版の記述比較

**末字commit・対照CLIの修正は確認済み。全800面を新規生成し、独立補助監査経由で600組の比較を完了した。今回、明確な改善は確認できず、BASEを維持する。**

通常の製品監査には別のsplit scope不具合が残っている。公式FAILと停止記録を保存し、原版条件に基づく独立確認書を別に封印して計測した。**製品監査PASS・正式採用という結果ではない。** 審判能力もCAPABILITY_NOT_VERIFIEDのまま。

## 実行と確認

- 修正sourceは `43a6895`。独立再検証023で174 unit、60面、R1/R2を含む34項目の拒否・失効確認、fresh128枝と実CLI成功/不正キー拒否がPASS。原版・M1・審判の凍結501fileを保存した。
- 新plan `5f0e657be62f5541ef16b40737d44f86bca70cdf990985154693a7fbacb6954a`、同じ20葉・10seed。BASE/PF_GATE/PF_GATE_LENGTH/REFERENCE各200面、計**800面**を新rootへ生成。旧421面を再利用せず、除外・差替えなし。生成は約2,601秒で正常終了。
- 前回停止したA:3/91711/PF_GATE_LENGTHも通過。proposal630と次のrequest631はともに末字ID12。独立smoke時の全意味出力・状態・実main RNGと一致した。[MAIN_CASE_REGRESSION.json](MAIN_CASE_REGRESSION.json)。修復receiptは全試行を含めPF_GATE_LENGTHのA:3/91710・91711に各1件、他群0件。
- 製品監査はD:4/f29v.9のsplit scope誤判定で採点前に停止。原版の`nsegments/segment_id/boundary`条件と、監査の`segment_id>0`が一致しない。番号`0,2`、segment数2の実scheduleで、正しいfalseを監査が拒否する。誤ったtrueと0.8 gainを入れたtraceを受理する負例も再現した。[不具合と修正依頼](AUDIT_SCOPE_FINDING.md)。
- 製品コードと生成物を変更せず、canonical scheduleから原版条件を導く独立検証器を別に封印。**全600 arm-case、BASE対REFERENCE全200組の意味出力・全state・実main RNGがPASS**。R1/R2/末字の27負例と誤split補正2件も拒否した。公式AUDIT sealは発行していない。
- 予測前の追加登録 `0f74558` に従い、診断/exportのprivateコピーでrelease guardだけを独立確認書へ接続。処理本体と固定審判APIは同じ。**全600予測を保存後に採点**した。過去の独立M1本比較BASE200面との全意味出力・状態・実乱数一致も確認した。

最初の登録は `31700ae`。[追加方針](AUXILIARY_PROTOCOL.md)、[独立補助監査確認書](INDEPENDENT_AUDIT_REVIEW.json)、[guard接続記録](AUXILIARY_AUTHORITY_ADAPTERS.json)、[予測順序](PREDICTION_ORDER.json)を参照。元の公式FAIL・通常経路の停止statusはそのまま残す。

## 固定CALの主結果

値は審判の正解率。同点0.5、seed平均後にbifolium等重み。**50%に近いほど生成器側に有利**とする。括弧内は葉単位bootstrap10,000回の記述的95%区間。

| 群 | 全体 J24.CAL | 段落末 ATOM.PARA_END.CAL |
|---|---:|---:|
| BASE | **62.0%**（47.0–76.5%） | **73.3%**（58.3–86.4%） |
| PF_GATE：終端確率調整 | **62.0%**（46.5–76.5%） | **73.1%**（57.2–86.7%） |
| PF_GATE_LENGTH：語長調整も追加 | **65.0%**（50.0–79.0%） | **72.5%**（58.1–85.0%） |

全体は200試行・比較可能20葉、NA=0、同点=0。段落末は200試行中180比較可能・18葉、NA=20。段落末の同点はBASE4、PF_GATE5、PF_GATE_LENGTH3。NAを同点に置き換えていない。

## 事前指定した対応差

下表は共通比較可能trialでの、**50%からの距離の変化**。単位はpercentage point。負なら50%へ近づき、正なら遠ざかる。今回は全群50%より上なので、率差と距離差の数値は一致する。

| 対比 | 指標 | 距離変化 | 葉bootstrap 95%区間 |
|---|---|---:|---:|
| BASE→PF_GATE | J24.CAL | 0.00 pp | −2.50〜+2.50 pp |
| BASE→PF_GATE | PARA_END.CAL | −0.28 pp | −2.50〜+1.94 pp |
| PF_GATE→PF_GATE_LENGTH | J24.CAL | +3.00 pp | −4.50〜+10.00 pp |
| PF_GATE→PF_GATE_LENGTH | PARA_END.CAL | −0.56 pp | −6.11〜+5.56 pp |

終端確率だけの調整では全体平均は同じ。語長も調整した群は、この集合では全体の正解率が上がる方向、段落末はわずかに下がる方向だった。**対応差の区間はいずれも0を跨ぎ、全体・局所の改善を確認できる結果ではない。**

全96 view×3群の率・coverage・NA・区間は [ALL_VIEWS.csv](ALL_VIEWS.csv)、96 view×2対比の対応率差と50%距離差の区間は [ALL_PAIRED.csv](ALL_PAIRED.csv)。主/主要局所の葉別結果は [PRIMARY_BY_BIFOLIUM.csv](PRIMARY_BY_BIFOLIUM.csv)。元の採点行から全288率、主結果6区間、主要対比4区間を独立再計算し一致した：[INDEPENDENT_STATISTICS.json](INDEPENDENT_STATISTICS.json)。

## 生成の変化

同じ観測可能PF末尾29か所×10seedについて、ケース内→seed→葉等重みで集計した。18葉の可視末尾の診断であり、真正資料との同等性を表す値ではない。

| 群 | 平均可視glyph長 | 7glyph以上 | 3glyph以下 |
|---|---:|---:|---:|
| BASE | 4.656 | 4.72% | 19.44% |
| PF_GATE | 4.782 | 5.46% | 17.04% |
| PF_GATE_LENGTH | 4.806 | 10.00% | 19.63% |

法則の変更は実際の生成へ反映されている。gate変更呼出しはPF_GATE 9,487、PF_GATE_LENGTH 9,456。語長群のraw proposalは373,409、raw drawは1,363,177、32draw後のanchor fallbackは22回（0.00589%）。支持やpackingの失敗を差替えて継続していない。[PF_DIAGNOSTICS.json](PF_DIAGNOSTICS.json)、[修復件数](TERMINAL_REPAIR_SUMMARY.json)。

## 判断と次の作業

**BASE維持、第一案の採用は保留。** 補助経路の記述値を得られた一方、製品監査のsplit scope修正は実装側へ返しており、未修正のままである。原版の条件へ監査を合わせ、欠番scheduleと誤gainの拒否を回帰確認する必要がある。

報告019の能力対照は未達のまま。長さ・幅のJSD飽和、末字/SPACEの操作不足も残る。設計021の新距離・新donorは未実装で、今回の審判・モデル・閾値へ混ぜていない。次の本体案を数値だけで選ぶ前に、この測定・対照設計を整えることを優先する。

同じ開発20葉の再利用であり、10seedや800生成面を独立した真正標本と数えない。区間は利用可能な葉と固定モデルに条件付けた記述値で、改善・同等性・汎化・正式採用の確認は行っていない。固定CAL model setは `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`、refit・PROTO代用なし。

実装・原版・審判・status/request管理ファイルは変更せず、報告と独立補助検証コードのみを返した。raw生成語・真正語・面・正解キー・予測JSONL・snapshot・donor・archiveはGitに含めない。
