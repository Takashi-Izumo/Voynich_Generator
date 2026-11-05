# 本比較の停止: m変換後のW2 H2補正と可視末字状態の不一致

**P1・実装側への修正依頼。800面の本比較は421面で停止した。** seedの除外・差替え、assertの無効化、状態/ログの後付け書換えで継続しない。部分集合の識別率は算出していない。

## 実行と再現

- 固定plan `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17`、生成sourceは独立PASS済み第一案と同じ。開始方針の更新は197de98で全対照・本比較結果前に登録済み。
- 完了421/800面: BASE 200、PF_GATE 196、PF_GATE_LENGTH 25、REFERENCE 0。失敗1ケース、停止後未生成378ケース。全800ケースの状態は [PARTIAL_EXECUTION.csv](PARTIAL_EXECUTION.csv)。
- 失敗: **PF_GATE_LENGTH / A:3 / seed91711**。worker3のAssertionErrorで他workerもケース境界で停止した。
- 同じplanとsourceで、この1ケースだけを新Runtime・新出力rootへ再生成し、同じ失敗を再現した。実行順によるだけの現象ではない。
- 原版runnerの `terminal_mismatches==0 and fake_head==0` で停止。実測は **terminal_mismatches=1、plant_false_heads=0**。
- BASE 200面は前回の独立本比較BASEと、全意味出力・最終state・実main RNGが一致した。421面全体の監査PASSは作っていない。

## 特定した原因

失敗はf6v、locus f6v.10、segment0、W2、proposal_id630。段落内第5行のMIDDLE W2で、PF最終segmentでもF1LFでもない。PFの介入による後続RNG等への総効果で、この経路に到達している。

1. W2_B2はpre-mのstable長3でH2補正を準備する。
2. 原版 `apply_m_branch()` が末尾mを削除し、visible長が2になる。
3. [W2_B2.commit_surface](../../../../HerbalA_v22_3_20260921/model/code/w2_b2_sampler.py#L273) は先に親のsurface commitを実行する。
4. その後、H2を書き換える。visible長2なので、H2は可視末字でもある。
5. rowとsurface_commitsの文字列は更新するが、semantic `prev_terminal` は更新されない。

再現時には、可視末字は **a（ID12）**、状態は **o（ID10）** のまま。stable長3、visible長2、物理幅3。W2_B2適用/変更はtrue、F1LF/Stage3D適用はfalse。生の単語列は共有せず、[GENERATOR_FAILURE.json](GENERATOR_FAILURE.json)に位置・長さ・末字ID・関連flagだけを残した。

この状態は次の語のSPACE接続に使われるため、ページ末の監査値やログだけを修正しても生成は直らない。最終可視語が確定した時点で、次の語へ進む前に可視末字と意味状態を一致させる必要がある。

## 修正方針と必要な確認

既存W2_B2とm変換の連携で露出した問題である。原版・審判・m機構・W2_B2を丸ごと無効化せず、候補側のwrapper等で、最終visible H2をsemantic surface commit前に反映する構成を検討してほしい。routeのcommit_wordは既存のanchor方針を保持し、可視末字状態と混同しない。新しい乱数で回避せず、既に準備された補正を正しいcommit順序で適用する。

- 最低限、stable3→visible2のm削除＋W2 H2変更で、最終surface・surface_commits・prev_terminalと次の要求のprev_terminalが一致すること。
- mを保持した3→3、変更しないH2、rare末尾、PLANTリセット、F1LFの既存二段commitも確認する。同じ種類の境界としてBODY H1の2→1縮約もfixtureで確認する。
- 元のBASE/REFERENCEと恒等設定の正常経路、支持・packing・末字、route/state/RNG、R1/R2監査を保存する。
- 固定ケース A:3/91711/PF_GATE_LENGTHを回帰確認する。新sourceでplanを再封印し、独立確認後に同じ20葉・10seedの800面を新rootで再実行する。今回の421面を新sourceの残りへ継ぎ足さない。

## 対照側の別件

対照source `2bd7216` の `verify-export` CLIにも引数名の不一致がある。`__main__.py` は `exported=` を渡すが、`pipeline.verify_export` の引数名は `output`。提示CLIはTypeErrorで停止した。同じ照合関数を位置引数でAPIから実行するとPASSし、既存生成物や検査項目を変更せず続行できた。CLI→API接続を修正し、実際のCLI引数契約をテストしてほしい。

対照の独立機構では161 unitと448枝のfresh再生監査、20件の改変/汚染拒否を確認済み。全20葉の対照生成・再生監査・評価は別プロセスで継続し、結果を追記する。対照の合否と、今回の生成器不変条件違反を混同しない。

実装・status・依頼管理ファイルは変更せず、本報告だけを返す。raw生成語・snapshot・キー・archiveは含めない。tracebackは [main-failure-traceback.log](main-failure-traceback.log)、実行状態は [MAIN_FAILURE_SUMMARY.json](MAIN_FAILURE_SUMMARY.json) を参照。
