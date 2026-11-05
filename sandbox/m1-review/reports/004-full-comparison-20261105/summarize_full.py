"""Read-only generation checks and descriptive result exports for the frozen study."""
from pathlib import Path
from collections import Counter
import argparse
import csv
import gzip
import hashlib
import json
import sys


def sha_payload(path):
    data = gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['historical', 'results'])
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--historical', type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    plan = json.loads((root / 'plan/plan.json').read_text())
    if args.mode == 'historical':
        if args.historical is None:
            raise ValueError('Historical generation root required')
        rows = json.loads((root / 'generated/manifest.json').read_text())['records']
        baseline = [r for r in rows if r['arm'] == 'BASE']
        assert len(baseline) == 200
        names = ['tokens.csv.gz', 'packing.csv', 'requests.jsonl.gz', 'surface_commits.jsonl.gz',
                 'pf_candidates.csv.gz', 'pf_branch_tokens.csv.gz', 'phw_candidates.csv.gz', 'route_trace.jsonl.gz']
        mismatches = []
        checked = 0
        for r in baseline:
            new = root / 'generated' / r['path']
            old = args.historical / f'run{r["run"]}' / 'HerbalA_v22_3_STAGE3D_R1_CANDIDATE' / r['bif'].replace(':', '_')
            for name in names:
                same = sha_payload(new / name) == sha_payload(old / name)
                checked += 1
                if not same:
                    mismatches.append({'bif': r['bif'], 'run': r['run'], 'file': name})
        out = {'status': 'PASS' if not mismatches else 'FAIL', 'cases': len(baseline),
               'uncompressed_payload_files_compared': checked, 'mismatches': mismatches}
        (root / 'historical-baseline-check.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(out, ensure_ascii=False))
        if mismatches:
            raise ValueError('BASE differs from historical frozen generator')
        return

    arms = plan['arms']
    scores = {a: json.loads((root / f'evaluation/scores/{a}/summary.json').read_text()) for a in arms}
    comparisons = json.loads((root / 'evaluation/M1_COMPARISONS.json').read_text())
    audit = json.loads((root / 'audit/report.json').read_text())
    old = json.loads((root / 'historical-baseline-check.json').read_text())
    assert audit['status'] == old['status'] == 'PASS'
    assert audit['cases'] == 600 and audit['base_reference_checked'] and audit['base_reference_main_rng_checked']
    assert comparisons['primary'] == 'J24.CAL'
    outputs = root / 'summary'
    outputs.mkdir(exist_ok=False)
    table = []
    for view in sorted(set.intersection(*(set(s['views']) for s in scores.values()))):
        for arm in arms:
            s = scores[arm]['views'][view]
            table.append({'view': view, 'arm': arm, 'macro_expected_game_accuracy': s['macro_expected_game_accuracy'],
                          'distance_to_50': None if s['macro_expected_game_accuracy'] is None else abs(s['macro_expected_game_accuracy'] - .5),
                          'comparable_bifolia': s['comparable_bifolia'], 'decided': s['decided'], 'ties': s['ties'], 'NA': s['NA'],
                          'ci95_low': None if s['expected_game_cluster_bootstrap_95'] is None else s['expected_game_cluster_bootstrap_95'][0],
                          'ci95_high': None if s['expected_game_cluster_bootstrap_95'] is None else s['expected_game_cluster_bootstrap_95'][1]})
    with (outputs / 'all-views.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(table[0])); w.writeheader(); w.writerows(table)
    chosen = ['J24.CAL', 'ATOM.PARA_END.CAL', 'J24.PROTO', 'J07.CAL', 'J19.CAL', 'J20.CAL', 'J25.CAL']
    chosen += ['ATOM.' + a + '.CAL' for a in ['PHW', 'FIRST_INTERIOR', 'HEAD', 'W2', 'BODY', 'PLANT_END', 'LINE_END']]
    selected = {view: {arm: scores[arm]['views'][view] for arm in arms} for view in chosen}
    totals = {a: Counter() for a in arms + ['REFERENCE']}
    for row in json.loads((root / 'generated/manifest.json').read_text())['records']:
        p = root / 'generated' / row['path']
        md = json.loads((p / 'MECHANICAL.json').read_text())
        t = totals[row['arm']]
        t['cases'] += 1
        t['tokens'] += md.get('tokens', md.get('generated_tokens', 0))
        t['packing_failures'] += not md['packing_exact']
        for k in ['invalid_rows', 'support_violations', 'terminal_mismatches', 'plant_false_heads']:
            t[k] += md[k]
        for k in ['pf_selection_events', 'pf_rescue_candidates', 'pf_length_rescue_selected']:
            t[k] += md['inherited_stats'].get(k, 0)
        # The inherited counter refers to the original argmax even in PF_ANCHOR.
        t['original_argmax_candidate1_legacy_stat'] += md['inherited_stats'].get('pf_selected_candidate1', 0)
        events_path = p / 'm1_events.jsonl.gz'
        if events_path.exists():
            with gzip.open(events_path, 'rt') as f:
                for line in f:
                    e = json.loads(line)
                    t['actual_candidate0_adoptions'] += e['chosen'] == 0
                    t['actual_candidate1_adoptions'] += e['chosen'] == 1
                    t['actual_rescue_adoptions'] += e['chosen'] >= 2
    result = {'status': 'COMPLETED_DESCRIPTIVE_COMPARISON', 'plan_hash': plan['plan_hash'],
              'total_generated_pages': 800, 'comparison_trials_per_arm': 200,
              'bifolia': 20, 'runs_per_bifolium': 10, 'primary': 'J24.CAL', 'local_primary': 'ATOM.PARA_END.CAL',
              'bootstrap': 10000, 'selected_views': selected,
              'major_comparisons': {name: {v: vals[v] for v in ['J24.CAL', 'ATOM.PARA_END.CAL']}
                                    for name, vals in comparisons['comparisons'].items()},
              'mechanism': {a: dict(t) for a, t in totals.items()}, 'historical_baseline': old,
              'capability_controls': 'NOT_COMPLETED_FOR_PARAGRAPH_FINAL',
              'promotion': None, 'inference': 'descriptive_development_reused_bifolia_frozen_models'}
    (outputs / 'RESULTS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'rates': {v: {a: scores[a]['views'][v]['macro_expected_game_accuracy'] for a in arms}
                               for v in ['J24.CAL', 'ATOM.PARA_END.CAL', 'J24.PROTO']},
                      'major_comparisons': result['major_comparisons'], 'mechanism': result['mechanism']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
