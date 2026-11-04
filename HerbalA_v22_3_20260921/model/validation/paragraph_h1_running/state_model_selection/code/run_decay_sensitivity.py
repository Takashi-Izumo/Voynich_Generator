import pandas as pd, numpy as np, math, os, json, warnings
from collections import Counter, defaultdict
from scipy.stats import wilcoxon
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'results_sensitivity'),exist_ok=True)
from sklearn.cluster import KMeans
warnings.filterwarnings('ignore')

ROOT=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'data')
OUT='/mnt/data/H1_STATE_PARAMETERIZATION_CONTEST_20260917'
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

from scipy.stats import wilcoxon
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'results_sensitivity'),exist_ok=True)
R=[0.80,0.85,0.88,0.90,0.92,0.94,0.95,0.96,0.97,0.98,0.99,1.0]
LAM=[24.,32.,48.]
rows=[]
for rho in R:
 for lam in LAM:
  acc={b:[0.,0.,0] for b in leaves}
  for c in online:
   zline=len(c['donor_lines']); did=[];w=[]
   for li,ids in enumerate(c['donor_lines']):
    lag=zline-1-li;ww=rho**lag
    for j in ids:did.append(j);w.append(ww)
   did=np.array(did,int);w=np.array(w,float)
   r=continuous_ratio(did,lam,w);a=event_loss(apply_ratio(c['target'],r),c['target']);z=acc[c['bif']];z[0]+=a;z[1]+=c['base_loss'];z[2]+=c['n']
  for b,z in acc.items():rows.append(dict(rho=rho,lam=lam,bif=b,adj=z[0],base=z[1],n=z[2],loss=z[0]/z[2],delta=(z[0]-z[1])/z[2]))
df=pd.DataFrame(rows);df.to_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'results_sensitivity','DECAY_FINE.csv'),index=False)
# nested choose excluding target leaf
sel=[]
for b in leaves:
 best=None;bestv=1e9
 for (rho,lam),g in df.groupby(['rho','lam']):
  h=g[g.bif!=b];v=h.adj.sum()/h.n.sum()
  if v<bestv:bestv=v;best=(rho,lam)
 r=df[(df.bif==b)&(df.rho==best[0])&(df.lam==best[1])].iloc[0];sel.append(r.to_dict()|{'cv_other':bestv})
sd=pd.DataFrame(sel);sd.to_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'results_sensitivity','DECAY_FINE_NESTED.csv'),index=False)
print('global')
g=df.groupby(['rho','lam']).agg(adj=('adj','sum'),base=('base','sum'),n=('n','sum'));g['loss']=g.adj/g.n;g['delta']=(g.adj-g.base)/g.n;print(g.sort_values('loss').head(15).to_string())
print('selected rho',sd.rho.value_counts().sort_index().to_dict(),'lam',sd.lam.value_counts().sort_index().to_dict())
print('nested loss',sd.adj.sum()/sd.n.sum(),'delta',(sd.adj.sum()-sd.base.sum())/sd.n.sum(),'better',(sd.delta<0).sum(),'p',wilcoxon(sd.delta,alternative='less').pvalue)
