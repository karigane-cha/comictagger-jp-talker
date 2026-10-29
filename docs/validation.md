# 検証記録

## 現在の状態

2026-10-29 時点。パッケージの版は **0.4.0**。I1 の実装コミットは `942691f7f31e3f37d167dcfe24446d1eb788b5d7`、対象ブランチは `feat/ndl-http-diagnostics-i1`。`main` には未マージである。この文書は現在の検証状況を要約し、工程ごとの実測、失敗、再現手順、判断と成果物のハッシュは [検証履歴](validation_history.md) に保持する。

- **I1 HTTP 診断強化は完了**。既定 OFF の観測専用実装、オフライン試験、隔離ビルド、SSH 署名付きコミットを確認済み。
- **I2 の Windows GUI 正常系・キャッシュ系は GO**。HTTP 429 は未発生で、**原因未特定・解消判断なし**。SRU クールダウンと自動リトライの追加は HOLD。
- **Imprint 自動補完は NO-GO**。候補の診断は実装済みだが、信頼できる authority の供給・失効運用と、host の既存値保護・保存契約は未解決。
- **Imprint 診断は READ_ONLY**。R1 report、R2 CLI、R3 の独立 Wheel 方式を実装・検証している。診断完了や候補の一致は保存許可ではない。
- **MADB Series 補完は opt-in / default OFF**。NDL 由来の既存 Series を無条件に上書きしない。
- Python パッケージの要件は **3.12 以上**。CI は Ubuntu 24.04 / 3.12・3.13 と Windows / 3.14 のテストを設定し、build / Release は Windows / 3.14 を使う。
- Windows / Python 3.14.10 の I1 ローカル検証と、Python 3.14 系の I2 GUI 実測を区別する。I2 ログは `PyInstaller: No` であり、Windows 配布版 ComicTagger.exe の確認ではない。**Qt ランタイム ライブラリ追加後の CI 実ジョブも未確認**。

根拠の種類は次のとおり。

| 種類 | この文書での扱い |
|---|---|
| 実装・設定から確認 | 現在のコード、package metadata、テストと workflow の内容。設定の存在は実行成功を意味しない |
| 実行・解析で確認 | ローカル検証、GUI 手動検証、保存済みログの解析を区別し、日時・環境・対象コードを記載する |
| 報告値 | 実行ログを直接確認できていない結果は、報告ベースであることと未確認の範囲を明記する |
| 未確認 | 実 GitHub Actions、対象の実機、実 API など、証拠がない実行は NOT RUN または未確認とする |
| 履歴 | 以前の工程・版・環境に限る結果。当時の失敗や旧判断を現在の成功に書き換えない |

## Python 対応・セキュリティ・CI

現在の [pyproject.toml](../pyproject.toml) は `requires-python = ">=3.12"`、Ruff の `target-version = "py312"`。Python 3.10 / 3.11 は本プロジェクトのサポート対象外であり、3.11 の除外はプロジェクト側の判断である。package metadata の下限だけでは、各系列の古いパッチ版を拒否できない。

| 用途 | OS | Python 系列 | CI の最低セキュリティ版 | 実ジョブ（修正前） |
|---|---|---|---|---|
| test | Ubuntu 24.04 | 3.12 | 3.12.16 | 失敗 |
| test | Ubuntu 24.04 | 3.13 | 3.13.18 | 失敗 |
| test | Windows | 3.14 | 3.14.10 | 成功 |
| build / Release | Windows | 3.14 | 3.14.10 | build はスキップ、Release は未確認 |

修正前の実ジョブでは Ubuntu 両系列の PyQt6 import が `libEGL.so.1` 不足で失敗した。Linux ジョブに `libegl1` / `libgl1` と offscreen 初期化確認を追加済みだが、修正後の成功は未確認。run と当時の件数は [CI 失敗記録](validation_history.md#文書統合時の補足検証と-ci-失敗記録2026-10-29-整理前) を参照する。

[test workflow](../.github/workflows/test.yml) は明示的な matrix を使い、[Release workflow](../.github/workflows/release.yml) は Windows / 3.14 を使用する。両 workflow と build ジョブは、`setup-python` の後、pip bootstrap と依存導入の前に [runtime 検証](../.github/scripts/verify-python-runtime.py) を実行する。期待系列の不一致、最低版未達、安定版以外を拒否する。検証器は 3.15.2 以上も扱うが、3.15 の CI や互換性は未検証。

[bootstrap](../.github/scripts/bootstrap-pip.ps1) は SHA-256 を指定して pip 26.2.2 を導入する。[セキュリティ検証](../.github/scripts/verify-python-security.py) は pip 26.2.2 以上と pip 同梱 certifi 2026.10.19 以上を確認し、`--require-certifi` を指定した test / Release では独立 certifi 2026.10.19 以上も検査する。build は依存不要の metadata 導入なので独立 certifi を必須にしない。Python の `ssl` と pip / requests の証明書束は別の対策領域であり、版の検査だけで runner や取得経路の真正性を保証しない。

詳細な更新理由と、3.13 追加前の設定・失敗経緯は [Python セキュリティ更新の履歴](validation_history.md#python-サポート方針2026-年-10-月セキュリティ更新)、その後の設定は [3.13 CI 追加の履歴](validation_history.md#ubuntu--python-313-の-ci-設定追加2026-10-28) にある。

## 最新のローカル検証結果

以下は **2026-10-29 の I1 実装時に実行済みの結果**。SSH / ED25519 の署名検証は I1 コミット確定時に PASS。[署名検証の記録と再検証手順](validation_history.md#実装と署名付きコミット) を参照する。

| I1 の検証対象 | Windows / Python 3.14.10 での結果 |
|---|---|
| 重点試験 | **248 passed**。新規診断 68、既存 NDL 60、error 7、その他 113 |
| ビルド後の非 network 全体 | **3,135 passed / 0 skipped / 13 deselected / 1 xfailed** |
| packaging | **12 passed**。I1 の隔離成果物を使用 |
| Ruff check / format、runtime / pip / certifi、`pip check` | **PASS** |
| 隔離ビルド・ZIP 読み込み | sdist / Wheel / plugin ZIP を生成。診断 ON/OFF と本体 1.6.0b9 の既存ログへの DEBUG 到達をオフラインで確認 |

I1 の対象 6 ファイル、観測専用の契約、mock と実通信の区別は [I1 詳細](validation_history.md#i1ndl-http-429-診断強化2026-10-29)、有効化・バックアップ・復元は [診断ガイド](ndl_http_diagnostics_i1.md) を参照する。2026-10-28 までの 241 / 3,062 / 28 件の結果と独立 CLI 0.3.0 の確認は [旧記録](validation_history.md#文書統合時の補足検証と-ci-失敗記録2026-10-29-整理前) に移した。各時点の件数・環境は I1 の値で置き換えない。

既知の `xfail` は ComicTagger 1.6.0b9 の CIX writer による整数 `Volume=0` の省略。`13 deselected` はネットワーク試験の除外であり、過去の `13 skipped` と混同しない。境界値の単体試験は、その Python パッチ版を起動した証拠ではない。

### Windows GUI 実測（I2）

2026-10-29 の Windows GUI 通常検索・書誌取得では、**30 操作すべて成功、実 HTTP 9 件すべて 200、21 操作で `http_calls=0`**。保存済みの 3 起動分のログ原本を読み取り専用で解析した結果であり、解析時の新規実通信は未実施。

診断有効化、ID、通信時間、cache HIT と実 HTTP の区別を確認した。HTTP 429 は 0 件で、Retry-After / Date と次操作の比較は未確認。環境、起動別集計、SRU / Summary の内訳、全応答時間と判定根拠は [I2 詳細](validation_history.md#i2windows-gui-実測2026-10-29) を正本とする。

## 配布物の検証

I1 の成果物はバージョン表記を **0.4.0** のまま維持した診断用ローカルビルドであり、正式公開済み v0.4.0 とは別物。[I1 の配布物記録](validation_history.md#i1ndl-http-429-診断強化2026-10-29) に SHA-256 と検証範囲を記載する。

[scripts/build_plugin.py](../scripts/build_plugin.py) は純粋 Python Wheel の metadata と entry point を検査して ZIP 名でコピーする。したがって、同じ実行で生成した Wheel と ZIP は同じ bytes となる。Wheel は独立診断用、ZIP は ComicTagger の plugin 用であり、導入先と動作環境を区別する。[導入手順](phase2c2c_imprint_distribution_r3.md) を参照。

[MANIFEST.in](../MANIFEST.in) は source tree に存在する検証文書を sdist に収録する。旧試験用 0.3.0 のハッシュと履歴未収録の確認は [当時の配布物記録](validation_history.md#文書統合時の補足検証と-ci-失敗記録2026-10-29-整理前) に移した。I1 のビルド時点には両検証文書を含むが、後から追記する I2 記録の収録を意味しない。

同じバージョンでも build 時点によって内容とハッシュは異なる。旧成果物の値を新しいビルドや公開物に流用しない。過去のハッシュは [R3 履歴](validation_history.md#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26) と [レビュー後の履歴](validation_history.md#phase-2c-2c-4r3レビュー後の文書改善cli-英語化2026-10-26) にも保持する。

## Imprint 診断 CLI（R1～R3）

現在の実装は [R1 report](phase2c2c_imprint_report.md)、[R2 CLI](phase2c2c_imprint_diagnostics.md)、[R3 配布ガイド](phase2c2c_imprint_distribution_r3.md) に分かれる。

- R1 は取得済み evidence から純粋な `imprint-report-v1` を構成する。`operation=READ_ONLY`、`apply_allowed=false`、`writes_performed=false`。authority と archive は未供給で、保存先の既存値は未評価。
- R2 は `python -m comictagger_jp_talker.imprint_diagnostics` を明示実行する。`--ndl-id` に一件を指定し、`--allow-network` を渡す。許可前は source / session / cache を生成しない。許可後は NDL / MADB 通信と診断用 cache の読み書きを行い得るが、書誌・archive の保存は行わない。出力は text または JSON。
- 終了コードは 0 が診断処理完了、2 が入力・許可不足、3 が取得失敗・不完全取得、4 が内部・出力等の失敗、130 が中断。HOLD / REJECT や exit 0 は候補の保存許可ではない。
- R3 は Wheel を独立 venv に導入して起動する方式。2026-10-26 の記録は **GO 候補・受入レビュー未完了**であり、正式受入や当時の成果物の公開を意味しない。

2026-10-23～27 の詳細件数は履歴を正本とする。当時の Python 3.12.14 は現在のセキュリティ最低版を満たさない。[R1 履歴](validation_history.md#phase-2c-2c-4r1純粋-imprint-診断-report2026-10-23)、[R2 履歴](validation_history.md#phase-2c-2c-4r2明示実行の読み取り専用-imprint-診断-cli2026-10-23)、[R3 履歴](validation_history.md#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26)、[レビュー後の履歴](validation_history.md#phase-2c-2c-4r3レビュー後の文書改善cli-英語化2026-10-26) に初回失敗・PermissionError・権限付き再実行も保持し、後続の成功で置き換えない。

2026-10-26 の実 endpoint の保存済み JSON を検査した記録では、NDL 書誌 `R100000002-I023440575` は `M381096` / `C334830` に strong match した一方、Imprint 評価は **REJECT** だった。publisher 表記差による conflict は、誤拒否と断定していない。trace の重複表示を独立した HTTP 要求数とみなさない。詳細は [R3 実測](validation_history.md#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26) を参照。

## MADB 取得・Series 補完の検証

現在の `talker.py` と `metadata_supplement.py` は設定 `jpbooks_madb_series_supplement` を既定 False とし、選択した書誌の最終取得時に限って必要な MADB 取得を行う。`series_supplement_policy.py` は、空白除去後に NDL Series が残る場合はその値を維持する。補完は一致が安全で候補と表示値が一意な場合に限り、変更対象は Series と出典 Notes。任意の Imprint を補完する経路ではない。

取得・照合の共有基盤は取得状態・trace・raw evidence を保持し、Series 用に Book / Series を取得する。Agent / Holding の詳細は通常の Series 用取得では要求しない。試験用 fixture の cold / warm 要求数を、すべての実 API 呼出の保証とみなさない。

Phase 2C-1 では実 API の Series 比較と、synthetic fixture / HTTP mock による補完・fail-open・軽量取得の cold **6 → 3** / warm **0** を区別して検証した。安全な欠損条件を満たす実 API での end-to-end 補完成功例は未確認。[当時の記録](validation_history.md#v030-release-前の再検証) と [Imprint 候補評価の履歴](validation_history.md#phase-2c-2b-imprint-候補評価-api-の検証) に固有の結果を保持し、取得共有 A / B / C の詳細件数も下記の履歴へ集約する。

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

- HTTP 429 の原因・アクセス制限条件は未特定。I2 で 429 がなかったことは解消の証拠ではない。429 応答の Retry-After / Date と、次の明示操作の HTTP 200 / cache HIT の比較は未確認。
- Qt ランタイム ライブラリ追加後の Ubuntu / 3.12・3.13 での GUI と全体回帰、および Windows / 3.14 の Actions build / Release は未確認。
- Windows 配布版 ComicTagger.exe の同梱 Python の実パッチと更新状態、実画面での ZIP と独立診断の共存は未確認。独立 venv を更新しても host の Python は更新されない。
- Imprint authority の真正性・独立性・対象範囲・失効と、host の既存値保護・条件付き保存・検証が未解決。自動補完の NO-GO は維持する。
- 診断は全 evidence を出力するため、大量の候補でメモリと出力が増え得る。source constructor 内の部分初期化や close の制限は [R2 の制限](phase2c2c_imprint_diagnostics.md#6-resource-close-と中断) を参照。
- 実 API の応答、HTTP mock、synthetic fixture、保存済みログの解析、実行ログ未確認の報告値は異なる証拠であり、確認範囲を超えて一般化しない。

## 次の受入条件

1. I1 の実装と I2 の実測記録を独立したコミットとして管理し、両工程の検証結果を確認したうえで `main` への統合を判断する。
2. GitHub Actions の実ジョブで表の全系列と Windows build / Release を確認する。未実行のまま PASS としない。
3. 正式配布時は対象 version・内容・host を確認し、最終成果物のハッシュを build 後に外部で記録する。同一 version の過去の試験用ハッシュを流用しない。
4. 実 ComicTagger.exe での共存と、必要に応じた実 API の確認を独立して記録する。Imprint 自動補完は authority と host 保存契約の別途受入まで NO-GO。
5. 追加の接続確認・キャッシュ削除・意図的な 429 再現を行わず、必要な通常利用で継続観測する。429 が発生した場合だけ次の明示操作と比較し、クールダウン・自動リトライの採否を別工程で判断する。

## 詳細な検証履歴

[validation_history.md](validation_history.md) は既存の原文アーカイブに、文書統合時の補足記録と I1 / I2 の詳細を追記した履歴である。各版の pytest 件数、初回失敗、PermissionError、実 API・fixture の区別、再現コマンド、SHA-256 と検証対象コミットを保持する。古い CI 構成や未実施判定は、その記録時点の事実として読む。
