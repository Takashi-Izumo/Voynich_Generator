"""Read-only source/structure/frozen-selector audit for study-two design.

No new fitting, generation, donor replay, judge prediction or keyed scoring.
Only the pinned LEGACY_SCOPE frozen core-cache loader is used.
"""
from pathlib import Path
from collections import Counter
import argparse
import gc
import hashlib
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();assert not a.output.exists()
    from experiments.m1_pf.runtime import Runtime
    from experiments.pf_generation.common import file_hash,digest
    rt=Runtime();C=rt.C;fold_rows=[];checks=0;geometry=Counter();anomalies=[]
    for fold in range(5):
        bif=next(b for b in sorted(C.bifs) if int(rt.active.SEL.reset_index().set_index('bif').loc[b,'fold'])==fold)
        fc=rt.active.FoldContext.create(C,fold,bif,C.pages[bif][-1],'LEGACY_SCOPE',rt.active.POLICY)
        assert fc.scope_policy=='LEGACY_SCOPE'
        # This branch raises when the frozen cache is absent; it cannot silently fit.
        core,meta=rt.active.load_core(C,fc)
        assert meta['mode']=='FROZEN_18'
        selector=core[5];assert selector.kind=='PF'
        actual=selector.score.__globals__['pf_features']
        for surface in ['',*[rt.engine.m.I2G[i] for i in range(22)]]:
            for width,capacity in [(1,5),(5,12),(12,12)]:
                features=Counter(actual(surface,width,capacity))
                score=selector.score(surface,width,capacity)
                direct=selector.intercept+sum(selector.coefficients.get(k,0.)*n for k,n in features.items())
                assert score==direct
                assert len([k for k in features if k.startswith('E=')])==1
                assert len([k for k in features if k.startswith('EF=')])==1
                checks+=1
        fold_rows.append(dict(fold=fold,representative_bif=bif,core_mode=meta['mode'],core_cache_sha256=meta['sha256'],
            complete_external_bifolia=list(fc.complete_train_bifs),incomplete_aux_bifolia=list(fc.incomplete_aux_bifs),
            core_training_bifolia=list(fc.core_train_bifs),outer_test_bifolia=list(fc.outer_test_bifs),
            actual_selector_training_bifolia=selector.metadata.get('training_bifolia'),
            selector_excluded_bifolia=list(selector.excluded_bifolia),selector_payload_sha256=digest(selector.to_dict()),
            individual_terminal_coefficients={k:v for k,v in selector.coefficients.items() if k.startswith('E=')},
            terminal_family_coefficients={k:v for k,v in selector.coefficients.items() if k.startswith('EF=')},
            intercept=selector.intercept))
        del core,selector;gc.collect()
    for bif in C.bifs:
        page=C.pages[bif][-1];schedule=C.schedules[page]
        for sr in schedule.itertuples(index=False):
            if not rt.engine.is_pf(sr):continue
            ids=tuple(int(x) for x in schedule.loc[schedule.locus.astype(str)==str(sr.locus),'segment_id'])
            split=bool(int(sr.nsegments)>1 and int(sr.segment_id)==int(sr.nsegments)-1 and str(sr.boundary_type)=='LINE_END')
            key=int(sr.nsegments),int(sr.segment_id),ids,split
            geometry[key]+=1
            if split!=(int(sr.segment_id)>0):
                anomalies.append(dict(bif=str(bif),page=str(sr.page),locus=str(sr.locus),segment_id=int(sr.segment_id),
                    nsegments=int(sr.nsegments),retained_segment_ids=list(ids),boundary_type=str(sr.boundary_type),
                    literal_split_end=split,old_audit_assumption=int(sr.segment_id)>0))
    paths={
        'selector':Path(sys.modules['sel42_selectors'].__file__),
        'engine':Path(rt.engine.__file__),
        'fold_context':Path(sys.modules['fold_context'].__file__),
        'native_runtime':ROOT/'experiments/m1_pf/runtime.py',
        'surface_commit_repair':ROOT/'experiments/pf_generation/surface_commit.py',
    }
    output=dict(status='READ_ONLY_DESIGN_SOURCE_AUDIT_PASS',source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        product_source='43a6895',source_files={k:dict(path=str(v.relative_to(ROOT)),sha256=file_hash(v)) for k,v in paths.items()},
        frozen_selector_loading='LEGACY_SCOPE frozen18 cache only; no COMPLETE16_REFIT or selector load_pair shortcut',
        folds=fold_rows,score_feature_arithmetic_checks=checks,
        target_pf_geometry=[dict(nsegments=k[0],segment_id=k[1],retained_segment_ids=list(k[2]),literal_split_end=k[3],events=v) for k,v in sorted(geometry.items())],
        split_scope_counterexamples=anomalies,new_fits=0,new_generated_pages=0,judge_predictions=0,keyed_scores=0)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps(dict(status=output['status'],fold_training_sizes=[len(x['core_training_bifolia']) for x in fold_rows],
        selector_training_sizes=[len(x['actual_selector_training_bifolia']) for x in fold_rows],checks=checks,
        geometry_profiles=len(geometry),split_counterexamples=anomalies,new_fits=0,new_generated_pages=0)))

if __name__=='__main__':main()
