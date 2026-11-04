"""Mechanical logs are deliberately outside the blind prediction path."""
from collections import Counter
import csv
import gzip
import json
from pathlib import Path
from ..schema import glyphs
from .protocol import file_hash,read_json,read_jsonl,write_json


def audit(manifest_path,generated_root,output):
    m=read_json(manifest_path);root=Path(generated_root).resolve();totals=Counter();cases=[]
    ip=Path(manifest_path).parent/'inputs.jsonl'
    if file_hash(ip)!=m['inputs_sha256']:raise ValueError('export input was changed')
    frames={c['set_id']:dict(zip(m['source']['page_loci'][p['page']],c['target_layout']['lines']))
        for c,p in zip(read_jsonl(ip),m['provenance']) if c['set_id']==p['set_id']}
    if len(frames)!=len(m['provenance']):raise ValueError('export provenance/case order mismatch')
    for item in m['provenance']:
        p=Path(item['generated_file']).resolve()
        if not p.is_relative_to(root) or file_hash(p)!=item['generated_sha256']:raise ValueError('generated path/hash mismatch')
        with gzip.open(p,'rt') as f:tokens=list(csv.DictReader(f))
        with gzip.open(p.with_name('requests.jsonl.gz'),'rt') as f:req=[r for r in (json.loads(s) for s in f) if r.get('committed_to_final_page')]
        tm={(t['locus'],int(t['segment_id']),int(t['line_wordnum'])-1):t for t in tokens}
        rm={(r['locus'],int(r['segment_id']),int(r['word_index'])):r for r in req}
        if len(tm)!=len(tokens) or len(rm)!=len(req) or set(tm)!=set(rm):raise ValueError('committed request/token alignment failed')
        count=Counter()
        for key,t in tm.items():
            r=rm[key]
            if glyphs(t['surface'])!=glyphs(r['final_surface']):raise ValueError('committed visible surface mismatch')
            count['tokens']+=1
            if r.get('v22_3_stage3d_strict_scope'):
                count['strict_committed']+=1;count['strict_applied']+=bool(r.get('v22_3_stage3d_applied'));count['strict_changed']+=bool(r.get('v22_3_stage3d_changed'))
            live=r['role']=='W2' and r['row_phase']=='MIDDLE' and r['board']=='W2' and not r['end'] and 3<=r['first_len']<=5
            if live:
                count['B2_live_scope']+=1;count['B2_applied']+=bool(r.get('b2_h2_applied'));count['B2_changed']+=bool(r.get('b2_h2_changed'))
                count['B2_masked']+=not frames[item['set_id']][t['locus']]['whole_line_usable']
            if r['role']=='W2' and r['row_phase']=='MIDDLE' and r['board']=='W2' and not r['end']:
                visible=3<=len(glyphs(t['surface']) or ())<=5
                if live!=visible:
                    count['B2_length_scope_crossing']+=1
                    if frames[item['set_id']][t['locus']]['whole_line_usable']:count['B2_visible_length_scope_crossing']+=1
                    if t['surface']==t['stable_surface']+'m':count['m_append']+=1
                    elif t['stable_surface']==t['surface']+'m':count['m_remove']+=1
                    else:count['other_visible_transform']+=1
        totals.update(count);cases.append({'set_id':item['set_id'],'counts':dict(count)})
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    result={'status':'mechanism_audit_not_blind_prediction','sets':len(cases),'totals':dict(totals),'cases':cases}
    write_json(output/'mechanism_audit.json',result)
    return {'sets':len(cases),'totals':dict(totals)}
