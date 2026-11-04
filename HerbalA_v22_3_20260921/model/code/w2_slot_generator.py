from __future__ import annotations

"""HerbalA v21r Stage-4 W2 exact-4 SLOT candidate generator.

The component is deliberately selector-local and read-only with respect to the live
semantic state.  It enumerates stable-22 H2/H3/H4 triples under the physical-width
and LEFT-support constraints and scores them only with the Stage-3 fold tables:

    log P(H2 | H1,W[,T])
  + log P(H3 | H1,W)
  + log P_BODY(H4 | H3)

No RIGHT bridge, route score, bT score, leaf excess, terminal prior, anchor H2/H3/H4,
or smooth sharing across total widths is used.
"""

from dataclasses import dataclass
from typing import Callable, Sequence
import math
import numpy as np

from w2_sibling_generator import W2SiblingKey
from w2_slot_tables import FoldSlotTables, VALID_WIDTHS, N_GLYPHS


@dataclass(frozen=True)
class SlotContext:
    h1: int
    total_width: int
    previous_terminal: int
    row_phase: str


@dataclass(frozen=True)
class SlotCandidate:
    glyphs: tuple[int, int, int, int]
    logp_h2: float
    logp_h3: float
    logp_h4: float
    score: float


@dataclass(frozen=True)
class SlotSelectionKey:
    run_seed: int
    bif: str
    page: str
    locus: str
    segment_id: int
    word_index: int
    proposal_id: int
    namespace: str = "V21_W2_SLOT_SELECT_V1"

    def _base(self) -> W2SiblingKey:
        return W2SiblingKey(
            run_seed=int(self.run_seed),
            bif=str(self.bif),
            page=str(self.page),
            locus=str(self.locus),
            segment_id=int(self.segment_id),
            word_index=int(self.word_index),
            proposal_id=int(self.proposal_id),
            namespace=str(self.namespace),
        )

    def digest_hex(self) -> str:
        return self._base().digest_hex()

    def rng(self) -> np.random.Generator:
        return self._base().rng()


class W2SlotGenerator:
    """Enumerate and score legal W2 exact-4 candidates."""

    def __init__(
        self,
        tables: FoldSlotTables,
        glyph_widths: Sequence[int],
        stable_width: Callable[[Sequence[int]], int],
    ) -> None:
        self.tables = tables
        self.widths = np.asarray(glyph_widths, dtype=int)
        if self.widths.shape[0] < N_GLYPHS:
            raise ValueError("glyph-width table shorter than stable-22")
        self.stable_width = stable_width

    def enumerate(
        self,
        context: SlotContext,
        left_legal: Callable[[int, int, int], bool],
    ) -> list[SlotCandidate]:
        h1 = int(context.h1)
        W = int(context.total_width)
        T = int(context.previous_terminal)
        phase = str(context.row_phase)
        if not 0 <= h1 < N_GLYPHS:
            return []
        if W not in VALID_WIDTHS:
            return []
        if not 0 <= T < N_GLYPHS:
            return []

        p2 = np.asarray(self.tables.prob_h2(h1, W, T, phase), dtype=float)
        p3 = np.asarray(self.tables.prob_h3(h1, W), dtype=float)
        if p2.shape != (N_GLYPHS,) or p3.shape != (N_GLYPHS,):
            raise ValueError("bad SLOT probability-vector shape")
        if not (np.isfinite(p2).all() and np.isfinite(p3).all() and (p2 > 0).all() and (p3 > 0).all()):
            raise ValueError("invalid H2/H3 SLOT probability table")

        wh1 = int(self.widths[h1])
        out: list[SlotCandidate] = []
        # H4 is required to have physical width 1.  Candidate multiplicity is one
        # per distinct stable-22 tuple: SLOT is a state-space enumeration, not a
        # proposal-pool resampling step.
        h4s = [g for g in range(N_GLYPHS) if int(self.widths[g]) == 1]
        for h2 in range(N_GLYPHS):
            w12 = wh1 + int(self.widths[h2])
            if w12 + 2 > W:  # H3,H4 each consume at least width 1
                continue
            lp2 = math.log(float(p2[h2]))
            for h3 in range(N_GLYPHS):
                if not bool(left_legal(h1, h2, h3)):
                    continue
                w123 = w12 + int(self.widths[h3])
                if w123 + 1 != W:
                    continue
                p4 = np.asarray(self.tables.prob_h4(h3), dtype=float)
                if p4.shape != (N_GLYPHS,) or not (np.isfinite(p4).all() and (p4 > 0).all()):
                    raise ValueError("invalid H4 SLOT probability table")
                lp3 = math.log(float(p3[h3]))
                for h4 in h4s:
                    seq = (h1, h2, h3, h4)
                    if int(self.stable_width(seq)) != W:
                        raise AssertionError((seq, W, self.stable_width(seq)))
                    lp4 = math.log(float(p4[h4]))
                    score = lp2 + lp3 + lp4
                    if not math.isfinite(score):
                        raise ValueError("non-finite SLOT score")
                    out.append(SlotCandidate(seq, lp2, lp3, lp4, score))
        return out

    @staticmethod
    def softmax(candidates: Sequence[SlotCandidate]) -> np.ndarray:
        if not candidates:
            return np.asarray([], dtype=float)
        s = np.asarray([c.score for c in candidates], dtype=float)
        if not np.isfinite(s).all():
            raise ValueError("non-finite SLOT candidate score")
        z = s - float(s.max())
        p = np.exp(z)
        den = float(p.sum())
        if not math.isfinite(den) or den <= 0:
            raise ValueError("invalid SLOT normalization")
        p /= den
        if not np.isfinite(p).all() or (p <= 0).any() or abs(float(p.sum()) - 1.0) > 1e-12:
            raise ValueError("invalid SLOT probability vector")
        return p

    @staticmethod
    def select(candidates: Sequence[SlotCandidate], probs: np.ndarray, key: SlotSelectionKey) -> tuple[int, SlotCandidate, str]:
        if not candidates:
            raise ValueError("cannot select from empty SLOT candidate set")
        if probs.shape != (len(candidates),):
            raise ValueError("candidate/probability length mismatch")
        rng = key.rng()
        j = int(rng.choice(len(candidates), p=probs))
        return j, candidates[j], key.digest_hex()
