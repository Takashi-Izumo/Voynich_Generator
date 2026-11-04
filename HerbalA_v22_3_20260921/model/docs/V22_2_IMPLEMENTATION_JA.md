# HerbalA-v22.2 実装仕様

## 1. 定義

`HerbalA-v22.2` は `HerbalA-v22r-W2B2` を親とし、**normal F1-LFに限って5–6 glyph leaf-route routerをOFF**にする局所版である。

```text
v22.2 = v22r-W2B2 + normal F1-LF ROUTER-OFF
```

本パッケージは **実装・preflightまで**。v22.2としての審判は未実施。

## 2. 対象scope

全条件を同時に満たすrequestのみ対象。

```text
role == F1
row_phase == FIRST
physical LF: end == True and line_end_boundary == True
segment_id == 0
board == LF
paragraph-final FIRST / single-line paragraphではない
```

植物分断後の `segment_id > 0 / role=BODY` は対象外。

## 3. 実装位置 — accepted bank上のclock-safe ROUTER-OFF

最初の素朴実装では、親candidate selectorより前にroute scoreを0へすると、候補accept/retry数が変わりproposal clockまでずれるケースがあった。このため正式v22.2では、**親のproposal/accept経路を現在requestについて完全に通した後**にroute-neutral選択を行う。

処理順：

```text
親W2B2がcandidate bankを生成
↓
親route score込みで通常proposal
↓
親のaccept/retryをそのまま完了
↓
受理されたrequestのcandidate bankを取得
↓
各candidateについて
neutral_score = parent_score - route_score
↓
target P = softmax(neutral_score)
↓
parent P → target P をrequest-local maximal coupling
↓
route-neutral childをcommit
```

この方式により、対象requestそのものについては、

- proposal-id
- candidate bank
- proposal draws
- accept/reject
- parent RNG
- packing

を親と同じに保つ。

## 4. candidate bankは変更しない

v22.2は語を新規生成・追加しない。親W2B2がそのrequestで既に生成した候補bankだけから選び直す。

親bankは同一stable glyph長・同一physical width制約を既に満たすため、v22.2 childもそれを継承する。

## 5. route state

routerをモデル全体から削除するわけではない。

```text
BODY              router ON
W2                router ON
通常中間行LF      router ON
植物後BODY        router ON
normal F1-LF      selection時だけ router OFF
```

normal F1-LFでroute-neutralに選ばれた語は、受理後は**通常どおりroute/semantic stateへcommit**する。したがって後続への真正な因果効果は許す。ただし現在requestのproposal/retry clockは親と一致する。

## 6. RNG

親のmain RNGを追加消費しない。

route-neutral再選択にはrequest固有のSHA-256 side streamを使う。namespace：

```text
V22_2_F1LF_ROUTER_OFF_V1
```

最大結合を用い、親分布とroute-neutral分布の共通確率質量は可能な限り保持する。

## 7. 維持するもの

変更しないもの：

- v22r-W2B2全機構
- W2-B2 H2局所補正
- candidate bank生成
- candidate合法性
- exact glyph length
- stable physical width
- line / segment capacity
- remaining width
- SPACE
- carry / retry
- plant boundary
- paragraph-final系
- 親main RNG

## 8. 明示的に入れないもの

v22.2には以下を入れない。

- `S_LF` terminal prior
- BODY terminal row
- terminal-only correction
- sibling-word correction
- preterminal path correction
- plant-restart BODY correction

ROUTER-OFF単独の寄与を次の審判で測るためである。

## 9. 実装ファイル

- `code/f1lf_router_off_sampler.py`
- `code/run_v22_2.py`
- `code/validate_v22_2.py`
- `parameters/V22_2_CONFIG.json`
- `MODEL_STATUS_V22_2.json`

## 10. preflight実測

審判ではなく機械監査として `A:2 / seed 91701` の1ケースのみ実走した。

親とv22.2で：

```text
all requests       626 / 626
committed requests  71 / 71
proposal-id sequence  exact
candidate banks       exact
proposal draws        exact
accept/reject flags   exact
packing table         exact
```

v22.2対象normal F1-LFは2 request。1件でroute-neutral childが親選択と変わり、1件は同一だった。

NLL/JSD/slope/frequency等の審判値は計算していない。

## 11. 次段階

実装をここでfreezeし、次チャット／次工程で親W2B2との審判を行う。
