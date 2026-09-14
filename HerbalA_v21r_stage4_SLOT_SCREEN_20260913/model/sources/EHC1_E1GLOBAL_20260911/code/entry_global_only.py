"""Only replace E1 bridge/joints by the frozen external-only tables.
E2, H1V, H3, selector and all generator coefficients remain unchanged.
"""
from experiment_env import *
from entry_correction import CorrectionTables, configs
from dataclasses import replace

CANDIDATE='E12_VH_E1GLOBAL'

def candidate_config():
    return replace(configs()['E12_VH'], model_label=CANDIDATE)

class GlobalEntryTables(CorrectionTables):
    def __init__(self, external, known, cdf, quad, base, fc, core_audit, enabled=True):
        super().__init__(external, known, cdf, quad, base, fc, core_audit)
        legacy_fingerprint=self.content_fingerprint()
        if enabled:
            # Parent constructor with zero KN counts defines the exact A-only E1.
            # Never reuse its other tables: H2/H3/HEAD must still see known3.
            ext=CorrectionTables(external,known.iloc[:0].copy(),cdf,quad,base,fc,core_audit)
            self.bridge=ext.bridge
            self.joints=ext.joints
        self.audit.update(entry_known3_enabled=not enabled,
                          intervention='E1_KNOWN3_ONLY_OFF' if enabled else 'ADAPTER_OFF',
                          entry_external_bifs=list(fc.complete_train_bifs),
                          other_corrections_known3_enabled=True,
                          legacy_learning_fingerprint=legacy_fingerprint,
                          adapter_sha256=e.file_hash(Path(__file__)))
        import ehc_paths as ep
        self.audit['learning_sha256']=ep.digest(self.audit)
