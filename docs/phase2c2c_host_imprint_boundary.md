# Phase 2C-2C-3E0：ComicTagger の Imprint 保存境界

調査日: 2026-10-20。**調査・反例の実証は完了したが、Talker 単独による保存先保護は NO-GO。**
通常文字列を保持できる条件は存在する。しかし現行 API では、その条件をプラグインが保存時に強制できない。
工程 D の authority 供給も未完了であり、Imprint 自動補完全体の NO-GO は解除しない。

## 1. 対象と証拠の範囲

- Windows 11、既存 `.venv` の Python 3.12、ComicTagger `1.6.0b9`、comicinfoxml `0.5.1`。
  依存追加・更新は行っていない。プラグインの package version は `0.3.0` のまま。
- 開始時: `main`、HEAD `cbce602f07a3559b8299a8e55c2dfc9d13d29022`。
  工程 A～C 等の既存差分は変更済み 9 ファイル、未追跡 11 ファイル。削除・上書き・commit はしない。
- 根拠は導入済みソースと [専用テスト](../tests/test_imprint_host_boundary.py) による実測。
  CBZ、書誌、取得結果、選択 ID はすべて **synthetic**。MADB 実測 fixture や意味確認データではない。
- production code、既存テスト、既存 fixture、raw evidence は変更しない。
  設計書・validation の既存本文を保持して追記する。
- 各 archive 試験は pytest の一時ディレクトリへ CBZ と `observation.json` を出力する。
  JSON は実 XML 全文、parser の値、両 reader の値、処理前後の Imprint を分離する。
  `ensure_ascii=True` は記録上の可逆 escape であり、試験入力・保存値を正規化しない。

以下のソース位置はすべて `.venv/Lib/site-packages/` を基準とする。
インストール済みの特定バージョンに対する根拠であり、将来版の保証ではない。

| ソース・関数 | 確認した責務 |
|---|---|
| `comicapi/genericmetadata.py:310 overlay()` | 自身を更新。Imprint は scalar merge。通常の新値 None / 空文字列は OVERLAY で上書きしない |
| `comicapi/merge.py:overlay()` / `attribute` | OVERLAY と ADD_MISSING の優先方向。空白文字列は長さがあるため非空 |
| `comicapi/genericmetadata.py:574 fix_publisher()` | publisher と imprint を更新。名前の部分一致でも置換・消去が起こる |
| `comictaggerlib/md.py:14 prepare_metadata()` | import transform → 既存の copy / clear → merge → auto imprint → Notes / description の整備 |
| `comictaggerlib/md.py:43 read_selected_tags()` | 指定順に reader を実行し merge。使用形式と例外も返す |
| `comictaggerlib/cbltransformer.py:CBLTransformer.apply()` | credits、tags、description 等を変換。Imprint / publisher は変更しない |
| `comictaggerlib/ctsettings/file.py:md_options(), autotag(), internal()` | 既定値と設定の意味 |
| `comicapi/comicarchive.py:221 read_tags(), :236 write_tags()` | reader / writer の選択、metadata cache、page 情報更新、タグの有効性 |
| `comicapi/tags/comicrack.py:123 write_tags(), :174 assign(), :324` | CR の XML 生成、truthiness による要素削除、Imprint の xlate |
| `comicinfoxml.py:118 write_tags(), :164 assign(), :324` | CIX の同等処理。CR と例外境界は同一ではない |
| `comicapi/utils.py:430 xlate(), :624 get_publisher(), :674 load_publishers()` | 外周 strip と空白値の None 化、host の既存 publisher table |

`ComicArchive.read_raw_tags()` は XML を parse して再シリアライズする。
原 bytes の証明には使えないため、試験では ZIP から `ComicInfo.xml` を直接読む。
reader の cache を実保存値と誤認しないよう、観測時は新しい `ComicArchive(path)` を使用する。

## 2. 実際の取得・保存フロー

### GUI の手動タグ付け

1. `TaggerWindow.load_archive()` (`taggerwindow.py:2121`) はフォームを消去し、
   `read_selected_tags()` で選択済み形式を読み、`update_ui_for_archive()` → `metadata_to_form()` で表示する。
2. `SeriesSelectionWindow` の `SearchThread.run()` は `talker.search_for_series()` に検索文字列等を渡す。
   このプラグインの `search_metadata(GenericMetadata)` は独自 helper で、beta9 の callback ではない。
3. `TaggerWindow.finish_query()` は `QueryThread` を生成する。
   `QueryThread.run()` (`:95`) の最終 fetch 引数は `issue_id`, `series_id`, `issue_number`, `on_rate_limit`。
   archive、パス、既存 Imprint、host の merge 設定は渡さない。
4. `apply_query_metadata()` (`:1215`) は先に `form_to_metadata()` を呼び、
   `prepare_metadata(self.metadata, new_metadata, config)` の結果をフォームへ戻す。
5. `prompt_write_tags()` の保存確認はタグ形式名を示す一般的な確認であり、Imprint の旧値と候補の比較確認ではない。
   `write_tags()` (`:1285`) は再びフォームを metadata に変換し、
   `selected_write_tags` の順に書く。失敗時は後続形式を停止する。
6. 保存後は cache を読み直し、`selected_read_tags` を再読込してフォームを更新する。
   書込形式と再表示形式は独立に選べる。

`metadata_to_form()` (`:874`) は `None` の項目をフォームへ代入しない。
`form_to_metadata()` (`:1013`) は `leImprint.text()` を `utils.xlate()` に通す。
この組合せにより、merge 結果が None でも以前のフォーム値が残り、次の保存で復活する場合がある。
この挙動は安全機能として利用できない。空文字列ならフォームへ代入されるため、None とも異なる。

補足: `IssueSelectionWindow` の選択更新 (`issueselectionwindow.py:185`) は、issue / year / month /
cover / title のいずれかが不足すると詳細表示のために `fetch_comic_data(issue_id=...)` を呼ぶ。
従来設計の「候補 API は補完入口を呼ばない」はプラグインのメソッド単位の契約として維持されるが、
**GUI の候補選択中に最終 fetch メソッドが呼ばれないという保証ではない**。
host は fetch に保存目的かプレビュー目的かの区別も渡さない。今回、通信・補完処理は変更していない。

### GUI の自動タグ付け・曖昧候補の選択

- `AutoTagThread.identify_and_tag_single_archive()` (`autotagprogresswindow.py:103`) は
  `internal__read_tags` を `md.read_selected_tags()` で読む。ここでは関数既定の OVERLAY /
  merge_lists=False を使用し、GUI wrapper の `Metadata_Options__tag_merge` は渡さない。
  読取例外なら停止。空なら filename metadata、必要なら検索文字列・巻を補う。
- `tag.identify_comic()` は `IssueIdentifier.identify()` に archive と検索用 metadata を渡す。
  一意な match の `issue_id` と rate-limit callback だけを Talker の fetch に渡し、
  `prepare_metadata()` の結果を返す。worker は成功時に `internal__write_tags` の順で保存する。
- 曖昧候補を人手で選ぶ `AutoTagMatchWindow.save_match()` (`autotagmatchwindow.py:226`) は、
  parent の `read_selected_tags(self._tags, ca)` → fetch(issue_id) → prepare → 同じ `_tags` へ保存。
  このダイアログ経路はソース確認のみで、自動操作はしていない。
- `TaggerWindow._start_auto_tag()` は `temp_opts` を作るが、worker には `self.config[0]` を渡す。
  今回確認したコードでは、開始ダイアログの `auto_imprint` は worker 用 config へ代入されていない。
  checkbox を操作したという事実だけでは有効な設定を保証しない。
  試験は worker に実際に渡す config を明示している。ダイアログの伝搬は実機確認項目として残す。

### CLI

`CLI.save()` (`cli.py:514`) → `create_local_metadata()` (`:244`) → `online_tag()` (`:458`) →
`prepare_metadata()` → `CLI.write_tags()` (`:145`) → `ComicArchive.write_tags()`。
読取順は、選択タグを `tag_merge` で統合 → filename を既定 ADD_MISSING（prefer_filename なら OVERLAY）→
明示的 CLI metadata を OVERLAY。明示 metadata でも既存値は変わり得る。
オンラインの issue ID 指定時も fetch へ渡すのは ID と callback だけ。
`skip_existing_tags` は既存形式があればファイル全体をスキップし、`dryrun` は保存しない。
いずれも Imprint だけを補完するための原子的な保護機構ではない。

## 3. Talker から見える値と host の merge

現在の `JapaneseBooksTalker.fetch_comic_data()` は NDL 取得・巻照合・`to_metadata()` 後に
工程 C の `supplement_metadata()` を呼ぶ。ここにある metadata は NDL 由来で、
保存先の既存 metadata ではない。Imprint evaluator も今回接続していない。
同じ Talker instance で複数 archive を処理するため、検索時に見た状態を instance に記憶する案も、
保存先との対応・更新時点・並行処理・プレビュー呼出しを保証できない。

| 設定 | 実際の既定 | Imprint に関する効果 |
|---|---|---|
| `metadata_merge` | OVERLAY | 新値が None / `""` 以外なら旧値を置換。ASCII / 全角空白も非空 |
| ADD_MISSING | 明示変更 | 既存 metadata が None / `""` なら新値、その他なら旧値。ただし reader / フォームで失われた raw 値は戻せない |
| `clear_tags` | False | True は merge 前に新しい GenericMetadata を作る。ADD_MISSING でも archive 既存値を救えない |
| `auto_imprint` | False | merge 後に fix_publisher。ADD_MISSING より後なので既存値も変え得る |
| `apply_transform_on_import` | False | 現行 CBLTransformer は Imprint に直接触らない。全設定を保持するという意味ではない |
| `metadata_merge_lists` | True | scalar の Imprint には影響しない |
| `tag_merge` / `tag_merge_lists` | OVERLAY / True | 読取時の統合。自動 worker の上述の既定呼出しとの差に注意 |
| GUI の read / write tags | 導入環境では CIX | CIX 未導入時の fallback は CR。選択されない既存形式は保護判断に使われない |

メモリ内の ADD_MISSING は `overlay(new, old)` という逆方向の実装である。
旧 None + 新 `""` は `""`、旧 `""` + 新 None は None となる。
両方が欠損扱いでも戻る表現は同一ではない。writer 後はいずれも要素なしになる。
専用試験の初回の期待値をこの実挙動に合わせて訂正した。入力の正規化ではない。

`GenericMetadata.overlay()` の特殊 sentinel `REMOVE` は削除を表すが、
今回の通常の Talker 値 None / `""` とは異なる。プラグインから削除 sentinel を返す案は採用しない。
`prepare_metadata()` は旧 metadata の copy に処理し、取得側も transformer 内で copy する。
最終 Notes には host の日時・取得元・ID が付加され、description の HTML 整理も実行される。
将来の「プラグインは imprint / Notes だけを変更」という内部契約は、host 全体の変更集合の保証ではない。

`auto_imprint=True` で host 同梱 `publishers.json` を読み込んだ場合の実測:

| merge 後の publisher / imprint | fix_publisher 後 | 原因 |
|---|---|---|
| `vertigo` / None | `DC Comics` / `Vertigo` | host table による補完 |
| `vertigo` / `vert` | `DC Comics` / `Vertigo` | 大文字小文字を無視した部分一致 |
| `vertigo` / `DC` | `DC Comics` / `Vertigo` | publisher の部分文字列を消去後、補完 |
| `DC Comics` / `DC` | `DC Comics` / `""` | publisher と混同する値の消去。保存時に要素なし |
| `vertigo` / `別文庫` | `DC Comics` / `別文庫` | Imprint は維持、publisher は変更 |
| publisher None | 元の Imprint | 処理せず return |

host table はこの挙動の検証にのみ使用する。MADB の意味確認済み authority へ流用しない。
host は起動時に同梱 table と利用者の設定を読み込むため、上記は同梱 table に限定した実測である。

## 4. XML と reader の段階別実測

表中の `\r`, `\n`, `\t`, `\u3000` は可視化用の escape。実験には実際の文字を渡した。
CR と CIX の両 writer × 両 reader の Imprint 結果は一致した。

| 書込前の raw 値 | XML 内の Imprint text | XML parser の text | CR / CIX reader | 通常 prepare → 再保存後 |
|---|---|---|---|---|
| None / `""` | 要素なし | None | None | 要素なし / None |
| ASCII 空白 `   ` | 空白のまま | 空白のまま | None | 要素削除 / None |
| `\u3000\u3000` | 全角空白のまま | 全角空白のまま | None | 要素削除 / None |
| `架空文庫` | 同じ | 同じ | 同じ | 同じ |
| `Label A123` | 同じ | 同じ | 同じ | 同じ |
| ` \u3000架空文庫\u3000 ` | 同じ | 同じ | `架空文庫` | `架空文庫` |
| `架空  文庫` | 同じ | 同じ | 同じ | 同じ |
| `架空\r文庫` | literal CR | `架空\n文庫` | LF | LF |
| `架空\n文庫` | literal LF | 同じ | 同じ | 同じ |
| `架空\r\n文庫` | literal CRLF | `架空\n文庫` | LF | LF |
| `架空\t文庫` / `架空\n\t文庫` | 同じ | 同じ | 同じ | 同じ |
| `A<&>"'文庫` | `A&lt;&amp;&gt;"'文庫` | 元の文字列 | 元の文字列 | 元の文字列 |
| `𠮷📚文庫` | UTF-8 の非 BMP 文字 | 同じ | 同じ | 同じ |
| `A\x00B`, `A\x01B`, `A\x0bB`, `A\x1fB`, `A\ufffeB` | 不正文字を含めて書く | ParseError | タグなし、Imprint None | 正常な新 XML に置換、不正な旧値は残らない |

writer の `assign()` は falsy な None / 空文字列について、既存要素も削除する。
通常の文字列は変更せず ElementTree に渡す。markup の escape は XML 表現上の変換で、
再読込後の文字列の損失ではない。CR / CRLF は writer の trim ではなく **parser の改行正規化**。
外周空白・空白だけの値は **reader の xlate** による損失。
GUI 経路では **form_to_metadata の xlate** が writer より前にも作用する。
内部の複数空白・LF / TAB は今回の範囲では維持されたが、XML 不正な制御文字の保証には拡張しない。

不正 XML の writer 戻り値は両形式とも True だった。
`has_tags()` の XML validation が False となり、`read_selected_tags()` も
`is_empty=True, tags_used=[], error=None` を返した。明示例外だけを監視しても検知できない。
writer 成功を raw 保存成功・再読込成功とみなしてはならない。
現行 evaluator の XML 不正値拒否は維持する。外周空白や CR は XML 上有効でも raw 往復を満たさない。

CR / CIX は異なる API ID だが、両者の `.file` は `ComicInfo.xml`。
CR→CR、CIX→CIX、CR→CIX、CIX→CR は実 `read_tags(tag_id)` で試験可能。
同じ CBZ で異なる Imprint を順番に書くと **後の write の値**が一つの XML に残り、両 reader がそれを読む。
独立した二つの Imprint が存在するという fixture は作っていない。
一般の `read_selected_tags()` は OVERLAY で後の非空値、ADD_MISSING で先の非空値を優先する。
GUI は combo の選択一覧を反転して内部読取順にする（`select_read_tags():1328`）。
本環境の CR / CIX の Imprint は同値なので、順序による別の Imprint は実証対象として存在しない。
別の tag plugin や改造 reader との統合は未検証。

## 5. 既存値保護の反例と実 host 統合

| 保存先 raw / 取得値 / 条件 | prepare 後 | 最終保存・再読込 | 判定 |
|---|---|---|---|
| `既存文庫` / None / 既定 | `既存文庫` | 同じ | 通常値は保護 |
| `既存文庫` / `取得文庫` / 既定 | `取得文庫` | 同じ | 既存値を上書き |
| `既存文庫` / `取得文庫` / ADD_MISSING | `既存文庫` | 同じ | 条件付き保護 |
| `既存文庫` / None / clear=True、CLI・自動 worker | None | 要素なし | 消去 |
| 同上 / GUI の直接 apply → save | None | `既存文庫` | 旧フォームが復活。経路差であり保護契約ではない |
| ASCII 空白のみ / `取得文庫` / ADD_MISSING | `取得文庫` | 同じ | reader が旧値を None にしたため置換 |
| `既存文庫` / None / 対象タグを読まずに CLI 保存 | None | 要素なし | 旧値が merge 入力へ入らない |
| 欠損 / ` 取得文庫 ` / 既定 | raw のまま | `取得文庫` | GUI は書込前、CLI / worker は再読込で外周を失う |

保存先の空白値は **Talker へ渡る以前**の reader で欠損化するうえ、最終 fetch の引数にも含まれない。
単なる `existing_imprint not in (None, "")` gate で archive の空白値を保護したとは言えない。
読取前の XML に存在した情報と、取得結果内の既存値を区別する必要がある。

専用テストの内訳:

| 試験 | 件数・範囲 |
|---|---|
| 既定値・導入バージョン | 1 |
| raw → writer → parser → 両 reader → prepare → 再保存 | 15 値 × 2 writer = 30 |
| 不正 XML の成功戻り値・読取不能・再保存 | 5 値 × 2 writer = 10 |
| archive と取得側の組合せ | 8 既存値 × 6 取得値 × 2 merge × 2 clear × 2 writer = 384 |
| メモリ内 overlay の対照 | 8 × 6 × 2 merge = 96 |
| 設定の相互作用 | merge / clear / auto_imprint / import transform 各 2 × 2 writer = 32 |
| fix_publisher の分岐 | 8 |
| 共有 XML の書込順・両 reader | 2 順序 × 2 read merge = 4 |
| 実 CLI.save | 7 分岐 × 2 writer = 14。fetch の実引数、旧値読取の欠落も確認 |
| 実 TaggerWindow | 1 テスト内で 7 分岐 × 2 writer = 14 シナリオ |
| 実 AutoTagThread → identify_comic → prepare → write | 6 分岐 × 2 writer = 12 |
| 合計 | **592 passed** |

最初の値マトリクスは要求された 8 種類を全組合せにした。
auto_imprint は raw 値全体との直積ではなく、変換・維持・消去を起こす publisher / imprint を
選定し、merge / clear / transform との全組合せと独立した分岐試験に分けた。
リスト設定は scalar Imprint の分岐を増やさないため既定のまま。

GUI は実 Qt widget を offscreen で生成し、`load_archive()` → `apply_query_metadata()` →
`write_tags()` と実 CBZ の保存を同期実行した。検索・クリック操作・QueryThread の非同期実行・
Windows 配布 exe 全体を自動化したわけではない。
CLI と自動 worker は取得側を Mock に置換し、worker では画像照合だけも Mock に置換した。
merge、prepare、XML writer / reader、保存先は実物。外部 HTTP は既存 autouse fixture で禁止する。
pipeline の旧入力・新入力に対する非破壊性と raw の段階差も assertion にしている。

## 6. 保証できる部分集合と保証できない条件

次の条件を**保存時に実際に満たす**なら、通常値の既存 Imprint は保持できる。

1. 保存対象 XML の有効性を確認し、対象タグを正しく読み、競合する形式や同時編集がない。
2. 既存値と候補は XML で有効、外周空白がなく、CR を含まない。
   より保守的な将来の初期対象は制御文字を含まない通常の単一文字列に限定できる。
3. `clear_tags=False`, `auto_imprint=False`。非空の取得値を返すなら ADD_MISSING。
   None を返す場合でも未読タグ・事前 CLI metadata・GUI 操作による消去を防ぐ必要がある。
4. 利用者の編集や手動 Auto Imprint action を含む後段処理が、値を変更しない。
5. 実 write と再読込の成功を検証する。False / 例外 / 読取不能なら安全完了と宣言しない。

これらは現行プラグインが検査・強制できる条件ではなく、host 側の実行条件または利用者の運用条件。
設定案内だけで「保証」に格上げしない。任意の設定、未読タグ、空白だけの旧値、外周空白や CR を持つ
raw 値、XML 不正値、同時更新、別 host 版についての保証はできない。
ELIGIBLE は意味確認・候補安全性の結果であり、保存先の状態や host 往復可能性を証明しない。
停止が必要な値を trim / CR 置換して採用する案は採用しない。

## 7. 将来方式の比較（すべて未実装）

| 方式 | 既存値保護 | raw 保持 | host 変更 / 配布互換性 | 運用負担・残るリスク |
|---|---|---|---|---|
| 現行 Talker 内だけの安全条件付き補完 | 取得 metadata 内のみ。archive は不可 | 通常値に限定可能 | 本体変更なし、現行 loader に適合可能 | 保存先不明・設定不明。自動保存の保証方式として NO-GO |
| host 既存設定による限定補完 | 正しい読取 + ADD_MISSING + clear / auto OFF に依存 | 通常値のみ | 本体変更なし | 設定・フォーム・未読タグを強制できず、利用者への注意に留まる |
| 明示的な利用者確認 | 旧 raw XML と候補・出力差を保存直前に提示できれば改善 | 損失値は保留 | 現行の一般保存確認だけでは不足。専用導線が必要 | ファイル対応、確認後の変更、誤承認。確認契約と実機試験が先 |
| 候補表示・診断だけ | 書き込まない範囲で保護 | raw を診断資料に保持可能 | 評価 API は既存。GUI 表示場所・配布方法は別設計 | 最も小さい保存リスク。人手の転記・後日の保存は保証外 |
| host API 拡張 | raw 既存値・保存先 ID・読取形式・予定設定と保存直前条件付き適用が必要 | 非対応値を停止。任意 raw 対応には別契約が必要 | 本体変更と版の能力判定、旧版 fail-closed が必要 | snapshot 後の変更検出、原子的な欠損時のみ適用、保存検証の責任を定義する |
| 自動補完を見送る | 本機能による変更なし | 新規出力なし | 現行版互換 | 手動作業は残るが現在の推奨。本来の host 編集リスクまで消すわけではない |

先に進める候補は **診断のみの設計**、または **host の保存直前契約を明示した限定方式の設計**。
独自 writer や本体 patch を暗黙に導入しない。
ホスト API を変えて既存値を渡すだけでも、reader が失った raw 空白と保存後の変換は解決しない。
raw XML の存在・値、設定、保存対象との対応まで供給し、書込直前に再確認する必要がある。

## 8. 実機で残る確認手順

Windows 配布版 `ComicTagger.exe` の操作確認は未実施。利用者の実ファイルを使わず、
テスト生成 CBZ のコピーと隔離した config で行う。画面表示だけでなく保存 XML と再読込値を記録する。

1. exe の About / plugin 一覧で beta9 / CIX 0.5.1 を確認し、read / write を CIX、次に CR へ切り替える。
   普通の既存値・外周空白・空白のみ・LF / TAB を持つ CBZ を開く。
   期待: 外周は表示時に除去され、空白のみは空欄。元 XML はまだ変わらない。
2. ホストの通常フォーム編集で別の Imprint を保存し、旧値が保護される専用 gate がないことを確認する。
   将来の候補適用を既存プラグインが実行したという記録にはしない。
3. 取得側 Imprint が None の通常検索を行う場合は取得結果を先に確認し、
   clear OFF / ON でフォーム・保存 XML を比較する。NDL / MADB の追加通信はこの通常テストには含めない。
   期待: 既定で通常旧値を保持。clear ON の GUI の None 復活は source / offscreen 実測との一致を確認する。
4. `Publisher=vertigo`, `Imprint=vert` で手動 Auto Imprint action を実行する。
   期待: `DC Comics` / `Vertigo`。既存値にも作用する。
5. 自動タグ付け開始ダイアログの Auto Imprint ON / OFF と保存済み config の値を別々に変える。
   worker が使った設定を確認する。ダイアログ checkbox の表示だけを根拠にしない。
6. read / write 形式を CR / CIX の両順序にし、Imprint が共有 XML の一値であることを確認。
   不正 XML はテスト用コピーだけで開き、タグなし扱い・再保存による喪失を確認する。
7. 候補選択中の詳細 fetch、通常保存、曖昧候補確認後の保存を区別して記録する。
   これらの exe 操作が未完了の間、全 UI 経路での受入は宣言しない。

## 9. 受入判定と次工程

| 対象 | 判定 | 根拠・前提 |
|---|---|---|
| 保存先既存 Imprint の保護 | **CONDITIONAL GO** | §6 の通常値・正しい読取・設定・保存時の条件を host / 運用側で満たす部分集合のみ。任意 raw・任意設定では NO-GO |
| 通常 Imprint の CR / CIX 保存・再読込 | **GO** | 指定版、synthetic の日本語・英数字・内部空白・特殊文字・非 BMP に対する実 writer / reader と host 試験の範囲 |
| 外周空白・制御文字等を含む任意 raw の往復 | **NO-GO** | strip、CR 正規化、不正 XML。内部 LF / TAB の成功を任意 raw の成功へ拡張しない |
| host 設定による変換・上書きの抑止 | **CONDITIONAL GO** | 設定と後段操作を host 側で制約し再検証すること。Talker が強制する方式としては NO-GO |
| Talker 単独の安全性保証 | **NO-GO** | archive raw と保存設定・目的が引数にない。メモリ内 gate では代替不能 |
| 将来の限定補完方式 | **CONDITIONAL GO** | 診断専用、または保存直前の確認・host 契約、対象値制限、実機試験を先に設計。自動書込の着手許可ではない |

**E0 の調査・実証成果は GO**。一方、工程 E が要求した全対象の保存先保護は未達であり、
工程 F / G の自動補完実装を開始できる GO ではない。
工程 D の真正性・独立性・対象適合・期限・失効・監査も未解決のまま。
工程 A～C の取得共有基盤の GO は維持する。
推奨順序は、診断 / host 契約の方式選択 → 保存境界の追加受入、並行して D の供給実証 →
両方の NO-GO 解除レビュー → F → G。今回どの production 機能も追加していない。

専用・関連・全回帰・Ruff・packaging・差分検証の実行結果と既知の権限問題は
[validation.md の E0 記録](validation.md#phase-2c-2c-3e0comictagger-の-imprint-保存境界2026-10-20) を参照。
