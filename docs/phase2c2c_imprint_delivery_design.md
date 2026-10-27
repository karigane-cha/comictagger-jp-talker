# Phase 2C-2C-3E1：Imprint 提供方式と host 保存契約

2026-10-20。**第一候補は明示実行の読み取り専用診断コマンド（比較方式 B）**とする。
通常の Talker 取得に診断通信を加えず、Imprint / Notes / archive を変更しない。
将来の保存候補は host の保存直前契約を伴う確認付き限定補完（比較方式 C）。
現行 beta9 の設定や確認ダイアログだけでは成立しない。
工程 D と host 保存保証が未達のため、**Imprint 自動補完全体は NO-GO を維持**する。

この文書は詳細設計である。以下の新しい名前・コマンド・能力名・状態はすべて**提案**で、
既存 API や実装済み機能ではない。production code、公開設定、host、既存試験は変更していない。
依頼の「方式 A：診断」「方式 B：保存」の大分類と、末尾の比較方式 A～E を区別するため、
以降は「診断方式」「保存契約」と「比較方式 A～E」を使う。

## 1. 調査基準と E0 の固定条件

開始状態: `main`、HEAD `cbce602f07a3559b8299a8e55c2dfc9d13d29022`。
変更済み 9 / 未追跡 13 ファイルに工程 A～C・E0 の成果物がある。
導入済み ComicTagger `1.6.0b9`、comicinfoxml `0.5.1`、Python `3.12.14` を優先した。
根拠は [E0 報告](phase2c2c_host_imprint_boundary.md)、
[統合設計 §5～§7・§15・§16](phase2c2c_integration_design.md)、
[検証履歴](validation.md)、導入済みソースと実測テスト。

次の条件は E1 で緩和しない。

1. 最終 fetch に archive metadata、raw XML、保存設定、preview / save の目的は渡らない。
2. OVERLAY は取得側の非空 Imprint で上書きする。ADD_MISSING だけでは未読タグ、空白値、
   clear、後段変換を保護できない。auto_imprint は merge 後にも作用する。
3. GUI と CLI / 自動 worker の保存経路は異なる。GUI の None と旧フォーム値の復活も維持される。
4. CR / CIX は一つの `ComicInfo.xml` を使用する。外周空白は reader、CR / CRLF は XML parser で変わる。
5. writer が True でも不正 XML で再読込不能になり得る。
6. 候補選択中の詳細 fetch も最終取得 API を使う。E0 の調査 GO は保存安全性の GO ではない。

### 現在のコードを優先した設計上の補足

- 工程 C の `supplement_metadata()` はローカルな evidence を取得し、Series 用結果を使って
  GenericMetadata だけを返す。**取得済み evidence を後から取り出す host API はない**。
  共有 core が存在することと、通常 fetch の結果に evidence が公開されていることは別。
- §15 の「候補 API は補完しない」はメソッド単位の契約。GUI の候補選択が
  `fetch_comic_data()` を呼ばないという保証へ広げない。
- 初期設計 §6 の「Talker で imprint / Notes を変更」は将来の内部変換案で、
  archive の安全な保存方法としては未成立。E1 は保存側で条件付き delta を扱う案へ責務を分離する。
  第一段階の保存 delta は Imprint のみとし、Notes の追加は別途受入が必要な将来拡張とする。
  過去の案を削除せず §17 に理由を追記する。診断に Notes は使わない。

## 2. 現行 API の実在する能力

ソース位置は `.venv/Lib/site-packages/` 基準。

| 経路 | 実在する契約・利用者からの見え方 | 診断用途の判断 |
|---|---|---|
| `comictalker/comictalker.py:ComicTalker` | 公開メソッドは設定登録・解析、check_status、検索、fetch の 8 種。fetch は GenericMetadata、検索は ComicSeries 等 | 候補証拠 envelope、診断表示 callback、保存 veto / transaction callback はない |
| `search_for_series(callback=...)` | `(current, total)` の進捗 | raw 候補や archive ID の搬送に転用しない |
| `RLCallBack` | `callback(float, float)` と `interval` | rate limit 通知。callback identity / interval から保存先や目的を推定しない |
| `check_status()` | 設定・接続検査結果の `(message, bool)` | 書誌対象がない。MADB 候補診断の入口に転用しない |
| `about` / `attribution` | source の説明・リンク | 個別候補の動的診断画面ではない |
| `GenericMetadata.description` 等 | フォーム・詳細表示に使われ、保存対象にもなる | Notes と同様、診断用 payload を混ぜない。任意の追加属性も host 表示契約にならない |
| プラグイン `search_metadata()` | 独自 helper。host から既存 archive metadata は渡らない | 新しい host callback があると説明しない |
| `errors.report_error()` | エラーダイアログ・ログと `jpbooks/latest-error.txt` | NDL 失敗履歴を汚すため候補表示に使用しない。偽の TalkerError も発生させない |
| `comictaggerlib/log.py` | UTF-8 `ComicTagger.log`、起動時 rollover、backupCount=10、標準 stderr | 実在する補助出力先。既存設定・level に依存し、診断専用実行口は別に必要 |
| `TaggerWindow.setup_logger()` / `ApplicationLogWindow` | root logger から QTextEditLogger、`actionLogWindow` で表示。ログの保存先リンクもある | 閲覧可能。ただし structured report の検索・保存対象との対応・保存許可は提供しない |
| 独立コマンド | 現在 Imprint 診断用の module / command はない | 新規実装が必要。本体改変なしで既存 Python API を利用可能 |
| 専用診断 UI | 現行 Talker extension に登録口は見つからない | 新規 host 拡張または独立アプリが必要。未検証 hook を追加しない |

ログの root 既定は WARNING。プラグインの INFO は logger の設定次第で発行されない。
`verbose` の stream handler の level 変更だけで、あらゆる logger の INFO が見えるとは限らない。
診断が成功したという理由で WARNING / ERROR に偽装せず、明示コマンドの stdout を主出力にする。
GUI の `QTextEdit.append()` は rich text を解釈できるため、raw XML / HTML をそのまま表示しない。
test-only では JSON escape に加え `<`, `>`, `&` を可逆 escape して両出力先での保持を確認した。
ログの rollover・他の logger・利用者の削除があるため、ログを改ざん不能な監査台帳ともみなさない。

## 3. 診断方式の具体化

### 3.1 第一候補の入口

将来の仮称 module は `comictagger_jp_talker.imprint_diagnostics`。
使用形の例は `python -m comictagger_jp_talker.imprint_diagnostics --ndl-id ID --allow-network`。
**現在このコマンドは存在しない**。設計上の初期仕様は次のとおり。

- archive path を受け取らず、NDL ID 一件を対象にする。ISBN だけで先頭の NDL 書誌を選ばない。
  固定の既存 endpoint と ID 検証を使い、任意 URL、公式サイトの新規 scraping、画像取得を追加しない。
- `--allow-network` なしなら source を生成せず `BLOCKED / NETWORK_NOT_AUTHORIZED`。
  「cache だけを見る」と称して既存 source を呼ばない。現在の source は cache miss で通信する。
- 許可された実行は NDL の `get(..., summary_mode="none")` で書誌を取得し、
  既存 MADBSource と `acquire_linked_record_evidence(..., scope="series_linkage")` を一度呼ぶ。
  NDL summary fetch は診断に不要。NDL の session / cache、MADB の context manager を確実に閉じる。
- 既存 limiter / timeout / row・byte・relation cap、cache namespace / key / TTL、失敗境界を維持。
  自動 retry、full scope への追加取得、失敗 resource の診断目的だけの再取得はしない。
  明示 refresh は別の実行として ID を変え、利用者が指定したときだけ既存 refresh を使う。
- cache は読み書きし得るが、metadata / Notes / archive は読み書きしない。
  この「読み取り専用」は保存先に関する契約で、通信や cache 書込がゼロという意味ではない。
- stdout は人向け text または版付き JSON、stderr は実行失敗・進捗。JSON 内には
  `archive_state=not_supplied`, `writes_performed=false`, `authority_state=not_supplied` を必ず含める。
  exit 0 は「診断報告が生成された」だけ。候補採用や保存成功を意味しない。
  提案 exit code は 0=完全な診断実行、2=入力 / 許可不足、3=取得不完全、4=内部 / 出力失敗。
  authority 不足による HOLD / REJECT は診断自体のエラーとは区別する。
- 第一段階は stdout のみとする。ファイル出力・offline snapshot 読込を後で作る場合は
  schema / サイズ・入力検証と出力先を別途設計し、利用者 archive への上書きを認めない。
  JSON を authority package や保存許可 token として再利用しない。

別の純粋関数案 `describe_imprint_evidence(evidence)` は source / callback / metadata を受け取らず、
取得済み `LinkedRecordEvidence` だけを入力にして通信ゼロで診断内容を返す。
この関数も未実装。提供者が所有する同一実行の evidence を再利用し、run_id を引き継ぐ。
既存 Series fetch の evidence を取り出すために Talker 属性や global registry を追加しない。
現在の通常入口に reuse hook がないため、独立実行は独立取得になる。cache hit は通信を減らせるが、
**別実行の cache 読取を「同じ snapshot の共有」とは表現しない**。

### 3.2 診断の計算と raw 値の表示

`BookAcquisitionContext.included_in_linkage=True` の各 Book について、自身の bundle と context を
`extract_imprint_evidence()` → `classify_imprint_terms()` → `compare_imprint_candidates()` →
`evaluate_imprint_eligibility()` へ渡す。NDL は `ndl_input.to_record()` の独立コピーを使う。
全件の `linkage` を渡し、候補を一件に絞り込んだ偽の MATCHED は作らない。
ID / URI 不一致で除外された bundle は `books` の未採用根拠として表示し、採用評価に混ぜない。
bundle がない失敗にも架空の空 bundle や「候補なし」の断定を作らない。

第一段階の `authority_evidence` は常に空 tuple。純粋 evaluator の `existing_imprint=None` は
「保存先は欠損」という実測ではなく、意味評価を行うための未供給の入力として限定する。
外側に `target_known=false / existing_value_assessed=false` を必ず保持する。
authority が未供給なら VERIFIED / ELIGIBLE の表示を生成しない。
HOLD と REJECT は既存 evaluator の理由をそのまま残し、すべてを HOLD に丸めない。

| 診断項目 | 現行 evidence の出典・表示契約 |
|---|---|
| run / 版 | `acquisition_context.run_id`, started_at / finished_at、scope、プラグイン版、identity `phase2b2-v1`、evaluator `phase2c2b-v1`。取得時点の同時性は主張しない |
| NDL | `ndl_input.id / url / isbns / volumes / publishers / editions / issued / dates / series_titles`。raw ISBN と照合用正規化値を別欄にする |
| MADB Book | discovery の ID / URI、`books` の取得・除外状態、accepted bundle の ID / URI。複数候補を省略しない |
| identity | `linkage.status`, matches の confidence / reasons / conflicts、候補数、warnings / error / truncated。一意性・不整合は別欄 |
| raw brand | `ImprintCandidate.term` の kind / value / language / datatype、origin=Book / Series、related_to_book。IRI・bnode も文字列レーベルに変換しない |
| 対応関係 | evidence の record ID / URI、predicate、statements、statement_indices / label_indices。parser が除去した重複は復元したと称しない |
| 完全性 | discovery と Book 個別の context、resources、relations、Agent / Holding 未要求、trace の失敗・cap・cache。COMPLETE は要求範囲だけ |
| run 全体の異常 | `LinkedAcquisitionContext.issues` を順序・内容ごと保持。意味評価が扱わない issues も診断から落とさず、将来の適用 gate では未解決なら停止 |
| 分類・比較 | term role / semantic_kind / reasons、Book / Series の display と一致・競合、publisher / edition 比較、全 blockers |
| 意味評価 | state / reasons / authority assessments。raw brand の存在や一致を独立した意味確認へ昇格しない |
| authority | `not_supplied / UNVERIFIED`、供給・期限・失効を未評価と表示。fixture の trusted=True を使わない |
| 観測時刻 | event.observed_at はローカル観測。origin_fetched_at / cache_stored_at / response_sha256 が None なら unknown のまま。サーバーデータ更新時点も不明 |
| 保存先・操作 | `archive_state=not_supplied`, `operation=READ_ONLY`, `apply_allowed=false`, `writes_performed=false`。診断成功と保存成功を区別 |

raw は無加工の値と可逆 escape 表示を併記できる構造とし、HTML / terminal 制御を解釈させない。
表示の長さ制限では `display_truncated` と元の長さを明示し、取得 TRUNCATED と混同しない。
完全な報告を出せなかった場合は失敗を返し、切り詰めを完全な監査資料として保存しない。
新規ログ出力を通常 fetch に追加する案は第一段階から除外する。

## 4. 保存契約の責務と概念モデル

以下は **将来 host 拡張の仕様候補**。現行 ComicTalker / ComicArchive にこの API はない。
frozen な DTO と tuple、版付きの境界を想定する。source / session / mutable metadata /
callback / OS handle を証拠 DTO に含めない。実ファイル handle と排他権は host が管理する。

| 概念 DTO / 機能名（仮称） | 所有者・責務 |
|---|---|
| `CandidateReport` / `provide_candidates()` | プラグイン。取得済み evidence と意味評価、authority 供給状態を返す。ファイルに触れず delta の許可権を持たない |
| `SaveIntent` | host。operation_id、archive_token、目的 PREVIEW / DIAGNOSTIC / SAVE、metadata revision、書込計画を束ねる |
| `ArchiveObservation` / `inspect_target()` | host。実ファイル同一性、raw XML と全 Imprint 状態、読取成否、観測 revision を取得 |
| `AuthoritySupply` | 工程 D の信頼済み adapter。署名・出典独立性・対象・有効性の全結果。plugin が ready と宣言するだけでは足りない |
| `ApplyAssessment` / `assess_apply()` | plugin の意味評価と host の保存評価を別々に保持。host が全 gate の AND を検査 |
| `ReviewReceipt` | host の利用者確認。archive / metadata / settings / evidence / authority / 値 / writer 版の digest と期限に結び付く一回限りの許可 |
| `PreparedSave` / `apply_if_absent()` | host。変換済み最終 metadata を固定し、書込直前の再読取・排他下で欠損を再確認。delta だけを適用 |
| `SaveVerification` / `commit_and_verify()` | host。既存 writer、stage / commit / 同一・相互 reader 検証、監査・結果通知。成功を plugin に丸投げしない |

この名前を Python の実在メソッドとして introspection したり、`hasattr()` だけで信頼したりしない。
候補内容・raw の変化、他 archive への切替、authority 更新・失効、設定変更、metadata 編集で
ReviewReceipt を失効させる。単一の「直近候補」「直近 archive」を Talker 属性に保存しない。
取消・期限切れ・世代違いの callback は無効とし、同一候補でも別 archive の receipt を流用しない。

digest の入力は schema / policy version、全 raw term と出現位置、対象・設定・最終 metadata の
版付き canonical encoding とする仕様が別途必要。None / 空文字列、tuple 順序、数値 / 文字列、
Unicode の code point を区別し、NFKC 等で正規化しない。run_id は相関 ID であり内容 hash ではない。
parsed snapshot の digest を原 HTTP 応答の hash や署名の代替としない。
原応答の hash / 時刻がない場合は null と理由を保持し、保存 policy が要求する証拠を満たせなければ停止する。
この canonical encoding は今回実装せず、H1 / H2 の相互運用試験で確定する。

## 5. 保存先の同一性・raw 既存値

`ArchiveObservation` は最低限、次のデータを区別して持つ。

- host が発行する archive_token、operation_id、正規化済み表示パス、実ファイルの volume / file ID 等、
  size / mtime、観測時の全 archive digest、変更世代。パス・ISBN・NDL ID だけでは同一 archive としない。
  同じ書誌を持つ二つの CBZ は別対象。再リンク、置換、rename、同じ内容の別ファイルも識別する。
- read tags / write tags、実 writer / reader plugin の版と設定、保存順。
  CR / CIX は `physical_target=ComicInfo.xml` に集約する。未対応形式・不明 writer は BLOCKED。
- XML の存在 `present / absent / unknown` と読取 `not_read / success / failed` を分離。
  ZIP 列挙失敗を「要素なし」にしない。暗号化、破損、重複・紛らわしい member 名、同名 XML の複数 entry、
  想定外 namespace / root / Imprint 階層は曖昧性として停止する。
- 原 XML bytes の保護された参照と hash、encoding、parser の整形式結果、要素数、
  raw element 内容と解釈後 text。解析前 bytes を保持し、CR 正規化や entity 展開後 text と混同しない。
  DTD / 外部 entity は受理せず外部通信しない。サイズ超過・解析不能・対応付け不能も停止する。
- Imprint の観測状態 `absent / empty / whitespace / value / ambiguous / invalid / unknown`。
  `None` だけでまとめない。空白は XML character reference の解釈後も調べるが、raw 自体は変更しない。
  children / attributes / 複数 Imprint 等を勝手に単純な空欄へ変換しない。

**初期の限定契約では、正常に検査できた XML に Imprint 要素がない場合、または正常な archive 列挙で
ComicInfo.xml 自体がない場合だけ「適用可能な欠損」とする。**
`<Imprint/>` / 空 text も構造上存在する既存値として停止する保守的な仕様を選ぶ。
ASCII / 全角空白だけの値は必ず停止。既存値が候補と同じでも保存のやり直しはしない。
これは evaluator の None / `""` 契約の変更ではなく、host の raw 保護をより狭くする追加 gate。
将来 empty を許可する場合は、別の契約版と受入レビューを要する。

読取が成功しても通常 reader が None を返しただけではこの条件を満たさない。
利用者が UI で空白値を消した場合も、同じ処理で補完へ進まず、明示編集と新たな保存判定に分離する。
raw 値が存在する場合、限定補完を停止して archive を書かない。通常の別の保存操作まで
プラグインが安全にしたと宣言せず、host は停止理由と通常編集との違いを表示する。

## 6. 適用順序・確認・原子性

### 6.1 保存前の gate

提案する初期範囲はローカル CBZ、一つの物理 XML target、一つの明示 writer（CR または CIX）。
read 検証は同一 reader と相互 reader の両方。GUI / CLI / worker が同じ host 保存サービスを使うこと。

1. SAVE 目的と対応 capability を確認。PREVIEW / DIAGNOSTIC は READ_ONLY のまま。
2. host が raw を検査し、未読・不正・既存値あり・不明対象なら BLOCKED。
3. host の現在の通常処理を実行して保存予定 metadata を構築する。
   GUI のフォーム変換、CLI の明示 metadata、import transform、merge、Notes の整理をすべて先に完了する。
   初期契約では clear と auto_imprint は OFF を要求し、ON を黙って変更しない。
   import transform は対応版で検証済みのものだけを許し、その結果を固定する。
4. 最終 metadata の Imprint が None / `""` 以外なら停止。raw の欠損とこの条件を両方要求する。
   Series と他フィールドは通常処理で確定した値を基準とし、Imprint delta で変えない。
5. 取得の完全性、一意な安全な identity、run の未解決 issues なし、D の authority ready、
   evaluator の ELIGIBLE を要求する。どれも利用者確認で上書きしない。
6. raw 候補は XML 1.0 の有効な単一文字列で、両 reader の往復が一致するものだけ。
   初期 profile では外周空白、CR / LF / TAB、C0 / C1 制御文字を拒否する。
   E0 で LF / TAB は往復したが、初期対応を通常の単一行へ狭めるための追加制限である。
   非 BMP・内部空白・XML 特殊文字は対応試験の範囲で許す。trim / 改行置換で通さない。
7. host が確認画面 / CLI の明示確認に、実保存先、raw 欠損の根拠、候補の escape 表示、
   authority・取得状態・設定・予定変更を示す。一般的な Save Tags 確認を receipt の代わりにしない。

初期版は必ず REVIEW_REQUIRED を経由する。無人 worker は確認できなければ待機 / BLOCKED。
将来の自動適用は別能力・別 opt-in・別受入を必要とし、batch の包括承認を一件の確認とみなさない。
確認後に GUI フォームへ戻して再度変換しない。編集されたら plan / receipt を無効化する。

### 6.2 保存直前から検証まで

確認中にファイルを長時間ロックせず、commit 時に host が対象を開き直し、同一性・世代・全 hash・raw
既存値・設定・metadata revision・evidence 対応・authority の有効期間と失効情報を再検証する。
確認時と異なれば停止し、新しい確認を要求する。適用時刻不明や期限境界も fail-closed。
MADB cache が warm でも authority の有効性確認を省略しない。

理想の保存契約は、検査 → 条件付き適用 → commit を保護する排他または等価な transaction。
host が元ファイルに対する排他・置換防止の権利を取得し、stage 用コピーへ**既存 writer**を実行する。
stage の全 write を完了・検証してから、安全な commit を行い、対象を再読込して再検証する。
プラグイン独自の ComicInfo.xml writer は不要であり、作らない。

ただし **現在の host はこの保証を提供していない**。
`comicapi/archivers/zip.py:write_file()` は ZIP を append モードで開き、既存 member を remove / repack して
write する。`ComicArchive.write_tags()` の公開引数は metadata と tag_id で、expected revision、
排他 token、compare-and-swap 条件はない。複数の write をまとめた rollback 契約もない。
事前・事後 hash は検出手段であり、検査後から書込までの TOCTOU をなくさない。
atomic rename だけでも「検査した元ファイルがまだ対象である」という比較条件は保証できない。

Windows の file sharing、置換時の handle / lock、外部プロセスの編集、network filesystem、
クラッシュ、電源断まで含む commit 保証は未実装・未検証。
host 側で対応する platform / filesystem を限定し、実証できなければ
`CONCURRENT_WRITE_NOT_EXCLUDED` として CONDITIONAL_APPLY を禁止する。
プラグイン内 mutex は外部アプリを止めず、hash 二回一致もその間の状態を保証しない。

### 6.3 複数 write・失敗と監査

- 初期版は CR と CIX の**両方への write を同時に選択した保存計画を停止**する。
  同じ物理 XML を二度更新するためである。どちらか一つを明示選択させ、両 reader で検証する。
  host の通常 write 順をプラグインが黙って削除・変更しない。
- 将来複数形式を許す場合は物理 target ごとに plan を作り、全 write を stage 上で完了させる。
  最後の writer 後に全結果を検証し、途中失敗なら commit しない。
  一つ成功した後に原ファイルへ書いた別 writer が失敗する現在の挙動を、原子的成功とは呼ばない。
- writer False / 例外 / True でも不正 XML / 要素数不正 / reader 不一致なら
  `FAILED_PRECOMMIT`。stage は診断用に隔離できるが原本へ自動 retry しない。
- commit 後の読取不能・値不一致は `FAILED_POSTCOMMIT` または `INDETERMINATE`。
  原本不変・復元済みと虚偽表示しない。後続 write を停止し、観測した hash・差分・復旧先を通知する。
  自動 rollback も別の更新を上書きし得るため、排他と復元条件を実証できない限り禁止。
- 検証は fresh archive / reader で行い、metadata cache の値を使わない。
  XML の整形式、Imprint の一意性、raw 候補との decoded text 一致、両 reader の完全一致、
  他 metadata の予定値との一致、対象外 ZIP member の bytes / comment 保持を確認する。
  XML 全体の bytes は通常 writer の再整形で変わり得るため、raw 証拠の保持と XML 全 bytes 不変を混同しない。
- 成功通知は commit と再読込・監査完了後のみ `VERIFIED_SAVE`。
  writer True、意味 ELIGIBLE、利用者の承認だけでは成功を通知しない。
- 監査は host 所有で operation / archive token、各 digest、判定版、authority 供給版・期限・失効版、
  確認者 / 時刻、全 gate 理由、writer 戻り値・例外、期待値 / 実値、stage / commit 結果を記録する。
  raw と秘密・パスを混在させず、参照先・アクセス権・保存期間を定める。監査の事前確保失敗は停止、
  commit 後の監査失敗は成功を偽らず `AUDIT_INCOMPLETE`。普通のログで代用しない。

## 7. 状態・理由を統合しない結果モデル

外側の `DeliveryAssessment`（仮称）に独立した軸を持たせる。
既存 enum、identity、Imprint evaluator の理由や判定を変更しない。

| 軸 | 内容 |
|---|---|
| acquisition | 現行 context / trace と issues。範囲・不完全性・失敗の事実 |
| semantics | 現行 classification / comparison / eligibility。意味確認の状態 |
| authority_supply | not_supplied / ready / expired / revoked / conflicted / unavailable と D の根拠 |
| target | not_supplied / not_read / read_failed / observed / changed と raw 状態 |
| purpose | PREVIEW / DIAGNOSTIC / SAVE / UNKNOWN。現行 fetch は UNKNOWN |
| delivery | READ_ONLY / REVIEW_REQUIRED / CONDITIONAL_APPLY / BLOCKED |
| operation_result | NOT_STARTED / CANCELLED / FAILED_PRECOMMIT / FAILED_POSTCOMMIT / INDETERMINATE / VERIFIED_SAVE / AUDIT_INCOMPLETE |
| reasons | `(stage, code, target_or_evidence_ref, detail)` の tuple。最初の理由だけに丸めず必要な停止理由を保持 |

READ_ONLY は表示できるという意味で、保存 gate が満たされたという意味ではない。
診断では delivery=READ_ONLY と `apply_allowed=false` / `apply_blockers` を併記する。
SAVE 要求なら不足に応じて BLOCKED。REVIEW_REQUIRED は確認以外の gate が満たされた状態だけ、
CONDITIONAL_APPLY は確認後の再検証と排他が成立した操作状態だけとする。
ELIGIBLE から自動的に CONDITIONAL_APPLY へ遷移させない。

| 状況 | 停止段階 / 提案 code | 表示・保存 |
|---|---|---|
| raw 候補あり、authority なし | authority / AUTHORITY_NOT_SUPPLIED | READ_ONLY、UNVERIFIED。SAVE は BLOCKED |
| authority ready + ELIGIBLE、保存先不明 | target / TARGET_NOT_SUPPLIED | 診断可、SAVE は BLOCKED |
| 保存先が未読 / 読取失敗 | target / TARGET_NOT_READ / RAW_READ_FAILED | 欠損と扱わず BLOCKED |
| raw 空白・空要素・通常の既存値あり | target / EXISTING_RAW_IMPRINT | 値が候補と同じでも BLOCKED |
| identity conflict / 複数候補 / context issues | identity・acquisition / 現行理由 + RUN_ISSUES_UNRESOLVED | 全根拠を表示、採用しない |
| XML に使用できない候補 | value / XML_INVALID | 現行 REJECT を保持し BLOCKED |
| XML 有効だが reader で変わる | value / ROUNDTRIP_UNSAFE | 意味評価を変えず保存を BLOCKED |
| preview / 目的不明 | intent / PREVIEW_ONLY / PURPOSE_UNKNOWN | 通常 fetch で適用を開始しない |
| ファイル・設定・metadata が変化 | commit / TARGET_CHANGED / PLAN_CHANGED | receipt 失効、再確認 |
| authority 更新・期限切れ・失効 | authority / AUTHORITY_REEVALUATION_REQUIRED | 再評価前の保存は禁止 |
| writer True でも reader 不一致 | verify / READBACK_MISMATCH | 保存成功にしない |
| 取消・古い callback | intent / CANCELLED / STALE_OPERATION | 保存なし。取得済み cache の消去までは保証しない |

## 8. プレビュー・繰返し・並行処理

`IssueSelectionWindow._fetch()` (`issueselectionwindow.py:178`) は issue / year / month / cover / title の
どれかが不足すると `fetch_comic_data(issue_id, on_rate_limit)` を呼ぶ。
今回の関数単位実測では、返った詳細を `issue_list` へ戻さず同じ行の再取得で再度呼ばれた。
すべて揃った候補は呼ばない。最終 `TaggerWindow.QueryThread.run()` は ID・series ID・巻・callback だけを渡す。
最終経路は引数が多い場合があるが、CLI / 自動 worker は issue ID だけでも保存へ進む。
引数の個数、callback interval、呼出元 stack から目的を推定する方式は禁止する。

- 現在の Series 条件は ON かつ変換後 Series が空白 / 欠損の場合だけ取得。
  OFF なら MADB は増えない。通常 NDL はタイトルから Series が作られるため欠損例は主に synthetic 試験。
  E1 はこの条件・出力・通信数を変更しない。診断のために OFF を無視しない。
- 仮に診断を通常 fetch に追加すれば、プレビューだけで discovery / Book / Series の通信が増える。
  完全 cache hit は通信を減らすが、失効・refresh・不完全結果・破損は再取得を生じ得る。
  `fetch_comic_data()` の呼出回数と HTTP 回数を同一視しない。
- 取消は完了した通信や cache 更新を巻き戻さない。現行 fetch には診断専用 cancellation token もない。
  新しい診断 command は操作単位に終了できるが、割込み時に処理済み cache を未処理と称さない。
- 二つの archive が同じ NDL ID を持つ場合でも同じ保存対象ではない。同じ Talker instance は
  QueryThread / AutoTagThread 等へ渡される。順序を保証する global state や「最後の callback」で紐付けない。
- 将来の host は per-operation ID / archive token / generation を持ち、古い・取消済み・別対象の
  callback を破棄する。source / SQLite 接続を無条件に複数 worker で共有しない。
  pure な immutable evidence の再利用と、mutable な接続の同時使用は別の契約。
- authority はプレビュー時の評価を保存許可に使わず、確認時・保存直前に再評価。
  取得原時刻不明や D の有効性条件が未確定なら停止し、「今 cache を読んだ」ことで最新性を作らない。

第一候補の独立診断は archive を知らず保存せず、通常 GUI の preview に接続しないため、
これらの保存先混同を初期実装から切り離せる。

## 9. host 変更箇所と互換性

| 変更候補（将来のみ） | 必要な内容 |
|---|---|
| `comictalker` の任意能力契約 | 版付き候補レポートと operation purpose。既存 fetch の引数・戻り値は維持し、旧 plugin を壊さない |
| `md.prepare_metadata` 周辺 | 通常変換の完了点と immutable な保存計画の生成。意味評価の結果を汎用 overlay に混ぜない |
| `TaggerWindow.apply_query_metadata / write_tags` | 保存直前サービスへ routing、フォーム最終変換後の revision 固定、確認後再編集の失効 |
| `CLI.save / write_tags` | 同じサービス、dry-run と確認不能の扱い、通常 CLI 成功と候補保存成功の区別 |
| `AutoTagThread`, `tag.identify_comic`, `AutoTagMatchWindow.save_match` | 対象 token の伝搬、確認・取消・期限・各 archive の結果通知 |
| `ComicArchive` と archiver 境界 | raw 読取・物理 target 集約・排他・stage / commit・fresh reader 検証・失敗監査 |
| 診断 / 確認 UI | plain text / escaped raw、書誌と保存先の別表示、capability 不足時の無効化 |

候補能力名の例は `candidate_report_v1`, `raw_target_observation_v1`,
`conditional_imprint_save_v1`, `verified_commit_v1`。
host の protocol version と writer / reader / platform の対応 profile を検証し、
能力文字列の自己申告だけでなく統合試験済みの組合せを要求する。
欠落・未知版・対応外 filesystem・監査不能なら fail-closed、通常 fetch / Series は従来どおり。
beta9 は保存能力なしとして判定し、Imprint を GenericMetadata に入れる fallback は作らない。

既存プラグイン ZIP は host が import する Python package であり、
新しい console command を ComicTagger.exe に登録する仕組みではない。
独立診断は Python 環境へインストールした wheel / module を第一配布対象とし、
frozen exe 利用者向けの別配布・同梱 interpreter は未設計として扱う。
現行 beta9 と共存できることと、exe 内から直接起動できることは別の受入条件。
今回は package `0.3.0` と既存配布物を変更しない。

## 10. 比較方式 A～E の選定

| 評価軸 | A: 現行 Talker API の診断のみ | B: 明示診断コマンド | C: host の保存直前確認 | D: host API 拡張＋限定自動補完 | E: 自動補完を実装しない |
|---|---|---|---|---|---|
| 既存値保護 | 非書込なら可。ただし診断取得・表示入口がない | archive を扱わず保護 | raw 検査・欠損 gate・排他が必要 | C と同じ。確認省略でも条件を緩和しない | 本機能由来の変更なし |
| raw 保持 | logger なら escape 可能、metadata 流用不可 | JSON / text に raw と escape を分離 | profile 外を停止 | 同左 | 新規保存なし |
| authority | 未供給の表示は可、供給機構はない | UNVERIFIED の診断は D 完了前に可能 | ready と ELIGIBLE が必須 | 同左＋無人処理での期限 / 失効対応 | D と独立 |
| host 改変 | 出力手段は既存、診断専用 UI / callback はなし | 不要 | 必要。既存の確認ダイアログでは不足 | 必要、能力検出と監査も追加 | 不要 |
| beta9 配布 | plugin は共存可、完全な診断機能としては未対応 | Python module として共存。exe 内起動は不可 | beta9 は BLOCKED | beta9 は BLOCKED | 現状維持 |
| GUI / CLI / worker | logs 閲覧のみ。候補の専用表示なし | 独立 CLI。GUI / worker から自動起動しない | 全保存経路の統合が必要、worker は確認待ち | 全経路共通契約が必要 | 現行機能のみ |
| preview | fetch 内実装なら意図しない実行 | 独立実行なので影響なし | 明示 purpose / target token が必要 | 同左 | 既存挙動を維持 |
| 通信 / cache | 通常取得の通信増禁止が入口を制約 | 明示許可、既存上限・cache を使用 | 既存 evidence 再利用、期限時再評価 | 同左。大量処理でも制限維持 | 追加なし |
| 開発・保守 | logger は低いが入口不足は解消しない | 小～中。renderer・CLI・配布と検証 | 高い。UI・transaction・復旧・全経路 | 最も高い。無人監査・競合・権限 | 最小 |
| 実用性 | 利用者が診断を開始できず限定的 | 選んだ NDL 書誌の調査・理由確認に有用 | 安全契約成立後は欠損だけを人手確認 | 成立後は batch に有用 | 手動作業が残る |
| 決定的な阻害条件 | 通常 API に独立入口・evidence 出力なし | 新規実装と実行配布が必要。意味確認済み表示は不可 | authority と原子的保存契約が未達 | C の条件＋自動処理受入が未達 | 機能追加を望む利便性を満たさない |

点数では阻害条件を相殺しない。結論は次のとおり。

- **A: NO-GO（現行 Talker API だけで独立した候補診断機能を提供する案）**。
  ログという輸送・閲覧手段は GO だが、実行入口を追加せず全診断を実現できるという意味ではない。
- **B: CONDITIONAL GO、第一候補**。明示通信許可、非書込、authority 未供給表示、版付き出力、
  cache / 失敗の正確な記録、既存 Series 回帰と配布試験を受入条件とする。D 完了は診断の前提にしない。
- **C: 詳細設計・host 側の feasibility 試験は CONDITIONAL GO、現行環境への補完実装は NO-GO**。
  原子的な欠損時適用と D の成立を確認してから限定実装をレビューする。将来の拡張第一候補。
- **D: 自動補完の実装は NO-GO**。C の保存契約と D の authority を満たした後にも、
  無人処理・明示 opt-in・監査・復旧の受入が必要。
- **E: GO、現在の production 方針**。B の診断を別途作りながら自動保存を見送ることと両立する。

## 11. 工程 D との独立した条件

authority の供給・真正性・独立性・対象適合・期限・失効・監査は一つも E1 で解消していない。
`trusted=True`、HTTPS、単一 brand、Book / Series / NDL 一致、synthetic authority は trust の代替ではない。
報告書には raw 候補を「レーベル確定値」と呼ばず、未供給の意味評価は UNVERIFIED と表示する。
診断は正しい不足の表示だけで有用であり、確認者が手動で VERIFIED を押す機能は作らない。
将来 D が成立しても、保存先・目的・排他・往復・監査の gate が不成立なら F を解禁しない。
逆に host 保存が安全でも D が未成立なら保存しない。Notes やログへの表示でこの分離を迂回しない。

## 12. 試験、未解決事項、実機確認

### E1 の test-only 実測

[test_imprint_delivery_contract.py](../tests/test_imprint_delivery_contract.py) の 6 件:

- 導入済み ComicTalker の公開メソッドと fetch / callback 引数を確認。診断・保存先・目的の口はない。
- native source を HTTP mock で取得した cold / warm evidence をそのまま純粋 evaluator へ渡す。
  取得は cold の 3 要求だけで評価による追加通信は 0。metadata 全体・二つの synthetic CBZ の bytes は不変。
  authority tuple は空、ELIGIBLE にならず SEMANTIC_UNVERIFIED を保持。
  warm の原取得時刻と bundle 共通時刻が不明なままなのも確認。
- 実 `IssueSelectionWindow._fetch()` を周辺 widget の test double から呼ぶ。
  同じ Talker・同じ候補・二つの呼出側で各二回呼び、未完備なら計 4 fetch、完備なら 0。
  callback は各 view のものでも archive / purpose は渡らない。
  実 QueryThread.run() の同期呼出しでも archive は渡らず、CBZ に書かない。
- 実 host の file handler と ApplicationLogWindow に escaped synthetic JSON を送り、
  raw を可逆に復元できることを確認。これは診断機能の製品実装ではない。

通常試験は外部 HTTP 禁止。上記の取得・書誌はすべて synthetic。
GUI は関数単位 / ログ widget の確認で、検索クリック・取消競合・非同期並行実行・
Windows exe 全体を実証したとは記録しない。
E0 の 592 件は変更せず再利用する。通常値と損失値、writer True の失敗、同一 XML、
未読タグ・空白値の反例は E0 により固定する。

### 次に必要な契約試験

| 試験 | 受入条件 / 現時点 |
|---|---|
| 明示診断の非変更性 | 完全 / partial / failure / 出力失敗で metadata・Notes・archive 不変、通常 fetch / OFF / preview 追加通信 0。command 未実装なので今は計画 |
| 全候補・raw 表示 | multi-candidate、URI / bnode、language / datatype、XML / terminal 制御、issues、表示 cap を隠さない |
| 対象 gate | not_supplied / not_read / failed / unknown / duplicate XML / empty / whitespace を BLOCKED。gate 自体は未実装 |
| 往復 gate | E0 の通常値と損失値を流用し、非対応を変更せず拒否。True + malformed も失敗 |
| 複数 archive / callback | 同じ NDL ID、結果逆順、取消、設定変更、古い generation で別対象に適用しない。現在は引数不足を実証しただけ |
| commit 競合 | 確認後・hash 後・stage 後・rename 前の別プロセス更新、path 差替え、同内容別 file ID、lock 取得失敗 |
| transaction / 復旧 | writer 中断・二つ目の write 失敗・disk full・commit 後読取失敗・監査失敗。原本不変か不確定かを実測 |
| authority lifecycle | 確認後の期限切れ・失効・供給版変更、cache hit、時計不明。D の実供給物が必要 |
| 全 host 経路 | GUI のフォーム再編集、CLI の明示 metadata / dry-run、worker 確認不能、曖昧候補保存で同じ契約 |
| 旧 host・配布 | beta9 で保存能力不足を表示し Imprint なし、従来 Series と loader 維持。独立 command の wheel 実行、exe との境界 |

未解決事項は、B の CLI / renderer / 配布の未実装、D の供給、host の protocol と upstream 採用、
Windows / filesystem ごとの排他・commit 保証、監査の保存責任、全経路の実機操作である。
hash、利用者の確認、全テスト合格だけで将来の原子性を証明したとはしない。

Windows exe の追加手動試験は E0 手順に加え、隔離 config と synthetic CBZ で行う。
ログ画面の実メニューと保存先・level・escape 表示を確認し、同じ issue の選択を繰り返して
詳細 fetch と最終 fetch を区別して記録する。二つの CBZ、選択取消、再選択、auto-tag と通常検索を
交互に実行し、操作の順序と対象を記録する。現在は診断ボタンや安全保存能力がないことも確認対象。
将来 host 試作後は上表の競合・拒否・再確認・検証失敗表示を追加する。
通常テストで外部通信はせず、実通信を要する実機試験は別の明示的な調査として扱う。

## 13. 実装工程と開始条件

| 工程 | 依存と範囲 | 受入条件・判断 |
|---|---|---|
| R1: 純粋診断 report | A～C の immutable evidence と現行 evaluator | **CONDITIONAL GO**。非書込、authority 空、全候補と issues / raw / unknown 時刻、既存値未評価表示、serializable な版付き report |
| R2: 明示診断 command | R1 | **CONDITIONAL GO**。NDL ID 一件、通信許可、固定 endpoint、既存制限、close・中断・出力失敗、cache の実数、通常経路非接続 |
| R3: 診断配布・実用性 | R2 | **CONDITIONAL GO**。wheel / module 実行、beta9 との共存、表示・ログ・日本語 escape、exe 利用者向け制限の説明、既存 suite / loader の回帰 |
| H1: host 能力・raw 観測試作 | E0 / E1、本体側の別の実装承認 | **CONDITIONAL GO**。read-only の target 識別と全 raw 状態、未知版 fail-closed、同一 XML、各経路の operation token |
| H2: transaction と検証の実証 | H1、対応 OS / filesystem の確定 | **CONDITIONAL GO（実験に限る）**。排他・条件付き commit・全失敗 / 競合・監査を実測。hash だけの代用は不合格 |
| D: authority 供給 | 独立に進められる | **未達、採用は NO-GO**。既存設計 §5 の真正性・対象・期限・失効・監査を実供給物で受入 |
| F-C: 確認付き限定補完 | H1 / H2 と D の受入、全保存経路の共通化 | **現在 NO-GO**。raw 欠損限定・通常単一行・一 writer・一操作確認・旧 host 停止を実装前に再レビュー |
| F-D: 限定自動補完 | F-C の受入＋別の無人処理契約 | **NO-GO**。確認省略を新機能として審査、明示 opt-in、False 既定、期限・競合・復旧・監査 |
| G: 配布・保存の最終受入 | 許可された F の完了 | **現在 NO-GO**。新配布物・実 host・exe・対応 profile・authority 更新の総合検証 |

まず R1 → R2 → R3 を推奨し、H1 / H2 と D は別の契約・証拠として進める。
今回の成果はこれらの境界と開始条件の設計であり、実装開始や自動保存の承認ではない。
工程 A～C の取得共有基盤と E0 の調査 GO は維持し、Imprint 自動補完全体の NO-GO も維持する。
