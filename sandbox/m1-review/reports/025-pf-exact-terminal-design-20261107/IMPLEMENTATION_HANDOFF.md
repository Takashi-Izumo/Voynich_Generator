# 第二案の実装受け渡し

2026-11-07 日本時間。設計 `PF_EXACT_TERMINAL_V1_20261107`。[正本](DESIGN.md)、[JSON契約](DESIGN_CONTRACT.json)を参照。

**BASEを維持し、第一案を混ぜずにPF個別末字係数だけを比較する。** 独立検証側は本報告を `sandbox/m1-review` へ追記する。製品実装・status/request管理・既存報告の編集は実装側の担当。本報告は本比較の開始記録ではない。

## A. 製品監査の既知不具合を先に修正

- canonical scheduleから `nsegments>1 and segment_id==nsegments-1 and boundary_type=='LINE_END'` を導く。
- D:4/f29v.9、保持ID `[0,2]`、nsegments=2のID2はfalse。正しい原版traceを通し、誤trueだけでなく余分な0.8 gainを合わせた偽造も拒否する。
- contiguous split true・no split・PLANTを回帰確認する。番号の詰替えで回避しない。
- generation sourceとvalidator sourceを別封印し、過去の公式FAILやsource manifestを上書きしない。補助監査を公式PASSへ読み替えない。

返却: 修正commit、対象ファイル/hash、正負fixture結果、原版・審判・既存生成物を変更していないこと。独立検証側が再確認する。

## B. 第二案用の末字能力対照を具体化

- `PF_E_TERMINAL_CONTROL_V1_20261107` を旧対照・新距離案と別namespaceで実装する。
- 真正側の粗いmatching制約だけをdonor chooserへ渡し、個別末字/語・judge scoreは隠す。これは人工対照の構成条件であり、生成器の訓練入力へ渡さない。
- 外部complete16のproxy、同族内target循環、seed92101、完全segment64枝上限、外部rarity/先着IDによるdonor選択を固定する。
- conditional replayの支持・正規化、Map/m/rare/packingとの整合を証明し、全attemptを保存する。成立困難なら設計上の未達として返す。無断の条件緩和・seed探索をしない。
- donor封印後の操作成立15/18葉、channel coverage/能力のgateを使う。NLL順序からCAL順位を作らない。J24全体の能力へ一般化しない。

返却: 実装commit、未採点のcontrol plan/manifest、支持証明・機械検証、割当/母数の集約。生のdonor/snapshot/真正資料はprivate出力先で保持し、Gitへ入れない。能力判定は独立検証側が予測順封印を確認して行う。

## C. score adapterと観測を独立packageへ実装

- `experiments/pf_terminal_score/` を新設し、元SourceRuntime・原版engineの制御を再利用する。
- BASE/REFERENCEは元経路。非恒等群だけPF selector引数を替える。式は `S0 + (lambda-1)*E`、lambda=1またはE=0ならS0直接返却。
- EF/W/WB/WR/interceptと元selector辞書を保存する。全PF score呼出し（LEN1を含む）へ適用する。
- 完成candidate観測とscoreをtyped context/request intervalで一意に結ぶ。ログ用の別乱数や元request辞書への追記はしない。
- LEN1の「初期winner長<=5なら8枝」「族一致」「最初の適格救済は低得点でも採用」「main RNGはarm初期winner」を守る。第一案のruntime/gate/語長lawを読み込まない。
- surface_commit helperだけhash固定で再利用する。新study policyとreceiptを用意し、identityではbypass。全state/実RNGまで観測する。
- 例外時finally復元・同一process lockを実装する。

返却: 実装commit、新study source manifest/plan schema、score/state/candidate trace schema、実際のCLI、unit/拒否fixture結果、原版/審判hash不変確認。

## D. まず独立80面の機構検証

固定A:2/A:3/D:4/G:1、seed91701/91711、4群の通常順/逆順各32面と、seed91701・両E群lambda=1の16面。合計80面。BASE/REFERENCE厳密一致・identity・順序不変・採用state/初期winner RNG・repair・欠番scheduleを監査する。

実装側のPASSだけで本比較へ進めず、検証側が別rootで再現する。失敗はcase全体を残し、seed差替えやtraceの手修正で通さない。

## E. gate成立後に新しい本比較planを封印

Aの製品監査修正、Bの登録対象channel能力、C/Dの機構・拒否検証が揃ってから、20葉×10seed×4群=800新規生成/600審判比較の実行planを作る。主対比はBASE→HALFとBASE→ZERO。第一案との組合せや正式採用は別設計。

今回の受け渡し時点: **設計完了、製品修正未受領、第二案未実装、能力対照未達、本比較未開始。** 途中成果を `sandbox/m1-review` へ返し、独立検証側へcommitとprivate出力先を知らせる。
