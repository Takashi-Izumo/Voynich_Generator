"""Reject a raw policy row attributed to a different existing PF candidate."""
from pathlib import Path
import json
import os
import shutil
import sys

ROOT=Path(os.environ.get('PF_REVIEW_CHECKOUT','/workspace/voynich-results/m1-v2-independent-20261105/checkout'))
OUT=Path(os.environ.get('PF_REVIEW_ROOT','/workspace/voynich-results/pf-tracefix-independent-20261105'))
sys.path.insert(0,str(ROOT))
from experiments.pf_generation.tests.run_trace_probes import rows,write_rows
from experiments.pf_generation.audit import audit,verified_records
from experiments.pf_generation.evaluation import audited
from experiments.pf_generation.common import digest,file_hash,write_json

def main():
    plan=audited(OUT/'plan/plan.json',OUT/'forward')
    generated=OUT/'raw-candidate-context-copy'
    shutil.copytree(OUT/'forward',generated)
    manifest=json.loads((generated/'manifest.json').read_text())
    entry=next(r for r in manifest['records'] if r['arm']=='PF_GATE_LENGTH' and r['bif']=='A:2')
    case=generated/entry['path']
    proposals=rows(case/'pfgen_proposals.jsonl.gz')
    requests=rows(case/'requests.jsonl.gz')
    candidates=rows(case/'m1_candidates.jsonl.gz')
    row=proposals[0]
    original=dict(event=row['event'],candidate=row['candidate'],request_id=row['request_id'],call_id=row['call_id'])
    other=next(c for c in candidates if c['event']==row['event'] and c['candidate']!=row['candidate'])
    row['candidate']=other['candidate']
    request=requests[row['request_id']]
    assert request['pfgen']['candidate']!=row['candidate']
    receipt=next(r for r in request['pfgen']['raw_calls'] if r['call_id']==row['call_id'])
    receipt['row_sha256']=digest(row)
    for name,data in [('pfgen_proposals.jsonl.gz',proposals),('requests.jsonl.gz',requests)]:
        write_rows(case/name,data)
        entry['files'][name]=file_hash(case/name)
    write_json(generated/'manifest.json',manifest)
    verified_records(plan,generated)
    repeated=OUT/'raw-candidate-context-repeat-copy'
    shutil.copytree(OUT/'reverse',repeated)
    repeat_manifest=json.loads((repeated/'manifest.json').read_text())
    repeat_entry=next(r for r in repeat_manifest['records'] if r['arm']==entry['arm'] and r['bif']==entry['bif'])
    for name in ['pfgen_proposals.jsonl.gz','requests.jsonl.gz']:
        shutil.copyfile(case/name,repeated/repeat_entry['path']/name)
        repeat_entry['files'][name]=file_hash(repeated/repeat_entry['path']/name)
    write_json(repeated/'manifest.json',repeat_manifest)
    verified_records(plan,repeated)
    try:
        report=audit(OUT/'plan/plan.json',generated,OUT/'raw-candidate-context-audit',repeated)
        audited(OUT/'plan/plan.json',generated)
        status,reason='UNEXPECTED_ACCEPTANCE',report['status']
    except (ValueError,OSError,AssertionError) as exc:
        status,reason='REJECTED_AS_EXPECTED',str(exc)
    evidence=dict(status=status,reason=reason,original=original,raw_row_candidate_after=row['candidate'],
        authoritative_request_candidate=request['pfgen']['candidate'],checksums_and_receipt_digest_refreshed=True,
        tokens_state_rng_candidates_and_policy_decisions_unchanged=True,original_generation_unchanged=True,
        changed_case_files=['pfgen_proposals.jsonl.gz','requests.jsonl.gz'],
        same_change_in_both_orders=True,repeat_requested=True)
    write_json(OUT/'raw-candidate-context-probe.json',evidence)
    print(json.dumps(evidence,indent=2),flush=True)

if __name__=='__main__': main()
