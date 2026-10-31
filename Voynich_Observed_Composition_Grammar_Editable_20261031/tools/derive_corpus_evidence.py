#!/usr/bin/env python3
"""Rebuild observed Voynich-A tables directly from an annotated corpus.
Requires only Python 3 standard library. Does NOT use the VSL generator or model.
"""
import collections
import csv
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
INFILE = HERE / 'data' / 'source_pureA85_observed_tokens.csv.gz'
OUT = HERE / 'data'
COMPOSITES = ('cfh', 'ckh', 'cph', 'cth', 'ch', 'sh')
ALPHABET = ('q','cfh','ch','cph','cth','p','sh','ckh','f','k','o','t','a','d','e','s','i','l','y','r','m','n','g')
ROLE_ORDER=('PHW','F1_BODY','F1_LF','HEAD','W2','BODY','LF','PF_HEAD','PF_BODY','PF_LF')

def glyphs(form):
    result=[]; i=0
    while i<len(form):
        s=next((p for p in COMPOSITES if form.startswith(p,i)),form[i]);result.append(s);i+=len(s)
    if not result or not all(x in ALPHABET for x in result): raise ValueError(f'Not in observed alphabet: {form!r}, {result}')
    return tuple(result)

def read_csv():
    with gzip.open(INFILE,'rt',encoding='utf-8',newline='') as fd: return list(csv.DictReader(fd))

def write_csv(name,rows,headers):
    with open(OUT/name,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=headers,extrasaction='ignore');w.writeheader();w.writerows(rows)

def classify_line(words,idx,nlines):
    # Core 3+-line classroom structure. Exceptional short lines are catalogued but not excluded from corpus lexicon.
    n=len(words)
    if idx==0:
        return ['PHW'] if n==1 else ['PHW']+['F1_BODY']*(n-2)+['F1_LF']
    if idx==nlines-1:
        return ['PF_LF'] if n==1 else ['PF_HEAD']+['PF_BODY']*(n-2)+['PF_LF']
    return ['HEAD'] if n==1 else (['HEAD','LF'] if n==2 else ['HEAD','W2']+['BODY']*(n-3)+['LF'])

def build():
    data=read_csv()
    if len(data)!=6836:raise AssertionError('Unexpected token count; version mismatch')
    forms=collections.Counter(row['surface'] for row in data)
    pages=collections.defaultdict(set);bifs=collections.defaultdict(set);loci=collections.defaultdict(list)
    paras=collections.defaultdict(lambda:collections.OrderedDict())
    for row in data:
        w=row['surface'];pages[w].add(row['page']);bifs[w].add(row['bif']);loci[w].append(row['locus'])
        paras[(row['page'],row['para'])].setdefault(row['locus'],[]).append(w)
    roles=collections.defaultdict(collections.Counter)
    lex_role=collections.defaultdict(collections.Counter)
    excluded_paras=[];lines_by_para=collections.Counter();line_words=[]
    for (page,p),lined in paras.items():
        lines=list(lined.values());lines_by_para[len(lines)]+=1
        if len(lines)<3:
            excluded_paras.append({'page':page,'paragraph':p,'lines':len(lines),'tokens':sum(map(len,lines))});continue
        for idx,words in enumerate(lines):
            line_words.append(len(words))
            rr=classify_line(words,idx,len(lines));assert len(rr)==len(words)
            for r,w in zip(rr,words):
                roles[r][w]+=1;lex_role[w][r]+=1
    assert len(forms)==1971
    bigram=collections.Counter();trigram=collections.Counter();start=collections.Counter();end=collections.Counter()
    for w,c in forms.items():
        g=glyphs(w);start[g[0]]+=c;end[g[-1]]+=c
        for bg in zip(g,g[1:]):bigram[bg]+=c
        for tg in zip(g,g[1:],g[2:]):trigram[tg]+=c
    assert len(bigram)==229 and len(trigram)==881
    routeinfo=collections.defaultdict(lambda:{'tokens':0,'types':set(),'pages':set(),'carriers':collections.Counter()})
    for row in data:
        w=row['surface'];g=glyphs(w)
        for n in (4,5,6):
            for route in set(g[i:i+n] for i in range(len(g)-n+1)):
                v=routeinfo[route];v['tokens']+=1;v['types'].add(w);v['pages'].add(row['page']);v['carriers'][w]+=1
    routeinfo={r:v for r,v in routeinfo.items() if v['tokens']>=3 and len(v['types'])>=2 and len(v['pages'])>=2}
    assert len(routeinfo)==715
    by_form=collections.defaultdict(list)
    for r,v in routeinfo.items():
        for w in v['types']:by_form[w].append(r)
    lexical=[]
    for rank,(w,c) in enumerate(sorted(forms.items(),key=lambda kv:(-kv[1],kv[0])),1):
        gs=glyphs(w);rr=lex_role[w]
        fav=max(by_form[w],key=lambda x:(routeinfo[x]['tokens'],len(x),x)) if by_form[w] else ()
        lexical.append({'rank':rank,'form':w,'frequency':c,'glyphs':'.'.join(gs),'glyph_length':len(gs),'pages':len(pages[w]),'bifolia':len(bifs[w]),'sample_locus':loci[w][0],
         'roles':';'.join([r for r in ROLE_ORDER if rr[r]>0]),'representative_4to6_route':'.'.join(fav),**{r:rr[r] for r in ROLE_ORDER}})
    headers=('rank','form','frequency','glyphs','glyph_length','pages','bifolia','sample_locus','roles','representative_4to6_route')+ROLE_ORDER
    write_csv('attested_lexicon.csv',lexical,headers)
    write_csv('word_internal_bigrams.csv',[{'left':g[0],'right':g[1],'token_count':c} for g,c in sorted(bigram.items(),key=lambda x:(-x[1],x[0]))],('left','right','token_count'))
    write_csv('word_internal_trigrams.csv',[{'a':g[0],'b':g[1],'c':g[2],'token_count':n} for g,n in sorted(trigram.items(),key=lambda x:(-x[1],x[0]))],('a','b','c','token_count'))
    route_rows=[]
    for r,v in sorted(routeinfo.items(),key=lambda x:(-x[1]['tokens'],x[0])):
        route_rows.append({'route':'.'.join(r),'glyph_length':len(r),'containing_tokens':v['tokens'],'distinct_forms':len(v['types']),'pages':len(v['pages']),
             'examples':';'.join(x for x,_ in v['carriers'].most_common(8))})
    write_csv('shared_routes.csv',route_rows,('route','glyph_length','containing_tokens','distinct_forms','pages','examples'))
    # A pair is attested only when BOTH complete words occur, with a single substitution from the stated four families.
    pairs=[];seen=set()
    for a,b in [('l','r'),('ch','sh'),('k','t'),('o','a')]:
        for w in forms:
            gs=list(glyphs(w))
            for i,g in enumerate(gs):
                if g!=a:continue
                test=gs.copy();test[i]=b;other=''.join(test)
                key=(a,b,w,other)
                if other in forms and key not in seen:
                    seen.add(key)
                    pairs.append({'rule':f'{a}>{b}','source':w,'target':other,'source_count':forms[w],'target_count':forms[other],
                           'position_glyph_index':i+1,'total_glyph_length':len(gs)})
    pairs=sorted(pairs,key=lambda row:(row['rule'],-(row['source_count']+row['target_count']),row['source']))
    write_csv('attested_single_substitutions.csv',pairs,('rule','source','target','source_count','target_count','position_glyph_index','total_glyph_length'))
    role_stats=[]
    for role in ROLE_ORDER:
        c=roles[role];n=sum(c.values());gall=sum(a for w,a in c.items() if glyphs(w)[0] in ['p','f','k','t'])
        role_stats.append({'role':role,'tokens':n,'attested_types':len(c),'mean_glyph_length':round(sum(len(glyphs(w))*x for w,x in c.items())/n,3),
                 'gallows_start_pct':round(100*gall/n,3),'typical_forms':';'.join(x for x,_ in c.most_common(16))})
    write_csv('position_registrations.csv',role_stats,('role','tokens','attested_types','mean_glyph_length','gallows_start_pct','typical_forms'))
    # Corpus metrics ONLY; the tags do not imply parts of speech, inflections, sentence meanings.
    summary={
      'corpus':'Currier A, pure herbal A, annotated EVA tokens',
      'source':'source_pureA85_observed_tokens.csv.gz',
      'words':len(data),'word_types':len(forms),'pages':len(set(row['page'] for row in data)),
      'bifolia':len(set(row['bif'] for row in data)), 'paragraphs':len(paras),
      'lines':sum(len(x) for x in paras.values()),'paragraph_line_counts':dict(sorted(lines_by_para.items())),
      'core_paragraphs_3plus':len(paras)-len(excluded_paras),
      'core_role_tokens':sum(sum(c.values()) for c in roles.values()),
      'excluded_2line_paragraphs':excluded_paras,
      'glyph_alphabet':list(ALPHABET),'glyph_count':len(ALPHABET),
      'observed_bigram_types':len(bigram),'observed_trigram_types':len(trigram),
      'shared_routes_4to6':len(routeinfo),
      'q_token_count':sum(c for w,c in forms.items() if 'q' in glyphs(w)),
      'q_word_initial_tokens':start['q'],
      'q_followed_by_o_tokens':sum(c for w,c in forms.items() if any((g1,g2)==('q','o') for g1,g2 in zip(glyphs(w),glyphs(w)[1:]))),
      'end_glyphs':dict(end),
      'start_glyphs':dict(start),
      'substitution_pair_types':dict(collections.Counter(x['rule'] for x in pairs)),
      'role_stats':role_stats,
      'evidence_policy':{'observed':'directly computed from supplied lexical corpus','recommended':'corpus-biased but not obligatory','exploratory':'no inferred meaning or parts of speech'}
    }
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:summary[k] for k in ['words','word_types','pages','bifolia','paragraphs','lines','core_role_tokens','observed_bigram_types','observed_trigram_types','shared_routes_4to6','substitution_pair_types']},indent=2))
    return summary

if __name__=='__main__': build()
