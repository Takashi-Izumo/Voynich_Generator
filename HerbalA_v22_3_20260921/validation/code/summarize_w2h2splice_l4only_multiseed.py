import os,sys,json
from pathlib import Path
import numpy as np,pandas as pd
ST=Path('/mnt/data/puv_handoff/RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912/current_model/RMW1_BTI2_EHC2_DECOMP1_STAGE6_20260911');P=Path('/mnt/data/_parent_ehc1_all/EHC1_E1GLOBAL_20260911')
os.environ['EHC2_STAGE6_PARENT']=str(P);sys.path.insert(0,str(ST/'code'))
from stage6_env import *
import experiment_env as benv
OUT=Path('/mnt/data/w2h2splice_l4only_multiseed_judge_20260912')
S=pd.read_csv(OUT/'SCORES_ALL20.csv');Q=pd.read_csv(OUT/'MECHANICAL_ALL20.csv')
OLD=list(range(91321,91326));NEW=list(range(91326,91341));RUNS=OLD+NEW
Z=S[S.arm.eq('L4K16')].merge(S[S.arm.eq('PARENT')],on=['fold','bif','page','run','judge'],suffixes=('_new','_par'),validate='one_to_one');Z['improvement']=Z.abs_margin_par-Z.abs_margin_new;Z.to_csv(OUT/'PAIRED_ALL20_BY_RUN.csv',index=False)
def boot(x,seed):
 x=np.asarray(x,float);rng=np.random.default_rng(seed);N=30000;n=len(x);means=np.empty(N)
 for i in range(0,N,3000):
  k=min(3000,N-i);means[i:i+k]=x[rng.integers(0,n,(k,n))].mean(1)
 return np.quantile(means,[.025,.975])
periods={'OLD5':OLD,'NEW15':NEW,'ALL20':RUNS};summ=[];lout=[]
for per,runs in periods.items():
 zz=Z[Z.run.isin(runs)]
 for j,g in zz.groupby('judge'):
  leaf=g.groupby('bif',as_index=False).agg(parent=('abs_margin_par','mean'),new=('abs_margin_new','mean'),improvement=('improvement','mean'));leaf['period']=per;leaf['judge']=j;lout.append(leaf)
  a=g.abs_margin_par.mean();n=g.abs_margin_new.mean();x=leaf.improvement.to_numpy();lo,hi=boot(x,20260912+sum(map(ord,per+j)))
  summ.append(dict(period=per,judge=j,n_runs=len(runs),parent_abs=a,new_abs=n,change_pct=100*(n/a-1),improvement=x.mean(),leaves_improved=(x>1e-12).sum(),leaves_worsened=(x<-1e-12).sum(),p_signflip=benv.e.signflip(x),ci95_lo=lo,ci95_hi=hi))
SUM=pd.DataFrame(summ);SUM.to_csv(OUT/'SUMMARY_OLD5_NEW15_ALL20.csv',index=False);pd.concat(lout).to_csv(OUT/'LEAF_MEANS_BY_PERIOD.csv',index=False)
blocks={'B0_OLD':OLD,'B1_NEW':list(range(91326,91331)),'B2_NEW':list(range(91331,91336)),'B3_NEW':list(range(91336,91341))};br=[]
for name,runs in blocks.items():
 zz=Z[Z.run.isin(runs)]
 for j,g in zz.groupby('judge'):
  leaf=g.groupby('bif').improvement.mean();a=g.abs_margin_par.mean();n=g.abs_margin_new.mean();br.append(dict(block=name,judge=j,parent_abs=a,new_abs=n,change_pct=100*(n/a-1),improvement=leaf.mean(),leaves_improved=(leaf>1e-12).sum(),p_signflip=benv.e.signflip(leaf.to_numpy())))
B=pd.DataFrame(br);B.to_csv(OUT/'FIVE_SEED_BLOCK_STABILITY.csv',index=False)
cr=[]
for N in [5,10,15,20]:
 zz=Z[Z.run.isin(RUNS[:N])]
 for j,g in zz.groupby('judge'):
  leaf=g.groupby('bif').improvement.mean();a=g.abs_margin_par.mean();n=g.abs_margin_new.mean();cr.append(dict(n_seeds=N,judge=j,parent_abs=a,new_abs=n,change_pct=100*(n/a-1),improvement=leaf.mean(),leaves_improved=(leaf>1e-12).sum(),p_signflip=benv.e.signflip(leaf.to_numpy())))
C=pd.DataFrame(cr);C.to_csv(OUT/'CONVERGENCE_BY_NSEEDS.csv',index=False)
rr=[]
for j,g in Z.groupby('judge'):
 rr.append(dict(judge=j,pairs=len(g),pairs_improved=(g.improvement>1e-12).sum(),pairs_worsened=(g.improvement<-1e-12).sum(),pair_mean_improvement=g.improvement.mean()))
pd.DataFrame(rr).to_csv(OUT/'RUN_LEVEL_DIRECTION.csv',index=False)
AUD=dict(status='PASS' if len(Q)==800 and Q.packing.all() and Q.support.sum()==0 and Q.invalid.sum()==0 and Q.retry.sum()==0 else 'FAIL',mechanical_rows=int(len(Q)),packing_all=bool(Q.packing.all()),support=int(Q.support.sum()),invalid=int(Q.invalid.sum()),retry=int(Q.retry.sum()),old_runs=OLD,new_runs=NEW)
json.dump(AUD,open(OUT/'AUDIT.json','w'),indent=2)
print('KEY')
print(SUM[SUM.judge.isin(['H2_RAW','SPACE_RAW','bigram','ng','trigram','route56','bT_leaf_excess','glyph_depth','length_width'])].to_string(index=False))
print('\nBLOCKS')
print(B[B.judge.isin(['H2_RAW','bigram','ng','trigram'])].to_string(index=False))
print('\nCONV')
print(C[C.judge.isin(['H2_RAW','bigram','ng','trigram'])].to_string(index=False))
print('\nAUD',AUD)
