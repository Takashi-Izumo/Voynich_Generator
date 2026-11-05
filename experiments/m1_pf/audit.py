from __future__ import annotations

from collections import Counter
import csv
import gzip
import json
from pathlib import Path

from . import ARMS
from .common import digest, file_hash, model_dir, write_json
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
        if not p.name.startswith('m1_'):
            data[p.name] = read_jsonl(p)
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
        records[row['arm'], row['bif'], row['run']] = path
    return records


def generation_binding(plan, generated):
    verified_records(plan, generated)
    root = Path(generated)
    return dict(plan_hash=plan['plan_hash'], manifest_sha256=file_hash(root / 'manifest.json'),
                copied_plan_sha256=file_hash(root / 'plan.json'), status_sha256=file_hash(root / 'STATUS.json'))


def audit_case(path, arm):
    path = Path(path)
    md = json.loads((path / 'MECHANICAL.json').read_text())
    final_rng(path)
    require(md['packing_exact'] is True and md['invalid_rows'] == md['support_violations'] == 0,
            'Packing or support failed')
    require(md['terminal_mismatches'] == md['plant_false_heads'] == 0, 'Terminal/PLANT contract failed')
    tokens = read_csv(path / 'tokens.csv.gz')
    commits = read_jsonl(path / 'surface_commits.jsonl.gz')
    req = read_jsonl(path / 'requests.jsonl.gz')
    require(tokens and len(commits) == len(tokens), 'Empty/incomplete committed tokens')
    committed = [r for r in req if r['committed_to_final_page']]
    require({r['proposal_id'] for r in committed} == {r['proposal_id'] for r in commits}
            and len(committed) == len(commits), 'Request/final token linkage is not one-to-one')
    positions = [(r['page'], r['locus'], str(r['segment_id']), str(r['line_wordnum'])) for r in commits]
    require(positions == [(r['page'], r['locus'], r['segment_id'], r['line_wordnum']) for r in tokens],
            'Surface commits have different token positions')
    require([r['surface'] for r in commits] == [r['surface'] for r in tokens], 'Visible commit/token mismatch')
    previous_segment = None
    for token, commit in zip(tokens, commits):
        key = token['page'], token['locus'], token['segment_id']
        if key != previous_segment:
            require(commit['prev_terminal_before'] is None, 'SPACE connection crossed a segment/PLANT boundary')
            previous_segment = key
        if int(token['segment_id']) > 0:
            require(token['role'] == 'BODY', 'PLANT restart was promoted to HEAD/W2')
    events = read_jsonl(path / 'm1_events.jsonl.gz')
    candidates = read_jsonl(path / 'm1_candidates.jsonl.gz')
    require(len(events) == md['inherited_stats'].get('pf_selection_events', 0), 'PF event count differs')
    bank = read_csv(path / 'pf_branch_tokens.csv.gz')
    rescue_adopted = 0
    for event in events:
        cc = [c for c in candidates if c['event'] == event['event']]
        require([c['candidate'] for c in cc] == list(range(len(cc))), 'Missing/duplicated PF candidates')
        require(len(cc) in (2, 10), 'PF bank size is not 2 or 10')
        require(all(c['input_state_sha256'] == event['input_state_sha256'] and c['parent_isolation'] for c in cc),
                'PF candidate did not start from the same isolated input')
        argmax = max(range(2), key=lambda i: (cc[i]['score'], -i))
        require(event['original_argmax'] == argmax, 'Wrong original argmax/tie break')
        chosen = argmax if arm != 'PF_ANCHOR' else 0
        base = cc[argmax]
        target = base['stable_glyph_length'] <= 5
        require(event['rescue_target'] == target, 'Rescue trigger used visible rather than stable glyph length')
        for c in cc[2:]:
            eligible = (c['stable_glyph_length'] == base['stable_glyph_length'] + 1
                        and c['phys_width'] <= base['phys_width'] + 1
                        and c['stable_family'] == base['stable_family']
                        and c['score'] >= base['score'] - 1.)
            require(c['rescue_eligible'] == eligible, 'Incorrect LEN1 eligibility/family contract')
            if eligible and (chosen == argmax or c['score'] > cc[chosen]['score']):
                chosen = c['candidate']
        require(len(cc) == (10 if arm == 'BASE' and target else 2), 'Rescue branch leaked into another arm')
        require(event['chosen'] == chosen and [c['candidate'] for c in cc if c['selected']] == [chosen],
                'Wrong adopted PF branch')
        continuation = 0 if arm == 'PF_ANCHOR' else argmax
        require(event['continuation_candidate'] == continuation
                and event['rng_continuation_sha256'] == cc[continuation]['rng_exit_sha256'],
                'Wrong future RNG source')
        require(event['output_state_sha256'] == cc[chosen]['output_state_sha256'] and event['sampler_rebound'],
                'Wrong adopted state or sampler binding')
        require(event['rare_budget_after'] == cc[chosen]['rare_budget_after'], 'Wrong rare budget commit')
        rows = [r for r in bank if r['page'] == event['page'] and r['locus'] == event['locus']
                and int(r['segment_id']) == event['segment_id'] and int(r['selected']) == 1]
        final = [r for r in tokens if r['page'] == event['page'] and r['locus'] == event['locus']
                 and int(r['segment_id']) == event['segment_id']]
        require([{k: r[k] for k in final[0]} for r in rows] == final,
                'Only the endpoint, rather than the whole winning segment, was committed')
        rescue_adopted += int(chosen >= 2)
    require(len(candidates) == sum(2 + e['rescue_explored'] for e in events), 'Unlinked counterfactual candidate logs')
    return dict(pf_events=len(events), rescue_explored=sum(e['rescue_explored'] for e in events),
                rescue_adopted=rescue_adopted, candidate1_argmax=sum(e['original_argmax'] == 1 for e in events),
                anchor_overrides=sum(e['original_argmax'] != e['chosen'] for e in events if arm == 'PF_ANCHOR'))


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
        for bif in plan['bifolia']:
            for run in plan['runs']:
                for arm in ARMS:
                    p = records[arm, bif, run]
                    row = dict(arm=arm, bif=bif, run=run, **audit_case(p, arm))
                    if arm == 'BASE' and ('REFERENCE', bif, run) in records:
                        require(final_rng(p) == final_rng(records['REFERENCE', bif, run]),
                                f'BASE final main RNG differs from reference: {bif}/{run}')
                        require(semantic_case(p) == semantic_case(records['REFERENCE', bif, run]),
                                f'BASE differs from the unmodified engine: {bif}/{run}')
                        row['base_reference_exact'] = True
                        row['base_reference_main_rng_exact'] = True
                    if repeated:
                        require(final_rng(p) == final_rng(repeated[arm, bif, run]), 'Repeat final main RNG differs')
                        require(semantic_case(p) == semantic_case(repeated[arm, bif, run]),
                                f'Order/repeat contamination: {arm}/{bif}/{run}')
                        row['repeat_exact'] = True
                        row['repeat_main_rng_exact'] = True
                    results.append(row)
        ledger = json.loads((Path(plan_path).parent / 'scope_ledger.json').read_text())
        scope = Counter((r['generator_pf'], r['structural_end_atom'], r['judge_atom'], r['judge_observed'],
                         r['endpoint_usable'], r['observation_mode'], r['reason']) for r in ledger)
        require(generation_binding(plan, generated) == binding, 'Generation changed while auditing')
        if repeat:
            require(generation_binding(plan, repeat) == repeat_binding, 'Repeat generation changed while auditing')
        report = dict(schema_version=2, status='PASS', plan_hash=plan['plan_hash'], cases=len(results), results=results,
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
