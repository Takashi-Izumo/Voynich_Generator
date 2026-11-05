"""Exercise the literal parent commit chain, not a second implementation of it."""
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
import unittest

from experiments.m1_pf.runtime import Runtime as SourceRuntime
from experiments.pf_generation.surface_commit import sampler_class,audit_requests


class State:
    def __init__(self):
        self.prev_terminal=None;self.current=('route',);self.surface_commits=[]
        self.route_words=[];self.at_semantic_commit=[];self.stats=Counter()
        self.physical_key=('p','p.1');self.segment_id=0;self.step=0;self.word_index=1;self.row_phase='MIDDLE'
        self.par_h1_para_line_raw=5;self.par_h1_raw_para_final=False;self.par_h1_pending_n=0;self.notes=[]

    def commit(self,seq,role,sr):
        self.route_words.append(tuple(seq));self.current=tuple(seq)

    def bump(self,key,n=1):self.stats[key]+=n
    def board(self,*args):return 'BODY'

    def commit_surface(self,seq,stable,row,proposal):
        before=self.prev_terminal
        self.prev_terminal=int(seq[-1]) if isinstance(seq[-1],int) else None
        self.at_semantic_commit.append(tuple(seq))
        self.surface_commits.append(dict(**deepcopy(row),proposal_id=proposal,
            prev_terminal_before=before,prev_terminal_after=self.prev_terminal))

    def paragraph_h1_note(self,h1,expected):
        self.notes.append((h1,expected));self.par_h1_pending_n+=1


class SurfaceCommitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime=SourceRuntime()
        cls.parent=cls.runtime.active.configure(92101,'A:2')
        cls.m=cls.runtime.engine.m
        cls.fixed=sampler_class(cls.parent,cls.m)

    def fixture(self,stable,visible,role='W2',flags=None,fixed=True):
        cls=self.fixed if fixed else self.parent
        s=object.__new__(cls);s.state=State()
        record=dict(proposal_id=0,selected=self.m.word_str(stable),outcome='PROPOSED',role=role,
                    after_rare=self.m.word_str(visible),prev_terminal=None,committed_to_final_page=True,**(flags or {}))
        s.last_request=record;s.requests=[record];s.word_first_request=0;s.next_proposal_id=1
        row=dict(page='p',locus='p.1',segment_id=0,role=role,surface=self.m.word_str(visible),
                 stable_surface=self.m.word_str(stable),stable_glyph_len=len(stable),draw_segment_end=0)
        s.commit_word(stable,role,None)
        s.commit_surface(visible,stable,role,None,row)
        return s,row

    def next_request(self,s):
        args=[None,None,'BODY',3,2,None,8,None,None,None,False,None]
        return s._start_request(s.state,args,{})

    def test_w2_m_deletion_commits_final_h2_before_next_space_request(self):
        flags=dict(b2_h2_changed=True,b2_h2_selected_h2=12)
        s,row=self.fixture((10,10,20),(10,10),flags=flags)
        self.assertEqual(s.state.at_semantic_commit,[(10,12)])
        self.assertEqual(s.state.prev_terminal,12)
        self.assertEqual(s.state.surface_commits[-1]['prev_terminal_after'],12)
        self.assertEqual(self.next_request(s)['prev_terminal'],12)
        self.assertEqual(s.state.route_words,[(10,10,20)])
        self.assertEqual(row['surface'],self.m.word_str((10,12)))

    def test_legacy_reproduces_the_fixture_state_divergence(self):
        s,row=self.fixture((10,10,20),(10,10),flags=dict(b2_h2_changed=True,b2_h2_selected_h2=12),fixed=False)
        self.assertEqual(row['surface'],self.m.word_str((10,12)))
        self.assertEqual(s.state.prev_terminal,10)
        self.assertEqual(self.next_request(s)['prev_terminal'],10)

    def test_body_h1_m_deletion_updates_terminal_and_pending_statistics(self):
        flags=dict(paragraph_h1_changed=True,paragraph_h1_selected_h1=12,paragraph_h1_commit_eligible=True,
                   paragraph_h1_expected=[1/22]*22)
        s,row=self.fixture((10,20),(10,),role='BODY',flags=flags)
        self.assertEqual(s.state.at_semantic_commit,[(12,)])
        self.assertEqual(s.state.prev_terminal,12)
        self.assertEqual(self.next_request(s)['prev_terminal'],12)
        self.assertEqual(s.state.notes,[(12,[1/22]*22)])
        self.assertEqual(s.state.route_words,[(10,20)])

    def test_nonterminal_h2_kept_m_unchanged_h2_and_rare_suffix_are_literal_parent_paths(self):
        for visible,changed in [((10,10,20),True),((10,10),False),((10,10,'g'),True)]:
            flags=dict(b2_h2_changed=changed,b2_h2_selected_h2=12)
            s,row=self.fixture((10,10,20),visible,flags=flags)
            original,oldrow=self.fixture((10,10,20),visible,flags=flags,fixed=False)
            self.assertEqual(row,oldrow);self.assertEqual(s.requests,original.requests)
            self.assertEqual(vars(s.state),vars(original.state))
            self.assertNotIn('pfgen_terminal_precommit',s.last_request)

    def test_rare_prefix_retains_actual_terminal_position(self):
        s,row=self.fixture((10,10,20),('g',10,10),flags=dict(b2_h2_changed=True,b2_h2_selected_h2=12))
        self.assertEqual(s.state.at_semantic_commit,[('g',10,12)])
        self.assertEqual(s.last_request['pfgen_terminal_precommit']['physical_position'],2)
        self.assertEqual(audit_requests(s.requests,s.state.surface_commits,'PF_GATE_LENGTH'),1)

    def test_f1lf_stage3d_preserves_two_stage_route_visible_commit(self):
        flags=dict(v22_3_stage3d_applied=True,v22_2_f1lf_router_off_applied=True,
                   v22_3_stage3d_child_seq=[10,12,18],v22_2_child_seq=[10,12,21])
        s,row=self.fixture((10,10,21),(10,10,21),role='F1',flags=flags)
        old,oldrow=self.fixture((10,10,21),(10,10,21),role='F1',flags=flags,fixed=False)
        self.assertEqual(row,oldrow);self.assertEqual(s.requests,old.requests)
        self.assertEqual(vars(s.state),vars(old.state))
        self.assertEqual(s.state.route_words,[(10,12,21)])
        self.assertEqual(s.state.prev_terminal,18)

    def test_next_plant_segment_resets_terminal(self):
        s,row=self.fixture((10,10,20),(10,10),flags=dict(b2_h2_changed=True,b2_h2_selected_h2=12))
        # Invoke the real state begin(), including paragraph state/reset logic.
        r=self.runtime
        fc,core,cfg,prev,patch,tables=r.case_inputs('A:2')
        old=r.rb.PatchMapState
        try:
            r.rb.PatchMapState=r.active.ParagraphH1PatchMapState
            state,_,_=r.rb.init_state(r.C,fc,cfg,prev,92101,patch,tables)
        finally:r.rb.PatchMapState=old
        sr=next(x for x in r.C.schedules[fc.target_page].itertuples(index=False) if x.segment_id>0)
        state.motion.prev_terminal=12
        state.motion.begin(sr)
        self.assertIsNone(state.motion.prev_terminal)
        self.assertEqual(state.motion.board('BODY',False,False),'BODY')

    def test_width_change_is_rejected_before_semantic_commit(self):
        with self.assertRaisesRegex(ValueError,'physical width'):
            self.fixture((10,10,20),(10,10),flags=dict(b2_h2_changed=True,b2_h2_selected_h2=2))

    def test_receipt_missing_or_relabelled_is_rejected(self):
        s,row=self.fixture((10,10,20),(10,10),flags=dict(b2_h2_changed=True,b2_h2_selected_h2=12))
        self.assertEqual(audit_requests(s.requests,s.state.surface_commits,'PF_GATE_LENGTH'),1)
        for key,value in [('writer','BODY_H1'),('selected_terminal',10),('physical_position',True)]:
            records=deepcopy(s.requests);records[0]['pfgen_terminal_precommit'][key]=value
            with self.assertRaises(ValueError):audit_requests(records,s.state.surface_commits,'PF_GATE_LENGTH')
        records=deepcopy(s.requests);records[0].pop('pfgen_terminal_precommit')
        with self.assertRaisesRegex(ValueError,'Missing'):
            audit_requests(records,s.state.surface_commits,'PF_GATE_LENGTH')

    def two_words(self):
        s,row=self.fixture((10,10,20),(10,10),flags=dict(b2_h2_changed=True,b2_h2_selected_h2=12))
        next_word=self.next_request(s)
        next_word.update(selected=self.m.word_str((10,10)),committed_to_final_page=True,after_rare=self.m.word_str((10,10)))
        next_row=dict(row,role='BODY',surface=self.m.word_str((10,10)),stable_surface=self.m.word_str((10,10)))
        s.commit_surface((10,10),(10,10),'BODY',None,next_row)
        self.assertEqual(audit_requests(s.requests,s.state.surface_commits,'PF_GATE_LENGTH'),1)
        return s

    def test_next_request_state_tamper_is_rejected(self):
        s=self.two_words();s.requests[1]['prev_terminal']=10
        with self.assertRaisesRegex(ValueError,'Next request'):
            audit_requests(s.requests,s.state.surface_commits,'PF_GATE_LENGTH')

    def test_forging_logs_to_match_wrong_state_still_rejects_actual_surface(self):
        s=self.two_words();s.state.surface_commits[0]['prev_terminal_after']=10
        s.state.surface_commits[1]['prev_terminal_before']=10;s.requests[1]['prev_terminal']=10
        with self.assertRaisesRegex(ValueError,'actual committed surface'):
            audit_requests(s.requests,s.state.surface_commits,'PF_GATE_LENGTH')


if __name__=='__main__':unittest.main()
