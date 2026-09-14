from __future__ import annotations
import argparse,gzip,json,math,os,sys
from pathlib import Path
from collections import Counter,defaultdict
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
from w2_slot_tables import prepare_w2_events

GLOBAL=['H2_RAW','bigram','ng','trigram','SPACE_RAW','route56','bT_leaf_excess','glyph_depth','length_width']
LOCAL=['H2_JSD','H3_JSD','H4_JSD','H3H4_JSD','H1W_H3_JOINT_JSD','H3_CONDITIONAL_JSD','WIDTH_JSD','H2_WIDTH_JSD']
ARM_GLOB={
 'V20_COMPAT':'RMW1_BTI2_EHC2_DECOMP1_PUV_R4LEX_W2H2L4_K16',
 'SAFE_LEFT_BT_ON':'RMW1_BTI2_EHC2_DECOMP1_PUV_R4LEX_W2H2L4_K16_LEFT',
 'SAFE_LEFT_BT_OFF':'RMW1_BTI2_EHC2_DECOMP1_PUV_R4LEX_W2H2L4_K16_LEFT_BTOFF',
 'SLOT_BT_OFF':'HerbalA_v21r_W2_SLOT_BTOFF',
}

def parse_word(s:str)->tuple[int,...]:
    s=str(s);out=[];i=0;names=sorted(m.G2I,key=len,reverse=True)
    while i<len(s):
        hit=None
        for g in names:
            if s.startswith(g,i):hit=g;break
        if hit is None: raise ValueError((s,i))
        out.append(int(m.G2I[hit]));i+=len(hit)
    return tuple(out)

def js_counts(a:Counter,b:Counter)->float:
    keys=sorted(set(a)|set(b),key=repr)
    if not keys:return float('nan')
    x=np.asarray([a[k] for k in keys],float);y=np.asarray([b[k] for k in keys],float)
    if x.sum()<=0 or y.sum()<=0:return float('nan')
    x/=x.sum();y/=y.sum();z=.5*(x+y)
    def kl(p,q):
        mask=p>0
        return float(np.sum(p[mask]*np.log2(p[mask]/q[mask])))
    return .5*kl(x,z)+.5*kl(y,z)

def cond_h3(obs,gen):
    oc=defaultdict(Counter);gc=defaultdict(Counter);ow=Counter();gw=Counter()
    for g in obs:oc[(g[0],sum(int(m.WIDTH[x]) for x in g))][g[2]]+=1;ow[(g[0],sum(int(m.WIDTH[x]) for x in g))]+=1
    for g in gen:gc[(g[0],sum(int(m.WIDTH[x]) for x in g))][g[2]]+=1;gw[(g[0],sum(int(m.WIDTH[x]) for x in g))]+=1
    ctx=set(oc)|set(gc);den=sum(ow.values())+sum(gw.values())
    if not ctx or den<=0:return float('nan')
    val=0.;wt=0.
    for c in ctx:
        if not oc[c] or not gc[c]:continue
        w=(ow[c]+gw[c])/den;j=js_counts(oc[c],gc[c]);val+=w*j;wt+=w
    return val/wt if wt>0 else float('nan')

def local_metrics(obs,gen):
    def C(seq,fn):return Counter(fn(x) for x in seq)
    out={
      'H2_JSD':js_counts(C(obs,lambda g:g[1]),C(gen,lambda g:g[1])),
      'H3_JSD':js_counts(C(obs,lambda g:g[2]),C(gen,lambda g:g[2])),
      'H4_JSD':js_counts(C(obs,lambda g:g[3]),C(gen,lambda g:g[3])),
      'H3H4_JSD':js_counts(C(obs,lambda g:(g[2],g[3])),C(gen,lambda g:(g[2],g[3]))),
      'H1W_H3_JOINT_JSD':js_counts(C(obs,lambda g:(g[0],sum(int(m.WIDTH[x]) for x in g),g[2])),C(gen,lambda g:(g[0],sum(int(m.WIDTH[x]) for x in g),g[2]))),
      'H3_CONDITIONAL_JSD':cond_h3(obs,gen),
      'WIDTH_JSD':js_counts(C(obs,lambda g:sum(int(m.WIDTH[x]) for x in g)),C(gen,lambda g:sum(int(m.WIDTH[x]) for x in g))),
      'H2_WIDTH_JSD':js_counts(C(obs,lambda g:int(m.WIDTH[g[1]])),C(gen,lambda g:int(m.WIDTH[g[1]]))),
    }
    return out

def req_info(path):
    gen=[];q=Counter();cand=[];chg=[0,0,0];nchg=0
    with gzip.open(path,'rt') as f:
      for line in f:
        r=json.loads(line)
        is_w2=(r.get('role')=='W2' and r.get('board')=='W2')
        if is_w2 and r.get('first_len')==4:q['w2_exact4_requests']+=1;q['bt_on_exact4']+=int(bool(r.get('bt_enabled')))
        if r.get('w2_slot_applied'):
            q['slot_all']+=1;q['slot_fallback_all']+=int(bool(r.get('w2_slot_fallback')))
            if r.get('w2_slot_candidate_count') is not None:cand.append(int(r.get('w2_slot_candidate_count',0)))
            try:a=parse_word(r['w2_slot_anchor']);s=parse_word(r['w2_slot_selected'])
            except Exception:a=s=()
            if a and s:
                for k in range(1,4):chg[k-1]+=int(a[k]!=s[k])
                nchg+=1
        if r.get('h2splice_applied'):q['splice_all']+=1;q['splice_fallback_all']+=int(bool(r.get('h2splice_fallback_anchor')))
        if r.get('committed_to_final_page') and is_w2:
            try:g=parse_word(r.get('selected',''))
            except Exception:continue
            W=sum(int(m.WIDTH[x]) for x in g)
            if len(g)==4 and W in (4,5,6,7,8):gen.append(g)
            if r.get('w2_slot_applied'):
                q['slot_committed']+=1;q['slot_fallback_committed']+=int(bool(r.get('w2_slot_fallback')))
    return gen,q,cand,chg,nchg

def pval(x):
    x=np.asarray(x,float);x=x[np.isfinite(x)];x=x[np.abs(x)>1e-15]
    return 1. if len(x)==0 else float(wilcoxon(x,alternative='two-sided',method='approx').pvalue)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--runs',required=True);ap.add_argument('--arms',default='V20_COMPAT,SAFE_LEFT_BT_ON,SAFE_LEFT_BT_OFF,SLOT_BT_OFF');ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();runs=[int(x) for x in a.runs.split(',')];arms=a.arms.split(',');a.out.mkdir(parents=True,exist_ok=True)
    C=benv.e.context();F=list(benv.e.folds(C.bifs));real_docs={p:benv.e.real_doc(C,p) for p in C.seqs}
    grow=[];lrow=[];mrow=[]
    for fi,test in enumerate(F):
      train=[b for b in C.bifs if b not in test];train_docs=[real_docs[p] for b in train for p in C.pages[b]]
      for bif in test:
        page=C.pages[bif][-1];known=[real_docs[q] for q in C.pages[bif] if q!=page];judge=benv.e.Judges(train_docs,known);real=judge.score(real_docs[page],True)
        oe=prepare_w2_events(C.events,m.stable_width,[bif]);oe=oe[oe.page.astype(str)==str(page)];obs=[tuple(int(x) for x in g) for g in oe.glyphs]
        for run in runs:
          for arm in arms:
            p=a.root/f'run{run}'/ARM_GLOB[arm]/bif.replace(':','_')
            if not p.exists():raise FileNotFoundError(p)
            d=pd.read_csv(p/'tokens.csv.gz');gs=judge.score(benv.e.generated_doc(d),True)
            for j in GLOBAL:grow.append(dict(fold=fi,bif=bif,run=run,arm=arm,judge=j,value=abs(float(real[j]-gs[j]))))
            gen,q,cand,chg,nchg=req_info(p/'requests.jsonl.gz');lm=local_metrics(obs,gen)
            for j,v in lm.items():lrow.append(dict(fold=fi,bif=bif,run=run,arm=arm,judge=j,value=v,n_obs=len(obs),n_gen=len(gen)))
            md=json.load(open(p/'MECHANICAL.json'))
            mrow.append(dict(fold=fi,bif=bif,run=run,arm=arm,packing=bool(md.get('packing_exact')),support=int(md.get('support_violations',0)),invalid=int(md.get('invalid_rows',0)),slot_all=q['slot_all'],slot_committed=q['slot_committed'],fallback_all=q['slot_fallback_all'],fallback_committed=q['slot_fallback_committed'],splice_all=q['splice_all'],splice_fallback_all=q['splice_fallback_all'],w2_exact4_requests=q['w2_exact4_requests'],bt_on_exact4=q['bt_on_exact4'],candidate_mean=float(np.mean(cand)) if cand else float('nan'),h2_change=float(chg[0]/nchg) if nchg else float('nan'),h3_change=float(chg[1]/nchg) if nchg else float('nan'),h4_change=float(chg[2]/nchg) if nchg else float('nan')))
    G=pd.DataFrame(grow);L=pd.DataFrame(lrow);M=pd.DataFrame(mrow);G.to_csv(a.out/'global_scores.csv',index=False);L.to_csv(a.out/'local_scores.csv',index=False);M.to_csv(a.out/'mechanical_cases.csv',index=False)
    allscores=pd.concat([G[['bif','run','arm','judge','value']],L[['bif','run','arm','judge','value']]],ignore_index=True)
    leaf=allscores.groupby(['bif','arm','judge'],as_index=False).value.mean();leaf.to_csv(a.out/'leaf_means.csv',index=False)
    abs_=leaf.groupby(['arm','judge'],as_index=False).value.mean();abs_.to_csv(a.out/'absolute.csv',index=False)
    paired=[]
    base='SAFE_LEFT_BT_OFF';slot='SLOT_BT_OFF'
    for j in GLOBAL+LOCAL:
      b=leaf[(leaf.arm==base)&(leaf.judge==j)].set_index('bif').value;s=leaf[(leaf.arm==slot)&(leaf.judge==j)].set_index('bif').value;x=(b-s).dropna()
      paired.append(dict(reference=base,arm=slot,judge=j,improvement=float(x.mean()) if len(x) else float('nan'),wins=int((x>0).sum()),losses=int((x<0).sum()),ties=int((x==0).sum()),p=pval(x.values)))
    P=pd.DataFrame(paired);P.to_csv(a.out/'paired_safeoff_vs_slot.csv',index=False)
    mm=M.groupby('arm').agg(cases=('bif','size'),packing=('packing','all'),support=('support','sum'),invalid=('invalid','sum'),slot_all=('slot_all','sum'),slot_committed=('slot_committed','sum'),fallback_all=('fallback_all','sum'),fallback_committed=('fallback_committed','sum'),splice_all=('splice_all','sum'),splice_fallback_all=('splice_fallback_all','sum'),w2_exact4_requests=('w2_exact4_requests','sum'),bt_on_exact4=('bt_on_exact4','sum'),candidate_mean=('candidate_mean','mean'),h2_change=('h2_change','mean'),h3_change=('h3_change','mean'),h4_change=('h4_change','mean')).reset_index();mm['fallback_rate_all']=mm.fallback_all/mm.slot_all.replace(0,np.nan);mm['fallback_rate_committed']=mm.fallback_committed/mm.slot_committed.replace(0,np.nan);mm.to_csv(a.out/'mechanical_summary.csv',index=False)
    summary={'runs':runs,'arms':arms,'cases_per_arm':20*len(runs),'paired':P.to_dict('records'),'mechanical':mm.to_dict('records')}
    (a.out/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2,default=str))
if __name__=='__main__':main()
