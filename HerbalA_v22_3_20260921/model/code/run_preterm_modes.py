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
from integrated_sampler_v21 import V21SafeLeftBtOffSampler
from preterm_sampler import V21PretermR6Sampler,V21PretermQMap9Sampler
from short_body_h2_sampler import V21PretermShortBodyH2GlobalSampler,V21PretermShortBodyH2NoOpSampler

PARAM=PACKAGE_ROOT/'parameters'
SEL=pd.read_csv(PARAM/'LEAFEX_ALPHA_SELECTED.csv').set_index(['fold','bif'])
CFG=json.loads((PARAM/'MODEL_CONFIG.json').read_text(encoding='utf-8'))
ARM_IDS={
 'SAFE_LEFT_BT_OFF':'RMW1_BTI2_EHC2_DECOMP1_PUV_R4LEX_W2H2L4_K16_LEFT_BTOFF',
 'PRETERM_R6':'HerbalA_v21r_PRETERM_R6',
 'PRETERM_QMAP9':'HerbalA_v21r_PRETERM_QMAP9',
 'PRETERM_SHORT_H2_GLOBAL':'HerbalA_v21r_PRETERM_SHORTBODY_H2GLOBAL',
 'PRETERM_SHORT_H2_NOOP':'HerbalA_v21r_PRETERM_SHORTBODY_H2NOOP',
}
CLASSES={'SAFE_LEFT_BT_OFF':V21SafeLeftBtOffSampler,'PRETERM_R6':V21PretermR6Sampler,'PRETERM_QMAP9':V21PretermQMap9Sampler,'PRETERM_SHORT_H2_GLOBAL':V21PretermShortBodyH2GlobalSampler,'PRETERM_SHORT_H2_NOOP':V21PretermShortBodyH2NoOpSampler}

def configure(mode,run,bif):
 cls=CLASSES[mode]
 cls.BODY_R4_LAMBDA=float(CFG['body_r4_lambda'])
 cls.SIBLING_K=int(CFG['w2_h2_splice']['sibling_k'])
 cls.SIBLING_MAX_DRAWS=int(CFG['w2_h2_splice']['sibling_max_draws'])
 cls.EXACT_LENGTH=int(CFG['w2_h2_splice']['exact_glyph_length'])
 cls.RUN_SEED=int(run);cls.TARGET_BIF=str(bif)
 return cls

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--fold',type=int,required=True,choices=range(5))
 ap.add_argument('--runs',required=True)
 ap.add_argument('--modes',default='SAFE_LEFT_BT_OFF,PRETERM_QMAP9,PRETERM_SHORT_H2_GLOBAL')
 ap.add_argument('--output-root',type=Path,required=True)
 ap.add_argument('--skip-existing',action='store_true')
 a=ap.parse_args();fi=a.fold;runs=[int(x) for x in a.runs.split(',') if x.strip()];modes=[x for x in a.modes.split(',') if x]
 C=benv.e.context();frozen=json.loads((benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text());eta=pd.read_csv(ST/'parameters/SELECTED_ETA_BY_OUTER_FOLD.csv').set_index('outer_fold').loc[fi];cfg=MapConfig(**frozen[f'fold{fi}']);core=None;orig=rb.build_bt_leafex;rows=[]
 try:
  for bif in list(folds(C.bifs))[fi]:
   alpha=float(SEL.loc[(fi,bif),'selected_alpha']);rb.build_bt_leafex=lambda ref,ext,a0=32.0,_alpha=alpha: real_build(ref,ext,_alpha)
   page=C.pages[bif][-1];fc=FoldContext.create(C,fi,bif,page,'LEGACY_SCOPE',POLICY)
   if core is None:core,ca=load_core(C,fc)
   ex=C.events[C.events.bif.isin(fc.complete_train_bifs)];kn=C.events[C.events.page.isin(fc.known_pages)];prev=rb.page_prevalence(C,fc);tab=DecomposedEntryTablesUV(ex,kn,*core[:2],core[3],fc,ca,eta_u=float(eta.eta_u),eta_v=float(eta.eta_v));patch=puv_config()
   for run in runs:
    for mode in modes:
     dest=a.output_root/f'run{run}'/ARM_IDS[mode]/bif.replace(':','_')
     if a.skip_existing and (dest/'MECHANICAL.json').exists():continue
     cls=configure(mode,run,bif);rb.PatchSampler=cls
     res=rb.generate(C,fc,core,cfg,prev,patch,tab,run);rb.save_result(dest,res,fc,patch,tab);md=dict(res[1]);md.update(model_id=ARM_IDS[mode],preterm_mode=mode,alpha_leafex=alpha,lambda_r4=float(CFG['body_r4_lambda']));rows.append(md);print('GEN',mode,fi,bif,run,md['generated_rows_sha256'][:12],flush=True)
 finally: rb.build_bt_leafex=orig
 a.output_root.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(a.output_root/f'MECHANICAL_PRETERM_fold{fi}.csv',index=False)
if __name__=='__main__':main()
