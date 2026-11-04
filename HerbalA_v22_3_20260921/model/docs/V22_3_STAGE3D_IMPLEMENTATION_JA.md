# HerbalA-v22.3 candidate — F1-LF Stage 3D 実装記録

## 状態

`STAGE3D_IMPLEMENTED / STATIC+LOGICAL PASS / LIVE GENERATION NOT RUN`

正式なstable parentは引き続き `HerbalA-v22.2`。この段階では `v22.3` へ昇格しない。

## 実装した仮説

- `L <= 3`：normal middle-LF terminal selector
- `L >= 4`：F1 terminal selectorを維持し、`P(l)`だけnormal middle-LFから継承
- STOP/CONTINUE：親v22.2を変更しない
- y/n専用bias、S_LF、post-hoc rewriteは追加しない

長語は

`Pnew(l)=PnormalLF(l)`

`Pnew(g!=l)=PF1(g)*(1-PnormalLF(l))/(1-PF1(l))`

とし、non-l比およびy/n比を保存する。

## strict gate

frozen event/schedule metadataから再構成した `F1LF_STRICT_SCOPE_88.csv` を用いる。

- FIRST
- physical LF
- segment_id=0
- role=F1
- plant restart/boundaryなし
- multi-line paragraph
- multi-word line
- linear paragraph
- EXACT_W_SEQUENCE
- width known
- complete 20 bifolia only

再構成結果は **88 terminal events / 20 bifolia** で引き継ぎ値と一致した。

## live挿入位置

親v22.2の候補bank・accept/retry・packingを完全に通した後、v22.2 route-neutral childがstagingされた時点で、そのprefixを凍結してterminalだけをproposalする。最終childはcommit前に確定し、semantic route commitとvisible surface commitの双方へ同一childを渡す。

したがって禁止されているcommit後の `word[-1]=x` 型rewriteではない。

## source law

各target bifoliumを丸ごと除いた19 complete bifoliaから構築する。

- F1 source：FIRST non-LF F1
- normal-LF source：MIDDLE physical-LF BODY
- shared shrinkage source：MIDDLE BODY
- `tau=20`
- short/longを `L<=3 / L>=4` で分離

この表は20 target bifoliaごとに保存し、target bifoliumのglyphはsource lawへ入れない。

## frozen mechanics

Stage3D samplerは親anchorをpacking/retryへ返す。terminal proposalは同一prefix・同一glyph length・同一terminal physical widthだけを許す。candidate bank、STOP、SPACE、carry、retry、capacity、route proposal clockは変更しない。

## Stage3D validation

static/logical equivalent testは21/21 PASS。

20 bifoliaのlaw全てで：

- probability sum error <= machine epsilon級
- `P(l)` inheritance error <= 約1.2e-15
- non-l ratio error <= 約2.8e-15
- y/n ratio error <= 約2.3e-16
- support changes = 0
- NaN/negative = 0

加えてstrict scope ledger 88/20を1 testとして21/21とした。

## 未実行

Stage3Dではlive generation比較をまだ行わない。次のStage3Eでruntime unit/invariantを行い、その後Stage3Fで親v22.2とのpaired live auditへ進む。

## source provenance留保

旧Stage1/2のcomponent artifact自体は現在ランタイムに未マウントのため、source lawは凍結event metadataからcurrent-TL再構成した。詳細は `V22_3_STAGE3D_SOURCE_PROVENANCE_JA.md`。正式昇格前にStage3Eで照合する。
