# Phase 2C-2C-4R2：明示実行の読み取り専用 Imprint 診断 CLI

2026-10-23。NDL 書誌 ID 一件と明示通信許可を受け取り、既存 source の evidence を
R1 の `imprint-report-v1` として表示する独立コマンド。通常 Talker、GUI preview、
`metadata_supplement` には接続しない。**Imprint 自動補完全体は NO-GO を維持する。**

## 1. 実行方法と引数

Python と依存 package が利用できる環境で実行する。Windows Terminal / PowerShell 7 では
`-X utf8` を指定する。ComicTagger.exe 内に診断メニューや起動機構を追加するものではない。

```powershell
.venv/Scripts/python.exe -X utf8 -m comictagger_jp_talker.imprint_diagnostics --help
.venv/Scripts/python.exe -X utf8 -m comictagger_jp_talker.imprint_diagnostics --ndl-id R100000002-I023440575 --allow-network
.venv/Scripts/python.exe -X utf8 -m comictagger_jp_talker.imprint_diagnostics --ndl-id R100000002-I023440575 --allow-network --format json > report.json
$LASTEXITCODE
```

上の診断例は実通信を許可するコマンド。R2 の検証では HTTP mock のみを使用した。
終了コード 3 でも不完全取得の有効な report が出る。JSON parse 成功や終了コード 0 を保存許可と解釈しない。
出力失敗ではファイルが途中まで残り得るため、必ず終了コードも確認する。

| 引数 | 契約 |
|---|---|
| `--ndl-id` | 必須、一回だけ指定。NDLSource.get と同じ `[A-Za-z0-9_-]+`。存在確認は NDL source による |
| `--allow-network` | 既定 False。NDL / MADB 通信と source cache I/O の明示許可 |
| `--format` | `text` / `json`、既定 `text` |
| `--help` | 使用方法、終了コード 0 |
| `--version` | 現在の package version `0.4.0`、終了コード 0 |

略記した option、未知引数、複数 ID、任意 URL、endpoint、archive path は受け付けない。
`--refresh` は未実装。MADB は refresh を受け付けるが、NDL の `get()` は record cache を
明示的に bypass する引数を持たない。全取得の再実行を保証できないため、一部だけ refresh する入口を設けない。
将来追加する場合は NDL と MADB の両方の契約と要求数を別途確定する。

## 2. 通信許可と読み取り専用の範囲

`parse_args()` → `validate_request()` の後でのみ cache path を解決し、source を生成する。
許可なし、ID なし、不正 ID、不正引数、help / version では source / session / cache を生成しない。
通信しなかったことを表す偽の R1 report も生成しない。

許可後には既存 cache の通常の読書きがある。「読み取り専用」は保存先の metadata / archive に
対する契約で、cache 書込禁止という意味ではない。GenericMetadata、Notes、description、Imprint、
CBZ / CBR、ComicInfo.xml、NDL の `latest-error.txt` を変更しない。

診断専用 cache root は Windows で `%LOCALAPPDATA%/comictagger-jp-talker/imprint-diagnostics`。
その他の環境では `$XDG_CACHE_HOME/comictagger-jp-talker/imprint-diagnostics`、
該当環境変数がない場合は `~/.cache/comictagger-jp-talker/imprint-diagnostics` を使用する。
その下に既存 source の `jpbooks-ndl-v1` / `jpbooks-madb-v1` が作られる。
host 設定や既存エラー履歴を読む必要がなく、source 内の namespace / key / TTL は変更しない。
通常 Talker の cache との共有を保証するものではない。

## 3. NDL と MADB の取得

`acquire_diagnostic_evidence()` は `NDLSource.get(ndl_id, summary_mode="none")` を一度呼ぶ。
record cache または既存 SRU 取得を使用し、返った ID が指定 ID と一致することも確認する。
Summary JSON endpoint への追加要求、別書誌の title / ISBN fallback、通常の `fetch_comic_data()` は使わない。
正常 0 件は source の not-found `TalkerDataError`、HTTP / timeout は `TalkerNetworkError`、
SRU protocol / XML は `TalkerDataError` として error chain に保持する。いずれも MADB を開始しない。

NDL 成功後だけ `MADBSource` を生成し、共有 core を一回呼ぶ。

```python
evidence = acquire_linked_record_evidence(record, source, refresh=False, scope="series_linkage")
```

Book / Series の全直接 triple、discovery の取得順・制限を維持する。
Agent / Holding の詳細取得、追加検索、full scope、自動 retry は導入しない。

| 制約 | 維持する既存実装 |
|---|---|
| NDL endpoint | `https://ndlsearch.ndl.go.jp/api/sru` |
| NDL timeout | SRU `(5, 60)`。Summary `(5, 15)` は変更せず、診断では未使用 |
| NDL limiter | ローカル方針の 2 秒に 1 回 |
| MADB endpoint | `https://mediaarts-db.artmuseums.go.jp/sparql` |
| MADB timeout / limiter | `(5, 30)`、ローカル方針の 3 秒に 1 回 |
| discovery / triple | 既定 20 候補 / 300 triple。source の cap 処理を維持 |
| byte / relation | 2 MiB / 12 関係。未取得・partial / truncated の trace を保持 |
| cache | 既存の parser 検証、成功保存条件、namespace / key / 有効期間を維持 |

limiter 値を各機関の公式割当量と解釈しない。cold / warm の実測は fixture ごとの値であり、
すべての書誌の固定要求数ではない。NDL SRU と MADB HTTP は別々に数える。

## 4. R1 report と出力

取得を終えて source を閉じた後、`describe_imprint_evidence(evidence)` を一回呼ぶ。
JSON の唯一のデータ源は `report_to_json_data(report)`。text も同じ厳密な変換結果を表示に使う。
R1 の JSON field、型、順序、BookEvaluationState、evaluator、identity は変更しない。
R1 内部の schema 検証は既存どおり行う。未知型を `repr` / `default=str` で救済しない。

評価対象は R1 が決める。除外 bundle の再評価、未取得への空 bundle 生成、独自の候補救済はしない。
authority は未供給、archive は未供給、保存先の既存値は未評価。
`existing_imprint=None` は evaluator 入力であり、保存先の欠損を観測した意味ではない。

### Text

冒頭に NDL ID、title、raw ISBN、scope、run ID、discovery、linkage、候補数と各 Book の
台帳 index / 取得状態 / 評価状態 / eligibility を表示する。続けて R1 の全 field を
ラベルと配列 index 付きの plain text として出力する。失敗・未取得・除外を消さない。
分類、比較、blockers、issues、全 trace / event も省略しない。表示上の切詰めはない。
同じ ID の台帳項目も別 index のまま表示する。

```text
Authority: not supplied
Archive: not supplied
Existing Imprint: not assessed
Apply allowed: no
Writes performed: no
```

文字列は `json.loads()` で原値へ戻せる JSON string literal 表記。
日本語と通常の非 BMP 文字は可読なまま、ESC / ANSI、C0 / C1 / DEL、CR / LF / TAB、
Unicode 双方向・ゼロ幅・不可視文字、ASCII space 以外の separator、結合文字を escape する。
外周 ASCII space は引用符の内側に残し、全角空白は `\u3000` と表示する。
XML / HTML 特殊文字を markup として解釈しない。raw の trim / normalize / 削除はしない。
結合文字も保守的に escape するため、一部の可視アクセントは Unicode escape 表示になる。

原取得時刻が null のときは unknown と明記する。現在時刻で補わず、cache hit を原時刻の証明にしない。
run / event / origin / cache の時刻、hash の意味、`parsed_snapshot_digest=null`、
`snapshot_simultaneity=unknown` は R1 のまま。

### JSON と stdout / stderr

`json.dumps(..., ensure_ascii=True, allow_nan=False)` で全 serialization を終えてから、
stdout に一つの document と末尾改行を書き、flush の成功まで確認する。
ASCII の Unicode escape は JSON parse 後に日本語・非 BMP・制御文字を完全復元できる。
text は UTF-8 実行を推奨する。非対応 encoding の `UnicodeEncodeError` は失敗として扱う。

stdout は report 専用、stderr は実行エラー専用。外部由来の exception message も ASCII JSON quote する。
取得から renderer までの標準 logging を一時的に抑止し、既に stdout を捕捉した handler も遮断する。
その後 logging の disable 値を復元し、handler や通常 Talker の logger 名・設定は変更しない。
この一時抑止は独立した単一スレッドの CLI を前提とし、並行する host 内への組込み API ではない。

## 5. 終了コードと不完全取得

| Code | 意味 |
|---|---|
| 0 | 診断処理完了。help / version、完全取得で候補なし、HOLD / REJECT / identity conflict も含む |
| 2 | 入力不正・通信許可不足。report なし |
| 3 | 外部取得失敗・必要取得の不完全性。evidence が得られた場合は不完全 report を出力 |
| 4 | 内部契約、renderer、serialization、stdout 出力、close の失敗 |
| 130 | Ctrl+C。close の失敗が同時に起きても中断を優先し、両方の error を表示 |

取得の判定は discovery と各 Book の context / bundle の完全性に基づく。
partial / truncated、trace 不在による完全性不明、Book failure / 未取得、必要な Series / relations /
resource / book_series_scope の不完全性は 3。Agent / Holding の意図された未要求は失敗にしない。
既存 linkage の identity conflict は取得障害へ変換しない。
ただし要求 ID と返却 Book の ID / URI が違うケースは、core 自身が取得 error として保持するため 3。

有効 ISBN なしの `NOT_REQUESTED / no_valid_isbn` は 0 とする。意図された非実行であり、
「診断は完了したが MADB 候補の評価材料がない」と text と JSON の取得理由に明示する。
authority 不足の HOLD と HTTP 障害を混同しない。

NDL 取得失敗で evidence がなければ report は出さない。source 取得中の Talker / MADB の既存例外、
filesystem / SQLite error は外部取得失敗。TypeError / ValueError / AssertionError などは内部エラー。
取得後の serialization / 出力 / close の OSError は 4 であり、通信障害へ一括分類しない。
BrokenPipe、短い write、flush 失敗は成功にしない。module の失敗終了時は stdout を閉じ、
shutdown の再 flush が終了コードを 120 に変えることも防ぐ。

## 6. Resource close と中断

ExitStack で終了処理を登録する。NDLSource は close / context manager を持たないので、
NDL session と cache を別々に一回ずつ close する。一方が失敗しても他方を閉じる。
MADBSource は `__enter__` / `__exit__` を使用し、source が自身の session / cache を閉じる。
CLI から MADB の下位 resource を二重 close しない。

成功、NDL / MADB 取得失敗、discovery / Book failure、Ctrl+C、exit / close 失敗で終了処理を実行する。
report / renderer / stdout の失敗時には既に source は閉じられている。
close エラーは記録して残りの cleanup を継続し、元の取得エラーも error chain に保持する。
close 失敗時に成功 report を出さない。constructor が返る前に失敗した未成立 source は close しない。

既存 constructor 内の部分初期化には制限がある。NDL は session 作成後の cache 初期化失敗、
MADB は cache 作成後の session 初期化失敗などで、CLI へ object が返らない。
この内部 resource の回収保証は既存 source 側にない。R2 は constructor を変更せず、制限として保持する。
また source 自体の close が失敗した resource の解放成功は保証できず、再 close / 自動 retry はしない。

## 7. 検証・配布・次工程

専用テストは引数、許可前 I/O 0、実 source の HTTP mock、R1 接続、全候補、制御文字、
500 raw 候補と 1,000 件超 event、close / 中断 / serialization / 出力失敗を扱う。
R1 / E0 / E1 の既存テストは変更・削除しない。通常試験は外部 HTTP を禁止する。
全回帰、Ruff、配布物の結果は [validation.md](validation.md) の R2 記録に残す。

既存 build で sdist → wheel → plugin ZIP を生成する。全 production Python の集合と bytes を照合する。
wheel は `-I` の隔離 subprocess で実際の wheel を sys.path の先頭に置き、module を
`runpy.run_module(..., run_name="__main__")` で起動する。help / version、HTTP mock の text / JSON、
UTF-8 ファイル出力、ASCII JSON、text encoding 失敗、broken pipe、Ctrl+C を検証する。
既存 beta9 loader の path cleanup 後の通常 NDL / Series 機能を再検証する。
version `0.3.0`、既存 Talker entry point、Series default OFF を維持する。

text / JSON は全 evidence をメモリ上に展開するため大きくなる。ページング・表示上限は未実装。
通信の live 実用性、配布 exe の操作、一般利用者向けインストール方法の受入は R3 に残す。
R2 の wheel 起動検証だけで CLI の一般配布方針や R3 完了を決めない。

R3 は R2 の検証成功を前提に、配布方式の合意、beta9 との共存、日本語・escape・ログ・終了コードの
実環境での可読性と手順を確認する。新しい実通信確認は明示許可と既存 limiter の範囲で実施する。
本番 authority の真正性・対象適合・期限・失効の供給と host の保存契約は未実装。
Imprint 自動補完設定、GUI hook、保存処理は追加していない。**Imprint 自動補完全体は NO-GO**。

raw evidence の SHA-256 は
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12` を維持する。
