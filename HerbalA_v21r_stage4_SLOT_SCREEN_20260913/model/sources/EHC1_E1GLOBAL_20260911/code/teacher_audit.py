"""Actual adapter non-END rows on the same 80-surface diagnostic event set.
No target learning or fitted parameters: probabilities only, before selection.
"""
from experiment_env import *
from entry_global_only import *
from judge_experiment import paired_stats
from entry_correction import CorrectionTables,configs
from fold_context import FoldContext,load_core,folds
from boundary_events import POLICY
import json,math,time

def main():
    out=ROOT/'outputs/teacher';out.mkdir(parents=True,exist_ok=True)
    C=e.context();E=C.events
    P=pd.read_csv(DIAG/'outputs/prediction_event_manifest.csv.gz')
    P=P[P.bif.isin(C.bifs)&P.kind.isin(['H1_SPACE','H2'])]
    cfg=configs()['E12_VH'];newcfg=candidate_config()
    probs=[];records=[];invariance=[];correspond=[]
    old=pd.read_csv(DIAG/'outputs/information/information_ladder_events.csv.gz')
    old=old[old.contract.eq('SLOT_ORACLE_DIAGNOSTIC')&old.kind.isin(['H1_SPACE','H2'])]
    for fi,test in enumerate(folds(C.bifs)):
        core=None
        for b in test:
            for p in C.pages[b]:
                fc=FoldContext.create(C,fi,b,p,'LEGACY_SCOPE',POLICY)
                if core is None:core,ca=load_core(C,fc)
                ex=E[E.bif.isin(fc.complete_train_bifs)];kn=E[E.page.isin(fc.known_pages)]
                tab=CorrectionTables(ex,kn,*core[:2],core[3],fc,ca)
                new=GlobalEntryTables(ex,kn,*core[:2],core[3],fc,ca)
                sameh2=0
                for r in P[P.page.eq(p)].to_dict('records'):
                    depth=int(r['depth']);lp=min(int(r['pl']),3)-1
                    a=e.m.START;bb=e.m.START if depth==0 else int(r['h1'])
                    p0=tab.base_nonend(r['role'],lp,bool(r['end']),bool(r['line_end']),depth,a,bb)
                    if depth==0:
                        po=p0*np.exp(tab.bridge[r['phase'],r['board']][int(r['T'])])
                        pn=p0*np.exp(new.bridge[r['phase'],r['board']][int(r['T'])])
                    else:
                        key=(r['phase'],r['board'],depth,a,bb)
                        po=p0*tab.local_gain(key,p0,cfg.eta_h2)
                        pn=p0*new.local_gain(key,p0,newcfg.eta_h2)
                        assert np.array_equal(po,pn);sameh2+=1
                    pp={arm:(x/x.sum() if x.sum()>0 else x.copy()) for arm,x in [('BASE',p0),('E12_VH',po),(CANDIDATE,pn)]}
                    y=int(r['y']);truth=np.eye(22)[y]
                    for arm,px in pp.items():
                        i=len(probs);probs.append(px)
                        records.append(dict(event_id=r['event_id'],bif=b,page=p,kind=r['kind'],arm=arm,y=y,prob_index=i,
                                            prob=float(px[y]),loss_bits=-math.log2(max(float(px[y]),1e-15)),
                                            entropy=float(-sum(x*math.log2(x) for x in px if x>0)),
                                            brier=float(np.square(px-truth).sum()),native_supported=bool(p0[y]>0),row_defined=bool(px.sum()>0)))
                invariance.append(dict(bif=b,page=p,h2_exact_events=sameh2,target_learning=False))
            print('TEACHER',b,flush=True)
    X=pd.DataFrame(records);X.to_csv(out/'events.csv.gz',index=False);np.savez_compressed(out/'probabilities.npz',probabilities=np.array(probs))
    for arm,model,lev in [('BASE','BTI2_NATIVE','NATIVE'),('E12_VH','EHC_FROZEN_FORM','K3')]:
        o=old[old.model.eq(model)&old.level.eq(lev)]
        z=X[X.arm.eq(arm)].merge(o,on=['event_id','kind'],suffixes=('_new','_old'),validate='one_to_one')
        err=float(abs(z.prob_new-z.prob_old).max())
        assert err<1e-12,(arm,err)
        correspond.append(dict(arm=arm,events=len(z),max_prob_error=err))
    page=X.groupby(['arm','bif','page','kind'])[['loss_bits','brier','entropy']].mean().reset_index()
    by=page.groupby(['arm','bif','kind'])[['loss_bits','brier','entropy']].mean().reset_index()
    by.to_csv(out/'by_leaf.csv',index=False)
    by.groupby(['arm','kind'])[['loss_bits','brier','entropy']].mean().reset_index().to_csv(out/'summary.csv',index=False)
    pairs=[]
    for ref in ('BASE','E12_VH'):
        for kind in ['H1_SPACE','H2']:
            z=by[by.arm.eq(CANDIDATE)&by.kind.eq(kind)].merge(by[by.arm.eq(ref)&by.kind.eq(kind)],on='bif',suffixes=('_new','_ref'),validate='one_to_one')
            pairs.append(dict(reference=ref,kind=kind,reference_loss=z.loss_bits_ref.mean(),new_loss=z.loss_bits_new.mean(),**paired_stats(z.loss_bits_ref-z.loss_bits_new)))
    T=pd.DataFrame(pairs)
    for ref in T.reference.unique():
        mk=T.reference.eq(ref);T.loc[mk,'holm_two']=e.holm(T.loc[mk,'p_two_sided'])
    T.to_csv(out/'paired.csv',index=False)
    Z=X[X.native_supported].groupby(['arm','bif','page','kind']).loss_bits.mean().groupby(['arm','bif','kind']).mean().groupby(['arm','kind']).mean()
    Z.to_csv(out/'common_support_summary.csv')
    e.write(out/'AUDIT.json',dict(events=P.shape[0],probability_rows=len(X),h2_identical_events=sum(x['h2_exact_events'] for x in invariance),all80= len(invariance)==80,
                                 legacy_probability_reproduction=correspond,non_END_slot_diagnostic=True,all_target_learning=False,
                                 inherited_core_scope='frozen18',entry_training='external16',h2_training='external16+known3',floor=1e-15))
    print(T.to_string(index=False));print('TEACHER_DONE',flush=True)
if __name__=='__main__':main()
