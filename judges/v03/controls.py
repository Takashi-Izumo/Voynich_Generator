"""Preregistered local perturbations; diagnostics remain grouped by bifolium."""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import math
from pathlib import Path
import random

from ..schema import GLYPHS, WIDTH
from ..scoring import reference_mix
from .calibration import split_plan, validate_corpus
from .observations import endpoints, scopes, word_events
from .protocol import DEFAULT, PROTOCOL_HASH, digest, file_hash, read_json, read_jsonl, write_json, write_jsonl
from .schema import validate_case
from .statistics import aggregate, score


def locations(doc,view):
    if view.startswith('J08.'):
        scope=view.split('.')[1]
        return [(e.line,e.segment,None,e.g,len(e.g)-1,('SHORT' if len(e.g)<=3 else 'LONG',)) for e in endpoints(doc)
            if scope in scopes(doc['layout']['lines'][e.line],e.segment)]
    length=int(view.split('.')[1][1:])
    return [(e.line,e.segment,e.position,e.g,1,(e.g[0],)) for e in word_events(doc)
        if e.role=='W2' and not e.first and not e.final and e.boundary=='I' and len(e.g)==length]


def perturb(doc,known,view,direction,strength,replicate,cluster,slot):
    selected=locations(doc,view);N=len(selected);count=math.floor(strength*N)
    if not count:return None,{'reason':'NO_TARGET_OR_ZERO_MUTATION','target_events':N,'changed_events':0}
    reference=[]
    for r in known:
        c=Counter()
        for li,si,wi,g,pos,ctx in locations(r,view):c[ctx,g[pos]]+=1
        reference.append(c)
    mix=reference_mix(reference);mutatable=[]
    for loc in selected:
        li,si,wi,g,pos,ctx=loc;original=mix.get((ctx,g[pos]),0)
        eligible=[v for v in GLYPHS if v!=g[pos] and WIDTH[v]==WIDTH[g[pos]] and
            (mix.get((ctx,v),0)>original if direction=='toward_reference' else mix.get((ctx,v),0)<original)]
        if eligible:
            replacement=min(eligible,key=lambda v:((-mix.get((ctx,v),0) if direction=='toward_reference' else mix.get((ctx,v),0)),v))
            mutatable.append((loc,replacement))
    if not mutatable:return None,{'reason':'NO_REFERENCE_DIRECTION','target_events':N,'changed_events':0}
    payload=[DEFAULT['controls']['rng_namespace'],cluster,slot,view,direction,strength,replicate]
    rng=random.Random(int(hashlib.sha256(digest(payload).encode()).hexdigest(),16))
    rng.shuffle(mutatable);changed=mutatable[:count];result=deepcopy(doc)
    for (li,si,wi,g,pos,ctx),v in changed:
        word=list(g);word[pos]=v
        assert len(word)==len(g) and sum(WIDTH[x] for x in word)==sum(WIDTH[x] for x in g)
        if view.startswith('J11.'):
            assert word[0]==g[0] and tuple(word[2:])==g[2:]
        so=result['observations']['lines'][li]['segments'][si]
        if so['mode']=='END_ONLY':so['end_word']=''.join(word)
        else:so['tokens'][wi if wi is not None else -1]=''.join(word)
    return result,{'reason':'MODIFIED','target_events':N,'changed_events':len(changed),'actual_fraction':len(changed)/N}


def create_controls(corpus,output,plan=None):
    validate_corpus(corpus)
    if plan is not None:
        wanted=split_plan(corpus)
        if any(any(p[k]!=s[k] for k in s) for p,s in zip(plan['splits'],wanted)) or len(plan['splits'])!=5:raise ValueError('control fold plan mismatch')
    cases=[];details=[];assign=defaultdict(list);counter=0
    for b in sorted(corpus['bifolia'],key=lambda x:x['cluster_id']):
        for doc in sorted(b['pages'],key=lambda p:p['slot']):
            known=[p for p in b['pages'] if p['slot']!=doc['slot']]
            for view in ['J08.WIDE','J08.F1LF','J08.POSTPLANT','J11.L3.H2','J11.L4.H2','J11.L5.H2']:
                for direction in DEFAULT['controls']['directions']:
                    for strength in DEFAULT['controls']['strengths']:
                        for rep in range(DEFAULT['controls']['replicates']):
                            counter+=1
                            changed,info=perturb(doc,known,view,direction,strength,rep,b['cluster_id'],doc['slot'])
                            cid=digest(['control-v03',b['cluster_id'],doc['slot'],view,direction,strength,rep])[:24]
                            detail={'set_id':cid,'cluster_id':b['cluster_id'],'slot':doc['slot'],'view':view,'direction':direction,'strength':strength,'replicate':rep,**info}
                            details.append(detail)
                            if changed is None:continue
                            c={'schema_version':2,'protocol_id':DEFAULT['protocol_id'],'set_id':cid,'cluster_id':b['cluster_id'],
                                'seed':counter,'target_slot':doc['slot'],'text_profile':'stable22-visible','input_profile':'structure-endpoints-v2',
                                'known':known,'target_layout':doc['layout'],'candidates':{'A':doc['observations'],'B':changed['observations']}}
                            validate_case(c);assign[view,direction,strength].append(len(cases));cases.append(c)
    keys=[None]*len(cases);rng=random.Random(20261104)
    for _,indices in sorted(assign.items()):
        flags=[True]*(len(indices)//2)+[False]*(len(indices)//2)
        if len(flags)<len(indices):flags.append(bool(rng.getrandbits(1)))
        rng.shuffle(flags)
        for index,flag in zip(indices,flags):
            if not flag:cases[index]['candidates']={'A':cases[index]['candidates']['B'],'B':cases[index]['candidates']['A']}
            keys[index]={'set_id':cases[index]['set_id'],'truth':'A' if flag else 'B'}
    if not cases:raise ValueError('no applicable perturbation controls')
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_jsonl(output/'inputs.jsonl',cases);write_jsonl(output/'answer_key.jsonl',keys);write_jsonl(output/'control_plan.jsonl',details)
    write_json(output/'manifest.json',{'protocol_hash':PROTOCOL_HASH,'corpus_hash':digest(corpus),'planned_trials':counter,'modified_trials':len(cases),
        'control_code_sha256':file_hash(__file__),
        'inputs_sha256':file_hash(output/'inputs.jsonl'),'key_sha256':file_hash(output/'answer_key.jsonl'),'plan_sha256':file_hash(output/'control_plan.jsonl'),
        'mutation_scope':'same-width glyph substitutions; word-level/Markov support not guaranteed','data_status':'development_reused_not_fresh_confirmation'})
    return {'planned_trials':counter,'modified_trials':len(cases)}


def capability(predictions,controls,output,bootstrap=10000):
    controls=Path(controls);output=Path(output)
    m=read_json(controls/'manifest.json')
    if m['protocol_hash']!=PROTOCOL_HASH or m['control_code_sha256']!=file_hash(__file__):raise ValueError('control generator version mismatch')
    for f,k in [('inputs.jsonl','inputs_sha256'),('answer_key.jsonl','key_sha256'),('control_plan.jsonl','plan_sha256')]:
        if file_hash(controls/f)!=m[k]:raise ValueError('control artifacts were changed')
    pm=read_json(Path(predictions)/'manifest.json')
    if pm['input_file_sha256']!=m['inputs_sha256'] or pm['model_set_hash'] is None:raise ValueError('capability requires sealed calibrated predictions on these controls')
    if pm['calibration_corpus_hash']!=m['corpus_hash']:raise ValueError('control/calibration corpus mismatch')
    output.mkdir(parents=True,exist_ok=False)
    score(predictions,controls/'answer_key.jsonl',output/'scores',bootstrap)
    measured={(r['set_id'],r['view']):r for r in read_jsonl(output/'scores/measurements.jsonl')}
    plan=read_jsonl(controls/'control_plan.jsonl');groups=defaultdict(list)
    for p in plan:groups[p['view'],p['direction'],p['strength']].append(p)
    results=[];gates=DEFAULT['controls']['capability_gate']
    for (view,direction,strength),pp in sorted(groups.items()):
        modified=[p for p in pp if p['reason']=='MODIFIED']
        for family in ['PROTO','CAL']:
            rr=[measured[p['set_id'],view+'.'+family] for p in modified]
            stats=aggregate(rr,bootstrap) if rr else None
            status='INSUFFICIENT_DATA'
            if stats and stats['comparable_bifolia']>=gates['minimum_target_bifolia'] and stats['comparable_coverage']>=gates['minimum_comparable_fraction']:
                ci=stats['expected_game_cluster_bootstrap_95']
                status='CAPABILITY_SUPPORTED' if (stats['macro_expected_game_accuracy']>=gates['strong_expected_game_accuracy_min'] and ci and ci[0]>gates['strong_cluster_bootstrap_95_lower_strictly_above']) else 'LOW_POWER'
            results.append({'view':view+'.'+family,'direction':direction,'strength':strength,'planned_trials':len(pp),'modified_trials':len(rr),
                'mutation_applicability':len(rr)/len(pp),'status':status if strength==1 else 'SENSITIVITY_ONLY','summary':stats})
    result={'status':'development_capability_check_only','model_set_hash':pm['model_set_hash'],'protocol_hash':PROTOCOL_HASH,
        'results':results,'promotion_verdict':None,'limitations':['same-width controls may be lexically unnatural','not a multiplicity-adjusted discovery','intervals condition on fitted models']}
    write_json(output/'capability.json',result)
    return {'strong_control_statuses':dict(Counter(r['status'] for r in results if r['strength']==1)),'promotion_verdict':None}
