"""Recompute gate/proposal decisions independently of the generation hooks."""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

from judges.schema import WIDTH, glyphs
from experiments.m1_pf.audit import audit_case as audit_parent_case
from . import POLICY
from .common import band, length_band, digest, require
from .laws import Law


def read_rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


def policy_digest(path):
    path = Path(path)
    return digest([read_rows(path / 'pfgen_gates.jsonl.gz'), read_rows(path / 'pfgen_proposals.jsonl.gz'),
                   json.loads((path / 'PF_GENERATION_FINAL.json').read_text())])


def sigmoid(value):
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def logit(value):
    value = max(1e-8, min(1.0 - 1e-8, value))
    return math.log(value / (1.0 - value))


def close(left, right):
    require(math.isclose(left, right, rel_tol=0, abs_tol=1e-12), 'PF probability/weight mismatch')


def audit_case(path, arm, plan):
    path = Path(path)
    # All study-one arms retain the BASE PF argmax and LEN1 mechanism.
    result = audit_parent_case(path, 'BASE')
    final = json.loads((path / 'PF_GENERATION_FINAL.json').read_text())
    main = json.loads((path / 'M1_FINAL.json').read_text())
    fold = plan['folds'][main['bif']]
    payload = plan['laws'][str(fold)]
    law = Law.load(payload)
    require(final['plan_hash'] == plan['plan_hash'] and final['fold'] == fold
            and final['arm'] == main['arm'] == arm and final['bif'] == main['bif']
            and final['run'] == main['run'] and final['law_sha256'] == digest(payload)
            and final['effective_law_sha256'] == digest(law)
            and final['source_sha256'] == digest(plan['implementation_sources'])
            and final['identity_override'] == plan['identity_override'], 'Wrong PF final provenance')
    gates = read_rows(path / 'pfgen_gates.jsonl.gz')
    proposals = read_rows(path / 'pfgen_proposals.jsonl.gz')
    candidates = read_rows(path / 'm1_candidates.jsonl.gz')
    keys = {(c['page'], c['locus'], c['segment_id'], c['event'], c['candidate']) for c in candidates}
    key = lambda row: (row['page'], row['locus'], row['segment_id'], row['event'], row['candidate'])
    require(arm != 'BASE' or not gates, 'Gate adapter used in BASE')
    require(arm == 'PF_GATE_LENGTH' or not proposals, 'Length sampler used in wrong arm')
    for row in gates:
        require(row['generator_pf'] and key(row) in keys, 'Gate escaped PF candidate scope')
        require(row['band'] == band(row['rstart']) and row['offset'] == law.theta[row['band']], 'Wrong gate bin')
        before = row['parent_probability']
        after = before if row['offset'] == 0 else sigmoid(logit(before) + row['offset'])
        close(after, row['adapted_probability'])
        close(sigmoid(logit(after) + math.log(0.8)) if row['split_end'] else after, row['engine_probability'])
    for row in proposals:
        require(row['generator_pf'] and key(row) in keys and row['paragraph_line'] >= 2
                and row['row_phase'] == 'FINAL' and row['end'] and row['line_end_boundary']
                and row['state_unchanged'] and row['law_sha256'] == digest(law), 'Proposal escaped PF END scope')
        require(row['identity'] == law.identity, 'Wrong raw identity mode')
        draws = row['draws']
        require(1 <= len(draws) <= POLICY['max_raw_draws'], 'Raw draw ceiling violated')
        for index, draw in enumerate(draws):
            names = glyphs(draw['stable_surface']) if draw['stable_surface'] else ()
            require(len(names) == draw['length'] == len(draw['glyphs']), 'Raw glyph length mismatch')
            require(sum(WIDTH[g] for g in names) == draw['width'], 'Raw physical width mismatch')
            gain = law.gains[length_band(len(names))][band(draw['width'])] if names else None
            require(draw['gain'] == gain, 'Incorrect raw proposal gain')
            if not names or law.identity:
                require(draw['uniform'] is None and draw['accepted'] and len(draws) == 1, 'Identity/empty raw RNG changed')
            else:
                require(0 <= draw['uniform'] < 1, 'Invalid raw acceptance uniform')
                require(draw['accepted'] == (draw['uniform'] < gain / law.normalizer), 'Raw acceptance mismatch')
            require(index == len(draws) - 1 or not draw['accepted'], 'Continued after an accepted raw word')
        if row['fallback']:
            require(len(draws) == POLICY['max_raw_draws'] and not any(d['accepted'] for d in draws)
                    and row['chosen_draw'] == 0, 'Wrong raw anchor fallback')
        else:
            require(draws[-1]['accepted'] and row['chosen_draw'] == len(draws) - 1, 'Wrong accepted raw draw')
        require(row['selected_glyphs'] == draws[row['chosen_draw']]['glyphs'], 'Wrong raw word returned')
    require(final['gate_calls'] == len(gates) and final['proposal_calls'] == len(proposals)
            and final['raw_draws'] == sum(len(p['draws']) for p in proposals)
            and final['anchor_fallbacks'] == sum(p['fallback'] for p in proposals)
            and final['gate_changed_calls'] == sum(g['parent_probability'] != g['adapted_probability'] for g in gates),
            'PF trace summary mismatch')
    return dict(result, gate_calls=len(gates), proposal_calls=len(proposals), raw_draws=final['raw_draws'],
                anchor_fallbacks=final['anchor_fallbacks'], gate_changed_calls=final['gate_changed_calls'])
