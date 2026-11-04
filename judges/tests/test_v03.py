from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import itertools
import unittest

from judges.v03.protocol import ROOT, DEFAULT, PROTOCOL_HASH, digest, extractor_hash, read_json, write_jsonl
from judges.v03.schema import validate_case, candidate_doc, validate_prediction
from judges.v03.observations import endpoints, word_events, scopes
from judges.v03.predict import predict
from judges.v03.views import extract
from judges.v03.statistics import aggregate, score
from judges.v03.calibration import fit_prior, probabilities, loss, typicality, split_plan, validate_binding, fit, load_models
from judges.v03.controls import perturb
from judges.v03.artifacts import predict_file


def case():return deepcopy(read_json(ROOT/'contracts/case-v2.example.json'))


def corpus():
    c=case();pages=[deepcopy(d) for d in c['known']]+[{'slot':3,**candidate_doc(c,'A')}]
    return {'schema_version':2,'protocol_hash':PROTOCOL_HASH,'input_profile':'structure-endpoints-v2','source_hashes':{},
        'bifolia':[{'cluster_id':f'toy-bif-{i:02d}','fold':i//4,'pages':deepcopy(pages)} for i in range(20)]}


class V03Tests(unittest.TestCase):
    def test_partial_endpoint_is_not_a_word_or_head(self):
        c=case();validate_case(c);d=candidate_doc(c,'A')
        self.assertFalse(any(e.line==0 for e in word_events(d)))
        self.assertTrue(any(e.line==0 for e in endpoints(d)))
        self.assertEqual(word_events(d)[0].pline,2)
        self.assertFalse(word_events(d)[0].final)

    def test_shared_modes_and_slot_complement_are_enforced(self):
        for kind in ['mode','slot','truth','anchor']:
            c=case()
            if kind=='mode':c['candidates']['B']['lines'][0]['segments'][0]={'mode':'FULL','tokens':['chol']}
            elif kind=='slot':c['known'][0]['slot']=3
            elif kind=='truth':c['truth']='A'
            else:c['candidates']['B']['stable_surface']='hidden'
            with self.subTest(kind=kind),self.assertRaises(ValueError):validate_case(c)

    def test_no_compression_after_missing_line(self):
        c=case();c['target_layout']['lines'][1]['paragraph_line']=3
        with self.assertRaises(ValueError):validate_case(c)

    def test_unknown_paragraph_does_not_allow_known_paragraph_to_recur(self):
        c=case();doc=candidate_doc(c,'A')
        base=deepcopy(doc['layout']['lines'][-1]);data=deepcopy(doc['observations']['lines'][-1])
        frames=[];rows=[]
        for i,p in enumerate([0,None,1,None,0],1):
            f=deepcopy(base);f.update(line_no=i,paragraph=p,paragraph_line=1 if p is not None else None,paragraph_final=None)
            frames.append(f);rows.append(deepcopy(data))
        from judges.v03.schema import validate_doc
        with self.assertRaises(ValueError):validate_doc({'layout':{'lines':frames},'observations':{'lines':rows}})

    def test_glyphs_m_retained_and_invalid_rare_rejected(self):
        c=case();d=candidate_doc(c,'A')
        self.assertEqual(endpoints(d)[-1].g,('sh','o','m'))
        c['candidates']['A']['lines'][0]['segments'][0]['end_word']='daiing'
        with self.assertRaises(ValueError):validate_case(c)

    def test_plant_resets_connection_not_head(self):
        es=word_events(candidate_doc(case(),'A'))
        after=[e for e in es if e.segment==1][0]
        self.assertEqual(after.role,'BODY');self.assertIsNone(after.prev)

    def test_f1lf_is_shared_template_not_candidate_word_count(self):
        c=case();frame=c['target_layout']['lines'][0]
        self.assertIn('F1LF',scopes(frame,0))
        fs=extract(candidate_doc(c,'A'),c['known'])
        self.assertEqual(sum(fs['J08.F1LF/LONG'].counts.values()),1)
        self.assertEqual(sum(fs['J08.POSTPLANT/LONG'].counts.values()),0)

    def test_j11_lengths_and_support_do_not_require_internal_anchor(self):
        fs=extract(candidate_doc(case(),'A'),case()['known'])
        self.assertEqual(sum(fs['J11.L3.H2/H2'].counts.values()),1)
        self.assertEqual(sum(fs['J11.L4.H2/H2'].counts.values()),0)
        self.assertEqual(sum(fs['J11.SUPPORT/joint'].counts.values()),1)

    def test_j08_aggregate_counts_both_short_and_long_endpoints_once(self):
        c=case();end=deepcopy(c['target_layout']['lines'][-1])
        frame=deepcopy(c['target_layout']['lines'][0]);frame.update(line_no=4,paragraph=1,paragraph_line=1)
        end.update(line_no=5,paragraph=1,paragraph_line=2)
        c['target_layout']['lines'] += [frame,end]
        for side,w in [('A','chol'),('B','daiin')]:
            c['candidates'][side]['lines'] += [{'segments':[{'mode':'END_ONLY','end_word':w}]},{'segments':[{'mode':'NONE'}]}]
        p,_=predict(c)
        for side in ['A','B']:
            self.assertEqual(p['views']['J08.F1LF.PROTO']['coverage'][side+'_events'],2)
            self.assertEqual(p['views']['J08.F1LF.SHORT.PROTO']['coverage'][side+'_events'],1)
            self.assertEqual(p['views']['J08.F1LF.LONG.PROTO']['coverage'][side+'_events'],1)

    def test_indexed_one_glyph_relation_matches_exhaustive_search(self):
        from judges.features import near,near_any
        words=[tuple(x) for n in range(5) for x in itertools.product(('q','o','ch'),repeat=n)]
        for subset in [words[1:10],words[20:45],words[70:110]]:
            vocab=frozenset(subset)
            for w in words:self.assertEqual(near_any(w,vocab),any(near(w,v) for v in vocab))

    def test_swap_and_reference_order(self):
        c=case();before,_=predict(c)
        c['candidates']={'A':c['candidates']['B'],'B':c['candidates']['A']};after,_=predict(c)
        for k,v in before['views'].items():
            if v['delta'] is not None:self.assertAlmostEqual(v['delta'],-after['views'][k]['delta'])
        c=case();c['known'].reverse();permuted,_=predict(c)
        self.assertEqual(before['views'],permuted['views'])

    def test_tie_not_forced_into_expert_accuracy(self):
        c=case();c['candidates']['B']=deepcopy(c['candidates']['A']);p,_=predict(c)
        self.assertEqual(p['views']['J24.PROTO']['status'],'TIE')
        self.assertIsNone(p['views']['J24.PROTO']['pick']);self.assertIn(p['forced_primary_pick'],['A','B'])

    def test_prediction_cannot_disguise_missing_evidence_as_tie(self):
        p,_=predict(case());validate_prediction(p)
        p['views']['J24.PROTO'].update(status='TIE',delta=None,pick=None)
        with self.assertRaises(ValueError):validate_prediction(p)

    def test_cal_primary_does_not_silently_fallback(self):
        with self.assertRaises(ValueError):predict(case(),primary='J24.CAL')

    def test_exact_unequal_seed_statistics(self):
        ex=read_json(ROOT/'contracts/aggregation.example.json');s=aggregate(ex['trials'],100)
        for name,value in ex['expected'].items():
            mapped={'total_trials':'trials','total_bifolia':'bifolia'}.get(name,name)
            self.assertAlmostEqual(s[mapped],value)
        s=aggregate([{'cluster_id':'a','status':'TIE','correct':None}],100)
        self.assertIsNone(s['macro_decided_accuracy']);self.assertEqual(s['macro_expected_game_accuracy'],.5)
        s=aggregate([{'cluster_id':'a','status':'NA','correct':None}],100)
        self.assertIsNone(s['macro_expected_game_accuracy']);self.assertEqual(s['comparable_bifolia'],0)

    def test_smoothed_conditional_rows_positive_and_normalized(self):
        fs=[extract(candidate_doc(case(),'A'),[])];m=fit_prior(fs,'J11.L3.H2/H2',8,.75)
        for ctx in [('d',),('q',)]:
            p=probabilities(m,{},ctx)
            self.assertAlmostEqual(sum(p.values()),1);self.assertTrue(all(x>0 for x in p.values()))
        self.assertIsNotNone(loss(m,{},fs[0]['J11.L3.H2/H2'].counts))

    def test_rank_both_tails_and_calibration_minimum(self):
        rows=[{'cluster_id':str(b),'target_slot':s,'distance':d,'n':1} for b in range(6) for s,d in enumerate([.2,.8])]
        self.assertEqual(typicality(rows,0,1)[0],0);self.assertEqual(typicality(rows,1,1)[0],0)
        self.assertEqual(typicality(rows,.5,1)[0],1)
        self.assertEqual(typicality(rows[:4],.5,1),(None,None))

    def test_grouped_splits_and_holdout_guard(self):
        splits=split_plan(corpus());all_o=[]
        for s in splits:
            T=set(s['prior_train_cluster_ids']);Q=set(s['null_calibration_cluster_ids']);O=set(s['test_cluster_ids'])
            self.assertFalse(T&Q or T&O or Q&O);self.assertEqual((len(T),len(Q),len(O)),(8,8,4));all_o+=list(O)
        self.assertEqual(len(set(all_o)),20)
        model=splits[0]|{'protocol_hash':PROTOCOL_HASH,'extractor_hash':extractor_hash(),'nulls':{}}
        with self.assertRaises(ValueError):validate_binding(model,model['prior_train_cluster_ids'][0])
        model['nulls']={'bad':[{'cluster_id':model['test_cluster_ids'][0]}]}
        with self.assertRaises(ValueError):validate_binding(model,model['test_cluster_ids'][0])

    def test_control_changes_only_requested_h2_and_preserves_width(self):
        c=case();d=candidate_doc(c,'A');known=deepcopy(c['known'])
        # Add observable middle lines to the references, biasing their W2 H2 toward o.
        for r in known:
            r['layout']=deepcopy(d['layout']);r['observations']=deepcopy(d['observations'])
            r['observations']['lines'][1]['segments'][0]['tokens'][1]='dor'
        changed,info=perturb(d,known,'J11.L3.H2','toward_reference',1,0,'toy',3)
        self.assertEqual(info['changed_events'],1)
        self.assertEqual(changed['observations']['lines'][1]['segments'][0]['tokens'][1],'dor')
        self.assertEqual(changed['layout'],d['layout'])

    def test_seal_key_separation_and_tamper_detection(self):
        with TemporaryDirectory() as td:
            p=Path(td);write_jsonl(p/'input.jsonl',[case()])
            predict_file(p/'input.jsonl',p/'pred')
            self.assertFalse(read_json(p/'pred/manifest.json')['answer_key_read'])
            write_jsonl(p/'key.jsonl',[{'set_id':case()['set_id'],'truth':'A'}])
            r=score(p/'pred',p/'key.jsonl',p/'score',100)
            self.assertEqual(r['primary_summary']['trials'],1)
            with (p/'pred/predictions.jsonl').open('a') as f:f.write('\n')
            with self.assertRaises(ValueError):score(p/'pred',p/'key.jsonl',p/'tampered',100)

    def test_parallel_predictions_equal_serial_without_reading_keys(self):
        with TemporaryDirectory() as td:
            p=Path(td);c=case();d=deepcopy(c);d['set_id']='another';d['seed']=2
            write_jsonl(p/'inputs.jsonl',[c,d])
            predict_file(p/'inputs.jsonl',p/'serial')
            predict_file(p/'inputs.jsonl',p/'parallel',jobs=2)
            self.assertEqual((p/'serial/predictions.jsonl').read_bytes(),(p/'parallel/predictions.jsonl').read_bytes())
            self.assertEqual((p/'serial/channels.jsonl').read_bytes(),(p/'parallel/channels.jsonl').read_bytes())

    def test_genuine_only_fit_and_artifact_binding(self):
        with TemporaryDirectory() as td:
            p=Path(td);c=corpus();payload=fit(c,p/'models')
            _,bound=load_models(p/'models')
            self.assertEqual(len(bound),20);self.assertEqual(len(payload['models']),5)
            cc=case();cc['cluster_id']='toy-bif-00'
            r,_=predict(cc,bound[cc['cluster_id']],primary='J24.CAL')
            self.assertIn(r['views']['J24.CAL']['status'],['DECIDED','TIE','NA'])
            # Training membership cannot be substituted for the case's holdout model.
            wrong=next(m for m in payload['models'] if cc['cluster_id'] not in m['test_cluster_ids'])
            with self.assertRaises(ValueError):predict(cc,wrong,primary='J24.CAL')


if __name__=='__main__':unittest.main()
