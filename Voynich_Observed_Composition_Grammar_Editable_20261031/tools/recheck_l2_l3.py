#!/usr/bin/env python3
"""Pure-standard-library exploratory L2/L3 4-glyph-route permutation test.
Preserves each paragraph's first/final lines and all interior line lengths, and shuffles its interior tokens.
Not a proof of semantic family activation.
"""
import csv
import gzip
import json
import random
from collections import OrderedDict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
COMPOSITES=('cfh','ckh','cph','cth','ch','sh')
def glyphs(w):
    a=[];i=0
    while i<len(w):
        c=next((g for g in COMPOSITES if w.startswith(g,i)),w[i]);a.append(c);i+=len(c)
    return a

def main():
    with gzip.open(ROOT/'data/source_pureA85_observed_tokens.csv.gz','rt',encoding='utf-8',newline='') as fd:
        rows=list(csv.DictReader(fd))
    paras=OrderedDict()
    for row in rows:
        pars=paras.setdefault((row['page'],row['para']),OrderedDict())
        pars.setdefault(row['locus'],[]).append(row['surface'])
    valid=[list(p.values()) for p in paras.values() if len(p)>=4]
    cache={w:{tuple(glyphs(w)[i:i+4]) for i in range(len(glyphs(w))-3)} for w in set(r['surface'] for r in rows)}
    def paths(words):
        return set().union(*(cache[w] for w in words))
    obs=sum(len(paths(lines[1]) & paths(lines[2])) for lines in valid)
    rng=random.Random(101)
    null=[]
    for _ in range(5000):
        count=0
        for lines in valid:
            interior=lines[1:-1]
            lens=[len(line) for line in interior]
            words=[w for line in interior for w in line]
            rng.shuffle(words)
            count+=len(paths(words[:lens[0]]) & paths(words[lens[0]:lens[0]+lens[1]]))
        null.append(count)
    result={'sample_paragraphs_4plus':len(valid),'observed_shared_route_sum':obs,'null_repetitions':5000,
            'null_mean':round(sum(null)/len(null),3),'null_ge_observed':sum(x>=obs for x in null),
            'one_sided_plus_one_p':round((1+sum(x>=obs for x in null))/(len(null)+1),5),
            'seed':101,'note':'4-glyph word-internal path sets; first and final lines fixed; shuffle interior words only'}
    (ROOT/'data/l2_l3_exploratory_test.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
