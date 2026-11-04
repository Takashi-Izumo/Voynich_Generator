# Visible-input judges v0.2

## 1. 入力と分離

JSONLの各行は次の必須キーだけを持ちます。追加キーは拒否します。

```json
{
  "schema_version": 1,
  "set_id": "opaque-pair-id",
  "cluster_id": "opaque-bifolium-id",
  "seed": 91701,
  "text_profile": "stable22",
  "known": ["document1", "document2", "document3"],
  "candidates": {"A": "documentA", "B": "documentB"}
}
```

上のdocument文字列の位置に、実際は以下のオブジェクトを入れます。

```json
{"lines": [
  {"paragraph": 0, "segments": [
    {"end": "PLANT", "tokens": ["qokar", null]},
    {"end": "LINE_END", "tokens": ["daiin", "chol"]}
  ]},
  {"paragraph": 0, "segments": [], "excluded": true}
]}
```

- paragraphは整数または文字列。同一段落の行は連続し、再出現は拒否します。
- 最終segmentだけLINE_END、それ以外はPLANT。通常segmentのtokensは非空です。
- `null`やglyph化できない語は原位置に残り、その前後をSPACEでつなぎません。
- excluded行は位置を残す評価除外マスクです。segmentsは空にします。これを飛ばして縦の隣接を作りません。
- 現在は共有layout条件付き対決だけをサポートします。候補A/Bの行数、段落区切り、segment境界、excluded maskの一致を検証します。段落IDの表記そのものや語数は一致不要です。参照3面のlayoutは候補や他の参照面と異なって構いません。自由layout profileは未実装です。
- 各文書には観測可能なglyphを含む語が少なくとも1つ必要です。片側全除外・全UNKNOWNは拒否します。
- 1行段落はfirst/finalの両方、1語行はhead/LFの両方です。第一行は各段落の第一行です。
- `ch/sh/cfh/ckh/cph/cth`は1 glyph。文字数とモデル内のglyph幅を区別します。画像の実測幅を自動推定する実装ではありません。
- `stable22`ではrare文字の残存を拒否します。`raw`ではbgjvzuをstable解析時に除き、別途J21に数えます。mは除きません。
- knownはちょうど3文書。truth、実在page名、内部role、candidate bank、score、乱数state等のフィールドは入力schemaにありません。

正解は別JSONL `{"set_id":"...", "truth":"A"}` に置きます。predictはそのパスを受け取らず、scoreだけが読みます。これはコードの入力分離であり、OSによるファイルアクセス隔離ではありません。匿名IDは同点解消と照合にだけ使用し、文字列の類似度学習には使いません。

## 2. 固定ベースラインの採点

設定は`registry.CONFIG`で版管理します。CLIから係数を即席変更する経路はありません。変更時はversionを更新し、新しい実験として再封印します。

v0.2.0の設定名は`partition-prototype-jsd-v2`です。v1とは条件付き混合とJ17の定義が異なり、設定hashも異なります。過去のv1予測は新設定で答え合わせせず、元入力から作り直します。

`primary_atoms`はATOMSの非空・重複なしの部分集合、`atom_weights`はその集合と完全一致するキーを要求します。重みは有限・非負、合計は有限・正である必要があります。重み0の区分は総合から除外します。APIの`predict(case, config=...)`でも設定を検証・適用し、実際に使った設定のhashを返します。CLIの封印・答え合わせは現在のregistry設定に固定です。

### 区分

各語は次の優先順で唯一の総合用区分に入ります。

1. PLANT_END：植物前の最終語
2. PARA_END：段落最終行の物理行末
3. LINE_END：その他の物理行末
4. PHW：各段落第一行の物理第一語
5. FIRST_INTERIOR：第一行の残る継続語
6. HEAD：第二行以降の物理第一語
7. W2：第二行以降の物理第二語
8. BODY：残る継続語

語内のword、長さ×幅、語頭2字、terminal、bigram、trigramをそれぞれ別channelとして数えます。通常SPACEのT→H1、語ペア、語長ペアも、接続先の区分に一度だけ割り当てます。参照3面を各面内で正規化して等重みで混合します。両候補と参照に事象があるchannelだけを共通に用い、各候補のスコアを`-JSD(candidate, reference)`とします。channel差を区分内で平均し、その後、設定した正の重みを持つ有効区分だけで重み付き平均した差でA/Bを決めます。NA区分を除いた重みで再正規化します。デフォルトは8区分の等重みです。J01〜J23/J25の表示をさらに投票させません。これは固定の特徴合成であり、channelを統計的に独立と仮定した証拠の加算ではありません。

空のchannelはNAであり完全一致ではありません。片側だけ空の場合も、そのchannelは両側とも採点から外します。事象数・適用channel数・有効区分を出力します。この初版は欠測の発生そのものを識別する学習器を含みません。

内部で差0のchannelを左右へ乱択投票させません。比較可能な正重み区分が1つもなければ入力不成立としてエラーにし、予測を封印しません。比較可能な区分があり、最終差の絶対値が設定許容幅（デフォルト1e-12）以下のときだけ、`sha256(config_hash|set_id|final-tie-v1)`の固定規則で二択にします。暗号学的な正解隠蔽を主張せず、ID割付を真偽と独立に固定します。

「参照に近いほど真正」という方向を固定した研究用比較器です。参照への過剰一致を見破る校正器は未学習です。型数・反復等の表示も、それだけで同等性の証明にはなりません。

### 条件付きchannel

J09等は単なるH1H2 joint-JSDではありません。まず各参照面のjoint分布を正規化して等重み混合し、その混合jointをcontextで条件付けます。各面で先に条件付けた行を均等平均する方法ではありません。混合jointのcontext質量を重みとし、参照・A・Bのすべてで観測された共通contextについて、条件付きoutcome分布のJSDを重み付き平均します。参照context被覆率と事象数も出します。未観測contextへ確率を外挿する平滑化は初版に含めません。

J17もJ19と同様に照合面数を2面に揃えます。候補は参照3面から2面を取る3組を使い、各参照面の基準値は自身以外の2面だけを使います。J17の各subsetの非空channelを正規化して等重み混合し、persistenceはsubsetごとに別stateを持ちます。J17のcountsはこの混合後の質量であり、原glyph事象数そのものではありません。

## 3. 表示IDと実装の範囲

| ID | 表示・特徴 | 制約 |
|---|---|---|
| J01 | 第一行第一語の語形・長さ幅・語頭・末尾・語内ngram | 物理語順から抽出 |
| J02 | 第一行全体 | J01/行末等と重なる表示 |
| J03 | 第二行以降の物理行頭 | UNKNOWN後や図後を昇格させない |
| J04 | 第二行以降の物理第二語 | 内部W2ラベルは読まない |
| J05 | 物理第三語以降 | 第一行・行末との重複を許す表示 |
| J06 | 物理行末 | Pを含めない |
| J07 | 段落最終行全体 | 最終語だけでない |
| J08 | 第一行末terminal・L≤3/L≥4 | 広い可視FIRST-LF。strict 88 ledgerの復元・teacher-forced NLLではない |
| J09 | HEAD H2|H1、H3|H1H2 | 共通context条件付きJSD |
| J10 | 同一段落・隣接物理行の語頭遷移 | 除外行をまたがない |
| J11 | 中間行・継続W2のL3/L4/L5 H2|H1 | 内部sibling/B2適用ログは使わない |
| J12 | 継続BODY L2〜4のH2|H1 | 共通context条件付きJSD |
| J13 | 過去の完了行にあるBODY語頭の最頻glyph→現在H1 | 可視履歴の代替診断。RUN32の期待残差state再現ではない |
| J14 | 継続BODYのsegment残幅帯→terminal族 | 可視glyph幅からの相対残幅。内部R≤9の直接再現でない。未知幅のsegmentはNA |
| J15 | 通常SPACEのT→H1、bT→H1 | PLANT/UNKNOWNをまたがない |
| J16 | P/L/I別の末尾2字 | bank加点・inventory・旧bT尤度の完全再現ではない |
| J17 | 2面照合の共有3〜6gram、prefix/非prefix、可視route持続 | 候補は2面subsetの平均。内部MapState/dwell/adjacencyの監査とは別。植物前で一律resetしない |
| J18 | glyph-depth/END、長さ×幅joint | 見える語境界のみ。内部STOP確率は不使用 |
| J19 | 参照2面とのexact/1glyph-near/novel | 候補は3面中の2面の全組合せ平均、各参照は他2面でLOO。探索表示 |
| J20 | 型数・hapax等の頻度帯、反復の物理行距離 | 語数で正規化した粗いbin。未校正 |
| J21 | rareの有無・種類・境界位置 | raw profileだけ。stable22ではNA |
| J22 | 植物前末・図後最初の語 | 必須表示。PとLを区別 |
| J23 | 面全体語彙・語内2〜6gram | 旧TF-IDF cosineの再現ではない |
| J24 | 上述の8区分からの総合 | 旧combined/16票panelとは別の新ベースライン |
| J25 | 同segment内の語ペア・語長ペア | 完全一致語ペアは疎い。NA/被覆率を確認 |

基本表示にも専門表示にもNAがあり得ます。IDが25あることは、独立25審判の完成や、有効25票を意味しません。厳密な機構監査の追加、旧審判の履歴再現、新総合の学習・校正は別の作業です。

## 4. 封印と答え合わせ

predictは入力全件を検証してから新しい出力ディレクトリを作成します。同じset_id、同じcluster_id/seedの二重登録を拒否します。既存ディレクトリへの上書きはしません。

`manifest.json`には設定、設定hash、コードhash、入力ファイルhash、予測hashを保存します。scoreは予測hashと設定hashを確認し、キー集合の完全一致を要求します。hashは改変検出・再現記録であり、署名や第三者による封印サービスではありません。

主成績は`mean_b(mean_seed(correct))`。raw正答率とbifolium等重み正答率は別欄です。区間はbifoliumの平均正答率を単位とした固定seed bootstrapの記述的percentile区間です。clusterが1つなら区間を出しません。20 bifolia×10seedを200独立標本とは扱いません。

scoreは総合主審の正答率と、各表示の決定件数・NA・同点・被覆率・判定したケースだけの記述的正答率を出します。後者は棄権を除くため、主ゲームの正答率と混同しません。専門審判すべての多重比較や昇格判定は未実装です。`promotion_verdict`は常にnullです。

## 5. v22.3 adapterの条件

`export-v223`は、v22.3の現在の固定第4面と保存済みtokens.csv.gzを読みます。採点器からはadapterやcorpusをimportしません。

adapterは元scheduleと原転写が一致するcleanな物理行だけを評価し、対象面の同じマスクを真正・疑似に適用します。除外行も空のplaceholderとして残し、位置を詰めません。既知3面には同じ品質規則を適用します。評価データを見て成績の悪いseedを選別する機能はありません。

共有layoutで条件付けられること、未知/rareを含む原行の除外、f28v.7例外はexport manifestに記録します。raw profileの検証や旧200ケースとの前処理一致を主張しません。全20面を評価するには全対象生成物を別途用意してください。
