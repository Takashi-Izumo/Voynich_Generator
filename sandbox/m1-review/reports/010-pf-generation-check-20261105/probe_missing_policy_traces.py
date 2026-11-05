"""Reviewer negative probe on a separate copy, never on original artifacts."""
from pathlib import Path
import gzip
import json
import os
import shutil
import sys

ROOT = Path(os.environ.get('PF_REVIEW_CHECKOUT', '/workspace/voynich-results/m1-v2-independent-20261105/checkout'))
OUT = Path(os.environ.get('PF_REVIEW_ROOT', '/workspace/voynich-results/pf-generation-independent-20261105'))
sys.path.insert(0, str(ROOT))
from experiments.pf_generation.audit import audit
from experiments.pf_generation.common import file_hash, write_json
from experiments.pf_generation.evaluation import audited

def main():
    generated = OUT / 'trace-omission-copy'
    shutil.copytree(OUT / 'forward', generated)
    manifest_path = generated / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    row = next(r for r in manifest['records'] if r['arm'] == 'PF_GATE_LENGTH' and r['bif'] == 'A:2')
    case = generated / row['path']
    final_path = case / 'PF_GENERATION_FINAL.json'
    final = json.loads(final_path.read_text())
    before = {k: final[k] for k in ['gate_calls', 'gate_changed_calls', 'proposal_calls', 'raw_draws', 'anchor_fallbacks']}
    assert before['gate_calls'] > 0 and before['proposal_calls'] > 0
    originals = {p.name: file_hash(p) for p in case.iterdir() if p.is_file()}
    for name in ('pfgen_gates.jsonl.gz', 'pfgen_proposals.jsonl.gz'):
        (case / name).write_bytes(gzip.compress(b''))
        row['files'][name] = file_hash(case / name)
    final.update({k: 0 for k in before})
    write_json(final_path, final)
    row['files'][final_path.name] = file_hash(final_path)
    write_json(manifest_path, manifest)
    expected_unchanged = set(originals) - {'pfgen_gates.jsonl.gz', 'pfgen_proposals.jsonl.gz', final_path.name}
    assert all(file_hash(case / name) == originals[name] for name in expected_unchanged)
    try:
        result = audit(OUT / 'plan/plan.json', generated, OUT / 'trace-omission-audit')
        audited(OUT / 'plan/plan.json', generated)
        status, reason = 'UNEXPECTED_ACCEPTANCE', result['status']
    except (ValueError, OSError, AssertionError) as exc:
        status, reason = 'REJECTED_AS_EXPECTED', str(exc)
    evidence = dict(probe='erase_all_new_policy_trace_rows_and_zero_counters_with_fresh_checksums',
                    status=status, audit_result=reason, arm=row['arm'], bif=row['bif'],
                    removed_counts=before, unchanged_original_case_files=len(expected_unchanged),
                    generated_tokens_state_rng_candidates_requests_unchanged=True,
                    source_artifacts_unmodified=True)
    write_json(OUT / 'trace-omission-probe.json', evidence)
    print(json.dumps(evidence, indent=2), flush=True)
    # Make the same omission in the reverse-order copy: equality between two
    # equally incomplete traces must not replace validation of their coverage.
    repeated = OUT / 'trace-omission-repeat-copy'
    shutil.copytree(OUT / 'reverse', repeated)
    repeat_manifest = json.loads((repeated / 'manifest.json').read_text())
    repeat_row = next(r for r in repeat_manifest['records'] if r['arm']==row['arm'] and r['bif']==row['bif'])
    for name in ('pfgen_gates.jsonl.gz', 'pfgen_proposals.jsonl.gz', 'PF_GENERATION_FINAL.json'):
        shutil.copyfile(case / name, repeated / repeat_row['path'] / name)
        repeat_row['files'][name] = file_hash(repeated / repeat_row['path'] / name)
    write_json(repeated / 'manifest.json', repeat_manifest)
    try:
        result = audit(OUT / 'plan/plan.json', generated, OUT / 'trace-omission-repeat-audit', repeated)
        audited(OUT / 'plan/plan.json', generated)
        status, reason = 'UNEXPECTED_ACCEPTANCE', result['status']
    except (ValueError, OSError, AssertionError) as exc:
        status, reason = 'REJECTED_AS_EXPECTED', str(exc)
    write_json(OUT / 'trace-omission-both-orders.json', dict(status=status, audit=reason,
               same_omission_in_both_orders=True, original_artifacts_unmodified=True))

if __name__ == '__main__':
    main()
