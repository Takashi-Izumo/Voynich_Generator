# M1本比較・事前固定計画

日付: 2026-11-05（日本時間）。ユーザーが検証側を実行担当と指定した上で「では開始してください」と指示したため、本比較を開始する。以前の保留は今回の**実行**について解除されたものと扱う。main merge・採用・昇格の承認とは扱わない。

## 固定する比較

- 実装snapshot: sandbox commit `602c4501ba34792135d585691c005536a341b936`時点のschema v2。実装ファイルは独立再検証時の25ファイルから変更なし。
- 原版・審判: `c610c2a81e733748e0fb246de89143d6ecda764e`。
- BASE / PF_NO_RESCUE / PF_ANCHORの3群。SHADOW、M2、M3は追加しない。
- 同じcomplete 20 bifoliaの固定第4面、同じknown3、layout・quality mask、同じ外部訓練資料。
- 各bifoliumのseedは`91701,91702,91703,91704,91705,91707,91708,91709,91710,91711`。これは以前から宣言された共通履歴集合で、91706の旧除外と91711への旧置換を継承する。新しい失敗seedを除外・補充しない。
- 各群200面、比較対象600面。原版REFERENCEも200面生成し、BASEとの全ケース一致を検査。実生成は計800面。
- 原版のPLANT切断、BODY再開、m、複合glyph、state/RNG/rare、F1LF commit契約を維持する。
- 4独立processで既存Runtime.generateを呼ぶ外部orchestratorを使用。実装・審判は修正しない。1process内は逐次、`NUMBA_NUM_THREADS=2`。source・入力tree・plan・orchestratorをhashで固定する。

## 評価と推定対象

- primary: `J24.CAL`。主要局所: `ATOM.PARA_END.CAL`。
- 主要対比: BASE→PF_NO_RESCUE、PF_NO_RESCUE→PF_ANCHOR。
- 固定CAL model-set: `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。再学習・調整・PROTO fallbackをしない。
- 全群の予測保存後に正解を使って採点する。
- bifolium内でseed平均、その後bifolium等重み。同点1/2、NA除外。共通の比較可能trialによる対応比較、50%からの距離の差、符号付き率差、方向反転、NA/TIE・coverageを併記する。
- 凍結実装の記述cluster bootstrapは10,000反復。利用可能bifoliaと固定モデルを条件とする区間として報告する。
- 監視項目: 全8atom、J07、J19/J20/J25、PROTO。その他の専門項目・channelは探索的な表として残す。結果を見て主要指標や対比を変更しない。
- 救済探索停止はrequest採番を介して後続side RNGにも作用する。この波及を含む総効果を比較し、直接効果の分離とは主張しない。

## 今回の結論の範囲

今回の本比較は**事前固定した記述的な開発比較**とする。現20 bifoliaは再利用済みであり、独立確認とは呼ばない。新seedを独立な真正標本とは数えない。

段落末等の両方向能力対照、採否許容幅・多重比較による推論上の選抜は今回に混在させない。能力確認済みと仮定せず、率が50%へ近づいても同等性・有意性・正式採用・一般化を宣言しない。採否を行う段階は別planで先に条件を確定する。今回の`promotion`はnull。

## 失敗・監査・保存

- 最初の失敗で全体を不完了とし、進行中のworkerもケース境界で停止。部分出力と失敗原因を保存。seed除外・自動修復・候補実装の変更で続行しない。
- 出力先は新規ディレクトリ。既存のsmall-smokeや旧版の監査PASSを再利用しない。
- 全case checksum、packing、支持、可視末字、PLANT、採用segment/state/rare、最終main RNGを監査する。
- BASE対REFERENCE200ケースの一致に加え、既存の公式v22.3出力とのBASE照合を行う。実行順反転は先の独立24面で確認済みであり、今回800面を再度逆順で増やすことはしない。
- 正常な監査が完了してから匿名化・採点へ進む。report/manifest bindingを確認し、元資料・モデル・予測・採点のhashを保存する。
- 生生成物、匿名候補、正解、予測、採点はローカルに分離保存。共有sandboxへは計画・集計・再現手順・小さいlogだけを追加する。実装・status・mainは変更しない。

実行root: `/workspace/voynich-results/m1-full-comparison-20261105/`。具体的なplan hash・source/input/model hash・orchestrator hashは同梱の`STUDY_PROTOCOL.json`に固定する。
