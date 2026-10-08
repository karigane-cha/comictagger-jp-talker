# Phase 2C-2A: MADB Imprint 調査・候補評価仕様案

調査日: **2026-10-08 (JST)**。対象: **v0.3.0 / Phase 2C-1**。
状態: **調査・設計のみ。候補評価 API、設定、補完処理は未実装。**

## 1. 目的・範囲・判断

MADB の `schema:brand` を `GenericMetadata.imprint` に安全に使える条件を、既存の実装、公式資料、実資料から定める。
**推奨は CONDITIONAL GO。Phase 2C-2B の純粋な候補評価を進め、Phase 2C-2C の自動補完は意味確認の取得方法が確立するまで保留する。**

単一の表示名、Book / Series 一致、NDL の叢書表記一致だけでは出版レーベルを証明できない。
実資料には版表示、雑誌名、出版叢書、出版社と同じ名称、番号、別表記、階層の結合がある。
文字列を整形して一つに選ぶ規則や、調査根拠のないレーベル辞書を導入しない。

成果物は本書、[実資料台帳](research/madb/imprint_examples.md)、[機械可読 evidence](research/madb/imprint_evidence.json)、
[独立した取得・検証スクリプト](../scripts/research_madb_imprint.py)。既存資料は変更していない。
本書の採用条件は今後の仕様案、台帳の raw 値は観測、意味分類と採用可能性は分析による判断である。

## 2. 既存実装と過去の成果

確認した資料: [Phase 2A](phase2_madb_spec.md)、[source](phase2b1_madb_source.md)、[linkage](phase2b2_linkage.md)、
[Series 補完](phase2c1_series_supplement.md)、[過去の台帳](research/madb/examples.md)、
[過去の evidence](research/madb/evidence.json)、[過去のクエリ](research/madb/queries/)、[検証記録](validation.md)、[README](../README.md)。
特に Phase 2A の §13 は、複数 brand、`150`、読み、Series の結合値を既に記録している。
これらは今回初めて発見した事実として扱わず、現在の Endpoint で再確認した。

| 実装 | 現在の保持・動作 | 再利用と必要な拡張 |
|---|---|---|
| [madb_models.py](../comictagger_jp_talker/sources/madb_models.py) | Book / Series の `labels: tuple[RDFTerm, ...]`。`kind`、`value`、`datatype`、`language` を保持 | そのまま候補抽出の入力にできる。`labels` は意味確認済みレーベルの配列ではない |
| [madb_parser.py](../comictagger_jp_talker/sources/madb_parser.py) | 両モデルの labels は HTTPS `schema:brand` の全 term。全直接 triple は `statements` に保持 | URI / blank node を文字列表示に格上げしない。Book の同一 statement は重複排除、Series は raw の重複も保持 |
| [madb_queries.py](../comictagger_jp_talker/sources/madb_queries.py) | ISBN-10 / 13、型・URI 検証、bounded SELECT。候補既定 20、triple 既定 300 | 新しい identity query やタイトル照合は不要 |
| [madb.py](../comictagger_jp_talker/sources/madb.py) | `get_for_series_linkage()` は Book / Series の全直接 triple。Agents / Holdings は未要求 | brand、publisher、版、出典も既に取得。取得スコープ名は歴史的名称であり Imprint にも使える |
| [linkage.py](../comictagger_jp_talker/linkage.py) | `phase2b2-v1`、MATCHED / EXACT / STRONG、直接 URL の矛盾、discovery の truncated を保持 | アルゴリズムを変更しない。公開 `LinkageResult` は RDF bundle を返さないため、呼び出し側で snapshot を共有する契約が必要 |
| [provenance.py](../comictagger_jp_talker/provenance.py) | `FieldEvidence`、Series 名の表示・読み・その他分類、NDL / MADB の比較 | raw term と参照情報は再利用。取得日時・query ID・上位下位・意味確認は別の評価コンテキストで保持 |
| [series_supplement.py](../comictagger_jp_talker/series_supplement.py) | OFF、Series がある場合は早期 return。安全な MADB_ONLY の単一候補だけ採用 | この早期 return を Imprint の実行条件として流用しない。Series 比較は Book / Series brand 比較でもない |
| [mapping.py](../comictagger_jp_talker/mapping.py) / [talker.py](../comictagger_jp_talker/talker.py) | 通常の NDL 変換では Imprint を設定しない。選択書誌の `fetch_comic_data()` で任意の Series 補完 | Imprint は多くの取得書誌で空になる。将来の opt-in は追加の問い合わせを広く起動し得る |
| [models.py](../comictagger_jp_talker/models.py) | `BookRecord.series_titles` は raw `dcndl:seriesTitle`。作品 identity ではない | レーベル・作品・叢書の意味分類を別に設計。NDL 値を直接 Imprint へ代入しない |

`ma:dataPublisher`、`ma:dataUrl`、更新日時、`schema:productID` 等は全直接 triple に残る。
取得日時、HTTP header、query ID は production の RDF モデルには保存されない。
RDF の raw 保持と HTTP の原応答の永続保存は別機能である。
`get_for_series_linkage()` の completeness は要求した Book / Series 範囲についての状態であり、関連 graph 全体の完全性ではない。

### 重複して設計しないもの

ISBN 正規化、URL identity、候補の一意性判定、truncated の検出、source cache、limiter、timeout、Series 出力規則は既存の処理を使う。
`SeriesNameClassification` は表示可能性の参考に限る。表示可能な brand を出版レーベルとする意味判定に流用しない。
`FieldComparisonState.NDL_ONLY / MADB_ONLY` を Book / Series の由来の違いに転用しない。

## 3. 調査方法・出典・取得状態

標本は **39 Book / 27 Series**。指定された 7 Book をすべて含む。
集英社、講談社、小学館、KADOKAWA、芳文社、白泉社、秋田書店に加え、少年画報社、冬水社、竹書房、若木書房等を含む。
選定理由を各 Book に保存した。ランダム標本ではなく、単一値だけでなく危険な構造を意図的に選んだ。

1. 2026-09-24 に取得済みの release 1.2.20 の ZIP を SHA-256 検証して再利用した。新たな全件ダウンロードはない。
2. 現行 [公式 Endpoint](https://mediag.bunka.go.jp/madb_lab/lod/sparql/) へ、最大 8 個の既知 URI の直接 triple だけを取得する SELECT を逐次実行した。
3. Book 5 batch、現在の明示的 `schema:isPartOf` に限った Series 4 batch、計 9 query が成功した。
4. 11 Book を既存 NDL source で最大 5 件の SRU 問い合わせにより比較した。各 query の対象書誌は 1 件だった。概要の追加取得はしていない。
5. M1032568 / M1032569 の 2 件は既存 ISBN discovery を実施し、現在の全候補と取得済み snapshot を既存 `compare_candidates()` へ渡した。両方 MATCHED / EXACT、矛盾なし、discovery 非 truncated。
6. 出版元の公式情報を照合した。URL、取得手段、確認範囲、不足を evidence の `official_sources` に記録した。

本体と同じ MADB transport、3 秒 limiter、connect 5 秒 / read 30 秒、2 MiB 上限、redirect 無効、自動 retry なしを利用した。
research の batch は最大 `300 × URI 数 + 1` 行。応答全体が上限未満、各 resource も 300 行未満である場合だけ完全な直接 triple 観測とした。
Book は最大 44 triples、Series は最大 26 triples。全 66 resource の型と ID を既存 parser で検証した。
Endpoint 固有の未公表の切り詰めや複数 request 間の snapshot isolation は保証できない。

最初の制限環境では 1 query が `network` で失敗し、8 resource を UNAVAILABLE と記録した。
許可された環境で同じ query を明示的に 1 回再実行し成功した。失敗履歴は残し、最新の成功を集計に使った。
成功した API 調査では HTTP 429 / 503、timeout、row / byte cap 到達を観測していない。
これらの状態は、後続フェーズの合成 fixture で試験する必要がある。

白泉社の公式ページは Web の直接取得が 2 回 timeout した。公式ページの検索索引本文で ISBN とシリーズ名を確認した結果と、直接取得未完了を分離した。
芳文社の公式注文書は PDF の抽出本文を確認した。画像取得は cache miss で失敗したため、視覚的な確認成功とは扱っていない。

### 公式仕様と実データの差

| 出典 | 確認内容・限界 |
|---|---|
| [MADB 公式スキーマ PDF](https://github.com/mediaarts-db/dataset/blob/main/doc/MADBメタデータスキーマ仕様書.pdf) | 取得済み Ver.1.2 / 2024-01-31 を再読。Series pp.41–42、Book p.69 の brand は出版者が設定する単行本レーベル、literal / 0-N、読みは ja-Hrkt。Book p.73 の productID はレーベル番号。今回最新版への更新有無を再取得で確認したわけではない |
| [MADB Lab 利用方法](https://mediag.bunka.go.jp/madb_lab/lod/howto/) | 現行 HTTPS schema / `#` namespace と呼び出し制約。推定実行時間 60 秒超、短時間の連続呼び出し制限。具体的な SELECT 上限や quota の時間窓は不明 |
| [Schema.org brand](https://schema.org/brand) | 汎用のブランドを表す。MADB の literal 表現や出版レーベル専用の制約を保証しない |
| [公式 dataset repository](https://github.com/mediaarts-db/dataset) | URI 移行、配布物、利用条件。今回使用した release は保存済み 1.2.20 であり、現在の最新 release と断定しない |

PDF の `http://schema.org/` と `/data/property/` を、現行 query の HTTPS schema / `#` と機械的に混在させない。
仕様の literal / 0-N はレーベルの意味保証、一意性、階層順、別表記同義性の保証ではない。
国立美術館国立アート リサーチ センター「メディア芸術データベース」を加工して作成した。原画像・作品本文は収録しない。

## 4. プロパティごとの観測

| プロパティ | 今回の直接 RDF 観測と扱い |
|---|---|
| Book / Series `schema:brand` | 全値が literal。言語タグなしと ja-hrkt。明示的 datatype は応答にない。URI / blank node / ja / 他言語 / 数値 datatype は未観測。未観測を未対応値が存在しない保証にしない |
| Book / Series `schema:publisher` | literal。複数値、読みの併記、`[発売]`、`[頒布]` がある。発行・発売・頒布は別の役割 |
| `dcterms:publisher` | `P...` 形式の literal を再確認。責任主体参照の仕様があっても、実値を IRI と扱わず lookup しない |
| Book `schema:isPartOf` | 型検証済み MangaBookSeries URI。今回各 Book は 0 または 1。関係があるだけで同じ版・同じレーベルとは保証されない |
| Series `schema:isPartOf` | 今回 Work 参照なし。Imprint 補完に Work は要求しない |
| `ma:seriesName` | 全直接 triple で確認し、値なしと未取得を分離。brand の代替として使わない。具体的な標本出現数は evidence の property 集計で示す |
| `schema:version` | literal。`愛蔵版`、`完全版` 等。brand と同じ版表示や Book / Series の版情報の差を候補判定で保留する |
| `schema:productID` | literal。NDL の叢書番号と対応することがある。brand 内の数値を黙ってこの欄へ移動したり捨てたりしない |

調査の追加対象は `rdf:type` / `schema:identifier`（resource の型と ID の整合）、`schema:isbn` / `ma:dataUrl`（既存 identity の検証）、
`schema:name` / `schema:volumeNumber`（対象巻と版の文脈）、`ma:dataPublisher` / 更新日時（原データと取得時点の区別）。
これらは意味確認・出典依存性に必要であり、Imprint へ書き込む対象ではない。

| property の出現 resource / term 数 | Book | Series |
|---|---:|---:|
| `schema:brand` | 35 / 80 | 24 / 45 |
| `schema:publisher` | 39 / 44 | 25 / 25 |
| `dcterms:publisher` | 24 / 24 | 25 / 25 |
| `schema:isPartOf` | 29 / 29 | 0 / 0 |
| `schema:version` | 11 / 11 | 12 / 12 |
| `schema:productID` | 22 / 22 | 0 / 0 |
| `ma:seriesName` | 1 / 2 | 0 / 0 |

Book brand の 80 terms はタグなし 44、ja-hrkt 36。Series はタグなし 25、ja-hrkt 20。
`ma:seriesName` は M189667 の `伯爵カインコレクション` とその読みで、brand の `Jets comics` とは別の記述である。
今回の 66 resource と保存済み release で、上記 7 property の raw RDF term 集合を比較した差分は **0**。
これを Endpoint 全体の不変性、その他の property の同一性、release と現在の snapshot の同一性の保証としない。
比較範囲と集合を evidence の `analysis.historical_comparison`、property 別の型・言語・datatype の出現数を `analysis.property_statistics` に保存した。

Book / Series は RDF 上の値集合として比較する。SPARQL の返却順、JSON-LD の配列順に優先順位の意味を与えない。
表示値を deduplicate しても、元 term、出現箇所、読み、datatype、出典は残す。
とくに `\u3000` が文字どおりに入った値を Unicode escape として再解釈しない。

## 5. 代表例と Book / Series / Publisher / NDL の関係

raw の詳細、URI、ISBN、取得日時は [台帳](research/madb/imprint_examples.md) を参照。
以下の引用値は原データとして空白・表記を変更していない。

| Book | 観測事実 | 判断・制約 |
|---|---|---|
| M1032569 | Dear Anemone **2**。Book `ジャンプコミックス`、Series 関係なし、NDL 同値、EXACT | [出版社の同巻・同 ISBN](https://www.shueisha.co.jp/books/items/contents.html?isbn=978-4-08-884174-8) に同じ書誌レーベル。意味確認を明示的に与える仕様案で唯一の採用候補 |
| M299519 | Book / Series `白泉社文庫`、NDL 同値、ISBN-10 | [公式ページ](https://www.hakusensha.co.jp/comicslist/41593/) の検索索引本文で意味確認。完全な MADB discovery は今回未実施。直接公式ページ取得も未完了で、自動採用条件は未充足 |
| M292389 | Book / Series `ジャンプ・コミックスデラックス` | [公式書誌](https://www.shueisha.co.jp/books/items/contents.html?isbn=4-08-859190-9&mode=1) は中黒・空白の異なる表示。人による意味確認と、自動的な別表記統合は別の判断 |
| M852457 | Book / Series ともに `MFコミックス`、`フラッパーシリーズ` の 2 表示値 | [公式商品](https://www.kadokawa.co.jp/product/322104000242/) の複合レーベルは確認できるが、上位・下位のどれを raw Imprint とするかは未確定 |
| M381096 | Book に `Manga time KR comics` / `Kirara menu`、Series は結合文字列 | [公式注文書](https://houbunsha.co.jp/patron/pdf/201805_ordersheet_mangatimeKR.pdf) は上位に相当する名称と ISBN を確認できる。Kirara menu の位置・採用名は未確認 |
| M519976 | `ラキッシュ・コミックス` と literal `150`、読み側にも `150` | NDL は `ラキッシュ・コミックス ; no. 150`。番号混入を確認できるが、残りの候補を無条件に採用しない |
| M197767 | Book / Series brand と Book `schema:version` が `愛蔵版` | 単一表示・双方一致でも版表示との重複として棄却。出版社のブランド不存在まで証明したわけではない |
| M197011 | Book / Series brand、publisher が `太平洋文庫` | publisher と同名でも兼ねる可能性の調査が必要。原則として棄却し、同名の妥当性は未確認 |
| M190399 | Book は `マーガレットコミックス` と `別冊マーガレット`、Series / NDL は前者だけ | [公式の雑誌情報](https://betsuma.shueisha.co.jp/new/) で後者の雑誌としての役割を確認。NDL 一致で Book の複数値を一つに絞らない |
| M255146 / M299514 / M197041 | 英語・日本語・略称の複数表示、Series は単一または結合 | 見た目や読みだけで同一レーベルにまとめない |
| M353277 | Book は DX 付き、Series の表示は DX なし、読みにはデラックス | 読みで表示差を消さない。BOTH_CONFLICT |
| M1080059 | Book `ジュニアコミックス`、Series `辻なおき0戦シリーズ` | 出版叢書と単行本レーベルの異なる可能性。BOTH_CONFLICT |
| M1079799 | Book brand 欠損、Series `辻なおき0戦シリーズ`、Book / Series title も異なる | SERIES_ONLY。Series の値を Book のレーベルとして採用する根拠なし |
| M280574 | `手塚治虫漫画全集`、NDL は同名と番号 `410` | 叢書・全集と出版レーベルの境界。意味は UNVERIFIED |
| M1118994 | 単一表示 `講談社コミックス. 週刊少年マガジン`、ISBN なし | 単一文字列に複数役割が含まれる。既存 ISBN discovery 経路も利用できない |
| M1032913 / M196308 等 | 空 literal、brand property 欠損 | 空 literal と property 欠損を保存上は区別し、いずれも安全な候補はない |

通常版と完全版、発行主体と発売主体、旧出版元と現行の所属を混ぜない。
M280044 は Book の版表示がなく、関連 Series は完全版である。同じ Series の関係だけで Book の版を補って確定しない。
M1065430 の一迅社と `[頒布]講談社`、M215577 の発行・発売表記は raw の役割を残す。
移管、同名の別出版社ブランド、公式な全レーベル階層は今回未確認であり、後続の自動採用範囲に含めない。

### NDL を裏付けにできる範囲

11 件の `series_titles`、publisher、editions を直接取得して保存した。`series_titles` はレーベル以外の叢書や番号も含む。
完全一致は「記述が一致する」という観測、レーベルとしての妥当性は別の判断とする。
M1032570 は NDL に特装版があり、MADB の同一書誌で版の専用値が欠ける。版の省略を別版確定にも同版証明にも使わない。
MADB の `ma:dataPublisher=NDLサーチ` は標本の 10 Book で観測した。
M1032568 / M1032569 の NDL 一致は同一原データに由来し得るため、独立した意味確認 2 件と数えない。
旧 MADB データの出典が generic dataset 表記の場合も、NDL 由来でないと推定しない。

## 6. 分類モデル・文字列処理

言語分類、意味分類、候補間の関係、取得状態を別の軸として保持する。
一つの enum に「読める」「レーベル」「複数」「取得不能」を押し込めない。

| 軸 | 仕様案 |
|---|---|
| `ImprintTermRole` | DISPLAY、READING、OTHER_LANGUAGE、UNSUPPORTED、INVALID、EMPTY |
| `ImprintSemanticKind` | VERIFIED_LABEL、PUBLISHER_OR_ISSUER、NUMERIC_IDENTIFIER、PUBLICATION_SERIES、MAGAZINE、EDITION_STATEMENT、OTHER_BRAND、UNVERIFIED |
| `LabelRelation` | UPPER、LOWER、ALTERNATIVE、COMPOSITE、UNRESOLVED。関係元 evidence と意味確認の根拠が必須 |
| `AuthorityState` | VERIFIED、UNVERIFIED、CONTRADICTED。確認した書誌・ISBN・媒体・出版主体・適用時期を明示 |
| `AcquisitionState` | COMPLETE、TRUNCATED、PARTIAL、UNAVAILABLE、NOT_REQUESTED、NOT_RELATED |

「単一の明確な出版レーベル」は VERIFIED_LABEL と単一候補の組み合わせ。
出版社名、上位・下位、結合文字列、表記ゆれ、読み、番号、出版叢書・雑誌、意味不明のブランド、不正値、欠損の 12 分類を上記の軸で表す。
上位・下位と ALTERNATIVE は文字列から自動生成せず、意味確認がなければ UNRESOLVED。
COMPOSITE の分解候補は診断として保存できるが、分解・連結結果を出力値にしない。

### language / datatype

| raw RDF | 分類 |
|---|---|
| literal、tag なし、datatype なし / xsd:string | DISPLAY 候補。タグなしの英語やひらがなを読みと推定しない |
| literal、ja、datatype なし / rdf:langString | DISPLAY 候補。今回 ja の実例は未観測なので後続 fixture が必要 |
| literal、ja-hrkt、datatype なし / rdf:langString | READING。英語文字列が入っていても表示名へ格上げしない |
| その他の language、未知 datatype | OTHER_LANGUAGE / UNSUPPORTED。表示候補と併存しても自動採用を保留 |
| tag と datatype の不整合、surrogate 等 | 既存 parser の protocol 判定を維持。取得不能として fail-open |
| uri / bnode | UNSUPPORTED。URI 末尾や関連 label を新たに lookup して表示値にしない |
| 空 literal / trim 後空 | EMPTY。raw を残し、安全な表示候補に含めない |

BCP 47 の language tag の比較だけ casefold を使う。原 tag は保持する。
tag なし literal の datatype が JSON にない場合、取得 JSON に明示されていなかった事実を保持する。
`150` は literal 文字列であり、xsd:integer と観測したことにしない。

### raw・表示・比較の分離

- raw: RDF term と statement の subject / predicate、language、datatype を不変で保持する。
- display: 対象 resource に実在する表示値。採用時も原表記を出力し、外周空白の扱いを変えるなら transform を明示する。
- equality key: 初版は **NFC + 外周空白除去** のみ。内部空白、全角半角、英数字の大小文字、中黒、句読点、区切りを保持する。
- diagnostic key: NFKC、casefold、空白の折り畳みは候補同士の差を説明する用途だけ。一致しても採用可にはしない。

`ジャンプコミックス` と `ジャンプ・コミックス`、`KC DELUXE` と日本語名、`／` と `.`、`= ` を一律に同値化しない。
読みが同じことも別表記や階層の証明にしない。M353277 がこの制約の実例である。
XML 1.0 に保存できない control、surrogate、U+FFFE / U+FFFF は採用を棄却し、削除・置換して別値を作らない。

## 7. Book / Series 比較仕様

NDL / MADB 比較用 `FieldComparisonState` はそのまま残し、新しい `ImprintComparisonState` を設ける。
`availability`、`presence`、`cardinality`、`normalized_set_equal`、`overlap`、`relation_assessments` を独立した出力にする。
その上で次の集約 state を返す。state はレーベル意味の正解ではない。

| state | 意味 |
|---|---|
| BOOK_ONLY | 完全な Book に表示候補あり。関係なし、または必要な Series が完全で brand 候補なし |
| SERIES_ONLY | 完全な Book で候補欠損、完全な関連 Series に候補あり |
| BOTH_AGREE | 両者が単一表示候補で厳格な equality key が同じ |
| BOTH_CONFLICT | 両者が単一表示候補で equality key が違う |
| MULTIPLE | 複数表示候補、複数 Series 関係、または解消できない候補関係。両側の集合一致や部分一致は別に保持 |
| NONE | 完全取得の必要範囲に安全な非空表示候補がない |
| UNAVAILABLE | Book、必要な Series、relation か discovery が不完全・未取得。欠損と断定しない |

初期判定順は UNAVAILABLE → MULTIPLE → 単一値の一致 / 不一致 →片側 / NONE。
未知言語・URI 等の term は blocker を保持し、集約 state が BOOK_ONLY 等でも eligibility を別に拒否できる。
M381096 の Book 2 値と Series の結合 1 値、M807088 等を BOTH_AGREE と扱わない。
意味分類を経て番号を別欄へ分類しても、その証拠を削除して「元から単一」と扱わない。

**初版の自動採用は Book 起点に限定する。SERIES_ONLY は評価・説明だけ実装し、採用は無効。**
将来有効化するには一つの明示的 Series 関係、両 resource の完全取得、対象巻・版・発行主体・刊行時期の整合、
対象 Book へそのレーベルを適用できる独立した公式根拠、Series 内の移管や例外の不存在を検証する必要がある。
Series title や brand が一つであるだけでは不十分。M1079799 のような関係を跨ぐ意味の差がある。

## 8. 採用条件・棄却条件・評価アルゴリズム

### 書誌照合の gate

既存の identity algorithm を呼び出した結果が MATCHED、EXACT / STRONG の安全な候補が一意、discovery 非 truncated であること。
すべての discovery が成功し、候補 Book が完全取得され、採用 Book と snapshot の ID / URI が一致すること。
必要な Series 関係がすべて解決され、各 Series が完全取得、relation budget 未到達、取得失敗なしであること。
直接 NDL URL identity の矛盾は無条件に棄却する。

EXACT は既存仕様では ISBN 差異と共存する場合がある。本仕様の自動 Imprint 出力はより厳しく、**MatchConflict が一つでもあれば棄却**する。
リンク判定自体は変更しない。版・発行主体・媒体に明示的な矛盾があれば追加の Imprint gate で保留する。
部分検索を完全検索として一意性の証拠にしない。候補の先頭を選択しない。

### Imprint の gate

1. 既存 Imprint が `None` または空文字列である。初版では空白だけの文字列も既存値として保護し、上書きしない。
2. Book に一つの安全な DISPLAY 候補がある。複数値、未解決の別表記、階層、結合値、未知 term は保留する。
3. 出版レーベルとして VERIFIED の意味根拠がある。単一 brand、Book / Series 一致、NDL 一致はこの gate の代わりにならない。
4. 根拠が対象巻・ISBN・媒体・版・出版主体・適用時期に合う。現在の出版元の所属を古い版へ遡及させない。
5. publisher だけと同名の候補、数値、版表示、雑誌、出版叢書、未確認ブランドは初版では棄却または保留する。
6. Series 関係があるなら、取得を省いて矛盾の不存在を推定しない。初版は BOTH_AGREE、または完全取得で Series brand 候補なしの BOOK_ONLY を許す。
7. 表示値が XML に保存可能である。raw 表示を変えて別候補を作らない。
8. provenance を元の statement と意味確認根拠へ追跡できる。

意味確認は例えば出版元の同じ ISBN の書誌欄のレーベルを、信頼できる入力契約で与える。
今回の M1032569 はこの条件の実資料例である。公式サイトの毎回の scrape や任意 URL へのアクセスを plugin に追加する案ではない。
**現行モデルだけでは一般の brand の意味を検証できる仕組みがない。意味確認データの提供方法は 2C-2C の移行を阻む未解決事項。**
将来辞書を提案する場合は出版社・版・時期・出典・更新手順を伴う根拠付きの設計を別途評価する。今回辞書を追加しない。

### 1～4 の処理案

```text
extract_imprint_evidence(book, related_series, acquisition_context)
  -> subject / predicate / RDFTerm を付けた候補と relation evidence
classify_imprint_terms(evidence, authority_evidence=())
  -> 言語・意味・候補間関係、未確認理由（raw 不変）
compare_imprint_candidates(classifications, ndl_record, acquisition_context)
  -> Book / Series 比較 + NDL 観測 + publisher / edition conflict
evaluate_imprint_eligibility(linkage, comparison, existing_imprint)
  -> eligible / hold / reject + 単一 raw 候補または None + 全理由
```

処理は pure function とし、ネットワークや GenericMetadata 変更を起動しない。
各段階は複数候補を保持する。候補数を減らす場合は捨てた理由と evidence を明示する。
失敗・保留を一つの bool だけで表さず、複数の原因を保持する。
後続の supplement は別段階で、この評価結果を検証してから一つの出力欄だけを更新する。

## 9. Phase 2C-2B の内部 API 案

追加先候補は独立した `imprint_candidates.py`。今回追加していない。

| 型 | 主な内容 |
|---|---|
| `ImprintCandidate` | `FieldEvidence`、直接 subject URI、origin=book / series、raw statement の参照、display、comparison key、role、semantic kind |
| `ImprintClassification` | resource ごとの display / reading / alternative / nonlabel / unsupported / empty、上下・複合関係と根拠、blockers |
| `ImprintComparison` | 上記比較 state、完全性、候補配列、集合一致・重なり、Book / Series relations、NDL 叢書 evidence、publisher / edition 比較 |
| `ImprintEligibility` | eligible / hold / reject、selected candidate または None、全 reasons、identity の参照、評価仕様の version |
| `LabelAuthorityEvidence` | 公式出典 URL / locator、確認時点、label statement、Book / ISBN / publisher / edition / medium / date の適用範囲、由来 group、verification state |
| `AcquisitionContext` | request ID、取得日時、scope、resource ごとの completeness、discovery の状態、未要求・関係なしの区別、raw bundle の参照 |

`FieldEvidence` の source / raw_value / record_id / record_uri / predicate_or_path / transform / related_uri は再利用する。
Series 由来の候補は actual subject を Series として追跡し、Book との関係 statement も保存する。
NDL 由来の MADB 値は source の違いだけで独立根拠にしない。由来 group の不明は独立性 UNVERIFIED。
HTTP 日時や query ID は RDF に存在する情報として捏造せず、取得コンテキストに格納する。

reason enum の初版候補:
`NOT_MATCHED`、`IDENTITY_AMBIGUOUS`、`DISCOVERY_TRUNCATED`、`BOOK_INCOMPLETE`、`SERIES_INCOMPLETE`、
`RELATION_UNRESOLVED`、`IDENTITY_CONFLICT`、`CONTEXT_CONFLICT`、`EXISTING_IMPRINT`、`NO_DISPLAY`、
`UNSUPPORTED_TERM`、`MULTIPLE_DISPLAYS`、`COMPOSITE_UNRESOLVED`、`HIERARCHY_UNRESOLVED`、
`SEMANTIC_UNVERIFIED`、`PUBLISHER_EQUAL`、`NONLABEL_VALUE`、`SERIES_CONFLICT`、`SERIES_ONLY_DISABLED`、`INVALID_XML`。

### 単体試験・fixture の計画

実測 fixture は evidence の resource を必要な predicate に絞って生成し、取得日と query ID を注記する。
M1032569 の安全な単一値、M1032568 の EXACT だが意味未確認、M381096 / M852457 / M807088 の階層・結合、
M519976 の番号、M190399 の雑誌、M197767 の版、M197011 の publisher 同名、M353277 / M1080059 の矛盾、
M1079799 の SERIES_ONLY、空と欠損、複数 publisher、異なる ISBN を残す。

未観測の ja / 他言語 / URI / blank node / numeric datatype、未知 qualifier、truncated、relation 失敗、429 / 503、invalid XML は
**合成 fixture** と明記する。実測 fixture と混同しない。
並び替え不変、raw evidence の不変、未知 term が既知表示と併存する場合の保留、由来 group の重複排除、
既存 Imprint 保護、EXACT と ISBN conflict の併存を意味のある境界試験とする。
GenericMetadata の変更、設定登録、実 API への自動アクセスは 2C-2B に含めない。

## 10. Phase 2C-2C の取得共有・補完・負荷設計

提案する設定名は `jpbooks_madb_imprint_supplement`、既定値 False、明示的な opt-in。
これは将来の名称案で、今回登録も GUI 表示もしていない。
`fetch_comic_data()` の NDL 取得・番号整合・変換後に、Series と Imprint の need をそれぞれ判定する。
候補一覧、`fetch_series()`、issue 候補取得、status check では補完の追加通信を起動しない。

```text
need_series  = series_enabled  AND NDL 変換後の Series が空
need_imprint = imprint_enabled AND NDL 変換後の Imprint が空
if neither need: 変換済み NDL メタデータを返す
else: 一度だけ既存 ISBN discovery と Book / Series の取得・照合
      同じ immutable snapshot を両方の評価へ渡す
      各欄の安全な評価だけを個別に適用する
```

`get_for_series_linkage()` 自体は変更不要。公開 linkage API は bundle を返さないため、共有する取得コンテキストの API が必要である。
例: `LinkedRecordEvidence(linkage, bundles, acquisition_context)` を返す内部経路を設け、既存公開関数は従来の `LinkageResult` を返す wrapper とする。
既存 `_link_ndl_record()` の取得ループを一箇所で利用し、identity / Series 比較の規則を複製・緩和しない。
この接続は 2C-2C の範囲。2C-2B の pure API は既に取得した bundle を引数で受けるだけにする。

Series の補完評価・Notes は既存仕様を維持する。Imprint の意味確認失敗で、独立して安全な Series 補完まで棄却しない。
同時 ON と Series だけ ON の出力を比較し、既存 Series の結果が一致することを検証する。
Series が存在していても need_imprint は独立に評価する。

### API 要求数とキャッシュ

有効な異なる正規化 ISBN 数を `k`、発見された Book 数を `b`、各 Book の取得する関連 Series 数を `s_i` とする。
初回の要求数は **`k + b + Σs_i`**。通常の `k=1, b=1` は Series 関係なしで 2、1 Series ありで 3 requests。
意味確認を公式サイトから毎回取得する requests はこの計画に含めず、そのような追加 transport は未設計。

| 条件 | MADB 通信 |
|---|---|
| 両設定 OFF、または両欄とも補完不要 | 0 |
| どちらか一方だけ必要 | 上記の一連の取得 |
| 両方必要 | 同じ取得を共有し、要求数を 2 倍にしない |
| 完全な cache が有効 | 該当 scope の transport は 0。未キャッシュの scope だけ要求 |
| refresh / cache 期限切れ | 既存 source の policy で再取得。補完のための自動 retry を追加しない |

候補上限は ISBN query ごとに既定 20、最大 100。関連要求 budget は Book bundle ごとに 12。
複数 ISBN や複数 Book にまたがる全体の候補数は 20 とは限らない。
例として単一 ISBN で既定上限の 20 Book、各 1 Series なら 41 requests になり得る。truncated なら採用しない。
Agent / Holding の参照先は問い合わせない。Book の全直接 triple 内にそれらへの参照が入ることとは区別する。
候補が同じ Series を共有しても、現行 relation cache の key は親 URI / predicate / kind を含むため、別 Book の Series 要求が必ず一つにまとまるわけではない。
cache の parser namespace、LIMIT、endpoint、scope を既存のまま使う。完全取得だけ cache 採用、現在のホストの約 7 日の失効方針を再利用する。
性能を理由に既存 limiter、timeout、byte / row / relation cap、identity 検証を緩和しない。

### 書き込みと fail-open

採用時だけ `replace(metadata, imprint=raw_display, notes=最小追記)` の形を検討する。
Imprint 以外の欄は既存の選択・補完仕様のまま。Notes の追記は重複せず、Book / 必要な Series ID、confidence、理由、raw の出典と評価仕様 version を明示する。
短い Notes は内部の structured evidence の代わりにしない。変換・加工した場合はその由来を記録する。
MADB の network / timeout / HTTP / protocol / schema / cache 障害では元の NDL metadata を返し、NDL の取得失敗記録へ置き換えない。
設定 OFF の通信数と出力は v0.3.0 と同じであることを比較する。

### 2C-2C の試験

OFF、Imprint の既存値、Series 既存 / 欠損、同時 ON、cache hit / refresh、1 / 2 / 3 request の正常例、truncated、多候補、完全性失敗、直接 identity conflict、
意味確認不可、XML 不正値を確認する。ComicInfo.xml の Imprint と Notes を実際の CR / CIX writer で保存・再読込し、日本語と記号を比較する。
配布 ZIP は現行 beta.9 loader と ComicArchive で読み込み、両設定 OFF の既存結果と、一欄だけ採用する結果を統合試験する。
本フェーズで Imprint writer を追加したり、その試験が既に成功したと扱ったりしない。

## 11. 採用品質・残る制約・移行条件

| 指標 | 結果 | 定義・制限 |
|---|---:|---|
| 調査 Book / Series | 39 / 27 | 最新の完全な直接 triple 観測 |
| brand property を持つ Book | 35 | 空 literal の 1 件も含む |
| 単一の非空 DISPLAY を持つ Book | 25 | 意味がレーベルである保証はない |
| 複数の非空 DISPLAY を持つ Book | 9 | 番号や別表記も含む |
| 読み term のある Book | 31 | うち非空の読みは 28 |
| publisher と厳格に同じ brand を持つ Book | 1 | M197011。これ以外の混同がないという意味ではない |
| 出版元情報でレーベルの意味を確認 | 4 | M852457、M299519、M292389、M1032569。1 件は公式索引本文、1 件は人による別表記認識。すべてが自動採用可能ではない |
| 版表示との重複として確認して不採用 | 1 | M197767。ブランド不存在の証明とは別 |
| 意味の正解未確定 | 34 | 部分的な役割確認ができた資料も、完全な出力値は不明ならここへ含める |
| 仕様案の条件を今回満たす候補 | 1 | M1032569。確認済み公式根拠を評価入力に与えるという条件付き |
| 仕様案での誤採用（正解確認済み部分のみ） | 0 | 5 件の狭い確認範囲。未確認 34 件は精度の分母に含めない。未実装の自動補完の精度証明でもない |
| 今回の Imprint 書き込み | 0 | 調査・設計のみ |

Book / Series 比較は BOTH_AGREE 14、BOOK_ONLY 9、BOTH_CONFLICT 2、MULTIPLE 9、NONE 4、SERIES_ONLY 1。
UNAVAILABLE は接続失敗履歴に存在するが、最新の成功した標本では 0。
単一値と双方一致だけを採用条件にすると M197767 の版表示を拾う。この規則は採用しない。
publisher 同名や全集の例は、正解未確認のまま保留できることが仕様の要件である。
標本は同じ Series を共有する Book を含み、独立したランダム試行ではない。採用率や誤採用率を MADB 全体へ推定しない。

未解決事項は、独立した意味根拠の供給方法、公式階層・別表記の検証、古い出版元と移管、同名ブランド、Series-only の Book 適用性、
未観測の RDF 型・言語、公式サイトの取得失敗と媒体差、query 間の更新整合、opt-in による要求数の増加。
NDL の系列表記は意味根拠の供給方法を単独では解決しない。

### 移行条件と実装順序

1. **2C-2B に進む**: pure extraction / classification / comparison / eligibility、型と reason enum、raw provenance、境界 fixture を実装する。UNVERIFIED は必ず保留する。
2. **2C-2B の受入条件**: 実測の正常例と不採用例、合成の不完全・未知型を分けて試験し、既存コードの identity / Series 出力と通常 metadata が変わらないことを示す。
3. **2C-2C の意味確認条件**: 信頼できる根拠入力の供給方法、書誌・媒体・時期への適用範囲、原データ依存性、更新と無効化手順を確定する。供給できない場合は一般的な自動補完を開始しない。
4. **2C-2C の取得条件**: 一度の取得で bundle を両評価に共有する内部契約を設け、既存公開 API と Series 動作を保持する。
5. **最後に opt-in 出力**: 一意・完全・意味 VERIFIED の Book 候補だけ書き込み、XML / ZIP / cache / fail-open / OFF 互換性を統合検証する。

候補の表示・評価には十分な構造的根拠があるため NO-GO とはしない。
一般の自動補完には追加の意味根拠が必要であるため GO ともしない。
未確認の資料を高い補完率のために採用する設計へは進まない。

## 12. 成果物の検証と再現

既存 virtualenv を使用した。network marker のテストは opt-in のまま無効で、通常テストは network を禁止する既存 fixture に従った。

```powershell
.venv/Scripts/python.exe -X utf8 scripts/research_madb_imprint.py --offline
.venv/Scripts/python.exe -X utf8 scripts/research_madb_imprint.py --collect
# 制限環境で network 失敗が保存された場合だけ、承認環境で明示的に再実行
.venv/Scripts/python.exe -X utf8 scripts/research_madb_imprint.py --collect --retry-network-once
.venv/Scripts/python.exe -X utf8 scripts/research_madb_imprint.py --ndl
.venv/Scripts/python.exe -X utf8 scripts/research_madb_imprint.py --verify
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .research/phase2c2a-pytest-20261008
.venv/Scripts/python.exe -m ruff check scripts/research_madb_imprint.py
.venv/Scripts/python.exe -m ruff format --check scripts/research_madb_imprint.py
git diff --check
git status --short
```

`--offline` は初回 seed 用の保存済み ZIP を要求し、過去の取得日時を今回の取得と書き換えない。
配布 ZIP と SHA-256 は旧 evidence と今回 `historical.sources` に記録した。ファイルがない場合は無断でダウンロードせず停止する。
既存 evidence がある場合、collector は同じ query の成功・失敗を再利用する。失敗を黙って refresh せず、network 失敗だけ明示的な再実行を許す。
新たな時点の調査では別の保存先を使い、このファイルの履歴を破棄しない。network 失敗の flag は自動 retry ではない。

`--verify` はネットワークを使わず、JSON、query hash、raw binding、ID / URI / 型、triple cap、分析集計、参照先、既存 identity 結果を確認する。
query 本文を保存したので API 観測は再実行できる。意味の人による判断は `analysis.cases`、根拠は `official_sources` で追跡し、取得結果から自動的に確定したことにしない。
NDL の raw 全書誌を fixture として配布せず、今回必要な seriesTitle / publisher / edition の XML、parsed 値、query、ID、原 XML hash を保存した。

既存試験: **1,376 passed / 13 skipped / 1 xfailed**（25.33 秒）。新しい採用 API の試験を既に実行したという結果ではない。
production code、Phase 1、Series 補完、metadata 出力、設定、版番号は変更していない。
commit / merge / push / tag / GitHub Release は実行していない。
