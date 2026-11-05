# PF生成改善・第1比較

設計007の最優先案を独立packageとして実装したものです。`BASE / PF_GATE / PF_GATE_LENGTH`を扱い、原版・審判・既存M1は変更しません。正式版への採用を表す実装ではありません。

- `PF_GATE`: 複数行段落の最終LINE_END segmentだけ、親のclosing gateへ4区分のoffsetを追加します。
- `PF_GATE_LENGTH`: 同じgateに、親raw END語の長さ・幅に対する正の重み付けを追加します。最大32回の支持内再提案後は最初のanchorへbackoffします。Map候補選択、m/rare、packing、末字整合、PFの2候補とLEN1は親を維持します。
- 新法則は外部16葉だけでfitし、外側test4葉とtarget known3を除外します。学習表はstable22、適用先はpre-m raw語で、最終visible分布は別に記録します。

gateのsplit gainは原版engineで一度だけ適用します。sampler factoryとrunnerの一時接続は`finally`で復元します。共有coreのSTOP配列や展開runtimeを変更しません。

## 実行

v22.3の親archive・依存関係は既存M1と同じです。Python環境は `/workspace/.venvs/voynich/bin/python`、実行時は `NUMBA_NUM_THREADS=2` と `PYTHONPYCACHEPREFIX=/workspace/voynich-setup/pycache` を使用しています。

以下の各出力先は未使用のパスを指定してください。既存のplan・生成物・PASSを上書きしません。

```bash
python -m experiments.pf_generation plan --output /path/to/new-run/plan
python -m experiments.pf_generation generate \
  --plan /path/to/new-run/plan/plan.json --output /path/to/new-run/forward
python -m experiments.pf_generation generate \
  --plan /path/to/new-run/plan/plan.json --output /path/to/new-run/reverse --reverse
python -m experiments.pf_generation audit \
  --plan /path/to/new-run/plan/plan.json --generated /path/to/new-run/forward \
  --repeat /path/to/new-run/reverse --output /path/to/new-run/audit
python -m experiments.pf_generation summarize \
  --plan /path/to/new-run/plan/plan.json --generated /path/to/new-run/forward \
  --output /path/to/new-run/summary
python -m experiments.pf_generation export \
  --plan /path/to/new-run/plan/plan.json --generated /path/to/new-run/forward \
  --output /path/to/new-run/anonymous
python -m experiments.pf_generation evaluate \
  --plan /path/to/new-run/plan/plan.json --inputs /path/to/new-run/anonymous \
  --models /path/to/frozen/cal-models --output /path/to/new-run/evaluation \
  --jobs 2 --bootstrap 100
```

標準smokeはA:2/A:3/G:1・seed91701、3群+REFERENCEの12面です。逆順を含め24面。`plan --identity`で別の恒等planを作れば、新しい2群もBASE/原版と全意味出力・最終state・main RNGで一致することを監査します。恒等設定ではaccept乱数を追加しません。

`--kind development --bifolia all --runs ...`で別の開発planを作れますが、本比較の開始には能力対照・実行予算・実行計画の準備が必要です。通常のbootstrap既定値は10,000、上記の100は採点接続smoke用です。固定CAL hashは `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`。モデルが違えば停止し、PROTOへfallbackしません。

## 監査と検証

planは新法則、policy、ソース、凍結原版・審判、展開入力tree、構造scopeを封印します。監査receiptは現在の生成manifest・copied plan・statusと結合し、生成物とchecksumを更新しても古いPASSを受理しません。再監査を始めた時点で旧sealを無効化します。

`m1_events/m1_candidates`は既存の枝・state・RNG監査契約を継承しています。追加の `pfgen_gates/pfgen_proposals` は全試行を記録し、独立監査で確率・重み・採否・上限・scopeを再計算します。main RNGは各armの初期2候補argmax、採用stateは救済枝の場合もあり、両者を分けて記録します。共有request採番と後続side RNGへの波及を含む総効果です。

```bash
python -m unittest discover -s experiments/pf_generation/tests -v
python -m unittest discover -s experiments/m1_pf/tests -v
python -m unittest discover -s judges/tests -v
```

実データ負例は、他の生成・採点processが動いていない時に任意で実行します。対象ファイルを一時変更しますが、`finally`で元bytesを復元し、最後に新しい正の監査を行います。

```bash
python -m experiments.pf_generation.tests.run_artifact_probes \
  --plan /path/to/new-run/plan/plan.json --generated /path/to/new-run/forward \
  --repeat /path/to/new-run/reverse --output /path/to/new-run/probes
```

検証結果と再現記録は [実装側検証記録](../../sandbox/m1-review/implementation/009-pf-generation-v1/VALIDATION.md)を参照してください。通常順/逆順24面、恒等対照12面、実行予算測定12面の計48面は機構smokeであり、48個の独立した真正面ではありません。

## 次段階

個別末字scoreとSPACE接続は別studyとして設計済みで、このpackageの第1比較には混ぜていません。64枝replayを用いる審判能力対照は未実装で、本比較前の別工程です。全20葉×10seedの新本比較、正式採用、main mergeは今回行っていません。
