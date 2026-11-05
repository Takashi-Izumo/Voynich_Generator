# 依頼018: PF能力対照replayの独立確認

共有sandboxをfetchし、開始HEADを記録してください。今回の実装は `experiments/pf_controls/`、設計は [017](../designs/017-pf-controls-v1/DESIGN.md)、実装manifestとsmokeは [017 implementation](../implementation/017-pf-controls-v1/VALIDATION.md) にあります。原版/M1/審判/pf_generationを変更していません。検証側の[依頼016](../reports/016-controls-and-main-comparison-20261105/IMPLEMENTATION_REQUEST.md)に対応しています。

## 受領済みの前段

報告015の22fileと報告016の15fileを、それぞれmanifestのサイズ・SHA-256で確認しました。R2は独立PASS、R1回帰もPASSであり、その受領をstatusへ反映しました。本比較の準備plan `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17` は新package追加後もload/検証可能です。

## 独立確認してほしい点

1. manifestとsource/input/model/proxy/planの封印。外部16完全葉×4面、新表からtest4葉/target known3全除外、葉等重み、prior0.5・縮約20・空SPACE条件backoff。
2. literal BASEのPF第0候補の入口観測。全state/rare/route/paragraph/main RNG/sampler control/要求採番/immutable fingerprint/known3/layoutの保存。観測あり・なしの全意味出力、全最終state、実main RNGが一致すること。
3. 各generator PFイベント64complete-segment枝。END_ONLYのatom昇格なし。clone/支持/同容量/末字/PLANT・図後BODY・要求番号隔離・親state/RNG/rare/route/control復元・finally復元。
4. selectorへ真正target語値・審判score・keyが入らないこと。near/farの生NLL、3laneのfilter、1e-12/tie順、変更不能/NO_MATCH_WITHIN_64を含む全予定例。seed交換・枝追加・条件緩和なし。
5. 選択封印後に真正原面のFULL PF segment全体を差し替えること。known3/layout/mask/他segment/END_ONLYを保存。真の正解が真正側で、NLL/CALから付けられないこと。exportの再構成監査とキー漏洩拒否。
6. 全生成recordの新規再生監査。提示済みPASSやchecksumだけに依存せず、欠落・重複・内側要求context誤結合・型違い・receipt更新・main RNG改変などを拒否し、失敗後にsealを消すこと。負例scriptはcopyだけを改変し、展開入力を編集しません。
7. 全予測保存後の採点、固定model hash照合、再fit/fallbackなし。far3channelの新基準、near診断、NA/変更不能を含む固定分母、off-target全channel変化、同点1/2・葉cluster bootstrap。操作成立率は封印選択後の真正面対改変面の対象feature count差であり、選別feedbackに使いません。

fresh rootのsmoke、export/verify、負例、unitのCLIは [README](../../../experiments/pf_controls/README.md)。機構smokeから能力PASSは主張していません。smoke planを `evaluate` に渡すと拒否し、全20葉の `--kind controls` planだけを能力判定に用います。

smokeでは末字のfar操作成立は1/3面、SPACE farは2/3面で、未変更も全予定例に残しています。SPACE nearはtext変更2面に対し対象feature変更0面でした。生成BASEに対するNLL差を、真正面に対する操作成立の代わりにしないでください。全cohortでも80%未満なら `MANIPULATION_NOT_REALIZED` として記録し、審判能力不足や支持上の不可能に読み替えたり、条件を緩めて埋めたりしません。

## 全対照と本比較

独立機構確認後、検証側で新rootに `plan --bifolia all --kind controls` を作り、generate→audit→export→verify-export→evaluateを実行してください。実装側は全対照の生成/予測/採点と800面を先行していません。共有したfull control planはfit/構造cohortの準備のみです。

`evaluate` の `CAPABILITY_RESULTS.json` は結果であり、独立確認書を自動発行しません。検証側は3channelのfarと操作・比較可能性を確認し、報告016の契約に沿う `CAPABILITY_REVIEW.json` を確定した場合だけ、準備済みorchestratorを起動してください。失敗時は有利なdonor/seed/部分集合への変更で埋めず、そのまま報告してください。

返却は新しい `reports/<unique-id>/` だけをcommit/pushし、開始commit、実行コマンド、全予定/実行/拒否数、時間・RSS、manifestを含めてください。生生成物・真正語・snapshot・正解キー・archiveはGitへ追加せず、既存報告/実装/status/requestも変更しません。main merge・正式採用・個別末字/SPACE本体studyは今回に含めません。
