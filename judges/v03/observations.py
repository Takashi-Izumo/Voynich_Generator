from __future__ import annotations

from dataclasses import dataclass
from ..schema import Event, WIDTH, glyphs


@dataclass(frozen=True)
class EndpointObservation:
    line: int
    segment: int
    g: tuple[str,...]
    end: str
    mode: str


def legacy_doc(doc):
    lines=[]
    for frame,data in zip(doc['layout']['lines'],doc['observations']['lines']):
        full=frame['whole_line_usable']
        lines.append({'paragraph':frame['paragraph'] if frame['paragraph'] is not None else f'unknown-{frame["line_no"]}',
            'segments':[{'end':sf['end'],'tokens':so['tokens']} for sf,so in zip(frame['segments'] or [],data['segments'] or [])] if full else [],
            **({} if full else {'excluded':True})})
    return {'lines':lines}


def word_events(doc):
    result=[]
    for li,(frame,data) in enumerate(zip(doc['layout']['lines'],doc['observations']['lines'])):
        if not frame['whole_line_usable']: continue
        ordinal=0;pl=frame['paragraph_line'];first=pl==1
        for si,(sf,so) in enumerate(zip(frame['segments'],data['segments'])):
            gs=[glyphs(w) for w in so['tokens']]
            for wi,(w,g) in enumerate(zip(so['tokens'],gs)):
                role='BODY' if si else 'PHW' if first and ordinal==0 else 'F1' if first else 'HEAD' if ordinal==0 else 'W2' if ordinal==1 else 'BODY'
                end=('P' if sf['end']=='PLANT' else 'L') if wi==len(gs)-1 else 'I'
                remaining=sum(sum(WIDTH[c] for c in x) for x in gs[wi:])+len(gs)-wi-1
                result.append(Event(g,w,li,('int',frame['paragraph']),pl,first,frame['paragraph_final'],ordinal,si,wi,end,gs[wi-1] if wi else None,role,remaining))
                ordinal+=1
    return result


def endpoints(doc):
    result=[]
    for li,(frame,data) in enumerate(zip(doc['layout']['lines'],doc['observations']['lines'])):
        for si,(sf,so) in enumerate(zip(frame['segments'] or [],data['segments'] or [])):
            if so['mode']=='NONE': continue
            w=so['tokens'][-1] if so['mode']=='FULL' else so['end_word']
            result.append(EndpointObservation(li,si,glyphs(w),sf['end'],so['mode']))
    return result


def scopes(frame,si):
    if frame['paragraph_line']!=1 or frame['segments'] is None or frame['segments'][si]['end']!='LINE_END': return []
    out=['WIDE']
    if si>0: out.append('POSTPLANT')
    if (frame['paragraph_final'] is False and frame['layout_mode']=='LINEAR_PARAGRAPH' and si==0 and len(frame['segments'])==1
            and frame['source_multiword'] is True and frame['mapping_exact'] is True and frame['segments'][0]['end_predecessor_known'] is True):
        out.append('F1LF')
    return out
