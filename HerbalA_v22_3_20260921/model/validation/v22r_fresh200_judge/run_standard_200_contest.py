from __future__ import annotations
import os,sys,json,hashlib,argparse
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import binomtest

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--pkg',type=Path,required=True); ap.add_argument('--gen',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--model-dir',required=True); ap.add_argument('--model-label',required=True); args=ap.parse_args()
    PKG=args.pkg; GEN=args.gen; OUT=args.out; OUT.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(PKG/'model/code'))
    from runtime_bootstrap import prepare_runtime
    HANDOFF,PARENT,ST=prepare_runtime(); os.environ['EHC2_STAGE6_PARENT']=str(PARENT); sys.path.insert(0,str(ST/'code'))
    import stage6_env
    import experiment_env as benv
    RUNS=list(range(91701,91711)); JUDGES=['word','ng','bigram','trigram','route56','combined']
    C=benv.e.context(); folds_list=list(benv.e.folds(C.bifs))
    pairs=[]
    for fi,test in enumerate(folds_list):
        for bif in test:
            page=C.pages[bif][-1]
            for run in RUNS: pairs.append(dict(fold=fi,bif=bif,page=page,run=run))
    assert len(pairs)==200
    rng=np.random.default_rng(202609170917); flags=np.array([1]*100+[0]*100,dtype=int); rng.shuffle(flags)
    for i,(r,fl) in enumerate(zip(pairs,flags),1): r['pair_id']=f'P{i:03d}'; r['real_on_left']=int(fl)
    key=pd.DataFrame(pairs)
    pres=[]
    for r in pairs:
        for side in ['L','R']:
            opaque=hashlib.sha256(f"{r['pair_id']}|{side}|20260917".encode()).hexdigest()[:16]
            pres.append(dict(pair_id=r['pair_id'],fold=r['fold'],bif=r['bif'],page=r['page'],run=r['run'],side=side,opaque_doc_id=opaque))
    pd.DataFrame(pres).to_csv(OUT/'BLIND_PRESENTATION.csv',index=False); key.to_csv(OUT/'BLIND_KEY.csv',index=False)
    pb=(OUT/'BLIND_PRESENTATION.csv').read_bytes(); (OUT/'BLIND_PRESENTATION.sha256').write_text(hashlib.sha256(pb).hexdigest()+'  BLIND_PRESENTATION.csv\n')
    docs={p:benv.e.real_doc(C,p) for p in C.seqs}; outcomes=[]; scores=[]
    pairmap={(x['bif'],x['run']):x for x in pairs}
    for fi,test in enumerate(folds_list):
        train=[b for b in C.bifs if b not in test]; train_pages=[p for b in train for p in C.pages[b]]
        for bif in test:
            page=C.pages[bif][-1]; known=[q for q in C.pages[bif] if q!=page]; judge=benv.e.Judges([docs[p] for p in train_pages],[docs[p] for p in known]); real=judge.score(docs[page],True)
            for run in RUNS:
                rr=pairmap[(bif,run)]; loc=GEN/f'run{run}'/args.model_dir/bif.replace(':','_'); d=pd.read_csv(loc/'tokens.csv.gz'); gd=benv.e.generated_doc(d); gs=judge.score(gd,True); lir=bool(rr['real_on_left'])
                for j in JUDGES:
                    rsc=float(real[j]); gsc=float(gs[j]); ls=rsc if lir else gsc; rside=gsc if lir else rsc
                    if abs(ls-rside)<=1e-12: chosen='TIE'; correct=np.nan
                    else: chosen='L' if ls>rside else 'R'; correct=int(chosen==('L' if lir else 'R'))
                    outcomes.append(dict(pair_id=rr['pair_id'],fold=fi,bif=bif,page=page,run=run,judge=j,left_score=ls,right_score=rside,chosen_side=chosen,correct=correct,score_gap=abs(ls-rside)))
                    scores.append(dict(pair_id=rr['pair_id'],fold=fi,bif=bif,page=page,run=run,judge=j,real_score=rsc,generated_score=gsc,margin=rsc-gsc,abs_margin=abs(rsc-gsc)))
        print('JUDGED',fi,flush=True)
    O=pd.DataFrame(outcomes); S=pd.DataFrame(scores); O.to_csv(OUT/'BLIND_OUTCOMES_200.csv',index=False); S.to_csv(OUT/'SCORES_200.csv',index=False)
    raw=[]; clusters=[]; leafrows=[]
    for j,g in S.groupby('judge',sort=False):
        w=int((g.margin>1e-12).sum()); t=int((g.margin.abs()<=1e-12).sum()); l=len(g)-w-t; n=w+l; pdsc=float(binomtest(w,n,.5).pvalue) if n else 1
        raw.append(dict(judge=j,sets=len(g),real_wins=w,generated_wins=l,ties=t,real_win_rate=w/n if n else np.nan,descriptive_binom_p=pdsc,mean_margin=float(g.margin.mean()),mean_abs_margin=float(g.abs_margin.mean())))
        lv=g.groupby('bif',sort=False).margin.mean(); w2=int((lv>1e-12).sum()); t2=int((lv.abs()<=1e-12).sum()); l2=len(lv)-w2-t2; p=float(binomtest(w2,w2+l2,.5).pvalue) if w2+l2 else 1
        sums=np.zeros(1)
        for v in lv.to_numpy(float): sums=np.concatenate((sums+v,sums-v))
        ob=float(lv.sum()); eps=1e-12*max(1.,abs(ob)); ps=float(np.mean(np.abs(sums)>=abs(ob)-eps))
        clusters.append(dict(judge=j,leaves=len(lv),real_wins=w2,generated_wins=l2,ties=t2,binom_p=p,signflip_p=ps,mean_leaf_margin=float(lv.mean()),mean_leaf_abs_margin=float(lv.abs().mean())))
        for bif,v in lv.items(): leafrows.append(dict(judge=j,bif=bif,mean_margin=float(v),real_wins=int(v>1e-12)))
    RAW=pd.DataFrame(raw); CLU=pd.DataFrame(clusters); RAW.to_csv(OUT/'RAW_200_SUMMARY.csv',index=False); CLU.to_csv(OUT/'CLUSTER_20_SUMMARY.csv',index=False); pd.DataFrame(leafrows).to_csv(OUT/'BY_LEAF.csv',index=False)
    summary={'status':'COMPLETE','model':args.model_label,'runs':RUNS,'n_pairs':200,'n_unique_real_target_pages':20,'primary_judge':'combined','formal_stat_unit':'20 bifolia','raw_200_is_descriptive_only':True,'presentation_sha256':hashlib.sha256(pb).hexdigest(),'combined_raw':RAW[RAW.judge.eq('combined')].iloc[0].to_dict(),'combined_cluster':CLU[CLU.judge.eq('combined')].iloc[0].to_dict()}
    (OUT/'CONTEST_SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,'item') else x))
    print(RAW.to_string(index=False)); print(CLU.to_string(index=False))
if __name__=='__main__': main()
