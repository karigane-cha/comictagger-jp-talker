# Phase I1: ComicTagger upstream 検証と GUI 整合性修正の詳細設計

調査日: 2026-10-31（Asia/Tokyo）。対象: **develop の固定コミット fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3**。状態: **I1 調査・設計完了、I2 実装未着手**。

## 1. Executive Summary

**問題 A・B・C はすべて最新 develop でも REPRODUCED。整合性条件は FAIL。** 既存の修正と重複するという根拠は見つからなかった。問題別の最小修正を develop に提案する設計を確定する。

| 問題 | 最新版の実測（Python 3.12 / 3.14 の合計） | 判断 |
|---|---|---|
| A: ソート中のセル混在 | タイトル・年・巻数各 6/6、計 18/18。通常の最終 ID は維持 | 行更新の原子化を実装する工程へ GO |
| B: キャンセル済み Issue 応答 | 6/6。期待 B/B に対して最終取得 A/B | 要求世代・確定境界・寿命管理を一体で実装する工程へ GO |
| C: 空結果の状態残留 | Series 空結果 6/6、出版社全件除外 6/6 | 明示クリアを実装する工程へ GO |
| C の追加発見: 空 Issue | 2/2。旧 A の ID が残り OK が有効、最終 A/B | 表示問題だけではない。B と同じ優先度 |
| Source order 新機能 | 今回の対象外 | HOLD 維持 |

追加で、同一 Series 再要求の旧結果採用、Cancel / reject 後の Issue 再表示、文字列フィルターで全行を隠しても確定可能な状態を確認した。単なる行混在、現在行の ID、要求の帰属、最終取得を区別する。**書籍への誤保存を確認したものではない。実書籍を開いたりタグを書いたりしていない。**

実験は最新 checkout を sys.path の先頭へ置く **ソース直接ロード**。既存 distribution の表示は 1.6.0b9 のままだが、ロードされた 86 個のホスト Python モジュールのパス・内容を固定 develop と照合した。旧版を最新版として実行したものではない。生成 version モジュールの補助と既存依存関係の制約は 6 節に明示する。

## 2. Scope and Constraints

参照資料は [表示順調査](ndl-gui-search-order-investigation.md) と [前工程の整合性調査](ndl-gui-selection-integrity-investigation.md)。旧版の再現件数は後者を再利用する。

今回行ったのは、公式 GitHub の読み取り、独立した調査用 checkout の取得、固定データによる offscreen 実験、設計文書の作成だけである。JP Talker、本体、既存テスト、既存 2 文書、設定、仮想環境、依存関係を変更していない。Issue / PR 投稿、commit / push / tag / Release も行わない。

- 新ソース: .tools/research-comictagger-develop。git check-ignore で管理対象外と確認。
- 旧ソース: .research/comictagger を読み取り専用で利用。切り替え・fetch・reset・clean なし。
- 検証コード: PowerShell の標準入力から Python へ渡す。恒久的な monkey patch なし。
- 一時設定・キャッシュ: .tools/pytest-tmp/selection-integrity-*。終了後の残留なし。
- GUI 実験の requests.Session.request は禁止する Mock。NDL / MADB / 画像への実通信なし。
- 「静的事実」「実測」「設計契約」「未確認」を区別する。以下の設計上の型・関数は、断りがない限り次工程の提案であり現行実装ではない。

## 3. Baseline Host Revision

| 項目 | 開始時の確認 |
|---|---|
| JP ブランチ / HEAD | main / d186c8e776a0a7ea6cf70d6da056027cc7fb258d |
| JP Talker | 0.4.0 |
| 依存指定 | comictagger>=1.6.0b9,<1.7、開発用 comictagger[gui,cix]==1.6.0b9 |
| Talker 最低版 | comictagger_min_ver = "1.6.0b9" |
| 既存ホスト | 両環境とも distribution 1.6.0b9 |
| 旧 checkout | tag 1.6.0-beta.9 / 57e5571c91c7515ee2cd594da6c780e61b056b15、clean |
| 開始時の未追跡文書 | docs/ndl-gui-search-order-investigation.md、docs/ndl-gui-selection-integrity-investigation.md |

依存根拠: [pyproject.toml][J-project] 13・16 行、[talker.py][J-talker] 30〜44 行。開始時に追跡ファイルと既存 2 文書、計 133 ファイルの SHA-256 を採取した。

## 4. Latest Upstream Revision

公式 [develop API][U-branch] を今回照会し、別 checkout の HEAD と一致を確認した。前工程の SHA をそのまま最新と仮定していない。

| 項目 | 結果 |
|---|---|
| 初回取得時刻 | 2026-10-31 01:24:49 JST 前後 |
| 再照合時刻 | 2026-10-31 01:33:48 JST |
| HEAD | fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3、再照合でも一致 |
| commit 日時 | 2026-09-06 21:53:31 UTC（author: 21:52:40 UTC） |
| HEAD の変更 | Make quick tag use the filename more often for accurate results |
| beta.9 からの到達可能な追加コミット数 | 65。git rev-list --count OLD..HEAD |
| git describe | 1.6.0-beta.10-58-gfa11a34 |
| 最新の公開 prerelease | 1.6.0-beta.10 |
| GitHub が返す最新安定 release | 1.5.5、2022-11-26 公開 |

[HEAD][U-head]、[beta.10][U-beta10]、[安定版][U-stable] を参照。develop、公開 beta、安定 release は別の対象である。

直近の履歴:

| SHA 短縮 | 内容 |
|---|---|
| fa11a345 | quick tag の filename 利用 |
| 111e7a2d | quick tag の重複結果クラッシュ修正 |
| ae5a1810 | zipremove の固定 |
| 745faff8 / ec3505c5 | 著者・contributor 文書 |
| 42931407 / ef7f367f | #849 の metadata 列修正 |
| 24fa8413 | assertions の修正 |

通常サンドボックスの git ls-remote は通信接続に失敗した。許可された調査用 clone をネットワーク利用可能な実行で取得した。GitHub API と clone の一致を確認しており、取得失敗を旧版で代替していない。

## 5. Upstream Commit and Source Comparison

固定ソースの AST を比較し、行番号・書式の差を除外した。主要 6 ファイルのうち 4 ファイルが変更、2 ファイルはバイト一致。統計は 377 additions / 268 deletions だが、これ自体は修正の根拠にしない。

| 対象 | beta.9 → develop の行 | 原因の分類 | 根拠 |
|---|---|---|---|
| Series.update_row | 346 → 359 | UNCHANGED | 全関数の AST 一致。同じ row で 4 列を更新 |
| Series.current_item_changed | 703 → 718 | UNCHANGED | AST 一致。row を保存して _fetch → update_row |
| SelectionWindow.current_item_changed | 241 → 254 | UNCHANGED | None で return、固定 row の利用 |
| Issue QueryThread.run | 56 → 61 | UNCHANGED | finish(list)、token なし、TalkerError はログだけ |
| Issue.perform_query | 99 → 104 | UNCHANGED | worker を単一属性に代入、Cancel 無効化なし |
| Issue.query_finished | 118 → 123 | UNCHANGED | 旧応答でも再構築・show。initial_id の要求間リセットなし |
| Issue.update_row | 151 → 162 | UNCHANGED | 同じ row に番号・日付・題名を順次設定 |
| Series.search_complete | 576 → 587 | INDIRECT_CHANGE | エラー / 空結果の通知を OptionalMessageDialog へ変更。現在の self.search_thread を読む原因は残存 |
| Series.search_canceled / update_buttons | 551 / 424 → 562 / 437 | UNCHANGED | disconnect と遅延 reject、bool(series_list) によるボタン判定 |
| TaggerWindow.finish_query | 1202 → 1235 | UNCHANGED | 親 selector の issue / series / number を最終 worker へコピー |
| MatchSelectionWindow / update_match | 旧形式 → 新 IssueResult | INDIRECT_CHANGE | series / md / Score を使用。要求世代の修正ではない |
| ComicTalker / GenericMetadata | 同一ファイル | UNCHANGED | 公開取得 API と ComicSeries / GenericMetadata は不変 |

ソース: [旧 Series][B-series]、[新 Series][D-series]、[旧 Issue][B-issue]、[新 Issue][D-issue]、[新 TaggerWindow][D-tagger]、[新 MatchSelectionWindow][D-match]。この 3 原因に DIRECT_FIX / REMOVED は見つからない。

関係する変更は [9cb72561][C-webengine]（Issue の HTML 描画）、[512b45b7][C-result]（IssueResult の再構成）、[51d4a484][C-dialog]（通知ダイアログ）、[d85a8ba4][C-tpb]（TPB 検出）。[ef7f367f / #849][C-columns] は autotagmatchwindow.py の列対応修正であり、Series.update_row の動的ソート問題の修正ではない。

## 6. Runtime Source Identity Verification

両環境とも起動直後、ホスト import より前に固定 checkout の絶対パスを sys.path[0] に設定した。comictaggerlib / comicapi / comictalker が先にロードされていないことを assert。実験後、ロード済みの各 .py の __file__ が checkout 配下にあり、git show 固定 SHA:path と改行正規化後に一致することを assert した。**86 モジュールすべて一致**。

ロード先の共通ルート:

C:/Work/VSCode/comictagger-jp-talker/.tools/research-comictagger-develop/

| モジュールの相対パス | develop の SHA-256（実ファイルのバイト列） |
|---|---|
| comictaggerlib/seriesselectionwindow.py | 89507716aa37e7dbf25d5de12b58e7a51a063588e4704f02facfae1444e5f586 |
| comictaggerlib/issueselectionwindow.py | db2668d02cb8f836fa144359cb26601e526cc10890788d05ed856840b35eb5f3 |
| comictaggerlib/taggerwindow.py | 311664e9da28d56d8e7e104fbbab748eef7ec44fef23b825ae5333d0585df5a0 |
| comictaggerlib/matchselectionwindow.py | 215a45bfa140892463fb3a50df670b41dc9a58f759d0105c2dbd82a60a289a5e |
| comictalker/comictalker.py | 5c9979fdf79adfaab94185bab1bc682bf62abf7333c3e40a9ca6a5424bf4c1c1 |
| comicapi/genericmetadata.py | b681e0d038579b125bb98e6441d46afa07e25f764672bc58814be9249cc2e726 |

旧 Series は 07be4c64449adc61ba13fee6990941100e90811b5b9896a2faeafe82167ecc4f、旧 Issue は 89c787246bf8a8442a1fcf9edde87aa5a0bab62febbdca9feee8548b09f7a88d。旧版と異なるモジュールを実際に使用した。

**distribution とロード対象を混同しない。** importlib.metadata.version("comictagger") は両環境とも 1.6.0b9。今回最新 distribution をインストールしていない。

checkout にはビルド生成物 comictaggerlib.ctversion がなく、最初の import は ModuleNotFoundError になった。[pyproject.toml][D-project] の setuptools_scm 設定で生成されるモジュールだけを、プロセス内の ModuleType で補った。version は git describe に基づく実験用ラベル 1.6.0b11.dev58 とし、正式にビルドされた distribution の版を測定した値とは扱わない。生成モジュールの __file__ は in-memory と明記し、86 個の追跡ソースとは別に数える。既存インストールからホストコードを混ぜて補っていない。

setup.cfg の有効な実行時依存条件を 3.14 環境と照合すると、zipremove==0.9.2 に対し 0.10.0 が存在する。3.12 も zipremove は 0.10.0 と確認した。依存関係を更新しない。GUI の今回の経路では archive 更新を行わず、この不一致で対象モジュールのロードは妨げられなかった。**配布物全体の互換性は HOLD**。正式受入には、別途用意する隔離環境で develop の依存指定、生成 version、Qt resources を満たしたビルドが必要。

## 7. Reproduction Environment Matrix

| 項目 | 3.12 | 3.14 |
|---|---|---|
| 実行ファイル | .venv/Scripts/python.exe | .tools/venv-py314-codex/Scripts/python.exe |
| Python | 3.12.14 | 3.14.10 |
| PyQt / Qt | 6.11.0 / 6.11.0 | 6.12.0 / 6.12.0 |
| 対象コード | 固定 develop、86 モジュール一致 | 同左 |
| 既存 distribution | 1.6.0b9 | 1.6.0b9 |
| 既存環境の変更 | なし | なし |

実行コマンドは次の形。調査用 Python の前半は前工程文書の最小再現コード、最新版ロード補助と今回の反復・追加ケースは本書末尾を参照。

~~~powershell
$env:QT_QPA_PLATFORM='offscreen'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONUTF8='1'
@'
<プロセス内の調査コード>
'@ | .tools/venv-py314-codex/Scripts/python.exe -u -B -
# 比較時は .venv/Scripts/python.exe -u -B -
~~~

固定データは NDL-A〜E、年 2020 / 2015 / 2025 / None / 2015、巻数 1 / 2 / 3 / None / 5、説明 DETAIL:<ID>:v0、出版社 PUB:<ID>。実 JP Talker の count_of_issues=1 とは区別したホスト境界用 fixture である。

テスト ハーネスの変更は次のとおり。

- ソース直接ロードと生成 version 補助: ロード基盤の変更。対象の取得・更新・確定関数は置換しない。
- R1 の title / year / count を各 3 回、R2 を 3 回に展開。期待値は前工程と同一。
- R3 の空結果メッセージだけを OptionalMessageDialog.information の Mock で抑止。結果採用・クリア・ボタン状態は実メソッド。
- Auto-Select 引き渡しは新 IssueResult(Score, ComicSeries, GenericMetadata) に適応。画像照合自体は未実行。
- 生存中 worker を実験側のリストに保持。これにより破棄クラッシュを避けるが、結果採用を修正してはいない。製品の所有権が安全という証明には用いない。
- source Mock の JP_BRIDGE は実 JP Talker の公開メソッドを実行する。
- フォント・生成 graphics resources を補わないため画像表示の視覚品質は対象外。画像 URL は空、外部リンクは example.invalid の文字列だけ。

## 8. Latest develop Reproduction Results

### 旧版と最新版の比較

件数は制御条件下の不整合観測数 / 実施数。終了コード 0 を PASS と読み替えない。

| 対象 | beta.9 / 3.12 | beta.9 / 3.14 | develop / 3.12 | develop / 3.14 |
|---|---|---|---|---|
| R1 年変更 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 |
| R1 タイトル変更 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 |
| R1 巻数変更 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 |
| R2 旧 Issue 応答 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 |
| R3 空 Series | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 | FAIL 3/3 |
| R3 出版社全件除外 | 本条件は未測定 | 本条件は未測定 | FAIL 3/3 | FAIL 3/3 |

最新版の A / B / C はいずれも REPRODUCED。FIXED_VERIFIED / NOT_REPRODUCED ではない。旧版欄は前工程の証拠、最新版欄は今回の実測である。

### 期待値と実測値

R1 年更新: 年昇順で A の年を 2020 → 2030 とした。

~~~text
期待 C: title=検証作品 3, year=2025, count=0003, publisher=PUB:NDL-C
実測 C: title=検証作品 3, year=2025, count=0001, publisher=PUB:NDL-A
UserRole=C。選択・詳細・最終取得は A / A / (A,A,"1")。
~~~

R2: 実 QThread と Event を使い、A 開始 → Cancel ボタンクリック → B の行を QTest でクリック → B 開始 → B 完了 → A 完了 → Issue 確定、という順序を固定した。

~~~text
B 完了後: parent.series_id=B, selector.series_id=B, selector.issue_id=B
A 完了後: parent.series_id=B, selector.series_id=B, selector.issue_id=A
期待 fetch: (issue_id=B, series_id=B, issue_number="1")
実測 fetch: (issue_id=A, series_id=B, issue_number="1")
~~~

R3: rowCount=0、current ID=None に対し、series_id=A と DETAIL:A が残った。Series の OK / Issues は無効。空結果以降の追加 fetch は 0 件。リンクを設定した別ケースでは A のリンクも残留した。

### 追加境界ケース（各環境 1 回）

| 条件 | 実測 | 判定 |
|---|---|---|
| 同一 Series A の旧 / 新要求 | NEW の後に OLD が採用、最終 OLD/A | FAIL。Series ID 比較だけでは足りない |
| 旧要求が TalkerError | NEW を維持、最終 NEW/A | 条件内 PASS。旧エラーは現行コードでログのみ。世代で破棄したわけではない |
| Cancel 後に Issue.reject | 非表示から、遅延応答で再び visible=True | FAIL |
| A の Issue の後、B が 0 件 | rows=0、issue_id=A、initial_id=A、旧詳細、OK=True、最終 A/B | FAIL。新たに確認した取得対象への影響 |
| 正常な X/B | issue_id=X、series_id=B、最終 X/B | PASS |
| 空結果のリンク | example.invalid/NDL-A のリンクが残る | FAIL |
| テキスト フィルターで全行を隠す | visible rows=0、current row=0、selected=A、OK=True | FAIL。行数は 5 のまま、出版社除外とは別 |
| 新 IssueResult による update_match | B → Issue → 最終 B/B | PASS |
| Series 直接 OK | 最終 ("",B,"") | PASS |

さらに各環境で 1 回、Series の old / new 検索を直接重複起動した。old 完了で未完了の new の空リストを描画し、旧 A 詳細が残り、new 完了で新 ID 集合に戻った。これは API 呼び出しのストレス条件であり、通常 UI からの到達性は未確認。

実 JP Talker の source Mock 検証は各環境 1 回。search、fetch_series、fetch_issues_in_series、巻号・年検索で ID 対応が一致し、最終 A/B は既存契約どおり source.get(A) を選んだ。ここを JP 側で B へ差し替える対策は採らない。

### 実行結果と制約

| 実験群 | 各環境の観測件数 | 終了コード | 内容 |
|---|---:|---:|---|
| R1〜R3 主実験 | 18 | 0 | 整合性 FAIL 18。R1 の局所 ID・最終取得自体は一致 |
| 追加境界 | 9 | 0 | FAIL 5 / 条件内 PASS 4 |
| Series 重複・JP bridge | 2 | 0 | 前者 FAIL、後者 PASS |
| Qt 所有権の分離実験 | 6 | 0 | 6 PASS。13 節参照 |

主実験の Qt 警告は各 397 件、追加境界は各 191 件、Series / JP は各 19 件。追加群ではフォント ディレクトリ、null pixmap、未生成の about.png resource、offscreen propagateSizeHints の警告を確認。未処理 slot 例外は 0 件、QTextEditLogger has been deleted は発生しなかった。所有権分離実験の出力に警告なし。

準備段階の失敗は集計に含めない。生成 version 不在の import 失敗、R3 観測コードのラベル名誤りによる例外ダイアログ待ちを修正した。後者はプロセスを停止し、誤った lblIssuesLink を実在する lblSeriesLink に修正して両環境を再実行した。Series 追加 fixture の新 ID に説明・出版社もそろえて再検証した。期待する整合性条件は緩めていない。

pytest と全テスト スイートは実行していない。実画像照合、実書籍への保存、一般的なネットワーク障害、全 OS・全 Talker は未検証。

## 9. Version-Specific Root Cause Analysis

A の原因は旧版と同じ。ソート列の setText / DisplayRole 更新で item が移動しても、後続の item(row, column) は古い整数位置を参照する。UserRole を持つ title item 自体は移動するため、行の識別と全セルの整合は別問題である。

B の原因も同じ。Issue QueryThread は要求 Series ID を保持するが、その情報を結果 list に添えていない。perform_query の Cancel は結果採用を無効にせず、query_finished は完了順で一覧を置換し show する。旧 error は成功結果と異なりログのみで return するため、旧エラーの試験が PASS でも要求管理が安全とは言えない。

C は Series と Issue で重大度が異なる。Series は空辞書でボタンを無効化するが、ID・詳細・リンクを消さない。Issue は空結果でも前回の issue_id / initial_id と OK が残り、最終取得へ伝播した。テキスト フィルターは非表示にするだけで、選択の有効性を再評価しない。

Issue.update_row にも同種の固定 row リスクが静的に残る。今回、複数 Issue のソートキー変化を実測したわけではないため STATIC_RISK とする。最終 QueryThread の TalkerError 時に worker.run 内で通知 UI を呼ぶ経路も静的に確認したが、今回の 3 問題とは別のエラー処理監査事項である。

## 10. Issue Generation Token Contract

**採用: アプリ内の単調増加整数 generation + 不変の RequestKey。** QApplication の寿命内で再利用しない。整数を Python object として signal に渡し、Qt の 32 bit int の上限を token に持ち込まない。

| 候補 | 評価 |
|---|---|
| 整数カウンター | 順序が明確、ログ・決定的テストが容易。採用 |
| UUID | 一意性は得られるが、単一プロセスで必要な性質を超える。不採用 |
| id(worker) | オブジェクト破棄後の再利用、UI 寿命との結合がある。不採用 |
| 要求ごとの lambda へ束縛 | token を運べるが、dialog の強参照や queued 接続の受信コンテキストが分散する。主要方式にはしない |
| 共通の大きな RequestContext 基底 | Issue / Series の描画・受入条件まで共通化するのは過剰。不採用 |

RequestKey は generation、source_id、kind、requested_series_id（Issue）、親選択の epoch を含む。Series 検索では requested_series_id の代わりに不変 SearchSpec を使う。worker_id は registry の登録番号で generation と同じ値を用い、1 要求 1 worker とする。これは Python オブジェクト ID ではない。

Controller 側の RequestContext は key、状態、採用結果、error、cancelled、progress 参照を持つ。worker は key と API 入力の読み取り専用コピーだけを持つ。UI の可変な self.series_id を worker.run から読まない。

同一 Series・同じ検索条件でも、新規要求のたびに generation を更新する。Cancel / Close では current_key を None にして無効化し、以前の token を再利用しない。結果集合は adopted_key と結び付け、取得待ち中に旧結果を確定させない。

## 11. Worker Signal / Slot Contract

**採用: 不変の要求情報を worker が保持し、明示的 payload 付き signal を QObject の slot へ queued 接続する。** 完了 signal は成功・失敗を 1 個の Outcome に統一する。既存の finish(list) の単純転送を廃止する。公開 Talker API は変更しない。

提案シグネチャ:

~~~python
# 設計上のシグネチャ。今回追加した製品コードではない。
class QueryThread(QtCore.QThread):
    completed = QtCore.pyqtSignal(object, object)  # RequestKey, Outcome
    ratelimited = QtCore.pyqtSignal(object, float, float)

    def __init__(self, talker, key, requested_series_id, owner):
        ...

    def run(self) -> None:
        ...

class IssueSelectionWindow:
    @QtCore.pyqtSlot(object, object)
    def on_issue_completed(self, key, outcome) -> None:
        ...

    @QtCore.pyqtSlot(object, float, float)
    def on_issue_ratelimited(self, key, full_time, sleep_time) -> None:
        ...
~~~

Outcome は成功時の tuple[GenericMetadata, ...] または ErrorInfo のどちらか一方。ErrorInfo はエラー種別、source、code、表示用文字列、整形済み traceback を持つ。QObject / QWidget を渡さない。worker は emit 後に結果 metadata を変更しない。

run は TalkerError と通常の Exception を捕捉し、成功または失敗の terminal Outcome を 1 回だけ emit して return する。worker からダイアログを表示しない。ログは旧要求でも残してよいが、現在 UI の error / toast / progress は token の検証後だけ更新する。強制プロセス終了はこの契約外。

採用の順序は固定する。

1. GUI スレッド上の slot であること。
2. controller が CLOSED / CANCELLED でなく、現在 LOADING であること。
3. key.generation、source_id、kind が current_key と一致すること。
4. requested_series_id と親選択 epoch が現在の要求・親候補に一致すること。
5. 同じ key の terminal Outcome を既に採用していないこと。
6. failure なら FAILED へ移行し、該当 progress だけ閉じ、出力選択を空にする。
7. success なら ID を検証した結果集合を採用し READY へ移行する。空 tuple は成功した空結果として扱う。
8. 選択・描画の完了後に確定ボタンを再評価する。

重要: 結果採用の判定に「worker がまだ registry にいるか」を使わない。finished の処理と UI への queued Outcome の処理順が別受信先で前後しても、UI が保持する不変 key / context で判定できる。QObject の sender() を結果の識別に利用しない。

progress / ratelimit にも同じ key を付ける。古い worker と新 progress を直接 connect しない。close_progress(key) は現在保持する progress の key と一致した場合だけ、cancel signal を再発火させず閉鎖・deleteLater する。

[Qt QObject の契約][Q-object] では、disconnect 後も既に queued されたイベントが届き得る。したがって disconnect は後始末として使用できるが、整合性保証を置き換えない。

## 12. Request State Machine

状態と GUI の関係:

| 状態 | current key / 要求 Series | 結果・選択 | 確定 | progress / worker |
|---|---|---|---|---|
| IDLE | なし | 空 | 不可 | なし |
| LOADING | 新 key / 要求 ID | 旧結果と出力選択は空 | 不可 | 現行 progress、実行中 worker |
| READY | 採用 key / 要求 ID | 現行結果。空結果なら無選択 | 有効な可視 Issue がある場合だけ可 | progress なし。worker は終了処理中でもよい |
| FAILED | 失敗 key は診断用のみ | 空、error あり | 不可 | progress なし。終了待ちを registry が管理 |
| CANCELLED | current key なし | 空 | 不可 | progress なし。旧 worker は生存し得る |
| CLOSED | current key なし | UI 状態は空。受渡済み receipt は独立値 | 不可 | UI を破棄できる。worker は registry が管理 |

遷移:

| イベント | 遷移と副作用 |
|---|---|
| 初回要求 | IDLE → LOADING、新 generation |
| 同一 / 別 Series 再要求 | 旧 key を無効化 → 出力クリア → 新 LOADING |
| 現行成功・非空 | LOADING → READY、adopted_key を記録、番号ヒントから初期選択 |
| 現行成功・空 | LOADING → READY、空一覧・無選択・確定不可 |
| 現行失敗 | LOADING → FAILED、現行 error だけ表示 |
| Cancel | LOADING / READY → CANCELLED、結果・選択・key を破棄 |
| 旧成功 / 旧失敗 / 旧進捗 | 状態不変。描画・通知・progress 閉鎖なし |
| Issue 確定 | READY の受入条件を再検証 → receipt 作成 → CLOSED |
| Dialog close / Escape / reject | どの状態でも CLOSED、子 UI のみクリア |
| 親 Series 変更 / 親画面終了 | 子の key を無効化。旧子結果の受入を禁止 |
| 再利用した dialog を開く | CLOSED の表示状態を復元せず、新 key で LOADING |

UI Cancel、結果無効化、requestInterruption、通信の終了、QThread.finished、QObject.destroyed は別イベントである。

## 13. Cancellation and QThread Ownership

**採用: QApplication が所有する小さな RequestRegistry に実行中 QThread を保持する。** ダイアログを worker の唯一の所有者にしない。新要求時に self.querythread を上書きしても旧 worker の強参照は registry に残る。

registry は GUI スレッドの QObject。live[generation] に worker と不変 key を保持し、QThread の QObject parent も registry とする。worker の Qt.finished を registry の bound slot へ queued 接続する。

解放契約:

1. Cancel / Close は UI の key を即時無効化し、requestInterruption を補助的に通知する。
2. 同期 Talker 呼び出しの途中では quit() / requestInterruption() が HTTP を止めるとは仮定しない。terminate() を使わない。
3. finished を受けた registry は wait(0) を確認する。完了同期できなければ短い QTimer で再確認し、GUI スレッドを待機で塞がない。
4. wait(0)==True 後に live から retiring へ移し、worker.deleteLater()。destroyed を受けて retiring から外すまで強参照と QObject parent の管理を維持する。
5. registry / QApplication の破棄より先に、管理 worker の終了と deferred deletion を完了させる。
6. 結果 signal の受信先は dialog の QObject slot。dialog 破棄後は Qt の接続管理に任せ、dialog を捕捉する匿名 callback を worker に残さない。
7. stale の error はログだけ、最新 UI を変更しない。progress は要求 key を持つ UI 所有物であり worker が直接操作しない。

[QThread の公式契約][Q-thread] により、稼働中 QThread の削除は不可で、finished と完全な終了同期も区別する。今回の設計は QThread.create() の例外的な破棄仕様に依存しない。

**分離実験:** 最新の実 Issue QueryThread を Event で保留し、アプリ所有の QObject が保持した。受信先の無効化 / deleteLater の 2 条件 × 3 回 × 2 環境、計 12/12 成功。requestInterruption 後も worker が動作中であること、終了前は window close を拒否すること、finished → wait(0) 成功 → destroyed 1 回、無効・破棄済み受信先への状態適用 0 件、終了後の close 成功を QSignalSpy / QTest で確認した。

これは Qt の所有権・破棄手順の検証であり、ホストへ registry を実装・統合した結果ではない。I2 / I3 では実アプリの全終了入口をこの契約へ接続することが必須。

## 14. Dialog Lifetime and Cleanup

ダイアログ close は通信完了を待たず許可できる。registry が生きている間、worker を保持して旧結果を捨てる。親 Series の close は子 Issue の context も CLOSED にする。閉じた後の遅延完了で show() してはならない。

アプリ全体の終了には別の drain 境界を設ける。

- [TaggerWindow.closeEvent][D-tagger] 2085 行の終了処理へ registry の稼働確認を加える。通常の actionExit は 547 行で self.close に接続されている。
- live または retiring に管理 worker が残る場合、closeEvent を ignore し、終了待ち状態へ移行。すべての要求を無効化し、新規要求を受け付けない。イベント ループと registry は維持する。drain 中は quitOnLastWindowClosed を抑止し、復帰時に以前の設定へ戻す。
- worker が終了し deferred deletion が済んだ時点で、終了を再試行する。終了確認・設定保存を二重実行しない。
- 待機を取り消す操作はアプリを維持するだけ。キャンセル済みの要求結果を再有効化しない。
- Talker が返らない場合はアプリを維持して待つ。タイムアウトを理由に稼働中 thread を破棄しない。通信時間の上限を公開 API の保証として新設しない。
- gui.py の例外ダイアログ Abort（64 行の QApplication.exit(1)）を含む明示的終了も drain の入口を通す。OS による強制終了やプロセス障害を正常終了の保証に含めない。
- aboutToQuit だけで後始末を開始する方式は採らない。イベント ループを止める前の入口で待機を制御する。

画像の後着応答は CoverImageWidget.clear() と URL 集合のクリアを利用する。[coverimagewidget.py][D-cover] 118〜133、245〜248 行を参照。任意の画像ローダーの全競合は今回未実測であり、I3 で旧画像の後着も検証する。Talker のロゴは選択詳細ではないので消さない。

## 15. Final Issue Acceptance Contract

受入条件はボタンの enabled だけに依存しない。accept()、done(Accepted)、ダブルクリックが共通の検証を通るようにする。

~~~python
def can_accept_issue(self) -> bool:
    return (
        self.state == READY
        and self.current_key == self.adopted_key
        and not self.cancelled
        and self.parent_selection_epoch == self.current_key.parent_epoch
        and self.parent_series_id == self.current_key.requested_series_id
        and self.current_item_is_visible()
        and self.current_issue_id in self.adopted_results
    )
~~~

この式に加えて、行 UserRole と current_issue_id の一致、結果の source 帰属、取得時の不正 ID 検査が済んでいることを確認する。欠落 issue_id は選択候補にしない。同一 ID に異なる metadata があるなど曖昧な重複は取得エラーとして確定を止める。

GenericMetadata.series_id が存在する場合は requested_series_id と矛盾しないことを確認する。series_id が欠落する Talker では要求コンテキストによる帰属を使い、従来の任意フィールドを突然必須化しない。**issue_id と series_id の文字列同一性は要求しない。** X/B は正当な組み合わせとして受け入れる。

確定時に不変の AcceptedSelection(key, series_id, issue_id, issue_number, parent_epoch) を作成し、親へ渡す。親 issue_selected でも現在の親候補・epoch を照合してから自身を accept する。旧子の可変属性を無条件にコピーしない。最終 TaggerWindow.finish_query は受理済み receipt の値で QueryThread を起動する。

内部の受渡しは selection_accepted = pyqtSignal(object)（AcceptedSelection）へ統一する。Issue → 親の issue_selected(receipt)、Series → TaggerWindow.finish_query(receipt) を接続し、業務処理を QDialog.finished(int) から外す。正常確定は receipt をローカルに確保 → super().done(Accepted) → selection_accepted.emit(receipt) の 1 回だけ。reject / close では emit しない。親は要求開始時に保存した expected_child_key と receipt.key を照合するため、子が CLOSED になって current_key を消した後でも検証できる。Accepted の閉鎖と Cancel による無効化を区別し、再要求・親選択変更では expected_child_key を必ず更新または破棄する。

Series 直接 OK は別の正常経路として残す。現行の可視 Series に対し issue_id=""、series_id=選択 ID、issue_number=検索時の番号ヒントを渡す。旧 Issue ID を転用しない。検索時の番号ヒントと確定した番号は別フィールドで保持する。

Auto-Select は新 IssueResult の series.id / md.issue を使い、通常の新要求・受入条件へ進める。画像照合経路だけ token 検証を省略しない。

## 16. Series Search Generation Contract

[SearchThread][D-series] 47 行以降も、結果を属性へ保存して searchComplete() を引数なしで通知する。search_complete の 605 行では現在の self.search_thread.ct_search_results を読む。これを **完了した要求の key + Outcome** に置き換える。

SearchSpec は talker/source、検索文字列、literal、refresh、threshold と描画時のフィルター方針のスナップショットを持つ。同じ検索語でも generation を更新する。古い result / error / progress / ratelimit を UI に適用しない。検索開始時に一覧・確定出力を空にし、未完了の別 worker の結果を参照しない。

現行の search_canceled は disconnect 後に QTimer で reject する。遅延 callback で新しい要求を閉じないよう、close_me も key を検証するか、Cancel 時点で対象画面を同期的に CLOSED にする。単なる disconnect 依存を除く。

共通化するのは RequestKey / Outcome / RequestRegistry と worker の解放だけ。Series の分類・ソート・初期選択と Issue の番号照合は各 controller に残す。各画面が独自に worker の所有権を実装する案より破棄規則を統一でき、汎用データ取得フレームワークを追加する必要はない。

Series の世代管理は独立した修正単位。通常 GUI からの重複開始は追加確認事項だが、直接呼び出しでの不整合と現在 worker 参照の原因は確定している。

## 17. Atomic Qt Row Update Design

**採用: ソート停止 + try/finally + 対象 item の事前保持。** ID は検証に使い、毎セルの探索には使わない。Series / Issue の同じ責務を扱う。

| 方式 | 判断 |
|---|---|
| ソート停止 | 最小の中心方式。前工程の対照実験 24/24 成功、対象関数は develop でも AST 一致 |
| item を全列分保持 | 行の途中移動に強い補助。sorting 停止中の検証・ロールバックにも使う |
| ID で毎回検索 | 可能だが O(n) の再探索と重複 ID の曖昧さ。1 回の row 再取得だけでは不十分 |
| 再入防止ガード | 更新区間のみ採用。単独ではソートによる位置変更を防げない |

トランザクションの境界:

1. selection_epoch、対象 item、UserRole ID を保存し、その ID で詳細を取得する。ネットワーク取得中は sorting を止めない。
2. 取得後に epoch / current item / ID を再確認。途中に別候補へ移ったなら詳細・セルを一切採用しない。
3. 現行 _fetch は取得と描画が混在するため、取得部分と反映部分を分離するか、描画直前に epoch を検証する。current_item_changed で戻り値だけを確認しても、既に表示を書いた後では遅い。
4. 全セルの新しい表示値・roles を Qt 書き込み前に準備する。対象 ID、item の存在、列数を検証する。
5. sorting enabled、column、order、current item、選択 ID、全変更 roles / flags、詳細の旧値を保存する。
6. table の通知だけを QSignalBlocker で抑止し、更新ガードを立てて sorting=False。model / selectionModel の通知は止めない。
7. 同一 ID の保持済み item に全列を書き込み、同じ詳細を反映する。この区間で processEvents、取得 callback、await を呼ばない。
8. finally で元の列・方向と sorting 状態を復元する。元が False なら False。item 参照または ID で選択を維持し、先頭行への無条件選択をしない。
9. ガード解除後、選択 ID・詳細 ID・全セルを照合する。通知が必要なら整合した状態を 1 回だけ公開し、詳細を再取得しない。

新規構築では空 item の UserRole が未設定なので、「既存 ID 一致が必要な更新」と「検証済み record から行を作る処理」を区別する。構築全体も sorting 無効で行い、全行の完成後に初期選択する。

検索時の series_list と詳細時データの版が異なることは今回維持する。原子化のために辞書の挿入順や検索順位を変えない。[Qt の setItem 説明][Q-table] にも複数セル設定中のソート停止が示されているが、今回の setText による現象は実測で判定している。

## 18. Exception Safety

行更新前に書式化と候補照合を済ませ、通常の Python 例外で半行だけ書き換わる範囲を減らす。途中失敗時は、ソートを停止したまま保存済みの同一 item の roles / flags と詳細・ID を復元する。

ロールバック自体が失敗した場合は、曖昧な行を再利用せず、対象画面の選択・結果・確定を無効化して FAILED にする。再検索で回復する。他候補へ取得済み値を書き続けない。finally は sorting / 選択通知 / 更新ガードの復元を必ず行う。既に QObject が破棄された異常経路に対して、失効した Python wrapper を操作しない。

同期詳細取得中の再入には selection_epoch を使う。単純な busy フラグで新しい選択イベントを捨てるだけでは、新しい選択に旧詳細が残る。イベントを検出して epoch を進め、旧処理の反映を拒否する。これは Issue 一覧要求の generation と別の、同一画面内の選択更新契約である。

worker の error は Outcome として GUI で処理し、FAILED でも registry の finished / join / deletion は必ず実施する。結果処理の例外で worker の保持リストから先に消さない。

## 19. Empty-State Synchronization

対象フィールドと所有者:

| 所有者 | クリア対象 |
|---|---|
| SeriesSelectionWindow | series_id、issue_id、確定 issue_number、series_list、current item / selection、詳細 HTML、lblSeriesLink、選択 cover、OK / Issues / Auto-Select |
| IssueSelectionWindow | issue_id、確定 issue_number、initial_id、issue_list、current item / selection、詳細 HTML、lblIssueLink、選択 cover、OK |
| 各 controller | adopted_key、結果 receipt、選択 epoch の更新、error の表示状態 |
| 要求 context | requested_series_id / SearchSpec は LOADING 中の要求情報として保持。選択済み ID と混同しない |
| 別入力 | 検索語、利用者の番号ヒント、ソート列・方向、Talker ロゴは選択クリアの対象外 |

現在は issue_number が検索ヒントと選択結果を兼ねるため、requested_issue_number と確定用の値を区別する。再要求で initial_id を "" に戻し、新結果だけから初期選択を求める。古い Issue の番号を新結果の選択根拠にしない。

| イベント | 契約 |
|---|---|
| 検索開始 / 再検索 | 旧要求無効化、旧出力・詳細・一覧クリア、LOADING、確定不可 |
| 空結果 / 出版社全件除外 | READY の空集合、選択・詳細・リンク・画像なし、確定不可 |
| テキスト フィルター | データ集合は保持。現行候補が非表示なら無選択にして出力・詳細をクリア。可視候補を利用者が選ぶまで確定不可 |
| 選択候補消失 | current_item_changed(None, ...) で明示クリア。単純 return をやめる |
| Cancel / error | 旧結果を確定不可にし、詳細を空にする。error は最新 context のみ |
| 子画面終了 | 子の出力と context をクリア。親の別候補を勝手に変更しない |
| 親画面終了 | 子 context も無効化。後着応答で再表示しない |

フィルター解除で自動的に古い選択を復活させない。再選択は明示操作または新しい結果の初期選択として扱う。全件非表示でも rowCount は 0 にならないため、可視性と選択可能性で判定する。

## 20. JP Talker and Other Talker Compatibility

| 判断項目 | 結論 |
|---|---|
| 最新 GUI の 3 問題 | 未修正、今回再現 |
| 公開 Talker API | ComicTalker ファイルがバイト一致。指定 4 API の AST も一致 |
| ComicSeries / GenericMetadata | 定義ファイルがバイト一致。ID 契約の変更なし |
| IssueResult | 非互換の内部変更あり。旧 dataclass から Score / series / md の NamedTuple へ |
| JP Talker の局所動作 | 最新ロード下の実公開 API + source Mock で ID 対応を確認 |
| JP Talker の全体互換性 | 通常起動・配布物・画像照合・書き込みは未検証。更新推奨は HOLD |
| バージョン制約変更 | 今回不要。新たな最低版や beta 固定を設定しない |
| 提案修正の公開 API | 変更不要。signal / slot / receipt はホスト内部だけ |

根拠: [ComicTalker][D-api]、[GenericMetadata][D-metadata]、[IssueResult][D-result]、[JP Talker][J-talker]。JP Talker は IssueResult を公開 API の返却型としていない。

他 Talker では X/B のように ID が異なることが普通にある。固定データで X/B を確認したが、特定の外部 Talker 製品の全体動作を保証したわけではない。同一 Series の複数 Issue、欠落 ID、異なる metadata フィールドは 23 節の正式回帰に含める。

一括自動タグ付けは [AutoTagThread][D-auto] の identify_comic → metadata → ca.write_tags の経路であり、この IssueSelectionWindow の確定処理を使わない。今回の行混在・旧 Issue 結果競合の直接影響を一括処理へ拡大しない。一方 GUI Auto-Select は update_match → show_issues を共有するため正式回帰対象。

NDL の取得順、ISBN 優先、日付・出版社補完、資料種別、キャッシュキー、タグ writer の内容は変更しない。

## 21. Proposed Code Change Map

基点はすべて fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3。行番号は現行 develop の位置であり、将来の変更行を断定するものではない。

| ファイル / 関数 | 変更契約 |
|---|---|
| 新規内部モジュール comictaggerlib/requestcontext.py（提案名） | RequestKey / Outcome / ErrorInfo / RequestRegistry、generation 発行、live worker と終了待ち。公開プラグイン API にしない |
| issueselectionwindow.py: QueryThread 48、perform_query 104 | 不変 key、terminal Outcome、Cancel 無効化、registry 登録 |
| 同: query_finished 123、cell_double_clicked 153 | key 検証、空結果・initial_id リセット、共通の受入検証、receipt |
| 同: _fetch 189、update_row 162 | selection_epoch、取得と反映の分離、原子的な row 更新 |
| seriesselectionwindow.py: SelectionWindow 239〜266 | 可視性を考慮した選択クリア、None 選択、共通更新ガード |
| 同: show_issues 536、issue_selected 547 | 親 epoch と requested Series、receipt 検証 |
| 同: SearchThread 47、perform_query 332、search_complete 587 | key + Outcome、古い result / error / progress 棄却 |
| 同: search_canceled 562、close_me 573 | 要求単位のキャンセル。古い遅延 close を新要求に適用しない |
| 同: update_row 359、_fetch 402、current_item_changed 718 | 17〜18 節の原子化・選択 epoch |
| 同: update_buttons 437、filter 393、search_complete 587 | 空・非表示選択では確定不可。出力 ID と詳細クリア |
| taggerwindow.py: finish_query 1235 | 受理済み selection 値の利用。可変 selector 属性を再読しない |
| 同: closeEvent 2085 | 通常終了を registry の drain に接続 |
| gui.py: Application / 例外 Abort / gui 起動 | registry の QApplication 所有、明示終了入口の drain、終了待ち中のイベント ループ維持 |
| matchselectionwindow.py / resulttypes.py | 原則変更不要。現行 IssueResult 形式で回帰確認 |
| coverimagewidget.py | 原則既存 clear() を使用。後着画像の試験で不足が判明した場合のみ別の小修正として再評価 |
| ComicTalker / GenericMetadata / JP Talker | 変更しない |

## 22. Implementation Units and Commit Plan

今回 commit は作成しない。各単位は独立した不具合説明・回帰を持ち、依存する共通処理は重複実装しない。

| 単位 / 仮の commit 名 | 内容・内部変更 | 回帰 / 完了条件 / 提出単位 |
|---|---|---|
| U1: fix(gui): discard stale issue query results | registry、key / Outcome、Issue Cancel / Close、受入 receipt、LOADING / 空 Issue での確定防止。アプリ終了境界も含む | R2、同一 Series、旧 error、close、X/B、空 Issue、最終引数。finished と破棄を確認して 1 PR |
| U2: fix(gui): clear stale selection state | U1 のクリア処理を Series 空結果・None 選択・フィルター・リンク・画像へ適用 | 空 Series、出版社全除外、テキスト全非表示。U1 の空 Issue 受入修正を重複させず別 PR |
| U3: fix(gui): prevent row corruption during sorting | Series / Issue の sorting guard、item 保持、selection_epoch、例外時の復元 | タイトル・年・巻数、両 sorting 状態、例外、選択・fetch 回数。独立 PR |
| U4: fix(gui): discard stale series search results | U1 の registry と Outcome を Series に適用。可変 current thread 読みを廃止 | 同一語、逆順完了、旧 error、Cancel / progress。U1 依存の別 PR |

推奨順は U1 → U2 → U3 → U4。取得対象に影響する U1 / 空 Issue を優先する。U3 は別担当工程で先行可能だが、今回は並行実装を行わない。

I2 はこの契約に基づく実装、I3 は次節の正式自動回帰、I4 は依存を満たすビルドと実 GUI 統合確認、I5 は upstream の重複確認を再実施した後の提案。既存環境を上書きして I4 の環境を作らない。

## 23. Deterministic Regression Test Specification

### 共通条件・期待値

対象は固定 develop と提案修正後の同一基点。beta.9 は後方互換検証時に別 adapter で実行し、IssueResult の形式差だけを吸収する。次表の「修正前」は、実測済みを M、ソースからの予測を S、未測定を U と明記する。S / U を今回の成功・失敗件数に数えない。

- 基本データ F: 7 節の A〜E。個別の変更値は表に指定。
- I(A): issue_id=A、series_id=A、issue="1"。I(X,B): X が B に属する正常 Issue。
- N / O: 同じ Series A に属する新 / 旧 Issue。issue_id は NEW / OLD、番号は "1"。
- CLEAR: 19 節の出力 ID・詳細・リンク・画像・現在選択が空、確定不可。要求の入力ヒントは保持。
- fetch "-" は最終取得呼び出し 0 回を意味する。表の ID は NDL- 接頭辞を省略。
- 入力番号ヒントがあり一致候補がない場合は無選択。利用者の明示選択まで確定不可。ヒントが空の場合の初期選択は最初の有効な可視 Issue とする。
- 表の「表示 / 選択 / 最終引数」が修正後の受入条件。省略した描画項目も CLEAR または全セル一致の共通条件に従う。

### Issue

| テスト名 | 固定入力・事前状態 | 操作と完了順 | 期待表示 / 選択 / 最終引数 | 修正前 |
|---|---|---|---|---|
| cancelled_issue_result_ignored | F、A を選択 | A 開始→Cancel→B 行クリック→B 開始→B 完了→A 完了→OK | B の Issue・詳細 / B / (B,B,"1") | M: A/B |
| same_series_new_generation | O・N、ともに Series A | O 保留→Cancel→同じ A の N 開始→N→O→OK | N の内容 / NEW / (NEW,A,"1") | M: OLD/A |
| stale_issue_error_ignored | O は TalkerError、N は成功 | 上記と同順、最後に O が失敗 | N 維持、古い error / toast なし / NEW / (NEW,A,"1") | M: N 維持。token 以外の理由で PASS |
| close_pending_dialog | I(A)、worker 保留 | Cancel→reject / Escape / 親 close / deleteLater→A 完了 | 閉じたまま、再表示なし / 空 / -、worker 終了後 destroyed=1 | M: reject 後に再表示。他終了入口は U |
| accept_current_generation_only | I(A) を採用済み、B は保留 | B 開始中に OK / done(Accepted) / double click、B 完了後に再確定 | 待機中 CLEAR / 空 / -、後半 B / B / (B,B,"1") | S: 旧結果の受入ガードなし |
| final_fetch_arguments | F、正常 / 旧応答の両条件 | 採用完了→実子 accept→親 receipt→実最終 QueryThread | 採用 key の候補だけ / その ID / 正しい 3 引数 | M: 正常一致、旧応答 A/B |
| distinct_issue_series_ids | I(X,B)、I(Y,B)、番号 1 / 2 | B 取得→Y を選択→OK | Y の内容 / Y / (Y,B,"2")、X/B も別例で許可 | M: 単一 X/B は PASS。複数版 U |
| issue_initial_id_reset | A の番号 1 を採用済み、B は X の番号 2 のみ | B を番号 1 のヒントで再要求→完了→X を明示選択 | 完了直後は無選択・initial_id=""、明示後 X / (X,B,"2") | S: initial_id=A が残る |

### Series

| テスト名 | 固定入力・事前状態 | 操作と完了順 | 期待表示 / 選択 / 最終引数 | 修正前 |
|---|---|---|---|---|
| old_search_completion_ignored | F と ID に -NEW を付けた新集合 | old 保留→new 開始→old→new | old 時は最新 LOADING のまま、new で新一覧 / A-NEW / 確定前は - | M: old 時に未完了 new の空リストを採用 |
| cancelled_search_result_ignored | F、検索保留 | Cancel→old 完了 | CLOSED のまま / 空 / -、新画面を閉じない | U。disconnect 済み queued delivery も注入 |
| same_query_new_generation | 同じ検索語、異なる結果集合 | g1→g2→g2 完了→g1 完了 | g2 の一覧だけ / g2 初期候補 / その候補で直接 OK | S: current thread 参照に依存 |
| stale_search_error_ignored | g1 TalkerError、g2 F | g2 完了→g1 失敗 | g2 の一覧・詳細維持、旧 error なし / g2 選択 / その候補 | U。逆順・g2 LOADING 中も追加 |

### Qt

| テスト名 | 固定入力・事前状態 | 操作と完了順 | 期待表示 / 選択 / 最終引数 | 修正前 |
|---|---|---|---|---|
| detail_title_mutation_atomic | F、タイトル昇順、A 新題=龥 changed A | B→A 選択で詳細更新 | B に A の年・巻数・出版社なし / A / (A,A,"1") | M: B 行混在 |
| detail_year_mutation_atomic | F、年昇順、A 年=2030 | B→A | C は 2025 / 0003 / PUB:C / 選択 A / (A,A,"1") | M: C 行混在 |
| detail_count_mutation_atomic | F、巻数昇順、A 巻数=20 | B→A | B の出版社は PUB:B / A / (A,A,"1") | M: B の出版社が A |
| restore_sort_on_update_error | F、sorting=True / False、任意列方向 | 2 セル目で制御例外。別例で rollback も失敗 | 原状態復元、他行不変。rollback 失敗は FAILED / 空 / - | U。finally・失敗復元の正式試験 |
| selection_preserved_after_sort | F、各列の両方向、A 選択 | 詳細の sort key 変更→layoutChanged | current item と ID を維持、同一候補の全セル / A / (A,A,"1")、詳細取得 1 回 | M: ID は維持、全セルは条件により FAIL |

Issue.update_row も番号・日付の変化で同等のパラメーター試験を加える。I(X,B) / I(Y,B) の番号順が入れ替わっても Y の題名が X の内容にならないことを固定期待値で判定する。

### 空状態

| テスト名 | 固定入力・事前状態 | 操作と完了順 | 期待表示 / 選択 / 最終引数 | 修正前 |
|---|---|---|---|---|
| empty_refresh_clears_selection | A の詳細・リンクあり | 空 Series 応答→イベント処理 | rowCount=0、CLEAR / 空 / - | M: A 詳細・リンク残留、OK は無効 |
| empty_issue_result_clears_selection | A の Issue 採用後に B を要求 | B の空応答→OK / done / double click | CLEAR、initial_id="" / 空 / - | M: A が残り A/B fetch |
| selection_removed_by_filter | F、A 選択 | 出版社全除外、または文字列不一致→フィルター解除 | 除外中 CLEAR、文字列では元データ保持。解除だけで旧確定を復活させない / 空 / - | M: 出版社で旧詳細、文字列で旧選択・OK |

### 互換性

| テスト名 | 固定入力・事前状態 | 操作と完了順 | 期待表示 / 選択 / 最終引数 | 修正前 |
|---|---|---|---|---|
| jp_id_bridge | 実 JP Talker、BookRecord A〜E、source Mock | 検索→Series→Issue→最終取得 | record.id 維持。正常 B/B は B、意図的 A/B は既存契約で A | M: PASS |
| direct_series_accept | F、Issue 未確定 | B を選択→Series OK | B 詳細 / B / ("",B,"")。番号ヒントありの別例も追加 | M: 空番号例 PASS |
| auto_match_dispatch | 新 IssueResult(Score, series B, md B) | update_match→B 応答→Issue OK | B / B / (B,B,"1")。旧応答併存も token 条件を適用 | M: 正常例 PASS、競合併用 U |
| unrelated_talker_metadata | X/B・Y/B、任意 publisher / title / image、series_id=None の例、欠落 / 重複 ID | API fixture 完了→可視候補選択→OK | 無関係な metadata を変えず有効候補だけ受入。不明瞭 ID はエラーまたは選択不可 / 有効 ID / 元の正当な引数 | U |

### 決定性と teardown

- threading.Event で「開始済み」と「応答を解放してよい」を別々に制御する。ワーカー順序を sleep で作らない。
- QTest で行クリック・Cancel・OK を操作し、QSignalSpy で terminal / finished / destroyed を観測する。タイムアウトは失敗検出だけに使用。
- 各条件は新しい window / context で開始。ソート状態を明示し、同値キーの安定性を期待 ID の根拠にしない。
- failure 時も finally ですべての gate を解放、管理 worker を終了まで保持、wait に期限を設けて成功を assert、GUI の queued / deferred deletion を処理する。
- wait が失敗した worker を deleteLater / GC で破棄しない。テスト用の独立 subprocess を親側から異常終了扱いにする。これは製品で terminate を使う設計とは別。
- テスト用一時領域の SQLite 接続は対象パスを確認して閉じてから削除する。利用者のキャッシュや設定を読まない。
- 正常終了だけでなく、処理失敗・受信先破棄・アプリ終了待ちを正式受入に含める。
- 実書籍の writer を呼ばない。最終取得引数と返却 metadata までを実コード + Mock で検証する。

## 24. Upstream Contribution Strategy

公式 GitHub の Issue 検索で sort / stale / cancel / "wrong series" / empty / columns、PR 検索で sort / cancel を調査した。検索結果だけで不存在を証明せず、関連報告と open PR の変更ファイルも確認した。

| 既存報告・PR | 今回との関係 |
|---|---|
| [#475][U-475] / [#488][U-488] | 年・巻数の数値ソート。今回の更新途中の行混在とは別 |
| [#547][U-547] | ソート可能な item と数値表示の復元。sorting guard / 要求世代の修正なし |
| [#784][U-784] / [#708][U-708] | beta.6 の Issue 取得停止・rate limit 関連。コメントは beta.7 で修正済みとしている。今回 beta.9 / develop の旧応答混入と同一原因とは確認できない |
| [#849][U-849] | autotagmatchwindow の静的な列対応。Series の動的 row 問題とは別 |
| [open #847][U-847] | 通知ダイアログの queue。要求世代・行更新の修正ではないが、通知処理との競合に注意 |
| [open #775][U-775] | plugin revamp。対象 Series / Issue では import 等の変更。今回の原因への修正なし。将来の API 互換性は別調査 |

照会時の open PR は #855、#852、#850、#848、#847、#844、#838、#775 の 8 件。各 PR の変更ファイルを読み取り、最大 75 ファイルで API の 100 件上限内だった。今回の 3 原因の直接修正は見つからない。未マージ PR を検証対象へ混ぜていない。検索範囲外の説明・別表現の報告まで不存在とは断定しない。

新規提案の候補は、旧 Issue 応答、ソート途中のセル混在、空選択残留の 3 問題に分ける。空 Issue の誤取得は旧応答問題と似るが原因が異なるため、明示的な別再現として記載する。Series 世代管理は別の追補・PR とする。投稿直前に重複を再確認し、同一原因の既存報告が見つかればそこを参照して新規重複投稿を避ける。

対象ブランチは **develop**。最新安定版 1.5.5 は JP の最低対応版より古く、今回の修正基点にしない。beta.9 backport は develop での契約受入後に必要性・配布主体を判断する。beta.10 や develop への更新だけで今回の問題が解消するとは案内しない。JP の全体互換性も未検証なので、利用者へのホスト更新推奨は HOLD。

## 25. GO / HOLD / NO-GO Decision

GO は **I2 の実装へ進める設計判断**。修正済み・リリース可能・今回実装した、という意味ではない。

| 判断対象 | 判定 | 根拠 / 次工程の受入条件 |
|---|---|---|
| 最新版取得 | GO | API / clone / 再照会で SHA 固定 |
| 実行コード同一性 | GO | 86 モジュールのパス・内容一致。distribution 表示との差も開示 |
| A: セル混在 | GO | REPRODUCED。原子化・例外契約を確定 |
| B: 旧 Issue 応答 | GO | REPRODUCED。token と receipt、registry・終了境界を含む U1 が必須 |
| C: 空状態残留 | GO | REPRODUCED。空 Issue は取得対象にも影響。U1 / U2 で受入を分担 |
| Issue token | GO | 同一 ID 再要求も新 generation |
| Worker lifetime | GO（設計） | 保持・finished・join・deleteLater の契約と分離実験。製品での全終了入口接続が必須 |
| Cancel / Close | GO（設計） | 無効化と停止要求を分離。後着 UI 適用を禁止 |
| 同一 Series 再要求 | GO | 新旧応答混入を実測、ID 単独比較を不採用 |
| Final accept | GO（設計） | 現行結果集合・親 epoch・可視性・receipt |
| Series search | GO | 静的原因と制御実験、独立 U4 |
| Row update | GO（設計） | sorting 保存復元、item 保持、epoch、失敗時 rollback |
| Empty state | GO（設計） | 所有者・イベントごとのクリアと確定条件を確定 |
| API の形の互換性 | GO | 公開 API と metadata 型は同一。内部 IssueResult の差は adapter で対応 |
| JP / 他 Talker の配布物全体 | HOLD | 依存を満たしたビルド・通常 GUI・複数 Talker の統合確認が必要 |
| 回帰テスト | GO | 固定 fixture、Event、明示期待値、失敗時 teardown を定義 |
| upstream 対応 | GO（提案準備） | 今回調べた範囲で直接重複なし。投稿前に再確認 |
| JP 側の ID 差し替え回避 | NO-GO | 正常な issue 優先契約を壊し、GUI の原因を解消しない |
| Source order 新機能 | HOLD | 整合性修正とは独立。今回の修正受入後に前工程へ戻る |

NOT_NEEDED に該当する問題はない。I2 で worker の管理や終了入口を省略する案へ変わる場合、B / U4 は HOLD に戻す。単に disconnect する変更だけを安全な完了条件にしない。

## 26. Open Questions and Implementation Handoff

I1 の結論と契約は確定した。残るのは、未実装の契約を製品内で検証する I2 / I3 と、配布互換性を確認する I4 である。

1. I2 は固定 develop の別作業ツリーで開始する。今回の checkout や JP ソースをそのまま改変する作業ではない。
2. registry が管理する対象は Series / Issue の検索 worker。最終取得、画像、バッチ処理の既存 thread 管理全体を無条件に置換しない。アプリ終了の drain では既存管理との調停が必要。
3. App 終了・例外 Abort・親破棄の各入口を正式 GUI 試験で確認する。分離実験の成功を統合済みと扱わない。
4. 同期詳細 API 内の再入、QWebEngine の表示、後着画像、複数 Issue の row 更新は追加回帰が必要。今回の詳細 UI は QTextEdit。
5. 異なる issue / series ID、series_id 欠落、重複 ID の方針を他 Talker fixture で確認する。実ネットワーク検索は必要条件にしない。
6. develop を正式ビルドする隔離環境では setup.cfg の依存と generated resources を用意する。既存 .venv / .tools/venv-py314-codex を上書きしない。
7. 配布対象の Python / Qt、正式版への反映、beta.9 backport、upstream の採用判断は未確定。現在の利用者に更新のみで解決すると案内しない。
8. 実装前に upstream HEAD / open PR を再確認する。新たな直接修正が入った場合はその問題の U1〜U4 を再評価し、重複実装しない。

### 検証用ロード補助とコードの再利用

前工程文書の最小再現コードより前に、次の補助を置いた。ホストの製品関数を置換するコードではない。

~~~python
import sys, types
from pathlib import Path

source = Path(".tools/research-comictagger-develop").resolve()
assert not any(
    name.startswith(("comictaggerlib", "comicapi", "comictalker"))
    for name in sys.modules
)
sys.path.insert(0, str(source))
generated = types.ModuleType("comictaggerlib.ctversion")
generated.__file__ = "<in-memory build version for fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3>"
generated.version = "1.6.0b11.dev58"  # 実験用ラベル。distribution の測定値ではない
sys.modules[generated.__name__] = generated
~~~

R1 は前工程の create / choose / complete / evaluate を再利用し、次の 3 条件を各 3 回、新しい window で実行した。

~~~python
for repeat in range(3):
    for column, changes in (
        (0, {"name": "龥 changed A"}),
        (1, {"start_year": 2030}),
        (2, {"count_of_issues": 20}),
    ):
        w, talker, data, expected, calls = create()
        w.twList.sortItems(column, ASC)
        choose(w, "NDL-B")
        expected["NDL-A"] = replace(
            expected["NDL-A"], description="DETAIL:NDL-A:v1", **changes
        )
        choose(w, "NDL-A")
        print(evaluate(w, expected), snap(w), complete(w, talker, calls))
        w.hide()
~~~

R2 は前工程の Event / QThread シナリオを range(3) にした。R3 は create → choose(A) 後、空リストまたは全出版社をフィルター対象にして search_complete を呼び、イベント処理後に snap、lblSeriesLink、OK / Issues、追加 fetch 数を記録した。

同一 Series の追加ケースでは 1 回目と 2 回目の API 呼び出しを別 Event に割り当て、OLD / NEW を返した。エラー条件では OLD の返却だけを TalkerError に置換。空 Issue 条件は A の実 query_finished を終えた後、B の fetch_issues_in_series に [] を返し、実 OK と最終 QueryThread を通した。期待値は 23 節のとおりで、旧 ID の採用を正常とは判定していない。

### 完了時の検証

- git status --short、git diff --check、新規文書に対する git diff --no-index --check を実施。
- UTF-8、末尾空白、改行、掲載 Python の構文、固定 Source URL のパス・行番号を検査。
- 開始時の 133 ファイルのハッシュを照合し、既存 2 文書・Production code・既存テストは未変更。
- 旧 checkout は HEAD 57e5571c91c7515ee2cd594da6c780e61b056b15、clean のまま。
- 新 checkout は HEAD fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3、clean。Git 管理対象外で調査用に保持。
- .tools/pytest-tmp は管理対象外。今回の一時領域は残留なし。
- ステージ・コミット操作なし。今回の成果物は本書だけ。

終了時の Git 状態:

~~~text
?? docs/ndl-gui-search-order-investigation.md
?? docs/ndl-gui-selection-integrity-i1-design.md
?? docs/ndl-gui-selection-integrity-investigation.md
~~~

### Source References

以下の D-* は develop の固定 SHA、B-* は beta.9 の固定 SHA、J-* は JP の HEAD に固定する。URL のパス・行番号は対応するローカル Git オブジェクトで検証した。GitHub API の可変 branch / PR 情報は 4・24 節の照会時点の記録である。

[J-project]: https://github.com/karigane-cha/comictagger-jp-talker/blob/d186c8e776a0a7ea6cf70d6da056027cc7fb258d/pyproject.toml#L13
[J-talker]: https://github.com/karigane-cha/comictagger-jp-talker/blob/d186c8e776a0a7ea6cf70d6da056027cc7fb258d/comictagger_jp_talker/talker.py#L30
[U-branch]: https://api.github.com/repos/comictagger/comictagger/branches/develop
[U-head]: https://github.com/comictagger/comictagger/commit/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3
[U-beta10]: https://github.com/comictagger/comictagger/releases/tag/1.6.0-beta.10
[U-stable]: https://github.com/comictagger/comictagger/releases/tag/1.5.5
[B-series]: https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictaggerlib/seriesselectionwindow.py#L346
[D-series]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictaggerlib/seriesselectionwindow.py#L359
[B-issue]: https://github.com/comictagger/comictagger/blob/57e5571c91c7515ee2cd594da6c780e61b056b15/comictaggerlib/issueselectionwindow.py#L99
[D-issue]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictaggerlib/issueselectionwindow.py#L104
[D-tagger]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictaggerlib/taggerwindow.py#L1235
[D-match]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictaggerlib/matchselectionwindow.py#L99
[C-webengine]: https://github.com/comictagger/comictagger/commit/9cb72561af52e4238d8aabf2cfe65caec653ad00
[C-result]: https://github.com/comictagger/comictagger/commit/512b45b7f7a070b3521633ce84ea719d41fc58dd
[C-dialog]: https://github.com/comictagger/comictagger/commit/51d4a4849cde7398c9fd5a05a930a7bc442546f8
[C-tpb]: https://github.com/comictagger/comictagger/commit/d85a8ba4b5990daf5d9e27899225e5fa47ed4ae1
[C-columns]: https://github.com/comictagger/comictagger/commit/ef7f367fa3d8f42e253adde4690c47d79c1e7905
[D-project]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/pyproject.toml#L15
[D-cover]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictaggerlib/coverimagewidget.py#L118
[D-api]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictalker/comictalker.py#L172
[D-metadata]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comicapi/genericmetadata.py#L130
[D-result]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictaggerlib/resulttypes.py#L21
[D-auto]: https://github.com/comictagger/comictagger/blob/fa11a3456cbe5aa9f54f47bdc374ba26b2b946f3/comictaggerlib/autotagprogresswindow.py#L173
[Q-object]: https://doc.qt.io/qt-6/qobject.html#disconnect
[Q-thread]: https://doc.qt.io/qt-6/qthread.html#finished
[Q-table]: https://doc.qt.io/qt-6/qtablewidget.html#setItem
[U-475]: https://github.com/comictagger/comictagger/issues/475
[U-488]: https://github.com/comictagger/comictagger/pull/488
[U-547]: https://github.com/comictagger/comictagger/pull/547
[U-784]: https://github.com/comictagger/comictagger/issues/784
[U-708]: https://github.com/comictagger/comictagger/pull/708
[U-849]: https://github.com/comictagger/comictagger/pull/849
[U-847]: https://github.com/comictagger/comictagger/pull/847
[U-775]: https://github.com/comictagger/comictagger/pull/775
