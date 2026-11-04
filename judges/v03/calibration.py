"""Genuine-only fitting; grouped outer holdout and disjoint null calibration."""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import math
from pathlib import Path

from ..features import Feature
from ..schema import GLYPHS
from ..scoring import jsd, reference_mix
from .protocol import DEFAULT, PROTOCOL_HASH, digest, extractor_hash, read_json, write_json, file_hash
from .schema import fields, validate_doc
from .views import extract, sample_n, conditional_counts, conditional_spec


def ctx_key(ctx):return digestable(ctx)


def digestable(value):
    import json
    return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def joint(name,features):
    return reference_mix([conditional_counts(name,f) for f in features])


def fit_prior(features, name, lam=32, rho=0):
    exemplar=next((f[name] for f in features if name in f),None)
    spec=conditional_spec(name,exemplar) if exemplar else None
    if spec is None:return None
    counts=Counter()
    for fs in features:
        if name in fs:counts.update(conditional_counts(name,fs[name]))
    rows=defaultdict(Counter);pool=Counter()
    for (c,v),n in counts.items():rows[ctx_key(c)][v]+=n;pool[v]+=n
    return {'lambda':lam,'rho':rho,'context_cardinality':spec['contexts'],
        'outcomes':spec['outcomes'] or list(GLYPHS),'rows':dict(rows),'pool':dict(pool),'total':sum(pool.values())}


def probabilities(model,reference_joint,ctx):
    outcomes=model['outcomes'];alpha=DEFAULT['fitting']['jeffreys_pseudocount'];total=model['total']
    row=model['rows'].get(ctx_key(ctx),{});nc=sum(row.values());lam=model['lambda'];rho=model['rho'] if reference_joint else 0
    prior_mass=(nc+alpha)/(total+model['context_cardinality']*alpha)
    rr={v:n for (c,v),n in reference_joint.items() if c==ctx};rm=sum(rr.values())
    denom=(1-rho)*prior_mass+rho*rm
    return {v:((1-rho)*prior_mass*(row.get(v,0)+lam*(model['pool'].get(v,0)+alpha)/(total+len(outcomes)*alpha))/(nc+lam)+rho*rr.get(v,0))/denom for v in outcomes}


def loss(model,reference_joint,counts):
    if not counts:return None
    by=defaultdict(Counter)
    for (c,v),n in counts.items():by[c][v]+=n
    value=0.0
    for c,rr in by.items():
        p=probabilities(model,reference_joint,c)
        value+=math.fsum(-n*math.log2(p[v]) for v,n in rr.items())
    return value/sum(counts.values())


def descriptor(name,feature,reference_features,conditionals):
    if not feature.counts:return None,'NO_EVENTS'
    if conditional_spec(name,feature) is not None:
        model=conditionals.get(name)
        if model is None:return None,'NO_CALIBRATION'
        value=loss(model,joint(name,reference_features),conditional_counts(name,feature))
        return value,'OK'
    q=reference_mix([x.counts for x in reference_features])
    return (jsd(q,feature.counts),'OK') if q else (None,'NO_REFERENCE_EVENTS')


def size_bin(n):
    for b in DEFAULT['fitting']['null_size_bins']:
        if n>=b['min'] and (b['max'] is None or n<=b['max']):return b['name']
    raise ValueError('size bin requires positive raw observation count')


def typicality(rows,distance,n):
    settings=DEFAULT['fitting']
    for level,chosen in [('SIZE_BIN',[r for r in rows if size_bin(r['n'])==size_bin(n)]),('ALL_SIZES',rows)]:
        grouped=defaultdict(list)
        for r in chosen:grouped[r['cluster_id']].append(r)
        if len(grouped)<settings['min_null_bifolia'] or len(chosen)<settings['min_null_target_pages']:continue
        eps=DEFAULT['tie_epsilon'];fractions=[]
        for _,rr in sorted(grouped.items()):
            fractions.append(math.fsum(1 if r['distance']<distance-eps else .5 if abs(r['distance']-distance)<=eps else 0 for r in rr)/len(rr))
        mid=math.fsum(fractions)/len(fractions)
        return max(0.0,1-2*abs(mid-.5)),{'level':level,'bifolia':len(grouped),'target_pages':len(chosen),'event_count':sum(r['n'] for r in chosen)}
    return None,None


def calibrated_scores(model,refs,sides):
    names=sorted(set().union(*[set(x) for x in refs+list(sides.values())]));out={}
    for name in names:
        exemplar=next(x[name] for x in refs+list(sides.values()) if name in x)
        empty=lambda:Feature(conditional=exemplar.conditional)
        rf=[r.get(name,empty()) for r in refs]
        row={'reference_events':[sample_n(f) for f in rf],'reference_nonempty_pages':sum(bool(f.counts) for f in rf),
            'A':None,'B':None,'reason':'OK','calibration':{}}
        for side in ['A','B']:
            f=sides[side].get(name,empty());n=sample_n(f);row[side+'_events']=n
            d,reason=descriptor(name,f,rf,model['conditionals'])
            row[side+'_distance']=d
            if conditional_spec(name,f) is not None and f.counts:
                observed={c for r in rf for c,v in conditional_counts(name,r)}
                cc=conditional_counts(name,f)
                prior_only=sum(v for (c,o),v in cc.items() if c not in observed)
                row[side+'_prior_only_events']=prior_only
                row[side+'_reference_observed_fraction']=1-prior_only/sum(cc.values())
            if d is None:row['reason']=reason;row['calibration'][side]=None
            else:
                t,coverage=typicality(model['nulls'].get(name,[]),d,n)
                row[side]=t;row['calibration'][side]=coverage
                if t is None:row['reason']='INSUFFICIENT_CALIBRATION'
        out[name]=row
    return out


def validate_corpus(corpus):
    fields(corpus,'schema_version protocol_hash input_profile source_hashes bifolia')
    if corpus['schema_version']!=2 or corpus['protocol_hash']!=PROTOCOL_HASH or corpus['input_profile']!='structure-endpoints-v2':raise ValueError('unsupported corpus profile')
    if len(corpus['bifolia'])!=20:raise ValueError('protocol requires 20 bifolia')
    ids=set();folds=Counter()
    for b in corpus['bifolia']:
        fields(b,'cluster_id fold pages')
        if not isinstance(b['cluster_id'],str) or not b['cluster_id'] or b['cluster_id'] in ids:raise ValueError('invalid/duplicate corpus cluster')
        if type(b['fold']) is not int or b['fold'] not in range(5):raise ValueError('invalid outer fold')
        if len(b['pages'])!=4 or {p['slot'] for p in b['pages']}!=set(range(4)):raise ValueError('four distinct source slots required')
        for p in b['pages']:validate_doc(p,reference=True)
        ids.add(b['cluster_id']);folds[b['fold']]+=1
    if any(folds[i]!=4 for i in range(5)):raise ValueError('outer folds must contain four bifolia')


def split_plan(corpus):
    validate_corpus(corpus);result=[]
    for f in range(5):
        test=sorted(b['cluster_id'] for b in corpus['bifolia'] if b['fold']==f)
        external=sorted((b['cluster_id'] for b in corpus['bifolia'] if b['fold']!=f),key=lambda x:hashlib.sha256(('v03-split-v1|'+x).encode()).hexdigest())
        result.append({'outer_fold':f,'test_cluster_ids':test,'prior_train_cluster_ids':external[:8],'null_calibration_cluster_ids':external[8:]})
    return result


def validate_binding(model,cluster_id):
    if model['protocol_hash']!=PROTOCOL_HASH or model['extractor_hash']!=extractor_hash():raise ValueError('model protocol/extractor mismatch')
    T=set(model['prior_train_cluster_ids']);Q=set(model['null_calibration_cluster_ids']);O=set(model['test_cluster_ids'])
    if len(model['prior_train_cluster_ids'])!=8 or len(model['null_calibration_cluster_ids'])!=8 or len(model['test_cluster_ids'])!=4 or len(T)!=8 or len(Q)!=8 or len(O)!=4 or T&Q or T&O or Q&O or cluster_id not in O:
        raise ValueError('model is not bound to a disjoint outer holdout')
    for rr in model['nulls'].values():
        for r in rr:fields(r,'cluster_id target_slot distance n')
        if len({(r['cluster_id'],r['target_slot']) for r in rr})!=len(rr):raise ValueError('duplicate null target pages')
        if any(r['cluster_id'] not in Q or type(r['target_slot']) is not int or r['target_slot'] not in range(4) or type(r['n']) is not int or r['n']<1 or type(r['distance']) not in [int,float] or not math.isfinite(r['distance']) for r in rr):
            raise ValueError('invalid or non-calibration null target')


def fit(corpus,output,plan=None):
    validate_corpus(corpus);splits=split_plan(corpus)
    if plan is not None:
        provided=plan['splits']
        if len(provided)!=5 or any(any(p[k]!=s[k] for k in s) for p,s in zip(provided,splits)):
            raise ValueError('fold plan disagrees with fixed grouped split')
    by={b['cluster_id']:b for b in corpus['bifolia']};cache={}
    def features(doc,refs):
        k=(digest(doc),tuple(sorted(digest(r) for r in refs)))
        if k not in cache:cache[k]=extract(doc,refs)
        return cache[k]
    own={(b['cluster_id'],p['slot']):features(p,[]) for b in corpus['bifolia'] for p in b['pages']}
    code=extractor_hash();models=[]
    for split in splits:
        T=split['prior_train_cluster_ids'];Q=split['null_calibration_cluster_ids']
        all_fs=[own[b,p['slot']] for b in T for p in by[b]['pages']]
        names=sorted({n for fs in all_fs for n,f in fs.items() if conditional_spec(n,f) is not None})
        candidates={(lam,rho):defaultdict(list) for lam in DEFAULT['fitting']['hyperparameters']['lambda'] for rho in DEFAULT['fitting']['hyperparameters']['rho']}
        for held in T:
            train_fs=[own[b,p['slot']] for b in T if b!=held for p in by[b]['pages']]
            priors={n:fit_prior(train_fs,n) for n in names}
            per_candidate={pair:defaultdict(list) for pair in candidates}
            pages=by[held]['pages']
            for p in pages:
                refs=[own[held,r['slot']] for r in pages if r['slot']!=p['slot']]
                for name in names:
                    feature=own[held,p['slot']].get(name)
                    if not feature or not feature.counts or priors[name] is None:continue
                    rr=[r.get(name,Feature(conditional=feature.conditional)) for r in refs]
                    mix=joint(name,rr);counts=conditional_counts(name,feature)
                    for pair in candidates:
                        prior=priors[name] | {'lambda':pair[0],'rho':pair[1]}
                        per_candidate[pair][name].append(loss(prior,mix,counts))
            for pair,fs in per_candidate.items():
                for name,values in fs.items():candidates[pair][name].append(math.fsum(values)/len(values))
        conditionals={};selection={}
        for name in names:
            available=[(math.fsum(v[name])/len(v[name]),-pair[0],pair[1],pair) for pair,v in candidates.items() if len(v.get(name,[]))>=DEFAULT['fitting']['minimum_inner_validation_bifolia']]
            if not available:
                selection[name]={'status':'INSUFFICIENT_TRAINING'};continue
            best=min(available);lam,rho=best[-1]
            conditionals[name]=fit_prior(all_fs,name,lam,rho)
            selection[name]={'status':'FIT','lambda':lam,'rho':rho,'inner_macro_log_loss':best[0],'validation_bifolia':len(candidates[lam,rho][name])}
        nulls=defaultdict(list)
        for b in Q:
            pages=by[b]['pages']
            for p in pages:
                known=[r for r in pages if r['slot']!=p['slot']]
                refs=[features(r,[x for x in known if x['slot']!=r['slot']]) for r in known]
                target=features(p,known)
                for name,f in target.items():
                    rr=[r.get(name,Feature(conditional=f.conditional)) for r in refs]
                    d,reason=descriptor(name,f,rr,conditionals)
                    if d is not None:nulls[name].append({'cluster_id':b,'target_slot':p['slot'],'distance':d,'n':sample_n(f)})
        model={**split,'protocol_hash':PROTOCOL_HASH,'extractor_hash':code,'corpus_hash':digest(corpus),
            'conditionals':conditionals,'nulls':dict(nulls),'fit_diagnostics':selection}
        validate_binding(model,split['test_cluster_ids'][0]);models.append(model)
        print('FIT',split['outer_fold'],'conditional_models',len(conditionals),'null_channels',len(nulls),flush=True)
    payload={'protocol_hash':PROTOCOL_HASH,'extractor_hash':code,'corpus_hash':digest(corpus),'models':models}
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    write_json(output/'models.json',payload)
    write_json(output/'manifest.json',{'models_sha256':file_hash(output/'models.json'),'model_set_hash':digest(payload),
        'protocol_hash':PROTOCOL_HASH,'extractor_hash':code,'status':'fitted_not_capability_verified','data_status':'development_reused_not_fresh_confirmation'})
    return payload


def load_models(path):
    path=Path(path);payload=read_json(path/'models.json');m=read_json(path/'manifest.json')
    if file_hash(path/'models.json')!=m['models_sha256'] or digest(payload)!=m['model_set_hash'] or payload['extractor_hash']!=extractor_hash() or payload['protocol_hash']!=PROTOCOL_HASH:
        raise ValueError('fitted model artifact was changed or has an incompatible extractor')
    binding={}
    if len(payload['models'])!=5 or {m['outer_fold'] for m in payload['models']}!=set(range(5)):
        raise ValueError('five distinct outer models required')
    universe=set().union(*(set(m['test_cluster_ids']) for m in payload['models']))
    if len(universe)!=20:raise ValueError('outer model coverage must be exactly 20 clusters')
    for model in payload['models']:
        if set(model['prior_train_cluster_ids'])|set(model['null_calibration_cluster_ids']) != universe-set(model['test_cluster_ids']):
            raise ValueError('model train/calibration universe differs from outer split')
        for b in model['test_cluster_ids']:
            validate_binding(model,b)
            if b in binding:raise ValueError('duplicate outer model binding')
            binding[b]=model
    return payload,binding
