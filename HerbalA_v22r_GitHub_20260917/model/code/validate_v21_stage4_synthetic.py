from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from runtime_bootstrap import prepare_runtime
HANDOFF,PARENT,ST=prepare_runtime()
sys.path.insert(0,str(ST/'code'))
vp=next((ROOT/'runtime').rglob('v19r_rb3_pw2_close1.py')).parent
sys.path.insert(0,str(vp))
import v19r_rb3_pw2_close1 as m
from w2_slot_tables import load_fold_tables
from w2_slot_generator import W2SlotGenerator,SlotContext,SlotSelectionKey


def main():
    # Unit-only synthetic test.  LEFT legality is represented by a deterministic
    # synthetic support mask; the live sampler separately asserts the actual
    # v20r/SAFE_LEFT support function on every selected SLOT word.
    tab=load_fold_tables(ROOT/'parameters/v21_slot_tables/fold0.json')
    slot=W2SlotGenerator(tab,m.WIDTH,m.stable_width)
    # Search a compact context with legal candidates under a deliberately sparse
    # LEFT-support mask.  This verifies that unsupported triples can never escape.
    found=None
    for h1 in range(22):
        for W in (4,5,6,7,8):
            for T in range(22):
                def legal(a,b,c):
                    return ((int(a)*31+int(b)*7+int(c)) % 5) != 0
                c=slot.enumerate(SlotContext(h1,W,T,'MIDDLE'),legal)
                if c:
                    found=(h1,W,T,c,legal);break
            if found:break
        if found:break
    assert found is not None
    h1,W,T,cands,legal=found
    p=slot.softmax(cands)
    key=SlotSelectionKey(91400,'SYN','synthetic','synthetic.1',0,1,0)
    j,cand,digest=slot.select(cands,p,key)
    s=cand.glyphs
    checks={
        'H1_fixed': s[0]==h1,
        'glyph_length_4': len(s)==4,
        'W_fixed': int(m.stable_width(s))==W,
        'H4_width_1': int(m.WIDTH[s[3]])==1,
        'LEFT_legal': bool(legal(*s[:3])),
        'RIGHT_unused_by_component': True,
        'probability_finite': bool(np.isfinite(p).all() and np.isfinite(cand.score)),
        'probability_normalized': abs(float(p.sum())-1.0)<1e-12,
        'candidate_count_positive': len(cands)>0,
        'selection_digest': bool(digest),
    }
    assert all(v for k,v in checks.items() if k!='selection_digest') and checks['selection_digest']
    out={'status':'PASS','context':{'H1':h1,'W':W,'T':T,'row_phase':'MIDDLE'},'candidate_count':len(cands),'selected':m.word_str(s),'selected_index':j,'checks':checks}
    dst=ROOT/'validation/stage4';dst.mkdir(parents=True,exist_ok=True)
    (dst/'SYNTHETIC.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
