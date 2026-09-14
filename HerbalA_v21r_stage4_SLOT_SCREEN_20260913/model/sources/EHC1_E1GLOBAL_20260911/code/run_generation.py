"""Precommitted 300-page generation; never executes judge scores."""
from experiment_env import *
from entry_global_only import GlobalEntryTables, candidate_config, CANDIDATE
from run_bti2_ehc1 import generate,save_result,page_prevalence
from route_map_model import MapConfig
from entry_correction import CorrectionTables,configs
from fold_context import FoldContext,load_core,folds
from boundary_events import POLICY
import json,time,argparse

NONTARGET_TABLES=('ex','kn','head_ex','head_kn')
def same_arrays(a,b,names):
    return all(set(getattr(a,n))==set(getattr(b,n)) and all(np.array_equal(getattr(a,n)[k],getattr(b,n)[k]) for k in getattr(a,n)) for n in names)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fold',type=int);ap.add_argument('--skip-audit',action='store_true');args=ap.parse_args()
    plan=json.loads((ROOT/'PLAN_FROZEN_BEFORE_GENERATION.json').read_text())
    C=e.context(); cfgs=configs();cfgs[CANDIDATE]=candidate_config()
    frozen=json.loads((EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text())
    all_a=[];ta=[];ident=[];start=time.monotonic()
    for fi,test in enumerate(folds(C.bifs)):
        if args.fold is not None and fi!=args.fold:continue
        cfg=MapConfig(**frozen[f'fold{fi}']);core=None
        for b in test:
            p=C.pages[b][-1];fc=FoldContext.create(C,fi,b,p,'LEGACY_SCOPE',POLICY)
            if core is None:core,ca=load_core(C,fc)
            prev=page_prevalence(C,fc)
            ex=C.events[C.events.bif.isin(fc.complete_train_bifs)];kn=C.events[C.events.page.isin(fc.known_pages)]
            tab=CorrectionTables(ex,kn,*core[:2],core[3],fc,ca)
            new=GlobalEntryTables(ex,kn,*core[:2],core[3],fc,ca)
            external=CorrectionTables(ex,kn.iloc[:0],*core[:2],core[3],fc,ca)
            assert same_arrays(tab,new,NONTARGET_TABLES)
            assert same_arrays(external,new,('bridge','joints'))
            changed=GlobalEntryTables(ex,kn.iloc[::2],*core[:2],core[3],fc,ca)
            assert same_arrays(new,changed,('bridge','joints'))
            checks=0
            for role in ('F1','HEAD','W2','BODY'):
                for lp in range(3):
                    for end,le in [(False,False),(True,False),(True,True)]:
                        for ph in ('FIRST','MIDDLE','FINAL'):
                            board='LF' if end and le else 'HEAD' if role=='HEAD' else 'W2' if role=='W2' else 'BODY'
                            x=tab.gains(role,lp,end,le,ph,board,role=='HEAD',cfgs['E12_VH'])
                            y=new.gains(role,lp,end,le,ph,board,role=='HEAD',cfgs[CANDIDATE])
                            assert all(np.array_equal(v,w) for v,w in zip(x,y));checks+=1
            for pl in range(2,7):
                for ph in ('FIRST','MIDDLE','FINAL'):
                    for previous in [None]+list(range(22)):
                        x=tab.head_row(pl,previous,core[2].lstart,ph,.5)
                        y=new.head_row(pl,previous,core[2].lstart,ph,.5)
                        assert all(np.array_equal(v,w) for v,w in zip(x,y));checks+=1
            ta.append(dict(fold=fi,bif=b,page=p,external_train=list(fc.complete_train_bifs),known3=list(fc.known_pages),
                           entry_known3_enabled=False,external_bridge_exact=True,other_tables_exact=True,
                           explicit_nonentry_gain_checks=checks,known3_substitution_entry_invariant=True,
                           entry_changed_cells=int(sum(np.count_nonzero(tab.bridge[k]!=new.bridge[k]) for k in tab.bridge)),
                           other_known3_retained=True,target_used=False))
            new.save(ROOT/'parameters/corrections'/b.replace(':','_'))
            if not args.skip_audit:
                a=generate(C,fc,core,cfg,prev,cfgs['E12_VH'],tab,91011)
                orig=EHC/'outputs/mechanical/run91011/E12_VH'/b.replace(':','_')
                md=json.loads((orig/'MECHANICAL.json').read_text())
                assert a[1]['generated_rows_sha256']==md['generated_rows_sha256'],('frozen replay',b)
                assert a[1]['rng_end']==md['rng_end']
                off=GlobalEntryTables(ex,kn,*core[:2],core[3],fc,ca,enabled=False)
                ao=generate(C,fc,core,cfg,prev,cfgs[CANDIDATE],off,91011)
                assert ao[1]['generated_rows_sha256']==a[1]['generated_rows_sha256'],('off identity',b)
                assert ao[1]['rng_end']==a[1]['rng_end'] and ao[1]['route_final_state']==a[1]['route_final_state']
                ident.append(dict(bif=b,page=p,run=91011,original_replayed=True,adapter_off_identical=True,tokens=len(a[0]),rng_exact=True,route_exact=True))
            for arm in plan['arms']:
                tt=None if arm=='BASE' else tab if arm=='E12_VH' else new
                for run in plan['runs']:
                    dest=ROOT/'outputs/generated'/f'run{run}'/arm/b.replace(':','_')
                    if (dest/'MECHANICAL.json').exists():
                        audit=json.loads((dest/'MECHANICAL.json').read_text())
                    else:
                        result=generate(C,fc,core,cfg,prev,cfgs[arm],tt,run)
                        save_result(dest,result,fc,cfgs[arm],tt);audit=result[1]
                    all_a.append(audit)
                print('GENERATED',fi,b,arm,len(plan['runs']),f'{time.monotonic()-start:.1f}s',flush=True)
            e.write(ROOT/'outputs'/f'TABLE_AUDIT_fold{args.fold if args.fold is not None else "ALL"}.json',ta)
            pd.DataFrame(ident).to_csv(ROOT/'outputs'/f'IDENTITY_fold{args.fold if args.fold is not None else "ALL"}.csv',index=False)
    tag=str(args.fold) if args.fold is not None else 'ALL'
    pd.DataFrame(all_a).to_csv(ROOT/'outputs'/f'MECHANICAL_fold{tag}.csv',index=False)
    hashes={str(p.relative_to(ROOT)):e.file_hash(p) for p in (ROOT/'outputs/generated').glob('run*/*/*/*') if p.is_file()}
    seal=dict(plan=plan,pages=len(all_a),segments=sum(z['packing_segments'] for z in all_a),packing_pass=all(z['packing_exact'] for z in all_a),
              retries=sum(z['segment_retries'] for z in all_a),elapsed=time.monotonic()-start,hashes=hashes,judged=False)
    e.write(ROOT/'outputs'/f'GENERATION_SEALED_{tag}.json',seal)
    print('SEALED',len(all_a),seal['segments'],seal['retries'],flush=True)
if __name__=='__main__': main()
