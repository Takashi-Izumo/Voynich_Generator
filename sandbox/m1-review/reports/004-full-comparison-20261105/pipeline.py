"""Sequential frozen audit/export/evaluation after successful full generation."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--checkout', type=Path, required=True)
    ap.add_argument('--models', type=Path, required=True)
    ap.add_argument('--historical', type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()
    stages = []

    def status(stage, state='RUNNING', error=None):
        (root / 'PIPELINE.json').write_text(json.dumps({'status': state, 'stage': stage,
                                                       'completed_stages': stages, 'error': error}, indent=2) + '\n')
        print(stage, state, flush=True)

    def execute(stage, cmd):
        status(stage)
        with (root / (stage + '.log')).open('w') as log:
            subprocess.run(cmd, cwd=args.checkout, stdout=log, stderr=subprocess.STDOUT, check=True)
        stages.append(stage)

    try:
        status('WAITING_GENERATION')
        while True:
            try:
                generation = json.loads((root / 'generated/STATUS.json').read_text())
            except json.JSONDecodeError:
                time.sleep(1)
                continue
            if generation['status'] == 'FAILED':
                raise RuntimeError('Generation failed; no audit/scoring will be run')
            if generation['status'] == 'GENERATED_NOT_AUDITED':
                if generation['completed_cases'] != 800:
                    raise ValueError('Full comparison is incomplete')
                break
            time.sleep(10)
        plan = str(root / 'plan/plan.json')
        cli = [sys.executable, '-m', 'experiments.m1_pf']
        execute('audit', cli + ['audit', '--plan', plan, '--generated', str(root / 'generated'), '--output', str(root / 'audit')])
        execute('historical', [sys.executable, str(root / 'summarize_full.py'), 'historical', '--root', str(root), '--historical', str(args.historical)])
        execute('export', cli + ['export', '--plan', plan, '--generated', str(root / 'generated'), '--output', str(root / 'anonymous')])
        execute('evaluate', cli + ['evaluate', '--plan', plan, '--inputs', str(root / 'anonymous'),
                                   '--models', str(args.models), '--output', str(root / 'evaluation'), '--jobs', '4', '--bootstrap', '10000'])
        execute('summarize', [sys.executable, str(root / 'summarize_full.py'), 'results', '--root', str(root)])
        status('COMPLETED', 'PASS')
    except BaseException as exc:
        status('STOPPED', 'FAILED', str(exc))
        raise


if __name__ == '__main__':
    main()
