from __future__ import annotations
import argparse,gzip,json,os,sys
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import wilcoxon
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'code'))
from runtime_bootstrap import prepare_runtime
HANDOFF,PARENT,ST=prepare_runtime();os.environ['EHC2_STAGE6_PARENT']=str(PARENT);sys.path.insert(0,str(ST/'code'))
from stage6_env import *
import experiment_env as benv
sys.path.insert(0,str(benv.EHC/'code'));sys.path.insert(0,str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
import v19r_rb3_pw2_close1 as m

GLOBAL=['H2_RAW','bigram','ng','trigram','SPACE_RAW','route56','bT_leaf_excess','glyph_depth','length_width']
ARM_DIR={
 'SAFE_LEFT_BT_OFF':'RMW1_BTI2_EHC2_DECOMP1_PUV_R4LEX_W2H2L4_K16_LEFT_BTOFF',
 'PRETERM_R6':'HerbalA_v21r_PRETERM_R6',
 'PRETERM_QMAP9':'HerbalA_v21r_PRETERM_QMAP9',
}
NMY={'n','m','y'}; LR={'l','r'}
REAL_TARGET={'avgw':1.263285,'nmy':0.465909,'lr':0.477273,'close':-0.011364}

def terminal(s):
 s=str(s)
 for g in sorted(m.G2I,key=len,reverse=True):
  if s.endswith(g): return g
 return None

def pval(x):
 x=np.asarray(x,float);x=x[np.isfinite(x)];x=x[np.abs(x)>1e-15]
 return 1.0 if len(x)==0 else float(wilcoxon(x,alternative='two-sided',method='approx').pvalue)

def req_audit(path):
 ev=chg=comm=commchg=0; deltas=[]
 with gzip.open(path,'rt') as f:
  for line in f:
   r=json.loads(line)
   if r.get('preterm_applied'):
    ev+=1; chg+=int(bool(r.get('preterm_changed'))); deltas.append(int(r.get('preterm_selected_close_score',0))-int(r.get('preterm_anchor_close_score',0)))
    if r.get('committed_to_final_page'):
     comm+=1; commchg+=int(bool(r.get('preterm_changed')))
 return dict(preterm_events=ev,preterm_changed=chg,preterm_committed=comm,preterm_committed_changed=commchg,mean_close_delta=float(np.mean(deltas)) if deltas else 0.0)

def targeted(d,threshold=9):
 x=d[(d.role=='BODY')&(d.draw_segment_end==0)].copy()
 x['terminal']=x.stable_surface.map(terminal)
 x['nmy']=x.terminal.isin(NMY).astype(float);x['lr']=x.terminal.isin(LR).astype(float);x['close']=x.nmy-x.lr
 x['avgw']=x.phys_width/x.stable_glyph_len
 lo=x[x.rstart<=threshold]; hi=x[x.rstart>threshold]
 o={'n_body_nonfinal':len(x),'n_low':len(lo),'low_frac':len(lo)/len(x) if len(x) else np.nan}
 for name in ['avgw','nmy','lr','close']:
  o['low_'+name]=float(lo[name].mean()) if len(lo) else np.nan
  o['high_'+name]=float(hi[name].mean()) if len(hi) else np.nan
  o['low_'+name+'_target_abs_err']=abs(o['low_'+name]-REAL_TARGET[name]) if np.isfinite(o['low_'+name]) else np.nan
 return o

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--runs',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--arms',default='SAFE_LEFT_BT_OFF,PRETERM_R6,PRETERM_QMAP9');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 runs=[int(x) for x in a.runs.split(',') if x.strip()];arms=[x for x in a.arms.split(',') if x]
 C=benv.e.context();F=list(benv.e.folds(C.bifs));real_docs={p:benv.e.real_doc(C,p) for p in C.seqs}
 grow=[];trow=[];mrow=[]
 for fi,test in enumerate(F):
  train=[b for b in C.bifs if b not in test];train_docs=[real_docs[p] for b in train for p in C.pages[b]]
  for bif in test:
   page=C.pages[bif][-1];known=[real_docs[q] for q in C.pages[bif] if q!=page];judge=benv.e.Judges(train_docs,known);real=judge.score(real_docs[page],True)
   for run in runs:
    for arm in arms:
     p=a.root/f'run{run}'/ARM_DIR[arm]/bif.replace(':','_')
     d=pd.read_csv(p/'tokens.csv.gz');gs=judge.score(benv.e.generated_doc(d),True)
     for j in GLOBAL:grow.append(dict(fold=fi,bif=bif,run=run,arm=arm,judge=j,value=abs(float(real[j]-gs[j]))))
     tr=targeted(d,9);tr.update(fold=fi,bif=bif,run=run,arm=arm);trow.append(tr)
     md=json.load(open(p/'MECHANICAL.json'));ra=req_audit(p/'requests.jsonl.gz');ra.update(fold=fi,bif=bif,run=run,arm=arm,packing=bool(md.get('packing_exact')),support=int(md.get('support_violations',0)),invalid=int(md.get('invalid_rows',0)));mrow.append(ra)
 G=pd.DataFrame(grow);T=pd.DataFrame(trow);M=pd.DataFrame(mrow)
 G.to_csv(a.out/'global_scores.csv',index=False);T.to_csv(a.out/'targeted_case_metrics.csv',index=False);M.to_csv(a.out/'mechanical_cases.csv',index=False)
 leaf=G.groupby(['bif','arm','judge'],as_index=False).value.mean();leaf.to_csv(a.out/'leaf_means.csv',index=False)
 abs_=leaf.groupby(['arm','judge'],as_index=False).value.mean();abs_.to_csv(a.out/'absolute.csv',index=False)
 paired=[]
 for arm in [x for x in ['PRETERM_R6','PRETERM_QMAP9'] if x in arms]:
  for j in GLOBAL:
   b=leaf[(leaf.arm=='SAFE_LEFT_BT_OFF')&(leaf.judge==j)].set_index('bif').value;s=leaf[(leaf.arm==arm)&(leaf.judge==j)].set_index('bif').value;x=(b-s).dropna()
   paired.append(dict(reference='SAFE_LEFT_BT_OFF',arm=arm,judge=j,improvement=float(x.mean()),wins=int((x>0).sum()),losses=int((x<0).sum()),ties=int((x==0).sum()),p=pval(x.values)))
 P=pd.DataFrame(paired);P.to_csv(a.out/'paired_global.csv',index=False)
 # pooled targeted metrics across all tokens for each arm (not mean-of-case rates)
 pooled=[]
 for arm in arms:
  docs=[]
  for run in runs:
   for bif in C.bifs:
    p=a.root/f'run{run}'/ARM_DIR[arm]/bif.replace(':','_')/'tokens.csv.gz'
    docs.append(pd.read_csv(p))
  d=pd.concat(docs,ignore_index=True);z=targeted(d,9);z.update(arm=arm);pooled.append(z)
 PT=pd.DataFrame(pooled);PT.to_csv(a.out/'targeted_pooled.csv',index=False)
 mm=M.groupby('arm').agg(cases=('bif','size'),packing=('packing','all'),support=('support','sum'),invalid=('invalid','sum'),preterm_events=('preterm_events','sum'),preterm_changed=('preterm_changed','sum'),preterm_committed=('preterm_committed','sum'),preterm_committed_changed=('preterm_committed_changed','sum'),mean_close_delta=('mean_close_delta','mean')).reset_index();mm.to_csv(a.out/'mechanical_summary.csv',index=False)
 summary={'runs':runs,'global_absolute':abs_.to_dict('records'),'paired':P.to_dict('records'),'targeted_pooled':PT.to_dict('records'),'mechanical':mm.to_dict('records')}
 (a.out/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str)+'\n')
 print(json.dumps(summary,ensure_ascii=False,indent=2,default=str))
if __name__=='__main__':main()
