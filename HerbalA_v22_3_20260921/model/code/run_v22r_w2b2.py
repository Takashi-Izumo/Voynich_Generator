from __future__ import annotations
import os, sys, json, argparse
from pathlib import Path
import pandas as pd

from runtime_bootstrap import prepare_runtime, ROOT as PACKAGE_ROOT
HANDOFF, PARENT, ST = prepare_runtime()
os.environ['EHC2_STAGE6_PARENT'] = str(PARENT)
sys.path.insert(0, str(ST/'code')); sys.path.insert(0, str(PACKAGE_ROOT/'code'))
from stage6_env import *
import experiment_env as benv
sys.path.insert(0, str(benv.EHC/'code')); sys.path.insert(0, str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
import run_bti2_ehc1 as rb
import bti2_patch_state as patch_state_mod
from fold_context import FoldContext, load_core, folds
from route_map_model import MapConfig, build_bt_leafex as real_build
from boundary_events import POLICY
from e1_decomposed_uv import DecomposedEntryTablesUV, puv_config
from paragraph_h1_state import ParagraphH1PatchMapState
from w2_b2_sampler import V22rW2B2Sampler, V22rW2B2NoOpSampler

DEFAULT_RUNS=[91701]
PARAM=PACKAGE_ROOT/'parameters'
SEL=pd.read_csv(PARAM/'LEAFEX_ALPHA_SELECTED.csv').set_index(['fold','bif'])
CFG=json.loads((PARAM/'MODEL_CONFIG.json').read_text(encoding='utf-8'))
BASELINE=PARAM/'PARAGRAPH_H1_BASELINE.json'
B2CFG=json.loads((PARAM/'W2_B2_CONFIG.json').read_text(encoding='utf-8'))
ORIGINAL_PATCH_STATE=patch_state_mod.PatchMapState

ARM_IDS={
    'B2_NOOP':'HerbalA-v22r-W2B2-NOOP',
    'B2':'HerbalA-v22r-W2B2',
}
CLASSES={'B2_NOOP':V22rW2B2NoOpSampler,'B2':V22rW2B2Sampler}


def configure(mode, run, bif):
    cls=CLASSES[mode]
    cls.BODY_R4_LAMBDA=float(CFG['body_r4_lambda'])
    cls.SIBLING_K=int(CFG['w2_h2_splice']['sibling_k'])
    cls.SIBLING_MAX_DRAWS=int(CFG['w2_h2_splice']['sibling_max_draws'])
    cls.EXACT_LENGTH=int(CFG['w2_h2_splice']['exact_glyph_length'])
    cls.RUN_SEED=int(run); cls.TARGET_BIF=str(bif)
    cls.W2_B2_ENABLED=(mode == 'B2') and bool(B2CFG['enabled'])
    cls.W2_B2_MIN_LEN=int(B2CFG['scope']['min_glyph_length'])
    cls.W2_B2_MAX_LEN=int(B2CFG['scope']['max_glyph_length'])
    cls.W2_B2_KNOWN_TAU=float(B2CFG['target_h2_law']['known3_tau'])
    cls.W2_B2_NAMESPACE=str(B2CFG['selection']['namespace'])
    cls.configure_baseline(BASELINE)
    return cls


def main():
    ap=argparse.ArgumentParser(description='HerbalA v22r + accepted W2-B2 H2-only postcommit repair')
    ap.add_argument('--fold',type=int,required=True,choices=range(5)); ap.add_argument('--bif')
    ap.add_argument('--run',type=int); ap.add_argument('--runs')
    ap.add_argument('--mode',choices=list(CLASSES),default='B2')
    ap.add_argument('--output-root',type=Path,default=PACKAGE_ROOT/'outputs/w2_b2')
    ap.add_argument('--skip-existing',action='store_true')
    a=ap.parse_args(); fi=a.fold
    runs=[a.run] if a.run is not None else [int(x) for x in a.runs.split(',') if x.strip()] if a.runs else DEFAULT_RUNS

    C=benv.e.context()
    frozen=json.loads((benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/parameters/FROZEN_FOLD_CONFIGS.json').read_text())
    eta=pd.read_csv(ST/'parameters/SELECTED_ETA_BY_OUTER_FOLD.csv').set_index('outer_fold').loc[fi]
    cfg=MapConfig(**frozen[f'fold{fi}']); core=None; orig_bt=rb.build_bt_leafex; orig_state=rb.PatchMapState; rows=[]
    try:
        rb.PatchMapState=ParagraphH1PatchMapState
        for bif in list(folds(C.bifs))[fi]:
            if a.bif and bif!=a.bif: continue
            alpha=float(SEL.loc[(fi,bif),'selected_alpha'])
            rb.build_bt_leafex=lambda ref,ext,a0=32.0,_alpha=alpha: real_build(ref,ext,_alpha)
            page=C.pages[bif][-1]
            fc=FoldContext.create(C,fi,bif,page,'LEGACY_SCOPE',POLICY)
            if core is None: core,ca=load_core(C,fc)
            ex=C.events[C.events.bif.isin(fc.complete_train_bifs)]
            kn=C.events[C.events.page.isin(fc.known_pages)]
            prev=rb.page_prevalence(C,fc)
            tab=DecomposedEntryTablesUV(ex,kn,*core[:2],core[3],fc,ca,eta_u=float(eta.eta_u),eta_v=float(eta.eta_v))
            patch=puv_config()
            for run in runs:
                cls=configure(a.mode,run,bif); rb.PatchSampler=cls
                dest=a.output_root/f'run{run}'/ARM_IDS[a.mode].replace('-','_')/bif.replace(':','_')
                if a.skip_existing and (dest/'MECHANICAL.json').exists(): continue
                res=rb.generate(C,fc,core,cfg,prev,patch,tab,run)
                req=[r for r in res[3].get('requests',[]) if bool(r.get('committed_to_final_page',False))]
                applied=[r for r in req if bool(r.get('b2_h2_applied',False))]
                changed=[r for r in req if bool(r.get('b2_h2_changed',False))]
                audit=dict(
                    applied=len(applied), changed=len(changed),
                    parent_rng_untouched=all(bool(r.get('b2_h2_parent_rng_untouched',False)) for r in applied),
                    semantic_precommit_untouched=all(bool(r.get('b2_h2_semantic_state_untouched',False)) for r in applied),
                )
                res[1].update(model_id=ARM_IDS[a.mode],w2_b2_mode=a.mode,w2_b2_audit=audit,alpha_leafex=alpha,lambda_r4=float(CFG['body_r4_lambda']),judge_scores_run=False)
                rb.save_result(dest,res,fc,patch,tab)
                md=dict(res[1]); rows.append(md)
                print('GEN',a.mode,fi,bif,run,md['generated_rows_sha256'][:12],audit,flush=True)
    finally:
        rb.build_bt_leafex=orig_bt; rb.PatchMapState=orig_state
    a.output_root.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(a.output_root/f'MECHANICAL_{a.mode}_fold{fi}.csv',index=False)

if __name__=='__main__': main()
