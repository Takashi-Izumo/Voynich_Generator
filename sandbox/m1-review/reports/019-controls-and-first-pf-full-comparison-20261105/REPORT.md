# 第一案の本比較と対照試験：独立実行結果

**本比較は421/800面で生成器の不変条件違反により停止。対照106組は評価まで完了したが、能力確認は3項目とも未達。採否は判定せず、BASEを維持する。**

本比較の識別率は算出していない。以下の識別率は、真正面と操作面を区別する**対照試験**の数値であり、第一案を生成した疑似面の本比較成績ではない。

## 本比較：採点前の生成段階で停止

固定した20葉×10seed×4armの800面を実行し、BASE 200、PF_GATE 196、PF_GATE_LENGTH 25の計421面を生成した。PF_GATE_LENGTH / **A:3 / seed91711** で原版の末字不変条件に違反し、全workerがケース境界で停止した。REFERENCEは0面。失敗1ケース、停止後未生成378ケースであり、seedの除外・差替えはない。

同じケースを新Runtimeで単独再現し、報告用の [reproduce_failure.py](reproduce_failure.py) でも原版の同じAssertionErrorを再現した。**m削除でstable長3→visible長2となったW2語に、親のsurface commit後のH2補正が入る。H2が可視末字になるため、可視末字a（ID12）と記録されたprev_terminal=o（ID10）が不一致になる。** terminal_mismatches=1、plant_false_heads=0。失敗箇所はf6v.10のW2で、PF最終segmentでもF1LFでもない。

この状態は次の語のSPACE要求に使われる。最終可視語を次の語へ進む前に実状態へ反映する修正が必要であり、生成後に監査値やログを合わせるだけでは直らない。今回、植物前でいったん切る現行仕様を変更する根拠は見つかっていない。

詳細と回帰確認の依頼は先行push `740ec25` の [FAILURE_REPORT.md](FAILURE_REPORT.md)。全800ケースの実行状態は [PARTIAL_EXECUTION.csv](PARTIAL_EXECUTION.csv)、位置・長さ・末字IDの証拠は [GENERATOR_FAILURE.json](GENERATOR_FAILURE.json)。raw生成語は共有しない。

BASE 200面は、前回独立本比較のBASEと全意味出力・最終状態・実main RNGが一致した。一方、421面全体の監査PASS、最終export、部分集合の採点は作成していない。今回の421面を修正版の残りへ継ぎ足さない。

## 対照：機構監査と能力確認を分ける

対照source `2bd72160cb61d994e873c48d09a7dfca72b3375b` を独立checkoutで実行した。

- source manifest 36ファイル、fresh plan/proxy fit、unit 161件を確認。
- 3葉smokeの448枝再生監査、および改変・汚染・例外注入等20件の拒否検査がPASS。例外後のbindings/class controls復元と通常BASEの一致も確認。
- 全20葉、seed92101、35イベント×64枝＝**2,240枝**を生成し、固定sourceから全枝を作り直すfresh replay監査がPASS。通常BASEとの全意味出力・状態・実main RNG一致を確認。支持・物理詰め込み・末字・植物境界の違反は0。
- 全106組をexportし、元記録から入力・割当・キー・診断を再構成して照合。**106予測すべてを保存した後に採点**した。審判への入力にproxy・snapshot・キー・診断を含めない。export照合を行う検証器と、入力面だけを使う予測器を区別する。
- `verify-export` CLIは引数名 `exported` / `output` の不一致でTypeError。同じ `pipeline.verify_export(plan, generated, output)` を位置引数でAPIから呼び、同じ検査をPASSして続行した。sourceや検査項目は変更していない。[CLIの修正依頼](CONTROL_CLI_DEFECT.json)を残す。

したがって機構の結論は **API経由の監査PASS・CLI接続に不具合あり**。これを能力確認PASSと読み替えない。

## 固定CALによるfar対照の結果

| 対象チャネル | 操作実現面 | 操作実現率 | 識別率（同点0.5） | 葉bootstrap 95%区間 | 同点 | 判定 |
|---|---:|---:|---:|---:|---:|---|
| PARA_END / length_width | 17/18 | 94.4% | 47.2% | 38.9–55.6% | 15/18 | INSUFFICIENT_CAPABILITY |
| PARA_END / terminal | 6/18 | 33.3% | 47.2% | 36.1–58.3% | 13/18 | MANIPULATION_NOT_REALIZED |
| PARA_END / space_T_H1 | 8/17 | 47.1% | 58.8% | 44.1–73.5% | 10/17 | MANIPULATION_NOT_REALIZED |

全項目でNA=0、比較可能率100%。合格条件は事前固定の各項目：比較可能葉10以上、比較可能率80%以上、操作実現率80%以上、識別率60%以上、95%区間下限が50%より大きいこと。3項目すべてのPASSが必要であり、今回は **CAPABILITY_NOT_VERIFIED**。対照で操作が十分に成立したかを確認する場面なので、生成器の理想とされる「50%」を合格基準にはしない。

操作実現は、凍結した候補選択後に真正面と操作面の対象特徴countsが異なるかで判定した。外部proxy NLLがBASEより動いたことだけで実現と数えない。NO_MATCHや特徴不変の面も分母に残した。far選択は長さ・幅28/29か所、末字9/29、SPACE9/27。nearは補助診断で、ゲートに使っていない。

全6方向の数値・同点・coverage・区間は [CONTROL_RESULTS.csv](CONTROL_RESULTS.csv)。farの合否を独立再計算し、さらに全6方向の識別率と10,000回bootstrap区間を元の予測・キーから再計算して一致した：[CONTROL_INDEPENDENT_RECOMPUTATION.json](CONTROL_INDEPENDENT_RECOMPUTATION.json)。他の審判・atomの対照診断は [CONTROL_ALL_JUDGES.csv](CONTROL_ALL_JUDGES.csv) であり、これも本比較成績ではない。

## 長さ・幅の同点原因も特定

長さ・幅のfar対照18組中15組で、**両候補のraw JSDがともに1.0**だった。この15組では、既知3面のexactな(length, width)カテゴリと、両候補のカテゴリがそれぞれ非交差になる。うち**14組では対象特徴countsが実際に変化**していたが、距離が上限で飽和して差を失っている。

元の入力から参照分布・候補特徴・支持の交差・JSDを再計算し、保存済みchannel factsとの一致を確認した：[CONTROL_LENGTH_WIDTH_SATURATION.json](CONTROL_LENGTH_WIDTH_SATURATION.json)。この15組の同点はCAL変換前の距離段階で生じているため、CAL値の丸めだけでは説明できない。

このチャネルでは、疎なexact joint分布と三面参照JSDの組合せに識別上の限界がある。一方、末字とSPACEは操作実現率が低いため、今回だけで審判の識別能力を結論づけない。外部proxyでfarにしたことも、固定CALの典型度が下がることを保証しない。対照設計と測定方法の対応を見直す必要がある。審判団全体の無効を示したものではない。

## 次の作業と固定条件

1. **生成器のW2＋m縮約時のcommit順序を修正**し、最終可視末字・意味状態・次の要求が一致することを独立確認する。既存anchorのroute commitと可視末字状態を区別し、m/PLANT/F1LF、恒等設定、R1/R2監査を保持する。
2. **長さ・幅の距離の飽和を扱う評価設計**を作る。変更する場合は特徴・距離・genuine-onlyの学習/校正と検証条件を新しく事前登録する。今回の予測・区間・閾値は変更しない。
3. **末字・SPACEの対照操作の実現性**を改善する新設計を登録する。今回のNO_MATCHを削る、良いseed/枝だけ選ぶ、閾値を下げる方法でPASSにしない。
4. CLI→API引数契約を修正し、実際のCLI呼出しを確認する。

本比較の計算方針は、全対照結果・本比較出力が出る前の `197de98` で、能力確認を推論・採否の条件として保持した記述的実行へ変更登録した：[EXECUTION_AMENDMENT.md](EXECUTION_AMENDMENT.md)。能力確認PASSは捏造していない。この変更で生成器の不変条件違反を許容せず、今回も生成段階で停止した。

本比較plan `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17`、対照plan `33b7d30a29c3494e4d95fc25fa479df69fa24e10150050f2454d13fb824e3e76`、CAL model set `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。refit、PROTO代用、seed差替え、枝追加、閾値変更はしていない。対照評価器の `full_comparison_started:false` は対照評価器自身による起動がないという記録で、本比較の別登録実行状況は [STUDY_RESULT.json](STUDY_RESULT.json) と [MAIN_FAILURE_SUMMARY.json](MAIN_FAILURE_SUMMARY.json) を参照する。

本比較を再開する際は、修正版sourceを独立確認してplanを再封印し、同じ20葉・10seed・4armの全800面を新rootで再生成する。使用した20葉は開発で再利用しており、新seedも独立した真正面サンプルの追加ではない。採否・同等性・汎化の確認はまだ行えていない。

実装・審判・status・依頼管理ファイルは変更せず、検証報告だけを返した。rawの生成語・真正語・候補面・キー・snapshot・枝データ・archiveはGitに含めない。
