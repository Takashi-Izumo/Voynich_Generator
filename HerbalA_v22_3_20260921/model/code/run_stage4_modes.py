from __future__ import annotations
import os,sys,json,argparse
from pathlib import Path
import pandas as pd
from runtime_bootstrap import prepare_runtime,ROOT as PACKAGE_ROOT
HANDOFF,PARENT,ST=prepare_runtime();os.environ['EHC2_STAGE6_PARENT']=str(PARENT)
sys.path.insert(0,str(ST/'code'));sys.path.insert(0,str(PACKAGE_ROOT/'code'))
from stage6_env import *
import experiment_env as benv
sys.path.insert(0,str(benv.EHC/'code'));sys.path.insert(0,str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
import run_bti2_ehc1 as rb
from fold_context import FoldContext,load_core,folds
from route_map_model import MapConfig,build_bt_leafex as real_build
from boundary_events import POLICY
from e1_decomposed_uv import DecomposedEntryTablesUV,puv_config
from run_model_v21 import configure_sampler,ARM_IDS,CFG,SEL

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fold',type=int,required=True,choices=range(5));ap.add_argument('--runs',required=True);ap.add_argument('--modes',default='V20_COMPAT,SAFE_LEFT,SAFE_LEFT_BT_OFF,SLOT_BT_OFF');ap.add_argument('--output-root',type=Path,required=True);ap.add_argument('--skip-existing',action='store_true');a=ap.parse_args()
 fi=a.fold;runs=[int(x) for x in a.runs.split(',') if x.strip()];modes=[x for x in a.modes.split(',') if x]
 C=benv.e.context();frozen=json.loads((benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text());eta=pd.read_csv(ST/'parameters/SELECTED_ETA_BY_OUTER_FOLD.csv').set_index('outer_fold').loc[fi];cfg=MapConfig(**frozen[f'fold{fi}']);core=None;orig=rb.build_bt_leafex;rows=[]
 try:
  for bif in list(folds(C.bifs))[fi]:
   alpha=float(SEL.loc[(fi,bif),'selected_alpha']);rb.build_bt_leafex=lambda ref,ext,a0=32.0,_alpha=alpha: real_build(ref,ext,_alpha)
   page=C.pages[bif][-1];fc=FoldContext.create(C,fi,bif,page,'LEGACY_SCOPE',POLICY)
   if core is None:core,ca=load_core(C,fc)
   ex=C.events[C.events.bif.isin(fc.complete_train_bifs)];kn=C.events[C.events.page.isin(fc.known_pages)];prev=rb.page_prevalence(C,fc);tab=DecomposedEntryTablesUV(ex,kn,*core[:2],core[3],fc,ca,eta_u=float(eta.eta_u),eta_v=float(eta.eta_v));patch=puv_config()
   for run in runs:
    for mode in modes:
     dest=a.output_root/f'run{run}'/ARM_IDS[mode].replace('-','_')/bif.replace(':','_')
     if a.skip_existing and (dest/'MECHANICAL.json').exists():continue
     cls=configure_sampler(mode,run,bif,fi);rb.PatchSampler=cls
     res=rb.generate(C,fc,core,cfg,prev,patch,tab,run);rb.save_result(dest,res,fc,patch,tab);md=dict(res[1]);md.update(model_id=ARM_IDS[mode],v21_stage4_mode=mode,alpha_leafex=alpha,lambda_r4=float(CFG['body_r4_lambda']));rows.append(md);print('GEN',mode,fi,bif,run,md['generated_rows_sha256'][:12],flush=True)
 finally:rb.build_bt_leafex=orig
 a.output_root.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(a.output_root/f'MECHANICAL_STAGE4_fold{fi}.csv',index=False)
if __name__=='__main__':main()
