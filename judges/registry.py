"""Stable audit IDs; these are views, not 25 independent votes."""

NAMES = {
    'J01': '第一行第一語', 'J02': '第一行全体', 'J03': '第二行以降の物理行頭語',
    'J04': '第二行以降の物理第二語', 'J05': '物理第三語以降', 'J06': '物理行末',
    'J07': '段落末・最終行', 'J08': '第一行末・語長別terminal',
    'J09': '行頭語H2/H3条件付き', 'J10': '行頭語の縦依存',
    'J11': 'W2 H2条件付き・語長別', 'J12': '短BODY H2条件付き',
    'J13': '段落内BODY H1履歴', 'J14': 'segment末手前', 'J15': 'SPACE接続',
    'J16': '末尾2字・境界別', 'J17': '共有route・R4・系列',
    'J18': '語内深さ・語境界・長さ幅', 'J19': '語彙共有・近似語',
    'J20': '頻度・反復', 'J21': 'rareを含む表記',
    'J22': '植物前末・図後再開', 'J23': '面全体の語彙・語内n-gram',
    'J24': '総合集約', 'J25': '語順・語全体の連接',
}

# Endpoints take precedence over word ordinal: each visible word has one atom.
ATOMS = ('PHW', 'FIRST_INTERIOR', 'HEAD', 'W2', 'BODY', 'PLANT_END', 'LINE_END', 'PARA_END')

CONFIG = {
    'version': 'partition-prototype-jsd-v2',
    'direction': 'closer_to_known3',
    'reference': 'equal mixture of three per-document normalized distributions',
    'conditional': 'reference-weighted conditional JSD on common observed contexts',
    'primary_atoms': list(ATOMS),
    'atom_context_channels': ['space_T_H1', 'word_pair', 'length_pair'],
    'atom_weights': {k: 1.0 for k in ATOMS},
    'tie_epsilon': 1e-12,
    'internal_tie': 'neutral',
    'final_tie': 'sha256(set_id, config_hash), independent of answer key',
    'promotion_threshold': None,
    'status': 'research_baseline_not_calibrated',
}
