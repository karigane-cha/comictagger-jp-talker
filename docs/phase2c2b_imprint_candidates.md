# Phase 2C-2B: MADB Imprint 候補評価 API

実装・検証期間: **2026-10-08～2026-10-09 (JST)**。パッケージのバージョンは **v0.3.0** のまま。
評価仕様の識別子は `phase2c2b-v1`。推奨判断は **CONDITIONAL GO**。

## 1. 目的と範囲

取得済みの MADB Book / Series と既存の NDL / MADB 照合結果から、Imprint 候補の抽出・分類・比較・採用可否を返す。
[imprint_candidates.py](../comictagger_jp_talker/imprint_candidates.py) は pure function の内部 API である。
ネットワーク、ファイル I/O、SQLite、設定操作、GUI 操作、メタデータへの書き込みを行わない。
通常の Talker 取得経路には接続していない。

`GenericMetadata.imprint`、他のメタデータ、NDL mapping の規則、Series 補完、設定、バージョンを変更しない。
既存の ISBN 正規化、RDF parser、FieldEvidence、LinkageResult / RecordMatch を再利用する。
既存の identity algorithm は `phase2b2-v1` のままである。

## 2. Phase 2C-2A との対応と拡張

基準資料は [調査仕様書](phase2c2a_imprint_research.md)、[実資料台帳](research/madb/imprint_examples.md)、
[保存済み evidence](research/madb/imprint_evidence.json)、[調査用スクリプト](../scripts/research_madb_imprint.py)。
39 Book / 27 Series の raw RDF を再利用した。追加の実 API アクセスは行っていない。

単一表示、Book / Series の一致、NDL の `series_titles` の一致では意味を VERIFIED にしない。
M197767 の版表示、M197011 の publisher 同名、M519976 の番号、M190399 の雑誌混在を維持する。
階層・結合・別表記を推測で統合しない。Series-only の採用は無効である。

仕様案から次を具体化した。

- 補完不要を `SKIP` として追加した。既存値と完全な候補欠損を HOLD / REJECT から区別する。
- 言語・構造の分類と、信頼・対象範囲の検証後の意味確認を分けた。後者は `AuthorityAssessment.semantic_kind` に返す。
- 任意の URL や VERIFIED フラグでは足りず、`trusted`、独立性、対象範囲の明示的な確認を要求する。
- 型・tuple・enum・ISBN・時刻などの入力契約違反は `ValueError` とする。正規の入力での不足・矛盾は判定結果に返す。
- 出版社は厳格な集合一致を要求し、役割付き名称の省略や推測をしない。欠損・複数主体は保留する。
- 明示的な版が片側だけにある場合は未確認として保留する。版の欠損を通常版と断定しない。
- full bundle の Agent / Holding だけが不完全な場合は、呼び出し元による Book / Series 範囲の明示的な完全取得確認を受け付ける。

## 3. モデル

新しいモデルは frozen dataclass。配列は tuple とし、入力オブジェクトを変更しない。

| モデル | 情報 |
|---|---|
| `ImprintCandidate` | origin、FieldEvidence、raw statements、statement_indices、label_indices、Book との関連有無 |
| `ImprintExtraction` | 元 bundle、AcquisitionContext、全候補、raw relation statements、必要な Series URI、blockers |
| `ClassifiedImprintTerm` | 候補参照、言語 role、raw display、equality key、構造段階の意味分類、理由 |
| `ImprintClassification` | extraction と全 term の分類。未知値も保持 |
| `ContextComparison` | publisher / edition の Book・Series・NDL evidence、矛盾と未確認の別 |
| `ImprintComparison` | 比較 state、各表示集合・key・重なり・件数、NDL 観測、関連 Series 状態、文脈比較、blockers |
| `LabelAuthorityEvidence` | レーベル名、出典と locator、対象 Book / URI / ISBN / 巻、出版主体、版・媒体・日付、確認時刻、信頼・独立性・由来 group・適用範囲 |
| `AuthorityAssessment` | 全入力証拠、適用可否、理由。信頼と適用範囲が成立した意味分類 |
| `ResourceAcquisition` | resource URI と取得状態 |
| `AcquisitionContext` | discovery / Book / Series / relations、resource ごとの状態、Agent / Holding の未要求、要求 ID・取得時刻・媒体・取得範囲 |
| `ImprintEligibility` | decision、selected_candidate、全 reasons、comparison、linkage、全 authority assessments、評価仕様の識別子 |

enum は `ImprintTermRole`、`ImprintSemanticKind`、`LabelRelation`、`AuthorityState`、`AuthoritySourceKind`、
`AcquisitionState`、`ImprintComparisonState`、`ImprintEligibilityState`、`ImprintEligibilityReason` を追加した。
`FieldComparisonState` の意味は変更していない。

## 4. API と不変条件

```python
extraction = extract_imprint_evidence(bundle, acquisition)
classification = classify_imprint_terms(extraction)
comparison = compare_imprint_candidates(classification, ndl_record)
decision = evaluate_imprint_eligibility(
    linkage,
    comparison,
    existing_imprint=existing_imprint,
    authority_evidence=trusted_evidence,
)
```

四つの関数はいずれも同じ取得済みデータから再現可能な結果を返す。
NDL BookRecord の必要な値は comparison の tuple / FieldEvidence に固定し、その後の NDL 入力の変更に影響されない。
MADB の既存モデルは immutable な snapshot として参照する。

ELIGIBLE だけが一つの選択候補を持つ。候補は Book の実在する単一 raw display に対応し、比較・identity・XML・authority の条件を満たす。
他の状態は `selected_candidate=None` で、必ず理由を持つ。結果モデルの生成時にも不変条件を検証する。
全理由は重複除去して enum 値で安定順に返す。term / statement / Series / authority の入力順は採用可否に影響しない。
statement の位置情報は並べ替えた入力に対応するので、結果全体の位置情報まで同一であることは要求しない。

## 5. 抽出と provenance

Book の `labels` と各 Series の `labels` を origin ごとに抽出する。
`RDFTerm.kind / value / language / datatype` と元の subject / predicate / object は変更しない。
同一 RDFTerm は resource 内で一つの候補にまとめ、labels の全出現位置と全一致 statement の位置・実体を保持する。
同じ raw display でも言語・datatype が異なる term は別の候補として保持する。

Series 由来の FieldEvidence の `record_id / record_uri` は実際の Series を示す。
Book の `schema:isPartOf` statement と Series URI の関係を別に保持する。
未関連 Series の raw 候補も残すが、Book の表示集合には転用しない。未関連・重複 snapshot・未解決 relation は blocker になる。

raw statement と labels / publisher / edition / ISBN / date / volume の投影が矛盾する場合は採用を拒否する。
モデルの ID / URI、raw identifier、rdf:type も確認する。
labels にない raw brand も削除せず候補に残し、不整合を理由に返す。

既存 parser は Book の同一 triple を重複除去する。この API は入力 bundle に失われた出現を復元できない。
Series および明示的な synthetic bundle に残った重複は全件追跡できる。
取得原応答の永続保存はこの API の範囲外である。

## 6. RDF の言語分類

| 条件 | role |
|---|---|
| literal、言語なし、datatype なし / xsd:string | DISPLAY |
| literal、ja、datatype なし / rdf:langString | DISPLAY |
| literal、ja-hrkt、datatype なし / rdf:langString | READING |
| その他の言語 | OTHER_LANGUAGE |
| 未対応 datatype、URI、blank node | UNSUPPORTED |
| 上記の対応済み literal が空 / trim 後空 | EMPTY |
| tag / datatype の不整合、不正な型、surrogate | INVALID |

language の比較だけ casefold を使い、raw tag を保持する。文字種から表示と読みを推測しない。
未知言語・datatype が空文字列でも EMPTY へ格下げせず、未知 term の blocker を保持する。
未知 term が既知 display と共存すると、比較 state が BOOK_ONLY / BOTH_AGREE でも自動採用を保留する。
既存 parser の拒否条件を緩和していない。手作り snapshot の不正 term は INVALID として拒否する。

## 7. 意味分類と限界

構造段階では原則 UNVERIFIED。数字らしさは NUMERIC_LIKE、publisher 同名は PUBLISHER_EQUAL の診断にとどめる。
それらを理由に別の brand を正しい候補として選ばない。
同一 resource の `schema:version` と厳格に同じ brand は EDITION_STATEMENT / EDITION_EQUAL として保持し、保守的に拒否する。
これは同名ブランドの不存在を証明するものではない。

VERIFIED_LABEL、PUBLISHER_OR_ISSUER、NUMERIC_IDENTIFIER、PUBLICATION_SERIES、MAGAZINE、OTHER_BRAND などの外部意味判断は
LabelAuthorityEvidence で受け付け、信頼・独立性・対象適用性の検証後に AuthorityAssessment に返す。
明示的な非レーベルの意味が VERIFIED なら NONLABEL_VALUE で拒否する。意味が UNVERIFIED なら保留する。
raw 分類へ外部判断を上書きせず、構造的な診断と独立した意味証拠を両方残す。

## 8. 文字列比較と一意性

equality key は **NFC + 外周空白除去**。NFKC、大小文字、内部空白、句読点、中黒、略称、読み、区切りによる同値化は行わない。
raw display は出力候補として変更しない。

resource の表示集合では、同じ equality key の `ABC` / ` ABC ` や NFC の合成差も異なる raw display として MULTIPLE にする。
完全に同一の raw display の重複だけは一意と扱う。
Book と Series がそれぞれ単一なら equality key で比較するが、採用値は意味証拠と対応する Book の raw display に限る。
同じ raw display の複数 term から選択する際は安定順の代表候補を返し、comparison に他の全 term・出現・根拠を残す。

`book_candidate_count / series_candidate_count` は DISPLAY の異なる RDFTerm 数、
`book_occurrence_count / series_occurrence_count` は labels 内の全 DISPLAY 出現数。
`len(book_values) / len(series_values)` は異なる raw display 数を示す。

## 9. Book / Series 比較

| state | 内容 |
|---|---|
| UNAVAILABLE | discovery、Book、必要な Series、relation の取得・解決が不完全 |
| MULTIPLE | 複数 raw display または複数 Series 関係 |
| BOTH_AGREE | 双方の単一表示が厳格な equality key で一致 |
| BOTH_CONFLICT | 双方の単一表示が不一致 |
| BOOK_ONLY | Book に表示、完全な関連 Series に表示なし、または関係なし |
| SERIES_ONLY | Book に表示なし、関連 Series に表示あり。採用は無効 |
| NONE | 完全な必要範囲で非空の有効 display なし |

判定優先順は表の UNAVAILABLE → MULTIPLE → 双方比較 → 片側 → NONE。
未知 term、文脈の矛盾、取得完全性は独立した blockers にも残す。
集合一致と重なりを MULTIPLE の場合にも返す。集合一致で複数値を単一値へ変更しない。
NDL の `series_titles` の raw evidence と一致 key は観測のみで、独立した意味確認として数えない。

publisher は Book / 必要な各 Series / NDL の集合を比較する。複数主体・未知 term・欠損は保留する。
edition は明示値の矛盾を拒否し、片側の欠損を一致としない。
媒体は AcquisitionContext の確認済み値と authority を比較し、書名や一般的な material type から推測しない。
刊行時期は有効な ISO 日付の互換性で比較する。年・月だけの資料は同じ範囲の詳細日付と両立できるが、異なる年・月を同一視しない。

## 10. LabelAuthorityEvidence の入力契約

この型は外部で確認した証拠の受け皿であり、公式サイトの取得・本文解析・真正性確認を実施しない。
`source / locator / source_kind / checked_at` は監査用であり、HTTPS やホスト名から trust を生成しない。
`trusted=True` は、呼び出し元が確認済みの供給経路で渡したという明示的な契約である。
フィールド検証の成功だけでは実運用の真正性保証にならない。

採用には、VERIFIED、VERIFIED_LABEL、trusted、independence_verified、既知の origin_group、
正確な対象 Book ID / URI / 正規化 ISBN、publisher、確認済み editions / medium / publication_dates、
`target_scope_verified=True`、未確認事項なしをすべて要求する。
NDL / MADB の source_kind は独立根拠として採用しない。文字列の由来から独立性を推測しない。
同じ origin group の証拠の件数を独立した複数の確認として数える規則はない。

`editions=None` は未確認、`editions=()` は同 ISBN の公式書誌で版表示の不存在を確認済みという外部契約。
raw 側に版表示がある場合は欠損で一致させない。
媒体が MADB の構造化フィールドにない場合でも、同 Book・同 ISBN の公式書誌に対する
媒体を含む対象適用性の明示的な外部確認があれば評価できる。既知の媒体が相違する場合は拒否する。
これは M1032569 の同巻・紙版・同 ISBN の調査結果に合わせた規則で、未知の媒体を紙と推定する処理ではない。

authority の確認済みレーベル名と Book の raw display は原則完全一致を要求する。
別表記対応は `raw_label_values` に外部で確認した raw 値を明示した場合だけ評価し、API 内で名称を統合・置換しない。
relation が明示された階層・別表記・結合は初版では保留する。None を推測で関係解決済みに格上げしない。
信頼済み供給元は未解決の構造や適用条件を `unconfirmed` に記載する契約である。

全証拠と適用判定を結果に保持する。好都合な証拠だけを取り出さず、供給された証拠に矛盾・不適用・未確認があれば採用しない。
異なる巻、ISBN、版、出版主体、媒体、時期、未確認の由来は採用不可である。

## 11. Identity と取得完全性

MATCHED、安全な EXACT / STRONG が一意、採用対象自身に conflict なし、discovery 全体が COMPLETE、
truncated なし、発見済み候補の取得完全性・件数・ID / URI 整合、対象 Book の完全取得を要求する。
Book / Series の raw identifier・type・投影、CandidateSummary、RecordMatch の raw identity evidence が渡された snapshot と合うことも確認する。
直接 NDL URL による EXACT と ISBN discrepancy の共存は追加の Imprint 条件で拒否し、linkage algorithm 自体は変更しない。
他の非採用候補の独立した conflict は対象に転嫁しない。安全な複数照合候補と取得途中の一意性は保留する。
対象 Book 自身に明示的な conflict がある場合は、confidence が UNSAFE で安全な照合候補がなくても、その矛盾を理由に REJECT とする。

AcquisitionContext の初期値は NOT_REQUESTED。省略で取得完了を主張しない。
Series がないことを完全な Book で確認した場合は series / relations を NOT_RELATED とする。
関係がある場合は COMPLETE と全必要 snapshot を要求する。COMPLETE の宣言だけで未取得・partial / truncated を隠せない。
resources の状態は集約状態を補強し、不完全な raw snapshot の上書きには使えない。
request_id / acquired_at を raw RDF の観測事実として捏造しない。

`retrieval_scope="series_linkage"` の Agent / Holding 空配列は NOT_REQUESTED で、関係不存在の根拠にしない。
この取得範囲の bundle が partial / truncated なら採用不可。
full bundle が Agent / Holding だけで partial の場合は、呼び出し元が `book_series_scope=COMPLETE` を明示し、
実際の Book / 全必要 Series / relation が完全なときだけ対象の partial summary を許容する。
他候補の不完全な summary、truncated bundle はこの例外で許容しない。

現行 LinkageResult は bundle や snapshot の識別 token を持たない。
ID / URI / raw identity evidence の対応は確認するが、同一 ID の取得時点を暗号学的に証明する機能はない。
呼び出し元は同じ取得 snapshot で linkage と評価を生成する必要がある。

## 12. 採用判定

| decision | 規則 |
|---|---|
| ELIGIBLE | 全条件成立。BOTH_AGREE / BOOK_ONLY、Book の単一安全 display、意味確認と対象適用が成立 |
| HOLD | 取得不足、未知 term、複数候補・関係、意味確認・信頼・独立性・適用条件の不足、Series-only |
| REJECT | 対象自身の identity conflict、snapshot / provenance 不整合、明示的な文脈矛盾、版重複・確認済み非レーベル、Series conflict、不正 term / XML、意味証拠の矛盾・対象不一致 |
| SKIP | 既存 Imprint がある。または安全で完全な評価範囲に表示候補がなく、他の blocker がない |

既存 Imprint は None または空文字列だけ未設定とする。空白・改行・全角空白だけの値も保護する。
既存値の SKIP は最優先。その他は明確な違反を REJECT、残る不足を HOLD とし、全理由を返す。
不完全取得を NONE / SKIP に変換しない。XML 不正文字を削除・置換して候補を作らない。

M1032569 は、保存済み RDF / NDL / discovery と、出版社の同巻・同 ISBN の注記に基づく
明示的な信頼・適用範囲のテスト用証拠を渡した場合だけ ELIGIBLE。
同じ候補に証拠を渡さなければ HOLD。M1032568 の実測 EXACT も意味確認がなければ HOLD。
この正例は公式書誌を自動取得・検証した本番補完の成功を意味しない。

## 13. 実測 fixture と synthetic fixture

[imprint_measured.json](../tests/fixtures/madb/imprint_measured.json) は保存済み evidence の最新成功観測から、
評価に必要な predicate だけを縮約した 39 Book / 27 Series。raw binding の qualifier・subject・順序を保持する。
元ファイルの SHA-256、取得日時、request_id、出典・加工表示、縮約条件を記録した。
保存済み source との raw 値一致も試験する。

NDL の保存済み 11 書誌の選択フィールドと、M1032568 / M1032569 の実測 discovery を含む。
他の資料の discovery 成功、linkage 条件、AcquisitionContext の完了宣言は synthetic と明記した。
すべての authority trust / scope envelope は synthetic。M1032569 のレーベル・ISBN・媒体の根拠は
保存済み publisher-anemone の人による確認であり、その他の確認フィールドを今回新たに実測したとは扱わない。
未観測の RDF 型・言語・datatype、取得失敗、順序変更、Unicode、異版・別巻・独立性不足は synthetic fixture で試験する。

## 14. 検証結果と整形修正

[test_imprint_candidates.py](../tests/test_imprint_candidates.py) に新規 **235 件**。
全実測 Book の比較 state、正例・保留例・拒否例、未知 term と表示の共存、重複・raw 差・順序、
取得完全性、identity / snapshot / authority 条件、XML、入力不変、ネットワーク / ファイル I/O の禁止、
GenericMetadata 不変、既存 Series 補完の出力維持を検証した。

最終の実行結果と再現コマンドは [validation.md](validation.md) の Phase 2C-2B 記録に掲載する。
最終結果は専用単体 **235 passed**、全回帰 **1,612 passed / 13 skipped / 1 xfailed**。
新規の sdist 検証 1 件を含む packaging 3 件も通過し、Ruff check / format check、sdist → wheel → ZIP のビルドが成功した。
ビルド後に既存 packaging テストを実行し、実際の ZIP から内部評価 API を import できることを追加確認する。
通常の ZIP Talker 操作・既定 OFF・EXACT / STRONG の Series 補完は従来の統合試験を維持する。
新しい Imprint 書き込みの built-plugin integration は実施していない。

初回の全体 format check は既存 10 ファイルの整形で失敗した。
Ruff 0.16.8 による機械的な整形を適用し、9 Python ファイルの AST が同一であることと、
Phase 2A の仕様書の本文の非空白文字列・Python コード例の AST が同一であることを検証した。
mapping.py と既存テストの改行・行配置、および phase2_madb_spec.md のコード例の空白だけを修正した。
過去の観測値、判断、NDL mapping の規則、既存テストの意味は変更していない。
開始時の未コミットの Phase 2C-2A の 4 成果物は変更せず保持した。
MANIFEST.in に縮約 fixture の検証元となる保存済み evidence の収録を追加し、sdist 内で provenance を再検証できるようにした。
packaging テスト 1 件を追加し、sdist 内の評価モジュール・テスト・fixture・検証元が作業ファイルと一致することも検証する。

## 15. 未解決事項

真正性を保証する意味確認の供給元・更新・失効手順は未実装。
書誌ごとの媒体・版・時期・レーベル構造の確認は呼び出し元の責務で、既定ではすべて未確認。
publisher の役割付き表記、階層・別表記、移管・同名ブランド、Series-only の適用性は保守的に採用範囲外。
標本は意図的な 39 Book であり、MADB 全体の補完率や精度を推定しない。
parser で失われた Book の重複出現、取得原応答、query 間の snapshot 一貫性はこの pure API だけでは保証できない。

## 16. Phase 2C-2C の移行条件

推奨は **CONDITIONAL GO**。候補評価と安全な保留・拒否の内部基盤は利用できるが、本番の自動補完には次が必要。

1. 意味確認の信頼済み供給元、真正性確認、出典独立性、対象巻・ISBN・版・媒体・時期・構造の確認、更新・無効化手順を確立する。
2. `LinkedRecordEvidence(linkage, bundles, acquisition_context)` 相当の内部契約を設け、既存取得ループの同一 snapshot を Series / Imprint の評価で共有する。
3. 既存の公開 linkage API と Series 補完を維持し、取得状態の根拠・必要範囲・snapshot の識別方法を定める。
4. 実際の Imprint 書き込みと opt-in 設定は別フェーズで実装し、OFF / 既存値 / 同時 ON / cache / refresh / rate limit / fail-open を検証する。
5. CR / CIX writer で ComicInfo.xml の保存・再読込、ZIP loader、取得共有の要求数、適用条件の失効と拒否を統合試験する。

意味確認を継続供給できない場合、一般的な本番補完へ進まない。Series-only、汎用 metadata merge は有効化しない。
commit / merge / push / tag / GitHub Release は実行していない。
