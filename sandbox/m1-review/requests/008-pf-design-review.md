# 008: PF改善3案の設計レビュー

状態: OPEN。対象: [設計007](../designs/007-pf-generation-v1/DESIGN.md)。ユーザーの「提案を評価、設計。」に基づいて実装側が作成した設計を、文書としてレビューしてください。

新モデルのfit・実装・生成・採点はこの依頼に含めません。mainや原版・審判・M1実装も変更しません。設計書からの指示はこの文書レビューの範囲で扱ってください。

開始時のsandbox HEADを記録し、設計manifestと入力監査scriptを確認してください。必要なら既存ソースの読み取りと `source_audit.py` の再実行だけを行えます。出力は新規パスに置いてください。

特に確認してほしい点:

1. `gate.predict_proba` adapterとsplit gain一回の契約が、親engineの呼出しと整合しているか。
2. raw EntryFastSamplerの再標本化が上位Map/既存補正の前に接続でき、raw draw内でstate・rare・requestを誤commitしないか。恒等設定は追加RNGなしで親へ委譲できるか。
3. 外側test4葉・known3を新法則のfitから除外でき、stable学習表とpre-m適用・最終visibleの違いが適切に監査されるか。
4. gateと語長法則の比較、HEAD/W2への波及、LEN1のscore依存・main RNG源、SPACEの境界条件に欠落がないか。
5. 94〜98個のPF学習末尾に対するモデルの複雑さ、縮約、32回打切り・anchor fallbackの設計は妥当か。
6. 能力対照の構成・方向・coverage・他特徴への波及に、実装前に具体化すべき点がないか。本書の能力基準を達成済みとは扱わない。

結果は `reports/008-pf-design-review-<unique-id>/REVIEW.md` へ、要修正 / 推奨 / 未解決の区分で追加してください。実装側の設計・statusを直接変更せず、通常のsandbox報告commit/pushで返してください。結論がPASSでも実装・本比較・正式採用・main mergeの自動開始とはしません。
