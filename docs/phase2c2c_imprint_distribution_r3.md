# Phase 2C-2C-4R3：Wheel / python -m による診断の導入と利用

2026-10-26。採用する方式は既存 Wheel を専用 Python 仮想環境へ導入し、
`python -m comictagger_jp_talker.imprint_diagnostics` で独立実行する方式。
R3 の正式受入・公開はユーザー レビュー待ち。検証の詳細と暫定判定は
[検証履歴の R3 記録](validation_history.md#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26) を参照する。

## 1. 二つの配布物と必要環境

| 配布物 | 用途・導入先 |
|---|---|
| `jpbooks_talker-plugin-0.4.0.zip` | ComicTagger beta9 の plugins フォルダー。通常の NDL 検索・書誌取得・既存 Series 補完 |
| `comictagger_jp_talker-0.4.0-py3-none-any.whl` | 専用 Python 仮想環境へ pip で導入。読み取り専用 Imprint 診断 |

診断 CLI に ComicTagger.exe は不要。依存する **Python package の comictagger** は pip が導入する。
一方、通常の ComicTagger 利用に診断用 Wheel のインストールは必須ではない。
ZIP 内に診断 module が存在しても、ComicTagger.exe 内から起動できることを保証しない。
独立 exe、専用 console_scripts、pipx 専用導入、pyz、GUI メニューは追加しない。

- 現在の package metadata の Python 要件は **3.12 以上**。従来の 3.10 / 3.11 からの互換性変更である。
  R3 の独立導入実測は **3.12.14** だが、今回のセキュリティ最低版を満たさない過去の記録である。
  全 Python バージョンでの動作を実測した意味ではない。
- 3.12 系は 3.12.16 以上、3.13 系は 3.13.18 以上、3.14 系は 3.14.10 以上、
  3.15 系は 3.15.2 以上の安定版が必要。Windows では Python 3.14.10 以上の 3.14 系を推奨する。
  `Requires-Python` はパッチ版を検査しない。ComicTagger 同梱 Python と独立診断用 Python は別環境になり得る。
- CI のテストには Ubuntu 24.04 / Python 3.12・3.13 と Windows / Python 3.14 を設定する。
  build / Release は Windows / Python 3.14。新しい CI 構成の GitHub Actions での実行は未確認。
- 依存指定は `requests>=2.28,<3` と `comictagger>=1.6.0b9,<1.7`。依存解決には通常 package 配布元への接続が必要。
  診断用の導入に GUI / CIX extras は必要ない。
- Windows では Python の venv と **PowerShell 7** を推奨。

## 2. Wheel を導入する

配布者がレビュー済み Wheel を提供したら、例えばプロジェクトの
[GitHub Releases 一覧](https://github.com/karigane-cha/comictagger-jp-talker/releases) で
対象版の添付 `.whl` と案内された SHA-256 を確認する。
**この R3 では Release を作成・公開していない。0.3.0 の Wheel が公開済みとは主張しない。**
以下の 0.4.0 の例も準備中の版を示すものであり、公開済みを意味しない。
添付がなければ公開済み URL を推測せず、配布者から受け取るか、開発者向けの build 手順で生成する。

以下は手元の Wheel を使う例。`$wheel` を実際に取得したファイルへ変更する。
`py -3.14` は推奨系列の例で、Python が別の場所ならその実行ファイルを指定する。
事前に [Python 3.14.10 の公式配布ページ](https://www.python.org/downloads/release/python-31410/) から
修正版を導入し、以下の確認を通過してからネットワーク経由で依存関係を導入する。
開発リポジトリや ComicTagger の Python 環境に依存させない。

```powershell
$wheel = (Resolve-Path -Path "$HOME\Downloads\comictagger_jp_talker-0.4.0-py3-none-any.whl" -ErrorAction Stop).Path
Get-FileHash -Algorithm SHA256 $wheel
$venv = Join-Path $HOME 'jpbooks-diagnostics-venv'
if (Test-Path $venv) { throw '既存環境を上書きしないため、別の venv 名を指定してください。' }
$pythonCheck = @'
import sys
print(sys.version)
if sys.version_info[:2] != (3, 14) or sys.version_info.micro < 10 or sys.version_info.releaselevel != "final":
    raise SystemExit("Python 3.14.10 or later, final 3.14 release required")
'@
py -3.14 -c $pythonCheck
if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 のセキュリティ最低版を満たしていません。' }
py -3.14 -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'Python 仮想環境の作成に失敗しました。' }
$python = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw '仮想環境内に python.exe が見つかりません。' }
& $python -c $pythonCheck
if ($LASTEXITCODE -ne 0) { throw '仮想環境の Python がセキュリティ最低版を満たしていません。' }
& $python -m pip install --upgrade 'pip>=26.2.2' 'certifi>=2026.10.19'
if ($LASTEXITCODE -ne 0) { throw 'pip / certifi の更新に失敗しました。' }
& $python -m pip install $wheel
if ($LASTEXITCODE -ne 0) { throw 'Wheel の導入に失敗しました。' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Python の依存関係に問題があります。' }
& $python -X utf8 -m comictagger_jp_talker.imprint_diagnostics --help
if ($LASTEXITCODE -ne 0) { throw '診断 CLI のヘルプ表示に失敗しました。' }
& $python -X utf8 -m comictagger_jp_talker.imprint_diagnostics --version
if ($LASTEXITCODE -ne 0) { throw '診断 CLI のバージョン確認に失敗しました。' }
```

この例の version の期待値は `0.4.0`。環境の activate は不要で、毎回 `$python` を指定すると導入先の取り違えを避けられる。
別の PowerShell を開いた場合は `$venv` と `$python` を再設定する。
独立性の追加確認には以下を使用できる。`-I` は正式な起動必須条件ではない。

```powershell
& $python -I -X utf8 -c "import sys, comictagger_jp_talker; print(sys.executable); print(comictagger_jp_talker.__file__)"
& $python -I -X utf8 -m comictagger_jp_talker.imprint_diagnostics --help
if ($LASTEXITCODE -ne 0) { throw '診断 CLI の隔離モードでのヘルプ表示に失敗しました。' }
```

import 元は専用 venv の `Lib\site-packages\comictagger_jp_talker` であることを確認する。
リポジトリ直下以外のディレクトリから起動できる。PYTHONPATH や editable install は不要。

### 更新とアンインストール

新しい Wheel を取得し、同じ `$python` で更新する。版と hash を確認してから行う。

```powershell
& $python -m pip install --upgrade 'C:\Downloads\comictagger_jp_talker-次の版-py3-none-any.whl'
if ($LASTEXITCODE -ne 0) { throw 'Wheel の更新に失敗しました。' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Python の依存関係に問題があります。' }
& $python -X utf8 -m comictagger_jp_talker.imprint_diagnostics --version
if ($LASTEXITCODE -ne 0) { throw '診断 CLI のバージョン確認に失敗しました。' }
```

同一 version の検証用 Wheel を入れ替える場合は pip が導入済みとして扱うため、
配布者の指示で対象を確認したうえで `--force-reinstall` を使用する。未確認の Wheel へ自動更新しない。

```powershell
& $python -m pip uninstall comictagger-jp-talker
```

アンインストールは依存 package や診断 cache、保存済み report を自動削除しない。
ComicTagger 用 ZIP は別管理であり、この操作で削除しない。

## 3. 診断を実行する

NDL 書誌 ID 一件を明示する。以下は **NDL / MADB への通信を許可する実行例**。
本受入作業で Codex が実 endpoint に再実行したコマンドではない。
各例は PowerShell 7 を前提とし、§2 で設定した専用 venv の `$python` を共有する。
新しい shell では `$venv` と `$python` を設定し直す。text 保存例と JSON 保存例は
それぞれ新しい出力ディレクトリを作り、相互の変数や実行順には依存しない。

CLI 自身の help・エラー接頭辞・固定説明文は英語。NDL / MADB のタイトル・出版社・brand などの
原文と、外部ライブラリや OS の例外詳細は翻訳しない。JSON schema、reason code、通常 Talker の日本語 UI も変えない。

### Text 診断

```powershell
& $python -X utf8 -m comictagger_jp_talker.imprint_diagnostics --ndl-id R100000002-I023440575 --allow-network
$diagnosticExit = $LASTEXITCODE
$diagnosticExit
```

### Text 診断を UTF-8 ファイルへ保存する

PowerShell 7 で新規フォルダーへ保存する。`--allow-network` により NDL / MADB への外部通信が発生し得る。
stdout と stderr を別ファイルに保存し、exit 0 / 3 の非空 report だけを表示する。

```powershell
$run = Join-Path $HOME ('jpbooks-text-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $run | Out-Null
$textPath = Join-Path $run 'report.txt'
$errorPath = Join-Path $run 'error.txt'
& $python -X utf8 -m comictagger_jp_talker.imprint_diagnostics --ndl-id R100000002-I023440575 --allow-network --format text > $textPath 2> $errorPath
$diagnosticExit = $LASTEXITCODE
$diagnosticExit
if (
    ($diagnosticExit -in @(0, 3)) -and
    (Test-Path -LiteralPath $textPath -PathType Leaf) -and
    ((Get-Item -LiteralPath $textPath).Length -gt 0)
) {
    Get-Content -LiteralPath $textPath -Encoding utf8 -TotalCount 20
}
if (Test-Path -LiteralPath $errorPath -PathType Leaf) {
    Get-Content -LiteralPath $errorPath -Raw -Encoding utf8
}
```

保存先は `$textPath`。exit 3 の report は不完全取得であり、先頭 20 行の表示だけで全 evidence を確認したことにはならない。
exit 4 / 130 の部分出力を完全な report として利用しない。

### JSON 診断・読み込み・終了コード

既存 report を上書きしないよう、新しい専用出力フォルダーを作る。

```powershell
$run = Join-Path $HOME ('jpbooks-report-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $run | Out-Null
$jsonPath = Join-Path $run 'report.json'
$errorPath = Join-Path $run 'error.txt'
& $python -X utf8 -m comictagger_jp_talker.imprint_diagnostics --ndl-id R100000002-I023440575 --allow-network --format json > $jsonPath 2> $errorPath
$diagnosticExit = $LASTEXITCODE
$diagnosticExit
if (
    ($diagnosticExit -in @(0, 3)) -and
    (Test-Path -LiteralPath $jsonPath -PathType Leaf) -and
    ((Get-Item -LiteralPath $jsonPath).Length -gt 0)
) {
    $report = Get-Content -LiteralPath $jsonPath -Raw -Encoding utf8 -ErrorAction Stop |
        ConvertFrom-Json -ErrorAction Stop
    $report.schema_version
    $report.operation
    $report.apply_allowed
}
if (Test-Path -LiteralPath $errorPath -PathType Leaf) {
    Get-Content -LiteralPath $errorPath -Raw -Encoding utf8
}
```

`schema_version=imprint-report-v1`、`operation=READ_ONLY`、`apply_allowed=false` が固定契約。
終了コードは native command の直後に保存する。3 で report があっても取得完全とは扱わない。
parse 自体が失敗したファイルを完全な report として使用しない。
存在しないファイル、ディレクトリ、空ファイルは読み込まず、読込・parse 失敗は処理を停止する。
exit 4 / 130 の部分出力は解析対象にしない。

| 終了コード | 意味 |
|---|---|
| 0 | 診断処理完了。候補なし、HOLD / REJECT、意図された有効 ISBN なしも含む |
| 2 | 不正入力または通信許可なし。取得・report 生成なし |
| 3 | 外部取得失敗・必要取得の不完全性。evidence があれば不完全 report が出る |
| 4 | 内部契約・serialization・出力・close 失敗 |
| 130 | Ctrl+C による中断 |

## 4. 読み取り専用・cache・表示の意味

`--allow-network` は NDL / MADB 通信と診断用 source cache I/O を許可する。
許可前は source / session / cache を生成しない。許可後には cache 書込がある。
Windows の診断 cache は通常 `%LOCALAPPDATA%\comictagger-jp-talker\imprint-diagnostics`。
環境変数がない場合などの厳密な規則は [R2 の cache 契約](phase2c2c_imprint_diagnostics.md#2-通信許可と読み取り専用の範囲) を参照する。

専用 venv は Python package を分離するが、同じ Windows ユーザーの診断 CLI 同士はこの cache root を共有し得る。
通常 Talker は host が渡す cache folder を使用し、診断 CLI は host 設定ファイルを読み込まない。
任意の host カスタム設定が同じ場所を指す場合まで、絶対に衝突しないと保証するものではない。

- archive path は受け付けず、CBZ / CBR / ComicInfo.xml や GenericMetadata、Notes、description を更新しない。
- 既存 archive の Imprint は未確認。`existing_imprint=None` は保存先欠損の実測ではない。
- authority と archive は未供給。exit 0、matched / strong、JSON 生成成功は Imprint 採用・保存許可を意味しない。
- report は保存許可 token ではない。独立した本番 authority provider と host 保存契約は未実装。
- stdout は report、stderr はエラー。出力失敗時には部分ファイルが残り得る。
- text / JSON は全 evidence を出力するため、候補・event が多い場合はファイル容量とメモリ使用が増える。
  text の台帳・source outcome・evaluation には同じ snapshot / trace が複数箇所に現れる。

text は日本語を残し、制御文字・双方向制御・不可視文字・全角空白などを可逆 escape する。
JSON は Unicode escape を使い、parse 後に日本語・非 BMP・制御文字を復元する。
raw を trim / normalize した表示ではない。詳細は [R2 の出力契約](phase2c2c_imprint_diagnostics.md#4-r1-report-と出力) を参照する。

## 5. 文字コードとトラブルシューティング

Windows PowerShell 5.1 の `>` による text リダイレクトで文字化けしたとのユーザー報告がある。
PowerShell 7 と `-X utf8` を使い、読み込み時も UTF-8 を明示する。

| 症状 | 確認すること |
|---|---|
| `No module named comictagger_jp_talker` | `& $python -m pip show comictagger-jp-talker` で導入済みか確認 |
| 導入したはずなのに起動しない | `sys.executable` と `__file__` を確認。同じ venv の Python で install / 実行する |
| 通信許可不足 | 取得を許可する場合だけ `--allow-network` を付ける。cache だけの offline 診断機能ではない |
| 不正な NDL ID | URL や ISBN ではなく NDL 書誌 ID を一件指定。既存文法 `[A-Za-z0-9_-]+`、存在は NDL source で確認 |
| JSON parse 失敗 | 終了コードと stderr、空・部分ファイル、混入テキスト、読込 encoding を確認。エラー内容を消して成功扱いしない |
| 日本語の文字化け | `$PSVersionTable.PSVersion`、実行 Python、`-X utf8`、保存・読込 encoding を確認。旧 report を上書きせず新規出力で比較 |
| HTTP timeout / 取得失敗 | exit 3 と stderr / report の取得状態を確認。障害時に連続実行しない。自動 retry や強制 refresh は提供しない |
| cache の時刻が不明 | `observed_at` は今回の観測、`origin_fetched_at` は原取得、`cache_stored_at` は保存時刻。null を現在時刻や cache hit で補わない |
| ComicTagger.exe から起動できない | exe 内の診断起動機構は対象外。専用 Python の `-m` で起動する |

`--refresh` は存在しない。NDL / MADB の既存 timeout・limiter・cap・cache key を変更して回避する案内はしない。
source constructor 内の部分初期化回収、close 失敗、単一スレッドの logging 抑止については R2 の既知制限を引き継ぐ。

## 6. 実測の読み方と手動受入

ユーザー報告による実測では `R100000002-I023440575` は `matched / strong`、評価は `reject`、exit 0。
Book の brand は `Kirara menu` と `Manga time KR comics`、Series は `Manga time KR comics　／　Kirara menu`。
理由は `context_conflict / multiple_displays / semantic_unverified`。
MADB publisher `芳文社　∥　ホウブンシャ` と NDL `芳文社` の比較で conflict が観測された。
表記差が原因の可能性はあるが、確認済み候補の誤拒否と断定しない。R3 では比較規則を変更しない。

保存済み text 全体の cache_hit 6 / network stage 0 はユーザー報告と一致する観測で、
重複した trace 表現を含む。独立した 6 要求や、NDL / MADB の実 HTTP 0 件を証明しない。
Codex は今回 NDL / MADB の追加ライブ通信を行っていない。

実 ComicTagger.exe の画面操作は今回 **NOT RUN**。beta9 loader / offscreen の自動試験と区別する。
独立 Wheel 実行の阻害条件ではなく、exe 利用者向けの手動共存確認は次の手順で別に行う。

1. beta9 の実 exe、隔離 config、既存利用者データではないテスト用 CBZ コピーを用意する。
2. ZIP を plugins に配置し、About / plugin 一覧で版と Japanese Books、Series default OFF を確認する。
3. 別の専用 venv で help / version を実行しても host の設定と archive が変わらないことを確認する。
4. 通常の NDL 検索・詳細 preview と Series OFF / ON を確認する。実 endpoint を使う場合は
   別途明示許可を得て、既存 limiter に従い、検索・詳細 fetch・最終取得の通信を区別する。
   preview が最終 fetch を呼ぶ既知の経路を「全 preview 通信 0」と扱わない。
5. 通常経路が診断 CLI を自動実行せず、Imprint / 診断内容の Notes 出力が追加されていないことを確認する。
   既存 Series 補完の出典 Notes は従来の仕様として区別する。
6. 操作手順、版、設定、ログ、CBZ の前後 hash を記録する。未実施の画面操作を loader 成功から推定しない。

**R3 の受入は診断 CLI の配布・実行だけ。Imprint 自動補完全体は NO-GO を維持する。**

2026-10-26 の独立 venv 試験では Python 3.12.14 を使用し、通常の依存解決で
ComicTagger 1.6.0b11.dev0 / requests 2.34.2 が導入された。依存 package の外部取得を含む。
beta9 との共存は開発環境の beta9 loader 試験で別に確認する。
将来も同じ依存 version に解決される保証ではなく、検証環境と詳細結果は [R3 の受入記録](validation_history.md#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26) を参照する。
