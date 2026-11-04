# Stage 3C — live terminal proposal hook audit

Status: PASS
Parent: HerbalA-v22.2 (HerbalA_v22_2_JUDGED_20260920(4).zip)
Mode: read-only/static runtime audit; no parent source edited.

## Confirmed live chain

1. `bti2_patch_engine.generate_segment()` chooses the line/segment closure state (`end_state`) before requesting a word.
2. The parent sampler generates a complete word; its within-word END/STOP determines exact glyph length.
3. `V222F1LFRouterOffSampler.__call__()` executes the complete parent selector unchanged, preserving candidate bank, retry path and parent RNG.
4. For strict normal F1-LF, `_prepare_route_neutral_child()` constructs the v22.2 route-neutral child while preserving stable glyph length and physical width.
5. The correct Stage-3 terminal-source hook is immediately after that child is prepared and before `__call__()` returns the parent anchor.
6. The final staged child must be passed by `commit_word()` to the parent semantic/route commit.
7. The same final staged child must be used by `commit_surface()` before `PatchMapState.commit_surface()` records `prev_terminal`.

## Exact hook

File: `model/code/f1lf_router_off_sampler.py`
Current sequence:
- lines 197-199: full parent selector runs unchanged
- lines 215-218: route-neutral child prepared
- lines 220-230: child staged; parent anchor returned to engine
- lines 232-239: child substituted before semantic/route `commit_word`
- lines 252-271: visible stable positions substituted before downstream surface commit

Stage 3D should insert the length-aware terminal-source selector between current lines 215 and 220, operating on the prepared route-neutral `child`, and stage a single final child for both commit paths.

## Why this hook is correct

- Word length/within-word STOP has already been decided by the untouched parent generator.
- Parent candidate bank, proposal draws, packing/retry decision, and parent RNG trajectory remain unchanged.
- No `word[-1] = x` after commit is required.
- The selected terminal reaches route/semantic state through `commit_word(final_child, ...)`.
- The visible surface reaches `PatchMapState.commit_surface()` with the same terminal, so `visible terminal == semantic prev_terminal` is enforceable.
- F1 first-line words bypass the rare-glyph proposal branch (`para_line_raw == 1`), avoiding a rare suffix after the stable terminal.

## Relevant runtime evidence

`bti2_patch_engine.py`
- 116-119: `end_state` selected before word proposal.
- 166-180: word proposal/retry and end-state terminal-family acceptance.
- 186-197: accepted word is materialized, then `commit_word`, then `commit_surface`.

`entry_fast_sampler.py`
- 13-75: within-word draw loop.
- 60-69: END/STOP odds and depth/width correction.
- 70-75: END terminates the word; otherwise a glyph is appended.

`bti2_patch_state.py`
- 38-46: surface commit sets `prev_terminal` from the committed visible sequence.

`entry_correction.py`
- 101-117: `base_nonend()` exposes role/position/depth/history-specific 22-glyph non-END distributions.
- 127-142: `gains()` exposes early-depth position/phase/board corrections.

## Explicitly rejected insertion points

- Post-commit `word[-1]` replacement: forbidden and would risk visible/semantic mismatch.
- `paragraph_h1_sampler.commit_surface()` style postcommit rewrite: wrong layer for Stage 3.
- `w2_b2_sampler.commit_surface()` style postcommit rewrite: wrong layer for Stage 3.
- Editing `EntryFastSampler` globally: too broad; would violate strict F1-LF scope and risk changing STOP/RNG/packing outside scope.
- Editing `bti2_patch_engine` terminal-family retry logic: would alter frozen retry/packing mechanics.

## Stage 3D implementation contract from this audit

At the confirmed hook:
- strict scope gate only;
- use route-neutral child as the prefix/length anchor;
- L<=3: normal middle-LF terminal distribution;
- L>=4: F1 terminal distribution with only P(l) inherited from normal middle-LF, preserving all non-l ratios;
- stage one `final_child_seq`;
- return the untouched parent anchor from `__call__()`;
- commit `final_child_seq` through both semantic and visible commit paths;
- do not modify STOP, packing, retry, candidate bank, route mechanism, width, or length.
