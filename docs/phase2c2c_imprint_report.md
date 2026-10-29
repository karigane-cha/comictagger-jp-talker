# Phase 2C-2C-4R1：取得済み evidence の Imprint 診断 report

2026-10-23。R1 は取得済み `LinkedRecordEvidence` を説明する純粋 API。
通常の Talker / Series 補完には接続しない。R2 の通信・コマンド・renderer、R3 の実用性確認、
authority provider、archive 観測・保存は対象外。**Imprint 自動補完全体は NO-GO を維持する。**

## 1. 開始状態と確定 API

開始ブランチは `feat/madb-imprint-integration`、HEAD は
`2a12b22360dc1c129abbd8b6d678f6df725074cb`、作業ツリーは clean。
依頼で報告された基点との差異はなかった。package version は `0.3.0`、
`commit.gpgsign=true` / `gpg.format=ssh` を維持する。

配置は `comictagger_jp_talker/imprint_report.py`。

```python
def describe_imprint_evidence(evidence: LinkedRecordEvidence) -> ImprintDiagnosticReport: ...
def report_to_json_data(report: ImprintDiagnosticReport) -> dict[str, object]: ...
```

実装では既存 module の名前空間を明示して型を参照する。
返却型は frozen / kw-only の `ImprintDiagnosticReport`、Book 単位は同じく frozen の
`ImprintBookDiagnostic`。新規 enum は `BookEvaluationState` のみ。
既存取得状態・identity・evaluator の enum と規則は変更しない。

## 2. Schema と evidence の対応

schema は **`imprint-report-v1`**。identity は `phase2b2-v1`、evaluator は `phase2c2b-v1`。
既存の immutable な型を保持し、そのフィールドを明示した閉じた schema で JSON へ変換する。
既存型のフィールドが増減・並べ替えされた場合も、黙って schema を変えずエラーにする。

| Report の場所 | 内容・出典 |
|---|---|
| `schema_version / plugin_version / identity_algorithm_version / evaluator_version` | Report と処理規則の版 |
| `acquisition.run_id / scope / started_at / finished_at` | 同じ取得 run の台帳 |
| `acquisition.ndl_input` | NDL の ID・URL・タイトル・ISBN 原値・巻・出版社・版・issued・dates・series_titles |
| `acquisition.discovery.planned_isbns` | 取得 core が既存 ISBN 実装で正規化した検索値。原値とは別欄 |
| `acquisition.discovery.attempts` | ISBN ごとの state / reason / page / source outcome / error。正常 0 件と未実行・失敗を区別 |
| `acquisition.books` | 全 Book の取得順・発見 ID / URI・context・bundle・除外理由・error・included_in_linkage |
| `acquisition.traces` | source 呼出順、各 trace 内の event 順をそのまま保持 |
| `acquisition.issues` | run 全体の issues。順序・重複・本文を保持 |
| `linkage` | 既存 LinkageResult 全体。status / matches / candidates / warnings / error / truncated |
| `books[i].book_index` | `acquisition.books` の位置。ID をキーにした辞書へ集約しない |
| `books[i].evaluation` | 採用対象の既存 ImprintEligibility。comparison / classification / extraction まで保持 |
| `books[i].excluded_classification` | 除外 bundle の raw 候補・分類のみ。comparison / eligibility は実行しない |

source outcome の `value`、台帳の `bundle`、evaluator の extraction に同じ snapshot が
重複して現れる場合がある。各位置の責務と既存型の対応を保つ意図的な構造であり、
別々の取得を行ったという意味ではない。R1 では参照 ID による圧縮・出力の切り詰めを導入しない。
正規化 ISBN の原値との対応は、既存 `linkage.matches[].evidence` の raw_value / value / transform にも残る。
欠損した巻・版・日付を report 側で推定しない。

## 3. 全候補・失敗・除外候補

| `BookEvaluationState` | 意味 |
|---|---|
| `evaluated` | included_in_linkage=True の bundle を、その Book の context と linkage 全体で評価 |
| `excluded_from_linkage` | bundle は存在するが照合対象外。raw と分類を残し、採用評価は null |
| `bundle_unavailable` | bundle が存在しない。取得失敗と未取得の違いは元の context / reason / error に保持 |

失敗・未取得に空 bundle を作らない。discovery page、全 Book 台帳、公開 linkage 候補一覧の
それぞれを残す。同じ ID の異なる URI、同じ ID / URI の複数台帳項目も消さない。
一つの評価が安全そうでも、他の候補、discovery の truncated、run issues は隠さない。
意味評価の状態を run 全体の成功・保存可否へ集約するフィールドは設けない。

accepted bundle 一覧と台帳の対応、元 outcome と page / bundle の対応、
Book 個別 context と source context（discovery 集約分を除く）の対応、trace の順序を検証する。
取得失敗は report の内容、内部構造の矛盾は ValueError、未対応型は TypeError として区別する。
警告文字列を解析して取得状態を復元せず、例外を一括して HOLD に変換しない。

## 4. Evaluator と raw provenance

採用対象では既存の `extract_imprint_evidence()` → `classify_imprint_terms()` →
`compare_imprint_candidates()` → `evaluate_imprint_eligibility()` を使用する。
NDL 入力は台帳の `ndl_input.to_record()` で独立コピーを作る。元の mutable な BookRecord は保持しない。
identity は再計算せず、全候補の linkage をそのまま evaluator に渡す。

raw term の kind / value / datatype / language、Book / Series の origin、record ID / URI、
predicate、statements、statement_indices、label_indices、related_to_book を保持する。
role / semantic_kind / reasons、display と比較専用 equality_key、比較結果と blockers も保持する。
raw の trim / NFKC、IRI / bnode の display 化、reading の昇格、先頭 brand への集約は行わない。
parser が除去した重複は復元できない。取得済み snapshot に残る出現だけを報告する。
雑誌名・階層・結合・publisher 同名を文字列だけで意味確認しない。

## 5. Authority 未供給と保存先未評価

evaluator の `authority_evidence=()`、`existing_imprint=None` を固定する。
後者は evaluator の診断入力であり、archive の Imprint が欠損していたという観測ではない。
既存 evaluator が返す HOLD / REJECT / SKIP と全理由を維持する。
authority なしで ELIGIBLE や VERIFIED_LABEL が返れば、判定を丸めず契約違反として停止する。

| 固定フィールド | 値・意味 |
|---|---|
| `operation` | `READ_ONLY` |
| `authority_state` | `not_supplied` |
| `authority_authenticity_assessed` | false。真正性を未検証 |
| `authority_scope_assessed` | false。対象適合を未検証 |
| `authority_validity_assessed` | false。有効期限・失効状態を未検証 |
| `archive_state` | `not_supplied` |
| `target_known / existing_value_assessed` | false。保存先・既存値を未確認 |
| `apply_allowed / writes_performed` | false。書込許可も保存処理もない |

これらは Literal で限定し、JSON 変換時も検証する。report は保存許可 token ではない。

## 6. 完全性・時刻・hash

discovery / Book / Series / relations / resources / agents / holdings / book_series_scope を
元 context のまま保持する。Agent / Holding の NOT_REQUESTED を「存在しない」にしない。
Series relation の NOT_RELATED は取得側が確定した値だけを使う。
trace 不在、partial 0 件、row / byte / relation cap と失敗 event を省略しない。

現在の取得 API は datetime オブジェクトではなく timezone 付き ISO 8601 文字列を保持する。
report も文字列を使用し、offset と表記を保持する。naive / 不正時刻はエラー。
run 開始・終了、event 観測、origin_fetched_at、cache_stored_at を別々に出力し、None は null のまま。
現在時刻を取得して欠損を埋めることはない。

`response_sha256_kind=response_body_bytes` は source が観測した応答本文 bytes の hash。
cache event なら cache に残る本文であり、network event と同じ原取得時刻を保証しない。
event の stage / reason が出典を区別する。HTTP wire bytes や parsed snapshot の digest ではない。
`parsed_snapshot_digest=null`、`run_id_kind=local_correlation_id`、
`snapshot_simultaneity=unknown` とし、複数応答の同時点性を主張しない。

## 7. JSON と純粋性

enum は `.value` の文字列、tuple は array、None は null。
ID / URI / ISBN と raw Unicode は変更しない。日本語、非 BMP、XML 特殊文字、
CR / LF / TAB、C0 / C1、外周空白・全角空白を保持する。renderer は実装しない。
R2 の表示時には制御文字や markup を安全に escape する責務が残る。

明示フィールド表と型注釈を使用し、未知の型・mutable な入力・型違反を拒否する。
float は schema にないため有限値を含め拒否し、NaN / Infinity も出力しない。
repr / default=str / 暗黙の datetime 文字列化を使わない。
返却する dict / list は毎回新規で、変更しても report / evidence は変わらない。

API の実行中は source / session / cache / SQLite / filesystem / clock / logger に触れず、
GenericMetadata / ComicArchive を生成・更新せず、stdout / stderr に出力しない。
通常の Python import が行う module 読み込みとは分けて試験する。
通常 Talker の設定、Notes、description、Series の通信・出力は従来のまま。

## 8. 検証・配布・次工程

専用試験は **208 passed**。既存 fixture の linkage 24 ケース × 2 scope × trace 有無、
実測 RDF 39 件、synthetic 意味評価、純粋性、失敗・cap、JSON、入力契約を含む。
実測 RDF に synthetic な取得完全性を与えた試験を、本番 authority の検証と呼ばない。
500 候補、同一 ID の重複台帳、1,000 件以上の event も省略せず変換する。
JSON は `json.dumps(..., allow_nan=False)` / `json.loads()` と、独立した dataclass 展開との一致で確認する。

全回帰・Ruff・最新 sdist / wheel / ZIP・ComicTagger loader・byte 比較の結果と
権限エラーの経緯は [検証履歴の R1 記録](validation_history.md#phase-2c-2c-4r1純粋-imprint-診断-report2026-10-23) に記録する。
raw evidence の SHA-256 は
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12` を維持する。

R2 は本 schema を使い、NDL ID 一件・明示通信許可・既存取得制限・確実な close・
中断 / 出力失敗・安全な text / JSON 表示・通常経路非接続を受入条件として開始できる。
R1 は診断コマンドや exe 内での起動を提供しない。R3 の実用性確認も未実施。
authority の実供給と host の保存契約は未解決であり、**Imprint 自動補完全体は NO-GO**。
