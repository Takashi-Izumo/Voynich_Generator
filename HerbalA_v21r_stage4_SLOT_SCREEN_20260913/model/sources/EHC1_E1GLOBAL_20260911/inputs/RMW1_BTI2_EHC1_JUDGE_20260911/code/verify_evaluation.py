#!/usr/bin/env python3
"""Contract checks: exact frozen-judge equivalence, boundaries, hash preservation."""
import evaluation_common as e
from stage3_env import ROOT,EHC
import numpy as np,pandas as pd,json,zipfile,hashlib

def main():
 C=e.context();tests=[];mx=0.
 for fi in [0,2,4]:
  test=e.folds(C.bifs)[fi];b=test[0];p=C.pages[b][-1];train=[e.real_doc(C,q) for bb in C.bifs if bb not in test for q in C.pages[bb]];known=[e.real_doc(C,q) for q in C.pages[b] if q!=p];real=e.real_doc(C,p)
  gen=e.generated_doc(pd.read_csv(ROOT/f'outputs/multirun/generated/run91021/E12_VH/{b.replace(":","_")}/tokens.csv.gz'))
  model=e.Judges(train,known);ra=model.score(real);ge=model.score(gen)
  rr,_=e.J.decide(dict(set_id='contract_'+str(fi),training=train,known=known,candidates={'A':real,'B':gen}))
  for r in rr:
   if r['judge']=='SAMEINFO_panel':continue
   er=max(abs(r['score_A']-ra[r['judge']]),abs(r['score_B']-ge[r['judge']]));mx=max(mx,er);assert er<1e-12
  tests.append(dict(fold=fi,bif=b,exact_frozen16_equivalence=True))
 # Raw event accounting: a PLANT/UNKNOWN/reset event cannot be eligible SPACE.
 E=C.events
 assert not (E.entry_eligible & E.boundary_before.ne('SPACE')).any()
 assert not (E.entry_eligible & E.physical_head).any()
 # Input generator sources/parameters are byte-identical to frozen archive.
 path=ROOT/'input/RMW1_BTI2_EHC1_20260911.zip'
 if not path.exists():path=EHC.parents[1]/'RMW1_BTI2_EHC1_20260911.zip'
 if not path.exists():path=__import__('pathlib').Path('/mnt/data/RMW1_BTI2_EHC1_20260911.zip')
 changed=[];checked=0
 with zipfile.ZipFile(path) as z:
  for n in z.namelist():
   rel=n.split('/',1)[1] if '/' in n else ''
   if not rel or n.endswith('/') or '__pycache__' in n:continue
   if rel.startswith(('code/','parameters/','parent/')):
    fp=EHC/rel
    if not fp.exists() or hashlib.sha256(fp.read_bytes()).hexdigest()!=hashlib.sha256(z.read(n)).hexdigest():changed.append(rel)
    checked+=1
 assert not changed,changed
 out=dict(contract_tests=tests,max_frozen_score_error=mx,raw_entry_events=int(E.entry_eligible.sum()),cross_PLANT_or_unknown_entry_events=0,parent_stage2_files_checked=checked,changed_generator_or_parameter_files=changed,independent_llm_judges=False)
 e.write(ROOT/'EVALUATION_CONTRACT_AUDIT.json',out);print(out)
if __name__=='__main__':main()
