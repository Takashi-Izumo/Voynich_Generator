# PF能力対照: 実装設計 v1

依頼016を実装する。原版・M1・審判・第一案の生成法則を変更せず、`experiments/pf_controls/` に独立したsidecarを追加する。固定seed92101、第4面、namespace `PF_CAPABILITY_REPLAY_20261105_V1`。本比較の準備plan `262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17` を維持する。

## 入口と再生

原版 `generate_bif` のPF第0候補が最初に `complete_segment` へ渡す入口を観測する。第0候補のRNGはmain RNGの完全cloneであり、PF前の全GenerationState、rare/route/paragraph、samplerの全可変controlと意味状態、要求採番、immutable table fingerprint、fold/known3、元segment/layoutをJSONへ保存する。実行可能なpickleを読み込まない。保存snapshotの再生は、封印された元入力からBASE軌道を再走し、その入口を再構築する。

各PFイベントで64枝を固定生成する。END_ONLYもgenerator PFであれば再生するが、FULL atom観測へは昇格させない。各枝は元のcomplete-segment関数と支持を使い、同じ入口のstateとsampler可変controlを独立cloneする。side RNGの鍵はnamespace、seed、bif、page、locus、segment、event、branch、入口RNG状態。要求採番は入口から各clone内で進め、通常生成の採番へ戻さない。共有するparent sampler/確率表は意味上read-onlyで、内容fingerprintを前後比較する。row cacheと全要求/audit counter/logはprivateである。

64枝終了時にBASE入口の全state・実RNG・sampler control/採番が変わらないことを検査する。その後、原版のPF2候補/LEN1とmain RNG継続をそのまま走らせる。観測BASEと観測なしの原版BASEの全意味record、最終全state、実main RNGを一致させる。例外時もmodule bindingをfinallyで復元する。

sampler controlにはインスタンス属性に加え、MROを通した実効クラス設定32項目を含める。RUN_SEED/TARGET_BIF、BODY補正、W2、F1LF/Stage3D法則・scope、paragraph-H1 baselineの内容も保存する。configure前の各クラスのdata属性をdeepcopyし、finallyでは新しいoverrideを消して値を復元する。未知のbaseline型や内容は暗黙に省略せず拒否する。

## proxy、filterと選択

各outer foldで外部16完全葉の4面を使い、test4葉全体とtarget known3を新しい表から除外する。strictなPF末尾、通常の非最終LF末尾、segment内interior BODY遷移だけを使用する。各集計で葉等重みをevent数へ再尺度化する。

| family / channel | proxy | 追加filter |
|---|---|---|
| length_width / ATOM.PARA_END/length_width | 長さ3区分×可視幅4区分の12joint | complete segment / 同容量 / 支持内 |
| terminal / ATOM.PARA_END/terminal | 末字22glyph | BASEの長さ区分・可視幅・物理幅・末字族を固定 |
| space_T_H1 / ATOM.PARA_END/space_T_H1 | 前語末字22→当語H1の条件付き22 | BASEの長さ区分・可視幅・物理幅・末字を固定、segment内前語あり |

長さ区分は <=3, 4–6, >=7、可視幅区分は <=3, 4–6, 7–9, >=10。凍結glyph tokenizer/WIDTHで可視量を計算し、記録物理幅と分ける。通常priorはmass0.5の一様平滑化、PFはmass20でpriorへ縮約。SPACEの空BODY条件はBODY周辺H1へbackoffする。条件別massと空条件・全count・表hashをplanに記録する。

selector APIは生成BASE anchor、64枝、外部proxyだけを受け取る。真正target語値、judge score、CAL、キーを渡さない。NLLは `-log(probability)`。BASEより1e-12以上小さい候補の最小をnear、大きい候補の最大をfarとし、1e-12以内の同値は枝ID順。該当なしは `NO_MATCH_WITHIN_64`。探索の延長、seed交換、filter緩和はしない。

## 正解、分母と能力判定

原面の構造とFULL/前語有無だけからfamily別eligible cohortを固定する。20葉ではFULL PF18葉29末尾、SPACE17葉27末尾。donor bankと全選択IDを封印し、fresh auditを通した後だけ、真正原面のFULL PF segment全体を選択donorへ差し替える。部分語や他segmentとの継ぎ合わせはしない。1family×1方向×1eligible葉につき1variantを作り、未変更も含める。known3・layout・maskは同一である。

真正面側をA/Bの正解とする。配置はplan/family/方向/葉を含む匿名case IDのSHA-256末尾bitで固定し、語値・NLL・CALから決めない。予測へ渡すのは凍結schemaのcaseだけ。選択・キー・割当・入力のhashを照合し、全群の予測保存後に初めて採点する。固定CAL hashを確認し、再fit・PROTO fallbackしない。

操作成立は、選択後の真正面と改変面で対象channelの経験feature countが異なること。これはselectorへのfeedbackに使わず、全例のoff-target channel変化と併記する。比較可能性・操作成立率の分母は全構造eligible面。NAと変更不能も保存する。farに対し3channelそれぞれで、比較可能葉10以上・比較可能面80%以上・操作成立80%以上・葉等重みexpected accuracy60%以上・葉cluster bootstrap10,000回の95%下限>50%をすべて要求する。同点は1/2、NAはaccuracyから除外しcoverage分母に残す。同じ真正面/donorを独立標本として増やさない。

操作不成立は `MANIPULATION_NOT_REALIZED`、能力/比較可能性不足は `INSUFFICIENT_CAPABILITY`。nearは診断でありCAL順位を要求しない。CALは真正nullの両側typicalityで、proxy NLLの順位をCALの正解にしない。3つのfar channelすべてPASSが必要。実装は結果JSONのみを作り、検証側の独立確認書や本比較の起動を代行しない。

## 監査

source/input/model/planと全生成fileを結合し、イベント・枝・要求の欠落/重複・型付きcontext・snapshot receipt・選択を検査する。その上で元入力から全BASE軌道と64枝を再生成し、保存record全体に完全一致させる。入力recordの自己申告hashだけでPASSを出さない。生成物とchecksumの更新は既存PASSを失効させ、失敗した再監査はsealを削除する。exportも元の封印選択から再構成し、真正側・A/B割当・キー漏洩・text/layout/maskの変更を拒否する。

実装smokeはA:2/A:3/G:1のみ。全対照の予測/採点と800面比較は検証側が独立確認後に実行する。smokeから審判能力・モデル改善・正式採用は主張しない。
