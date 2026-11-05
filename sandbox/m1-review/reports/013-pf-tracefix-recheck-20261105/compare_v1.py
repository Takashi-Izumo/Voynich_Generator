"""Compare independently generated v2 against the earlier reviewer v1 run."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(os.environ.get('PF_REVIEW_CHECKOUT', '/workspace/voynich-results/m1-v2-independent-20261105/checkout'))
OUT = Path(os.environ.get('PF_REVIEW_ROOT', '/workspace/voynich-results/pf-tracefix-independent-20261105'))
OLD = Path(os.environ.get('PF_REVIEW_V1_ROOT', '/workspace/voynich-results/pf-generation-independent-20261105'))
sys.path.insert(0, str(ROOT))
from experiments.pf_generation.audit import semantic_case, read_jsonl
from experiments.pf_generation.common import digest, file_hash, write_json

def stripped(rows, names):
    return [{k:v for k,v in r.items() if k not in names} for r in rows]

def main():
    new = json.loads((OUT/'forward/manifest.json').read_text())['records']
    old = json.loads((OLD/'forward/manifest.json').read_text())['records']
    lookup = {(r['arm'],r['bif'],r['run']):r for r in old}
    checked = []
    for r in new:
        key = r['arm'],r['bif'],r['run']
        a, b = OUT/'forward'/r['path'], OLD/'forward'/lookup[key]['path']
        assert semantic_case(a)==semantic_case(b), key
        if key[0]!='REFERENCE':
            assert stripped(read_jsonl(a/'m1_candidates.jsonl.gz'), {'pfgen_trace'})==read_jsonl(b/'m1_candidates.jsonl.gz')
            for name,extra in [('pfgen_gates.jsonl.gz', {'trace_schema','query_id'}),
                               ('pfgen_proposals.jsonl.gz', {'trace_schema','call_id','request_id','gate_query_id'})]:
                assert stripped(read_jsonl(a/name),extra)==read_jsonl(b/name), (key,name)
        checked.append(dict(arm=r['arm'],bif=r['bif'],run=r['run'],semantic_state_rng_equal=True))
    artifacts=[]
    for family,names in [('predictions',['predictions.jsonl','channels.jsonl']),
                         ('scores',['measurements.jsonl','summary.json'])]:
        for arm in ['BASE','PF_GATE','PF_GATE_LENGTH']:
            for name in names:
                rel=Path('evaluation')/family/arm/name
                assert file_hash(OUT/rel)==file_hash(OLD/rel), str(rel)
                artifacts.append(dict(path=str(rel),sha256=file_hash(OUT/rel),byte_equal=True))
    write_json(OUT/'v1-comparison.json',dict(status='PASS',cases=checked,
        comparison='Full semantic output including final state and actual main RNG; only request pfgen metadata excluded',
        original_candidate_and_raw_gate_values_equal=True,evaluation_artifacts=artifacts,
        reference_run='Independent reviewer v1 run, not implementation-side outputs'))
    print('PASS: 12 cases, policy decisions, 6 prediction/channel files and 6 score files unchanged',flush=True)

if __name__=='__main__': main()
