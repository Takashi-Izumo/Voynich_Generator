# HerbalA-v22.2

Self-contained pre-judge implementation based on `HerbalA-v22r-W2B2`.

The only new behavior is a **normal F1-LF leaf-route-router OFF** layer. The parent request is generated and accepted normally; within the accepted parent candidate bank, v22.2 subtracts the 5/6-glyph route score and re-selects from the route-neutral probability using a request-local SHA-256 maximal coupling stream.

Scope: FIRST × physical LF × role F1 × segment_id 0, excluding paragraph-final/single-line FIRST and plant-restart BODY.

No `S_LF` terminal prior, BODY terminal-row patch, preterminal patch or plant-restart correction is included.

Status: `IMPLEMENTED_PREJUDGE_NOT_JUDGED`.

Run: `python model/code/run_v22_2.py --fold 0 --run 91701`  
Preflight: `python model/code/validate_v22_2.py`
