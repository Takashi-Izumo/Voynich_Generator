"""Independent execution of repair022; never writes product source or requests."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time

ROOT=Path('/workspace/voynich-results/m1-v2-independent-20261105/checkout')
OUT=Path('/workspace/voynich-results/pf-surface-independent-20261106')
IMPL=ROOT/'sandbox/m1-review/implementation/020-pf-surface-commit-fix'
OLD_CONTROL=Path('/workspace/voynich-results/pf-controls-independent-20261105/full-generated')
sys.path.insert(0,str(ROOT))

def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def run(name,args,expected=0):
    t=time.monotonic()
    with (OUT/(name+'.log')).open('w') as f:
        result=subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    r=dict(name=name,command=[sys.executable,*map(str,args)],returncode=result.returncode,expected_returncode=expected,wall_seconds=time.monotonic()-t)
    write(OUT/(name+'.result.json'),r);print(json.dumps(r),flush=True)
    assert result.returncode==expected,(name,'see log')
    return r
def cli(name,cmd,kind,**extras):
    args=['-m','experiments.pf_generation',cmd,'--plan',OUT/(kind+'-plan/plan.json')]
    for key,val in extras.items():args.extend(['--'+key.replace('_','-'),val])
    return run(name,args)

def fixed_and_preserved(plan):
    from experiments.pf_generation.audit import verified_records,semantic_case,read_jsonl
    from experiments.pf_generation.common import digest
    records=verified_records(plan,OUT/'forward')
    case=records['PF_GATE_LENGTH','A:3',91711]
    requests=read_jsonl(case/'requests.jsonl.gz');commits=read_jsonl(case/'surface_commits.jsonl.gz')
    request=next(r for r in requests if r['proposal_id']==630)
    current=next(r for r in commits if r['proposal_id']==630)
    following=next(r for r in requests if r['proposal_id']==631)
    assert current['prev_terminal_after']==following['prev_terminal']==12
    assert request['pfgen_terminal_precommit']['selected_terminal']==12
    assert request['pfgen_terminal_precommit']['before_semantic_surface_commit'] is True
    md=read(case/'MECHANICAL.json');assert md['terminal_mismatches']==0
    write(OUT/'fixed-case.json',dict(status='PASS',arm='PF_GATE_LENGTH',bif='A:3',run=91711,
        locus=current['locus'],proposal_id=630,following_proposal_id=631,
        semantic_terminal=current['prev_terminal_after'],next_request_terminal=following['prev_terminal'],
        visible_surface_sha256=digest(current['surface']),receipt=request['pfgen_terminal_precommit'],
        original_terminal_assert_passed=True,raw_word_published=False))
    prior=Path('/workspace/voynich-results/pf-r2-independent-20261105/forward')
    # The previous R2 review's literal normal paths must remain exactly unchanged.
    candidates=[prior]
    available=[]
    for root in candidates:
        if (root/'manifest.json').exists():available.append(root)
    # Historical BASE from the aborted main is an independently generated fallback.
    old_main=Path('/workspace/voynich-results/pf-first-full-comparison-20261105/generated')
    checks=[]
    for (arm,bif,seed),path in records.items():
        if seed!=91701:continue
        previous=None
        for root in available:
            manifest=read(root/'manifest.json')
            entry=next((x for x in manifest['records'] if (x['arm'],x['bif'],x['run'])==(arm,bif,seed)),None)
            if entry:previous=root/entry['path'];break
        if previous is None and arm=='BASE':
            for journal in (old_main/'workers').glob('*-journal.jsonl'):
                for line in journal.read_text().splitlines():
                    entry=json.loads(line)
                    if (entry.get('arm'),entry.get('bif'),entry.get('run'))==(arm,bif,seed):previous=old_main/entry['path'];break
                if previous is not None:break
        if previous is not None:
            assert semantic_case(path)==semantic_case(previous),(arm,bif,seed)
            checks.append(dict(arm=arm,bif=bif,run=seed,semantic_state_rng_exact=True))
    assert len(checks)==12
    write(OUT/'normal-preservation.json',dict(status='PASS',cases=checks,prior_roots=[str(p) for p in available]))

def terminal_probes(plan):
    from experiments.pf_generation.audit import audit,verified_records
    from experiments.pf_generation.evaluation import audited
    from experiments.pf_generation.common import file_hash
    from experiments.pf_generation.tests.run_trace_probes import rows,write_rows
    checks=[]
    for mode in ['remove_receipt_zero_count','stale_next_request','forged_commit_chain']:
        root=OUT/'terminal-probes-rechecked'/mode;root.mkdir(parents=True)
        for src,label in [('forward','forward'),('reverse','reverse')]:
            target=root/label;shutil.copytree(OUT/src,target)
            manifest=read(target/'manifest.json')
            entry=next(x for x in manifest['records'] if (x['arm'],x['bif'],x['run'])==('PF_GATE_LENGTH','A:3',91711))
            case=target/entry['path'];requests=rows(case/'requests.jsonl.gz');commits=rows(case/'surface_commits.jsonl.gz')
            if mode=='remove_receipt_zero_count':
                for row in requests:row.pop('pfgen_terminal_precommit',None)
                final=read(case/'PF_GENERATION_FINAL.json');final['terminal_precommits']=0;write(case/'PF_GENERATION_FINAL.json',final)
            else:
                next(r for r in requests if r['proposal_id']==631)['prev_terminal']=10
                if mode=='forged_commit_chain':
                    next(r for r in commits if r['proposal_id']==630)['prev_terminal_after']=10
                    next(r for r in commits if r['proposal_id']==631)['prev_terminal_before']=10
            write_rows(case/'requests.jsonl.gz',requests);write_rows(case/'surface_commits.jsonl.gz',commits)
            for name in entry['files']:entry['files'][name]=file_hash(case/name)
            write(target/'manifest.json',manifest);verified_records(plan,target)
        try:audit(OUT/'smoke-plan/plan.json',root/'forward',root/'audit',root/'reverse')
        except (ValueError,AssertionError) as exc:
            assert not (root/'forward/AUDIT.json').exists()
            try:audited(OUT/'smoke-plan/plan.json',root/'forward')
            except (ValueError,AssertionError,OSError):pass
            else:raise AssertionError('Failed terminal audit accepted downstream')
            checks.append(dict(mode=mode,rejected=True,reason=str(exc),both_orders_tampered=True,seal_revoked=True,stale_pass_rejected=True))
        else:raise AssertionError('Accepted terminal forgery '+mode)
    write(OUT/'terminal-probes.json',dict(status='PASS',checks=checks))

def control_cli():
    from experiments.pf_controls.common import seal,unseal,file_hash,file_inventory
    from experiments.pf_controls.plan import create
    create(OUT/'control-plan',['A:2'])
    assert read(OUT/'control-plan/plan.json')==read(IMPL/'control-cli-plan.json')
    for command in ['generate','audit','export']:
        args=['-m','experiments.pf_controls',command,'--plan',OUT/'control-plan/plan.json','--output',OUT/('control-'+command)]
        if command!='generate':args.extend(['--generated',OUT/'control-generate'])
        run('control-'+command,args)
    args=['-m','experiments.pf_controls','verify-export','--plan',OUT/'control-plan/plan.json','--generated',OUT/'control-generate','--exported',OUT/'control-export']
    run('control-real-cli',args)
    fresh=unseal(read(OUT/'control-generate/A_2.json'));old=unseal(read(OLD_CONTROL/'A_2.json'))
    for d in [fresh,old]:
        d.pop('plan_sha256');d.pop('sha256')
    assert fresh==old
    write(OUT/'control-preservation.json',dict(status='PASS',base_snapshot_donors_selections_exact=True,donors=len(fresh['donors']),events=len(fresh['snapshots']),only_plan_binding_differs=True))
    bad=OUT/'control-wrong-key';shutil.copytree(OUT/'control-export',bad)
    key=next(bad.glob('*/answer_key.jsonl'));keys=[json.loads(x) for x in key.read_text().splitlines()]
    keys[0]['truth']='B' if keys[0]['truth']=='A' else 'A';key.write_text(''.join(json.dumps(x)+'\n' for x in keys))
    manifest=unseal(read(bad/'EXPORT.json'));manifest.pop('sha256');manifest['files']=file_inventory(bad,('EXPORT.json',));write(bad/'EXPORT.json',seal(manifest))
    run('control-real-cli-wrong-key',[*args[:-1],bad],expected=1)
    assert 'Export assignment/text/key/diagnostic mismatch' in (OUT/'control-real-cli-wrong-key.log').read_text()

def main():
    m=read(IMPL/'MANIFEST.json')
    for item in m['files']:
        b=(ROOT/item['path']).read_bytes();assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256'],item['path']
    from experiments.pf_generation.common import frozen_sources,implementation_sources,digest
    assert digest(frozen_sources())==m['frozen_sources_sha256']
    assert digest(implementation_sources())==m['generation_sources_sha256']
    write(OUT/'manifest-check.json',dict(status='PASS',source_head='43a6895',files=len(m['files']),frozen_files=len(frozen_sources()),source_files=len(implementation_sources())))
    suites={'pf':'experiments/pf_generation/tests','controls':'experiments/pf_controls/tests','m1':'experiments/m1_pf/tests','judges':'judges/tests'}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(run,'unit-'+k,['-m','unittest','discover','-s',v,'-v']) for k,v in suites.items()]
        for f in futures:f.result()
    from experiments.pf_generation.plan import create_plan,load_plan
    smoke=create_plan(OUT/'smoke-plan',['A:2','A:3','G:1'],[91701,91711])
    identity=create_plan(OUT/'identity-plan',['A:2','A:3','G:1'],[91701],identity=True)
    old=read(ROOT/'sandbox/m1-review/reports/016-controls-and-main-comparison-20261105/full-plan/plan.json')
    full=create_plan(OUT/'full-plan',old['bifolia'],old['runs'],kind='development')
    for p,label in [(smoke,'smoke'),(identity,'identity'),(full,'full')]:assert p==read(IMPL/(label+'-plan/plan.json'))
    ignored={'plan_hash','implementation_sources','surface_commit_policy'}
    assert {k:v for k,v in full.items() if k not in ignored}=={k:v for k,v in old.items() if k not in ignored}
    try:load_plan(ROOT/'sandbox/m1-review/reports/016-controls-and-main-comparison-20261105/full-plan/plan.json')
    except ValueError as exc:old_rejection=str(exc)
    else:raise AssertionError('Old source plan accepted')
    write(OUT/'plan-check.json',dict(status='PASS',fresh_fits_equal_implementation=True,old_plan_rejected=old_rejection,
        full_plan_hash=full['plan_hash'],laws_cohort_seeds_models_masks_runtime_unchanged=True,planned_main_pages=800))
    commands=[('forward','smoke',[]),('reverse','smoke',['--reverse']),('identity','identity',[])]
    with ThreadPoolExecutor(max_workers=3) as pool:
        fs=[pool.submit(run,name,['-m','experiments.pf_generation','generate','--plan',OUT/(kind+'-plan/plan.json'),'--output',OUT/name,*extra]) for name,kind,extra in commands]
        for f in fs:f.result()
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(cli,'normal-audit','audit','smoke',generated=OUT/'forward',repeat=OUT/'reverse',output=OUT/'audit'),
            pool.submit(cli,'identity-audit','audit','identity',generated=OUT/'identity',output=OUT/'identity-audit')]
        for f in fs:f.result()
    fixed_and_preserved(smoke)
    terminal_probes(smoke)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[]
        for module,label in [('run_trace_probes','r1-probes'),('run_context_probes','r2-probes')]:
            fs.append(pool.submit(run,label,['-m','experiments.pf_generation.tests.'+module,'--plan',OUT/'smoke-plan/plan.json','--generated',OUT/'forward','--repeat',OUT/'reverse','--output',OUT/label]))
        for f in fs:f.result()
    # This prescribed probe temporarily mutates an extracted input: no other job runs here.
    run('required-probes',['-m','experiments.pf_generation.tests.run_artifact_probes','--plan',OUT/'smoke-plan/plan.json','--generated',OUT/'forward','--repeat',OUT/'reverse','--output',OUT/'required-probes'])
    control_cli()
    unit_counts={k:int(re.search(r'Ran (\d+) tests?',(OUT/('unit-'+k+'.log')).read_text()).group(1)) for k in suites}
    assert sum(unit_counts.values())==174
    write(OUT/'REVIEW_RESULT.json',dict(status='PASS_INDEPENDENT_MECHANISM_RECHECK',source_head='43a6895',
        unit_counts=unit_counts,fresh_pages=60,fixed_case_reproduced_and_corrected=True,
        actual_cli_and_resealed_wrong_key_checked=True,normal_identity_order_state_rng_checked=True,
        capability_status='CAPABILITY_NOT_VERIFIED_UNCHANGED',new_jury_donors='DESIGN_ONLY',full_plan_hash=full['plan_hash']))
    print('INDEPENDENT REPAIR REVIEW PASS',flush=True)

if __name__=='__main__':main()
