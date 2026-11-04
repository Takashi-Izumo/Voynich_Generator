from __future__ import annotations
import os,sys,json,math
from pathlib import Path
from collections import Counter
import numpy as np,pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

ST=Path('/mnt/data/puv_handoff/RMW1_BTI2_EHC2_DECOMP1_PUV_HANDOFF_COMPACT_20260912/current_model/RMW1_BTI2_EHC2_DECOMP1_STAGE6_20260911')
P=Path('/mnt/data/_parent_ehc1_all/EHC1_E1GLOBAL_20260911')
os.environ['EHC2_STAGE6_PARENT']=str(P);sys.path.insert(0,str(ST/'code'))
from stage6_env import *
import experiment_env as benv

PARENT_ROOT=Path('/mnt/data/leafex_full_validation_20260912')
CAND_ROOT=Path('/mnt/data/w2h2splice_l4only_full_20260912')
OUT=Path('/mnt/data/w2h2splice_l4only_judge_20260912');OUT.mkdir(parents=True,exist_ok=True)
RUNS=[91321,91322,91323,91324,91325]
PRIMARY=['SPACE_RAW','H2_RAW']
HEAD_GROUP=['H3_HEAD_RAW','HEAD_H1_RAW','HEAD_shape','HEAD_vertical','LF_shape','glyph_depth','length_width']
REG=['route56','bT_LL','bT_leaf_excess','bT_active','bT_presence_log','ng','bigram','trigram']

def group_for(j):
    if j in PRIMARY:return 'PRIMARY'
    if j in HEAD_GROUP:return 'HEAD'
    if j in REG:return 'REGRESSION'
    return 'OTHER'

def boot_ci(x,seed=20260912,B=20000):
    x=np.asarray(x,float);rng=np.random.default_rng(seed);n=len(x)
    if n==0:return (np.nan,np.nan)
    means=np.empty(B)
    for i in range(B):means[i]=x[rng.integers(0,n,n)].mean()
    return float(np.quantile(means,.025)),float(np.quantile(means,.975))

def holm(p):
    p=np.asarray(p,float);n=len(p);order=np.argsort(p);out=np.empty(n,float);mx=0
    for rank,idx in enumerate(order):
        val=min(1.0,(n-rank)*p[idx]);mx=max(mx,val);out[idx]=mx
    return out

def arm_path(arm,run,bif):
    if arm=='PARENT':return PARENT_ROOT/f'run{run}'/'PUV_R4_LEXCV'/bif.replace(':','_')
    if arm=='H2SPLICE':return CAND_ROOT/f'run{run}'/'W2H2SPLICE_L4ONLY_ON'/bif.replace(':','_')
    if arm=='BTI2_BASE':return ST/'outputs/confirmation/generated'/f'run{run}'/'BTI2_BASE'/bif.replace(':','_')
    raise KeyError(arm)

def glyphs(r,I2G):
    if 'glyph_names' in r:return tuple(r.get('glyph_names') or ())
    return tuple(I2G[int(x)] for x in r.get('glyphs',()))

def w2_events(doc,I2G):
    out=[]
    for r in doc['raw_events']:
        gl=glyphs(r,I2G)
        if r.get('base_role')!='W2' or not r.get('position_eligible',True) or len(gl)<2:continue
        state='L3' if len(gl)==3 else ('L4P' if len(gl)>=4 else 'L2')
        out.append((gl[0],gl[1],state,r.get('row_phase','?'),len(gl)))
    return out

def jsd_tokens(a,b):
    ca,cb=Counter(a),Counter(b);keys=set(ca)|set(cb)
    if not keys:return 0.0
    na=sum(ca.values());nb=sum(cb.values())
    if na==0 or nb==0:return np.nan
    p=np.array([ca[k]/na for k in keys],float);q=np.array([cb[k]/nb for k in keys],float);m=.5*(p+q)
    def kl(x,y):
        z=x>0;return float(np.sum(x[z]*np.log2(x[z]/y[z])))
    return .5*(kl(p,m)+kl(q,m))

def local_feat(doc,kind,I2G):
    ev=w2_events(doc,I2G);out=[]
    for h1,h2,state,phase,L in ev:
        if kind=='W2_H2':out.append('H2='+h2)
        elif kind=='W2_H1H2':out.append(h1+'>'+h2)
        elif kind=='W2_LEN_H1H2':out.append(state+':'+h1+'>'+h2)
        elif kind=='W2_PHASE_H1H2':out.append(str(phase)+'|'+h1+'>'+h2)
        else:raise KeyError(kind)
    return out or ['EMPTY']

def tfidf_model(training,known,kind,I2G):
    texts=[' '.join(local_feat(d,kind,I2G)) for d in training+known]
    v=TfidfVectorizer(token_pattern=r'[^ ]+',lowercase=False,sublinear_tf=True,norm='l2',min_df=1)
    v.fit(texts);P=np.asarray(v.transform([' '.join(local_feat(d,kind,I2G)) for d in known]).mean(axis=0)).ravel();P/=max(np.linalg.norm(P),1e-15)
    return v,P

def tfidf_score(doc,v,P,kind,I2G):return float(v.transform([' '.join(local_feat(doc,kind,I2G))]).dot(P)[0])

def pairs_real(E):
    out=[]
    for loc,g in E.groupby('locus',sort=False):
        rr=g.to_dict('records')
        for i in range(1,len(rr)):
            a,b=rr[i-1],rr[i]
            if b['entry_eligible'] and a['raw_item_index']+1==b['raw_item_index']:
                out.append(dict(page=b['page'],bif=b['bif'],phase=b['row_phase'],board=b['board'],T=int(a['glyphs'][-1]),H1=int(b['glyphs'][0])))
    return pd.DataFrame(out)

def pairs_gen(d):
    rr=benv.e.generated_doc(d)['raw_events'];out=[]
    for a,b in zip(rr[:-1],rr[1:]):
        ga,gb=a['glyph_names'],b['glyph_names']
        if ga and gb and a['locus']==b['locus'] and a['segment_id']==b['segment_id']:
            out.append(dict(phase=b['row_phase'],board=b['board'],T=benv.e.m.G2I[ga[-1]],H1=benv.e.m.G2I[gb[0]]))
    return pd.DataFrame(out)

def values(df,co):return list(zip(df['T'].to_numpy(),df['H1'].to_numpy())) if co=='TH1' else list(df[co])

C=benv.e.context();FOLDS=list(benv.e.folds(C.bifs));I2G=benv.e.m.I2G
real_docs={p:benv.e.real_doc(C,p) for p in C.seqs};R=pairs_real(C.events)

# All standard judges and metrics
scores=[];metrics=[];bdist=[];mechanical=[];local_scores=[];local_jsd=[];local_len=[]
features=['W2_H2','W2_H1H2','W2_LEN_H1H2','W2_PHASE_H1H2']
for fi,test in enumerate(FOLDS):
    train=[b for b in C.bifs if b not in test];train_pages=[p for b in train for p in C.pages[b]];train_docs=[real_docs[p] for p in train_pages]
    for bif in test:
        page=C.pages[bif][-1];known_pages=[q for q in C.pages[bif] if q!=page];known_docs=[real_docs[q] for q in known_pages];target=real_docs[page]
        judge=benv.e.Judges(train_docs,known_docs);real=judge.score(target,True);rp=R[R.page.eq(page)]
        lmods={k:tfidf_model(train_docs,known_docs,k,I2G) for k in features}; lreal={k:tfidf_score(target,*lmods[k],k,I2G) for k in features}; ltoks={k:local_feat(target,k,I2G) for k in features}
        for run in RUNS:
            for arm in ['PARENT','H2SPLICE','BTI2_BASE']:
                loc=arm_path(arm,run,bif);d=pd.read_csv(loc/'tokens.csv.gz');gd=benv.e.generated_doc(d);gs=judge.score(gd,True)
                for j in real:
                    mar=float(real[j]-gs[j]);scores.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,judge=j,real_score=float(real[j]),gen_score=float(gs[j]),margin=mar,abs_margin=abs(mar)))
                metrics.append(benv.e.metric_row(C,page,d,arm,run,bif,fi));gp=pairs_gen(d)
                for co in ['T','H1','TH1']:bdist.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,component=co,target_JSD=benv.e.jsd(values(rp,co),values(gp,co))))
                md=json.loads((loc/'MECHANICAL.json').read_text());mechanical.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,packing=md['packing_exact'],retries=md.get('segment_retries',0),support_violations=md.get('support_violations',0),invalid_rows=md.get('invalid_rows',0),max_norm=md.get('max_normalization_error',0.0),tokens=md.get('tokens'),types=md.get('types'),hapax=md.get('hapax')))
                for k in features:
                    gsc=tfidf_score(gd,*lmods[k],k,I2G);rs=lreal[k];local_scores.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,judge=k,real_score=rs,gen_score=gsc,abs_margin=abs(rs-gsc)))
                    local_jsd.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,judge=k,target_JSD=jsd_tokens(ltoks[k],local_feat(gd,k,I2G))))
                # direct per length pair JSD
                tev=w2_events(target,I2G);gev=w2_events(gd,I2G)
                for state in ['L3','L4P']:
                    rt=[h1+'>'+h2 for h1,h2,st,ph,L in tev if st==state] or ['EMPTY']; gt=[h1+'>'+h2 for h1,h2,st,ph,L in gev if st==state] or ['EMPTY']
                    local_len.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,state=state,target_JSD=jsd_tokens(rt,gt)))
        print('JUDGED',fi,bif,flush=True)

S=pd.DataFrame(scores);M=pd.DataFrame(metrics);B=pd.DataFrame(bdist);Q=pd.DataFrame(mechanical);LS=pd.DataFrame(local_scores);LJ=pd.DataFrame(local_jsd);LL=pd.DataFrame(local_len)
S.to_csv(OUT/'scores_by_leaf_run.csv',index=False);M.to_csv(OUT/'metrics_by_leaf_run.csv',index=False);B.to_csv(OUT/'boundary_jsd_by_leaf_run.csv',index=False);Q.to_csv(OUT/'mechanical_by_leaf_run.csv',index=False);LS.to_csv(OUT/'local_tfidf_by_leaf_run.csv',index=False);LJ.to_csv(OUT/'local_jsd_by_leaf_run.csv',index=False);LL.to_csv(OUT/'local_length_jsd_by_leaf_run.csv',index=False)

# summaries candidate vs parent and BTI2
rows=[]
for ref in ['PARENT','BTI2_BASE']:
    z=S[S.arm.eq('H2SPLICE')].merge(S[S.arm.eq(ref)],on=['fold','bif','page','run','judge'],suffixes=('_new','_ref'),validate='one_to_one')
    for j,g in z.groupby('judge'):
        leaf=g.assign(diff=g.abs_margin_ref-g.abs_margin_new).groupby('bif')['diff'].mean();a=float(g.abs_margin_ref.mean());n=float(g.abs_margin_new.mean());lo,hi=boot_ci(leaf,20260912+sum(map(ord,j+ref)))
        rows.append(dict(reference=ref,judge=j,group=group_for(j),ref_abs=a,new_abs=n,change_pct_vs_ref=100*(n/a-1) if a>1e-15 else np.nan,improvement_ref_minus_new=float(leaf.mean()),leaves_improved=int((leaf>1e-12).sum()),leaves_worsened=int((leaf<-1e-12).sum()),p_two=float(benv.e.signflip(leaf)),bootstrap95_lo=lo,bootstrap95_hi=hi))
PAI=pd.DataFrame(rows);PAI['p_holm']=np.nan
for (ref,grp),idx in PAI.groupby(['reference','group']).groups.items():PAI.loc[idx,'p_holm']=benv.e.holm(PAI.loc[idx,'p_two'].to_numpy())
PAI.to_csv(OUT/'paired_judges.csv',index=False)

mr=[]
for ref in ['PARENT','BTI2_BASE']:
    z=M[M.arm.eq('H2SPLICE')].merge(M[M.arm.eq(ref)],on=['fold','bif','page','run'],suffixes=('_new','_ref'),validate='one_to_one')
    for c in [x[3:] for x in M.columns if x.startswith('ae_')]:
        leaf=z.assign(diff=z['ae_'+c+'_ref']-z['ae_'+c+'_new']).groupby('bif')['diff'].mean();a=float(z['ae_'+c+'_ref'].mean());n=float(z['ae_'+c+'_new'].mean());lo,hi=boot_ci(leaf,20261012+sum(map(ord,c+ref)))
        mr.append(dict(reference=ref,metric=c,ref_MAE=a,new_MAE=n,change_pct_vs_ref=100*(n/a-1) if a>1e-15 else np.nan,improvement=float(leaf.mean()),leaves_improved=int((leaf>1e-12).sum()),leaves_worsened=int((leaf<-1e-12).sum()),p_two=float(benv.e.signflip(leaf)),bootstrap95_lo=lo,bootstrap95_hi=hi))
PM=pd.DataFrame(mr);PM.to_csv(OUT/'paired_metrics.csv',index=False)

br=[]
for ref in ['PARENT','BTI2_BASE']:
    z=B[B.arm.eq('H2SPLICE')].merge(B[B.arm.eq(ref)],on=['fold','bif','page','run','component'],suffixes=('_new','_ref'),validate='one_to_one')
    for co,g in z.groupby('component'):
        leaf=g.assign(diff=g.target_JSD_ref-g.target_JSD_new).groupby('bif')['diff'].mean();a=float(g.target_JSD_ref.mean());n=float(g.target_JSD_new.mean());lo,hi=boot_ci(leaf,20261112+sum(map(ord,co+ref)))
        br.append(dict(reference=ref,component=co,ref_JSD=a,new_JSD=n,change_pct_vs_ref=100*(n/a-1),improvement=float(leaf.mean()),leaves_improved=int((leaf>1e-12).sum()),leaves_worsened=int((leaf<-1e-12).sum()),p_two=float(benv.e.signflip(leaf)),bootstrap95_lo=lo,bootstrap95_hi=hi))
PB=pd.DataFrame(br);PB.to_csv(OUT/'paired_boundary.csv',index=False)

# local summaries
lout=[]
for metric,DF,col in [('TFIDF',LS,'abs_margin'),('JSD',LJ,'target_JSD')]:
    for ref in ['PARENT','BTI2_BASE']:
        z=DF[DF.arm.eq('H2SPLICE')].merge(DF[DF.arm.eq(ref)],on=['fold','bif','page','run','judge'],suffixes=('_new','_ref'),validate='one_to_one')
        for j,g in z.groupby('judge'):
            leaf=g.assign(diff=g[f'{col}_ref']-g[f'{col}_new']).groupby('bif')['diff'].mean();a=float(g[f'{col}_ref'].mean());n=float(g[f'{col}_new'].mean());lo,hi=boot_ci(leaf,20261212+sum(map(ord,metric+j+ref)))
            lout.append(dict(metric=metric,reference=ref,judge=j,ref_value=a,new_value=n,change_pct_vs_ref=100*(n/a-1),improvement=float(leaf.mean()),leaves_improved=int((leaf>1e-12).sum()),leaves_worsened=int((leaf<-1e-12).sum()),p_two=float(benv.e.signflip(leaf)),bootstrap95_lo=lo,bootstrap95_hi=hi))
PL=pd.DataFrame(lout);PL.to_csv(OUT/'local_summary.csv',index=False)

llout=[]
for ref in ['PARENT','BTI2_BASE']:
    z=LL[LL.arm.eq('H2SPLICE')].merge(LL[LL.arm.eq(ref)],on=['fold','bif','page','run','state'],suffixes=('_new','_ref'),validate='one_to_one')
    for st,g in z.groupby('state'):
        leaf=g.assign(diff=g.target_JSD_ref-g.target_JSD_new).groupby('bif')['diff'].mean();a=float(g.target_JSD_ref.mean());n=float(g.target_JSD_new.mean());lo,hi=boot_ci(leaf,20261312+sum(map(ord,st+ref)))
        llout.append(dict(reference=ref,state=st,ref_JSD=a,new_JSD=n,change_pct_vs_ref=100*(n/a-1),improvement=float(leaf.mean()),leaves_improved=int((leaf>1e-12).sum()),leaves_worsened=int((leaf<-1e-12).sum()),p_two=float(benv.e.signflip(leaf)),bootstrap95_lo=lo,bootstrap95_hi=hi))
PLL=pd.DataFrame(llout);PLL.to_csv(OUT/'local_length_summary.csv',index=False)

audit=dict(status='PASS' if len(Q)==300 and Q.packing.all() and Q.support_violations.sum()==0 and Q.invalid_rows.sum()==0 else 'FAIL',rows=int(len(Q)),packing_all=bool(Q.packing.all()),support_violations=int(Q.support_violations.sum()),invalid_rows=int(Q.invalid_rows.sum()),max_norm=float(Q.max_norm.max()))
json.dump(audit,open(OUT/'AUDIT.json','w'),indent=2)
print('\nKEY STANDARD vs PARENT')
print(PAI[(PAI.reference=='PARENT') & PAI.judge.isin(['bigram','ng','trigram','SPACE_RAW','H2_RAW','glyph_depth','length_width','route56','bT_leaf_excess'])].to_string(index=False))
print('\nLOCAL vs PARENT')
print(PL[PL.reference.eq('PARENT')].to_string(index=False))
print('\nLOCAL LEN vs PARENT')
print(PLL[PLL.reference.eq('PARENT')].to_string(index=False))
print('\nAUDIT',audit)
