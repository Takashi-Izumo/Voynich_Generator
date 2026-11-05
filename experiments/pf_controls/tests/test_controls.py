from __future__ import annotations

from copy import deepcopy
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.pf_controls.common import context, digest, seal, unseal, write_json, file_inventory, read
from experiments.pf_controls.evaluation import channel_measurement, gate
from experiments.pf_controls.proxy import allowed, facts, outcome, nll, select, smooth
from experiments.pf_controls import pipeline
from experiments.pf_controls.evaluation import evaluate
from experiments.pf_controls.replay import class_data,effective_class_controls,restore_class_controls


def rows(word='daiin', previous='or', width=5):
    return [dict(surface=previous,phys_width=2),dict(surface=word,phys_width=width)] if previous else [dict(surface=word,phys_width=width)]


def table():
    lengths=smooth([0,10,0,0,2,0,0,0,0,0,0,0],[1]*12)
    return dict(probabilities=dict(length_width=lengths,terminal=smooth(list(range(22)),[1]*22),
                                  space_T_H1=[smooth([j+1 for j in range(22)],[1]*22) for _ in range(22)]))


def fixture_case():
    ctx=dict(bif='A:2',run=92101,page='p',locus='p.1',segment_id=0,event=0)
    snapshot=seal(dict(**ctx,state_sha256='state',next_proposal_id=10,branches=64))
    donors=[seal(dict(**ctx,branch=i,snapshot_sha256=snapshot['sha256'],input_state_sha256='state',
                      proposal_start=10,proposal_end=11,requests=[dict(proposal_id=10)],
                      restored_parent=True,support_violations=0,physical_packing=True,rows=rows(),
                      output_state_sha256='output')) for i in range(64)]
    base=dict(rows=[dict(**r,locus='p.1',segment_id=0) for r in rows()])
    selections=[dict(**ctx,snapshot_sha256=snapshot['sha256'],**s) for s in select(base['rows'],donors,table())]
    p=dict(sha256='p',bifolia=['A:2'],proxies={'0':table()},corpus_hash='corpus',source_hashes={},
           eligible_events=[dict(bif='A:2',locus='p.1',segment_id=0,space=True)])
    case=seal(dict(bif='A:2',page='p',fold=0,plan_sha256='p',base=base,base_sha256=digest(base),
                   ordinary_base_sha256=digest(base),no_effect_checked=True,
                   snapshots=[snapshot],donors=donors,selections=selections))
    return p,case


class ProxyTests(unittest.TestCase):
    def test_visible_tokenizer_and_physical_separate(self):
        f=facts(rows('cfhbgaiin',width=11))
        self.assertEqual((f['length'],f['visible_width'],f['physical_width']),(5,8,11))

    def test_space_never_crosses_segment(self):
        f=facts(rows('daiin',previous=None))
        self.assertIsNone(f['previous_terminal'])
        with self.assertRaisesRegex(ValueError,'SPACE'):
            outcome(f,'space_T_H1')

    def test_prior_normalization_and_no_empty_mass(self):
        for size in (12,22):
            p=smooth([0]*size,[0]*size)
            self.assertAlmostEqual(sum(p),1)
            self.assertTrue(all(v>0 for v in p))

    def test_terminal_lane_constraints(self):
        a=facts(rows('daiin'))
        self.assertTrue(allowed(a,facts(rows('daiiy')),'terminal'))
        self.assertFalse(allowed(a,facts(rows('daiir')),'terminal'))
        self.assertFalse(allowed(a,facts(rows('daiiin')),'terminal'))
        self.assertFalse(allowed(a,facts(rows('daiiy',width=6)),'terminal'))

    def test_space_fixes_exact_terminal(self):
        a=facts(rows('daiin'))
        self.assertTrue(allowed(a,facts(rows('saiin',previous='dy')),'space_T_H1'))
        self.assertFalse(allowed(a,facts(rows('daiiy')),'space_T_H1'))
        self.assertFalse(allowed(a,facts(rows('daiin',previous=None)),'space_T_H1'))

    def test_deterministic_selection_and_directions(self):
        donors=[dict(branch=i,rows=rows(['daiin','saiiy','dy','daiiiiiin'][i%4])) for i in range(64)]
        selected=select(rows(),donors,table())
        self.assertEqual(selected,select(rows(),deepcopy(donors),table()))
        self.assertEqual(len(selected),6)
        for r in selected:
            if r['branch'] is not None:
                self.assertLess(r['donor_nll'],r['anchor_nll']-1e-12) if r['direction']=='near' else self.assertGreater(r['donor_nll'],r['anchor_nll']+1e-12)
                self.assertLess(r['branch'],4)  # Repeated equal donors resolve to first ID.

    def test_no_match_not_support_impossibility(self):
        donors=[dict(branch=i,rows=rows()) for i in range(64)]
        self.assertTrue(all(r['status']=='NO_MATCH_WITHIN_64' for r in select(rows(),donors,table())))

    def test_missing_duplicate_or_reordered_branches_rejected(self):
        donors=[dict(branch=i,rows=rows()) for i in range(64)]
        for bad in (donors[:-1],donors+[donors[0]],list(reversed(donors))):
            with self.assertRaisesRegex(ValueError,'coverage'):
                select(rows(),bad,table())

    def test_selector_does_not_accept_target_or_scores(self):
        with self.assertRaises(TypeError):
            select(rows(),[],table(),target=['trueword'])
        with self.assertRaises(TypeError):
            select(rows(),[],table(),judge_scores={})


class BindingTests(unittest.TestCase):
    def test_effective_class_controls_include_inherited_configuration(self):
        class Parent:
            RUN_SEED=0
            BODY_R4_LAMBDA=.85
            def method(self):pass
        class Child(Parent):
            RUN_SEED=92101
        self.assertEqual(effective_class_controls(Child),dict(RUN_SEED=92101,BODY_R4_LAMBDA=.85))

    def test_restore_class_controls_removes_new_overrides_and_restores_mutable_values(self):
        class Parent:RUN_SEED=0
        class Child(Parent):LAW={'p':[.5,.5]}
        saved=[(c,deepcopy(class_data(c))) for c in (Child,Parent)]
        Child.RUN_SEED=92101;Child.LAW['p'][0]=.9;Parent.RUN_SEED=7
        restore_class_controls(saved)
        self.assertEqual(Child.RUN_SEED,0)
        self.assertNotIn('RUN_SEED',vars(Child))
        self.assertEqual(Child.LAW,{'p':[.5,.5]})

    def test_complete_record_fixture(self):
        p,c=fixture_case();pipeline.validate_case_records(p,c,'A:2')

    def test_resealed_missing_all_or_one_trace_rejected(self):
        for count in (0,63):
            p,c=fixture_case();c['donors']=c['donors'][:count];c=seal({k:v for k,v in c.items() if k!='sha256'})
            with self.assertRaisesRegex(ValueError,'branches'):
                pipeline.validate_case_records(p,c,'A:2')

    def test_resealed_existing_context_misbind_rejected(self):
        for key,value in [('locus','p.2'),('page','other'),('segment_id',1),('event',1),('run',1),('bif','G:1')]:
            p,c=fixture_case();d=c['donors'][0];d[key]=value
            c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
            c=seal({k:v for k,v in c.items() if k!='sha256'})
            with self.assertRaisesRegex(ValueError,'context'):
                pipeline.validate_case_records(p,c,'A:2')

    def test_resealed_typed_branch_not_int(self):
        for value in (False,0.0):
            p,c=fixture_case();d=c['donors'][0];d['branch']=value
            c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
            c=seal({k:v for k,v in c.items() if k!='sha256'})
            with self.assertRaises(ValueError):pipeline.validate_case_records(p,c,'A:2')

    def test_resealed_missing_request_rejected(self):
        p,c=fixture_case();d=c['donors'][0];d['requests']=[]
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'})
        c=seal({k:v for k,v in c.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'request coverage'):
            pipeline.validate_case_records(p,c,'A:2')

    def test_resealed_changed_selection_rejected(self):
        p,c=fixture_case();c['selections'][0]['branch']=1
        c=seal({k:v for k,v in c.items() if k!='sha256'})
        with self.assertRaisesRegex(ValueError,'selection'):
            pipeline.validate_case_records(p,c,'A:2')

    def test_fresh_audit_rejects_forged_state_hash(self):
        p,c=fixture_case();expected=deepcopy(c);d=c['donors'][0];d['output_state_sha256']='forged'
        c['donors'][0]=seal({k:v for k,v in d.items() if k!='sha256'});c=seal({k:v for k,v in c.items() if k!='sha256'})
        pipeline.validate_case_records(p,c,'A:2')  # Local receipts alone are insufficient.
        with TemporaryDirectory() as td:
            root=Path(td)/'generated';root.mkdir()
            write_json(root/'plan.json',p);write_json(root/'A_2.json',c)
            write_json(root/'STATUS.json',dict(status='GENERATED_NOT_AUDITED',completed=['A_2.json'],plan_sha256='p'))
            write_json(root/'manifest.json',seal(dict(plan_sha256='p',files=file_inventory(root))))
            write_json(root/'AUDIT.json',dict(status='old PASS'))
            with patch.object(pipeline,'load',return_value=p),patch.object(pipeline,'Runtime'),\
                 patch.object(pipeline,'structure',return_value=(p['eligible_events'],'corpus',{})),\
                 patch.object(pipeline,'fit_fold',return_value=table()),patch.object(pipeline,'collect_case',return_value=expected):
                with self.assertRaisesRegex(ValueError,'Fresh replay differs'):
                    pipeline.audit('unused',root,Path(td)/'audit')
            self.assertFalse((root/'AUDIT.json').exists())

    def test_context_types_are_exact(self):
        ctx=dict(bif='A:2',run=92101,page='p',locus='p.1',segment_id=0,event=1)
        context(ctx)
        for key in ('run','segment_id','event'):
            for value in (True,1.0,'1',None):
                with self.assertRaises(ValueError):context(dict(ctx,**{key:value}))
        for key in ('bif','page','locus'):
            with self.assertRaises(ValueError):context(dict(ctx,**{key:1}))

    def test_receipt_rejects_changed_payload(self):
        r=seal(dict(branch=0,requests=[1,2]));r['requests'].pop()
        with self.assertRaises(ValueError):unseal(r)

    def test_typed_digest_rejects_bool_and_float(self):
        self.assertNotEqual(digest(dict(event=1)),digest(dict(event=True)))
        self.assertNotEqual(digest(dict(event=1)),digest(dict(event=1.0)))

    def test_stale_pass_after_artifact_and_checksum_update(self):
        with TemporaryDirectory() as td:
            root=Path(td);p=dict(sha256='p',bifolia=['A:2'])
            write_json(root/'plan.json',p);write_json(root/'A_2.json',dict(candidate=0))
            write_json(root/'STATUS.json',dict(status='GENERATED_NOT_AUDITED',completed=['A_2.json'],plan_sha256='p'))
            write_json(root/'manifest.json',seal(dict(plan_sha256='p',files=file_inventory(root))))
            old=pipeline.binding(p,root)
            report=root.parent/(root.name+'-report.json')
            try:
                write_json(report,seal(dict(status='PASS',plan_sha256='p',binding=old,fresh_replay_checked=True)))
                from experiments.pf_controls.common import file_hash
                write_json(root/'AUDIT.json',seal(dict(plan_sha256='p',binding=old,report=str(report),report_sha256=file_hash(report))))
                with patch.object(pipeline,'load',return_value=p):
                    self.assertEqual(pipeline.audited('unused',root),p)
                    write_json(root/'A_2.json',dict(candidate=1))
                    write_json(root/'manifest.json',seal(dict(plan_sha256='p',files=file_inventory(root,('manifest.json','AUDIT.json')))))
                    with self.assertRaisesRegex(ValueError,'Stale'):
                        pipeline.audited('unused',root)
            finally:report.unlink(missing_ok=True)

    def test_failed_audit_removes_old_seal_even_bad_plan(self):
        with TemporaryDirectory() as td:
            root=Path(td);write_json(root/'AUDIT.json',dict(status='PASS'))
            with patch.object(pipeline,'load',side_effect=ValueError('changed source')):
                with self.assertRaises(ValueError):pipeline.audit('x',root,root/'audit')
            self.assertFalse((root/'AUDIT.json').exists())


class GateTests(unittest.TestCase):
    config=dict(cluster_bootstrap_replicates=10000,minimum_contributing_bifolia=10,minimum_comparable_page_fraction=.8,
                minimum_macro_expected_accuracy=.6,cluster_bootstrap_95_lower_strictly_above=.5,
                minimum_realized_target_manipulation_fraction=.8)

    def records(self,status='DECIDED',correct=1):
        return [dict(cluster_id=str(i),status=status,correct=correct) for i in range(10)]

    def test_raw_nll_has_no_role_in_cal_truth(self):
        self.assertEqual(channel_measurement(dict(A=.2,B=.9),'A','c')['correct'],0)
        self.assertEqual(channel_measurement(dict(A=.9,B=.2),'A','c')['correct'],1)

    def test_ties_are_half_not_hashed_forced_pick(self):
        m=channel_measurement(dict(A=.4,B=.4),'A','c')
        self.assertEqual(m['status'],'TIE');self.assertIsNone(m['correct'])
        result=gate(self.records('TIE',None),[True]*10,10,self.config)
        self.assertEqual(result['macro_expected_game_accuracy'],.5)
        self.assertEqual(result['status'],'INSUFFICIENT_CAPABILITY')

    def test_na_kept_in_coverage_denominator(self):
        rr=self.records();rr[-3:]=self.records('NA',None)[-3:]
        result=gate(rr,[True]*10,10,self.config)
        self.assertEqual(result['comparable_coverage'],.7)
        self.assertEqual(result['status'],'INSUFFICIENT_CAPABILITY')

    def test_unrealized_manipulation_has_separate_failure(self):
        self.assertEqual(gate(self.records(),[False]*10,10,self.config)['status'],'MANIPULATION_NOT_REALIZED')

    def test_per_channel_preregistered_gate_pass(self):
        self.assertEqual(gate(self.records(),[True]*10,10,self.config)['status'],'PASS')

    def test_replicates_do_not_increase_leaf_count(self):
        records=[dict(cluster_id='one',status='DECIDED',correct=1) for _ in range(10)]
        result=gate(records,[True]*10,10,self.config)
        self.assertEqual(result['comparable_bifolia'],1)
        self.assertEqual(result['status'],'INSUFFICIENT_CAPABILITY')

    def test_all_six_predictions_sealed_before_any_scoring(self):
        from judges.v03.protocol import digest as jd,write_jsonl
        from experiments.pf_controls.common import file_hash
        with TemporaryDirectory() as td:
            root=Path(td);exported=root/'export';exported.mkdir();events=[];exports={}
            for lane in ('length_width','terminal','space_T_H1'):
                for direction in ('near','far'):
                    label=lane+'__'+direction;d=exported/label;d.mkdir()
                    write_jsonl(d/'inputs.jsonl',[dict(set_id=label)])
                    write_jsonl(d/'answer_key.jsonl',[dict(set_id=label,truth='A')])
                    exports[label]=dict(inputs=[{}],diagnostics=[dict(target_feature_realized=True)])
            p=dict(kind='controls',sha256='p',model_set_hash=jd({}),extractor_hash='e',protocol_hash='r',
                   eligible_cohorts={lane:['one'] for lane in ('length_width','terminal','space_T_H1')},
                   contract=dict(gate=self.config,comparison_plan_hash='main'))
            def predict(ip,output,models,primary,jobs):
                label=Path(ip).parent.name;events.append('predict');output=Path(output);output.mkdir(parents=True)
                write_jsonl(output/'predictions.jsonl',[dict(set_id=label,cluster_id='one',seed=92101)])
                write_jsonl(output/'channels.jsonl',[dict(set_id=label,channels=dict(CAL={
                    'ATOM.PARA_END/'+label.split('__')[0]:dict(A=.9,B=.2)}))])
                write_json(output/'manifest.json',dict(model_set_hash=jd({}),extractor_hash='e',protocol_hash='r',
                    input_file_sha256=file_hash(ip),channels_sha256=file_hash(output/'channels.jsonl'),
                    predictions_sha256=file_hash(output/'predictions.jsonl'),answer_key_read=False))
            def score(*args):
                self.assertEqual(events.count('predict'),6)
                self.assertTrue(read(root/'results/PREDICTIONS.json')['all_predictions_complete'])
                events.append('score')
            with patch('experiments.pf_controls.evaluation.verify_export',return_value=(p,dict(sha256='x'),exports)),\
                 patch('judges.v03.calibration.load_models',return_value=({},{})),\
                 patch('judges.v03.artifacts.predict_file',side_effect=predict),\
                 patch('judges.v03.statistics.score',side_effect=score):
                result=evaluate('plan','generated',exported,'models',root/'results')
            self.assertEqual(events,['predict']*6+['score']*6)
            self.assertTrue(result['independent_review_required'])
            self.assertEqual(len(result['channel_results']),3)
            self.assertFalse((root/'results/CAPABILITY_REVIEW.json').exists())

    def test_wrong_fixed_model_rejected_before_predicting(self):
        with patch('experiments.pf_controls.evaluation.verify_export',return_value=(dict(model_set_hash='wrong'),{},{})),\
             patch('judges.v03.calibration.load_models',return_value=({},{})),\
             patch('judges.v03.artifacts.predict_file') as predictor:
            with self.assertRaisesRegex(ValueError,'model set mismatch'):
                evaluate('plan','generated','exported','models','unused')
            predictor.assert_not_called()


if __name__=='__main__':unittest.main()
