# PF生成・選択改善の設計 v1

作成: 2026-11-05（日本時間）。状態: **設計済み・設計レビュー用。新モデルは未実装、未学習、未生成、未評価**。

[3提案の評価](EVALUATION.md)、[機械可読の設計契約](DESIGN_CONTRACT.json)、[ソース・学習母集団監査](SOURCE_AUDIT.json)と併読する。本書は既存M1のM2/M3とは別のPF改善系列で、正式版の番号は割り当てない。

## 1. 目的と範囲

BASEを対照として、段落末の短語・中語・長語の分布と、幅・末字・接続の残差を調べる。最初の実装対象は提案1。その後に提案2、提案3を別々に検討する。

適用segmentは親の `is_pf(sr)` と同一:

```text
raw_para_final == True
boundary_type == LINE_END
para_line_raw >= 2
```

全PFへ同じ構造条件で適用し、審判に観測されるかで生成処理を切り替えない。評価時だけFULL / END_ONLY / NONEを分ける。END_ONLYをatomの観測例へ加えない。

原版・審判・M1実装は保存し、新しい独立package `experiments/pf_generation/` を予定する。PF以外に直接の新処理は加えないが、PFでの採用state・語数・RNGが後続へ及ぼす総効果は含む。PLANT切断、図後BODY、既存route・rare・m・F1LF二段commitを維持する。

## 2. 変更箇所と処理順

```text
固定入力・fold・新lawのhashを照合
  → PF以外は親models/samplerで生成
  → PFでは既存2候補と条件付きLEN1の各枝を生成
       → PF_GATE: 親のclosing確率へPF offsetを追加
       → PF_GATE_LENGTH: 同じgate + raw END語への長さ重み
       → 親のMap選択・既存補正・m/rare・packing・commit
  → 既存PF scoreで2候補argmax、既存LEN1判定・採用
  → 採用stateをcommit、main RNGは初期2候補argmax枝から継続
  → 機構監査 → 匿名化 → 固定審判の全予測保存 → 採点
```

`runtime.py`は既存runner構築を参照し、PFの `complete_segment()` 呼出しにcase-localなmodels viewを渡す。gateはそのviewの `gate.predict_proba()` adapterで差し替える。原版 `m.gate_prob`、共有models、展開runtimeファイルを変更しない。原版のsplit後 `FINAL_SEG_CLOSE_GAIN=0.80` はengine側で一度だけ適用する。

raw語長重みは、既存 `EntryFastSampler` を継承した `PFEndProposalSampler.__call__()` へ置く。`qend`だけの交換ではない。上位のv22.3 sampler系列はそのままとし、Map候補bankのraw drawにも同じ法則を適用する。ゲートとsamplerをcase外へ残さず、`finally`で接続を復元する。

既存runnerは `rb.EntryFastSampler(base,tables,patch)` でinstanceを作るため、新runtimeはこのbindingをcase-local lawを捕捉するfactoryへ一時接続し、元bindingも保存・復元する。共有coreのFastSamplerやその `dw/dw2` 配列を変更しない。REFERENCEでは元bindingを使う。新runtimeも1process内の生成をlockで直列化し、並行実行は別processに限る。

## 3. 新法則の訓練契約

- `FoldContext.complete_train_bifs` の16葉・全4面だけを使う。外側test4葉すべてを除外し、target葉のknown3も新法則には使用しない。元のcore・既存known3補正は保存する。
- parent `strict_line` を満たし、複数行段落の最終LINE_ENDに対応する完全なsegmentをPF学習資料とする。順序、幅和+空白=容量、各語の残り幅、最終語flagを検証する。不完全行を継ぎ合わせない。
- 通常行末priorは同じ外部16葉のstrictな非段落最終・`para_line_raw >= 2`・LINE_END末尾を使う。PLANT、F1LF、1行段落を混ぜない。
- 複合glyphは1glyph。学習表は入力のstable22 surfaceと親の `m.stable_width` を使用し、mを保持する。生成への適用はpre-m/pre-rare raw語であることを明記する。学習表の語が生成器の潜在pre-m語だったとは仮定しない。
- 審判の可視幅と親の物理幅を区別する。m/rare後の語長・可視幅・実物理幅を別に記録し、学習分布と最終可視分布が一致するという保証は置かない。この表記差が主要残差なら別版で表記整合を検討する。
- PF資料は葉ごとに等重みになるようにし、総重みは元の有効件数へ合わせる。priorも葉ごとに等重みとする。欠けた葉とイベント数を保存する。
- この版では縮約強度等の探索を行わない。将来探索する場合は外部16葉内だけで行い、内側検証葉を新法則のfitから除外する。既存親modelが内側葉を既に学習している場合は、その事実を残し、全体系の独立したnested評価とは呼ばない。

## 4. 提案1-A: PF_GATE

各PF segmentの各語開始位置で、真正資料の `R=segment_rstart`、`C=segment_capacity` と最終語label `y` を作る。親のgateとsplit gainを適用した確率を `z0(R,C,split)` とする。

```text
zPF = sigmoid(logit(z0) + theta[remaining_width_band(R)])
remaining_width_band = 1–3 / 4–6 / 7–9 / 10+
```

学習は `logit(z0)` をoffsetとした4係数の正則化binomial loss:

```text
loss(theta) = sum_i w_i * binomial_log_loss(y_i, zPF_i)
              + (20 / 2) * sum_b theta_b^2
```

容量・残り幅比は親gateで扱い、初版で追加の大きい条件表を作らない。観測0のbinは `theta=0`。非有限値、収束失敗、入力不整合は停止する。明示されたデータ不足は0 offsetへbackoffする。全offset=0の恒等設定では親gateへ直接委譲し、追加乱数を消費しない。

gate adapterが返すのはsplit gainを加える前の確率。fit時の `z0` に含めたsplit gainとengine側での一度の適用が整合することを数式・実値で検査する。早期closingを強制せず、許容された親のpacking/retryを残す。

## 5. 提案1-B: PF_GATE_LENGTH

PF_GATEと同じgateを使い、raw END語へ条件付きの長さ重みを追加する。先に末尾幅を予約する方式や語内kernelの書換えは初版では採らない。

学習表は長さ3区分 `B=1–3 / 4–6 / 7+`、物理幅4区分 `J=1–3 / 4–6 / 7–9 / 10+`。通常LINE_ENDから `pLF(B|J)`、PFから `pPF(B|J)` を作る。

```text
pLF(B|J) = (nLF(B,J) + 0.5 / 3) / (nLF(J) + 0.5)
pPF(B|J) = (nPF(B,J) + 20 * pLF(B|J)) / (nPF(J) + 20)
gain(B,J) = clip(pPF(B|J) / pLF(B|J), 0.25, 4.0)
```

観測0のPF幅binでは `gain=1`。通常行末にも資料がない幅binはuniformからのfitを行わず `gain=1` とする。小さい正のpriorは比率を有限にするためのもので、親grammarに存在しない語の生成支持を追加しない。

適用条件はPF segment内の現在の `end=True` 呼出しだけ。`pl>=2`、`state.row_phase==FINAL`、`line_end_boundary=True` とsegment対応を再検査する。roleはBODYに限定せずHEAD/W2も許すが、元の強制H1・W2補正・Map選択は保存する。

raw語の重み付けは次の有限再標本化とする。

1. 親EntryFastSamplerを呼び、最初のraw語をanchorとして保存する。語長とstable物理幅を測る。
2. `gain(B,J) / M` の確率で受理する。`M=max_{B,J} gain(B,J)` はそのlawの全binで共通の定数。生成に渡された同じword RNGを使用する。
3. 不受理なら同じ親raw samplerから再提案する。raw drawはanchorを含め最大32回。すべて不受理なら最初のanchorへbackoffする。
4. raw語を返した後に、元のMap候補選択・既存補正・m/rare処理・packing・terminal-family判定を通常どおり行う。新たなraw再提案の内部でrare変換やcommitを実行しない。

全gain=1またはlaw無効なら、余分なaccept乱数を引かず、親を一度呼んで直接返す。従って恒等設定はBASEの生成・state・main RNGを再現できる設計とする。

空のraw語には長さbinを割り当てず、親へそのまま返して既存のpacking/retryへ委ねる。親例外も握り潰さない。幅binごとにaccept正規化定数を変えて、意図しない幅間の重みを追加しない。なお親raw分布は学習priorと同一ではないため、共通Mでも幅の周辺分布は保存されるとは限らず、実測を併記する。

これは親raw分布への正の重み付けであり、完成語の比率を学習表に強制一致させる方法ではない。幅fit、Mapの同長・同幅候補条件、m/rare、PF selector、LEN1、32回打切りが最終分布へ作用する。anchor fallback率・raw draw数・棄却理由・各段階の長さ分布を必須出力とする。

最小受理率は正の重み上限・下限から1/16。32回の上限でもfallbackが無視できるとは仮定しない。Map内の補助候補drawにも再標本化が入るため、raw総呼出し数と時間・最大メモリをsmokeで測り、本比較前の実行予算へ反映する。

合法な長語が親支持に存在しない条件を、raw drawsで出なかっただけの条件と混同しない。記録は `NO_SUPPORTED_LONG_PATH`（支持解析で確認できた場合のみ）、`NOT_OBSERVED_WITHIN_LIMIT`、`NO_TRAINING_BIN`、`RAW_BACKOFF_ANCHOR` を区別する。支持の全探索が未実装なら不可能とは宣言しない。

## 6. 提案2: PF_E_HALF / PF_E_ZERO

提案1の変更をすべて無効にしてBASEから分岐する。初期2候補と、従来条件で探索する救済枝の全scoreに次を適用する。

```text
E(seq) = 元coefficient['E=' + raw stable末字glyph]
S_lambda = S_BASE + (lambda_E - 1) * E(seq)
lambda_E = 1.0 / 0.5 / 0.0
```

intercept、W/WB/WR、EF、2候補数、LEN1の+1・幅+1・族一致・許容差1.0・8追加枝を維持する。`lambda_E=1` は再計算せず元score関数を直接返し、浮動小数点の再加算でtieを変えない。score欠損のE係数は元と同様0。

LEN1の適格判定にも `S_lambda` を使うことを明示する。これは個別末字成分を変えたアルゴリズム全体の総効果であり、救済を固定した純粋な末字選択効果ではない。初期argmaxと救済適格性をBASE scoreでも併記するが、後者は同じbank上の記述的診断に限る。main RNG継続元は、そのarmの初期2候補argmax。rescued stateとの分離は原版どおり。

全score、E寄与、EF寄与、候補順位、救済適格・採用、stable/visibleのn/y/m、後続RNGを保存する。末字だけの後処理やPF外のm法則変更は行わない。

## 7. 提案3: PF_SPACE_HEAD

提案1・2の変更を無効にし、BASEから分岐する。完成したPF候補segment内の最後の2語だけから `前語末字族 → PF語頭glyph` を取る。語は最終可視stable22 profile（rareを除去、mは保持）とする。元S_BASEのpre-m末字特徴と別fieldで記録する。

外部16葉のstrict PF SPACEと通常BODY SPACEから、末字族ごとの条件付きH1分布を求める。通常BODYへの縮約20、通常BODY側の小prior0.5を使う。資料のない条件は新score=0へbackoff。初版は語長対を同時に加えない。

```text
S_space = clip(log pPF(H1|previous_family) - log pBODY(H1|previous_family), -2, 2)
S_new = S_BASE + 0.5 * S_space
```

一語segmentでは `S_space=0`。PLANT・行を越えた前語、欠損区間をまたぐ前語を使わない。元selectorを改変せず、新しいcomplete-segment score adapterがS_BASEへ加算する。LEN1適格性もこのscoreを用いるため、提案2と同じ総効果の注意を適用する。係数0では元scoreへ直接委譲する。

`前語長→PF語長` は別arm `PF_SPACE_LENGTH_PAIR` の後続設計とする。同じ比較でSPACE_H1と同時追加しない。提案1が採用候補になった場合も、初めて組合せる段階で別planを作る。

## 8. 状態・RNG・入力封印

- 枝は同じ入口GenerationStateからcloneし、親state/main RNGの汚染を検査する。採用segmentの全state、rare、route、last_request、word_first_requestと参照結合をcommitする。
- 初期argmaxの終了main RNGを継続元とし、救済採用時も救済枝のRNGへ変更しない。新処理の乱数消費・全attempt共有のproposal_id・後続補正side RNGへの波及は総効果に含める。
- 新しいsampler制御監査は、immutable law参照、記述counter、純粋cache、枝固有の制御を列挙して区別する。未知fieldは拒否する。M1 `SamplerControl` の許可集合を黙って拡張・無効化しない。
- 新packageで新しいplan schemaとsealを作る。原版・審判・M1のhash、runtime tree、外部学習資料と除外集合、law、ソース、設定、seed、評価maskを結合する。生成後のmanifestと監査receiptも結合し、古いPASSを再利用しない。
- 本書のmanifestは設計資料の完全性を示すだけで、生成実行のplanではない。別の新規出力先と実行planが必要。

## 9. 実装分割と出力契約

| 予定module | 責務 |
|---|---|
| `laws.py` / `fit.py` | external16の抽出、gate offset、長さ比、score law、除外集合とhash |
| `gate.py` | case-localなgate adapter、split gainの一度の適用 |
| `proposal.py` | 親raw samplerの支持内再標本化、恒等経路、32回上限 |
| `overlay.py` / `runtime.py` | PF枝、完成segment score、接続復元、独立出力 |
| `plan.py` / `audit.py` | 新schema、入力/監査binding、state/RNG、非介入境界 |
| `diagnostics.py` | 候補・採用・可視分布の再現可能な集計、能力対照 |
| `evaluation.py` | 審判APIへのadapter。元feature、fit、CAL、集約を変更しない |

最小の追加ログは、gateイベントのC/R/role/元確率/offset/採用flag、raw候補の長さ/幅/gain/draw数/fallback、PF候補のS_BASE/各新成分/採否/state/RNG。stageはraw → Map選択後stable → m/rare後 → PF採用後visibleで区別する。7+跨ぎを記録し、M1ログの既存2〜5閾値だけを流用しない。

## 10. 実装後の検証計画

1. **恒等経路**: offset=0、gain=1、lambda_E=1、SPACE係数0が、BASE/原版REFERENCEとtokens・packing・request・commit・最終state/main RNGで一致することを確認する。
2. **小規模生成**: 固定A:2/A:3/G:1、seed91701でBASE/PF_GATE/PF_GATE_LENGTHとREFERENCE、通常順/逆順を実行する。3×1×4×2=24面。境界の十分性を構造ledgerで先に確認し、不足の境界は合成fixtureで補う。結果を見て都合のよいseedへ替えない。
3. **負例と境界**: 学習の外側test混入、展開入力改変、law/設定改変、生成物とchecksum更新後の古いPASS、RNG偽装、未知mutable fieldを拒否する。R=小、複合glyph、m跨ぎ、一語PF、PLANT後BODY、F1LF、END_ONLYも確認する。
4. **機構**: packing/support/確率/末字整合/commit不整合は0。raw打切りや学習bin不足は失敗と混ぜず母数付きで報告する。fallbackが集中して実質介入できない場合は本比較前に設計へ戻る。
5. **能力対照**: 長さ・幅、末字、SPACEについて、外部16葉の参照分布へ寄せる/離す診断対照を別planで作る。対照の選択には審判scoreを使わない。同容量・支持内の候補を優先し、単独特徴だけ動かせなかった数と他特徴の変化を報告する。診断用の人工対照を本体改善のarmへ混ぜない。
6. **能力の判定候補**: 独立cluster10以上、変更可能coverage80%以上、各方向の期待順位正答率75%以上かつcluster bootstrap下限50%超を初期基準とする。対照の構成・比較方向・母集団・hashを生成前に固定する。到達できなければ `INSUFFICIENT_CAPABILITY` とし、検出できない指標で同等性・改善を宣言しない。
7. **開発本比較**: 上記を確認してから別実行planを封印する。提案1はBASE/PF_GATE/PF_GATE_LENGTH、全20葉×同じ10seedの各200面+REFERENCE200面を想定する。主対比はBASE→PF_GATE、PF_GATE→PF_GATE_LENGTH。初期seed集合は旧共通集合を継承し、新しい失敗seedは除外・補充しない。

能力対照は次の手順で具体化する。実行前にcontrol planへ同じ定義を封印する。

- BASE生成時のPF入口snapshotを保存し、別processで同容量の親支持内segmentを各イベント64枝まで再生する。診断用の採番・RNG・rareは独立したreplayに閉じ、元BASEや本比較の継続を変えない。追加生成は診断専用で、2候補の本体armへ加えない。
- 外部16葉から固定した生の参照分布に対する負のlog確率を距離Dとする。長さ/幅は3×4区分のjoint分布、末字は22glyph分布、SPACEは前語末字族条件付きH1分布。通常LF/BODYへの縮約20とprior0.5を用い、審判score・target真正語は距離へ使わない。
- 同じイベントのBASE末尾に対し、Dが小さいnear候補と大きいfar候補を選ぶ。差1e-12以内は同距離とする。末字対照では長さ区分・物理幅と末字族を固定し、SPACE対照では末尾語の長さ区分・物理幅・末字を固定する。length/widthはまとめた対照とし、長さだけの寄与とは呼ばない。条件を満たす両方向の候補がなければ変更不能と数え、結果を見て条件を緩めない。
- near/base、base/farの2組をA/B匿名化し、元のknown3・layoutとともに固定predictorへ渡す。control種類・near/far label・snapshot・選択距離は渡さない。全予測保存後、nearがbaseより、baseがfarより高い真正らしさscoreを得るかを各方向で採点する。同点1/2。これは人工対照の順位課題で、真正/生成の本比較正答率とは別に保存する。
- donorに含まれる他の語も変わり得るため、対象外のatom・末字・SPACE・語長の変化を記録する。成立した対照の検出能力を、特徴ごとの完全な因果分離へ読み替えない。変更可能coverageは対象FULL PFイベント数に対する比率と、両方向を作れたtarget面・独立葉数を併記する。

主指標はJ24.CAL、主要局所はATOM.PARA_END.CAL。50%からの距離差と符号付き差、共通trialの対応、同点/NA/coverage、葉等重み、記述cluster bootstrap10,000回を保存する。PROTO、8atom、J07/J19/J20/J25、生の短中長分布・幅・n/y/m・SPACEとfallbackを併記する。全群の予測を保存・封印してから正解で採点する。

短語側やW2を悪化させて7+だけを増やした候補を、長語不足の解決だけで採用しない。本版は開発上の評価設計までとし、正式採用の許容幅・多重比較による選抜・独立確認は別の事前計画で扱う。`promotion=null`。

## 11. 完了条件と次の受け渡し

本段階の完了条件は、3案の評価、ソースに対応する実装箇所、学習・fallback・RNG契約、比較と監査の設計を共有すること。これは本書で満たす。

検証側には[依頼008](../../requests/008-pf-design-review.md)で、設計上の欠落・実装不能・評価漏洩を文書レビューしてもらう。新モデルの実装や800面生成をこの依頼で開始しない。実装開始後も、原版・審判・過去報告を上書きしない。

再現用の入力監査コマンド（出力は未使用のパスを指定）:

```bash
NUMBA_NUM_THREADS=2 PYTHONPYCACHEPREFIX=/workspace/voynich-setup/pycache \
  /workspace/.venvs/voynich/bin/python \
  sandbox/m1-review/designs/007-pf-generation-v1/source_audit.py \
  --output /tmp/pf-design-source-audit-new.json
```
