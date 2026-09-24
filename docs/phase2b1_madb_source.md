# Phase 2B-1: MADB read-only source

Phase 1 の正式リリース 0.1.12 を基準に、内部 source layer を追加した。
ローカル package version は 0.2.0。正準定義は `comictagger_jp_talker/__init__.py` の
`__version__` で、setuptools の dynamic version と既存 plugin builder がこれを参照する。
新しい production dependency、ユーザー設定、Release 操作は追加していない。

設計根拠は [Phase 2A 仕様書](phase2_madb_spec.md)、[実例台帳](research/madb/examples.md)、
[実測記録](research/madb/evidence.json)、[query](research/madb/queries/)。
Phase 2A の成果物は変更せず、Work の延期は今回の明示的なスコープに従う。

## API と実装

```python
from pathlib import Path
from comictagger_jp_talker.sources.madb import MADBSource

with MADBSource(Path("cache")) as source:
    page = source.search_by_isbn("9784832241190")
    for candidate in page.records:
        print(candidate.id, candidate.uri, candidate.isbns)
    bundle = source.get("M381096")  # 正準 Book URI も可
    print(bundle.book, bundle.series, bundle.warnings, bundle.completeness)
```

- `search_by_isbn(isbn, *, refresh=False)` は `MADBSearchPage` を返す。
  同一 URI だけを重複排除し、URI 順で返す。先頭候補に正解という意味はない。
- `get(book_id_or_uri, *, refresh=False)` は `MADBRecordBundle` を返す。
  Book の直接 triples、Series、creator/publisher Agent URI、holding を必要な範囲で取得する。
- `check_status()` は明示的な source 単体の疎通確認。正常 0 件も正常な通信として扱う。
- `close()` と context manager により Session / ComicCacher を閉じる。
  constructor、import はネットワークへアクセスしない。

`sources/madb_queries.py` は literal escape、ISBN 候補、許可 ID/URI と bounded SELECT を担当する。
`sources/madb_parser.py` は SPARQL JSON 検証と raw record 構築を担当する。
`sources/madb_models.py` は以下の immutable source-specific model を定義する。

- `RDFTerm`、`MADBStatement`、`MADBCredit`、`ExternalIdentifier`
- `MADBBookRecord`、`MADBSeriesRecord`、`MADBAgentRecord`、`MADBHoldingRecord`
- `MADBRecordBundle`、`MADBSearchResult`、`MADBSearchPage`

URI / literal / bnode、datatype、language、未知 predicate を保存する。
読みの `ja-hrkt`、複数 brand、巻次、日付、不正値も raw のまま残す。
credit の先頭 role は名前候補と分離するが、Agent と順序で結合せず association は unresolved。
Agent の個人・団体を ID prefix から推定しない。P 番号の publisher literal を URI と扱わない。
Supplement は Book に紐づく snapshot であり、永続 Book identity ではない。
ISBN、JPNO、NDL Search URL、Agent 典拠 URI、provider 付き所蔵資料 ID は別 scheme。
provider が単一名称として取得できない所蔵資料 ID の normalized 値は未設定。
所蔵資料 ID を NDL Bib ID に読み替えない。`schema:productID` は raw statement のみ。

## Query / transport / cache

endpoint は `https://mediaarts-db.artmuseums.go.jp/sparql` に固定。
Phase 2A 実測の `data/class#`、`data/property#`、`https://schema.org/` を使う。
form POST / SPARQL JSON を用い、redirect を追跡しない。任意 endpoint / raw SPARQL を受け取らない。
Book は M 番号、Series / Agent は C 番号、Supplement は ref 配下の S 番号に限定し、
返却された rdf:type を検証する。Book / Series の identifier と URI の整合を確認する。
literal の改行・タブ・引用符・バック スラッシュは escape し、その他の制御文字と孤立 surrogate は拒否。

ISBN discovery は Book URI / identifier / 一致した raw ISBN だけを取得する。
既存 `isbn.py` の checksum 検証と ISBN-10/13 相互変換を再利用し、978 の 13 桁入力でも
10 桁候補を検索する。979 は 13 桁のみ。不正入力は通信前に `ValueError`。
raw ISBN の set 表記・指数表記・checksum error は修復せず、normalized 値を未設定で保存する。
同じ Book の複数 ISBN と異なる Book の同一 ISBN を保持する。

| 制限 | 方針 |
|---|---|
| 検索 | 既定 20 行、最大 100 行。同一 Book の複数 ISBN 行も数えるため候補数はこれ以下 |
| 直接 triples | 各 resource 既定 300 行、最大 1,000 行 |
| 関連取得 | get 当たり最大 12 resource。Book 本体を含め最大 13 request |
| 応答サイズ | 展開後 2 MiB。stream 中に上限を検査して中断 |
| timeout | connect 5 秒、read 30 秒。read は requests の無通信時間制限 |
| rate limiter | 同一プロセスで通信 1 件ずつ、開始間隔 3 秒以上。NDL とは独立 |
| retry | 自動 retry なし。遅い query の負荷増幅を避け、error classification と caller retry に限定 |

rate limit は local conservative policy であり公式 quota ではない。
HTTP error には status / Retry-After を保持する。full response は通常ログへ出力しない。

ComicCacher は専用 folder `jpbooks-madb-v1` を使用する。
論理 namespace は `madb:query:v1`、`madb:resource:v1`、`madb:relation:v1`。
キーは固定 endpoint、parser namespace、query 本文・LIMIT、relation の親 URI / predicate / kind を含む。
query の簡易結果を resource cache に流用しない。relation の Supplement は親 Book の範囲に限定する。
host の search expiration（現在 7 日）に従い、独自 TTL / SQLite は導入しない。
cache hit でも parser と完全性を再検証し、破損なら warning と network refresh を行う。
正常 0 件 search は cache 可。error / truncated resource は cache しない。bundle 自体も cache しない。
関連取得に失敗しても、個別に成功した完全な resource cache は使用できる。
`refresh=True` は Book と取得対象 relation を含めて cache を迂回する。

## 完全性とエラー

`MADBError` は host `TalkerError` を継承し、`kind` で network / http / rate_limited /
timeout / protocol / query / schema / not_found / truncated を区別する。
HTML 200、JSON 破損、head/results/bindings 欠損、未知 term type は正常 0 件に変換しない。
HTTP 400 は query error、429 は rate_limited。それ以外の非 200 は http error。
Book 自体の失敗は例外。relation の失敗は Book を残した partial bundle と warning。
Book の Series 欠損は正常な空 tuple。URI 以外の未解決 relation は raw を残して warning。
LIMIT 到達は保守的に truncated とする。型・identity まで欠けた切り詰め応答は例外とする。
byte / row cap を超えた応答も truncated error とし、不完全 JSON の部分復元は行わない。

## 統合境界

NDL/MADB merge、GenericMetadata mapping、Series / Imprint / Credits / Publisher / Date の上書きは未実装。
title fuzzy search、電子／紙判定、RecordMatch、MangaWork model / lookup も未実装。
通常の Japanese Books 検索・fetch・status は NDL のみ。MADB 停止の影響を受けない。
Series の `hasPart` や Work を required join にしない。

## 検証手順

```powershell
python -m ruff check .
python -m pytest -m "not network"
$env:JPBOOKS_RUN_NETWORK_TESTS = "1"
python -m pytest tests/test_madb_integration.py -m network
Remove-Item Env:JPBOOKS_RUN_NETWORK_TESTS
git diff --check
python -m build
$wheels = @(Get-ChildItem dist\comictagger_jp_talker-*-py3-none-any.whl)
if ($wheels.Count -ne 1) { throw "Expected exactly one wheel" }
python scripts/build_plugin.py $wheels[0].FullName
```

build 前に古い dist / build / generated egg-info を除去する。
unit tests は架空 SPARQL JSON、破損 cache、各種失敗、LIMIT、raw 保持、入力検証を扱う。
既存 NDL fixture の v0.1.12 metadata snapshot を全番号モードで比較し、MADB 自動起動を禁止する。
network tests は Phase 2A の M381096 → C334830 と ISBN-10-only M299519 を意図的な現時点 baseline とする。
公開データの更新による変更時は evidence を確認し、無条件に期待値を弱めない。

## Phase 2B-2 以降

今回の対象外: direct NDL URL comparison、ISBN exact/equivalent RecordMatch、candidate ambiguity handling、
Series field comparison、provenance / FieldEvidence、conflict state。
