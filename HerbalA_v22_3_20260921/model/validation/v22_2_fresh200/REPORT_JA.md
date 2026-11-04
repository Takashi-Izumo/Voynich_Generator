# HerbalA-v22.2 fresh 200 審判報告

日付: 2026-09-20

親: `HerbalA-v22r-W2B2`  
候補: `HerbalA-v22.2 = parent + normal F1-LF ROUTER-OFF`

## 判定

**PASS WITH RESIDUAL / PROMOTE**

v22.2は、normal F1-LFだけ5–6g leaf-route scoreを最終候補選択から外す最小修正として、fresh seedで再現した。主目的のroute56距離を有意に改善し、combined盲検はchance域を維持し、packing・候補bank・proposal clockへの副作用は検出されなかった。

ただしglobal route56とbigramのsigned residualはなお有意であり、F1-LF terminal familyも完全には閉じていない。したがって clean PASS ではなく `PASS WITH RESIDUAL` とする。

## Fresh seed

正式seedは `92001–92009, 92011`。当初予定した92010は、**親W2B2単体**がfold 4で既存の `terminal_mismatch/fake_head` assertionに停止したため、審判値を見る前に機械的不成立として除外し、92011へ全体置換した。

また採点前に、single-candidate F1-LF bankを「適用」と記録してchildをstageしない実装バグを発見した。これは選択肢が1個しかないため本来no-opであり、`SINGLE_CANDIDATE` skipへ修正した。修正後に全400ケースを最初から再生成した。

## 1. 機械監査

- parent: 200/200 packing exact
- v22.2: 200/200 packing exact
- support violation: 0 / 0
- invalid row: 0 / 0
- segment retry: 0 / 0
- 220 committed normal-F1-LF scope requests
- 218 route-neutral eligible, 2 single-candidate no-op
- actual visible word changes: **56**
- changed pages: **55/200**
- changed bifolia: **17/20**
- changed wordは全56件 `role=F1, segment_id=0, non-PF`
- exact glyph length: 56/56維持
- physical width: 56/56維持
- scope外visible word change: **0**

親と子の全177,127 requestについて、proposal key・candidate bank・proposal draws・accept/reject outcome・親probabilityは**全件一致**。したがってv22.2は受理済みbank内のroute-neutral再選択だけを変えている。

内部route traceは55/200頁で変わったが、これは実際にwordが変わった55頁と完全一致し、その後のrequest bank/probability/visible outputには波及しなかった。

## 2. 標準凍結judge

20 bifoliaを正式統計単位とする。

| judge | parent margin | v22.2 margin | signed shift | v22.2 real/gen |
|---|---:|---:|---:|---:|
| word | -0.001377 | -0.001038 | +0.000338 | 9/11 |
| ng | -0.017481 | **-0.016665** | **+0.000815** | 7/13 |
| bigram | -0.021388 | -0.021140 | +0.000247 | 8/12 |
| trigram | -0.007477 | **-0.006631** | **+0.000847** | 8/12 |
| route56 | -0.032871 | **-0.032188** | +0.000683 | 4/16 |
| combined | -0.009429 | **-0.008852** | **+0.000577** | **8/12** |

paired signed-shift Wilcoxonは ng `p=.00467`, trigram `p=.00333`, combined `p=.00871`。6標準judgeでHolm補正しても q≈.0233, .0200, .0349。

combinedはv22.2でも 8/12、binomial p=.503、sign-flip p=.251でchance域。

### route56 primary

route routerを外す変更の直接ターゲットとして、`|real-generated margin|` は

`0.062188 -> 0.061351`

へ改善。20葉中**14改善 / 2悪化 / 4同率**、Wilcoxon片側 **p=.000290**。10 fresh seedのうち8 seedで平均改善方向。

一方route56 signed residualそのものは `4 real / 16 generated`, sign-flip p=.0128で残るため、全解決とはしない。

## 3. F1-LF局所審判

真正targetにnormal F1-LFが存在する16葉を局所評価。

- exact terminal direct-JSD: `0.78135 -> 0.74748`（改善方向、非有意）
- F1-LF route56 direct-JSD: `0.98439 -> 0.96359`（疎で10葉のみ）
- terminal-family JSD: `0.42154 -> 0.43781`（微悪化、非有意）

特に `y` は、

- MAE: `0.50625 -> 0.46146`
- real-targetに対するleaf slope: **`-0.172 -> +0.0018`**

となり、親の逆方向追従がほぼ消えた。MAE paired p=.0918で単独有意までは届かない。

`NMY/LR`は小さな非有意悪化が残り、terminal-family問題の完全解決とは扱わない。

## 4. frequency / length / width

- token数: exact invariant
- mean word length: exact invariant
- mean physical width: exact invariant
- F6–10, F11+: exact invariant
- types/hapax:ごく小さい改善方向
- F3–5:ごく小さい悪化方向、非有意

局所router OFFがfrequency spectrumを実質的に壊した証拠はない。

## 5. 最終判定

採用理由:

1. 事前に狙ったroute56距離がfresh 20葉で有意改善。
2. combined blindはchance域を維持。
3. ng/trigram/combined signed residualも縮小。
4. F1-LF `y` の逆追従がほぼ消える。
5. 56変更語はscope内だけで、scope外visible change 0。
6. 全request clock/candidate bankは親と完全一致。
7. length/width/packing/frequencyに実質的回帰なし。

残差:

- global route56 residualは未閉鎖。
- global bigram residualも未閉鎖。
- F1-LF NMY/LR / terminal familyは完全には直っていない。

よって、

**`HerbalA-v22.2 = PROMOTE / PASS WITH RESIDUAL`**

と判定する。
