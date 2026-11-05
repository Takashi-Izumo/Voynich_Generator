# 実装側への依頼: PF審判能力対照

ユーザーの「対照・本比較」に基づく次工程。R1/R2は[報告015](../015-pf-r2-context-recheck-20261105/REVIEW.md)で独立PASS済み。まずそのmanifestと報告を受領し、実装側が管理するstatusを更新してほしい。この依頼は検証側のreports内へ置き、既存requests/statusを直接変更していない。

## 担当と成果物

実装側は `experiments/pf_controls/` 等の独立packageに、PF入口snapshot・支持内replay・対照export・監査を実装し、設計/機械可読plan、code manifest、機構smoke、独立検証依頼を新しい一意のdirectoryで返す。検証側が独立確認・全対照の生成/予測/採点・800面本比較を実行する。全対照の予測・採点と800面を実装側で先行開始しない。

原版・既存M1・審判・現在の `pf_generation` の生成法則を維持する。可能な限り既存fileを変更せず独立sidecarで計測し、全sourceとcontrol planを封印する。生成sourceの変更が必要なら変更範囲を明示し、新しい検証・本比較planの再封印が必要になる。

## 必須の実装契約

1. **BASEとsnapshot**: 固定20葉の第4面、control seed92101を使う。原版BASEのPF入口で、全GenerationState、rare/route/paragraph状態、main RNG、samplerの意味状態と制御、legacy要求採番、immutable table fingerprint、fold・known3・segment/layoutを記録する。観測したBASEと普通のBASEの全意味出力・state・実main RNGを一致させる。
2. **独立replay**: namespace `PF_CAPABILITY_REPLAY_20261105_V1` とイベントID/枝番号から、各PFイベント最大64のcomplete-segment枝を再生する。branch cloneとmain/rare/requestの隔離、結合復元を検査する。追加枝を本体の2候補/LEN1へ混ぜない。再生後にBASE側のstate・RNG・採番が変わらないことを確認する。元sampler/engine bindingはfinallyで復元し、展開入力fileを編集しない。
3. **新proxy表**: 外部16完全葉だけ、全4面のstrict資料から作る。outer test4葉とtarget known3を新表のfitから除外。長さ3区分×可視幅4区分のjoint、末字22glyph、前語末字22glyph→H1の条件付き表を用い、通常LF/BODY priorへ縮約20、prior mass0.5。葉等重み、空条件のbackoffと表のhashを記録する。語長・可視幅は凍結tokenizer/WIDTHを使い、生成器の記録物理幅と区別する。
4. **選択**: sourceは完成したBASE生成anchorとreplay候補だけ。真正targetの語値とtest judge scoreをselectorへ渡さない。各表の生NLLがBASEより小さいnear、大きいfarを決定的に選ぶ。同値差1e-12、候補ID順でtie-breakする。見つからなければ `NO_MATCH_WITHIN_64`。64回に候補がないことを支持上の不可能とは呼ばず、条件緩和・追加枝・seed交換で埋めない。
5. **laneの制約**: length/widthはjoint操作。terminal laneはBASE anchorの長さ区分・可視幅・物理幅・末字族を固定する。SPACE laneはBASE anchorの長さ区分・可視幅・物理幅・末字を固定し、segment内に前語がある候補を使う。PLANTや行を跨ぐ接続を作らない。他特徴も動くことを全例で記録する。
6. **独立した正解**: donor選択を封印してから、真正原面のFULL PF segmentを選択donorで置いた改変面を作る。A/Bは真正原面と改変面で、known3/layout/quality maskは同じ。語数が変わっても部分語の補綴や不完全行の継ぎ合わせをしない。END_ONLYをatomへ昇格させない。対照keyは真正原面の側であり、NLL/CALの大小から付けない。
7. **観測可能性**: 原面の対象イベント有無だけでfamily別eligible cohortを予測前に固定する。第4面20面ではFULL PF 18葉29末尾、SPACEあり17葉27末尾を読み取り確認済み。selectorへは語値を渡さない。全予定対照、変更不能、NA、対象特徴の操作成立率を保存し、結果後の有利な部分集合に絞らない。far/nearは各family・eligible target面ごとに1variantを作る。
8. **予測/採点の分離**: 全donor bank、選択、case/key/割当のhashを封印する。predictorへsnapshot・NLL・処置label・key・生成logを渡さず、全予測保存後にscoreする。凍結model-setを照合し、再fit・PROTO fallbackを行わない。
9. **新しい能力判定**: 詳細は [CONTROL_CONTRACT.json](CONTROL_CONTRACT.json)。farの真正原面対改変面を3つの対象CAL channelで個別に判定する。nearは診断で、near/base/farのCAL順位や旧75%基準を使わない。10葉、80%比較可能性/操作成立、60%expected accuracy、10,000回の葉cluster bootstrap95%下限>50%を事前基準とし、3channelすべて通過で本比較へ進む。同点1/2。真正面・donorの反復を独立標本に数えない。
10. **監査と負例**: source/input/fold/snapshot/receipt/record/候補contextを結合する。欠落・重複・誤結合・checksum更新・古いPASS・失敗後seal・main RNG/rare/route汚染・target混入・key漏洩を拒否する。R1/R2を再導入しない。support/packing/末字/PLANTの違反は0、失敗を隠さず停止する。

## 返してほしいもの

- plan schemaと3familyの対象channel、コホート、分母、NLL、filter/tie、A/B割当、判定式が読める設計とJSON。
- 完全なreplay/export/audit code、依存・source/input/model hashのmanifest。
- A:2/A:3/G:1、seed92101でBASE観測の無影響、replayの支持/容量、snapshot・rare/state/RNG復元、選択の決定性、失敗/負例を確認した機構smoke。
- 未成立/未実装の箇所、予定64枝と実生成数、時間・最大RSS。能力PASSやモデル改善をsmokeから主張しない。
- 検証側向けの新しい独立確認依頼と、全対照を新規rootで再現できるCLI。

この契約で成立しない設計上の点があれば、全対照予測前に具体的な修正版として返す。予測・採点後に都合よく条件を調整しない。本比較planの生成hashは `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17`。検証側の開始用スクリプトは準備済みで、対照の独立確認後に使う。
