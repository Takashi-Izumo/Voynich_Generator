"""Run six saved fresh pages from a relocated, standalone directory."""
from experiment_env import *
from entry_global_only import *
from run_bti2_ehc1 import generate,page_prevalence
from route_map_model import MapConfig
from fold_context import FoldContext,folds,load_core
from boundary_events import POLICY
from entry_correction import configs,CorrectionTables
import json

def main():
    C=e.context();cfgs=configs();cfgs[CANDIDATE]=candidate_config()
    frozen=json.loads((EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text())
    checks=[]
    for b in ('A:2','G:4'):
        fi=next(i for i,x in enumerate(folds(C.bifs)) if b in x)
        p=C.pages[b][-1];fc=FoldContext.create(C,fi,b,p,'LEGACY_SCOPE',POLICY);core,ca=load_core(C,fc)
        ex=C.events[C.events.bif.isin(fc.complete_train_bifs)];kn=C.events[C.events.page.isin(fc.known_pages)]
        tab=CorrectionTables(ex,kn,*core[:2],core[3],fc,ca);new=GlobalEntryTables(ex,kn,*core[:2],core[3],fc,ca)
        cfg=MapConfig(**frozen[f'fold{fi}']);prev=page_prevalence(C,fc)
        for arm in ('BASE','E12_VH',CANDIDATE):
            result=generate(C,fc,core,cfg,prev,cfgs[arm],None if arm=='BASE' else tab if arm=='E12_VH' else new,91151)
            old=json.loads((ROOT/'outputs/generated/run91151'/arm/b.replace(':','_')/'MECHANICAL.json').read_text())
            got=result[1]
            for k in ('generated_rows_sha256','rng_end','route_final_state','packing_exact','segment_retries'):
                assert json.loads(json.dumps(got[k],default=str))==old[k],(b,arm,k)
            checks.append(dict(bif=b,page=p,run=91151,arm=arm,tokens=len(result[0]),surface_exact=True,rng_exact=True,route_exact=True,packing=True))
            print('RELOCATED',b,arm,flush=True)
    e.write(ROOT/'PORTABILITY_AUDIT.json',dict(passed=True,pages=len(checks),tokens=sum(x['tokens'] for x in checks),checks=checks,
                                             same_runtime=True,relocation_only_not_cross_version=True))
if __name__=='__main__':main()
