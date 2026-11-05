"""Independent review authority for descriptive computation; no product AUDIT seal.

The product audit's FAIL is preserved. Only its incorrect split-label predicate
is replaced in a private, read-only validator by the literal frozen schedule
predicate. All generation, model, masks and statistical rules remain unchanged.
"""
from pathlib import Path
import hashlib
import json
import sys
import time

ROOT=Path('/workspace/voynich-results/m1-v2-independent-20261105/checkout')
OUT=Path('/workspace/voynich-results/pf-repaired-full-comparison-20261106')
CHECK=Path('/workspace/voynich-results/pf-surface-independent-20261106')
PLAN=ROOT/'sandbox/m1-review/reports/024-pf-repaired-full-comparison-20261106/full-plan/plan.json'
sys.path.insert(0,str(ROOT))

def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def kernel(plan):
    from experiments.m1_pf.runtime import Runtime
    from experiments.pf_generation.common import file_hash
    rt=Runtime();native={}
    for frame in rt.C.schedules.values():
        for sr in frame.itertuples(index=False):
            key=str(sr.page),str(sr.locus),int(sr.segment_id)
            assert key not in native
            native[key]=bool(int(sr.nsegments)>1 and int(sr.segment_id)==int(sr.nsegments)-1 and str(sr.boundary_type)=='LINE_END')
    path=ROOT/'experiments/pf_generation/policy_audit.py'
    original=path.read_text()
    assert file_hash(path)==plan['implementation_sources']['experiments/pf_generation/policy_audit.py']
    old="row.get('trace_schema') == TRACE_SCHEMA and row['split_end'] == (row['segment_id'] > 0)"
    new="row.get('trace_schema') == TRACE_SCHEMA and type(row['split_end']) is bool and row['split_end'] == diagnostic_native_split[(row['page'],row['locus'],row['segment_id'])]"
    assert original.count(old)==1
    corrected=original.replace(old,new)
    diagnostic=read(OUT/'differential-diagnostic.json')
    assert diagnostic['original_source_sha256']==hashlib.sha256(original.encode()).hexdigest()
    assert diagnostic['diagnostic_source_sha256']==hashlib.sha256(corrected.encode()).hexdigest()
    ns={'__name__':'experiments.pf_generation._review_native_scope','__package__':'experiments.pf_generation','diagnostic_native_split':native}
    exec(compile(corrected,'<independent native-scope validator; product source unchanged>','exec'),ns)
    return ns['audit_case'],dict(original=old,independent=new,
        original_source_sha256=hashlib.sha256(original.encode()).hexdigest(),independent_source_sha256=hashlib.sha256(corrected.encode()).hexdigest())

def negative_checks(validator):
    from experiments.pf_generation.plan import load_plan
    smoke=load_plan(CHECK/'smoke-plan/plan.json');full=load_plan(PLAN);results=[]
    originals={}
    for order in ['forward','reverse']:
        originals[order]={(r['arm'],r['bif'],r['run']):r for r in read(CHECK/order/'manifest.json')['records']}
    for family,directory,expected in [('R1',CHECK/'r1-probes',13),('R2',CHECK/'r2-probes',11),('TERMINAL',CHECK/'terminal-probes-rechecked',3)]:
        roots=sorted(p for p in directory.iterdir() if p.is_dir() and (p/'forward/manifest.json').exists())
        assert len(roots)==expected,(family,len(roots))
        for root in roots:
            changed=[]
            for order in ['forward','reverse']:
                if not (root/order/'manifest.json').exists():continue
                for r in read(root/order/'manifest.json')['records']:
                    key=r['arm'],r['bif'],r['run']
                    if r['files']!=originals[order][key]['files']:changed.append((root/order/r['path'],r['arm']))
            assert changed,root
            p,arm=changed[0]
            try:validator(p,arm,smoke)
            except (ValueError,AssertionError) as exc:
                results.append(dict(family=family,probe=root.name,rejected=True,reason=str(exc)))
            else:raise AssertionError('Independent validator accepted '+str(root))
    for arm in ['PF_GATE','PF_GATE_LENGTH']:
        try:validator(OUT/'split-false-accept'/arm,arm,full)
        except ValueError as exc:
            assert str(exc)=='Wrong gate trace schema or split scope'
            results.append(dict(family='NATIVE_SPLIT',probe=arm,rejected=True,reason=str(exc),product_auditor_accepts_this_forgery=True))
        else:raise AssertionError('Independent validator accepted false split gain')
    assert len(results)==29
    return results

def main():
    from experiments.pf_generation.plan import load_plan
    from experiments.pf_generation.audit import verified_records,generation_binding,semantic_case,final_rng
    from experiments.pf_generation.common import file_hash
    t=time.monotonic();plan=load_plan(PLAN);bound=generation_binding(plan,OUT/'generated')
    fail_hash=file_hash(OUT/'audit/report.json')
    assert read(OUT/'audit/report.json')['status']=='FAIL' and not (OUT/'generated/AUDIT.json').exists()
    validator,scope_change=kernel(plan);negatives=negative_checks(validator)
    write(OUT/'independent-native-scope-negative-checks.json',dict(status='PASS',checks=negatives))
    records=verified_records(plan,OUT/'generated');results=[];refs=0
    for bif in plan['bifolia']:
        for seed in plan['runs']:
            for arm in plan['arms']:
                result=validator(records[arm,bif,seed],arm,plan)
                results.append(dict(arm=arm,bif=bif,run=seed,**result))
            a,b=records['BASE',bif,seed],records['REFERENCE',bif,seed]
            assert final_rng(a)==final_rng(b) and semantic_case(a)==semantic_case(b)
            refs+=1
            if refs%25==0:print('INDEPENDENT AUDIT',len(results),'/600; exact BASE/REFERENCE',refs,'/200',flush=True)
    assert generation_binding(load_plan(PLAN),OUT/'generated')==bound
    assert file_hash(OUT/'audit/report.json')==fail_hash and not (OUT/'generated/AUDIT.json').exists()
    report=dict(status='PASS_INDEPENDENT_NATIVE_SCOPE_REVIEW_FOR_DESCRIPTIVE_COMPUTATION',
        schema_version=1,comparison_plan_hash=plan['plan_hash'],generation_source='43a6895',generation_binding=bound,
        model_set_hash=plan['required_model_set_hash'],checked_arm_cases=len(results),exact_base_reference_cases=refs,
        negative_checks=29,negative_checks_sha256=file_hash(OUT/'independent-native-scope-negative-checks.json'),
        correction=scope_change,official_audit_status='FAIL_PRESERVED',official_audit_report_sha256=fail_hash,
        official_AUDIT_seal_created=False,generated_data_or_product_source_modified=False,
        release_scope='read-only independent reviewer authority for the already requested descriptive comparison only',
        quality_equivalence_or_promotion_claims=False,capability_status='CAPABILITY_NOT_VERIFIED_UNCHANGED',
        review_code_sha256=file_hash(Path(__file__)),wall_seconds=time.monotonic()-t,results=results)
    write(OUT/'independent-audit-review.json',report)
    print('INDEPENDENT NATIVE-SCOPE REVIEW PASS; OFFICIAL FAIL PRESERVED; NO PREDICTIONS YET',flush=True)

def authorized():
    from experiments.pf_generation.plan import load_plan
    from experiments.pf_generation.audit import generation_binding
    from experiments.pf_generation.common import file_hash
    p=load_plan(PLAN);review=read(OUT/'independent-audit-review.json')
    assert review['status']=='PASS_INDEPENDENT_NATIVE_SCOPE_REVIEW_FOR_DESCRIPTIVE_COMPUTATION'
    assert review['comparison_plan_hash']==p['plan_hash'] and review['generation_binding']==generation_binding(p,OUT/'generated')
    assert review['review_code_sha256']==file_hash(Path(__file__))
    assert review['negative_checks_sha256']==file_hash(OUT/'independent-native-scope-negative-checks.json')
    assert review['official_audit_report_sha256']==file_hash(OUT/'audit/report.json')
    assert not (OUT/'generated/AUDIT.json').exists()
    return p,review

if __name__=='__main__':main()
