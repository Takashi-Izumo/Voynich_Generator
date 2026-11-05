"""Read-only source/scope inventory for PF design; never fit or generate a model."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def length_band(n):
    return "1-3" if n <= 3 else "4-6" if n <= 6 else "7+"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=Path(__file__).resolve().parents[4])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    sys.path.insert(0, str(checkout))
    from experiments.m1_pf.common import PACKAGE, file_hash
    from experiments.m1_pf.runtime import Runtime

    runtime = Runtime()  # Validates trusted inputs; no case_inputs/load_core/generate call.
    from fold_context import folds

    context = runtime.C
    tokens = context.T
    complete = set(context.bifs)
    strict_pf = tokens[tokens.bif.isin(complete) & tokens.strict_line & tokens.pf]
    checks = 0
    for _, group in strict_pf.groupby(["bif", "page", "locus", "segment_id"]):
        rows = list(group.sort_values("global_order").itertuples())
        capacity = int(rows[0].segment_capacity)
        remaining = capacity
        for i, row in enumerate(rows):
            assert int(row.segment_rstart) == remaining
            assert int(row.width) == runtime.engine.m.stable_width(row.glyphs)
            assert bool(row.is_segment_end) == (i == len(rows) - 1)
            remaining -= int(row.width)
            if i < len(rows) - 1:
                remaining -= 1
        assert remaining == 0
        checks += 1

    fold_rows = []
    for fi, test in enumerate(folds(context.bifs)):
        train = complete - set(test)
        pf = strict_pf[strict_pf.bif.isin(train)]
        ends = pf[pf.is_segment_end]
        ordinary = tokens[
            tokens.bif.isin(train) & tokens.strict_line
            & (tokens.para_line_raw >= 2) & ~tokens.raw_para_final
            & tokens.boundary_type.eq("LINE_END") & tokens.is_segment_end
        ]
        assert not set(pf.bif) & set(test)
        fold_rows.append({
            "outer_fold": fi,
            "excluded_bifolia": list(test),
            "training_bifolia": sorted(train),
            "pf_training_bifolia_with_events": int(ends.bif.nunique()),
            "pf_segments": int(len(ends)),
            "pf_word_starts": int(len(pf)),
            "pf_end_roles": dict(sorted(Counter(ends.role).items())),
            "pf_length_band_counts": dict(sorted(Counter(map(length_band, ends.length)).items())),
            "pf_physical_width_counts": dict(sorted(Counter(map(int, ends.width)).items())),
            "ordinary_line_end_prior_events": int(len(ordinary)),
        })

    relative_sources = [
        Path(runtime.engine.__file__),
        PACKAGE / "model/code/runtime_bootstrap.py",
        PACKAGE / "model/code/run_v22_3_stage3d.py",
        PACKAGE / "model/code/integrated_sampler_v21.py",
    ]
    for name in ["entry_fast_sampler", "close1_sampler", "sel42_selectors", "fold_context",
                 "sel42_data", "v19r_rb3_pw2_close1", "bti2_patch_sampler"]:
        relative_sources.append(Path(sys.modules[name].__file__))
    output = {
        "schema_version": 1,
        "purpose": "PF proposal design: existing source and training-scope inventory only",
        "source_scope": "parent strict_line, pf, complete bifolia; all four pages of external16",
        "new_parameter_fit": False,
        "new_generation": False,
        "new_judge_prediction_or_scoring": False,
        "runtime_inputs": runtime.input_snapshot,
        "source_data_hashes": context.input_hashes,
        "source_hashes": {str(p.relative_to(checkout)): file_hash(p) for p in sorted(set(relative_sources))},
        "source_pf_segments_capacity_checked": checks,
        "source_pf_segments": int(strict_pf.is_segment_end.sum()),
        "physical_width_profile": {name: int(runtime.engine.m.WIDTH[index])
                                   for name, index in runtime.engine.m.G2I.items()},
        "outer_folds": fold_rows,
        "limitations": [
            "Counts overlap between outer folds and are not independent samples.",
            "Training counts use parent strict_line, not the evaluation target-only mask.",
            "The corpus was already used for development; this is not independent confirmation.",
        ],
    }
    # Never replace an earlier inventory or result.
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "fold_pf_segments": [r["pf_segments"] for r in fold_rows],
                      "capacity_checks": checks, "new_generation": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
