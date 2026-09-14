#!/usr/bin/env python3
from __future__ import annotations
from connection_pilot import *
import pandas as pd, time
from route_map_experiment import Context,folds,page_prevalence,make_core,generate_one,SEED
from route_map_model import MapConfig,build_route_map,build_bt_active,build_bt_leafex
from experiment import metrics
from pilot_engine import generate_bif,GenerationState
from entry_sampler import EntryFastSampler

class EntryMapSampler(PilotSampler):
    def begin_segment(self,state,sr):
        super().begin_segment(state,sr);self.base.state=self.state

JROOT=Path(os.environ.get('BTI2_JUDGES','/mnt/data/rmw1_connection_pilot_work/RMW1_BTI2_200SET_CONTEST_20260909'))
sys.path.append(str(JROOT/'code'))
import judge_sameinfo as judge
from sklearn.feature_extraction.text import TfidfVectorizer


def doc_real(C,page):
    d=C.df[C.df.page.eq(page)].sort_values('global_order');ls=[];layout=[]
    for _,g in d.groupby('locus',sort=False):
        ls.append(' '.join(g.surface.astype(str)));layout.append(dict(para=int(g.iloc[0]['para']),phase=int(g.iloc[0]['para_line_raw'])))
    return dict(lines=ls,layout=layout)


def doc_generated(C,page,rows):
    d=pd.DataFrame(rows);d['__i']=np.arange(len(d));ls=[];layout=[]
    for _,g in d.groupby('locus',sort=False):
        ls.append(' '.join(g.surface.astype(str)));layout.append(dict(para=int(g.iloc[0]['para']),phase=int(g.iloc[0]['para_line_raw'])))
    return dict(lines=ls,layout=layout)


class FrozenJudges:
    def __init__(self,training,known):
        self.models={};self.bt=judge.bt_model(training,known)
        for kind in judge.VEC_KINDS:
            v=TfidfVectorizer(token_pattern=r'[^ ]+',lowercase=False,sublinear_tf=True,norm='l2',min_df=1)
            v.fit([' '.join(judge.tokens(d,kind)) for d in training+known])
            P=np.asarray(v.transform([' '.join(judge.tokens(d,kind)) for d in known]).mean(axis=0)).ravel()
            P/=max(np.linalg.norm(P),1e-15);self.models[kind]=(v,P)
    def score(self,doc):
        ret={kind:float(v.transform([' '.join(judge.tokens(doc,kind))]).dot(P)[0]) for kind,(v,P) in self.models.items()}
        ret.update(judge.bt_scores(doc,self.bt));ret['combined']=.5*(ret['word']+ret['ng'])
        return ret


def generate(C,b,page,core,cfg,prev,correction,train,run,ls,lp,btprof,conditional=False,entry=False):
    cdf,quad,models,base,ph,pf=core
    refs=[p for p in C.pages[b] if p!=page]
    assert len(refs)==3 and page not in refs and b not in train
    rmap,univ=build_route_map({p:C.seqs[p] for p in refs},prev,cfg.maxprev)
    rdf=C.df[C.df.page.isin(refs)];edf=C.df[C.df.bif.isin(train)]
    seed=int(m.keyed_rng(SEED,b,page,run,cfg.name,'mapstate').integers(1,2**31-1))
    allr=sorted(rmap[6] or rmap[5]);current=None
    if allr:current=allr[int(m.keyed_rng(SEED,b,page,run,cfg.name,'initial').integers(len(allr)))]
    mst=PilotMapState(cfg,rmap,univ,seed,current,bt_active=build_bt_active(rdf),bt_lambda=1.5,
        bt_leafex=build_bt_leafex(rdf,edf,32.),bt_profile_lambda=btprof,
        correction=correction,lambda_space=ls,lambda_position=lp,conditional_position=conditional)
    st=GenerationState(phw_cache=[] if b==C.D['bifs'][0] else [()],rare=m.build_rare_state(b,[page],run,C.auth,SEED),motion=mst)
    rng=m.keyed_rng(SEED,run,b,page,cfg.name,'main');sampler=EntryMapSampler(EntryFastSampler(base)) if entry else PilotSampler(base)
    rows,ss,state,*_=generate_bif(run,b,cdf,quad,C.schedules[page],models,sampler,rng,st,C.mm,C.feats,C.gm,ph,pf,SEED)
    met=metrics(rows);met.update(state.motion.stats)
    met.update(segment_retries=int(ss.get('segment_retries',0)),map5=len(rmap[5]),map6=len(rmap[6]),bt_active_types=len(mst.bt_active))
    return rows,met,state.motion.trace


def main():
    fi=int(sys.argv[1]);conditional_only='--conditional' in sys.argv;entry_only='--entry' in sys.argv;od=HERE/'outputs'/(f'entry_fold{fi}' if entry_only else f'conditional_fold{fi}' if conditional_only else f'fold{fi}');od.mkdir(parents=True,exist_ok=True)
    C=Context();fs=folds(C.bifs);test=fs[fi];train=[b for b in C.bifs if b not in test]
    cfg=MapConfig(**json.loads((PARENT/'parameters/FROZEN_FOLD_CONFIGS.json').read_text())[f'fold{fi}'])
    bp=[1,.25,1,1,1][fi];core=make_core(C,test);prev=page_prevalence(C,test)
    t0=time.monotonic();results=[];scores=[];traces=[];tokens=[];audits=[]
    for b in test:
        page=C.pages[b][-1];refs=C.pages[b][:-1]
        external=C.df[C.df.bif.isin(train)];known=C.df[C.df.page.isin(refs)]
        corr=CorrectionModel(external,known,core[0],core[1],core[3])
        audit=dict(bif=b,target=page,fold=fi,**corr.audit)
        assert b not in audit['external_leaves'] and page not in audit['known_pages']
        audits.append(audit)
        fj=FrozenJudges([doc_real(C,p) for bb in train for p in C.pages[bb]],[doc_real(C,p) for p in refs])
        realdoc=doc_real(C,page);rs=fj.score(realdoc)
        for arm,(ls,lp) in ([('ENTRY12',(0,0))] if entry_only else [('CONDITIONAL',(1,1))] if conditional_only else [('BASE',(0,0)),('SPACE',(1,0)),('POSITION',(0,1)),('BOTH',(1,1))]):
            rows,met,tr=generate(C,b,page,core,cfg,prev,corr,train,6001,ls,lp,bp,conditional=conditional_only,entry=entry_only)
            if b==test[0] and arm=='BASE':
                _,_,original,_=generate_one(C,b,page,core,cfg,prev,6001,keep=True,bt_lambda=1.5,bt_profile_lambda=bp,bt_external_bifs=train)
                assert rows==original, 'OFF branch not identical to parent!'
                (od/'OFF_IDENTITY.json').write_text(json.dumps(dict(bif=b,run=6001,byte_equivalent_rows=True,parent_rows=len(original)),indent=2))
            gd=doc_generated(C,page,rows);gs=fj.score(gd)
            results.append(dict(fold=fi,bif=b,page=page,run=6001,arm=arm,**met))
            for j in gs:
                mar=rs[j]-gs[j];scores.append(dict(fold=fi,bif=b,page=page,run=6001,arm=arm,judge=j,real_score=rs[j],generated_score=gs[j],margin=mar,real_win=int(mar>1e-12),tie=abs(mar)<=1e-12))
            for x in rows:tokens.append(dict(**x,arm=arm,fold=fi))
            for x in tr:traces.append(dict(**x,arm=arm,fold=fi,bif=b,run=6001))
            # mechanical audit: packed physical extent, NOT lexical quality.
            for (loc,sid),g in pd.DataFrame(rows).groupby(['locus','segment_id'],sort=False):
                assert g.phys_width.sum()+len(g)-1==int(g.iloc[0].segment_capacity)
                assert int(g.iloc[-1].r_after_word)==0
            pd.DataFrame(results).to_csv(od/'metrics.csv',index=False);pd.DataFrame(scores).to_csv(od/'scores.csv',index=False)
            print('pilot',fi,b,arm,'words',len(rows),'sec',round(time.monotonic()-t0,1),flush=True)
    pd.DataFrame(tokens).to_csv(od/'tokens.csv.gz',index=False);pd.DataFrame(traces).to_csv(od/'trace.csv.gz',index=False)
    (od/'learning_audit.json').write_text(json.dumps(audits,indent=2,ensure_ascii=False))
    (od/'DONE.json').write_text(json.dumps(dict(fold=fi,leaves=len(test),arms=1 if conditional_only or entry_only else 4,seconds=time.monotonic()-t0,packing='PASS',parent_unmodified=True),indent=2))

if __name__=='__main__':main()
