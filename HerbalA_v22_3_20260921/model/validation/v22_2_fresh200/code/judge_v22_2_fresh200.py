from __future__ import annotations
import os,sys,json,math
from pathlib import Path
from collections import Counter
import numpy as np,pandas as pd
from scipy.stats import binomtest, wilcoxon

PKG=Path('/mnt/data/_v22_2_judge/HerbalA_v22_2_F1LF_ROUTER_OFF_20260920')
PARENT_ROOT=Path('/mnt/data/v22_2_judge_parent')
CHILD_ROOT=Path('/mnt/data/v22_2_judge_child')
OUT=Path('/mnt/data/v22_2_judge_results'); OUT.mkdir(parents=True,exist_ok=True)
RUNS=[92001,92002,92003,92004,92005,92006,92007,92008,92009,92011]
ARMS={'PARENT':(PARENT_ROOT,'HerbalA_v22r_W2B2'),'V22_2':(CHILD_ROOT,'HerbalA_v22_2')}

sys.path.insert(0,str(PKG/'model/code'))
from runtime_bootstrap import prepare_runtime
H,P,ST=prepare_runtime(); os.environ['EHC2_STAGE6_PARENT']=str(P); sys.path.insert(0,str(ST/'code'))
import stage6_env, experiment_env as benv
C=benv.e.context(); E=C.events.copy(); FOLDS=list(benv.e.folds(C.bifs)); I2G=benv.e.m.I2G
REAL_DOCS={p:benv.e.real_doc(C,p) for p in C.seqs}

# paragraph line count for excluding single-line/paragraph-final FIRST
mx=E.groupby(['page','para']).para_line_raw.max().rename('para_max_line')
E=E.join(mx,on=['page','para'])

def exact_signflip(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)==0:return np.nan
    sums=np.zeros(1)
    for v in x: sums=np.concatenate((sums+v,sums-v))
    ob=float(x.sum()); eps=1e-12*max(1.,abs(ob))
    return float(np.mean(np.abs(sums)>=abs(ob)-eps))

def one_sided_wilcoxon(x, alternative='greater'):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    x=x[np.abs(x)>1e-15]
    if len(x)==0:return np.nan
    try:return float(wilcoxon(x,alternative=alternative,zero_method='wilcox').pvalue)
    except Exception:return np.nan

def jsd_counts(a:Counter,b:Counter):
    keys=set(a)|set(b)
    if not keys:return np.nan
    pa=np.array([a.get(k,0.0) for k in keys],float); pb=np.array([b.get(k,0.0) for k in keys],float)
    if pa.sum()<=0 or pb.sum()<=0:return np.nan
    pa/=pa.sum();pb/=pb.sum();m=.5*(pa+pb)
    def kl(p,q):
        z=p>0;return float(np.sum(p[z]*np.log2(p[z]/q[z])))
    return .5*(kl(pa,m)+kl(pb,m))

def gtuple_real(r): return tuple(int(x) for x in r.glyphs)

def parse_glyphs(s):
    # reuse stable parser from model module
    from f1lf_router_off_sampler import _parse_stable_word
    return tuple(_parse_stable_word(str(s)))

def real_f1lf(page):
    z=E[(E.page==page)&(E.base_role=='F1')&(E.row_phase=='FIRST')&(E.physical_final)&(E.segment_id==0)&(E.board=='LF')&(E.para_max_line>1)]
    return [gtuple_real(r) for r in z.itertuples(index=False)]

def gen_f1lf(d):
    z=d[(d.role=='F1')&(d.para_line_raw==1)&(d.segment_id==0)&(d.draw_segment_end==1)&(d.boundary_type=='LINE_END')&(d.pf_final_segment==0)]
    out=[]
    for s in z.stable_surface:
        try: out.append(parse_glyphs(s))
        except Exception: pass
    return out

def feat_counts(words,kind):
    c=Counter()
    if kind=='WORD':
        c.update(words)
    elif kind=='TERM':
        c.update((w[-1],) for w in words if w)
    elif kind=='FAMILY':
        for w in words:
            if not w:continue
            g=I2G[w[-1]]
            fam='NMY' if g in {'n','m','y'} else ('LR' if g in {'l','r'} else 'OTHER')
            c[(fam,)]+=1
    elif kind=='BIGRAM':
        for w in words:
            c.update(tuple(w[i:i+2]) for i in range(max(0,len(w)-1)))
    elif kind=='TRIGRAM':
        for w in words:
            c.update(tuple(w[i:i+3]) for i in range(max(0,len(w)-2)))
    elif kind=='ROUTE56':
        for w in words:
            for n in (5,6): c.update(tuple(w[i:i+n]) for i in range(max(0,len(w)-n+1)))
    else: raise KeyError(kind)
    return c

def comps(words):
    n=max(len(words),1)
    cnt=Counter(I2G[w[-1]] for w in words if w)
    return {'y':cnt['y']/n,'n':cnt['n']/n,'NMY':sum(cnt[x] for x in ['n','m','y'])/n,'LR':sum(cnt[x] for x in ['l','r'])/n}

def arm_path(arm,run,bif):
    root,model=ARMS[arm]; return root/f'run{run}'/model/bif.replace(':','_')

# Standard frozen judges and global metric rows
std=[]; metric=[]; mech=[]; local=[]; components=[]; directdiff=[]
KINDS=['WORD','TERM','FAMILY','BIGRAM','TRIGRAM','ROUTE56']
for fi,test in enumerate(FOLDS):
    train=[b for b in C.bifs if b not in test]
    train_pages=[p for b in train for p in C.pages[b]]
    train_docs=[REAL_DOCS[p] for p in train_pages]
    for bif in test:
        page=C.pages[bif][-1]; known=[q for q in C.pages[bif] if q!=page]
        judge=benv.e.Judges(train_docs,[REAL_DOCS[q] for q in known]); real_scores=judge.score(REAL_DOCS[page],True)
        rw=real_f1lf(page); rc={k:feat_counts(rw,k) for k in KINDS}; rcomp=comps(rw)
        for run in RUNS:
            docs={}
            for arm in ARMS:
                loc=arm_path(arm,run,bif)
                d=pd.read_csv(loc/'tokens.csv.gz'); docs[arm]=d; gd=benv.e.generated_doc(d); gs=judge.score(gd,True)
                for j in ['word','ng','bigram','trigram','route56','combined']:
                    std.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,judge=j,real_score=float(real_scores[j]),gen_score=float(gs[j]),margin=float(real_scores[j]-gs[j]),abs_margin=abs(float(real_scores[j]-gs[j]))))
                mr=benv.e.metric_row(C,page,d,arm,run,bif,fi); metric.append(mr)
                md=json.loads((loc/'MECHANICAL.json').read_text())
                mech.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,packing=bool(md.get('packing_exact',False)),support=int(md.get('support_violations',0)),invalid=int(md.get('invalid_rows',0)),retry=int(md.get('segment_retries',0)),tokens=md.get('tokens'),types=md.get('types'),hapax=md.get('hapax')))
                gw=gen_f1lf(d); gc={k:feat_counts(gw,k) for k in KINDS}; gcomp=comps(gw)
                for k in KINDS:
                    dist=jsd_counts(rc[k],gc[k]) if len(rw)>0 else np.nan
                    local.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,judge='F1LF_'+k,real_n=len(rw),gen_n=len(gw),direct_target_jsd=dist))
                for co in ['y','n','NMY','LR']:
                    components.append(dict(fold=fi,bif=bif,page=page,run=run,arm=arm,component=co,real_n=len(rw),gen_n=len(gw),real=rcomp[co],gen=gcomp[co],abs_err=abs(rcomp[co]-gcomp[co])))
            # direct output change audit parent vs child by row key
            a=docs['PARENT']; b=docs['V22_2']; keys=['locus','para','para_line_raw','segment_id','line_wordnum','segment_wordnum']
            mm=a.merge(b,on=keys,suffixes=('_p','_c'),how='outer',indicator=True)
            same_shape=bool((mm._merge=='both').all())
            changed=(mm._merge!='both') | (mm.stable_surface_p.fillna('')!=mm.stable_surface_c.fillna(''))
            # child direct scope row classification
            direct=(mm.role_c.eq('F1') & mm.para_line_raw.eq(1) & mm.segment_id.eq(0) & mm.draw_segment_end_c.eq(1) & mm.boundary_type_c.eq('LINE_END') & mm.pf_final_segment_c.eq(0))
            directdiff.append(dict(fold=fi,bif=bif,page=page,run=run,row_alignment_exact=same_shape,total_changed=int(changed.sum()),direct_scope_changed=int((changed&direct).sum()),downstream_changed=int((changed&~direct).sum())))
        print('JUDGED',fi,bif,flush=True)

S=pd.DataFrame(std); M=pd.DataFrame(metric); Q=pd.DataFrame(mech); L=pd.DataFrame(local); Cmp=pd.DataFrame(components); D=pd.DataFrame(directdiff)
S.to_csv(OUT/'01_standard_scores.csv',index=False); M.to_csv(OUT/'02_global_metrics.csv',index=False); Q.to_csv(OUT/'03_mechanical.csv',index=False); L.to_csv(OUT/'04_f1lf_direct_jsd.csv',index=False); Cmp.to_csv(OUT/'05_f1lf_components.csv',index=False); D.to_csv(OUT/'06_output_diff_audit.csv',index=False)

# Standard summaries arm vs real and paired child vs parent closeness-to-zero
std_rows=[]; pair_rows=[]
for arm in ARMS:
    for j,g in S[S.arm==arm].groupby('judge'):
        lv=g.groupby('bif').margin.mean(); w=int((lv>1e-12).sum()); t=int((lv.abs()<=1e-12).sum()); l=len(lv)-w-t
        std_rows.append(dict(arm=arm,judge=j,real_wins=w,generated_wins=l,ties=t,binom_p=float(binomtest(w,w+l,.5).pvalue) if w+l else 1.0,signflip_p=exact_signflip(lv),mean_leaf_margin=float(lv.mean()),mean_abs_margin=float(g.abs_margin.mean())))
for j in S.judge.unique():
    p=S[(S.arm=='PARENT')&(S.judge==j)].groupby('bif').agg(parent=('abs_margin','mean'))
    c=S[(S.arm=='V22_2')&(S.judge==j)].groupby('bif').agg(child=('abs_margin','mean'))
    z=p.join(c); z['improve']=z.parent-z.child
    pair_rows.append(dict(judge=j,parent_abs=float(z.parent.mean()),child_abs=float(z.child.mean()),improvement=float(z.improve.mean()),leaves_improved=int((z.improve>1e-12).sum()),leaves_worsened=int((z.improve<-1e-12).sum()),ties=int((z.improve.abs()<=1e-12).sum()),signflip_p=exact_signflip(z.improve),wilcoxon_greater=one_sided_wilcoxon(z.improve,'greater')))
STD=pd.DataFrame(std_rows); PAIR=pd.DataFrame(pair_rows); STD.to_csv(OUT/'10_standard_cluster20.csv',index=False); PAIR.to_csv(OUT/'11_standard_parent_child.csv',index=False)

# F1LF direct JSD summary on leaves with target event(s)
loc_rows=[]
for j in L.judge.unique():
    piv=[]
    for arm in ARMS:
        gg=L[(L.arm==arm)&(L.judge==j)&(L.real_n>0)].groupby('bif').direct_target_jsd.mean().rename(arm)
        piv.append(gg)
    z=pd.concat(piv,axis=1).dropna(); z['improve']=z.PARENT-z.V22_2
    loc_rows.append(dict(judge=j,n_leaves=len(z),parent_jsd=float(z.PARENT.mean()),child_jsd=float(z.V22_2.mean()),improvement=float(z.improve.mean()),leaves_improved=int((z.improve>1e-12).sum()),leaves_worsened=int((z.improve<-1e-12).sum()),ties=int((z.improve.abs()<=1e-12).sum()),signflip_p=exact_signflip(z.improve),wilcoxon_greater=one_sided_wilcoxon(z.improve,'greater')))
LOC=pd.DataFrame(loc_rows); LOC.to_csv(OUT/'12_f1lf_direct_summary.csv',index=False)

# Component error parent vs child on evaluable target leaves
co_rows=[]
for co in ['y','n','NMY','LR']:
    p=Cmp[(Cmp.arm=='PARENT')&(Cmp.component==co)&(Cmp.real_n>0)].groupby('bif').abs_err.mean().rename('parent')
    c=Cmp[(Cmp.arm=='V22_2')&(Cmp.component==co)&(Cmp.real_n>0)].groupby('bif').abs_err.mean().rename('child')
    z=pd.concat([p,c],axis=1).dropna();z['improve']=z.parent-z.child
    # across leaves slope of generated mean vs real target proportion
    pr=Cmp[(Cmp.arm=='PARENT')&(Cmp.component==co)&(Cmp.real_n>0)].groupby('bif').agg(real=('real','first'),gen=('gen','mean'))
    cr=Cmp[(Cmp.arm=='V22_2')&(Cmp.component==co)&(Cmp.real_n>0)].groupby('bif').agg(real=('real','first'),gen=('gen','mean'))
    def slope(df):
        x=df.real.to_numpy(float);y=df.gen.to_numpy(float);v=np.var(x);return float(np.cov(x,y,bias=True)[0,1]/v) if v>0 else np.nan
    co_rows.append(dict(component=co,n_leaves=len(z),parent_mae=float(z.parent.mean()),child_mae=float(z.child.mean()),improvement=float(z.improve.mean()),leaves_improved=int((z.improve>1e-12).sum()),wilcoxon_greater=one_sided_wilcoxon(z.improve,'greater'),parent_slope=slope(pr),child_slope=slope(cr)))
CO=pd.DataFrame(co_rows); CO.to_csv(OUT/'13_f1lf_component_summary.csv',index=False)

# Global metric paired: columns ae_* generated absolute errors from metric_row
met_rows=[]
for c in [x[3:] for x in M.columns if x.startswith('ae_')]:
    p=M[M.arm=='PARENT'].groupby('bif')['ae_'+c].mean().rename('parent'); q=M[M.arm=='V22_2'].groupby('bif')['ae_'+c].mean().rename('child'); z=pd.concat([p,q],axis=1).dropna();z['improve']=z.parent-z.child
    met_rows.append(dict(metric=c,parent_MAE=float(z.parent.mean()),child_MAE=float(z.child.mean()),improvement=float(z.improve.mean()),leaves_improved=int((z.improve>1e-12).sum()),leaves_worsened=int((z.improve<-1e-12).sum()),wilcoxon_greater=one_sided_wilcoxon(z.improve,'greater')))
MET=pd.DataFrame(met_rows); MET.to_csv(OUT/'14_global_metric_pairwise.csv',index=False)

# mechanical and patch scope audit from child request logs
reqrows=[]
for fi,test in enumerate(FOLDS):
  for bif in test:
    for run in RUNS:
      loc=arm_path('V22_2',run,bif)
      import gzip
      with gzip.open(loc/'requests.jsonl.gz','rt') as f:
        for line in f:
          r=json.loads(line)
          if not r.get('committed_to_final_page',False):continue
          if r.get('v22_2_f1lf_router_off_scope',False):
            reqrows.append(dict(fold=fi,bif=bif,run=run,page=r.get('page'),locus=r.get('locus'),proposal_id=r.get('proposal_id'),applied=bool(r.get('v22_2_f1lf_router_off_applied',False)),changed=bool(r.get('v22_2_changed',False)),skip=r.get('v22_2_skip_reason',''),role=r.get('role'),row_phase=r.get('row_phase'),segment_id=r.get('segment_id'),board=r.get('board'),parent_returned=bool(r.get('v22_2_current_request_parent_proposal_returned',False))))
REQ=pd.DataFrame(reqrows); REQ.to_csv(OUT/'15_scope_requests.csv',index=False)

aud={
 'fresh_seeds':RUNS,
 'cases_parent':int(len(Q[Q.arm=='PARENT'])),'cases_child':int(len(Q[Q.arm=='V22_2'])),
 'packing_parent_all':bool(Q[Q.arm=='PARENT'].packing.all()),'packing_child_all':bool(Q[Q.arm=='V22_2'].packing.all()),
 'support_parent':int(Q[Q.arm=='PARENT'].support.sum()),'support_child':int(Q[Q.arm=='V22_2'].support.sum()),
 'invalid_parent':int(Q[Q.arm=='PARENT'].invalid.sum()),'invalid_child':int(Q[Q.arm=='V22_2'].invalid.sum()),
 'retry_parent':int(Q[Q.arm=='PARENT'].retry.sum()),'retry_child':int(Q[Q.arm=='V22_2'].retry.sum()),
 'row_alignment_all':bool(D.row_alignment_exact.all()),'total_output_word_changes':int(D.total_changed.sum()),'direct_scope_word_changes':int(D.direct_scope_changed.sum()),'downstream_word_changes':int(D.downstream_changed.sum()),
 'scope_requests':int(len(REQ)),'scope_applied':int(REQ.applied.sum()) if len(REQ) else 0,'scope_changed':int(REQ.changed.sum()) if len(REQ) else 0,'single_candidate_skips':int((REQ.skip=='SINGLE_CANDIDATE').sum()) if len(REQ) else 0,
}
(OUT/'20_AUDIT.json').write_text(json.dumps(aud,ensure_ascii=False,indent=2))
print('\nSTANDARD');print(STD.to_string(index=False));print('\nPAIR');print(PAIR.to_string(index=False));print('\nLOCAL');print(LOC.to_string(index=False));print('\nCOMP');print(CO.to_string(index=False));print('\nAUD',json.dumps(aud,indent=2))
