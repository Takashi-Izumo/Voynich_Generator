# 第二案: PF個別末字係数の比較設計

作成: **2026-11-07 日本時間**。設計ID: `PF_EXACT_TERMINAL_V1_20261107`。

**BASEから独立に、PF selectorの個別末字成分だけを半減・無効化する。第一案とは組み合わせない。** 本書は実装担当へ渡す仕様であり、新候補の実装・生成・審判予測・採点はまだ行っていない。BASEを維持し、`promotion=null` とする。

[機械可読契約](DESIGN_CONTRACT.json)、[実装受け渡し](IMPLEMENTATION_HANDOFF.md)、[読取専用ソース監査](SOURCE_AUDIT.json)を併読する。既存[提案005](../005-post-m1-proposals-20261105/PROPOSAL.md)の第二案、[設計007 §6](../../designs/007-pf-generation-v1/DESIGN.md)を現在のソースと検証条件に具体化したもの。古い設計・報告は書き換えない。

## 1. 仮説と比較群

凍結PF selectorの5 foldすべてで `coefficient['E=n'] > coefficient['E=y']` だった。nへの相対的な加点が可視PFのn過多・y不足へ寄与している可能性を調べる。ただしselectorの入力はpre-m stable末字であり、可視末字とは一致しない場合がある。係数だけで原因を確定せず、n→yの置換や真正割合への強制一致を行わない。

| 群 | lambda_E | 内容 |
|---|---:|---|
| BASE | 1.0 | 原版のPF score・生成をそのまま使う |
| PF_E_HALF | 0.5 | `E=個別glyph` の成分だけ半減 |
| PF_E_ZERO | 0.0 | 同成分だけ除去 |
| REFERENCE | — | 独立に起動する原版。BASE一致確認用で、審判比較群へ加えない |

主対比は **BASE→PF_E_HALF、BASE→PF_E_ZERO**。HALF→ZEROは補助診断。lambda探索、selector再学習、第一案のgate/語長law、SPACE score、救済停止、候補0固定は加えない。

## 2. ソースと母集団を固定する

確認時HEADは `6ed1f8318c287c7c641f4883e58b39b84a2183e1`、製品実装sourceは `43a6895`。ファイル別hashはSOURCE_AUDITに記録した。実装完了後には新しいsource commitと生成planを別途封印する。本書のmanifestは生成許可sealではない。

- 元PF selectorは `LEGACY_SCOPE` の **FROZEN_18** core cacheから取得する。各foldの外部complete16葉に不完全補助2葉（A:1、B:4）を加えた18葉で訓練され、外側test4葉を除いている。実物のselector metadataとも一致した。
- 第二案ではこのselectorを再利用する。`COMPLETE16_REFIT` や別の `load_pair(bif)` shortcutへ切り替えない。cache不在は停止し、再fitへ自動移行しない。
- 後述の新しい能力対照のproxy分布は **外部complete16葉のみ**。生成器の既存18葉学習と混同しない。targetのknown3を新しいproxy学習やlambda選択へ使わない。
- 固定審判のprior8/null8/test4、feature抽出、CAL、集約は変更しない。既存known3補正は原版のまま使う。

読取専用監査で5 coreを読込み、空surfaceおよび22glyph、3組のwidth/capacityについて計345回、元scoreと特徴の演算を照合した。新fit・生成・予測・採点は各0。[再現コード](source_audit.py)は新候補の実装ではない。

## 3. scoreの厳密な定義

元の `sel42_selectors.pf_features(surface,width,capacity)` を使う。surfaceは候補末語の **raw stable_surface（pre-m）**、widthは既存呼出しの `phys_width`、capacityは既存 `segment_capacity`。tokenize/I2Gも原版へ委譲し、文字列の最終1文字を使わない。複合glyphは1glyph。

```text
features = W=width, WB=min(width//2,8),
           WR=min(round(10*width/max(capacity,1)),10),
           E=last_stable_glyph, EF=NMY/LR/OTHER
S0 = original_selector.score(surface,width,capacity)
E  = original_coefficients.get('E=' + last_stable_glyph, 0.0)

if lambda_E == 1.0 or E == 0.0:
    return S0
return S0 + (lambda_E - 1.0) * E
```

NMYはn/m/y、LRはl/r、その他はOTHER。空surfaceの原特徴は `E=EMPTY`。これは算術fixtureに用いるが、実生成の空segmentを合法化しない。

`E=` という完全prefixだけを対象にする。`startswith('E')` ではEFまで巻き込むため不適合。intercept、W/WB/WR、EFの値・特徴数・加算方法を保つ。selectorの共有coefficient辞書を変更せず、前後のpayload hash一致を確認する。

lambda=1では元scoreを直接返す。非恒等の式も上記の演算順を固定し、`rest + lambda*E` 等に組み替えない。選択・tie・許容差には原版の浮動小数点比較をそのまま使い、epsilonで同点を増やさない。監査上の数値照合許容差と、実際の選択規則は分ける。有限値以外、未登録lambda、PF以外のselector接続は停止する。

score全体の縮小とは異なる。特にLEN1のscore許容差は絶対値1.0なので、全体を縮小すると初期argmax以外の条件まで変わる。本案ではその処理をしない。

## 4. PFの範囲と原版LEN1

適用scopeは原版 `is_pf(sr)` と同一:

```text
raw_para_final is true
boundary_type == LINE_END
para_line_raw >= 2
```

全構造PFへ適用し、FULL/END_ONLY/NONEで生成を切り替えない。END_ONLYを審判atomの新しい観測例へ昇格させない。植物前の切断、図後BODY、厳密F1LF、PHW処理は原版を維持する。今回のtarget scheduleには構造PFが35か所ある一方、既存審判で見えるFULL PFは18葉・29末尾。両者の母数を混ぜない。

原版engineの制御フローを直接使い、次の規則を再実装で変えない。

1. 初期2候補（ID 0,1）を原版のstate clone・keyed RNGで完成させ、すべて `S_lambda` で採点する。初期argmaxは `(score,-candidate_id)` の最大。tieは0。
2. **そのarmの初期argmax** のpre-m stable長が5以下なら、追加8枝（ID 2..9）をすべて生成する。6以上なら追加枝0。最初の適格枝で探索を打ち切らない。
3. 各救済枝は初期argmaxに対して、stable長がちょうど+1、物理幅が `initial_width+1` 以下、**末字族一致**、`S_lambda >= initial_S_lambda - 1.0` を満たす必要がある。幅は「必ず+1」ではない。個別末字一致でもない。
4. **最初の適格救済は、初期argmaxよりscoreが低くても採用する。** その後は採用中の救済よりscoreが厳密に高い枝だけで更新する。救済同士のtieは先の枝を保つ。初期候補と適格救済全体のglobal argmaxへ変えない。
5. 採用枝の全state/rare/routeをcommitする。一方、main RNGの継続元は **そのarmの初期2候補argmax枝**。救済枝でも、歴史的BASE群のargmax枝でもない。

元sourceのPF `_edge_key(...,phw=False)` は末字族を返す。周辺の古いexact-terminalコメントではなく実装を基準にする。PHW側の許容差0.5等は変更しない。

rank変更によって初期winner長・LEN1発動・探索bank・共有request採番・以後の生成が変わり得る。これは個別末字scoreを変えた**アルゴリズム全体の総効果**であり、候補を固定した末字だけの因果効果ではない。

同一の観測bank上でS0順位・S0救済条件を補助計算してもよい。ただしS0なら未生成の救済枝を必要とする場合は `COUNTERFACTUAL_BANK_NOT_OBSERVED`。その診断を「BASE再現」と呼ばず、ログを埋めるために余分な枝を生成しない。SHADOW群は本設計に加えない。

## 5. 独立packageと接続

新packageは `experiments/pf_terminal_score/` を推奨する。原版、M1、第一案、審判を編集せず、新runner/plan/auditを用意する。

| module | 責務 |
|---|---|
| `score.py` | 純粋なEWeightSelector。元PF selectorを保持し、scoreと分解値を返す |
| `runtime.py` | SourceRuntimeを基にcase-local接続、恒等経路、復元、lock |
| `observer.py` | 完成候補とscore・state/RNGを外部traceへ記録。制御しない |
| `plan.py` | 新study ID、arms、lambda、source/input/coeff/repair hash、seeds、scope、maskを封印 |
| `audit.py` | canonical scheduleと元係数から、候補・score・選択・状態遷移を独立再計算 |
| `controls.py` | 独立対照plan。製品の候補bankや生成stateへ接続しない |
| `diagnostics.py` / `evaluation.py` | 分布診断と固定審判APIへの接続 |

case-localな `rb.patch_generate` wrapperで、元 `engine.generate_bif` のsignatureへbindしてPF selector引数だけをadapterへ替える。PHW selector、models、gate、EntryFastSampler、原版engine制御フローはそのまま渡す。第一案Runtime/Overlayを継承してgate/語長処理を無効化する方法は採らない。

既存M1 Runtimeの `_generate` はarm名からM1 Overlayを作るため、そのまま新armを渡して呼ばない。入力/core読込み等は再利用できるが、生成接続と返却state/RNGの捕捉は新studyで明示する。

観測は元 `complete_segment` のcase-local wrapperとscore adapterの組で行う。候補生成前にtyped contextを設定し、完了後の候補末語に対するPF scoreを一意に結び付ける。loggerが制御用乱数を引いたり、sampler/request/stateを変更したりしてはならない。元request辞書への識別子追加ではなく、別の `pfe_*` traceに保存する。

元bindingは例外・途中停止を含め `finally` で復元し、元Runtimeと同じ生成lock内で接続する。並列生成は別process。identity/BASE/REFERENCEの出力・request・実state・main RNGを原版と厳密比較する。

### 5.1 既存の末字precommit修復

source `43a6895` の純粋helper `experiments/pf_generation/surface_commit.py` は、変更後の経路でも必要になり得る。**helperだけをhash固定で再利用**し、第一案の生成lawや接続を読み込まない。

- 非恒等PF_E_HALF/PF_E_ZEROに限り、新studyのrepair policyで接続する。元の `SURFACE_COMMIT_POLICY` を書き換えてarm名を使い回さない。
- 既存helperが対象にする、物理末尾でrare suffixがない、すでに選択済みのW2/H2 stable3→visible2、BODY/H1 stable2→visible1だけを扱う。選ばれたsurfaceを親の意味commit前に渡す。route anchor/stable_seq・pending H1統計・元のF1LF/rare処理・乱数は保存する。
- BASE/REFERENCEおよびlambda=1のidentity fixtureは元経路へ直接委譲し、repairを足さない。潜在する原版失敗が出たら停止し、seed差替えやbaseline修正で続行しない。
- `pfgen_terminal_precommit` は共有helperの妥当性receiptとして由来を明示する。第一案の `request['pfgen']` gate/語長traceを持ち込まない。全attemptのrepair件数と採用枝への反映を記録する。

helperの既存 `audit_requests(...,arm)` は `arm != 'BASE'` を使う。これを新studyへ無条件に流用せず、新しいpolicyのlambda/arm適用条件でreceipt監査を行う。REFERENCEと恒等E群にrepairを要求しない。

このrepairは第二案の追加施策として性能を競うものではなく、変わった選択経路の有効なstate commitを維持する処理。ただし発生時は総効果へ含まれるため隠さず報告する。

## 6. traceと独立監査

planには凍結入力・原版runtime tree・core cache・PF/PHW selector payload・新source・設定・repair policy・seeds・評価maskを結合する。新sourceを実装した事実と、生成後に検証器だけを修正した事実は別manifestに記録し、古い生成source hashを新validator hashで上書きしない。

各PF eventは `(study,arm,bif,run,page,locus,segment_id,event_id)`、各候補はさらにcandidate_idとtyped request intervalで識別する。

- 全構造PFのcanonical inventory、event入口state/RNG、初期2候補・必要時の8救済枝。各枝の入力state hash、原版branch RNG namespaceと入口/出口hash、完成segment hash、request ID範囲、rare/route状態。
- score入力の元surface、tokenized pre-m末字、E係数・E寄与、intercept/W/WB/WR/EF寄与、S0/S_lambda、初期argmax、救済各条件、選択順と最終採用ID。可視末字/長さ/幅は別stageに記録する。
- 最終採用stateとmain RNG継続元を別々に照合し、次segment入口・最終返却state/RNGまでchainを検証する。枝入口のGenStateは共通snapshotからのclone。全attempt共有のrequest counter/cacheは原版どおり進め、loggerが巻き戻さない。
- `begin_segment` がsamplerを枝stateへbindする前の外側入口を、既にbind済みと誤認しない。完了後と採用境界で実参照結合を照合する。
- 対象event総数はtraceの自己申告ではなくscheduleから導く。候補数は最初の2候補とそのarmのscoreで独立に決める。欠落・重複・並替え・空trace・他候補の実在labelへの付け替えを拒否する。

### 6.1 split監査の修正を先行する

製品監査に残る `segment_id>0` 判定を流用しない。trusted canonical scheduleから原版どおり次を導く。

```text
split_end = nsegments > 1
            and segment_id == nsegments - 1
            and boundary_type == LINE_END
```

segment番号を詰め直して意味を変えない。D:4/f29v.9の保持ID `[0,2]`、nsegments=2では、ID2のsplit_endは **false**。誤ったtrueだけでなく、それに合わせた余分な0.8 gainも拒否する。真の原版split箇所はgainを一度だけ適用する。

この修正・負例再現は別の実装成果として先に返す。新studyが通常の公式監査でPASSするまで本比較へ進まない。[報告024の補助経路](../024-pf-repaired-full-comparison-20261106/AUXILIARY_PROTOCOL.md)は、当時の記述比較だけの登録であり、新studyの標準経路へ自動継承しない。

## 7. 第二案に必要な能力対照

旧末字対照は操作成立6/18葉で、能力確認に使える状態ではない。設計021の新距離・conditional replayも未実装。本案では個別Eを動かしEFを残すため、**同じ末字族内で個別glyphが変わった場合の検出能力**を対象channelで確認する。族を変えただけの対照では代用しない。

新対照IDは `PF_E_TERMINAL_CONTROL_V1_20261107`。以下は独立control planの必須仕様であり、conditional samplerの支持・正規化の実装証明まで完了したという意味ではない。その証明、機械的監査、全割当封印を予測前のgateにする。

### 7.1 構成と操作成立

1. 同じ20 targetのうち既存FULL PFを持つ18葉・29末尾を母集団とする。control seedは92101。各BASE PF入口snapshotから、隔離したstate/RNG/rare/route/request countersで、1 event最大64回の**完全segment**を生成する。既存の本体2候補へ足さず、真正語の切り貼りや完成語の末字置換をしない。
2. matching用に真正側から渡す情報は、末字族・可視glyph長bin（1–3/4–6/7+）・可視glyph換算幅・実物理幅・canonical layout/maskの**粗い制約manifest**だけとする。これは人工対照を構成するための条件であり、生成器/lambda/proxyの学習へ渡さない。donor chooserには真正の個別末字・単語・審判scoreを渡さない。粗い制約の抽出元とhashを保存する。
3. proxyは外部complete16葉のstrict PFと通常LINE_END（F1LF/PLANTを除外）から、mを保持した22glyph末字分布を作る。葉等重みを有効event件数へ再規格化し、`pLF(g)=(nLF(g)+0.5/22)/(nLF+0.5)`、`pPF(g)=(nPF(g)+20*pLF(g))/(nPF+20)`。空資料はdata不足として停止し、targetへbackoffしない。
4. 同じ末字族内のglyphをexternal `-log(pPF(g))` の降順・同値はglyph ID順に固定する。64 trialへのtarget割当はこの順を循環する。**BASEよりproxy NLLが大きいことを条件にしない。** BASEは既にproxy上の高側にあり得るため、旧near/far条件を引き継がない。対象glyphの正支持・条件付き提案の正規化は、raw ENDだけでなくnative constraints、Map、m/rare後まで含めて証明する。証明のない最終CDF行の交換で「条件付き生成済み」としない。
5. 全branchを記録し、完成donorの末字族、長bin、可視glyph幅、物理幅が粗い制約と一致するものだけを適格とする。native support/packing/HEAD/W2/PHW/m/rareも満たす必要がある。適格候補の中からexternal rarity最大、tieはtrial ID最小で1本選ぶ。真正個別末字・CAL・JSDを見て選び直さない。64に達した未成立を支持不可能とは呼ばない。
6. 全donor IDと割当を封印してから、元真正面の対応する**完全segment**を置換した対照面を確定する。known3、layout、maskは保存し、END_ONLYを追加しない。参照は元真正面。個別末字を開示して操作成立を測るのはこの後。同じ末字になった例、末字histogramが相殺された例、donor不成立例を除外せず18葉の母数へ残す。

他の語・SPACE等も変わり得るので全featureの変化を報告する。個別末字だけの純粋な因果操作とは呼ばない。対象末字channelでは、**同族内の個別末字histogramの変化**と末尾ごとの変化を両方確認する。固定条件のまま15/18葉以上で実現しなければ `MANIPULATION_NOT_REALIZED` として予測前に停止する。seed、族、幅、branch上限、葉subsetを緩めない。

### 7.2 審判能力の確認

全donor封印後に対象descriptorの変化とJSD飽和を診断する。これでdonorを選び直さない。比較対象すべてでraw distanceと有効nが完全に同じなら固定CALも全tieとなるため、そのcontrol versionは `UNINFORMATIVE_CONTROL` として止める。それ以外は全18組の匿名予測を保存し終えてから真正/対照のキーで採点する。未変更例も予測・母数に含める。

対象は固定 `ATOM.PARA_END/terminal` CAL channel。真正を高く評価する期待正答率について、同点0.5、NAは比較可能coverageに明示し、葉等重みとする。以下を**すべて**満たした場合だけ `TARGET_TERMINAL_CAPABILITY_PASS`:

- 操作成立15/18葉以上（80%以上）。比較可能coverage80%以上、独立した比較可能葉10以上。
- macro正答率60%以上、葉bootstrap 10,000回（seed20261104）の95%区間下限が0.5より大きい。
- 機械的監査PASS、source/入力/制約/donor/予測順のsealが一致。

60%はこの新しい人工対照の能力gateであり、生成器の採用閾値ではない。旧007の75%条件を流用していない。proxy NLLの順序からCAL順位を保証しない。[CAL訂正012](../../designs/012-pf-review-corrections/CAPABILITY_CONTROL_ERRATUM.md)を適用する。

このPASSが示すのは登録した操作と対象channelの検出能力だけ。J24/ATOM総合の検出力や同等性、旧三対照全体の能力確認へ広げない。失敗時は第二案の本比較を止め、別の測定/対照設計へ戻す。新距離・新審判を使うなら、真正資料だけで事前fit/校正した新protocol/model setとして別封印し、旧CAL結果と混ぜない。

## 8. 実装後の機構検証

**これは今後の実行仕様。今日の生成件数は0。** 最初の固定集合に欠番scheduleを持つD:4を加える。

| 検証 | bif / seed / groups | 新規生成面数 |
|---|---|---:|
| 通常順 | A:2,A:3,D:4,G:1 × 91701,91711 × 4群 | 32 |
| 逆順・別root | 同じ32組を逆順で実行 | 32 |
| 恒等設定 | 同じ4葉 × 91701 × 4群。E両群をlambda=1へ設定 | 16 |
| 計 | 本比較・能力対照を含めない | **80** |

恒等設定では全群がREFERENCEと意味出力・packing・元request・全state・実main RNGで一致すること。通常設定でもBASE/REFERENCEは一致し、順序反転で各caseの出力が変わらないこと。語のCSVだけの一致で済ませない。

実例で不足する枝は結果を見てseedを替えず、境界fixtureで補う:

- 同じ幅・末字族で個別Eだけ異なりrankが変わる例、lambda=1直接委譲、E=0/欠損/EMPTY、複合glyph、pre-m/visible不一致、selector共有辞書不変。
- 初期tie、初期長5/6、長+1、幅が減る/同じ/+1/+2、同族異glyph、tol等号、最初の救済が初期より低得点、後続救済tie、適格なし、8枝すべての探索。
- 採用stateと初期argmax RNGの別commit、branch入力clone、共有request採番、次segment/最終state、例外時binding復元。
- 一語PF、厳密F1LF、PLANT前切断/図後BODY、END_ONLY、m保持/削除、rare prefix/suffix、BODY H1 2→1、W2 3→2とreceipt。
- scheduleからの全PF coverage、非連番ID `[0,2]` のsplit false、通常split true、一度だけの0.8 gain。

拒否fixtureは、score/候補の欠落・重複・並替え・全0自己申告、別candidateへの実在label付替え、lambda/W/EF/intercept改変、誤tokenization、誤LEN1基準、救済RNGからの継続、historical BASE初期winnerの誤使用、state/repair偽装、誤splitと整合する誤gain、manifest/入力/キー/古いPASS再利用を含む。独立検証側でtraceとchecksumを同時改変した負例も作る。

## 9. 後続の開発本比較

**開始条件**は、split製品監査修正の独立確認、第二案のunit/80面/拒否fixture PASS、登録した末字能力対照PASS、新studyの公式audit/plan/seal完成。現時点ではいずれも第二案の完了成果として存在しない。本書から自動開始しない。

条件成立後、別の実行planで固定する:

- 同じcomplete20葉の4面目をtarget、残り3面をknown3。外側5foldは維持する。
- seed `91701,91702,91703,91704,91705,91707,91708,91709,91710,91711`。
- BASE/PF_E_HALF/PF_E_ZERO/REFERENCE各200面、計**800面を新rootへ新規生成**。審判比較は3群×200=600組。第一案の生成物を混ぜず、失敗caseの除外・seed補充・恒等群の流用をしない。
- 主指標 `J24.CAL`、主要局所 `ATOM.PARA_END.CAL`。機序の事前指定readoutとして `CAL['ATOM.PARA_END/terminal']` を併記するが、新しいJ24票や独立主検定へ数えない。
- 固定CAL model set `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。refit、PROTO代用、新距離への無告知切替はしない。モデル変更時は本仕様の評価版も分ける。
- 全600予測を保存・封印後に正解キーで採点。seedを葉内平均した後、bifolium等重み。同点0.5、NAはNAのままcoverage/母数を示す。主対比ごとに共通比較可能trial上の率差と50%距離差、符号反転を出す。
- 葉bootstrap10,000回、seed20261104。対応差を葉内で構成し、同じ再標本葉で比較する。独立葉数を生成面数やseed数で水増ししない。
- 候補bank・選択後・最終可視のn/y/m、全22glyph、末字族、短中長、物理幅/可視幅、救済発動/適格/採用、rank変更、repair、SPACE、周辺atomを併記する。非観測PFも機構監査の母数に残す。

50%への接近は、対象審判に識別されにくくなったという開発上の所見。50%未満へ大きく反転した場合を改善扱いしない。同じ開発20葉の再利用なので汎化確認とは呼ばず、採用許容幅や新たな有意差閾値を後付けしない。現段階の正式採用・main mergeは対象外。

距離差は、共通trialから作った葉等重みの率をA/Bとすると `abs(B-0.5)-abs(A-0.5)`。葉ごとの絶対距離を先に平均する値とは区別する。各bootstrapでも再標本葉からA/Bを作ってから同じ式を適用する。

## 10. 今回の完了範囲

第二案の数式、原版LEN1、接続位置、状態/RNG、独立監査、能力対照の前提、機構検証と比較を設計した。新たに行ったのは読取専用のソース監査のみ。製品監査の既知不具合と能力対照未達は残存し、実装・80面検証・能力対照・800面本比較は未着手。

公開物は報告・設計・集約されたソース監査だけ。raw真正語/生成語、面、正解キー、予測JSONL、snapshot、donor、archiveはこの報告commitに含めない。
