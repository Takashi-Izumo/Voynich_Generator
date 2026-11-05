from __future__ import annotations

from collections import Counter
import csv
import gzip
import json
from pathlib import Path

from . import ARMS
from .common import digest, file_hash, model_dir, write_json
from .policy_audit import audit_case, policy_digest
from .plan import load_plan


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def read_csv(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def read_jsonl(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return [json.loads(s) for s in f if s.strip()]


def semantic_case(path):
    path = Path(path)
    md = json.loads((path / 'MECHANICAL.json').read_text())
    md.pop('elapsed_seconds', None)
    data = {'mechanical': md}
    for p in path.glob('*.csv*'):
        data[p.name] = read_csv(p)
    for p in path.glob('*.jsonl.gz'):
        if not p.name.startswith(('m1_', 'pfgen_')):
            data[p.name] = read_jsonl(p)
            if p.name == 'requests.jsonl.gz':
                data[p.name] = [{k: v for k, v in row.items() if k != 'pfgen'} for row in data[p.name]]
    data['full_final_state_sha256'] = json.loads((path / 'M1_FINAL.json').read_text())['final_state_sha256']
    data['final_main_rng_state'] = final_rng(path)
    return data


def final_rng(path):
    path = Path(path)
    final = json.loads((path / 'M1_FINAL.json').read_text())
    state = final['final_main_rng_state']
    require(digest(state) == final['final_main_rng_sha256'], 'Final main RNG hash mismatch')
    mechanical = json.loads((path / 'MECHANICAL.json').read_text())
    require(state == mechanical['rng_end'], 'Final main RNG differs from generator audit')
    return state


def verified_records(plan, generated):
    generated = Path(generated)
    status = json.loads((generated / 'STATUS.json').read_text())
    require(status['status'] in ('GENERATED_NOT_AUDITED', 'AUDITED'), 'Generation failed or is incomplete')
    manifest = json.loads((generated / 'manifest.json').read_text())
    require(manifest['plan_hash'] == plan['plan_hash'] == status['plan_hash'], 'Generation plan mismatch')
    require(json.loads((generated / 'plan.json').read_text()) == plan, 'Copied generation plan differs')
    rows = manifest['records']
    keys = [(r['arm'], r['bif'], r['run']) for r in rows]
    expected = {(a, b, s) for a in ARMS for b in plan['bifolia'] for s in plan['runs']}
    require(len(keys) == len(set(keys)), 'Duplicate generated cases')
    require(set(keys) >= expected and set(keys) - expected <= {('REFERENCE', b, s) for b in plan['bifolia'] for s in plan['runs']},
            'Missing or unexpected arm/seed/bifolium')
    refs = {k for k in keys if k[0] == 'REFERENCE'}
    require(not refs or refs == {('REFERENCE', b, s) for b in plan['bifolia'] for s in plan['runs']},
            'Partial reference generation')
    records = {}
    for row in rows:
        path = (generated / row['path']).resolve()
        require(path.is_relative_to(generated.resolve()), 'Generation path escapes its output root')
        actual = {p.name for p in path.iterdir() if p.is_file()}
        require(actual == set(row['files']), 'Generation files added or removed')
        for name, h in row['files'].items():
            require(Path(name).name == name and file_hash(path / name) == h, 'Generated artifact changed: ' + name)
        final = json.loads((path / 'M1_FINAL.json').read_text())
        require((final['arm'], final['bif'], final['run']) == (row['arm'], row['bif'], row['run']),
                'Final metadata case differs from manifest')
        records[row['arm'], row['bif'], row['run']] = path
    return records


def generation_binding(plan, generated):
    verified_records(plan, generated)
    root = Path(generated)
    return dict(plan_hash=plan['plan_hash'], manifest_sha256=file_hash(root / 'manifest.json'),
                copied_plan_sha256=file_hash(root / 'plan.json'), status_sha256=file_hash(root / 'STATUS.json'))


def audit(plan_path, generated, output, repeat=None):
    plan = load_plan(plan_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    # Once a new audit starts, a previous seal cannot remain the active PASS.
    (Path(generated) / 'AUDIT.json').unlink(missing_ok=True)
    results = []
    try:
        binding = generation_binding(plan, generated)
        repeat_binding = generation_binding(plan, repeat) if repeat else None
        records = verified_records(plan, generated)
        repeated = verified_records(plan, repeat) if repeat else None
        require(all(('REFERENCE', b, s) in records for b in plan['bifolia'] for s in plan['runs']),
                'All BASE reference cases are required')
        for bif in plan['bifolia']:
            for run in plan['runs']:
                for arm in ARMS:
                    p = records[arm, bif, run]
                    row = dict(arm=arm, bif=bif, run=run, **audit_case(p, arm, plan))
                    if arm == 'BASE' and ('REFERENCE', bif, run) in records:
                        require(final_rng(p) == final_rng(records['REFERENCE', bif, run]),
                                f'BASE final main RNG differs from reference: {bif}/{run}')
                        require(semantic_case(p) == semantic_case(records['REFERENCE', bif, run]),
                                f'BASE differs from the unmodified engine: {bif}/{run}')
                        row['base_reference_exact'] = True
                        row['base_reference_main_rng_exact'] = True
                    if plan['identity_override']:
                        require(semantic_case(p) == semantic_case(records['REFERENCE', bif, run]),
                                'Identity policy differs from original reference')
                        row['identity_reference_exact'] = True
                    if repeated:
                        audit_case(repeated[arm, bif, run], arm, plan)
                        require(final_rng(p) == final_rng(repeated[arm, bif, run]), 'Repeat final main RNG differs')
                        require(semantic_case(p) == semantic_case(repeated[arm, bif, run]),
                                f'Order/repeat contamination: {arm}/{bif}/{run}')
                        require(policy_digest(p) == policy_digest(repeated[arm, bif, run]), 'Repeat PF policy logs differ')
                        row['repeat_exact'] = True
                        row['repeat_main_rng_exact'] = True
                        row['repeat_policy_coverage_checked'] = True
                    results.append(row)
        ledger = json.loads((Path(plan_path).parent / 'scope_ledger.json').read_text())
        scope = Counter((r['generator_pf'], r['structural_end_atom'], r['judge_atom'], r['judge_observed'],
                         r['endpoint_usable'], r['observation_mode'], r['reason']) for r in ledger)
        require(generation_binding(plan, generated) == binding, 'Generation changed while auditing')
        if repeat:
            require(generation_binding(plan, repeat) == repeat_binding, 'Repeat generation changed while auditing')
        report = dict(schema_version=2, trace_coverage_checked=True, status='PASS', plan_hash=plan['plan_hash'], cases=len(results), results=results,
                      generation_binding=binding, repeat_binding=repeat_binding,
                      repeat_root=str(Path(repeat).resolve()) if repeat else None,
                      base_reference_checked=all(r.get('base_reference_exact', False) for r in results if r['arm'] == 'BASE'),
                      base_reference_main_rng_checked=all(r.get('base_reference_main_rng_exact', False) for r in results if r['arm'] == 'BASE'),
                      repeat_checked=repeat is not None, statistical_evaluation='NOT_RUN', promotion=None,
                      scope_counts=[dict(generator_pf=k[0], structural_end_atom=k[1], judge_atom=k[2],
                                         judge_observed=k[3], endpoint_usable=k[4], observation_mode=k[5], reason=k[6], segments=v)
                                    for k, v in sorted(scope.items(), key=lambda item: json.dumps(item[0]))])
        write_json(output / 'report.json', report)
    except Exception as exc:
        write_json(output / 'report.json', {'status': 'FAIL', 'error': str(exc), 'plan_hash': plan['plan_hash']})
        raise
    write_json(Path(generated) / 'AUDIT.json', {'schema_version': 2, 'report_sha256': file_hash(output / 'report.json'),
                                              'report': str((output / 'report.json').resolve()),
                                              'plan_hash': plan['plan_hash'], 'generation_binding': binding})
    return report
