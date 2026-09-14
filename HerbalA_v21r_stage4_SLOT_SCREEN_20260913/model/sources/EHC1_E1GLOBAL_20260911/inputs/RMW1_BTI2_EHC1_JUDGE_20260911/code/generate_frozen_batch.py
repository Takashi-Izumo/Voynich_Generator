#!/usr/bin/env python3
"""Generate preselected frozen EHC1 arms on reserved fresh seeds, without judging."""
from __future__ import annotations
import evaluation_common as e
from stage3_env import EHC,ROOT
import json,argparse,time
import pandas as pd
from run_bti2_ehc1 import generate,save_result,page_prevalence
from route_map_model import MapConfig

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['multirun','confirmation'],required=True);a=ap.parse_args()
 sel=json.loads((ROOT/('SELECTION_FROZEN.json' if a.stage=='multirun' else 'CONFIRMATION_FROZEN.json')).read_text());arms=['BASE']+sel['selected_arms'];runs=sel['fresh_screen_seeds'] if a.stage=='multirun' else sel['confirmation_seeds']
 root=ROOT/'outputs'/a.stage/'generated';root.mkdir(parents=True,exist_ok=True)
 e.write(root/'PLAN_BEFORE_GENERATION.json',dict(arms=arms,runs=runs,selection=sel,judge_scores_used_during_generation=False,generator_stage2_hash=e.env.EXPECTED))
 C=e.context();cfgs=e.configs();frozen=json.loads((e.env.EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text());cores={};audits=[];start=time.monotonic()
 for fi,test in enumerate(e.folds(C.bifs)):
  cfg=MapConfig(**frozen[f'fold{fi}'])
  for b in test:
   p=C.pages[b][-1];tabs={}
   for arm in arms:
    patch=cfgs[arm];scope='LEGACY_SCOPE' if patch.scope_policy=='FROZEN_PARENT' else patch.scope_policy
    fc=e.FoldContext.create(C,fi,b,p,scope,e.POLICY)
    if (fi,scope) not in cores:cores[fi,scope]=e.load_core(C,fc)
    core,ca=cores[fi,scope];prev=page_prevalence(C,fc);tab=None
    if arm!='BASE':
     if scope not in tabs:
      tab=e.CorrectionTables(C.events[C.events.bif.isin(fc.complete_train_bifs)],C.events[C.events.page.isin(fc.known_pages)],*core[:2],core[3],fc,ca);tabs[scope]=tab
     tab=tabs[scope]
    for run in runs:
     dest=root/f'run{run}'/arm/b.replace(':','_')
     if (dest/'MECHANICAL.json').exists():audit=json.loads((dest/'MECHANICAL.json').read_text())
     else:
      result=generate(C,fc,core,cfg,prev,patch,tab,run);save_result(dest,result,fc,patch,tab);audit=result[1]
     audits.append(audit)
    print('GENERATED',a.stage,fi,b,arm,len(runs),'runs',round(time.monotonic()-start,1),'sec',flush=True)
 pd.DataFrame(audits).to_csv(root/'MECHANICAL_SUMMARY.csv',index=False)
 files={str(p.relative_to(root)):e.file_hash(p) for p in sorted(root.glob('run*/*/*/*')) if p.is_file()}
 e.write(root/'GENERATION_SEALED.json',dict(arms=arms,runs=runs,pages=len(audits),segments=sum(x['packing_segments'] for x in audits),packing_pass=all(x['packing_exact'] for x in audits),segment_retries=sum(x['segment_retries'] for x in audits),elapsed_seconds=time.monotonic()-start,hashes=files,judge_scores_run=False))
 print('ALL_GENERATION_COMPLETE',a.stage,len(audits),flush=True)
if __name__=='__main__':main()
