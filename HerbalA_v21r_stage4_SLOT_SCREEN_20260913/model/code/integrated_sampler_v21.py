from __future__ import annotations
import json
import numpy as np
import v19r_rb3_pw2_close1 as m
from bti2_patch_sampler import PatchSampler as ParentPatchSampler
from route_map_model import subseqs
from w2_sibling_generator import W2SiblingGenerator,W2SiblingKey,W2SiblingState,make_anchor,assert_pool_constraints
from w2_slot_generator import W2SlotGenerator,SlotContext,SlotSelectionKey

class V21CalibratedPatchSampler(ParentPatchSampler):
    """Promoted parent selector: BODY non-prefix R4 lambda=0.85."""
    BODY_R4_LAMBDA=0.85
    DISABLE_W2_EXACT4_BT=False

    def _bank_bt_enabled(self, st, role, first, excluded_end, end, line_end):
        enabled=(not excluded_end and role!='PHW' and bool(st.bt_active))
        if enabled and bool(self.DISABLE_W2_EXACT4_BT):
            try:
                board=st.board(role,bool(end),bool(line_end))
            except Exception:
                board=None
            if role=='W2' and board=='W2' and len(first)==4:
                enabled=False
        return bool(enabled)
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
        bt_enabled=self._bank_bt_enabled(st,role,first,excluded_end,end,line_end)
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

class V20CompatSampler(V21CalibratedPatchSampler):
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

class V21SafeLeftSampler(V20CompatSampler):
    """Stage-2 SAFE_LEFT: v20r W2 exact-L4 H2 splice with only LEFT bridge legality.

    All proposal generation, K16 collection, H1/exact-length/stable-width constraints,
    same-H2-width constraint, H3+/terminal freezing, selector, RNG namespaces, and
    fallback semantics are inherited unchanged from V20CompatSampler.  The only
    behavioral change is removal of the RIGHT H2-H3-H4 support requirement.
    """

    def _eligible(self, anchor, state, gen, pool):
        _g1, _g2, g3 = gen._gains(anchor, state)
        tab = self.base.tables
        h1 = int(anchor.glyphs[0])
        h2a = int(anchor.glyphs[1])
        h3 = int(anchor.glyphs[2])
        lp = int(state.lp)
        end = bool(state.end)
        line_end = bool(state.line_end_boundary)
        w2a = int(m.WIDTH[h2a])
        out = []
        for seq in pool.siblings:
            h2 = int(seq[1])
            if int(m.WIDTH[h2]) != w2a:
                continue
            p2 = np.asarray(tab.base_nonend('W2', lp, end, line_end, 2, h1, h2), float) * np.asarray(g3[h1, h2], float)
            if p2[h3] <= 0:
                continue
            out.append((h2, seq))
        return out

    def __call__(self, *args, **kwargs):
        selected = super().__call__(*args, **kwargs)
        record = self.last_request
        if record is not None and record.get('h2splice_applied'):
            record['h2splice_bridge_mode'] = 'LEFT_ONLY'
            record['h2splice_left_support_required'] = True
            record['h2splice_right_support_required'] = False
            record['direct_reason'] = 'W2_H2_ONLY_SPLICE_L4_K16_LEFT_ONLY'
        if self.state is not None and self.state.last_proposal.get('w2h2splice'):
            self.state.last_proposal['w2h2splice_bridge_mode'] = 'LEFT_ONLY'
        return selected


class V21W2BtOffMixin:
    """Disable only the parent candidate-bank bT gate for W2 exact-4 anchors."""
    DISABLE_W2_EXACT4_BT=True


class V21SafeLeftBtOffSampler(V21W2BtOffMixin, V21SafeLeftSampler):
    """Stage-4 formal control: SAFE_LEFT with W2 exact-4 bT scoring disabled."""
    pass


class V21SlotBtOffSampler(V21W2BtOffMixin, V21CalibratedPatchSampler):
    """Stage-4 SLOT generator with W2 exact-4 bT scoring disabled."""
    EXACT_LENGTH=4
    RUN_SEED=0
    TARGET_BIF=''
    SLOT_TABLE=None
    SIBLING_K=16
    SIBLING_MAX_DRAWS=4096

    def _slot_key(self, record):
        return SlotSelectionKey(
            run_seed=int(self.RUN_SEED), bif=str(self.TARGET_BIF),
            page=str(record['page']), locus=str(record['locus']),
            segment_id=int(record['segment_id']), word_index=int(record['word_index']),
            proposal_id=int(record['proposal_id']), namespace='V21_W2_SLOT_SELECT_V1')

    def _request_state(self, args, kwargs, st):
        end=bool(args[10]); line_end=bool(kwargs.get('line_end_boundary',False))
        return W2SiblingState(lp=int(args[4]),rstart=int(args[6]),end=end,
            line_end_boundary=line_end,row_phase=str(st.row_phase),board='W2',physical_head=False)

    def _left_support_fn(self, anchor, state, gen):
        _g1,_g2,g3=gen._gains(anchor,state); tab=self.base.tables
        lp=int(state.lp); end=bool(state.end); line_end=bool(state.line_end_boundary)
        def legal(h1,h2,h3):
            p2=np.asarray(tab.base_nonend('W2',lp,end,line_end,2,int(h1),int(h2)),float)*np.asarray(g3[int(h1),int(h2)],float)
            return bool(p2[int(h3)]>0)
        return legal

    def _safe_left_fallback(self, anchor_seq, args, kwargs, record, st):
        anchor=make_anchor(anchor_seq,m.stable_width); state=self._request_state(args,kwargs,st)
        key=W2SiblingKey(run_seed=int(self.RUN_SEED),bif=str(self.TARGET_BIF),page=str(record['page']),locus=str(record['locus']),segment_id=int(record['segment_id']),word_index=int(record['word_index']),proposal_id=int(record['proposal_id']),namespace='W2H2SPLICE_POOL_V1')
        gen=W2SiblingGenerator(cdf=args[0],quad=args[1],base=self.base.parent,tables=self.base.tables,patch=self.base.patch,stable_width=m.stable_width)
        pool=gen.collect(anchor,state,key,target_accepts=int(self.SIBLING_K),max_draws=int(self.SIBLING_MAX_DRAWS)); assert_pool_constraints(pool,m.stable_width)
        legal=self._left_support_fn(anchor,state,gen); h2a=int(anchor_seq[1]); w2a=int(m.WIDTH[h2a]); elig=[]
        for seq in pool.siblings:
            h2=int(seq[1]); h3=int(anchor_seq[2])
            if int(m.WIDTH[h2])!=w2a: continue
            if legal(int(anchor_seq[0]),h2,h3): elig.append(h2)
        if not elig:
            return tuple(anchor_seq), True, int(pool.accepted), int(len(elig)), int(pool.draws), None
        sk=W2SiblingKey(run_seed=int(self.RUN_SEED),bif=str(self.TARGET_BIF),page=str(record['page']),locus=str(record['locus']),segment_id=int(record['segment_id']),word_index=int(record['word_index']),proposal_id=int(record['proposal_id']),namespace='W2H2SPLICE_SELECT_V1')
        rr=sk.rng(); h2=int(elig[int(rr.integers(len(elig)))]); z=list(anchor_seq); z[1]=h2
        return tuple(z), False, int(pool.accepted), int(len(elig)), int(pool.draws), sk.digest_hex()

    def __call__(self,*args,**kwargs):
        st=self.state
        anchor_seq=tuple(super().__call__(*args,**kwargs))
        if st is None or not anchor_seq: return anchor_seq
        role=args[2]; end=bool(args[10]); line_end=bool(kwargs.get('line_end_boundary',False)); board=st.board(role,end,line_end); record=self.last_request
        rng_before=json.dumps(args[5].bit_generator.state,sort_keys=True,default=str); sem_before=st.semantic_digest()
        if record is not None:
            record['w2_slot_applied']=False
            record['w2_exact4_bt_forced_off']=bool(role=='W2' and board=='W2' and len(anchor_seq)==4)
        if role!='W2' or board!='W2' or len(anchor_seq)!=int(self.EXACT_LENGTH) or record is None:
            return anchor_seq
        W=int(m.stable_width(anchor_seq))
        if W not in (4,5,6,7,8) or self.SLOT_TABLE is None or st.prev_terminal is None:
            reason='WIDTH_OUTSIDE' if W not in (4,5,6,7,8) else 'TABLE_OR_T_UNAVAILABLE'
            selected,fb_anchor,pooln,elign,draws,fdigest=self._safe_left_fallback(anchor_seq,args,kwargs,record,st)
            record.update(w2_slot_applied=True,w2_slot_fallback=True,w2_slot_fallback_stage='SAFE_LEFT_BT_OFF',w2_slot_fallback_reason=reason,w2_slot_candidate_count=0,w2_slot_anchor=m.word_str(anchor_seq),w2_slot_selected=m.word_str(selected),w2_slot_safeleft_pool_n=pooln,w2_slot_safeleft_eligible_n=elign,w2_slot_safeleft_draws=draws,w2_slot_safeleft_anchor_fallback=fb_anchor,w2_slot_safeleft_digest=fdigest,selected=m.word_str(selected))
            st.bump('w2slot_events'); st.bump('w2slot_fallback'); st.bump('w2slot_changed',int(selected!=anchor_seq))
            st.last_proposal.update(w2slot=True,w2slot_fallback=True,w2slot_changed=bool(selected!=anchor_seq))
            assert json.dumps(args[5].bit_generator.state,sort_keys=True,default=str)==rng_before; assert st.semantic_digest()==sem_before
            return selected
        anchor=make_anchor(anchor_seq,m.stable_width); state=self._request_state(args,kwargs,st)
        gen=W2SiblingGenerator(cdf=args[0],quad=args[1],base=self.base.parent,tables=self.base.tables,patch=self.base.patch,stable_width=m.stable_width)
        legal=self._left_support_fn(anchor,state,gen)
        slot=W2SlotGenerator(self.SLOT_TABLE,m.WIDTH,m.stable_width)
        try:
            ctx=SlotContext(h1=int(anchor_seq[0]),total_width=W,previous_terminal=int(st.prev_terminal),row_phase=str(st.row_phase))
            cands=slot.enumerate(ctx,legal)
            probs=slot.softmax(cands)
        except Exception as exc:
            cands=[]; probs=np.asarray([],float); slot_exc=f'{type(exc).__name__}:{exc}'
        else:
            slot_exc=None
        if not cands:
            selected,fb_anchor,pooln,elign,draws,fdigest=self._safe_left_fallback(anchor_seq,args,kwargs,record,st)
            record.update(w2_slot_applied=True,w2_slot_fallback=True,w2_slot_fallback_stage='SAFE_LEFT_BT_OFF',w2_slot_fallback_reason='NO_LEGAL_CANDIDATE' if slot_exc is None else 'INVALID_NORMALIZATION_OR_TABLE',w2_slot_exception=slot_exc,w2_slot_candidate_count=0,w2_slot_anchor=m.word_str(anchor_seq),w2_slot_selected=m.word_str(selected),w2_slot_safeleft_pool_n=pooln,w2_slot_safeleft_eligible_n=elign,w2_slot_safeleft_draws=draws,w2_slot_safeleft_anchor_fallback=fb_anchor,w2_slot_safeleft_digest=fdigest,selected=m.word_str(selected))
            st.bump('w2slot_events'); st.bump('w2slot_fallback'); st.bump('w2slot_changed',int(selected!=anchor_seq))
            st.last_proposal.update(w2slot=True,w2slot_fallback=True,w2slot_changed=bool(selected!=anchor_seq))
        else:
            sk=self._slot_key(record); j,cand,digest=slot.select(cands,probs,sk); selected=tuple(cand.glyphs)
            assert role=='W2' and board=='W2'; assert len(selected)==4; assert selected[0]==anchor_seq[0]; assert int(m.stable_width(selected))==int(m.stable_width(anchor_seq)); assert int(m.stable_width(selected)) in (4,5,6,7,8); assert int(m.WIDTH[selected[3]])==1; assert legal(*selected[:3])
            H2p=self.SLOT_TABLE.prob_h2(int(selected[0]),W,int(st.prev_terminal),str(st.row_phase)); H3p=self.SLOT_TABLE.prob_h3(int(selected[0]),W); H4p=self.SLOT_TABLE.prob_h4(int(selected[2]))
            assert np.isfinite(H2p).all() and np.isfinite(H3p).all() and np.isfinite(H4p).all()
            record.update(w2_slot_applied=True,w2_slot_fallback=False,w2_slot_fallback_stage=None,w2_slot_fallback_reason=None,w2_slot_anchor=m.word_str(anchor_seq),w2_slot_selected=m.word_str(selected),w2_slot_candidate_count=int(len(cands)),w2_slot_selection_digest=digest,w2_slot_h2_depth=int(self.SLOT_TABLE.h2_depth),w2_slot_total_width=W,w2_slot_prev_terminal=int(st.prev_terminal),w2_slot_score=float(cand.score),w2_slot_logp_h2=float(cand.logp_h2),w2_slot_logp_h3=float(cand.logp_h3),w2_slot_logp_h4=float(cand.logp_h4),selected=m.word_str(selected),selected_index=int(j),candidates=[m.word_str(c.glyphs) for c in cands],scores=[float(c.score) for c in cands],probabilities=probs.tolist(),candidate_count=int(len(cands)),requested_K=int(len(cands)),shortfall=False,proposal_draws=0,probability_entropy=float(-np.sum(probs*np.log(probs))),candidate_lengths=[4]*len(cands),candidate_widths=[W]*len(cands),direct=False,direct_reason='V21_W2_SLOT_SELECT_V1',alternative_rng_end=None)
            st.bump('w2slot_events'); st.bump('w2slot_changed',int(selected!=anchor_seq)); st.bump('w2slot_candidates',len(cands))
            st.last_proposal.update(w2slot=True,w2slot_fallback=False,w2slot_changed=bool(selected!=anchor_seq),w2slot_candidate_count=len(cands),w2slot_anchor=m.word_str(anchor_seq),w2slot_selected=m.word_str(selected))
        assert json.dumps(args[5].bit_generator.state,sort_keys=True,default=str)==rng_before; assert st.semantic_digest()==sem_before
        record['w2_slot_parent_rng_untouched']=True; record['w2_slot_semantic_state_untouched']=True
        return selected


# Stage-1 compatibility aliases. No behavior changes.
CalibratedPatchSampler = V21CalibratedPatchSampler
PromotedW2H2L4K16Sampler = V20CompatSampler
SafeLeftW2H2L4K16Sampler = V21SafeLeftSampler
SafeLeftBtOffSampler = V21SafeLeftBtOffSampler
SlotBtOffSampler = V21SlotBtOffSampler
