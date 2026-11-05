"""Read-only differential diagnostic. NEVER issues an official AUDIT seal."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import time

ROOT=Path('/workspace/voynich-results/m1-v2-independent-20261105/checkout')
OUT=Path('/workspace/voynich-results/pf-repaired-full-comparison-20261106')

def main():
    import sys
    sys.path.insert(0,str(ROOT))
    from experiments.pf_generation.plan import load_plan
    from experiments.pf_generation.audit import verified_records,semantic_case,final_rng
    from experiments.m1_pf.runtime import Runtime
    from experiments.pf_generation.common import file_hash
    from experiments.pf_generation import TRACE_SCHEMA
    plan=load_plan(ROOT/'sandbox/m1-review/reports/024-pf-repaired-full-comparison-20261106/full-plan/plan.json')
    records=verified_records(plan,OUT/'generated')
    assert len(records)==800 and not (OUT/'generated/AUDIT.json').exists()
    protected={p:file_hash(p) for p in [OUT/'generated/manifest.json',OUT/'generated/STATUS.json',OUT/'audit/report.json']}
    runtime=Runtime();native={};schedule=[]
    for page,frame in runtime.C.schedules.items():
        for sr in frame.itertuples(index=False):
            key=str(sr.page),str(sr.locus),int(sr.segment_id)
            value=bool(int(sr.nsegments)>1 and int(sr.segment_id)==int(sr.nsegments)-1 and str(sr.boundary_type)=='LINE_END')
            assert key not in native
            native[key]=value
            if str(sr.page)=='f29v' and str(sr.locus)=='f29v.9':
                schedule.append(dict(page=key[0],locus=key[1],segment_id=key[2],nsegments=int(sr.nsegments),boundary_type=str(sr.boundary_type),literal_engine_split_end=value))
    source_path=ROOT/'experiments/pf_generation/policy_audit.py';source=source_path.read_text()
    old="row.get('trace_schema') == TRACE_SCHEMA and row['split_end'] == (row['segment_id'] > 0)"
    new="row.get('trace_schema') == TRACE_SCHEMA and type(row['split_end']) is bool and row['split_end'] == diagnostic_native_split[(row['page'],row['locus'],row['segment_id'])]"
    assert source.count(old)==1
    replacement=source.replace(old,new)
    ns={'__name__':'experiments.pf_generation._independent_split_diagnostic','__package__':'experiments.pf_generation','diagnostic_native_split':native}
    exec(compile(replacement,'<read-only diagnostic of policy_audit, no official seal>','exec'),ns)
    audited=[];base=0;t=time.monotonic()
    for bif in plan['bifolia']:
        for seed in plan['runs']:
            for arm in plan['arms']:
                result=ns['audit_case'](records[arm,bif,seed],arm,plan)
                audited.append(dict(arm=arm,bif=bif,run=seed,**result))
            a,b=records['BASE',bif,seed],records['REFERENCE',bif,seed]
            assert final_rng(a)==final_rng(b) and semantic_case(a)==semantic_case(b),(bif,seed)
            base+=1
            if base%25==0:print('DIAGNOSTIC',len(audited),'/600; BASE/REFERENCE',base,'/200',flush=True)
    assert all(file_hash(p)==h for p,h in protected.items())
    assert not (OUT/'generated/AUDIT.json').exists()
    report=dict(status='DIAGNOSTIC_ONLY_ALL_OTHER_CHECKS_PASS_NOT_AN_OFFICIAL_AUDIT_RELEASE',
        original_official_audit_remains='FAIL',original_audit_error='Wrong gate trace schema or split scope',
        comparison_plan_hash=plan['plan_hash'],generation_source='43a6895',checked_arm_cases=len(audited),
        base_reference_semantics_state_actual_rng_exact=base,original_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        diagnostic_source_sha256=hashlib.sha256(replacement.encode()).hexdigest(),only_replaced_expression={'original':old,'diagnostic':new},
        canonical_split_scope_source='Frozen Runtime.C.schedules; literal original engine nsegments/segment_id/boundary predicate',
        problem_schedule=schedule,official_seal_created=False,generated_artifacts_or_original_audit_changed=False,
        export_predictions_or_scoring_performed=False,wall_seconds=time.monotonic()-t,results=audited)
    (OUT/'differential-diagnostic.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['results','problem_schedule']}),flush=True)

if __name__=='__main__':main()
