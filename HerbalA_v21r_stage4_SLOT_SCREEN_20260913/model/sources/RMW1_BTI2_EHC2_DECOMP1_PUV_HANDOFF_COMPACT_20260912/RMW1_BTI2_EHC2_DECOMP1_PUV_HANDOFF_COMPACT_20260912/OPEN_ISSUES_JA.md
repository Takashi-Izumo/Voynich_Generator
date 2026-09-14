# 現時点のPUV問題点一覧

## P0 — 正式昇格を阻止している主要問題

### 1. general n-gram回帰警告

Stage6のBTI2_BASE比:

- `ng`: **+13.619%**
- `bigram`: **+14.143%**
- `trigram`: **+16.339%**

事前の「+10%超新規回帰警告を作らない」条件に反するため、正式BTI2後継に昇格できない。

ただし20 bifolia pairedでは:

- ng p=0.264
- bigram p=0.400
- trigram p=0.150
- Holm後はいずれも非有意

したがって「確定した破綻」ではなく、**方向として無視できない回帰警告**。

---

### 2. 頁平均token/length/width MAEの悪化

BTI2_BASE比:

- token count MAE: **+17.83%**
- mean length MAE: **+21.21%**
- mean width MAE: **+19.60%**

特にmean length / mean widthは葉単位でも強い悪化。

ただし詳細な`length_width` judge自体はPUVがBTI2より**約18.0%改善**している。

したがって、

> 長さ/幅の分布そのものが悪い

のではなく、

> **頁内で各shape状態を何回訪れるか、結果として頁平均がどこへ動くか**

が問題。

BTI2のshape scheduleへ単純に戻すと詳細length/width改善を失うため、単純固定は不採用。

---

## P1 — 原因は分かったが安全な補正法が未発見

### 3. n-gram回帰はshape feedbackだけでは説明できない

Stage6同seed反実仮想:

`SHAPE_LOCK`でもBTI2比:

- ng +8.84%
- bigram +16.60%
- trigram +13.94%

`REQUEST_LOCK`でも:

- ng +11.72%
- bigram +16.40%
- trigram +16.15%

したがって、shape/packing feedbackも一部原因だが主因ではない。

---

### 4. prevT / route feedbackは止められない

REQUEST_LOCKするとT-H1 joint改善が弱くなる。

通常PUVのBTI2比T-H1改善:

- **-8.74%**

REQUEST_LOCK:

- **-3.34%**

通常PUV比ではREQUEST_LOCKがT-H1 JSDを約+5.92%悪化、p≈0.0085。

つまりprevT/route feedbackは副作用だけではなく、PUVの望ましいT-H1改善の一部でもある。

---

### 5. H1-H2 compatibility不足説は棄却済み

語頭H1-H2 bigram `B_START` はPUVがBTI2より約**4.94%改善**、p≈0.0368。

したがって:

> 新しいH1を選んだため既存H2と噛み合わない

という単純説明は成立しない。

H1/H2へ新しいpenaltyを入れるべきではない。

---

### 6. state occupancy単独も原因ではない

H2以降のstate occupancy JSDは粗いstateで:

- BTI2: 0.3702
- PUV: 0.3593

とPUVの方が有意に良い（p≈0.0217）。

trigram審判の反実仮想でも、target emissionを固定してPUV occupancyだけ使うと、PUVがBTI2より有意に良い（p≈0.0036）。

したがってoccupancy-only controllerは不適切。

---

### 7. 本命残差は state–emission interaction

現在もっとも整合的な分解:

- PUV occupancy単独: 良い
- PUV conditional emission単独: 大きな悪化ではない
- **PUV occupancy × PUV emission**: 組み合わせるとtrigram回帰が出る

反実仮想trigram abs-margin:

- actual PUV−BTI2: **+0.007421**
- target occupancy固定: +0.000723
- target emission固定: **−0.011446**（PUVが良い）
- interaction差分: **+0.018144**

しかし「どのinteractionが危険か」をtargetを見ずに予測する方法がまだ無い。

---

## P1 — 試したが棄却した修正

### 8. SEC0 predictor FAIL → SEC1は未実装

SEC0はknown3+externalだけから

`risk = overvisit × emission mismatch`

がPUVのn-gram悪化を予測できるか検定した。

最良 `tau_S=128`:

- pooled rho=0.2556
- 正方向fold=3/5
- raw one-sided p=0.1379
- Holm p=0.4136

事前条件 `4/5 fold + Holm p<.05` を満たさずFAIL。

riskも疎く:

- risk=0: 161/320 pseudo-target
- risk>.05: 0 visit

よってSEC1 gateは**実装しない**。

---

### 9. RBS1_STRICTは不採用

6+ glyph語でroute56を落とさずbTを改善するselector rescueは機械的には成功したが、3seedでbT改善が頑健でなく、SPACE改善を少し戻した。

さらに元PUVのbT警告自体がseed追加で+10%以内へ収束した。

現Stage6ではBTI2比 `bT_leaf_excess +5.07%` であり、現在の主要blockerではない。

RBS1は現行PUVへ入れない。

---

## P2 — 統計的状態と解釈上の注意

### 10. n-gram警告は+10%閾値を越えるが統計的確定ではない

現在はpromotion contract上はFAILだが、Holm後有意ではない。

従って今後の修正は大きな新文法を足すのではなく、**小さく、training-onlyで予測可能なものに限定**すべき。

---

### 11. PUVの主要改善は壊してはいけない

BTI2_BASE比:

- SPACE_RAW: **−20.97%**, Holm p=0.0240
- H2_RAW: **−13.28%**（非有意）
- H1 JSD: **−9.69%**
- T-H1 joint JSD: **−8.74%**, p=0.000565

したがって、次の改良でU/Vを弱めたり、prevT/route feedbackを全面停止したり、H1/H2を直接再補正するのは優先度が低い。

---

## 現時点の正式判断

- PUV本体: **保持**
- U/V分解: **構造部品として支持**
- 正式A_LEGACY後継: **未昇格**
- 正式BTI2後継: **未昇格**
- blind contest: **まだ進まない**
- RBS1: **不採用**
- SEC1: **未実装 / SEC0 FAIL**

次のチャットでは、これらを前提として議論を再開する。
