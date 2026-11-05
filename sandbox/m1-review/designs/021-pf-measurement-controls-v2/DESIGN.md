# PF評価・能力対照の見直し案 v2

状態: **設計のみ。新審判・新donor方式は未実装、未fit、未予測。** 報告019を受けた次版候補であり、今回のv0.3の結果・モデル・閾値を変更しない。今回修正した生成器commit不整合/CLI不具合とは別の課題として扱う。

## 受領した事実と判断

対照機構は全20葉2,240枝のfresh replayで独立PASSした。far能力対照はlength_widthが47.2%・操作実現17/18、terminalが47.2%・操作実現6/18、SPACEが58.8%・操作実現8/17。全項目NA=0。length_widthは15/18組でraw JSDが両側1、うち14組で対象countは変わっていた。末字/SPACEは操作が不足しており、この結果から審判の能力不足を断定しない。

したがって、(1) exact joint JSDの非交差時の上限飽和、(2) 固定64枝と厳密filter下の変更候補不足を別に解く。CALの丸めや本体PF法則を原因と決めつけず、v0.3審判団全体の無効や生成器改善も主張しない。旧106組の数値・分母・区間を保存し、新方式の成績へ付け替えない。

## A. 長さ・幅: joint energy distanceを候補にする

exactカテゴリJSDを単に平滑化する案は、平滑化幅と質量の選択が距離を強く左右する。長さ/幅を別々の1次元距離にする案はjointの依存を失う。ここではjointを保持する2次元energy distanceを第一候補とする。RBF kernelは帯域により遠方で再び数値的な飽和が起き得るため、最初の候補にはしない。

凍結visible tokenizer/WIDTHから、各FULL PARA_ENDを `x=(glyph_length/sL, visible_width/sW)` とする。モデルのprior-train8葉・全4面の真正資料だけで、葉等重み→面等重み→対象末尾等重みの分布を作る。各尺度は `max(1, weighted_IQR)`、分位点はCDFがq以上になる最初の値。emptyなら1とし、count/backoff/hashを保存する。outer test4とnull-calibration8の語値を尺度fitへ使わない。

候補の経験分布Pと、known3各面の非空分布を等重み混合したQについて、

`D(P,Q) = 2 Σ_i,j p_i q_j ||x_i-y_j|| - Σ_i,k p_i p_k ||x_i-x_k|| - Σ_j,l q_j q_l ||y_j-y_l||`。

丸めで `-1e-12 <= D < 0` の場合だけ0へ補正し、それ以下は失敗とする。参照/候補が空なら既定の観測規則に従うNA。glyphが複合でも1glyphとして扱い、物理幅に置き換えない。この距離はカテゴリ支持が非交差という理由だけでは一律1にならず、jointの幾何的な離れ方を区別できる。一方、CALの有限null rankによる同点や識別能力の不足まで解消する保証はない。

新protocol/extractor/channel名 `ATOM.PARA_END/length_width_energy` と新model-setを作り、v0.3 `length_width` のscoreに混ぜない。既存と同じ外側20葉の5分割で、prior-train8/null-calibration8/test4を分離し、null8の真正4面leave-one-face-outから新距離を校正する。CALは引き続き両側typicalityとする。PROTO fallback、疑似面を使ったfit、旧CALモデルの流用はしない。他channel/atom、集約への組込みも新protocol内で明示し、現行J24.CALを自動置換しない。

機構fixtureは自己距離0、分布順序不変、複合glyph、空観測NA、尺度変更の効果、joint依存だけ異なる分布、非交差でも幾何的距離が異なる2分布を含める。真正nullのcoverage・離散rank・両端score・raw距離同点を全例記録する。新予測前に全code/source/model/hashと判定基準を封印する。

## B. 末字/SPACE: 条件付き支持内replayを先に実現性試験する

V1の64枝を延長したり、NO_MATCHを消したり、scoreを見てseedを交換する方法は採らない。次版では外部16葉だけで条件を決める**支持を広げない条件付きproposal**を検討する。通常生成器へは適用しない。

- 入口は同じBASE PF snapshot、同じ20葉の第4面・seed92101。最大64 complete-segment試行を維持し、事前にLW21/terminal21/SPACE22へ割り当てる。near/farは各割当bankから同時に選び、後から割当数を融通しない。
- terminalはBASEの長さ区分・可視幅・物理幅・末字族のfilterを維持する。外部proxyのNLLで並べた、BASEと異なる同幅末字を決定的に各枝へ割り当て、END raw proposalの最終glyph条件として扱う。各親CDFの正の支持内で条件付けし、元の0確率を正にしない。HEAD等の強制条件やm/rareが優先する場合は実現失敗を記録する。
- SPACEはBASEの長さ区分・可視幅・物理幅・末字を維持する。外部proxyだけで前語末字/H1条件を割り当て、同segmentの続行語とEND語の支持内proposalへ条件を渡す。未来のEND判断を先取りして状態を書き換えず、最終segmentが条件を満たしたかで判定する。PLANTや行を跨ぐ前語を作らない。
- 「元確率」「条件付き確率」「条件の支持質量」「条件不成立/zero-mass」「実際のm/rare後の特徴」を記録する。完成したsegmentだけをdonorとし、語末だけの後編集・行の継ぎ合わせ・packing失敗の自動補修はしない。条件付きproposalの正当性は新しい独立監査の対象とする。
- 原版の2候補/LEN1、本体state/RNG/rare/route/要求採番から隔離する。selectorへ真正target語値・judge score・CAL・keyを渡さない。新namespaceは `PF_CAPABILITY_CONDITIONAL_REPLAY_V2_20261105`。失敗は `CONDITION_NOT_REALIZED_WITHIN_64` 等で全分母に残す。

これは実現性を保証した実装ではない。既存親samplerの候補bank、強制HEAD、m/rare、segment再試行との結合を先に設計・unit・小規模監査し、実際に元の支持内であることを検証する。制約を満たせない条件を「支持上不可能」と断定しない。単にterminal/SPACE filterを緩めた対照を純粋な局所操作として扱うこともしない。

## C. 段階と事前判定

1. 新距離の機構検証とgenuine-only fit/null校正を完了し、新審判を独立に固定する。新donor方式も通常BASE無影響・全枝再生・原支持/packing・commit状態を独立確認する。
2. structurally eligible cohortを18/18/17葉として予測前に固定し、donor/選択を封印後に真正面対改変面を作る。操作実現は真正面との対象feature count差で測り、proxy NLL差と区別する。全予定例、未変更、NA、他channel変化を保存する。
3. **全対象channelの操作実現80%以上を予測前に確認する。** 不足時は `MANIPULATION_NOT_REALIZED` としてこの版を止め、予測を開始しない。結果を見て枝数・seed・subset・filterを変更しない。
4. 新版の106組相当の全予測を保存してからscoreする。far3channelそれぞれで独立葉10以上、比較可能性80%以上、操作80%以上、expected accuracy60%以上、葉cluster bootstrap10,000回の95%下限>50%を要求する。同点1/2、nearは診断だけ。新channelを含む具体的required setは新model封印時までに固定し、その後は変更しない。

同じ開発20葉の再利用であり、新seed/donor/予測を独立真正面の追加と数えない。結果が良くても汎化・同等性・正式採用を自動主張しない。本比較の記述的実行方針とは分離し、能力未確認という事実を保持する。現段階の成果はこの設計と機械可読仕様だけで、旧結果を再計算して合格へ変える作業は行っていない。
