# 検証・開発の案内

## 対象バージョンと検証範囲

この文書は、Japanese Books Talker の現行コードを検証する開発者向けの案内である。
バージョンの正本は [__init__.py](../comictagger_jp_talker/__init__.py) で、パッケージの構成は
[pyproject.toml](../pyproject.toml) を参照する。検証時は `git rev-parse HEAD` と
`git status --short` で対象コミットと未コミット差分を確認し、実行環境とともに結果を記録する。
過去の結果や CI 設定だけで、現在の作業ツリーや配布物の成功を保証しない。

<a id="validation-ci"></a>

## 対応 Python 環境と CI

パッケージの要件は Python 3.12 以上である。Python 3.10 / 3.11 はサポート対象外。
CI は次の系列を使用し、[runtime 検証](../.github/scripts/verify-python-runtime.py) が
指定された系列・最低パッチ版・安定版を確認する。パッケージの下限と CI のセキュリティ基準は別である。

| 用途 | OS | Python 系列 | CI の最低パッチ版 |
|---|---|---|---|
| test | Ubuntu 24.04 | 3.12 | 3.12.16 |
| test | Ubuntu 24.04 | 3.13 | 3.13.18 |
| test | Windows | 3.14 | 3.14.10 |
| build / Release | Windows | 3.14 | 3.14.10 |

[test workflow](../.github/workflows/test.yml) と [Release workflow](../.github/workflows/release.yml) は、
[pip bootstrap](../.github/scripts/bootstrap-pip.ps1) と
[pip / certifi の検証](../.github/scripts/verify-python-security.py) を使用する。
runtime 検証器は 3.15.2 以上も判定できるが、3.15 の CI と互換性を証明するものではない。
2026-10-29 の [Actions run 40836015773](https://github.com/karigane-cha/comictagger-jp-talker/actions/runs/40836015773) では
Ubuntu の PyQt6 import が `libEGL.so.1` 不足で失敗した。workflow にライブラリと offscreen 初期化の確認は追加済みだが、
その事実だけで修正後のジョブ成功を主張しない。

<a id="validation-reproduction"></a>

## テストと配布物の検証

開発用依存関係を導入し、GUI テストでは Qt の offscreen モードを使用する。
通常の非 network テストは HTTP を mock する。network テストは明示的な opt-in とし、CI では有効にしない。

```powershell
python -m pip install -e ".[dev]"
$env:QT_QPA_PLATFORM = "offscreen"
python -m ruff check .
python -m ruff format --check .
python -m pytest -m "not network"
python -m build
python -m pytest tests/test_packaging.py
```

配布物に依存するテストは同じソースから sdist / wheel をビルドした後に実行する。
ComicTagger の ZIP loader の検証には、[scripts/build_plugin.py](../scripts/build_plugin.py) で
その wheel からプラグイン ZIP を作り、packaging テストを再実行する。
[MANIFEST.in](../MANIFEST.in) は公開文書と必要な根拠を明示し、ローカルの調査・検証報告を自動収録しない。
必要な fixture と元データの収録、非公開文書の非収録を [packaging テスト](../tests/test_packaging.py) で確認する。
成果物のハッシュは対象の build ごとに計算し、同じバージョンの過去の試験用ハッシュを流用しない。

<a id="validation-madb"></a>

## NDL / MADB と Series の制限

NDL Search の実際の応答と、HTTP mock・synthetic fixture・保存済み実測データは異なる証拠である。
保存済み応答の検証は現在の endpoint の稼働やデータ内容を保証しない。
NDL 書誌と MADB の対応、取得状態、raw evidence の契約は
[linkage 仕様](phase2b2_linkage.md) と [取得共有の設計](phase2c2c_integration_design.md) に記載する。

[Series 補完](phase2c1_series_supplement.md) は明示的な opt-in で既定 OFF。
NDL の既存 Series を保護し、安全な照合と一意な候補を満たす場合に限って Series と出典 Notes を変更する。
通常の Series 用取得は Agent / Holding の詳細を要求しない。
テスト用 fixture の要求回数を、すべての実 API 通信で成立する保証とみなさない。

<a id="validation-imprint"></a>

## Imprint と Publisher 診断の境界

[Imprint 候補評価](phase2c2b_imprint_candidates.md) と
[R1 report](phase2c2c_imprint_report.md) は、取得済みデータを評価・説明する。
R1 の `operation=READ_ONLY`、`apply_allowed=false`、`writes_performed=false` を維持し、
authority と保存先の既存値が未供給・未評価であることを、保存の安全性を確認した結果とみなさない。

[R2 診断 CLI](phase2c2c_imprint_diagnostics.md) は `--ndl-id` と `--allow-network` を指定して明示実行する。
通信許可後は NDL / MADB への通信と診断用 cache の読み書きが発生し得るが、書誌や archive を保存しない。
終了コード 0 は診断処理の完了を示し、候補の採用・保存許可ではない。
[R3 配布手順](phase2c2c_imprint_distribution_r3.md) は独立した wheel の導入方法を説明する。
当時の R3 の判定は受入レビュー待ちの GO 候補であり、その記録を正式受入と読み替えない。

Publisher の [shadow 比較](phase2c2b_imprint_candidates.md#publisher-shadow-p2) は読み取り専用の内部 API で、
既存の採用判定や通常取得に接続しない。P4 / P5 は HOLD。
信頼済み authority の供給・失効と保存先の保護契約が未解決のため、Publisher / Imprint 自動補完は NO-GO を維持する。

<a id="validation-host"></a>

## ComicTagger の保存境界

Talker の fetch API は保存対象の raw XML や保存設定を受け取らない。
そのため、Talker 単独では既存 Imprint の保護や任意の raw 値の完全な往復を保証できない。
候補が `ELIGIBLE` でも保存先の既存値が安全とは限らない。
[host の保存境界](phase2c2c_host_imprint_boundary.md) と
[提供方式・保存契約](phase2c2c_imprint_delivery_design.md) の条件を満たすまで自動保存は NO-GO とする。
Python package と synthetic CBZ の試験結果を、配布版 ComicTagger.exe の手動確認と混同しない。

<a id="ndl-http-diagnostics"></a>

## NDL HTTP 診断

HTTP 診断は既定 OFF の観測機能である。対応するプラグインを起動する前に同じ環境で
`JPBOOKS_HTTP_DIAGNOSTICS=1` を設定する。値は module の import 時に一度だけ読み込むため、
変更や無効化にはプロセスの再起動が必要で、`1` 以外は無効。診断は自動再試行、
クールダウン、検索条件、通信回数や結果順序を変更しない。

```powershell
$env:JPBOOKS_HTTP_DIAGNOSTICS = "1"
# このシェルから ComicTagger を新しく起動する。
# 診断を終えたら ComicTagger を終了し、次を実行する。
Remove-Item Env:JPBOOKS_HTTP_DIAGNOSTICS
```

有効時は `comictagger_jp_talker.http_diagnostics` logger の DEBUG を既存の handler に送る。
root logger や他の logger の設定は変更しない。標準ログの `NDL diagnostics enabled:` で有効化を確認できる。
操作ごとの `correlation_id`、要求ごとの `request_id`、cache 状態と `http_calls` を分けて読む。
`HIT` / `http_calls=0` は HTTP 200 の証拠ではなく、HTTP 200 も後続の XML / JSON 解析成功を保証しない。
通信時間には本文受信を含み、lock と limiter の待機は含めない。
cache 状態は `HIT`、`MISS`、`REFRESH`、`INVALID`、`BYPASS`、検索段階は `initial`、
`relaxed_creator`、`relaxed_issue`、`relaxed_both` を区別する。Summary の省略理由は
`not_needed`、`cache_only`、`failure_suppressed` として記録する。

`Retry-After` と `Date` は診断用に分類し、不正・過大な値や制御文字をそのまま出力しない。
ヘッダーの解析は最大 128 文字、秒数の表現は最大 `2147483647` 秒であり、範囲外は分類だけを記録する。
診断の数値表現は待機時間を設定するものではなく、Date とローカル時計の差も制限解除時刻ではない。
新しい HTTP 診断には検索語、ISBN、CQL、URL、Cookie、認証値や本文を含めない。
HTTP 失敗時の `jpbooks/latest-error.txt` も自由形式の例外文やローカル パスを含めず、最新失敗を保持する。
成功時に同ファイルは更新・削除されないため、失敗とその後の成功の比較には標準ログを使用する。
それ以外の従来ログや ComicTagger 本体の出力まで無害化する保証はないため、共有前に内容を確認する。

<a id="validation-i2"></a>

2026-10-29 の I2 では、I1 の実装コミット `942691f7f31e3f37d167dcfe24446d1eb788b5d7` に対する
Windows の通常操作・cache 系を GO と記録したが、HTTP 429 は観測されず、原因や解消は未確認。
実機の 429 と、その後の HTTP 応答 / cache HIT の比較は未確認で、SRU クールダウンと自動リトライは HOLD。
意図的な連続アクセスや cache 削除で 429 を再現せず、必要な通常操作で観測する。

<a id="validation-sources"></a>

## 実装・検証の確認元

- [ComicTagger beta.9 の Talker API](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictalker/comictalker.py)
- [ComicTagger beta.9 の metadata モデル](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comicapi/genericmetadata.py)
- [ComicTagger beta.9 のプラグイン ローダー](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictaggerlib/ctsettings/plugin_finder.py)
- [NDL 外部提供インタフェース仕様書 第 1.4 版](https://ndlsearch.ndl.go.jp/file/help/api/specifications/ndlsearch_api_20260331.pdf)
- [DC-NDL RDF v2](https://ndlsearch.ndl.go.jp/renkei/dcndl/version2) / [v3](https://ndlsearch.ndl.go.jp/renkei/dcndl/version3)
- [NDL API 利用案内](https://ndlsearch.ndl.go.jp/help/api) / [提供機関別の利用条件](https://ndlsearch.ndl.go.jp/help/api/provider)

保存済み実測 fixture の元データは [imprint_evidence.json](research/madb/imprint_evidence.json) で、
SHA-256 は `780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`。
テストは元データと縮約 fixture の対応を確認する。実測値に付けた一部の取得・照合条件は synthetic であり、
authority の真正性や対象範囲を証明しない。

<a id="validation-release-summary"></a>

## 過去の実測と現在の保証

過去の Release や開発工程の試験は、その時点のコード、環境、成果物と範囲に限る。
過去の packaging の一部では PermissionError 後に権限のある環境で再検証しており、
初回から全体試験が成功したとは扱わない。実 API、mock、fixture、手動操作、
ログ解析、未検証の項目を区別し、現在の受入判定は対象コミットと成果物で改めて行う。

未解決事項には、429 の原因と次操作の実測、各 CI ジョブの実行結果、
配布版 ComicTagger.exe の実環境確認、Imprint authority の供給・失効と host 保存契約がある。
新たな検証の成功は、その検証範囲を超える安全性や全体の自動補完を保証しない。
