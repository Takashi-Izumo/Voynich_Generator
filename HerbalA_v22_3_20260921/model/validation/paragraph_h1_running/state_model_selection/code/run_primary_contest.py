import pandas as pd, numpy as np, math, os, json, warnings
from collections import Counter, defaultdict
from scipy.stats import wilcoxon
from sklearn.cluster import KMeans
warnings.filterwarnings('ignore')

ROOT=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data')
OUT=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'results_primary')
os.makedirs(OUT,exist_ok=True)

E=pd.read_csv(ROOT+'/data/events.csv.gz')
T=pd.read_csv(ROOT+'/data/full_segment_schedule_tokens.csv')
O=pd.read_csv(ROOT+'/data/observed_tokens_stable.csv',low_memory=False)[['global_order','n_glyph']]
GLYPHS=['q','cfh','ch','cph','cth','p','sh','ckh','f','k','o','t','a','d','e','s','i','l','y','r','m','n']
COMPOUNDS=['cfh','ckh','cph','cth','ch','sh']; G2I={g:i for i,g in enumerate(GLYPHS)}; V=len(GLYPHS)
def tok(s):
    out=[];i=0
    while i<len(s):
        hit=None
        for g in COMPOUNDS:
            if s.startswith(g,i):hit=g;break
        if hit is not None:out.append(G2I[hit]);i+=len(hit)
        else:
            if s[i] not in G2I: raise ValueError((s,s[i]))
            out.append(G2I[s[i]]);i+=1
    return tuple(out)

D=E.merge(T[['global_order','is_segment_end','is_para_final']],on='global_order').merge(O,on='global_order').sort_values('global_order').reset_index(drop=True)
D['glyphs']=D.surface.map(tok);D['H1']=D.glyphs.map(lambda x:int(x[0]))
comp=set(D.groupby('bif').page.nunique().loc[lambda x:x==4].index)
D=D[D.bif.isin(comp)].copy()
mask=(D.para_line_raw>=2)&(~D.is_para_final)&(D.base_role=='BODY')&(~D.is_segment_end)&(D.n_glyph>=2)
Q=D[mask].copy().reset_index(drop=True)
Q['tkey']=list(zip(Q.boundary_before.astype(str),Q.prev_terminal.astype(int)))
Q['ctx']=list(zip(Q.n_glyph.astype(int),Q.tkey))
leaves=sorted(comp)
A=16.; LL=64.

# Cross-fitted baseline: exact length + previous T + leaf-known3, as prior validation.
allY=Counter(Q.H1); bifY=defaultdict(Counter); total=defaultdict(Counter); bifc=defaultdict(lambda:defaultdict(Counter)); pagec=defaultdict(lambda:defaultdict(Counter)); lenc=defaultdict(Counter); biflen=defaultdict(lambda:defaultdict(Counter))
for _,r in Q.iterrows():
    b,p,y,ctx,L=str(r.bif),str(r.page),int(r.H1),r.ctx,int(r.n_glyph)
    bifY[b][y]+=1;total[ctx][y]+=1;bifc[b][ctx][y]+=1;pagec[p][ctx][y]+=1;lenc[L][y]+=1;biflen[b][L][y]+=1
base_probs=np.zeros((len(Q),V),float)
for i,r in Q.iterrows():
    b,p,ctx,L=str(r.bif),str(r.page),r.ctx,int(r.n_glyph)
    N=sum(allY.values())-sum(bifY[b].values())
    prior=np.array([(allY[y]-bifY[b][y]+.5)/(N+.5*V) for y in range(V)])
    nL=sum(lenc[L].values())-sum(biflen[b][L].values())
    pL=np.array([(lenc[L][y]-biflen[b][L][y]+A*prior[y])/(nL+A) for y in range(V)])
    nc=sum(total[ctx].values())-sum(bifc[b][ctx].values())
    pg=np.array([(total[ctx][y]-bifc[b][ctx][y]+A*pL[y])/(nc+A) for y in range(V)])
    nl=sum(bifc[b][ctx].values())-sum(pagec[p][ctx].values())
    pl=np.array([(bifc[b][ctx][y]-pagec[p][ctx][y]+LL*pg[y])/(nl+LL) for y in range(V)])
    base_probs[i]=pl/pl.sum()

# Paragraph lines, online cases. Each later eligible line is a target; only prior eligible lines may update state.
para_lines={}
for key,g in Q.groupby(['bif','page','para'],sort=False):
    lines=[]
    for loc,gg in g.groupby('locus',sort=False):
        lines.append((int(gg.global_order.min()),loc,gg.index.to_list()))
    para_lines[key]=sorted(lines)
online=[]
for key,lines in para_lines.items():
    if len(lines)<2: continue
    for z in range(1,len(lines)):
        donor_lines=[ids for _,_,ids in lines[:z]]
        target=lines[z][2]
        online.append(dict(key=key,bif=key[0],page=key[1],para=key[2],target_line=z,donor_lines=donor_lines,target=target))

# utility losses
LOG2=np.log(2.0)
def event_loss(probs, ids):
    ys=Q.loc[ids,'H1'].astype(int).to_numpy()
    pp=probs[np.arange(len(ids)),ys]
    return float(-np.log2(np.maximum(pp,1e-300)).sum())

def apply_ratio(ids, ratio):
    qb=base_probs[ids]*ratio[None,:]
    qb=np.maximum(qb,1e-300);qb/=qb.sum(axis=1,keepdims=True)
    return qb

def continuous_ratio(donor_ids, lam, weights=None):
    if weights is None:
        weights=np.ones(len(donor_ids),float)
    else: weights=np.asarray(weights,float)
    ys=Q.loc[donor_ids,'H1'].astype(int).to_numpy()
    Ocnt=np.bincount(ys,weights=weights,minlength=V).astype(float)
    Ecnt=(base_probs[donor_ids]*weights[:,None]).sum(axis=0)
    n=float(weights.sum())
    if n<=0:return np.ones(V)
    m=Ecnt/n
    s=(Ocnt+lam*m)/(n+lam)
    return s/np.maximum(m,1e-15)

# Precompute base loss per case.
for c in online:
    c['base_loss']=event_loss(base_probs[c['target']],c['target'])
    c['n']=len(c['target'])

# candidate scoring storage: family -> candidate -> leaf -> [adj_loss, base_loss, n]
CONT_LAM=[1.,2.,4.,8.,16.,32.,64.,128.,256.,1e12]
RHO=[0.0,0.25,0.5,0.7,0.85,0.95,0.99,1.0]
DISC_K=[1,2,3,4,5]
DISC_ALPHA=[32.]

# continuous running residual scores
cont={lam:{b:[0.,0.,0] for b in leaves} for lam in CONT_LAM}
decay={(rho,lam):{b:[0.,0.,0] for b in leaves} for rho in RHO for lam in CONT_LAM}
for c in online:
    b=c['bif'];target=c['target'];baseL=c['base_loss'];n=c['n']
    donor=[j for ids in c['donor_lines'] for j in ids]
    for lam in CONT_LAM:
        r=continuous_ratio(donor,lam)
        adjL=event_loss(apply_ratio(target,r),target)
        z=cont[lam][b];z[0]+=adjL;z[1]+=baseL;z[2]+=n
    # decay: immediate previous donor line weight 1; each earlier line rho^lag
    zline=len(c['donor_lines'])
    for rho in RHO:
        did=[];w=[]
        for li,ids in enumerate(c['donor_lines']):
            lag=zline-1-li
            ww=(rho**lag) if not (rho==0 and lag>0) else 0.0
            for j in ids: did.append(j);w.append(ww)
        did=np.array(did,dtype=int);w=np.array(w,float)
        keep=w>0;did=did[keep];w=w[keep]
        for lam in CONT_LAM:
            r=continuous_ratio(did,lam,w)
            adjL=event_loss(apply_ratio(target,r),target)
            z=decay[(rho,lam)][b];z[0]+=adjL;z[1]+=baseL;z[2]+=n

# paragraph residual vector for discrete prototype learning.
def para_feature(ids,alpha):
    ys=Q.loc[ids,'H1'].astype(int).to_numpy();n=len(ids)
    oc=np.bincount(ys,minlength=V).astype(float);ec=base_probs[ids].sum(axis=0);m=ec/n
    s=(oc+alpha*m)/(n+alpha);ratio=s/np.maximum(m,1e-15)
    return np.log(np.clip(ratio,1e-4,1e4))

def fit_discrete(held_leaf,K,alpha):
    keys=[]; feats=[]; ns=[]; Olist=[]; Elist=[]
    for key,lines in para_lines.items():
        if key[0]==held_leaf: continue
        ids=[j for _,_,x in lines for j in x]
        if len(ids)<3: continue
        keys.append(key);feats.append(para_feature(ids,alpha));ns.append(len(ids))
        ys=Q.loc[ids,'H1'].astype(int).to_numpy();Olist.append(np.bincount(ys,minlength=V).astype(float));Elist.append(base_probs[ids].sum(0))
    X=np.vstack(feats);ns=np.asarray(ns,float);Oa=np.vstack(Olist);Ea=np.vstack(Elist)
    if K==1:
        lab=np.zeros(len(keys),int)
    else:
        km=KMeans(n_clusters=K,random_state=917+K*100+int(alpha),n_init=4,max_iter=200)
        lab=km.fit_predict(X,sample_weight=ns)
    ratios=[];pri=[]
    for z in range(K):
        sel=(lab==z);nn=float(ns[sel].sum());oc=Oa[sel].sum(0);ec=Ea[sel].sum(0);m=ec/max(nn,1e-12)
        s=(oc+alpha*m)/(nn+alpha);r=s/np.maximum(m,1e-15)
        ratios.append(r);pri.append(float(sel.sum()))
    pri=np.array(pri,float);pri=(pri+0.5)/(pri.sum()+0.5*K)
    return np.vstack(ratios),pri

def discrete_case_loss(c,ratios,pri):
    # infer fixed paragraph state from past observed lines; posterior predictive mixture for target line
    K=len(pri);logpost=np.log(np.maximum(pri,1e-300))
    donor=[j for ids in c['donor_lines'] for j in ids]
    ys=Q.loc[donor,'H1'].astype(int).to_numpy()
    for z in range(K):
        q=apply_ratio(donor,ratios[z])
        logpost[z]+=np.log(np.maximum(q[np.arange(len(donor)),ys],1e-300)).sum()
    m=logpost.max();post=np.exp(logpost-m);post/=post.sum()
    target=c['target'];mix=np.zeros((len(target),V),float)
    for z in range(K):mix+=post[z]*apply_ratio(target,ratios[z])
    return event_loss(mix,target),float(-np.sum(post*np.log2(np.maximum(post,1e-300))))

disc={(K,a):{b:[0.,0.,0,0.,0] for b in leaves} for K in DISC_K for a in DISC_ALPHA} # loss, base,n, entropy sum,cases
for b in leaves:
    cases=[c for c in online if c['bif']==b]
    for K in DISC_K:
        for alpha in DISC_ALPHA:
            ratios,pri=fit_discrete(b,K,alpha)
            for c in cases:
                adjL,ent=discrete_case_loss(c,ratios,pri)
                z=disc[(K,alpha)][b];z[0]+=adjL;z[1]+=c['base_loss'];z[2]+=c['n'];z[3]+=ent;z[4]+=1

# Convert family candidate dicts to long CV matrix.
rows=[]
for lam,dct in cont.items():
    for b,z in dct.items(): rows.append(dict(family='CONTINUOUS',candidate=f'lambda={lam:g}',bif=b,adj=z[0],base=z[1],n=z[2],extra=np.nan))
for (rho,lam),dct in decay.items():
    for b,z in dct.items(): rows.append(dict(family='DECAY',candidate=f'rho={rho:g}|lambda={lam:g}',bif=b,adj=z[0],base=z[1],n=z[2],extra=rho))
for (K,a),dct in disc.items():
    for b,z in dct.items(): rows.append(dict(family='DISCRETE',candidate=f'K={K}|alpha={a:g}',bif=b,adj=z[0],base=z[1],n=z[2],extra=(z[3]/z[4] if z[4] else np.nan)))
C=pd.DataFrame(rows);C['loss']=C.adj/C.n;C['base_loss']=C.base/C.n;C['delta']=(C.adj-C.base)/C.n
C.to_csv(OUT+'/CANDIDATE_LEAF_SCORES.csv',index=False)

# Nested target-blind selection: for each target leaf, pick family candidate minimizing pooled loss on other leaves.
selected=[]
for fam in ['DISCRETE','CONTINUOUS','DECAY']:
    F=C[C.family==fam]
    for b in leaves:
        best=None;bestv=1e99
        for cand,g in F.groupby('candidate'):
            h=g[g.bif!=b];v=h.adj.sum()/h.n.sum()
            if v<bestv-1e-15:
                bestv=v;best=cand
        r=F[(F.bif==b)&(F.candidate==best)].iloc[0]
        selected.append(dict(family=fam,bif=b,candidate=best,n=int(r.n),base_loss=r.base_loss,loss=r.loss,delta=r.delta,extra=r.extra,cv_other_loss=bestv))
S=pd.DataFrame(selected)
S.to_csv(OUT+'/NESTED_SELECTED_LEAF.csv',index=False)

# summaries
summ=[]
for fam,g in S.groupby('family'):
    x=g.delta.to_numpy();w=g.n.to_numpy()
    try:p=float(wilcoxon(x,alternative='less').pvalue)
    except:p=np.nan
    summ.append(dict(family=fam,N=int(g.n.sum()),leaves=len(g),base=float(np.average(g.base_loss,weights=w)),loss=float(np.average(g.loss,weights=w)),weighted_delta=float(np.average(x,weights=w)),mean_leaf_delta=float(x.mean()),better=int((x<0).sum()),p_vs_base=p,total_bits_saved=float(-(g.delta*g.n).sum()),candidate_mode=g.candidate.mode().iloc[0]))
SUM=pd.DataFrame(summ).sort_values('loss')
# BH vs base
ps=SUM.p_vs_base.to_numpy();ordr=np.argsort(ps);m=len(ps);qs=np.zeros(m);prev=1.
for ri in range(m-1,-1,-1):
    i=ordr[ri];rank=ri+1;val=min(prev,ps[i]*m/rank);qs[i]=val;prev=val
SUM['q_vs_base']=qs
SUM.to_csv(OUT+'/SUMMARY.csv',index=False)

# pairwise direct on same leaves, lower is better
pairs=[]
fams=['DISCRETE','CONTINUOUS','DECAY']
for i in range(len(fams)):
    for j in range(i+1,len(fams)):
        a,b=fams[i],fams[j]
        ga=S[S.family==a].set_index('bif');gb=S[S.family==b].set_index('bif');d=(ga.loss-gb.loss).dropna()
        try:p2=float(wilcoxon(d,alternative='two-sided').pvalue);p_less=float(wilcoxon(d,alternative='less').pvalue)
        except:p2=p_less=np.nan
        pairs.append(dict(contrast=f'{a} - {b}',mean_leaf_diff=float(d.mean()),weighted_diff=float(np.average(d,weights=ga.loc[d.index,'n'])),a_better=int((d<0).sum()),b_better=int((d>0).sum()),n=len(d),p_two_sided=p2,p_a_better=p_less))
PAIR=pd.DataFrame(pairs);PAIR.to_csv(OUT+'/PAIRWISE.csv',index=False)

# Selection distributions.
selrows=[]
for fam,g in S.groupby('family'):
    for cand,n in g.candidate.value_counts().items():selrows.append(dict(family=fam,candidate=cand,leaves=int(n)))
SEL=pd.DataFrame(selrows);SEL.to_csv(OUT+'/HYPERPARAM_SELECTION.csv',index=False)

# decay rho selected, discrete K selected parsed
S2=S.copy()
S2['selected_K']=S2.apply(lambda r:int(r.candidate.split('|')[0].split('=')[1]) if r.family=='DISCRETE' else np.nan,axis=1)
S2['selected_rho']=S2.apply(lambda r:float(r.candidate.split('|')[0].split('=')[1]) if r.family=='DECAY' else np.nan,axis=1)
# winner by leaf
piv=S2.pivot(index='bif',columns='family',values='loss')
piv['winner']=piv.idxmin(axis=1);piv.to_csv(OUT+'/LEAF_WINNERS.csv')

# Additional fixed-candidate descriptive table: best global CV candidate per family chosen from all leaf-CV (not used for target evaluation selection, just interpretability)
fixed=[]
for fam in fams:
    f=C[C.family==fam]
    vals=[]
    for cand,g in f.groupby('candidate'): vals.append((g.adj.sum()/g.n.sum(),cand))
    vals.sort();loss,cand=vals[0]
    g=f[f.candidate==cand]
    fixed.append(dict(family=fam,candidate=cand,cv_loss=loss,weighted_delta=float((g.adj.sum()-g.base.sum())/g.n.sum()),better=int((g.delta<0).sum())))
FIX=pd.DataFrame(fixed);FIX.to_csv(OUT+'/GLOBAL_CV_BEST_CANDIDATES.csv',index=False)

meta={
 'date':'2026-09-17','events':int(len(Q)),'online_target_lines':int(len(online)),'online_target_events':int(sum(c['n'] for c in online)),'leaves':leaves,
 'baseline':'exact glyph length + previous terminal T + leaf-known-3 H1; cross-fitted as prior package',
 'target':'all BODY 2+ glyph, paragraph line >=2, non paragraph-final, non segment-end; each eligible line after the first predicted from prior eligible lines only',
 'discrete':'fixed paragraph latent state, K=1..6 prototypes learned from other leaves; target state posterior inferred only from past lines; K/alpha target-blind nested CV',
 'continuous':'all past same-paragraph H1 residuals pooled without decay; lambda target-blind nested CV',
 'decay':'same continuous residual with line-lag exponential weight rho^lag, immediate previous line weight 1; rho/lambda target-blind nested CV',
 'grids':{'continuous_lambda':CONT_LAM,'decay_rho':RHO,'discrete_K':DISC_K,'discrete_alpha':DISC_ALPHA}
}
with open(OUT+'/META.json','w') as f:json.dump(meta,f,ensure_ascii=False,indent=2)

print('\nSUMMARY')
print(SUM.to_string(index=False))
print('\nPAIRWISE')
print(PAIR.to_string(index=False))
print('\nSELECTION')
print(SEL.to_string(index=False))
print('\nWINNERS')
print(piv['winner'].value_counts().to_string())
print('\nDISCRETE K')
print(S2[S2.family=='DISCRETE'].selected_K.value_counts().sort_index().to_string())
print('\nDECAY rho')
print(S2[S2.family=='DECAY'].selected_rho.value_counts().sort_index().to_string())
