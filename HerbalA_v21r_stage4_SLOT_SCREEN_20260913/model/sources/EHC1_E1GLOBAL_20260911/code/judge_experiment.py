"""Evaluate sealed fixed arms using the exact frozen 16 judges + RAW4.
Additional T/H1/TH1 JSD and log-joint components use the DIAG1 definitions.
No coefficient selection or generator modifications occur here.
"""
from experiment_env import *
from entry_global_only import CANDIDATE
from collections import defaultdict
import json,time,math

OUT=ROOT/'outputs/judged'
PRIMARY=['SPACE_RAW','H2_RAW']

def paired_stats(x,boot=10000):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    rg=np.random.default_rng(26091151)
    bs=x[rg.integers(len(x),size=(boot,len(x)))].mean(1)
    return dict(leaves=len(x),improvement_mean=float(x.mean()),leaves_improved=int((x>1e-12).sum()),
                p_two_sided=e.signflip(x),ci_low=float(np.quantile(bs,.025)),ci_high=float(np.quantile(bs,.975)))

def pairs_real(E):
    out=[]
    for loc,g in E.groupby('locus',sort=False):
        rr=g.to_dict('records')
        for i in range(1,len(rr)):
            a,b=rr[i-1],rr[i]
            normal=b['entry_eligible'] and a['raw_item_index']+1==b['raw_item_index']
            if normal:
                out.append(dict(page=b['page'],bif=b['bif'],phase=b['row_phase'],board=b['board'],T=int(a['glyphs'][-1]),H1=int(b['glyphs'][0])))
    return pd.DataFrame(out)

def pairs_gen(d):
    rr=e.generated_doc(d)['raw_events'];out=[]
    for a,b in zip(rr[:-1],rr[1:]):
        ga,gb=a['glyph_names'],b['glyph_names']
        if ga and gb and a['locus']==b['locus'] and a['segment_id']==b['segment_id']:
            out.append(dict(phase=b['row_phase'],board=b['board'],T=e.m.G2I[ga[-1]],H1=e.m.G2I[gb[0]]))
    return pd.DataFrame(out)

def ref_joint(ex,kn):
    ec=defaultdict(lambda:np.zeros((22,22)));kc=defaultdict(lambda:np.zeros((22,22)))
    for dat,ct in [(ex,ec),(kn,kc)]:
        for r in dat.itertuples():
            for k in ['ALL',r.board,(r.phase,r.board)]:ct[k][r.T,r.H1]+=1
    gl=(ec['ALL']+.5);gl/=gl.sum();out={}
    for bd in ('HEAD','W2','BODY','LF'):
        z=(ec[bd]+32*gl)/(ec[bd].sum()+32)
        for ph in ('FIRST','MIDDLE','FINAL'):
            z2=(ec[ph,bd]+32*z)/(ec[ph,bd].sum()+32)
            out[ph,bd]=(kc[ph,bd]+32*z2)/(kc[ph,bd].sum()+32)
    return out

def pair_scores(df,Q):
    sums=[]
    for r in df.itertuples():
        q=Q[r.phase,r.board];jo=q[r.T,r.H1];tm=q.sum(1)[r.T];hm=q.sum(0)[r.H1]
        sums.append([math.log2(tm),math.log2(hm),math.log2(jo/(tm*hm)),math.log2(jo),math.log2(jo/tm)])
    return dict(zip(['T_marginal','H1_marginal','association','joint','conditional'],np.mean(sums,axis=0)))

def pair_values(df,component):
    return list(zip(df['T'],df.H1)) if component=='TH1' else list(df[component])

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    seal=json.loads((ROOT/'outputs/GENERATION_SEALED_ALL.json').read_text())
    assert seal['pages']==300 and seal['packing_pass']
    for fn,h in seal['hashes'].items():assert e.file_hash(ROOT/fn)==h,fn
    plan=seal['plan'];C=e.context();docs={p:e.real_doc(C,p) for p in C.seqs};R=pairs_real(C.events)
    scores=[];metrics=[];dists=[];boundary=[];decomp=[];training=[];oldchecks=[];counts=[]
    old=pd.read_csv(JUDGE/'outputs/confirmation/judged/scores_by_leaf_run.csv')
    t0=time.monotonic()
    for fi,test in enumerate(e.folds(C.bifs)):
        train=[b for b in C.bifs if b not in test];tp=[p for b in train for p in C.pages[b]]
        for b in test:
            p=C.pages[b][-1];kp=[q for q in C.pages[b] if q!=p]
            judge=e.Judges([docs[q] for q in tp],[docs[q] for q in kp]);rs=judge.score(docs[p])
            Q=ref_joint(R[R.bif.isin(train)],R[R.page.isin(kp)]);rp=R[R.page.eq(p)];kr=R[R.page.isin(kp)]
            rsc=pair_scores(rp,Q)
            for arm in ('BASE','E12_VH'):
                op=JUDGE/'outputs/confirmation/generated/run91031'/arm/b.replace(':','_')/'tokens.csv.gz'
                oldscore=judge.score(e.generated_doc(pd.read_csv(op)))
                oo=old[old.run.eq(91031)&old.bif.eq(b)&old.arm.eq(arm)].set_index('judge')
                err=max(abs(oldscore[j]-oo.loc[j,'gen_score']) for j in oldscore)
                assert err<1e-12,(b,arm,err)
                oldchecks.append(dict(bif=b,arm=arm,run=91031,max_abs_error=err,scores=len(oldscore)))
            for run in plan['runs']:
                pairsets={'REAL':rp}
                for arm in plan['arms']:
                    loc=ROOT/'outputs/generated'/f'run{run}'/arm/b.replace(':','_')
                    d=pd.read_csv(loc/'tokens.csv.gz');gd=e.generated_doc(d);gs=judge.score(gd)
                    for k in rs:
                        m=rs[k]-gs[k]
                        scores.append(dict(fold=fi,bif=b,page=p,run=run,arm=arm,judge=k,real_score=rs[k],gen_score=gs[k],margin=m,abs_margin=abs(m)))
                    metrics.append(e.metric_row(C,p,d,arm,run,b,fi))
                    for k in ('bigram','trigram'):
                        gt=e.J.tokens(gd,k);rt=e.J.tokens(docs[p],k)
                        kt=[x for q in kp for x in e.J.tokens(docs[q],k)];at=[x for q in tp for x in e.J.tokens(docs[q],k)]
                        dists.append(dict(bif=b,page=p,run=run,arm=arm,ngram=k,target_jsd=e.jsd(gt,rt),known3_jsd=e.jsd(gt,kt),awide_jsd=e.jsd(gt,at)))
                    gp=pairs_gen(d);pairsets[arm]=gp;gsc=pair_scores(gp,Q)
                    counts.append(dict(bif=b,page=p,run=run,arm=arm,real_boundaries=len(rp),generated_boundaries=len(gp)))
                    for co in rsc:
                        m=rsc[co]-gsc[co];decomp.append(dict(bif=b,page=p,run=run,arm=arm,component=co,real=rsc[co],generated=gsc[co],margin=m,abs_margin=abs(m)))
                    for co in ('T','H1','TH1'):
                        boundary.append(dict(bif=b,page=p,run=run,arm=arm,component=co,target_JSD=e.jsd(pair_values(rp,co),pair_values(gp,co)),known3_JSD=e.jsd(pair_values(kr,co),pair_values(gp,co)),method='NATURAL_N'))
                # Same-boundary-number sensitivity; fixed seed, all arms retained.
                n=min(len(x) for x in pairsets.values());sampled=defaultdict(list)
                for rep in range(32):
                    g=np.random.default_rng(e.m.keyed_rng(9115101,b,run,rep).integers(1,2**31))
                    vals={a:pair_values(x.iloc[g.choice(len(x),n,replace=False)],'TH1') for a,x in pairsets.items()}
                    for arm in plan['arms']:sampled[arm].append(e.jsd(vals['REAL'],vals[arm]))
                for arm,vs in sampled.items():boundary.append(dict(bif=b,page=p,run=run,arm=arm,component='TH1',target_JSD=float(np.mean(vs)),known3_JSD=np.nan,method='MATCHED_N_32',boundaries=n))
            training.append(dict(fold=fi,bif=b,target=p,known3=kp,external_bifs=train,external_pages=tp,all_arms_same_judge=True,target_used_to_fit=False))
            print('JUDGED',fi,b,f'{time.monotonic()-t0:.1f}s',flush=True)
    S=pd.DataFrame(scores);M=pd.DataFrame(metrics);e.PRIMARY[:]=PRIMARY
    su,pa=e.summarize(S,M,OUT,10000)
    # Primary comparison is the requested ablation vs E12_VH; BTI2 also retained.
    paired=[]
    for ref in ('E12_VH','BASE'):
        z=S[S.arm.eq(CANDIDATE)].merge(S[S.arm.eq(ref)],on=['bif','run','judge'],suffixes=('_new','_ref'),validate='one_to_one')
        for j,g in z.groupby('judge'):
            v=(g.abs_margin_ref-g.abs_margin_new).groupby(g.bif).mean()
            paired.append(dict(reference=ref,arm=CANDIDATE,judge=j,reference_abs=g.abs_margin_ref.mean(),new_abs=g.abs_margin_new.mean(),change_pct=100*(g.abs_margin_new.mean()/g.abs_margin_ref.mean()-1),**paired_stats(v)))
    P=pd.DataFrame(paired)
    for ref in P.reference.unique():
        mask=P.reference.eq(ref);P.loc[mask,'holm_all20']=e.holm(P.loc[mask,'p_two_sided'])
        for group,kinds in [('primary',PRIMARY),('head',e.HEAD),('regression',e.REGRESSION),('main6',e.MAIN6)]:
            mask=P.reference.eq(ref)&P.judge.isin(kinds);P.loc[mask,'holm_'+group]=e.holm(P.loc[mask,'p_two_sided'])
    mk=P.judge.isin(PRIMARY);P.loc[mk,'holm_primary_both_references4']=e.holm(P.loc[mk,'p_two_sided'])
    P.to_csv(OUT/'candidate_paired_both_references.csv',index=False)
    # Seed effects, taken before averaging across repeated realizations.
    seed=[]
    for ref in ('BASE','E12_VH'):
        for j in S.judge.unique():
            for run in plan['runs']:
                base=S[S.arm.eq(ref)&S.judge.eq(j)&S.run.eq(run)].abs_margin.mean()
                new=S[S.arm.eq(CANDIDATE)&S.judge.eq(j)&S.run.eq(run)].abs_margin.mean()
                seed.append(dict(reference=ref,judge=j,run=run,reference_abs=base,new_abs=new,change_pct=100*(new/base-1)))
    pd.DataFrame(seed).to_csv(OUT/'per_seed_effects.csv',index=False)
    D=pd.DataFrame(dists);D.to_csv(OUT/'ngram_distances.csv',index=False)
    D.groupby(['arm','ngram'])[['target_jsd','known3_jsd','awide_jsd']].mean().reset_index().to_csv(OUT/'ngram_distance_summary.csv',index=False)
    B=pd.DataFrame(boundary);B.to_csv(OUT/'boundary_JSD_by_page.csv',index=False)
    B.groupby(['method','arm','component'])[['target_JSD','known3_JSD']].mean().reset_index().to_csv(OUT/'boundary_JSD_summary.csv',index=False)
    tests=[]
    for ref in ('BASE','E12_VH'):
        for (method,co),g in B.groupby(['method','component']):
            z=g[g.arm.eq(CANDIDATE)].merge(g[g.arm.eq(ref)],on=['bif','run'],suffixes=('_new','_ref'),validate='one_to_one')
            for meas in ['target_JSD','known3_JSD']:
                if z[meas+'_ref'].isna().all():continue
                v=(z[meas+'_ref']-z[meas+'_new']).groupby(z.bif).mean()
                tests.append(dict(reference=ref,method=method,component=co,metric=meas,base=z[meas+'_ref'].mean(),new=z[meas+'_new'].mean(),change_pct=100*(z[meas+'_new'].mean()/z[meas+'_ref'].mean()-1),**paired_stats(v)))
    T=pd.DataFrame(tests)
    for ref in T.reference.unique():
        mk=T.reference.eq(ref)&T.method.eq('NATURAL_N');T.loc[mk,'holm_six']=e.holm(T.loc[mk,'p_two_sided'])
    T.to_csv(OUT/'boundary_JSD_tests.csv',index=False)
    DC=pd.DataFrame(decomp);DC.to_csv(OUT/'boundary_log_decomposition_by_page.csv',index=False)
    DC.groupby(['arm','component'])[['margin','abs_margin']].mean().reset_index().to_csv(OUT/'boundary_log_decomposition_summary.csv',index=False)
    pd.DataFrame(counts).to_csv(OUT/'boundary_event_counts.csv',index=False)
    mp=[]
    for ref in ('BASE','E12_VH'):
        z=M[M.arm.eq(CANDIDATE)].merge(M[M.arm.eq(ref)],on=['bif','run'],suffixes=('_new','_ref'),validate='one_to_one')
        for k in [x[3:] for x in M if x.startswith('ae_')]:
            v=(z['ae_'+k+'_ref']-z['ae_'+k+'_new']).groupby(z.bif).mean()
            mp.append(dict(reference=ref,metric=k,reference_mae=z['ae_'+k+'_ref'].mean(),new_mae=z['ae_'+k+'_new'].mean(),**paired_stats(v)))
    pd.DataFrame(mp).to_csv(OUT/'metrics_paired_both_references.csv',index=False)
    e.write(OUT/'TRAINING_AUDIT.json',training);e.write(OUT/'LEGACY_SCORE_REPRODUCTION.json',oldchecks)
    final=su.pivot(index='judge',columns='arm',values='mean_abs_margin').reset_index()
    for ref in ('BASE','E12_VH'):
        zz=P[P.reference.eq(ref)][['judge','change_pct','p_two_sided','holm_primary']].rename(columns={c:f'{c}_vs_{ref}' for c in ['change_pct','p_two_sided','holm_primary']})
        final=final.merge(zz,on='judge',validate='one_to_one')
    final.to_csv(ROOT/'FINAL_COMPARISON.csv',index=False)
    e.write(OUT/'JUDGE_COMPLETE.json',dict(pages=300,score_rows=len(S),numerical_judges=20,independent_llm_calls=0,runs=plan['runs'],new_generation=True,
              same_frozen_evaluation_source=True,primary=PRIMARY,main_reference='E12_VH',candidate_selection=False,
              old_scores_checked=sum(x['scores'] for x in oldchecks),old_score_maxerror=max(x['max_abs_error'] for x in oldchecks),seconds=time.monotonic()-t0))
    print(final.to_string(index=False));print('COMPLETE',flush=True)
if __name__=='__main__':main()
