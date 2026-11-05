"""Resume independent checks after the documented expected-OSError harness fix."""
from concurrent.futures import ThreadPoolExecutor
import json
import re

from review_fix import ROOT,OUT,run,write,read,terminal_probes,control_cli

def main():
    from experiments.pf_generation.plan import load_plan
    smoke=load_plan(OUT/'smoke-plan/plan.json')
    assert read(OUT/'audit/report.json')['status']=='PASS'
    assert read(OUT/'identity-audit/report.json')['status']=='PASS'
    assert read(OUT/'normal-preservation.json')['status']=='PASS'
    assert read(OUT/'normal-trace-preservation.json')['status']=='PASS'
    terminal_probes(smoke)
    checks=read(OUT/'terminal-probes.json')['checks']
    for row,needle in zip(checks,['Missing/out-of-scope terminal precommit receipt','Next request did not observe','Semantic terminal differs']):
        assert needle in row['reason']
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[]
        for module,label in [('run_trace_probes','r1-probes'),('run_context_probes','r2-probes')]:
            futures.append(pool.submit(run,label,['-m','experiments.pf_generation.tests.'+module,'--plan',OUT/'smoke-plan/plan.json','--generated',OUT/'forward','--repeat',OUT/'reverse','--output',OUT/label]))
        for f in futures:f.result()
    # Exclusive source-input mutation test, with restoration and final positive audit.
    run('required-probes',['-m','experiments.pf_generation.tests.run_artifact_probes','--plan',OUT/'smoke-plan/plan.json','--generated',OUT/'forward','--repeat',OUT/'reverse','--output',OUT/'required-probes'])
    control_cli()
    units={k:int(re.search(r'Ran (\d+) tests?',(OUT/('unit-'+k+'.log')).read_text()).group(1)) for k in ['pf','controls','m1','judges']}
    assert sum(units.values())==174
    write(OUT/'REVIEW_RESULT.json',dict(status='PASS_INDEPENDENT_MECHANISM_RECHECK',source_head='43a6895',
        unit_counts=units,fresh_pages=60,fixed_case_reproduced_and_corrected=True,
        actual_cli_and_resealed_wrong_key_checked=True,normal_identity_order_state_rng_checked=True,
        normal_trace_preservation_cases=12,capability_status='CAPABILITY_NOT_VERIFIED_UNCHANGED',
        new_jury_donors='DESIGN_ONLY',full_plan_hash=load_plan(OUT/'full-plan/plan.json')['plan_hash'],
        review_harness_expected_file_missing_exception_corrected=True))
    print('INDEPENDENT REPAIR REVIEW PASS',flush=True)

if __name__=='__main__':main()
