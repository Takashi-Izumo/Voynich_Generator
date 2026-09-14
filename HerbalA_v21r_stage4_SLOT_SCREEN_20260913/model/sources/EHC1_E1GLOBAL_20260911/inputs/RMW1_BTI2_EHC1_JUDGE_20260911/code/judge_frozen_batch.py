#!/usr/bin/env python3
"""One common set of frozen numerical judges per leaf; no generator changes."""
from __future__ import annotations
import evaluation_common as e
from stage3_env import ROOT
import json,argparse,time
import numpy as np,pandas as pd
from pathlib import Path

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['multirun','confirmation'],required=True);a=ap.parse_args()
 inp=ROOT/'outputs'/a.stage/'generated';out=ROOT/'outputs'/a.stage/'judged';out.mkdir(parents=True,exist_ok=True)
 seal=json.loads((inp/'GENERATION_SEALED.json').read_text())
 for fn,h in seal['hashes'].items():assert e.file_hash(inp/fn)==h,fn
 C=e.context();docs={p:e.real_doc(C,p) for p in C.seqs};scores=[];metrics=[];trainaudit=[];distances=[]
 for fi,test in enumerate(e.folds(C.bifs)):
  train=[b for b in C.bifs if b not in test];tp=[p for b in train for p in C.pages[b]]
  for b in test:
   p=C.pages[b][-1];kp=[q for q in C.pages[b] if q!=p];judge=e.Judges([docs[q] for q in tp],[docs[q] for q in kp]);real=judge.score(docs[p])
   for run in seal['runs']:
    for arm in seal['arms']:
     d=pd.read_csv(inp/f'run{run}'/arm/b.replace(':','_')/'tokens.csv.gz');gd=e.generated_doc(d);sc=judge.score(gd)
     for k in real:
      mar=real[k]-sc[k];scores.append(dict(fold=fi,bif=b,page=p,run=run,arm=arm,judge=k,real_score=real[k],gen_score=sc[k],margin=mar,abs_margin=abs(mar)))
     metrics.append(e.metric_row(C,p,d,arm,run,b,fi))
     for k in ('bigram','trigram'):
      gt=e.J.tokens(gd,k);rt=e.J.tokens(docs[p],k);kt=[x for q in kp for x in e.J.tokens(docs[q],k)];at=[x for q in tp for x in e.J.tokens(docs[q],k)]
      distances.append(dict(fold=fi,bif=b,page=p,run=run,arm=arm,ngram=k,target_jsd=e.jsd(gt,rt),known3_jsd=e.jsd(gt,kt),awide_jsd=e.jsd(gt,at),real_known3_jsd=e.jsd(rt,kt),real_awide_jsd=e.jsd(rt,at)))
   trainaudit.append(dict(fold=fi,bif=b,target=p,known3=kp,external_train_bifs=train,external_pages=tp,target_in_feature_fit=False,shared_across_arms=True))
   print('JUDGED',a.stage,fi,b,flush=True)
 S=pd.DataFrame(scores);M=pd.DataFrame(metrics);SU,CO=e.summarize(S,M,out)
 # Standard 16-test multiplicity is reported separately from four added diagnostics.
 SU['holm16_direction']=np.nan
 standard=set(e.J.JUDGES[:-1])
 for arm in SU.arm.unique():
  mk=SU.arm.eq(arm)&SU.judge.isin(standard);SU.loc[mk,'holm16_direction']=e.holm(SU.loc[mk,'p_leaf_direction_two_sided'])
 SU.to_csv(out/'judge_summary.csv',index=False)
 pd.DataFrame(distances).to_csv(out/'ngram_distances.csv',index=False);e.write(out/'TRAINING_AUDIT.json',trainaudit)
 e.write(out/'JUDGE_AUDIT.json',dict(standard_judges=sorted(standard),extra_diagnostics=e.EXTRA,numerical_judges=20,independent_llm_calls=0,source_hash=e.file_hash(Path(__file__).parent/'frozen_judge_sameinfo.py'),generator_changed=False,feature_fit_uses='external complete16 all64 pages + target known3; candidate never used for fit',seed_cluster_unit='bifolium; 20 clusters',runs=seal['runs'],pages=seal['pages'],legacy_SPACE_includes_clean_PLANT_adjacency=True,additional_SPACE_RAW_excludes_PLANT=True,final_surface_used=True))
 print('JUDGE_COMPLETE',a.stage,len(S));print(CO[CO.judge.isin(e.PRIMARY+e.HEAD)][['arm','judge','change_pct','leaves_improved','p_improve_one_sided','holm_primary','holm_head']].to_string(index=False))
if __name__=='__main__':main()
