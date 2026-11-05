"""Generation, independent replay audit, and blind genuine-vs-modified export."""
from __future__ import annotations

from copy import deepcopy
from collections import defaultdict
from pathlib import Path
import hashlib
import json

from judges.v03.adapter import source_documents
from judges.v03.protocol import DEFAULT, digest as jury_digest, write_jsonl, read_jsonl
from judges.v03.schema import validate_case
from judges.v03.views import extract
from . import FAMILIES, DIRECTIONS, SEED, BRANCHES
from .common import PACKAGE, canonical, context, digest, file_hash, file_inventory, read, require, seal, unseal, write_json
from .plan import load, structure
from .proxy import fit_fold, select
from .replay import Runtime


def collect_case(rt, p, bif):
    observed = rt.collect(bif)
    ordinary = rt.collect(bif, observe=False)
    require(observed['base_sha256'] == ordinary['base_sha256'], 'Observed BASE differs from literal original BASE')
    require(observed['base']['final'] == ordinary['base']['final'], 'BASE final full state/main RNG mismatch')
    events = {(s['locus'],s['segment_id']):s for s in observed['snapshots']}
    selections = []
    for eligible in [e for e in p['eligible_events'] if e['bif']==bif]:
        key = eligible['locus'], eligible['segment_id']
        require(key in events, 'Eligible FULL event missing from generation')
        snapshot = events[key]
        anchor = [r for r in observed['base']['rows'] if (r['locus'],r['segment_id'])==key]
        donors = [d for d in observed['donors'] if context(d)==context(snapshot)]
        for choice in select(anchor, donors, p['proxies'][str(observed['fold'])]):
            if choice['family']=='space_T_H1' and not eligible['space']:
                continue
            selections.append(dict(**{k:snapshot[k] for k in ('bif','run','page','locus','segment_id','event')},
                                   snapshot_sha256=snapshot['sha256'], **choice))
    return json.loads(json.dumps(seal(dict(**observed, selections=selections, ordinary_base_sha256=ordinary['base_sha256'],
                     no_effect_checked=True, plan_sha256=p['sha256'])),allow_nan=False))


def validate_case_records(p, case, bif):
    """Cheap structural checks before the authoritative, fresh 64-branch replay."""
    unseal(case)
    require(case['bif']==bif and case['plan_sha256']==p['sha256'] and case['no_effect_checked'] is True,
            'Wrong case/plan')
    require(case['base_sha256']==case['ordinary_base_sha256']==digest(case['base']), 'BASE receipt mismatch')
    snapshots=case['snapshots'];donors=case['donors']
    require([s['event'] for s in snapshots]==list(range(len(snapshots)))
            and len({context(s) for s in snapshots})==len(snapshots),'Snapshot coverage/order mismatch')
    require(len(donors)==BRANCHES*len(snapshots),'Missing/extra replay branches')
    for i,s in enumerate(snapshots):
        unseal(s)
        require(s['bif']==bif and s['run']==SEED and s['page']==case['page'] and s['branches']==BRANCHES,
                'Snapshot case mismatch')
        current=donors[i*BRANCHES:(i+1)*BRANCHES]
        require([d['branch'] for d in current]==list(range(BRANCHES)),'Duplicate/missing/reordered branch IDs')
        for d in current:
            unseal(d)
            require(type(d['branch']) is int and context(d)==context(s)
                    and d['snapshot_sha256']==s['sha256'] and d['input_state_sha256']==s['state_sha256'],
                    'Replay belongs to another snapshot/candidate context')
            require(d['proposal_start']==s['next_proposal_id']
                    and [r['proposal_id'] for r in d['requests']]==list(range(d['proposal_start'],d['proposal_end'])),
                    'Replay request coverage mismatch')
            require(d['restored_parent'] is True and d['support_violations']==0 and d['physical_packing'] is True,
                    'Replay support/isolation failure')
    expected_selections=[]
    for eligible in [e for e in p['eligible_events'] if e['bif']==bif]:
        key=eligible['locus'],eligible['segment_id']
        s=next((s for s in snapshots if (s['locus'],s['segment_id'])==key),None)
        require(s is not None,'Eligible snapshot absent')
        anchor=[r for r in case['base']['rows'] if (r['locus'],r['segment_id'])==key]
        current=[d for d in donors if context(d)==context(s)]
        for choice in select(anchor,current,p['proxies'][str(case['fold'])]):
            if choice['family']=='space_T_H1' and not eligible['space']:continue
            expected_selections.append(dict(**{k:s[k] for k in ('bif','run','page','locus','segment_id','event')},
                                            snapshot_sha256=s['sha256'],**choice))
    require(case['selections']==expected_selections and digest(case['selections'])==digest(expected_selections),
            'Donor selection changed or misbound')


def generate(plan, output):
    p = load(plan)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'plan.json', p)
    write_json(output/'STATUS.json', dict(status='RUNNING', plan_sha256=p['sha256']))
    rt = Runtime()
    completed = []
    try:
        for bif in p['bifolia']:
            require(rt.input_snapshot==p['runtime_inputs'],'Runtime differs from sealed control inputs')
            case = collect_case(rt,p,bif)
            name = bif.replace(':','_')+'.json'
            (output/name).write_text(json.dumps(case,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
            completed.append(name)
            print(f'REPLAY {bif} events={len(case["snapshots"])} branches={len(case["donors"])}',flush=True)
        require(load(plan)==p,'Control source/input/plan changed during generation')
    except Exception as exc:
        write_json(output/'STATUS.json',dict(status='FAILED',error=str(exc),completed=completed,plan_sha256=p['sha256']))
        raise
    write_json(output/'STATUS.json',dict(status='GENERATED_NOT_AUDITED', completed=completed,plan_sha256=p['sha256']))
    write_json(output/'manifest.json',seal(dict(plan_sha256=p['sha256'], files=file_inventory(output))))
    return completed


def binding(p, generated):
    root = Path(generated)
    m = unseal(read(root/'manifest.json'))
    require(m['plan_sha256'] == p['sha256'] and read(root/'plan.json') == p, 'Generation plan mismatch')
    status = read(root/'STATUS.json')
    expected = sorted(b.replace(':','_')+'.json' for b in p['bifolia'])
    require(status['status'] == 'GENERATED_NOT_AUDITED' and sorted(status['completed']) == expected
            and status['plan_sha256'] == p['sha256'], 'Incomplete or failed generation')
    require(sorted(m['files']) == sorted([*expected,'plan.json','STATUS.json']), 'Manifest coverage mismatch')
    for name, h in m['files'].items():
        require(Path(name).name == name and file_hash(root/name) == h, 'Generation artifact changed: '+name)
    require(file_inventory(root, ('manifest.json','AUDIT.json')) == m['files'], 'Extra/missing generation artifact')
    return digest(m)


def audit(plan, generated, output):
    root = Path(generated)
    # An unsuccessful re-audit always revokes the old PASS first.
    (root/'AUDIT.json').unlink(missing_ok=True)
    p = load(plan)
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    try:
        bound = binding(p,root)
        for bif in p['bifolia']:
            validate_case_records(p,read(root/(bif.replace(':','_')+'.json')),bif)
        rt = Runtime()
        eligible, corpus, raw = structure(rt,p['bifolia'])
        require(eligible == p['eligible_events'] and corpus == p['corpus_hash'] and raw == p['source_hashes'],
                'Corpus/eligibility differs from preregistration')
        for f in p['proxies']:
            require(fit_fold(rt,int(f)) == p['proxies'][f], 'Proxy fit/source mismatch (including target leakage)')
        rows = []
        for bif in p['bifolia']:
            stored = unseal(read(root/(bif.replace(':','_')+'.json')))
            # The expected record is produced directly from the frozen runtime, never from supplied traces.
            # This checks missing/extra/duplicate records, typed contexts, receipts, row values, IDs and all state/RNG.
            expected = collect_case(rt,p,bif)
            require(stored == expected and digest(stored)==digest(expected), 'Fresh replay differs: '+bif)
            rows.append(dict(bif=bif,events=len(stored['snapshots']),donors=len(stored['donors']),
                             expected_donors=BRANCHES*len(stored['snapshots']),
                             selections=len(stored['selections']),base_sha256=stored['base_sha256']))
        require(binding(p,root) == bound, 'Artifacts changed during audit')
        require(load(plan)==p,'Control source/input/plan changed during audit')
        report = seal(dict(status='PASS',plan_sha256=p['sha256'],binding=bound,cases=rows,
                           fresh_replay_checked=True,base_full_semantics_state_main_rng_checked=True,
                           support_packing_terminal_plant_violations=0,capability_pass=False))
        write_json(output/'report.json',report)
        write_json(root/'AUDIT.json',seal(dict(plan_sha256=p['sha256'],binding=bound,
                   report=str((output/'report.json').resolve()),report_sha256=file_hash(output/'report.json'))))
        return report
    except Exception as exc:
        write_json(output/'report.json',dict(status='FAIL',error=str(exc),plan_sha256=p['sha256']))
        (root/'AUDIT.json').unlink(missing_ok=True)
        raise


def audited(plan, generated):
    p=load(plan)
    bound=binding(p,generated)
    receipt=unseal(read(Path(generated)/'AUDIT.json'))
    require(receipt['plan_sha256']==p['sha256'] and receipt['binding']==bound
            and file_hash(receipt['report'])==receipt['report_sha256'],'Stale audit PASS')
    report=unseal(read(receipt['report']))
    require(report['status']=='PASS' and report['plan_sha256']==p['sha256'] and report['binding']==bound
            and report['fresh_replay_checked'] is True,'Invalid audit PASS')
    return p


def build_export(p, cases):
    _,corpus,docs,loci,_=source_documents(PACKAGE)
    require(jury_digest(corpus)==p['corpus_hash'],'Corpus changed before export')
    corpus_by={r['cluster_id']:r for r in corpus['bifolia']}
    result={}
    for lane in FAMILIES:
        for direction in DIRECTIONS:
            inputs,keys,diagnostics=[],[],[]
            for bif in p['eligible_cohorts'][lane]:
                case=cases[bif]
                page=case['page'];true=docs[page]
                changed=deepcopy(true)
                choices=[c for c in case['selections'] if c['family']==lane and c['direction']==direction]
                modifications=[]
                for choice in choices:
                    e=next(e for e in p['eligible_events'] if e['bif']==bif and e['locus']==choice['locus']
                           and e['segment_id']==choice['segment_id'])
                    li,si=e['line_index'],e['segment_id']
                    require(true['layout']['lines'][li]['whole_line_usable']
                            and true['observations']['lines'][li]['segments'][si]['mode']=='FULL',
                            'Cannot promote END_ONLY to atom')
                    if choice['branch'] is not None:
                        donor=next(d for d in case['donors'] if context(d)==context(choice) and d['branch']==choice['branch'])
                        require(donor['snapshot_sha256']==choice['snapshot_sha256'],'Donor snapshot/context mismatch')
                        from judges.schema import glyphs
                        tokens=[''.join(glyphs(r['surface'])) for r in donor['rows']]
                        changed['observations']['lines'][li]['segments'][si]={'mode':'FULL','tokens':tokens}
                    modifications.append(choice)
                cluster=hashlib.sha256(('cluster/'+bif).encode()).hexdigest()[:16]
                known=corpus_by[cluster]['pages'][:3]
                cid=jury_digest(['PF-CONTROL',p['sha256'],lane,direction,cluster])[:24]
                side='A' if int(hashlib.sha256(cid.encode()).hexdigest()[-1],16)%2 else 'B'
                c=dict(schema_version=2,protocol_id=DEFAULT['protocol_id'],set_id=cid,cluster_id=cluster,
                       seed=SEED,target_slot=3,text_profile='stable22-visible',input_profile='structure-endpoints-v2',
                       known=known,target_layout=true['layout'],candidates={side:true['observations'],
                       'B' if side=='A' else 'A':changed['observations']})
                validate_case(c)
                # Diagnostics only after all selected donor IDs were frozen by generation + fresh audit.
                tfeat,cfeat=extract(true,known),extract(changed,known)
                feature='ATOM.PARA_END/'+lane
                realized=tfeat[feature].counts != cfeat[feature].counts
                inputs.append(c);keys.append(dict(set_id=cid,truth=side))
                diagnostics.append(dict(set_id=cid,bif=bif,cluster_id=cluster,family=lane,direction=direction,
                       target_feature_realized=realized,changed=changed['observations']!=true['observations'],
                       selections=modifications,
                       all_channel_feature_changes={k:dict(genuine=canonical(tfeat[k].counts if k in tfeat else {}),
                                                          modified=canonical(cfeat[k].counts if k in cfeat else {}))
                          for k in sorted(tfeat.keys()|cfeat.keys())
                          if (tfeat[k].counts if k in tfeat else {})!=(cfeat[k].counts if k in cfeat else {})}))
            result[lane+'__'+direction]=dict(inputs=inputs,keys=keys,diagnostics=diagnostics)
    return result


def export(plan,generated,output):
    p=audited(plan,generated)
    cases={b:unseal(read(Path(generated)/(b.replace(':','_')+'.json'))) for b in p['bifolia']}
    exports=build_export(p,cases)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    for label,data in exports.items():
        lane=output/label;lane.mkdir()
        write_jsonl(lane/'inputs.jsonl',data['inputs'])
        write_jsonl(lane/'answer_key.jsonl',data['keys'])
        write_jsonl(lane/'diagnostics.jsonl',data['diagnostics'])
    write_json(output/'EXPORT.json',seal(dict(plan_sha256=p['sha256'],generation_binding=binding(p,generated),
               generated_root=str(Path(generated).resolve()),files=file_inventory(output),
               predictor_files='only each inputs.jsonl; no snapshots/proxies/logs/keys/diagnostics',
               all_donors_selected_before_true_word_substitution=True)))
    return exports


def verify_export(plan,generated,output):
    p=audited(plan,generated)
    m=unseal(read(Path(output)/'EXPORT.json'))
    require(m['plan_sha256']==p['sha256'] and m['generation_binding']==binding(p,generated),'Export generation changed')
    require(file_inventory(output,('EXPORT.json',))==m['files'],'Export artifacts changed')
    cases={b:unseal(read(Path(generated)/(b.replace(':','_')+'.json'))) for b in p['bifolia']}
    expected=build_export(p,cases)
    for label,data in expected.items():
        for file,key in [('inputs.jsonl','inputs'),('answer_key.jsonl','keys'),('diagnostics.jsonl','diagnostics')]:
            actual=read_jsonl(Path(output)/label/file)
            require(actual==data[key] and digest(actual)==digest(data[key]),
                    'Export assignment/text/key/diagnostic mismatch')
    return p,m,expected
