from __future__ import annotations
import os,sys,json,argparse
from pathlib import Path
import pandas as pd
from runtime_bootstrap import prepare_runtime,ROOT as PACKAGE_ROOT
HANDOFF,PARENT,ST=prepare_runtime()
os.environ['EHC2_STAGE6_PARENT']=str(PARENT)
sys.path.insert(0,str(ST/'code'));sys.path.insert(0,str(PACKAGE_ROOT/'code'))
from stage6_env import *
import experiment_env as benv
sys.path.insert(0,str(benv.EHC/'code'));sys.path.insert(0,str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
import run_bti2_ehc1 as rb
from fold_context import FoldContext,load_core,folds
from route_map_model import MapConfig,build_bt_leafex as real_build
from boundary_events import POLICY
from e1_decomposed_uv import DecomposedEntryTablesUV,puv_config
from integrated_sampler_v21 import V20CompatSampler,V21SafeLeftSampler,V21SafeLeftBtOffSampler,V21SlotBtOffSampler
from w2_slot_tables import load_fold_tables

DEFAULT_RUNS=[91321,91322,91323,91324,91325]
PARAM=PACKAGE_ROOT/'parameters'
SEL=pd.read_csv(PARAM/'LEAFEX_ALPHA_SELECTED.csv').set_index(['fold','bif'])
CFG=json.loads((PARAM/'MODEL_CONFIG.json').read_text(encoding='utf-8'))
ARM_IDS={
    'V20_COMPAT': CFG['model_id'],
    'SAFE_LEFT': 'RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16-LEFT',
    'SAFE_LEFT_BT_OFF': 'RMW1-BTI2-EHC2-DECOMP1-PUV-R4LEX-W2H2L4-K16-LEFT-BTOFF',
    'SLOT_BT_OFF': 'HerbalA-v21r-W2-SLOT-BTOFF',
}

def configure_sampler(mode,run,bif,fold=None):
    classes={
        'V20_COMPAT':V20CompatSampler,
        'SAFE_LEFT':V21SafeLeftSampler,
        'SAFE_LEFT_BT_OFF':V21SafeLeftBtOffSampler,
        'SLOT_BT_OFF':V21SlotBtOffSampler,
    }
    cls=classes[mode]
    cls.BODY_R4_LAMBDA=float(CFG['body_r4_lambda'])
    cls.SIBLING_K=int(CFG['w2_h2_splice']['sibling_k'])
    cls.SIBLING_MAX_DRAWS=int(CFG['w2_h2_splice']['sibling_max_draws'])
    cls.EXACT_LENGTH=int(CFG['w2_h2_splice']['exact_glyph_length'])
    cls.RUN_SEED=int(run);cls.TARGET_BIF=str(bif)
    if mode=='SLOT_BT_OFF':
        if fold is None: raise ValueError('fold required for SLOT')
        cls.SLOT_TABLE=load_fold_tables(PACKAGE_ROOT/'parameters/v21_slot_tables'/f'fold{int(fold)}.json')
    return cls

def main():
    ap=argparse.ArgumentParser(description='v21 Stage-2 generator: V20_COMPAT or SAFE_LEFT')
    ap.add_argument('--fold',type=int,required=True,choices=range(5));ap.add_argument('--bif');ap.add_argument('--run',type=int);ap.add_argument('--runs');ap.add_argument('--mode',choices=['V20_COMPAT','SAFE_LEFT','SAFE_LEFT_BT_OFF','SLOT_BT_OFF'],default='SAFE_LEFT');ap.add_argument('--output-root',type=Path,default=PACKAGE_ROOT/'outputs/stage2');ap.add_argument('--skip-existing',action='store_true')
    a=ap.parse_args();fi=a.fold
    if a.run is not None:runs=[a.run]
    elif a.runs:runs=[int(x) for x in a.runs.split(',') if x.strip()]
    else:runs=DEFAULT_RUNS
    C=benv.e.context();frozen=json.loads((benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text());eta=pd.read_csv(ST/'parameters/SELECTED_ETA_BY_OUTER_FOLD.csv').set_index('outer_fold').loc[fi];cfg=MapConfig(**frozen[f'fold{fi}']);core=None;orig=rb.build_bt_leafex;rows=[]
    try:
        for bif in list(folds(C.bifs))[fi]:
            if a.bif and bif!=a.bif:continue
            alpha=float(SEL.loc[(fi,bif),'selected_alpha']);rb.build_bt_leafex=lambda ref,ext,a0=32.0,_alpha=alpha: real_build(ref,ext,_alpha)
            page=C.pages[bif][-1];fc=FoldContext.create(C,fi,bif,page,'LEGACY_SCOPE',POLICY)
            if core is None:core,ca=load_core(C,fc)
            ex=C.events[C.events.bif.isin(fc.complete_train_bifs)];kn=C.events[C.events.page.isin(fc.known_pages)];prev=rb.page_prevalence(C,fc);tab=DecomposedEntryTablesUV(ex,kn,*core[:2],core[3],fc,ca,eta_u=float(eta.eta_u),eta_v=float(eta.eta_v));patch=puv_config()
            for run in runs:
                cls=configure_sampler(a.mode,run,bif,fi);rb.PatchSampler=cls
                dest=a.output_root/f'run{run}'/ARM_IDS[a.mode].replace('-','_')/bif.replace(':','_')
                if a.skip_existing and (dest/'MECHANICAL.json').exists():continue
                res=rb.generate(C,fc,core,cfg,prev,patch,tab,run);rb.save_result(dest,res,fc,patch,tab);md=dict(res[1]);md.update(model_id=ARM_IDS[a.mode],v21_stage2_mode=a.mode,alpha_leafex=alpha,lambda_r4=float(CFG['body_r4_lambda']),w2h2splice=('L4_ONLY_K16_LEFT_ONLY' if a.mode=='SAFE_LEFT' else 'L4_ONLY_K16_LEFT_ONLY_BTOFF' if a.mode=='SAFE_LEFT_BT_OFF' else 'SLOT_STAGE4_BTOFF' if a.mode=='SLOT_BT_OFF' else 'L4_ONLY_K16_PROMOTED'));rows.append(md);print('GEN',a.mode,fi,bif,run,md['generated_rows_sha256'][:12],flush=True)
    finally:rb.build_bt_leafex=orig
    a.output_root.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(a.output_root/f'MECHANICAL_{a.mode}_fold{fi}.csv',index=False)
if __name__=='__main__':main()
