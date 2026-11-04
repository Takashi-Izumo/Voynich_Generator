from __future__ import annotations

import hashlib
import math
from ..features import Feature
from ..registry import ATOMS
from ..scoring import compare
from .protocol import DEFAULT, PROTOCOL_HASH, digest, extractor_hash
from .schema import candidate_doc, finite_tree, template, validate_case
from .views import extract, groups, sample_n, observation_counts
from .observations import scopes


def view_result(parts, names, family):
    active=[k for k in names if k in parts and parts[k]['A'] is not None and parts[k]['B'] is not None]
    a=math.fsum(parts[k]['A'] for k in active)/len(active) if active else None
    b=math.fsum(parts[k]['B'] for k in active)/len(active) if active else None
    delta=a-b if active else None
    status='NA' if delta is None else 'TIE' if abs(delta)<=DEFAULT['tie_epsilon'] else 'DECIDED'
    available=[parts[k] for k in names if k in parts]
    why='NO_EVENTS'
    if available:
        reasons=[x['reason'] for x in available]
        for reason in ['INSUFFICIENT_CALIBRATION','NO_CALIBRATION','NO_COMMON_CONTEXT','NO_REFERENCE_EVENTS','NO_EVENTS']:
            if reason in reasons:why=reason;break
    coverage={'source_slots':0,'A_events':max((x['A_events'] for x in available),default=0),
        'B_events':max((x['B_events'] for x in available),default=0),
        'reference_events':[max((x['reference_events'][i] for x in available),default=0) for i in range(3)],
        'reference_nonempty_pages':max((x['reference_nonempty_pages'] for x in available),default=0),
        'common_contexts':sum(x.get('contexts',0) for x in available) if family=='PROTO' else None,
        'reference_context_mass':min((x['reference_context_coverage'] for x in available if 'reference_context_coverage' in x),default=None),
        'calibration':{side:next((x.get('calibration',{}).get(side) for x in available if x.get('calibration',{}).get(side)),None) for side in ['A','B']}}
    if coverage['reference_context_mass'] is not None:coverage['reference_context_mass']=min(1.0,max(0.0,coverage['reference_context_mass']))
    return {'family':family,'status':status,'reason':why if status=='NA' else 'EXACT_OR_NUMERIC_TIE' if status=='TIE' else 'OK',
        'scores':{'A':a,'B':b},'delta':delta,'pick':None if status!='DECIDED' else 'A' if delta>0 else 'B',
        'active_channels':active,'coverage':coverage}


def channel_scores(refs,sides):
    names=sorted(set().union(*[set(x) for x in refs+list(sides.values())]))
    out={}
    for name in names:
        exemplar=next(x[name] for x in refs+list(sides.values()) if name in x)
        empty=lambda:Feature(conditional=exemplar.conditional)
        rf=[r.get(name,empty()) for r in refs];a=sides['A'].get(name,empty());b=sides['B'].get(name,empty())
        score=compare(rf,a,b)
        score.update(reason='NO_COMMON_CONTEXT' if score['status']=='NA_CONTEXT' else 'NO_REFERENCE_EVENTS' if not any(x.counts for x in rf) else 'NO_EVENTS' if score['status']!='OK' else 'OK',
            reference_events=[sample_n(x) for x in rf],reference_nonempty_pages=sum(bool(x.counts) for x in rf),A_events=sample_n(a),B_events=sample_n(b))
        out[name]=score
    return out


def combine_primary(views,family):
    names=[f'ATOM.{a}.{family}' for a in ATOMS]
    active=[k for k in names if views[k]['status']!='NA']
    minimum=1 if family=='PROTO' else DEFAULT['primary']['calibrated_min_common_atoms']
    parts={k:{'A':v['scores']['A'],'B':v['scores']['B'],'reason':v['reason'],**v['coverage']} for k,v in views.items() if k in names}
    result=view_result(parts,active if len(active)>=minimum else [],family)
    if len(active)<minimum:result['reason']='TOO_FEW_ACTIVE_ATOMS'
    return result


def predict(case, model=None, primary='J24.PROTO', context=None):
    validate_case(case)
    if primary not in ['J24.PROTO','J24.CAL']:raise ValueError('unsupported primary')
    if primary=='J24.CAL' and model is None:raise ValueError('CAL requires a bound fitted model')
    known=sorted(case['known'],key=lambda d:d['slot'])
    refs=[extract(d,[r for j,r in enumerate(known) if j!=i]) for i,d in enumerate(known)]
    sides={s:extract(candidate_doc(case,s),known) for s in ['A','B']}
    proto=channel_scores(refs,sides)
    views={name+'.PROTO':view_result(proto,ks,'PROTO') for name,ks in groups(proto,'PROTO').items()}
    views['J24.PROTO']=combine_primary(views,'PROTO')
    all_channels={'PROTO':proto}
    if model is not None:
        from .calibration import calibrated_scores, validate_binding
        validate_binding(model,case['cluster_id'])
        cal=calibrated_scores(model,refs,sides)
        views.update({name+'.CAL':view_result(cal,ks,'CAL') for name,ks in groups(cal,'CAL').items()})
        views['J24.CAL']=combine_primary(views,'CAL');all_channels['CAL']=cal
    selected=views[primary]
    frames=case['target_layout']['lines']
    counts={s:observation_counts(candidate_doc(case,s),sides[s]) for s in ['A','B']}
    reference_counts=[observation_counts(d,fs) for d,fs in zip(known,refs)]
    for name,v in views.items():
        base=name.rsplit('.',1)[0]
        if name.startswith('J08.'):
            scope=name.split('.')[1]
            n=sum(sf['end_word_known'] and scope in scopes(frame,si) for frame in frames for si,sf in enumerate(frame['segments'] or []))
            unit='ENDPOINTS'
        elif name.startswith('J11.'):
            n=sum(f['whole_line_usable'] and f['paragraph_line'] is not None and f['paragraph_line']>1 and f['paragraph_final'] is False for f in frames);unit='MIDDLE_LINES'
        else:
            n=sum(len(f['segments']) for f in frames if f['whole_line_usable']);unit='FULL_SEGMENTS'
        v['coverage'].update(source_slots=n,source_unit=unit,A_events=counts['A'][base],B_events=counts['B'][base],
            reference_events=[x[base] for x in reference_counts],reference_nonempty_pages=sum(x[base]>0 for x in reference_counts))
    forced=selected['pick']
    if selected['status']=='TIE':
        forced='A' if hashlib.sha256(f'{PROTOCOL_HASH}|{case["set_id"]}|{primary}|tie-v1'.encode()).digest()[0]&1 else 'B'
    result={'schema_version':2,'set_id':case['set_id'],'cluster_id':case['cluster_id'],'seed':case['seed'],'target_slot':case['target_slot'],
        'protocol_hash':PROTOCOL_HASH,'input_hash':digest(case),'template_hash':digest(template(case)),
        'extractor_hash':context or extractor_hash(),'model_hash':digest(model) if model is not None else None,
        'primary':primary,'forced_primary_pick':forced,'views':views}
    # Per-channel facts remain sealed alongside the row for independent audits.
    finite_tree(result)
    return result,all_channels
