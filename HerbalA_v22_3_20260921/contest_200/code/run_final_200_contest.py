from __future__ import annotations
import os,sys,json,hashlib
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import binomtest

PKG=Path('/mnt/data/RMW1_BTI2_EHC2_DECOMP1_PUV_R4LEX_W2H2L4_K16_20260912')
GEN=Path('/mnt/data/final_200_contest_20260912/generated')
OUT=Path('/mnt/data/final_200_contest_20260912'); OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PKG/'code'))
from runtime_bootstrap import prepare_runtime
HANDOFF,PARENT,ST=prepare_runtime()
os.environ['EHC2_STAGE6_PARENT']=str(PARENT)
sys.path.insert(0,str(ST/'code'))
from stage6_env import *
import experiment_env as benv

RUNS=list(range(99001,99011))
MODEL='RMW1_BTI2_EHC2_DECOMP1_PUV_R4LEX_W2H2L4_K16'
JUDGES=['word','ng','bigram','trigram','route56','combined']

# Pair identities first, before any scoring.
C=benv.e.context(); folds_list=list(benv.e.folds(C.bifs))
pairs=[]
for fi,test in enumerate(folds_list):
    for bif in test:
        page=C.pages[bif][-1]
        for run in RUNS:
            pairs.append(dict(fold=fi,bif=bif,page=page,run=run))
assert len(pairs)==200
# exactly 100 real-left and 100 real-right, shuffled independently of scores
rng=np.random.default_rng(202609120200)
flags=np.array([1]*100+[0]*100,dtype=int); rng.shuffle(flags)
for i,(r,fl) in enumerate(zip(pairs,flags),1):
    r['pair_id']=f'P{i:03d}'; r['real_on_left']=int(fl)
key=pd.DataFrame(pairs)
# presentation omits truth; side ids are opaque hashes fixed before scoring
presentation=[]
for r in pairs:
    for side in ['L','R']:
        opaque=hashlib.sha256(f"{r['pair_id']}|{side}|20260912".encode()).hexdigest()[:16]
        presentation.append(dict(pair_id=r['pair_id'],fold=r['fold'],bif=r['bif'],page=r['page'],run=r['run'],side=side,opaque_doc_id=opaque))
pd.DataFrame(presentation).to_csv(OUT/'BLIND_PRESENTATION.csv',index=False)
key[['pair_id','fold','bif','page','run','real_on_left']].to_csv(OUT/'BLIND_KEY.csv',index=False)
# hash presentation before scoring
pres_bytes=(OUT/'BLIND_PRESENTATION.csv').read_bytes()
(OUT/'BLIND_PRESENTATION.sha256').write_text(hashlib.sha256(pres_bytes).hexdigest()+'  BLIND_PRESENTATION.csv\n')

docs={p:benv.e.real_doc(C,p) for p in C.seqs}
outcomes=[]; score_rows=[]
for fi,test in enumerate(folds_list):
    train=[b for b in C.bifs if b not in test]
    train_pages=[p for b in train for p in C.pages[b]]
    for bif in test:
        page=C.pages[bif][-1]
        known=[q for q in C.pages[bif] if q!=page]
        judge=benv.e.Judges([docs[p] for p in train_pages],[docs[p] for p in known])
        real_doc=docs[page]
        real_scores=judge.score(real_doc,True)
        for run in RUNS:
            rr=next(x for x in pairs if x['bif']==bif and x['run']==run)
            loc=GEN/f'run{run}'/MODEL/bif.replace(':','_')
            d=pd.read_csv(loc/'tokens.csv.gz')
            gen_doc=benv.e.generated_doc(d)
            gen_scores=judge.score(gen_doc,True)
            left_is_real=bool(rr['real_on_left'])
            for j in JUDGES:
                rs=float(real_scores[j]); gs=float(gen_scores[j])
                ls=rs if left_is_real else gs; rsd=gs if left_is_real else rs
                eps=1e-12
                if abs(ls-rsd)<=eps:
                    chosen='TIE'; correct=np.nan
                else:
                    chosen='L' if ls>rsd else 'R'
                    truth='L' if left_is_real else 'R'
                    correct=int(chosen==truth)
                outcomes.append(dict(pair_id=rr['pair_id'],fold=fi,bif=bif,page=page,run=run,judge=j,left_score=ls,right_score=rsd,chosen_side=chosen,correct=correct,score_gap=abs(ls-rsd)))
                score_rows.append(dict(pair_id=rr['pair_id'],fold=fi,bif=bif,page=page,run=run,judge=j,real_score=rs,generated_score=gs,margin=rs-gs,abs_margin=abs(rs-gs)))
    print('JUDGED fold',fi,flush=True)
O=pd.DataFrame(outcomes); S=pd.DataFrame(score_rows)
O.to_csv(OUT/'BLIND_OUTCOMES_200.csv',index=False); S.to_csv(OUT/'SCORES_200.csv',index=False)
# Reveal only after predictions saved: merge key for auditable side-truth output
R=O.merge(key[['pair_id','real_on_left']],on='pair_id',validate='many_to_one')
R['truth_side']=np.where(R.real_on_left.eq(1),'L','R')
R.to_csv(OUT/'REVEALED_OUTCOMES_200.csv',index=False)

# raw 200 summary: descriptive binomial only (same 20 real target pages repeat 10x)
raw=[]
for j,g in S.groupby('judge',sort=False):
    wins=int((g.margin>1e-12).sum()); ties=int((g.margin.abs()<=1e-12).sum()); losses=len(g)-wins-ties
    n_eff=wins+losses
    p_desc=float(binomtest(wins,n_eff,.5).pvalue) if n_eff else 1.0
    raw.append(dict(judge=j,sets=len(g),real_wins=wins,generated_wins=losses,ties=ties,real_win_rate=wins/n_eff if n_eff else np.nan,descriptive_binom_p=p_desc,mean_margin=float(g.margin.mean()),mean_abs_margin=float(g.abs_margin.mean())))
RAW=pd.DataFrame(raw); RAW.to_csv(OUT/'RAW_200_SUMMARY.csv',index=False)

# historical formal contest aggregation: mean within leaf over 10 fresh seeds, then 20 leaves
leafrows=[]; clusters=[]
for j,g in S.groupby('judge',sort=False):
    lv=g.groupby('bif',sort=False).margin.mean()
    wins=int((lv>1e-12).sum()); ties=int((lv.abs()<=1e-12).sum()); losses=len(lv)-wins-ties
    p=float(binomtest(wins,wins+losses,.5).pvalue) if wins+losses else 1.0
    # exact sign flip on leaf mean margins
    x=lv.to_numpy(float); sums=np.zeros(1)
    for v in x: sums=np.concatenate((sums+v,sums-v))
    ob=x.sum(); eps=1e-12*max(1.,abs(ob)); ps=float(np.mean(np.abs(sums)>=abs(ob)-eps))
    clusters.append(dict(judge=j,leaves=20,real_wins=wins,generated_wins=losses,ties=ties,binom_p=p,signflip_p=ps,mean_leaf_margin=float(lv.mean()),mean_leaf_abs_margin=float(lv.abs().mean())))
    for bif,v in lv.items(): leafrows.append(dict(judge=j,bif=bif,mean_margin=float(v),real_wins=int(v>1e-12)))
CLU=pd.DataFrame(clusters); CLU.to_csv(OUT/'CLUSTER_20_SUMMARY.csv',index=False); pd.DataFrame(leafrows).to_csv(OUT/'BY_LEAF.csv',index=False)

# seed-level stability
seed=[]
for (j,run),g in S.groupby(['judge','run']):
    w=int((g.margin>1e-12).sum()); t=int((g.margin.abs()<=1e-12).sum())
    seed.append(dict(judge=j,run=run,real_wins=w,generated_wins=20-w-t,ties=t,mean_margin=float(g.margin.mean())))
pd.DataFrame(seed).to_csv(OUT/'BY_SEED.csv',index=False)

# Diagnostic: which judge is strongest detector; combined correct/wrong profiles
D=RAW.sort_values('real_win_rate',ascending=False).copy(); D.to_csv(OUT/'DETECTOR_RANKING.csv',index=False)
# Pair-wise judge votes, useful for post-hoc "where spotted" without changing contest.
pivot=S.pivot_table(index=['pair_id','fold','bif','page','run'],columns='judge',values='margin',aggfunc='first').reset_index()
for j in JUDGES: pivot[j+'_real_vote']=(pivot[j]>1e-12).astype(int)
pivot.to_csv(OUT/'PAIR_VOTE_MATRIX.csv',index=False)

summary={
 'status':'COMPLETE', 'model':'RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16',
 'runs':RUNS,'n_pairs':200,'n_unique_real_target_pages':20,'repeats_per_target':10,
 'pair_order_randomized':True,'left_real':int(key.real_on_left.sum()),'right_real':int((1-key.real_on_left).sum()),
 'primary_judge':'combined','formal_stat_unit':'20 bifolia; ten fresh seeds averaged within leaf',
 'raw_200_is_descriptive_only':True,
 'presentation_sha256':hashlib.sha256(pres_bytes).hexdigest(),
 'combined_raw':RAW[RAW.judge.eq('combined')].iloc[0].to_dict(),
 'combined_cluster':CLU[CLU.judge.eq('combined')].iloc[0].to_dict(),
}
(OUT/'CONTEST_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=lambda x: x.item() if hasattr(x,'item') else x))
print('\nRAW 200\n',RAW.to_string(index=False))
print('\nCLUSTER 20\n',CLU.to_string(index=False))
print('\n',json.dumps(summary,ensure_ascii=False,indent=2,default=lambda x: x.item() if hasattr(x,'item') else x))
