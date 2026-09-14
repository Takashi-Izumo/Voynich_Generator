#!/usr/bin/env python3
from pathlib import Path
import json,hashlib
import pandas as pd
import evaluation_common as e
from stage3_env import ROOT

def md_table(df):return df.to_markdown(index=False,floatfmt='.6f')

def main():
 out=ROOT/'outputs';s=pd.read_csv(out/'confirmation/judged/judge_summary.csv');p=pd.read_csv(out/'confirmation/judged/paired_vs_parent.csv');met=pd.read_csv(out/'confirmation/judged/metric_summary.csv');pre=pd.read_csv(out/'multirun/judged/paired_vs_parent.csv');tf=pd.read_csv(out/'screen/teacher_forced_paired.csv');rank=pd.read_csv(out/'screen/selection_ranking.csv')
 final=s.pivot(index='judge',columns='arm',values=['real_wins','mean_abs_margin']);order=e.PRIMARY+e.HEAD+['SPACE_RAW','glyph_depth']+e.MAIN6+['bT_LL','bT_leaf_excess','bT_active','bT_presence_log','length_width','LF_shape','HEAD_H1_RAW'];rows=[]
 for j in order:
  q=p[p.judge.eq(j)].iloc[0];rows.append({'judge':j,'BTI2真正選択/100':int(final.loc[j,('real_wins','BASE')]),'E12_VH真正選択/100':int(final.loc[j,('real_wins','E12_VH')]),'BTI2絶対残差':q.base_abs,'E12_VH絶対残差':q.new_abs,'変化%':q.change_pct,'改善葉/20':int(q.leaves_improved)})
 main=pd.DataFrame(rows);main.to_csv(ROOT/'FINAL_COMPARISON.csv',index=False)
 mm=met.pivot(index='metric',columns='arm',values='MAE').reset_index();mm['差']=mm.E12_VH-mm.BASE
 audit=[]
 for stage in ['multirun','confirmation']:
  x=json.loads((out/stage/'generated/GENERATION_SEALED.json').read_text());audit.append({k:x[k] for k in ['pages','segments','packing_pass','segment_retries','runs']})
 status=dict(status='JUDGED_NOT_PROMOTED',version='RMW1-BTI2-EHC1',evaluated_finalist='E12_VH',champion='RMW1-BTI2',judge_scores_run=True,numerical_judges=16,extra_diagnostics=4,independent_LLM_calls=0,generator_settings_changed=False,formal_BTI2_modified=False,stage2_archive_sha256=e.env.EXPECTED,screen_run=91011,multirun_runs=[91021,91022,91023],confirmation_runs=[91031,91032,91033,91034,91035],new_generated_pages=sum(x['pages'] for x in audit),exact_segments=sum(x['segments'] for x in audit),packing_pass=all(x['packing_pass'] for x in audit),segment_retries=sum(x['segment_retries'] for x in audit),independent_bifolium_clusters=20,inherited_rare_provenance='UNVERIFIED',promoted=False,reasons=['SPACE_T_H1 improves reproducibly, but raw SPACE improvement is smaller and not decisive','H2 improvement is directionally stable, but two-sided uncertainty crosses zero','route56 and bT leaf-excess exceed preset +10% residual warning in confirmation','types/hapax MAE rises modestly','teacher-forced H1/H2 proposal probabilities do not improve'],statistical_scope='same historical twenty fourth surfaces; fresh generator seeds, not novel held-out manuscript pages')
 e.write(ROOT/'MODEL_STATUS.json',status)
 txt=f'''# RMW1-BTI2-EHC1：Stage 3 審判報告

2026-09-11。**SPACEの主審判は改善。ただし正式BTI2への昇格は保留。**

## 1. 結論

凍結済みEHC1を変更せず審判した。有力だった最終比較条件は **E12_VH**（E1=1、E2=1、通常HEAD H1V=.5、HEAD限定H3=.5、LEGACY_SCOPE、B0）。別5seedの確認で、旧SPACE_T_H1の平均絶対残差は32.87%減り、真正選択回数は91/100→55/100になった。主2比較の両側Holm補正はp={p.set_index('judge').loc['SPACE_T_H1','holm_primary_two_sided']:.6f}。

一方、PLANTと不明語跨ぎを除いたSPACE_RAWでは絶対残差改善は11.00%に留まり、葉単位両側p=.500793。route56は+13.22%、bT_leaf_excessは+10.55%と、仕様上の+10%警告を超えた。types/hapaxのMAEも少し増加した。したがって **JUDGED_NOT_PROMOTED** とし、championは元のRMW1-BTI2のまま。

これは全失敗でも完全解決でもない。従来SPACE審判に対する改善は複数seedで持続したが、通常SPACEを正しく再現したこと、一般指標をすべて維持したこと、書記の機構を特定したことは証明していない。

## 2. 実施範囲と手順

1. Stage 2 archiveをSHA-256で確認し、別作業用ディレクトリへ展開。保存済みrun91011・10条件×20葉の200頁を簡易診断へ使用した。
2. 原位置を与えたH1/H2/H3 teacher forcing、SPACE/H2/HEADの簡易適合、types/hapax・語長幅・target n-gram距離でスクリーニング。先に保存した規則により、主介入E12を必須比較対照とし、追加候補としてE12_VHを選択した。
3. **BASE/E12/E12_VH × 20葉 × run91021–91023 = 180生成頁**。共通の16数値審判と4補助診断を適用。
4. E12_VHを係数変更なしで固定し、**BASE/E12_VH × 20葉 × run91031–91035 = 200生成頁**で確認した。3seed結果に回帰警告があったので、この追加確認は昇格ではなく改善と副作用の頑健性を調べる診断として行った。
5. 全実行を保存し、頁のbest-of-N選別や、審判後のparameter変更は行っていない。

新規生成は合計380頁・7,030 segment。全packing PASS、segment retry=0。親とEHC1のコード・parameter等533ファイルをStage 2 archiveと再照合し変更0。旧16審判との点数一致も、3代表foldで誤差0を確認した。さらに同梱ZIPを別展開先へ自動展開し、3代表fold×BASE/E12_VHの6頁を再生成して、全文・乱数・route状態・新規入力hashが一致した。

これらは**20葉の同じ固定第4面**である。380個の独立した実資料でも、未使用の380葉でもない。過去の研究で同じ実測頁を使用しており、新seedの確認は生成変動に対する確認である。

## 3. 最終5seedの全結果

次表は一つの表の中でseedを混ぜず、確認用91031–91035だけを示す。負の変化率が絶対残差の減少。真正選択回数は記述値であり、100独立試行の二項検定を主検定にはしない。

{md_table(main)}

主2指標の片側HolmはSPACE=.007643、H2=.039555。両側HolmはSPACE=.015285、H2=.079109。H2の改善量bootstrap95%区間は約[-.000209,.025183]で0を跨ぐため、H2を確定解決とは呼ばない。

HEAD shapeは約20.49%改善だが、HEAD群3比較の両側Holmでは有意ではない。縦HEADは約10.36%悪化、第3字専用診断は約3.37%改善に留まった。H3を追加するだけでHEAD全体が解けたとは判定しない。

従来16審判の「実測−生成」の葉平均に対する両側sign-flip＋16補正では、E12_VHに有意な方向偏りが残る項目は0。ただし、これを等価性・識別不能の証明とはしない。絶対残差の回帰警告は別に存在する。

## 4. 3seedから5seedで変わったこと

3seedではE12_VHのng/trigram絶対残差が+28.97%/+26.33%だったが、確認5seedでは+5.04%/−4.97%になった。これを「全般的なn-gram崩壊が確認できた」とは読まない。反対に5seedでroute56/bT_leaf_excessが+13.22%/+10.55%になり、こちらが新たな警告として残った。

旧SPACEは3seedで44.94%改善、別5seedで32.87%改善。確認5seedすべてで改善方向だった。H2も確認5seedすべてで改善方向だが、葉間ばらつきがあり、両側検定の確実性はSPACEほど高くない。

## 5. PLANTを除外するとSPACE評価が弱まる

旧 `SPACE_T_H1` はclean物理行内の語を連続して数える。PLANT跨ぎやcleanで失われた位置の影響を完全には排除しない。これは旧審判との互換性のため無変更で残した。

追加の `SPACE_RAW` は実測側で原位置台帳を用い、生成側では同一segmentの実受理語だけを隣接とする。不明語を飛び越さず、PLANTで接続を切る。

確認5seed：旧SPACEは **91/100→55/100、絶対残差−32.87%**。SPACE_RAWは **88/100→42/100、絶対残差−11.00%**。後者は生成側がknown3へ寄りすぎる向きにも動き、符号付きmarginは+.063118→−.020766となった。回数が50を下回ること自体を改善や勝利とは扱わない。

この差から「PLANT跨ぎだけが改善原因」とまでは断定しない。母集団・原位置・roleの定義も異なるためである。しかし、**普通のSPACEだけを見ても同じ程度に直った**とは言えない。

## 6. 語型・hapax・長さ・幅

以下は確認5seedの頁別絶対誤差の平均。token/語型集計は親と同じclean定義、幅・長さは保存生成欄を使用した。

{md_table(mm)}

types 5.35→5.91、hapax 6.48→7.38。増加幅は+0.56/+0.90で、仕様の+1.0/+1.5警告幅以内だが、改善ではない。平均語長MAEは+.02713、平均幅MAEは+.04105。局所END保存と全体出力不変を混同してはいけない。

頻度帯F2、F3–5、F6–10等には改善方向もある。全帯が一方向に悪くなったわけではない。詳細はmetric_summary.csvとmetric_paired.csvに保存した。

## 7. n-gramの「悪化」の意味

主審判のng/bigram/trigramは、targetそのものへの距離ではなく、known3適合スコアの実測−生成差を見る。これとtarget距離/A-wide距離を別に保存した。

確認5seedのtarget bigram JSDは .190299→.195107、target trigram JSDは .431288→.436202 と、小幅に悪化。一方known3 JSDはbigram .137913→.134825、trigram .340518→.338991と近づく。A-wide JSDはbigram .123591→.124861、trigram .323403→.324296でほぼ同水準。

したがって、「A-wide文法が壊れた」とは判定しない。**葉参照への寄せ方と、特定targetの再現度は別指標**である。

## 8. 実測文脈でのteacher forcing

この診断は実測slot/語位置/segment終了条件を固定し、次に継続字を書く場合のnon-END分布を評価する。停止・packing・候補選別を含む最終語の尤度ではない。

{md_table(tf[(tf.arm=='E12_VH')][['kind','base_loss','new_loss','improvement','leaves_improved','p_two','holm_primary_two_sided','holm_head_two_sided']])}

単位はbit/予測字。表は各葉内平均→20葉等重み。正のimprovementが改善。E1のH1_SPACEとE2のH2は、それぞれ約.0591/.0593 bit悪化した。H2の両側主2比較補正は約.02477。HEAD H1とHEAD H3は平均で改善方向だった。

同じ生成器を通すとSPACE/H2の生成頁適合が良くなるのに、実測文脈でのproposal確率は必ずしも改善しない。したがって入口補正を、そのまま書記の正しい局所遷移則と解釈することはできない。selector・語長幅・停止を通した出力の偏りを打ち消す補正になっている可能性があるが、これは解釈候補であり、今回その主因を同定したわけではない。

support外は、旧scopeではH1_SPACE 1/1173、H2 5/1464、HEAD H3 6/192。E/Hはsupportを開放しないため件数は変わらない。表示lossのfloorは1e-15。F16ではH2 6件、HEAD H3 8件であり、稀なsupport欠落を含めた診断として扱う。

## 9. 実装部品別の現在地

- **E1/E2**：従来SPACE審判では有効。ただし普通SPACEのみでは利得が小さく、H1/H2 proposalのteacher-forcing損失は悪化。機構上の最適性は未証明。
- **HEAD H1V/H3**：E12単独のHEAD副作用を緩和する候補。縦HEADとH3専用残差は残る。単独H3の成功としない。
- **F16**：機械実装は完了しているが、今回の二候補上限では重いmulti-seed審判へ進めていない。簡易1runでtypes/hapaxは良好だったが、正式統一・昇格は未判断。
- **B_ALIGN**：原位置とPLANT/行末のコード整合化は実装済み。簡易1runでtypes/hapaxに警告が出たため、性能上の採用は保留。

今回、F16×HEAD×境界の新規統合や係数grid探索はしていない。仕様の独立切替を維持し、審判結果から生成器を再調整していない。

## 10. 判定と保存

**E12_VHはSPACE改善の有力部品。ただし正式championはBTI2のまま。**

昇格を見送る理由は、(i) 普通SPACEのみの改善が小さく確実でない、(ii) route56/bT leaf-excessに回帰警告、(iii) types/hapaxの誤差増加、(iv) 実測H1/H2確率の悪化、である。統計非有意だけを根拠に「副作用なし」とはしない。

全生成物・全審判・悪化条件も削除せず保存した。新規E/H学習はexternal16+known3のみだが、継承稀字/m/G parameterの全由来はUNVERIFIEDのまま。独立LLM審判は0回であり、数値審判16＋補助4の結果である。

### 主ファイル

- `FINAL_COMPARISON.csv`：最終5seedの20指標一覧。
- `outputs/confirmation/judged/paired_vs_parent.csv`：葉単位対応検定、片側/両側、群別Holm、bootstrap区間。
- `outputs/confirmation/judged/per_seed_effects.csv`：seed別方向。
- `outputs/confirmation/judged/metric_summary.csv`：語彙・長さ・幅の実測比較。
- `outputs/screen/teacher_forced_events.csv.gz`：実測位置ごとの予測確率。
- `outputs/screen/teacher_forced_paired.csv`：teacher forcingの葉単位検定。
- `EVALUATION_CONTRACT_AUDIT.json`：旧16審判一致と凍結コード確認。
- `MODEL_STATUS.json`：JUDGED_NOT_PROMOTED。
'''
 (ROOT/'REPORT_JA.md').write_text(txt)
 # This note does not change the previously sealed selection or generator results.
 e.write(ROOT/'SUMMARY_ENRICHMENT_NOTE.json',dict(note='After selections, paired summaries were additionally annotated with group-specific two-sided Holm columns. Raw scores and generator outputs were not changed; historical selection digest refers to the pre-enrichment table.',multirun_raw_score_sha256=e.file_hash(out/'multirun/judged/scores_by_leaf_run.csv'),confirmation_raw_score_sha256=e.file_hash(out/'confirmation/judged/scores_by_leaf_run.csv')))
 print('REPORT_WRITTEN',len(txt))
if __name__=='__main__':main()
