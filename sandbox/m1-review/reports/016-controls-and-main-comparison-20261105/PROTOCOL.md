# 対照・第一案の本比較への移行

2026-11-05。ユーザーの「対照・本比較」を、審判能力対照と、その確認後の第一案本比較を進める指示として受領した。第一案の独立PASSは `20bd3c6f69038ae8f8d5cfb1af406f86922f057f`、生成・審判のsourceは `a6873a2f3af64b423411dc9daeb14fa43879dea3` と同一である。

**現在は本比較の計画・実行スクリプトを準備済み、能力対照の実装待ち。** 実装側への具体的な依頼は [IMPLEMENTATION_REQUEST.md](IMPLEMENTATION_REQUEST.md)。既存の役割分担に従い、新しい対照実装は実装側、独立検証・対照評価・本比較実行はこの検証側が担当する。

## 今回こちらで完了したこと

- 新しいdevelopment planを外部16葉から実際にfitし、全5foldを検証した。PF学習末尾は96 / 94 / 96 / 98 / 96件。planとscope ledgerを共有する。
- 本比較の800ケースを固定し、4worker各200ケースへの重複なし割当を確認した。
- 新しい外部orchestratorで12面を生成し、原版との一致、既存smokeとの全意味出力・state・実main RNG・policy記録の一致を監査した。正常PASS。
- 対照の独立確認書がない本比較の起動、full planをsmokeとして起動する操作を、ともに出力作成前に拒否することを確認した。
- 固定corpusから観測可能性だけを読み取り確認した。固定第4面20面中、FULL PFは18葉29末尾、SPACEを観測できるPFは17葉27末尾。対照の予測・採点はまだ行っていない。

これらの12面はorchestratorの機構試運転であり、能力対照や800面の本比較とは数えない。

## 本比較の固定条件

- [plan](full-plan/plan.json) hash: `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17`。
- BASE / PF_GATE / PF_GATE_LENGTH、同じcomplete 20 bifoliaの固定第4面、同じknown3・layout・quality mask。
- seed: `91701,91702,91703,91704,91705,91707,91708,91709,91710,91711`。過去の共通集合を継承し、新しい失敗seedを除外・補充しない。
- 各群200面、比較600面。原版REFERENCE200面を加え実生成800面。BASE対REFERENCE全200ケースの意味出力・全state・実main RNG一致を検査する。
- 主対比: BASE→PF_GATE、PF_GATE→PF_GATE_LENGTH。主指標J24.CAL、主要局所ATOM.PARA_END.CAL。固定CAL `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。再fit・PROTO fallbackなし。
- 全600予測を保存してから正解キーで採点する。bifolium内seed平均→bifolium等重み。同点1/2、NA・coverageを別記する。共通比較可能trialの対応差、率差、50%からの距離差、向きの反転を保存する。
- 記述cluster bootstrap10,000回。8atom、PROTO、J07/J19/J20/J25、生の語長・幅・末字・SPACE、raw段階・選択後・visible、fallbackを診断として併記する。
- 原版PLANT切断・図後BODY、F1LF、m/rare、複合glyph、PF2候補/LEN1、採用stateと初期argmax由来main RNGを維持する。request採番・side RNGを介した後続変化を含む総効果とする。
- 最初の失敗でworkerをケース境界で停止し、部分出力を保存する。入力・sourceの変更、失敗seedの差替え、自動修復で続行しない。

実行条件のJSONは [EXECUTION_CONTRACT.json](EXECUTION_CONTRACT.json)。orchestratorはケースディレクトリとjournalの書き手をworkerごとに分け、全worker終了後だけmanifestを確定する。監査PASS後に匿名化・予測へ進む。

## 対照で確かめること

従来の生NLLのnear/base/far順序をCALの正解順位にしない。CALは真正nullの中央で高く両裾で低い。既存 `judges.v03.controls` はJ08/J11向けで、旧75%基準も残るため、今回のPF能力対照の代わりに自動適用しない。凍結審判を変更せず、別package・別plan・別集計で実装する。

対照の正解は **真正の原面 対 事前規則でPFを改変した面** とする。正解を審判scoreやそのnull順位から作らない。donorは原版BASEの入口snapshotから同容量・支持内で最大64枝を再生し、外部16葉のproxy表とBASE生成anchorだけで選ぶ。target真正語の値や評価対象の審判scoreでdonorを選ばない。

3つの対象channelは長さ/可視幅、個別末字、SPACEの `ATOM.PARA_END/length_width`、`/terminal`、`/space_T_H1`。farを強い改変の主対照、nearを診断とする。nearがCALで上位になることは合否条件にしない。原面と改変面の全channel・全atomの変化を報告し、対象特徴だけの因果分離とは呼ばない。

今回の数値基準は予測前に [CONTROL_CONTRACT.json](CONTROL_CONTRACT.json) で新たに指定する。各far対照の対象channelに対し、独立bifolia10以上、比較可能な対象面80%以上、意図した対象特徴の変化80%以上、葉等重みexpected accuracy 60%以上、cluster bootstrap95%下限が50%超をすべて要求する。3channelすべてのPASSで本比較へ進む。旧75%基準の自動継承ではない。

操作が成立しなければ `MANIPULATION_NOT_REALIZED`、比較可能性や識別能力が不足すれば `INSUFFICIENT_CAPABILITY` とする。結果に応じて有利なdonor・seed・channelだけを採用したり、合格基準を緩めたりしない。raw/descriptor/CALの関係は診断として報告し、descriptorの値を見て有利な対照だけを抽出しない。

実装側はこの契約に沿った機械可読planとsmokeを返し、検証側が実装を確認してから全対照を生成・評価する。実装上成立しない点は予測前に新しい設計版として返す。control packageを独立させれば今回の本比較planを維持できる。生成側sourceを変えた場合は、このplanでそのまま走らせず、新sourceの検証と再封印を先に行う。

## 実行開始条件と未完了事項

本比較の実行スクリプトは、対照の独立確認で生成する `CAPABILITY_REVIEW.json` を要求する。現時点の [pending記録](CAPABILITY_REVIEW.pending.json) は開始条件を満たさない。対照PASS後の再度のユーザー承認を前提にはしない。今回のユーザー指示の範囲内で、検証側が独立確認書を確定して実行する。

既存の[共有sandbox運用](../../README.md)は「クラウド間の自動起動・常駐ポーリングは設定していません」としている。Gitへの依頼の配置だけで実装側チャットは起動しないため、次の依存作業には実装側チャットの再開が必要である。こちらで実装・status・依頼管理ファイルを上書きして役割を引き取らない。

本比較は再利用20葉の事前固定した記述的な開発比較である。seedやdonorを独立な真正標本と数えない。対照PASSも汎用的な識別力・同等性・正式採用を証明しない。個別末字/SPACEの本体study、正式採用、main mergeは今回の実行に含めず、`promotion=null`。

生生成物・正解キー・parent archiveはGitへ含めない。準備rootは `/workspace/voynich-results/pf-controls-main-preparation-20261105/`。[MAIN_COMMANDS.md](MAIN_COMMANDS.md) と [manifest](MANIFEST.json) を参照。
