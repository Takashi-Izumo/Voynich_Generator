from __future__ import annotations
import os,sys,argparse,json,math
from pathlib import Path
from collections import Counter
import numpy as np,pandas as pd
from scipy.stats import binomtest

GLYPHS=['q','cfh','ch','cph','cth','p','sh','ckh','f','k','o','t','a','d','e','s','i','l','y','r','m','n']
COMPOUNDS=['cfh','ckh','cph','cth','ch','sh']; G2I={g:i for i,g in enumerate(GLYPHS)}
def tok(s):
    s=str(s); out=[]; i=0
    while i<len(s):
        hit=None
        for c in COMPOUNDS:
            if s.startswith(c,i): hit=c; break
        if hit is not None: out.append(G2I[hit]); i+=len(hit)
        else:
            if s[i] not in G2I: return None
            out.append(G2I[s[i]]); i+=1
    return tuple(out)

def jsd_counts(a:Counter,b:Counter):
    keys=set(a)|set(b)
    if not keys: return 0.0
    pa=np.array([a.get(k,0.0) for k in keys],float); pb=np.array([b.get(k,0.0) for k in keys],float)
    if pa.sum()<=0 or pb.sum()<=0: return 1.0
    pa/=pa.sum(); pb/=pb.sum(); m=.5*(pa+pb)
    def kl(p,q):
        z=p>0; return float(np.sum(p[z]*np.log2(p[z]/q[z])))
    return .5*kl(pa,m)+.5*kl(pb,m)

def features_real(df):
    rows=[]
    for r in df.itertuples(index=False):
        g=tuple(r.glyphs)
        if not g: continue
        rows.append(dict(g=g, role=str(r.base_role), lf=bool(r.physical_final)))
    return rows

def features_gen(df):
    rows=[]
    for r in df.itertuples(index=False):
        g=tok(r.stable_surface)
        if not g: continue
        rows.append(dict(g=g, role=str(r.role), lf=bool(int(r.draw_segment_end))))
    return rows

def extract(rows,name):
    c=Counter()
    if name=='H1':
        for x in rows:
            if x['role']=='BODY' and len(x['g'])>=1: c[(x['g'][0],)]+=1
    elif name=='H1H2':
        for x in rows:
            if x['role']=='BODY' and len(x['g'])>=2: c[x['g'][:2]]+=1
    elif name=='H1H2H3':
        for x in rows:
            if x['role']=='BODY' and len(x['g'])>=3: c[x['g'][:3]]+=1
    elif name=='terminal':
        for x in rows:
            if x['role']=='BODY' and len(x['g'])>=1: c[(x['g'][-1],)]+=1
    elif name=='bT':
        for x in rows:
            if x['role']=='BODY' and len(x['g'])>=2: c[x['g'][-2:]]+=1
    elif name=='LF':
        # line-final word shape: full glyph sequence, exact shape
        for x in rows:
            if x['lf']: c[x['g']]+=1
    else: raise KeyError(name)
    return c

def exact_signflip(x):
    x=np.asarray(x,float); sums=np.zeros(1)
    for v in x: sums=np.concatenate([sums+v,sums-v])
    ob=x.sum(); eps=1e-12*max(1.,abs(ob)); return float(np.mean(np.abs(sums)>=abs(ob)-eps))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pkg',type=Path,required=True); ap.add_argument('--gen',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--model-dir',required=True); ap.add_argument('--label',required=True); args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(args.pkg/'model/code')); from runtime_bootstrap import prepare_runtime
    H,P,ST=prepare_runtime(); os.environ['EHC2_STAGE6_PARENT']=str(P); sys.path.insert(0,str(ST/'code')); import stage6_env,experiment_env as benv
    C=benv.e.context(); E=C.events.copy(); folds_list=list(benv.e.folds(C.bifs)); RUNS=range(91701,91711); names=['H1','H1H2','H1H2H3','terminal','bT','LF']
    realrows={p:features_real(E[E.page.eq(p)]) for p in C.seqs}
    scores=[]
    for fi,test in enumerate(folds_list):
        for bif in test:
            page=C.pages[bif][-1]; known=[q for q in C.pages[bif] if q!=page]
            kr=[]
            for p in known: kr.extend(realrows[p])
            kcounts={n:extract(kr,n) for n in names}; rcounts={n:extract(realrows[page],n) for n in names}
            real_score={n:-jsd_counts(rcounts[n],kcounts[n]) for n in names}
            for run in RUNS:
                d=pd.read_csv(args.gen/f'run{run}'/args.model_dir/bif.replace(':','_')/'tokens.csv.gz'); gr=features_gen(d)
                for n in names:
                    gs=-jsd_counts(extract(gr,n),kcounts[n]); rs=real_score[n]
                    scores.append(dict(fold=fi,bif=bif,page=page,run=run,judge=n,real_score=rs,generated_score=gs,margin=rs-gs,real_n=sum(rcounts[n].values()),known_n=sum(kcounts[n].values()),gen_n=sum(extract(gr,n).values())))
    S=pd.DataFrame(scores); S.to_csv(args.out/'SPECIALIZED_SCORES_200.csv',index=False)
    raw=[]; clu=[]; leaf=[]
    for n,g in S.groupby('judge',sort=False):
        w=int((g.margin>1e-12).sum()); t=int((g.margin.abs()<=1e-12).sum()); l=len(g)-w-t; nn=w+l
        raw.append(dict(judge=n,real_wins=w,generated_wins=l,ties=t,real_win_rate=w/nn if nn else np.nan,binom_p=float(binomtest(w,nn,.5).pvalue) if nn else 1,mean_margin=float(g.margin.mean()),mean_abs_margin=float(g.margin.abs().mean())))
        lv=g.groupby('bif').margin.mean(); w2=int((lv>1e-12).sum()); t2=int((lv.abs()<=1e-12).sum()); l2=len(lv)-w2-t2
        clu.append(dict(judge=n,real_wins=w2,generated_wins=l2,ties=t2,binom_p=float(binomtest(w2,w2+l2,.5).pvalue) if w2+l2 else 1,signflip_p=exact_signflip(lv),mean_leaf_margin=float(lv.mean()),mean_leaf_abs_margin=float(lv.abs().mean())))
        for b,v in lv.items(): leaf.append(dict(judge=n,bif=b,mean_margin=float(v)))
    pd.DataFrame(raw).to_csv(args.out/'SPECIALIZED_RAW.csv',index=False); pd.DataFrame(clu).to_csv(args.out/'SPECIALIZED_CLUSTER20.csv',index=False); pd.DataFrame(leaf).to_csv(args.out/'SPECIALIZED_BY_LEAF.csv',index=False)
    print(pd.DataFrame(raw).to_string(index=False)); print(pd.DataFrame(clu).to_string(index=False))
if __name__=='__main__': main()
