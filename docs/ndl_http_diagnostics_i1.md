# NDL HTTP 診断ビルドと I2 実測

この I1 ビルドは方式 A の観測機能だけを追加したローカル検証用です。
パッケージのバージョンは `0.4.0` のままですが、公開済み v0.4.0 の正式成果物とは異なります。
自動リトライ、SRU クールダウン、通信数・検索条件・並び順の変更はありません。
I1 のテストとビルドでは NDL API に通信しません。

## 診断の仕様

`JPBOOKS_HTTP_DIAGNOSTICS=1` を設定してから ComicTagger を起動します。
値は診断モジュールの import 時に一度だけ読み取ります。変更後はプロセスの再起動が必要です。
`1` 以外は無効です。既定 OFF では追加 ID・時計読み取り・成功ヘッダー解析を行いません。
HTTP 失敗の安全な報告は、診断 ON/OFF に関係なく適用します。

詳細 logger は `comictagger_jp_talker.http_diagnostics` です。
有効時だけ、この logger を DEBUG にします。root、他の logger、handler は変更しません。
ComicTagger 1.6.0b9 の既存ファイル handler は、この DEBUG を標準ログへ記録できます。
起動時の `NDL diagnostics enabled:` は通信不要の有効化確認です。

| 項目 | 意味 |
|---|---|
| `run_id` | 診断を開始したプロセス内の実行単位 |
| `operation_seq` | その実行単位での操作連番 |
| `correlation_id` | 公開操作ごとの識別子。検索語から生成しない |
| `request_id` | `Session.get()` ごとの識別子 |
| `http_call_no` | 操作内の取得呼び出し番号。キャッシュだけなら増えない |
| `source_id` / `session_id` | source と Session の識別子。メモリ アドレスや Cookie は使わない |
| `query_stage` | `initial` / `relaxed_creator` / `relaxed_issue` / `relaxed_both` |
| `lock_wait_ms` | 外側の既存 RLock 取得に要した時間。別の lock イベントに記録 |
| `limiter_wait_ms` | 既存 limiter の許可取得に要した時間 |
| `elapsed` | HTTP 通信時間、秒。本文受信を含み、ロック・limiter 待機を除外 |

公開 Talker 呼び出しは、ネストしていても新しい操作として識別します。
source の内部委譲だけは、現在の操作を引き継ぎます。
ContextVar は worker 内で作成し、終了・例外のどちらでも解放します。
直接の source 呼び出しも、操作コンテキストがなければ新しく作成します。
採番はスレッド間で排他します。

| Cache 値 | 意味 |
|---|---|
| `HIT` | 既存キャッシュを利用 |
| `MISS` | 利用できるキャッシュなし |
| `REFRESH` | 既存の refresh 分岐でキャッシュを無視 |
| `INVALID` | キャッシュの解析失敗を検出 |
| `BYPASS` | 接続確認など、キャッシュ対象外の経路 |

`layer=search/record/summary` で対象を区別します。
Summary の省略理由は `not_needed`、`cache_only`、`failure_suppressed` で記録します。
不正な Summary キャッシュは既存どおり基本書誌へフォールバックし、新たな再取得は追加しません。
再入可能なロックへの内部委譲でも lock イベントが出るため、待機時間を重複加算しないでください。

HTTP 200 は通信の成功です。その後の XML/JSON 解析失敗とは別に扱います。
`operation completed` の `outcome` と `http_calls` も確認してください。
GUI のキャンセルを推測して `cancelled` と記録することはありません。

### ヘッダーとプライバシー

取得するヘッダーは `Retry-After` と `Date` だけです。
値は最大 128 文字まで解析し、不正な値・制御文字・秘密値をそのまま出力しません。
`retry_after_kind` は `absent/delta/http_date/invalid/oversized/excessive` です。
非負整数秒は最大 `2147483647` まで表現し、それより大きい値は分類だけ記録します。
これは診断上の表現限界であり、待機時間の設定ではありません。
過去の HTTP-date は `http_date`、秒数 `0`、`retry_after_past=true` で区別します。
Date は UTC に正規化します。ローカル時刻との差は時計ずれの参考値であり、制限解除の時刻ではありません。

新規 HTTP 診断には検索語、ISBN、CQL、URL、Cookie、認証値、本文を含めません。
HTTP 失敗の `latest-error.txt` も、例外の自由文やローカル パスを保存せず、関数名・行番号・例外型・安全な値から構成します。
元例外の `__cause__`、エラーコード、GUI の基本説明とコピー案内は維持します。
通信以外の従来のエラー報告や、本体が別途出す書誌候補のログまでは無害化しません。
ログ全体を共有する場合は、それらの記録も確認してください。

`latest-error.txt` は最新失敗 1 件を保持し、成功時には更新・削除しません。
失敗と次の成功の比較には標準ログを使います。

## I2 の準備

以下はユーザーが次工程で実行する手順です。I1 では実機のプラグインを差し替えません。
ComicTagger を終了してから作業してください。
現在確認した既定配置を使います。別の設定ディレクトリを指定して起動している場合は、実際の配置へ変更してください。

```powershell
$repo = 'C:\Work\VSCode\comictagger-jp-talker'
$diagnosticZip = Join-Path $repo '.tools\ndl-http429-i1\source\dist\jpbooks_talker-plugin-0.4.0.zip'
$pluginDir = Join-Path $env:LOCALAPPDATA 'ComicTagger\ComicTagger\plugins'
$installedZip = Join-Path $pluginDir 'jpbooks_talker-plugin-0.4.0.zip'
$logDir = Join-Path $env:LOCALAPPDATA 'ComicTagger\ComicTagger\Logs'
$latestError = Join-Path $env:LOCALAPPDATA 'ComicTagger\ComicTagger\Cache\jpbooks\latest-error.txt'

if (-not (Test-Path -LiteralPath $diagnosticZip -PathType Leaf)) { throw '診断 ZIP がありません。' }
if (-not (Test-Path -LiteralPath $installedZip -PathType Leaf)) { throw '元の ZIP の配置を確認してください。' }
$backupDir = Join-Path $env:LOCALAPPDATA ('ComicTagger-I1-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupDir | Out-Null
$backupZip = Join-Path $backupDir 'jpbooks_talker-plugin-0.4.0.zip'
Copy-Item -LiteralPath $installedZip -Destination $backupZip
$originalHash = (Get-FileHash -LiteralPath $installedZip -Algorithm SHA256).Hash
if ((Get-FileHash -LiteralPath $backupZip -Algorithm SHA256).Hash -ne $originalHash) { throw 'バックアップの不一致' }
Copy-Item -LiteralPath $diagnosticZip -Destination $installedZip -Force
Get-FileHash -LiteralPath $installedZip -Algorithm SHA256
```

バックアップは plugin ディレクトリの外へ置き、旧 ZIP と診断 ZIP を同時に読み込ませないでください。
出力されたハッシュを I1 の検証記録と比較してください。

### 通信なしの事前確認

既存の検証用 Python と ZIP を使い、実機設定へ触れずに確認できます。
ホストのログ設定を先に作り、ネットワークは禁止します。

```powershell
$python = Join-Path $repo '.tools\venv-py31410-security\Scripts\python.exe'
$probeDir = Join-Path $repo ('.tools\ndl-http429-i1\offline-probe-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
$env:JPBOOKS_HTTP_DIAGNOSTICS = '1'
$probe = @'
import logging, sys
from pathlib import Path
from unittest.mock import patch
import requests
from comictaggerlib.log import setup_logging
setup_logging(0, Path(sys.argv[2]))
sys.path.insert(0, sys.argv[1])
with patch.object(requests.Session, "request", side_effect=AssertionError("Offline probe")):
    from comictagger_jp_talker import http_diagnostics as d
    assert ".zip" in d.__file__ and d.enabled()
    with d.operation_scope("search", "offline_probe"):
        pass
assert logging.getLogger().level == logging.WARNING
'@
& $python -I -c $probe $diagnosticZip $probeDir
if ($LASTEXITCODE -ne 0) { throw '通信なしの診断確認が失敗しました。' }
Select-String -LiteralPath (Join-Path $probeDir 'ComicTagger.log') -Pattern 'NDL diagnostics enabled:','http_calls=0'
```

### 起動と観測

実際の exe パスは I1 で確定していません。以下ではユーザーが確認した値を入力します。
既存の別プロセスへ渡さず、新しく起動する必要があります。

```powershell
$comicTaggerExe = Read-Host '確認済みの ComicTagger.exe の絶対パス'
if (-not (Test-Path -LiteralPath $comicTaggerExe -PathType Leaf)) { throw 'exe の場所を確認してください。' }
$env:JPBOOKS_HTTP_DIAGNOSTICS = '1'
& $comicTaggerExe
```

通常の起動後、検索を追加せずに標準ログの有効化マーカーを確認します。

```powershell
Select-String -LiteralPath (Join-Path $logDir 'ComicTagger.log') -Pattern 'NDL diagnostics enabled:'
```

追加の Test API、キャッシュ削除、429 再現の連打は行いません。
必要な通常検索が 429 になったら、同じ `correlation_id` の行を確認します。
`latest-error.txt` にも同じ Request ID が入ります。
`Retry-After` が有効ならその待機を尊重し、次に必要となった検索で別 ID の記録と比較します。
ヘッダー欠落時の安全な再アクセス時刻は、この実装だけでは決められません。

```powershell
Get-Content -LiteralPath $latestError
Select-String -LiteralPath (Join-Path $logDir 'ComicTagger.log') -Pattern 'NDL .*request','NDL operation','NDL cache'
```

比較する項目は Correlation ID、操作、cache、`http_calls`、status、Retry-After、Date、待機、通信時間、Session ID です。
`HIT` と `http_calls=0` は通信なしです。HTTP 200 の証拠として扱いません。
ログは起動時にローテーションされるため、再起動前に必要なログを退避してください。

### 無効化と元の版への復帰

ComicTagger を終了し、同じ PowerShell で次を実行します。

```powershell
Remove-Item Env:\JPBOOKS_HTTP_DIAGNOSTICS -ErrorAction SilentlyContinue
Copy-Item -LiteralPath $backupZip -Destination $installedZip -Force
if ((Get-FileHash -LiteralPath $installedZip -Algorithm SHA256).Hash -ne $originalHash) { throw '復元の不一致' }
& $comicTaggerExe
```

環境変数の解除だけでも、再起動後の詳細診断は無効になります。
同じバージョン番号でも診断 ZIP と正式 ZIP は別物なので、復元時もハッシュで確認してください。
