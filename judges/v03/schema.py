"""Strict standard-library structural and semantic validation for schema 2."""
from __future__ import annotations

import math
from ..schema import glyphs, RARE
from .protocol import DEFAULT


def fields(obj, required):
    if not isinstance(obj, dict) or set(obj) != set(required.split()):
        raise ValueError('fields must be exactly: '+required)


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def word(value):
    if not isinstance(value, str) or not value or any(c.isspace() or c in RARE for c in value) or glyphs(value) is None:
        raise ValueError('invalid stable22-visible word')


def validate_doc(doc, reference=False):
    fields(doc, 'slot layout observations' if reference else 'layout observations')
    if reference and (not integer(doc['slot']) or doc['slot'] > 3):
        raise ValueError('invalid reference slot')
    layout, obs = doc['layout'], doc['observations']
    fields(layout, 'lines'); fields(obs, 'lines')
    if not isinstance(layout['lines'], list) or not layout['lines'] or not isinstance(obs['lines'], list) or len(layout['lines']) != len(obs['lines']):
        raise ValueError('layout/observation line count mismatch')
    last_para = None; finished = set(); prior = None; observed = 0
    reasons = {'UNPARSEABLE_SPAN','ORDER_MISMATCH','EMPTY_SEGMENT','MISSING_SOURCE_LINE',
        'UNKNOWN_STRUCTURE','UNCONFIRMED_ENDPOINT','LEGACY_LAYOUT_EXCEPTION'}
    for i, (frame, data) in enumerate(zip(layout['lines'], obs['lines']), 1):
        fields(frame, 'line_no paragraph paragraph_line paragraph_final layout_mode whole_line_usable mapping_exact source_multiword mask_reasons segments')
        fields(data, 'segments')
        if type(frame['line_no']) is not int or frame['line_no'] != i:
            raise ValueError('line_no must preserve consecutive source positions')
        for key in ['paragraph','paragraph_line']:
            if frame[key] is not None and not integer(frame[key], int(key=='paragraph_line')):
                raise ValueError('invalid '+key)
        for key in ['paragraph_final','mapping_exact','source_multiword']:
            if frame[key] is not None and type(frame[key]) is not bool:
                raise ValueError('invalid tri-state '+key)
        if type(frame['whole_line_usable']) is not bool or frame['layout_mode'] not in ['LINEAR_PARAGRAPH','OTHER','UNKNOWN']:
            raise ValueError('invalid line quality/layout')
        rr = frame['mask_reasons']
        if not isinstance(rr,list) or any(not isinstance(x,str) or x not in reasons for x in rr) or len(rr)!=len(set(rr)):
            raise ValueError('invalid mask reasons')
        para = frame['paragraph']
        if para is not None:
            if para != last_para:
                if para in finished: raise ValueError('noncontiguous paragraph')
                if last_para is not None: finished.add(last_para)
                if prior is not None and prior['paragraph'] is not None and prior['paragraph_final'] is False:
                    raise ValueError('paragraph changes after explicit nonfinal line')
            elif prior is not None and prior['paragraph'] == para:
                if prior['paragraph_final'] is True:
                    raise ValueError('line follows explicit paragraph end')
                if prior['paragraph_line'] is not None and frame['paragraph_line'] is not None and frame['paragraph_line'] != prior['paragraph_line']+1:
                    raise ValueError('paragraph position was compressed or inconsistent')
            last_para = para
        prior = frame
        fs, ds = frame['segments'], data['segments']
        if fs is None:
            if ds is not None or frame['whole_line_usable']:
                raise ValueError('unknown structure must remain unknown')
            continue
        if not isinstance(fs,list) or not fs or not isinstance(ds,list) or len(fs)!=len(ds):
            raise ValueError('segment layout mismatch')
        if frame['whole_line_usable'] and (frame['mapping_exact'] is not True or any(frame[k] is None for k in ['paragraph','paragraph_line','paragraph_final'])):
            raise ValueError('FULL requires known structure and exact mapping')
        for j, (sf, so) in enumerate(zip(fs,ds)):
            fields(sf,'end end_word_known end_predecessor_known')
            if sf['end'] != ('LINE_END' if j==len(fs)-1 else 'PLANT') or type(sf['end_word_known']) is not bool or (sf['end_predecessor_known'] is not None and type(sf['end_predecessor_known']) is not bool):
                raise ValueError('invalid source segment boundary/quality')
            if not isinstance(so,dict): raise ValueError('invalid segment observation')
            expected = 'FULL' if frame['whole_line_usable'] else 'END_ONLY' if sf['end_word_known'] else 'NONE'
            if so.get('mode') != expected: raise ValueError('observation mode must follow shared source quality')
            if expected=='FULL':
                fields(so,'mode tokens')
                if not isinstance(so['tokens'],list) or not so['tokens']: raise ValueError('FULL requires tokens')
                for w in so['tokens']: word(w); observed += 1
                if not sf['end_word_known']: raise ValueError('FULL must include a known endpoint')
            elif expected=='END_ONLY':
                fields(so,'mode end_word');word(so['end_word']);observed += 1
            else: fields(so,'mode')
    if not observed:
        raise ValueError('document has no observable words')


def candidate_doc(case, side):
    return {'layout':case['target_layout'],'observations':case['candidates'][side]}


def validate_case(case):
    fields(case,'schema_version protocol_id set_id cluster_id seed target_slot text_profile input_profile known target_layout candidates')
    if type(case['schema_version']) is not int or case['schema_version']!=2 or case['protocol_id']!=DEFAULT['protocol_id']:
        raise ValueError('unsupported v03 schema/protocol')
    if case['text_profile']!='stable22-visible' or case['input_profile']!='structure-endpoints-v2':
        raise ValueError('unsupported text/input profile')
    if any(not isinstance(case[x],str) or not case[x] for x in ['set_id','cluster_id']) or type(case['seed']) is not int or not integer(case['target_slot']) or case['target_slot']>3:
        raise ValueError('invalid case identity')
    if not isinstance(case['known'],list) or len(case['known'])!=3: raise ValueError('exactly known3 required')
    for d in case['known']: validate_doc(d,reference=True)
    if {d['slot'] for d in case['known']} != set(range(4))-{case['target_slot']}:
        raise ValueError('known slots must complement target slot')
    fields(case['candidates'],'A B')
    for side in ['A','B']:
        validate_doc(candidate_doc(case,side))


def unique_cases(cases):
    if not cases: raise ValueError('empty case set')
    ids=set(); trials=set()
    for c in cases:
        validate_case(c)
        trial=(c['cluster_id'],c['target_slot'],c['seed'])
        if c['set_id'] in ids or trial in trials: raise ValueError('duplicate case ID/trial')
        ids.add(c['set_id']);trials.add(trial)


def template(case):
    # Known order is not a semantic difference.
    return {k:case[k] for k in ['cluster_id','target_slot','seed','input_profile','text_profile','target_layout']} | {'known':sorted(case['known'],key=lambda d:d['slot'])}


def finite_tree(obj):
    if isinstance(obj,float) and not math.isfinite(obj): raise ValueError('non-finite prediction')
    if isinstance(obj,dict):
        for v in obj.values(): finite_tree(v)
    elif isinstance(obj,list):
        for v in obj: finite_tree(v)


def validate_prediction(row):
    fields(row,'schema_version set_id cluster_id seed target_slot protocol_hash input_hash template_hash extractor_hash model_hash primary forced_primary_pick views')
    finite_tree(row)
    from .protocol import PROTOCOL_HASH
    if row['schema_version']!=2 or row['protocol_hash']!=PROTOCOL_HASH or row['primary'] not in ['J24.PROTO','J24.CAL'] or row['primary'] not in row['views']:
        raise ValueError('unsupported prediction schema/protocol/primary')
    for v in row['views'].values():
        fields(v,'family status reason scores delta pick active_channels coverage')
        fields(v['scores'],'A B')
        if v['family'] not in ['PROTO','CAL'] or v['status'] not in ['DECIDED','TIE','NA']:raise ValueError('invalid prediction state')
        a,b=v['scores']['A'],v['scores']['B'];d=v['delta'];eps=DEFAULT['tie_epsilon']
        if v['status']=='NA':
            if v['pick'] is not None or d is not None or a is not None or b is not None or v['active_channels']:raise ValueError('NA cannot contain evidence or a hidden decision')
        else:
            if not v['active_channels'] or any(type(x) not in [int,float] for x in [a,b,d]) or abs((a-b)-d)>eps:raise ValueError('prediction scores/delta inconsistent')
            if v['family']=='CAL' and not(-eps<=a<=1+eps and -eps<=b<=1+eps):raise ValueError('typicality score out of range')
            if v['status']=='TIE' and (abs(d)>eps or v['pick'] is not None):raise ValueError('invalid tie')
            if v['status']=='DECIDED' and (abs(d)<=eps or v['pick']!=('A' if d>0 else 'B')):raise ValueError('invalid signed decision')
    primary=row['views'][row['primary']]
    expected=primary['pick'] if primary['status']=='DECIDED' else None
    if primary['status']=='TIE':
        if row['forced_primary_pick'] not in ['A','B']:raise ValueError('valid primary tie requires a reproducible coin')
    elif row['forced_primary_pick']!=expected:raise ValueError('forced primary does not match its evidence')
