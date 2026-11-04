# Stage 3D-r1 route-state leakage fix

Stage 3Gで `seed 91708 / C:2 / f23v.1` に1件のroute-state leakageを検出した。
原因はStage3D final_childを `MapState.commit()` へ渡していたこと。

修正後:

- `commit_word`: 親v22.2のcommit pathをそのまま呼び、`v22_2_child_seq`をroute/MapStateへcommit
- `commit_surface`: Stage3D final_childをvisible surfaceと`prev_terminal`へcommit
- `commit_surface`中にroute `current` が変化しないことをassert

これによりroute mechanismをv22.2と完全一致させつつ、F1-LF terminalだけをvisible/semantic terminalとして反映する。
