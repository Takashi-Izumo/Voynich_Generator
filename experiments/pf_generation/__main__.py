from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description='PF design 007 study one; frozen v22.3 and judge v0.3')
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--bifolia', default='A:2,A:3,G:1')
    p.add_argument('--runs', default='91701')
    p.add_argument('--kind', choices=['smoke', 'development'], default='smoke')
    p.add_argument('--identity', action='store_true')
    for command in ['generate', 'audit', 'export', 'evaluate', 'summarize']:
        p = sub.add_parser(command)
        p.add_argument('--plan', type=Path, required=True)
        p.add_argument('--output', type=Path, required=True)
        if command in ('audit', 'export', 'summarize'):
            p.add_argument('--generated', type=Path, required=True)
        if command == 'generate':
            p.add_argument('--reverse', action='store_true')
        elif command == 'audit':
            p.add_argument('--repeat', type=Path)
        elif command == 'evaluate':
            p.add_argument('--inputs', type=Path, required=True)
            p.add_argument('--models', type=Path, required=True)
            p.add_argument('--jobs', type=int, choices=range(1, 5), default=1)
            p.add_argument('--bootstrap', type=int, default=10000)
    a = ap.parse_args(argv)
    try:
        if a.command == 'plan':
            from .plan import create_plan
            plan = create_plan(a.output, a.bifolia.split(','), [int(s) for s in a.runs.split(',')], a.kind, a.identity)
            result = dict(plan_hash=plan['plan_hash'], laws=list(plan['laws']))
        elif a.command == 'generate':
            from .plan import generate
            result = dict(generated=len(generate(a.plan, a.output, a.reverse)))
        elif a.command == 'audit':
            from .audit import audit
            report = audit(a.plan, a.generated, a.output, a.repeat)
            result = {k: report[k] for k in ['status', 'cases', 'base_reference_checked', 'repeat_checked']}
        elif a.command == 'export':
            from .evaluation import export
            result = dict(exported_arms=export(a.plan, a.generated, a.output)['arms'])
        elif a.command == 'evaluate':
            from .evaluation import evaluate
            result = dict(comparisons=list(evaluate(a.plan, a.inputs, a.models, a.output, a.jobs, a.bootstrap)))
        else:
            from .diagnostics import summarize
            result = summarize(a.plan, a.generated, a.output)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, AssertionError) as exc:
        print('PF generation stopped: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
