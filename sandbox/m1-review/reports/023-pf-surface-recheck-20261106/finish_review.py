"""Finish only preserved-data comparison and wrong-key CLI after binding fix."""
from copy import deepcopy
import re
import shutil
import json
from review_fix import ROOT,OUT,OLD_CONTROL,read,write,run

def main():
    from experiments.pf_controls.common import unseal,seal,file_inventory
    from experiments.pf_generation.plan import load_plan
    fresh=unseal(read(OUT/'control-generate/A_2.json'));old=unseal(read(OLD_CONTROL/'A_2.json'))
    binding_diff={k for k in fresh if fresh[k]!=old[k]};assert binding_diff=={'sha256','plan_sha256'}
    for d in [fresh,old]:d.pop('plan_sha256');d.pop('sha256')
    assert fresh==old
    write(OUT/'control-preservation.json',dict(status='PASS',base_snapshot_donors_selections_exact=True,
        donors=len(fresh['donors']),events=len(fresh['snapshots']),only_validated_plan_binding_and_its_outer_hash_differ=True))
    bad=OUT/'control-wrong-key';shutil.copytree(OUT/'control-export',bad)
    key=next(bad.glob('*/answer_key.jsonl'));keys=[json.loads(x) for x in key.read_text().splitlines()]
    keys[0]['truth']='B' if keys[0]['truth']=='A' else 'A';key.write_text(''.join(json.dumps(x)+'\n' for x in keys))
    m=unseal(read(bad/'EXPORT.json'));m.pop('sha256');m['files']=file_inventory(bad,('EXPORT.json',));write(bad/'EXPORT.json',seal(m))
    unseal(read(bad/'EXPORT.json'))
    run('control-real-cli-wrong-key',['-m','experiments.pf_controls','verify-export','--plan',OUT/'control-plan/plan.json',
        '--generated',OUT/'control-generate','--exported',bad],expected=1)
    assert 'Export assignment/text/key/diagnostic mismatch' in (OUT/'control-real-cli-wrong-key.log').read_text()
    units={k:int(re.search(r'Ran (\d+) tests?',(OUT/('unit-'+k+'.log')).read_text()).group(1)) for k in ['pf','controls','m1','judges']}
    assert sum(units.values())==174
    for path in ['audit/report.json','identity-audit/report.json','normal-preservation.json','normal-trace-preservation.json',
                 'terminal-probes.json','r1-probes/trace-probes.json','r2-probes/context-probes.json','required-probes/probes.json','control-audit/report.json']:
        assert read(OUT/path)['status']=='PASS'
    write(OUT/'REVIEW_RESULT.json',dict(status='PASS_INDEPENDENT_MECHANISM_RECHECK',source_head='43a6895',unit_counts=units,
        fresh_pages=60,fixed_case_reproduced_and_corrected=True,actual_cli_and_resealed_wrong_key_checked=True,
        normal_identity_order_state_rng_checked=True,normal_trace_preservation_cases=12,
        capability_status='CAPABILITY_NOT_VERIFIED_UNCHANGED',new_jury_donors='DESIGN_ONLY',
        full_plan_hash=load_plan(OUT/'full-plan/plan.json')['plan_hash'],review_harness_corrections_disclosed=True))
    print('INDEPENDENT REPAIR REVIEW PASS',flush=True)

if __name__=='__main__':main()
