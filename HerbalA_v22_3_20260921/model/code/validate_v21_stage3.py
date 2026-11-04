from __future__ import annotations
import json, os, sys, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from runtime_bootstrap import prepare_runtime, ROOT as PACKAGE_ROOT
HANDOFF,PARENT,ST=prepare_runtime(); os.environ['EHC2_STAGE6_PARENT']=str(PARENT)
sys.path.insert(0,str(ST/'code'));sys.path.insert(0,str(PACKAGE_ROOT/'code'))
from stage6_env import *
import experiment_env as benv
sys.path.insert(0,str(benv.EHC/'code'));sys.path.insert(0,str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
from fold_context import FoldContext,folds
from boundary_events import POLICY
import v19r_rb3_pw2_close1 as m
from w2_slot_tables import load_fold_tables,prepare_w2_events,prepare_body_h4_events,canonical_event_hash,VALID_WIDTHS


def main():
    C=benv.e.context(); defs=list(folds(C.bifs)); table_dir=PACKAGE_ROOT/'parameters/v21_slot_tables'; out=PACKAGE_ROOT/'validation/stage3'
    rows=[]
    for fi,test_bifs in enumerate(defs):
        tab=load_fold_tables(table_dir/f'fold{fi}.json')
        assert tuple(tab.test_bifs)==tuple(test_bifs)
        for tb in test_bifs:
            fc=FoldContext.create(C,fi,tb,C.pages[tb][-1],'LEGACY_SCOPE',POLICY)
            assert tuple(fc.complete_train_bifs)==tuple(tab.train_bifs)
            assert tb not in tab.train_bifs
        w2=prepare_w2_events(C.events,m.stable_width,tab.train_bifs); body=prepare_body_h4_events(C.events,m.WIDTH,tab.train_bifs)
        assert canonical_event_hash(w2,f'fold{fi}:W2')==tab.w2_event_sha256
        assert canonical_event_hash(body,f'fold{fi}:BODY_H4')==tab.body_h4_event_sha256
        assert set(w2.W.unique()).issubset(set(VALID_WIDTHS))
        # probability normalization and positivity on every observed context
        checks=0
        for r in w2.itertuples(index=False):
            for p in (tab.prob_h2(r.H1,r.W,r.T,r.PHASE),tab.prob_h3(r.H1,r.W),tab.prob_h4(r.H3)):
                assert p.shape==(22,); assert np.isfinite(p).all(); assert (p>0).all(); assert abs(float(p.sum())-1.0)<1e-10; checks+=1
        rows.append(dict(fold=fi,status='PASS',w2_train=len(w2),body_h4_train=len(body),probability_checks=checks,h2_alpha=tab.h2_alpha,h2_depth=tab.h2_depth,h3_alpha=tab.h3_alpha,h4_alpha=tab.h4_alpha))
    pd.DataFrame(rows).to_csv(out/'VALIDATION.csv',index=False)
    print(json.dumps({'status':'PASS','folds':5,'rows':rows},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
