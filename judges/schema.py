from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

GLYPHS = ('q', 'cfh', 'ch', 'cph', 'cth', 'p', 'sh', 'ckh', 'f', 'k', 'o', 't', 'a', 'd', 'e', 's', 'i', 'l', 'y', 'r', 'm', 'n')
COMPOUNDS = ('cfh', 'ckh', 'cph', 'cth', 'ch', 'sh')
RARE = frozenset('bgjvzu')
WIDTH = {g: 4 if g in COMPOUNDS[:4] else 2 if g in ('ch', 'sh', 'p', 'f', 'k', 't') else 1 for g in GLYPHS}


def glyphs(text: str | None) -> tuple[str, ...] | None:
    if text is None:
        return None
    text = ''.join(c for c in text if c not in RARE)
    out = []
    i = 0
    while i < len(text):
        hit = next((g for g in COMPOUNDS if text.startswith(g, i)), None)
        if hit:
            out.append(hit)
            i += len(hit)
        elif text[i] in GLYPHS:
            out.append(text[i])
            i += 1
        else:
            return None
    return tuple(out) or None


def validate_doc(doc: dict) -> None:
    if not isinstance(doc, dict) or set(doc) != {'lines'} or not isinstance(doc['lines'], list) or not doc['lines']:
        raise ValueError('document must contain a nonempty lines list only')
    finished = set()
    previous = None
    for line in doc['lines']:
        if not isinstance(line, dict) or set(line) - {'paragraph', 'segments', 'excluded'} or not {'paragraph', 'segments'} <= set(line):
            raise ValueError('invalid line fields')
        para = line['paragraph']
        if type(para) not in (str, int) or para == '':
            raise ValueError('paragraph must be a nonempty string or integer')
        # Typed IDs avoid conflating integer 1 and string "1".
        para = (type(para).__name__, para)
        if para != previous:
            if para in finished:
                raise ValueError('paragraphs must be contiguous')
            if previous is not None:
                finished.add(previous)
            previous = para
        if type(line.get('excluded', False)) is not bool:
            raise ValueError('excluded must be boolean')
        segs = line['segments']
        if line.get('excluded', False):
            if segs != []:
                raise ValueError('excluded line must have segments=[]')
            continue
        if not isinstance(segs, list) or not segs:
            raise ValueError('line must have segments')
        for i, seg in enumerate(segs):
            if not isinstance(seg, dict) or set(seg) != {'end', 'tokens'}:
                raise ValueError('segment must contain end and tokens only')
            if seg['end'] != ('LINE_END' if i == len(segs)-1 else 'PLANT'):
                raise ValueError('interior segments end at PLANT; last segment at LINE_END')
            if not isinstance(seg['tokens'], list) or not seg['tokens']:
                raise ValueError('empty segment')
            if any(t is not None and (not isinstance(t, str) or not t or any(c.isspace() for c in t)) for t in seg['tokens']):
                raise ValueError('token must be a nonempty whitespace-free string or null')


def validate_case(case: dict) -> None:
    required = {'schema_version', 'set_id', 'cluster_id', 'seed', 'text_profile', 'known', 'candidates'}
    if not isinstance(case, dict) or set(case) != required:
        raise ValueError(f'case fields must be exactly {sorted(required)}; answer/provenance fields are forbidden')
    if type(case['schema_version']) is not int or case['schema_version'] != 1:
        raise ValueError('unsupported schema_version')
    if any(not isinstance(case[k], str) or not case[k] for k in ('set_id', 'cluster_id')):
        raise ValueError('set_id and cluster_id must be nonempty strings')
    if type(case['seed']) is not int or case['text_profile'] not in ('stable22', 'raw'):
        raise ValueError('invalid seed/text_profile')
    if not isinstance(case['known'], list) or len(case['known']) != 3:
        raise ValueError('exactly three known documents required')
    if not isinstance(case['candidates'], dict) or set(case['candidates']) != {'A', 'B'}:
        raise ValueError('exactly candidates A and B required')
    for doc in case['known'] + list(case['candidates'].values()):
        validate_doc(doc)
        if case['text_profile'] == 'stable22':
            for line in doc['lines']:
                for seg in line['segments']:
                    for token in seg['tokens']:
                        if token is not None and any(c in RARE for c in token):
                            raise ValueError('stable22 profile cannot retain rare characters')

    # This baseline is a shared-layout contest, not a free-layout profile.
    # Compare paragraph boundaries, not arbitrary local paragraph ID spellings.
    def layout_signature(doc):
        signature = []
        previous = None
        paragraph = -1
        for line in doc['lines']:
            key = (type(line['paragraph']).__name__, line['paragraph'])
            if key != previous:
                paragraph += 1
                previous = key
            signature.append((paragraph, line.get('excluded', False), tuple(s['end'] for s in line['segments'])))
        return signature

    if layout_signature(case['candidates']['A']) != layout_signature(case['candidates']['B']):
        raise ValueError('candidate shared layout/exclusion masks differ')
    for doc in case['known'] + list(case['candidates'].values()):
        if not any(glyphs(token) for line in doc['lines'] for seg in line['segments'] for token in seg['tokens']):
            raise ValueError('each document must contain observable glyphs')


def read_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding='utf-8') as f:
        result = [json.loads(line) for line in f if line.strip()]
    if not result:
        raise ValueError('empty JSONL input')
    return result


@dataclass(frozen=True)
class Event:
    g: tuple[str, ...] | None
    text: str | None
    line: int
    para: tuple
    pline: int
    first: bool
    final: bool
    ordinal: int
    segment: int
    position: int
    boundary: str
    prev: tuple[str, ...] | None
    role: str
    remaining: int | None

    @property
    def atom(self) -> str:
        if self.boundary == 'P':
            return 'PLANT_END'
        if self.boundary == 'L':
            return 'PARA_END' if self.final else 'LINE_END'
        if self.first:
            return 'PHW' if self.ordinal == 0 else 'FIRST_INTERIOR'
        if self.ordinal == 0:
            return 'HEAD'
        if self.ordinal == 1:
            return 'W2'
        return 'BODY'


def events(doc: dict) -> list[Event]:
    """Raw positions survive unknown words. PLANT resets SPACE, not paragraph."""
    lines = doc['lines']
    last = {}
    for i, line in enumerate(lines):
        last[(type(line['paragraph']).__name__, line['paragraph'])] = i
    plines = {}
    out = []
    for li, line in enumerate(lines):
        para = (type(line['paragraph']).__name__, line['paragraph'])
        plines[para] = plines.get(para, 0) + 1
        pl = plines[para]
        ordinal = 0
        for si, seg in enumerate(line['segments']):
            gs = [glyphs(t) for t in seg['tokens']]
            for wi, (text, g) in enumerate(zip(seg['tokens'], gs)):
                boundary = ('P' if seg['end'] == 'PLANT' else 'L') if wi == len(gs)-1 else 'I'
                role = 'BODY' if si else 'PHW' if pl == 1 and ordinal == 0 else 'F1' if pl == 1 else 'HEAD' if ordinal == 0 else 'W2' if ordinal == 1 else 'BODY'
                remaining = None if any(x is None for x in gs[wi:]) else sum(sum(WIDTH[c] for c in x) for x in gs[wi:]) + len(gs)-wi-1
                out.append(Event(g, text, li, para, pl, pl == 1, last[para] == li, ordinal, si, wi, boundary, gs[wi-1] if wi else None, role, remaining))
                ordinal += 1
    return out
