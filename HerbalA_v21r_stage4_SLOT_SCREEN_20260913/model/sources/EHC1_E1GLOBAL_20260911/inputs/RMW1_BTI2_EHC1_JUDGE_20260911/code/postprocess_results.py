#!/usr/bin/env python3
"""Descriptive and paired summaries only; never fit or change a generator."""
import evaluation_common as e
from stage3_env import ROOT
import pandas as pd,numpy as np,json

def main():
 out=ROOT/'outputs';T=pd.read_csv(out/'screen/teacher_forced_by_leaf.csv');tp=[]
 for arm in sorted(set(T.arm)-{'BASE','OFF'}):
  z=T[T.arm.eq(arm)].merge(T[T.arm.eq('BASE')],on=['bif','kind'],suffixes=('_new','_base'))
  for k,g in z.groupby('kind'):
   v=g.loss_bits_base-g.loss_bits_new;tp.append(dict(arm=arm,kind=k,base_loss=g.loss_bits_base.mean(),new_loss=g.loss_bits_new.mean(),improvement=v.mean(),leaves_improved=int((v>1e-12).sum()),p_two=e.signflip(v)))
 P=pd.DataFrame(tp);P['holm_primary_two_sided']=np.nan;P['holm_head_two_sided']=np.nan
 for arm in P.arm.unique():
  for group,ks in [('primary',['H1_SPACE','H2']),('head',['H1_HEAD','H3_HEAD'])]:
   mk=P.arm.eq(arm)&P.kind.isin(ks);P.loc[mk,'holm_'+group+'_two_sided']=e.holm(P.loc[mk,'p_two'])
 P.to_csv(out/'screen/teacher_forced_paired.csv',index=False)
 # Per-seed descriptive effect direction; seeds are not additional independent leaves.
 for stage in ['multirun','confirmation']:
  sd=out/stage/'judged'
  if not (sd/'scores_by_leaf_run.csv').exists():continue
  S=pd.read_csv(sd/'scores_by_leaf_run.csv');r=[]
  CO=pd.read_csv(sd/'paired_vs_parent.csv')
  for arm in CO.arm.unique():
   for gn,ks in [('primary',e.PRIMARY),('head',e.HEAD),('regression',e.REGRESSION),('main6',e.MAIN6)]:
    mk=CO.arm.eq(arm)&CO.judge.isin(ks);CO.loc[mk,'holm_'+gn+'_two_sided']=e.holm(CO.loc[mk,'p_two_sided'])
  CO.to_csv(sd/'paired_vs_parent.csv',index=False)
  for arm in sorted(set(S.arm)-{'BASE'}):
   z=S[S.arm.eq(arm)].merge(S[S.arm.eq('BASE')],on=['bif','run','judge'],suffixes=('_new','_base'),validate='one_to_one')
   for (run,j),g in z.groupby(['run','judge']):
    ba=g.abs_margin_base.mean();nw=g.abs_margin_new.mean();r.append(dict(arm=arm,run=run,judge=j,base_abs=ba,new_abs=nw,change_pct=100*(nw/ba-1),base_real_wins=int((g.margin_base>1e-12).sum()),new_real_wins=int((g.margin_new>1e-12).sum())))
  pd.DataFrame(r).to_csv(sd/'per_seed_effects.csv',index=False)
  D=pd.read_csv(sd/'ngram_distances.csv');D.groupby(['arm','ngram']).mean(numeric_only=True).reset_index().to_csv(sd/'ngram_distance_summary.csv',index=False)
  M=pd.read_csv(sd/'metrics_by_leaf_run.csv');mp=[]
  for arm in sorted(set(M.arm)-{'BASE'}):
   z=M[M.arm.eq(arm)].merge(M[M.arm.eq('BASE')],on=['bif','run'],suffixes=('_new','_base'),validate='one_to_one')
   for k in [k[3:] for k in M if k.startswith('ae_')]:
    v=(z['ae_'+k+'_new']-z['ae_'+k+'_base']).groupby(z.bif).mean();x=v.to_numpy();rg=np.random.default_rng(112233);bs=x[rg.integers(len(x),size=(20000,len(x)))].mean(axis=1)
    mp.append(dict(arm=arm,metric=k,MAE_change=v.mean(),ci_low=np.quantile(bs,.025),ci_high=np.quantile(bs,.975),p_two=e.signflip(v),leaves_improved=int((v<-1e-12).sum())))
  pd.DataFrame(mp).to_csv(sd/'metric_paired.csv',index=False)
 print('POSTPROCESS_COMPLETE',flush=True)
if __name__=='__main__':main()
