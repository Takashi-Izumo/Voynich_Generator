#!/usr/bin/env python3
"""Frozen Stage-2 outputs: teacher-forced diagnostics and inexpensive screening.
No changes to generator settings. Selection rule is saved before reading outcomes.
"""
from __future__ import annotations
import evaluation_common as e
from stage3_env import EHC,ROOT
import numpy as np,pandas as pd
import json,math,time
from pathlib import Path

RULE=dict(stage='screen_on_mechanical_seed',run=91011,mandatory_reference_candidate='E12',max_candidates=2,
 second_candidate='lowest fixed equal-weight normalized absolute residual across SPACE_T_H1,H2_RAW,HEAD_shape,HEAD_vertical,H3_HEAD_RAW',
 eligible_if='non-BASE/non-OFF/non-E12; primary SPACE/H2 composite below BASE; types MAE<=BASE+1; hapax<=BASE+1.5; mean_len<=BASE+.05; mean_width<=BASE+.10; target bigram/trigram JSD<=1.10 BASE',
 no_eligible='only E12 advances; no new model or coefficient is invented',
 fresh_screen_seeds=[91021,91022,91023],confirmation_seeds=[91031,91032,91033,91034,91035],
 context='same 20 historical target surfaces; seed generalization, not fresh manuscripts')

def main():
 out=ROOT/'outputs/screen';out.mkdir(parents=True,exist_ok=True);e.write(out/'SELECTION_RULE_BEFORE_SCREEN.json',RULE)
 C=e.context();cfgs=e.configs();frozen=EHC/'outputs/mechanical/run91011';scores=[];metrics=[];teacher=[];trace=[];audit=[];cores={}
 td={p:e.real_doc(C,p) for p in C.seqs};plmeta=C.T.set_index('global_order'); lp_by_locus={str(r.locus):min(int(r.para_line_raw),3)-1 for r in C.T.itertuples(index=False)}
 for fi,test in enumerate(e.folds(C.bifs)):
  train=[b for b in C.bifs if b not in test];train_docs=[td[p] for b in train for p in C.pages[b]]
  for b in test:
   p=C.pages[b][-1];known=[q for q in C.pages[b] if q!=p];judges=e.Judges(train_docs,[td[q] for q in known],e.SCREEN);sr=judges.score(td[p],False);tables={}
   for arm,patch in cfgs.items():
    dpath=frozen/arm/b.replace(':','_');d=pd.read_csv(dpath/'tokens.csv.gz');sg=judges.score(e.generated_doc(d),False)
    for k in sr:scores.append(dict(fold=fi,bif=b,page=p,arm=arm,run=91011,judge=k,real_score=sr[k],gen_score=sg[k],margin=sr[k]-sg[k],abs_margin=abs(sr[k]-sg[k])))
    metrics.append(e.metric_row(C,p,d,arm,91011,b,fi))
    scope='LEGACY_SCOPE' if patch.scope_policy=='FROZEN_PARENT' else patch.scope_policy;fc=e.FoldContext.create(C,fi,b,p,scope,e.POLICY)
    if (fi,scope) not in cores:cores[fi,scope]=e.load_core(C,fc)
    core,ca=cores[fi,scope]
    if scope not in tables:
     tables[scope]=e.CorrectionTables(C.events[C.events.bif.isin(train)],C.events[C.events.page.isin(known)],*core[:2],core[3],fc,ca)
    tab=tables[scope];prev_heads={};obs=C.events[C.events.page.eq(p)].sort_values('global_order')
    for r in obs.itertuples(index=False):
     g=tuple(r.glyphs);pl=int(r.para_line_raw);lp=min(pl,3)-1;mt=plmeta.loc[r.global_order];end=bool(mt.is_segment_end);le=str(mt.boundary_type)=='LINE_END';pk=(p,r.para)
     for depth,kind,yes in [(0,'H1_SPACE',r.entry_eligible),(1,'H2',r.position_eligible and len(g)>=2),(2,'H3_HEAD',r.position_eligible and r.physical_head and r.base_role=='HEAD' and len(g)>=3),(0,'H1_HEAD',r.position_eligible and r.physical_head and r.base_role=='HEAD')]:
      if not yes:continue
      a=g[depth-2] if depth>=2 else e.m.START;bb=g[depth-1] if depth else e.m.START
      p0=tab.base_nonend(r.base_role,lp,end,le,depth,a,bb);new=p0.copy()
      if kind=='H1_HEAD':p0,new=tab.head_row(pl,prev_heads.get(pk),core[2].lstart,r.row_phase,patch.eta_vertical_head)
      elif kind=='H1_SPACE':
       if patch.eta_entry:new=p0*np.exp(patch.eta_entry*tab.bridge[r.row_phase,r.board][r.prev_terminal]);new=new/new.sum()
      else:
       eta=patch.eta_h2 if depth==1 else patch.eta_h3 if patch.h3_scope in ('HEAD','NON_PHW') else 0.
       gain=tab.local_gain((r.row_phase,r.board,depth,a,bb),p0,eta);new=p0*gain
       if new.sum():new/=new.sum()
      prob=float(new[g[depth]]);zero=prob<=0;teacher.append(dict(fold=fi,bif=b,page=p,arm=arm,kind=kind,global_order=r.global_order,role=r.base_role,board=r.board,row_phase=r.row_phase,truth=e.m.I2G[g[depth]],prob=prob,zero_support=zero,loss_bits=-math.log2(max(prob,1e-15)),base_same_scope_prob=float(p0[g[depth]])))
     if r.physical_head and r.base_role=='HEAD':prev_heads[pk]=g[0]
    reqfile=dpath/'requests.jsonl.gz'
    if reqfile.exists():
     for r in e.jsonl(reqfile):
      if not r.get('committed_to_final_page'):continue
      st=[]
      cs=r.get('candidates') or [r['selected']];probs=r.get('probabilities') or [1.]*len(cs)
      def local(w):
       gl=e.J.glyph(w,False)
       if not gl:return (np.nan,np.nan)
       gi=[e.m.G2I[x] for x in gl];t=r['prev_terminal'];ascore=float(tab.bridge[r['row_phase'],r['board']][t,gi[0]]) if t is not None else np.nan
       h2=np.nan
       if len(gi)>=2:
        lp=lp_by_locus[r['locus']]
        p0=tab.base_nonend(r['role'],lp,r['end'],r['line_end_boundary'],1,e.m.START,gi[0]);k=(r['row_phase'],r['board'],1,e.m.START,gi[0]);ex=tab.ex.get(k);kn=tab.kn.get(k)
        pe=p0 if ex is None else (ex+16*p0)/(ex.sum()+16);pk=pe if kn is None else (kn+8*pe)/(kn.sum()+8);h2=math.log2(max(float(pk[gi[1]]),1e-15))
       return ascore,h2
      for name,w in [('first',r['first']),('selected',r['selected']),('surface',r.get('final_surface',r['selected']))]:
       aa,hh=local(w);trace.append(dict(arm=arm,bif=b,run=91011,stage=name,proposal_id=r['proposal_id'],entry_association=aa,h2_logprob=hh))
      cv=np.array([local(w) for w in cs]);pr=np.asarray(probs);pr=pr/pr.sum()
      trace.append(dict(arm=arm,bif=b,run=91011,stage='bank_uniform',proposal_id=r['proposal_id'],entry_association=float(np.nanmean(cv[:,0])) if np.isfinite(cv[:,0]).any() else np.nan,h2_logprob=float(np.nanmean(cv[:,1])) if np.isfinite(cv[:,1]).any() else np.nan))
   audit.append(dict(fold=fi,bif=b,target=p,known3=known,training16=train,target_in_feature_fit=False))
   print('SCREEN',fi,b,p,flush=True)
 S=pd.DataFrame(scores);M=pd.DataFrame(metrics);TF=pd.DataFrame(teacher);TR=pd.DataFrame(trace)
 S.to_csv(out/'scores_by_leaf.csv',index=False);M.to_csv(out/'metrics_by_leaf.csv',index=False);TF.to_csv(out/'teacher_forced_events.csv.gz',index=False);TR.to_csv(out/'committed_stage_trace.csv.gz',index=False)
 ts=TF.groupby(['arm','kind']).agg(events=('loss_bits','size'),loss_bits=('loss_bits','mean'),zero_support=('zero_support','sum')).reset_index();ts.to_csv(out/'teacher_forced_summary.csv',index=False)
 TF.groupby(['arm','bif','kind']).agg(events=('loss_bits','size'),loss_bits=('loss_bits','mean'),zero_support=('zero_support','sum')).reset_index().to_csv(out/'teacher_forced_by_leaf.csv',index=False)
 TR.groupby(['arm','stage'])[['entry_association','h2_logprob']].mean().reset_index().to_csv(out/'committed_stage_summary.csv',index=False)
 TFLEAF=TF.groupby(['arm','bif','kind']).agg(loss_bits=('loss_bits','mean')).reset_index();tp=[]
 for arm in cfgs:
  if arm in ('BASE','OFF'):continue
  z=TFLEAF[TFLEAF.arm.eq(arm)].merge(TFLEAF[TFLEAF.arm.eq('BASE')],on=['bif','kind'],suffixes=('_new','_base'))
  for k,g in z.groupby('kind'):
   v=g.loss_bits_base-g.loss_bits_new;tp.append(dict(arm=arm,kind=k,base_loss=g.loss_bits_base.mean(),new_loss=g.loss_bits_new.mean(),improvement=v.mean(),leaves_improved=int((v>1e-12).sum()),p_two=e.signflip(v)))
 TPAIR=pd.DataFrame(tp);TPAIR['holm_primary_two_sided']=np.nan;TPAIR['holm_head_two_sided']=np.nan
 for arm in TPAIR.arm.unique():
  for group,ks in [('primary',['H1_SPACE','H2']),('head',['H1_HEAD','H3_HEAD'])]:
   mk=TPAIR.arm.eq(arm)&TPAIR.kind.isin(ks);TPAIR.loc[mk,'holm_'+group+'_two_sided']=e.holm(TPAIR.loc[mk,'p_two'])
 TPAIR.to_csv(out/'teacher_forced_paired.csv',index=False)

 sm=S.groupby(['arm','judge']).abs_margin.mean().unstack();base=sm.loc['BASE'];rat=sm.div(base);rank=[];bm=M[M.arm.eq('BASE')].mean(numeric_only=True)
 for arm in sm.index:
  gm=M[M.arm.eq(arm)].mean(numeric_only=True);warnings=[]
  for k,tol in [('types',1.),('hapax',1.5),('mean_len',.05),('mean_width',.10)]:
   if gm['ae_'+k]-bm['ae_'+k]>tol:warnings.append(k)
  for k in ('bigram_target_jsd','trigram_target_jsd'):
   if gm[k]>1.1*bm[k]:warnings.append(k)
  primary=float(rat.loc[arm,e.PRIMARY].mean());composite=float(rat.loc[arm,e.PRIMARY+e.HEAD].mean())
  rank.append(dict(arm=arm,primary_ratio=primary,composite_ratio=composite,warnings=';'.join(warnings),eligible=not warnings and primary<1 and arm not in ('BASE','OFF','E12'),**{k:gm[k] for k in gm.index if k.startswith('ae_') or k.endswith('_jsd')}))
 R=pd.DataFrame(rank).sort_values('composite_ratio');R.to_csv(out/'selection_ranking.csv',index=False);sm.to_csv(out/'absolute_residual_summary.csv');S.groupby(['arm','judge']).margin.agg(['mean',lambda x:(x>1e-12).sum()]).to_csv(out/'signed_screen_summary.csv')
 elig=R[R.eligible];arms=['E12']+elig.arm.head(1).tolist();selection=dict(RULE,selected_arms=arms,settings_changed=False,ranking_frozen=True,screen_scores_sha256=e.file_hash(out/'scores_by_leaf.csv'),teacher_forced_sha256=e.file_hash(out/'teacher_forced_events.csv.gz'))
 e.write(ROOT/'SELECTION_FROZEN.json',selection);e.write(out/'TRAINING_AUDIT.json',audit)
 print('FROZEN',arms);print(R[['arm','primary_ratio','composite_ratio','warnings','eligible']].to_string(index=False));print(ts.to_string(index=False))
if __name__=='__main__':main()
