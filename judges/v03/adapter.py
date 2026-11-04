"""Optional corpus adapter. Never imported by the blind predictor."""
from __future__ import annotations

from collections import defaultdict
import csv
import gzip
from pathlib import Path
import random
import re
import runpy
import sys

from ..schema import glyphs
from .observations import scopes
from .protocol import DEFAULT, PROTOCOL_HASH, digest, file_hash, read_json, write_json, write_jsonl
from .schema import validate_case, validate_doc


def source_context(package):
    package=Path(package).resolve();sys.path.insert(0,str(package/'model/code'))
    g=runpy.run_path(str(package/'model/code/run_v22_3_stage3d.py'),run_name='judges_v03_export')
    return g['benv'].e.context(),g,sys.modules['build_full_schedule']


def source_documents(package):
    C,g,builder=source_context(package)
    raw_path=g['rb'].ep.DATA/'ZL3b-n.txt'
    raw=defaultdict(list)
    for line in raw_path.read_text().splitlines():
        m=re.match(r'^<([^>]+)>\s*(.*)$',line)
        if not m or ',' not in m[1] or '.' not in m[1]:continue
        locus,tag=m[1].split(',',1);page=locus.split('.')[0]
        if len(tag)>1 and tag[1]=='P':raw[page].append((locus,tag,m[2]))
    docs={};page_loci={};population=[];f1lf=set()
    pages=sorted({str(p) for b in C.bifs for p in C.pages[b]})
    for page in pages:
        tok={str(loc):gg.sort_values('global_order') for loc,gg in C.T[C.T.page.eq(page)].groupby('locus',sort=False)}
        ev={str(loc):gg.sort_values('global_order') for loc,gg in C.events[C.events.page.eq(page)].groupby('locus',sort=False)}
        if not set(tok)<=set(loc for loc,tag,text in raw[page]):raise ValueError('raw source line table missing schedule loci')
        frames=[];observations=[];loci=[];previous=None
        for li,(loc,tag,text) in enumerate(raw[page],1):
            group=tok.get(loc);items=builder.raw_items(text)
            if loc=='f28v.7':items=[x for x in items if x[0]!='B']
            reasons=[];sf=[];segments=[]
            if group is None:
                reasons=['MISSING_SOURCE_LINE']
                if previous and previous['paragraph'] is not None and previous['paragraph_line'] is not None and tag.startswith(('+','=')) and '<%>' not in text and previous['paragraph_final'] is False:
                    para,pline=previous['paragraph'],previous['paragraph_line']+1
                else:para,pline=None,None
                # Raw boundary markers remain structural evidence, even without recognized words.
                sf=[{'end':'PLANT' if j<sum(k=='B' for k,v in items) else 'LINE_END','end_word_known':False,'end_predecessor_known':None} for j in range(sum(k=='B' for k,v in items)+1)]
                segments=[{'mode':'NONE'} for _ in sf];mapping=None;multi=None;whole=False
            else:
                first=group.iloc[0];para=int(first.para);pline=int(first.para_line_raw)
                schedule_segs=list(group.groupby('segment_id',sort=True))
                whole=bool(items) and not any(k=='X' for k,v in items) and [v for k,v in items if k=='W']==group.surface.astype(str).tolist()
                if any(k=='X' for k,v in items):reasons.append('UNPARSEABLE_SPAN')
                if [v for k,v in items if k=='W']!=group.surface.astype(str).tolist():reasons.append('ORDER_MISMATCH')
                raw_parts=[[]]
                for item in items:
                    if item[0]=='B':raw_parts.append([])
                    else:raw_parts[-1].append(item)
                aligned=len(raw_parts)==len(schedule_segs)
                if not aligned:
                    whole=False;reasons.append('UNKNOWN_STRUCTURE')
                if any(not x for x in raw_parts):whole=False;reasons.append('EMPTY_SEGMENT')
                event=ev[loc]
                mapping=bool(event.mapping_quality.astype(str).eq('EXACT_W_SEQUENCE').all())
                multi=len(C.df[C.df.locus.eq(loc)])>1
                for j,(sid,sg) in enumerate(schedule_segs):
                    last=sg.iloc[-1];part=raw_parts[j] if aligned else []
                    known=bool(part and part[-1][0]=='W' and part[-1][1]==str(last.surface))
                    se=event[event.segment_id.eq(sid)]
                    before=not str(se.iloc[-1].boundary_before)=='UNKNOWN_GAP' if len(se) else None
                    sf.append({'end':str(last.boundary_type),'end_word_known':known,'end_predecessor_known':before})
                    if whole:
                        if not known:raise ValueError('clean schedule terminal differs from raw source')
                        segments.append({'mode':'FULL','tokens':sg.surface.astype(str).tolist()})
                    elif known:segments.append({'mode':'END_ONLY','end_word':str(last.surface)})
                    else:segments.append({'mode':'NONE'})
                if not whole and not reasons:reasons.append('UNCONFIRMED_ENDPOINT')
            frame={'line_no':li,'paragraph':para,'paragraph_line':pline,'paragraph_final':bool('<$>' in text),
                'layout_mode':'LINEAR_PARAGRAPH','whole_line_usable':whole,'mapping_exact':mapping,
                'source_multiword':multi,'mask_reasons':sorted(set(reasons)),'segments':sf}
            frames.append(frame);observations.append({'segments':segments});loci.append(loc);previous=frame
            if sf and 'F1LF' in scopes(frame,len(sf)-1):
                if sf[-1]['end_word_known']:f1lf.add((page,loc))
            population.append({'page':page,'locus':loc,'whole_line_usable':whole,'endpoint_segments':sum(x['end_word_known'] for x in sf),'missing_source_tokens':group is None})
        doc={'layout':{'lines':frames},'observations':{'lines':observations}}
        validate_doc(doc)
        docs[page]=doc;page_loci[page]=loci
    with (Path(package)/'model/parameters/F1LF_STRICT_SCOPE_88.csv').open() as f:
        strict={(r['page'],r['locus']) for r in csv.DictReader(f)}
    if f1lf!=strict:
        raise ValueError('structural F1LF/ledger mismatch: '+str({'extra':sorted(f1lf-strict),'missing':sorted(strict-f1lf)}))
    folds={str(r.bif):int(r.fold) for r in g['SEL'].reset_index().itertuples()}
    corpus={'schema_version':2,'protocol_hash':PROTOCOL_HASH,'input_profile':'structure-endpoints-v2',
        'source_hashes':{'raw':file_hash(raw_path),'ledger':file_hash(Path(package)/'model/parameters/F1LF_STRICT_SCOPE_88.csv')},
        'bifolia':[{'cluster_id':digest('cluster/'+str(b))[:16], # overwritten below to preserve v02 cluster binding
            'fold':folds[str(b)],'pages':[{'slot':i,**docs[str(p)]} for i,p in enumerate(C.pages[b])]} for b in sorted(C.bifs)]}
    import hashlib
    for rec,b in zip(corpus['bifolia'],sorted(C.bifs)):
        rec['cluster_id']=hashlib.sha256(('cluster/'+str(b)).encode()).hexdigest()[:16]
    provenance={'population':population,'page_loci':page_loci,'f1lf_endpoints':len(f1lf),'restored_source_lines':sum(x['missing_source_tokens'] for x in population)}
    return C,corpus,docs,page_loci,provenance


def export(plan,output):
    allowed={'package','generated_root','model_dir','runs','bifolia','blinding_seed'}
    if set(plan)!=allowed:raise ValueError('export plan fields must be '+str(sorted(allowed)))
    C,corpus,docs,loci,source_info=source_documents(plan['package'])
    selected=sorted(C.bifs if plan['bifolia'] is None else plan['bifolia']);runs=plan['runs']
    if not selected or not runs or len(set(selected))!=len(selected) or not set(selected)<=set(C.bifs) or any(type(x) is not int for x in runs) or len(set(runs))!=len(runs):raise ValueError('invalid bifolia/runs')
    flags=[True]*(len(selected)*len(runs)//2)+[False]*(len(selected)*len(runs)//2)
    rng=random.Random(plan['blinding_seed'])
    if len(flags)<len(selected)*len(runs):flags.append(bool(rng.getrandbits(1)))
    rng.shuffle(flags)
    corpus_by={r['cluster_id']:r for r in corpus['bifolia']}
    cases=[];keys=[];provenance=[]
    import hashlib
    for bif in selected:
        cluster=hashlib.sha256(('cluster/'+bif).encode()).hexdigest()[:16]
        refs=corpus_by[cluster]['pages'][:3];page=str(C.pages[bif][-1]);true=docs[page]
        for run in runs:
            path=Path(plan['generated_root'])/f'run{run}'/plan['model_dir']/bif.replace(':','_')/'tokens.csv.gz'
            with gzip.open(path,'rt') as f:rows=list(csv.DictReader(f))
            if not rows or {r['page'] for r in rows}!={page} or {int(r['run']) for r in rows}!={run}:raise ValueError('wrong generated page/run')
            by=defaultdict(lambda:defaultdict(list))
            for r in rows:by[r['locus']][int(r['segment_id'])].append(r)
            if set(by)!=set(C.T[C.T.page.eq(page)].locus.astype(str)):raise ValueError('generated loci differ from frozen schedule')
            fake=[]
            for frame,loc in zip(true['layout']['lines'],loci[page]):
                ss=[]
                for si,sf in enumerate(frame['segments']):
                    mode='FULL' if frame['whole_line_usable'] else 'END_ONLY' if sf['end_word_known'] else 'NONE'
                    if mode=='NONE':ss.append({'mode':'NONE'});continue
                    rr=sorted(by[loc][si],key=lambda r:int(r['segment_wordnum']))
                    if not rr or {r['boundary_type'] for r in rr}!={sf['end']} or [int(r['segment_wordnum']) for r in rr]!=list(range(1,len(rr)+1)) or [int(r['draw_segment_end']) for r in rr]!=[0]*(len(rr)-1)+[1]:
                        raise ValueError('invalid generated segment: '+str((run,bif,loc,si)))
                    def visible(r):
                        gs=glyphs(r['surface'])
                        if not gs:raise ValueError('invalid generated visible token')
                        return ''.join(gs)
                    ss.append({'mode':'FULL','tokens':[visible(r) for r in rr]} if mode=='FULL' else {'mode':'END_ONLY','end_word':visible(rr[-1])})
                fake.append({'segments':ss})
            side='A' if flags[len(cases)] else 'B'
            cid=digest(['v03',cluster,3,run])[:24]
            c={'schema_version':2,'protocol_id':DEFAULT['protocol_id'],'set_id':cid,'cluster_id':cluster,'seed':run,'target_slot':3,
                'text_profile':'stable22-visible','input_profile':'structure-endpoints-v2','known':refs,'target_layout':true['layout'],
                'candidates':{side:true['observations'],'B' if side=='A' else 'A':{'lines':fake}}}
            validate_case(c);cases.append(c);keys.append({'set_id':cid,'truth':side})
            provenance.append({'set_id':cid,'bif':bif,'page':page,'generated_file':str(path.resolve()),'generated_sha256':file_hash(path)})
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_jsonl(output/'inputs.jsonl',cases);write_jsonl(output/'answer_key.jsonl',keys);write_json(output/'corpus.json',corpus)
    write_json(output/'export_manifest.json',{'protocol_hash':PROTOCOL_HASH,'plan':plan,'sets':len(cases),'source':source_info,'provenance':provenance,'corpus_hash':digest(corpus),
        'inputs_sha256':file_hash(output/'inputs.jsonl'),'answer_key_sha256':file_hash(output/'answer_key.jsonl')})
    return len(cases)
