"""Reproduce the recorded failure on the original, sealed source and inputs.

Run from any directory with this repository's environment and a NEW output path:
  python reproduce_failure.py --output /workspace/voynich-results/pf-failure-repro-new

The expected result on the recorded source is the original AssertionError.
This is a diagnostic case, not a replacement or continuation of the 800-case run.
"""
from pathlib import Path
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output must be a new path')
    root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(root))
    from experiments.pf_generation.plan import load_plan
    from experiments.pf_generation.runtime import Runtime
    plan = load_plan(root/'sandbox/m1-review/reports/016-controls-and-main-comparison-20261105/full-plan/plan.json')
    assert plan['plan_hash'] == '262097f1db82c4c53c2f2b8ebf84ddee227c8ebd2264fb3f56ab02a42f131c17'
    Runtime(plan).generate('A:3', 91711, 'PF_GATE_LENGTH', args.output)


if __name__ == '__main__':
    main()
