# 第一案 PF_GATE / PF_GATE_LENGTH 独立検証

2026-11-05。依頼010。開始HEAD: `fd1fa286671962ab768886597a82b167e7dcb52f`。

**結論: 要修正。通常の生成・恒等対照・既定の負例・固定CAL接続は再現できたが、介入ログを欠落させた生成物を新規監査が受理する。第一案の独立PASSはまだ付けない。** 原版・既存M1・審判・実装・statusは変更していない。本報告と再現用資料だけを追加する。

## R1 — P2: 介入ログの完全性を監査していない

対象: [policy_audit.py](../../../../experiments/pf_generation/policy_audit.py#L55) の行55–98、および [audit.py](../../../../experiments/pf_generation/audit.py#L124) の順序反転比較。

存在するgate/proposal行の値は再計算するが、PF候補・語生成要求から期待される行が存在することを確認していない。空の配列では検査ループを通過し、同じ配列から作った集計値との比較だけが残る。反転側も同じ欠落なら、policy digestの一致では検出できない。

再現:

1. 正常に監査できた通常順の生成物を別rootへコピーする。
2. `PF_GATE_LENGTH / A:2 / 91701` の `pfgen_gates.jsonl.gz` と `pfgen_proposals.jsonl.gz` を空にする。
3. `PF_GENERATION_FINAL.json` のgate/proposal/raw draw/fallback関連5集計を0にし、この3ファイルのmanifest checksumを更新する。tokens、requests、PF候補、state、RNG等の17ファイルは変更しない。
4. 古いPASSを使わず、新規の `audit()` を実行する。

**結果: PASS。評価前チェック `audited()` も受理した。** 実際にはgate 57回、raw介入1,954回、親raw draw 4,084回の記録を消している。さらに逆順側のコピーにも同じ欠落を施し、`repeat`付きの新規監査と評価前チェックが通ることも確認した。

証拠: [単独監査の負例](trace-omission-probe.json)、[反転込みの負例](trace-omission-both-orders.json)、[再現script](probe_missing_policy_traces.py)。改変したのはコピーだけであり、正常生成物・入力は保存されている。改変コピーで新しい予測・採点までは実行していない。

影響は「今回の語生成が壊れている」というものではない。監査PASSが介入ログの欠落を否定できず、介入が適用された範囲・回数を保証できない問題である。checksum更新後の新規監査も信頼する現在の契約では修正が必要。

修正案:

- gate query、PF枝、語生成要求、raw呼出しを識別子と順序で対応づけ、期待する記録の欠落・重複・範囲外を検出する。ログ自身の件数を数えて同じログの集計と比較するだけでは足りない。
- 最低限、gateを使う各PF候補の語開始をカバーすること、PF END raw要求に対応する介入記録があることを独立した候補・要求記録から検査する。retry・Map内候補・破棄枝・恒等設定を含めて対応を定義する。
- 全消去、部分欠落、重複、集計/checksum更新、両順序で同じ欠落を負例へ加える。失敗時にsealを失効させ、正常対照は通す。

今回の正常出力を別途集計すると、すべての介入PF候補に少なくとも候補語数分のgate行があり、構造scope外の記録もなかった。この手元確認は出荷する監査コードの修正を代替しない。

## 独立再実行の結果

共有の生成物や過去PASSを流用せず、新規rootで実行した。

| 確認 | 結果 |
|---|---|
| 実装manifest | 37ファイルのサイズ・SHA-256一致 |
| 新unit / M1 / 審判 | 20 / 27 / 56件、全PASS |
| 新規fit | 全5fold。PF学習末尾96 / 94 / 96 / 98 / 96件 |
| fitの別計算 | 元表からmask・等葉重み・長さ表を再構成し、gateは別のBrent法で解いた。theta最大差約6.08e-13、gain差0 |
| 通常順・逆順 | A:2/A:3/G:1、seed91701、3群+REFERENCE、24面 |
| BASE対原版 | 全意味出力・最終state・実際の最終main RNG一致 |
| 順序反転 | 比較9ケースの意味出力・state・RNG・policy digest一致 |
| 別の恒等plan | 12面。全3群・計9ケースが原版の意味出力・state・RNGと一致 |
| packing / support / invalid / 末字 / PLANT | 正常生成物では違反0 |
| 既定の実データ負例 | law、展開設定、token+checksum、旧PASS、失敗後seal、自己整合REFERENCE RNG改変をすべて拒否 |
| 復元 | 入力と元生成物のchecksumを再確認。最後の新規正監査PASS、現sealも再確認 |
| 固定CAL | 再fit・fallbackなし。9予測を全保存した後で採点、2対比へ接続 |
| 追加のログ欠落負例 | **誤受理。R1** |

fitは新法則について外部16完全葉の全4面から抽出し、外側test4葉とtarget known3を除外していた。全16葉にPF学習例がある。親coreは既存の `FROZEN_18`、すなわち外部16完全葉と従来の不完全補助2葉を用いる既存構成を維持する。全体系を新たにcomplete16で再学習したという意味ではない。

新規fitしたsmoke planの内容は共有planと一致した。hashが同じなのは決定的に再計算できたためで、共有ファイルをコピーして実行したためではない。

- study plan: `32537fffbcb53f9a5cfa03545650cde3fabe816cd19292aa5bd01743e5289152`
- identity plan: `de01514c5e869b9667e223aec5262f8afa4b704020879adc323736a9edffb131`
- 固定CAL: `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79`

## 機構・境界・表記

- gate adapterはcase-localなmodels viewへだけ接続し、split gainは親engineの一箇所で適用する。fit側にも同じ0.8をoffsetとして一度含めていた。通常順のsplit gate記録はPF_GATE 27回、PF_GATE_LENGTH 13回。
- raw再標本化はEntryFastSamplerを親として呼び、Map選択・engineのm/rare変換より前にある。支持外の語を足す経路はない。lawはimmutableで、semantic stateをraw再標本化内で変更しない。32回上限・最初のanchorへのfallback・空語・恒等設定の追加accept RNGなしを確認した。
- 通常順PF_GATE_LENGTHのraw介入は6,229回、親raw draw 20,904回、fallback 1回（0.0161%）。破棄枝・Map内候補・retryを含む母数であり、採用語数ではない。
- 学習表のstable22はmを保持する。各foldのPF学習末尾にmを含む例は14 / 2 / 13 / 13 / 14件。一方、補正対象はpre-m/pre-rareのraw語であり、同じ潜在表記だとは扱わない。raw draw、raw返却、Map等の後のrequest選択語、最終stable/visibleを[段階別集計](stages-and-scope.json)で区別した。母数は段階間で異なる。
- 今回の実生成では7+を跨ぐm変化は0例だった。追加の合成fixtureで複合glyphを1glyphと数え、stable 6 → visible 7で新しい閾値6を記録することを確認した。
- 対象構造PFは7末尾、そのうちatomで観測するFULLは6、END_ONLYは1。END_ONLYをatomへ追加していない。審判から観測されないPFにも各介入群でgate記録10回があり、生成を観測可否で切り替えていない。
- 植物前の切断とprev_terminalリセットを保存し、植物後はBODY。通常順の図後BODY tokenはBASE 27、PF_GATE 27、PF_GATE_LENGTH 25。後続の生成数が変わることは総効果に含まれる。
- F1LFのソース・法則・strict scope、既存2候補、LEN1、初期2候補argmax由来のmain RNG継続を維持した。採用stateとmain RNG源を混同していない。後続F1LFの生成内容・試行数まで群間で固定した比較ではない。
- proposal_idは破棄枝を含む共有採番を維持する。raw乱数消費・語数・採用state・後続side RNGへの波及を含む総効果であり、末語長だけの因果分離とは呼ばない。

## 効果についてまだ言えないこと

可視PFは6末尾・3葉のみ。葉等重みの7+比率は3群とも27.78%、平均可視glyph長はBASE/PF_GATE 6.11、PF_GATE_LENGTH 5.06だった。固定CALのJ24とPARA_ENDはこのsmokeでは各群2/3。これらから改善・同等性・長語不足の解消を判断しない。

法則はPFと通常LFの**幅条件付き**の比であり、現在の生成器と真正PFの残差へ直接合わせる方式ではない。smoke fold0の7+ gainは幅7–9で0.9599、10+で0.9754である。長語を一律に増やす実装ではなく、仕様違反ともいえない。後続比較では生の幅分布・短中長・SPACE・末字と各段階の通過率を併記し、今回の長語不足への改善方向を確認する必要がある。

## 本比較前の設計上の宿題 — 能力対照の順位方向

依頼008の背景として読んだ[設計007の能力対照](../../designs/007-pf-generation-v1/DESIGN.md#L172)には、参照分布の負log確率Dを小さくしたnearが、BASEより高いCALの真正らしさを得る、という期待順位がある。この方向は現審判からは保証されない。

[calibration.py](../../../../judges/v03/calibration.py#L79) のCALは真正null内の順位Fに対して `1 - 2*abs(F - 0.5)` を使う。中央で高く、両裾で低い。距離を小さくしても低距離側の裾へ進めばCALは下がる。さらに設計のDは単語の負log確率であり、審判の文書分布の記述量とも同一ではない。従ってnear > BASE > farを普遍的な合否基準にすると、正しく動く審判を能力不足と判定し得る。

これは今回実装された第一案の生成バグではないが、64枝replay・能力判定を実装する前に修正したい。生の特徴量・距離が意図どおり動く検査と、CALが真正nullの中央域／両裾を区別する検査を分け、期待方向を事前に定義する。評価対象の審判scoreを見て都合のよいdonorへ選び直さない。能力対照は未実装・未達成のままであり、この報告でもPASSを付けていない。

## 実行時間・次の受け渡し

今回新たに生成したのは36面。全foldのfitは追加生成を伴わない。通常順・逆順・恒等設定のprocess時間は約203.5 / 114.2 / 176.7秒、各最大RSSは約424–426 MiBだった。相互に並行しfitとも重なっているため、単独実行の速度比較や800面の予算保証に用いない。[計測記録](performance.json)を参照。

実装側への依頼はR1の修正と対応する負例追加。修正後、ソースが変わるため新planから必要な小規模再検証を行う。原版・審判を変更する必要は現時点で認めない。個別末字・SPACE study、新本比較、正式採用、main mergeは開始していない。

生生成物・正解キー・parent archiveはGitへ含めていない。ローカル実行rootは `/workspace/voynich-results/pf-generation-independent-20261105/`。[再現手順](REPRO.md)と[成果物manifest](MANIFEST.json)を参照。
