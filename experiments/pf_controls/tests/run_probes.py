"""Real artifact probes. All mutations are copies; the source tree is never edited."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import shutil
import time

from unittest.mock import patch
from experiments.pf_controls.common import digest, file_inventory, read, seal, write_json
from experiments.pf_controls.plan import load
from experiments.pf_controls.pipeline import audit, audited, export, verify_export
from experiments.pf_controls.replay import Runtime
import experiments.pf_controls.replay as replay


def run(plan,generated,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    generated=Path(generated);p=audited(plan,generated)
    name=p['bifolia'][0].replace(':','_')+'.json'
    original=read(generated/name)
    checks=[]

    def missing_all(c):c['donors']=[]
    def missing_one(c):c['donors'].pop()
    def duplicate(c):c['donors'][-1]=deepcopy(c['donors'][-2])
    def context(c):
        d=c['donors'][0];d['event']=1
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
    def typed(c):
        d=c['donors'][0];d['branch']=0.0
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
    def request(c):
        d=c['donors'][0];d['requests'].pop()
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
    def misbound(c):
        d=c['donors'][0];d['snapshot_sha256']=c['snapshots'][-1]['sha256']
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
    def selection(c):c['selections'][0]['branch']=63 if c['selections'][0]['branch']!=63 else 62
    def support(c):
        d=c['donors'][0];d['support_violations']=1
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
    def main_rng(c):
        c['base']['final']['main_rng']['state']['state']+=1
        c['base_sha256']=c['ordinary_base_sha256']=digest(c['base'])
    def inner_request(c):
        d=c['donors'][0];d['requests'][0]['locus']=c['snapshots'][-1]['locus']
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
    for label,mutate in [('missing_all',missing_all),('missing_one',missing_one),('duplicate',duplicate),
                         ('existing_event_context',context),('float_branch_id',typed),('missing_request',request),
                         ('snapshot_misbind',misbound),('selection_changed',selection),('support_violation',support),
                         ('inner_request_context',inner_request),('main_rng_forged_receipt',main_rng)]:
        root=output/label
        shutil.copytree(generated,root)
        c=deepcopy(original);mutate(c)
        write_json(root/name,seal({k:v for k,v in c.items() if k!='sha256'}))
        write_json(root/'manifest.json',seal(dict(plan_sha256=p['sha256'],files=file_inventory(root,('manifest.json','AUDIT.json')))))
        stale=False
        try:audited(plan,root)
        except (ValueError,FileNotFoundError):stale=True
        if not stale:raise AssertionError('Stale PASS accepted: '+label)
        t=time.monotonic()
        try:audit(plan,root,output/(label+'-audit'))
        except ValueError as exc:
            if (root/'AUDIT.json').exists():raise AssertionError('Failed audit left a PASS')
            checks.append(dict(probe=label,rejected=True,stale_pass_rejected=True,seal_revoked=True,
                               reason=str(exc),seconds=time.monotonic()-t))
        else:raise AssertionError('Tampered artifact accepted: '+label)
        print('REJECT',label,flush=True)
        shutil.rmtree(root)

    bad=deepcopy(p);next(iter(bad['proxies'].values()))['known3_used']=True
    bad=seal({k:v for k,v in bad.items() if k!='sha256'});write_json(output/'target-leak-plan.json',bad)
    try:load(output/'target-leak-plan.json')
    except ValueError as exc:checks.append(dict(probe='target_known3_fit',rejected=True,reason=str(exc)))
    else:raise AssertionError('Target leakage plan accepted')

    export(plan,generated,output/'export-original')
    from judges.v03.protocol import read_jsonl,write_jsonl
    for label in ('key-leak','typed-input','wrong-key'):
        copied=output/label
        shutil.copytree(output/'export-original',copied)
        target=next(copied.glob('*/answer_key.jsonl' if label=='wrong-key' else '*/inputs.jsonl'))
        records=read_jsonl(target)
        if label=='key-leak':records[0]['truth']='A'
        elif label=='typed-input':records[0]['seed']=float(records[0]['seed'])
        else:records[0]['truth']='B' if records[0]['truth']=='A' else 'A'
        write_jsonl(target,records)
        m=read(copied/'EXPORT.json');m['files']=file_inventory(copied,('EXPORT.json',))
        write_json(copied/'EXPORT.json',seal({k:v for k,v in m.items() if k!='sha256'}))
        try:verify_export(plan,generated,copied)
        except ValueError as exc:checks.append(dict(probe=label+'_resealed_export',rejected=True,reason=str(exc)))
        else:raise AssertionError('Resealed export mutation accepted: '+label)

    # Exercise finally restoration with an actual mid-PF exception and actual live-state contamination.
    rt=Runtime();rb,e=rt.rb,rt.engine
    before=rb.PatchSampler,rb.PatchMapState,rb.build_bt_leafex,rb.patch_generate,e.complete_segment
    class_before=digest([(c.__name__,replay.class_control_payload(c)) for c in rt.active.V223F1LFLengthTerminalSampler.__mro__ if c is not object])
    for label,effect in [('injected_failure',RuntimeError('probe PF exception')),
                         ('route_contamination',None),('request_counter_contamination',None),('class_control_contamination',None)]:
        real_clone=replay.clone_sampler
        def corrupted(sampler,state):
            if label=='route_contamination':
                sampler.state.attempts+=1
            elif label=='request_counter_contamination':
                sampler.next_proposal_id+=1
            elif label=='class_control_contamination':
                type(sampler).RUN_SEED+=1
            return real_clone(sampler,state)
        try:
            with patch.object(replay,'clone_sampler',side_effect=effect or corrupted):
                rt.collect(p['bifolia'][0])
        except (RuntimeError,ValueError,AssertionError) as exc:
            after=rb.PatchSampler,rb.PatchMapState,rb.build_bt_leafex,rb.patch_generate,e.complete_segment
            if before!=after:raise AssertionError('Bindings not restored')
            after_class=digest([(c.__name__,replay.class_control_payload(c)) for c in rt.active.V223F1LFLengthTerminalSampler.__mro__ if c is not object])
            if class_before!=after_class:raise AssertionError('Class controls not restored')
            checks.append(dict(probe=label,rejected=True,bindings_restored=True,class_controls_restored=True,reason=str(exc)))
        else:raise AssertionError('Contamination accepted')
    real_state_clone=e.GenerationState.clone
    def corrupt_rare(self):
        z=real_state_clone(self);z.rare['budget']+=1
        return z
    try:
        with patch.object(e.GenerationState,'clone',corrupt_rare):
            rt.collect(p['bifolia'][0])
    except (RuntimeError,ValueError,AssertionError) as exc:
        after=rb.PatchSampler,rb.PatchMapState,rb.build_bt_leafex,rb.patch_generate,e.complete_segment
        if before!=after:raise AssertionError('Rare probe bindings not restored')
        checks.append(dict(probe='rare_clone_corruption',rejected=True,bindings_restored=True,reason=str(exc)))
    else:raise AssertionError('Rare clone corruption accepted')
    ordinary=rt.collect(p['bifolia'][0],observe=False)
    if ordinary['base_sha256']!=original['base_sha256']:raise AssertionError('Failure polluted later ordinary BASE')
    audited(plan,generated)
    write_json(output/'summary.json',dict(status='PASS',checks=checks,ordinary_base_after_failure_equal=True,
               original_artifacts_preserved=True,source_input_files_never_modified=True))
    return checks


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--plan',required=True);a.add_argument('--generated',required=True);a.add_argument('--output',required=True)
    run(**vars(a.parse_args()))
