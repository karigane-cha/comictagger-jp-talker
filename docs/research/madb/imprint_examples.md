# Phase 2C-2A: Imprint 実資料台帳

調査日: **2026-10-08 (JST)**。現在の Endpoint と、2026-09-24 取得の release 1.2.20 を分離した。
39 Book / 27 Series の直接 RDF、11 件の NDL 書誌、公式出版情報を比較した。
数値・別表記・雑誌名・版表示・欠損・矛盾を意図的に含めた標本であり、採用率を全体へ一般化しない。

[仕様書](../../phase2c2a_imprint_research.md) / [raw evidence](imprint_evidence.json) / [過去の台帳](examples.md)。

## 1. 読み方

`@ja-hrkt` は読み。タグなしは `(untagged)`。datatype 未記載は RDF JSON に未記載という観測であり、数値型を推定しない。
raw 値と概要表の出典由来の書名・名称には案内文の空白規則を適用して書き換えない。文字どおりの `\u3000` も原値のまま。
Book / Series の `UNAVAILABLE` は一度の制限環境の接続失敗にも記録し、後の成功で失敗履歴を消していない。
以下は各リソースの今回最後の取得結果。全 66 リソースは上限未到達・型と ID を既存 parser で確認した。
`confirmed_label` は人による出版情報の確認、`confirmed_nonlabel_for_policy` は版表示との重複による保守的な不採用、`unknown` は正解未確定。
採用可否は仕様案に対する評価であり、Imprint の書き込みは実施していない。

## 2. 集計

| 指標 | 件数 |
|---|---:|
| `books` | 39 |
| `series` | 27 |
| `book_brand_property` | 35 |
| `single_nonempty_display` | 25 |
| `multiple_nonempty_display` | 9 |
| `reading_property` | 31 |
| `nonempty_reading` | 28 |
| `publisher_equal` | 1 |
| `eligible_under_proposed_rule` | 1 |
| `wrong_adoptions_known_subset` | 0 |
| `metadata_writes` | 0 |
| `ndl_books` | 11 |
| `madb_source_explicit_ndl` | 10 |

比較状態: {'MULTIPLE': 9, 'BOTH_AGREE': 14, 'BOOK_ONLY': 9, 'NONE': 4, 'BOTH_CONFLICT': 2, 'SERIES_ONLY': 1}。
意味の正解確認: {'unknown': 34, 'confirmed_label': 4, 'confirmed_nonlabel_for_policy': 1}。未確認 34 件を誤採用 0 件の保証に含めない。

## 3. 全 Book の概要

| Book | 書名 | 出版主体 raw | Book 表示値 | Series 表示値 | 状態 | 分類・判断 |
|---|---|---|---|---|---|---|
| [M381096](https://mediaarts-db.artmuseums.go.jp/id/M381096) | ご注文はうさぎですか? | 芳文社　∥　ホウブンシャ | Kirara menu / Manga time KR comics | Manga time KR comics　／　Kirara menu | MULTIPLE | hierarchy_unverified / hold |
| [M852457](https://mediaarts-db.artmuseums.go.jp/id/M852457) | FX戦士くるみちゃん | KADOKAWA　∥　カドカワ | MFコミックス / フラッパーシリーズ | MFコミックス / フラッパーシリーズ | MULTIPLE | composite_label / hold |
| [M299519](https://mediaarts-db.artmuseums.go.jp/id/M299519) | パタリロ! | 白泉社　∥　ハクセンシャ | 白泉社文庫 | 白泉社文庫 | BOTH_AGREE | single_label / hold |
| [M292389](https://mediaarts-db.artmuseums.go.jp/id/M292389) | SLAM DUNK | 集英社　∥　シュウエイシャ | ジャンプ・コミックスデラックス | ジャンプ・コミックスデラックス | BOTH_AGREE | single_label_variant / hold |
| [M1032569](https://mediaarts-db.artmuseums.go.jp/id/M1032569) | Dear Anemone | 集英社 | ジャンプコミックス | — | BOOK_ONLY | single_label / eligible_under_proposed_rule |
| [M519976](https://mediaarts-db.artmuseums.go.jp/id/M519976) | G・defend | 冬水社　∥　トウスイシャ | 150 / ラキッシュ・コミックス | ラキッシュ・コミックス | MULTIPLE | numeric_and_label / hold |
| [M1032568](https://mediaarts-db.artmuseums.go.jp/id/M1032568) | キジトラ猫の小梅さん | 少年画報社 | ねこぱんちコミックス | — | BOOK_ONLY | single_candidate / hold |
| [M1032570](https://mediaarts-db.artmuseums.go.jp/id/M1032570) | 僕の心のヤバイやつ | 秋田書店 | Shōnen champion comics = 少年チャンピオン・コミックス | — | BOOK_ONLY | combined_alias / hold |
| [M1032672](https://mediaarts-db.artmuseums.go.jp/id/M1032672) | バイバイバイ | 集英社 | ジャンプコミックス | — | BOOK_ONLY | single_candidate / hold |
| [M1032913](https://mediaarts-db.artmuseums.go.jp/id/M1032913) | さらば、漫画よ | イースト・プレス | — | — | NONE | empty_literal / hold |
| [M1065430](https://mediaarts-db.artmuseums.go.jp/id/M1065430) | お兄ちゃんはおしまい! | 一迅社 / [頒布]講談社 | IDコミックス | — | BOOK_ONLY | publisher_roles / hold |
| [M1033548](https://mediaarts-db.artmuseums.go.jp/id/M1033548) | まあじゃんほうろうき | 竹書房 | ばんぶーこみっくす | — | BOOK_ONLY | single_candidate / hold |
| [M1033549](https://mediaarts-db.artmuseums.go.jp/id/M1033549) | Sonic wizard | 竹書房 | Bamboo comics | — | BOOK_ONLY | single_candidate / hold |
| [M1076947](https://mediaarts-db.artmuseums.go.jp/id/M1076947) | ブルーロック | 講談社 | KODANSHA BILINGUAL COMICS | — | BOOK_ONLY | single_candidate / hold |
| [M1118994](https://mediaarts-db.artmuseums.go.jp/id/M1118994) | ブルーロック | 講談社 | 講談社コミックス. 週刊少年マガジン | — | BOOK_ONLY | composite_or_magazine / hold |
| [M1080059](https://mediaarts-db.artmuseums.go.jp/id/M1080059) | 山ゆりの歌 | 若木書房 | ジュニアコミックス | 辻なおき0戦シリーズ | BOTH_CONFLICT | series_conflict / hold |
| [M189455](https://mediaarts-db.artmuseums.go.jp/id/M189455) | ZETMAN | 集英社　∥　シュウエイシャ | Young jump comics | Young jump comics | BOTH_AGREE | single_candidate / hold |
| [M189501](https://mediaarts-db.artmuseums.go.jp/id/M189501) | 純粋!デート倶楽部 | エンターブレイン | BEAM COMIX | BEAM COMIX | BOTH_AGREE | single_candidate / hold |
| [M189667](https://mediaarts-db.artmuseums.go.jp/id/M189667) | 少年の孵化する音 | 白泉社　∥　ハクセンシャ | Jets comics | Jets comics | BOTH_AGREE | single_candidate / hold |
| [M190399](https://mediaarts-db.artmuseums.go.jp/id/M190399) | 好きって言わせる方法 | 集英社　∥　シュウエイシャ | マーガレットコミックス / 別冊マーガレット | マーガレットコミックス | MULTIPLE | label_and_magazine / hold |
| [M191237](https://mediaarts-db.artmuseums.go.jp/id/M191237) | BAKUMAN。 | 集英社　∥　シュウエイシャ | ジャンプ・コミックス | ジャンプ・コミックス | BOTH_AGREE | single_candidate / hold |
| [M196308](https://mediaarts-db.artmuseums.go.jp/id/M196308) | 劇画トヨタ喜一郎 | 産業技術記念館　∥　サンギョウ ギジュツ キネンカン | — | — | NONE | missing / hold |
| [M196908](https://mediaarts-db.artmuseums.go.jp/id/M196908) | 月は東に日は西に | 白泉社 | — | — | NONE | missing / hold |
| [M197041](https://mediaarts-db.artmuseums.go.jp/id/M197041) | 赤き血のイレブン | 少年画報社 | YKコミックス / ヤングキングコミックス | ヤングキングコミックス　／　YKコミックス | MULTIPLE | multiple_variants / hold |
| [M197767](https://mediaarts-db.artmuseums.go.jp/id/M197767) | 黒い鷲 | 中央公論社　∥　チュウオウコウロンシャ | 愛蔵版 | 愛蔵版 | BOTH_AGREE | edition_statement / hold |
| [M208827](https://mediaarts-db.artmuseums.go.jp/id/M208827) | ふしぎ遊戯 玄武開伝 | 小学館　∥　ショウガクカン | 少コミフラワーコミックス | 少コミフラワーコミックス | BOTH_AGREE | single_candidate / hold |
| [M215577](https://mediaarts-db.artmuseums.go.jp/id/M215577) | 強殖装甲ガイバー | 徳間書店 / [発売]徳間書店 | 少年キャプテンコミックス | 少年キャプテンコミックス | BOTH_AGREE | publisher_roles / hold |
| [M224983](https://mediaarts-db.artmuseums.go.jp/id/M224983) | 工業哀歌バレーボーイズ　 | 講談社　∥　コウダンシャ | ヤンマガKCスペシャル | ヤンマガKCスペシャル | BOTH_AGREE | single_candidate / hold |
| [M256549](https://mediaarts-db.artmuseums.go.jp/id/M256549) | 美少女戦士セーラームーン | 講談社　∥　コウダンシャ | なかよしアニメブックス / 講談社ヒットブックス | 講談社ヒットブックス　／　なかよしアニメブックス | MULTIPLE | hierarchy_unverified / hold |
| [M280044](https://mediaarts-db.artmuseums.go.jp/id/M280044) | ドラゴンボール | 集英社 | ジャンプ・コミックス | ジャンプ・コミックス | BOTH_AGREE | edition_context_unverified / hold |
| [M307396](https://mediaarts-db.artmuseums.go.jp/id/M307396) | ドラゴンボール | 集英社 | ジャンプ・コミックス | ジャンプ・コミックス | BOTH_AGREE | single_candidate / hold |
| [M255146](https://mediaarts-db.artmuseums.go.jp/id/M255146) | AKIRA | 講談社　∥　コウダンシャ | 講談社コミックスデラックス / KC DELUXE | 講談社コミックスデラックス | MULTIPLE | multiple_variants / hold |
| [M299514](https://mediaarts-db.artmuseums.go.jp/id/M299514) | パタリロ! | 白泉社 / 白泉社　∥　ハクセンシャ / [発売]白泉社 | 花とゆめcomics / 花とゆめコミックス | 花とゆめコミックス | MULTIPLE | multiple_variants / hold |
| [M280225](https://mediaarts-db.artmuseums.go.jp/id/M280225) | ブラック・ジャック | 秋田書店 / 秋田書店　∥　アキタ ショテン | — | — | NONE | missing / hold |
| [M280574](https://mediaarts-db.artmuseums.go.jp/id/M280574) | ブラック・ジャック | 講談社　∥　コウダンシャ | 手塚治虫漫画全集 | 手塚治虫漫画全集 | BOTH_AGREE | publication_series / hold |
| [M353277](https://mediaarts-db.artmuseums.go.jp/id/M353277) | 霊媒師多比野福助 | 学習研究社 | ピチコミックスミステリーDX | ピチコミックスミステリー | BOTH_CONFLICT | series_conflict / hold |
| [M807088](https://mediaarts-db.artmuseums.go.jp/id/M807088) | 07-ghost | 一迅社　∥　イチジンシャ | Zero-sum comics / IDコミックス | IDコミックス　／　Zero-sum comics | MULTIPLE | hierarchy_unverified / hold |
| [M1079799](https://mediaarts-db.artmuseums.go.jp/id/M1079799) | 別冊こだま | 若木書房 | — | 辻なおき0戦シリーズ | SERIES_ONLY | series_only_publication_series / hold |
| [M197011](https://mediaarts-db.artmuseums.go.jp/id/M197011) | 悪は死なず | 太平洋文庫 | 太平洋文庫 | 太平洋文庫 | BOTH_AGREE | publisher_equal / hold |

## 4. 個別の raw 値・選定理由・判断

### M381096

指定例。上位・下位候補と Series の結合表記。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784832241190` (untagged) / datatype 未記載 |
| Book brand | `Kirara menu` (untagged) / datatype 未記載<br>`Manga time KR comics` (untagged) / datatype 未記載<br>`KIRARA MENU` @ja-hrkt / datatype 未記載 |
| Publisher | `芳文社　∥　ホウブンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4832200000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `619` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C334830](https://mediaarts-db.artmuseums.go.jp/id/C334830) brand | `Manga time KR comics　／　Kirara menu` (untagged) |
| Series publisher | 芳文社　∥　ホウブンシャ |
| NDL [R100000002-I023440575](https://ndlsearch.ndl.go.jp/books/R100000002-I023440575) | `Manga time KR comics. Kirara menu ; 619` / Publisher: 芳文社 / 版: 値なし |

観測比較: `MULTIPLE`。意味分類（人による判断）: `hierarchy_unverified` / `unknown`。

上位に相当する名称だけ公式情報で確認。Kirara menu の意味・階層・表示選択は未確認。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

出典: [publisher-kirara](https://houbunsha.co.jp/patron/pdf/201805_ordersheet_mangatimeKR.pdf) / `read`。2018 年の公式注文書の 4 頁で ISBN とまんがタイムＫＲコミックスの掲載を確認。Kirara menu の階層と英語同義表記は未確認。

### M852457

指定例。MF コミックスとフラッパーシリーズ。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784046806680` (untagged) / datatype 未記載 |
| Book brand | `エムエフ コミックス. フラッパー シリーズ` @ja-hrkt / datatype 未記載<br>`MFコミックス` (untagged) / datatype 未記載<br>`フラッパーシリーズ` (untagged) / datatype 未記載 |
| Publisher | `KADOKAWA　∥　カドカワ` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C449335](https://mediaarts-db.artmuseums.go.jp/id/C449335) brand | `エムエフ コミックス. フラッパー シリーズ` @ja-hrkt<br>`MFコミックス` (untagged)<br>`フラッパーシリーズ` (untagged) |
| Series publisher | KADOKAWA　∥　カドカワ |
| NDL [R100000002-I031565930](https://ndlsearch.ndl.go.jp/books/R100000002-I031565930) | `MFコミックス. フラッパーシリーズ` / Publisher: KADOKAWA / 版: 値なし |

観測比較: `MULTIPLE`。意味分類（人による判断）: `composite_label` / `confirmed_label`。

公式商品は複合レーベルを表示。Book の 2 値から下位を一つ選ぶ根拠はない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, required_identity_or_authority_conditions_not_established。

出典: [publisher-fx](https://www.kadokawa.co.jp/product/322104000242/) / `read`。対象巻と ISBN が一致。商品ページのタイトルに MFコミックス フラッパーシリーズ。

### M299519

指定例。白泉社文庫と ISBN-10。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 38 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4592880714` (untagged) / datatype 未記載 |
| Book brand | `白泉社文庫` (untagged) / datatype 未記載<br>`ハクセンシャ ブンコ` @ja-hrkt / datatype 未記載 |
| Publisher | `白泉社　∥　ハクセンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4592000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C259763](https://mediaarts-db.artmuseums.go.jp/id/C259763) brand | `白泉社文庫` (untagged)<br>`ハクセンシャ ブンコ` @ja-hrkt |
| Series publisher | 白泉社　∥　ハクセンシャ |
| NDL [R100000002-I000002347196](https://ndlsearch.ndl.go.jp/books/R100000002-I000002347196) | `白泉社文庫` / Publisher: 白泉社 / 版: 値なし |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_label` / `confirmed_label`。

公式索引本文と ISBN が一致。単一候補だが ISBN discovery は今回未実施。直接取得は未完了。

仕様案の判定: `hold`。候補: `白泉社文庫`。
棄却・保留理由: required_identity_or_authority_conditions_not_established。

出典: [publisher-patalliro](https://www.hakusensha.co.jp/comicslist/41593/) / `official_page_search_index_read`。公式ページの検索結果本文で ISBN とシリーズ名の白泉社文庫を確認。直接ページ取得は未完了。

### M292389

指定例。完全版とジャンプ・コミックスデラックス。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4088591909` (untagged) / datatype 未記載 |
| Book brand | `ジャンプ・コミックスデラックス` (untagged) / datatype 未記載<br>`ジャンプ コミックス デラックス` @ja-hrkt / datatype 未記載 |
| Publisher | `集英社　∥　シュウエイシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4080000000` (untagged) / datatype 未記載 |
| 版 | `完全版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C262152](https://mediaarts-db.artmuseums.go.jp/id/C262152) brand | `ジャンプ・コミックスデラックス` (untagged)<br>`ジャンプ コミックス デラックス` @ja-hrkt |
| Series publisher | 集英社　∥　シュウエイシャ |
| NDL [R100000002-I000002984445](https://ndlsearch.ndl.go.jp/books/R100000002-I000002984445) | `ジャンプ・コミックスデラックス` / Publisher: 集英社 / 版: 値なし |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_label_variant` / `confirmed_label`。

レーベルの意味は公式書誌で確認。句読点と空白の差を自動的に同義化しない。

仕様案の判定: `hold`。候補: `ジャンプ・コミックスデラックス`。
棄却・保留理由: required_identity_or_authority_conditions_not_established。

出典: [publisher-slam](https://www.shueisha.co.jp/books/items/contents.html?isbn=4-08-859190-9&mode=1) / `read`。完全版第 1 巻の ISBN と書誌欄のジャンプコミックス　デラックスを確認。MADB 表示との同義性は人による判定。

### M1032569

指定例。新しい書誌と直接 NDL URL。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784088841748` (untagged) / datatype 未記載 |
| Book brand | `ジャンプコミックス` (untagged) / datatype 未記載<br>`ジャンプ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `集英社` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I033671596` (untagged) / datatype 未記載 |
| NDL [R100000002-I033671596](https://ndlsearch.ndl.go.jp/books/R100000002-I033671596) | `ジャンプコミックス` / Publisher: 集英社 / 版: 値なし |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `single_label` / `confirmed_label`。

対象巻の公式書誌に同じレーベル名。現在の ISBN discovery が一意で直接 NDL URL も一致。

仕様案の判定: `eligible_under_proposed_rule`。候補: `ジャンプコミックス`。
棄却・保留理由: なし（意味確認を評価入力に与えた場合）。

出典: [publisher-anemone](https://www.shueisha.co.jp/books/items/contents.html?isbn=978-4-08-884174-8) / `read`。第 2 巻の ISBN、紙版、書誌欄のジャンプコミックスを確認。第 1 巻とは区別。

### M519976

指定例。数値を含む brand。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784864234436` (untagged) / datatype 未記載 |
| Book brand | `150` (untagged) / datatype 未記載<br>`ラキッシュ・コミックス` (untagged) / datatype 未記載<br>`150` @ja-hrkt / datatype 未記載<br>`ラキッシュ ・ コミックス ; no` @ja-hrkt / datatype 未記載 |
| Publisher | `冬水社　∥　トウスイシャ` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `no` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C342971](https://mediaarts-db.artmuseums.go.jp/id/C342971) brand | `ラキッシュ・コミックス` (untagged)<br>`ラキッシュ コミックス` @ja-hrkt |
| Series publisher | 冬水社　∥　トウスイシャ |
| NDL [R100000002-I029302662](https://ndlsearch.ndl.go.jp/books/R100000002-I029302662) | `ラキッシュ・コミックス ; no. 150` / Publisher: 冬水社 / 版: 値なし |

観測比較: `MULTIPLE`。意味分類（人による判断）: `numeric_and_label` / `unknown`。

NDL の no. 150 に対応する文字列 150 が brand に混在。番号を落とした残りの選択も意味確認なしでは許可しない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1032568

指定例。既存 EXACT 照合の再確認。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784785977382` (untagged) / datatype 未記載 |
| Book brand | `ねこぱんちコミックス` (untagged) / datatype 未記載<br>`ネコ パンチ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `少年画報社` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I033625982` (untagged) / datatype 未記載 |
| NDL [R100000002-I033625982](https://ndlsearch.ndl.go.jp/books/R100000002-I033625982) | `ねこぱんちコミックス` / Publisher: 少年画報社 / 版: 値なし |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `single_candidate` / `unknown`。

EXACT identity を再確認したが出版元本文にはレーベルが明示されていない。NDL 由来の一致は独立した意味確認ではない。

仕様案の判定: `hold`。候補: `ねこぱんちコミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

出典: [publisher-koume](https://www.shonengahosha.co.jp/book_Info.php?id=10521) / `read`。第 25 巻の ISBN と書名を確認。本文にはねこぱんちコミックスの明示がなく意味確認には使えない。

### M1032570

秋田書店。英語と日本語の結合別表記。

取得: `2026-10-08T09:58:53.310536+00:00` / query `imprint-book-02` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784253226707` (untagged) / datatype 未記載 |
| Book brand | `Shōnen champion comics = 少年チャンピオン・コミックス` (untagged) / datatype 未記載<br>`Shōnen champion comics = ショウネン チャンピオン ・ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `秋田書店` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I033670009` (untagged) / datatype 未記載 |
| NDL [R100000002-I033670009](https://ndlsearch.ndl.go.jp/books/R100000002-I033670009) | `Shōnen champion comics = 少年チャンピオン・コミックス` / Publisher: 秋田書店 / 版: 特装版 |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `combined_alias` / `unknown`。

英語と日本語が = で結合。特装版を含む書誌だが別表記関係と出力選択は未確認。

仕様案の判定: `hold`。候補: `Shōnen champion comics = 少年チャンピオン・コミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1032672

新しい書誌。Series 未接続とジャンプコミックス。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784088842325` (untagged) / datatype 未記載 |
| Book brand | `ジャンプコミックス` (untagged) / datatype 未記載<br>`ジャンプ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `集英社` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I033671615` (untagged) / datatype 未記載 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `ジャンプコミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1032913

空文字 brand と新しい直接 NDL URL。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784781623733` (untagged) / datatype 未記載 |
| Book brand | `` (untagged) / datatype 未記載<br>`` @ja-hrkt / datatype 未記載 |
| Publisher | `イースト・プレス` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I033686059` (untagged) / datatype 未記載 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `NONE`。意味分類（人による判断）: `empty_literal` / `unknown`。

空の表示と空の読みは raw に保持。出版レーベルの欠損として補完しない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: none, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1065430

一迅社と頒布元の講談社を区別。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784758087575` (untagged) / datatype 未記載 |
| Book brand | `IDコミックス` (untagged) / datatype 未記載<br>`ID コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `一迅社` (untagged) / datatype 未記載<br>`[頒布]講談社` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I034206797` (untagged) / datatype 未記載 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `publisher_roles` / `unknown`。

一迅社と [頒布]講談社は別の役割。頒布元だけでレーベルの所属を確定しない。

仕様案の判定: `hold`。候補: `IDコミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1033548

ひらがな表示と読みの区別。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4884757602` (untagged) / datatype 未記載 |
| Book brand | `バンブー コミックス` @ja-hrkt / datatype 未記載<br>`ばんぶーこみっくす` (untagged) / datatype 未記載 |
| Publisher | `竹書房` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I033715585` (untagged) / datatype 未記載 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `ばんぶーこみっくす`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1033549

英語表示と空の読み。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4884758536` (untagged) / datatype 未記載 |
| Book brand | `Bamboo comics` (untagged) / datatype 未記載<br>`` @ja-hrkt / datatype 未記載 |
| Publisher | `竹書房` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I033715602` (untagged) / datatype 未記載 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `Bamboo comics`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1076947

バイリンガル版の英語レーベル候補。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 38 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784065405918` (untagged) / datatype 未記載 |
| Book brand | `KODANSHA BILINGUAL COMICS` (untagged) / datatype 未記載<br>`` @ja-hrkt / datatype 未記載 |
| Publisher | `講談社` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I034296254` (untagged) / datatype 未記載 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `KODANSHA BILINGUAL COMICS`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1118994

セット書誌。レーベルと雑誌名を含む単一文字列。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 33 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | —（完全取得範囲で値なし） |
| Book brand | `コウダンシャ コミックス. シュウカン ショウネン マガジン` @ja-hrkt / datatype 未記載<br>`講談社コミックス. 週刊少年マガジン` (untagged) / datatype 未記載 |
| Publisher | `講談社` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | `` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `NDLサーチ` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | `https://ndlsearch.ndl.go.jp/books/R100000002-I034819932` (untagged) / datatype 未記載 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOOK_ONLY`。意味分類（人による判断）: `composite_or_magazine` / `unknown`。

単一文字列に講談社コミックスと週刊少年マガジンが含まれ、ISBN も欠損。単一表示というだけでは安全でない。

仕様案の判定: `hold`。候補: `講談社コミックス. 週刊少年マガジン`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1080059

古い出版社の汎用的レーベル名。

取得: `2026-10-08T09:58:53.573129+00:00` / query `imprint-book-03` / `complete` / 19 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | —（完全取得範囲で値なし） |
| Book brand | `ジュニアコミックス` (untagged) / datatype 未記載<br>`ジュニアコミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `若木書房` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | —（完全取得範囲で値なし） |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C285138](https://mediaarts-db.artmuseums.go.jp/id/C285138) brand | `辻なおき0戦シリーズ` (untagged)<br>`ツジ ナオキ 0セン シリーズ` @ja-hrkt |
| Series publisher | 若木書房　∥　ワカギショボウ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_CONFLICT`。意味分類（人による判断）: `series_conflict` / `unknown`。

Book のジュニアコミックスと Series の辻なおき0戦シリーズが不一致。

仕様案の判定: `hold`。候補: `ジュニアコミックス`。
棄却・保留理由: both_conflict, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M189455

言語タグなしの英語表示。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784088774169` (untagged) / datatype 未記載 |
| Book brand | `Young jump comics` (untagged) / datatype 未記載 |
| Publisher | `集英社　∥　シュウエイシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4080000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C268475](https://mediaarts-db.artmuseums.go.jp/id/C268475) brand | `Young jump comics` (untagged)<br>`Young jump comics` @ja-hrkt |
| Series publisher | 集英社　∥　シュウエイシャ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `Young jump comics`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M189501

旧発行主体と現在のレーベル移管の検証課題。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4757719094` (untagged) / datatype 未記載 |
| Book brand | `ビーム コミックス` @ja-hrkt / datatype 未記載<br>`BEAM COMIX` (untagged) / datatype 未記載 |
| Publisher | `エンターブレイン` (untagged) / datatype 未記載 |
| Publisher reference | `P4757700000` (untagged) / datatype 未記載 |
| 版 | `完全版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C268453](https://mediaarts-db.artmuseums.go.jp/id/C268453) brand | `ビーム コミックス` @ja-hrkt<br>`BEAM COMIX` (untagged) |
| Series publisher | エンターブレイン |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `BEAM COMIX`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M189667

旧レーベル Jets comics。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4592142268` (untagged) / datatype 未記載 |
| Book brand | `Jets comics` (untagged) / datatype 未記載 |
| Publisher | `白泉社　∥　ハクセンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4592000000` (untagged) / datatype 未記載 |
| 版 | `完全版` (untagged) / datatype 未記載 |
| productID | `1` (untagged) / datatype 未記載 |
| ma:seriesName | `伯爵カインコレクション` (untagged) / datatype 未記載<br>`ハクシャク カイン コレクション` @ja-hrkt / datatype 未記載 |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C268313](https://mediaarts-db.artmuseums.go.jp/id/C268313) brand | `Jets comics` (untagged) |
| Series publisher | 白泉社　∥　ハクセンシャ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `Jets comics`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M190399

brand に雑誌名が混在。ISBN の不正値も保持。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 36 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4088466361` (untagged) / datatype 未記載<br>`9784088466361` (untagged) / datatype 未記載 |
| Book brand | `マーガレットコミックス` (untagged) / datatype 未記載<br>`マーガレット コミックス` @ja-hrkt / datatype 未記載<br>`別冊マーガレット` (untagged) / datatype 未記載<br>`ベッサツ マーガレット` @ja-hrkt / datatype 未記載 |
| Publisher | `集英社　∥　シュウエイシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4080000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `4636` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C268155](https://mediaarts-db.artmuseums.go.jp/id/C268155) brand | `マーガレットコミックス` (untagged)<br>`マーガレット コミックス` @ja-hrkt |
| Series publisher | 集英社　∥　シュウエイシャ |
| NDL [R100000002-I000011167352](https://ndlsearch.ndl.go.jp/books/R100000002-I000011167352) | `マーガレットコミックス` / Publisher: 集英社 / 版: 値なし |

観測比較: `MULTIPLE`。意味分類（人による判断）: `label_and_magazine` / `unknown`。

別冊マーガレットは公式雑誌情報で確認。マーガレットコミックスだけに自動的に絞らない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

出典: [publisher-betsuma](https://betsuma.shueisha.co.jp/new/) / `read`。別冊マーガレットは号、表紙、掲載作品を持つ雑誌。レーベルとは独立した役割。

### M191237

ジャンプ・コミックスと新しい表記との差。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 39 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4088701646` (untagged) / datatype 未記載<br>`9784088701646` (untagged) / datatype 未記載 |
| Book brand | `ジャンプ・コミックス` (untagged) / datatype 未記載<br>`ジャンプ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `集英社　∥　シュウエイシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4080000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C267564](https://mediaarts-db.artmuseums.go.jp/id/C267564) brand | `ジャンプ・コミックス` (untagged)<br>`ジャンプ コミックス` @ja-hrkt |
| Series publisher | 集英社　∥　シュウエイシャ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `ジャンプ・コミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M196308

復刻版、非商業的発行主体、brand 欠損。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 30 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | —（完全取得範囲で値なし） |
| Book brand | —（完全取得範囲で値なし） |
| Publisher | `産業技術記念館　∥　サンギョウ ギジュツ キネンカン` (untagged) / datatype 未記載 |
| Publisher reference | `P0000088890` (untagged) / datatype 未記載 |
| 版 | `復刻版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C318692](https://mediaarts-db.artmuseums.go.jp/id/C318692) brand | 値なし |
| Series publisher | 産業技術記念館　∥　サンギョウ ギジュツ キネンカン |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `NONE`。意味分類（人による判断）: `missing` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: none, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M196908

愛蔵版と Book / Series brand 欠損。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 27 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4592138163` (untagged) / datatype 未記載 |
| Book brand | —（完全取得範囲で値なし） |
| Publisher | `白泉社` (untagged) / datatype 未記載 |
| Publisher reference | `P4592000000` (untagged) / datatype 未記載 |
| 版 | `愛蔵版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C318253](https://mediaarts-db.artmuseums.go.jp/id/C318253) brand | 値なし |
| Series publisher | 白泉社 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `NONE`。意味分類（人による判断）: `missing` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: none, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M197041

略称と正式名が並ぶ複数表示値。

取得: `2026-10-08T09:58:56.435394+00:00` / query `imprint-book-04` / `complete` / 29 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | —（完全取得範囲で値なし） |
| Book brand | `YKコミックス` (untagged) / datatype 未記載<br>`ヤング キング コミックス` @ja-hrkt / datatype 未記載<br>`ヤングキングコミックス` (untagged) / datatype 未記載<br>`YOUNG KING COMICS` @ja-hrkt / datatype 未記載 |
| Publisher | `少年画報社` (untagged) / datatype 未記載 |
| Publisher reference | `P4785900000` (untagged) / datatype 未記載 |
| 版 | `完全復刻版` (untagged) / datatype 未記載 |
| productID | `COMIC406` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C318292](https://mediaarts-db.artmuseums.go.jp/id/C318292) brand | `ヤング キング コミックス　／　YOUNG KING COMICS` @ja-hrkt<br>`ヤングキングコミックス　／　YKコミックス` (untagged) |
| Series publisher | 少年画報社 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `MULTIPLE`。意味分類（人による判断）: `multiple_variants` / `unknown`。

YK とヤングキングの同義性は未検証。Series の結合値から同義性を推定しない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M197767

単一 brand が版表示の愛蔵版。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4120017672` (untagged) / datatype 未記載 |
| Book brand | `愛蔵版` (untagged) / datatype 未記載 |
| Publisher | `中央公論社　∥　チュウオウコウロンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4120000000` (untagged) / datatype 未記載 |
| 版 | `愛蔵版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C317995](https://mediaarts-db.artmuseums.go.jp/id/C317995) brand | `愛蔵版` (untagged) |
| Series publisher | 中央公論社　∥　チュウオウコウロンシャ |
| NDL [R100000002-I000001963749](https://ndlsearch.ndl.go.jp/books/R100000002-I000001963749) | `` / Publisher: 中央公論社 / 版: 値なし |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `edition_statement` / `confirmed_nonlabel_for_policy`。

Book の schema:version と schema:brand がともに愛蔵版。版表示の混入として安全規則で棄却。出版社によるブランド不存在の証明ではない。

仕様案の判定: `hold`。候補: `愛蔵版`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M208827

特別版。異なる複数の有効 ISBN。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4091384757` (untagged) / datatype 未記載<br>`409159008X` (untagged) / datatype 未記載 |
| Book brand | `ショウコミ フラワー コミックス` @ja-hrkt / datatype 未記載<br>`少コミフラワーコミックス` (untagged) / datatype 未記載 |
| Publisher | `小学館　∥　ショウガクカン` (untagged) / datatype 未記載 |
| Publisher reference | `P4090000000` (untagged) / datatype 未記載 |
| 版 | `ドラマCD付きプレミアム版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C312981](https://mediaarts-db.artmuseums.go.jp/id/C312981) brand | `ショウコミ フラワー コミックス` @ja-hrkt<br>`少コミフラワーコミックス` (untagged) |
| Series publisher | 小学館　∥　ショウガクカン |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `少コミフラワーコミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M215577

発行・発売の役割付き publisher。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 40 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4198390304` (untagged) / datatype 未記載<br>`4198395306` (untagged) / datatype 未記載 |
| Book brand | `少年キャプテンコミックス` (untagged) / datatype 未記載<br>`ショウネンキヤプテン コミツクス` @ja-hrkt / datatype 未記載 |
| Publisher | `徳間書店` (untagged) / datatype 未記載<br>`[発売]徳間書店` (untagged) / datatype 未記載 |
| Publisher reference | `P4190000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `82` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C310329](https://mediaarts-db.artmuseums.go.jp/id/C310329) brand | `少年キャプテンコミックス` (untagged)<br>`ショウネンキャプテン コミックス` @ja-hrkt |
| Series publisher | 徳間書店 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `publisher_roles` / `unknown`。

発行・発売を区別。複数の ISBN があり一意性未検証。

仕様案の判定: `hold`。候補: `少年キャプテンコミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M224983

ヤンマガ KC と番号 productID。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 32 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4063613135` (untagged) / datatype 未記載 |
| Book brand | `ヤンマガKCスペシャル` (untagged) / datatype 未記載<br>`ヤンマガ KC スペシャル` @ja-hrkt / datatype 未記載 |
| Publisher | `講談社　∥　コウダンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4060000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `1313` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C306033](https://mediaarts-db.artmuseums.go.jp/id/C306033) brand | `ヤンマガKCスペシャル` (untagged)<br>`ヤンマガ KC スペシャル` @ja-hrkt |
| Series publisher | 講談社　∥　コウダンシャ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `ヤンマガKCスペシャル`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M256549

上位・下位候補の複数値。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 36 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4061777432` (untagged) / datatype 未記載 |
| Book brand | `なかよしアニメブックス` (untagged) / datatype 未記載<br>`講談社ヒットブックス` (untagged) / datatype 未記載<br>`コウダンシャ ヒット ブックス` @ja-hrkt / datatype 未記載<br>`ナカヨシ アニメ ブックス` @ja-hrkt / datatype 未記載 |
| Publisher | `講談社　∥　コウダンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4060000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `42` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C293223](https://mediaarts-db.artmuseums.go.jp/id/C293223) brand | `講談社ヒットブックス　／　なかよしアニメブックス` (untagged)<br>`コウダンシャ ヒット ブックス　／　ナカヨシ アニメ ブックス` @ja-hrkt |
| Series publisher |  |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `MULTIPLE`。意味分類（人による判断）: `hierarchy_unverified` / `unknown`。

複数のレーベル候補が Series では一つの結合表記になる。階層順と選択方針は未確認。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M280044

作品の通常版と完全版を区別。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 29 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `408873453X` (untagged) / datatype 未記載 |
| Book brand | `ジャンプ・コミックス` (untagged) / datatype 未記載<br>`ジャンプ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `集英社` (untagged) / datatype 未記載 |
| Publisher reference | `P4080000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C257147](https://mediaarts-db.artmuseums.go.jp/id/C257147) brand | `ジャンプ・コミックス` (untagged)<br>`ジャンプ コミックス` @ja-hrkt |
| Series publisher | 集英社 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `edition_context_unverified` / `unknown`。

Book には版表示がなく Series は完全版。ISBN 一致や Series 関係だけでは版情報を補って確定しない。

仕様案の判定: `hold`。候補: `ジャンプ・コミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M307396

同作品の完全版と通常版を比較。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 35 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4088734440` (untagged) / datatype 未記載 |
| Book brand | `ジャンプ・コミックス` (untagged) / datatype 未記載<br>`ジャンプ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `集英社` (untagged) / datatype 未記載 |
| Publisher reference | `P4080000000` (untagged) / datatype 未記載 |
| 版 | `完全版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C257147](https://mediaarts-db.artmuseums.go.jp/id/C257147) brand | `ジャンプ・コミックス` (untagged)<br>`ジャンプ コミックス` @ja-hrkt |
| Series publisher | 集英社 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `single_candidate` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `ジャンプ・コミックス`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M255146

KC DELUXE と日本語別表記。

取得: `2026-10-08T09:58:59.443797+00:00` / query `imprint-book-05` / `complete` / 44 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4061037110` (untagged) / datatype 未記載 |
| Book brand | `講談社コミックスデラックス` (untagged) / datatype 未記載<br>`KC deluxe` @ja-hrkt / datatype 未記載<br>`KC DELUXE` (untagged) / datatype 未記載 |
| Publisher | `講談社　∥　コウダンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4060000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `KCDX-11` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C293897](https://mediaarts-db.artmuseums.go.jp/id/C293897) brand | `講談社コミックスデラックス` (untagged)<br>`KC deluxe` @ja-hrkt |
| Series publisher | 講談社　∥　コウダンシャ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `MULTIPLE`。意味分類（人による判断）: `multiple_variants` / `unknown`。

KC DELUXE と日本語名は別表示候補。Series は日本語名だけ。自動的に別表記として統合しない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M299514

複数表記と複数 publisher。文庫版との比較。

取得: `2026-10-08T09:59:02.445712+00:00` / query `imprint-book-06` / `complete` / 42 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | —（完全取得範囲で値なし） |
| Book brand | `花とゆめcomics` (untagged) / datatype 未記載<br>`ハナ ト ユメ comics` @ja-hrkt / datatype 未記載<br>`花とゆめコミックス` (untagged) / datatype 未記載<br>`ハナトユメ コミックス` @ja-hrkt / datatype 未記載 |
| Publisher | `白泉社` (untagged) / datatype 未記載<br>`白泉社　∥　ハクセンシャ` (untagged) / datatype 未記載<br>`[発売]白泉社` (untagged) / datatype 未記載 |
| Publisher reference | `P4592000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `180` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C259719](https://mediaarts-db.artmuseums.go.jp/id/C259719) brand | `花とゆめコミックス` (untagged)<br>`ハナ ト ユメ コミックス` @ja-hrkt |
| Series publisher | 白泉社　∥　ハクセンシャ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `MULTIPLE`。意味分類（人による判断）: `multiple_variants` / `unknown`。

日本語と comics 表記が複数。Series が一つでも Book の曖昧さを消さない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M280225

Book brand 欠損と別版の Series を検証。

取得: `2026-10-08T09:59:02.445712+00:00` / query `imprint-book-06` / `complete` / 34 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4253099696` (untagged) / datatype 未記載 |
| Book brand | —（完全取得範囲で値なし） |
| Publisher | `秋田書店` (untagged) / datatype 未記載<br>`秋田書店　∥　アキタ ショテン` (untagged) / datatype 未記載 |
| Publisher reference | `P4253000000` (untagged) / datatype 未記載 |
| 版 | `豪華版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C280024](https://mediaarts-db.artmuseums.go.jp/id/C280024) brand | 値なし |
| Series publisher |  |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `NONE`。意味分類（人による判断）: `missing` / `unknown`。

出版元による意味確認がなく、表示可能性を出版レーベルの証明と扱わない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: none, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M280574

手塚治虫漫画全集。叢書とレーベルの境界。

取得: `2026-10-08T09:59:02.445712+00:00` / query `imprint-book-06` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `406367410X` (untagged) / datatype 未記載 |
| Book brand | `手塚治虫漫画全集` (untagged) / datatype 未記載<br>`テズカ オサム マンガ ゼンシュウ` @ja-hrkt / datatype 未記載 |
| Publisher | `講談社　∥　コウダンシャ` (untagged) / datatype 未記載 |
| Publisher reference | `P4060000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `MT410` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C276685](https://mediaarts-db.artmuseums.go.jp/id/C276685) brand | `手塚治虫漫画全集` (untagged)<br>`シュズカ オサム マンガ ゼンシュウ` @ja-hrkt |
| Series publisher | 講談社　∥　コウダンシャ |
| NDL [R100000002-I000007530508](https://ndlsearch.ndl.go.jp/books/R100000002-I000007530508) | `手塚治虫漫画全集 ; 410` / Publisher: 講談社 / 版: 値なし |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `publication_series` / `unknown`。

NDL でも手塚治虫漫画全集 ; 410。全集・叢書の記述を Imprint にする方針は未確認。

仕様案の判定: `hold`。候補: `手塚治虫漫画全集`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M353277

Book / Series の DX 差異。

取得: `2026-10-08T09:59:02.445712+00:00` / query `imprint-book-06` / `complete` / 30 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `4056004188` (untagged) / datatype 未記載 |
| Book brand | `ピチコミックスミステリーDX` (untagged) / datatype 未記載<br>`ピチ コミックス ミステリー デラックス` @ja-hrkt / datatype 未記載 |
| Publisher | `学習研究社` (untagged) / datatype 未記載 |
| Publisher reference | `P4050000000` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C286629](https://mediaarts-db.artmuseums.go.jp/id/C286629) brand | `ピチコミックスミステリー` (untagged)<br>`ピチ コミックス ミステリー デラックス` @ja-hrkt |
| Series publisher | 学習研究社 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_CONFLICT`。意味分類（人による判断）: `series_conflict` / `unknown`。

Book は DX 付き、Series 表示は DX なし。Series の読みにはデラックスがあるが読みで表示差を解消しない。

仕様案の判定: `hold`。候補: `ピチコミックスミステリーDX`。
棄却・保留理由: both_conflict, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M807088

上位・下位候補と Series の結合表記。

取得: `2026-10-08T09:59:02.445712+00:00` / query `imprint-book-06` / `complete` / 31 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | `9784758031387` (untagged) / datatype 未記載 |
| Book brand | `Zero-sum comics` (untagged) / datatype 未記載<br>`ID コミックス. Zero-sum comics` @ja-hrkt / datatype 未記載<br>`IDコミックス` (untagged) / datatype 未記載 |
| Publisher | `一迅社　∥　イチジンシャ` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | `文庫版` (untagged) / datatype 未記載 |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C357047](https://mediaarts-db.artmuseums.go.jp/id/C357047) brand | `IDコミックス　／　Zero-sum comics` (untagged)<br>`ID コミックス　／　Zero-sum comics` @ja-hrkt |
| Series publisher | 一迅社　∥　イチジンシャ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `MULTIPLE`。意味分類（人による判断）: `hierarchy_unverified` / `unknown`。

ID と Zero-sum の 2 値。Series の結合表記から上下関係や正解表示を推定しない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: multiple, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M1079799

追加例。Book brand 欠損と Series brand 存在。

取得: `2026-10-08T09:59:02.445712+00:00` / query `imprint-book-06` / `complete` / 19 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | —（完全取得範囲で値なし） |
| Book brand | —（完全取得範囲で値なし） |
| Publisher | `若木書房` (untagged) / datatype 未記載 |
| Publisher reference | —（完全取得範囲で値なし） |
| 版 | —（完全取得範囲で値なし） |
| productID | —（完全取得範囲で値なし） |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | —（完全取得範囲で値なし） |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C285138](https://mediaarts-db.artmuseums.go.jp/id/C285138) brand | `辻なおき0戦シリーズ` (untagged)<br>`ツジ ナオキ 0セン シリーズ` @ja-hrkt |
| Series publisher | 若木書房　∥　ワカギショボウ |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `SERIES_ONLY`。意味分類（人による判断）: `series_only_publication_series` / `unknown`。

Book は別冊こだま、関連 Series 名は山ゆりの歌、Series brand は辻なおき0戦シリーズ。Book の出版レーベルを証明しない。

仕様案の判定: `hold`。候補: `未選択`。
棄却・保留理由: series_only, semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

### M197011

追加例。brand と publisher に同じ文字列がある。

取得: `2026-10-08T09:59:02.445712+00:00` / query `imprint-book-06` / `complete` / 26 triples。

| 項目 | raw 値 / 関係 |
|---|---|
| ISBN | —（完全取得範囲で値なし） |
| Book brand | `太平洋文庫` (untagged) / datatype 未記載 |
| Publisher | `太平洋文庫` (untagged) / datatype 未記載 |
| Publisher reference | `P0000000190` (untagged) / datatype 未記載 |
| 版 | —（完全取得範囲で値なし） |
| productID | `159` (untagged) / datatype 未記載 |
| ma:seriesName | —（完全取得範囲で値なし） |
| MADB 出典 | `メディア芸術データベースベータ版データセット` (untagged) / datatype 未記載 |
| MADB 直接 NDL URL | —（完全取得範囲で値なし） |
| Series [C318337](https://mediaarts-db.artmuseums.go.jp/id/C318337) brand | `太平洋文庫` (untagged) |
| Series publisher | 太平洋文庫 |
| NDL | 今回の実 API 取得対象外。MADB URL の存在を NDL 実取得と扱わない |

観測比較: `BOTH_AGREE`。意味分類（人による判断）: `publisher_equal` / `unknown`。

太平洋文庫が publisher と brand に同じ文字列。兼業や別の役割は未確認。

仕様案の判定: `hold`。候補: `太平洋文庫`。
棄却・保留理由: semantic_unverified_or_nonlabel, required_identity_or_authority_conditions_not_established。

## 5. 取得失敗と未確認事項

制限環境の最初の MADB 接続は `network` で失敗した。承認された環境で同じ bounded query を明示的に 1 回再実行し成功。自動リトライはない。
HTTP 429 / 503、timeout、truncated 応答は今回の成功リクエストでは未観測。採用条件の試験には後続の合成 fixture が必要。
白泉社の公式商品ページは Web 取得が 2 回 timeout した。公式ページの検索索引本文で確認した内容と、直接取得未完了を別々に保存した。
芳文社の公式注文書は PDF の抽出本文を確認した。画像取得は cache miss で失敗しており、視覚的な確認成功とは扱っていない。
公式情報で確認できた正解と、文脈からの分類候補を分離した。階層・移管・同名別ブランド・URI / blank node brand は未確定のまま。
旧台帳と今回の tracked property 値の差分は仕様書を参照。原台帳は変更していない。
