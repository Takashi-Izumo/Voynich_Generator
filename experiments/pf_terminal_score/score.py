"""Reweight the frozen PF selector's individual pre-m terminal feature.

Pass the adapter only as the native engine's pf_selector. BASE and REFERENCE
use the original selector. Candidate generation, LEN1, state and RNG belong
to the native engine; the M1 Runtime._generate installs its own Overlay.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sel42_selectors import LinearSelector


@dataclass(frozen=True)
class ScoreBreakdown:
    original_score: float
    adjusted_score: float
    lambda_e: float
    terminal_key: str
    terminal_coefficient: float
    intercept: float
    # Native feature order, including the original (unscaled) E contribution.
    feature_contributions: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class EWeightSelector:
    original: LinearSelector
    lambda_e: float

    def __post_init__(self):
        if self.original.kind != "PF":
            raise ValueError("EWeightSelector requires a PF selector")
        if (not isinstance(self.lambda_e, Real) or isinstance(self.lambda_e, bool)
                or self.lambda_e not in (0.0, 0.5, 1.0)):
            raise ValueError("lambda_e must be 0.0, 0.5 or 1.0")
        # Use native Python float arithmetic even for a numeric scalar input.
        object.__setattr__(self, "lambda_e", float(self.lambda_e))
        if not isfinite(self.original.intercept) or not all(
            isfinite(value) for value in self.original.coefficients.values()
        ):
            raise ValueError("Non-finite frozen PF coefficient or intercept")

    def _original_score(self, surface, width, capacity):
        if not (isfinite(width) and isfinite(capacity)):
            raise ValueError("Non-finite PF width or capacity")
        score = self.original.score(surface, width, capacity)
        if not isfinite(score):
            raise ValueError("Non-finite original PF score")
        return score

    @staticmethod
    def _features(surface, width, capacity):
        # Available after the caller initializes the frozen source runtime.
        from sel42_selectors import pf_features

        features = pf_features(surface, width, capacity)
        (terminal_key,) = (key for key in features if key.startswith("E="))
        return features, terminal_key

    def _adjust(self, original_score, terminal_coefficient):
        if self.lambda_e == 1.0 or terminal_coefficient == 0.0:
            return original_score
        score = original_score + (self.lambda_e - 1.0) * terminal_coefficient
        if not isfinite(score):
            raise ValueError("Non-finite adjusted PF score")
        return score

    def score(self, surface: str, width: float = 0, capacity: float = 1) -> float:
        """Native score signature. surface must be the raw stable_surface."""
        original_score = self._original_score(surface, width, capacity)
        if self.lambda_e == 1.0:
            return original_score
        _, terminal_key = self._features(surface, width, capacity)
        return self._adjust(original_score, self.original.coefficients.get(terminal_key, 0.0))

    def breakdown(self, surface: str, width: float = 0, capacity: float = 1) -> ScoreBreakdown:
        """Describe one call without retaining observations on the selector."""
        original_score = self._original_score(surface, width, capacity)
        features, terminal_key = self._features(surface, width, capacity)
        coefficients = self.original.coefficients
        terminal_coefficient = coefficients.get(terminal_key, 0.0)
        return ScoreBreakdown(
            original_score=original_score,
            adjusted_score=self._adjust(original_score, terminal_coefficient),
            lambda_e=self.lambda_e,
            terminal_key=terminal_key,
            terminal_coefficient=terminal_coefficient,
            intercept=self.original.intercept,
            feature_contributions=tuple((key, coefficients.get(key, 0.0)) for key in features),
        )
