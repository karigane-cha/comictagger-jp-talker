# Phase 2C-1: controlled MADB Series supplement

v0.3.0 に含まれる実装。正式な直前 Release は v0.2.1、基点 commit は `ec9ad62`。
目的は NDL から Series が得られない場合だけ、利用者の明示的な opt-in と十分な照合根拠の下で補完すること。
MADB 全体の GenericMetadata mapping や source 優先順位は導入しない。
[Phase 2A](phase2_madb_spec.md)、[Phase 2B-1](phase2b1_madb_source.md)、
[Phase 2B-2](phase2b2_linkage.md) は歴史的記録として保持する。

## 構成と scope

| ファイル | 役割 |
|---|---|
| `provenance.py` | immutable SeriesNameClassification、既存比較への分類統合 |
| `series_supplement.py` | eligibility、Series-only output、出典 Notes、fail-open orchestration |
| `talker.py` | boolean setting と選択済み書誌 fetch の接続 |
| `sources/madb_parser.py` | Series の重複 raw statements も保持 |
| `linkage.py` / `sources/madb.py` | 共通の照合規則と軽量 Book / Series 取得。公開 full API も維持 |
| `sources/madb_models.py` | bundle の retrieval_scope で Agent / Holding 未取得を明示 |
| `sources/ndl.py` / `sources/ndl_summary.py` / `sources/base.py` | summary policy、optional failure、要求の重複抑止 |
| `mapping.py` | NDL-only の Phase 1 mapper。変更なし |

cross-source linkage を再実装せず、RecordMatch、LinkageResult、exact / strong / ambiguous / unsafe、
ISBN-10 / 13 等価性、直接 NDL URL evidence、unmatched / unavailable、truncated policy を維持する。
identity algorithm version は `phase2b2-v1`。Series name comparison の分類だけを精密化する。

## 表示名・読みの分類

対象は `MangaBook → schema:isPartOf → MangaBookSeries → schema:name` だけ。
`ma:seriesName`、`schema:brand`、`rdfs:label`、publisher、alternateName を代用しない。
RDF language metadata を使い、カタカナ / ASCII / 漢字の有無から推測しない。

| raw language | datatype | 分類 |
|---|---|---|
| `ja`（大小文字不問） | なし / `rdf:langString` | display |
| なし | なし / `xsd:string` | display |
| `ja-hrkt`（大小文字不問） | なし / `rdf:langString` | reading |
| その他の tag / datatype / 非 literal | 任意 | other |

タグなし display の根拠は Phase 2A の C334830 の raw schema:name と既存 MADB Series fixture。
`ja-Jpan`、`ja-Latn`、英語等は未対応。raw tag と datatype は変更しない。
未対応の非空名称は既知 display と同居していても自動選択を停止する。
非 literal name は従来どおり UNAVAILABLE。空文字 literal は raw に残し、有効値には数えない。

SeriesNameClassification は URI ごとに display_names / readings / other_names を FieldEvidence で保持する。
SeriesComparison.madb にも全 raw name evidence を残す。relation の raw term、Book ID / URI、Series URI、
predicate path、raw RDFTerm、language / datatype、既存 NDL provenance は失われない。
parser は Series の重複 statement も保持する。同一 URI 内の display だけを strip() 後の完全一致で重複除去する。
effective_display_values は比較 key。出力には最初の対応する非空 display の原文字列を使う。
NFC / NFKC、記号除去、大小文字変更、表示文字列の strip は行わない。別 URI は同名でも collapse しない。

## MULTIPLE semantics と C334830

1 Series URI + 1 effective display + 任意件数の認識済み reading は、reading を理由に MULTIPLE としない。
複数 URI、複数 distinct display、未対応の非空名称は MULTIPLE。
Series 未取得 / 不完全、未解決 relation、不正な name term は UNAVAILABLE。
BOTH_AGREE / BOTH_CONFLICT / NDL_ONLY / MADB_ONLY / NONE と exact Unicode 比較は維持する。

Phase 2A / v0.2.1 の M381096 → C334830 は表示 `ご注文はうさぎですか?`（タグなし）と
読み `ゴチュウモン ワ ウサギ デスカ`（`ja-hrkt`）を持つ。
v0.2.1 は両方を比較値に数えて MULTIPLE。新分類の effective display は前者 1 件で、
NDL の推定 Series が前者なら BOTH_AGREE。最新 endpoint の実測は [検証記録](validation.md) を参照する。
ネットワーク テストは raw 値 / tag も検査し、実データの変化を無条件で受け入れない。

## 設定と network trigger

key は `jpbooks_madb_series_supplement`、UI label は
**Supplement missing Series from MADB (experimental)**。既定 False、BooleanOptionalAction で登録する。
CLI は `--jpbooks-madb-series-supplement` / `--no-jpbooks-madb-series-supplement`。
保存・復元に対応し、旧 config に key がなくても OFF。非 boolean は state 変更前に拒否する。

NDL record fetch → Phase 1 mapping → Series の欠損と opt-in 確認 →
link_ndl_record_for_series → 共通 identity comparison → eligibility → supplement の順に処理する。
最終取得の `fetch_comic_data()` だけに接続する。beta.9 の `fetch_issues_in_series()` は issue 候補一覧、
`fetch_issues_by_series_issue_num_and_year()` は自動照合の候補絞り込みなので、補完を起動しない。
`search_for_series()`、`search_metadata()`、`fetch_series()`、`check_status()` も MADB を使わない。
OFF または非空 NDL Series では MADBSource / session / cache を生成しない。
ON で Series が whitespace-only の場合は空として扱う。既存の非空 Series は常に維持する。

## Eligibility matrix

| NDL Series | Setting | Linkage | MADB display | Result |
|---|---|---|---|---|
| 有 | OFF / ON | 任意 | 任意 | NDL 維持、MADB 通信なし |
| 無 | OFF | 任意 | 任意 | 補完なし、MADB 通信なし |
| 無 | ON | matched / exact | 一意で完全 | Series 補完 |
| 無 | ON | matched / strong | 一意で完全 | Series 補完 |
| 無 | ON | ambiguous / unsafe / unmatched | 任意 | 補完なし |
| 無 | ON | unavailable | 任意 | warning、NDL-only fallback |
| 無 | ON | search truncated（exact を含む） | 任意 | 補完なし |
| 無 | ON | exact / strong | 複数 URI / display / other | 補完なし |
| 無 | ON | exact / strong | reading-only / 空 / 未取得 | 補完なし |
| 無 | ON | exact / strong | XML に保存できない文字 | 補完なし、raw 保持 |

matched と個別 confidence の両方を検査する。SeriesComparison を持つ安全な候補が 1 件、
比較 state が MADB_ONLY、classification が 1 resource、effective display が 1 値であることを要求する。
strong は既存の一意な有効 ISBN と discovery / Book completeness による判定だけを使う。
直接 URL 矛盾は unsafe。直接 URL identity と ISBN field conflict の区別は Phase 2B-2 のまま保持する。
explicit comparison が truncated search の direct identity を exact として保持しても補完しない。
ISBN なしは既存 discovery で unmatched。title / creator / publisher fallback や URL 逆検索は追加しない。

## Fail-open と provenance Notes

MADB timeout / network / HTTP / 429 / protocol / schema 失敗では NDL GenericMetadata を返す。
Series relation の失敗・切り詰めも比較の UNAVAILABLE により採用を停止する。
軽量補完は Agent / Holding 自体を取得しない。full API の既存 relation failure semantics は維持する。
constructor / close の MADBError、OSError、SQLite error も optional failure として warning に残す。
既存 logging を使い、NDL の blocking error dialog や `latest-error.txt` に昇格させない。
NDL 本体の失敗は従来のエラー処理を維持する。

採用時だけ次の最小限の Notes を既存本文に追記する。

```text
MADB Series（補完）: 作品名
MADB Book ID: M1
MADB Series ID: C1
MADB 照合: exact (direct_ndl_url, isbn_normalized, isbn_raw)
```

同じ行の追記を防ぎ、繰り返し適用で Notes を増殖させない。非採用時は Notes も変更しない。
Structured FieldEvidence / classification は LinkageResult に保持し、Notes の短い audit text で置き換えない。
永続的な完全 RDF archive と diagnostics UI は追加しない。

## GenericMetadata の変更境界

変更は `series` と出典 `notes` だけ。dataclasses.replace で出力を作り、入力 metadata / record を変更しない。
title、issue、volume、issue_count、volume_count、credits、publisher、imprint、year / month / day、gtin、
description / Summary、tags、genres、language、web_links、format、identifier、data_origin、issue_id、series_id、
その他すべての fields は値を維持する。NDL identity を MADB ID に置き換えない。
ComicInfo.xml はホストの標準 writer に任せ、default OFF の固定 Phase 1 output を維持する。

## 通信・security・cache と既知の制限

既存 MADBSource の公式 HTTPS endpoint、bounded SELECT、許可 URI / ID、literal escaping、
2 MiB / row / relation cap、connect 5 秒 / read 30 秒 timeout、独立した 3 秒 limiter を再利用する。
cache は `jpbooks-madb-v1` の query / resource / relation。新しい cache、limiter、retry は追加しない。
必要時だけ context manager を生成して閉じる。process 間 limiter 共有、snapshot isolation は未対応。
利用条件は [Phase 2A の公式出典](phase2_madb_spec.md) と README のリンクを参照する。

NDL mapper は通常の非空 title を Series にできるため実際の欠損は少ない。
現行 NDL parser と Phase 1 policy を弱めて対象を増やさない。
安全な実データの補完成功例が確認できない場合は synthetic / HTTP mock に留める。
ISBN discovery coverage、候補集合に依存する一意性、異版・媒体の完全一致を保証しない制約は既存どおり。

## Release-blocker 修正の performance boundary

NDLSource.get の `summary_mode` は `none` / `cache` / `fetch`。直接呼び出しの既定値は従来の `fetch`。
候補検索では summary enrichment をしない。`fetch_series()`、`fetch_issues_in_series()`、
`fetch_issues_by_series_issue_num_and_year()` は `cache`、最終 `fetch_comic_data()` は `fetch` を明示する。
必要な SRU 書誌を取得した後、概要キャッシュが空の場合だけ最終取得で最大 1 回追加要求する。
概要 HTTP 429 / 503、timeout、ConnectionError、requests transport error、不正 JSON / envelope / item / ID は
warning と NDL base metadata へ fail-open。内部の AttributeError / TypeError / assertion は隠さない。
SRU 本体の HTTP 429 / timeout / invalid XML は従来どおり fatal。

正常な概要あり・概要なし応答の 7 日キャッシュ、SRU の Refresh 連動は維持する。
失敗は正常キャッシュへ保存しない。即時の手動再取得による重複を防ぐため、同一 source に最大 128 ID の
メモリ上の抑止期限を保持する。通常 30 秒、妥当な Retry-After の秒数 / HTTP-date が長ければそれを尊重する。
これはローカルの重複抑止であり、安全な再試行時刻の保証ではない。期限後も自動再試行はしない。
source 再生成で失敗状態は消える。NDL limiter は 1 request / 2 sec のまま。

MADBSource.get_for_series_linkage は whole Book と関連 Series の direct triples を上限付きで取得する。
Book の ID / type / 全 ISBN / 全 ma:dataUrl / 全 isPartOf、Series の ID / type / schema:name と
language / datatype を既存 parser で評価する。Book に含まれる creator / publisher / provider の raw reference は
残すが、Agent と Holding の詳細 query は実行しない。
MADBRecordBundle.retrieval_scope=`series_linkage` は Agents / Holdings が **NOT REQUESTED** であることを表す。
空 tuple を「存在しない」と解釈しない。completeness は取得 scope に対する状態。
full get と公開 link_ndl_record は full scope の従来動作を維持する。

1 ISBN / 1 Book / 1 Series の cold cache は **3 要求**（ISBN discovery + whole Book + whole Series）。
修正前の relation を持つ fixture は **6 要求**（上記 + Agent 2 + Holding 1）だった。
2 要求に結合しない理由は JOIN による row 増殖と、部分的な列選択で未観測の URL 矛盾や Series relation を
見落とすことを避け、既存の resource row cap / parser / completeness 判定をそのまま使うため。
上限に到達した filtered partial response を完全な Book と扱う経路は追加しない。
複数候補も既存 discovery 上限と Book ごとの relation budget 内で取得・保持し、先頭候補を選ばない。
全取得は直列、MADB limiter は 1 request / 3 sec のまま、automatic retry は追加しない。
完全な warm cache は 0 要求。full API と軽量 API の raw resource cache は共用し、未取得 relation の不在は保存しない。

## テスト例と Phase 2C-2 以降

`tests/test_series_supplement.py` は分類、tag 大小文字、datatype、raw / duplicate、同名別 URI、
設定保存 / 旧 config、通信抑止、exact / strong、拒否条件、全非 Series fields の比較、Notes dedupe、
transport / parser / cache、各取得段階の障害、source close を検証する。
`tests/test_linkage.py` の Phase 1 回帰を維持し、`tests/test_linkage_integration.py` の C334830 を再検証する。
`tests/test_packaging.py` は実 ZIP の beta.9 load、default OFF、mock HTTP による opt-in exact / strong を検証する。
`tests/test_summary_policy.py` は各 host path の cold / SRU cache / summary cache 要求数、報告書誌の 429、
optional failure と SRU fatal の境界、Retry-After と bounded suppression を検証する。
`tests/test_series_retrieval.py` は 3 要求、Agent / Holding 0、scope、cache 共用、full API と共通の照合規則を検証する。
実 ZIP でも候補の概要要求 0、概要 429 fail-open、Agent / Holding reference が存在する軽量補完を確認する。
通常 suite の外部 HTTP は autouse fixture で禁止し、実通信は `JPBOOKS_RUN_NETWORK_TESTS=1` のみ。
最新の件数、format baseline、build / network 結果は [検証記録](validation.md) に記載する。

今回未実装の将来候補は Imprint candidate policy、Credits comparison / supplement、Publisher comparison、
Date comparison、broader provenance-aware merge policy、user-facing diagnostics / source visibility、
根拠が得られた場合だけの weak-linkage research。MangaWork と general automatic metadata merge も未実装。
