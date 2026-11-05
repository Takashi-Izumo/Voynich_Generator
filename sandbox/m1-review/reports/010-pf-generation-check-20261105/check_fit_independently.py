"""Reviewer-side reconstruction; does not use pf_generation fit functions."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import sys

import numpy as np
from scipy.optimize import brentq
from scipy.special import expit

ROOT = Path(os.environ.get('PF_REVIEW_CHECKOUT', '/workspace/voynich-results/m1-v2-independent-20261105/checkout'))
OUT = Path(os.environ.get('PF_REVIEW_ROOT', '/workspace/voynich-results/pf-generation-independent-20261105'))
sys.path.insert(0, str(ROOT))
from experiments.m1_pf.runtime import Runtime
from experiments.m1_pf.common import digest

def bands(values, thresholds):
    return np.searchsorted(thresholds, np.asarray(values), side='left')

def weights(frame):
    n = Counter(frame.bif)
    return np.array([len(frame) / (len(n) * n[b]) for b in frame.bif])

def counts(frame):
    result = np.zeros((3, 4))
    for row, w in zip(frame.itertuples(), weights(frame)):
        result[bands(row.length, [3, 6]), bands(row.width, [3, 6, 9])] += w
    return result

def main():
    rt = Runtime()
    plan = json.loads((OUT / 'all-folds-plan/plan.json').read_text())
    smoke = json.loads((OUT / 'plan/plan.json').read_text())
    identity = json.loads((OUT / 'identity-plan/plan.json').read_text())
    shared = json.loads((ROOT / 'sandbox/m1-review/implementation/009-pf-generation-v1/study-plan/plan.json').read_text())
    assert smoke == shared, 'Fresh fit differs from implementation report'
    contract_root = ROOT / 'sandbox/m1-review/designs/007-pf-generation-v1'
    manifest = json.loads((contract_root / 'MANIFEST.json').read_text())
    for item in manifest['files']:
        b = (contract_root / item['path']).read_bytes()
        assert len(b) == item['bytes'] and hashlib.sha256(b).hexdigest() == item['sha256']
    result = {'status': 'PASS', 'method': 'Reconstructed source masks and counts; independent Brent root solve for ridge gradient',
              'smoke_plan_hash': smoke['plan_hash'], 'all_fold_plan_hash': plan['plan_hash'],
              'identity_plan_hash': identity['plan_hash'], 'fresh_smoke_plan_equals_shared_bytes_as_json': True,
              'design_manifest_files_checked': len(manifest['files']), 'folds': []}
    for f in range(5):
        law = plan['laws'][str(f)]
        excluded = tuple(sorted(rt.C.bifs)[f::5])
        training = sorted(set(rt.C.bifs) - set(excluded))
        assert law['excluded_bifolia'] == list(excluded)
        assert law['training_bifolia'] == training and not law['known3_used']
        fc = rt.active.FoldContext.create(rt.C, f, excluded[0], rt.C.pages[excluded[0]][-1], 'LEGACY_SCOPE', rt.active.POLICY)
        core, audit = rt.active.load_core(rt.C, fc)
        assert law['parent_core_sha256'] == audit['sha256']
        strict = rt.C.T[rt.C.T.bif.isin(training) & rt.C.T.strict_line]
        pf = strict[strict.raw_para_final & strict.boundary_type.eq('LINE_END') & (strict.para_line_raw >= 2)].sort_values('global_order')
        lf = strict[~strict.raw_para_final & strict.boundary_type.eq('LINE_END') & (strict.para_line_raw >= 2) & strict.is_segment_end]
        ends = pf[pf.is_segment_end]
        assert not set(pf.bif) & set(excluded)
        assert not set(lf.bif) & set(excluded)
        assert set(pf.page) <= {p for b in training for p in rt.C.pages[b]}
        for _, group in pf.groupby(['page', 'locus', 'segment_id']):
            rows = list(group.itertuples())
            remaining = rows[0].segment_capacity
            for i, row in enumerate(rows):
                assert row.segment_rstart == remaining and row.width == rt.engine.m.stable_width(row.glyphs)
                assert row.length == len(row.glyphs)
                assert bool(row.is_segment_end) == (i == len(rows) - 1)
                remaining -= row.width + (i < len(rows) - 1)
            assert remaining == 0
        pf_counts, lf_counts = counts(ends), counts(lf)
        np.testing.assert_allclose(pf_counts, law['pf_length_counts'], atol=1e-12, rtol=0)
        np.testing.assert_allclose(lf_counts, law['ordinary_length_counts'], atol=1e-12, rtol=0)
        prior = (lf_counts + .5 / 3) / (lf_counts.sum(axis=0) + .5)
        target = (pf_counts + 20 * prior) / (pf_counts.sum(axis=0) + 20)
        gains = np.clip(target / prior, .25, 4.)
        gains[:, (pf_counts.sum(axis=0) == 0) | (lf_counts.sum(axis=0) == 0)] = 1.
        np.testing.assert_allclose(gains, law['gains'], atol=1e-12, rtol=0)
        r, c = pf.segment_rstart.to_numpy(float), pf.segment_capacity.to_numpy(float)
        x = np.column_stack([r, np.log1p(r), r / np.maximum(c, 1), c])
        parent = core[2].gate.predict_proba(x)[:, 1]
        offset = np.log(np.clip(parent, 1e-8, 1-1e-8) / (1-np.clip(parent, 1e-8, 1-1e-8)))
        offset += np.where(pf.nsegments.to_numpy(int) > 1, np.log(.8), 0.)
        w, y, bins = weights(pf), pf.is_segment_end.to_numpy(int), bands(r, [3, 6, 9])
        theta = []
        for b in range(4):
            mask = bins == b
            grad = lambda t: np.sum(w[mask] * (expit(offset[mask] + t) - y[mask])) + 20 * t
            theta.append(brentq(grad, -100, 100, xtol=1e-14) if mask.any() else 0.)
        np.testing.assert_allclose(theta, law['theta'], atol=1e-10, rtol=0)
        if str(f) in smoke['laws']:
            assert law == smoke['laws'][str(f)]
            other = identity['laws'][str(f)]
            assert other['fitted_theta'] == law['theta'] and other['fitted_gains'] == law['gains']
        result['folds'].append(dict(fold=f, pf_ends=len(ends), pf_starts=len(pf), prior_ends=len(lf),
            contributing_pf_bifolia=sorted(set(ends.bif)), training_bifolia=training, excluded_bifolia=list(excluded),
            law_sha256=digest(law), max_theta_difference=float(np.max(np.abs(np.array(theta)-law['theta']))),
            max_gain_difference=float(np.max(np.abs(gains-law['gains']))),
            parent_core_scope=audit['mode'], auxiliary_parent_bifolia=list(fc.incomplete_aux_bifs),
            training_m_ends=int(sum('m' in str(s) for s in ends.surface)),
            long_word_gain_by_width=law['gains'][2]))
    (OUT / 'independent-fit-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'fold_pf_ends': [r['pf_ends'] for r in result['folds']],
                      'max_theta_difference': max(r['max_theta_difference'] for r in result['folds'])}), flush=True)

if __name__ == '__main__':
    main()
