# Phase 1 調査記録

調査日：2026-09-19。実装前にワークスペースが空であることを確認。
既存ファイル、Git 管理情報、AGENTS.md、既存ライセンスはなかった。
新規コードのライセンスはユーザーが MIT を指定した。

## ComicTagger の確認元

- [ComicTagger beta.9 / ComicTalker](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictalker/comictalker.py)
- [GenericMetadata / Credit / ComicSeries / MetadataOrigin](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comicapi/genericmetadata.py)
- [Talker entry point loader](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictalker/__init__.py)
- [ローカル ZIP・wheel loader](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictaggerlib/ctsettings/plugin_finder.py)
- [設定登録](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictaggerlib/ctsettings/plugin.py)
- [auto-tagging](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictaggerlib/issueidentifier.py)
- [IssueResult](https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictaggerlib/resulttypes.py)
- [GCD Talker](https://github.com/comictagger/gcd_talker/tree/d09f08c138dc2e7af7a88a3f67440b2e428ae16b)
- [現在の develop の ComicTalker も照合](https://github.com/comictagger/comictagger/blob/develop/comictalker/comictalker.py)

beta.9 のタグは `1.6.0-beta.9`、commit は `57e5571c91c7515ee2cd594da6c780e61b056b15`。
この公式チェックアウトを Python 環境にインストールして検証する。本体コードは変更していない。
実装は新規であり、参考コードをコピーしていない。ComicTagger/GCD のライセンスは Apache-2.0。

### 必須メソッドと設定フック

`ComicTalker` は ABC の abstractmethod ではなく、以下のメソッドで `NotImplementedError` を発生させる。
引数名、位置引数、keyword-only `on_rate_limit` を beta.9 に合わせた。

| メソッド | 返却型 |
|---|---|
| `check_status(settings)` | `tuple[str, bool]` |
| `search_for_series(series_name, callback=None, refresh_cache=False, literal=False, series_match_thresh=90, *, on_rate_limit=None)` | `list[ComicSeries]` |
| `fetch_comic_data(issue_id=None, series_id=None, issue_number="", *, on_rate_limit=None)` | `GenericMetadata` |
| `fetch_series(series_id, *, on_rate_limit=None)` | `ComicSeries` |
| `fetch_issues_in_series(series_id, *, on_rate_limit=None)` | `list[GenericMetadata]` |
| `fetch_issues_by_series_issue_num_and_year(series_id_list, issue_number, year, *, on_rate_limit=None)` | `list[GenericMetadata]` |
| `register_settings(parser)` | `None` |
| `parse_settings(settings)` | `dict[str, Any]` |

Talker entry point group は `comictagger.talker`。entry point 名と Talker の id は一致必須。
GCD と同じ `settngs.Manager.add_setting()` を用い、本体が自動登録する key/url を
`file=False, cmdline=False` で上書きして非表示にする。API 認証を求めない。

`ComicSeries` は id/name だけでなく aliases/counts/description/image_url/publisher/start_year/format が必要。
`web_links` は `Url` の list、`credits` は `Credit` の list、genres/tags は set。
ISBN 用属性は **gtin**、`identifiers` という複数形属性は存在しない。
`identifier` は CoMet 系の単一文字列であり、ISBN の主保存先にはしない。

`IssueResult` はホストの画像照合結果型。Talker が返す型ではない。
beta.9 の `identify` は series・issue と表紙の比較を使用する。
`equivalent identifiers` の照会フックは、このベースクラスと呼び出し元に存在しない。
GTIN が metadata にあっても search_for_series には渡されない。
本体変更・モンキーパッチによる回避はしない。

### キャッシュ・ローカル プラグイン・タグ保存

`ComicCacher` は書誌データを任意 bytes として保存できる。
検索は 7 日、シリーズ情報は 1 年で失効する。プラグイン専用サブ ディレクトリで利用し、
本体側のキャッシュ バージョンに干渉しない。0 件も 1 個のキャッシュ エントリーとして保存する。
ホスト同梱 `comictalker.vendor.pyrate_limiter` と `RLCallBack` を使用。

ZIP と wheel はルートの `.dist-info/entry_points.txt` から発見される。
ローダーは読み込み後に一時 sys.path とプラグインの sys.modules 登録を戻す。
したがって自パッケージの実行時遅延 import を避け、必要なプラグイン内モジュールはトップレベルで import する。

標準 `TaggerWindow.populate_combo_boxes` が `talker.name` を Metadata Download に追加する。
標準シリーズ UI は Talker 返却候補を独自再ソートする。順位をホスト UI まで強制することはできない。
標準 CR writer には GTIN/Translator の保存コードがない。
ComicTagger が extras に指定する既存 `comicinfoxml==0.5.*` の CIX writer には両者があり、
同じ `GenericMetadata` から保存可能。独自 writer を追加する必要はない。

## NDL Search の確認元

- [外部提供インタフェース仕様 第 1.4 版 2026-03-31](https://ndlsearch.ndl.go.jp/file/help/api/specifications/ndlsearch_api_20260331.pdf)
- [data group / mediatype 一覧](https://ndlsearch.ndl.go.jp/file/help/api/specifications/ndlsearch_api_ap2_20240401.pdf)
- [DC-NDL RDF v2.2](https://ndlsearch.ndl.go.jp/renkei/dcndl/version2)
- [API 利用条件](https://ndlsearch.ndl.go.jp/help/api)
- [メタデータ提供機関と利用条件](https://ndlsearch.ndl.go.jp/help/api/provider)

エンドポイントは `https://ndlsearch.ndl.go.jp/api/sru`。
`operation=searchRetrieve`、`version=1.2`、`recordSchema=dcndl_v3`、`recordPacking=xml` を明示。
省略時のスキーマは dc、packing は string なので省略しない。
0.1.6 までは `dcndl`（v2 系）。0.1.7 はコンテンツ日付を正式に取得するため `dcndl_v3` を使用。
API キーは不要。

CQL 正式項目の isbn/title/creator/publisher/mediatype/from/until/itemno を確認。
ISBN-10/13 はサーバ側で両形式に変換して完全一致する。
タイトル・著者・出版社は部分一致。値に AND/OR がある時の仕様上の注意から、` = ` 前後に空白を付ける。
値の引用符・バック スラッシュ・masking 文字をエスケープし、URL エンコードは requests へ任せる。
上限は API 側 500 件、501 件以降の取得不可。Phase 1 は既定 20 件・最大 100 件・1 ページに抑える。
`from`/`until` は内部 SearchQuery に準備し、GUI 設定は Phase 1 では追加しない。

`mediatype=books` は図書であり紙の意味ではない。`booklet` が紙。
`digital` は形態、`online` は電子書籍・電子雑誌、`electronic` は電子資料。
data group `book` は巻号・図書等の基本単位書誌で、`books` とは別。

### XML の名前空間

| prefix（任意） | namespace URI |
|---|---|
| sru | `http://www.loc.gov/zing/srw/` |
| diag | `http://www.loc.gov/zing/srw/diagnostic/` |
| rdf | `http://www.w3.org/1999/02/22-rdf-syntax-ns#` |
| rdfs | `http://www.w3.org/2000/01/rdf-schema#` |
| dc | `http://purl.org/dc/elements/1.1/` |
| dcterms | `http://purl.org/dc/terms/` |
| dcndl | `http://ndl.go.jp/dcndl/terms/` |
| foaf | `http://xmlns.com/foaf/0.1/` |

`ElementTree` の namespace 辞書と完全修飾属性名を使用する。ローカル名だけの探索はしない。
API 通信は HTTPS だが namespace URI の http を勝手に https へ変更してはいけない。

### 実応答の観察

ISBN `488594287X` で実際に正常 SRU 応答を確認し、同一 ISBN の 2 書誌があった。
内容を配布 fixture にはコピーせず、必要構造を架空書誌 fixture で再現した。

- `recordData/rdf:RDF` の下に `BibAdminResource`, `BibResource`, `Item` が並ぶ。
- 書誌 URL は `BibResource/@rdf:about` の `https://ndlsearch.ndl.go.jp/books/<token>#material`。
  fragment を外して Web へ設定し、返却 token を itemno 検索に使う。ISBN から URL を作らない。
- 同じ `BibResource/@rdf:about` の 2 つ目に所蔵参照だけがある場合がある。
  タイトルを持つ本体ノードだけを解析し、Item の所蔵注記を Summary へ入れない。
- DC-NDL RDF を返していても `recordSchema` のラベルが `info:srw/schema/1/dc-v1.1` だった。
  ラベルのみで拒否せず、ペイロードの namespace を検証する。
- 著者は `dcterms:creator/foaf:Agent/foaf:name` と `dc:creator` の責任表示がある。
- 出版年だけの `issued` と、年月が詳しい `date` が同時にあった。
- ISBN は `rdf:datatype="http://ndl.go.jp/dcndl/terms/ISBN"`、ハイフン付きもある。
- 言語が jpn の書誌と ja の書誌があった。
- 件名の rdf:Description/rdf:value と、NDC/NDLC の rdf:resource が別々にあった。
- 書誌なし検索で、numberOfRecords=0 ではなく `Record does not exist` の SRU 診断も観測。

NDL→GenericMetadata の最終マッピングと安全な巻次推測のルールは README に記載。
申請・attribution は NDL API 利用案内に従い「NDL サーチの API を使用」と明記し、機関別条件へのリンクを用意する。

## 0.1.1 の不具合調査

利用者から指定された `4-08-852811-5` はチェック ディジットが有効な ISBN-10 で、
対応する ISBN-13 は `9784088528113`。両形式の ISBN 検索で、HTTP 200 とともに
`info:srw/diagnostic/1/1`、`Record does not exist`、`An error occurred` が返った。
公式例と同じ空白なしの CQL、ハイフン付き ISBN でも同じ結果だった。
別途タイトル＋著者検索では件数を持つ正常な応答を確認した。
したがって、今回確認した応答は該当書誌なしであり、認証不足や ISBN の検証失敗ではない。
API で見つからない理由や、NDL の全サービスに書誌が存在しないことまでは断定できない。

以前はすべての SRU 診断を `TalkerDataError` にしていた。
0.1.1 では上記の URI と文言が一致し、書誌がなく件数も矛盾しない場合だけ 0 件へ変換する。
利用者の報告にあった `Record does not exit` という表記も許容する。
一般エラーにも使われる URI なので、URI だけでは判定しない。

beta.9 の `comictaggerlib.ui.qtutils.critical()` は標準の `QMessageBox` を使う。
Windows で実際に `Ctrl+C` を送信し、本文・検索入力・ログ保存先がクリップボードへ入ることを検証した。
Talker の例外コードは維持し、操作案内だけを追加する。独自 GUI や本体の置換は不要。
詳細ログは UTF-8 の `jpbooks/latest-error.txt` と標準の logging に出力する。

## 0.1.2 の要約取得調査

対象は [NDL 書誌 R100000002-I031565930](https://ndlsearch.ndl.go.jp/books/R100000002-I031565930)、
ISBN `9784046806680`。SRU の書誌 ID 検索と ISBN 検索を照合したところ、
`dcterms:abstract` はなく、`dcterms:description` に表現種別・機器種別・キャリア種別があった。
JPRO を指定した検索と `dcndl_v3` の応答でも、この書誌の要約は得られなかった。

[外部提供インタフェース仕様書 第 1.4 版](https://ndlsearch.ndl.go.jp/file/help/api/specifications/ndlsearch_api_20260331.pdf)
の 2(7) は、内部項目を確認する詳細 JSON の公式エンドポイントを記載している。
`https://ndlsearch.ndl.go.jp/api/bib/external/search` に `cs=bib` と返却書誌 ID の `f-token` を渡す。
この応答の、同じ書誌の `items` に紙版・デジタル版の JPRO 要約が含まれることを確認した。

実応答で確認した項目は、要約 `items[].meta.t35200[].v`、媒体 `k39022[].v`、提供元 `k80404[].v`。
JSON の内部項目コードの安定性は保証されていないため、専用パーサーに分離する。
同じ書誌 ID のみを対象に、紙を優先し、紙に要約がない場合だけデジタルを選ぶ。
関連作品の `rels` は参照せず、ISBN から資料 ID を生成しない。

SRU で候補を選んだ後、その書誌の要約が欠落している場合だけ詳細 API を呼ぶ。
検索時の全候補への追加アクセスはしない。同じ rate limiter と ComicCacher を使用する。
API の利用条件は従来どおり [提供機関別の案内](https://ndlsearch.ndl.go.jp/help/api/provider) に従う。
プラグインは Web ページのスクレイピングや JPRO への直接接続を追加していない。

GTIN の赤系表示も本体ソースで確認した。`update_tag_tweaks()` は書き込み形式の対応項目で
入力欄の有効状態と色を変える。別途 `gtin_changed()` は値の検証失敗時に背景色を変える。
保存済み／未保存の状態表示ではなく、CR が GTIN 非対応であることと区別して説明する。

## 0.1.3 のタイトル検索調査

利用者の比較対象は、タイトル `こちら葛飾区亀有公園前派出所`、NDL・図書館を対象とした
刊行年の古い順の Web 検索。一方、従来実装は `title` と `mediatype=books` を条件にし、
API 既定のタイトル順の先頭 20 件だけを取得していた。
実応答は 590 件で、先頭 20 件すべてが作品名を副題に含む再編集版だった。
受信していない本編の巻は、ComicTagger で再ソートしても候補に戻せない。

NDL の仕様書の SRU 1.2 `sortBy` を実際に照合した。
`AND sortBy=issued_date/sort.ascending` で本編の第 1 巻等が先頭側に入った。
一般的な CQL の末尾 `sortBy issued_date/sort.ascending` は、この API では直前の
`mediatype` の値に含めて解釈され、診断エラーになったため使用しない。
日付の内部索引が不明な候補等もあり、返却された `issued` の厳密な昇順とは限らない。

プラグインは取得順の設定を追加し、既定を古い順に変更した。設定値から固定のソート句だけを選び、
入力文字列をソート句として実行しない。ソート句は検索キャッシュのキーにも含まれる。
既存のタイトル順の検索キャッシュを、古い順の結果として再利用しない。
Web の対象機関の絞り込みまでは同一化せず、ComicTagger の表示順も変更しない。

## 0.1.7 のデジタル日付調査

2026-09-21 に公式仕様と保存済み実応答を確認し、対象書誌を実 API でも再検証した。

- [DC-NDL v3 仕様](https://ndlsearch.ndl.go.jp/renkei/dcndl/version3)：
  BibResource の書誌日付と Item の出版年月日（コンテンツ）を分離して定義。
- [v3 の変更点](https://ndlsearch.ndl.go.jp/renkei/dcndl/major_changes_version3)：
  `dcndl:dateDigitized` を停止し、Item 配下の `dcterms:date` / `dcterms:issued` へ移す。
  媒体変換後の出版・作成日を表し、紙の発売日と同一とは限らない。
- [NDL タイプ語彙](https://ndlsearch.ndl.go.jp/file/renkei/dcndl/ndltype_ver.1.1_20240105.pdf)：
  OnlineResource・OnlineJournal・ElectronicResource・ComputerDisc・Magneticdisk・Document の URI を確認。

`R100000002-I029046058` は書誌 issued が `2018`、date が `2018.7`。
リンクされた電子書籍 Item `R100000137-I75806750000002020618` は date が `2018-06-27`、形式が EPUB。
当該電子版の ID を検索しても紙の共通書誌が返った。検索時の mediatype だけでは、返却書誌自身の媒体を確定できない。
`吾輩は猫である` の online 検索では JPRO の独立電子書誌も確認した。
その書誌 `R100000137-I396sj00200000000000e` は自己 Item に電子書籍・EPUB の根拠がある一方、
Item に日付はなく、書誌 issued の `2021-09-08` へ fallback する。

正式にリンクされた Item だけを URI ごとに保存し、日付・種別・形式を別々に保持する。
dateDigitized は v2 の入力互換用に保持。available は公開可能期間も表すため採用しない。
複数の電子版を横断して精度を補完せず、日付が異なる場合は書誌日付へ戻して警告する。
原応答は配布外の `.research` に置き、通常テストは最小限の合成 XML を使用する。

## Phase 2（MADB）の候補設計

まず公式 API・利用条件・書誌単位と作品単位の ID を調査する。今回の NDL コードから推測しない。
`BookSource` protocol の別実装と `BookRecord` の変換アダプターを追加する構成を候補とする。
必要になった時にだけ、ソース付き永続 ID、作品と版の別モデル、フィールド単位の出典を追加する。
`BookRecord.series_titles` は NDL の出版シリーズ等の原データを表す項目として維持する。
MADB の漫画作品シリーズはこの項目へ代入せず、作品名・作品 ID・出典を持つ独立した項目を追加する。
選択書誌と作品の対応を確認した場合だけ、その項目をタイトル推測より高信頼の `Series` 候補にする。
別名も作品の別名と明示された情報に限定し、出版シリーズ名とは分離する。
Phase 1 は既存値 → タイトル推測のみとし、MADB の取得・統合処理や未使用のモデルは追加しない。
ISBN 一致で誤って紙・電子・新装版を上書き統合しないこと、ComicTagger 標準候補選択を維持することを優先する。
