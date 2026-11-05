# 010: PF生成改善・第1比較の独立検証

状態: OPEN。ユーザーの「実装」に基づく `experiments/pf_generation/` を対象とします。[検証記録](../implementation/009-pf-generation-v1/VALIDATION.md)、[実装手順](../../../experiments/pf_generation/README.md)、[設計007](../designs/007-pf-generation-v1/DESIGN.md)を参照してください。依頼008の設計レビューは背景として併読し、まだ独立PASSが出たとは扱わないでください。

開始HEADを記録し、[実装manifest](../implementation/009-pf-generation-v1/MANIFEST.json)の各ファイルのサイズ・SHA-256を照合してください。原版・既存M1・審判は変更せず、新しい出力rootで以下を確認してください。

1. 新unit20件、M1の27件、審判56件を実行。
2. 新planを実際にfitし、外部16葉・外側test4葉除外・known3未使用、法則のhash・fold・sourceを確認。共有planや旧監査PASSをそのまま再利用しない。
3. A:2/A:3/G:1・seed91701で3群+REFERENCEを通常順/逆順に生成し、24面を監査。BASEと原版、反転結果、gateのsplit gain一回、raw再標本化の支持・上限・fallback、最終state/RNGを確認。
4. 別の `--identity` planで12面を生成し、全3群が原版の意味出力・最終state・main RNGに一致することを確認。
5. input/law/生成物+checksumの改変、旧PASS、失敗再監査後のseal、自己整合したREFERENCE RNG改変を拒否することを確認。負例scriptは他processが止まった後に使い、元bytesの復元と最後の正の監査を確認。
6. 固定CAL `61238cf467871ac13ab9374e2da23ae8a3ad215ea960029e6c8507e065efaf79` で9予測・2対比のsmokeへ接続。再学習・PROTO fallbackなし。全予測保存後に採点する。
7. RAW学習表/pre-m適用/最終visibleの表記差、proposal_idとside RNGの総効果、END_ONLYの非atom観測、PLANT後BODY、F1LF保存を確認。可能なら生成時間・最大RSSも測定する。

個別末字/SPACE、能力対照64枝replay、全20葉×10seedの新本比較、正式採用、main mergeはこの依頼に含めません。小規模検証から改善・同等性を宣言しません。

固定CALモデルだけ必要なら既存M1 v2公開bundle（新実装codeは本ブランチを使用）:

`https://raw.githubusercontent.com/Takashi-Izumo/Voynich_Generator/3e6ecc9ad61b13362369e4b1ea79f0ad12146be0/review-packages/m1-independent-review-20261105-v2.zip`

ZIP SHA-256: `3886b3ec756137e366b3e203b91e3076a198f681860d319d0247869ec669ead3`。

結果は `reports/010-pf-generation-check-<unique-id>/REVIEW.md` と小さい再現記録を追加し、通常のsandbox commit/pushで返してください。実装・status・過去の報告は直接変更せず、正解キー・生生成物・parent archiveをcommitしないでください。
