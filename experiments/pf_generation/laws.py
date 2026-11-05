"""Small external16 laws. No target known3 or evaluation scores enter fitting."""
from __future__ import annotations

from dataclasses import dataclass
import math
import numpy as np
from scipy.special import expit

from . import POLICY
from .common import band, length_band, digest, require


@dataclass(frozen=True)
class Law:
    theta: tuple
    gains: tuple

    @classmethod
    def load(cls, payload):
        theta = tuple(float(x) for x in payload['theta'])
        gains = tuple(tuple(float(x) for x in row) for row in payload['gains'])
        require(len(theta) == 4 and len(gains) == 3 and all(len(row) == 4 for row in gains), 'Invalid law shape')
        require(all(math.isfinite(x) for x in theta), 'Nonfinite gate offset')
        require(all(math.isfinite(x) and POLICY['gain_min'] <= x <= POLICY['gain_max'] for row in gains for x in row),
                'Invalid proposal gain')
        return cls(theta, gains)

    @property
    def identity(self):
        return all(x == 1.0 for row in self.gains for x in row)

    @property
    def normalizer(self):
        return max(x for row in self.gains for x in row)


def equal_leaf_weights(frame):
    require(len(frame) > 0, 'No training events')
    counts = frame.groupby('bif').bif.transform('size').to_numpy(float)
    return len(frame) / (frame.bif.nunique() * counts)


def fit_offsets(offsets, labels, bins, weights, ridge=20.0):
    offsets, labels, bins, weights = map(np.asarray, (offsets, labels, bins, weights))
    require(len(offsets) == len(labels) == len(bins) == len(weights) > 0, 'Invalid gate training rows')
    require(np.isfinite(offsets).all() and np.isfinite(weights).all() and (weights > 0).all()
            and np.isin(labels, [0, 1]).all() and np.isin(bins, [0, 1, 2, 3]).all() and ridge > 0,
            'Invalid gate observations')
    result = []
    for b in range(4):
        selected = bins == b
        if not selected.any():
            result.append(0.0)
            continue
        x, y, w = offsets[selected], labels[selected], weights[selected]
        theta = 0.0
        for _ in range(100):
            p = expit(x + theta)
            gradient = float(np.sum(w * (p - y)) + ridge * theta)
            if abs(gradient) < 1e-9:
                break
            hessian = float(np.sum(w * p * (1 - p)) + ridge)
            theta -= gradient / hessian
        else:
            raise ValueError('PF gate did not converge')
        require(math.isfinite(theta), 'Nonfinite fitted offset')
        result.append(theta)
    return result


def count_lengths(frame):
    counts = np.zeros((3, 4), float)
    if len(frame):
        for row, weight in zip(frame.itertuples(), equal_leaf_weights(frame)):
            counts[length_band(int(row.length)), band(int(row.width))] += weight
    return counts


def fit_length_gains(pf_counts, lf_counts):
    pf, lf = np.asarray(pf_counts, float), np.asarray(lf_counts, float)
    require(pf.shape == lf.shape == (3, 4) and np.isfinite(pf).all() and np.isfinite(lf).all()
            and (pf >= 0).all() and (lf >= 0).all(), 'Invalid length counts')
    prior = (lf + POLICY['prior_mass'] / 3) / (lf.sum(axis=0) + POLICY['prior_mass'])
    target = (pf + POLICY['shrinkage_mass'] * prior) / (pf.sum(axis=0) + POLICY['shrinkage_mass'])
    gains = np.clip(target / prior, POLICY['gain_min'], POLICY['gain_max'])
    gains[:, (pf.sum(axis=0) == 0) | (lf.sum(axis=0) == 0)] = 1.0
    return gains.tolist()


def fit_fold(runtime, fold, identity=False):
    a, context, m = runtime.active, runtime.C, runtime.engine.m
    test = tuple(a.folds(context.bifs)[fold])
    train = tuple(sorted(set(context.bifs) - set(test)))
    bif = test[0]
    fc = a.FoldContext.create(context, fold, bif, context.pages[bif][-1], 'LEGACY_SCOPE', a.POLICY)
    require(tuple(fc.complete_train_bifs) == train and not set(train) & set(test), 'External16 mismatch')
    core, core_audit = a.load_core(context, fc)
    tokens = context.T
    strict = tokens[tokens.bif.isin(train) & tokens.strict_line]
    pf = strict[strict.pf].sort_values('global_order').copy()
    require(len(pf) > 0, 'No PF training segments')
    for _, group in pf.groupby(['page', 'locus', 'segment_id']):
        rows = list(group.itertuples())
        remaining = int(rows[0].segment_capacity)
        for i, row in enumerate(rows):
            require(int(row.segment_rstart) == remaining and int(row.width) == m.stable_width(row.glyphs),
                    'PF training width mismatch')
            require(bool(row.is_segment_end) == (i == len(rows) - 1), 'Incomplete PF training segment')
            remaining -= int(row.width) + int(i < len(rows) - 1)
        require(remaining == 0, 'PF training capacity mismatch')
    r = pf.segment_rstart.to_numpy(float)
    c = pf.segment_capacity.to_numpy(float)
    x = np.c_[r, np.log1p(r), r / np.maximum(c, 1), c]
    p = core[2].gate.predict_proba(x)[:, 1]
    offsets = np.array([m.logit(value) for value in p])
    split = pf.nsegments.to_numpy(int) > 1
    offsets += np.where(split, math.log(m.FINAL_SEG_CLOSE_GAIN), 0.0)
    theta = fit_offsets(offsets, pf.is_segment_end.astype(int).to_numpy(), [band(v) for v in r],
                        equal_leaf_weights(pf), POLICY['gate_ridge'])
    ends = pf[pf.is_segment_end]
    ordinary = strict[(strict.para_line_raw >= 2) & ~strict.raw_para_final
                      & strict.boundary_type.eq('LINE_END') & strict.is_segment_end]
    pc, lc = count_lengths(ends), count_lengths(ordinary)
    gains = fit_length_gains(pc, lc)
    training = pf[['bif', 'page', 'locus', 'segment_id', 'surface', 'segment_rstart',
                   'segment_capacity', 'is_segment_end']].to_dict('records')
    prior_rows = ordinary[['bif', 'page', 'locus', 'surface', 'width', 'length']].to_dict('records')
    payload = dict(fold=fold, training_bifolia=list(train), excluded_bifolia=list(test),
                   known3_used=False, pf_segments=len(ends), pf_word_starts=len(pf),
                   ordinary_line_ends=len(ordinary), training_sha256=digest(training),
                   prior_sha256=digest(prior_rows), parent_core_sha256=core_audit['sha256'],
                   theta=[0.0] * 4 if identity else theta,
                   gains=np.ones((3, 4)).tolist() if identity else gains,
                   fitted_theta=theta, fitted_gains=gains, identity_override=bool(identity),
                   pf_length_counts=pc.tolist(), ordinary_length_counts=lc.tolist(),
                   runtime_inputs=runtime.input_snapshot, source_data_hashes=context.input_hashes)
    Law.load(payload)
    return payload
