from __future__ import annotations
import stage3_env as env
from pathlib import Path
from collections import Counter
import json,gzip,hashlib
import numpy as np,pandas as pd
from scipy.spatial.distance import jensenshannon
from sklearn.feature_extraction.text import TfidfVectorizer
from fold_context import Context,FoldContext,folds,load_core
from boundary_events import build_events,POLICY
from entry_correction import CorrectionTables,configs
import frozen_judge_sameinfo as J
import v19r_rb3_pw2_close1 as m
PRIMARY=['SPACE_T_H1','H2_RAW']
HEAD=['HEAD_shape','HEAD_vertical','H3_HEAD_RAW']
REGRESSION=['word','ng','bigram','trigram','route56','combined','bT_LL','bT_leaf_excess','bT_active','bT_presence_log','glyph_depth','LF_shape','length_width']
EXTRA=['SPACE_RAW','H2_RAW','H3_HEAD_RAW','HEAD_H1_RAW']
SCREEN=['SPACE_T_H1','H2_RAW','HEAD_shape','HEAD_vertical','H3_HEAD_RAW','SPACE_RAW']
MAIN6=['word','ng','bigram','trigram','route56','combined']

def write(path,obj):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str,sort_keys=True)+'\n')
def file_hash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jsonl(p):
 with gzip.open(p,'rt') as f:return [json.loads(l) for l in f]
def context():
 C=Context();C.events,C.event_lines=build_events(C);return C

def real_doc(C,p):
 d=C.df[C.df.page.eq(p)].sort_values('global_order');ls=[];layout=[]
 for _,g in d.groupby('locus',sort=False):
  ls.append(' '.join(g.surface.astype(str)));layout.append(dict(para=int(g.iloc[0]['para']),phase=int(g.iloc[0]['para_line_raw'])))
 return dict(lines=ls,layout=layout,raw_events=C.events[C.events.page.eq(p)].to_dict('records'))

def gen_events(d):
 rows=[];last={};heads={};prev=None;sk=None
 for r in d.to_dict('records'):last[r['locus']]=int(r['line_wordnum'])
 for r in d.to_dict('records'):
  lk=r['locus'];key=(r['page'],lk,int(r['segment_id']));gl=J.glyph(str(r['surface']),False)
  if key!=sk:prev=None
  ph=int(r['line_wordnum'])==1 and int(r['segment_id'])==0;fin=int(r['line_wordnum'])==last[lk]
  role=r['role'];rp='FIRST' if int(r['para_line_raw'])==1 else 'FINAL' if bool(r['pf_final_segment']) else 'MIDDLE'
  # pf_final_segment flags only the last segment; recover raw row phase from final segment of line.
  rows.append(dict(locus=lk,para=int(r['para']),para_line_raw=int(r['para_line_raw']),physical_head=ph,physical_final=fin,
   base_role=role,board='LF' if fin else 'HEAD' if ph else 'W2' if int(r['segment_id'])==0 and int(r['line_wordnum'])==2 else 'BODY',row_phase=rp,
   glyph_names=gl,entry_eligible=bool(gl and prev is not None and role not in ('PHW','HEAD') and not ph),prev_terminal_name=prev,
   position_eligible=bool(gl and role!='PHW'),segment_id=int(r['segment_id']),surface=str(r['surface'])))
  prev=gl[-1] if gl else None;sk=key
 pf_loci=set(d.loc[d.pf_final_segment.astype(bool),'locus'].astype(str))
 for r in rows:
  if r['row_phase']!='FIRST' and r['locus'] in pf_loci:r['row_phase']='FINAL'
 return rows

def generated_doc(d):
 ls=[];layout=[]
 for _,g in d.groupby('locus',sort=False):
  ls.append(' '.join(g.surface.astype(str)));layout.append(dict(para=int(g.iloc[0]['para']),phase=int(g.iloc[0]['para_line_raw'])))
 return dict(lines=ls,layout=layout,raw_events=gen_events(d))

def feature_tokens(doc,kind):
 if kind not in EXTRA:return J.tokens(doc,kind)
 out=[]
 for r in doc['raw_events']:
  gl=tuple(r.get('glyph_names',())) if 'glyph_names' in r else tuple(m.I2G[int(x)] for x in r['glyphs'])
  if not gl:continue
  rp,bd=r['row_phase'],r['board'];T=r.get('prev_terminal_name')
  if 'prev_terminal' in r and int(r['prev_terminal'])>=0:T=m.I2G[int(r['prev_terminal'])]
  if kind=='SPACE_RAW' and r['entry_eligible']:out.append(J.encoded(rp,bd,T,gl[0]))
  elif kind=='H2_RAW' and r['position_eligible'] and len(gl)>=2:out.append(J.encoded(rp,bd,gl[0],gl[1]))
  elif kind=='H3_HEAD_RAW' and r['position_eligible'] and r['physical_head'] and r['base_role']=='HEAD' and len(gl)>=3:out.append(J.encoded(rp,bd,*gl[:3]))
  elif kind=='HEAD_H1_RAW' and r['position_eligible'] and r['physical_head'] and r['base_role']=='HEAD':out.append(J.encoded(min(int(r['para_line_raw']),5),rp,gl[0]))
 return out or ['EMPTY']

class Judges:
 def __init__(self,training,known,kinds=None):
  self.kinds=list(kinds if kinds is not None else J.VEC_KINDS+EXTRA);self.models={};self.bt=J.bt_model(training,known)
  for k in self.kinds:
   v=TfidfVectorizer(token_pattern=r'[^ ]+',lowercase=False,sublinear_tf=True,norm='l2',min_df=1)
   v.fit([' '.join(feature_tokens(d,k)) for d in training+known])
   P=np.asarray(v.transform([' '.join(feature_tokens(d,k)) for d in known]).mean(axis=0)).ravel();P/=max(np.linalg.norm(P),1e-15)
   self.models[k]=(v,P)
 def score(self,d,full=True):
  ret={k:float(v.transform([' '.join(feature_tokens(d,k))]).dot(P)[0]) for k,(v,P) in self.models.items()}
  if full:
   ret.update(J.bt_scores(d,self.bt));ret['combined']=.5*(ret['word']+ret['ng'])
  return ret

def jsd(a,b):
 ca,cb=Counter(a),Counter(b);keys=sorted(ca.keys()|cb.keys());x=np.array([ca[k] for k in keys],float);y=np.array([cb[k] for k in keys],float)
 return float(jensenshannon(x/x.sum(),y/y.sum(),base=2)**2) if x.sum() and y.sum() else float('nan')

def descriptive(d):
 ws=[ ''.join(c for c in str(w) if c not in J.RARE) for w in d.surface ];ws=[w for w in ws if w];ct=Counter(ws);v=list(ct.values())
 glens=d.glyph_len.to_numpy() if 'glyph_len' in d else np.array([len(g) for g in d.glyphs])
 widths=d.phys_width.to_numpy() if 'phys_width' in d else np.array([m.stable_width(g) for g in d.glyphs])
 res=dict(tokens=len(ws),types=len(ct),hapax=sum(n==1 for n in v),F2=sum(n==2 for n in v),F3_5=sum(3<=n<=5 for n in v),F6_10=sum(6<=n<=10 for n in v),F11p=sum(n>=11 for n in v),mean_len=float(np.mean(glens)),mean_width=float(np.mean(widths)))
 for n in (3,4,5):res['F'+str(n)]=sum(x==n for x in v)
 return res

def metric_row(C,p,d,arm,run,b,fi):
 gd=generated_doc(d);rd=real_doc(C,p);obs=descriptive(C.df[C.df.page.eq(p)]);gen=descriptive(d)
 ret=dict(fold=fi,bif=b,page=p,arm=arm,run=run)
 for k,v in gen.items():ret.update({k:v,'real_'+k:obs[k],'ae_'+k:abs(v-obs[k])})
 for k in ('bigram','trigram'):
  ret[k+'_target_jsd']=jsd(J.tokens(rd,k),J.tokens(gd,k))
 return ret

def holm(ps):
 ps=np.asarray(ps,float);out=np.ones(len(ps));ix=np.argsort(ps);mx=0.
 for j,i in enumerate(ix):mx=max(mx,(len(ps)-j)*ps[i]);out[i]=min(1.,mx)
 return out

def signflip(x,alternative='two-sided'):
 x=np.array(x,float);x=x[np.isfinite(x)&(np.abs(x)>1e-15)]
 if not len(x):return 1.
 sums=np.zeros(1)
 for v in x:sums=np.concatenate((sums+v,sums-v))
 ob=x.sum();eps=1e-12*max(1.,abs(ob))
 return float(np.mean(sums>=ob-eps)) if alternative=='greater' else float(np.mean(np.abs(sums)>=abs(ob)-eps))

def summarize(S,M,out,bootstrap_n=20000):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 S.to_csv(out/'scores_by_leaf_run.csv',index=False);M.to_csv(out/'metrics_by_leaf_run.csv',index=False)
 sums=[];pairs=[]
 for (arm,j),g in S.groupby(['arm','judge'],sort=False):
  lv=g.groupby('bif').margin.mean();sums.append(dict(arm=arm,judge=j,pages=len(g),leaves=len(lv),real_wins=int((g.margin>1e-12).sum()),ties=int((g.margin.abs()<=1e-12).sum()),mean_margin=g.margin.mean(),mean_abs_margin=g.abs_margin.mean(),leaves_positive=int((lv>1e-12).sum()),p_leaf_direction_two_sided=signflip(lv)))
 SU=pd.DataFrame(sums);SU['holm_all_direction']=SU.groupby('arm').p_leaf_direction_two_sided.transform(lambda x:holm(x))
 SU.to_csv(out/'judge_summary.csv',index=False)
 for arm in S.arm.unique():
  if arm=='BASE':continue
  z=S[S.arm.eq(arm)].merge(S[S.arm.eq('BASE')],on=['bif','run','judge'],suffixes=('_new','_base'),validate='one_to_one')
  for j,g in z.groupby('judge'):
   v=(g.abs_margin_base-g.abs_margin_new).groupby(g.bif).mean();x=v.to_numpy();rg=np.random.default_rng(2026091101);boots=x[rg.integers(len(x),size=(bootstrap_n,len(x)))].mean(axis=1)
   ba=float(g.abs_margin_base.mean());nw=float(g.abs_margin_new.mean())
   pairs.append(dict(arm=arm,judge=j,base_abs=ba,new_abs=nw,change_pct=100*(nw/ba-1) if ba>1e-12 else np.nan,improvement_mean=float(v.mean()),leaves_improved=int((v>1e-12).sum()),leaves_worsened=int((v<-1e-12).sum()),p_improve_one_sided=signflip(v,'greater'),p_two_sided=signflip(v),improvement_ci_low=float(np.quantile(boots,.025)),improvement_ci_high=float(np.quantile(boots,.975))))
 CO=pd.DataFrame(pairs)
 if len(CO):
  CO['holm_all_improvement']=CO.groupby('arm').p_improve_one_sided.transform(lambda x:holm(x));CO['holm_all_two_sided']=CO.groupby('arm').p_two_sided.transform(lambda x:holm(x))
  for gn,ks in [('primary',PRIMARY),('head',HEAD),('regression',REGRESSION),('main6',MAIN6)]:
   CO['holm_'+gn]=np.nan
   for arm in CO.arm.unique():
    mk=CO.arm.eq(arm)&CO.judge.isin(ks);CO.loc[mk,'holm_'+gn]=holm(CO.loc[mk,'p_improve_one_sided']);CO.loc[mk,'holm_'+gn+'_two_sided']=holm(CO.loc[mk,'p_two_sided'])
  CO.to_csv(out/'paired_vs_parent.csv',index=False)
 ms=[]
 for arm,g in M.groupby('arm',sort=False):
  for k in [c[3:] for c in M if c.startswith('ae_')]:
   ms.append(dict(arm=arm,metric=k,real_mean=g['real_'+k].mean(),generated_mean=g[k].mean(),MAE=g['ae_'+k].mean()))
 pd.DataFrame(ms).to_csv(out/'metric_summary.csv',index=False)
 return SU,CO
