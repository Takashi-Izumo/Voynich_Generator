# M1実装設計・境界条件

schema v2では [REVIEW_FIXES.md](REVIEW_FIXES.md) の4点を反映しています。planに展開済み入力treeを固定し、監査receiptを生成物へ結合します。最終main RNGはstate/hashを専用記録・比較します。END_ONLYが末尾診断に利用可能でもatomはFULL行のword_eventsしか読まないため、構造ラベルと観測集合を区別します。v1の検証済みという記載は当時の機構smokeであり、現在の計画・監査封印の保証ではありません。

## 位置付け

入力仕様書（2026-11-04・v1.0）を基に、ユーザーの「実装を開始」指示を優先して、M1の独立overlayと小規模検証を実装する。M2/M3・大規模審判・正式昇格は別段階。基準commitは `c610c2a81e733748e0fb246de89143d6ecda764e`、active runnerは `run_v22_3_stage3d.py`。名前が類似するv21の別modeは基準に代用しない。

## ソース確認で確定した事実

- active v22.3は `V223F1LFLengthTerminalSampler` → router-off → W2B2 → paragraph-H1 → short-H2 → PRETERM → v21 safe-left/bT-offの系列で、生成segment/PF分岐は親 `bti2_patch_engine.py` が担当する。
- `is_pf`: `raw_para_final and boundary_type == LINE_END and para_line_raw >= 2`。1行段落、植物前segmentはPF介入外。審判のPARA_ENDと同じ母集団ではない。
- PFはstable表記から複合glyphをtokenizeし、スコアには幅・幅帯・幅/容量・末字・末字族を使う。文字列長や語長そのものを直接scoreにしていない。
- LEN1はstable長5以下の元argmaxに対し8枝を生成する。長さ+1、幅+1以内、NMY/LR/OTHER族の一致、元score−1.00以上が適格条件。末字そのものは固定しない。
- 最初の適格救済は元argmaxよりscoreが低くても採用され得る。その後は**救済候補間**で最大scoreを選ぶ。同scoreでは早い候補が残る。
- 救済採用後もmain RNGは元argmax枝から継続する。救済枝のRNGを採る変更は別armである。
- 最終segment全体の採用なので、末尾以外や後続segmentのroute/rareも変わり得る。
- 原版の `next_proposal_id` は破棄枝を含めて進み、既存補正のside RNGにも入る。単なるログ番号としてrollbackできない。
- 旧 `GenerationState.digest()` は履歴・attempts等の全mutable stateを含まない。cloneの正しさをそれだけで証明できない。
- 原版の `rebind` はstate参照を付け直すが、`last_request`は最後に探索した枝のものが残り得る。次の`begin_segment`/`prepare_word`でリセットされる参照であり、原版生成の意味出力へ影響しないことをBASEとの比較で確認する。

## 処理フローと変更点

```text
固定入力/planを検証
  → 原版configure・fold context・core・decomposed tablesをそのまま構築
  → PF以外: 原版complete_segment
  → PF: 同じ入口state/RNGから2枝を原版complete_segmentで生成
       → score/元argmaxを記録
       → BASEだけ原版LEN1を実行
       → PF_ANCHORだけ候補0を選択
       → 採用segment/state/control参照をcommit
       → armで固定したmain RNGから継続
  → 原版save_result＋M1追加ログ
  → 原版REFERENCEとBASEの意味出力を比較
  → 既存v0.3 adapterで匿名化
  → 固定CALモデルで全予測を封印 → 採点 → 対応比較
```

追加するのは `experiments/m1_pf/` 以下だけ。`runtime.py` が元runnerの構築関数を呼び、生成呼出し中だけ `rb.patch_generate` を独立overlayへ切り替える。sampler class、PatchMapState、build_bt_leafex、engine参照は`finally`で復元する。元engine関数・archive・凍結コードを上書きしない。

`overlay.py`は基準engineのPF構成を保持し、選択/救済条件と監査を追加する。`common.py`はhashと保護、`plan.py`は固定計画と実行、`audit.py`は独立再検査、`evaluation.py`は変更しない審判APIへの接続を担当する。

## D01–D05の決定

| ID | 決定と検証 |
|---|---|
| D01 RNG | BASE/PF_NO_RESCUEは元argmax、PF_ANCHORは候補0の終了状態。救済枝stateとRNG源は意図的に別で、候補別入口/出口hashと継続元を記録する。 |
| D02 隔離 | 各候補の前に入口sampler制御を復元し、stateをclone。生成後に親の全mutable snapshotとmain RNGが不変か検査。既存共有採番規則は例外として明示し記録する。 |
| D03 再結合 | 勝者のGenerationState全体を採用。sampler.state/base.stateを勝者motionへrebindし、勝者last_request/word_first_requestも復元。rare、route、surface commit、段落H1pendingもsnapshotで照合する。 |
| D04 BASE再現 | 原版engineを呼ぶREFERENCEと、tokens・packing・commit・request・確率行・行頭・候補bank・経路trace・意味あるMECHANICAL・全最終stateを比較。elapsed_seconds/gzipヘッダだけを比較から除外する。 |
| D05 配置 | 独立overlayをcontext内で接続しfinally復元。元展開runtimeを直接修正しない。原版Git tree、読み込んだruntime.py群と信頼済みZIP、入力hashを記録・照合する。 |

### 採番と隔離の限界を区別する

`requests/head_rows`、累積監査counter、row_catalogは共有する。`next_proposal_id`も原版どおり共有するが、これは既存side RNG入力である。各候補の `proposal_id_start/end` で消費を追跡する。追加救済を停止すると、救済の採否以外に後続の採番/side RNGにも影響する。これを検証結果の説明から落とさない。

全side RNGまで破棄枝から完全隔離する案は、BASEの原版完全再現と両立しないため、このM1には混在させない。必要なら、採番方式自体を変更する新しい基準版・追加対比として設計する。M1の2つの対比は実装上の総効果であり、完全な2×2要因実験や直接効果の推定ではない。

## 入力と守る境界

生成呼出しは原版の `C, fc, core, cfg, prev, patch, tables, run` を維持し、known3と外部16のfold設定・共有layoutを変えない。許可された構造入力はpage/line/paragraph/segment ID、原位置、段落最終行flag、PLANT/LINE_END、容量、layout/quality mask。真正targetの語列・A/B正解・採点・CALの結果を新たな生成引数にしない。

品質対応表を作る段階では元資料から同じ構造profileを再構築する。真正文書を含むその返り値を生成器へ渡さず、planへはhashと構造対応だけを保存する。審判adapterへは本来の手順で真正候補も渡すが、predictor入力は匿名候補のみとし、正解・export manifest・内部生成ログを渡さない。

PLANTでsegmentを切り、次segmentのprev_terminalをresetする。再開はBODYで、HEAD/W2/SPACEを捏造しない。PLANTをLINE_ENDに置き換えず、段落/routeの全resetも追加しない。監査はsurface commitの位置・語列・ID対応とsegment先頭のprev_terminal=Noneも検査する。厳密F1LFのroute用child/最終可視childの二段commitには触れない。

`stable_surface`と`surface`を別に保存する。長さは元tokenizerで数え、審判visible profileではrare文字を除いてもmを残す。stable/visibleの末字・族・m数・長さ閾値跨ぎを候補ログへ保存する。

## 実験・評価計画

機構smokeと採否用開発比較を分離する。smokeは事前にA:2/A:3/G:1、seed 91701を固定し、実際の救済採用・候補1argmax・非介入境界を確認する。後続の開発比較は同じplanの全群・全葉・全seedを生成し、不都合なseedを落とさない。旧91706除外は新候補に適用できる規則ではない。失敗したら計画全体を不完了として止め、原因と部分出力を保存する。

主判定はJ24.CAL、主要局所はATOM.PARA_END.CAL。PROTO・生の分布・全周辺atom・J07/J19/J20/J25も監視する。v0.3は固定のモデル、feature、mask、校正、集約を全群へ適用する。固定モデルset・extractor・protocol hashが仕様と違えば採点を始めない。

既存score/compare APIでtrial・mask・known3・真正面・model・primaryの対応を検査し、DECIDED/TIEが両群で共通のtrialに限ってseed内平均→bifolium等重みを求める。追加で `|右のmacro率−.5|−|左のmacro率−.5|`、bifolium別距離差平均、符号付き率差、方向反転、NA/TIE遷移、対応cluster bootstrap区間を併記する。低い率だけを改善や過適合と断定しない。

現時点では許容幅・採用規則・検定族の数値をユーザー指定として作らない。`promotion=null`、推論上の選抜なしの記述比較として実装する。今後、有意差を採否へ使う場合は、2対比×2主要指標を候補とした検定族とHolm等の処理、周辺悪化の許容幅を**結果を見る前に**合意・固定した新planを作る。

### 次段階の能力確認（未実装・未実施）

M1局所対照は、PARA_ENDで語長/幅、末字族/末字、接続を1項ずつ参照分布へ寄せる/離す案とする。観測/支持内の候補だけを使い、変更不能数を母数と一緒に報告する。現行J08/J11の能力を段落末に外挿しない。既存の10 bifolia・coverage80%・期待率75%・記述区間下限50%超という能力基準の適用は、対照定義と対象集合を確定後に根拠と共に判断する。

未使用bifoliaはこの環境では確認できていない。新seedや同葉別面を独立した一般化確認と呼ばない。既存20葉の結果は開発結果として扱い、独立資料がなければ一般化主張を留保する。

## M2/M3への接続

- M2は独立した後続plan/armにし、`Runtime.case_inputs` のMapConfigをcopyして `exact_scale` だけ、または元samplerを継承したclassの `BODY_R4_LAMBDA` だけを変更する接続を用意できる。両者やM1を同時に変更しない。語長・役割・末尾種別を揃えた共有語彙残差を先に確認する。
- M3の診断は既存tokensの可視表記とscope ledgerを使い、FIRST/MIDDLE/FINAL×PLANT/LINE_ENDで分ける。末字法則を作る場合も外側target葉を除いた資料に縮約し、切断仕様を変えない。既に末尾はbT OFFなので「植物前だけOFF」を新介入と呼ばない。
- F1LF原Stage1表とのsource-law照合は依然として別の未解決事項。今回のM1成功を出典解決やv22.4昇格へ読み替えない。

## 受け入れ条件と停止位置

1. 原版/審判/overlay/データ/plan hashが一致しなければ生成前に停止。
2. 不完全clone・非採用枝の親state/main RNG汚染・未知のsampler制御field・rebind不一致は候補生成の直後に停止。
3. packing・support・glyph・末字整合・植物再開・commit位置対応の不一致は原版監査またはM1監査で停止。
4. BASEと原版REFERENCEの意味出力・state・RNG不一致は匿名化前に停止。
5. 順序反転・並行別processで結果が違えば再現性不合格。成果物は消さず新plan/runへ原因を記録。
6. 固定CALモデル不在・hash不一致、入力/予測/正解の改変、対応trial不一致は採点前/対応比較前に停止。
7. 機構PASSでも採否・審判能力・一般化・正式昇格は別条件であり宣言しない。
