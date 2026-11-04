# HerbalA-v22r-W2B2 — active model

親：`HerbalA-v22r`。

追加実装：`code/w2_b2_sampler.py`。

実行器：`code/run_v22r_w2b2.py`。ルートの `code/run_v22r.py` もこれを起動する。

設定：`parameters/W2_B2_CONFIG.json`。

検証：`validation/w2_b2/`。

W2-B2はMIDDLE W2、3–5 glyphのH2だけをpost-commitで変更する。H1/H3+/terminal/length/width/route/packing/RNGは凍結。

fresh blind 200と多様審判をPASS済み。global bigram residualは残る。

F1 patchは未採用・未統合。
