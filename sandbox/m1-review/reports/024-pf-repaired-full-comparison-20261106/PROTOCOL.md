# 末字commit修正版：記述的本比較の新規実行登録

ユーザーの既存指示「対照・本比較」「本比較」と、修正到着の連絡を受けて再検証・再実行する。修正022の独立確認を完了してから、新sourceの800面を新rootへ生成する。旧本比較421面、旧planのPASS、旧実行登録を新しいhashへ流用しない。

## sourceと比較条件

- 生成source `43a6895`。候補PF_GATE/PF_GATE_LENGTHに、m縮約後の最終可視H1/H2をsemantic surface commit前へ渡す修復を含む。BASE/REFERENCEはliteral原版。終端・語長法則と、この整合性修復を含む版の総効果として比較する。
- 新full plan `5f0e657be62f5541ef16b40737d44f86bca70cdf990985154693a7fbacb6954a`。検証側のfresh fitと実装020の封印planが一致。外部16葉の法則、20葉の固定第4面、known3、layout、観測mask、展開入力は旧版と同じ。
- BASE / PF_GATE / PF_GATE_LENGTH各200面、原版REFERENCE200面、**実生成800面・比較600面**。seedは `91701,91702,91703,91704,91705,91707,91708,91709,91710,91711`。失敗seedの追加除外・補充はしない。
- 主対比BASE→PF_GATE、PF_GATE→PF_GATE_LENGTH。主指標J24.CAL、主要局所ATOM.PARA_END.CAL。固定model set `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`、refit/PROTO代用なし。
- 4worker、各200ケース、既存の同一driverと分割則を使う。最初の失敗で全workerがケース境界で停止し、部分出力を保存する。自動修復・case差替え・部分集合の採点を行わない。

## 機構・採点

全生成後、600 arm-caseのpolicy/trace/支持/packing/末字/PLANT監査と、BASE対REFERENCE全200面の意味出力・全state・実main RNG一致を確認する。さらに過去の独立M1本比較BASE200面との一致を確認する。旧421面は生成物の継ぎ足しに使わない。

全600予測を保存した後に採点する。seed平均→bifolium等重み、同点0.5、NAはcoverageに残して比較可能性を別記する。共通比較可能trialでの率差、50%からの距離差、向きの反転を保存し、葉単位bootstrap10,000回を使う。全審判・atomの数値も保存し、良い項目だけを選ばない。主・主要局所の区間と対応差、および全項目の率を元の採点行から独立再計算する。

原版PLANT切断と図後BODY、F1LF、m/rare、複合glyph、元の2候補/LEN1、anchor routeと実main RNGの契約を維持する。末字修復receiptの全件数（不採用の試行を含む）を群別に報告する。

## 能力確認の位置付け

報告019/commit `197de98` で登録した記述的実行方針を継承する。**能力確認はCAPABILITY_NOT_VERIFIEDのまま**であり、品質改善・同等性・採用を主張しない。新登録JSONは新plan/sourceに明示的に結合し、旧019の登録JSONは変更しない。

長さ・幅のexact joint JSD飽和、末字/SPACE対照の操作不足は、このcommit修正で解決した問題ではない。設計021の新審判・新donor・新校正は未実装であり、今回のモデル・距離・閾値に混ぜない。旧106組の結果を維持する。

同じ開発20葉の再利用であり、10seedや新規800生成面を独立した真正資料の追加とは数えない。bootstrap区間も利用可能な葉と固定モデルに条件付けた記述値である。正式採用・main merge・後続の個別末字/SPACE本体studyは対象外、`promotion=null`。

生成後の各工程は、この登録と末字commit修正の独立報告023に結び付ける。生の真正語・疑似語・面・正解キー・snapshot・parent archiveはGitへ含めず、報告・集計・hash・小さい検証スクリプトだけを共有する。
