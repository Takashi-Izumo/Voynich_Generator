from __future__ import annotations
import env
from env import ROOT
import json,hashlib,math
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import binomtest
from sklearn.feature_extraction.text import TfidfVectorizer
from route_map_experiment import Context,folds
import frozen_judge_sameinfo as judge
PRIMARY=['word','ng','bigram','trigram','route56','combined']

def doc_real(C,page):
    d=C.df[C.df.page.eq(page)].sort_values('global_order');ls=[];layout=[]
    for _,g in d.groupby('locus',sort=False):
        ls.append(' '.join(g.surface.astype(str)));layout.append(dict(para=int(g.iloc[0]['para']),phase=int(g.iloc[0]['para_line_raw'])))
    return dict(lines=ls,layout=layout)
def doc_generated(d):
    ls=[];layout=[]
    for _,g in d.groupby('locus',sort=False):
        ls.append(' '.join(g.surface.astype(str)));layout.append(dict(para=int(g.iloc[0]['para']),phase=int(g.iloc[0]['para_line_raw'])))
    return dict(lines=ls,layout=layout)
class FrozenJudges:
    def __init__(self,training,known):
        self.models={};self.bt=judge.bt_model(training,known)
        for kind in judge.VEC_KINDS:
            v=TfidfVectorizer(token_pattern=r'[^ ]+',lowercase=False,sublinear_tf=True,norm='l2',min_df=1)
            v.fit([' '.join(judge.tokens(d,kind)) for d in training+known])
            P=np.asarray(v.transform([' '.join(judge.tokens(d,kind)) for d in known]).mean(axis=0)).ravel();P/=max(np.linalg.norm(P),1e-15)
            self.models[kind]=(v,P)
    def score(self,doc):
        ret={kind:float(v.transform([' '.join(judge.tokens(doc,kind))]).dot(P)[0]) for kind,(v,P) in self.models.items()}
        ret.update(judge.bt_scores(doc,self.bt));ret['combined']=.5*(ret['word']+ret['ng']);return ret

def signflip(x,alternative='two-sided'):
    x=np.asarray(x,float);x=x[np.abs(x)>1e-15]
    if not len(x):return 1.
    sums=np.array([0.])
    for v in x:sums=np.concatenate([sums+v,sums-v])
    obs=x.sum();eps=1e-12*max(1.,abs(obs))
    if alternative=='greater':return float(np.mean(sums>=obs-eps))
    return float(np.mean(np.abs(sums)>=abs(obs)-eps))
def holm(ps):
    ps=np.asarray(ps,float);order=np.argsort(ps);out=np.ones(len(ps));mx=0.
    for j,i in enumerate(order):mx=max(mx,(len(ps)-j)*ps[i]);out[i]=min(1.,mx)
    return out

def main():
    out=ROOT/'outputs/signed_final_judge';out.mkdir(exist_ok=True);inp=ROOT/'outputs/signed_final'
    # Verify every frozen generation file before evaluating anything.
    for fi in range(5):
        seal=json.loads((inp/f'GENERATION_SEALED_FOLD{fi}.json').read_text())
        for fn,sha in seal['hashes'].items():assert hashlib.sha256((inp/fn).read_bytes()).hexdigest()==sha
    D=pd.concat([pd.read_csv(inp/f'tokens_fold{fi}.csv.gz') for fi in range(5)],ignore_index=True)
    C=Context();scores=[];audit=[]
    for fi,test in enumerate(folds(C.bifs)):
        train=[b for b in C.bifs if b not in test];td=[doc_real(C,p) for b in train for p in C.pages[b]]
        for b in test:
            page=C.pages[b][-1];kp=[p for p in C.pages[b] if p!=page]
            fj=FrozenJudges(td,[doc_real(C,p) for p in kp]);real=fj.score(doc_real(C,page))
            for (case,run),g in D[D.bif.eq(b)].groupby(['case','run'],sort=False):
                ss=fj.score(doc_generated(g))
                for k in real:
                    margin=real[k]-ss[k]
                    scores.append(dict(fold=fi,bif=b,page=page,case=case,run=run,judge=k,real_score=real[k],generated_score=ss[k],margin=margin,abs_margin=abs(margin),real_win=int(margin>1e-12),tie=int(abs(margin)<=1e-12)))
            audit.append(dict(fold=fi,bif=b,target=page,known3=';'.join(kp),training_bifolia=';'.join(train),target_in_feature_fit=False))
    S=pd.DataFrame(scores);S.to_csv(out/'scores_by_leaf_run.csv',index=False);pd.DataFrame(audit).to_csv(out/'judge_training_audit.csv',index=False)
    summary=[]
    for (case,j),g in S.groupby(['case','judge']):
        lm=g.groupby('bif').margin.mean()
        summary.append(dict(case=case,judge=j,sets=len(g),leaves=len(lm),real_wins=int(g.real_win.sum()),ties=int(g.tie.sum()),
                            leaves_positive=int((lm>1e-12).sum()),mean_margin=g.margin.mean(),mean_abs_margin=g.abs_margin.mean(),
                            leaf_signflip_two_sided=signflip(lm),binomial_sets_descriptive=float(binomtest(int(g.real_win.sum()),len(g),.5).pvalue)))
    SU=pd.DataFrame(summary)
    SU['holm16_two_sided']=SU.groupby('case').leaf_signflip_two_sided.transform(lambda x:holm(x.to_numpy()))
    SU.to_csv(out/'judge_summary.csv',index=False)
    comparisons=[]
    for case in [x for x in S.case.unique() if x!='PARENT']:
        a=S[S.case.eq(case)];b=S[S.case.eq('PARENT')]
        z=a.merge(b,on=['bif','run','judge'],suffixes=('_new','_parent'))
        for j,g in z.groupby('judge'):
            delta=(g.abs_margin_parent-g.abs_margin_new).groupby(g.bif).mean()
            parent=float(g.abs_margin_parent.mean());new=float(g.abs_margin_new.mean())
            rng=np.random.default_rng(100901);v=delta.to_numpy();boots=v[rng.integers(len(v),size=(10000,len(v)))].mean(axis=1)
            comparisons.append(dict(case=case,judge=j,parent_abs=parent,new_abs=new,change_pct=100*(new/max(parent,1e-15)-1),
                                    leaves_improved=int((delta>1e-12).sum()),leaf_signflip_improvement=signflip(delta,'greater'),
                                    delta_ci_lo=float(np.quantile(boots,.025)),delta_ci_hi=float(np.quantile(boots,.975))))
    CO=pd.DataFrame(comparisons);CO['holm16_improvement']=CO.groupby('case').leaf_signflip_improvement.transform(lambda x:holm(x.to_numpy()))
    CO['holm6_improvement']=np.nan
    for case in CO.case.unique():
        mask=CO.case.eq(case)&CO.judge.isin(PRIMARY);CO.loc[mask,'holm6_improvement']=holm(CO.loc[mask,'leaf_signflip_improvement'].to_numpy())
    CO.to_csv(out/'paired_vs_parent.csv',index=False)
    M=pd.concat([pd.read_csv(inp/f'cheap_audit_fold{fi}.csv') for fi in range(5)],ignore_index=True)
    mr=[]
    for case,g in M.groupby('case'):
        for k in ['tokens','types','hapax','F2','F3_5','mean_len','mean_width']:
            mr.append(dict(case=case,metric=k,sets=len(g),real_mean=g['real_'+k].mean(),generated_mean=g[k].mean(),MAE=g['ae_'+k].mean()))
    pd.DataFrame(mr).to_csv(out/'metric_summary.csv',index=False)
    rr=[]
    for case,g in M.groupby('case'):
        for n in (5,6):rr.append(dict(case=case,n=n,target_known=int(g[f'known_target{n}'].sum()),known_hits=int(g[f'known_hit{n}'].sum()),known_recall=g[f'known_hit{n}'].sum()/max(g[f'known_target{n}'].sum(),1),
                                    target_types=int(g[f'target{n}'].sum()),target_hits=int(g[f'target_hit{n}'].sum()),target_recall=g[f'target_hit{n}'].sum()/max(g[f'target{n}'].sum(),1)))
    pd.DataFrame(rr).to_csv(out/'route_recall_summary.csv',index=False)
    audit=dict(frozen_judge_definitions=True,judge_count=16,LLM_judges_called=0,sets=int(M.shape[0]),
               primary_tests=6,leaf_cluster_unit=20,final_fresh_seeds=[8721,8722,8723],
               oracle_all_runs=[],adaptive_re_tuning_after_judge=False,
               statistical_scope='same historically used 20 target pages; fresh seed robustness, not newly held-out manuscript data')
    (out/'AUDIT.json').write_text(json.dumps(audit,indent=2));print('JUDGE_COMPLETE',len(S),flush=True)
if __name__=='__main__':main()
