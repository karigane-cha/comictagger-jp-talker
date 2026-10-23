# Phase 2C-2C-1: MADB Imprint 本番統合の調査・詳細設計

調査日: **2026-10-20 (JST)**。対象: `karigane-cha/comictagger-jp-talker`、`main`、
`cbce602f07a3559b8299a8e55c2dfc9d13d29022`、パッケージ `0.3.0`。
開始時の作業ツリーは clean。本書だけを追加し、production code、既存テスト、設定、書き込み処理は変更しない。
commit / push / merge / tag / Release は行わない。

**取得共有の実装は CONDITIONAL GO、Imprint 自動補完の実装は NO-GO。**
取得共有は既存の公開結果・要求数・Series 出力を維持する内部変更として進められる。
自動補完には、意味確認の信頼済み供給経路、保存先の既存値保護、writer / reader の raw 値保持について阻害条件がある。
本書の API 名・型・設定・Notes は将来の設計であり、利用可能な機能の説明ではない。

## 1. 調査根拠と現在の接続点

判断の優先順位は現在のコード、既存テスト、過去の設計書の順とする。
[Phase 2C-2A](phase2c2a_imprint_research.md)、
[Phase 2C-2B](phase2c2b_imprint_candidates.md)、
[Phase 2C-1](phase2c1_series_supplement.md) を確認した。
外部サイトの新規調査や MADB / NDL の実通信は行っていない。
過去の実測値は保存済み evidence の観測時点の情報として扱う。

| 現在の実装 | 確認した契約・接続点 |
|---|---|
| [talker.py](../comictagger_jp_talker/talker.py) | `fetch_comic_data()` は選択 ID を確定し、`source.get(..., summary_mode="fetch")`、`resolve_record_number()`、要求巻との整合性確認、`to_metadata()`、`supplement_series()` の順。最後の呼び出しが将来の共通補完入口への置換点 |
| [mapping.py](../comictagger_jp_talker/mapping.py) | NDL のタイトルから Series を生成し、`series_titles` は原データの Notes に残す。Imprint を設定しない。mapper は変更しない |
| [series_supplement.py](../comictagger_jp_talker/series_supplement.py) | OFF / 非空 Series で source を生成せず return。ON / 欠損なら context manager 内で軽量照合し、close 後に `apply_series_supplement()` を適用。変更対象は `series` / `notes` だけ |
| [linkage.py](../comictagger_jp_talker/linkage.py) | 公開 `link_ndl_record()` は full、`link_ndl_record_for_series()` は Book / Series の取得関数を `_link_ndl_record()` に渡す。戻り値はいずれも `LinkageResult` |
| 同上の `_link_ndl_record()` | 有効な ISBN を ISBN-13 にまとめてソートし、全 ISBN discovery、発見 ID 順の Book 取得、ID / URI 確認、`compare_candidates()`。ローカルの `bundles` は返却されず失われる |
| 同上の失敗経路 | discovery / Book の `MADBError` でループを中断。取得済み evidence を残した `UNAVAILABLE` を返す。未取得候補の `CandidateSummary.completeness=None` を保持し、Series 比較は実行しない |
| [sources/madb.py](../comictagger_jp_talker/sources/madb.py) | `get_for_series_linkage()` は全直接 triple の Book / Series を取得。full と同じ parser / cache を使う。Agent / Holding 詳細は未要求 |
| 同上の `_get_bundle()` | Series の取得失敗、無効 relation、取得上限は warnings に集約。Series 失敗は Book 失敗と異なり例外を上へ投げず、partial bundle を返す。失敗理由の構造化台帳はない |
| [imprint_candidates.py](../comictagger_jp_talker/imprint_candidates.py) | 抽出 → 分類 → 比較 → eligibility の pure API。`phase2c2b-v1`。取得・設定・metadata 書き込みは行わない |
| [sources/madb_models.py](../comictagger_jp_talker/sources/madb_models.py) / [provenance.py](../comictagger_jp_talker/provenance.py) | MADB snapshot、raw RDFTerm、FieldEvidence、LinkageResult の構成要素は frozen / tuple。`BookRecord` 自体は mutable なので別扱いが必要 |

`fetch_comic_data()` の NDL 取得失敗・巻不一致は補完より先に終了する。
候補一覧の `search_for_series()` / `search_metadata()`、`fetch_series()`、
`fetch_issues_in_series()`、`fetch_issues_by_series_issue_num_and_year()`、Talker の `check_status()` は補完入口を通らない。
候補の書誌取得は `summary_mode="cache"`、最終取得だけ `fetch` という境界も維持する。
`MADBSource.check_status()` は別の source 用 API であり、Talker の接続確認へ組み込まない。

### 1.1 過去の設計書との相違・補足

| 過去の記述・想定 | 現行コードを基準にした扱い |
|---|---|
| 2A は候補評価 API を未実装と記載 | 2B で実装済み。本番接続・意味確認の供給・書き込みは引き続き未実装 |
| 2A の publisher 同名は原則棄却という案 | 2B は `PUBLISHER_EQUAL` の診断と未確認時の保留を分離する。同名だけで非レーベルと断定しない。版表示との同値は `EDITION_EQUAL` / `NONLABEL_VALUE` による拒否 |
| 2C-1 の将来候補に Imprint candidate policy を列挙 | 評価部分は現在存在する。Series の採用規則を Imprint の規則へ置き換えない |
| 2B の `LinkedRecordEvidence(linkage, bundles, acquisition_context)` 案 | 単一 Book 用 `AcquisitionContext` 一つでは複数候補・途中失敗を表せない。本書では共通取得台帳と Book ごとの context に具体化 |
| 2B の `checked_at` / `trusted` | 時刻形式と caller の申告を検証するだけ。現在時刻、期限、失効、署名、実在する検証主体を確認する実装はない |
| 2B の M1032569 の ELIGIBLE | 実測 RDF とテスト用 authority を組み合わせた評価成功。本番供給経路や保存成功の実証ではない |
| 2B の過去の 1,612 passed | 今回の基点には NDL timeout 分離等の後続変更がある。今回の検証結果は §10 に別記 |
| 取得日時・snapshot 一貫性への期待 | 現行 source の戻り値は HTTP 取得日時・cache hit 情報・snapshot token を持たない。単一の取得済みオブジェクト共有は可能だが、サーバー上の同時点性は保証できない |
| 既存値保護・raw 出力の一般的な表現 | Talker に渡された metadata と保存先アーカイブの metadata は別物。ホストの merge と CR / CIX reader の空白処理も §7 の阻害条件になる |

最新変更の NDL timeout は SRU `(5, 60)`、summary `(5, 15)`。
MADB は `(5, 30)` のまま。今回の共有設計はこれらを変更しない。
`8f99fef` の byte-exact evidence 保護と `.gitattributes` の例外も維持する。

## 2. 維持する安全性境界

- 単一 `schema:brand`、Book / Series 一致、NDL `series_titles` 一致は意味確認の代用にしない。
  `UNVERIFIED` は保留。明示的な矛盾が併存すれば現行 evaluator の REJECT を優先し、いずれも採用しない。
- 既存 identity algorithm `phase2b2-v1` を変更しない。直接 NDL URL の EXACT と ISBN conflict が共存する結果も保存する。
  Imprint はその conflict を追加条件で拒否する。Series の過去の挙動へこの拒否を逆流させない。
- Book の単一 raw display と完全な必要取得範囲だけを検討する。Series-only は常に採用対象外。
  複数表示・複数 relation・未知 term の併存を、先頭選択や候補除去で解決しない。
- publisher / edition は現在の厳格な比較を維持する。役割付き出版主体を削ったり、版の欠損を通常版と推定したりしない。
  階層・結合・別表記・移管・同名ブランドを文字列処理や固定辞書で確定しない。
- 比較 key の NFC + 外周空白除去は比較専用。raw 値・言語・datatype・statement・出現位置は保持する。
  XML 不正値を削除・置換して採用可能にしない。raw の重複を parser が既に失った場合も復元したとは主張しない。
- NDL の書誌、identity、Series 比較、既存 provenance は変更しない。汎用 metadata merge に広げない。
  Notes は構造化 evidence の代替ではない。

## 3. 取得共有の内部 API

### 3.1 比較と採用案

| 案 | 評価 |
|---|---|
| `LinkageResult` に bundle を追加する | 公開戻り値の意味・比較・利用側への影響が大きい。採用しない |
| Series の後に Imprint が再取得し、cache に依存する | refresh、失敗、cache 失効で重複する。同一 snapshot の保証もない。採用しない |
| source に `last_bundle` 等の可変状態を置く | 複数候補、例外、再入時に取り違える。採用しない |
| acquire callback で bundle だけ収集する | 小変更だが、discovery の途中失敗や Series の未要求 / 失敗の区別が足りない。完全性の証明としては不採用 |
| frozen な取得結果を返す内部 core と、従来の公開 wrapper | **採用案**。取得ループを一つにし、公開 API は `.linkage` / `.bundle` の projection を返す。状態は取得時に記録する |

将来の型の概略を示す。省略した型も frozen dataclass / tuple とし、可変 dict、source、session、
callback、cache handle、mutable `BookRecord` を成果物へ持ち込まない。

```python
@dataclass(frozen=True)
class BookAcquisitionContext:
    book_id: str
    book_uri: str
    context: AcquisitionContext


@dataclass(frozen=True)
class LinkedAcquisitionContext:
    run_id: str
    ndl_input: NDLInputSnapshot
    discovery: DiscoveryAcquisition
    books: tuple[BookAcquisitionContext, ...]
    events: tuple[AcquisitionEvent, ...]


@dataclass(frozen=True)
class LinkedRecordEvidence:
    linkage: LinkageResult
    bundles: tuple[MADBRecordBundle, ...]
    acquisition_context: LinkedAcquisitionContext
```

`NDLInputSnapshot` は identity / Series / Imprint 評価に使う ID、URL、タイトル、ISBN、巻、
publisher、版、刊行日、叢書名等を raw の tuple に固定する。
同一呼び出しの比較にはこの snapshot から作った private な入力を使い、利用者の `BookRecord` を変更しない。
将来、新たに評価が参照するフィールドを加える場合は snapshot 契約も更新する。

`DiscoveryAcquisition` は予定した正規化 ISBN、ISBN ごとの要求状態、発見された ID / URI、
truncated の有無、構造化 error を保持する。成功して 0 件と検索未実行を区別する。
`AcquisitionEvent` は段階、query key、resource kind / URI、親 URI / predicate、
開始・完了時刻、cache / network の別、状態、error kind / HTTP status / Retry-After、未要求理由を保持する。
無効な relation は URI を捏造せず、元 statement の参照と `invalid_reference` を残す。
上限到達、前段階の失敗、不要な scope を同じ未要求理由にしない。

追加の型を循環 import なしで配置する。推奨は中立の `acquisition.py` に取得状態・台帳を置き、
`linkage.py` が `LinkedRecordEvidence` を定義する構成。
現在 `imprint_candidates.py` は `linkage.py` を import するため、その逆向きの top-level import は追加しない。
`AcquisitionState` / `ResourceAcquisition` / `AcquisitionContext` を中立 module へ移す場合、
従来の `imprint_candidates` import path から同じ型を再公開し、既存 API・既定値・検証規則を維持する。
型移動だけを独立した変更として検証する。

### 3.2 入口と公開互換性

内部入口の仮称を `acquire_linked_record_evidence(record, source, *, refresh=False)` とする。
本番補完用は常に既存の `series_linkage` scope。全直接 triple を取得し、brand だけの SELECT を作らない。
full API も同じ取得 core を使うが、従来どおり Agent / Holding を取得する。

- 公開 `link_ndl_record()` と `link_ndl_record_for_series()` は引数・既定値・戻り値 `LinkageResult` を維持。
  `compare_candidates()` / `_evaluate()` / `compare_series()` の identity と判定順は維持する。
- source に内部の bundle + trace 返却経路を作り、`get()` / `get_for_series_linkage()` は従来の bundle だけを返す。
  `_get_bundle()` の取得順、上限、warning の内容・順序・重複除去、例外の境界を変えない。
- 成功した bundle は Book ID 順で一度だけ保持。`CandidateSummary` と ID / URI / completeness が一致することを検証する。
  同一 ID の矛盾した snapshot を選別して救済しない。
- discovery / Book 失敗時も、それまでの bundle と台帳を返す。失敗した resource に偽の空 bundle を作らない。
  未取得の発見候補にも context を設け、後続中断は `NOT_REQUESTED` と記録する。
- `linkage` は従来の失敗経路と同じ `UNAVAILABLE`、matches、warnings、error、truncated を返す。
  trace の追加情報を公開 identity の再判定に使わない。Series 失敗は従来の partial bundle / Series 比較に任せる。

一つの `AcquisitionContext.book` を全候補の状態へ使わない。
Imprint 評価時には対象 Book の context を取り出すが、discovery は実行全体の状態を引き継ぎ、
`LinkageResult.candidates` に他候補の不完全性も残す。対象だけ完全なら採用してよいという短絡はしない。

### 3.3 完全性の意味

| 観測 | 台帳と evaluator 用 context |
|---|---|
| 有効 ISBN なし | discovery は `NOT_REQUESTED`、理由 `no_valid_isbn`。従来の公開結果は UNMATCHED。タイトル検索や URL 逆引きを追加しない |
| 全予定 ISBN の検索成功、非 truncated、0 件 | discovery は `COMPLETE`。Book context は空。候補なしの正常な結果 |
| 一つでも検索が truncated | discovery は `TRUNCATED`。ほかに失敗があれば各状態・truncated フラグも保持 |
| 最初の検索失敗 / 途中失敗 | 集約は観測なしなら `UNAVAILABLE`、一部成功なら `PARTIAL`。残る ISBN は `NOT_REQUESTED`。`truncated=False` でも COMPLETE とはしない |
| Book 全直接 triple の完全取得 | 対象 `book=COMPLETE`。row cap は `TRUNCATED`、失敗は `UNAVAILABLE`。Book 不完全時は relation の不存在を認定しない |
| 完全な Book に raw `isPartOf` がない | 対象 `series=NOT_RELATED` / `relations=NOT_RELATED`。取得していないから空なのではなく、関係の不存在を観測 |
| 有効な全 relation と全必要 Series が完全 | 対象 `series=COMPLETE` / `relations=COMPLETE`。各 resource も COMPLETE |
| relation はあるが Series が失敗 | resource は `UNAVAILABLE`、集約 series / relations は `PARTIAL` または `UNAVAILABLE`。空 tuple を NOT_RELATED にしない |
| relation cap、無効 URI、literal / bnode relation | 未要求理由と raw を保持し、relations は `PARTIAL`。未試行 resource は `NOT_REQUESTED`、Series row cap は resource `TRUNCATED` |
| 軽量 scope の Agent / Holding | 常に `NOT_REQUESTED`。raw 参照があっても、空 tuple を不存在とはしない |

集約 series は、全成功なら COMPLETE、一部の必要取得や関係解決が不足なら PARTIAL、
要求した取得がすべて失敗なら UNAVAILABLE、要求可能な取得を一つも試していなければ NOT_REQUESTED とする。
TRUNCATED は個々の resource と、切り詰め以外の欠損がない集約で明示する。
複数の状態が混在しても event ごとの情報を落とさず、集約 enum 一つで理由を表し切ろうとしない。
`relations=COMPLETE` は有効 URI の列挙だけでなく全必要 snapshot の解決完了を意味する。
Book が不完全なら、見えた Series が全部取得できても relation 全体は COMPLETE にしない。

warnings の文字列解析で状態を復元しない。source 内の分岐で直接台帳を作る。
evaluator の `_availability()` は context と raw bundle の双方を確認するため、
COMPLETE の宣言だけで partial / truncated を上書きできない。
full scope の Agent / Holding だけが不完全な場合の `book_series_scope=COMPLETE` 例外は、
台帳で Book / Series / relation の完全性を証明できる場合に限る。本番共有で full scope を選ぶ理由はない。

### 3.4 snapshot、cache、取得上限

共有単位は **一回の最終取得内のローカル snapshot**。
Series と Imprint は同じ `LinkedRecordEvidence.bundles` のオブジェクトを参照し、評価中に再取得しない。
識別子は run ID、query key、Book / Series の raw snapshot digest の組で監査する。
digest は qualifier・順序・重複も保存する版管理済み直列化に対して計算し、比較用正規化を施さない。
HTTP 原応答の hash と parsed snapshot の hash は別項目にする。
同じ ID の別時点データが内容一致なら digest は同じになり得る。暗号学的な取得時点証明ではない。

cache hit は再解析した結果が完全な場合に既存と同じく利用できる。
run の開始時刻、cache から読んだ時刻、原応答の取得時刻を区別する。
旧 cache は原取得日時を公開しないため `origin_fetched_at=None` とし、現在時刻を補わない。
既存 `AcquisitionContext.acquired_at` も、実際の取得時刻を裏付けられない場合は None。
`request_id` を MADB サーバー発行 ID と偽らず、ローカル識別子の由来を台帳に記載する。
異なる時点の cache / network の組合せや request 間の snapshot isolation は保証できない。
未知の freshness を authority の現在有効性と同一視しない。

以下は変更しない。

- 公式 endpoint、許可 ID / URI、literal escaping、redirect 無効、逐次処理、自動 retry なし。
- MADB の connect 5 秒 / read 30 秒、2 MiB、候補既定 20 / 最大 100、直接 triple 既定 300 / 最大 1,000、
  Book ごとの関連 resource 要求上限 12、process 内の 1 request / 3 秒 limiter と lock。
- `jpbooks-madb-v1`、query / resource / relation の cache namespace、endpoint / query / scope を含む key。
  完全な成功だけを保存し、0 件成功は保存、不完全結果・失敗は正常結果として保存しない。
- 導入済み ComicCacher の検索 cache 期限 7 日。期限処理を延長せず、失効後は従来どおり再取得する。
  freshness 情報を足すためだけに旧 cache を強制更新しない。

`refresh=True` は共有呼び出し全体で一度伝播し、discovery / Book / Series へ従来どおり渡す。
現在の `fetch_comic_data()` に refresh 引数はない。検索の `refresh_cache` から最終取得へ暗黙に伝搬させず、
共有 API の refresh と host 操作を区別する。
ISBN が複数ある場合の union、候補ごとの 12 relation 上限も維持し、新たな全体上限を勝手に導入しない。

## 4. 本番経路への将来の接続

補完要否は `to_metadata()` の直後、同じ元 metadata に対して独立に判定する。

```python
need_series = series_enabled and not (metadata.series or "").strip()
need_imprint = imprint_enabled and (metadata.imprint is None or metadata.imprint == "")
```

Series の空白判定を Imprint へ流用しない。Imprint の `" "`、改行、全角空白は既存値であり保護する。
apply 時にも既存値を再確認し、判断と書き込みの間に値が設定されていれば上書きしない。

```text
選択 NDL ID
  → NDL get(summary_mode="fetch")
  → 書誌の巻整合性確認
  → to_metadata() = baseline
  → Series / Imprint の need を独立計算
  → 両方不要なら baseline を返す
  → 一つの MADBSource / 一回の共有取得 / close
  → Series が必要なら既存 apply_series_supplement(baseline, evidence.linkage)
  → Imprint が必要なら同じ bundle + 対象 context + 同じ NDL snapshot を評価
  → 有効な authority と ELIGIBLE を確認したときだけ Imprint / Notes を適用
  → 出力を返す
```

将来の共通入口は `metadata_supplement.py` の `supplement_metadata()` を候補とする。
`apply_series_supplement()` の採用条件は保持し、既存 `supplement_series()` も互換 wrapper として残す。
共通入口から `supplement_series()` を呼んで取得させた後、Imprint を別取得する構成は禁止する。
取得共有だけの工程では Imprint の設定・provider・書き込みへ接続しない。

authority が利用不能と事前に分かる場合、Imprint のためだけの MADB 通信は不要。
Series が必要ならその取得は通常どおり行う。この事前条件を満たす本番 provider がない現時点では、
Imprint の設定自体を公開しない。

| Series 設定 | Imprint 設定 | 必要フィールド | 共有取得 |
|---|---|---|---|
| OFF | OFF | 任意 | 0 回。source / cache / authority provider を生成しない |
| ON | OFF | Series 欠損 | 1 回。現行結果と等価 |
| OFF | ON | Imprint が None / 空文字列 | provider が運用可能な将来に 1 回。Series の有無は起動条件にしない |
| ON | ON | 両方欠損 | 1 回。同一 snapshot で独立評価 |
| ON | ON | 片方だけ欠損 | 1 回。既存側を変更しない |
| ON | ON | 両方既存 | 0 回。空白だけの Imprint も既存扱い |

### 4.1 request 数の受入基準

下表は synthetic な「有効 ISBN 1、Book 1、関連 Series 1」、成功、完全な source cache を前提とする。
authority はローカル検証済み供給を仮定し、追加 HTTP は 0。NDL の SRU / summary は別に計数する。

| 状態 | Series のみ必要 | Imprint のみ必要 | 両方必要・共有 | 二重取得した場合の比較値 |
|---|---:|---:|---:|---|
| cold | 3 | 3 | 3 | 独立 cold cache なら 6。同じ cache の逐次取得なら 3 でも、取得ループは 2 回 |
| warm | 0 | 0 | 0 | HTTP 0 でも別の snapshot 読込を 2 回行う |
| `refresh=True` | 3 | 3 | 3 | 6 |
| 必要な cache がすべて失効 | 3 | 3 | 3 | 後段が再生成された cache を使えるかに依存 |
| Book に Series 関係なし、cold | 2 | 2 | 2 | 同一 cache なら後段は 0、refresh なら合計 4 |

複数 ISBN / Book / Series は実際の既存 query key と cache 状態で数える。
同じ Series URI でも parent を含む relation cache key が違えば別要求となり得る。
本工程は既存 source 内の resource 要求をさらに統合する最適化を含まない。
HTTP 数に加え、共有入口 1 回、各 consumer が同じ snapshot を参照すること、
Agent / Holding 0、authority URL への要求 0 を計測する。

## 5. 意味確認データの供給契約

### 5.1 現在の不足と供給方式

`LabelAuthorityEvidence` は外部検証を済ませた情報の受け皿であり、trust の生成器ではない。
`trusted=True`、HTTPS URL、公式らしい host 名、`AuthorityState.VERIFIED` の設定だけでは採用しない。
テスト helper `authority()`、`acquired()`、`imprint_measured.json` の authority envelope は本番へ import しない。

本番候補は、出版社・レーベル管理主体の正式な書誌提供物、または根拠資料を検証した管理者による
**版管理・署名付きのローカル evidence package**。ネットワーク外で取得・審査・配布し、Talker は読み取り専用で検証する。
これは実在する供給元が確保できたという結論ではない。現時点ではどちらの運用も構築されていない。
固定の名称辞書、任意 URL 取得、新規の公式サイト用 scraping、MADB / NDL 一致からの trust 生成は採用しない。

署名は供給物の改変検知と発行者確認であり、内容の正しさを証明するものではない。
信頼の起点となる発行者鍵・管理主体・審査手順・根拠資料へのアクセス権・利用条件を先に確定する。
根拠資料の原本 / hash / 抜粋位置と reviewer の判断を結び付ける。検索索引本文だけを直接公式本文確認へ格上げしない。

### 5.2 provider の戻り値と判定責任

仮称 `AuthorityProvider.assess(target, *, evaluation_time)` は frozen な `AuthoritySupply` を返す。
最低限、状態（ready / missing / expired / revoked / unavailable / conflicted）、適用対象、
全 assertion、拒否した assertion と理由、供給版、schema 版、発行者、署名検証結果、原資料 hash、
検証者、確認時刻、有効期間、失効台帳版、検証 policy 版を持つ。
外部データはまず未信頼の DTO として読み、検証を通過した adapter だけが `LabelAuthorityEvidence` を作る。

| 検証対象 | 必須の確認 |
|---|---|
| 真正性 | 承認された発行者と署名、package / 根拠資料の hash、schema、改変・古い版への巻き戻し検知。URL は locator として記録するだけ |
| 出典独立性 | 原資料の提供主体・転載経路を確認し `origin_group` を割り当てる。NDL / MADB、同じデータの再配布や複数 URL を独立した裏付けと数えない。不明なら保留 |
| 書誌 ID / ISBN | 対象 NDL ID / URI、MADB Book ID / URI、両者の ISBN と authority の ISBN を照合。ISBN-10 / 13 は既存の正規化のみ。Series ID や作品名だけで適用しない |
| 巻 | 同巻の公式書誌であることを raw 巻と根拠位置で確認。`LabelAuthorityEvidence.volume` は現在 optional で MADB 巻との比較に限られるため、provider は NDL 側の巻・版との対応も確認する。巻なしは確認済みの不存在と未知を分ける |
| publisher | 発行 / 発売 / 頒布を含む主体と刊行時点を確認。現在の厳格な集合比較を回避するための名称削除はしない |
| edition | `None` は未知、`()` は該当書誌で版表示の不存在を確認した場合だけ。片側欠損、特装版、復刻、移管を同版と推定しない |
| medium | 同 ISBN・同巻の紙 / 電子等の適用根拠。`mediatype="books"`、タイトル、書誌型から紙と推定しない。MADB に値がなければその欠損を記録したうえで対象を外部確認する |
| publication time | 書誌の刊行日と authority の適用期間・当時の所属を確認。現在の所属だけでは足りない。日付の粒度は現行 evaluator の互換性判定に従う |
| label structure | 単一レーベルとしての意味、階層・別名・結合・雑誌・叢書・出版社との役割を確認。relation が未解決なら保留。`relation=None` を未調査の省略に使わない |
| raw 対応 | 原則 Book の raw display と完全一致。確認済み `raw_label_values` の対応だけ許し、NFKC・略称・読みで補わない。明示的な階層 / 別表記 relation を現行 evaluator で解除しない |

対象抽出は版管理済みの完全な index に基づく。同じ対象に関する不利な証拠・失効・矛盾も返す。
無関係と証明できる別書誌だけは適用外として監査記録を残す。対象の対応が曖昧な証拠を黙って捨てない。
有効な assertion と失効・不適用な assertion が混在するとき、好都合な一件だけを evaluator へ渡さない。
供給集合の完全性を主張できなければ supply を ready にしない。

現行 evaluator は期限を判定しないため、provider の lifecycle gate が不成立なら書き込みを禁止する。
失効データを黙って削って空 tuple に置き換えるだけでは監査が失われる。
`AuthoritySupply` に全履歴・理由を保持し、Imprint の結果は保留または拒否として残す。
純粋 evaluator の enum や意味判断を変更せず、供給段階の拒否理由は外側の結果に保持する。
`ELIGIBLE` と supply ready の両方が成立して初めて apply へ進める。

### 5.3 更新・失効・再評価・監査

- immutable な package ID / version / digest と assertion ID を付け、更新は検証済み版への原子的な差し替えとする。
  更新失敗時に未検証の新版を使わず、旧版も期限・失効確認を満たす間だけ使用可能とする。
- `valid_from` / `expires_at` / `revoked_at`、置換先、失効理由、署名鍵失効を管理する。
  `checked_at` が古くても自動更新しない。未来時刻、期限境界、時計不明、失効一覧が古い場合は保留。
- 固定日数を根拠なく決めない。資料更新頻度と管理主体の運用に基づく期限・失効情報の最大許容経過時間が未確定なら NO-GO。
  オフライン配布では最新失効の即時検知を保証できず、その許容条件も運用契約が必要。
- 各評価で供給版・有効性を再確認する。MADB の warm cache でも期限切れ authority を再利用しない。
  結果を cache する将来拡張では NDL / MADB digest、供給版、失効版、policy / evaluator 版を key に含める。本工程では結果 cache を作らない。
- 監査記録には使用 / 不使用の全 assertion、構造化判定理由、snapshot digest、評価時刻を保存する設計とする。
  Notes には最小限の ID のみを置く。監査資料の保管先、保存期間、配布権限、記録失敗時の扱いを決めるまで本番化しない。
- 後日の失効は次回の採用を停止する。既に保存された Imprint を自動削除・上書きする処理は作らない。
  影響した評価 ID を追跡可能にし、訂正は別の明示的な運用へ渡す。

現時点の判定は **供給方式未確立のため NO-GO**。
研究用の人手注記を、そのまま継続運用できる信頼済み package と扱わない。

## 6. 設定、出力、Notes の将来方針

設定キー候補は `jpbooks_madb_imprint_supplement`、CLI は `--jpbooks-madb-imprint-supplement`。
既定 False、旧 config の未設定も False、明示的な boolean opt-in とする。
Series 設定から継承せず、`"true"` / `1` / None 等の誤った型を受理しない。
将来は現行 Series と同じ `BooleanOptionalAction`、保存・再読込・無効化の契約を使う。
provider 不備を opt-in で上書きできない。今回この設定を登録・保存するコードは追加しない。

将来の `apply_imprint_supplement()` は pure transformation。
必要な再検査後、`dataclasses.replace(metadata, imprint=raw_display, notes=...)` で新しい値を返す。
title、publisher、issue / volume、各 count、credits、日付、gtin、description、tags、genres、
format、language、web_links、identifier、NDL data_origin / issue_id / series_id 等はすべて維持する。
Series が別途採用された場合にのみ全体の変更集合は `series` / `imprint` / `notes` となる。
非採用時には Notes も変えない。

Notes 案は次の程度に絞る。値は例示であり、本番の証拠ではない。

```text
MADB Imprint（補完）: レーベルの原表示
MADB Book ID: M123
MADB Imprint 根拠: authority-package-v1/assertion-123
MADB Imprint 評価: phase2c2b-v1
```

Series の既存 Notes 生成を変更せず、Series → Imprint の順で追記する。
既存本文・改行を再整形せず、`splitlines()` による既存行集合に存在する行は追加しない。
両者に共通する `MADB Book ID` は一度だけとなり、Series ID / 照合行はそのまま残す。
Imprint の行は専用の接頭辞で識別し、Series の根拠と混同しない。
raw display が改行を含む場合、Notes の一行表示に限って `\n` / `\r` / `\t` 等を可逆 escape する。
metadata の Imprint と raw evidence 自体は変更しない。監査 ID も制御文字を含まない契約にする。
通常の適用を繰り返すと既存 Imprint の gate で停止し、同じ行も増殖しない。
手動で Imprint だけを消して再評価した場合の過去 Notes は監査履歴として残し、古い根拠を削除しない。

## 7. ホストの既存値保護と CR / CIX の阻害条件

導入済み ComicTagger `1.6.0b9` / `comicinfoxml 0.5.1` のローカルコードも確認した。
Talker の `fetch_comic_data()` は ID と巻を受け取り、保存先の `GenericMetadata` を受け取らない。
`search_metadata()` は host の metadata-aware callback ではなく、最終保存先の状態を引き継ぐ用途には使えない。
従って §4 の gate が直接保証するのは **補完関数へ渡された metadata の保護**である。
既存アーカイブの Imprint を読み取った、または保護したという意味ではない。

ホストの `comictaggerlib/md.py:prepare_metadata()` は既存 metadata に取得結果を overlay し、
設定により import transform、clear tags、`auto_imprint` の `fix_publisher()` も実行する。
Talker から任意の host 設定下の最終保存値を保証する手段は確認できない。
安全な保存先既存値の受渡し / 適用境界、または保証可能な host の統合契約が必要。
単に「利用者が merge 設定を選ぶ」という注意書きだけで既存値保護済みとはしない。
ホストの汎用 merge を改造することや plugin 独自のアーカイブ書き込みは、本設計の解決策に含めない。
この境界を解消できなければ、本番の自動補完は NO-GO のままにする。

CR の `comicapi/tags/comicrack.py` と CIX の `comicinfoxml.py` は双方 `<Imprint>` を書き、
読込時に `utils.xlate()` を呼ぶ。同関数は外周空白を除去し、空白だけなら None を返す。
そのため `" Label "` の metadata / XML / 再読込 metadata が完全一致するとは限らず、
保存済み空白だけの既存値も通常 reader を経由すると欠損に見える。
CR を含む改行の XML 正規化も確認対象となる。

将来の保存試験では三層を分ける。

1. evaluator / apply が Book の raw display を変更しないこと。
2. 実 writer の `ComicInfo.xml` が期待する `<Imprint>` / Notes を保存すること。
3. 同じ tag および CR / CIX 相互読込、通常の host merge / 保存経路で何が保持・変更されるか。

ホストの正規化を plugin の出力修正で隠さない。差分を正確に記録し、厳密な保存・再読込保証が必要な値は
本番出力を保留する追加 gate、または互換性が確認された host の契約が必要。
この gate は候補評価自体を VERIFIED に変更せず、raw を削除・置換して通すこともしない。
保証対象の確定と実測試験が未完了のため、Imprint writer 統合の受入は未達である。

## 8. fail-open とエラー境界

| 障害の位置 | 将来の動作 |
|---|---|
| NDL SRU / 書誌整合性 | 従来のエラーを維持。MADB を呼ばない |
| NDL optional summary | 既存の warning / base metadata 維持・抑止期限を変更しない |
| MADB source 生成・取得・close | `MADBError` / `OSError` / `sqlite3.Error` を補完境界で処理。NDL baseline を返す。source の close は保証する |
| discovery / Book 429 / 503 / timeout 等 | 従来の UNAVAILABLE を保ち、取得済み証拠と error を台帳へ残す。再試行・別 URL への fallback はしない |
| Series の取得失敗 | 部分 bundle と context を保持。現行 Series 比較で不採用、Imprint も必要範囲不足として保留 |
| authority 不足・期限切れ・失効・矛盾 | Imprint のみ停止。既に正当に補完された Series と Notes は維持 |
| authority 供給物の破損 / 読込失敗 | provider 専用の検証・I/O error に分類し、Imprint のみ停止。信頼フラグを立てない |
| XML 不正値・候補拒否 | 原値と理由を evidence に残し、該当フィールドと Notes を変更しない |

MADB / provider の予期される障害を `@copyable_errors` まで漏らさない。
`MADBError` は `TalkerError` を継承するため、漏らすと `report_error()` により NDL の
`latest-error.txt` を更新してしまう。既存の NDL エラー履歴を byte 単位で維持することを試験する。
warning は optional MADB / authority の段階と run ID を識別できる内容にし、任意の原本文を大量に出さない。

現行と同様、取得・close が完了してから metadata を適用する。
共通取得に失敗した場合の Series 挙動を変えず、取得成功後の authority 障害だけを Imprint に隔離する。
`except Exception` でプログラム不具合や assertion を一括で隠さない。
evaluator の `ValueError` は入力契約違反である。外部供給の形式不正は provider adapter で専用 error に変換し、
内部の誤った型生成まで通常の取得障害として扱わない。

## 9. テスト設計と fixture の区別

### 9.1 現在の根拠

- [test_imprint_candidates.py](../tests/test_imprint_candidates.py): raw / qualifier / 出現、比較・意味確認・既存値・XML、
  snapshot 対応、pure API、既存 Series 不変。現行の期限失効や本番 provider の試験ではない。
- [test_series_supplement.py](../tests/test_series_supplement.py) /
  [test_series_retrieval.py](../tests/test_series_retrieval.py): 設定、経路制限、軽量 3 要求、warm cache、
  full 互換、raw 参照、constructor / close、fail-open。
- [test_linkage.py](../tests/test_linkage.py)、[test_madb.py](../tests/test_madb.py)、
  [test_madb_boundary.py](../tests/test_madb_boundary.py): identity、上限、失敗、cache、raw の基盤。
- [test_summary_policy.py](../tests/test_summary_policy.py)、[test_talker.py](../tests/test_talker.py)、
  [test_comicinfo.py](../tests/test_comicinfo.py)、[test_packaging.py](../tests/test_packaging.py):
  NDL 回帰、writer / reader、実 ZIP loader。現行の Imprint 補完後の保存試験はない。

実測 fixture は [imprint_measured.json](../tests/fixtures/madb/imprint_measured.json)。
2026-10-08 の 39 Book / 27 Series、NDL 11 書誌の選択項目、M1032568 / M1032569 の discovery を含む。
元の [imprint_evidence.json](research/madb/imprint_evidence.json) の SHA-256 は
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`。
縮約された predicate の raw 一致を検証する資料であり、本番の全直接 triple 取得の代替ではない。
他資料の完全な discovery / context とすべての authority trust / scope envelope は synthetic。
M1032569 の出版社の注記も、テストで補った trust / scope の全項目を実測したことにはならない。

`single.json` / `book.json` / `series.json` 等と HTTP mock は synthetic。
429 / 503 / timeout、失効、未観測の datatype、XML 不正値、複数候補は synthetic と明示する。
新たな本番 authority の正例には承認された実供給物が必要であり、synthetic 合格で代替しない。

### 9.2 追加する将来の受入試験

| 分類 | ケースと確認内容 |
|---|---|
| 設定 × 既存値 | OFF/OFF、ON/OFF、OFF/ON、ON/ON と Series / Imprint の None、空文字列、通常値、ASCII 空白、改行、全角空白を組合せる。Series と Imprint の欠損判定差、source / provider 未生成、変更フィールド集合を確認 |
| 公開互換 | full / 軽量の各公開 API と内部結果 `.linkage` を比較。status、matches、confidence、reasons、conflicts、warnings、error、候補順、truncated、`series` の値と旧試験結果を維持 |
| 取得共有 | §4.1 の cold / warm / refresh / 全失効 / 一部失効。HTTP mock の request 数と query scope、取得 core 1 回、snapshot の同一性、session / cache close を確認 |
| discovery | 0 件、有効 ISBN なし、10/13 等価、複数 ISBN の union、truncated、途中失敗、発見後未取得、同一 NDL URL を主張する複数 Book、複数の安全候補。先頭選択しない |
| resource / relations | Book / Series の row / byte cap、partial、Book 成功後の Series 失敗、12 relation 到達、無効 URI / literal / bnode、重複 relation、関係なしと未要求。Agent / Holding 未要求を保持 |
| cache | 有効な 0 件 cache、壊れた cache の再取得、不完全結果非保存、失効境界、旧 cache の取得日時不明。refresh 後の別 snapshot を同じ評価へ混ぜない |
| identity / context | direct EXACT + ISBN conflict、別 NDL URL、対象 ID / URI / raw evidence 不一致、非採用候補の独立 conflict、publisher 欠損・複数主体・役割差、版 conflict / 片側欠損。Series の従来結果も並行確認 |
| authority 不足 | 未供給、UNVERIFIED、trusted=False、未確認の独立性、NDL / MADB 由来、欠けた媒体・版・刊行時期・構造。すべて不採用 |
| authority lifecycle | expires_at 直前 / 同時 / 直後、未来 checked_at、失効、古い失効一覧、署名不正、鍵失効、package 改変・巻き戻し、更新中断。warm MADB cache でも再評価 |
| authority 対象 | Book / NDL ID、ISBN、巻、publisher、版、媒体、刊行時期、raw label の不一致と複数根拠の相互矛盾。好都合な証拠だけを選別しない |
| 意味・構造 | 単一 brand、一致した Book / Series、NDL 叢書一致だけでは HOLD。階層・別表記・結合・出版社同名・版同名・番号・雑誌・Series-only の現行判断を維持 |
| raw / XML | 制御文字、surrogate、FFFE / FFFF、qualifier 不正、未知 term 併存、NFC 差、外周 / 内部空白、CR / LF / TAB、非 BMP、literal の escape 文字。raw hash と出現位置を保持し、sanitize しない |
| fail-open | discovery / Book / Series の各段階で 429 / 503 / timeout / network / protocol / schema / not_found、OSError / SQLite、constructor / close、provider 失敗。NDL 結果とエラー履歴、適用済み Series を維持 |
| 通信禁止経路 | 全設定組合せで候補検索、`fetch_series()`、両 issue 候補 API、`check_status()` に MADB / authority 通信がない。import 時通信も禁止 |
| Notes | 両補完同時、繰返し適用、既存同一行、末尾改行の有無、複数行 raw 表示、手動変更後の再評価。Series Notes と既存本文を保持し同一行を増殖させない |
| host / XML | 実 `ComicArchive` と CR / CIX で CBZ 保存、XML 確認、同一 / 相互 reader、既存通常値 / 空白値、host overlay / transform / auto_imprint / clear_tags の影響。§7 の保証不能を合格扱いにしない |
| 配布物 | 最新 source から sdist → wheel → plugin ZIP、収録内容照合、`python -I` の beta9 `find_plugins()` / `get_talkers()`、loader の path cleanup 後の遅延 import。既定 OFF、同時 ON、失敗、request 数、authority asset・失効情報の検証 |
| 全回帰 | NDL mapping、summary、日付、巻、Series、既存 API、Ruff / format、`git diff --check`。Imprint 未採用でも旧 Series の期待値は変えない |

通常テストの外部 HTTP 禁止 fixture を維持し、時間・cache 期限は制御可能な時計と保存状態で検証する。
実通信は別の opt-in 調査とし、実測結果と synthetic 結果を同じ成功件数の説明で混同しない。

## 10. 今回の検証結果

既存 `.venv` を使用。Python `3.12.14`、ComicTagger `1.6.0b9`、comicinfoxml `0.5.1`、
pytest `9.1.1`、Ruff `0.16.8`、build `1.6.1`、setuptools `84.0.0`。
環境の pip module は未導入だったため、版の取得には `importlib.metadata.version()` を使用した。
依存追加・更新は行っていない。

| 実行 | 結果 |
|---|---|
| 既存全体 suite（文書追加前） | **1 failed / 1,631 passed / 13 skipped / 1 xfailed**、24.37 秒。失敗は既存 sdist を開く際の `PermissionError` |
| 同じ配布物の packaging 再実行（許可された sandbox 外） | **3 passed**、13.60 秒。sdist の source / fixture byte 一致、entry point、実 ZIP の beta9 loader と既存 Series / summary 動作を確認 |
| ZIP と作業ツリーの production Python 比較 | **18 ファイルすべて byte 一致**。古い ZIP の成功を現行実装の検証に取り違えていない |
| `ruff check .` | **All checks passed** |
| `ruff format --check .` | **59 files already formatted** |
| 文書追加後の `tests/test_wording.py` | **2 passed**、0.13 秒。既存文書と新規文書を含む表記規則を確認 |
| 差分・文書形式 | `git diff --check` および新規未追跡ファイルの `git diff --no-index --check` を確認。UTF-8 / BOM なし / LF、文書内のローカルリンクはすべて存在 |
| raw evidence | 上記 SHA-256 と一致。`.gitattributes` の `-text -eol` を確認。既存の追跡ファイルに変更なし |

全体 suite の 13 skipped は明示的 opt-in の network 試験。
1 xfailed は既知の CIX の整数 Volume 0 出力制約であり、Imprint の検証結果ではない。
全体 suite が一度で全成功したとは記録しない。失敗した packaging は再実行で全件成功した。
今回 ZIP / sdist を再ビルドしておらず、既存配布物を検証した。
新しい Imprint 設定・本番供給・書き込み・共有 API は未実装なので、それらの統合試験を合格済みとはしない。
現行 CR / CIX の既存 roundtrip 試験は全体 suite で実行済み。Imprint 専用の §9 の試験は今後の計画である。

再現コマンド:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c1-pytest-20261020
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c1-packaging-20261020 tests/test_packaging.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c1-wording-20261020 tests/test_wording.py
git diff --check
git diff --no-index --check -- /dev/null docs/phase2c2c_integration_design.md
git status --short
```

テストの作業出力は既存の ignore 対象 `.research` 等に限定する。
新しい Markdown は UTF-8 / LF、既存ファイルの改行・整形には触れない。
研究 evidence の `-text -eol` 例外とその hash を維持する。

## 11. 実装工程、依存関係、受入条件

本書作成後の別工程として、次の順に分割する。

| 工程 | 依存 | 将来の主な変更対象 | 受入条件 |
|---|---|---|---|
| A. 取得状態の中立モデルと source 台帳 | 本設計 | 新規 `acquisition.py`、`sources/madb.py`、必要に応じ `sources/madb_models.py`、`imprint_candidates.py` の互換 import | frozen / tuple、全状態の根拠、warning 解析不要、未要求 / 不存在分離。公開 source の bundle、例外、要求数・cache・上限が等価 |
| B. 同じ snapshot を返す内部 linkage core | A | `linkage.py`、linkage / retrieval テスト | 公開 `LinkageResult` 完全互換。成功・途中失敗・複数候補を保持。単一取得ループで raw / NDL 入力が対応し、循環 import なし |
| C. Series だけで共有入口へ移行 | B | 新規 `metadata_supplement.py`、`series_supplement.py`、`talker.py`、Series / packaging テスト | Imprint 設定なし。既存 Series の全出力、通信抑止、3 / 0 要求、失敗時 NDL 維持、エラー履歴、ZIP loader が等価 |
| D. authority 供給の実証と運用契約 | A と独立に調査可能 | 将来の `label_authority.py`、供給 schema / policy / 監査資料、専用 fixture | 実在する供給元・真正性・独立性・対象適用・期限・失効・監査を説明し、実供給物で検証。synthetic だけの正例では未達 |
| E. host 保存境界の実証 | B と並行に調査可能 | host 統合 / CR・CIX 検証用テスト、設計文書 | 保存先の既存 Imprint と空白値を保護できる契約を確認。raw の XML / reader 差を測定し、保証できない値の停止方針を確定 |
| F. pure Imprint 出力と二設定の統合 | C + D + E、NO-GO 解除のレビュー | 新規 `imprint_supplement.py`、共通入口、`talker.py`、設定 / Notes / fail-open テスト | 明示 opt-in・False 既定、provider ready + ELIGIBLE だけ採用、既存値保護、変更フィールド限定、同時 ON の取得 1 回、Series 回帰なし |
| G. 配布物・最終保存の受入 | F | packaging / ComicInfo テスト、検証記録 | 新規 build の ZIP、beta9 loader、CR / CIX の保存・再読込、authority の期限・失効、全体 suite / Ruff / format / diff check が成立 |

ファイルの仮称は責務を示す。既存 `mapping.py`、NDL source、identity 規則、query template を
補完率向上のために変更する工程は含まない。A～C だけで区切ってレビューできる構成にする。

## 12. 最終判定と阻害条件

| 対象 | 判定 | 条件・理由 |
|---|---|---|
| 取得共有の実装 | **CONDITIONAL GO** | A～C の範囲。公開戻り値・identity・Series 出力・失敗経路・request 数を維持し、取得時の構造化台帳と複数候補の context を実装すること。authority や Imprint 設定の解禁を伴わない |
| Imprint 自動補完の実装 | **NO-GO** | 信頼済み供給経路が未構築。期限・失効・監査運用が未定。保存先の既存 Imprint を Talker が参照できず、空白値の保存・再読込も保証できない |

未解決事項を推測で埋めない。特に D の供給主体・鍵管理・資料の権利・失効情報の配布周期・保管責任、
E の既存値を参照できる host 契約、外周空白 / 改行を含む raw 値の出力保証は実装前の阻害条件。
cache の原取得時刻不明、複数 request の同時点性、MADB discovery の coverage、parser で失われた重複は既知の制限として残す。
これらを COMPLETE / VERIFIED の宣言で解消しない。

推奨順序は **A → B → C**。D と E は独立した根拠確認として進められるが、
両方の受入が成立しない限り F / G の本番自動補完へ進まない。

## 13. 工程 A の実装記録（Phase 2C-2C-2A）

2026-10-20 (JST)。工程 A のみを実装した。上記の工程 B 以降と Imprint 自動補完の NO-GO は変更しない。
開始時の本書は前工程からの未追跡ファイルだったため、既存本文を保持して本節を追記した。
基点は引き続き `main` / `cbce602`。以下は本節時点の実装であり、§1 の調査時点のコードとは区別する。

### モデルと内部入口

`acquisition.py` へ `AcquisitionState`、`ResourceAcquisition`、`AcquisitionContext` を移した。
enum 値、既定値、入力検証はそのまま保持し、`imprint_candidates.py` から同一クラスを再公開する。
追加した `AcquisitionStage` / `AcquisitionReason` は取得状態とは別軸。
`AcquisitionFailure`、`AcquisitionEvent`、`AcquisitionTrace` は frozen dataclass であり、
返却するコレクションは tuple。例外本体・traceback・source・session・callback を返却しない。

MADB 固有の結果と組立処理は `sources/madb_acquisition.py` に分離した。
`MADBAcquisition(value, context, trace, error)` の value は既存の `MADBSearchPage` または
`MADBRecordBundle`。成功なら error=None、最上位の `MADBError` による失敗なら value=None とする。
Series の取得失敗は従来どおり partial bundle の正常返却であり、失敗の詳細は trace に残る。

内部入口は次の二つ。後続の linkage core は各結果を保持し、value を再取得せずに利用できる。

```python
discovery = source._search_by_isbn_with_trace(isbn, refresh=False)
acquired = source._get_with_trace(book_id, refresh=False, series_only=True)
# acquired.value: existing MADBRecordBundle, or None on a fatal MADBError
# acquired.context: source-call scope, not a completed linkage/discovery assertion
# acquired.trace.events: immutable ordered observations
# acquired.error: immutable fatal error facts, never a traceback
```

full scope は `series_only=False`。公開 `search_by_isbn()` / `get()` / `get_for_series_linkage()` は
従来の戻り値と例外を維持し、記録器を渡さず同じ取得処理を実行する。
公開 API を内部 outcome の projection に置換する必要はなかった。
元の例外をそのまま再送出できるよう、共有する private 処理に記録器を任意で渡す方式を採用した。
記録器は一回の呼び出し内だけ mutable で、source 属性には保存しない。
これは §3 の仮称・配置を具体化したものであり、linkage core の実装ではない。

### 記録内容と完全性

cache、network、snapshot、relation、scope の各段階を、実際の分岐で記録する。
cache hit / miss / invalid / refresh、応答成功、parse 失敗、row / byte cap と上限値、
relation budget、重複参照、無効参照、未要求 scope、上流失敗を区別する。
query key / namespace、resource kind / URI、ISBN、親 URI / predicate、raw statement、
parsed statement の位置、HTTP status / Retry-After / error kind を対応付ける。
warning の解析は行わず、既存 warning の順序・重複除去を変更しない。

`context.resources` は既存 evaluator の Book / Series 範囲に限定する。
Agent と Series が同じ URI 空間を使うため、未要求 Agent の記録で取得済み Series の状態を上書きしない。
Agent / Holding の各参照は kind を伴う trace に保持し、集約状態を `agents` / `holdings` に返す。
full scope でも URI ではない publisher 参照は現行どおり取得せず、`NON_URI_PUBLISHER` として明示する。
そのため台帳の Agent 完全性が partial でも、既存 bundle の completeness は従来の complete のままの場合がある。
台帳の追加情報で旧 bundle の意味や値を変更しない。

完全な Book で raw `isPartOf` がない場合だけ series / relations は NOT_RELATED。
Book が partial / truncated で参照が見えない場合は series=NOT_REQUESTED、relations=PARTIAL。
有効 Series がすべて失敗すれば UNAVAILABLE、一部成功なら PARTIAL。
無効 relation だけなら series=NOT_REQUESTED、relations=PARTIAL。
Series row cap は TRUNCATED、budget で未試行の resource は NOT_REQUESTED と理由を残す。
full scope で Series の取得に失敗した場合、その Series 内の Agent 参照も観測できないことを
UPSTREAM_FAILED の scope event で残す。軽量 scope の Agent / Holding は常に NOT_REQUESTED。

取得済みの各 snapshot と relation の状態は成功後に消さず、途中の Series 失敗後も従来どおり後続取得を続ける。
Book の失敗では後続の scope を NOT_REQUESTED と記録して終了する。
入力の ValueError、closed source の RuntimeError、OSError / SQLite error、内部の assertion は
従来の境界を維持して送出し、正常な outcome に変換しない。それらの異常終了時の台帳返却は今回の契約に含めない。

一回の ISBN 検索の COMPLETE は、全 NDL ISBN の discovery 完了を意味しない。
Book 取得結果の discovery は NOT_REQUESTED のまま。全 ISBN の予定・中断・候補集合を集約する責務は工程 B に残す。
`AcquisitionContext` をそのまま本番 Imprint 評価へ渡して COMPLETE に補う処理は追加していない。

### 時刻と原応答

run ID はローカル UUID、開始・観測・終了時刻は UTC の実行時刻。
network の `origin_fetched_at` は今回の応答本文の受信完了を観測したローカル時刻であり、
サーバー上の更新日時や全 resource の共通時刻ではない。
完全な本文が取得できた場合に限り、その bytes の SHA-256 を記録する。
requests の本文 bytes に対する hash であり、HTTP wire bytes の hash ではない。

cache hit / invalid cache では保存された本文の hash は記録できるが、
原 HTTP の status / header / 取得時刻、cache 保存時刻は得られないため None。
本文が未完の timeout / byte cap、HTTP error で本文を読まない場合も完全な応答 hash は None。
bundle 全体の `acquired_at` は None とし、cache と network を混在させた取得時刻を捏造しない。
新規の cache envelope、parsed snapshot digest、HTTP 原応答 archive は追加していない。

### 互換性と次工程

専用テストは synthetic な HTTP / cache / parser 入力を使用し、実測 fixture を新たに作成していない。
実測 evidence と hash は既存の Imprint 回帰試験で保持を確認する。
公開経路と trace 経路の bundle、warning、例外情報、HTTP の引数・順序・件数、cache 書き込みを比較する。
packaging では新規 module の収録、旧 import path の同一性、実 ZIP 内での取得台帳と warm cache も確認する。
最終件数と権限問題を含む実行結果は [validation.md](validation.md) の Phase 2C-2C-2A に記録する。

工程 B は **CONDITIONAL GO**。この台帳を使い、全 discovery / 候補集合の状態を集約し、
公開 LinkageResult と Series 出力の互換性を保持する条件で進められる。
今回は `linkage.py`、`talker.py`、Series 補完、NDL mapping、authority、Imprint 設定・書き込みを変更していない。

## 14. 工程 B の確定契約（Phase 2C-2C-2B）

工程 A の §13 はその時点の記録として維持する。本節は工程 B で実装した契約。
`linkage.py` の取得ループを一つの core へ移し、公開 wrapper はその `linkage` のみを返す。
`talker.py` / `series_supplement.py` の入口、設定、採用条件、書き込みは変更していない。
既存 Series 補完は従来の wrapper を経由するため、内部では共通 core を通るが、
補完側を共有結果へ移行する工程 C は未実装。

### 内部入口と型配置

```python
evidence = acquire_linked_record_evidence(record, madb_source, refresh=False, scope="series_linkage")
# evidence.linkage: historical LinkageResult
# evidence.bundles: accepted, already-acquired MADBRecordBundle objects
# evidence.acquisition_context: complete local run ledger
```

`scope` は `series_linkage`（既定）または `full`。不正な値は通信前に ValueError。
公開 `link_ndl_record()` は full、`link_ndl_record_for_series()` は series_linkage を使用する。
両関数の引数と戻り値は従来どおり。`compare_candidates()` と `_evaluate()` の比較規則は変更していない。
package `0.3.0`、identity `phase2b2-v1`、Imprint evaluator `phase2c2b-v1` を維持する。

| 型 | 配置と責務 |
|---|---|
| `NDLInputSnapshot` | 新規 `linked_acquisition.py`。取得開始前の比較入力 |
| `ISBNDiscovery` | 同上。正規化 ISBN ごとの state / reason / page / 元の acquisition / error |
| `DiscoveryAcquisition` | 同上。全 ISBN の予定順、個別結果、全体状態、truncated と複数の理由 |
| `BookAcquisitionContext` | 同上。発見した Book ID / URI、統合 context、元の acquisition、bundle、error、採用対象の区別 |
| `LinkedAcquisitionContext` | 同上。run ID、UTC 開始・終了、scope、NDL 入力、discovery、全 Book、元の traces、issues |
| `LinkedRecordEvidence` | `linkage.py`。`linkage`、`bundles`、`acquisition_context` |

全 dataclass は frozen、コレクションは tuple。mutable な source / session / cache / callback /
recorder / 例外本体を保持しない。新規モデルは工程 A の取得状態 enum を再利用し、
`imprint_candidates.py` を import しない。旧 import path の 3 型は引き続き同一クラス。
`LinkedAcquisitionContext.events` は各 trace の元 event を取得順に並べた tuple の property。
元の source outcome / trace / bundle / statement はコピーして作り直さず参照を保持する。

### NDL 入力の固定範囲

`id`、`url`、`title` と、`isbns`、`volumes`、`publishers`、`editions`、`issued`、
`dates`、`series_titles` の raw 値を保持する。現行 identity、Series 比較、Imprint 比較の参照箇所を確認した。
list は tuple へコピーし、文字列の NFC / NFKC 正規化、版・出版社・巻の補正はしない。
`volumes` と `title` が巻の原値であり、推定した巻番号は既存の比較処理が求める。
snapshot の `to_record()` は呼ぶたびに新しい list を持つ private な `BookRecord` を作る。
一回の core は最初に作った private 入力だけを使用し、取得中の呼び出し元による変更を混在させない。

書誌の全フィールドを複製する契約ではない。現在の比較で参照しない `raw_xml`、
`content_dates`、著者・説明等は含めない。将来の authority 検証で媒体や追加の日付・書誌情報が必要なら、
その用途と raw 型を確認して契約を追加する。今回の snapshot を媒体確認済みの根拠にはできない。

### 一回の取得フローと集約

1. 既存の `isbn13()` で有効 ISBN を正規化・重複除去し、昇順の tuple に固定する。
2. 全 ISBN を順番に `_search_by_isbn_with_trace()` で検索する。
3. 全 discovery の候補を Book ID でまとめ、Book ID 順に `_get_with_trace()` で取得する。
4. `MADBAcquisition.value` をそのまま比較・共有に使い、追加取得を行わない。
5. 全体の discovery 状態を各 Book の context に付加する。元の source context は outcome 内に変更せず残す。
6. 従来の判定と warning 生成を行い、共有結果を返す。

最上位の discovery / Book failure で直ちに後続の取得を中断する。
残った ISBN は個別に NOT_REQUESTED / `upstream_failed`。
発見済み・未取得 Book も bundle=None、book=NOT_REQUESTED / `upstream_failed` として返す。
Series 内部失敗は source の従来動作どおり partial bundle として取得が続き、各失敗 event を保持する。

| discovery の条件 | 集約状態と根拠 |
|---|---|
| 有効 ISBN なし | NOT_REQUESTED / `no_valid_isbn` |
| 全 ISBN が trace 上 COMPLETE | COMPLETE。正常な 0 件も含む |
| 最初の discovery が失敗 | UNAVAILABLE。後続は NOT_REQUESTED |
| 一部成功後に失敗 | PARTIAL。成功 page、failure、後続未実行をすべて保持 |
| 成功した discovery に row cap | TRUNCATED。各 ISBN の状態と `discovery_truncated` を保持 |
| truncated と失敗の混在 | PARTIAL、truncated=True、両方の理由を保持 |
| trace 不足・その他の不完全性 | PARTIAL。trace がない非 truncated 成功を COMPLETE にしない |

一回の source call の COMPLETE だけでは全体を COMPLETE にしない。
byte cap 等で page が返らない failure の場合、全体は UNAVAILABLE / PARTIAL となり、
TRUNCATED の event と cap 値は元 trace 内に残る。公開 `LinkageResult.truncated` は、
従来どおり返却済み search page の truncated の OR であり、台帳を理由に意味を拡張しない。

### 現行コードを優先した互換性判断

- 同じ ID / URI の重複発見は一回だけ取得する。同じ ID に異なる URI が出る場合、
  旧 core は最後の URI を使っていた。この挙動を維持し、全 search page と
  `conflicting_discovery_uri:<ID>` を別に保存する。将来の採用側は安全性阻害条件として扱う必要がある。
- 取得した Book の ID / URI が discovery と違う場合、従来どおり schema failure / UNAVAILABLE。
  その bundle は `evidence.bundles` に含めず、該当 `BookAcquisitionContext.bundle` と元 outcome に保存する。
  `included_in_linkage=False`、error と `discovered_book_mismatch:<ID>` を明示する。
  source の COMPLETE は取得自体の状態なので、identity 整合性の証明と混同しない。
- source は候補を既に parser で重複除去している。parser 内で失われた元の行を復元する契約ではない。
- `Mock(spec=MADBSource)` 等の既存 fake や公開メソッドの monkeypatch は、通信前に選ぶ adapter で対応する。
  実 MADBSource の変更されていない公開メソッドは trace 経路を使い、公開メソッドが置換されていれば
  そのメソッドを一度だけ呼ぶ。別クラスの fake は class に trace メソッドを明示した場合だけ trace 対応とする。
  trace を試してから公開メソッドを再実行する fallback はない。
- trace がない正常値は既存の identity 比較には使用するが、新台帳では `trace_unavailable` を残す。
  Book / Series / relations の完全性を推定せず、空 Series を NOT_RELATED にしない。
  軽量 scope の Agent / Holding は NOT_REQUESTED。元の trace、HTTP 時刻、hash は捏造しない。

この adapter と不整合診断は §3 の概略を具体化したもの。公開結果を保つため、
新しい台帳上の阻害条件を identity algorithm に混入させない設計とした。
本番 Imprint 評価への接続時には、個別の context だけでなく run 全体の issues と
`included_in_linkage` も検証する必要がある。今回 evaluator には接続しない。

### 例外・provenance・制限

工程 A の最上位 `MADBError` は outcome.error から従来の UNAVAILABLE に変換する。
既存の matches / confidence / candidate count、取得済み candidate completeness、
warning の内容・順序・重複除去、error kind / message / status / Retry-After を保持する。
ValueError / RuntimeError / OSError / SQLite error / assertion は従来どおり送出する。
これらの異常終了時に途中台帳を返す契約は追加しない。NDL のエラー履歴にも書き込まない。

run ID は linkage 全体と各 source call で別。UTC 開始・終了は実行時刻であり、
bundle の原取得日時ではない。原 HTTP 時刻、cache 保存日時、hash の意味は §13 のまま。
HTTP 本文 hash は parsed RDF snapshot hash ではなく、複数 HTTP の同時点性も保証しない。
新しい cache envelope / parsed snapshot digest は未実装。endpoint、query、parser、
timeout、limiter、cap、cache key / namespace / 期限 / 保存条件、refresh、自動 retry 禁止を維持した。

### 検証と次工程の受入条件

旧 core の段階で 24 ケース × 2 scope の公開結果を
`tests/fixtures/linkage_evidence_baseline.json` に固定した。
この fixture と新規専用テストの HTTP 応答・fake trace はすべて synthetic。
既存の実測 evidence は変更していない。新 wrapper と新 core の比較だけに依存しない。
工程 A の 58 テスト、既存 Series / identity / NDL / Imprint / packaging の回帰も実行する。
詳細な件数、build・権限問題・ZIP の結果は [validation.md](validation.md) の工程 B に追記する。

取得共有基盤は工程 C へ **CONDITIONAL GO**。次工程では以下を受入条件とする。

1. Series / Imprint の要否を個別判定し、必要な場合だけ一回の共有取得へ接続する。
2. 既存 Series の結果、標準経路の通信数、候補一覧等での補完用通信ゼロを維持する。
3. Imprint の判定前に全 discovery・各 Book・relation・issues と snapshot の対応を検証する。
4. Imprint の本番 authority 供給・真正性・失効・適用範囲が解決するまで、自動補完を有効化しない。

**Imprint 自動補完は NO-GO を維持する。** 取得台帳の完成は意味確認の供給問題を解消しない。

## 15. 工程 C の確定契約（Phase 2C-2C-2C）

工程 A / B の §13 / §14 はその時点の記録として保持する。本工程では既存 Series 補完だけを
共通取得入口へ接続した。Imprint の設定、意味確認 provider、evaluator の本番接続、書き込み、
工程 D / E の追加調査は行っていない。version `0.3.0` と既存の各 algorithm version を維持する。

### 共通入口と依存方向

新規 `metadata_supplement.py` に次の入口を置く。

```python
def supplement_metadata(
    metadata: GenericMetadata,
    record: BookRecord,
    cache_folder: Path,
    *,
    series_enabled: bool = False,
) -> GenericMetadata: ...
```

必要条件は `series_enabled and not (metadata.series or "").strip()`。
OFF、または非空 Series がある場合は、source / session / cache を生成せず入力オブジェクトを返す。
ON で None / 空文字列 / 空白だけの場合に限り、一つの `MADBSource` と一回の
`acquire_linked_record_evidence(record, source, scope="series_linkage")` を使用する。
full scope、旧 linkage wrapper を先に呼ぶ経路、二重取得はない。

`LinkedRecordEvidence` は local 変数に保持し、取得済み `.linkage` だけを Series 採用関数へ渡す。
`.bundles` / `.acquisition_context` を再構築しない。source の close 後も同じ immutable な結果を
入口内で参照でき、将来の別評価もこの位置で共有できる。今回の返却値は従来どおり metadata のみ。
source、session、cache、recorder を module の global 属性へ保存しない。

循環 import を避けるため、純粋な採用関数だけを新規 `series_supplement_policy.py` に分離した。
これは §4 の概略を具体化する際の配置変更であり、関数本体は移行前と AST が一致する。
`series_supplement.py` は `apply_series_supplement` を同一オブジェクトとして再公開し、
`supplement_series(metadata, record, cache_folder, *, enabled=False)` を互換 wrapper として残す。
wrapper は `series_enabled=enabled` で共通入口へ一度だけ委譲し、取得・ログ・close・Notes を処理しない。

```text
talker.py ────────────────────→ metadata_supplement.py → linkage.py / MADBSource
series_supplement.py（互換）───→ metadata_supplement.py → series_supplement_policy.py
series_supplement.py（再公開）────────────────────────→ series_supplement_policy.py
```

共通入口から互換 wrapper への逆参照はない。両 module を先に import する順序をそれぞれ試験し、
import 時に session を作らないことも確認する。従来の constructor の monkeypatch は内部依存位置が
変わるため、既存テストでは `metadata_supplement.MADBSource` へ対象を移した。assertion は保持する。

### Talker の接続点と設定

`fetch_comic_data()` の `to_metadata()` 直後だけを新入口へ切り替えた。
NDL ID の決定、`get(summary_mode="fetch")`、巻の解決、要求巻との照合、metadata 変換は変更しない。
取得失敗・巻不一致・ID 未選択では共通入口へ到達しない。
候補検索、`search_metadata()`、`fetch_series()`、両 issue 候補 API、`check_status()` では
共通入口を実行しない。候補取得の `summary_mode="cache"` を保持する。

公開設定は既存の `jpbooks_madb_series_supplement` のみで、既定 False、保存・復元・検証規則もそのまま。
新入口には refresh 引数を追加していない。検索の `refresh_cache=True` は NDL にだけ伝わり、
最終 MADB 取得は既存どおり core の既定 refresh=False を使う。
core を直接呼ぶ明示的な refresh=True の契約は工程 B のまま。

### Series / Notes と障害の等価性

EXACT / STRONG、一意性、取得完全性、MADB_ONLY、一つの display を要求する従来の採用条件を維持する。
AMBIGUOUS / UNSAFE / UNAVAILABLE、truncated、reading-only、複数表示・Series URI、
XML 不正値を救済しない。raw display は変更せず、既存 Series を上書きしない。
採用時の変更は `series` / `notes` だけ。既存 Notes の本文・改行、行単位の重複抑止を維持する。
Imprint 等の他フィールドは変更しない。

取得 → `with` 終了による close → warning → 採用関数、の順。
constructor / 取得 / close の `MADBError`、`OSError`、`sqlite3.Error` は元の metadata を返す。
source の生成が成功した場合は正常・異常にかかわらず close を一度試みる。
source 内の既存 `close()` が session と cache の close を試み、入口から二度目の close は呼ばない。
close が失敗した場合も補完前の入力を返す。close 成功を偽って記録するものではない。
constructor が例外で返らなかった場合の部分初期化処理は既存 source の責務で、今回変更していない。

UNAVAILABLE の warning、個別 warning、例外時 warning の文言・順序・回数を保持した。
既存のログ設定も壊さないよう logger 名は `comictagger_jp_talker.series_supplement` を継続使用する。
`latest-error.txt` を更新せず、既存ファイルの bytes を保持する。
TypeError / ValueError / RuntimeError / assertion は隠蔽せず伝播する。
複数の例外が同時に起きた際の Python context manager の例外処理も変更していない。

### 通信・試験・配布物

すべて HTTP mock による synthetic 試験。実測 fixture / raw evidence は変更していない。

| 条件 | 確認する MADB 通信 |
|---|---|
| OFF / 既存 Series あり | source 生成 0、HTTP 0 |
| 単一 ISBN / Book / Series の最終 fetch | source 1、共有 core 1、cold HTTP 3、warm 追加 0 |
| 同じ条件の明示的な内部 refresh | HTTP 3。検索 refresh からは伝搬しない |
| Series relation なし | discovery + Book の 2 |
| 二つの正規化 ISBN、同じ Book | discovery 2 + Book + Series の 4 |
| 二つの Book、同じ Series URI | discovery + Book / Series 各 2 の 5 |
| Series cache の部分失効・破損 | 追加 HTTP 1 |
| discovery / Book / Series で 429 / 503 / timeout | 各 1 / 2 / 3 で終了、自動 retry なし |
| Agent / Holding | 詳細 HTTP 0 |

同じ Series URI でも relation cache key は親 Book を含むため、複数 Book の cold では
各 Book の取得範囲に従って要求する。今回、Book 間の追加共有や query 削減は導入していない。

実 NDL parser は欠落タイトルを拒否し、通常の mapping はそのタイトルから Series を作る。
そのため欠損 Series の試験は synthetic な BookRecord を用いる。
SRU / summary と補完を併せた試験では、正当な XML を既存 parser で取得した後に、
欠損比較入力だけを test adapter で注入する。通常タイトルの対照では MADB が 0 要求であることを確認する。
本番 parser / mapping を緩和した実測例や、補完対象の実在性を証明したものではない。

移行前に `metadata_supplement_baseline.json` へ 29 ケースの全 GenericMetadata フィールドと
warning の名前・level・本文を固定した。新入口、互換入口、Talker の三経路で同じ固定値と比較する。
既存の採用試験、工程 A の 58 件、工程 B の 165 件と公開 linkage の固定 fixture も維持する。
新規専用試験は 163 件。関連試験は 871 passed / 2 skipped。
全回帰・build・実 ZIP の結果と権限問題は [validation.md](validation.md) の工程 C に記録する。

配布検証は現在の source から sdist → wheel → 既存 `build_plugin.py` の ZIP を作る。
全 production Python を実ファイル一覧で byte 比較し、ファイル数を工程 B の 21 に固定しない。
beta9 loader の path cleanup 後に新入口・既存 Series 補完・共有 core を実行し、
default OFF、NDL summary・巻処理、軽量 3 / 0 要求を確認する。

### 受入判断と残る阻害条件

工程 A～C は **既存 Series 補完を対象とする取得共有基盤として GO**。
これは取得台帳、共有 snapshot、既存 Series の出力・通信・障害処理の範囲の判断。
取得時刻が不明な旧 cache、複数応答の同時点性、parsed snapshot digest 等は工程 B の制限を継承する。
工程 C で解消したとは扱わない。

**Imprint 自動補完は NO-GO**。工程 D では authority の真正性・独立性・対象適合・更新・失効運用の
実証が必要。工程 E では既存設計 §7 の保存先既存値の保護と host 保存・再読込境界の解決が必要。
その前提や実装可否は別途判断する。工程 C の完了だけで Imprint 評価・設定・書き込みを有効化しない。

## 16. 工程 E0 の保存境界実証（Phase 2C-2C-3E0）

2026-10-20、ComicTagger `1.6.0b9` / comicinfoxml `0.5.1` の導入済み実装、
実 GenericMetadata / prepare_metadata / ComicArchive と synthetic CBZ を使用した。
詳細は [保存境界の調査報告](phase2c2c_host_imprint_boundary.md)、
実行結果は [validation.md](validation.md) の E0 記録を参照する。
§13～§15 の確定契約と production code は変更していない。

### 確定した保存フローと §7 からの補足

最終 fetch には archive metadata、raw XML、保存設定が渡らない。
独自 `search_metadata()` は host callback ではないため、既存値供給の代替にならない。
GUI はフォーム → prepare → フォーム → 保存前の再変換 → writer → 選択 reader の再読込、
CLI / 自動 worker は archive metadata → prepare → writer を使う。
prepare は import transform → clear → merge → auto_imprint の順に処理する。

- OVERLAY は非空の取得 Imprint で既存値を上書きする。ADD_MISSING はメモリ内の非空値を保護するが、
  reader が既に None にした空白値、未読のタグ、clear 後の値は保護しない。
- auto_imprint は merge の後に publisher と Imprint を変更できる。現行 import transformer は
  Imprint を直接変更しない。両者を同じ変換として扱わない。
- GUI の `metadata_to_form()` は None を代入しないため、clear 後の None が旧フォーム値として
  保存時に復活するケースを実測した。CLI / 自動 worker の消去と異なり、保護機能として依存しない。
- CR と CIX は同じ `ComicInfo.xml` を読む。独立した既存値の二重保存ではない。
  両 writer は raw 外周空白を保存するが、両 reader は xlate で除去し、空白だけなら None にする。
  CR / CRLF は XML parser が LF に変換する。GUI ではフォーム変換でも外周を失う。
- XML 不正文字を含む XML でも writer は True を返し得る。両 reader はタグなしとして扱い、
  再保存で旧値を失う。writer の成功戻り値だけを保存の受入条件にしない。
- 候補専用 API が共通入口を呼ばない既存契約は維持する。ただし host の
  `IssueSelectionWindow` は詳細表示の不足を補うために `fetch_comic_data()` を呼ぶことがある。
  現行 API では保存目的とプレビュー目的も区別できない。§15 を GUI 全操作の通信禁止とは解釈しない。

### 保証範囲と追加の受入条件

通常の日本語・英数字・内部空白・XML 特殊文字・非 BMP 文字は両形式で往復した。
内部 LF / TAB も今回の範囲では保持されたが、外周空白、CR、XML 不正値を含む任意 raw の保証はできない。
raw を trim / 改行置換して採用する設計には変更しない。非対応値は停止が必要。

通常既存値を保護する部分集合は、対象の正しい読取、clear / auto_imprint OFF、
新しい非空値が来る場合の ADD_MISSING、後段編集・同時更新なし、実保存と再読込の検証を要する。
これらは host 側の実行条件であり、現在の Talker が強制できる条件ではない。
一般的な保存確認ダイアログも raw 旧値と候補の照合確認にはならない。
将来の host 契約には raw の存在と値、保存先との対応、予定設定、保存直前の状態確認、
欠損時のみの適用と保存検証が必要。単に GenericMetadata を追加引数にするだけでは不十分。

| 対象 | 判定 |
|---|---|
| E0 の調査・反例の実証 | **GO**。新規 592 件、実 CLI / offscreen GUI / 自動 worker の保存を含む |
| 通常文字列の CR / CIX 往復 | **GO**。導入版・試験対象値の範囲 |
| 保存先既存値の保護 | **CONDITIONAL GO**。上述の部分集合のみ。任意 raw / 設定では NO-GO |
| host の変換・上書き抑止 | **CONDITIONAL GO**。host 側の制約と再検証が必要。Talker からの強制は不可 |
| 任意 raw の往復 / Talker 単独の保証 | **NO-GO** |
| 将来の限定方式 | **CONDITIONAL GO**。診断のみ、または保存直前の確認・host 契約の追加設計が先 |

GUI は実 widget の同期した保存経路を offscreen で試験した。
検索クリック、曖昧候補ダイアログ、開始ダイアログの設定伝搬、配布 exe 全体の操作は未検証。
特に開始ダイアログの auto_imprint と worker の有効設定は同じとは限らず、実機手順を報告書に残した。

工程 E の全対象保護は未達であり、E0 の調査完了を工程 F / G の着手許可としない。
工程 D の authority 供給・失効・監査も未完了なので、**Imprint 自動補完全体は NO-GO**。
工程 A～C の取得共有基盤の GO は維持する。
推奨順序は、診断 / host 契約の方式選択と E の追加受入、並行する D の実証、
両者の NO-GO 解除レビュー、その後に F → G。

## 17. 工程 E1 の提供方式と host 保存契約（Phase 2C-2C-3E1）

2026-10-20。[提供方式の詳細設計](phase2c2c_imprint_delivery_design.md) に、
現行 API の能力、診断の出力契約、将来の保存責務・対象識別・競合・検証・監査を定義した。
§16 までの記録を保持し、production code / 公開設定 / host / 既存テストは変更していない。
E0 の「調査 GO」と「Talker 単独の保存保証 NO-GO」を引き継ぐ。

### 選定結果と診断の契約

**第一候補は独立した明示診断コマンド（詳細設計の比較方式 B、CONDITIONAL GO）**。
NDL ID 一件と明示的な通信許可を受け、既存の固定 endpoint / 制限 / cache を使い、
NDL summary は取得せず、共有 core の軽量 scope で一度取得する。現在コマンドは未実装。
純粋な report 関数は既存 `LinkedRecordEvidence` だけを受け、再取得しない。
通常 Series 補完の evidence はローカル変数であり、後から取り出せる host API はない。
別の明示診断実行を、cache hit という理由で通常 fetch と同じ snapshot と称しない。

出力は stdout の text / 版付き JSON。Imprint / Notes / description / ComicInfo.xml を変更しない。
Book / Series の raw term、language / datatype、identity、全候補・競合、完全性、
`LinkedAcquisitionContext.issues`、分類・保留・拒否理由、unknown 時刻を保持する。
authority は初期版で未供給、意味確認は UNVERIFIED。保存先は not_supplied、
既存値は未評価、保存処理なしを表示する。診断成功は採用・保存成功を意味しない。

現行 Talker に診断専用 callback / UI 登録口 / 保存先引数 / purpose はない。
ログファイルと ApplicationLogWindow は実在する補助表示先だが、実行入口の代替ではない。
通常 fetch / check_status に診断通信を加えず、NDL の `latest-error.txt` を流用しない。
比較方式 A は「現行 API だけで独立した診断機能」として NO-GO。
診断コマンドの Python module 配布と、ComicTagger.exe 内での起動能力を混同しない。

### 将来の保存責務と §6 の扱い

将来の拡張候補は **host の保存直前確認付き限定補完（比較方式 C）**。
候補・意味評価は plugin、raw 保存先観測・確認・条件付き適用・writer・検証・監査は host が担当する。
`SaveIntent` / `ArchiveObservation` / `ReviewReceipt` / `PreparedSave` 等は提案名で、
現行 API には存在しない。beta9 は保存能力なしとして fail-closed にし、旧 fetch への fallback は作らない。

§6 の pure apply / 最小限 Notes 案だけでは保存先保護を保証できないため、
初期の限定保存案は host が最終 metadata に Imprint delta だけを適用し、Notes 追加は別受入へ延期する。
既存 Series / Notes は通常 host 処理後の予定値を基準に保持し、診断情報を混ぜない。
これは責務と初期範囲を狭める設計上の補足であり、現行 apply / evaluator を変更するものではない。

初期の host 契約は次を要求する。

- 実ファイル同一性、operation_id、metadata / settings revision、raw XML の bytes と読取状態。
  同じ ISBN / NDL ID / Talker instance / callback で archive を識別しない。
- 正常に確認した XML の Imprint 要素なし、または正常な archive 列挙で XML 自体なしの場合だけ適用可能。
  空要素も既存値として停止する。空白、未読、不正 XML、重複 member / 要素を欠損にしない。
- clear / auto_imprint OFF、フォーム・import transform・merge 後の最終 metadata を固定。
  raw 欠損と metadata 欠損を両方要求し、確認後の再変換・編集で計画を失効させる。
- authority ready と evaluator ELIGIBLE は独立の必須条件。context の issues も未解決なら停止。
  候補は XML 有効、外周空白・CR / LF / TAB・C0 / C1 なしの通常単一行に限定し、normalize しない。
- 一つの CBZ / 物理 XML に一つの writer を明示選択。CR と CIX への同時 write は初期版では停止。
  両 reader による fresh な再読込と期待値比較は必須。
- 確認後の再検査、排他または同等の transaction、既存 writer による stage、commit と事後検証、監査。
  現行 ZIP writer に原子的な欠損時適用契約はない。hash / mutex / atomic rename だけで
  TOCTOU 解消を宣言しない。実証できない環境は BLOCKED。

READ_ONLY / REVIEW_REQUIRED / CONDITIONAL_APPLY / BLOCKED は新しい概念状態。
既存の意味評価 ELIGIBLE と統合しない。取得・authority・target・purpose・保存結果の各軸で
停止理由を保持し、writer True だけで VERIFIED_SAVE にしない。既存 production enum への追加はない。

### プレビューと受入条件

詳細表示の不足した候補は `_fetch()` の繰返しで再度最終 fetch を呼び、callback に archive / purpose はない。
通常の Series 条件・通信は変更しない。新しい診断は通常 fetch に接続しない。
将来 host は per-operation token と取消・世代管理を持ち、同じ候補を使う複数 archive の結果を混ぜない。
authority はプレビュー時の成功を再利用せず、確認時・保存直前に供給版・期限・失効を再評価する。

| 対象 | E1 の判断 |
|---|---|
| 比較 A: 現行 Talker API のみの独立診断 | **NO-GO**。実行・報告の専用契約がない。ログ表示手段の存在とは別 |
| 比較 B: 明示診断 command | **CONDITIONAL GO**。第一候補。非書込、明示通信、UNVERIFIED、版付き出力、配布・回帰受入が必要 |
| 比較 C: 確認付き限定保存 | host 側の設計・実験は **CONDITIONAL GO**。現行環境への補完実装は **NO-GO** |
| 比較 D: 限定自動補完 | **NO-GO**。C の契約と D の authority、別の無人処理受入が必要 |
| 比較 E: 自動補完を見送る | **GO**。現在の production 方針として B と両立 |

追加の test-only 6 件で API 能力、evidence の無通信評価、metadata / CBZ 不変、
プレビューの反復と引数不足、escaped raw の実ログ表示を確認した。
保存 gate / transaction / 診断 command は未実装であり、それらの安全性をテストで証明したとはしない。
詳細な試験結果は [validation.md](validation.md) の E1 記録を参照。

推奨順序は純粋 report → 明示 command → 診断配布。
並行して host raw 観測 / transaction の feasibility と D の実供給を別々に検証する。
双方の受入・レビュー前に F / G を開始しない。
工程 A～C の GO と E0 の実測を維持し、**Imprint 自動補完全体は NO-GO**。

## 18. 工程 R1 の確定契約（Phase 2C-2C-4R1）

2026-10-23。§17 までの設計・記録を保持し、純粋な診断 report のみを実装した。
詳細は [R1 の契約](phase2c2c_imprint_report.md)、検証結果は [validation.md](validation.md) を参照。

- `imprint_report.describe_imprint_evidence(LinkedRecordEvidence)` は frozen な
  `ImprintDiagnosticReport` を返す。`report_to_json_data(report)` は新しい JSON 互換 dict を返す。
- schema は `imprint-report-v1`、package は `0.3.0`。identity `phase2b2-v1` と
  evaluator `phase2c2b-v1` は変更しない。JSON の型・フィールドは明示し、暗黙の schema 変更を拒否する。
- acquisition 台帳、全 discovery page、失敗・未取得・除外を含む全 Book、全 trace / issues と
  linkage 全体を保持する。Book の対応は台帳の位置で示し、同じ ID を集約しない。
- included_in_linkage=True の bundle に既存の抽出・分類・比較・評価を適用する。
  NDL は取得時 snapshot の独立コピー。除外 bundle は分類まで、bundle 不在は評価なし。
  identity を再計算せず、局所的な一件だけの MATCHED を作らない。
- raw term・出典・qualifier・statement / label indices・比較 key・blockers を保持する。
  authority は空 tuple、保存先は未供給。HOLD / REJECT / SKIP を変更しない。
- operation=READ_ONLY、authority_state / archive_state=not_supplied、target_known /
  existing_value_assessed / apply_allowed / writes_performed=false を固定する。
  `existing_imprint=None` は archive 欠損の観測ではない。
- 取得時刻・cache・応答 hash の不明値は null のまま。bundle の同時点性は unknown。
  API は通信・filesystem・metadata 更新・clock 読取・出力を行わない。

R1 の専用試験は 208 件。R2 の通信・コマンド・renderer、R3 の実用性確認は実装していない。
通常 Talker / metadata_supplement / Series 補完への接続、新設定、entry point は追加しない。
R2 は明示通信許可・既存取得制限・close・安全な表示・通常経路非接続を条件に進める。
工程 D と host 保存契約の未解決事項は維持し、**Imprint 自動補完全体は NO-GO**。
