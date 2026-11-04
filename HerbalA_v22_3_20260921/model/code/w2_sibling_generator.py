"""W2 H1-fixed sibling proposal generator (Stage 1, not integrated).

This module is intentionally selector-free.  It does not modify the live generation
chain.  It only exposes a deterministic, side-streamed proposal component that:

* takes an already-selected W2 anchor;
* clamps H1 to the anchor H1;
* redraws the word with the frozen parent W2 proposal generator;
* accepts only siblings with the exact anchor glyph length and stable physical width;
* preserves multiplicity of repeated accepted proposals;
* never uses W2 residual tables or the held-out target page.

The caller owns model objects (cdf, quad, base sampler, entry tables, patch) and the
request-local state.  This makes the component reusable by Stage 2 without changing
parent code in Stage 1.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Iterable, Optional, Sequence, Tuple

import numpy as np

try:
    from entry_fast_sampler import draw_entry_word
except Exception as exc:  # pragma: no cover - environment diagnostic
    draw_entry_word = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

GlyphSeq = Tuple[int, ...]


@dataclass(frozen=True)
class W2Anchor:
    glyphs: GlyphSeq
    h1: int
    length: int
    width: int


@dataclass(frozen=True)
class W2SiblingState:
    """Only state legitimately available at the W2 proposal request."""
    lp: int
    rstart: int
    end: bool
    line_end_boundary: bool
    row_phase: str
    board: str = "W2"
    physical_head: bool = False


@dataclass(frozen=True)
class W2SiblingKey:
    """Stable physical/proposal identity for the dedicated RNG substream."""
    run_seed: int
    bif: str
    page: str
    locus: str
    segment_id: int
    word_index: int
    proposal_id: int
    namespace: str = "W2SIB_V1"

    def canonical_bytes(self) -> bytes:
        obj = {
            "namespace": self.namespace,
            "run_seed": int(self.run_seed),
            "bif": str(self.bif),
            "page": str(self.page),
            "locus": str(self.locus),
            "segment_id": int(self.segment_id),
            "word_index": int(self.word_index),
            "proposal_id": int(self.proposal_id),
        }
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def digest_hex(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()

    def rng(self) -> np.random.Generator:
        # SeedSequence from four uint32 words; deterministic across Python processes.
        d = hashlib.sha256(self.canonical_bytes()).digest()
        entropy = np.frombuffer(d[:16], dtype="<u4").astype(np.uint32).tolist()
        return np.random.default_rng(np.random.SeedSequence(entropy))


@dataclass
class SiblingPoolResult:
    anchor: W2Anchor
    siblings: list[GlyphSeq]
    draws: int
    rejected_h1: int
    rejected_length: int
    rejected_width: int
    empty_draws: int
    row_audit: np.ndarray
    substream_digest: str

    @property
    def accepted(self) -> int:
        return len(self.siblings)



def make_anchor(seq: Sequence[int], stable_width: Callable[[Sequence[int]], int]) -> W2Anchor:
    g = tuple(int(x) for x in seq)
    if len(g) < 2:
        raise ValueError("W2 sibling anchor must contain H1 and H2")
    return W2Anchor(glyphs=g, h1=int(g[0]), length=len(g), width=int(stable_width(g)))


class W2SiblingGenerator:
    """Frozen-parent W2 sibling proposal component.

    No live sampler state is mutated.  `base`, `tables`, and `patch` are treated as
    read-only model objects.  H1 is clamped by a one-hot depth-0 gain; all H2+ rows,
    STOP odds, quad gate, and entry corrections remain the frozen parent logic.
    """

    ROLE_ID_W2 = 3
    N_GLYPHS = 22

    def __init__(
        self,
        *,
        cdf: Any,
        quad: Any,
        base: Any,
        tables: Any,
        patch: Any,
        stable_width: Callable[[Sequence[int]], int],
    ) -> None:
        if draw_entry_word is None:
            raise ImportError("entry_fast_sampler.draw_entry_word unavailable") from _IMPORT_ERROR
        self.cdf = cdf
        self.quad = quad
        self.base = base
        self.tables = tables
        self.patch = patch
        self.stable_width = stable_width

    def _gains(self, anchor: W2Anchor, state: W2SiblingState):
        if state.board != "W2":
            raise ValueError(f"Stage-1 W2 sibling generator requires board='W2', got {state.board!r}")
        if state.physical_head:
            raise ValueError("W2 sibling generator cannot be used at physical head")
        g1 = np.zeros(self.N_GLYPHS, dtype=float)
        if not (0 <= anchor.h1 < self.N_GLYPHS):
            raise ValueError(f"invalid H1 {anchor.h1}")
        g1[anchor.h1] = 1.0
        g2, g3 = self.tables.gains(
            "W2",
            int(state.lp),
            bool(state.end),
            bool(state.line_end_boundary),
            str(state.row_phase),
            str(state.board),
            False,
            self.patch,
        )
        return g1, g2, g3

    def draw_raw(self, anchor: W2Anchor, state: W2SiblingState, rng: np.random.Generator, audit: np.ndarray) -> GlyphSeq:
        """Draw one frozen-parent W2 proposal with H1 clamped to the anchor."""
        g1, g2, g3 = self._gains(anchor, state)
        seq = draw_entry_word(
            self.cdf,
            self.quad,
            self.ROLE_ID_W2,
            int(state.lp),
            rng,
            int(state.rstart),
            self.base.dw,
            self.base.dw2,
            -1,
            self.base.hh2,
            g1,
            g2,
            g3,
            audit,
        )
        return tuple(int(x) for x in seq)

    def collect(
        self,
        anchor: W2Anchor,
        state: W2SiblingState,
        key: W2SiblingKey,
        *,
        target_accepts: int,
        max_draws: int,
    ) -> SiblingPoolResult:
        """Collect accepted siblings, preserving proposal multiplicity.

        `target_accepts` is a testing/collection limit only.  Stage 1 does not define
        a production K or selector.  Stage 2 will decide K and fallback semantics.
        """
        if target_accepts < 1:
            raise ValueError("target_accepts must be >= 1")
        if max_draws < target_accepts:
            raise ValueError("max_draws must be >= target_accepts")
        rng = key.rng()
        audit = np.zeros(8, dtype=float)
        accepted: list[GlyphSeq] = []
        rejected_h1 = rejected_length = rejected_width = empty_draws = 0
        draws = 0
        while len(accepted) < target_accepts and draws < max_draws:
            draws += 1
            seq = self.draw_raw(anchor, state, rng, audit)
            if not seq:
                empty_draws += 1
                continue
            if int(seq[0]) != anchor.h1:
                rejected_h1 += 1
                continue
            if len(seq) != anchor.length:
                rejected_length += 1
                continue
            if int(self.stable_width(seq)) != anchor.width:
                rejected_width += 1
                continue
            accepted.append(seq)
        return SiblingPoolResult(
            anchor=anchor,
            siblings=accepted,
            draws=draws,
            rejected_h1=rejected_h1,
            rejected_length=rejected_length,
            rejected_width=rejected_width,
            empty_draws=empty_draws,
            row_audit=audit,
            substream_digest=key.digest_hex(),
        )


def assert_pool_constraints(result: SiblingPoolResult, stable_width: Callable[[Sequence[int]], int]) -> None:
    """Hard assertions used both in Stage-1 self-test and future Stage-2 audit."""
    a = result.anchor
    for s in result.siblings:
        assert s, "empty accepted sibling"
        assert int(s[0]) == a.h1, (s, a)
        assert len(s) == a.length, (s, a)
        assert int(stable_width(s)) == a.width, (s, a)
    # entry_fast_sampler audit slots: support violation, invalid probability, zero-Z.
    assert float(result.row_audit[5]) == 0.0, result.row_audit
    assert float(result.row_audit[6]) == 0.0, result.row_audit
    assert float(result.row_audit[7]) == 0.0, result.row_audit
