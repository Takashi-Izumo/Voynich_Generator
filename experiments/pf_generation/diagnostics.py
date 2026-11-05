"""Reproducible descriptive exports, independent of answer keys and judge scores."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from judges.schema import glyphs, WIDTH
from . import ARMS
from .audit import verified_records, read_csv, read_jsonl
from .common import length_band, require, write_json
from .evaluation import audited


def summarize(plan_path, generated, output):
    plan = audited(plan_path, generated)
    records = verified_records(plan, generated)
    scope = json.loads((Path(plan_path).parent / 'scope_ledger.json').read_text())
    observed = {(r['bif'], r['page'], r['locus'], r['segment_id']) for r in scope
                if r['generator_pf'] and r['judge_observed']}
    result = dict(plan_hash=plan['plan_hash'], inference=plan['inference'], promotion=None,
                  scope='generator_pf_and_judge_observed; within_case_then_seed_then_equal_bifolium', arms={})
    for arm in ARMS:
        stats = Counter()
        by_bif = defaultdict(lambda: defaultdict(list))
        for (a, bif, run), path in records.items():
            if a != arm:
                continue
            meta = json.loads((path / 'PF_GENERATION_FINAL.json').read_text())
            stats['cases'] += 1
            for k in ['gate_calls', 'gate_changed_calls', 'proposal_calls', 'raw_draws', 'anchor_fallbacks']:
                stats[k] += meta[k]
            tokens = read_csv(path / 'tokens.csv.gz')
            endpoints = [r for r in tokens if r['draw_segment_end'] == '1'
                         and (bif, r['page'], r['locus'], int(r['segment_id'])) in observed]
            values = defaultdict(list)
            for row in endpoints:
                gs = glyphs(row['surface'])
                stable = glyphs(row['stable_surface'])
                values['visible_length'].append(len(gs))
                values['visible_glyph_width'].append(sum(WIDTH[g] for g in gs))
                values['physical_width'].append(int(row['phys_width']))
                values['visible_7plus'].append(len(gs) >= 7)
                values['stable_7plus'].append(len(stable) >= 7)
                values['visible_le3'].append(len(gs) <= 3)
                values['visible_4to6'].append(4 <= len(gs) <= 6)
                values['m_crossed_7'].append((len(gs) >= 7) != (len(stable) >= 7))
            for k, vv in values.items():
                by_bif[bif][k].append(statistics.mean(vv))
            stats['observed_pf_events'] += len(endpoints)
        macros = {k: statistics.mean(statistics.mean(v[k]) for v in by_bif.values() if k in v)
                  for k in sorted({k for v in by_bif.values() for k in v})}
        result['arms'][arm] = dict(counts=dict(stats), visible_pf_macro=macros,
                                  visible_pf_bifolia=len(by_bif),
                                  raw_fallback_rate=(stats['anchor_fallbacks'] / stats['proposal_calls']
                                                     if stats['proposal_calls'] else None))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'diagnostics.json', result)
    return result
