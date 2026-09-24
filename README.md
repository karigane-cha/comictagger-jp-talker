# Japanese Books Talker for ComicTagger

日本で出版された漫画・書籍の書誌メタデータを取得する独立 Talker プラグインです。
表示名は **Japanese Books**、Talker ID は **jpbooks**。
通常のメタデータ取得元は **国立国会図書館サーチ（NDL Search）だけ**です。
HTTPS の SRU 1.2 API と DC-NDL RDF v3（`recordSchema=dcndl_v3`）を使用し、API キー・secret は不要です。
要約の補完には、NDL の公式仕様書に記載された書誌詳細 JSON API も使用します。
CBZ の読み書きと ComicInfo.xml 生成は ComicTagger の標準機構へ任せます。

Phase 2B-1 では内部の [MADB read-only source](docs/phase2b1_madb_source.md) を追加しています。
通常の Talker 検索・設定・ComicInfo.xml 出力への接続と NDL/MADB merge は未実装です。

## 対応環境

- ComicTagger **1.6.0-beta.9（Python 表記 1.6.0b9）以上、1.7 未満**。
  直接確認する対象は beta.9。以降の 1.6 系すべての動作保証ではありません。
- Python 3.10 以上。開発検証は Windows / Python 3.12 / beta.9。

## NDL API・メタデータの利用条件

**このプラグインは NDL サーチの API を使用しています。**
API キー不要であることと、利用申請不要であることは別です。
利用目的・提供機関によって、事前申請・許諾・クレジット表示が必要になる場合があります。
導入前に、次の公式案内を確認してください。「常に申請不要」とはしていません。

- [NDL Search API 利用案内・利用条件・申請手続き](https://ndlsearch.ndl.go.jp/help/api)
- [データ提供機関ごとのメタデータ利用条件](https://ndlsearch.ndl.go.jp/help/api/provider)
- [NDL Search サイトポリシー](https://ndlsearch.ndl.go.jp/help/sitepolicy)
- [API 仕様の概要](https://ndlsearch.ndl.go.jp/help/api/specifications)

継続利用についての連絡依頼や、多重アクセスを避ける注意も上記に記載されています。
返却された提供元リポジトリ番号・書誌 URL・rights は保持し、候補説明と Notes に表示します。
個別機関の条件をプラグインが自動判定するものではありません。
このソースコードの **MIT License は NDL・他機関のメタデータには適用されません**。

## インストールと有効化

### Windows の ComicTagger 配布版：ローカル プラグイン

1. ビルドで生成した `jpbooks_talker-plugin-<version>.zip` を ComicTagger の **plugins フォルダー**へ置きます。
   ZIP は展開しません。wheel（`.whl`）をそのまま置く方式も同じローダーで利用可能です。
2. 標準設定パスは通常 `%LOCALAPPDATA%\ComicTagger\plugins` です。
   `--config <フォルダー>` を指定している場合は `<フォルダー>\plugins` になります。
   実際のパスは [ComicTagger 公式のプラグイン導入手順](https://github.com/comictagger/comictagger/wiki/Installing-plugins)
   とアプリの設定・ログで確認してください。
3. ComicTagger を再起動します。
4. **Metadata Download** のソースで **Japanese Books** を選びます。
   `--list-plugins` でも `jpbooks: Japanese Books` の登録を確認できます。
5. Preferences の Japanese Books 設定では API キーを入力する必要はありません。

更新時は、このプラグインの旧 ZIP／wheel と入れ替えてください。同じプラグインの複数版を置かないでください。
ローカル ZIP は純 Python のパッケージ本体と `.dist-info` がルートにある wheel と同じ構造です。
ComicTagger 本体や依存ライブラリは ZIP に重複同梱しません。

### pip でインストールした ComicTagger

**ComicTagger と同じ Python 環境**で実行します。

```powershell
python -m pip install .
```

配布 wheel を使用する場合：

```powershell
$wheels = @(Get-ChildItem dist\comictagger_jp_talker-*-py3-none-any.whl)
if ($wheels.Count -ne 1) { throw "Expected exactly one wheel" }
python -m pip install $wheels[0].FullName
```

### ISBN を ComicInfo.xml に保存するタグ形式

beta.9 の従来の **CR** writer は `GenericMetadata.gtin` を `<GTIN>` に書き出しません。
**既存の ComicInfoXML（CIX、`comicinfoxml` 0.5 系）タグ プラグイン**を使用し、
ComicTagger の **読み込みタグ・書き込みタグの両方で CIX のみ**を選択してください。
CIX なら GTIN と Translator を保存して再表示できます。
Windows 配布版では既に同梱されている場合があります。
pip 環境で追加する場合は次を使用できます。

```powershell
python -m pip install "comictagger[cix]==1.6.0b9"
```

CR と CIX は同じ `ComicInfo.xml` を使います。GTIN を保持したい場合は書き込みに CIX のみを選択してください。
CR のみでも日本語タイトル・著者・出版社・日付等は保存できます。
互換性のため ISBN と責任表示は Notes にも残します。Kavita 側の表示・索引は Kavita の対応仕様に依存します。

#### GTIN がフェッチ後の再表示で空になる場合

Online search で値が表示された段階では、画面上の編集内容です。
タグの保存を実行して初めて CBZ に反映されます。beta.9 は保存直後にも、
選択中の読み込みタグを使って値を読み直します。

| 書き込みタグ | 読み込みタグ | 新規保存・再表示の結果 |
|---|---|---|
| CR | CR | GTIN は書き出されず、再表示でも空欄 |
| CIX | CR | XML 内に GTIN があっても、画面では空欄 |
| CIX | CIX | GTIN を保存・再表示できる |

1. 読み込みタグと書き込みタグの両方で **ComicInfoXML（CIX）**を選択します。
2. CR で読み込んだ直後など、GTIN が空欄なら Online search で再取得します。
3. タグの保存を実行してから、同じ CBZ を読み直します。

CIX が一覧にない場合は、上記の CIX 導入方法を確認してください。
両方が CIX でも消える場合は、使用中の ComicTagger と CIX のバージョン、
保存時のエラー、保存された `ComicInfo.xml` の `GTIN` 要素の有無を確認します。
Talker の標準 API から、ホストの読み込み・書き込み設定を自動変更することはできません。

GTIN 欄の赤系の表示は、保存済み／未保存の印ではありません。
beta.9 では書き込み形式の非対応項目を赤系で表示し、GTIN の値の検証で不正と判定された場合にも
背景色を変更します。CR から CIX への切り替えで解消した場合は、形式の対応範囲によるものと考えられます。

## 検索の使い方

### ISBN 検索

ComicTagger 標準のシリーズ検索欄へ、ISBN-10 または ISBN-13 を入力します。
例：`488594287X` / `4-88594-287-X` / `9784885942877` / `ISBN: 488594287X`。
空白・ハイフンを除去してチェック ディジットを検証します。ISBN-10 末尾の小文字 x も認識します。
GTIN-14 の先頭 0＋ISBN-13 も受け付けます。978/979 以外の一般商品 EAN は書籍 ISBN として扱いません。
ISBN は NDL の `isbn` 項目で検索し、著者・出版社・資料種別フィルターは外します。
同一 ISBN でも複数書誌を返すので、版・提供元・日付を確認して選択してください。

**beta.9 の標準 Talker 検索は既存 metadata / GTIN を引数に渡しません。**
既存 GTIN の自動検索はホスト API 上実現できないため、GTIN 欄から検索欄へコピーしてください。
Python 利用向けには `search_metadata(GenericMetadata)` があり、GTIN → `identifier` → series/title の順で利用します。
これはプラグイン独自の補助メソッドで、beta.9 が自動呼び出しするフックではありません。

### タイトル検索

ComicTagger の **Online search のシリーズ検索欄**へ `キングダム`、`キングダム 74`、`3月のライオン` 等を入力します。
ISBN を入力するのと同じ欄です。
著者・出版社は Preferences の **Author filter / Publisher filter** で指定できます。
検索値は CQL リテラルとして引用・エスケープし、任意の CQL を実行する検索欄にはしません。

タイトル検索の取得順は **刊行年の古い順**が既定です。
Preferences の **Title search order** で `oldest`（古い順）、`newest`（新しい順）、
`title`（従来のタイトル順）を選べます。ISBN・書誌 ID の検索条件は変えません。

取得順は、上限件数内にどの候補を含めるかを決める NDL 側の並び順です。
ComicTagger の画面上ではタイトル類似度・年・列の設定等で再度並べ替えるため、表示順を強制しません。
NDL の内部的な並び替え用日付と返却された出版日が異なる場合や、日付不詳の候補もあります。

例えば `こちら葛飾区亀有公園前派出所` は、調査時点で図書の候補が 590 件あり、
従来のタイトル順の先頭 20 件は再編集版で埋まっていました。
古い順に取得すると、本編の第 1 巻から候補に入ることを実 API で確認しています。
部分一致検索なので、再編集版なども正当な候補として残ります。版や巻番号を確認して選んでください。

Web 検索と比較するときは、検索項目、資料種別、著者・出版社、並び順、取得上限をそろえてください。
Web の「国立国会図書館・図書館」の絞り込みは、このプラグインの既定条件には含まれません。
すべての検索結果を自動取得する機能はなく、長期連載の後半の巻などは巻番号を加えて検索してください。

通常検索は、入力にある情報を使い、次の順で **0 件の場合に**検索を緩めます。

1. タイトル＋巻番号
2. タイトル＋著者
3. タイトルのみ

出版社・資料種別は明示フィルターなので維持します。Literal search では巻推測や再検索をしません。
NDL が「該当書誌なし」を `Record does not exist`（`Record does not exit` の表記も許容）という
SRU 診断で返す場合は、診断 URI と件数・書誌の有無を確認し、通常の 0 件として扱います。
それ以外の SRU 診断・ネットワーク障害時は検索条件を緩めず、エラーを表示します。
ISBN で 0 件の場合は、同じ版の候補を確認できるようタイトルと著者で検索し直してください。

### エラーのコピーと詳細ログ

エラー画面を選択して **Ctrl+C** を押すと、表示されたエラー全文をコピーできます。
貼り付け先はメモ帳などのテキスト エディターを使用してください。
ComicTagger 標準の Windows / Qt のコピー機能を使い、プラグインからも操作方法を画面に表示します。
独自の画面や ComicTagger 本体への変更は追加していません。

詳細ログは ComicTagger の cache フォルダー内 `jpbooks/latest-error.txt` に UTF-8 で保存します。
実際の絶対パスはエラー画面に表示します。プラグインのバージョン、日時、操作、検索入力、
API の接続先、例外の詳細と呼び出し履歴を記録し、次のエラーで上書きします。
標準の ComicTagger ログ画面にも同じ詳細を出力します。書き込みに失敗した場合は、その画面を案内します。
該当書誌がない通常の検索では、エラーとして記録しません。

### 複数候補・異版

NDL の 1 書誌を 1 シリーズ候補、その 1 冊を 1 issue として返します。
作品全巻を統合した架空シリーズ ID を生成しません。
ISBN・版・電子資料・文庫・新装版・完全版は NDL が提供した情報を候補説明に表示します。
提供元に区別がないものをプラグインが確実に分類することはできません。

候補にはタイトル、刊行年、出版社、説明（著者・ISBN・版・資料種別・提供元）を設定します。
同一 ISBN の候補も消しません。順序のルールは次のとおりです。

1. ISBN 完全一致（ISBN-10/13 の等価性込み）
2. NDL 蔵書系 `R100000002` の書誌
3. 著者・出版社・ISBN・日付・言語・説明・巻次の項目充足数
4. 返却書誌 ID による安定した順序

同一 ID の重複のみ除去します。先頭候補の自動採用はしません。
ComicTagger 自身が類似度・年などで再ソートするため、UI の並びが Talker の返却順と違う場合があります。
候補選択後に標準 issue 選択で巻・タイトルを確認してください。

## 設定・アクセス頻度

| 設定 | 既定 | 意味 |
|---|---|---|
| NDL material type | `books` | 図書。**紙限定ではありません** |
| Author filter | 空欄 | タイトル検索の著者 |
| Publisher filter | 空欄 | タイトル検索の出版社 |
| Maximum candidates | 20 | 1〜100。1 クエリ 1 リクエスト、ページの大量走査なし |
| Title search order | `oldest` | 取得対象を古い順／新しい順／タイトル順から選択。表示順とは別 |
| Copy subjects to Tags | 無効 | 有効時は件名のみ最大 10 件 |

`booklet` は紙、`digital` はデジタル、`online` は電子書籍・電子雑誌、`electronic` は電子資料。
空欄なら限定しません。data group の `book` と mediatype の `books` は異なる指定です。
Phase 1 は mediatype を使います。

同一プロセスの NDL アクセスを直列化し、ComicTagger 同梱の limiter で **2 秒に 1 回**までに抑えます。
これはプラグイン独自の控えめな設定で、NDL が保証する上限ではありません。
接続 timeout は 5 秒、読み取り timeout は 30 秒。エラー時の自動連続再試行はしません。
検索結果（0 件を含む）は既存 `ComicCacher` の 7 日、書誌は 1 年の有効期間を利用します。
キャッシュは ComicTagger の cache フォルダー内 `jpbooks-ndl-v1` に保存します。
要約補完は選択した書誌に SRU の要約がない場合だけ行い、未取得なら追加で 1 回通信します。
要約あり・なしの正常な詳細応答を 7 日間キャッシュし、追加 API にも同じ limiter を適用します。
Refresh を使った検索では、選択した書誌の要約も再取得します。
複数の ComicTagger プロセス間ではアクセス頻度は共有されません。

## メタデータの対応表

### Summary の情報量について

NDL の [DC-NDL 仕様](https://ndlsearch.ndl.go.jp/renkei/dcndl/version2) では、
あらすじに相当する `dcterms:abstract` と注記の `dcterms:description` は任意項目です。
Summary を次の優先順位で取得します。

1. 選択した書誌の SRU `dcterms:abstract`。
2. なければ NDL 書誌詳細 JSON の、同じ書誌にまとめられた紙の資料の要約。
3. 紙の要約もなければ、同じ書誌にまとめられたデジタルの資料の要約。

詳細 API は [外部提供インタフェース仕様書 第 1.4 版](https://ndlsearch.ndl.go.jp/file/help/api/specifications/ndlsearch_api_20260331.pdf)
の 2(7) に記載された `https://ndlsearch.ndl.go.jp/api/bib/external/search` です。
SRU から得た書誌 ID を `f-token` に指定し、返却 ID が一致した書誌の `items` だけを参照します。
項目コード `t35200` が要約、`k39022` が紙／デジタル、`k80404` が提供元です。
内部項目のため将来変更される可能性があり、不正な応答や通信失敗は標準のエラー画面で通知します。

同じ媒体内に複数の要約提供レコードがある場合は、応答順の最初の有効なレコードを使用します。
紙とデジタルの本文を連結せず、提供元・媒体・返却資料 ID を Notes に残します。
NDL が同じ書誌にまとめた資料だけが対象で、タイトルの似た他巻・別書誌から補完しません。
両 API に要約がない場合は Summary を設定しません。Web ページのスクレイピングは行いません。

「表現種別」「機器種別」「キャリア種別」等を含む `dcterms:description` は **Notes の書誌注記**へ移します。
これまで保存した Summary を消す処理ではないため、要約を取得できない資料では、
既存の注記がホストの結合設定によって残ることがあります。その場合は標準画面で修正してください。
目次と内容細目は 0.1.7 の Summary への変換対象に含まれません。
取得漏れを調べる際は、ISBN に加え、選択した NDL 書誌 URL があると候補を特定できます。

### フィールドの対応

| NDL / DC-NDL | GenericMetadata | 方針 |
|---|---|---|
| `dcterms:title` | `title` | 日本語の表示文字列を保持 |
| 既存シリーズ名／`dcterms:title` | `series` | 既存値優先。なければタイトル末尾の巻次を保守的に分離 |
| `dcndl:seriesTitle` | `notes`・候補詳細 | 出版シリーズ等の原データとして全件保持。作品名・別名には使用しない |
| `dcndl:volume` | 論理巻番号 → `issue` / `volume` | 原文は内部・Notes に保持。出力先は設定で選択 |
| タイトルの巻次 | 論理巻番号 → `issue` / `volume` | 明示値との不一致を検出。矛盾する巻番号は出力しない |
| `dcterms:creator`, `dc:creator`, `dcterms:contributor` | `credits: list[Credit]` | 責任表示優先。明示された役割を変換、不明・曖昧な役割は Other |
| `dcterms:publisher/foaf:Agent/foaf:name` | `publisher` | 複数は ` / ` で保持 |
| ISBN 型の `dcterms:identifier` | `gtin` | 検証済み ISBN-13。別 ISBN が複数なら勝手に 1 つを選ばない |
| 書誌／コンテンツの `dcterms:issued`, `dcterms:date` | `year/month/day` | 取得元を設定で選択。同一資料の compatible な値だけで精度補完 |
| `dcterms:language` | `language` | isocodes で 2 文字 ISO コードへ。jpn→ja。明示された他言語を優先 |
| `dcterms:abstract`、詳細 JSON の資料の要約 | `description` | SRU の要約 → 紙 → デジタル。本文の生成・他巻の合成なし |
| `dcterms:description` | `notes` | 書誌注記として保持。所蔵情報の注記を混ぜない |
| 書誌 `rdf:about` | `web_links: list[Url]` | 応答の HTTPS 書誌 URL から fragment だけ除去 |
| 件名・分類・NDC | 内部で別々の list | Genre の自動推測なし。Tags は任意・最大 10 件 |
| `dcndl:edition`, `dcndl:materialType` | `format`, `notes` | 返却された版／種別／URI を保持 |
| 提供元・ISBN・責任表示・rights | `notes` | 出典・識別子の追跡用 |
| ソース・書誌 ID | `data_origin`, `series_id`, `issue_id` | `MetadataOrigin("jpbooks", "Japanese Books")` |

`issue_count` / `volume_count` は分からなければ空欄。検索件数を全巻数にしません。
単行本の巻番号は既定では `issue` に設定し、以下の設定で `volume` にも出力できます。
言語がない資料を一律 ja とはしません。複数言語は最初の明示コードを使用し、未対応コードは空欄です。

### 出版年月日の取得元

Preferences の **Publication date source** で選択します。選択肢は内部値で表示されます。

| 設定値 | 意味 | 採用する日付 |
|---|---|---|
| `auto`（既定） | Automatic | デジタルと判定できる書誌のみデジタル日付を優先。それ以外は書誌日付 |
| `bibliographic` | Bibliographic date | 常に書誌日付。従来と同じ処理 |
| `digital` | Digital date | 関連付けられたデジタル資料の日付を優先。使える値がなければ書誌日付 |

NDL の [DC-NDL v3 仕様](https://ndlsearch.ndl.go.jp/renkei/dcndl/version3)に従い、
書誌とコンテンツの日付を別々に保持します。parser は日付の採用を決めません。

- 書誌日付：`BibResource/dcterms:issued`・`dcterms:date` → 既存の `BookRecord.issued`・`dates`。
- コンテンツ日付：選択書誌の `dcndl:record` で明示的にリンクされた `Item` ごとに、
  `dcterms:issued`・`dcterms:date`、資料種別・形式・注記・URI を `content_dates: list[ContentDates]` に保存。
- v2 の `dcndl:dateDigitized` は `digitized_dates`／各 `ContentDates.digitized` に別途保持し、
  コンテンツの出版日がない場合のデジタル化日として使用。
- `dcterms:available` は `available_dates`／各 `ContentDates.available` に保持しますが、
  利用可能日・期間を出版日とは断定できないため出力には使用しません。

Automatic の判定は、NDL の正式なオンライン・電子資料 URI、EPUB / PDF 等の形式、
「電子書籍」等の注記の完全一致、デジタル化日を使用します。部分一致やタイトルからの推測はしません。
Item から自動判定する場合は、選択書誌と同じ書誌 URL の Item に限定します。
紙の書誌に関連電子版が含まれるだけでは、自動的に電子版の日付を採用しません。
NDL の `mediatype=digital` 等でも紙の共通書誌が返る実例があるため、検索条件だけでは判定しません。
判定根拠がない書誌でデジタル日付を使う場合は、候補詳細を確認して `digital` を選択してください。

同一資料では `issued` を優先し、年・月・日が矛盾しない `date` で精度を補います。
対応する数値表記は `YYYY`・`YYYY-MM`・`YYYY-MM-DD` とドット区切りです。
存在しない日付・年号表記・日本語の年月日表記・日時・期間は原文を保持して変換対象から除きます。
年だけの日付に、別資料の月日を結合することはありません。

選択書誌自身のデジタル Item がある場合は、その資料に限定します。
関連電子版しかない場合、複数のデジタル資料から異なる値が得られたら先頭を採用せず、
書誌日付へ戻して警告します。年月と年月日の精度だけが異なる複数資料も自動統合しません。
有効な日付がどちらにもなければ空欄です。両方の日付が異なる場合は原表記・採用元を Notes と候補詳細に残します。
候補の年と最終タグは同じ設定を使いますが、NDL API の検索順・ソート条件は変更しません。

実例：[お兄ちゃんはおしまい!](https://ndlsearch.ndl.go.jp/books/R100000002-I029046058) の
書誌日付は `2018.7`、関連電子版の Item 日付は `2018-06-27` でした。
この紙書誌の `auto` / `bibliographic` は 2018 年 7 月、`digital` は 2018 年 6 月 27 日を返します。
これは紙の発売日を補完する設定ではなく、採用する資料の日付を変更する設定です。

0.1.7 は SRU のスキーマを `dcndl`（v2 系）から `dcndl_v3` に変更し、検索・書誌キャッシュを分離します。
旧キャッシュに不足する Item 情報は再取得するため、手動のキャッシュ削除は不要です。
ComicTagger の結合処理では新しい空欄が既存の月・日を削除しない場合があります。
精度の低い日付へ変更した場合は、不要な既存の月・日を標準画面で消してから保存してください。

### 巻番号の書き込み先

Preferences の Japanese Books 設定にある **Volume number output** で選択します。
選択肢は内部値で表示されます。論理巻番号が `2` の場合：

| 設定値 | 意味 | GenericMetadata.volume / CIX Volume | GenericMetadata.issue / CIX Number |
|---|---|---|---|
| `volume` | Volume only | 整数 `2` | 未出力 |
| `issue`（既定） | Issue only | 未出力 | 文字列 `"2"` |
| `both` | Volume and Issue | 整数 `2` | 文字列 `"2"` |

`record.volumes` は NDL の `dcndl:volume` の原文であり、出力先を変更しても書き換えません。
共通の `resolve_record_number()` が明示値・タイトル推定値・既存／要求値・採用元・不一致の有無を返します。
矛盾がなければ、従来の **明示値 → 既存／要求値 → タイトル推定値**の順を維持します。
ただし照合時には既存／要求値を渡さず、書誌由来の値と要求巻を比較します。
書誌の巻番号がない場合、直接選択した書誌の取得では要求巻を補えますが、巻指定による候補照合では一致扱いにしません。

明示値とタイトル推定値が異なる場合、または複数の異なる明示値がある場合は、
**どちらの巻番号も出力せず、Notes と候補詳細に不一致を表示**します。
要求巻を指定した取得はエラー、巻番号・年による候補照合では除外します。原データは保持します。
直接選択して要求巻なしで取得する場合は、巻番号以外の情報を取得して手動で確認できます。

明示巻次は `explicit_volume_number()` で 1 〜 3 桁の整数を抽出してから比較します。
全角数字・先頭のゼロ・`第2巻`、`1 (国王誕生の巻)`、`第１巻（国王誕生の巻）`、`volume 1` / `Volume 1` に対応します。
半角／全角の対応する丸括弧を 1 組だけ許可し、補足の意味は推測しません。
例えば `1` と `1 (国王誕生の巻)` は同じ `1` として重複除去するため、不一致にはなりません。
Notes の NDL 巻次には正規化前の原文を保持します。
「上」「下」「前編」「後編」「外伝」や `12.5` は整数へ変換しません。
範囲・分数・不明な英字付き巻次・4 桁以上の値・ネストや複数の括弧も整数への正規化対象外です。
`2024` 等を含む解釈不能な巻次は Volume / Issue の両方を未出力とし、原表記を BookRecord と Notes に保持します。
認識できない値を捨てて一致扱いにはしないため、`1` と「上」の組み合わせ等は引き続き不一致になります。
出力モードにかかわらず、解釈不能な明示巻次があれば推定・要求巻を代用せず、Notes に原表記と整数変換できない旨を残します。
再検索用の `search_metadata()` は既存 Volume を優先し、なければ Issue を検索条件に使います。
`SearchQuery.issue` は検索時の巻番号条件であり、出力する Issue とは独立しています。

**既存タグの自動削除は行いません。** beta.9 の通常の結合処理は `None` を既存値の削除として扱わないため、
Volume only へ切り替えても既存 Issue が残る場合があります。Issue only に切り替えた場合の既存 Volume も同様です。
不要なフィールドは標準画面で空欄にしてから Save Tags で保存してください。
空のタグから保存した場合は、表に記載した要素だけが CIX に書き込まれます。
Volume only では標準 issue 選択画面の番号列が空欄になるため、書名・候補詳細を確認して選択してください。
標準 UI・CIX writer・検索 API の構文は変更しません。

### 責任表示と role

責任表示の役割は次の規則で変換します（0.1.5 以降）。

| 日本語の役割 | Credit role |
|---|---|
| 著・著者・作・文・原作 | Writer |
| 漫画・作画・画・絵 | Artist |
| 原案・構成 | Plotter |
| 脚本・シナリオ | Scripter |
| 訳・訳者・翻訳・監訳 | Translator |
| 編・編者・編集 | Editor |
| 編著／原作・脚本 | Writer + Editor／Writer + Scripter |
| 線画・ペン入れ／下絵 | Inker／Penciller |
| 彩色・着色・カラー | Colorist |
| 表紙画・表紙イラスト・カバーイラスト・カバー画・装画 | Cover Artist |
| レタリング・写植・植字 | Letterer |
| 監修・解説・校閲・企画・写真・撮影・デザイン・装丁・校注・注・注釈・解題・協力・監修協力・編集協力 | Other |
| 意味が曖昧な作画原稿・文字・表紙・カバー、その他の未知の役割 | Other |

末尾の役割は空白区切り、または対応する `[]`・`［］`・`()`・`（）` で囲まれた場合に認識します。
括弧の除去・空白の整理は役割部分だけに行い、氏名を Unicode 正規化しません。
未知の役割も、括弧付き、または末尾が「担当」「協力」の空白区切りの語なら分離して Other にします。
その他の未知語は氏名と区別する根拠がないため、責任表示全体を保持して Other とします。
括弧が不正な場合も無理に除去しません。複合役割は表に記載したものだけを認識します。
人名の `・`・カンマ・セミコロン・「ほか」は分割せず、姓名の順序も変更しません。

`responsibilities` がある場合は優先し、空の場合だけ `creators` を使います。
役割を持たない creator 名だけは互換性のため Writer とし、責任表示・contributor の役割不明は Other とします。
同じ人物・同じ role は重複除去し、異なる role は保持します。
責任表示の原文は Notes に残し、著者・寄与者の原表記も Notes に保持します。

**取得時の Credit role と CIX 保存後の role は一致するとは限りません。**
beta.9 と comicinfoxml 0.5.1 では Plotter・Scripter は XML の Writer に統合され、
Artist は Penciller と Inker に保存されます。Other の専用要素はなく、元の役割は Notes で確認します。
Cover Artist は CoverArtist、Translator は Translator 要素に書き込まれますが、
この CIX reader は Translator を credits に読み戻さず、CoverArtist は Cover として読み戻します。
プラグイン独自のタグ writer や role は追加しません。

現時点では、シリーズ名は **利用可能な既存 series → `infer_volume(record.title)` で得た作品名**の順です。
巻次を分離できないタイトルは、そのまま作品名として使用します。
beta.9 は既存 series を fetch 時に渡さないので、その優先処理は `to_metadata(..., existing_series=...)` で利用可能です。
`dcndl:seriesTitle` は出版シリーズ・レーベル・雑誌名等を含み、漫画作品名とは限りません。
`Series` と候補の `aliases` には使用せず、`record.series_titles` に原文のまま保持します。
Notes と候補詳細には「NDL シリーズ表記（原データ）」として表示します。
検索欄の入力値を、選択した本の既存シリーズ名として代用することもしません。
古いキャッシュも取得時に新しい規則で変換するため、キャッシュ削除は不要です。
保存済みのタグには再フェッチして変更内容を確認し、Save Tags で反映してください。

末尾巻次の推測は `作品. 74` / `作品 74` / `作品第74巻` / `作品 volume 74` 等の区切られた 1 〜 3 桁だけです。
`volume` は空白と整数が続く場合だけ巻番号表現として消費し、数字がなければ Series に残します。`vol.` は未対応です。
巻番号の後ろに丸括弧の補足が 1 つある形式にも対応します。半角／全角の括弧と、括弧前の空白の有無を扱います。
例えば `パタリロ! : 選集. 1 (国王誕生の巻)` は Series が `パタリロ! : 選集`、論理巻番号が `1` になります。
シリーズ名の記号、完全な Title、NDL の巻次原文は保持します。
ネスト・複数・空・左右が不一致の括弧、小数、範囲、4 桁の数字は推定対象外です。
`20世紀少年`、`3月のライオン`、`7SEEDS`、`86―エイティシックス―` は変更しません。
ただし末尾数字が作品名そのものかどうかを完全には判断できません。Title の原文は常に保持します。
全角数字の変換は ISBN／巻次等の検索・数値処理だけで、表示文字列全体への NFKC 等はしません。
補助漢字・異体字セレクターは保持します。孤立したサロゲートは有効な XML 文字ではないため、
API 検索では `TalkerDataError` とし、不正 XML を保存することはしません。

内部の `BookRecord` とキャッシュの RDF 原文には分類等も残ります。補完した要約の原文は JSON キャッシュに保持します。
すべての原文フィールドを ComicInfo.xml に永続化する機能ではありません。キャッシュ失効後の完全な原文保存は保証しません。

## 開発・ビルド・テスト

文書とプラグインが提供する案内文では、英数字と日本語の間に半角スペースを入れます。
複数のカタカナ語が連続して合計 8 文字以上になる場合も、単語ごとに半角スペースを入れます。
例えば「チェック ディジット」「ローカル プラグイン」と表記します。
書誌の原文、ISBN、URL、実行するコードや検索例は、値を壊さないようそのまま保持します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
$wheels = @(Get-ChildItem dist\comictagger_jp_talker-*-py3-none-any.whl)
if ($wheels.Count -ne 1) { throw "Expected exactly one wheel" }
python scripts/build_plugin.py $wheels[0].FullName
```

テストは実際の ComicTagger beta.9 の型・ローダー・タグ writer を利用します。
fixture は公式の要素構造をもとに作った架空の書誌です。通常のテストは HTTP を mock し、実アクセスを禁止します。
GUI テストは PyQt6 の offscreen モードで標準ウィンドウを使用します。
成果物の ZIP テストは、上記ビルド後に `python -m pytest` を再実行すると実行されます。

オプトインのネットワーク テストは NDL と MADB の実 endpoint を呼び出します。
MADB だけの実行方法と通信上限は [MADB source の実装記録](docs/phase2b1_madb_source.md) を参照してください。

```powershell
$env:JPBOOKS_RUN_NETWORK_TESTS = "1"
python -m pytest -m network
Remove-Item Env:JPBOOKS_RUN_NETWORK_TESTS
```

CI ではこの環境変数を設定しません。詳細な確認元と制約は [調査記録](docs/research.md)、
検証結果と手動確認事項は [検証記録](docs/validation.md) を参照してください。

## 既知の制限と今後の予定

- 標準 API に GTIN 入力・equivalent identifiers 検索フックがなく、既存 GTIN による完全自動照合は不可。
- 現時点では表紙画像を取得しません。beta.9 の auto-tagging は表紙比較を必要とするため、
  完全自動タグ付けは対象外。標準の手動シリーズ／issue 選択を使ってください。
- 全巻をまとめるシリーズ検索ではなく、書誌単位の候補。通常は上限 20 件なので絞り込みが必要です。
- NDL API で公開対象外の書誌、巻次なし、日付不詳、役割不詳等のデータは補完できません。
- 該当書誌なしの診断だけを 0 件として扱い、その他の SRU 診断はエラーにします。
  混在した不正書誌はスキップして警告し、全件不正ならエラー。
- CR のみでは GTIN・Translator を専用要素へ保存できません。CIX をご利用ください。
- NDL 書誌の分類から漫画ジャンルを自動推定せず、Kavita での表示結果は手動確認が必要です。

今後、**MADB** を取得元にした場合、`BookSource.search/get` と `BookRecord` を再利用するアダプターを候補とします。
追加時に公式 API・ID 体系・利用条件を調査し、ソース付き ID とフィールド別出典を導入するか検討します。
MADB が漫画作品として明示するシリーズは、NDL の `series_titles` と別の、作品 ID・出典を伴う項目で扱います。
作品との対応を確認した情報だけを高信頼ソースとし、タイトルからの推測より優先する設計です。
既存値の扱いは明示的に定め、出版シリーズ名を作品の別名へ自動転用しません。
ISBN 一致だけで紙・電子・異版を合成せず、候補選択を残す方針です。
その後 **openBD**、**Google Books API**、**Rakuten Books** を取得元に追加することを検討します。

## ライセンス

本プロジェクトで作成したソースコードおよび文書は [MIT License](LICENSE) の下で提供します。ただし、文書やテストに含まれる外部提供元のメタデータ、およびその引用・加工部分には MIT License は適用されません。それらは各提供元の利用条件に従います。

MADB に由来する実例・集計は、国立美術館国立アートリサーチセンター「メディア芸術データベース」の公開データを参照し、本プロジェクトが抽出・加工して作成したものです。出典、対象データセットの版、加工内容は各資料に記載しています。データセットの再利用については[公式案内](https://github.com/mediaarts-db/dataset)を参照してください。

ComicTagger／GCD Talker の実装コードはコピーしていません。両プロジェクトは Apache-2.0 であり、依存パッケージとしての条件はそれぞれのライセンスに従います。
