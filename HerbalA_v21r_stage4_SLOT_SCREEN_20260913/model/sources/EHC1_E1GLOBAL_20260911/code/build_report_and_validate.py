"""Report fixed results; verify frozen inputs/code. Never tune or regenerate."""
from experiment_env import *
from entry_global_only import CANDIDATE
import json,hashlib,shutil

def main():
    plan=json.loads((ROOT/'PLAN_FROZEN_BEFORE_GENERATION.json').read_text())
    seal=json.loads((ROOT/'outputs/GENERATION_SEALED_ALL.json').read_text())
    jc=json.loads((ROOT/'outputs/judged/JUDGE_COMPLETE.json').read_text())
    teacher=json.loads((ROOT/'outputs/teacher/AUDIT.json').read_text())
    ma=pd.read_csv(ROOT/'outputs/MECHANICAL_foldALL.csv')
    tables=json.loads((ROOT/'outputs/TABLE_AUDIT_foldALL.json').read_text())
    identity=pd.read_csv(ROOT/'outputs/IDENTITY_foldALL.csv')
    old=json.loads((ROOT/'INPUT_FILES_SHA256.json').read_text())
    changed=[n for n,h in old.items() if not (ROOT/n).exists() or e.file_hash(ROOT/n)!=h]
    code=json.loads((ROOT/'CODE_FROZEN_BEFORE_JUDGING.json').read_text())
    codechanged=[n for n,h in code.items() if e.file_hash(ROOT/'code'/n)!=h]
    assert not changed and not codechanged
    for fn,h in seal['hashes'].items(): assert e.file_hash(ROOT/fn)==h
    assert len(ma)==300 and ma.packing_exact.all() and ma.segment_retries.sum()==0
    for k in ('support_violations','terminal_mismatches','plant_false_heads','invalid_rows'):
        assert ma[k].fillna(0).sum()==0,k
    assert ma.max_end_error.fillna(0).max()==0
    assert len(identity)==20 and identity.adapter_off_identical.all()
    audit=dict(implementation_change_only='E1.bridge/E1.joints use external-only rather than external+known3',
               frozen_input_files_checked=len(old),frozen_input_changes=changed,computational_code_changes_after_freeze=codechanged,
               table_audit_bifolia=len(tables),H2_H3_HEAD_local_checks=sum(t['explicit_nonentry_gain_checks'] for t in tables),
               nonentry_tables_exact=all(t['other_tables_exact'] for t in tables),external_E1_exact=all(t['external_bridge_exact'] for t in tables),
               known3_substitution_E1_invariant=all(t['known3_substitution_entry_invariant'] for t in tables),
               adapter_off_identity_pages=len(identity),original_EHC1_reproduction_pages=len(identity),identity_replay_generations=2*len(identity),
               fresh_performance_pages=len(ma),fresh_performance_tokens=int(ma.tokens.sum()),packing_segments=int(ma.packing_segments.sum()),
               exact_packing=True,segment_retries=0,support_violations=0,terminal_mismatches=0,
               local_END_max_error=float(ma.max_end_error.fillna(0).max()),normalization_max_error=float(ma.max_normalization_error.fillna(0).max()),
               numerical_judges=20,judge_scores=len(pd.read_csv(ROOT/'outputs/judged/scores_by_leaf_run.csv')),
               old_judge_scores_reproduced=jc['old_scores_checked'],old_judge_maxerror=jc['old_score_maxerror'],
               teacher_audit=teacher,independent_llm_judge_calls=0,coefficient_search=False,second_intervention=False,
               inherited_rare_provenance='UNVERIFIED',original_archives_changed=False,
               audit_helper_initial_tuple_list_mismatch='Fixed by canonical JSON comparison; generated words and RNG already matched; no model change')
    if (ROOT/'PORTABILITY_AUDIT.json').exists():
        audit['portability']=json.loads((ROOT/'PORTABILITY_AUDIT.json').read_text());assert audit['portability']['passed']
    e.write(ROOT/'VALIDATION.json',audit)
    status=dict(version='RMW1-BTI2-EHC1-E1GLOBAL',arm=CANDIDATE,status='JUDGED_NOT_PROMOTED',
                champion='RMW1-BTI2',EHC1_reference='E12_VH',only_step_1_executed=True,
                implementation_complete=True,judge_scores_run=True,target_used_to_fit=False,
                entry_leaf_delta=0,entry_external_strength=1,H2_known3=True,H1V_known3=True,H3_known3=True,
                route_and_bt_known3=True,fit_or_tuning_after_judging=False,performance_runs=plan['runs'],
                comparison='300 newly generated pages; all arms use the same 5 run IDs, 20 bifolia',
                reason='H1 forcing improves and target TH1 JSD retains improvement over BTI2, but SPACE judge regresses vs E12_VH and ng/bigram regression warnings remain',
                inference_limit='historical 20 targets; no new independent manuscript sample',inherited_rare_provenance='UNVERIFIED')
    e.write(ROOT/'MODEL_STATUS.json',status)
    f=pd.read_csv(ROOT/'FINAL_COMPARISON.csv')
    scores=pd.read_csv(ROOT/'outputs/judged/judge_summary.csv')
    metrics=pd.read_csv(ROOT/'outputs/judged/metric_summary.csv')
    tf=pd.read_csv(ROOT/'outputs/teacher/summary.csv')
    bd=pd.read_csv(ROOT/'outputs/judged/boundary_JSD_summary.csv')
    main=f[f.judge.isin(['SPACE_RAW','SPACE_T_H1','H2_RAW','HEAD_shape','HEAD_vertical','glyph_depth','route56','bT_leaf_excess','ng','bigram','trigram','combined'])]
    metric=metrics.pivot(index='metric',columns='arm',values='MAE')
    metric=metric.reindex(['types','hapax','tokens','mean_len','mean_width','F2','F3_5','F6_10','F11p'])
    report='''# EHC1–E1GLOBAL：E1のknown3差分だけOFFにした実装・審判

2026-09-11 / **JUDGED_NOT_PROMOTED**

## 結論

①を実装し、審判まで実施した。H1の局所forcing lossは想定どおり明瞭に改善した。一方、完成頁のSPACE_RAWと従来SPACE審判では、現EHC1/E12_VHより絶対残差が増えた。したがって「known3差分を全部OFFにすれば総合的に直る」という案は採用しない。

ただし全失敗ではない。実測target頁のT–H1 jointへのJSDはBTI2より6.17%改善し、旧EHC1との差は小さい点推定だった。H2出力残差も旧EHC1より21.66%改善方向。H1 forcingと、未知頁に似た分布を生成することと、known3参照の審判は別目的である。単純な一軸の「良い／悪い」に還元しない。

正式性能基準はBTI2のまま。E12_VHも維持。E1GLOBALは比較可能な診断枝として凍結した。②の共有化・③H2混合・④頁状態は実装していない。

## 1. 変更を一つに限定

`GlobalEntryTables`は凍結`CorrectionTables`を継承し、既存と同じexternal16 + known3からE2/H1V/H3を構築する。その後、E1の`bridge`と、その説明用`joints`だけを、known3 countが空の同じ凍結コンストラクタで作ったexternal-only値へ置く。

- E1の共通作用・強さ1・clip ±2・board/phase・平滑化は不変。
- E2=1、通常HEAD H1V=.5、通常HEAD H3=.5は旧E12_VHのまま。
- H2/H3/HEADのknown3 countを消していない。
- route/bTのknown3、active抽選、係数、K、same-length/same-width、STOP、quad、LEN1、稀字、packing、boundary B0は不変。
- coreは凍結18葉版、新規E1共通表はouter保留4葉を除いたcomplete16葉。
- A-onlyとは対象葉を含めた全85頁fitではない。

変更表以外の学習配列は20/20葉で完全一致。同一局所入力におけるH2/H3/HEAD計算9,060比較も一致した。known3を半分へ置き換えても新E1表は不変である。

## 2. 実行条件

**BTI2 / E12_VH / E12_VH_E1GLOBAL × 20葉 × 5新seed = 300生成頁**。

runは91151–91155。参照パッケージ内の生成・予約manifestに重複がないことを実行前に確認した。候補がユーザー指定の1本なので探索3seed→候補選別は行わず、最初から5seedで全3条件を比較することを固定した。計画は`PLAN_FROZEN_BEFORE_GENERATION.json`。

全5seedを結果にかかわらず完走し、best-of-N、係数調整、途中の成績による停止はない。旧seedの得点と新seedの得点を一つの比較表へ混ぜていない。生成器用のtarget情報は従来と同じ許可layoutだけ。target本文は補正表へ入らない。

独立単位は20 bifolia。各runで実測score−生成scoreの絶対値を取り、その後runを葉内で平均する。葉単位の両側sign-flipと10,000回cluster bootstrapを用いた。主比較は新候補対E12_VH、BTI2は別の基準比較。主群はSPACE_RAW＋H2_RAW。両参照をまとめた4比較Holmも併記した。

これは数値審判20種で、独立LLMの自由判定は0回。同じ歴史的20実測targetを用いており、新しい独立資料を100頁得たわけではない。

## 3. H1 forcingは改善、H2行は完全不変

実測80面全保留回転の同じ10,661事象（H1_SPACE 4,790、H2 5,871）で、実装した確率行を再計算した。これは新しい実資料による検証ではなく、今回の実装が先のA-only診断を再現することの確認である。実測slot/終了状態を条件とするnon-END予測であり、最終語・停止・packingの尤度ではない。

| 種類 | BTI2 | 旧E12_VH | E1葉差OFF |
|---|---:|---:|---:|
| H1_SPACE loss (bit/字) | 3.390764 | 3.473450 | 3.361006 |
| H2 loss (bit/字) | 2.194609 | 2.249106 | 2.249106 |

H1は旧EHC1比0.112444 bit改善、18/20葉、2比較Holm p=.0000153。BTI2比では0.029758 bit改善方向だがp=.1764で確実ではない。H2は全5,871事象で確率行が旧EHC1と完全一致し、親より悪い状態もそのまま残る。したがって完成頁H2の変化はH2表を直した効果ではなく、H1とそれ以降の生成経路が変わった波及である。

support外行は1e-15のloss floorを明示した。共通supportだけの別表も保存。旧DIAG1のnative/EHC確率との10,661×2照合も1e-12以内で一致した。

## 4. 主審判：現EHC1に対するSPACE利得は後退

負の変化率が絶対残差の減少。以下はすべて新しい同じ5seed。

'''+main.to_markdown(index=False,floatfmt='.6f')+'''

旧EHC1→葉差OFFのSPACE_RAWは0.054821→0.065293、+19.10%。4/5seedで悪化方向、主2比較Holm p=.2949で、平均悪化を確定したとは言えない。従来SPACEは0.047832→0.073265、+53.17%、5/5seedで悪化方向。未補正p=.01067だが、20項目全体の補正ではp=.2134。単独pだけで全体改善／悪化を確定しない。

真正選択回数は、通常SPACEがBTI2 85/100、旧EHC1 37/100、葉差OFF 85/100。従来SPACEは93→52→87/100。完成頁に残る一方向のSPACE偏りは葉集約・20指標補正でも有意であり、新版はSPACE審判を騙せていない。

一方、BTI2との比較では通常SPACE絶対残差は14.99%縮小し、主2比較Holm p=.00470。H2は36.50%縮小、同p=.01744。両参照の主4比較をまとめるとp=.00939/.05232となる。これは『EHC1を超えた』ことではない。

H2は旧EHC1比でも21.66%改善し、5/5seedで改善方向。ただし葉単位の主2補正p=.2049で未確定。H2条件付き表そのものは変えていない点を重視する。

## 5. 対象頁そのものへの距離は、改善の大部分が残る

通常SPACEの原位置確認済み隣接だけを数える。JSDはbase2のdivergence。

| 接続分布 | BTI2 | 旧EHC1 | E1葉差OFF |
|---|---:|---:|---:|
| target TH1 JSD | .441301 | .410218 | .414063 |
| known3 TH1 JSD | .362503 | .294742 | .326552 |
| 同境界数target TH1 JSD | .453209 | .421218 | .424889 |

葉差OFFはBTI2比target JSDで6.17%改善、6比較Holm p=.01521。一方、旧EHC1比では+0.94%の小幅悪化でp=.6472。これは同等性の証明ではないが、点推定では実測距離改善の大部分が残る。同じ境界数へ32回部分抽出する感度分析でも同方向だった。

known3への距離は旧EHC1より10.79%遠ざかる。これはE1の葉別作用を消す介入と整合的。known3から遠ざかることを、そのまま特定targetから遠ざかった量と同一視しない。

共通参照jointのlog適合を分解すると、associationの符号付き残差はBTI2 +.547090、旧EHC1 −.514152、新版 −.253863。絶対残差は.581096/.535681/.346964だった。過剰適合方向への振れはこの説明用scoreでは縮む。TF-IDF型のSPACE審判とは異なる関数なので、両者の符号や率を直接混ぜない。この分解で良くなっても、SPACE_RAW審判の後退を帳消しにしない。

## 6. 一般指標・語彙

今回の5seedのMAE：

'''+metric.to_markdown(floatfmt='.6f')+'''

types/hapaxは旧EHC1から5.38→5.36、6.94→6.90でほぼ横ばい。BTI2の5.77/7.23より平均は良いが、小さい差であり完全再現や有意な優位とはしない。語数MAEは旧EHC1と同じ5.15。平均語長は旧EHC1より少し悪化し、平均幅は少し改善。

一方、BTI2比でng +10.57%、bigram +12.58%が従来の+10%警告を超える。旧EHC1比ではroute56 +14.68%、bT leaf-excess +11.21%、bigram +14.81%、glyph-depth +15.21%、HEAD H1_RAW +16.35%などに警告がある。統計的に確定した悪化とは限らないが、無条件昇格させる成績ではない。旧seedでのEHC1悪化値を今回の新seedへ持ち込んで解釈しない。

語頭／語末の直接の重なりや表共有化、H2混合等は今回追加していない。要求された①だけで判定を止めた。

## 7. 機械監査・凍結

- 性能用300/300頁、5,550/5,550 segmentでexact packing。segment retry=0。
- E1以外の学習表20/20葉で完全一致、H2/H3/HEADの同一局所条件9,060比較一致。
- H2 forcingの全5,871行は旧EHC1と完全一致。
- 旧EHC1 run91011を全20頁再現。adapter OFFも同20頁で全文hash・RNG・route state一致。監査用再生成40頁は性能300頁と別。
- 旧judgeの800得点は最大1.78e-15差で再現。
- 凍結入力8,053ファイルと、採点前に固定した計算コード6ファイルに変更0。未採用・悪化出力も保存。
- 同長同幅、local END、support、最終surface T、boundaryの既存runtime assertは通過。K shortfallは親仕様のまま残し、件数を保存。
- 6頁の別ディレクトリ再現はPORTABILITY_AUDIT.jsonに記録。監査補助コードでPython tupleとJSON listを直接比較した初回の偽不一致はcanonical JSON比較へ直した。語列・RNGは初回から一致し、生成コードやパラメータを修正したものではない。

継承稀字/m/Gパラメータの全来歴は引き続きUNVERIFIED。新規E1のtarget隔離と、既存モデル全経路の来歴証明は別である。

## 8. 判断

**①は部分成功だが、単純OFFを性能後継として採用しない。**

H1予測を不安定にしていた成分を取り除くことはできた。しかし細かなknown3補正は、完成出力の葉的な接続特徴にも貢献していた。『全部必要』『全部不要』のどちらも示していない。外部共通作用を残して不要な細分化だけを縮約する②の動機は残るが、最適な縮約値を今回の両端比較から決めない。

forcingの良さだけでも、known3審判だけでも、実測joint距離だけでも勝者を決めない。今回の版は`JUDGED_NOT_PROMOTED`として固定し、BTI2・旧EHC1を保存する。

## 主要出力

- `FINAL_COMPARISON.csv`: 同じ新5seedの20審判、両参照への対応比較。
- `outputs/judged/candidate_paired_both_references.csv`: 葉単位検定、CI、群補正、主4比較感度。
- `outputs/judged/metric_summary.csv`: 語彙・長さ・幅のMAE。
- `outputs/judged/boundary_JSD_tests.csv`: 通常SPACEの周辺／joint距離、同境界数感度。
- `outputs/teacher/summary.csv`, `paired.csv`, `events.csv.gz`, `probabilities.npz`: 全80面の局所行監査。
- `outputs/generated/`: 全3条件×5seed×20葉のtokenと生成trace。
- `VALIDATION.json`, `IMMUTABILITY_AUDIT.json`, `PORTABILITY_AUDIT.json`: 監査。

出典は同梱凍結EHC1、旧審判、DIAG1のコードと台帳。今回の数値は新規実行出力であり、過去レポートからの推測や外挿ではない。外部web資料・別転写を使用していない。
'''
    (ROOT/'REPORT_JA.md').write_text(report)
    (ROOT/'README_JA.md').write_text('''# EHC1 E1GLOBAL — ①だけの実装・審判

状態: JUDGED_NOT_PROMOTED。正式基準BTI2は変更しない。

## 再実行

完全版ZIPを新しいディレクトリへ展開し、同梱環境に必要なライブラリを用意する。`inputs/RMW1_BTI2_EHC1_20260911/requirements.txt`も参照。

```bash
python -B code/run_generation.py
python -B code/teacher_audit.py
python -B code/judge_experiment.py
python -B code/smoke_relocation.py
python -B code/build_report_and_validate.py
```

生成runnerは既存出力を再利用する。最初から再生成するには別展開先で`outputs/generated`を削除する。旧入力は変更しない。`freeze_plan.py`は今回の固定計画を作った履歴コードであり、再実行のたびにseedや計画を変更する必要はない。

結果版ZIPは`inputs/`を含まない。同名のEHC1・旧審判・DIAG1結果ZIPを`inputs/`へ展開するか、完全版を使う。結果版に完全再現できる全入力があるとは主張しない。

通常SPACEとH2が主指標。1字の予測loss、known3参照の真偽得点、target JSDは別物として読む。すべての出力を保存し、勝つseedだけを選んでいない。文字列が違う版の同じ語番号を同一文脈介入とみなさない。

別展開先試験は同じPython/NumPy/Numba等の環境での試験であり、異なるバージョンでbit-level一致する保証ではない。
''')
    print('REPORT_WRITTEN',audit['fresh_performance_pages'],audit['fresh_performance_tokens'])
if __name__=='__main__':main()
