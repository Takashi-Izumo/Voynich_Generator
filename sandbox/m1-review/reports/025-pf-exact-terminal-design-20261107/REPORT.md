# 第二案の設計・実装受け渡し

2026-11-07 日本時間。**設計完了。第二案の実装・生成・審判予測は未開始。**

第二案を、BASE/PF_E_HALF/PF_E_ZEROの個別末字係数1.0/0.5/0.0の比較として具体化した。幅・末字族・原版LEN1を保持し、第一案のgate/語長lawを混ぜない。BASEを維持する。

- [設計正本](DESIGN.md): 数式、適用範囲、元LEN1、state/RNG、独立package、監査、能力対照、機構検証と本比較。
- [実装受け渡し](IMPLEMENTATION_HANDOFF.md): split監査修正、対照、score adapter、独立80面検証、その後の本比較planの順序と返却物。
- [JSON契約](DESIGN_CONTRACT.json): 固定値、母数、開始gate、現時点の未達状態。
- [読取専用ソース監査](SOURCE_AUDIT.json)と[再現コード](source_audit.py): 5つの凍結18葉core、345算術照合、35構造PFのgeometry、欠番scheduleの監査不整合。
- [設計整合確認](VERIFICATION.json)、[成果物hash](MANIFEST.json)。

5 foldすべてで元PF係数はE=nがE=yより高いことを確認した。原因を断定せず、成分を切り分けて試す。pre-m stable末字と可視末字は分ける。最初の適格LEN1救済が初期winnerより低scoreでも採用される挙動、採用stateと初期winner RNGの別commitも仕様化した。

本比較には、未修正のsplit製品監査の独立確認と、同族内の個別末字を変える新対照での対象channel能力確認が必要。前回の補助監査経路や未達対照をPASSとして継承しない。今後の機構検証80面、本比較800面/600組は予定件数であり、今回実行していない。

今回の変更は本報告ディレクトリへの追記のみ。製品・原版・審判・status/request・既存報告は編集していない。新fit、生成、donor replay、審判予測、正解付き採点は各0。
