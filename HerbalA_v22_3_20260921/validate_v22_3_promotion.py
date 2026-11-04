#!/usr/bin/env python3
from pathlib import Path
import csv, hashlib, json
R=Path(__file__).resolve().parent
D=json.loads((R/'DECISION_V22_3_FORMAL.json').read_text(encoding='utf-8'))
assert D['decision']=='PROMOTED_PASS_WITH_RESIDUAL' and D['promotion'] is True
F=R/'model/frozen_law_v22_3'
rows=list(csv.DictReader((F/'LAW_FREEZE_MANIFEST.csv').open(encoding='utf-8')))
for r in rows:
 p=F/r['file']; assert p.exists(), r['file']; assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'], r['file']
h=hashlib.sha256()
for r in rows:
 h.update(r['file'].encode()); h.update(b'\0'); h.update(r['sha256'].encode()); h.update(b'\n')
meta=json.loads((F/'LAW_FREEZE.json').read_text(encoding='utf-8'))
assert h.hexdigest()==meta['law_plus_interpreter_sha256']
S=json.loads((R/'model/MODEL_STATUS.json').read_text(encoding='utf-8'))
assert S['model_id']=='HerbalA-v22.3' and S['promotion'] is True
print(json.dumps({'status':'PASS','model_id':S['model_id'],'decision':D['decision'],'law_plus_interpreter_sha256':h.hexdigest(),'files_checked':len(rows)},indent=2))
