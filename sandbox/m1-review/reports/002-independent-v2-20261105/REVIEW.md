# M1 v2独立再検証報告

- reviewer: 検証側Codex。実装側のPASSを再利用せず独立実行。
- 日付: 2026-11-05（日本時間）。
- 開始時sandbox commit: `6c1dbcd72e942ac3d675df43dbc7872105249bf8`。
- 対象snapshot: `294a7afdc86949e4f774166c449a5415de9573c1e4e57ab6bb94032df57c1504`。manifest内25ファイルの実hashを照合。
- plan: `c392a1588d29139a6aaa53be18ce947b782159d0be02d0644f9c5f62329c3107`（新規schema v2）。
- 判定: **機構・接続の小規模再検証PASS。本比較は保留を維持。**

## 結論と前回報告の訂正

v1で再現したR1〜R3の問題は、今回の独立した負例で解消を確認した。検証したv2に新たな要修正事項は見つからなかった。

前回R4の「最終main RNGを記録・比較していない」はレビュー側の見落としであり撤回する。v1にも`MECHANICAL.rng_end`があり、意味出力の比較に含まれていた。詳細は[ERRATUM_V1.md](ERRATUM_V1.md)。v2の専用field・照合・負例は契約の明示化として確認した。

## 実行した内容

| 項目 | 独立確認結果 |
|---|---|
| M1 unit tests | 27件PASS |
| 凍結審判unit tests | 56件PASS |
| 実生成 | A:2 / A:3 / G:1、seed91701、3群＋原版REFERENCE、通常順と逆順を別processで並行実行。計24面 |
| BASE対原版REFERENCE | 3/3ケースで意味出力・最終state・明示的な最終main RNGが一致 |
| 通常順対逆順 | 3群×3ケースで意味出力・最終main RNGが一致 |
| 以前の公式原版出力との照合 | 3ケース×8ファイルの非圧縮payload計24本がbyte一致 |
| 匿名化・CAL接続 | 各群3trial、計9予測を全て保存後に採点、2つの対応比較まで完了 |
| 固定モデル | 指定model-set hashに一致。再学習・変更・PROTO fallbackなし |
| 独立負例 | 入力4種、成果物/監査/RNG6種を作成し、期待する拒否を確認 |

使用Pythonは`/workspace/.venvs/voynich/bin/python`（3.12.14）、`NUMBA_NUM_THREADS=2`。評価は`--jobs 2 --bootstrap 100`。コマンドは[COMMANDS.md](COMMANDS.md)、追加負例は`probes.py`とJSONの記録を参照。

ローカルの全生成物・監査・匿名入力・予測・採点は`/workspace/voynich-results/m1-v2-independent-20261105/`。共有Gitには報告・集計・再現script・小さなテキストlogだけを追加した。原版・審判・候補実装は変更していない。

## 4項目の再確認

| 項目 | 判定 | 独立した証拠 |
|---|---|---|
| 展開済み入力と計画の固定 | PASS | 実runtime上の設定を同じbytes数のまま変更、selector削除、追加selector、圧縮pickle coreの変更を作成。封印planの読込が全て拒否。削除ファイルの自動復元なし。元bytesへ全て戻した後はplanが再通過。`input-probes.json` |
| 生成物更新時の古いPASS拒否 | PASS | 正常な生成物を別rootへコピーし、tokenとmanifest checksumを更新。現在のchecksum検査は通るが旧PASSは拒否。sealのbindingだけ更新しても旧reportとの不一致で拒否。失敗した再監査で旧sealが削除され、repeat側の更新も拒否。`artifact-probes.json` |
| END_ONLYとatom観測の区別 | PASS | 凍結`word_events()`から直接観測集合を作りledgerと全73segmentを照合、不一致0。END_ONLYの19箇所は全て`judge_atom=null`、`judge_observed=false`、末尾情報の`endpoint_usable=true`。PF機構7箇所のうちatom直接観測は6。`scope-probes.json` |
| BASE/原版の最終main RNGの専用比較 | PASS（v1指摘は訂正） | 実randの終了state/hashを記録しMECHANICALとも一致。最終semantic state hashを保ったままREFERENCEのRNGとMECHANICALを整合的に変更し、manifestを更新した負例は`BASE final main RNG differs from reference`で拒否。MECHANICAL側だけのRNG変更も拒否。`artifact-probes.json` |

### 入力tree固定の範囲

信頼済み2本のarchiveの内容を期待inventoryとし、展開済み15,632ファイルの集合・bytes数・SHA-256を照合する。tree hashは`defa4df428a64a25358aae4a5c3305d4e31614cfa3c29136eb8359d570cce204`。archive自体のhash、原版・審判の追跡済みsource、M1 overlayも別に固定する。

compiler cacheを除外することは、固定資料と実行時出力を分ける今回の運用に整合する。runtimeが完全に未展開なら信頼済みarchiveから初期化でき、既存treeの部分削除・変更・追加は拒否する。あらゆる悪意のあるprocessや同時改変に対する安全性を証明したものではない。

### 監査bindingの範囲

監査対象のmanifest、copied plan、generation statusのhashをreportとsealへ結合し、export前に現在の生成物checksumとbindingを再確認する。repeatのbindingも同様に確認する。今回の負例は正常runのコピーだけに作り、正常な匿名入力・CAL評価には使っていない。

## その他の機構・評価契約

- BASEの2候補argmax、LEN1の適格条件・救済採用、PF_NO_RESCUEの救済停止、PF_ANCHORの候補0採用を確認。BASEのPFイベント7、救済探索24枝、採用1。PF_ANCHORの元argmaxからの変更2。
- 親state/rare/段落履歴のclone、採用segment全体のcommit、rebind、main RNG継続元を確認した。PLANTで切断し、図後BODY再開、可視m・複合glyph、厳密F1LFの既存commit契約を保つ。
- `next_proposal_id`は破棄枝でも進み、後続の補正用side RNGに作用する。これはv2でも維持する既存契約。今回の比較は波及を含む総効果であり、救済採用だけの直接効果を分離したとは扱わない。全乱数の完全な枝隔離をPASSとしたものではない。
- 審判と原版は基準commit`c610c2a81e733748e0fb246de89143d6ecda764e`から変更なし。匿名候補と正解は分離し、3群の予測保存後に採点。モデルは以前の固定資料を使用し、指定hashに一致することを確認した。

```text
extractor  5b74ed23eda0cad35377e0786f0c3aa8cc7375a033bb6cdc7ed81b98e343bc37
protocol   007d2c9556c5f19a72aa044aa01cf6bf6cbe60f7296e50504112242cf97896f0
model_set  61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79
```

## 問題点・未実施の範囲

今回の再検証範囲で追加の実装不具合は再現しなかった。v1のR1〜R3に対する修正と、RNG専用契約の負例はいずれも通過した。

段落末等の審判能力対照、全20葉×10seed、独立した一般化、採否の許容幅・多重比較方針の確定は実施していない。元Stage1表とのsource-law照合も今回の機構検証で解決したとは扱わない。bootstrap100のsmokeから改善・同等性・有意性・正式昇格を主張しない。

## 本比較への移行可否

**実装修正の独立再確認はPASS。本比較は現行sandboxの保留を維持する。**

実装側への引き継ぎ: R1〜R3の再修正を求める事項は今回なかった。前回R4は訂正として記録してほしい。次段階では、主要指標・周辺悪化・審判能力対照・採否規則を含む本比較計画を先に確定する。記述比較と採否/一般化の判断を分け、必要なら採番経路を揃えるSHADOW診断を別planで検討する。

この報告で本比較の実行、main merge、正式昇格を自動承認しない。検証側は報告だけを追加し、`status.json`と実装側の依頼文は変更していない。
