"""External16-only proxy laws and selectors with no target-word/score argument."""
from __future__ import annotations

from collections import Counter
import math
import numpy as np

from judges.schema import GLYPHS, WIDTH, glyphs
from experiments.pf_generation.common import band, length_band
from experiments.pf_generation.overlay import family
from . import FAMILIES, DIRECTIONS
from .common import digest, require


def facts(rows):
    require(bool(rows), 'Empty donor segment')
    g = glyphs(rows[-1]['surface'])
    require(bool(g), 'Invalid visible endpoint')
    prev = glyphs(rows[-2]['surface']) if len(rows) > 1 else None
    require(len(rows) == 1 or bool(prev), 'Invalid predecessor')
    return dict(length=len(g), length_bin=length_band(len(g)), visible_width=sum(WIDTH[x] for x in g),
                width_bin=band(sum(WIDTH[x] for x in g)), physical_width=int(rows[-1]['phys_width']),
                terminal=g[-1], family=family(g[-1]), h1=g[0], previous_terminal=prev[-1] if prev else None,
                nwords=len(rows))


def outcome(f, lane):
    if lane == 'length_width':
        return 4 * f['length_bin'] + f['width_bin']
    if lane == 'terminal':
        return GLYPHS.index(f['terminal'])
    require(lane == 'space_T_H1' and f['previous_terminal'] is not None, 'No segment-local SPACE')
    return GLYPHS.index(f['previous_terminal']), GLYPHS.index(f['h1'])


def smooth(target, ordinary):
    t, o = np.asarray(target, float), np.asarray(ordinary, float)
    require(t.shape == o.shape and t.ndim == 1 and (t >= 0).all() and (o >= 0).all(), 'Invalid proxy counts')
    prior = (o + .5 / len(o)) / (o.sum() + .5)
    return ((t + 20 * prior) / (t.sum() + 20)).tolist()


def weighted(rows, lane, shape):
    counts = np.zeros(shape, float)
    selected = [r for r in rows if lane != 'space_T_H1' or r['facts']['previous_terminal'] is not None]
    by = Counter(r['bif'] for r in selected)
    for r in selected:
        counts[outcome(r['facts'], lane)] += len(selected) / (len(by) * by[r['bif']])
    return counts


def fit_fold(rt, fold):
    test = sorted(rt.active.folds(rt.C.bifs)[fold])
    train = sorted(set(rt.C.bifs) - set(test))
    require(len(train) == 16 and len(test) == 4, 'Proxy fold is not external16')
    strict = rt.C.T[rt.C.T.bif.isin(train) & rt.C.T.strict_line].sort_values('global_order')
    pf, lf, body = [], [], []
    for _, group in strict.groupby(['page', 'locus', 'segment_id'], sort=False):
        rows = list(group.itertuples(index=False))
        for i, row in enumerate(rows):
            record = dict(bif=str(row.bif), page=str(row.page), locus=str(row.locus), segment_id=int(row.segment_id),
                          word=i, facts=facts([dict(surface=r.surface, phys_width=r.width) for r in rows[:i+1]]))
            if i and row.role == 'BODY' and not bool(row.is_segment_end):
                body.append(record)
            if i == len(rows)-1 and str(row.boundary_type) == 'LINE_END' and int(row.para_line_raw) >= 2:
                (pf if bool(row.raw_para_final) else lf).append(record)
    tables = {}
    count_payload = {}
    for lane, shape in [('length_width', (12,)), ('terminal', (22,)), ('space_T_H1', (22,22))]:
        t, o = weighted(pf, lane, shape), weighted(body if lane == 'space_T_H1' else lf, lane, shape)
        if lane == 'space_T_H1':
            marginal = (o.sum(axis=0) + .5/22) / (o.sum() + .5)
            prior = np.array([(row + .5*marginal) / (row.sum()+.5) for row in o])
            p = (t + 20*prior) / (t.sum(axis=1)[:,None]+20)
            tables[lane] = p.tolist()
            count_payload['empty_body_contexts_backed_off_to_marginal'] = [GLYPHS[i] for i in range(22) if not o[i].sum()]
        else:
            tables[lane] = smooth(t, o)
        count_payload[lane] = dict(pf=t.tolist(), ordinary=o.tolist())
    payload = dict(fold=int(fold), training_bifolia=train, excluded_bifolia=test, known3_used=False,
                   training_pages=sorted(strict.page.astype(str).unique()),
                   training_sha256=digest(pf), prior_sha256=digest([lf, body]),
                   counts=count_payload, probabilities=tables, tables_sha256=digest(tables),
                   prior_mass=.5, shrinkage_mass=20, weighting='equal_leaf_rescaled_to_event_count',
                   ordinary='strict nonfinal LF endpoints; strict interior BODY transitions within segment')
    require(len(payload['training_pages']) == 64, 'Proxy training must include all four faces')
    return payload


def nll(table, f, lane):
    ix = outcome(f, lane)
    p = table['probabilities'][lane]
    p = p[ix[0]][ix[1]] if isinstance(ix, tuple) else p[ix]
    require(math.isfinite(p) and 0 < p <= 1, 'Invalid proxy probability')
    return -math.log(p)


def allowed(anchor, candidate, lane):
    if lane == 'length_width':
        return True
    fixed = ('length_bin', 'visible_width', 'physical_width', 'family' if lane == 'terminal' else 'terminal')
    return all(anchor[k] == candidate[k] for k in fixed) and (lane != 'space_T_H1' or
            anchor['previous_terminal'] is not None and candidate['previous_terminal'] is not None)


def select(anchor_rows, donors, table):
    """No true-page observations, known3, scores, CAL or keys can enter this API."""
    require([d['branch'] for d in donors] == list(range(64)), 'Donor bank coverage must be exactly 64 ordered branches')
    anchor = facts(anchor_rows)
    result = []
    for lane in FAMILIES:
        available = lane != 'space_T_H1' or anchor['previous_terminal'] is not None
        base = nll(table, anchor, lane) if available else None
        for direction in DIRECTIONS:
            matches = []
            for d in donors:
                f = facts(d['rows'])
                if available and allowed(anchor, f, lane):
                    score = nll(table, f, lane)
                    if (score < base-1e-12 if direction == 'near' else score > base+1e-12):
                        matches.append((score, d['branch'], f))
            best = None
            for score, branch, f in matches:
                if best is None or (score < best[0]-1e-12 if direction == 'near' else score > best[0]+1e-12):
                    best = score, branch, f
            result.append(dict(family=lane, direction=direction, anchor=anchor, anchor_nll=base,
                               branch=best[1] if best else None, donor_nll=best[0] if best else None,
                               donor=best[2] if best else None,
                               status='SELECTED' if best else 'NO_MATCH_WITHIN_64'))
    return result
