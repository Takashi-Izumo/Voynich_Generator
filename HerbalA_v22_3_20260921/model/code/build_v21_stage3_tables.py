from __future__ import annotations
import os, sys, json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

from runtime_bootstrap import prepare_runtime, ROOT as PACKAGE_ROOT
HANDOFF, PARENT, ST = prepare_runtime()
os.environ['EHC2_STAGE6_PARENT'] = str(PARENT)
sys.path.insert(0, str(ST/'code')); sys.path.insert(0, str(PACKAGE_ROOT/'code'))
from stage6_env import *
import experiment_env as benv
sys.path.insert(0, str(benv.EHC/'code')); sys.path.insert(0, str(benv.EHC/'parent/HerbalA_RMW1_BTI2_20260909/code'))
from fold_context import FoldContext, folds
from boundary_events import POLICY
import v19r_rb3_pw2_close1 as m
from w2_slot_tables import (
    ALPHA_GRID, H4_ALPHA_FIXED, VALID_WIDTHS, FoldSlotTables, H2Counts, H3Counts, H4Counts,
    canonical_event_hash, prepare_w2_events, prepare_body_h4_events,
    select_h2_inner_cv, select_h3_inner_cv, score_h2, score_h3, score_h4, save_fold_tables,
)

OUT = PACKAGE_ROOT/'validation/stage3'
TABLE_DIR = PACKAGE_ROOT/'parameters/v21_slot_tables'


def _domain_for_fold(C, fi, test_bifs):
    train_domains = []
    known_counts = []
    for bif in test_bifs:
        page = C.pages[bif][-1]
        fc = FoldContext.create(C, fi, bif, page, 'LEGACY_SCOPE', POLICY)
        train_domains.append(tuple(fc.complete_train_bifs))
        known_counts.append(len(fc.known_pages))
    if any(x != train_domains[0] for x in train_domains[1:]):
        raise AssertionError(f'fold {fi}: complete_train_bifs differs by target: {train_domains}')
    return train_domains[0], known_counts


def main():
    OUT.mkdir(parents=True, exist_ok=True); TABLE_DIR.mkdir(parents=True, exist_ok=True)
    C = benv.e.context(); fold_defs = list(folds(C.bifs))
    selection_rows=[]; domain_rows=[]; leak_rows=[]; count_rows=[]; outer_rows=[]; width_rows=[]
    h2_grids=[]; h3_grids=[]; table_rows=[]
    held_w2_all=[]; held_body_all=[]
    for fi, test_bifs in enumerate(fold_defs):
        train_bifs, known_counts = _domain_for_fold(C, fi, test_bifs)
        if set(train_bifs) & set(test_bifs):
            raise AssertionError(f'fold {fi}: leakage in bif lists')
        w2_train = prepare_w2_events(C.events, m.stable_width, train_bifs)
        body_train = prepare_body_h4_events(C.events, m.WIDTH, train_bifs)
        w2_test = prepare_w2_events(C.events, m.stable_width, test_bifs)
        body_test = prepare_body_h4_events(C.events, m.WIDTH, test_bifs)
        if set(w2_train.bif) & set(test_bifs): raise AssertionError('W2 target leakage')
        if set(body_train.bif) & set(test_bifs): raise AssertionError('BODY target leakage')
        if not set(w2_train.bif).issubset(set(train_bifs)): raise AssertionError('W2 unexpected bif')
        if not set(body_train.bif).issubset(set(train_bifs)): raise AssertionError('BODY unexpected bif')
        h2_best,h2_grid=select_h2_inner_cv(w2_train, ALPHA_GRID)
        h3_best,h3_grid=select_h3_inner_cv(w2_train, ALPHA_GRID)
        h2_grid.insert(0,'fold',fi); h3_grid.insert(0,'fold',fi); h2_grids.append(h2_grid); h3_grids.append(h3_grid)
        h2c=H2Counts.fit(w2_train); h3c=H3Counts.fit(w2_train); h4c=H4Counts.fit(body_train)
        w2_hash=canonical_event_hash(w2_train, f'fold{fi}:W2')
        body_hash=canonical_event_hash(body_train, f'fold{fi}:BODY_H4')
        tab=FoldSlotTables(
            fold=fi, train_bifs=tuple(train_bifs), test_bifs=tuple(test_bifs),
            h2_alpha=float(h2_best['alpha']), h2_depth=int(h2_best['depth']),
            h3_alpha=float(h3_best['alpha']), h4_alpha=float(H4_ALPHA_FIXED),
            h2=h2c,h3=h3c,h4=h4c,w2_event_sha256=w2_hash,body_h4_event_sha256=body_hash,
        )
        save_fold_tables(TABLE_DIR/f'fold{fi}.json',tab)
        # outer diagnostics; never used for selection.
        l2,n2=score_h2(w2_test,h2c,tab.h2_alpha,tab.h2_depth)
        l3,n3=score_h3(w2_test,h3c,tab.h3_alpha)
        l4,n4=score_h4(w2_test,h4c,tab.h4_alpha)
        outer_rows.append(dict(fold=fi,n_w2=n2,h2_loss=l2/n2,h3_loss=l3/n3,h4_loss=l4/n4,n_body_test=len(body_test)))
        for bif in test_bifs:
            sub=w2_test[w2_test.bif==bif]
            a2,b2=score_h2(sub,h2c,tab.h2_alpha,tab.h2_depth); a3,b3=score_h3(sub,h3c,tab.h3_alpha); a4,b4=score_h4(sub,h4c,tab.h4_alpha)
            outer_rows.append(dict(fold=fi,bif=bif,n_w2=b2,h2_loss=a2/b2,h3_loss=a3/b3,h4_loss=a4/b4,n_body_test=int((body_test.bif==bif).sum())))
        selection_rows.append(dict(fold=fi,h2_alpha=tab.h2_alpha,h2_context_depth=tab.h2_depth,h2_inner_loss=float(h2_best['token_loss']),h3_alpha=tab.h3_alpha,h3_inner_loss=float(h3_best['token_loss']),h4_alpha=tab.h4_alpha))
        domain_rows.append(dict(fold=fi,test_bifs=';'.join(test_bifs),train_bifs=';'.join(train_bifs),n_test_bifs=len(test_bifs),n_train_bifs=len(train_bifs),known_page_counts=';'.join(map(str,known_counts)),domain_consistent=True))
        for tb in test_bifs:
            leak_rows.append(dict(fold=fi,target_bif=tb,target_in_train=tb in train_bifs,target_w2_rows_in_training=int((w2_train.bif==tb).sum()),target_body_rows_in_training=int((body_train.bif==tb).sum()),status='PASS'))
        count_rows.append(dict(fold=fi,w2_train=len(w2_train),w2_test=len(w2_test),body_h4_train=len(body_train),body_h4_test=len(body_test),w2_h1_types=w2_train.H1.nunique(),w2_h2_types=w2_train.H2.nunique(),w2_h3_types=w2_train.H3.nunique(),w2_h4_types=w2_train.H4.nunique(),body_h3_types=body_train.H3.nunique(),body_h4_types=body_train.H4.nunique()))
        for w,n in w2_train.W.value_counts().sort_index().items(): width_rows.append(dict(fold=fi,split='train',W=int(w),n=int(n)))
        for w,n in w2_test.W.value_counts().sort_index().items(): width_rows.append(dict(fold=fi,split='test',W=int(w),n=int(n)))
        table_rows.append(dict(fold=fi,table_file=str((TABLE_DIR/f'fold{fi}.json').relative_to(PACKAGE_ROOT)),w2_event_sha256=w2_hash,body_h4_event_sha256=body_hash))
        held_w2_all.append(w2_test.assign(outer_fold=fi)); held_body_all.append(body_test.assign(outer_fold=fi))
        print('FOLD',fi,'W2 train/test',len(w2_train),len(w2_test),'BODY',len(body_train),len(body_test),'H2',tab.h2_depth,tab.h2_alpha,'H3',tab.h3_alpha,'loss',l2/n2,l3/n3,l4/n4,flush=True)
    pd.concat(h2_grids,ignore_index=True).to_csv(OUT/'H2_INNER_CV_GRID.csv',index=False)
    pd.concat(h3_grids,ignore_index=True).to_csv(OUT/'H3_INNER_CV_GRID.csv',index=False)
    pd.DataFrame(selection_rows).to_csv(OUT/'FOLD_SELECTION.csv',index=False)
    pd.DataFrame(domain_rows).to_csv(OUT/'TRAINING_DOMAINS.csv',index=False)
    pd.DataFrame(leak_rows).to_csv(OUT/'TARGET_LEAKAGE_AUDIT.csv',index=False)
    pd.DataFrame(count_rows).to_csv(OUT/'EVENT_COUNTS.csv',index=False)
    pd.DataFrame(width_rows).to_csv(OUT/'WIDTH_COUNTS.csv',index=False)
    pd.DataFrame(table_rows).to_csv(OUT/'TABLE_FILES.csv',index=False)
    outer_df=pd.DataFrame(outer_rows); outer_df.to_csv(OUT/'OUTER_DIAGNOSTICS.csv',index=False)
    held_w2=pd.concat(held_w2_all,ignore_index=True); held_body=pd.concat(held_body_all,ignore_index=True)
    # aggregate held-out diagnostics by rescoring per fold to preserve selected parameters.
    agg=[]
    for target in ('H2','H3','H4'):
        total_loss=0.0; total_n=0; bif_losses=[]
        for fi in range(5):
            tab=FoldSlotTables.from_json(json.loads((TABLE_DIR/f'fold{fi}.json').read_text()))
            te=held_w2[held_w2.outer_fold==fi]
            if target=='H2': l,n=score_h2(te,tab.h2,tab.h2_alpha,tab.h2_depth)
            elif target=='H3': l,n=score_h3(te,tab.h3,tab.h3_alpha)
            else: l,n=score_h4(te,tab.h4,tab.h4_alpha)
            total_loss+=l; total_n+=n
            for bif in te.bif.unique():
                s=te[te.bif==bif]
                if target=='H2': q,k=score_h2(s,tab.h2,tab.h2_alpha,tab.h2_depth)
                elif target=='H3': q,k=score_h3(s,tab.h3,tab.h3_alpha)
                else: q,k=score_h4(s,tab.h4,tab.h4_alpha)
                bif_losses.append(q/k)
        agg.append(dict(target=target,n=total_n,token_loss=total_loss/total_n,bif_mean_loss=float(np.mean(bif_losses))))
    pd.DataFrame(agg).to_csv(OUT/'OUTER_DIAGNOSTIC_SUMMARY.csv',index=False)
    summary={
      'stage':'V21_STAGE3_SLOT_TABLE_BUILDER','status':'PASS',
      'folds':5,'outer_w2_events':int(len(held_w2)),'outer_body_h4_events':int(len(held_body)),
      'expected_outer_w2_events':176,'expected_outer_body_h4_events':596,
      'valid_widths':list(VALID_WIDTHS),'h4_alpha_fixed':H4_ALPHA_FIXED,
      'leakage_failures':int((pd.DataFrame(leak_rows).status!='PASS').sum()),
      'selection':selection_rows,
      'outer_diagnostics':agg,
      'generator_connected':False,
    }
    if summary['outer_w2_events'] != 176: raise AssertionError(summary)
    if summary['outer_body_h4_events'] != 596: raise AssertionError(summary)
    if summary['leakage_failures'] != 0: raise AssertionError(summary)
    (OUT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')

if __name__=='__main__': main()
