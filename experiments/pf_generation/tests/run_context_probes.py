"""R2 attribution probes; only raw context, receipt digest and checksums change."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil

from experiments.pf_generation.audit import audit, verified_records
from experiments.pf_generation.common import digest, file_hash, require, write_json
from experiments.pf_generation.evaluation import audited
from experiments.pf_generation.tests.run_trace_probes import rows, write_rows


def corrupt_context(generated, mode):
    manifest_path = generated / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    entry = next(r for r in manifest['records'] if r['arm'] == 'PF_GATE_LENGTH' and r['bif'] == 'A:2')
    case = generated / entry['path']
    original_hashes = {p.name: file_hash(p) for p in case.iterdir() if p.is_file()}
    proposals, requests, candidates = [rows(case / name) for name in
        ['pfgen_proposals.jsonl.gz', 'requests.jsonl.gz', 'm1_candidates.jsonl.gz']]
    row = proposals[0]
    original = deepcopy(row)
    if mode == 'candidate':
        other = next(c for c in candidates if c['event'] == row['event'] and c['candidate'] != row['candidate'])
        row['candidate'] = other['candidate']
    elif mode == 'whole_existing':
        other = next(c for c in candidates if c['event'] != row['event'])
        row.update({k: other[k] for k in ['page', 'locus', 'segment_id', 'event', 'candidate']})
    elif mode == 'page':
        row['page'] = 'wrong-page'
    elif mode in ('locus', 'segment_id', 'event'):
        different = next((c[mode] for c in candidates if c[mode] != row[mode]), None)
        row[mode] = different if different is not None else row[mode] + 1 if isinstance(row[mode], int) else 'wrong-locus'
    elif mode == 'candidate_float':
        row['candidate'] = float(row['candidate'])
    elif mode == 'candidate_bool':
        row['candidate'] = bool(row['candidate'])
    elif mode == 'candidate_string':
        row['candidate'] = str(row['candidate'])
    else:
        raise ValueError(mode)
    context = {'page', 'locus', 'segment_id', 'event', 'candidate'}
    require({k: v for k, v in row.items() if k not in context} ==
            {k: v for k, v in original.items() if k not in context}, 'Policy decisions changed in context probe')
    request = requests[row['request_id']]
    receipt = next(r for r in request['pfgen']['raw_calls'] if r['call_id'] == row['call_id'])
    receipt['row_sha256'] = digest(row)
    for name, data in [('pfgen_proposals.jsonl.gz', proposals), ('requests.jsonl.gz', requests)]:
        write_rows(case / name, data)
        entry['files'][name] = file_hash(case / name)
    write_json(manifest_path, manifest)
    require(all(file_hash(case / name) == expected for name, expected in original_hashes.items()
                if name not in ('pfgen_proposals.jsonl.gz', 'requests.jsonl.gz')), 'Core evidence changed')
    return dict(raw_call_id=row['call_id'], request_id=row['request_id'],
                before={k: original[k] for k in context}, after={k: row[k] for k in context},
                unchanged_case_files=len(original_hashes) - 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--generated', type=Path, required=True)
    ap.add_argument('--repeat', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    plan = audited(a.plan, a.generated)
    a.output.mkdir(parents=True, exist_ok=False)
    tests = [(name, 'single') for name in ['candidate', 'page', 'locus', 'segment_id', 'event',
                                          'whole_existing', 'candidate_float', 'candidate_bool', 'candidate_string']]
    if a.repeat is not None:
        tests += [('candidate', 'both'), ('candidate', 'repeat_only')]
    results = []
    source_hashes = {p: file_hash(p) for source in [a.generated, a.repeat] if source is not None
                     for p in [source / 'manifest.json', source / 'AUDIT.json'] if p.exists()}
    for mode, variant in tests:
        root = a.output / (mode + '-' + variant)
        generated = root / 'forward'
        shutil.copytree(a.generated, generated)
        repeat = root / 'reverse' if variant != 'single' else None
        if repeat is not None:
            shutil.copytree(a.repeat, repeat)
            evidence = corrupt_context(repeat, mode)
            verified_records(plan, repeat)
        if variant != 'repeat_only':
            evidence = corrupt_context(generated, mode)
        verified_records(plan, generated)
        try:
            audit(a.plan, generated, root / 'audit', repeat)
        except (ValueError, OSError, AssertionError) as exc:
            reason = str(exc)
            require('candidate context' in reason, 'Context probe failed for an unrelated reason: ' + reason)
            require(not (generated / 'AUDIT.json').exists(), 'Stale seal survived rejected context')
            try:
                audited(a.plan, generated)
            except (ValueError, OSError, AssertionError):
                pass
            else:
                raise AssertionError('Rejected context accepted by evaluation precheck')
            results.append(dict(probe=mode + '-' + variant, status='REJECTED_AS_EXPECTED', reason=reason,
                receipt_and_checksums_refreshed=True, checksum_validation_passed=True,
                stale_seal_invalidated=True, evaluation_precheck_rejected=True, **evidence))
        else:
            raise AssertionError('Misattributed raw context accepted')
        print(mode, variant, 'REJECTED', flush=True)
    require(all(file_hash(p) == h for p, h in source_hashes.items()), 'Original artifacts changed')
    audited(a.plan, a.generated)
    write_json(a.output / 'context-probes.json', dict(status='PASS',plan_hash=plan['plan_hash'],
        context_probe_count=len(results),original_artifacts_unmodified=True,probes=results))


if __name__ == '__main__':
    main()
