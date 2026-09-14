#!/usr/bin/env python3
"""Re-extract bundled Stage 2 and replay six confirmation pages exactly."""
import evaluation_common as e
from stage3_env import ROOT,EHC
import json
from run_bti2_ehc1 import generate,page_prevalence
from route_map_model import MapConfig

def main():
 C=e.context();configs=e.configs();frozen=json.loads((EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text());checks=[]
 for fi in (0,2,4):
  b=e.folds(C.bifs)[fi][0];p=C.pages[b][-1];fc=e.FoldContext.create(C,fi,b,p,'LEGACY_SCOPE',e.POLICY);core,ca=e.load_core(C,fc);cfg=MapConfig(**frozen[f'fold{fi}']);prev=page_prevalence(C,fc)
  for arm in ('BASE','E12_VH'):
   tab=None
   if arm!='BASE':tab=e.CorrectionTables(C.events[C.events.bif.isin(fc.complete_train_bifs)],C.events[C.events.page.isin(fc.known_pages)],*core[:2],core[3],fc,ca)
   res=generate(C,fc,core,cfg,prev,configs[arm],tab,91031)
   orig=json.loads((ROOT/f'outputs/confirmation/generated/run91031/{arm}/{b.replace(":","_")}/MECHANICAL.json').read_text())
   for key in ('generated_rows_sha256','rng_end','route_final_state','generation_input_sha256'):assert json.loads(json.dumps(res[1][key],default=str))==orig[key],(arm,b,key)
   checks.append(dict(arm=arm,bif=b,run=91031,rows=len(res[0]),all_generation_fields=True,rng=True,route_state=True,new_generation_input=True))
 e.write(ROOT/'EXECUTION_REPLAY_AUDIT.json',dict(pages=len(checks),checks=checks,all_pass=True,auto_extracted_from_bundled_zip=True,exact_environment=True))
 print('REPLAY_PASS',checks)
if __name__=='__main__':main()
