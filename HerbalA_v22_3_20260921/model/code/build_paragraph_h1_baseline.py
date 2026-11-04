from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

GLYPHS=['q','cfh','ch','cph','cth','p','sh','ckh','f','k','o','t','a','d','e','s','i','l','y','r','m','n']
COMPOUNDS=['cfh','ckh','cph','cth','ch','sh']; G2I={g:i for i,g in enumerate(GLYPHS)}; V=len(GLYPHS)
TARGET_PAGES={'A:2':'f7v','B:3':'f14v','D:1':'f32v','F:2':'f47v','A:3':'f6v','C:1':'f24v','D:3':'f30v','F:4':'f45v','A:4':'f5v','C:2':'f23v','D:4':'f29v','G:1':'f49v','B:1':'f9v','C:3':'f22v','E:3':'f38v','G:3':'f54v','B:2':'f15v','C:4':'f21v','E:4':'f37v','G:4':'f53v'}
LEAVES=list(TARGET_PAGES)

def tok(s):
    s=str(s);out=[];i=0
    while i<len(s):
        hit=None
        for g in COMPOUNDS:
            if s.startswith(g,i):hit=g;break
        if hit is not None:out.append(G2I[hit]);i+=len(hit)
        else:
            if s[i] not in G2I:raise ValueError((s,s[i]))
            out.append(G2I[s[i]]);i+=1
    return tuple(out)

def build(data_dir:Path,out:Path):
    E=pd.read_csv(data_dir/'events.csv.gz')
    T=pd.read_csv(data_dir/'full_segment_schedule_tokens.csv')
    O=pd.read_csv(data_dir/'observed_tokens_stable.csv',low_memory=False)[['global_order','n_glyph']]
    D=E.merge(T[['global_order','is_segment_end','is_para_final']],on='global_order').merge(O,on='global_order').sort_values('global_order').reset_index(drop=True)
    D['glyphs']=D.surface.map(tok);D['H1']=D.glyphs.map(lambda x:int(x[0]))
    comp=set(D.groupby('bif').page.nunique().loc[lambda x:x==4].index)
    D=D[D.bif.isin(comp)].copy()
    mask=(D.para_line_raw>=2)&(~D.is_para_final)&(D.base_role=='BODY')&(~D.is_segment_end)&(D.n_glyph>=2)
    Q=D[mask].copy().reset_index(drop=True)
    Q['ctx']=list(zip(Q.n_glyph.astype(int),Q.boundary_before.astype(str),Q.prev_terminal.astype(int)))
    A=16.;LL=64.
    allY=Counter(Q.H1);bifY=defaultdict(Counter);total=defaultdict(Counter);bifc=defaultdict(lambda:defaultdict(Counter));pagec=defaultdict(lambda:defaultdict(Counter));lenc=defaultdict(Counter);biflen=defaultdict(lambda:defaultdict(Counter))
    for _,r in Q.iterrows():
        b,p,y,ctx,L=str(r.bif),str(r.page),int(r.H1),r.ctx,int(r.n_glyph)
        bifY[b][y]+=1;total[ctx][y]+=1;bifc[b][ctx][y]+=1;pagec[p][ctx][y]+=1;lenc[L][y]+=1;biflen[b][L][y]+=1
    ctxs=[]
    for L in range(2,13):
        for t in range(V):ctxs.append((L,'SPACE',t))
        ctxs.append((L,'PLANT',-1));ctxs.append((L,'UNKNOWN_GAP',-1))
    res={}
    for b in LEAVES:
        p=TARGET_PAGES[b];N=sum(allY.values())-sum(bifY[b].values())
        prior=np.array([(allY[y]-bifY[b][y]+.5)/(N+.5*V) for y in range(V)],float);table={}
        for L,bound,t in ctxs:
            nL=sum(lenc[L].values())-sum(biflen[b][L].values())
            pL=np.array([(lenc[L][y]-biflen[b][L][y]+A*prior[y])/(nL+A) for y in range(V)],float)
            ctx=(L,bound,t);nc=sum(total[ctx].values())-sum(bifc[b][ctx].values())
            pg=np.array([(total[ctx][y]-bifc[b][ctx][y]+A*pL[y])/(nc+A) for y in range(V)],float)
            nl=sum(bifc[b][ctx].values())-sum(pagec[p][ctx].values())
            pl=np.array([(bifc[b][ctx][y]-pagec[p][ctx][y]+LL*pg[y])/(nl+LL) for y in range(V)],float);pl/=pl.sum()
            table[f'{L}|{bound}|{t}']=[float(x) for x in pl]
        res[b]={'target_page':p,'table':table}
    meta={'version':'PARAH1_BASELINE_V1','date':'2026-09-17','glyphs':GLYPHS,'lambda_running':32.0,'external_alpha':A,'leaf_lambda':LL,'scope':'BODY n_glyph>=2, para_line>=2, non-paragraph-final, non-segment-end','baseline':'exact glyph length + boundary/previous terminal + target-blind leaf-known-3','complete_bifolia':LEAVES,'target_pages':TARGET_PAGES,'events_used':int(len(Q)),'source':'H1_STATE_PARAMETERIZATION_CONTEST_20260917 data; target page excluded from leaf-known3 baseline'}
    out.write_text(json.dumps({'metadata':meta,'by_bif':res},ensure_ascii=False,separators=(',',':')),encoding='utf-8')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[1]/'validation/paragraph_h1_running/state_model_selection/data');ap.add_argument('--out',type=Path,default=Path(__file__).resolve().parents[1]/'parameters/PARAGRAPH_H1_BASELINE.json');a=ap.parse_args();build(a.data_dir,a.out);print(a.out)
