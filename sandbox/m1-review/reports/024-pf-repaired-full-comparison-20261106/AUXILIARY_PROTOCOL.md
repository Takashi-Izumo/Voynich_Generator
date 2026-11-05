# 独立補助監査経由の記述比較：予測前の追加登録

通常経路は800面の生成後、監査のsplit scope誤判定で停止した。公式監査のFAIL・停止statusと最初の登録は保存する。誤りの詳細と修正依頼は [AUDIT_SCOPE_FINDING.md](AUDIT_SCOPE_FINDING.md)。この追加は、全例を固定審判で比較する既存のユーザー指示を、生成物を破壊せず完了するための別の検証経路である。

## 変更する範囲

- 原版のcanonical scheduleからsplit_endを導く独立検証器を別コードとして封印する。製品の監査コードは変更せず、製品AUDIT sealも作らない。
- 全600ケースとBASE対REFERENCE200組を確認し、元/後の生成manifest・status・全ファイルhashを照合する。R1/R2/末字の27負例と、誤ったsplit補正の2偽造を再度拒否する。
- その確認書と実行コードのhashを800面のgeneration bindingへ結合する。export前と予測前、完了時に再検証する。
- 診断・exportの凍結コードは、privateな別namespaceのコピーで**release guardだけ**をこの独立確認へ接続する。製品moduleは書き換えない。処理本体のsource hashも記録する。固定審判の予測・採点は元のAPIを使う。

## 維持する範囲

生成source43a6895、plan5f0e657b、全800生成面、全600比較、20葉・10seed、known3/layout/mask、法則、外部学習範囲、固定CAL model set61238cf4、主/主要局所、2対比、同点/NA、葉重み、10,000回bootstrap、独立した率・区間の再計算は初回登録どおり。D:4を除外せず、seed・面・モデル・閾値を差し替えない。旧421面も使わない。

全600予測を保存してから採点する。追加登録時点で、今回のexport・予測・採点は存在しない。登録は生成後の構造上の監査誤りを受けたもので、判別成績を見た変更ではない。

## 結果の呼び方

最終結果は **「独立補助監査経由の記述比較」** と明示し、通常の製品監査PASSや正式採用として扱わない。公式FAILと製品修正依頼を併記する。CAPABILITY_NOT_VERIFIEDはそのまま、新審判/新donor設計021は未実装であり、品質改善・同等性・汎化・採用を主張しない。

実行コードは [independent_canonical_audit.py](independent_canonical_audit.py)、[run_auxiliary_comparison.py](run_auxiliary_comparison.py)。生成物・実装・審判・status/request管理ファイルは変更せず、今回の報告と補助検証コードだけを返す。
