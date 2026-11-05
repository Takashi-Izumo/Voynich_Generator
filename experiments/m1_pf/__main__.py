from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import ARMS


def main(argv=None):
    ap = argparse.ArgumentParser(description='M1 PF selection/rescue ablation; frozen v22.3 and jury v0.3')
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--bifolia', default='A:2,A:3,G:1')
    p.add_argument('--runs', default='91701')
    p.add_argument('--kind', choices=['smoke', 'development'], default='smoke')
    p.add_argument('--blinding-seed', type=int, default=20261104)
    p = sub.add_parser('generate')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reference', action='store_true')
    p.add_argument('--arm-order', default=','.join(ARMS))
    p = sub.add_parser('audit')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--generated', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--repeat', type=Path)
    p = sub.add_parser('export')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--generated', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('evaluate')
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--models', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--jobs', type=int, choices=range(1, 5), default=1)
    p.add_argument('--bootstrap', type=int, default=10000)
    a = ap.parse_args(argv)
    try:
        if a.command == 'plan':
            from .plan import create_plan
            result = create_plan(a.output, a.bifolia.split(','), [int(s) for s in a.runs.split(',')], a.blinding_seed, a.kind)
            result = {'plan_hash': result['plan_hash'], 'primary': result['primary']}
        elif a.command == 'generate':
            from .plan import generate
            result = {'generated': len(generate(a.plan, a.output, a.reference, a.arm_order.split(',')))}
        elif a.command == 'audit':
            from .audit import audit
            result = audit(a.plan, a.generated, a.output, a.repeat)
        elif a.command == 'export':
            from .evaluation import export
            result = {'exported_arms': export(a.plan, a.generated, a.output)['arms'], 'primary': 'J24.CAL'}
        else:
            from .evaluation import evaluate
            result = {'comparisons': list(evaluate(a.plan, a.inputs, a.models, a.output, a.jobs, a.bootstrap))}
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AssertionError) as exc:
        print('M1 stopped: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
