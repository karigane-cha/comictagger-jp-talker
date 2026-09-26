# 検証記録

## 0.2.0 の検証

2026-09-27 (JST)、正式 Release preparation で再実行した結果。
production の基準は main の `d352379`（Phase 2B-1 MADB foundation と Phase 1 Series 修正を含む）。
この preparation の変更は文書のみで、production Python、workflow、Phase 2A evidence は変更していない。
package version は **0.2.0**。正準定義は `comictagger_jp_talker/__init__.py` の `__version__`、
setuptools は `pyproject.toml` の dynamic version でこれを参照する。

### ローカル環境と結果

Windows、CPython 3.12.14、ComicTagger 1.6.0b9、comicinfoxml 0.5.1。
`.venv/Scripts/python.exe` を使用し、pytest の一時領域と cache を `.tools/` 内に指定した。

| 検証 | 今回の結果 |
|---|---|
| `python -m ruff check .` | 成功 |
| `python -m ruff format --check .` | 既存 baseline の 12 ファイルが整形対象、31 ファイルが整形済み。改行混在・既存のリスト整形・Phase 2A 文書内の Python code fence 等の差。今回それらは変更していない |
| `python -m pytest -m "not network"` | **1151 passed / 10 deselected / 1 xfailed**、18.56 秒。skip なし。xfail は CIX writer の `Volume=0` 省略 |
| `JPBOOKS_RUN_NETWORK_TESTS=1 python -m pytest -m network` | **10 passed / 1152 deselected**、80.20 秒。NDL 8 件、MADB 2 件。全 suite を 1 回実行し、環境変数は終了後に解除 |
| `git diff --check` | 成功 |
| `python -m build` | 成功。旧 dist / generated egg-info を削除、build 不在を確認してから隔離環境で sdist → wheel を生成 |
| `python scripts/build_plugin.py <自動検出した wheel>` | wheel / sdist が各 1 件であることを確認し、plugin ZIP を生成 |
| `python -m pytest tests/test_packaging.py::test_built_zip_in_isolated_host -q` | **1 passed**、8.88 秒。実 ZIP を beta.9 loader で読み込み、loader の sys.path 後処理後も mock NDL 検索・取得成功 |
| wheel / sdist metadata | Name=`comictagger-jp-talker`、Version=`0.2.0` |
| local plugin ZIP | 52,055 bytes、有効な ZIP、`archive.testzip() is None`、package METADATA は 1 件 |

生成物:

- `dist/comictagger_jp_talker-0.2.0-py3-none-any.whl`
- `dist/comictagger_jp_talker-0.2.0.tar.gz`
- `dist/jpbooks_talker-plugin-0.2.0.zip`

ZIP の entry point、`talker.py`、現在の `mapping.py`、MADB の `madb.py` / `madb_models.py` /
`madb_parser.py` / `madb_queries.py` を確認。全 package Python source を作業領域の source と照合した。
tests、research datasets、`.git`、`__pycache__`、`.pyc` は含まれない。
成果物と一時 Release notes は `.gitignore` 対象で、preparation commit には文書だけを含める。
Release asset は既存の tag workflow が生成する plugin ZIP だけ。
最終公開状況は [v0.2.0 Release](https://github.com/karigane-cha/comictagger-jp-talker/releases/tag/v0.2.0) と
[GitHub Actions](https://github.com/karigane-cha/comictagger-jp-talker/actions) を参照する。

### Phase 2B-1 MADB network verification

`tests/test_madb_integration.py` の 2 件が成功。
ISBN `9784832241190` から MangaBook `M381096` を検索し、Book と MangaBookSeries `C334830` を取得、
bundle の completeness=`complete` を確認した。
ISBN-13 `9784592880714` から ISBN-10-only の `M299519`（`4592880714`）も検出した。
通常 Talker lookup は NDL Search のみで、MADB 自動アクセス、GenericMetadata mapping、
NDL/MADB linkage / merge、Phase 2B-2 は未実装という境界を unit tests でも維持している。

### Series inference の NDL network regression

`tests/test_integration.py::test_real_phase1_series_and_number_regressions` の 3 実例が成功。

| NDL record | raw title | raw volume | 最終 Series | 明示巻 / 推定巻 / 論理巻 | conflict |
|---|---|---|---|---|---|
| `R100000002-I030727178` | `My Girl. vol.31` | `vol.31` | `My Girl` | `31` / `31` / `31` | False |
| `R100000002-I025437130` | `ご注文はうさぎですか? : アンソロジーコミック. volume 1` | `volume 1` | `ご注文はうさぎですか? : アンソロジーコミック` | `1` / `1` / `1` | False |
| `R100000002-I029306375` | `ご注文はうさぎですか? = Is the order a rabbit? 7` | `7` | `ご注文はうさぎですか?` | `7` / `7` / `7` | False |

raw title / volumes / series_titles は不変。原巻次を Notes に保持し、整数変換できない旨の警告は出ない。
Volume only / Issue only / Both、0 巻、非整数抑止、こち亀・パタリロ!・既存の `volume 1`、
全角数字と正式な記号の保持は non-network suite で確認した。

## 0.1.12 のローカル build 検証

2026-09-24。0.1.11 以降の Series 検索と巻番号推定の修正を含む。

- `search_metadata()` の Series 入力・空白除去・fallback を検証。検索時の資料種別が `online` なら図書は対象外となるため、図書検索では設定を `books` にする。
- 実書誌 `R100000002-I000001355589` の巻番号区切りと、`R100000002-I023440575` のタイトル／NDL 巻次 `volume 1` を確認。後者は Series=`ご注文はうさぎですか?`、明示巻・タイトル推定巻・論理巻番号=`1`、不一致なし。原タイトルと巻次は保持する。
- `volume` / `Volume` に空白と 1 〜 3 桁の整数が続く場合だけ巻番号 marker として認識する。数字のない `volume`、小数・範囲・分数・4 桁は推定・出力せず、0 巻と Volume only / Issue only / Both を検証した。`vol.` は未対応。

既知の制約として、ComicTagger 1.6.0b9 の CIX writer は整数 Volume=0 を省略する。非整数巻次は Volume / Issue へ出力しない。複数 Publisher の役割分離は未対応。

## 0.1.11 の Release 準備

NDL Search 単独の Phase 1 完了版。作品名の Series 推定、括弧付き副題と明示巻次の正規化、論理巻番号と Volume / Issue の分離、紙・電子の日付、責任表示、ISBN / GTIN、Notes の原値保持を含む。

- 非整数巻次を安全に未出力とし、NDL の版表示・資料種別を ComicInfo Format へ変換しない。
- 不明な creator role の Other fallback、破損キャッシュからの復旧、要約と制御文字の安全性を Phase 1 audit tests で確認。
- `vX.Y.Z` の tag push でテスト、build、ComicTagger plugin ZIP の検証、GitHub Release と asset の作成を行う workflow を追加。
- CIX writer の Volume=0 省略、複数 Publisher の役割未分離、複数言語の先頭のみ使用は既知の制約として維持。

## 0.1.10 の Phase 1 完了確認

NDL Search 単独の Phase 1 を監査し、安全に確定できる書誌情報だけを ComicTagger へ出力する方針を確認。

- ISBN / GTIN、作品名の Series 推定、括弧付き副題、明示巻次とタイトル推定巻の照合、3 種類の Volume / Issue 出力を検証。
- 紙・デジタル資料の日付、責任表示と構造化 creator role、未知の役割の Other、要約・制御文字・キャッシュ破損時の復旧を検証。
- 解釈不能な非整数巻次は Volume / Issue へ出力せず、NDL 原値を BookRecord と Notes に保持。
- NDL の版表示・資料種別から ComicInfo の Format を生成せず、原値を BookRecord・Notes・候補説明に保持。
- ComicTagger 1.6.0b9 の CIX writer が Volume=0 を省略する既知の制約は xfail として記録。複数 Publisher の役割分離は未対応。

## 0.1.9 の追加検証

NDL の明示巻次を専用 helper で正規化してから、タイトル推定値と比較する対応を追加。

- `1 (国王誕生の巻)`、全角数字・括弧、巻付き表記、先頭のゼロ、1 〜 3 桁を検証。
- 正規化後に同じ巻番号となる複数値は重複除去し、異なる巻番号や不明な巻次との競合は保持。
- 小数・範囲・分数・英字付き巻次・4 桁の値を整数化せず、原文と既存の Issue 文字列保持を検証。
- 全出力モードで検索候補から取得・巻照合、原文保持、Notes の誤警告がないことを検証。
- 実際の ComicTagger による CR / CIX 保存・再読込と、beta.9 の配布 ZIP 読み込み後の取得を検証。

NDL parser、BookRecord、タイトル推定、日付、責任表示、検索構文、巻番号出力設定は変更しない。

## 0.1.8 の追加検証

巻番号の後ろに丸括弧の補足が 1 つあるタイトルから、シリーズ名と巻番号を推定する対応を追加。

- 半角／全角の対応する括弧、空白あり／なし、第 N 巻、全角数字、従来の末尾数字を検証。
- ネスト・複数・空・不一致の括弧、小数、範囲、4 桁の年、区切りのない数字を推定しないことを検証。
- シリーズ名の記号、完全な Title、NDL の巻次原文、既存 Series の優先、巻番号の競合検出を検証。
- 全出力モードで候補選択から取得・巻照合までを検証。実際の beta.9 による配布 ZIP の読み込み後にも副題を含む Title を確認。

NDL parser、BookRecord、検索構文、出版日、責任表示、巻番号出力設定は変更しない。

## 0.1.7 の追加検証

2026-09-21、書誌日付とデジタル資料の日付を分離し、取得元設定を追加。

- Automatic / Bibliographic date / Digital date、紙と電子の判定、fallback、元データ保持を検証。
- 年・年月・年月日の精度、同一資料内の矛盾、不正日付、複数電子版の競合、資料を横断しない精度補完を検証。
- namespace、書誌との明示リンク、v2 の dateDigitized、v3 の Item 日付、無関係な Item の除外を検証。
- 設定保存、Talker 全取得経路と候補の年、CIX 保存・再読込、配布 ZIP 内の処理を検証。
- v2 の書誌キャッシュを v3 で再利用しないことを確認。
- opt-in の実 API テストで `R100000002-I029046058` の書誌年月と電子版の日付を比較し成功。

検索 CQL・ソート条件・ランキング、シリーズ名、巻番号設定、責任表示の役割変換は維持する。
通常テストでは HTTP を mock し、実応答全文は fixture へコピーしない。

## 0.1.6 の追加検証

2026-09-20、NDL の巻次原文・論理巻番号・出力先を分離した。

- beta.9 で `volume: int | None`、`issue: str | None`、CIX の Volume / Number 対応を確認。
- `GenericMetadata.overlay()` と `prepare_metadata()` を確認。通常の結合は新しい `None` で既存値を削除しない。
- 明示巻のみ、タイトル推定のみ、一致、不一致、複数明示巻、既存／要求値の分離と原文保持を検証。
- 出力先 3 種類、全角数字、非整数巻、要求との不一致、年の照合、既存 Volume からの再検索を検証。
- 設定の既定値・保存／読込・検証と、実際の CR / CIX での各出力モードの CBZ 保存・再読込を検証。
- beta.9 標準 GUI の各出力モードで候補の手動選択・取得を検証。Volume only の番号列は空欄。
- ZIP 読み込み後にも Volume only で要求巻との照合と fetch が成功することを検証。

矛盾する書誌は巻番号を未出力とし、Notes・候補詳細で警告する。要求巻付き取得はエラー、巻指定の照合では除外する。
既存タグの自動削除はせず、利用者の exe では不要な Issue / Volume を標準画面で空欄にして保存する。
NDL の XML 解釈、検索構文、シリーズ名、責任表示の役割変換は変更しない。

## 0.1.5 の追加検証

2026-09-20、責任表示の括弧処理・役割変換・creator fallback を分離した。

- beta.9 の `Credit`、標準 role 選択肢、GenericMetadata の role 同義語、comicinfoxml 0.5.1 の writer/reader を確認。
- 全対応役割について、括弧なし・半角／全角の角括弧・丸括弧を検証。
- 指定された実例、未知の役割、曖昧な表記、不正括弧、Unicode、複数人物を分割しないことを検証。
- 責任表示優先、creator fallback のみ Writer、contributor の Other、複数 role と重複除去、原文保持を検証。
- CIX で実際に CBZ を保存し、Writer への統合、Artist の保存先、Other の非対応、Notes の再読込を確認。
- ZIP ロード後にも SRU の括弧付き責任表示から Credit を取得する検証を追加。

NDL parser・Talker API・BookRecord は変更しない。原文を Notes に保存し、CIX の制限は README に明記した。
作画原稿・文字・表紙・カバーは曖昧なため Other。任意の複合役割・人物の自動分割は行わない。

## 0.1.4 の追加検証

2026-09-20、NDL の出版シリーズ等が漫画作品の `Series`・別名へ混入する問題を修正。

- `Series` は `existing_series` を優先し、なければ `infer_volume(record.title)` の作品名を使用。
- 出版レーベル・雑誌名・複数の出版シリーズ・空の値を使い、作品名と別名へ混入しないことを検証。
- 巻次付きタイトルと `20世紀少年` のような作品名、既存値の優先を検証。
- `series_titles` の原文が変更されず、Notes と候補詳細に残り、候補詳細では HTML がエスケープされることを検証。
- 標準 Talker の検索・issue 選択・fetch、実際の CR / CIX による CBZ 保存・再読込を検証。
- 配布 ZIP の beta.9 ローダー検証にも、作品名・空の別名・原データの Notes 保持を追加。

MADB の漫画作品シリーズは、出版シリーズとは別の出典付き項目として将来追加する方針を記載した。
Phase 1 に未使用のモデル・取得処理は追加していない。
利用者の exe では ZIP を入れ替えて再起動し、再フェッチ後の Series と Notes を確認して保存する。
既存キャッシュの削除は不要。保存済みタグを自動で一括修正するものではない。

## 0.1.3 の追加検証

2026-09-19、タイトル検索の取得順を改善した。

- `こちら葛飾区亀有公園前派出所` の図書検索で 590 件の応答を確認。
  従来の先頭 20 件が再編集版で占められ、古い順を指定すると本編の第 1 巻等が含まれることを確認。
- `oldest`・`newest`・`title` のクエリ生成、ソート指定の注入拒否、取得順ごとのキャッシュ分離を検証。
- 著者・巻番号を緩める再検索でも取得順を保持し、ISBN・書誌 ID 検索にはソートを追加しないことを検証。
- 設定の既定値と検証、文書・設定文言の空白ルールも検証。

変更箇所：`models.py`、`sources/ndl.py`、`talker.py`、バージョン定義、README と調査・検証記録、関連テスト。
取得上限は従来どおりで、Web の対象機関の絞り込みや画面上の順序との完全一致を保証するものではない。

## 0.1.2 の追加検証

2026-09-19、Summary の要約と書誌注記を分離し、NDL の詳細 JSON API で要約を補完した。

- 利用者指定の ISBN `9784046806680` を実際の Talker 経由で検索・取得し、
  書誌 `R100000002-I031565930` に対応する紙版の JPRO 要約を取得。
  取得した 70 文字の要約と GTIN が CIX で CBZ に保存・再読込できることを確認。
- 通常テストは架空の JSON と HTTP mock を使用。紙優先、デジタルへの切り替え、
  要約なし、別書誌の拒否、不正 JSON、timeout、キャッシュ再利用・再起動・Refresh を検証。
- 追加 API が既存の rate limiter を使い、検索時には呼ばれないことを検証。
- 書誌注記が Summary に混ざらず Notes に残ること、要約の提供元・媒体・資料 ID を記録することを検証。
- beta.9 の実際の GUI で、CR 選択時の GTIN 非対応状態、CIX 選択時の入力可能状態、
  不正な値に対する背景色の変化を確認。
- 配布 ZIP のテストは、ホストのロード後に詳細 JSON による要約補完も実行する。

実応答の全文は配布 fixture にコピーしていない。検証用の CBZ と応答は配布対象外の作業フォルダーに置いた。
更新後は 0.1.2 の ZIP に入れ替え、同じ ISBN を再フェッチして CIX で保存する。
SRU の古いキャッシュも新しいマッピングで読み直すため、この変更のための全キャッシュ削除は不要。
詳細 JSON の内部項目が将来変更される可能性は README に記載した。

変更箇所：`models.py`、`mapping.py`、`sources/ndl.py`、新規 `sources/ndl_summary.py`、
`errors.py`、バージョン定義、README と調査・検証記録、Summary・GUI・ZIP の関連テスト。

## 0.1.1 の追加検証

2026-09-19、利用者の ISBN 検索エラーを修正。以下は 0.1.1 の検証であり、
後段の 0.1.0 の初回検証記録とは区別する。

- `4-08-852811-5` と `9784088528113` の実応答で該当書誌なしの SRU 診断を再現。
  CQL の空白や ISBN のハイフンの違いでも結果は同じだった。
- 該当書誌なしを 0 件として返し、タイトル＋巻番号検索からタイトル検索へ進めることを確認。
- 他の診断、診断と件数・書誌の矛盾、複数診断の混在をエラーのまま保持することを確認。
- エラーの UTF-8 保存、日本語・補助漢字・不正入力のログ保持、書き込み失敗時の案内を確認。
- beta.9 の標準エラー画面で `Ctrl+C` による全文コピーを実際のクリップボードで検証。
- 文書と設定・案内文の英数字／日本語間の空白、長いカタカナ複合語の分かち書きを検証。
  書誌原文、URL、識別子、実行例の値は変更しない。
- 隔離ビルドと ZIP 生成が成功。beta.9 のローダーで更新版を読み込み、
  正常取得・該当書誌なし・コピー案内付きエラーを確認。テストは **132 passed, 1 skipped**。
  skip は通常無効のネットワーク テスト。ZIP 検証用サブプロセスにも UTF-8 を明示する。

変更箇所：`sources/ndl.py`、`talker.py`、`mapping.py`、新規 `errors.py`、
バージョン定義、README と調査・検証記録、関連テスト、CI のビルド対象。

更新時は旧版の ZIP／wheel を plugins フォルダーから外し、0.1.1 の ZIP と入れ替える。
利用者の配布版 exe では、再起動後の検索結果と `Ctrl+C` の操作を最終確認する。

## 0.1.0 の初回検証

検証日：2026-09-19。ComicTagger 本体は変更していない。

### 0.1.0 初回実装時の検証環境

- Windows、CPython 3.12.14
- ComicTagger 1.6.0b9（公式 beta.9 タグのソースをインストール）
- comicinfoxml 0.5.1、PyQt6 6.11.0 / Qt 6.11.2
- pytest 9.1.1、setuptools 84.0.0、build 1.6.1
- 新規プラグイン 0.1.0（editable install と生成 ZIP の両方）

### 0.1.0 初回実装時の検証と結果

| 検証 | 結果 |
|---|---|
| `python -m build` | 成功。隔離ビルドで sdist→wheel を生成 |
| `python scripts/build_plugin.py dist/comictagger_jp_talker-0.1.0-py3-none-any.whl` | 成功。wheel と同内容のローカル ZIP |
| `python -m pytest -q` 相当（作業用 tmpdir 指定） | **111 passed, 1 skipped**。skip は通常無効のネットワーク テスト |
| `JPBOOKS_RUN_NETWORK_TESTS=1 ... pytest -m network` | **1 passed**。ISBN-13 で SRU を 1 回呼び出し |
| `python -m ruff check .` | 成功 |
| `python -m ruff format --check .` | 成功 |
| importlib entry point / `get_talkers()` | `jpbooks` → `Japanese Books` を確認 |
| beta.9 `find_plugins()` を別プロセスで実行 | ZIP 由来のクラスをロードし、loader の sys.path 後処理後も検索・取得成功 |
| beta.9 `TaggerWindow` / 標準シリーズ・issue ウィンドウ | offscreen でソース表示、2 候補表示、issue74 表示、自動確定しないことを確認 |
| beta.9 `ComicArchive` + CR writer | CBZ 内 ComicInfo.xml への日本語・著者・出版社・日付・LanguageISO 等の保存と再読込成功 |
| beta.9 `ComicArchive` + CIX writer | 上記に加え **GTIN、Translator** の保存と再読込成功 |

ISBN-10 は実装前の実 API 応答調査と mock テスト、ISBN-13 は実装後のオプトイン テストで確認。
日本語タイトルは実 API の構造調査と、mock による Talker/GUI 検証で確認。
通常テストでは requests のアクセスを禁止し、個別の HTTP response だけを mock した。
ComicTagger の型を独自に再定義していない。

網羅範囲：ISBN-10/13 の正規化と全単一桁改変検出、両方向変換、GTIN-14、
CQL 引用と日本語、namespace 差し替え、正常／0 件／ SRU 診断／不正 XML／不正書誌、
timeout／接続／HTTP エラー、キャッシュ再利用・refresh・再起動、候補保持と順位、
日本語 Unicode、credits、日付の不正月日・閏年、言語、subject/NDC 分離、URL 検証、巻番号誤解析防止。

隔離環境の一時フォルダー／所有権制約があったため、テストには作業フォルダー内の
`--basetemp` と `-p no:cacheprovider` を指定して最終確認した。
最初のビルドは依存ダウンロードのネットワーク制限で失敗し、許可後の通常ビルドで成功した。
Qt の offscreen 環境ではシステム フォントの自動発見に制約があったため、
テスト側だけでインストール済み Meiryo を読み込み、画面キャプチャで日本語も確認した。
本体やプラグインによるフォント設定変更はしていない。

### 0.1.0 初回実装時の Definition of Done

| 項目 | 状態 |
|---|---|
| 1. build | 成功 |
| 2. beta.9 で読み込み | 実際の beta.9 ローダーで wheel/ZIP を確認 |
| 3. Japanese Books 表示 | 実際の標準 GUI で確認（offscreen） |
| 4. API key なし | 設定を非表示、実 API 接続成功 |
| 5–7. ISBN-13 / ISBN-10 / 日本語検索 | 実応答調査・単体／連携テストで確認 |
| 8. 複数候補 | 標準シリーズ UI で 2 候補を確認 |
| 9. GenericMetadata | 実際のクラスで変換・型検証 |
| 10. GTIN/ISBN | gtin 保持、CIX の GTIN 要素で往復確認 |
| 11–14. 著者・出版社・出版日・日本語 | CBZ 保存／再読込・Unicode 比較で確認 |
| 15. ComicInfo.xml 保存 | 実際の ComicArchive/CR/CIX で確認 |
| 16. unit tests | 111 passed（通常ネットワーク テスト 1 件 skip） |
| 17–18. README / 利用条件 | README と公式リンクを追加 |

### 0.1.0 初回実装時の手動確認事項

1. 利用中の **Windows 配布版 ComicTagger.exe beta.9** の正しい plugins フォルダーへ ZIP を置き、
   再起動後に Japanese Books が表示されること。本検証は Python パッケージ版の beta.9 で行っており、
   利用者が既に配置している exe そのものは起動していない。
2. 標準検索欄で ISBN を検索し、複数候補の版・著者・出版社を確認して選択すること。
3. CIX を単独の書き込みタグに選び、利用者の CBZ で保存・再読込して GTIN 等を確認すること。
4. Kavita で再スキャンし、シリーズ名・巻番号・日本語表示を確認すること。
   Kavita への API 接続・実機検証は行っていない。
5. 実利用の目的・提供機関に合う NDL メタデータ利用条件を確認すること。

### 0.1.0 初回実装時の既知の制限

beta.9 の標準検索メソッドに既存 GTIN や metadata が渡らないため、
GTIN の自動優先検索は補助メソッド経由のみ。標準 UI では ISBN を検索欄へ入力する。
表紙を取得しないため、表紙照合を行うホスト auto-tagging は対象外。
CR の GTIN/Translator 非対応は CIX で対応する。本体の変更や独自 writer では回避しない。
1 書誌 1 候補、件数上限、NDL 叢書名の意味、曖昧な巻次・著者役割等の制約は README 参照。

### 0.1.0 初回実装時の追加ファイル

初回実装時はすべて新規。既存ファイルの削除・置換はなかった。

- `pyproject.toml`, `MANIFEST.in`, `.gitignore`, `LICENSE`, `README.md`
- `comictagger_jp_talker/{__init__,talker,models,isbn,mapping}.py`
- `comictagger_jp_talker/sources/{__init__,base,ndl}.py`
- `tests/conftest.py`, `tests/fixtures/ndl.xml`
- `tests/test_{isbn,mapping,ndl,talker,comicinfo,gui,packaging,integration}.py`
- `scripts/build_plugin.py`, `.github/workflows/test.yml`
- `docs/research.md`, `docs/validation.md`

調査用 checkout・Python／依存環境・一時キャッシュは `.research`, `.tools`, `.venv` に分離して
`.gitignore` 対象とし、配布 wheel には含めない。
0.1.0 初回検証時点では GitHub Actions の設定ファイルを追加済みだったが、リモート CI 自体は未実行だった。
