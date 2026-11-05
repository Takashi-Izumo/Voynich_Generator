"""R1: corrupt separate copies, refresh checksums, require fresh audit rejection."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import shutil

from experiments.pf_generation.audit import audit, verified_records
from experiments.pf_generation.common import file_hash, require, write_json
from experiments.pf_generation.evaluation import audited


def rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


def write_rows(path, data):
    with gzip.open(path, 'wt') as handle:
        for row in data:
            handle.write(json.dumps(row, sort_keys=True) + '\n')


def corrupt(generated, mode, arm='PF_GATE_LENGTH'):
    manifest_path = generated / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    record = next(r for r in manifest['records'] if r['arm'] == arm and r['bif'] == 'A:2')
    case = generated / record['path']
    gates = rows(case / 'pfgen_gates.jsonl.gz')
    proposals = rows(case / 'pfgen_proposals.jsonl.gz')
    requests = rows(case / 'requests.jsonl.gz')
    candidates = rows(case / 'm1_candidates.jsonl.gz')
    if mode == 'erase_all':
        gates, proposals = [], []
    elif mode == 'erase_gates':
        gates = []
    elif mode == 'partial_gate':
        gates.pop(len(gates) // 2)
    elif mode == 'partial_raw':
        proposals.pop(len(proposals) // 2)
    elif mode == 'duplicate_gate':
        gates.insert(1, dict(gates[0]))
    elif mode == 'duplicate_raw':
        proposals.insert(1, dict(proposals[0]))
    elif mode == 'reorder_raw':
        proposals[0], proposals[1] = proposals[1], proposals[0]
    elif mode == 'partial_inner_draw':
        row = next(r for r in proposals if not r['fallback'] and len(r['draws']) > 1)
        row['draws'].pop(0)
        row['chosen_draw'] -= 1
    elif mode == 'erase_request_links':
        for request in requests:
            request.pop('pfgen', None)
    elif mode == 'erase_raw_links_and_windows':
        proposals = []
        for candidate in candidates:
            candidate['pfgen_trace']['raw_start'] = candidate['pfgen_trace']['raw_stop'] = 0
        for request in requests:
            if 'pfgen' in request:
                request['pfgen']['raw_calls'] = []
    elif mode == 'wrong_request':
        proposals[0]['request_id'] += 1
    else:
        raise ValueError(mode)
    final_path = case / 'PF_GENERATION_FINAL.json'
    final = json.loads(final_path.read_text())
    final.update(gate_calls=len(gates), proposal_calls=len(proposals),
                 gate_changed_calls=sum(g['parent_probability'] != g['adapted_probability'] for g in gates),
                 raw_draws=sum(len(p['draws']) for p in proposals),
                 anchor_fallbacks=sum(p['fallback'] for p in proposals))
    write_json(final_path, final)
    for name, data in [('pfgen_gates.jsonl.gz', gates), ('pfgen_proposals.jsonl.gz', proposals),
                       ('requests.jsonl.gz', requests), ('m1_candidates.jsonl.gz', candidates)]:
        write_rows(case / name, data)
        record['files'][name] = file_hash(case / name)
    record['files'][final_path.name] = file_hash(final_path)
    write_json(manifest_path, manifest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--generated', type=Path, required=True)
    ap.add_argument('--repeat', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    plan = audited(a.plan, a.generated)
    a.output.mkdir(parents=True, exist_ok=False)
    originals = {p: file_hash(p) for root in [a.generated, a.repeat]
                 for p in [root / 'manifest.json', root / 'AUDIT.json'] if p.exists()}
    tests = [(mode, 'PF_GATE_LENGTH', False, False) for mode in
             ['erase_all', 'partial_gate', 'partial_raw', 'duplicate_gate', 'duplicate_raw', 'reorder_raw',
              'partial_inner_draw', 'erase_request_links', 'erase_raw_links_and_windows', 'wrong_request']]
    tests += [('erase_gates', 'PF_GATE', False, False), ('erase_all', 'PF_GATE_LENGTH', True, False),
              ('erase_all', 'PF_GATE_LENGTH', True, True)]
    results = []
    for i, (mode, arm, with_repeat, repeat_only) in enumerate(tests):
        label = f'{i:02d}-{arm}-{mode}' + ('-both-orders' if with_repeat and not repeat_only else '-repeat-only' if repeat_only else '')
        root = a.output / label
        generated = root / 'forward'
        shutil.copytree(a.generated, generated)
        repeat = root / 'reverse' if with_repeat else None
        if repeat is not None:
            shutil.copytree(a.repeat, repeat)
            corrupt(repeat, mode, arm)
        if not repeat_only:
            corrupt(generated, mode, arm)
        verified_records(plan, generated)
        if repeat is not None:
            verified_records(plan, repeat)
        try:
            audit(a.plan, generated, root / 'audit', repeat)
        except (ValueError, OSError, AssertionError) as exc:
            reason = str(exc)
            require(not (generated / 'AUDIT.json').exists(), 'Failed audit retained stale seal')
            try:
                audited(a.plan, generated)
            except (ValueError, OSError, AssertionError):
                precheck_rejected = True
            else:
                raise AssertionError('Evaluation accepted a failed fresh audit')
            results.append(dict(probe=label, status='REJECTED_AS_EXPECTED', reason=reason,
                                checksums_refreshed_and_verified=True, old_seal_invalidated=True,
                                evaluation_precheck_rejected=precheck_rejected))
        else:
            raise AssertionError('Missing/duplicate policy evidence accepted: ' + label)
        print(label, 'REJECTED', flush=True)
    require(all(file_hash(p) == expected for p, expected in originals.items()), 'Original artifacts changed')
    audited(a.plan, a.generated)
    result = dict(status='PASS', plan_hash=plan['plan_hash'], trace_probe_count=len(results),
                  original_artifacts_unmodified=True, original_positive_precheck=True, probes=results)
    write_json(a.output / 'trace-probes.json', result)


if __name__ == '__main__':
    main()
