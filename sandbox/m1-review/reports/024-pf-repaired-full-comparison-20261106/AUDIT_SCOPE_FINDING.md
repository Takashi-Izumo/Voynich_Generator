# P1: split scopeの監査式が原版と異なる

**末字commit/CLI修正の独立確認023はPASSのまま。本比較の全800面も生成に成功したが、製品の全件監査は採点前にFAILした。** 原版に正しいtraceを拒否し、誤った補正のtraceを受理する監査不具合を再現した。実装側へ修正を依頼する。

## 原因と範囲

エラーは `Wrong gate trace schema or split scope`。schemaは正しいv2で、問題は [policy_audit.py](../../../../experiments/pf_generation/policy_audit.py#L158) の `row['split_end'] == (row['segment_id'] > 0)` という簡略化である。これは今回の末字修正より前から存在した式。

凍結原版と生成側runtimeは、**`nsegments > 1 and segment_id == nsegments - 1 and boundary_type == 'LINE_END'`** を用いる。実データD:4 / f29v.9には次のscheduleがある。

| segment_id | nsegments | boundary | 原版のsplit_end | 現行監査が要求する値 |
|---:|---:|---|---|---|
| 0 | 2 | PLANT | false | false |
| 2 | 2 | LINE_END | **false** | **true** |

番号は`0,2`と欠番を持つ。原版の値を監査が`segment_id>0`へ置き換えてはいけない。生成・traceはこのscheduleに対して原版どおりfalseであり、PLANT前でいったん切る原版の挙動や入力を変更する必要はない。

両候補群のD:4全10seed、計20ケース・202 gate行がこの不一致に該当する。[GATE_SPLIT_DIAGNOSTICS.json](GATE_SPLIT_DIAGNOSTICS.json)、[SPLIT_SCHEDULE.json](SPLIT_SCHEDULE.json)参照。標準smokeのA:2/A:3/G:1では、このschedule形状を通っていなかった。

## 誤受理も実証

D:4/91701の両候補群をそれぞれ別rootへコピーし、該当gateの`split_end`をtrue、`engine_probability`を余分な0.8 gainに合わせて偽造した。生成語・request・state・候補・乱数等の19ファイルは一切変更しない。現行のcase監査APIは、正しい元ケースを拒否する一方、この誤ったtraceを受理した。

これはcase単位の再現であり、全件の公式PASSやAUDIT sealは作っていない。[SPLIT_FALSE_ACCEPT.json](SPLIT_FALSE_ACCEPT.json)、[再現コード](probe_split_false_accept.py)参照。

## 修正依頼

1. 凍結source/inputに結合したcanonical scheduleをpage/locus/segment_idで引き、原版のnsegments/boundary条件を独立に導く。trace自身のフラグだけを信用せず、未知のkey、型違い、不一致を拒否する。
2. 0.8 gain適用後の確率も、そのcanonical条件で検算する。生成側を誤った監査式へ合わせたり、segment番号や原版のPLANT処理を変更したりしない。
3. D:4の欠番、通常の連続split、非split、PLANT境界を実scheduleから確認する。wrong flagと、それに合わせて確率も偽造したデータを拒否する負例を追加する。R1/R2・末字・元2候補/LEN1・source/入力/生成物の保護を維持する。
4. 生成源の版と監査器の版を分けて封印できる互換検証を検討する。監査のみの修正で生成物の旧provenanceを新hashへ書き換えず、承認した監査差分と元の生成plan/sourceを明示して、この800面を検証できる形が望ましい。生成法則・本体・入力を変えた場合は新sourceで再生成する。

## 今回の独立補助監査

生成物と製品コードを保存したまま、監査コードのこの判定式だけを、凍結scheduleから得る原版条件へ差し替えたprivateな検証器を用いた。flag型もboolを要求し、他の監査条件はそのまま。全600 arm-caseとBASE対REFERENCE全200組の意味出力・全state・実main RNGがPASSした。R1/R2/末字の27負例と上記2偽造を、補助検証器でもすべて拒否した。

補助確認書は [INDEPENDENT_AUDIT_REVIEW.json](INDEPENDENT_AUDIT_REVIEW.json)。元の [公式監査FAIL](OFFICIAL_AUDIT_FAILURE.json)を保存し、製品のAUDIT sealは発行しない。既存の本比較指示を完了するため、この別の確認記録に基づく記述比較を、予測前に [AUXILIARY_EXECUTION.json](AUXILIARY_EXECUTION.json) と [追加方針](AUXILIARY_PROTOCOL.md) へ登録する。審判・モデル・指標・全600例・閾値は変更せず、審判能力の未確認と採用保留も維持する。
