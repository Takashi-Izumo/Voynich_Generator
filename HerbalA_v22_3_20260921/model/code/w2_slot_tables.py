from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd

N_GLYPHS = 22
UNIFORM = np.full(N_GLYPHS, 1.0 / N_GLYPHS, dtype=float)
ALPHA_GRID = (2.0, 4.0, 8.0, 16.0, 32.0)
H2_DEPTHS = (1, 2, 3, 4)
VALID_WIDTHS = (4, 5, 6, 7, 8)
H4_ALPHA_FIXED = 2.0


def _key(parts: Sequence[object]) -> str:
    norm=[]
    for x in parts:
        if isinstance(x, np.generic):
            x=x.item()
        norm.append(x)
    return json.dumps(norm, ensure_ascii=False, separators=(",", ":"))


def _arr(v: Sequence[float] | np.ndarray) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    if a.shape != (N_GLYPHS,):
        raise ValueError(f"expected {N_GLYPHS} glyph counts, got {a.shape}")
    return a


def _glyph_tuple(x) -> tuple[int, ...]:
    return tuple(int(v) for v in x)


def _count_vector(values: Iterable[int]) -> np.ndarray:
    out = np.zeros(N_GLYPHS, dtype=float)
    for v in values:
        i = int(v)
        if not 0 <= i < N_GLYPHS:
            raise ValueError(f"glyph outside stable-22: {i}")
        out[i] += 1.0
    return out


def _group_counts(df: pd.DataFrame, cols: Sequence[str], target: str) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    if df.empty:
        return out
    for vals, sub in df.groupby(list(cols), sort=True, dropna=False):
        if not isinstance(vals, tuple):
            vals = (vals,)
        out[_key(vals)] = _count_vector(sub[target].tolist())
    return out


def _smooth_root(root_counts: np.ndarray, alpha: float) -> np.ndarray:
    c = _arr(root_counts)
    den = float(c.sum() + alpha)
    if den <= 0:
        return UNIFORM.copy()
    return (c + float(alpha) * UNIFORM) / den


def _smooth_child(counts: np.ndarray | None, parent: np.ndarray, alpha: float) -> np.ndarray:
    if counts is None:
        return np.asarray(parent, dtype=float)
    c = _arr(counts)
    den = float(c.sum() + alpha)
    if den <= 0:
        return np.asarray(parent, dtype=float)
    return (c + float(alpha) * np.asarray(parent, dtype=float)) / den


def _safe_log2_prob(p: float) -> float:
    return -math.log2(max(float(p), 1e-300))


def _json_counts(d: Mapping[str, np.ndarray]) -> dict[str, list[float]]:
    return {str(k): np.asarray(v, dtype=float).tolist() for k, v in sorted(d.items())}


def _from_json_counts(d: Mapping[str, Sequence[float]]) -> dict[str, np.ndarray]:
    return {str(k): _arr(v) for k, v in d.items()}


def canonical_event_hash(df: pd.DataFrame, label: str) -> str:
    cols = ["global_order", "bif", "page", "locus", "glyphs", "base_role", "board", "prev_terminal", "row_phase"]
    h = hashlib.sha256()
    h.update((label + "\n").encode("utf-8"))
    for _, r in df.sort_values("global_order").iterrows():
        vals = []
        for c in cols:
            if c == "glyphs":
                vals.append(",".join(str(int(x)) for x in r[c]))
            else:
                vals.append(str(r[c]))
        h.update(("\t".join(vals) + "\n").encode("utf-8"))
    return h.hexdigest()


def prepare_w2_events(events: pd.DataFrame, stable_width, bifs: Sequence[str]) -> pd.DataFrame:
    d = events[events["bif"].isin(tuple(bifs))].copy()
    mask = (
        d["base_role"].eq("W2")
        & d["board"].eq("W2")
        & d["glyphs"].map(lambda g: len(g) == 4)
    )
    d = d.loc[mask].copy()
    if d.empty:
        return d
    d["glyphs"] = d["glyphs"].map(_glyph_tuple)
    d["H1"] = d["glyphs"].map(lambda g: int(g[0]))
    d["H2"] = d["glyphs"].map(lambda g: int(g[1]))
    d["H3"] = d["glyphs"].map(lambda g: int(g[2]))
    d["H4"] = d["glyphs"].map(lambda g: int(g[3]))
    d["W"] = d["glyphs"].map(lambda g: int(stable_width(g)))
    d["T"] = d["prev_terminal"].astype(int)
    d["PHASE"] = d["row_phase"].astype(str)
    d = d[d["W"].isin(VALID_WIDTHS)].copy()
    for c in ("H1", "H2", "H3", "H4"):
        if not d[c].between(0, N_GLYPHS - 1).all():
            raise AssertionError(f"non stable-22 glyph in W2 {c}")
    return d.sort_values("global_order").reset_index(drop=True)


def prepare_body_h4_events(events: pd.DataFrame, glyph_widths: Sequence[int], bifs: Sequence[str]) -> pd.DataFrame:
    widths = np.asarray(glyph_widths, dtype=int)
    d = events[events["bif"].isin(tuple(bifs))].copy()
    mask = (
        d["base_role"].eq("BODY")
        & d["board"].eq("BODY")
        & d["glyphs"].map(lambda g: len(g) == 4)
    )
    d = d.loc[mask].copy()
    if d.empty:
        return d
    d["glyphs"] = d["glyphs"].map(_glyph_tuple)
    d["H3"] = d["glyphs"].map(lambda g: int(g[2]))
    d["H4"] = d["glyphs"].map(lambda g: int(g[3]))
    d = d[d["H4"].map(lambda x: int(widths[int(x)]) == 1)].copy()
    for c in ("H3", "H4"):
        if not d[c].between(0, N_GLYPHS - 1).all():
            raise AssertionError(f"non stable-22 glyph in BODY {c}")
    return d.sort_values("global_order").reset_index(drop=True)


@dataclass
class H2Counts:
    root: np.ndarray
    h1: dict[str, np.ndarray]
    h1w: dict[str, np.ndarray]
    h1wt: dict[str, np.ndarray]
    h1wtp: dict[str, np.ndarray]

    @classmethod
    def fit(cls, df: pd.DataFrame) -> "H2Counts":
        return cls(
            root=_count_vector(df["H2"].tolist()),
            h1=_group_counts(df, ["H1"], "H2"),
            h1w=_group_counts(df, ["H1", "W"], "H2"),
            h1wt=_group_counts(df, ["H1", "W", "T"], "H2"),
            h1wtp=_group_counts(df, ["H1", "W", "T", "PHASE"], "H2"),
        )

    def prob(self, h1: int, w: int, t: int, phase: str, alpha: float, depth: int) -> np.ndarray:
        if depth not in H2_DEPTHS:
            raise ValueError(depth)
        p = _smooth_root(self.root, alpha)
        p = _smooth_child(self.h1.get(_key((int(h1),))), p, alpha)
        if depth >= 2:
            p = _smooth_child(self.h1w.get(_key((int(h1), int(w)))), p, alpha)
        if depth >= 3:
            p = _smooth_child(self.h1wt.get(_key((int(h1), int(w), int(t)))), p, alpha)
        if depth >= 4:
            p = _smooth_child(self.h1wtp.get(_key((int(h1), int(w), int(t), str(phase)))), p, alpha)
        return p

    def to_json(self) -> dict:
        return {
            "root": self.root.tolist(),
            "h1": _json_counts(self.h1),
            "h1w": _json_counts(self.h1w),
            "h1wt": _json_counts(self.h1wt),
            "h1wtp": _json_counts(self.h1wtp),
        }

    @classmethod
    def from_json(cls, x: Mapping[str, object]) -> "H2Counts":
        return cls(_arr(x["root"]), _from_json_counts(x["h1"]), _from_json_counts(x["h1w"]), _from_json_counts(x["h1wt"]), _from_json_counts(x["h1wtp"]))


@dataclass
class H3Counts:
    root: np.ndarray
    h1: dict[str, np.ndarray]
    h1w: dict[str, np.ndarray]

    @classmethod
    def fit(cls, df: pd.DataFrame) -> "H3Counts":
        return cls(
            root=_count_vector(df["H3"].tolist()),
            h1=_group_counts(df, ["H1"], "H3"),
            h1w=_group_counts(df, ["H1", "W"], "H3"),
        )

    def prob(self, h1: int, w: int, alpha: float) -> np.ndarray:
        p = _smooth_root(self.root, alpha)
        p = _smooth_child(self.h1.get(_key((int(h1),))), p, alpha)
        p = _smooth_child(self.h1w.get(_key((int(h1), int(w)))), p, alpha)
        return p

    def to_json(self) -> dict:
        return {"root": self.root.tolist(), "h1": _json_counts(self.h1), "h1w": _json_counts(self.h1w)}

    @classmethod
    def from_json(cls, x: Mapping[str, object]) -> "H3Counts":
        return cls(_arr(x["root"]), _from_json_counts(x["h1"]), _from_json_counts(x["h1w"]))


@dataclass
class H4Counts:
    root: np.ndarray
    h3: dict[str, np.ndarray]

    @classmethod
    def fit(cls, df: pd.DataFrame) -> "H4Counts":
        return cls(root=_count_vector(df["H4"].tolist()), h3=_group_counts(df, ["H3"], "H4"))

    def prob(self, h3: int, alpha: float = H4_ALPHA_FIXED) -> np.ndarray:
        p = _smooth_root(self.root, alpha)
        p = _smooth_child(self.h3.get(_key((int(h3),))), p, alpha)
        return p

    def to_json(self) -> dict:
        return {"root": self.root.tolist(), "h3": _json_counts(self.h3)}

    @classmethod
    def from_json(cls, x: Mapping[str, object]) -> "H4Counts":
        return cls(_arr(x["root"]), _from_json_counts(x["h3"]))


def score_h2(df: pd.DataFrame, counts: H2Counts, alpha: float, depth: int) -> tuple[float, int]:
    loss = 0.0
    n = 0
    for r in df.itertuples(index=False):
        p = counts.prob(r.H1, r.W, r.T, r.PHASE, alpha, depth)
        loss += _safe_log2_prob(p[int(r.H2)])
        n += 1
    return loss, n


def score_h3(df: pd.DataFrame, counts: H3Counts, alpha: float) -> tuple[float, int]:
    loss = 0.0
    n = 0
    for r in df.itertuples(index=False):
        p = counts.prob(r.H1, r.W, alpha)
        loss += _safe_log2_prob(p[int(r.H3)])
        n += 1
    return loss, n


def score_h4(df: pd.DataFrame, counts: H4Counts, alpha: float = H4_ALPHA_FIXED) -> tuple[float, int]:
    loss = 0.0
    n = 0
    for r in df.itertuples(index=False):
        p = counts.prob(r.H3, alpha)
        loss += _safe_log2_prob(p[int(r.H4)])
        n += 1
    return loss, n


def select_h2_inner_cv(df: pd.DataFrame, alpha_grid: Sequence[float] = ALPHA_GRID, depths: Sequence[int] = H2_DEPTHS) -> tuple[dict, pd.DataFrame]:
    bifs = tuple(sorted(df["bif"].unique()))
    rows = []
    for depth in depths:
        for alpha in alpha_grid:
            total_loss = 0.0
            total_n = 0
            bif_losses = []
            for val_bif in bifs:
                tr = df[df["bif"] != val_bif]
                va = df[df["bif"] == val_bif]
                if va.empty or tr.empty:
                    continue
                c = H2Counts.fit(tr)
                l, n = score_h2(va, c, float(alpha), int(depth))
                total_loss += l; total_n += n; bif_losses.append(l / n)
            rows.append({
                "depth": int(depth), "alpha": float(alpha), "tokens": int(total_n),
                "token_loss": float(total_loss / total_n),
                "bif_mean_loss": float(np.mean(bif_losses)) if bif_losses else float("nan"),
                "inner_bifs": len(bif_losses),
            })
    grid = pd.DataFrame(rows).sort_values(["token_loss", "depth", "alpha"], ascending=[True, True, True]).reset_index(drop=True)
    best = grid.iloc[0].to_dict()
    return best, grid


def select_h3_inner_cv(df: pd.DataFrame, alpha_grid: Sequence[float] = ALPHA_GRID) -> tuple[dict, pd.DataFrame]:
    bifs = tuple(sorted(df["bif"].unique()))
    rows = []
    for alpha in alpha_grid:
        total_loss = 0.0
        total_n = 0
        bif_losses = []
        for val_bif in bifs:
            tr = df[df["bif"] != val_bif]
            va = df[df["bif"] == val_bif]
            if va.empty or tr.empty:
                continue
            c = H3Counts.fit(tr)
            l, n = score_h3(va, c, float(alpha))
            total_loss += l; total_n += n; bif_losses.append(l / n)
        rows.append({
            "alpha": float(alpha), "tokens": int(total_n),
            "token_loss": float(total_loss / total_n),
            "bif_mean_loss": float(np.mean(bif_losses)) if bif_losses else float("nan"),
            "inner_bifs": len(bif_losses),
        })
    grid = pd.DataFrame(rows).sort_values(["token_loss", "alpha"], ascending=[True, True]).reset_index(drop=True)
    best = grid.iloc[0].to_dict()
    return best, grid


@dataclass
class FoldSlotTables:
    fold: int
    train_bifs: tuple[str, ...]
    test_bifs: tuple[str, ...]
    h2_alpha: float
    h2_depth: int
    h3_alpha: float
    h4_alpha: float
    h2: H2Counts
    h3: H3Counts
    h4: H4Counts
    w2_event_sha256: str
    body_h4_event_sha256: str

    def prob_h2(self, h1: int, w: int, t: int, phase: str) -> np.ndarray:
        return self.h2.prob(h1, w, t, phase, self.h2_alpha, self.h2_depth)

    def prob_h3(self, h1: int, w: int) -> np.ndarray:
        return self.h3.prob(h1, w, self.h3_alpha)

    def prob_h4(self, h3: int) -> np.ndarray:
        return self.h4.prob(h3, self.h4_alpha)

    def to_json(self) -> dict:
        return {
            "schema": "V21_W2_SLOT_TABLES_V1",
            "fold": int(self.fold),
            "train_bifs": list(self.train_bifs),
            "test_bifs": list(self.test_bifs),
            "valid_total_widths": list(VALID_WIDTHS),
            "n_glyphs": N_GLYPHS,
            "h2": {"alpha": float(self.h2_alpha), "context_depth": int(self.h2_depth), "counts": self.h2.to_json()},
            "h3": {"alpha": float(self.h3_alpha), "model": "H1_EXACT_WIDTH", "counts": self.h3.to_json()},
            "h4": {"alpha": float(self.h4_alpha), "model": "BODY_SHARED_H3", "counts": self.h4.to_json()},
            "hashes": {"w2_training_events_sha256": self.w2_event_sha256, "body_h4_training_events_sha256": self.body_h4_event_sha256},
        }

    @classmethod
    def from_json(cls, x: Mapping[str, object]) -> "FoldSlotTables":
        h2 = x["h2"]; h3 = x["h3"]; h4 = x["h4"]
        return cls(
            fold=int(x["fold"]), train_bifs=tuple(x["train_bifs"]), test_bifs=tuple(x["test_bifs"]),
            h2_alpha=float(h2["alpha"]), h2_depth=int(h2["context_depth"]), h3_alpha=float(h3["alpha"]), h4_alpha=float(h4["alpha"]),
            h2=H2Counts.from_json(h2["counts"]), h3=H3Counts.from_json(h3["counts"]), h4=H4Counts.from_json(h4["counts"]),
            w2_event_sha256=str(x["hashes"]["w2_training_events_sha256"]), body_h4_event_sha256=str(x["hashes"]["body_h4_training_events_sha256"]),
        )


def save_fold_tables(path: Path, tables: FoldSlotTables) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(tables.to_json(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_fold_tables(path: Path) -> FoldSlotTables:
    return FoldSlotTables.from_json(json.loads(path.read_text(encoding="utf-8")))
