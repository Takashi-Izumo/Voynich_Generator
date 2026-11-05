"""Recompute gate/proposal decisions independently of the generation hooks."""
from __future__ import annotations

import gzip
import json
import math
from pathlib import Path

from judges.schema import WIDTH, glyphs
from experiments.m1_pf.audit import audit_case as audit_parent_case
from . import POLICY, TRACE_SCHEMA
from .common import band, length_band, digest, require
from .laws import Law


def read_rows(path):
    with gzip.open(path, 'rt') as handle:
        return [json.loads(line) for line in handle]


def policy_digest(path):
    path = Path(path)
    return digest([read_rows(path / 'pfgen_gates.jsonl.gz'), read_rows(path / 'pfgen_proposals.jsonl.gz'),
                   json.loads((path / 'PF_GENERATION_FINAL.json').read_text()),
                   [(r['proposal_id'], r.get('pfgen')) for r in read_rows(path / 'requests.jsonl.gz')],
                   [c.get('pfgen_trace') for c in read_rows(path / 'm1_candidates.jsonl.gz')]])


def trace_coverage(candidates, requests, gates, proposals, arm):
    """Expected coverage comes from branch/request records, not policy row totals."""
    require([r['proposal_id'] for r in requests] == list(range(len(requests))), 'Missing/duplicate request IDs')
    if arm == 'BASE':
        require(not gates and not proposals and all('pfgen' not in r for r in requests), 'Policy trace in BASE')
        return dict(gate_queries=0, raw_calls=0, pf_requests=0)
    require([g.get('query_id') for g in gates] == list(range(len(gates))), 'Missing/duplicate/reordered gate query IDs')
    require([r.get('call_id') for r in proposals] == list(range(len(proposals))), 'Missing/duplicate/reordered raw call IDs')
    next_gate = next_raw = 0
    covered_requests = set()
    for candidate in candidates:
        window = candidate.get('pfgen_trace', {})
        require(window.get('trace_schema') == TRACE_SCHEMA, 'Missing PF candidate trace window')
        require(all(type(window.get(k)) is int for k in ['gate_start', 'gate_stop', 'raw_start', 'raw_stop']),
                'Invalid trace window IDs')
        ga, gz, ra, rz = [window[k] for k in ['gate_start', 'gate_stop', 'raw_start', 'raw_stop']]
        require(ga == next_gate and ra == next_raw and gz - ga >= candidate['nwords'] and rz >= ra,
                'Missing PF gate coverage or noncontiguous candidate windows')
        require(gz <= len(gates) and rz <= len(proposals), 'Missing PF policy rows for candidate window')
        next_gate, next_raw = gz, rz
        start, stop = candidate['proposal_id_start'], candidate['proposal_id_end']
        require(type(start) is int and type(stop) is int and 0 <= start < stop <= len(requests),
                'Invalid PF request interval')
        interval = requests[start:stop]
        require(not covered_requests.intersection(range(start, stop)), 'Overlapping PF request intervals')
        covered_requests.update(range(start, stop))
        query_ids, raw_ids = [], []
        by_query = {}
        for request in interval:
            require((request['page'], request['locus'], request['segment_id']) ==
                    (candidate['page'], candidate['locus'], candidate['segment_id'])
                    and request['row_phase'] == 'FINAL' and request['line_end_boundary'], 'PF request scope mismatch')
            link = request.get('pfgen', {})
            require(link.get('trace_schema') == TRACE_SCHEMA and type(link.get('gate_query_id')) is int
                    and ga <= link['gate_query_id'] < gz and link.get('event') == candidate['event']
                    and link.get('candidate') == candidate['candidate'], 'Missing/wrong PF request gate link')
            gid = link['gate_query_id']
            query_ids.append(gid)
            gate = gates[gid]
            require((gate['page'], gate['locus'], gate['segment_id'], gate['event'], gate['candidate']) ==
                    (candidate['page'], candidate['locus'], candidate['segment_id'], candidate['event'], candidate['candidate']),
                    'Gate query belongs to another candidate')
            require(gate['rstart'] == request['rstart'] and gate['capacity'] == candidate['segment_capacity'],
                    'Gate/request width mismatch')
            word = request['word_index'], request['rstart']
            require(gid not in by_query or by_query[gid] == word, 'Gate query merged distinct word starts')
            by_query[gid] = word
            # END requests use the unchanged v21 Map bank: one anchor plus
            # proposal_draws raw calls. PF END is board LF, outside W2 splice.
            expected = 1 + request['proposal_draws'] if arm == 'PF_GATE_LENGTH' and request['end'] else 0
            receipts = link.get('raw_calls')
            require(isinstance(receipts, list) and len(receipts) == expected, 'Missing/duplicate PF END raw request coverage')
            for receipt in receipts:
                rid = receipt.get('call_id')
                require(type(rid) is int and ra <= rid < rz, 'Raw call outside candidate window')
                row = proposals[rid]
                require(row['request_id'] == request['proposal_id'] and row['gate_query_id'] == gid
                        and row['word_index'] == request['word_index'] and row['rstart'] == request['rstart']
                        and row['role'] == request['role'], 'Raw call/request linkage mismatch')
                require(receipt.get('draws') == len(row['draws']) and receipt.get('row_sha256') == digest(row),
                        'Missing/changed inner raw draws or raw receipt')
                raw_ids.append(rid)
            if receipts:
                first = proposals[receipts[0]['call_id']]
                require(first['draws'][first['chosen_draw']]['stable_surface'] == request['first'],
                        'First raw return differs from parent request anchor')
        require(query_ids == sorted(query_ids) and set(query_ids) == set(range(ga, gz)),
                'Missing/extra/reordered gate queries for PF requests')
        require(raw_ids == list(range(ra, rz)), 'Missing/duplicate/reordered raw calls for PF requests')
    require(next_gate == len(gates) and next_raw == len(proposals), 'Unlinked PF policy rows')
    require(all(('pfgen' in r) == (r['proposal_id'] in covered_requests) for r in requests),
            'Missing/out-of-scope PF request metadata')
    return dict(gate_queries=next_gate, raw_calls=next_raw, pf_requests=len(covered_requests))


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
    require(final.get('trace_schema') == TRACE_SCHEMA and final['plan_hash'] == plan['plan_hash'] and final['fold'] == fold
            and final['arm'] == main['arm'] == arm and final['bif'] == main['bif']
            and final['run'] == main['run'] and final['law_sha256'] == digest(payload)
            and final['effective_law_sha256'] == digest(law)
            and final['source_sha256'] == digest(plan['implementation_sources'])
            and final['identity_override'] == plan['identity_override'], 'Wrong PF final provenance')
    gates = read_rows(path / 'pfgen_gates.jsonl.gz')
    proposals = read_rows(path / 'pfgen_proposals.jsonl.gz')
    candidates = read_rows(path / 'm1_candidates.jsonl.gz')
    requests = read_rows(path / 'requests.jsonl.gz')
    coverage = trace_coverage(candidates, requests, gates, proposals, arm)
    keys = {(c['page'], c['locus'], c['segment_id'], c['event'], c['candidate']) for c in candidates}
    key = lambda row: (row['page'], row['locus'], row['segment_id'], row['event'], row['candidate'])
    require(arm != 'BASE' or not gates, 'Gate adapter used in BASE')
    require(arm == 'PF_GATE_LENGTH' or not proposals, 'Length sampler used in wrong arm')
    for row in gates:
        require(row.get('trace_schema') == TRACE_SCHEMA and row['split_end'] == (row['segment_id'] > 0),
                'Wrong gate trace schema or split scope')
        require(row['generator_pf'] and key(row) in keys, 'Gate escaped PF candidate scope')
        require(row['band'] == band(row['rstart']) and row['offset'] == law.theta[row['band']], 'Wrong gate bin')
        before = row['parent_probability']
        after = before if row['offset'] == 0 else sigmoid(logit(before) + row['offset'])
        close(after, row['adapted_probability'])
        close(sigmoid(logit(after) + math.log(0.8)) if row['split_end'] else after, row['engine_probability'])
    for row in proposals:
        require(row.get('trace_schema') == TRACE_SCHEMA, 'Wrong raw trace schema')
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
    require(final['gate_calls'] == coverage['gate_queries'] and final['proposal_calls'] == coverage['raw_calls']
            and final['raw_draws'] == sum(len(p['draws']) for p in proposals)
            and final['anchor_fallbacks'] == sum(p['fallback'] for p in proposals)
            and final['gate_changed_calls'] == sum(g['parent_probability'] != g['adapted_probability'] for g in gates),
            'PF trace summary mismatch')
    return dict(result, trace_coverage_checked=True, pf_requests=coverage['pf_requests'],
                gate_calls=len(gates), proposal_calls=len(proposals), raw_draws=final['raw_draws'],
                anchor_fallbacks=final['anchor_fallbacks'], gate_changed_calls=final['gate_changed_calls'])
