from __future__ import annotations

from collections import Counter, OrderedDict
from functools import lru_cache
from ..features import Feature, extract as legacy_extract
from ..registry import ATOMS, NAMES
from .observations import endpoints, legacy_doc, scopes, word_events
from .protocol import digest


def sample_n(feature):
    return feature.events if feature.events is not None else int(round(sum(feature.counts.values())))


_CACHE = OrderedDict()


def extract(doc, references):
    key=(digest(doc),tuple(sorted(digest(r) for r in references)))
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    value=_extract(doc,references)
    _CACHE[key]=value
    if len(_CACHE)>512:_CACHE.popitem(last=False)
    return value


def _extract(doc, references):
    old=legacy_doc(doc);es=word_events(doc)
    base=legacy_extract(old,[legacy_doc(r) for r in references],'stable22',event_list=es)
    result={k.replace('ATOM:','ATOM.'):v for k,v in base.items() if not k.startswith(('J08/','J11/'))}
    for length in [3,4,5]:
        result[f'J11.L{length}.H2/H2']=base.get(f'J11/L{length}',Feature(conditional=True))
    for scope in ['WIDE','F1LF','POSTPLANT']:
        for part in ['SHORT','LONG','JOINT','TERM']:
            result[f'J08.{scope}/{part}']=Feature(conditional=part=='TERM')
    for e in endpoints(doc):
        if e.end!='LINE_END':continue
        band='SHORT' if len(e.g)<=3 else 'LONG'
        for scope in scopes(doc['layout']['lines'][e.line],e.segment):
            result[f'J08.{scope}/{band}'].counts[e.g[-1]]+=1
            result[f'J08.{scope}/JOINT'].counts[band,e.g[-1]]+=1
            result[f'J08.{scope}/TERM'].counts[(band,),e.g[-1]]+=1
    support=Counter()
    for li,frame in enumerate(doc['layout']['lines']):
        if not(frame['whole_line_usable'] and frame['paragraph_line'] is not None and frame['paragraph_line']>1 and frame['paragraph_final'] is False):continue
        words=[e for e in es if e.line==li and e.segment==0]
        if len(words)<2:support[('ABSENT',)]+=1
        else:
            w=words[1];support[('END' if w.boundary!='I' else 'INTERIOR',min(len(w.g),6),w.g[0])]+=1
    result['J11.SUPPORT/joint']=Feature(support)
    return result


def groups(channels, family):
    result={}
    for name in NAMES:
        if name not in ['J08','J11','J24']:
            result[name]=[k for k in channels if k.startswith(name+'/')]
    for atom in ATOMS:
        name='ATOM.'+atom;result[name]=[k for k in channels if k.startswith(name+'/')]
    for scope in ['WIDE','F1LF','POSTPLANT']:
        name='J08.'+scope
        result[name]=[name+'/'+part for part in (['SHORT','LONG'] if family=='PROTO' else ['TERM'])]
        for part in ['SHORT','LONG','JOINT']:result[name+'.'+part]=[name+'/'+part]
    result['J11.H2']=[f'J11.L{length}.H2/H2' for length in [3,4,5]]
    for length in [3,4,5]:result[f'J11.L{length}.H2']=[f'J11.L{length}.H2/H2']
    result['J11.SUPPORT']=['J11.SUPPORT/joint']
    return result


def conditional_spec(name, feature):
    if name.startswith('J08.') and name.rsplit('/',1)[-1] in ['SHORT','LONG','TERM']:
        return {'contexts':2,'outcomes':None}
    if not feature.conditional:return None
    count=22
    if name.startswith('J12/'):count=3*22
    elif name in ['J09/H3','J15/bT_H1']:count=22*22
    elif name.startswith('J10/'):count=5*22
    elif name.startswith('J14/'):return {'contexts':10,'outcomes':['NMY','LR','OTHER']}
    return {'contexts':count,'outcomes':None}


def conditional_counts(name,feature):
    part=name.rsplit('/',1)[-1]
    if name.startswith('J08.') and part in ['SHORT','LONG']:
        return Counter({((part,),outcome):n for outcome,n in feature.counts.items()})
    return feature.counts


def observation_counts(doc, features):
    """Unique observations for a display; not the maximum/sum of overlapping channels."""
    es=word_events(doc)
    selections={
        'J01':lambda e:e.first and e.ordinal==0,'J02':lambda e:e.first,
        'J03':lambda e:not e.first and e.ordinal==0,'J04':lambda e:not e.first and e.ordinal==1,
        'J05':lambda e:e.ordinal>=2,'J06':lambda e:e.boundary=='L','J07':lambda e:e.final,
        'J09':lambda e:e.role=='HEAD' and len(e.g)>=2,
        'J12':lambda e:e.role=='BODY' and e.boundary=='I' and 2<=len(e.g)<=4,
        'J15':lambda e:e.prev is not None,'J16':lambda e:len(e.g)>=2,
        'J17':lambda e:len(e.g)>=3,'J18':lambda e:True,'J19':lambda e:True,
        'J20':lambda e:True,'J21':lambda e:False,
        'J22':lambda e:e.boundary=='P' or (e.segment>0 and e.position==0),
        'J23':lambda e:True,'J24':lambda e:True,'J25':lambda e:e.prev is not None}
    result={name:sum(test(e) for e in es) for name,test in selections.items()}
    for name,key in [('J10','J10/vertical'),('J13','J13/visible_history'),('J14','J14/relative_remaining')]:
        result[name]=sample_n(features.get(key,Feature()))
    for atom in ATOMS:result['ATOM.'+atom]=sum(e.atom==atom for e in es)
    for scope in ['WIDE','F1LF','POSTPLANT']:
        ee=[e for e in endpoints(doc) if scope in scopes(doc['layout']['lines'][e.line],e.segment)]
        name='J08.'+scope
        result[name]=result[name+'.JOINT']=len(ee)
        result[name+'.SHORT']=sum(len(e.g)<=3 for e in ee)
        result[name+'.LONG']=sum(len(e.g)>=4 for e in ee)
    selected=[e for e in es if e.role=='W2' and not e.first and not e.final and e.boundary=='I' and 3<=len(e.g)<=5]
    result['J11.H2']=len(selected)
    for length in [3,4,5]:result[f'J11.L{length}.H2']=sum(len(e.g)==length for e in selected)
    result['J11.SUPPORT']=sum(f['whole_line_usable'] and f['paragraph_line'] is not None and f['paragraph_line']>1 and f['paragraph_final'] is False for f in doc['layout']['lines'])
    return result
