"""Show the old scope test accepting a forged gain, on private case copies only."""
from pathlib import Path
import gzip
import json
import math
import shutil
import sys

ROOT=Path('/workspace/voynich-results/m1-v2-independent-20261105/checkout')
OUT=Path('/workspace/voynich-results/pf-repaired-full-comparison-20261106')
sys.path.insert(0,str(ROOT))

def main():
    from experiments.pf_generation.plan import load_plan
    from experiments.pf_generation.policy_audit import audit_case,read_rows,sigmoid,logit
    from experiments.pf_generation.common import file_hash
    plan=load_plan(ROOT/'sandbox/m1-review/reports/024-pf-repaired-full-comparison-20261106/full-plan/plan.json')
    records=json.loads((OUT/'generated/manifest.json').read_text())['records'];results=[]
    for arm in ['PF_GATE','PF_GATE_LENGTH']:
        entry=next(r for r in records if (r['arm'],r['bif'],r['run'])==(arm,'D:4',91701))
        source=OUT/'generated'/entry['path'];copy=OUT/'split-false-accept'/arm;shutil.copytree(source,copy)
        hashes={p.name:file_hash(p) for p in source.iterdir() if p.is_file()}
        try:audit_case(source,arm,plan)
        except ValueError as exc:assert str(exc)=='Wrong gate trace schema or split scope'
        else:raise AssertionError('Expected the original correct case to be rejected')
        rows=read_rows(copy/'pfgen_gates.jsonl.gz');changed=0
        for row in rows:
            if row['page']=='f29v' and row['locus']=='f29v.9' and row['segment_id']==2:
                assert row['split_end'] is False
                row['split_end']=True
                row['engine_probability']=sigmoid(logit(row['adapted_probability'])+math.log(.8))
                changed+=1
        assert changed>0
        with gzip.open(copy/'pfgen_gates.jsonl.gz','wt') as f:
            for row in rows:f.write(json.dumps(row,sort_keys=True)+'\n')
        accepted=audit_case(copy,arm,plan)
        assert all(file_hash(copy/name)==h for name,h in hashes.items() if name!='pfgen_gates.jsonl.gz')
        assert all(file_hash(source/name)==h for name,h in hashes.items())
        results.append(dict(arm=arm,bif='D:4',run=91701,status='FALSE_ACCEPT_REPRODUCED',
            correct_original_case_rejected=True,forged_wrong_gain_case_accepted=True,changed_gate_rows=changed,
            modified_files=['pfgen_gates.jsonl.gz'],unmodified_generated_and_request_evidence=len(hashes)-1,
            expected_frozen_engine_split_end=False,forged_split_end=True,forged_extra_gain=.8,
            level='per-case audit API; no full-run PASS seal issued'))
    assert not (OUT/'generated/AUDIT.json').exists()
    (OUT/'split-false-accept.json').write_text(json.dumps(dict(status='AUDITOR_FALSE_REJECTION_AND_FALSE_ACCEPT_REPRODUCED',
        generation_unchanged=True,source_unchanged=True,official_seal_created=False,results=results),indent=2)+'\n')
    print(json.dumps(results),flush=True)

if __name__=='__main__':main()
