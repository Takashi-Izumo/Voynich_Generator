"""Read-only comparison with the previous independent schema-v2 run."""
import os
import json
from pathlib import Path
import sys

ROOT=Path(os.environ.get('PF_REVIEW_CHECKOUT','/workspace/voynich-results/m1-v2-independent-20261105/checkout'))
OUT=Path(os.environ.get('PF_REVIEW_ROOT','/workspace/voynich-results/pf-r2-independent-20261105'))
PRIOR=Path(os.environ.get('PF_REVIEW_PRIOR_ROOT','/workspace/voynich-results/pf-tracefix-independent-20261105'))
sys.path.insert(0,str(ROOT))
from experiments.pf_generation.audit import semantic_case,read_jsonl
from experiments.pf_generation.common import file_hash,write_json

def main():
    current=json.loads((OUT/'forward/manifest.json').read_text())['records']
    prior=json.loads((PRIOR/'forward/manifest.json').read_text())['records']
    lookup={(r['arm'],r['bif'],r['run']):r for r in prior}
    cases=[]
    for r in current:
        key=r['arm'],r['bif'],r['run']
        a,b=OUT/'forward'/r['path'],PRIOR/'forward'/lookup[key]['path']
        assert semantic_case(a)==semantic_case(b),key
        for name in ['pfgen_gates.jsonl.gz','pfgen_proposals.jsonl.gz','requests.jsonl.gz']:
            assert read_jsonl(a/name)==read_jsonl(b/name),(key,name)
        if r['arm']!='REFERENCE':
            for name in ['m1_events.jsonl.gz','m1_candidates.jsonl.gz']:
                assert read_jsonl(a/name)==read_jsonl(b/name),(key,name)
        cases.append(dict(arm=r['arm'],bif=r['bif'],run=r['run'],semantic_state_actual_main_rng_equal=True,
                          all_policy_and_request_metadata_equal=True))
    artifacts=[]
    for family,names in [('predictions',['predictions.jsonl','channels.jsonl']),('scores',['measurements.jsonl','summary.json'])]:
        for arm in ['BASE','PF_GATE','PF_GATE_LENGTH']:
            for name in names:
                rel=Path('evaluation')/family/arm/name
                assert file_hash(OUT/rel)==file_hash(PRIOR/rel),str(rel)
                artifacts.append(dict(path=str(rel),sha256=file_hash(OUT/rel),byte_equal=True))
    write_json(OUT/'prior-comparison.json',dict(status='PASS',prior='Previous independent reviewer schema-v2 run',
        cases=cases,evaluation_artifacts=artifacts,quality_inference=None))
    print('PASS: 12 cases incl. state/main RNG and policy/request metadata; 12 prediction/score files byte-equal',flush=True)

if __name__=='__main__':main()
