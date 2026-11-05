"""Aggregate reviewer evidence from generated traces, without reading answer keys."""
from pathlib import Path
from collections import Counter, defaultdict
import json
import os
import sys

ROOT = Path(os.environ.get('PF_REVIEW_CHECKOUT', '/workspace/voynich-results/m1-v2-independent-20261105/checkout'))
OUT = Path(os.environ.get('PF_REVIEW_ROOT', '/workspace/voynich-results/pf-generation-independent-20261105'))
sys.path.insert(0, str(ROOT))
from experiments.pf_generation.audit import read_csv, read_jsonl

def tally(sequences):
    from judges.schema import glyphs
    lengths = [len(glyphs(s)) for s in sequences]
    return dict(n=len(lengths), bands=dict(Counter('1-3' if n<=3 else '4-6' if n<=6 else '7+' for n in lengths)))

def main():
    manifest = json.loads((OUT/'forward/manifest.json').read_text())
    ledger = json.loads((OUT/'plan/scope_ledger.json').read_text())
    scope = {(r['bif'], r['page'], r['locus'], r['segment_id']):r for r in ledger}
    result = {'stage_samples_are_different_denominators': True, 'all_attempts_include_discarded_branches': True,
              'scope_counts': dict(Counter(str((r['generator_pf'],r['observation_mode'],r['judge_atom'],r['judge_observed'])) for r in ledger)), 'arms': {}}
    raw = []
    returned = []
    for arm in ['BASE', 'PF_GATE', 'PF_GATE_LENGTH']:
        candidates, final_stable, final_visible, selected_pre_rare = [], [], [], []
        counts = Counter()
        gate_min_margin = None
        for entry in manifest['records']:
            if entry['arm'] != arm: continue
            p = OUT/'forward'/entry['path']
            cc = read_jsonl(p/'m1_candidates.jsonl.gz')
            gates = read_jsonl(p/'pfgen_gates.jsonl.gz')
            proposals = read_jsonl(p/'pfgen_proposals.jsonl.gz')
            tokens = read_csv(p/'tokens.csv.gz')
            requests = read_jsonl(p/'requests.jsonl.gz')
            gate_keys = Counter((r['page'],r['locus'],r['segment_id'],r['event'],r['candidate']) for r in gates)
            for c in cc:
                sr = scope[(entry['bif'], c['page'], c['locus'], c['segment_id'])]
                assert sr['generator_pf']
                if arm != 'BASE':
                    margin = gate_keys[(c['page'],c['locus'],c['segment_id'],c['event'],c['candidate'])]-c['nwords']
                    assert margin >= 0, (arm, entry['bif'], c, margin)
                    gate_min_margin = margin if gate_min_margin is None else min(gate_min_margin,margin)
                candidates.append(c['surface'])
                counts['all_pf_candidates'] += 1
                counts['candidate_m_crossed_7'] += (c['stable_glyph_length']>=7)!=(c['visible_glyph_length']>=7)
            for g in gates:
                sr = scope[(entry['bif'],g['page'],g['locus'],g['segment_id'])]
                assert sr['generator_pf']
                counts['gate_events']+=1
                counts['split_gate_events']+=g['split_end']
                counts['gate_events_on_judge_unobserved_pf']+=not sr['judge_observed']
            for q in proposals:
                sr = scope[(entry['bif'],q['page'],q['locus'],q['segment_id'])]
                assert sr['generator_pf'] and q['end'] and q['line_end_boundary'] and q['paragraph_line']>=2
                raw.extend(d['stable_surface'] for d in q['draws'])
                from judges.schema import glyphs
                names=q['draws'][q['chosen_draw']]['stable_surface']
                returned.append(names)
                counts['raw_proposal_calls'] += 1
                counts['raw_anchor_fallbacks'] += q['fallback']
                counts['raw_draws'] += len(q['draws'])
                counts['max_raw_draws_per_call'] = max(counts['max_raw_draws_per_call'],len(q['draws']))
            for t in tokens:
                sr = scope[(entry['bif'],t['page'],t['locus'],int(t['segment_id']))]
                if sr['generator_pf'] and t['draw_segment_end']=='1':
                    final_stable.append(t['stable_surface']); final_visible.append(t['surface'])
                if int(t['segment_id'])>0:
                    assert t['role']=='BODY'
                    counts['post_plant_body_tokens']+=1
            for q in requests:
                sr = scope[(entry['bif'],q['page'],q['locus'],q['segment_id'])]
                if sr['generator_pf'] and q['end'] and q['line_end_boundary'] and q['committed_to_final_page']:
                    selected_pre_rare.append(q['selected'])
                counts['strict_f1lf_requests']+=bool(q['v22_3_stage3d_strict_scope'])
            md=json.loads((p/'MECHANICAL.json').read_text())
            assert md['packing_exact'] and md['plant_false_heads']==md['terminal_mismatches']==md['invalid_rows']==md['support_violations']==0
        result['arms'][arm] = dict(counts=dict(counts), minimum_gate_rows_minus_candidate_nwords=gate_min_margin,
            all_candidate_visible=tally(candidates), committed_request_selected_pre_rare=tally(selected_pre_rare),
            final_generator_pf_stable=tally(final_stable), final_generator_pf_visible=tally(final_visible))
    result['raw_all_attempt_draws'] = tally(raw)
    result['raw_returned_before_map'] = tally(returned)
    result['limitations']=['Raw and candidate samples include retries and discarded branches; they are not independent tokens.',
                          'A committed request selected word is after Map and inherited sampler corrections, before engine rare work.',
                          'F1LF source and policy are frozen; downstream RNG permits later F1LF realizations to differ.',
                          'END_ONLY remains a non-atom endpoint observation, and is not promoted to FULL.']
    (OUT/'stages-and-scope.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':'PASS','arms':{a:r['counts'] for a,r in result['arms'].items()}}),flush=True)

if __name__=='__main__': main()
