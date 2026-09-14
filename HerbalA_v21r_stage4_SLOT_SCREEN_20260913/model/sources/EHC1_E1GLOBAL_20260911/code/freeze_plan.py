from experiment_env import *
import json,hashlib,platform
RUNS=[91151,91152,91153,91154,91155]
# Search existing execution manifests; namespace is page generation run, not
# incidental substring of floating point arrays or stochastic diagnostic seeds.
seen=set()
for p in (ROOT/'inputs').rglob('MECHANICAL.json'):
    d=json.loads(p.read_text())
    if 'run' in d:seen.add(int(d['run']))
for p in (ROOT/'inputs').rglob('*FROZEN.json'):
    try:d=json.loads(p.read_text())
    except Exception:continue
    for k in ['fresh_screen_seeds','confirmation_seeds','runs']:
        if isinstance(d.get(k),list): seen.update(x for x in d[k] if isinstance(x,int))
assert not seen.intersection(RUNS)
plan=dict(experiment='EHC1_E1GLOBAL_SINGLE_ABLATION',date='2026-09-11',
          change='Only E1 bridge and its diagnostic joint: external+known3 -> external-only',
          reference='E12_VH',baseline='BASE',candidate='E12_VH_E1GLOBAL',
          arms=['BASE','E12_VH','E12_VH_E1GLOBAL'],runs=RUNS,leaves=20,pages=300,
          same_seed_all_arms=True,primary_reference='E12_VH',secondary_reference='BASE',
          primary_judges=['SPACE_RAW','H2_RAW'],legacy_space_secondary=True,
          target_joint_JSD_secondary=True,coefficient_search=False,candidate_search=False,
          no_interim_performance_stopping=True,new_model_after_scores=False,
          core_scope='frozen18; outer heldout4 excluded',entry_scope='external complete16 only',
          other_leaf_information='unchanged; E2/H1V/H3/route/bT still use known3',
          fresh_seed_scope='absent in available generation and seed reservation manifests; historical target pages reused',
          known_existing_runs=sorted(seen),bootstrap=10000,statistical_unit='20 bifolia',
          thresholds_warning_only={'types_mae_increase':1.,'hapax_mae_increase':1.5,'mean_len_mae_increase':.05,'mean_width_mae_increase':.1,'ngram_bt_relative_abs_increase':.1},
          reasons_for_direct_5seeds='One user-specified intervention, no candidate or coefficient selection; all five runs report together')
e.write(ROOT/'PLAN_FROZEN_BEFORE_GENERATION.json',plan)
manifest={}
for parent in [EHC,JUDGE,DIAG]:
    for p in parent.rglob('*'):
        if p.is_file() and '__pycache__' not in str(p) and 'numba_cache' not in str(p):
            manifest[str(p.relative_to(ROOT))]=e.file_hash(p)
e.write(ROOT/'INPUT_FILES_SHA256.json',manifest)
e.write(ROOT/'ENVIRONMENT.json',dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__,platform=platform.platform()))
print('FROZEN',len(manifest),'files',plan)
