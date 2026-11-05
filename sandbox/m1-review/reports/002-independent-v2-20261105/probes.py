"""Independent v2 negative probes; candidate implementation stays unchanged."""
from pathlib import Path
from copy import deepcopy
import argparse
import csv
import gzip
import json
import re
import shutil
import sys

ROOT = None


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(value, ensure_ascii=False))


def expect_rejection(call):
    try:
        call()
    except (ValueError, AssertionError, KeyError, OSError) as exc:
        return {'rejected': True, 'error': str(exc)}
    raise AssertionError('Negative input unexpectedly accepted')


def inputs():
    from experiments.m1_pf.common import PACKAGE, file_hash
    from experiments.m1_pf.plan import load_plan
    plan = ROOT / 'plan/plan.json'
    runtime = PACKAGE / 'model/runtime'
    settings = next(runtime.rglob('FROZEN_FOLD_CONFIGS.json'))
    selector = next(p for p in runtime.rglob('*_PF.json') if 'selectors' in p.parts)
    core = next(p for p in runtime.rglob('*.pkl.gz') if 'core_cache' in p.parts)
    out = {}
    load_plan(plan)
    for label, path, action in [('same_size_configuration_change', settings, 'change'),
                                ('selector_deletion', selector, 'delete'),
                                ('core_change', core, 'change')]:
        original = path.read_bytes()
        before = file_hash(path)
        try:
            if action == 'delete':
                path.unlink()
            elif label.startswith('same_size'):
                updated, n = re.subn(rb'("beta"\s*:\s*)([0-9])',
                                     lambda m: m[1] + bytes([48 + (m[2][0] - 48 + 1) % 10]), original, count=1)
                assert n == 1 and len(updated) == len(original)
                path.write_bytes(updated)
            else:
                path.write_bytes(bytes([original[0] ^ 1]) + original[1:])
            out[label] = expect_rejection(lambda: load_plan(plan))
            if action == 'delete':
                assert not path.exists(), 'Deleted input was silently restored'
        finally:
            path.write_bytes(original)
            assert file_hash(path) == before
    extra = runtime / 'm1-extra-selector-probe.json'
    assert not extra.exists()
    try:
        extra.write_text('{}')
        out['additional_selector'] = expect_rejection(lambda: load_plan(plan))
    finally:
        extra.unlink()
    load_plan(plan)
    out['all_inputs_restored_and_plan_valid'] = True
    save('input-probes.json', out)


def scope():
    from experiments.m1_pf.common import PACKAGE
    from judges.v03.adapter import source_documents
    from judges.v03.observations import word_events
    C, corpus, docs, page_loci, provenance = source_documents(PACKAGE)
    ledger = json.loads((ROOT / 'plan/scope_ledger.json').read_text())
    actual = {}
    for page in {r['page'] for r in ledger}:
        for e in word_events(docs[page]):
            if e.boundary in ('L', 'P'):
                actual[page, page_loci[page][e.line], e.segment] = e.atom
    wrong = [r for r in ledger if r['judge_atom'] != actual.get((r['page'], r['locus'], r['segment_id']))
             or r['judge_observed'] != ((r['page'], r['locus'], r['segment_id']) in actual)]
    ends = [r for r in ledger if r['observation_mode'] == 'END_ONLY']
    assert not wrong and len(ends) == 19
    assert all(not r['judge_observed'] and r['judge_atom'] is None and r['endpoint_usable'] for r in ends)
    save('scope-probes.json', {'segments': len(ledger), 'mismatches': len(wrong),
                              'end_only': len(ends), 'end_only_atom_observed': 0,
                              'pf_mechanism_segments': sum(r['generator_pf'] for r in ledger),
                              'pf_atom_observed': sum(r['generator_pf'] and r['judge_observed'] for r in ledger)})


def artifacts():
    from experiments.m1_pf.audit import audit, final_rng, generation_binding
    from experiments.m1_pf.common import digest, file_hash, write_json
    from experiments.m1_pf.evaluation import audited
    from experiments.m1_pf.plan import load_plan
    plan_path = ROOT / 'plan/plan.json'
    plan = load_plan(plan_path)
    normal = ROOT / 'forward'
    audited(plan_path, normal)
    fixtures = ROOT / 'negative-fixtures'
    fixtures.mkdir(exist_ok=False)
    out = {}

    def clone(label, src=normal):
        dest = fixtures / label
        shutil.copytree(src, dest)
        return dest

    def manifest_case(root, arm='BASE', bif='A:2'):
        m = json.loads((root / 'manifest.json').read_text())
        r = next(r for r in m['records'] if r['arm'] == arm and r['bif'] == bif)
        return m, r, root / r['path']

    def refresh(root, m, row, files):
        path = root / row['path']
        for name in files:
            row['files'][name] = file_hash(path / name)
        write_json(root / 'manifest.json', m)

    def change_token(root):
        m, row, case = manifest_case(root)
        p = case / 'tokens.csv.gz'
        with gzip.open(p, 'rt', newline='') as f:
            reader = csv.DictReader(f)
            fields, rows = reader.fieldnames, list(reader)
        rows[0]['surface'] += 'q'
        with gzip.open(p, 'wt', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        refresh(root, m, row, ['tokens.csv.gz'])

    stale = clone('stale')
    change_token(stale)
    generation_binding(plan, stale)  # Current checksums are valid.
    out['old_pass_after_token_and_checksum_update'] = expect_rejection(lambda: audited(plan_path, stale))
    seal = json.loads((stale / 'AUDIT.json').read_text())
    seal['generation_binding'] = generation_binding(plan, stale)
    write_json(stale / 'AUDIT.json', seal)
    out['refreshing_only_seal_cannot_rebind_old_report'] = expect_rejection(lambda: audited(plan_path, stale))
    out['failed_reaudit'] = expect_rejection(lambda: audit(plan_path, stale, fixtures / 'failed-reaudit'))
    assert not (stale / 'AUDIT.json').exists()
    out['failed_reaudit_old_seal_removed'] = True

    forward = clone('repeat-forward')
    reverse = clone('repeat-reverse', ROOT / 'reverse')
    audit(plan_path, forward, fixtures / 'repeat-audit', reverse)
    audited(plan_path, forward)
    change_token(reverse)
    generation_binding(plan, reverse)
    out['updated_repeat_rejected'] = expect_rejection(lambda: audited(plan_path, forward))

    rngroot = clone('rng-reference')
    m, row, case = manifest_case(rngroot, 'REFERENCE')
    f = json.loads((case / 'M1_FINAL.json').read_text())
    old_state_hash = f['final_state_sha256']
    rng = deepcopy(f['final_main_rng_state'])
    rng['state']['state'] += 1
    f['final_main_rng_state'], f['final_main_rng_sha256'] = rng, digest(rng)
    write_json(case / 'M1_FINAL.json', f)
    mech = json.loads((case / 'MECHANICAL.json').read_text())
    mech['rng_end'] = rng
    write_json(case / 'MECHANICAL.json', mech)
    refresh(rngroot, m, row, ['M1_FINAL.json', 'MECHANICAL.json'])
    assert f['final_state_sha256'] == old_state_hash
    final_rng(case)  # Internally consistent RNG metadata, but differs from BASE.
    out['rng_only_change_same_semantic_state'] = expect_rejection(lambda: audit(plan_path, rngroot, fixtures / 'rng-audit'))
    assert 'BASE final main RNG differs' in out['rng_only_change_same_semantic_state']['error']

    mismatch = clone('rng-mismatch')
    m, row, case = manifest_case(mismatch)
    mech = json.loads((case / 'MECHANICAL.json').read_text())
    mech['rng_end']['state']['state'] += 1
    write_json(case / 'MECHANICAL.json', mech)
    refresh(mismatch, m, row, ['MECHANICAL.json'])
    out['final_rng_mechanical_mismatch'] = expect_rejection(lambda: final_rng(case))
    save('artifact-probes.json', out)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['inputs', 'scope', 'artifacts'])
    p.add_argument('--root', type=Path, required=True)
    args = p.parse_args()
    ROOT = args.root.resolve()
    sys.path.insert(0, str(ROOT / 'checkout'))
    {'inputs': inputs, 'scope': scope, 'artifacts': artifacts}[args.mode]()
