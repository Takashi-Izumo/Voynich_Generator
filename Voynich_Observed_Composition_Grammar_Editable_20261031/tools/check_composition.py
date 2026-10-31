#!/usr/bin/env python3
"""Check original user-written Voynich-A-style paragraphs against a corpus-induced surface grammar.
This is NOT a text generator and it does NOT evaluate meanings. Requires Python 3 standard library only.
Run from any directory: python tools/check_composition.py examples/grade_A_original.eva --level A
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'
COMPOSITES=('cfh','ckh','cph','cth','ch','sh')
ALPHABET={'q','cfh','ch','cph','cth','p','sh','ckh','f','k','o','t','a','d','e','s','i','l','y','r','m','n','g'}
ALTERNATIONS={('ch','sh'),('sh','ch'),('k','t'),('t','k'),('l','r'),('r','l'),('o','a'),('a','o')}

def glyphs(w):
    g=[];i=0
    while i<len(w):
        x=next((z for z in COMPOSITES if w.startswith(z,i)),w[i]);g.append(x);i+=len(x)
    return tuple(g)

def forms_and_ngrams():
    with (DATA/'attested_lexicon.csv').open(encoding='utf-8',newline='') as f:
        byform={row['form']:row for row in csv.DictReader(f)}
    with (DATA/'word_internal_bigrams.csv').open(encoding='utf-8',newline='') as f:
        bgs={(r['left'],r['right']) for r in csv.DictReader(f)}
    with (DATA/'word_internal_trigrams.csv').open(encoding='utf-8',newline='') as f:
        tgs={(r['a'],r['b'],r['c']) for r in csv.DictReader(f)}
    return byform,bgs,tgs

def expected_roles(words,i,nlines):
    if i==0:return ['PHW']+['F1_BODY']*(len(words)-2)+['F1_LF']
    if i==nlines-1:return ['PF_HEAD']+['PF_BODY']*(len(words)-2)+['PF_LF']
    return ['HEAD','W2']+['BODY']*(len(words)-3)+['LF']

def route4(words):
    out=set()
    for w in words:
        g=glyphs(w)
        for i in range(len(g)-3):out.add(tuple(g[i:i+4]))
    return out

def novelty_parents(word,role,byform,bgs,tgs):
    g=glyphs(word)
    if not (1<=len(g)<=10) or not all(x in ALPHABET for x in g):return []
    if any((a,b) not in bgs for a,b in zip(g,g[1:])):return []
    if any((a,b,c) not in tgs for a,b,c in zip(g,g[1:],g[2:])):return []
    parents=[]
    for i,x in enumerate(g):
        for a,b in ALTERNATIONS:
            if x!=b:continue
            h=list(g);h[i]=a;base=''.join(h)
            if base in byform and int(byform[base].get(role,0))>0:
                parents.append({'attested_parent':base,'change':f'{a}>{b} at glyph {i+1}'})
    # Optional i-repeat: insertion or deletion of exactly one i, based on the corpus's variable i-runs.
    for i in range(len(g)+1):
        h=list(g);h.insert(i,'i');base=''.join(h)
        if base in byform and int(byform[base].get(role,0))>0:
            parents.append({'attested_parent':base,'change':f'delete i at glyph {i+1}'})
    for i,x in enumerate(g):
        if x!='i':continue
        h=list(g);h.pop(i);base=''.join(h)
        if base in byform and int(byform[base].get(role,0))>0:
            parents.append({'attested_parent':base,'change':f'insert i at glyph {i+1}'})
    return sorted(parents,key=lambda p:(p['attested_parent'],p['change']))

def parse(text):
    paras=[]; cur=[]
    for line in text.splitlines():
        line=line.strip()
        if not line or line=='---':
            if cur:paras.append(cur);cur=[]
            continue
        if line.startswith('#'):continue
        words=[x for x in re.split(r'[\s.]+',line) if x]
        cur.append(words)
    if cur:paras.append(cur)
    return paras

def validate(text,level='A',strict_roles=True):
    byform,bgs,tgs=forms_and_ngrams()
    paragraphs=parse(text);issues=[];warnings=[];parsed=[];total=0;novel=[]
    def fail(message):issues.append(message)
    def warn(message):warnings.append(message)
    if not paragraphs:fail('No paragraphs found.')
    for pi,lines in enumerate(paragraphs,1):
        if len(lines)<3:
            fail(f'P{pi}: the conservative classroom grammar requires at least 3 lines (rare attested 2-line paragraphs lie outside it).')
        if len(lines)>23:warn(f'P{pi}: more than 23 lines (outside observed range).')
        parsed_lines=[]
        for li,words in enumerate(lines):
            minwords=2 if li==0 or li==len(lines)-1 else 3
            if len(words)<minwords:
                fail(f'P{pi} L{li+1}: {len(words)} words but classroom minimum is {minwords}.')
            if not words:continue
            if len(words)>13:warn(f'P{pi} L{li+1}: >13 words, outside observed sample.')
            if li==0 and len(words)>=1 and glyphs(words[0])[0] not in {'p','f','k','t'}:
                warn(f'P{pi} L1: first word {words[0]} does not start with a gallows; observed first-line rate is 82.9%, not 100%.')
            if len(words)<minwords: continue
            rr=expected_roles(words,li,len(lines))
            if len(rr)!=len(words):continue
            vals=[]
            for wi,(w,r) in enumerate(zip(words,rr),1):
                total+=1;g=glyphs(w)
                base={'word':w,'role':r,'glyph_length':len(g),'observed':w in byform}
                if any(x not in ALPHABET for x in g):
                    fail(f'P{pi} L{li+1} W{wi}: glyph out of the observed 23-glyph inventory: {w}.')
                if not 1<=len(g)<=10:
                    fail(f'P{pi} L{li+1} W{wi}: {len(g)} glyphs, outside observed 1-10 range.')
                if w in byform:
                    ct=int(byform[w].get(r,0))
                    base['observed_at_role']=ct
                    if ct==0:
                        msg=f'P{pi} L{li+1} W{wi}: {w} exists in corpus, but has no observed {r} occurrence.'
                        if strict_roles:fail(msg)
                        else:warn(msg)
                elif level=='A':
                    fail(f'P{pi} L{li+1} W{wi}: {w} is not attested; level A allows only observed complete words.')
                else:
                    if any(pair not in bgs for pair in zip(g,g[1:])):
                        fail(f'P{pi} L{li+1} W{wi}: {w} contains an unobserved word-internal bigram.')
                    elif any(trip not in tgs for trip in zip(g,g[1:],g[2:])):
                        fail(f'P{pi} L{li+1} W{wi}: {w} contains an unobserved word-internal trigram.')
                    else:
                        parents=novelty_parents(w,r,byform,bgs,tgs)
                        base['parents']=parents[:4]
                        if level=='B' and not parents:
                            fail(f'P{pi} L{li+1} W{wi}: {w} needs one licensed edit from an attested word used in role {r} (level B).')
                        else:
                            novel.append({'form':w,'role':r,'parents':parents[:4]})
                            if level=='C' and not parents:
                                warn(f'P{pi} L{li+1} W{wi}: {w} is exploratory C (no attested one-edit role analogue).')
                vals.append(base)
            parsed_lines.append(vals)
        carry=[]
        if len(lines)>=3:
            shared=route4(lines[1]) & route4(lines[2])
            carry=['.'.join(x) for x in sorted(shared)]
            if not shared:warn(f'P{pi}: no L2/L3 shared 4-glyph path; this is allowed, since carryover is an empirical preference, not a rule.')
        parsed.append({'paragraph':pi,'lines':len(lines),'line_slots':parsed_lines,'l2_l3_shared_4glyph_routes':carry})
    return {'status':'PASS' if not issues else 'FAIL','level':level,'strict_role_evidence':strict_roles,
        'paragraphs':len(paragraphs),'words':total,'novel_words':novel,'errors':issues,'advisories':warnings,'parsed':parsed,
        'meaning_verified':False,'scope':'surface-structure only, pure Herbal A (not semantic decipherment)'}

def main():
    ap=argparse.ArgumentParser(description='Corpus-derived VSL-A surface composition checker (NOT a generator).')
    ap.add_argument('text_file',nargs='?',help='An EVA passage; newline=line, blank line=paragraph.')
    ap.add_argument('--level',choices=['A','B','C'],default='A',help='A: observed words; B: licensed one-edit innovations; C: experimental n-gram-only forms.')
    ap.add_argument('--relax-roles',action='store_true',help='Make zero-attested-role cases advisory rather than failures.')
    ap.add_argument('--json',action='store_true',help='Print full structured audit.')
    ap.add_argument('--list-role',choices=['PHW','F1_BODY','F1_LF','HEAD','W2','BODY','LF','PF_HEAD','PF_BODY','PF_LF'])
    a=ap.parse_args()
    if a.list_role:
        db,_,_=forms_and_ngrams()
        ranked=sorted(((w,int(x[a.list_role])) for w,x in db.items() if int(x[a.list_role])>0),key=lambda t:(-t[1],t[0]))
        print(f'{a.list_role}: {len(ranked)} observed types; most frequent 30:')
        for w,n in ranked[:30]:print(f'  {w:<17} {n:>4}')
        return
    if not a.text_file:ap.error('Provide an input EVA text file or --list-role.')
    result=validate(Path(a.text_file).read_text(encoding='utf-8'),a.level,not a.relax_roles)
    if a.json:print(json.dumps(result,indent=2,ensure_ascii=False))
    else:
        print(f'{result["status"]} -- evidence class {result["level"]}; {result["paragraphs"]} paragraphs, {result["words"]} words; {len(result["novel_words"])} novel words')
        for p in result['parsed']:
            print(f'  Paragraph {p["paragraph"]}: {p["lines"]} lines; L2/L3 shared 4-glyph routes: {", ".join(p["l2_l3_shared_4glyph_routes"][:12]) or "none"}')
        for x in result['errors']:print('  ERROR:',x)
        for x in result['advisories']:print('  NOTE:',x)
        print('Validation is formal/orthographic only; no semantic or syntactic translation claim.')
    raise SystemExit(0 if result['status']=='PASS' else 1)

if __name__=='__main__':main()
