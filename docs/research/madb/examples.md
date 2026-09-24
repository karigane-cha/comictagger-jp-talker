# MADB Phase 2A 実例台帳

調査日: 2026-09-24。公式 release **1.2.20 (2026-09-18)** の JSON-LD を抽出・整形して作成。
出典: [国立美術館国立アートリサーチセンター「メディア芸術データベース」](https://mediaarts-db.artmuseums.go.jp/)、[公式データセット](https://github.com/mediaarts-db/dataset/releases/tag/1.2.20)。データセットは自由な二次利用が可能。
本表の抽出・正規化候補は本プロジェクトによる加工であり、MADB の公式判断ではない。

先頭14冊は endpoint でも全直接プロパティを確認（`examples.rq`: 476行、14 URI）。全29冊を掲載。主要12タイトル群＋攻殻機動隊・キジトラ猫の小梅さん等。
— は欠損であり、存在しないという一般的主張ではない。JSON-LD の `@language` と `@id` は原文のまま保持。
Work は全例で未取得。material は全例で専用 Book プロパティを未確認で、ページ数・寸法のみから紙と確定しない。
NDL URL/JPNO は別識別子。endpoint 所蔵経由の NDL 資料IDは M381096 のみ別記し、他例にないと断定しない。

## 1. ご注文はうさぎですか? volume 1

Book URI: [M381096](https://mediaarts-db.artmuseums.go.jp/id/M381096)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["ご注文はうさぎですか?", {"@value": "ゴチュウモン ワ ウサギ デスカ", "@language": "ja-hrkt"}] |
| 表示ラベル | "ご注文はうさぎですか? volume 1" |
| raw volume | "volume 1" |
| ISBN raw | "9784832241190" |
| Creator responsibility | "[著]Koi" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C48511"} |
| Publisher | "芳文社　∥　ホウブンシャ" |
| Publisher reference | "P4832200000" |
| Label | ["Kirara menu", "Manga time KR comics", {"@value": "KIRARA MENU", "@language": "ja-hrkt"}] |
| 公開年月日 | "2012-03" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "22038767" |
| Label number / other product ID | "619" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C334830](https://mediaarts-db.artmuseums.go.jp/id/C334830) |
| Series title | ["ご注文はうさぎですか?", {"@value": "ゴチュウモン ワ ウサギ デスカ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": "Manga time KR comics　／　Kirara menu"} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

endpoint 追加確認: `schema:provider → ref/S1748248` の `schema:name="国立国会図書館"`、`ma:ownerIdentifier="2"`、`ma:materialIdentifier="023440575"`。JPNO と混同しない。別の所蔵 `S2151624` の注記には第20刷の情報があり、Book の公開年月日を置換しない。

## 2. こちら葛飾区亀有公園前派出所 第1巻

Book URI: [M250454](https://mediaarts-db.artmuseums.go.jp/id/M250454)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["こちら葛飾区亀有公園前派出所", {"@value": "コチラ カツシカク カメアリ コウエンマエ ハシュツジョ", "@language": "ja-hrkt"}, {"@value": "コチラ カツシカク カメアリコウエンマエ ハシュツショ", "@language": "ja-hrkt"}, {"@value": "コチラカツシカクカメアリコウエンマエハシュツジョ", "@language": "ja-hrkt"}] |
| 表示ラベル | "こちら葛飾区亀有公園前派出所 第1巻" |
| raw volume | "第1巻" |
| ISBN raw | —（このレコードに値なし） |
| Creator responsibility | ["[著]山止たつひこ", "[著]秋本治", {"@value": "アキモトオサム", "@language": "ja-hrkt"}] |
| Creator URI | [{"@id": "https://mediaarts-db.artmuseums.go.jp/id/C55790"}, {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C73098"}] |
| Publisher | "集英社" |
| Publisher reference | "P4080000000" |
| Label | ["ジャンプ・コミックス", {"@value": "ジヤンプ コミツクス", "@language": "ja-hrkt"}] |
| 公開年月日 | "1977-07-31" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "77035601" |
| Label number / other product ID | ["852811", "JC811"] |
| 別タイトル | ["早うち両さん!?の巻", {"@value": "ハヤウチ リョウ サン ノ マキ", "@language": "ja-hrkt"}] |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C295645](https://mediaarts-db.artmuseums.go.jp/id/C295645) |
| Series title | ["こちら葛飾区亀有公園前派出所", {"@value": "コチラ カツシカク カメアリ コウエンマエ ハシュツジョ", "@language": "ja-hrkt"}, {"@value": "コチラ カツシカク カメアリコウエンマエ ハシユツシヨ", "@language": "ja-hrkt"}, {"@value": "コチラカツシカクカメアリコウエンマエハシュツジョ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["ジャンプ・コミックス", {"@value": "ジヤンプ コミツクス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 3. パタリロ! 1

Book URI: [M299519](https://mediaarts-db.artmuseums.go.jp/id/M299519)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["パタリロ!", {"@value": "パタリロ", "@language": "ja-hrkt"}] |
| 表示ラベル | "パタリロ! 1" |
| raw volume | "1" |
| ISBN raw | "4592880714" |
| Creator responsibility | "[著]魔夜峰央" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C52860"} |
| Publisher | "白泉社　∥　ハクセンシャ" |
| Publisher reference | "P4592000000" |
| Label | ["白泉社文庫", {"@value": "ハクセンシャ ブンコ", "@language": "ja-hrkt"}] |
| 公開年月日 | "1994-09-21" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "94068874" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | ["国王誕生の巻", "選集", {"@value": "コクオウ タンジョウ ノ マキ", "@language": "ja-hrkt"}, {"@value": "センシュウ", "@language": "ja-hrkt"}] |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C259763](https://mediaarts-db.artmuseums.go.jp/id/C259763) |
| Series title | ["パタリロ!", {"@value": "パタリロ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["白泉社文庫", {"@value": "ハクセンシャ ブンコ", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 4. ブルーロック 1

Book URI: [M1076947](https://mediaarts-db.artmuseums.go.jp/id/M1076947)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["ブルーロック", {"@value": "BLUELOC", "@language": "en"}, {"@value": "ブルー ロック", "@language": "ja-hrkt"}] |
| 表示ラベル | "ブルーロック 1" |
| raw volume | "1" |
| ISBN raw | "9784065405918" |
| Creator responsibility | ["DerrNate", "ノ村優介", "金城宗幸", {"@value": "カネシロムネユキ", "@language": "ja-hrkt"}, {"@value": "ノムラユウスケ", "@language": "ja-hrkt"}] |
| Creator URI | [{"@id": "https://mediaarts-db.artmuseums.go.jp/id/C414769"}, {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C429611"}, {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C520852"}] |
| Publisher | "講談社" |
| Publisher reference | —（このレコードに値なし） |
| Label | ["KODANSHA BILINGUAL COMICS", {"@value": "", "@language": "ja-hrkt"}] |
| 公開年月日 | "2025-09-13" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | "https://ndlsearch.ndl.go.jp/books/R100000002-I034296254" |
| JPNO (NDL Bib ID とは別) | "24171282" |
| Label number / other product ID | "" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | "バイリンガル版デラックス" |
| normalized volume candidate | 1 |
| Series URI | 未取得 |
| Series title | —（このレコードに値なし） |
| Series edition / label | {"edition": null, "brand": null} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 5. FX戦士くるみちゃん 1

Book URI: [M852457](https://mediaarts-db.artmuseums.go.jp/id/M852457)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["FX戦士くるみちゃん", {"@value": "エフエックス センシ クルミチャン", "@language": "ja-hrkt"}] |
| 表示ラベル | "FX戦士くるみちゃん 1" |
| raw volume | "1" |
| ISBN raw | "9784046806680" |
| Creator responsibility | ["[作画]炭酸だいすき", "[原作]でむにゃん"] |
| Creator URI | [{"@id": "https://mediaarts-db.artmuseums.go.jp/id/C439937"}, {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C439938"}] |
| Publisher | "KADOKAWA　∥　カドカワ" |
| Publisher reference | —（このレコードに値なし） |
| Label | ["MFコミックス", "フラッパーシリーズ", {"@value": "エムエフ コミックス. フラッパー シリーズ", "@language": "ja-hrkt"}] |
| 公開年月日 | "2021-07" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "23584310" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C449335](https://mediaarts-db.artmuseums.go.jp/id/C449335) |
| Series title | ["FX戦士くるみちゃん", {"@value": "エフエックス センシ クルミチャン", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["MFコミックス", "フラッパーシリーズ", {"@value": "エムエフ コミックス. フラッパー シリーズ", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 6. お兄ちゃんはおしまい! 10

Book URI: [M1065430](https://mediaarts-db.artmuseums.go.jp/id/M1065430)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["お兄ちゃんはおしまい!", {"@value": "オニイチャン ワ オシマイ !", "@language": "ja-hrkt"}] |
| 表示ラベル | "お兄ちゃんはおしまい! 10" |
| raw volume | "10" |
| ISBN raw | "9784758087575" |
| Creator responsibility | ["ねことうふ", {"@value": "ネコトウフ", "@language": "ja-hrkt"}] |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C67586"} |
| Publisher | ["[頒布]講談社", "一迅社"] |
| Publisher reference | —（このレコードに値なし） |
| Label | ["IDコミックス", {"@value": "ID コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2025-08-11" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | "https://ndlsearch.ndl.go.jp/books/R100000002-I034206797" |
| JPNO (NDL Bib ID とは別) | "24147233" |
| Label number / other product ID | "" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 10 |
| Series URI | 未取得 |
| Series title | —（このレコードに値なし） |
| Series edition / label | {"edition": null, "brand": null} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 7. SLAM DUNK 1

Book URI: [M292389](https://mediaarts-db.artmuseums.go.jp/id/M292389)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["SLAM DUNK", {"@value": "Slam dunk", "@language": "ja-hrkt"}, {"@value": "スラム ダンク", "@language": "ja-hrkt"}] |
| 表示ラベル | "SLAM DUNK 1" |
| raw volume | "1" |
| ISBN raw | "4088591909" |
| Creator responsibility | "[著]井上雄彦" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C57175"} |
| Publisher | "集英社　∥　シュウエイシャ" |
| Publisher reference | "P4080000000" |
| Label | ["ジャンプ・コミックスデラックス", {"@value": "ジャンプ コミックス デラックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2001-03" |
| Edition | "完全版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "20154120" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C262152](https://mediaarts-db.artmuseums.go.jp/id/C262152) |
| Series title | ["Slam dunk", {"@value": "Slam dunk", "@language": "ja-hrkt"}, {"@value": "スラム ダンク", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "完全版", "brand": ["ジャンプ・コミックスデラックス", {"@value": "ジャンプ コミックス デラックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 8. ドラゴンボール 1

Book URI: [M307396](https://mediaarts-db.artmuseums.go.jp/id/M307396)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["ドラゴンボール", {"@value": "ドラゴン ボール", "@language": "ja-hrkt"}] |
| 表示ラベル | "ドラゴンボール 1" |
| raw volume | "1" |
| ISBN raw | "4088734440" |
| Creator responsibility | "[著]鳥山明" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C53398"} |
| Publisher | "集英社" |
| Publisher reference | "P4080000000" |
| Label | ["ジャンプ・コミックス", {"@value": "ジャンプ コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2002-12" |
| Edition | "完全版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "20359565" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | "完全版" |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C257147](https://mediaarts-db.artmuseums.go.jp/id/C257147) |
| Series title | ["ドラゴンボール", {"@value": "ドラゴン ボール", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "完全版", "brand": ["ジャンプ・コミックス", {"@value": "ジャンプ コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 9. 美少女戦士セーラームーン 10

Book URI: [M256854](https://mediaarts-db.artmuseums.go.jp/id/M256854)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["美少女戦士セーラームーン", {"@value": "ビショウジョ センシ セーラームーン", "@language": "ja-hrkt"}] |
| 表示ラベル | "美少女戦士セーラームーン 10" |
| raw volume | "10" |
| ISBN raw | "4063348733" |
| Creator responsibility | "[著]武内直子" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C56940"} |
| Publisher | "講談社　∥　コウダンシャ" |
| Publisher reference | "P4060000000" |
| Label | ["KCデラックス", {"@value": "KC デラックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2004-05" |
| Edition | "新装版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "20601228" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 10 |
| Series URI | [C293194](https://mediaarts-db.artmuseums.go.jp/id/C293194) |
| Series title | ["美少女戦士セーラームーン", {"@value": "ビショウジョ センシ セーラームーン", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "新装版", "brand": ["KCデラックス", {"@value": "KC デラックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 10. AKIRA 1

Book URI: [M255124](https://mediaarts-db.artmuseums.go.jp/id/M255124)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["AKIRA", {"@value": "アキラ", "@language": "ja-hrkt"}] |
| 表示ラベル | "AKIRA 1" |
| raw volume | "1" |
| ISBN raw | "4061744682" |
| Creator responsibility | ["[カバーデザイン]ツカモトルーム", "[原作・脚本・監督]大友克洋"] |
| Creator URI | [{"@id": "https://mediaarts-db.artmuseums.go.jp/id/C55211"}, {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C69465"}] |
| Publisher | "講談社" |
| Publisher reference | "P4060000000" |
| Label | ["講談社アニメコミックス", {"@value": "コウダンシャ アニメ コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "1988-08-29" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | —（このレコードに値なし） |
| Label number / other product ID | "68" |
| 別タイトル | ["ネオ東京2019", {"@value": "ネオ トウキョウ 2019", "@language": "ja-hrkt"}] |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C293900](https://mediaarts-db.artmuseums.go.jp/id/C293900) |
| Series title | ["AKIRA", {"@value": "アキラ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["講談社アニメコミックス", {"@value": "コウダンシャ アニメ コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 11. 寄生獣 1

Book URI: [M437792](https://mediaarts-db.artmuseums.go.jp/id/M437792)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["寄生獣", {"@value": "キセイジュウ", "@language": "ja-hrkt"}] |
| 表示ラベル | "寄生獣 1" |
| raw volume | "1" |
| ISBN raw | "9784063770483" |
| Creator responsibility | "[著]岩明均" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C58227"} |
| Publisher | "講談社　∥　コウダンシャ" |
| Publisher reference | "P4060000000" |
| Label | "KCDX" |
| 公開年月日 | "2014-08" |
| Edition | "新装版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "22452694" |
| Label number / other product ID | "3648" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C349038](https://mediaarts-db.artmuseums.go.jp/id/C349038) |
| Series title | ["寄生獣", {"@value": "キセイジュウ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "新装版", "brand": "KCDX"} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 12. ブラック・ジャック 1

Book URI: [M276768](https://mediaarts-db.artmuseums.go.jp/id/M276768)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["ブラック・ジャック", {"@value": "ブラック ジャック", "@language": "ja-hrkt"}] |
| 表示ラベル | "ブラック・ジャック 1" |
| raw volume | "1" |
| ISBN raw | "4253207510" |
| Creator responsibility | "[著]手塚治虫" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C48012"} |
| Publisher | "秋田書店　∥　アキタ ショテン" |
| Publisher reference | "P4253000000" |
| Label | ["少年チャンピオン・コミックス", {"@value": "ショウネン チャンピオン コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2004-11" |
| Edition | "新装版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "20678389" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C279443](https://mediaarts-db.artmuseums.go.jp/id/C279443) |
| Series title | ["ブラック・ジャック", {"@value": "ブラック ジャック", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "新装版", "brand": ["少年チャンピオン・コミックス", {"@value": "ショウネン チャンピオン コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 13. 攻殻機動隊 1.5

Book URI: [M242946](https://mediaarts-db.artmuseums.go.jp/id/M242946)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["攻殻機動隊", {"@value": "コウカク キドウタイ", "@language": "ja-hrkt"}] |
| 表示ラベル | "攻殻機動隊 1.5" |
| raw volume | "1.5" |
| ISBN raw | "9784063754537" |
| Creator responsibility | "[著]士郎正宗" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C55526"} |
| Publisher | "講談社　∥　コウダンシャ" |
| Publisher reference | "P4060000000" |
| Label | ["KCデラックス", {"@value": "KC デラックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2008-03" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "21386165" |
| Label number / other product ID | "2453" |
| 別タイトル | "human error processer" |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1.5 |
| Series URI | [C298613](https://mediaarts-db.artmuseums.go.jp/id/C298613) |
| Series title | ["攻殻機動隊", {"@value": "コウカク キドウタイ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": "ヤングマガジンKCデラックス"} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 14. キジトラ猫の小梅さん 25

Book URI: [M1032568](https://mediaarts-db.artmuseums.go.jp/id/M1032568)。endpoint 照合済み。

| 項目 | 値 |
|---|---|
| Book title | ["キジトラ猫の小梅さん", {"@value": "キジトラネコ ノ コウメサン", "@language": "ja-hrkt"}] |
| 表示ラベル | "キジトラ猫の小梅さん 25" |
| raw volume | "25" |
| ISBN raw | "9784785977382" |
| Creator responsibility | ["ほしのなつみ", {"@value": "ホシノナツミ", "@language": "ja-hrkt"}] |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C48379"} |
| Publisher | "少年画報社" |
| Publisher reference | —（このレコードに値なし） |
| Label | ["ねこぱんちコミックス", {"@value": "ネコ パンチ コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2024-08-06" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | "https://ndlsearch.ndl.go.jp/books/R100000002-I033625982" |
| JPNO (NDL Bib ID とは別) | "24023323" |
| Label number / other product ID | "" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 25 |
| Series URI | 未取得 |
| Series title | —（このレコードに値なし） |
| Series edition / label | {"edition": null, "brand": null} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 15. パタリロ! 1

Book URI: [M299514](https://mediaarts-db.artmuseums.go.jp/id/M299514)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["パタリロ!", {"@value": "パタリロ", "@language": "ja-hrkt"}] |
| 表示ラベル | "パタリロ! 1" |
| raw volume | "1" |
| ISBN raw | —（このレコードに値なし） |
| Creator responsibility | ["[著]魔夜峰央", {"@value": "マヤミネオ", "@language": "ja-hrkt"}] |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C52860"} |
| Publisher | ["[発売]白泉社", "白泉社", "白泉社　∥　ハクセンシャ"] |
| Publisher reference | "P4592000000" |
| Label | ["花とゆめcomics", "花とゆめコミックス", {"@value": "ハナ ト ユメ comics", "@language": "ja-hrkt"}, {"@value": "ハナトユメ コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "1979-11-20" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "82031594" |
| Label number / other product ID | "180" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C259719](https://mediaarts-db.artmuseums.go.jp/id/C259719) |
| Series title | ["パタリロ!", {"@value": "パタリロ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["花とゆめコミックス", {"@value": "ハナ ト ユメ コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 16. パタリロ! 100

Book URI: [M522378](https://mediaarts-db.artmuseums.go.jp/id/M522378)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["パタリロ!", {"@value": "パタリロ", "@language": "ja-hrkt"}] |
| 表示ラベル | "パタリロ! 100" |
| raw volume | "100" |
| ISBN raw | "9784592215004" |
| Creator responsibility | "[著]魔夜峰央" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C52860"} |
| Publisher | "白泉社　∥　ハクセンシャ" |
| Publisher reference | —（このレコードに値なし） |
| Label | ["花とゆめCOMICS", {"@value": "ハナ ト ユメ コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2018-11" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "23141359" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 100 |
| Series URI | [C259719](https://mediaarts-db.artmuseums.go.jp/id/C259719) |
| Series title | ["パタリロ!", {"@value": "パタリロ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["花とゆめコミックス", {"@value": "ハナ ト ユメ コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 17. 星恋華 9

Book URI: [M189717](https://mediaarts-db.artmuseums.go.jp/id/M189717)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["星恋華", {"@value": "ホシレンゲ", "@language": "ja-hrkt"}] |
| 表示ラベル | "星恋華 9" |
| raw volume | "9" |
| ISBN raw | "4391914638" |
| Creator responsibility | "[著]佐伯かよの" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C50948"} |
| Publisher | "主婦と生活社" |
| Publisher reference | "P4391000000" |
| Label | ["ミッシィコミックス", {"@value": "ミッシィ コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "1993-12" |
| Edition | ["改訂版", "普及版"] |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | —（このレコードに値なし） |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 9 |
| Series URI | [C268153](https://mediaarts-db.artmuseums.go.jp/id/C268153) |
| Series title | ["星恋華", {"@value": "ホシレンゲ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": ["改訂版", "普及版"], "brand": ["ミッシィコミックス", {"@value": "ミッシィ コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 18. もやしもん 3

Book URI: [M190666](https://mediaarts-db.artmuseums.go.jp/id/M190666)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["もやしもん", {"@value": "モヤシモン", "@language": "ja-hrkt"}] |
| 表示ラベル | "もやしもん 3" |
| raw volume | "3" |
| ISBN raw | "4063721531" |
| Creator responsibility | "[著]石川雅之" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C58994"} |
| Publisher | "講談社　∥　コウダンシャ" |
| Publisher reference | "P4060000000" |
| Label | ["イブニングKCDX", {"@value": "イブニング KC DX", "@language": "ja-hrkt"}] |
| 公開年月日 | "2006-05" |
| Edition | "特装版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "21033691" |
| Label number / other product ID | "2153" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 3 |
| Series URI | [C267879](https://mediaarts-db.artmuseums.go.jp/id/C267879) |
| Series title | ["もやしもん", {"@value": "モヤシモン", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["イブニングKC", {"@value": "イブニング KC", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 19. サイキック・ドクター越智啓子の不思議クリニック 1

Book URI: [M192790](https://mediaarts-db.artmuseums.go.jp/id/M192790)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["サイキック・ドクター越智啓子の不思議クリニック", {"@value": "サイキック ドクター オチ ケイコ ノ フシギ クリニック", "@language": "ja-hrkt"}] |
| 表示ラベル | "サイキック・ドクター越智啓子の不思議クリニック 1" |
| raw volume | "1" |
| ISBN raw | "9784022670885" |
| Creator responsibility | "[画]森村真琴,堆木庸" |
| Creator URI | [{"@id": "https://mediaarts-db.artmuseums.go.jp/id/C63716"}, {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C63738"}] |
| Publisher | "朝日新聞社　∥　アサヒ シンブンシャ" |
| Publisher reference | "P4020000000" |
| Label | ["ソノラマコミック文庫", {"@value": "ソノラマ コミック ブンコ", "@language": "ja-hrkt"}] |
| 公開年月日 | "2007-10" |
| Edition | "新版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "21331757" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C266920](https://mediaarts-db.artmuseums.go.jp/id/C266920) |
| Series title | ["サイキック・ドクター越智啓子の不思議クリニック", {"@value": "サイキック ドクター オチ ケイコ ノ フシギ クリニック", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "新版", "brand": ["ソノラマコミック文庫", {"@value": "ソノラマ コミック ブンコ", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 20. 劇画トヨタ喜一郎

Book URI: [M196308](https://mediaarts-db.artmuseums.go.jp/id/M196308)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["劇画トヨタ喜一郎", {"@value": "トヨタ キイチロウ", "@language": "ja-hrkt"}] |
| 表示ラベル | "劇画トヨタ喜一郎" |
| raw volume | —（このレコードに値なし） |
| ISBN raw | —（このレコードに値なし） |
| Creator responsibility | ["[原作]木本正次", "[画]影丸譲也"] |
| Creator URI | [{"@id": "https://mediaarts-db.artmuseums.go.jp/id/C47534"}, {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C77543"}] |
| Publisher | "産業技術記念館　∥　サンギョウ ギジュツ キネンカン" |
| Publisher reference | "P0000088890" |
| Label | —（このレコードに値なし） |
| 公開年月日 | "1994-06" |
| Edition | "復刻版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "21473943" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 未決定（raw を保持） |
| Series URI | [C318692](https://mediaarts-db.artmuseums.go.jp/id/C318692) |
| Series title | ["劇画トヨタ喜一郎", {"@value": "トヨタ キイチロウ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "復刻版", "brand": null} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 21. 月は東に日は西に 1

Book URI: [M196908](https://mediaarts-db.artmuseums.go.jp/id/M196908)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["月は東に日は西に", {"@value": "ツキ ワ ヒガシ ニ ヒ ワ ニシ ニ", "@language": "ja-hrkt"}] |
| 表示ラベル | "月は東に日は西に 1" |
| raw volume | "1" |
| ISBN raw | "4592138163" |
| Creator responsibility | "[著]わかつきめぐみ" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C57665"} |
| Publisher | "白泉社" |
| Publisher reference | "P4592000000" |
| Label | —（このレコードに値なし） |
| 公開年月日 | "1991-12-01" |
| Edition | "愛蔵版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | —（このレコードに値なし） |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 1 |
| Series URI | [C318253](https://mediaarts-db.artmuseums.go.jp/id/C318253) |
| Series title | ["月は東に日は西に", {"@value": "ツキ ワ ヒガシ ニ ヒ ワ ニシ ニ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "愛蔵版", "brand": null} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 22. 07-ghost 5

Book URI: [M807088](https://mediaarts-db.artmuseums.go.jp/id/M807088)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["07-ghost", {"@value": "セブン ゴースト", "@language": "ja-hrkt"}] |
| 表示ラベル | "07-ghost 5" |
| raw volume | "5" |
| ISBN raw | "9784758031387" |
| Creator responsibility | "[著]雨市" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C52686"} |
| Publisher | "一迅社　∥　イチジンシャ" |
| Publisher reference | —（このレコードに値なし） |
| Label | ["IDコミックス", "Zero-sum comics", {"@value": "ID コミックス. Zero-sum comics", "@language": "ja-hrkt"}] |
| 公開年月日 | "2015-12" |
| Edition | "文庫版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "23231197" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 5 |
| Series URI | [C357047](https://mediaarts-db.artmuseums.go.jp/id/C357047) |
| Series title | ["07-GHOST", {"@value": "セブン ゴースト", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": "文庫版", "brand": ["IDコミックス　／　Zero-sum comics", {"@value": "ID コミックス　／　Zero-sum comics", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 23. 太陽が見ている（かもしれないから） 3

Book URI: [M452977](https://mediaarts-db.artmuseums.go.jp/id/M452977)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["太陽が見ている（かもしれないから）", {"@value": "タイヨウ ガ ミテ イル カモ シレナイ カラ", "@language": "ja-hrkt"}] |
| 表示ラベル | "太陽が見ている（かもしれないから） 3" |
| raw volume | "3" |
| ISBN raw | "9784088454511" |
| Creator responsibility | "[著]いくえみ綾" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C57286"} |
| Publisher | "集英社　∥　シュウエイシャ" |
| Publisher reference | "P4080000000" |
| Label | ["マーガレットコミックス", {"@value": "マーガレット コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2015-09" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "22634289" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 3 |
| Series URI | [C347839](https://mediaarts-db.artmuseums.go.jp/id/C347839) |
| Series title | ["太陽が見ている かもしれないから", {"@value": "タイヨウ ガ ミテ イル", "@language": "ja-hrkt"}, {"@value": "タイヨウ ガ ミテ イル カモ シレナイ カラ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["マーガレットコミックス", {"@value": "マーガレット コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

`schema:description` に「電子版描きおろし〆切その後エッセイ」がある。これは収録内容の文字列であり、電子版 Book である根拠に使えない。

## 24. ふしぎ遊戯 玄武開伝 五

Book URI: [M208827](https://mediaarts-db.artmuseums.go.jp/id/M208827)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["ふしぎ遊戯 玄武開伝", {"@value": "フシギ ユウギ ゲンブ カイデン", "@language": "ja-hrkt"}] |
| 表示ラベル | "ふしぎ遊戯 玄武開伝 五" |
| raw volume | "五" |
| ISBN raw | ["4091384757", "409159008X"] |
| Creator responsibility | "[著]渡瀬悠宇" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C56414"} |
| Publisher | "小学館　∥　ショウガクカン" |
| Publisher reference | "P4090000000" |
| Label | ["少コミフラワーコミックス", {"@value": "ショウコミ フラワー コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2005-12" |
| Edition | "ドラマCD付きプレミアム版" |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "20954620" |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 未決定（raw を保持） |
| Series URI | [C312981](https://mediaarts-db.artmuseums.go.jp/id/C312981) |
| Series title | ["ふしぎ遊戯 玄武開伝", {"@value": "フシギ ユウギ ゲンブ カイデン", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["少コミフラワーコミックス", {"@value": "ショウコミ フラワー コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 25. 好きって言わせる方法 4

Book URI: [M190399](https://mediaarts-db.artmuseums.go.jp/id/M190399)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["好きって言わせる方法", {"@value": "make you say I love you", "@language": "ja-hrkt"}, {"@value": "スキ ッテ イワセル ホウホウ", "@language": "ja-hrkt"}] |
| 表示ラベル | "好きって言わせる方法 4" |
| raw volume | "4" |
| ISBN raw | ["4088466361", "9784088466361"] |
| Creator responsibility | "[著]永田正実" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C57515"} |
| Publisher | "集英社　∥　シュウエイシャ" |
| Publisher reference | "P4080000000" |
| Label | ["マーガレットコミックス", "別冊マーガレット", {"@value": "ベッサツ マーガレット", "@language": "ja-hrkt"}, {"@value": "マーガレット コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2011-03-30" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "21913763" |
| Label number / other product ID | "4636" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 4 |
| Series URI | [C268155](https://mediaarts-db.artmuseums.go.jp/id/C268155) |
| Series title | ["好きって言わせる方法", {"@value": "スキ ッテ イワセル ホウホウ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["マーガレットコミックス", {"@value": "マーガレット コミックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 26. さらば、漫画よ 上

Book URI: [M1032913](https://mediaarts-db.artmuseums.go.jp/id/M1032913)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["さらば、漫画よ", {"@value": "Goodby", "@language": "en"}, {"@value": "サラバ マンガ ヨ", "@language": "ja-hrkt"}] |
| 表示ラベル | "さらば、漫画よ 上" |
| raw volume | "上" |
| ISBN raw | "9784781623733" |
| Creator responsibility | ["高見奈緒", {"@value": "タカミナオ", "@language": "ja-hrkt"}] |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C438738"} |
| Publisher | "イースト・プレス" |
| Publisher reference | —（このレコードに値なし） |
| Label | ["", {"@value": "", "@language": "ja-hrkt"}] |
| 公開年月日 | "2024-09-06" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | "https://ndlsearch.ndl.go.jp/books/R100000002-I033686059" |
| JPNO (NDL Bib ID とは別) | "24026265" |
| Label number / other product ID | "" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 未決定（raw を保持） |
| Series URI | 未取得 |
| Series title | —（このレコードに値なし） |
| Series edition / label | {"edition": null, "brand": null} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 27. バイバイバイ 下

Book URI: [M1032672](https://mediaarts-db.artmuseums.go.jp/id/M1032672)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["バイバイバイ", {"@value": "By", "@language": "en"}, {"@value": "バイバイバイ", "@language": "ja-hrkt"}] |
| 表示ラベル | "バイバイバイ 下" |
| raw volume | "下" |
| ISBN raw | "9784088842325" |
| Creator responsibility | ["あんねこ", {"@value": "アンネコ", "@language": "ja-hrkt"}] |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C445173"} |
| Publisher | "集英社" |
| Publisher reference | —（このレコードに値なし） |
| Label | ["ジャンプコミックス", {"@value": "ジャンプ コミックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "2024-09-06" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | "https://ndlsearch.ndl.go.jp/books/R100000002-I033671615" |
| JPNO (NDL Bib ID とは別) | "24023465" |
| Label number / other product ID | "" |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 未決定（raw を保持） |
| Series URI | 未取得 |
| Series title | —（このレコードに値なし） |
| Series edition / label | {"edition": null, "brand": null} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 28. 工業哀歌バレーボーイズ　 別巻

Book URI: [M224983](https://mediaarts-db.artmuseums.go.jp/id/M224983)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["工業哀歌バレーボーイズ　", {"@value": "コウギョウ アイカ バレー ボーイズ", "@language": "ja-hrkt"}] |
| 表示ラベル | "工業哀歌バレーボーイズ　 別巻" |
| raw volume | "別巻" |
| ISBN raw | "4063613135" |
| Creator responsibility | "[著]村田ひろゆき" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C55714"} |
| Publisher | "講談社　∥　コウダンシャ" |
| Publisher reference | "P4060000000" |
| Label | ["ヤンマガKCスペシャル", {"@value": "ヤンマガ KC スペシャル", "@language": "ja-hrkt"}] |
| 公開年月日 | "2005-03" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | "20748251" |
| Label number / other product ID | "1313" |
| 別タイトル | ["虎子", {"@value": "トラコ", "@language": "ja-hrkt"}] |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 未決定（raw を保持） |
| Series URI | [C306033](https://mediaarts-db.artmuseums.go.jp/id/C306033) |
| Series title | ["工業哀歌バレーボーイズ", {"@value": "コウギョウ アイカ バレー ボーイズ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["ヤンマガKCスペシャル", {"@value": "ヤンマガ KC スペシャル", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

## 29. 霊媒師多比野福助 外伝

Book URI: [M353277](https://mediaarts-db.artmuseums.go.jp/id/M353277)。release JSON-LD 確認。

| 項目 | 値 |
|---|---|
| Book title | ["霊媒師多比野福助", {"@value": "スピリッツ マスター タビノ フクスケ", "@language": "ja-hrkt"}] |
| 表示ラベル | "霊媒師多比野福助 外伝" |
| raw volume | "外伝" |
| ISBN raw | "4056004188" |
| Creator responsibility | "[著]速水翼" |
| Creator URI | {"@id": "https://mediaarts-db.artmuseums.go.jp/id/C55500"} |
| Publisher | "学習研究社" |
| Publisher reference | "P4050000000" |
| Label | ["ピチコミックスミステリーDX", {"@value": "ピチ コミックス ミステリー デラックス", "@language": "ja-hrkt"}] |
| 公開年月日 | "1994-04-01" |
| Edition | —（このレコードに値なし） |
| 言語 | "日本語" |
| 外部出典 URL / NDL | —（このレコードに値なし） |
| JPNO (NDL Bib ID とは別) | —（このレコードに値なし） |
| Label number / other product ID | —（このレコードに値なし） |
| 別タイトル | —（このレコードに値なし） |
| 巻副題 | —（このレコードに値なし） |
| normalized volume candidate | 未決定（raw を保持） |
| Series URI | [C286629](https://mediaarts-db.artmuseums.go.jp/id/C286629) |
| Series title | ["霊媒師=多比野福助", {"@value": "スピリッツ マスター タビノフクスケ", "@language": "ja-hrkt"}, {"@value": "レイバイ シ タビノ フクスケ", "@language": "ja-hrkt"}] |
| Series edition / label | {"edition": null, "brand": ["ピチコミックスミステリー", {"@value": "ピチ コミックス ミステリー デラックス", "@language": "ja-hrkt"}]} |
| Work URI / title | 未取得 |
| Material / digital status | 未確定 |

