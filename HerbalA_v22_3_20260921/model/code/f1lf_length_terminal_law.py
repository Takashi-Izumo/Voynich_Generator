from __future__ import annotations

"""Stage-3D terminal-law utilities for HerbalA-v22.3 candidate.

This module contains no generator-side effects.  It translates the frozen
Stage-1/Stage-2 F1-LF hypothesis into target-blind LOBO terminal source laws
and builds the strict 88-event activation ledger from frozen schedule/event
metadata.

The statistical intervention is deliberately terminal-only:
  * short words (L<=3): normal middle-LF terminal law;
  * long words (L>=4): F1 terminal law, except P(l) inherited from normal LF;
  * STOP/CONTINUE is not touched here.

Source laws are estimated from the other complete bifolia only.  tau=20 is the
frozen shrinkage value from the terminal-source contest.  A tiny numerical
floor is used only to keep bank/live support invariant under finite precision;
it never creates a candidate because the live sampler applies a separate legal
support mask.
"""

from dataclasses import dataclass, asdict
from typing import Iterable
import numpy as np
import pandas as pd
import v19r_rb3_pw2_close1 as m

N_GLYPH = 22
L_GLYPH = int(m.G2I['l'])
NUMERICAL_FLOOR = 1e-15  # log/division guard only; never added to probability support


def _norm(p):
    p = np.asarray(p, dtype=float).copy()
    if p.shape != (N_GLYPH,):
        raise ValueError(f'Expected {N_GLYPH} glyph probabilities, got {p.shape}')
    if not np.all(np.isfinite(p)) or np.any(p < 0):
        raise ValueError('Invalid probability vector')
    z = float(p.sum())
    if z <= 0:
        raise ValueError('Zero-mass probability vector')
    p /= z
    return p


def _counts(df: pd.DataFrame) -> np.ndarray:
    out = np.zeros(N_GLYPH, dtype=float)
    for g in df['glyphs']:
        z = tuple(g)
        if not z:
            continue
        t = int(z[-1])
        if 0 <= t < N_GLYPH:
            out[t] += 1.0
    return out


def _shrink(source_counts: np.ndarray, shared_counts: np.ndarray, tau: float) -> np.ndarray:
    source_counts = np.asarray(source_counts, float)
    shared_counts = np.asarray(shared_counts, float)
    # Preserve empirical support exactly.  No epsilon mass is added to glyphs.
    # tau shrinks toward the observed shared source only.
    if float(shared_counts.sum()) <= 0:
        raise ValueError('Empty shared source')
    shared = shared_counts / shared_counts.sum()
    q = source_counts + float(tau) * shared
    if q.sum() <= 0:
        q = shared.copy()
    return _norm(q)


def long_l_inheritance(p_f1: np.ndarray, p_normal_lf: np.ndarray) -> np.ndarray:
    """Frozen Stage-1 transform.

    P_new(l) = P_normalLF(l)
    P_new(g!=l) = P_F1(g) * (1-P_normalLF(l))/(1-P_F1(l))

    This preserves all non-l ratios exactly (up to floating point rounding),
    including y/n.  Support is required to remain identical to p_f1.
    """
    p_f1 = _norm(p_f1)
    p_normal_lf = _norm(p_normal_lf)
    old_l = float(p_f1[L_GLYPH])
    new_l = float(p_normal_lf[L_GLYPH])
    if not (0.0 <= old_l < 1.0) or not (0.0 <= new_l < 1.0):
        raise ValueError(('Degenerate l probability', old_l, new_l))
    scale = (1.0 - new_l) / (1.0 - old_l)
    out = p_f1 * scale
    out[L_GLYPH] = new_l
    # Do not renormalize unless roundoff forces it: the formula sums to 1.
    err = abs(float(out.sum()) - 1.0)
    if err > 1e-12:
        raise AssertionError(('Long selector normalization drift', err))
    out /= out.sum()
    return out


@dataclass(frozen=True)
class TerminalLaw:
    target_bif: str
    training_bifs: tuple[str, ...]
    tau: float
    source_definition: str
    f1_long_n: int
    normal_lf_short_n: int
    normal_lf_long_n: int
    shared_body_short_n: int
    shared_body_long_n: int
    p_f1_long: tuple[float, ...]
    p_normal_lf_short: tuple[float, ...]
    p_normal_lf_long: tuple[float, ...]
    p_long_new: tuple[float, ...]

    def short(self) -> np.ndarray:
        return np.asarray(self.p_normal_lf_short, float)

    def long(self) -> np.ndarray:
        return np.asarray(self.p_long_new, float)

    def asdict(self):
        return asdict(self)


def build_terminal_law(events: pd.DataFrame, complete_bifs: Iterable[str], target_bif: str,
                       tau: float = 20.0) -> TerminalLaw:
    """Build one whole-bifolium-excluded terminal source law.

    The implementation intentionally uses only terminal glyph counts and frozen
    structural labels.  Target-bifolium glyphs are excluded from every source.

    F1 source: FIRST-line non-LF F1 words (the target F1-LF cell itself is not
    used as a source).
    normal-LF source: MIDDLE-row physical LF BODY words.
    shared source: MIDDLE-row BODY words, used only as tau=20 shrinkage anchor.

    Each source is split at L<=3 / L>=4 before estimating the terminal law.
    """
    bifs = tuple(sorted(str(x) for x in complete_bifs))
    target_bif = str(target_bif)
    if target_bif not in bifs:
        raise ValueError(f'Target bifolium not in complete set: {target_bif}')
    train_bifs = tuple(x for x in bifs if x != target_bif)
    d = events[events['bif'].astype(str).isin(train_bifs)].copy()
    if len(d) == 0:
        raise ValueError('No source events after LOBO exclusion')
    d['L'] = d['glyphs'].map(len)
    # Source-quality policy: exact token mapping and position-eligible only.
    if 'mapping_quality' in d:
        d = d[d['mapping_quality'].astype(str).eq('EXACT_W_SEQUENCE')]
    if 'position_eligible' in d:
        d = d[d['position_eligible'].astype(bool)]

    f1 = d[d['base_role'].astype(str).eq('F1') & ~d['board'].astype(str).eq('LF')]
    nlf = d[(d['base_role'].astype(str).eq('BODY')) &
            (d['board'].astype(str).eq('LF')) &
            (d['row_phase'].astype(str).eq('MIDDLE'))]
    body = d[(d['base_role'].astype(str).eq('BODY')) &
             (d['board'].astype(str).eq('BODY')) &
             (d['row_phase'].astype(str).eq('MIDDLE'))]

    f1_long = f1[f1['L'].ge(4)]
    nlf_short = nlf[nlf['L'].le(3)]
    nlf_long = nlf[nlf['L'].ge(4)]
    body_short = body[body['L'].le(3)]
    body_long = body[body['L'].ge(4)]
    if min(len(f1_long), len(nlf_short), len(nlf_long), len(body_short), len(body_long)) <= 0:
        raise ValueError(('Empty Stage-3D source stratum', target_bif,
                          len(f1_long), len(nlf_short), len(nlf_long),
                          len(body_short), len(body_long)))

    p_f1_long = _shrink(_counts(f1_long), _counts(body_long), tau)
    p_nlf_short = _shrink(_counts(nlf_short), _counts(body_short), tau)
    p_nlf_long = _shrink(_counts(nlf_long), _counts(body_long), tau)
    p_long = long_l_inheritance(p_f1_long, p_nlf_long)

    return TerminalLaw(
        target_bif=target_bif,
        training_bifs=train_bifs,
        tau=float(tau),
        source_definition=(
            'LOBO complete-bifolia; F1=FIRST non-LF F1; '
            'normalLF=MIDDLE physical-LF BODY; shared=MIDDLE BODY; '
            'exact mapping + position eligible; split L<=3/L>=4'
        ),
        f1_long_n=int(len(f1_long)),
        normal_lf_short_n=int(len(nlf_short)),
        normal_lf_long_n=int(len(nlf_long)),
        shared_body_short_n=int(len(body_short)),
        shared_body_long_n=int(len(body_long)),
        p_f1_long=tuple(map(float, p_f1_long)),
        p_normal_lf_short=tuple(map(float, p_nlf_short)),
        p_normal_lf_long=tuple(map(float, p_nlf_long)),
        p_long_new=tuple(map(float, p_long)),
    )


def build_strict_scope_ledger(C, events: pd.DataFrame, lines: pd.DataFrame) -> pd.DataFrame:
    """Reproduce the frozen 88-event / 20-complete-bifolia strict scope.

    width_known is conservative: UNKNOWN_GAP immediately before the terminal
    event is treated as unknown width.  The ledger stores only structural
    metadata; no target terminal glyph is used by the runtime gate.
    """
    d = C.df.copy()
    line_meta = d.groupby(['page', 'locus'], as_index=False).agg(
        layout_mode=('layout_mode', 'first'),
        line_word_count=('surface', 'size'),
        para=('para', 'first'),
    )
    para_lines = (d.groupby(['page', 'para'])['para_line_raw'].max()
                    .rename('paragraph_line_count').reset_index())
    line_meta = line_meta.merge(para_lines, on=['page', 'para'], how='left')
    line_q = lines[['locus', 'raw_plant', 'raw_unknown', 'exact']].copy()
    x = (events.merge(line_q, on='locus', how='left')
               .merge(line_meta[['page','locus','layout_mode','line_word_count','paragraph_line_count']],
                      on=['page','locus'], how='left'))
    complete = set(map(str, C.bifs))
    width_known = ~x['boundary_before'].astype(str).eq('UNKNOWN_GAP')
    plant_boundary = x['raw_plant'].fillna(0).astype(int).gt(0)
    mask = (
        x['bif'].astype(str).isin(complete)
        & x['base_role'].astype(str).eq('F1')
        & x['row_phase'].astype(str).eq('FIRST')
        & x['physical_final'].astype(bool)
        & x['segment_id'].astype(int).eq(0)
        & x['board'].astype(str).eq('LF')
        & x['mapping_quality'].astype(str).eq('EXACT_W_SEQUENCE')
        & width_known
        & ~plant_boundary
        & x['layout_mode'].astype(str).eq('linear_paragraph')
        & x['line_word_count'].astype(int).gt(1)
        & x['paragraph_line_count'].astype(int).gt(1)
    )
    z = x.loc[mask, ['page','locus','bif','para','para_line_raw','segment_id','base_role','row_phase','board',
                     'physical_final','mapping_quality','layout_mode','line_word_count','paragraph_line_count',
                     'boundary_before','raw_plant','raw_unknown','exact']].copy()
    z['role'] = 'F1'
    z['plant_restart'] = False
    z['plant_boundary'] = False
    z['width_known'] = True
    z['strict_scope'] = True
    z = z.sort_values(['bif','page','locus']).reset_index(drop=True)
    if len(z) != 88 or z['bif'].nunique() != 20:
        raise AssertionError(('Strict F1-LF ledger mismatch', len(z), z['bif'].nunique()))
    if z[['page','locus']].duplicated().any():
        raise AssertionError('Strict scope ledger contains duplicate page/locus keys')
    return z


def law_invariants(law: TerminalLaw) -> dict:
    pf = np.asarray(law.p_f1_long, float)
    pl = np.asarray(law.p_normal_lf_long, float)
    pn = np.asarray(law.p_long_new, float)
    non_l = [i for i in range(N_GLYPH) if i != L_GLYPH]
    # Compare ratios only on the positive F1 support.  Zero-probability glyphs
    # must stay exactly zero and are checked separately by support_changes.
    pos_non_l = [i for i in non_l if pf[i] > 0]
    anchor = max(pos_non_l, key=lambda i: pf[i])
    ratio_err = max(abs((pn[i] / pn[anchor]) - (pf[i] / pf[anchor])) for i in pos_non_l)
    y, n = int(m.G2I['y']), int(m.G2I['n'])
    if pf[y] > 0 and pf[n] > 0 and pn[n] > 0:
        yn_err = abs((pn[y] / pn[n]) - (pf[y] / pf[n]))
    else:
        yn_err = 0.0 if ((pf[y] > 0) == (pn[y] > 0) and (pf[n] > 0) == (pn[n] > 0)) else float('inf')
    return dict(
        probability_sum_error=max(abs(pf.sum()-1), abs(pl.sum()-1), abs(pn.sum()-1)),
        l_inheritance_error=abs(float(pn[L_GLYPH])-float(pl[L_GLYPH])),
        non_l_ratio_error=float(ratio_err),
        y_n_ratio_error=float(yn_err),
        support_changes=int(np.sum((pf > 0) != (pn > 0))),
        finite=bool(np.all(np.isfinite(pn))),
        nonnegative=bool(np.all(pn >= 0)),
    )
