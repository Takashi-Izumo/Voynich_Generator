#!/usr/bin/env python3
"""Stateless SAME-INFO numerical judges. This program never reads an answer key.
Only one anonymized set plus its permitted training corpus enters each decision.
Scores/rationales are sealed before a separate scorer opens the answer key.
"""
from __future__ import annotations
import os
for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json, hashlib, math, collections, itertools, sys
from functools import lru_cache
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
ROOT=Path(__file__).resolve().parents[1]
GLYPHS=['q','cfh','ch','cph','cth','p','sh','ckh','f','k','o','t','a','d','e','s','i','l','y','r','m','n']
COMPOUNDS=['cfh','ckh','cph','cth','ch','sh']; STABLE=set(GLYPHS);RARE=set('bgjvzu')
WIDTH={g:(4 if g in COMPOUNDS[:4] else 2 if g in ['ch','sh','p','f','k','t'] else 1) for g in GLYPHS}
VEC_KINDS=['word','ng','bigram','trigram','route56','SPACE_T_H1','HEAD_shape','HEAD_vertical','LF_shape','length_width','glyph_depth']
BT_KINDS=['bT_LL','bT_leaf_excess','bT_active','bT_presence_log']
JUDGES=['word','ng','bigram','trigram','route56','combined']+BT_KINDS+VEC_KINDS[5:]+['SAMEINFO_panel']

def sha(x):return hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()
@lru_cache(maxsize=30000)
def glyph(s,clean=True):
    if clean:s=''.join(x for x in s if x not in RARE)
    out=[];i=0
    while i<len(s):
        h=next((g for g in COMPOUNDS if s.startswith(g,i)),None)
        if h:out.append(h);i+=len(h)
        elif s[i] in STABLE:out.append(s[i]);i+=1
        else:return ()
    return tuple(out)
def role(j,n):return 'LF' if j==n-1 else 'HEAD' if j==0 else 'W2' if j==1 else 'BODY'
def encoded(*x):return '|'.join(map(str,x))
def tokens(doc,kind):
    words=[w for ln in doc['lines'] for w in ln.split()]
    if kind=='word':return [''.join(c for c in w if c not in RARE) for w in words if ''.join(c for c in w if c not in RARE)] or ['EMPTY']
    if kind in ['ng','bigram','trigram','route56']:
        lo,hi={'ng':(2,4),'bigram':(2,2),'trigram':(3,3),'route56':(5,6)}[kind]
        out=[]
        for w in words:
            g=glyph(w)
            for n in range(lo,hi+1):out.extend(str(n)+'='+','.join(g[i:i+n]) for i in range(len(g)-n+1))
        return out or ['EMPTY']
    out=[];previous_head=None;previous_para=None
    lastline={m['para']:i for i,m in enumerate(doc['layout'])}
    for li,(ln,meta) in enumerate(zip(doc['lines'],doc['layout'])):
        gs=[glyph(w) for w in ln.split()];gs=[g for g in gs if g];n=len(gs)
        if not n:continue
        para=meta['para'];phase=meta['phase'];rp='FIRST' if phase==1 else 'FINAL' if lastline[para]==li else 'MIDDLE'
        if kind=='SPACE_T_H1':
            for j in range(1,n):out.append(encoded(rp,role(j,n),gs[j-1][-1],gs[j][0]))
        elif kind=='HEAD_shape':
            h=gs[0];out.extend([encoded('H1',min(phase,5),h[0]),encoded('H12',min(phase,5),*h[:2]),encoded('HL',rp,min(len(h),12))])
        elif kind=='HEAD_vertical':
            if previous_para==para and previous_head is not None:out.append(encoded(min(phase,5),previous_head,gs[0][0]))
        elif kind=='LF_shape':
            h=gs[-1];out.extend([encoded('T',rp,h[-1]),encoded('BT',rp,*h[-2:]),encoded('L',rp,min(len(h),12))])
        elif kind=='length_width':
            for j,g in enumerate(gs):
                out.extend([encoded('L',rp,role(j,n),min(len(g),12)),encoded('W',rp,role(j,n),min(sum(WIDTH[x] for x in g),24))])
        elif kind=='glyph_depth':
            for j,g in enumerate(gs):
                for d in range(len(g)+1):
                    a=g[d-2] if d>=2 else 'START';b=g[d-1] if d>=1 else 'START';c=g[d] if d<len(g) else 'END'
                    out.append(encoded(rp,role(j,n),min(d,9),a,b,c))
        previous_head=gs[0][0];previous_para=para
    return out or ['EMPTY']
def bt_events(doc):
    out=[]
    for ln in doc['lines']:
        # Last DISPLAYED physical-line word excluded before any glyph filtering.
        for w in ln.split()[:-1]:
            g=glyph(w,False)
            if len(g)>=2:out.append(g[-2:])
    return out

def bt_model(train,known):
    uni=list(itertools.product(GLYPHS,repeat=2))
    ec=collections.Counter(x for d in train for x in bt_events(d));kc=collections.Counter(x for d in known for x in bt_events(d))
    p0={x:(ec[x]+.5)/(sum(ec.values())+.5*len(uni)) for x in uni}
    p={x:(kc[x]+32*p0[x])/(sum(kc.values())+32) for x in uni}
    seen=[set(bt_events(d)) for d in known];active={x for x in uni if sum(x in s for s in seen)>=2}
    return p,p0,active

def bt_scores(d,params):
    p,p0,active=params;ev=bt_events(d);s=set(ev)
    if not ev:return {j:0. for j in BT_KINDS}
    ll=float(np.mean([math.log2(p[x]) for x in ev]));ex=float(np.mean([math.log2(p[x]/p0[x]) for x in ev]))
    return dict(bT_LL=ll,bT_leaf_excess=ex,bT_active=len(s&active)/len(s),
                bT_presence_log=float(np.mean([math.log2((1-1e-6+p0[x])/(p0[x]+1e-6)) if x in active else 0 for x in s])))
def pick(sid,judge,a,b):
    if abs(a-b)>1e-12:return 'A' if a>b else 'B'
    return 'A' if int(sha('tie20260909|'+sid+'|'+judge)[:8],16)%2==0 else 'B'

def decide(obj):
    sid=obj['set_id'];train=obj['training'];known=obj['known'];cand=obj['candidates']
    scores={'A':{},'B':{}};details={}
    for kind in VEC_KINDS:
        v=TfidfVectorizer(token_pattern=r'[^ ]+',lowercase=False,sublinear_tf=True,norm='l2',min_df=1)
        v.fit([' '.join(tokens(d,kind)) for d in train+known])
        K=v.transform([' '.join(tokens(d,kind)) for d in known]);P=np.asarray(K.mean(axis=0)).ravel();P/=max(np.linalg.norm(P),1e-15)
        X=v.transform([' '.join(tokens(cand[c],kind)) for c in 'AB']);s=np.asarray(X.dot(P)).ravel()
        for i,c in enumerate('AB'):scores[c][kind]=float(s[i])
        # Exact signed feature contributions to the A minus B score, BEFORE unblinding.
        dif=(X[0]-X[1]).toarray().ravel()*P;inds=np.argsort(-np.abs(dif))[:5];names=v.get_feature_names_out()
        details[kind]=[dict(feature=names[i],A_minus_B_contribution=float(dif[i])) for i in inds if abs(dif[i])>1e-15]
    bp=bt_model(train,known)
    for c in 'AB':
        scores[c].update(bt_scores(cand[c],bp))
        scores[c]['combined']=.5*(scores[c]['word']+scores[c]['ng'])
    # Unweighted, fixed majority of the 16 individual judges, not calibrated on answers.
    singles=JUDGES[:-1]
    va=sum(pick(sid,j,scores['A'][j],scores['B'][j])=='A' for j in singles)
    scores['A']['SAMEINFO_panel']=va/len(singles);scores['B']['SAMEINFO_panel']=1-va/len(singles)
    rows=[]
    for j in JUDGES:
        a=scores['A'][j];b=scores['B'][j]
        rows.append(dict(set_id=sid,judge=j,score_A=a,score_B=b,pick=pick(sid,j,a,b),tie=abs(a-b)<=1e-12,
                         rationale='higher fixed known3-compatibility score' if j!='SAMEINFO_panel' else 'fixed unweighted majority of 16 judges',
                         provenance='candidate+known3+outer_training16',target_lookup=False))
    rationale=dict(set_id=sid,scores=scores,vector_feature_contributions=details,
                   active_bT=['+'.join(x) for x in sorted(bp[2])],
                   inputs_used=['current candidate strings','current known3','training16 corpus','nonlexical line/paragraph layout'],
                   forbidden_inputs_used=[],answer_key_seen=False)
    return rows,rationale

def main():
    od=ROOT/'stage1_sameinfo';od.mkdir(exist_ok=True);dd=od/'decisions';dd.mkdir(exist_ok=True)
    rows=[]
    for i,f in enumerate(sorted((ROOT/'judging_inputs').glob('SET*.json')),1):
        obj=json.loads(f.read_text());rr,why=decide(obj);rows.extend(rr)
        (dd/(obj['set_id']+'.json')).write_text(json.dumps(why,ensure_ascii=False,sort_keys=True,indent=2))
        if i%25==0:print('SAMEINFO sealed decisions',i,flush=True)
    df=pd.DataFrame(rows);df.to_csv(od/'predictions_BLIND.csv',index=False)
    payload=dict(stage='SAMEINFO',sets=200,judges=JUDGES,decisions=len(df),answer_key_opened=False,
                 predictions_sha256=sha((od/'predictions_BLIND.csv').read_bytes()),
                 code_sha256=sha(Path(__file__).read_bytes()),
                 input_audit_sha256=sha((ROOT/'input_access_audit.csv').read_bytes()))
    (od/'PREDICTIONS_SEALED.json').write_text(json.dumps(payload,indent=2))
    print(json.dumps(payload,indent=2),flush=True)
if __name__=='__main__':main()
