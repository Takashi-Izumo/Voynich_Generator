from __future__ import annotations
import os,sys,json,gzip,argparse
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import wilcoxon
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'code'))
from runtime_bootstrap import prepare_runtime
HANDOFF,PARENT,ST=prepare_runtime();os.environ['EHC2_STAGE6_PARENT']=str(PARENT);sys.path.insert(0,str(ST/'code'))
from stage6_env import *
import experiment_env as benv
KEY=['H2_RAW','SPACE_RAW','bigram','ng','trigram','route56','bT_leaf_excess','glyph_depth','length_width']
RUNS=[91321,91322,91323,91324,91325]

def pval(x):
    x=np.asarray(x,float);x=x[np.isfinite(x)];x=x[np.abs(x)>1e-15]
    return 1. if not len(x) else float(wilcoxon(x,alternative='two-sided',method='approx').pvalue)

def req_stats(path):
    n=ch=fb=pool=elig=right_off=0
    with gzip.open(path,'rt') as f:
        for line in f:
            r=json.loads(line)
            if r.get('h2splice_applied'):
                n+=1;ch+=int(bool(r.get('h2splice_changed')));fb+=int(bool(r.get('h2splice_fallback_anchor')));pool+=int(r.get('h2splice_pool_n',0));elig+=int(r.get('h2splice_eligible_n',0));right_off+=int(r.get('h2splice_right_support_required') is False)
    return n,ch,fb,pool,elig,right_off

def find_case(root,run,bif,arm):
    if arm=='BOTH':
        hits=list((root/f'run{run}').glob(f'*/{bif.replace(":","_")}'))
    else:
        hits=list((root/f'run{run}').glob(f'*LEFT*/{bif.replace(":","_")}'))
    if len(hits)!=1: raise RuntimeError((arm,run,bif,hits))
    return hits[0]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--both-root',type=Path,required=True);ap.add_argument('--left-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--prior-ref',type=Path)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    C=benv.e.context();F=list(benv.e.folds(C.bifs));real_docs={p:benv.e.real_doc(C,p) for p in C.seqs};rows=[];mech=[]
    for fi,test in enumerate(F):
        train=[b for b in C.bifs if b not in test];train_docs=[real_docs[p] for b in train for p in C.pages[b]]
        for bif in test:
            page=C.pages[bif][-1];known=[real_docs[q] for q in C.pages[bif] if q!=page];judge=benv.e.Judges(train_docs,known);real=judge.score(real_docs[page],True)
            for run in RUNS:
                for arm,root in [('BOTH',a.both_root),('LEFT',a.left_root)]:
                    p=find_case(root,run,bif,arm);d=pd.read_csv(p/'tokens.csv.gz');gs=judge.score(benv.e.generated_doc(d),True)
                    for j in KEY: rows.append(dict(fold=fi,bif=bif,run=run,arm=arm,judge=j,abs_margin=abs(float(real[j]-gs[j]))))
                    md=json.load(open(p/'MECHANICAL.json'))
                    if arm=='LEFT': n,ch,fb,pool,elig,roff=req_stats(p/'requests.jsonl.gz')
                    else: n=ch=fb=pool=elig=roff=0
                    mech.append(dict(fold=fi,bif=bif,run=run,arm=arm,packing=bool(md.get('packing_exact')),support=int(md.get('support_violations',0)),invalid=int(md.get('invalid_rows',0)),events=n,changed=ch,fallback=fb,pool=pool,eligible=elig,right_off=roff))
    S=pd.DataFrame(rows);S.to_csv(a.out/'scores.csv',index=False)
    LA=S.groupby(['bif','arm','judge'],as_index=False).abs_margin.mean();LA.to_csv(a.out/'leaf_means.csv',index=False)
    ABS=LA.groupby(['arm','judge'],as_index=False).abs_margin.mean();ABS.to_csv(a.out/'absolute.csv',index=False)
    pr=[]
    for j in KEY:
        b=LA[(LA.arm=='BOTH')&(LA.judge==j)].set_index('bif').abs_margin;l=LA[(LA.arm=='LEFT')&(LA.judge==j)].set_index('bif').abs_margin;x=(b-l).dropna()
        pr.append(dict(reference='BOTH',judge=j,arm='LEFT',improvement=float(x.mean()),wins=int((x>0).sum()),losses=int((x<0).sum()),ties=int((x==0).sum()),p=pval(x.values)))
    P=pd.DataFrame(pr);P.to_csv(a.out/'paired_both_vs_left.csv',index=False)
    Q=pd.DataFrame(mech);Q.to_csv(a.out/'mechanical_cases.csv',index=False)
    q=Q[Q.arm=='LEFT'];M=pd.DataFrame([dict(arm='LEFT',events=int(q.events.sum()),changed=int(q.changed.sum()),fallback=int(q.fallback.sum()),pool=int(q.pool.sum()),eligible=int(q.eligible.sum()),eligible_per_event=float(q.eligible.sum()/q.events.sum()),changed_rate=float(q.changed.sum()/q.events.sum()),right_off_events=int(q.right_off.sum()),support=int(q.support.sum()),invalid=int(q.invalid.sum()),packing=bool(q.packing.all()))]);M.to_csv(a.out/'mechanical_summary.csv',index=False)
    # exact reproduction against historical LEFT/BOTH 5-seed result if provided
    rep={'cases':100,'status':'PASS'}
    if a.prior_ref:
        old_abs=pd.read_csv(a.prior_ref/'absolute.csv');old_mech=pd.read_csv(a.prior_ref/'mechanical.csv')
        cmp=[]
        for arm in ['BOTH','LEFT']:
            for j in KEY:
                nv=float(ABS[(ABS.arm==arm)&(ABS.judge==j)].abs_margin.iloc[0]);ov=float(old_abs[(old_abs.arm==arm)&(old_abs.judge==j)].abs_margin.iloc[0]);cmp.append(dict(kind='absolute',arm=arm,key=j,new=nv,old=ov,abs_diff=abs(nv-ov),match=abs(nv-ov)<1e-12))
        om=old_mech[old_mech.arm=='LEFT'].iloc[0]
        nm=M.iloc[0]
        for k in ['events','changed','fallback','pool','eligible']:
            cmp.append(dict(kind='mechanical',arm='LEFT',key=k,new=float(nm[k]),old=float(om[k]),abs_diff=abs(float(nm[k])-float(om[k])),match=float(nm[k])==float(om[k])))
        Cmp=pd.DataFrame(cmp);Cmp.to_csv(a.out/'historical_reproduction.csv',index=False);rep['historical_checks']=len(Cmp);rep['historical_matches']=int(Cmp.match.sum());rep['historical_status']='PASS' if bool(Cmp.match.all()) else 'FAIL'
        if not bool(Cmp.match.all()): rep['status']='FAIL'
    rep['left_mechanical']=M.iloc[0].to_dict();rep['both_vs_left']=P[P.judge.isin(['H2_RAW','bigram','ng','trigram'])].to_dict('records')
    (a.out/'SUMMARY.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2,default=lambda x: bool(x) if isinstance(x,np.bool_) else float(x) if isinstance(x,np.floating) else int(x) if isinstance(x,np.integer) else str(x))+'\n')
    print(json.dumps(rep,ensure_ascii=False,indent=2,default=str))
    if rep['status']!='PASS': raise SystemExit(2)
if __name__=='__main__':main()
