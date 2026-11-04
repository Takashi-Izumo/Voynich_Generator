from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def main(argv=None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if raw and raw[0] == 'v03':
        from .v03.cli import main as v03_main
        return v03_main(raw[1:])
    parser = argparse.ArgumentParser(description='Voynich visible-input judge panel (research baseline)')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('validate', help='validate blind JSONL inputs without scoring')
    p.add_argument('--input', type=Path, required=True)
    p = sub.add_parser('predict', help='seal predictions; does not accept/read an answer key')
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('score', help='open answer key after predictions have been sealed')
    p.add_argument('--predictions', type=Path, required=True)
    p.add_argument('--key', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--bootstrap', type=int, default=5000)
    p = sub.add_parser('export-v223', help='optional adapter using verified v22.3 runtime')
    p.add_argument('--package', type=Path, default=Path(__file__).resolve().parents[1]/'HerbalA_v22_3_20260921')
    p.add_argument('--generated-root', type=Path, required=True)
    p.add_argument('--model-dir', default='HerbalA_v22_3_STAGE3D_R1_CANDIDATE')
    p.add_argument('--run', type=int, action='append', required=True)
    p.add_argument('--bif', action='append')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--blinding-seed', type=int, default=20261104)
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            from .schema import read_jsonl, validate_case
            from .contest import unique, unique_trials
            cases = read_jsonl(args.input)
            unique(cases)
            for case in cases:
                validate_case(case)
            unique_trials(cases)
            print(json.dumps({'valid': True, 'sets': len(cases)}))
        elif args.command == 'predict':
            from .contest import run_predict
            rows = run_predict(args.input, args.output)
            print(json.dumps({'sealed': True, 'sets': len(rows), 'output': str(args.output)}))
        elif args.command == 'score':
            from .contest import run_score
            print(json.dumps(run_score(args.predictions, args.key, args.output, args.bootstrap), ensure_ascii=False))
        else:
            from .v223 import export
            print(json.dumps({'exported': export(args.package, args.generated_root, args.model_dir, args.run, args.bif, args.output, args.blinding_seed)}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f'judges: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
