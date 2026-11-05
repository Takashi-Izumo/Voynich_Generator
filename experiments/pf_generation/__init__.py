"""PF design 007, study one: closing gate and supported END-word proposals."""
from experiments.m1_pf import BASE_COMMIT, EXTRACTOR_HASH, HISTORICAL_SEEDS, MODEL_SET_HASH, PROTOCOL_HASH

ARMS = ('BASE', 'PF_GATE', 'PF_GATE_LENGTH')
CONTRASTS = (('BASE', 'PF_GATE'), ('PF_GATE', 'PF_GATE_LENGTH'))
DESIGN = 'sandbox/m1-review/designs/007-pf-generation-v1/DESIGN_CONTRACT.json'
POLICY = dict(gate_ridge=20.0, prior_mass=0.5, shrinkage_mass=20.0,
              gain_min=0.25, gain_max=4.0, max_raw_draws=32)
