"""Parallel orchestration only; use the frozen M1 Runtime without modifying it."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse
import hashlib
import json
import multiprocessing as mp
import sys

RUNTIME = PLAN = OUTPUT = STOP = None


def init_worker(checkout, plan_path, output, stop):
    global RUNTIME, PLAN, OUTPUT, STOP
    sys.path.insert(0, checkout)
    from experiments.m1_pf.plan import load_plan
    from experiments.m1_pf.runtime import Runtime
    PLAN = load_plan(plan_path)
    RUNTIME = Runtime()
    if RUNTIME.input_snapshot != PLAN['runtime_inputs']:
        raise ValueError('Worker inputs differ from sealed plan')
    OUTPUT, STOP = Path(output), stop


def generate_bifolium(bif):
    from experiments.m1_pf.common import file_hash, model_dir, write_json
    records = []
    progress = OUTPUT / 'workers' / (bif.replace(':', '_') + '.json')
    try:
        for arm in tuple(PLAN['arms']) + ('REFERENCE',):
            directory = model_dir(arm) if arm != 'REFERENCE' else 'HerbalA_v22_3_M1_REFERENCE'
            for run in PLAN['runs']:
                if STOP.is_set():
                    raise RuntimeError('Stopped because another worker failed')
                dest = OUTPUT / arm / f'run{run}' / directory / bif.replace(':', '_')
                md = RUNTIME.generate(bif, run, arm, dest)
                records.append(dict(arm=arm, bif=bif, run=run, path=str(dest.relative_to(OUTPUT)),
                                    files={p.name: file_hash(p) for p in sorted(dest.iterdir()) if p.is_file()}))
                write_json(progress, dict(status='RUNNING', bif=bif, records=records))
                print(f'GEN {arm} {bif} {run} {md["generated_rows_sha256"][:12]}', flush=True)
    except BaseException as exc:
        STOP.set()
        write_json(progress, dict(status='FAILED', bif=bif, error=str(exc), records=records))
        raise
    write_json(progress, dict(status='COMPLETE', bif=bif, records=records))
    return records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--checkout', type=Path, required=True)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    checkout, root = args.checkout.resolve(), args.root.resolve()
    sys.path.insert(0, str(checkout))
    from experiments.m1_pf.plan import load_plan
    from experiments.m1_pf.common import write_json
    plan_path = root / 'plan/plan.json'
    plan = load_plan(plan_path)
    study = json.loads((root / 'study_protocol.json').read_text())
    own_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if study['plan_hash'] != plan['plan_hash'] or study['orchestrator_sha256'] != own_hash:
        raise ValueError('Study protocol or orchestration code changed')
    if args.workers != study['generation_workers']:
        raise ValueError('Worker count differs from protocol')
    out = root / 'generated'
    out.mkdir(exist_ok=False)
    (out / 'workers').mkdir()
    write_json(out / 'plan.json', plan)
    expected = len(plan['bifolia']) * len(plan['runs']) * 4
    write_json(out / 'STATUS.json', dict(status='RUNNING', plan_hash=plan['plan_hash'],
                                        expected_cases=expected, orchestrator_sha256=own_hash))
    ctx = mp.get_context('spawn')
    stop = ctx.Event()
    records = []
    try:
        with ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx,
                                 initializer=init_worker,
                                 initargs=(str(checkout), str(plan_path), str(out), stop)) as pool:
            futures = [pool.submit(generate_bifolium, bif) for bif in plan['bifolia']]
            for future in as_completed(futures):
                records.extend(future.result())
                print(f'COMPLETED_BIFOLIA {len(records) // (4 * len(plan["runs"]))}/{len(plan["bifolia"])}', flush=True)
    except BaseException as exc:
        stop.set()
        write_json(out / 'STATUS.json', dict(status='FAILED', plan_hash=plan['plan_hash'],
                                            error=str(exc), complete_bifolium_records=len(records),
                                            orchestrator_sha256=own_hash))
        raise
    arm_order = {a: i for i, a in enumerate(tuple(plan['arms']) + ('REFERENCE',))}
    bif_order = {b: i for i, b in enumerate(plan['bifolia'])}
    run_order = {s: i for i, s in enumerate(plan['runs'])}
    records.sort(key=lambda r: (arm_order[r['arm']], bif_order[r['bif']], run_order[r['run']]))
    keys = {(r['arm'], r['bif'], r['run']) for r in records}
    if len(records) != expected or len(keys) != expected:
        raise AssertionError('Incomplete/duplicate full comparison')
    write_json(out / 'manifest.json', dict(plan_hash=plan['plan_hash'], records=records))
    write_json(out / 'STATUS.json', dict(status='GENERATED_NOT_AUDITED', plan_hash=plan['plan_hash'],
                                        completed_cases=len(records), orchestrator_sha256=own_hash))
    print(json.dumps({'generated': len(records), 'plan_hash': plan['plan_hash']}), flush=True)


if __name__ == '__main__':
    main()
