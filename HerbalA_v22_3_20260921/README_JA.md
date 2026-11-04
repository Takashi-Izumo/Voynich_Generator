# HerbalA-v22.2 — F1-LF ROUTER-OFF 正式審判済み

**親モデル:** `HerbalA-v22r-W2B2`  
**状態:** `PROMOTED_PASS_WITH_RESIDUAL`  
**審判日:** 2026-09-20

Fresh seed `92001–92009, 92011`、20 bifolia × 10 seed = 200セットで審判。
主目的route56距離は14/20葉改善、paired Wilcoxon p=0.000290。combinedは8/12でchance域を維持。packing 200/200 PASS、scope外visible change 0。

詳細: `model/validation/v22_2_fresh200/REPORT_JA.md`

## 実装

# HerbalA-v22.2 — F1-LF ROUTER-OFF 実装版

**親モデル:** `HerbalA-v22r-W2B2`  
**状態:** `IMPLEMENTED_PREJUDGE_NOT_JUDGED`  
**審判:** 未実施

v22.2の変更は一つだけです。

```text
normal F1-LF
= FIRST × physical LF × role F1 × segment_id 0
```

で、親W2B2が受理したcandidate bankから**5–6g leaf-route scoreを除いた確率で再選択**します。

親proposal/accept/retryは現在requestについて完全に通してから再選択するため、candidate bank・proposal clock・packingを直接変えません。選ばれたchildはその後通常どおりsemantic/route stateへcommitします。

`S_LF` prior、BODY terminal row、植物再開BODY補正は入れていません。

## 実行

```bash
cd model/code
python run_v22_2.py --fold 0 --run 91701
```

## preflight

```bash
cd model/code
python validate_v22_2.py
```

A:2 / seed 91701のmechanical smokeのみ実施済みで、親と626/626 proposal、candidate bank、accept/reject、packingが一致しました。**審判指標は未計算です。**

詳細：`model/docs/V22_2_IMPLEMENTATION_JA.md`
