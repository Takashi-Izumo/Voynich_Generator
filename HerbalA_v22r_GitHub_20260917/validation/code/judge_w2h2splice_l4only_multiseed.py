from __future__ import annotations
import os,sys,json,math
from pathlib import Path
import numpy as np,pandas as pd

ST=Path('/mnt/data/puv_handoff/RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912/current_model/RMW1_BTI2_EHC2_DECOMP1_STAGE6_20260911')
P=Path('/mnt/data/_parent_ehc1_all/EHC1_E1GLOBAL_20260911')
os.environ['EHC2_STAGE6_PARENT']=str(P);sys.path.insert(0,str(ST/'code'))
from stage6_env import *
import experiment_env as benv

OLD_PARENT=Path('/mnt/data/leafex_full_validation_20260912')
OLD_CAND=Path('/mnt/data/w2h2splice_l4only_full_20260912')
NEW=Path('/mnt/data/w2h2splice_l4only_multiseed_20260912')
OUT=Path('/mnt/data/w2h2splice_l4only_multiseed_judge_20260912');OUT.mkdir(parents=True,exist_ok=True)
OLD_RUNS=list(range(91321,91326));NEW_RUNS=list(range(91326,91341));RUNS=OLD_RUNS+NEW_RUNS
KEY=['H2_RAW','SPACE_RAW','bigram','ng','trigram','route56','bT_leaf_excess','glyph_depth','length_width']

def arm_path(arm,run,bif):
    b=bif.replace(':','_')
    if run in OLD_RUNS:
        if arm=='PARENT':return OLD_PARENT/f'run{run}'/'PUV_R4_LEXCV'/b
        return OLD_CAND/f'run{run}'/'W2H2SPLICE_L4ONLY_ON'/b
    else:
        return NEW/f'run{run}'/('W2H2SPLICE_L4ONLY_OFF' if arm=='PARENT' else 'W2H2SPLICE_L4ONLY_ON')/b

def signflip(x,B=200000,seed=20260912):
    x=np.asarray(x,float);x=x[np.isfinite(x)];n=len(x)
    if n==0:return np.nan
    if n<=20:
        sums=[]
        # exact all 2^n
        obs=abs(x.mean())
        cnt=0;tot=1<<n
        for mask in range(tot):
            s=0.0
            for i,v in enumerate(x):s += v if (mask>>i)&1 else -v
            if abs(s/n)>=obs-1e-15:cnt+=1
        return cnt/tot
    rng=np.random.default_rng(seed);obs=abs(x.mean());cnt=0
    for _ in range(B):
        m=float(np.mean(x*rng.choice([-1,1],size=n)))
        cnt += abs(m)>=obs-1e-15
    return (cnt+1)/(B+1)

def boot_ci(x,B=50000,seed=20260912):
    x=np.asarray(x,float);rng=np.random.default_rng(seed);n=len(x)
    a=x[rng.integers(0,n,(B,n))].mean(axis=1)
    return float(np.quantile(a,.025)),float(np.quantile(a,.975))

C=benv.e.context();FOLDS=list(benv.e.folds(C.bifs));real_docs={p:benv.e.real_doc(C,p) for p in C.seqs}
rows=[];mech=[]
for fi,test in enumerate(FOLDS):
    train=[b for b in C.bifs if b not in test];train_pages=[p for b in train for p in C.pages[b]];train_docs=[real_docs[p] for p in train_pages]
    for bif in test:
        page=C.pages[bif][-1];known_pages=[q for q in C.pages[bif] if q!=page];known_docs=[real_docs[q] for q in known_pages];judge=benv.e.Judges(train_docs,known_docs);real=judge.score(real_docs[page],True)
        for run in RUNS:
            for arm in ['PARENT','L4K16']:
                loc=arm_path(arm,run,bif);d=pd.read_csv(loc/'tokens.csv.gz');gd=benv.e.generated_doc(d);gs=judge.score(gd,True)
                for j in KEY:
                    mar=float(real[j]-gs[j]);rows.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,judge=j,abs_margin=abs(mar),margin=mar))
                md=json.loads((loc/'MECHANICAL.json').read_text())
                mech.append(dict(fold=fi,bif=bif,run=run,arm=arm,packing=bool(md['packing_exact']),support=int(md.get('support_violations',0)),invalid=int(md.get('invalid_rows',0)),retry=int(md.get('segment_retries',0))))
        print('J',fi,bif,flush=True)
S=pd.DataFrame(rows);Q=pd.DataFrame(mech);S.to_csv(OUT/'SCORES_ALL20.csv',index=False);Q.to_csv(OUT/'MECHANICAL_ALL20.csv',index=False)

# pair every run/leaf
Z=S[S.arm.eq('L4K16')].merge(S[S.arm.eq('PARENT')],on=['fold','bif','page','run','judge'],suffixes=('_new','_par'),validate='one_to_one')
Z['improvement']=Z.abs_margin_par-Z.abs_margin_new
Z.to_csv(OUT/'PAIRED_ALL20_BY_RUN.csv',index=False)
periods={'OLD5':OLD_RUNS,'NEW15':NEW_RUNS,'ALL20':RUNS}
summ=[]
leaf_out=[]
for period,runs in periods.items():
  zz=Z[Z.run.isin(runs)]
  for j,g in zz.groupby('judge'):
    leaf=g.groupby('bif',as_index=False).agg(parent=('abs_margin_par','mean'),new=('abs_margin_new','mean'),improvement=('improvement','mean'))
    leaf['period']=period;leaf['judge']=j;leaf_out.append(leaf)
    a=float(g.abs_margin_par.mean());n=float(g.abs_margin_new.mean());x=leaf.improvement.to_numpy();lo,hi=boot_ci(x,seed=20260912+sum(map(ord,period+j)))
    summ.append(dict(period=period,judge=j,n_runs=len(runs),parent_abs=a,new_abs=n,change_pct=100*(n/a-1),improvement=float(x.mean()),leaves_improved=int((x>1e-12).sum()),leaves_worsened=int((x<-1e-12).sum()),leaves_tied=int((abs(x)<=1e-12).sum()),p_signflip=signflip(x),ci95_lo=lo,ci95_hi=hi))
SUM=pd.DataFrame(summ);SUM.to_csv(OUT/'SUMMARY_OLD5_NEW15_ALL20.csv',index=False);pd.concat(leaf_out).to_csv(OUT/'LEAF_MEANS_BY_PERIOD.csv',index=False)

# independent 5-seed blocks: old and 3 new blocks
blocks={'B0_OLD':OLD_RUNS,'B1_NEW':list(range(91326,91331)),'B2_NEW':list(range(91331,91336)),'B3_NEW':list(range(91336,91341))}
br=[]
for name,runs in blocks.items():
  zz=Z[Z.run.isin(runs)]
  for j,g in zz.groupby('judge'):
    leaf=g.groupby('bif').improvement.mean();a=float(g.abs_margin_par.mean());n=float(g.abs_margin_new.mean())
    br.append(dict(block=name,judge=j,parent_abs=a,new_abs=n,change_pct=100*(n/a-1),improvement=float(leaf.mean()),leaves_improved=int((leaf>1e-12).sum()),p_signflip=signflip(leaf.to_numpy())))
pd.DataFrame(br).to_csv(OUT/'FIVE_SEED_BLOCK_STABILITY.csv',index=False)

# convergence by first N seeds, N=5,10,15,20
cr=[]
for N in [5,10,15,20]:
  runs=RUNS[:N];zz=Z[Z.run.isin(runs)]
  for j,g in zz.groupby('judge'):
    leaf=g.groupby('bif').improvement.mean();a=float(g.abs_margin_par.mean());n=float(g.abs_margin_new.mean())
    cr.append(dict(n_seeds=N,judge=j,parent_abs=a,new_abs=n,change_pct=100*(n/a-1),improvement=float(leaf.mean()),leaves_improved=int((leaf>1e-12).sum()),p_signflip=signflip(leaf.to_numpy())))
pd.DataFrame(cr).to_csv(OUT/'CONVERGENCE_BY_NSEEDS.csv',index=False)

# paired run-level direction: number of seed x leaf pairs improved
rr=[]
for j,g in Z.groupby('judge'):
 rr.append(dict(judge=j,pairs=len(g),pairs_improved=int((g.improvement>1e-12).sum()),pairs_worsened=int((g.improvement<-1e-12).sum()),pair_mean_improvement=float(g.improvement.mean())))
pd.DataFrame(rr).to_csv(OUT/'RUN_LEVEL_DIRECTION.csv',index=False)

AUD=dict(status='PASS' if len(Q)==800 and Q.packing.all() and Q.support.sum()==0 and Q.invalid.sum()==0 and Q.retry.sum()==0 else 'FAIL',mechanical_rows=len(Q),packing_all=bool(Q.packing.all()),support=int(Q.support.sum()),invalid=int(Q.invalid.sum()),retry=int(Q.retry.sum()),old_runs=OLD_RUNS,new_runs=NEW_RUNS)
json.dump(AUD,open(OUT/'AUDIT.json','w'),indent=2)
print('\nSUMMARY KEY')
print(SUM[SUM.judge.isin(['H2_RAW','bigram','ng','trigram','route56','bT_leaf_excess','SPACE_RAW'])].to_string(index=False))
print('\nBLOCKS')
B=pd.read_csv(OUT/'FIVE_SEED_BLOCK_STABILITY.csv');print(B[B.judge.isin(['bigram','ng','trigram','H2_RAW'])].to_string(index=False))
print('\nAUDIT',AUD)
