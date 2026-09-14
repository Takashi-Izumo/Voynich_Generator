from __future__ import annotations
import json
import numpy as np
import v19r_rb3_pw2_close1 as m
from bti2_patch_sampler import PatchSampler as ParentPatchSampler
from route_map_model import subseqs
from w2_sibling_generator import W2SiblingGenerator,W2SiblingKey,W2SiblingState,make_anchor,assert_pool_constraints

class CalibratedPatchSampler(ParentPatchSampler):
    """Promoted parent selector: BODY non-prefix R4 lambda=0.85."""
    BODY_R4_LAMBDA=0.85
    def __call__(self,*args,**kwargs):
        st=self.state
        if st is None:return super().__call__(*args,**kwargs)
        semantic_before=st.semantic_digest();st.last_proposal={}
        record=self._start_request(st,args,kwargs)
        first=self.base(*args,**kwargs)
        record['first']=m.word_str(first);record['first_len']=len(first);record['first_width']=m.stable_width(first)
        role=args[2];R=int(args[6]);end=bool(args[10]);line_end=bool(kwargs.get('line_end_boundary',False));w=m.stable_width(first)
        if st.cfg.K<=1 or st.cfg.beta==0 or role=='PHW' or not first or not (w==R if end else w+2<=R):
            record.update(selected=m.word_str(first),candidates=[m.word_str(first)],scores=[],probabilities=[1.],selected_index=0,direct=True,direct_reason='PHW' if role=='PHW' else 'NO_BANK_OR_FIT')
            assert semantic_before==st.semantic_digest();self.tx_checks+=1;return first
        st.attempts+=1;rr=np.random.default_rng(np.random.SeedSequence([st.seed,st.step,st.attempts,4707]));cands=[first];newargs=list(args);newargs[5]=rr;draws=0
        while len(cands)<st.cfg.K and draws<64*st.cfg.K:
            draws+=1;s=self.base(*newargs,**kwargs)
            if not s:continue
            sw=m.stable_width(s)
            if sw!=w:continue
            if st.cfg.same_len and len(s)!=len(first):continue
            cands.append(s)
        scores=[];exs=[];btflags=[];r4rest=[]
        excluded_end=end and line_end if st.patch.boundary_policy=='B_ALIGN' else end
        bt_enabled=(not excluded_end and role!='PHW' and bool(st.bt_active))
        for c in cands:
            sc,ex=st.candidate_features(c)
            rest=0.0
            if role=='BODY' and st.cfg.min_n<=4 and len(c)>=4:
                ss=subseqs(tuple(int(x) for x in c),4);hits=ss & st.paths.get(4,frozenset())
                if hits:
                    pref=tuple(int(x) for x in c[:4]);nh=len(hits)-int(pref in hits);rest=float(st.cfg.beta*2.0*nh)
                    sc-=(1.0-float(self.BODY_R4_LAMBDA))*rest
            bt=tuple(int(x) for x in c[-2:]) if len(c)>=2 else None;active=bool(bt_enabled and bt in st.bt_active)
            if active and st.bt_lambda:sc+=st.bt_lambda
            if bt_enabled and bt is not None and st.bt_profile_lambda:sc+=st.bt_profile_lambda*max(-2.,min(2.,float(st.bt_leafex.get(bt,0.))))
            scores.append(sc);exs.append(ex);btflags.append(active);r4rest.append(rest)
        scores=np.asarray(scores,float)
        if st.cfg.deterministic:j=int(np.argmax(scores));p=np.zeros(len(cands));p[j]=1.
        else:p=np.exp(scores-scores.max());p/=p.sum();j=int(rr.choice(len(cands),p=p))
        st.bump('events');st.bump('changed',int(tuple(cands[j])!=tuple(first)));st.bump('candidates',len(cands));st.bump('shortfall',int(len(cands)<st.cfg.K))
        if bt_enabled:
            any_active=any(btflags);base_active=bool(btflags[0]);selected_active=bool(btflags[j]);st.bump('bt_events');st.bump('bt_any_active',int(any_active));st.bump('bt_base_active',int(base_active));st.bump('bt_selected_active',int(selected_active));st.bump('bt_opportunity_missed',int(any_active and not base_active));st.bump('bt_opportunity_recovered',int(any_active and not base_active and selected_active))
        st.last_proposal=dict(candidate_count=len(cands),candidate_rank=j,candidate_score=float(scores[j]),proposal_draws=draws,selected_exact=len(exs[j]),base_width=w,base_len=len(first),selected_len=len(cands[j]),bt_enabled=bool(bt_enabled),bt_any_active=bool(any(btflags)) if bt_enabled else False,bt_base_active=bool(btflags[0]) if bt_enabled else False,bt_selected_active=bool(btflags[j]) if bt_enabled else False,bt_active_candidates=int(sum(btflags)) if bt_enabled else 0,body_r4_lambda=float(self.BODY_R4_LAMBDA),body_r4_rest_selected=float(r4rest[j]))
        assert all(m.stable_width(c)==w for c in cands);assert not st.cfg.same_len or all(len(c)==len(first) for c in cands)
        record.update(direct=False,candidate_count=len(cands),proposal_draws=draws,requested_K=st.cfg.K,shortfall=len(cands)<st.cfg.K,candidates=[m.word_str(c) for c in cands],scores=scores.tolist(),probabilities=p.tolist(),probability_entropy=float(-np.sum(p[p>0]*np.log(p[p>0]))),selected_index=j,selected=m.word_str(cands[j]),bt_enabled=bool(bt_enabled),physical_line_final_candidate=bool(end and line_end),candidate_lengths=[len(c) for c in cands],candidate_widths=[m.stable_width(c) for c in cands],alternative_rng_end=rr.bit_generator.state,body_r4_lambda=float(self.BODY_R4_LAMBDA),body_r4_rest_scores=r4rest)
        assert semantic_before==st.semantic_digest();self.tx_checks+=1;return cands[j]

class PromotedW2H2L4K16Sampler(CalibratedPatchSampler):
    """Promoted W2 exact-L4, K16, legal same-width H2-only splice.

    The calibrated parent first selects the anchor.  Only for W2 anchors of exact
    glyph length 4, a dedicated SHA-256 side-stream generates up to K16 siblings
    with H1/exact length/stable physical width fixed.  Legal H2 values must have
    anchor-H2 glyph width and positive parent bridge support to anchor H3/H4.
    Only H2 is spliced; H1, H3+, terminal, exact length and physical width remain
    identical to the anchor.  No known3/W2-residual table is used.
    """
    SIBLING_K=16
    SIBLING_MAX_DRAWS=4096
    EXACT_LENGTH=4
    RUN_SEED=0
    TARGET_BIF=''

    def _select_rng(self,record):
        k=W2SiblingKey(run_seed=int(self.RUN_SEED),bif=str(self.TARGET_BIF),page=str(record['page']),locus=str(record['locus']),segment_id=int(record['segment_id']),word_index=int(record['word_index']),proposal_id=int(record['proposal_id']),namespace='W2H2SPLICE_SELECT_V1')
        return k,k.rng()

    def _eligible(self,anchor,state,gen,pool):
        g1,g2,g3=gen._gains(anchor,state);tab=self.base.tables
        h1=int(anchor.glyphs[0]);h2a=int(anchor.glyphs[1]);h3=int(anchor.glyphs[2]);h4=int(anchor.glyphs[3])
        lp=int(state.lp);end=bool(state.end);line_end=bool(state.line_end_boundary);w2a=int(m.WIDTH[h2a]);out=[]
        for seq in pool.siblings:
            h2=int(seq[1])
            if int(m.WIDTH[h2])!=w2a:continue
            p2=np.asarray(tab.base_nonend('W2',lp,end,line_end,2,h1,h2),float)*np.asarray(g3[h1,h2],float)
            if p2[h3]<=0:continue
            p3=np.asarray(tab.base_nonend('W2',lp,end,line_end,3,h2,h3),float)
            if p3[h4]<=0:continue
            out.append((h2,seq))
        return out

    def __call__(self,*args,**kwargs):
        st=self.state;anchor_seq=tuple(super().__call__(*args,**kwargs))
        if st is None or not anchor_seq:return anchor_seq
        role=args[2];end=bool(args[10]);line_end=bool(kwargs.get('line_end_boundary',False));board=st.board(role,end,line_end);record=self.last_request
        rng_before=json.dumps(args[5].bit_generator.state,sort_keys=True,default=str);sem_before=st.semantic_digest()
        if role!='W2' or board!='W2' or len(anchor_seq)!=int(self.EXACT_LENGTH) or record is None:
            if record is not None:record['h2splice_applied']=False
            return anchor_seq
        anchor=make_anchor(anchor_seq,m.stable_width)
        state=W2SiblingState(lp=int(args[4]),rstart=int(args[6]),end=end,line_end_boundary=line_end,row_phase=str(st.row_phase),board='W2',physical_head=False)
        key=W2SiblingKey(run_seed=int(self.RUN_SEED),bif=str(self.TARGET_BIF),page=str(record['page']),locus=str(record['locus']),segment_id=int(record['segment_id']),word_index=int(record['word_index']),proposal_id=int(record['proposal_id']),namespace='W2H2SPLICE_POOL_V1')
        gen=W2SiblingGenerator(cdf=args[0],quad=args[1],base=self.base.parent,tables=self.base.tables,patch=self.base.patch,stable_width=m.stable_width)
        pool=gen.collect(anchor,state,key,target_accepts=int(self.SIBLING_K),max_draws=int(self.SIBLING_MAX_DRAWS));assert_pool_constraints(pool,m.stable_width)
        for f in ('selected','selected_index','candidates','scores','probabilities','candidate_count','requested_K','shortfall','proposal_draws','probability_entropy','candidate_lengths','candidate_widths','direct','direct_reason','alternative_rng_end'):
            if f in record:record['anchor_'+f]=record[f]
        elig=self._eligible(anchor,state,gen,pool)
        record.update(h2splice_applied=True,h2splice_anchor=m.word_str(anchor_seq),h2splice_pool_n=int(pool.accepted),h2splice_eligible_n=int(len(elig)),h2splice_draws=int(pool.draws),h2splice_shortfall=bool(pool.accepted<int(self.SIBLING_K)),h2splice_anchor_h2=int(anchor_seq[1]),h2splice_anchor_terminal=int(anchor_seq[-1]))
        if not elig:
            selected=anchor_seq;j=0;cands=[anchor_seq];fallback=True;sel_digest=None
        else:
            sk,srng=self._select_rng(record);j=int(srng.integers(len(elig)));h2=int(elig[j][0]);tmp=list(anchor_seq);tmp[1]=h2;selected=tuple(tmp);cands=[]
            for hh,_ in elig:
                z=list(anchor_seq);z[1]=int(hh);cands.append(tuple(z))
            fallback=False;sel_digest=sk.digest_hex()
        assert selected[0]==anchor_seq[0];assert selected[2:]==anchor_seq[2:];assert selected[-1]==anchor_seq[-1];assert len(selected)==4;assert int(m.stable_width(selected))==int(m.stable_width(anchor_seq))
        p=[1.0/len(cands)]*len(cands)
        record.update(h2splice_fallback_anchor=fallback,h2splice_selection_digest=sel_digest,h2splice_selected=m.word_str(selected),h2splice_selected_index=int(j),h2splice_changed=bool(selected!=anchor_seq),selected=m.word_str(selected),selected_index=int(j),candidates=[m.word_str(x) for x in cands],scores=[],probabilities=p,candidate_count=len(cands),requested_K=int(self.SIBLING_K),shortfall=bool(pool.accepted<int(self.SIBLING_K)),proposal_draws=int(pool.draws),probability_entropy=float(np.log(len(cands))) if cands else 0.,candidate_lengths=[4 for _ in cands],candidate_widths=[m.stable_width(x) for x in cands],direct=False,direct_reason='W2_H2_ONLY_SPLICE_L4_K16')
        st.bump('w2h2splice_events');st.bump('w2h2splice_changed',int(selected!=anchor_seq));st.bump('w2h2splice_zero_fallback',int(fallback))
        st.last_proposal.update(w2h2splice=True,w2h2splice_changed=bool(selected!=anchor_seq),w2h2splice_anchor=m.word_str(anchor_seq),w2h2splice_selected=m.word_str(selected),w2h2splice_exact_length=4,w2h2splice_k=16)
        assert json.dumps(args[5].bit_generator.state,sort_keys=True,default=str)==rng_before;assert st.semantic_digest()==sem_before
        record['h2splice_parent_rng_untouched']=True;record['h2splice_semantic_state_untouched']=True
        return selected
