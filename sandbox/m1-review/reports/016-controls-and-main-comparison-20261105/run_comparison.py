"""Parallel driver for a sealed PF plan; generation only, no scoring or refit.

Invoke after the separately documented capability gate has passed.
Each worker owns disjoint case directories and a private progress journal.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time


def jobs_for(plan):
    return [(a,b,s) for a in (*plan['arms'],'REFERENCE') for b in plan['bifolia'] for s in plan['runs']]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkout',type=Path,required=True)
    ap.add_argument('--plan',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--workers',type=int,choices=range(1,5),default=4)
    ap.add_argument('--purpose',choices=['smoke','main'],required=True)
    ap.add_argument('--capability-review',type=Path)
    ap.add_argument('--worker-id',type=int)
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    args.checkout=args.checkout.resolve();args.plan=args.plan.resolve();args.output=args.output.resolve()
    sys.path.insert(0,str(args.checkout))
    from experiments.pf_generation.plan import load_plan
    from experiments.pf_generation.common import file_hash,write_json,model_dir
    plan=load_plan(args.plan)
    jobs=jobs_for(plan)
    assert len(jobs)==len(set(jobs))
    partitions=[jobs[i::args.workers] for i in range(args.workers)]
    assert sorted(j for part in partitions for j in part)==sorted(jobs)
    if args.dry_run:
        print(json.dumps(dict(plan_hash=plan['plan_hash'],cases=len(jobs),per_worker=list(map(len,partitions)),
                              arms=[*plan['arms'],'REFERENCE'],generation_started=False)),flush=True)
        return 0
    capability_hash=None
    if args.purpose=='smoke':
        if plan['kind']!='smoke' or len(jobs)>12:
            raise ValueError('Orchestrator smoke is limited to a smoke plan with at most 12 pages')
    else:
        if args.capability_review is None:
            raise ValueError('Main comparison requires the completed independent capability review')
        args.capability_review=args.capability_review.resolve()
        review=json.loads(args.capability_review.read_text())
        expected_channels=['ATOM.PARA_END/length_width','ATOM.PARA_END/terminal','ATOM.PARA_END/space_T_H1']
        if not (review.get('schema_version')==1 and review.get('status')=='PASS_CAPABILITY_REVIEW'
                and review.get('comparison_plan_hash')==plan['plan_hash']
                and review.get('model_set_hash')==plan['required_model_set_hash']
                and review.get('required_channels')==expected_channels
                and all(review.get('channel_results',{}).get(c,{}).get('status')=='PASS' for c in expected_channels)):
            raise ValueError('Capability review does not release this plan and its required channels')
        capability_hash=file_hash(args.capability_review)
    if args.worker_id is not None:
        assert 0<=args.worker_id<args.workers
        from experiments.pf_generation.runtime import Runtime
        runtime=Runtime(plan)
        journal=args.output/'workers'/f'{args.worker_id}.jsonl'
        with journal.open('x') as log:
            for arm,bif,run in partitions[args.worker_id]:
                if (args.output/'STOP').exists():return 3
                dest=args.output/arm/f'run{run}'/model_dir(arm)/bif.replace(':','_')
                try:
                    runtime.generate(bif,run,arm,dest)
                    record=dict(arm=arm,bif=bif,run=run,path=str(dest.relative_to(args.output)),
                                files={p.name:file_hash(p) for p in sorted(dest.iterdir()) if p.is_file()})
                    log.write(json.dumps(record,sort_keys=True)+'\n');log.flush();os.fsync(log.fileno())
                except Exception as exc:
                    (args.output/'STOP').touch(exist_ok=True)
                    write_json(args.output/'workers'/f'{args.worker_id}-failure.json',
                               dict(arm=arm,bif=bif,run=run,error=str(exc)))
                    raise
        return 0
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'workers').mkdir()
    write_json(args.output/'plan.json',plan)
    write_json(args.output/'STATUS.json',dict(status='RUNNING',plan_hash=plan['plan_hash']))
    write_json(args.output/'ORCHESTRATOR.json',dict(driver_sha256=file_hash(Path(__file__)),
               workers=args.workers,partition='canonical_jobs[i::workers]',cases=len(jobs),
               purpose=args.purpose,capability_review_sha256=capability_hash))
    processes=[];handles=[];failure=None
    try:
        for i in range(args.workers):
            handle=(args.output/'workers'/f'{i}.log').open('x');handles.append(handle)
            cmd=[sys.executable,str(Path(__file__).resolve()),'--checkout',str(args.checkout),
                 '--plan',str(args.plan),'--output',str(args.output),'--workers',str(args.workers),'--worker-id',str(i),
                 '--purpose',args.purpose]
            if args.capability_review is not None:cmd.extend(['--capability-review',str(args.capability_review)])
            processes.append(subprocess.Popen(cmd,cwd=args.checkout,stdout=handle,stderr=subprocess.STDOUT))
        last_print=0.
        while any(p.poll() is None for p in processes):
            bad=[(i,p.returncode) for i,p in enumerate(processes) if p.poll() not in (None,0)]
            if bad and failure is None:
                failure=str(bad);(args.output/'STOP').touch(exist_ok=True)
            if time.monotonic()-last_print>=20:
                completed=sum(len(p.read_text().splitlines()) for p in (args.output/'workers').glob('*.jsonl'))
                print(json.dumps(dict(completed=completed,total=len(jobs),stopping=failure is not None)),flush=True)
                last_print=time.monotonic()
            time.sleep(1)
        if any(p.returncode!=0 for p in processes):
            raise RuntimeError('Worker failure: '+str([(i,p.returncode) for i,p in enumerate(processes) if p.returncode!=0]))
        records=[json.loads(line) for p in sorted((args.output/'workers').glob('*.jsonl'))
                 for line in p.read_text().splitlines()]
        lookup={(r['arm'],r['bif'],r['run']):r for r in records}
        assert len(records)==len(lookup)==len(jobs) and set(lookup)==set(jobs)
        for record in records:
            dest=args.output/record['path']
            assert {p.name for p in dest.iterdir() if p.is_file()}==set(record['files'])
            assert all(file_hash(dest/name)==expected for name,expected in record['files'].items())
        load_plan(args.plan)
        if capability_hash is not None:
            assert file_hash(args.capability_review)==capability_hash,'Capability review changed during generation'
        write_json(args.output/'manifest.json',dict(plan_hash=plan['plan_hash'],records=[lookup[j] for j in jobs]))
        write_json(args.output/'STATUS.json',dict(status='GENERATED_NOT_AUDITED',completed_cases=len(records),
                                                  plan_hash=plan['plan_hash']))
        print(json.dumps(dict(generated=len(records),status='GENERATED_NOT_AUDITED')),flush=True)
        return 0
    except BaseException as exc:
        (args.output/'STOP').touch(exist_ok=True)
        # Workers check STOP between cases. Preserve their partial evidence.
        while any(p.poll() is None for p in processes):time.sleep(1)
        write_json(args.output/'STATUS.json',dict(status='FAILED',error=str(exc),plan_hash=plan['plan_hash']))
        raise
    finally:
        for handle in handles:handle.close()


if __name__=='__main__':raise SystemExit(main())
