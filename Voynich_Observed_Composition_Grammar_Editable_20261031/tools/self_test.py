#!/usr/bin/env python3
"""Pure-stdlib self-test for the observed grammar evidence and manual composition checker."""
import csv
import json
from pathlib import Path
import check_composition as cc
R=Path(__file__).resolve().parents[1]
summary=json.loads((R/'data/summary.json').read_text())
assert [summary[k] for k in ['words','word_types','pages','bifolia','paragraphs','lines','core_role_tokens','observed_bigram_types','observed_trigram_types','shared_routes_4to6']]==[6836,1971,85,22,165,1090,6816,229,881,715]
print('PASS: all observed corpus cardinalities')
with (R/'data/attested_lexicon.csv').open(encoding='utf-8',newline='') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==1971 and sum(int(x['frequency']) for x in rows)==6836
print('PASS: every observed word has a counted surface form')
assert sum(int(x['PHW']) for x in rows)==164 and sum(int(x['PF_LF']) for x in rows)==164
print('PASS: core positional roles')
a=(R/'examples/grade_A_original.eva').read_text()
b=(R/'examples/grade_B_one_edit_original.eva').read_text()
assert cc.validate(a,level='A')['status']=='PASS'
print('PASS: new grade A paragraphs (attested roles and words)')
assert cc.validate(b,level='A')['status']=='FAIL'
print('PASS: Grade A correctly rejects new nonattested word')
x=cc.validate(b,level='B')
assert x['status']=='PASS' and len(x['novel_words'])==1 and x['novel_words'][0]['form']=='doin'
print('PASS: Grade B one-edit novel-word license with attested trigrams')
assert cc.validate(a.replace('pchor','qqz'),level='C')['status']=='FAIL'
print('PASS: forbidden glyph/bigram rejected')
assert cc.validate(a.replace('pchor shol','chol shol'),level='A')['status']=='FAIL'
print('PASS: role-misplaced words rejected')
assert cc.validate('chol\nshol\ndaiin',level='A')['status']=='FAIL'
print('PASS: undersized lines rejected')
assert cc.validate(a,level='A')['parsed'][0]['l2_l3_shared_4glyph_routes']
print('PASS: line-2/line-3 route continuity detected without making it mandatory')
print('ALL 10 TESTS PASS')
