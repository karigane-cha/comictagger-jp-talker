# 検証記録

## 現在の状態

2026-10-29 時点の作業ツリーを基準とする。パッケージの版は **0.4.0**。この文書は、現在の実装・設定と、記録された過去の実測を区別してまとめる。工程ごとの実測、失敗、再現手順、当時の判断と成果物のハッシュは [検証履歴](validation_history.md) に原文のまま保持している。

- **Imprint 自動補完は NO-GO**。候補の診断は実装済みだが、信頼できる authority の供給・失効運用と、host の既存値保護・保存契約は未解決。
- **Imprint 診断は READ_ONLY**。R1 report、R2 CLI、R3 の独立 Wheel 方式を実装・検証している。診断完了や候補の一致は保存許可ではない。
- **MADB Series 補完は opt-in / default OFF**。NDL 由来の既存 Series を無条件に上書きしない。
- Python パッケージの要件は **3.12 以上**。CI は Ubuntu 24.04 / 3.12・3.13 と Windows / 3.14 のテストを設定し、build / Release は Windows / 3.14 を使う。
- Windows / Python 3.14.10 のローカル実測は記録済み。**現在の構成での GitHub Actions 実ジョブは NOT RUN**。Ubuntu / 3.13.18 以上の実行と Windows 配布版 ComicTagger.exe の実画面操作も未確認。

根拠の種類は次のとおり。

| 種類 | この文書での扱い |
|---|---|
| 実装・設定から確認 | 現在のコード、package metadata、テストと workflow の内容。設定の存在は実行成功を意味しない |
| ローカル実測・ユーザー報告 | 日時・環境・コード状態とともに記載する。ユーザー提供の実測はその旨を明記する |
| 未確認 | 実 GitHub Actions、対象の実機、実 API など、証拠がない実行は NOT RUN または未確認とする |
| 履歴 | 以前の工程・版・環境に限る結果。当時の失敗や旧判断を現在の成功に書き換えない |

## Python 対応・セキュリティ・CI

現在の [pyproject.toml](../pyproject.toml) は `requires-python = ">=3.12"`、Ruff の `target-version = "py312"`。Python 3.10 / 3.11 は本プロジェクトのサポート対象外であり、3.11 の除外はプロジェクト側の判断である。package metadata の下限だけでは、各系列の古いパッチ版を拒否できない。

| 用途 | OS | Python 系列 | CI の最低セキュリティ版 | 実ジョブ |
|---|---|---|---|---|
| test | Ubuntu 24.04 | 3.12 | 3.12.16 | NOT RUN |
| test | Ubuntu 24.04 | 3.13 | 3.13.18 | NOT RUN |
| test | Windows | 3.14 | 3.14.10 | NOT RUN |
| build / Release | Windows | 3.14 | 3.14.10 | NOT RUN |

[test workflow](../.github/workflows/test.yml) は明示的な matrix を使い、[Release workflow](../.github/workflows/release.yml) は Windows / 3.14 を使用する。両 workflow と build ジョブは、`setup-python` の後、pip bootstrap と依存導入の前に [runtime 検証](../.github/scripts/verify-python-runtime.py) を実行する。期待系列の不一致、最低版未達、安定版以外を拒否する。検証器は 3.15.2 以上も扱うが、3.15 の CI や互換性は未検証。

[bootstrap](../.github/scripts/bootstrap-pip.ps1) は SHA-256 を指定して pip 26.2.2 を導入する。[セキュリティ検証](../.github/scripts/verify-python-security.py) は pip 26.2.2 以上と pip 同梱 certifi 2026.10.19 以上を確認し、`--require-certifi` を指定した test / Release では独立 certifi 2026.10.19 以上も検査する。build は依存不要の metadata 導入なので独立 certifi を必須にしない。Python の `ssl` と pip / requests の証明書束は別の対策領域であり、版の検査だけで runner や取得経路の真正性を保証しない。

詳細な更新理由と、3.13 追加前の設定・失敗経緯は [Python セキュリティ更新の履歴](validation_history.md#python-サポート方針2026-年-10-月セキュリティ更新)、その後の設定は [3.13 CI 追加の履歴](validation_history.md#ubuntu--python-313-の-ci-設定追加2026-10-28) にある。

## 最新のローカル検証結果

以下は **2026-10-28 の Python 3.13 CI 追加時までに記録された結果**であり、後続の文書統合作業で新たに全体試験を行ったという意味ではない。

| 時点・環境 | 検証と結果 | 根拠・範囲 |
|---|---|---|
| 3.13 CI 追加前、Windows / Python 3.14.10 | 関連 pytest **241 passed** | ユーザー報告。整理案では runtime / packaging / diagnostics とされるが、対象内訳の裏付けは未確認 |
| 同上 | 非 network 全体 **3,062 passed / 13 deselected / 1 xfailed**、Ruff check / format 成功 | ユーザー報告。上記の関連試験とは別で、実ジョブではない |
| 同上 | 隔離 build で sdist / Wheel を生成し、`scripts/build_plugin.py` で plugin ZIP を作成。Wheel の `Requires-Python >=3.12`、独立 venv への導入と CLI `--help` / `--version` 成功 | ユーザー報告。Wheel と ZIP の bytes / SHA-256 は一致 |
| 3.13 CI 追加後、Windows / Python 3.14.10 | runtime / matrix テスト **28 passed**、Ruff check / format と test workflow の actionlint 成功 | ローカル記録。全体 pytest と配布物は再実行していない |
| 3.13 CI 追加後、Windows / Python 3.12.14 | 同じ runtime / matrix テスト **28 passed** と Ruff 成功 | 補助確認。3.12.16 未満のためセキュリティ受入ではない |
| 3.13 CI 追加前、Windows / Python 3.12.14 | 非 network 全体 **3,062 passed / 13 deselected / 1 xfailed** | 別環境での旧記録。上記 3.14.10 の報告とは別の実測 |

2026-10-28 の後続の文書統合作業で、Windows / Python 3.14.10 の既存セキュリティ用 venv を再確認した。runtime の検証、pip **26.2.2**、pip 同梱 certifi **2026.10.19**、独立 certifi **2026.10.23** の検査と `pip check` は成功。整理案にも当時の `pip check` 成功という記述はあるが、その過去の実行ログは確認できていない。

同じ文書統合作業で、既存の独立診断用 venv をリポジトリ外から `-I` で起動し、Python 3.14.10 と `site-packages` からの import、CLI の `--help` および `--version` **0.3.0** を確認した。導入記録の Wheel ハッシュは下表の旧試験用 Wheel と一致する。これは文書統合後に新規 build する Wheel の起動結果ではない。

3.13.17 / 3.13.18 / 3.13.19 の境界値テストは version 判定の単体試験であり、Python 3.13.18 を実際に起動した証拠ではない。既知の `xfail` は ComicTagger 1.6.0b9 の CIX writer による整数 `Volume=0` の省略。`13 deselected` はネットワーク試験の除外であり、過去の `13 skipped` と混同しない。

3.14.9 の旧環境が起動できなかったこと、当初の 3.14.10 未実施判定、および sandbox 内の権限問題は [履歴](validation_history.md#python-サポート方針2026-年-10-月セキュリティ更新) と [後続の確認](validation_history.md#ubuntu--python-313-の-ci-設定追加2026-10-28) に残している。

## 配布物の検証

2026-10-28 にローカルで生成された **試験用**成果物の SHA-256 は以下のとおり。公開 Release の成果物のハッシュではない。今回、保存済みの 3 ファイルを読み取り、これらの値と一致することを確認した。

| 成果物 | SHA-256 |
|---|---|
| `comictagger_jp_talker-0.3.0.tar.gz` | `626d9c3701d765ea43619e1a086552f33b416f17c5b705ca4bc0bfe814d55579` |
| `comictagger_jp_talker-0.3.0-py3-none-any.whl` | `49657a48922eb6b8fa95ca30015fcd6d3d2b05910fb60b28996525908bdf0cc6` |
| `jpbooks_talker-plugin-0.3.0.zip` | `49657a48922eb6b8fa95ca30015fcd6d3d2b05910fb60b28996525908bdf0cc6` |

[scripts/build_plugin.py](../scripts/build_plugin.py) は純粋 Python Wheel の metadata と entry point を検査して ZIP 名でコピーする。したがって、同じ実行で生成した Wheel と ZIP は同じ bytes となる。Wheel は独立診断用、ZIP は ComicTagger の plugin 用であり、導入先と動作環境を区別する。[導入手順](phase2c2c_imprint_distribution_r3.md) を参照。

[MANIFEST.in](../MANIFEST.in) の `recursive-include docs *.md` は source tree に存在する両方の検証文書を sdist に収録する設定である。保存済みの上記 sdist を調べたところ、旧 `validation.md` は含まれるが、`validation_history.md` と整理案は含まれない。今後の sdist に履歴を含めるには、その build の source tree に履歴ファイルが必要であり、GitHub Actions では checkout 対象になっている必要がある。

同じ 0.3.0 でも build 時点によって内容は異なる。文書編集後に build した sdist や将来の公開成果物に、上表のハッシュを流用しない。2026-10-26 と 10-27 の異なる試験用ハッシュも [R3 履歴](validation_history.md#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26) と [レビュー後の履歴](validation_history.md#phase-2c-2c-4r3レビュー後の文書改善cli-英語化2026-10-26) に保持している。

## Imprint 診断 CLI（R1～R3）

現在の実装は [R1 report](phase2c2c_imprint_report.md)、[R2 CLI](phase2c2c_imprint_diagnostics.md)、[R3 配布ガイド](phase2c2c_imprint_distribution_r3.md) に分かれる。

- R1 は取得済み evidence から純粋な `imprint-report-v1` を構成する。`operation=READ_ONLY`、`apply_allowed=false`、`writes_performed=false`。authority と archive は未供給で、保存先の既存値は未評価。
- R2 は `python -m comictagger_jp_talker.imprint_diagnostics` を明示実行する。`--ndl-id` に一件を指定し、`--allow-network` を渡す。許可前は source / session / cache を生成しない。許可後は NDL / MADB 通信と診断用 cache の読み書きを行い得るが、書誌・archive の保存は行わない。出力は text または JSON。
- 終了コードは 0 が診断処理完了、2 が入力・許可不足、3 が取得失敗・不完全取得、4 が内部・出力等の失敗、130 が中断。HOLD / REJECT や exit 0 は候補の保存許可ではない。
- R3 は Wheel を独立 venv に導入して起動する方式。2026-10-26 の記録は **GO 候補・ユーザー レビュー待ち**であり、正式受入や当時の成果物の公開を意味しない。

| 当時の工程・環境 | 代表的な結果 |
|---|---|
| R1、2026-10-23 / Python 3.12.14 | 専用 **208 passed**、全体 **2,825 passed / 13 skipped / 1 xfailed**。純粋 report と保存不可の境界を検証し R1 は GO |
| R2、2026-10-23 / Python 3.12.14 | R1 と合わせて **399 passed**、全体 **3,024 passed / 13 skipped / 1 xfailed**。Ruff、sdist / Wheel / ZIP build と packaging **12 passed**。R2 は GO |
| R3、2026-10-26 / Python 3.12.14 | 独立 venv で **29 subprocess**、全体 **3,024 passed / 13 skipped / 1 xfailed**。開発環境の beta.9 loader と独立 venv の依存は別に確認 |
| R3 のレビュー後、2026-10-27 | 全体 **3,039 passed / 13 skipped / 1 xfailed**。前後の CLI 出力比較と PowerShell 手順を検証 |

これらの 3.12.14 実測は現在のセキュリティ最低版を満たさない。R1 / R2 の初回の試験失敗、sandbox の PermissionError と権限付き再実行は [R1 履歴](validation_history.md#phase-2c-2c-4r1純粋-imprint-診断-report2026-10-23) と [R2 履歴](validation_history.md#phase-2c-2c-4r2明示実行の読み取り専用-imprint-診断-cli2026-10-23) にあり、後続の成功によって消えたものではない。

ユーザーが提供した実 endpoint の保存ログでは、NDL 書誌 `R100000002-I023440575` は `M381096` / `C334830` に strong match した一方、Imprint 評価は **REJECT** だった。保存済み JSON の検査による記録であり、この文書整理で実 API を再取得した結果ではない。publisher 表記差による conflict は、誤拒否と断定していない。trace の重複表示を独立した HTTP 要求数とみなさない。詳細は [R3 実測](validation_history.md#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26) を参照。

## MADB 取得・Series 補完の検証

現在の `talker.py` と `metadata_supplement.py` は設定 `jpbooks_madb_series_supplement` を既定 False とし、選択した書誌の最終取得時に限って必要な MADB 取得を行う。`series_supplement_policy.py` は、空白除去後に NDL Series が残る場合はその値を維持する。補完は一致が安全で候補と表示値が一意な場合に限り、変更対象は Series と出典 Notes。任意の Imprint を補完する経路ではない。

取得・照合の共有基盤は取得状態・trace・raw evidence を保持し、Series 用に Book / Series を取得する。Agent / Holding の詳細は通常の Series 用取得では要求しない。試験用 fixture の cold / warm 要求数を、すべての実 API 呼出の保証とみなさない。

| 証拠と工程 | 記録された結果 |
|---|---|
| 実 API、Phase 2C-1 | `M381096` / `C334830` の Series 比較は BOTH_AGREE。2026-10-05 の network suite は **13 passed / 1,377 deselected** |
| synthetic fixture / HTTP mock、Phase 2C-1 | NDL Series 欠損時の補完成功、fail-open、軽量取得の cold **6 → 3** / warm **0** を検証。安全な欠損条件を満たす実 API での end-to-end 補完成功例は未確認 |
| 実測を縮約した fixture と synthetic 条件、Phase 2C-2B | Imprint 候補評価 **235 passed**。真正な独立 authority を合成した場合の ELIGIBLE と、証拠不足時の HOLD を区別 |
| 取得共有 A / B / C、2026-10-20 | 専用 A **58 passed**、B の関連 **740 passed / 2 skipped**、C 専用 **163 passed**・関連 **871 passed / 2 skipped** |

A / B / C の各全体試験には sdist 読取時の **PermissionError 1 件**があり、権限のある環境で packaging を別途再実行した。全体試験が当初から成功したと扱わない。状態・通信数・経緯の詳細は [工程 A](validation_history.md#phase-2c-2c-2a-madb-取得状態モデルと構造化取得台帳)、[工程 B](validation_history.md#phase-2c-2c-2b共通-linkage-core-と取得済み-snapshot2026-10-20)、[工程 C](validation_history.md#phase-2c-2c-2c既存-series-補完の共通取得入口への移行2026-10-20) を参照。

## ComicTagger host 保存境界

2026-10-20 の E0 / E1 は、ComicTagger **Python package 1.6.0b9**、comicinfoxml 0.5.1、synthetic CBZ、実装コードと offscreen GUI 等を用いた試験であり、配布済み ComicTagger.exe の手動操作ではない。

- Talker の fetch API には保存対象の raw XML や保存設定が渡らず、既存 Imprint の安全な保護を単独で保証できない。通常の OVERLAY や空白値の扱いにも制約がある。
- E0 の保存境界試験は **592 passed**。任意の raw 値の完全な往復や既存値の保護は NO-GO。E1 の追加契約試験は **6 passed**。
- 両工程の全体試験には sdist 読取の PermissionError があり、packaging は別権限で確認した。詳しい反例と保存条件は [E0](validation_history.md#phase-2c-2c-3e0comictagger-の-imprint-保存境界2026-10-20) と [E1](validation_history.md#phase-2c-2c-3e1imprint-提供方式と-host-保存契約2026-10-20) を参照。

## 過去のリリース・開発工程の要約

| 時点 | 対象と代表的な検証 |
|---|---|
| v0.3.0、2026-10-05 | Phase 2C-1 の最終監査。非 network **1,375 passed / 1 skipped / 13 deselected / 1 xfailed**、実 API の試験は上記のとおり。[当時の記録](validation_history.md#v030-release-前の再検証) |
| v0.2.1、2026-09-27 | NDL / MADB の linkage と Series 比較。非 network **1,230 passed / 12 deselected / 1 xfailed**。[当時の記録](validation_history.md#v021-release-前の再検証) |
| v0.2.0、2026-09-27 | MADB read-only source。非 network **1,151 passed / 10 deselected / 1 xfailed**。[当時の記録](validation_history.md#020-の検証) |
| v0.1.x | NDL Talker、検索・日付・Series・ComicInfo、GUI / ZIP を段階的に検証。[初回以降の履歴](validation_history.md#010-の初回検証) |

これらの値は各時点の環境・成果物に対するものであり、現在のセキュリティ受入や新しい CI の成功を示さない。

## 既知の制約・未解決事項

- Ubuntu / 3.12.16 以上・3.13.18 以上の実 runner で、PowerShell bootstrap、依存導入、PyICU / GUI、全体回帰は未確認。Windows / 3.14 の現在の Actions build / Release も未確認。
- Windows 配布版 ComicTagger.exe の同梱 Python の実パッチと更新状態、実画面での ZIP と独立診断の共存は未確認。独立 venv を更新しても host の Python は更新されない。
- Imprint authority の真正性・独立性・対象範囲・失効と、host の既存値保護・条件付き保存・検証が未解決。自動補完の NO-GO は維持する。
- 診断は全 evidence を出力するため、大量の候補でメモリと出力が増え得る。source constructor 内の部分初期化や close の制限は [R2 の制限](phase2c2c_imprint_diagnostics.md#6-resource-close-と中断) を参照。
- 実 API の応答、HTTP mock、synthetic fixture、ユーザー提供ログは異なる証拠であり、実行した範囲を超えて一般化しない。

## 次の受入条件

1. 未追跡ファイルを含む変更をレビューし、履歴文書が配布対象の source tree に含まれる状態にする。
2. GitHub Actions の実ジョブで表の全系列と Windows build / Release を確認する。未実行のまま PASS としない。
3. 正式配布時は対象 version・内容・host を確認し、最終成果物のハッシュを build 後に外部で記録する。同一 version の過去の試験用ハッシュを流用しない。
4. 実 ComicTagger.exe での共存と、必要に応じた実 API の確認を独立して記録する。Imprint 自動補完は authority と host 保存契約の別途受入まで NO-GO。

## 詳細な検証履歴

[validation_history.md](validation_history.md) は整理開始時の `validation.md` の全文を保持した原文アーカイブである。各版の pytest 件数、初回失敗、PermissionError、実 API・fixture の区別、再現コマンド、過去の SHA-256 と Git / Release 操作の当時の記録を参照できる。アーカイブ内の古い CI 構成や未実施判定は、その記録時点の事実として読む。
