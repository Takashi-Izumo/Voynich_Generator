"""Opt-in real negative probes; restore every input/artifact and finish with PASS."""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import json
from pathlib import Path
import shutil

from experiments.pf_generation.audit import audit
from experiments.pf_generation.common import PACKAGE, digest, file_hash, require, write_json
from experiments.pf_generation.evaluation import audited
from experiments.pf_generation.plan import load_plan


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--generated', type=Path, required=True)
    ap.add_argument('--repeat', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    plan = audited(a.plan, a.generated)
    results = []

    def rejected(name, fn, expected):
        try:
            fn()
        except (ValueError, OSError, AssertionError) as exc:
            require(expected in str(exc), f'{name} rejected for an unexpected reason: {exc}')
            results.append(dict(probe=name, status='REJECTED_AS_EXPECTED', reason=str(exc)))
        else:
            raise AssertionError('Accepted invalid input: ' + name)

    modified_plan = a.output / 'changed-plan'
    shutil.copytree(a.plan.parent, modified_plan)
    changed = deepcopy(plan)
    next(iter(changed['laws'].values()))['theta'][0] += 1
    write_json(modified_plan / 'plan.json', changed)
    rejected('sealed_law_changed', lambda: load_plan(modified_plan / 'plan.json'), 'Sealed PF plan changed')

    settings = sorted((PACKAGE / 'model/runtime').rglob('FROZEN_FOLD_CONFIGS.json'))[0]
    original_settings = settings.read_bytes()
    try:
        payload = json.loads(original_settings)
        first = next(iter(payload.values()))
        first['beta'] = float(first['beta']) + .125
        write_json(settings, payload)
        rejected('expanded_generation_setting_changed', lambda: load_plan(a.plan), 'Extracted runtime input changed')
    finally:
        settings.write_bytes(original_settings)

    manifest_path = a.generated / 'manifest.json'
    original_manifest = manifest_path.read_bytes()
    manifest = json.loads(original_manifest)
    base = next(r for r in manifest['records'] if r['arm'] == 'BASE')
    tokens = a.generated / base['path'] / 'tokens.csv.gz'
    original_tokens = tokens.read_bytes()
    try:
        rows = gzip.decompress(original_tokens).decode()
        lines = rows.splitlines()
        # Change a visible word without changing the other committed evidence.
        import csv, io
        parsed = list(csv.DictReader(io.StringIO(rows)))
        parsed[0]['surface'] = 'q'
        handle = io.StringIO(newline='')
        writer = csv.DictWriter(handle, fieldnames=list(parsed[0]))
        writer.writeheader(); writer.writerows(parsed)
        tokens.write_bytes(gzip.compress(handle.getvalue().encode()))
        base['files']['tokens.csv.gz'] = file_hash(tokens)
        write_json(manifest_path, manifest)
        rejected('artifact_plus_refreshed_checksum_stale_pass', lambda: audited(a.plan, a.generated), 'mechanical audit seal')
        rejected('changed_visible_commit_reaudit', lambda: audit(a.plan, a.generated, a.output / 'bad-token-audit'),
                 'Visible commit/token mismatch')
        require(not (a.generated / 'AUDIT.json').exists(), 'Failed audit retained an old PASS')
        results.append(dict(probe='failed_reaudit_invalidates_old_pass', status='PASS'))
    finally:
        tokens.write_bytes(original_tokens)
        manifest_path.write_bytes(original_manifest)

    manifest = json.loads(original_manifest)
    reference = next(r for r in manifest['records'] if r['arm'] == 'REFERENCE')
    case = a.generated / reference['path']
    final_path, mechanical_path = case / 'M1_FINAL.json', case / 'MECHANICAL.json'
    originals = {p: p.read_bytes() for p in (final_path, mechanical_path)}
    try:
        final, mechanical = [json.loads(originals[p]) for p in (final_path, mechanical_path)]
        final['final_main_rng_state']['state']['state'] ^= 1
        final['final_main_rng_sha256'] = digest(final['final_main_rng_state'])
        mechanical['rng_end'] = final['final_main_rng_state']
        write_json(final_path, final); write_json(mechanical_path, mechanical)
        for p in originals:
            reference['files'][p.name] = file_hash(p)
        write_json(manifest_path, manifest)
        rejected('self_consistent_reference_rng_change', lambda: audit(a.plan, a.generated, a.output / 'bad-rng-audit'),
                 'BASE final main RNG differs from reference')
    finally:
        for p, data in originals.items():
            p.write_bytes(data)
        manifest_path.write_bytes(original_manifest)

    restored = audit(a.plan, a.generated, a.output / 'restored-positive-audit', a.repeat)
    audited(a.plan, a.generated)
    result = dict(status='PASS', plan_hash=plan['plan_hash'], probes=results,
                  restored_artifacts=True, restored_positive_audit=restored['status'])
    write_json(a.output / 'probes.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
