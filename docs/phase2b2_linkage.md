# Phase 2B-2: NDL / MADB linkage と Series comparison

0.2.1 development。0.2.0 の正式 Release、Phase 2B-1 の source foundation、
Phase 1 の Series 修正を基点にした内部 API。今回 Release は行わない。
目的は同一資料の対応関係と Series の一致・不一致を観測すること。
値の採用、上書き、GenericMetadata / ComicInfo.xml への MADB mapping は含まない。

## 根拠と構成

[Phase 2A 仕様書](phase2_madb_spec.md)、[実例台帳](research/madb/examples.md)、
[実測記録](research/madb/evidence.json)、[Phase 2B-1](phase2b1_madb_source.md) を前提とする。
同じ正規化 ISBN を複数 Book が共有する実測結果と、Book の `ma:dataUrl` を使用する。
JPNO、Agent の典拠 URI、Holding の資料 ID は Book の直接 NDL identity に読み替えない。

| ファイル | 役割 |
|---|---|
| `linkage.py` | 明示的な候補取得、純粋な候補照合、identity / confidence / error model |
| `provenance.py` | FieldEvidence、SeriesComparison、既存 Phase 1 の推定を利用する比較 |
| `sources/madb*.py` | 既存の取得・RDF 解析・cache・limiter。変更なし |
| `mapping.py` / `sources/ndl.py` / `talker.py` | 既存の通常経路。変更なし |

依存パッケージ、persistent cache、SPARQL template、UI option は追加していない。
import や通常 Talker lookup は MADB 通信を起動しない。

## API

```python
from pathlib import Path

from comictagger_jp_talker.linkage import compare_candidates, link_ndl_record
from comictagger_jp_talker.sources.madb import MADBSource

# record は既存 NDLSource から取得した BookRecord。
with MADBSource(Path("cache")) as source:
    result = link_ndl_record(record, source)
    # ISBN がなくても、外部で既知の Book を指定した直接照合は可能。
    bundle = source.get("M381096")
    comparison = compare_candidates(record, [bundle])
```

`link_ndl_record(record, madb_source, *, refresh=False)` は有効 ISBN-13 の集合を作り、
それぞれを既存 `search_by_isbn()` に渡す。候補 ID を重複排除してから `get()` する。
source の ISBN-10 / 13 両形式の検索、通信制限、cache をそのまま使う。
`refresh=True` は検索と Book / relation 取得へ伝播する。
ISBN がない場合は通信せず unmatched。NDL URL による全 MADB 逆検索は追加していない。

`compare_candidates(record, candidates, *, truncated=False, warnings=())` は通信を伴わない。
一意性は渡された集合の範囲内であり、全 MADB の一意性を保証しない。
呼び出し側は不完全な候補集合に `truncated=True` を指定する必要がある。
同じ Book ID の同一 snapshot は重複排除し、異なる snapshot の混在は `ValueError` とする。
全候補は ID 順に保持し、順番で候補を採用しない。

## Model と status

すべて frozen dataclass。enum は文字列値を持つ。

| Model | 保持する情報 |
|---|---|
| `RecordMatch` | NDL / MADB ID、confidence、reasons、conflicts、evidence、candidate_count、algorithm_version、任意の SeriesComparison |
| `LinkageResult` | status、全照合結果、候補 summary、warnings、任意の structured error、truncated |
| `CandidateSummary` | Book ID / URI / completeness。巨大な RDF bundle を複製しない。未取得なら completeness=None |
| `LinkageError` | MADBError の kind / message / HTTP status / Retry-After |
| `FieldEvidence` | source、field、value、raw_value、record ID / URI、predicate/path、transform、関連 URI |
| `SeriesComparison` | state、NDL evidence、全 MADB name evidence、別の比較 key、relation evidence、既存の論理巻解決結果、warnings |

`MatchConfidence`: exact / strong / ambiguous / unsafe。
`LinkageStatus`: matched / unmatched / ambiguous / unavailable / unsafe。
`MatchReason`: direct_ndl_url / isbn_raw / isbn_normalized / isbn_10_13_equivalent。
`MatchConflict`: ndl_url_mismatch / isbn_discrepancy。
`EvidenceSource`: ndl / madb。将来 source を enum に追加可能。
algorithm version は `phase2b2-v1` で、package version とは独立している。

候補に identity evidence も conflict もなければ RecordMatch を作らず、summary だけ残す。
matched 結果にも、選ばれていない ambiguous / unsafe candidate の RecordMatch は残る。
**呼び出し側は status と各 candidate の confidence を両方確認する必要がある。**

## Direct NDL URL と ISBN

Book の `ma:dataUrl` の literal / URI を、NDL `record.url` と比較する。
既存 `ndl_record_url()` を再利用し、HTTPS、正確な host `ndlsearch.ndl.go.jp`、
`/books/<許可された ID>`、query なしを要求する。fragment は除去する。
HTTP、他 host、query 付き、末尾 slash は同一資料の根拠にしない。
MADB parser の分類が `data_url` でも raw term から評価するので fragment 付きも扱える。
URL の不正値も evidence に残し、normalized value は None とする。

ISBN の checksum 検証と変換は既存 `isbn.py` の `isbn13()` / `normalize_isbn()` を使う。
ハイフン・空白・10 / 13 桁の等価性を扱い、無効値を修復しない。
全一致ペアについて正規化一致を残し、原文一致、10 / 13 桁の等価性も該当時に追加する。
無効値は raw evidence に残せるが、一致・矛盾の判定には使わない。

| 条件 | 判定 |
|---|---|
| 完全な Book の direct URL 一致、別 NDL URL なし | exact / matched |
| direct URL と ISBN の両方一致 | exact、両方の reason を保持 |
| direct URL 一致、有効 ISBN 集合が双方にあり交差なし | exact identity + isbn_discrepancy。field の不一致を隠さない |
| 正規化 ISBN 一致、候補が 1 件、完全な検索と Book | strong / matched。direct identity と同等にはしない |
| 複数 ISBN candidate、direct identity で確定できない | ambiguous。一方の URL が矛盾しても残りを自動的に strong にしない |
| 複数 candidate のうち 1 件だけ安全な direct identity | その candidate は exact。他候補と警告を残す |
| 複数 Book が同じ direct identity を主張 | ambiguous。Series の自動比較なし |
| 比較対象と異なる有効な direct NDL URL | unsafe。同じ URL も併記されていても unsafe |
| 検索 truncated | ISBN-only を strong にしない。完全な Book の direct identity は exact にできる |
| Book 本体の triples が不完全 | 隠れた URL 矛盾を否定できないため exact / strong にしない |
| 正常な検索 0 件、または根拠なし | unmatched。title / creator / publisher fallback なし |
| 検索または Book 取得の失敗 | unavailable。成功済み evidence / 発見済み候補 / error を保持 |

取得途中の失敗でも一意性を主張しない。ISBN-only の完了済み候補は ambiguous とし、
失敗した実行では Series を比較しない。HTTP 5xx / 429、timeout、connection error、
malformed JSON、schema error、発見後の Book 消失を正常 0 件に変換しない。
Series / Agent / Holding 取得の失敗は source の partial bundle として保持する。
Agent / Holding だけの失敗は、完全な Book identity や取得済み Series の比較を無効にはしない。

## Series と provenance

NDL は `infer_volume(record.title)` を直接再利用する。
通常 mapping の既存 Series 指定がない場合と同じ値であり、新しい parser は作らない。
空でないタイトルで巻次が分離できなければ、Phase 1 と同じくタイトル全体が候補となる。
`dcndl:seriesTitle` を作品 Series として代用しない。論理巻も `resolve_record_number()` を再利用する。

MADB は Book の `schema:isPartOf` で結ばれた MangaBookSeries の `schema:name` のみ。
brand、rdfs:label、ma:seriesName は代用しない。Book ID / URI、Series URI、
relation の raw term と name の raw RDFTerm（language / datatype を含む）、完全な predicate path を保持する。
NDL は record ID / URL、raw title、推定 Series、transform=`mapping.infer_volume` を保持する。

比較 key は **strip() + exact Unicode equality**。raw 値は変更しない。
句読点、`?`、`!`、`:`、volume、英語並列タイトルの削除や NFC / NFKC は行わない。

| State | 意味 |
|---|---|
| BOTH_AGREE | 双方に単一の比較値があり一致。値の採用を意味しない |
| BOTH_CONFLICT | 双方に単一の比較値があり不一致。正解 source は決めない |
| NDL_ONLY | NDL に候補があり、MADB に比較値がない |
| MADB_ONLY | NDL の候補が空で、MADB に比較値がある |
| NONE | 双方に比較値がない |
| MULTIPLE | 複数 Series URI、または strip 後に異なる複数 name。1 件一致しても合意としない |
| UNAVAILABLE | 関連 Series 未取得、未解決 relation、Series triples の切り詰め、不正な name term 等 |

自動比較は全体が matched で、十分な根拠を持つ candidate 1 件に限定する。
直接 `compare_series()` を使う場合は、呼び出し側が linkage 済みであることを確認する。

**言語選択は未実装。** `ja-hrkt` の読みや英語名も全件保持し、異なる名前なら MULTIPLE。
Phase 2A の C334830 は日本語名と読みの両方を持つため、日本語名が一致しても MULTIPLE になる。
これは別作品という断定ではなく、比較値を選ぶ方針が未決定という保守的な状態である。
異なる Series URI に同名が付く場合も、関係自体の複数性を残す。
未取得を NDL_ONLY / NONE と扱わず、空文字の原値と未取得を区別する。

## 通常出力との境界と制限

通常の search / fetch / status は従来の NDL 経路のみ。
GenericMetadata の series / title / issue / volume / credits / publisher / date / gtin /
description / notes / web_links は変更しない。FieldEvidence を Notes に出力しない。
MADB Series の上書き、Imprint、Credits merge、Publisher / Date mapping、自動 merge は未実装。
MangaWork、媒体の自動判定、source preference、title fuzzy linkage も含めない。

ISBN discovery は Phase 2B-1 の exact literal query の範囲に限られる。
手元の候補のハイフン付き ISBN は比較できるが、endpoint 上の任意のハイフン表記を
全文正規化検索する機能はない。ISBN なしの discovery と snapshot isolation も未対応。
Book identity の一致から作品・版・刷・媒体の完全な意味的一致を推論しない。
ネットワークで取得した実データは fixture や plugin ZIP に追加していない。

## 検証と Phase 2C の開始条件

`tests/test_linkage.py` は架空 RDF、実 source/parser/cache を通す mock integration、
Phase 1 回帰と provenance を検証する。既存 `test_madb_boundary.py` の固定 snapshot と
通信禁止検証を維持し、built ZIP の beta.9 load / NDL lookup にも MADB 禁止を追加した。

`tests/test_linkage_integration.py` は明示的な `JPBOOKS_RUN_NETWORK_TESTS=1` のときだけ実行する。
実例は Phase 2A の M1032568 / R100000002-I033625982 の direct URL、
M381096 / C334830 と Phase 1 の R100000002-I023440575 の ISBN / Series。
候補件数は dataset 更新で変わり得るため、複数化したら ambiguity を検証する。
通常 `python -m pytest -m "not network"` は外部 endpoint にアクセスしない。
実行結果と build 検証は [validation.md](validation.md) を参照する。

Phase 2C に進むには、次を確認する。

- direct URL linkage、ISBN-10 / 13 の等価性、重複候補の ambiguity。
- unavailable と unmatched の区別、切り詰めからの誤った一意性判定の防止。
- Series BOTH_AGREE / BOTH_CONFLICT / NDL_ONLY / MADB_ONLY と複数候補の保持。
- 原文・関係・変換の provenance 保持。
- 通常 NDL output の不変性、自動 MADB access がないこと。
- rate limiter を維持した opt-in network tests の安定性。今回の成功だけで長期安定を保証しない。

次の検討候補は controlled Series supplement、merge policy、provenance-aware field selection、
Imprint candidate evaluation、Credits comparison、利用者向け MADB integration policy。
言語別 Series 名の比較方針も必要になる。これらの Phase 2C 機能は今回実装しない。
