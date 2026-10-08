# 検証記録

## v0.3.0 Release 前の再検証

2026-10-05 (JST)。`feat/phase2c1-series-supplement` の未コミット Phase 2C-1 と release-blocker 修正を最終監査した。
基点と origin/main は正式 v0.2.1 の commit `ec9ad62882df51f228299efe83868fa0e0c805f7`。
canonical version は `comictagger_jp_talker/__init__.py` の 0.3.0、pyproject.toml の dynamic version を維持する。
production logic と tests は変更せず、README と実装・検証文書だけを Release 状態へ整理した。

監査で、ja / 根拠のあるタグなし文字列は display、ja-hrkt は reading、未対応 language / datatype は other と確認した。
raw RDFTerm / language / datatype / Series URI / predicate path を保持し、同一 URI の同一 display だけを有効値として重複除去する。
認識済み reading だけで MULTIPLE にせず、異なる URI と異なる display の曖昧性は維持する。
setting は `jpbooks_madb_series_supplement`、label は Supplement missing Series from MADB (experimental)、既定 False。
保存・復元、旧 config の key 欠損、CLI、非 boolean 拒否を既存 tests で再確認する。

補完は利用者の opt-in、選択済み最終 fetch、欠損 NDL Series、exact / safe strong、一意かつ完全な display の場合だけ。
変更は Series と最小限の provenance Notes だけで、NDL Series と他の GenericMetadata fields を維持する。
optional な NDL summary と MADB supplement は fail-open、SRU 本体は必須で失敗時 fatal。
候補の概要 network は 0、最終取得だけ必要時に最大 1。失敗の 7 日永続保存と自動 retry は行わない。
bounded in-memory suppression は最大 128 ID、Retry-After を尊重する。NDL limiter は 1 request / 2 sec のまま。
MADB は lightweight Book / Series retrieval、Agent / Holding は NOT REQUESTED、full API と共通 identity 判定を維持する。
既存 fixture の cold cache は full 6 → lightweight 3、Agent 2 → 0、Holding 1 → 0、warm cache は 0。
MADB limiter は 1 request / 3 sec のまま。並列要求と automatic retry は行わない。

### 検証方法と実資料の制限

NDL / MADB の実 endpoint で linkage と Series classification を確認し、M381096 / C334830 の BOTH_AGREE を検査する。
報告書誌 R100000002-I025375656 は、2026-10-03 の実確認で fetch_series 概要 0、最終取得概要 1、HTTP 200。
今回は deterministic な mock を中心に検査し、実 endpoint suite は最後に 1 回だけ実行した。
NDL Series 欠損かつ安全な MADB display が一意という実資料の end-to-end 補完成功例は未確認。
補完の成功経路は synthetic fixture / HTTP mock / built-plugin integration で検証する。

### 今回のローカル検証と配布物

| 検証 | 結果 |
|---|---|
| Ruff | **All checks passed** |
| repository format | **10 files would be reformatted / 43 files already formatted**。既存 baseline を維持 |
| changed Python format | **19 files already formatted** |
| focused regression | NDL / summary policy / Talker / supplement / lightweight MADB / linkage、**418 passed**、6.62 秒 |
| non-network suite | **1375 passed / 1 skipped / 13 deselected / 1 xfailed**、11.69 秒。失敗 0 |
| packaging / isolated host | clean build 後の実 ZIP で **2 passed**、13.61 秒。上記 skip 対象も成功 |
| git diff --check | **成功** |
| clean build | **成功**。安全な root / 絶対パス確認後、旧 dist / build / generated egg-info だけを清掃し、隔離 build で sdist → wheel |
| wheel / sdist | 各 1 件を自動検出。Name=comictagger-jp-talker、Version=0.3.0 |
| plugin ZIP | 既存 scripts/build_plugin.py の actual CLI で生成、**62,136 bytes**、testzip()=None、METADATA 1 件、entry point 正常 |
| source equality | wheel / sdist / ZIP の production Python **17 ファイル**が作業ツリーと byte 単位で完全一致 |
| ZIP 内容 | 必要な Talker / summary / lightweight MADB / linkage / provenance / supplement / mapping modules を含む。tests / research / .git / __pycache__ / .pyc は含まない |
| built ZIP 回帰 | beta.9 load、default OFF、候補 summary 0、final summary 429 fail-open、exact / strong 補完、Agent / Holding 0 が成功 |

skip は clean build 前に旧 ZIP を削除したための配布物テスト。xfail は既知 CIX writer の Volume=0 省略。
通常 suite の外部 HTTP は既存 fixture で禁止した。既知の sandbox 一時領域・配布物読み取り・依存取得の制約を避け、
pytest / build / ZIP 検証は許可された実行環境を使用した。
ZIP SHA-256: `1d05206983a500c219d35a2d1aed2311db771d24742301a55bfc32a51002fba5`。
生成物は `dist/comictagger_jp_talker-0.3.0-py3-none-any.whl`、`dist/comictagger_jp_talker-0.3.0.tar.gz`、
`dist/jpbooks_talker-plugin-0.3.0.zip`。Release asset は plugin ZIP のみで、wheel / sdist / PyPI の公開は行わない。

候補 summary 要求数は search_for_series / fetch_series / fetch_issues_in_series /
fetch_issues_by_series_issue_num_and_year が各 **0**、fetch_comic_data は必要時だけ **最大 1**。
SRU abstract と summary cache があれば **0**。報告 ID の 429 sequence は **1 要求 / metadata 成功**、
即時の次の fetch は追加要求 **0**。timeout / 503 / malformed response と SRU fatal の境界も成功した。
MADB の one-candidate fixture は cold **3 要求**、Agent / Holding **0**、warm cache **0**。

最終 network suite は non-network と packaging 成功後に **1 回だけ**実行し、
**13 passed / 1377 deselected**、140.68 秒。失敗と再実行なし。JPBOOKS_RUN_NETWORK_TESTS は終了後に解除した。
報告 ID R100000002-I025375656 は fetch_series 概要 **0**、final fetch 概要 **1**、
DETAIL_ENDPOINT は **HTTP 200 / Retry-After なし**、Summary あり。実 429 を再現するための追加要求は行っていない。
M381096 / C334830 は matched / strong、表示 `ご注文はうさぎですか?`（タグなし）と
読み `ゴチュウモン ワ ウサギ デスカ`（ja-hrkt）を保持し、effective display 1 件、**BOTH_AGREE**。
full MADB API の direct identity M1032568 は exact / NDL_ONLY を維持した。

| Phase 1 回帰 | Series / 論理巻 | 結果 |
|---|---|---|
| My Girl. vol.31 | My Girl / 31 | synthetic + 実 NDL 成功 |
| ご注文はうさぎですか? : アンソロジーコミック. volume 1 | ご注文はうさぎですか? : アンソロジーコミック / 1 | synthetic + 実 NDL 成功 |
| ご注文はうさぎですか? = Is the order a rabbit? 7 | ご注文はうさぎですか? / 7 | synthetic + 実 NDL 成功 |
| ブルーロック = BLUELOCK. 1 | ブルーロック / 1 | synthetic / audit 成功 |

検証後の最終変更は文書だけとし、production / tests / fixtures **56 ファイル**の byte hash を保持する。
文書の実測値追記では pytest 全実行を繰り返さず、hash の不変と git diff --check を確認する。
ローカル測定後に README / production / tests は変更せず、Release commit の公開 ZIP は別途ダウンロードして検証する。
正式公開状況は [v0.3.0 Release](https://github.com/karigane-cha/comictagger-jp-talker/releases/tag/v0.3.0) と
[GitHub Actions](https://github.com/karigane-cha/comictagger-jp-talker/actions) を参照する。

## 0.3.0 未公開 release-blocker 修正

2026-10-02 開始、2026-10-03 (JST) 最終検証。実利用の `R100000002-I025375656` で fetch_series と
fetch_comic_data がともに概要 JSON endpoint を呼び、HTTP 429 でメタデータ取得全体が失敗した。
未公開 Phase 2C-1 の blocker として修正し、version は 0.3.0 を維持する。

NDL の原因は get が概要を暗黙に取得し、概要の Network / Data error を必須 SRU と同じ fatal 経路へ渡したこと。
429 応答はキャッシュされず、次の caller でも要求が発生した。MADB の別の原因は補完が full get を使い、
Series のために creator / publisher Agent と provider Holding の詳細まで取得していたこと。

修正前に外部通信なしの HTTP mock で 5 host paths の cold / cache を計測した。
SRU abstract なし、同一 ID、概要 success cache なしでの DETAIL_ENDPOINT 要求数は次のとおり。

| path | 修正前 | 修正後 |
|---|---:|---:|
| search_for_series | 0 | 0 |
| fetch_series | 1 | 0 |
| fetch_issues_in_series | 1 | 0 |
| fetch_issues_by_series_issue_num_and_year | 1 | 0 |
| fetch_comic_data | 1 | 1 |
| fetch_series → fetch_comic_data、概要 200 | 1 | 1 |
| fetch_series → fetch_comic_data、概要 429 | 2、両方 fatal | 1、NDL metadata 成功 |

cold SRU は各単独 path で 1 要求、同一 query / record の SRU cache hit は 0。標準 sequence も SRU は合計 1。
正常な概要 cache hit では各 fetch の DETAIL_ENDPOINT 要求は修正前・修正後とも 0。
報告書誌 ID を使った mock でも fetch_series は概要 0、final fetch は 1、429 後の即時 final fetch は追加 0。
基本 GenericMetadata の全 fields、書誌 ID、NDL 出典、Series / title / volume / ISBN / 日付等を維持する。
429 の status / Retry-After / ID / endpoint は warning に残し、latest-error.txt を生成しない。
503 / timeout / ConnectionError / generic requests error / invalid JSON / envelope / wrong ID / item も同じ境界を検証する。
成功・正常な概要なしの 7 日キャッシュは維持し、失敗の永続保存と自動再試行は行わない。
128 ID 上限のメモリ抑止、期限切れ、Retry-After 秒数 / HTTP-date、再生成時に失敗状態を持ち越さないことを確認する。
SRU 429 / timeout / invalid XML は fatal、内部 AttributeError / TypeError / assertion は伝播する。

MADB の relation を持つ既存 fixture で cold **6 → 3 要求**、Agent **2 → 0**、Holding **1 → 0**。
新 API は MADBSource.get_for_series_linkage / link_ndl_record_for_series、bundle は retrieval_scope=`series_linkage`。
必要な whole Book / Series の raw identity・名称・完全性を取得し、他の relation 詳細は NOT REQUESTED。
full get / link_ndl_record、identity algorithm、default OFF、NDL Series 優先、分類と eligibility は維持する。
NDL 2 秒 / MADB 3 秒の limiter は変更せず、並列要求と automatic retry は追加していない。
実装の詳細は [Phase 2C-1 の performance boundary](phase2c1_series_supplement.md) を参照する。

### 修正後の検証と配布物

| 検証 | 結果 |
|---|---|
| 追加テスト | 新規 non-network **58 件**、報告書誌の live check **1 件**。旧候補経路の補完成功 4 ケースを削除し、候補の optional 通信禁止へ更新 |
| focused regression | NDL / Summary / Talker / Series supplement / linkage / MADB、**418 passed**、6.83 秒 |
| non-network suite | **1375 passed / 1 skipped / 13 deselected / 1 xfailed**、12.73 秒。失敗 0。skip は旧 ZIP 削除後、build 前の配布物テスト |
| built ZIP packaging tests | build 後に **2 passed**、13.74 秒。上記 skip 対象も実 ZIP で成功 |
| Ruff | **All checks passed** |
| repository format | 開始 **10 mismatch / 41 formatted**、終了 **10 mismatch / 43 formatted**。既存 mismatch は変更していない |
| changed Python format | **19 files already formatted** |
| git diff --check | **成功** |
| clean build | **成功**。安全な絶対パス確認後に旧 dist / build / generated egg-info を削除、通常の隔離 build で sdist → wheel |
| wheel / sdist / ZIP | Name=comictagger-jp-talker、Version=0.3.0。wheel / sdist は各 1 件を自動検出し、既存 scripts/build_plugin.py の CLI を使用 |
| ZIP validation | **62,147 bytes**、testzip()=None、entry point と必要 modules を確認、tests / research / .git / __pycache__ / .pyc なし |
| source equality | wheel / sdist / ZIP 内の production Python **17 ファイル**が作業ツリーと byte 単位で一致。ZIP と wheel も同一 |
| isolated host | beta.9 loader 後の ZIP を使用。load、default OFF、候補の summary 0、summary 429 fail-open、exact / strong 補完、Agent / Holding 0 を確認 |

ZIP SHA-256: `b5026333837434eb99995b01e71dd746dae077418d83305b1f103d9e09bae79f`。
配布物は dist 内の `comictagger_jp_talker-0.3.0-py3-none-any.whl`、
`comictagger_jp_talker-0.3.0.tar.gz`、`jpbooks_talker-plugin-0.3.0.zip`。
通常 suite は外部 HTTP 禁止。最初の sandbox 実行は pytest 一時領域へのアクセス拒否、build は隔離環境の依存取得で失敗し、
権限を上げた実行で検証・build を完了した。旧 artifact の削除と生成 wheel の読み取りにも同じ sandbox 制約があった。
既知 xfail は CIX writer の Volume=0 省略。無関係な format baseline と Phase 1 mapping は変更していない。

default OFF、ON + NDL Series、exact / safe strong、ambiguous / unsafe / truncated / unavailable、
display + reading / reading-only / multiple display / multiple Series URI の回帰は成功。
My Girl. vol.31 → My Girl / 31、
ご注文はうさぎですか? : アンソロジーコミック. volume 1 → 同作品名 / 1、
ご注文はうさぎですか? = Is the order a rabbit? 7 → ご注文はうさぎですか? / 7、
ブルーロック = BLUELOCK. 1 → ブルーロック / 1 は既存 synthetic / audit で個別に成功。

最終 network suite は non-network / built ZIP 検証後、許可された通信環境で **1 回だけ**実行した。
**13 passed / 1377 deselected**、89.74 秒。失敗と再実行なし。終了後に JPBOOKS_RUN_NETWORK_TESTS を解除した。
報告書誌 `R100000002-I025375656` は fetch_series の DETAIL_ENDPOINT 要求 **0**、
fetch_comic_data は **1**、概要 endpoint は **HTTP 200 / Retry-After なし**で Summary を取得した。
429 は今回実 endpoint では観測せず、元の報告 ID と built ZIP の HTTP mock で fail-open と即時重複抑止を確認した。

軽量 linkage の実 endpoint でも M381096 → C334830 は matched / strong、**BOTH_AGREE**。
raw `ご注文はうさぎですか?`（タグなし）と `ゴチュウモン ワ ウサギ デスカ`（ja-hrkt）を保持し、
effective display は前者 1 件。full API の M1032568 direct identity は exact / NDL_ONLY を維持する。
Phase 1 の My Girl. vol.31、アンソロジーの volume 1、並列タイトルの 7 は実 NDL でも成功。
ブルーロック = BLUELOCK. 1 は今回 synthetic / audit の検証で、追加の実通信は行っていない。

最終境界: Version=0.3.0。NDL SRU は REQUIRED / fatal on failure、概要 JSON は OPTIONAL / fail-open。
fetch_series summary network は NO、final selected fetch は AT MOST ONCE when needed。
MADB Series supplement は OPT-IN / DEFAULT OFF、NDL Series overwrite は NO、
MADB retrieval は LIGHTWEIGHT / NO AGENT / NO HOLDING。両 limiter は UNCHANGED、automatic retry は NO。
Imprint mapping / Credits merge / Publisher merge / Date merge / general automatic metadata merge は NOT IMPLEMENTED。
commit / merge / push / tag / Release / upload は NOT PERFORMED。変更は未コミット。

## 0.3.0 development / Phase 2C-1 初回検証（blocker 修正前）

2026-10-02 (JST)。開始時の main は clean。fetch / fast-forward pull 後も
main / origin/main / v0.2.1 は `ec9ad62882df51f228299efe83868fa0e0c805f7` で、左右の差分は 0 / 0。
`feat/phase2c1-series-supplement` を作成し、canonical version の
`comictagger_jp_talker/__init__.py` だけで **0.2.1 → 0.3.0** に更新した。
pyproject.toml の dynamic version、Phase 1 mapping、NDL source、MADB models / queries は変更していない。
変更は未コミット。commit / push / tag / Release / upload は行っていない。

分類と補完の規則は [Phase 2C-1 実装記録](phase2c1_series_supplement.md) を参照する。
Phase 2A / Phase 2B-1 と research evidence は変更せず、Phase 2B-2 には後続実装への注記だけを追加した。

### 最新のローカル結果

Windows / CPython 3.12 / ComicTagger 1.6.0b9。PATH に python がないため
`.venv/Scripts/python.exe` を使用。一時領域と pytest cache は今回専用の `.tools/pytest-2c1-*`。

| 検証 | 結果 |
|---|---|
| 新規 unit / HTTP mock tests | `tests/test_series_supplement.py` の **92 件**。分類、raw / duplicate、設定と旧 config、全 fetch の通信抑止、eligibility、Notes、不変 fields、transport 障害、cache / close |
| Ruff check | **All checks passed** |
| repository-wide format check | 開始時 **11 files would be reformatted / 37 files already formatted**。最終 **10 files would be reformatted / 41 files already formatted**。既存 mismatch を全体成功と扱わない |
| 変更 Python files の format check | 新規 2 件を含む **11 files already formatted** |
| non-network pytest | **1322 passed / 12 deselected / 1 xfailed**、21.71 秒。skip / warning なし。外部 HTTP は既存 autouse fixture で禁止 |
| opt-in network pytest | **12 passed / 1323 deselected**、105.35 秒。rate limiter を維持し、終了後に環境変数を解除 |
| git diff --check | **成功** |
| clean package build | **成功**。隔離環境で sdist → wheel、setuptools 84.0.0 |
| artifact metadata | wheel / sdist / ZIP の Name=comictagger-jp-talker、Version=0.3.0 |
| plugin ZIP validation | **60,622 bytes**、testzip() は None、METADATA 1 件、entry point を確認 |
| current source equality | wheel / sdist / ZIP の **全 production Python 17 ファイル**が作業ツリーと byte 単位で一致 |
| isolated host test | `tests/test_packaging.py::test_built_zip_in_isolated_host`、**1 passed**、9.70 秒。全 non-network suite でも再確認 |
| built ZIP default OFF | beta.9 の実 loader 後に mock NDL lookup 成功、MADB POST を禁止、既存 Series / その他 output を維持 |
| built ZIP opt-in | 実 ZIP の source / parser / linkage を mock HTTP で通し、exact / strong の両方で Series + Notes だけ変更。2 回目の fetch は cache hit |

既存 format mismatch は mapping.py、docs/phase2_madb_spec.md、tests の test_comicinfo.py、test_madb.py、
test_madb_boundary.py、test_mapping.py、test_ndl.py、test_numbers.py、test_phase1_audit.py、test_talker.py。
今回変更した talker.py は format を確認し、混在していた改行を LF に統一した。無関係なファイルは整形しない。
xfail は既知の CIX writer の Volume=0 省略。source / assertion の失敗はない。

最初の network suite は sandbox の WinError 10013 で全件失敗した。通信許可後の上記実行は全件成功。
旧 dist の削除と生成 wheel の読み取りにも sandbox のアクセス拒否があり、
許可された環境で workspace 内の dist / build / generated egg-info だけを清掃し、build / ZIP / 照合を完了した。
通常 NDL 本体エラーの扱いは従来どおりで、optional MADB failure を `latest-error.txt` に混入させない。

### M381096 / C334830 の実 endpoint

NDL `R100000002-I023440575` の Series は `ご注文はうさぎですか?`。
ISBN discovery は matched / strong、conflict なし。

| C334830 の raw schema:name | language tag | 分類 |
|---|---|---|
| `ご注文はうさぎですか?` | なし | display |
| `ゴチュウモン ワ ウサギ デスカ` | `ja-hrkt` | reading |

effective display は `ご注文はうさぎですか?` の **1 件**。
v0.2.1 の reading-induced MULTIPLE から **BOTH_AGREE** に改善した。
raw 値 / language / Series URI / predicate path は保持し、reading を display の候補数に含めない。
M1032568 / R100000002-I033625982 は matched / exact、Series は NDL_ONLY のまま。
実 endpoint data の変化は今回観測していない。新しい network request は追加せず、既存 suite に分類の検査を統合した。

安全な NDL Series missing + MADB 一意 display の実補完成功例は確認できていない。
現行 NDL parser は非空 title を必要とし、Phase 1 mapper はそのタイトルから Series を保持する。
本体の規則を弱めず、実補完成功は synthetic / HTTP mock / built ZIP mock に留めた。

### Phase 1 回帰と GenericMetadata の境界

| title | Series / 論理巻 | 結果 |
|---|---|---|
| My Girl. vol.31 | My Girl / 31 | synthetic + 実 NDL 成功 |
| ご注文はうさぎですか? : アンソロジーコミック. volume 1 | ご注文はうさぎですか? : アンソロジーコミック / 1 | synthetic + 実 NDL 成功 |
| ご注文はうさぎですか? = Is the order a rabbit? 7 | ご注文はうさぎですか? / 7 | synthetic + 実 NDL 成功 |
| ブルーロック = BLUELOCK. 1 | ブルーロック / 1 | synthetic / audit 成功 |

OFF 時は固定 Phase 1 snapshot を全番号モードで確認。関連 search / fetch paths の MADBSource 生成は 0。
ON でも非空 NDL Series なら MADBSource 生成は 0。実補完時の dataclass 全 field 比較では差分は series / notes だけ。
title / issue / volume / counts / credits / publisher / imprint / date / gtin / Summary / tags / genres / language /
web_links / format / identifier / data_origin / series_id / issue_id とその他 fields は不変。
NDL / MADB source records、raw RDFTerm と statements は変更しない。
timeout / network / HTTP 503 / 429 / protocol / schema を search / Book / Series の各段階で mock し、
NDL metadata が正常に返り、warning が残り、補完 Notes と blocking error が生じないことを確認した。
ambiguous / unsafe / truncated（exact を含む）/ unmatched / reading-only / multiple display / multiple URI も非採用。

### 配布物

- `dist/comictagger_jp_talker-0.3.0-py3-none-any.whl`
- `dist/comictagger_jp_talker-0.3.0.tar.gz`
- `dist/jpbooks_talker-plugin-0.3.0.zip`

wheel / sdist は各 1 件を自動検出し、既存 scripts/build_plugin.py の actual CLI に wheel path を渡した。
ZIP と wheel は byte 単位で同一。ZIP SHA-256 は
`748ac5208dddb87d2f39fc9fa95129a7e0cb0da956ee986766c7bc5d8b5e633b`。
talker.py、linkage.py、provenance.py、series_supplement.py、mapping.py、MADB source modules をすべて含む。
tests / research datasets / .git / __pycache__ / .pyc は ZIP に含まれない。sdist は既存 MANIFEST policy に従う。
build artifacts と一時検証 helper は ignore 対象で、commit / stage していない。
配布物検証後の最終更新は本記録のみ。production / tests は変更せず、文書の spacing と diff を再確認する。

### Integration boundary

Normal source when supplement disabled: **NDL Search**。
MADB Series supplement: **OPT-IN / DEFAULT OFF**。NDL Series overwrite: **NO**。
NDL Series missing の補完: **YES, only under controlled eligibility**。
Imprint mapping / Credits merge / Publisher merge / Date merge / MangaWork /
General automatic metadata merge: **NOT IMPLEMENTED**。
Phase 2C-2 以降の候補は Imprint candidate policy、Credits comparison / supplement、Publisher comparison、
Date comparison、broader provenance-aware merge policy、user-facing diagnostics / source visibility、
根拠が得られた場合だけの weak-linkage research。今回これらは実装していない。

## v0.2.1 Release 前の再検証

2026-09-27 (JST)。`feat/phase2b2-linkage` の実装コミット
`4d6e4c328c4720664ef0a282162c82fa42dc26d2` を対象に、今回あらためて全検証を実行した。
開始時の作業ツリーはクリーンで、実装は origin の feature branch にも存在していた。
merge-base は v0.2.0 の commit `0fcaa7aff44782e75c294dd260c7d9be1f0555e8`。
local / remote の v0.2.1 tag が未作成であることを確認した。

package version は開始時・終了時とも **0.2.1**。正準定義は
`comictagger_jp_talker/__init__.py` の `__version__`、pyproject.toml の dynamic version を維持する。
今回は production logic、tests、workflow、version を変更せず、Release 用の文書だけを更新する。
すでにある実装コミットを再作成せず、文書の追加コミットを main へ fast-forward 統合する。

### 実装と境界の再確認

`linkage.py` の RecordMatch / LinkageResult / confidence / structured error、
`provenance.py` の FieldEvidence / SeriesComparison を source と tests で確認した。
v0.2.0 から mapping.py、sources/ndl.py、sources/madb.py と関連 source models / parser / queries、
talker.py に差分はない。Series 推定は既存 infer_volume / resolve_record_number を再利用する。

direct NDL URL は exact、一意な有効 ISBN は strong、重複候補は ambiguous、
別 NDL record への direct URL は unsafe。URL 一致と ISBN 不一致は exact identity と
ISBN conflict を同時保持する。正常 0 件の unmatched と取得失敗の unavailable を区別し、
truncated search から ISBN-only の一意性を主張しない。ISBN-10 / 13 の等価性は既存 utility を使う。

Series は NDL の推定値と MADB の schema:isPartOf → MangaBookSeries → schema:name を、
strip() と Unicode 完全一致だけで比較する。BOTH_AGREE / BOTH_CONFLICT / NDL_ONLY /
MADB_ONLY / NONE / MULTIPLE / UNAVAILABLE と、raw 値・record ID / URI・関連 URI・変換経路の
provenance 保持を検証した。意味的な名前分類や aggressive normalization は追加していない。

通常 Japanese Books の source は NDL Search のみ。自動 MADB access は **NO**。
固定 fixture と照合前後の GenericMetadata 比較で title / series / issue / volume / credits /
publisher / date / gtin / description / notes / web_links の output semantics が不変であることを確認した。
GenericMetadata MADB mapping、Series overwrite、Imprint mapping、Credits / Publisher / Date merge、
automatic metadata merge、MangaWork、title fuzzy linkage、Phase 2C は **NOT IMPLEMENTED**。

### 今回のローカル実測結果

Windows、CPython 3.12.14、ComicTagger 1.6.0b9。`.venv/Scripts/python.exe` を使用。
一時領域と cache は前回と別の `.tools/pytest-release021-*` に配置した。

| 検証 | 今回の結果 |
|---|---|
| `python -m ruff check .` | 成功 |
| `python -m ruff format --check .` | 既存 baseline の **11 files would be reformatted / 37 files already formatted**。全体成功とは扱わない |
| 変更 Python files の format check | `git diff --name-only v0.2.0..HEAD` から抽出した **6 files already formatted** |
| `python -m pytest -m "not network"` | **1230 passed / 12 deselected / 1 xfailed**、18.15 秒。skip なし。79 件の linkage synthetic / mock integration を含む |
| `JPBOOKS_RUN_NETWORK_TESTS=1 python -m pytest -m network` | **12 passed / 1231 deselected**、61.58 秒。今回の network suite は 1 回だけ実行 |
| pytest warning | **なし**。前回の cache 書き込み warning は新しい cache path では再現しなかった |
| `git diff --check` | 成功 |
| `python -m build` | clean build 成功。隔離環境で sdist → wheel を生成 |
| local artifact metadata | wheel / sdist / plugin ZIP の Name=comictagger-jp-talker、Version=0.2.1 |
| local plugin ZIP | **57,530 bytes**、archive.testzip() は None、METADATA は 1 件、jpbooks entry point を確認 |
| source equality | wheel / sdist / ZIP 内の全 production Python が作業ツリーと byte 単位で一致 |
| `tests/test_packaging.py::test_built_zip_in_isolated_host` | **1 passed**、9.67 秒。新しく build した ZIP で beta.9 load、通常 NDL lookup、optional linkage API を検証 |

変更 Python 6 ファイルは __init__.py / linkage.py / provenance.py / test_linkage.py /
test_linkage_integration.py / test_packaging.py。format baseline の 11 ファイルは
mapping.py、talker.py、docs/phase2_madb_spec.md、tests の test_comicinfo.py、test_madb.py、
test_madb_boundary.py、test_mapping.py、test_ndl.py、test_numbers.py、test_phase1_audit.py、test_talker.py。
既存の改行混在、リスト整形、文書内 code fence 等の差であり、Release のための一括整形は行わない。
既知の xfail は CIX writer の Volume=0 省略。source / test correctness の失敗はない。

### 実 endpoint と Phase 1 regression

| 実例 | 今回の結果 |
|---|---|
| M1032568 / R100000002-I033625982 | direct NDL URL と ISBN 一致、matched / exact、Series は NDL_ONLY |
| M381096 / R100000002-I023440575 / C334830 | ISBN discovery で matched / strong、Series は MULTIPLE |

C334830 の日本語表示名 `ご注文はうさぎですか?` と読み `ゴチュウモン ワ ウサギ デスカ` を両方保持した。
**同一 Series resource の複数名称による MULTIPLE であり、意味的に複数の Series relation があるという断定ではない。**
display name と reading の意味分類は Phase 2C 前に追加検討が必要で、今回 production code は追加しない。
network suite の既存 limiter を維持し、実行後に JPBOOKS_RUN_NETWORK_TESTS を解除した。

| NDL title | Series | 論理巻 | 再検証 |
|---|---|---|---|
| My Girl. vol.31 | My Girl | 31 | synthetic と実 NDL で成功 |
| ご注文はうさぎですか? : アンソロジーコミック. volume 1 | ご注文はうさぎですか? : アンソロジーコミック | 1 | synthetic と実 NDL で成功 |
| ご注文はうさぎですか? = Is the order a rabbit? 7 | ご注文はうさぎですか? | 7 | synthetic と実 NDL で成功 |
| ブルーロック = BLUELOCK. 1 | ブルーロック | 1 | synthetic / audit で成功 |

### 配布物と Release 手順

- `dist/comictagger_jp_talker-0.2.1-py3-none-any.whl`
- `dist/comictagger_jp_talker-0.2.1.tar.gz`
- `dist/jpbooks_talker-plugin-0.2.1.zip`

旧 dist / generated egg-info を workspace 内の検証済みパスだけで削除し、build 不在も確認した。
wheel / sdist を各 1 件だけ自動検出し、既存 scripts/build_plugin.py で ZIP を作成した。
linkage.py / provenance.py / mapping.py / MADB source を含む全 production source を照合済み。
tests、research data、.git、__pycache__、.pyc は ZIP に含まれない。build artifacts と
日本語 Release notes の一時ファイルは `.tools/` / dist の ignore 対象で、stage しない。

検証後の最終更新は本検証記録だけで、production Python / tests の不変性を差分で確認した。
この docs-only 更新のために pytest 全 suite は繰り返さず、git diff --check と最終 diff を再確認する。
main CI success 後に既存形式の annotated tag を作り、Release workflow で plugin ZIP のみを公開する。
公開後は curated notes とダウンロードした asset の内容・metadata を検証する。
CI と local ZIP の hash 一致は要求しない。
最終公開状況は [v0.2.1 Release](https://github.com/karigane-cha/comictagger-jp-talker/releases/tag/v0.2.1) と
[GitHub Actions](https://github.com/karigane-cha/comictagger-jp-talker/actions) を参照する。
以下の development 記録および Phase 2A / Phase 2B-1 の調査・実装履歴は保持する。

## 0.2.1 development / Phase 2B-2

2026-09-27 (JST)。開始時の作業ツリーはクリーン、main / origin/main / v0.2.0 は
`0fcaa7a`。fetch と fast-forward pull 後も最新であることを確認し、
`feat/phase2b2-linkage` を作成した。main は Release より後のコミットではなく、
Phase 2B-1 と Series 修正を含む Release 本体と同一だった。
GitHub API で v0.2.0 の draft=false / prerelease=false、
published_at=`2026-09-26T17:30:42Z` を確認した。
canonical version は `comictagger_jp_talker/__init__.py` の **0.2.0 → 0.2.1**。
pyproject.toml の dynamic version は変更していない。commit / push / tag / Release は実施しない。

追加内容と規則は [Phase 2B-2 実装記録](phase2b2_linkage.md) を参照。
`linkage.py`、`provenance.py`、synthetic / integration tests を追加し、
README と built ZIP load test を更新した。MADB source 4 ファイル、NDL source、
mapping.py、talker.py は差分なし。通常 GenericMetadata / ComicInfo.xml に MADB 値を反映しない。

### 環境と結果

Windows、CPython 3.12.14、ComicTagger 1.6.0b9。`.venv/Scripts/python.exe` を使用。
一時領域と pytest cache は `.tools/` 配下。network tests の rate limiter は有効のまま。

| 検証 | 結果 |
|---|---|
| 新規 synthetic / mock integration | 79 件。direct URL、ISBN 原文・正規化・10/13 等価性、重複、矛盾、失敗、切り詰め、Series 全 state、provenance、入力と metadata の不変性 |
| `python -m ruff check .` | 成功 |
| `python -m ruff format --check .` | 既存 baseline の 11 ファイルが整形対象。今回変更・追加した Python 6 ファイルはすべて成功 |
| `python -m pytest -m "not network"` | **1230 passed / 12 deselected / 1 xfailed**、19.12 秒。skip なし。xfail は既知の CIX Volume=0 省略 |
| `JPBOOKS_RUN_NETWORK_TESTS=1 python -m pytest -m network` | **12 passed / 1227 deselected**、120.77 秒。既存 NDL 8 件、MADB source 2 件、新規 linkage 2 件。終了後に環境変数を解除 |
| `git diff --check` | 成功 |
| `python -m build` | 隔離環境で sdist → wheel の生成成功。package metadata は 0.2.1 |
| plugin ZIP | 自動検出した単一 wheel から既存 scripts/build_plugin.py で生成成功 |
| 全 production source の比較 | wheel / plugin ZIP / sdist 内の package Python が作業ツリーと byte 単位で一致 |
| `tests/test_packaging.py::test_built_zip_in_isolated_host` | 成功。beta.9 loader と通常 NDL lookup、別の隔離プロセスでの linkage module import、MADB の POST 禁止を検証 |

format baseline は mapping.py、talker.py、docs/phase2_madb_spec.md、tests の
test_comicinfo.py、test_madb.py、test_madb_boundary.py、test_mapping.py、test_ndl.py、
test_numbers.py、test_phase1_audit.py、test_talker.py。既存の改行混在・リスト整形・
文書内 code fence 等で、対象は今回変更していない。
変更前は __init__.py も含む 12 ファイルであり、version 更新時に同ファイルの改行を LF に揃えた。

初回 network suite は sandbox の WinError 10013 で通信できず、許可後に全件成功した。
成功時に pytest cache の nodeids 書き込みで WinError 5 の警告が 1 件あったが、
endpoint / assertion の失敗はない。後続の non-network suite は別の cache で警告なし。
旧配布物の削除・build 成果物の読み取りにも sandbox のアクセス拒否があったため、
許可後に指定した生成ディレクトリだけを再清掃して build / 検証した。
最初の隔離 build は依存取得段階で失敗し、日本語エラー出力の decode error も発生した。
再実行は PYTHONUTF8=1 と通信許可を使用して成功した。
ZIP 検証では host が module 探索状態を復元した後の import が editable install を参照し得るため、
optional API の import / pure comparison と、通常の host load / NDL lookup を別プロセスで検証する。
host test の前に optional module を読み込まず、通常の発見経路を維持した。

### 実 endpoint での観測

| 組み合わせ | linkage | Series |
|---|---|---|
| M1032568 / R100000002-I033625982 | matched / exact。direct_ndl_url と isbn_normalized の両方を確認 | NDL_ONLY。MADB に Series relation なし |
| M381096 / R100000002-I023440575 | ISBN discovery から matched。ISBN-only の strong | C334830 の日本語名と ja-hrkt 読みを保持し MULTIPLE |

C334830 の比較 key は `ご注文はうさぎですか?` と `ゴチュウモン ワ ウサギ デスカ`。
NDL の推定 Series は前者と一致するが、言語選択を導入していないので BOTH_AGREE と断定しない。
BOTH_AGREE / BOTH_CONFLICT / NDL_ONLY / MADB_ONLY / NONE / MULTIPLE / UNAVAILABLE は
synthetic tests でそれぞれ確認した。取得元の原文と RDF language / datatype は保持する。

### Phase 1 regression と出力境界

| NDL title | 比較 layer の Series | 論理巻 | 結果 |
|---|---|---|---|
| My Girl. vol.31 | My Girl | 31 | 成功 |
| ご注文はうさぎですか? : アンソロジーコミック. volume 1 | ご注文はうさぎですか? : アンソロジーコミック | 1 | 成功 |
| ご注文はうさぎですか? = Is the order a rabbit? 7 | ご注文はうさぎですか? | 7 | 成功 |
| ブルーロック = BLUELOCK. 1 | ブルーロック | 1 | 成功 |

すべて既存 infer_volume / resolve_record_number と通常 mapping の結果を照合。
先頭 3 件は既存の実 NDL network regression も成功。ブルーロックは synthetic / audit で検証。
固定 Phase 1 fixture の全番号モードと、linkage 実行前後の GenericMetadata 全フィールドの不変性を確認した。
通常 Talker の自動 MADB access は NO。MADB mapping、Series overwrite、Imprint mapping、
Credits merge、automatic metadata merge は NOT IMPLEMENTED。

### 配布物

- `dist/comictagger_jp_talker-0.2.1-py3-none-any.whl`
- `dist/comictagger_jp_talker-0.2.1.tar.gz`
- `dist/jpbooks_talker-plugin-0.2.1.zip`

旧 dist / generated egg-info を安全に削除し、build の不在も確認した。
wheel / sdist は各 1 件、ZIP は 57,230 bytes、archive.testzip() は None。
METADATA Version=0.2.1、jpbooks entry point、RecordMatch / LinkageResult / FieldEvidence /
SeriesComparison、confidence / state definitions、URL / ISBN 比較、MADB source、修正済み mapping.py を確認。
tests、research data、.git、__pycache__、.pyc は ZIP に含まれない。
成果物と一時 helper は gitignore 対象で、ソース変更として追加していない。

Phase 2C の候補は controlled Series supplement、merge policy、provenance-aware field selection、
Imprint candidate evaluation、Credits comparison、利用者向け MADB integration policy。
今回は実装せず、開始条件は Phase 2B-2 文書に記載した。

## 0.2.0 の検証

2026-09-27 (JST)、正式 Release preparation で再実行した結果。
production の基準は main の `d352379`（Phase 2B-1 MADB foundation と Phase 1 Series 修正を含む）。
この preparation の変更は文書のみで、production Python、workflow、Phase 2A evidence は変更していない。
package version は **0.2.0**。正準定義は `comictagger_jp_talker/__init__.py` の `__version__`、
setuptools は `pyproject.toml` の dynamic version でこれを参照する。

### ローカル環境と結果

Windows、CPython 3.12.14、ComicTagger 1.6.0b9、comicinfoxml 0.5.1。
`.venv/Scripts/python.exe` を使用し、pytest の一時領域と cache を `.tools/` 内に指定した。

| 検証 | 今回の結果 |
|---|---|
| `python -m ruff check .` | 成功 |
| `python -m ruff format --check .` | 既存 baseline の 12 ファイルが整形対象、31 ファイルが整形済み。改行混在・既存のリスト整形・Phase 2A 文書内の Python code fence 等の差。今回それらは変更していない |
| `python -m pytest -m "not network"` | **1151 passed / 10 deselected / 1 xfailed**、18.56 秒。skip なし。xfail は CIX writer の `Volume=0` 省略 |
| `JPBOOKS_RUN_NETWORK_TESTS=1 python -m pytest -m network` | **10 passed / 1152 deselected**、80.20 秒。NDL 8 件、MADB 2 件。全 suite を 1 回実行し、環境変数は終了後に解除 |
| `git diff --check` | 成功 |
| `python -m build` | 成功。旧 dist / generated egg-info を削除、build 不在を確認してから隔離環境で sdist → wheel を生成 |
| `python scripts/build_plugin.py <自動検出した wheel>` | wheel / sdist が各 1 件であることを確認し、plugin ZIP を生成 |
| `python -m pytest tests/test_packaging.py::test_built_zip_in_isolated_host -q` | **1 passed**、8.88 秒。実 ZIP を beta.9 loader で読み込み、loader の sys.path 後処理後も mock NDL 検索・取得成功 |
| wheel / sdist metadata | Name=`comictagger-jp-talker`、Version=`0.2.0` |
| local plugin ZIP | 52,055 bytes、有効な ZIP、`archive.testzip() is None`、package METADATA は 1 件 |

生成物:

- `dist/comictagger_jp_talker-0.2.0-py3-none-any.whl`
- `dist/comictagger_jp_talker-0.2.0.tar.gz`
- `dist/jpbooks_talker-plugin-0.2.0.zip`

ZIP の entry point、`talker.py`、現在の `mapping.py`、MADB の `madb.py` / `madb_models.py` /
`madb_parser.py` / `madb_queries.py` を確認。全 package Python source を作業領域の source と照合した。
tests、research datasets、`.git`、`__pycache__`、`.pyc` は含まれない。
成果物と一時 Release notes は `.gitignore` 対象で、preparation commit には文書だけを含める。
Release asset は既存の tag workflow が生成する plugin ZIP だけ。
最終公開状況は [v0.2.0 Release](https://github.com/karigane-cha/comictagger-jp-talker/releases/tag/v0.2.0) と
[GitHub Actions](https://github.com/karigane-cha/comictagger-jp-talker/actions) を参照する。

### Phase 2B-1 MADB network verification

`tests/test_madb_integration.py` の 2 件が成功。
ISBN `9784832241190` から MangaBook `M381096` を検索し、Book と MangaBookSeries `C334830` を取得、
bundle の completeness=`complete` を確認した。
ISBN-13 `9784592880714` から ISBN-10-only の `M299519`（`4592880714`）も検出した。
通常 Talker lookup は NDL Search のみで、MADB 自動アクセス、GenericMetadata mapping、
NDL/MADB linkage / merge、Phase 2B-2 は未実装という境界を unit tests でも維持している。

### Series inference の NDL network regression

`tests/test_integration.py::test_real_phase1_series_and_number_regressions` の 3 実例が成功。

| NDL record | raw title | raw volume | 最終 Series | 明示巻 / 推定巻 / 論理巻 | conflict |
|---|---|---|---|---|---|
| `R100000002-I030727178` | `My Girl. vol.31` | `vol.31` | `My Girl` | `31` / `31` / `31` | False |
| `R100000002-I025437130` | `ご注文はうさぎですか? : アンソロジーコミック. volume 1` | `volume 1` | `ご注文はうさぎですか? : アンソロジーコミック` | `1` / `1` / `1` | False |
| `R100000002-I029306375` | `ご注文はうさぎですか? = Is the order a rabbit? 7` | `7` | `ご注文はうさぎですか?` | `7` / `7` / `7` | False |

raw title / volumes / series_titles は不変。原巻次を Notes に保持し、整数変換できない旨の警告は出ない。
Volume only / Issue only / Both、0 巻、非整数抑止、こち亀・パタリロ!・既存の `volume 1`、
全角数字と正式な記号の保持は non-network suite で確認した。

## 0.1.12 のローカル build 検証

2026-09-24。0.1.11 以降の Series 検索と巻番号推定の修正を含む。

- `search_metadata()` の Series 入力・空白除去・fallback を検証。検索時の資料種別が `online` なら図書は対象外となるため、図書検索では設定を `books` にする。
- 実書誌 `R100000002-I000001355589` の巻番号区切りと、`R100000002-I023440575` のタイトル／NDL 巻次 `volume 1` を確認。後者は Series=`ご注文はうさぎですか?`、明示巻・タイトル推定巻・論理巻番号=`1`、不一致なし。原タイトルと巻次は保持する。
- `volume` / `Volume` に空白と 1 〜 3 桁の整数が続く場合だけ巻番号 marker として認識する。数字のない `volume`、小数・範囲・分数・4 桁は推定・出力せず、0 巻と Volume only / Issue only / Both を検証した。`vol.` は未対応。

既知の制約として、ComicTagger 1.6.0b9 の CIX writer は整数 Volume=0 を省略する。非整数巻次は Volume / Issue へ出力しない。複数 Publisher の役割分離は未対応。

## 0.1.11 の Release 準備

NDL Search 単独の Phase 1 完了版。作品名の Series 推定、括弧付き副題と明示巻次の正規化、論理巻番号と Volume / Issue の分離、紙・電子の日付、責任表示、ISBN / GTIN、Notes の原値保持を含む。

- 非整数巻次を安全に未出力とし、NDL の版表示・資料種別を ComicInfo Format へ変換しない。
- 不明な creator role の Other fallback、破損キャッシュからの復旧、要約と制御文字の安全性を Phase 1 audit tests で確認。
- `vX.Y.Z` の tag push でテスト、build、ComicTagger plugin ZIP の検証、GitHub Release と asset の作成を行う workflow を追加。
- CIX writer の Volume=0 省略、複数 Publisher の役割未分離、複数言語の先頭のみ使用は既知の制約として維持。

## 0.1.10 の Phase 1 完了確認

NDL Search 単独の Phase 1 を監査し、安全に確定できる書誌情報だけを ComicTagger へ出力する方針を確認。

- ISBN / GTIN、作品名の Series 推定、括弧付き副題、明示巻次とタイトル推定巻の照合、3 種類の Volume / Issue 出力を検証。
- 紙・デジタル資料の日付、責任表示と構造化 creator role、未知の役割の Other、要約・制御文字・キャッシュ破損時の復旧を検証。
- 解釈不能な非整数巻次は Volume / Issue へ出力せず、NDL 原値を BookRecord と Notes に保持。
- NDL の版表示・資料種別から ComicInfo の Format を生成せず、原値を BookRecord・Notes・候補説明に保持。
- ComicTagger 1.6.0b9 の CIX writer が Volume=0 を省略する既知の制約は xfail として記録。複数 Publisher の役割分離は未対応。

## 0.1.9 の追加検証

NDL の明示巻次を専用 helper で正規化してから、タイトル推定値と比較する対応を追加。

- `1 (国王誕生の巻)`、全角数字・括弧、巻付き表記、先頭のゼロ、1 〜 3 桁を検証。
- 正規化後に同じ巻番号となる複数値は重複除去し、異なる巻番号や不明な巻次との競合は保持。
- 小数・範囲・分数・英字付き巻次・4 桁の値を整数化せず、原文と既存の Issue 文字列保持を検証。
- 全出力モードで検索候補から取得・巻照合、原文保持、Notes の誤警告がないことを検証。
- 実際の ComicTagger による CR / CIX 保存・再読込と、beta.9 の配布 ZIP 読み込み後の取得を検証。

NDL parser、BookRecord、タイトル推定、日付、責任表示、検索構文、巻番号出力設定は変更しない。

## 0.1.8 の追加検証

巻番号の後ろに丸括弧の補足が 1 つあるタイトルから、シリーズ名と巻番号を推定する対応を追加。

- 半角／全角の対応する括弧、空白あり／なし、第 N 巻、全角数字、従来の末尾数字を検証。
- ネスト・複数・空・不一致の括弧、小数、範囲、4 桁の年、区切りのない数字を推定しないことを検証。
- シリーズ名の記号、完全な Title、NDL の巻次原文、既存 Series の優先、巻番号の競合検出を検証。
- 全出力モードで候補選択から取得・巻照合までを検証。実際の beta.9 による配布 ZIP の読み込み後にも副題を含む Title を確認。

NDL parser、BookRecord、検索構文、出版日、責任表示、巻番号出力設定は変更しない。

## 0.1.7 の追加検証

2026-09-21、書誌日付とデジタル資料の日付を分離し、取得元設定を追加。

- Automatic / Bibliographic date / Digital date、紙と電子の判定、fallback、元データ保持を検証。
- 年・年月・年月日の精度、同一資料内の矛盾、不正日付、複数電子版の競合、資料を横断しない精度補完を検証。
- namespace、書誌との明示リンク、v2 の dateDigitized、v3 の Item 日付、無関係な Item の除外を検証。
- 設定保存、Talker 全取得経路と候補の年、CIX 保存・再読込、配布 ZIP 内の処理を検証。
- v2 の書誌キャッシュを v3 で再利用しないことを確認。
- opt-in の実 API テストで `R100000002-I029046058` の書誌年月と電子版の日付を比較し成功。

検索 CQL・ソート条件・ランキング、シリーズ名、巻番号設定、責任表示の役割変換は維持する。
通常テストでは HTTP を mock し、実応答全文は fixture へコピーしない。

## 0.1.6 の追加検証

2026-09-20、NDL の巻次原文・論理巻番号・出力先を分離した。

- beta.9 で `volume: int | None`、`issue: str | None`、CIX の Volume / Number 対応を確認。
- `GenericMetadata.overlay()` と `prepare_metadata()` を確認。通常の結合は新しい `None` で既存値を削除しない。
- 明示巻のみ、タイトル推定のみ、一致、不一致、複数明示巻、既存／要求値の分離と原文保持を検証。
- 出力先 3 種類、全角数字、非整数巻、要求との不一致、年の照合、既存 Volume からの再検索を検証。
- 設定の既定値・保存／読込・検証と、実際の CR / CIX での各出力モードの CBZ 保存・再読込を検証。
- beta.9 標準 GUI の各出力モードで候補の手動選択・取得を検証。Volume only の番号列は空欄。
- ZIP 読み込み後にも Volume only で要求巻との照合と fetch が成功することを検証。

矛盾する書誌は巻番号を未出力とし、Notes・候補詳細で警告する。要求巻付き取得はエラー、巻指定の照合では除外する。
既存タグの自動削除はせず、利用者の exe では不要な Issue / Volume を標準画面で空欄にして保存する。
NDL の XML 解釈、検索構文、シリーズ名、責任表示の役割変換は変更しない。

## 0.1.5 の追加検証

2026-09-20、責任表示の括弧処理・役割変換・creator fallback を分離した。

- beta.9 の `Credit`、標準 role 選択肢、GenericMetadata の role 同義語、comicinfoxml 0.5.1 の writer/reader を確認。
- 全対応役割について、括弧なし・半角／全角の角括弧・丸括弧を検証。
- 指定された実例、未知の役割、曖昧な表記、不正括弧、Unicode、複数人物を分割しないことを検証。
- 責任表示優先、creator fallback のみ Writer、contributor の Other、複数 role と重複除去、原文保持を検証。
- CIX で実際に CBZ を保存し、Writer への統合、Artist の保存先、Other の非対応、Notes の再読込を確認。
- ZIP ロード後にも SRU の括弧付き責任表示から Credit を取得する検証を追加。

NDL parser・Talker API・BookRecord は変更しない。原文を Notes に保存し、CIX の制限は README に明記した。
作画原稿・文字・表紙・カバーは曖昧なため Other。任意の複合役割・人物の自動分割は行わない。

## 0.1.4 の追加検証

2026-09-20、NDL の出版シリーズ等が漫画作品の `Series`・別名へ混入する問題を修正。

- `Series` は `existing_series` を優先し、なければ `infer_volume(record.title)` の作品名を使用。
- 出版レーベル・雑誌名・複数の出版シリーズ・空の値を使い、作品名と別名へ混入しないことを検証。
- 巻次付きタイトルと `20世紀少年` のような作品名、既存値の優先を検証。
- `series_titles` の原文が変更されず、Notes と候補詳細に残り、候補詳細では HTML がエスケープされることを検証。
- 標準 Talker の検索・issue 選択・fetch、実際の CR / CIX による CBZ 保存・再読込を検証。
- 配布 ZIP の beta.9 ローダー検証にも、作品名・空の別名・原データの Notes 保持を追加。

MADB の漫画作品シリーズは、出版シリーズとは別の出典付き項目として将来追加する方針を記載した。
Phase 1 に未使用のモデル・取得処理は追加していない。
利用者の exe では ZIP を入れ替えて再起動し、再フェッチ後の Series と Notes を確認して保存する。
既存キャッシュの削除は不要。保存済みタグを自動で一括修正するものではない。

## 0.1.3 の追加検証

2026-09-19、タイトル検索の取得順を改善した。

- `こちら葛飾区亀有公園前派出所` の図書検索で 590 件の応答を確認。
  従来の先頭 20 件が再編集版で占められ、古い順を指定すると本編の第 1 巻等が含まれることを確認。
- `oldest`・`newest`・`title` のクエリ生成、ソート指定の注入拒否、取得順ごとのキャッシュ分離を検証。
- 著者・巻番号を緩める再検索でも取得順を保持し、ISBN・書誌 ID 検索にはソートを追加しないことを検証。
- 設定の既定値と検証、文書・設定文言の空白ルールも検証。

変更箇所：`models.py`、`sources/ndl.py`、`talker.py`、バージョン定義、README と調査・検証記録、関連テスト。
取得上限は従来どおりで、Web の対象機関の絞り込みや画面上の順序との完全一致を保証するものではない。

## 0.1.2 の追加検証

2026-09-19、Summary の要約と書誌注記を分離し、NDL の詳細 JSON API で要約を補完した。

- 利用者指定の ISBN `9784046806680` を実際の Talker 経由で検索・取得し、
  書誌 `R100000002-I031565930` に対応する紙版の JPRO 要約を取得。
  取得した 70 文字の要約と GTIN が CIX で CBZ に保存・再読込できることを確認。
- 通常テストは架空の JSON と HTTP mock を使用。紙優先、デジタルへの切り替え、
  要約なし、別書誌の拒否、不正 JSON、timeout、キャッシュ再利用・再起動・Refresh を検証。
- 追加 API が既存の rate limiter を使い、検索時には呼ばれないことを検証。
- 書誌注記が Summary に混ざらず Notes に残ること、要約の提供元・媒体・資料 ID を記録することを検証。
- beta.9 の実際の GUI で、CR 選択時の GTIN 非対応状態、CIX 選択時の入力可能状態、
  不正な値に対する背景色の変化を確認。
- 配布 ZIP のテストは、ホストのロード後に詳細 JSON による要約補完も実行する。

実応答の全文は配布 fixture にコピーしていない。検証用の CBZ と応答は配布対象外の作業フォルダーに置いた。
更新後は 0.1.2 の ZIP に入れ替え、同じ ISBN を再フェッチして CIX で保存する。
SRU の古いキャッシュも新しいマッピングで読み直すため、この変更のための全キャッシュ削除は不要。
詳細 JSON の内部項目が将来変更される可能性は README に記載した。

変更箇所：`models.py`、`mapping.py`、`sources/ndl.py`、新規 `sources/ndl_summary.py`、
`errors.py`、バージョン定義、README と調査・検証記録、Summary・GUI・ZIP の関連テスト。

## 0.1.1 の追加検証

2026-09-19、利用者の ISBN 検索エラーを修正。以下は 0.1.1 の検証であり、
後段の 0.1.0 の初回検証記録とは区別する。

- `4-08-852811-5` と `9784088528113` の実応答で該当書誌なしの SRU 診断を再現。
  CQL の空白や ISBN のハイフンの違いでも結果は同じだった。
- 該当書誌なしを 0 件として返し、タイトル＋巻番号検索からタイトル検索へ進めることを確認。
- 他の診断、診断と件数・書誌の矛盾、複数診断の混在をエラーのまま保持することを確認。
- エラーの UTF-8 保存、日本語・補助漢字・不正入力のログ保持、書き込み失敗時の案内を確認。
- beta.9 の標準エラー画面で `Ctrl+C` による全文コピーを実際のクリップボードで検証。
- 文書と設定・案内文の英数字／日本語間の空白、長いカタカナ複合語の分かち書きを検証。
  書誌原文、URL、識別子、実行例の値は変更しない。
- 隔離ビルドと ZIP 生成が成功。beta.9 のローダーで更新版を読み込み、
  正常取得・該当書誌なし・コピー案内付きエラーを確認。テストは **132 passed, 1 skipped**。
  skip は通常無効のネットワーク テスト。ZIP 検証用サブプロセスにも UTF-8 を明示する。

変更箇所：`sources/ndl.py`、`talker.py`、`mapping.py`、新規 `errors.py`、
バージョン定義、README と調査・検証記録、関連テスト、CI のビルド対象。

更新時は旧版の ZIP／wheel を plugins フォルダーから外し、0.1.1 の ZIP と入れ替える。
利用者の配布版 exe では、再起動後の検索結果と `Ctrl+C` の操作を最終確認する。

## 0.1.0 の初回検証

検証日：2026-09-19。ComicTagger 本体は変更していない。

### 0.1.0 初回実装時の検証環境

- Windows、CPython 3.12.14
- ComicTagger 1.6.0b9（公式 beta.9 タグのソースをインストール）
- comicinfoxml 0.5.1、PyQt6 6.11.0 / Qt 6.11.2
- pytest 9.1.1、setuptools 84.0.0、build 1.6.1
- 新規プラグイン 0.1.0（editable install と生成 ZIP の両方）

### 0.1.0 初回実装時の検証と結果

| 検証 | 結果 |
|---|---|
| `python -m build` | 成功。隔離ビルドで sdist→wheel を生成 |
| `python scripts/build_plugin.py dist/comictagger_jp_talker-0.1.0-py3-none-any.whl` | 成功。wheel と同内容のローカル ZIP |
| `python -m pytest -q` 相当（作業用 tmpdir 指定） | **111 passed, 1 skipped**。skip は通常無効のネットワーク テスト |
| `JPBOOKS_RUN_NETWORK_TESTS=1 ... pytest -m network` | **1 passed**。ISBN-13 で SRU を 1 回呼び出し |
| `python -m ruff check .` | 成功 |
| `python -m ruff format --check .` | 成功 |
| importlib entry point / `get_talkers()` | `jpbooks` → `Japanese Books` を確認 |
| beta.9 `find_plugins()` を別プロセスで実行 | ZIP 由来のクラスをロードし、loader の sys.path 後処理後も検索・取得成功 |
| beta.9 `TaggerWindow` / 標準シリーズ・issue ウィンドウ | offscreen でソース表示、2 候補表示、issue74 表示、自動確定しないことを確認 |
| beta.9 `ComicArchive` + CR writer | CBZ 内 ComicInfo.xml への日本語・著者・出版社・日付・LanguageISO 等の保存と再読込成功 |
| beta.9 `ComicArchive` + CIX writer | 上記に加え **GTIN、Translator** の保存と再読込成功 |

ISBN-10 は実装前の実 API 応答調査と mock テスト、ISBN-13 は実装後のオプトイン テストで確認。
日本語タイトルは実 API の構造調査と、mock による Talker/GUI 検証で確認。
通常テストでは requests のアクセスを禁止し、個別の HTTP response だけを mock した。
ComicTagger の型を独自に再定義していない。

網羅範囲：ISBN-10/13 の正規化と全単一桁改変検出、両方向変換、GTIN-14、
CQL 引用と日本語、namespace 差し替え、正常／0 件／ SRU 診断／不正 XML／不正書誌、
timeout／接続／HTTP エラー、キャッシュ再利用・refresh・再起動、候補保持と順位、
日本語 Unicode、credits、日付の不正月日・閏年、言語、subject/NDC 分離、URL 検証、巻番号誤解析防止。

隔離環境の一時フォルダー／所有権制約があったため、テストには作業フォルダー内の
`--basetemp` と `-p no:cacheprovider` を指定して最終確認した。
最初のビルドは依存ダウンロードのネットワーク制限で失敗し、許可後の通常ビルドで成功した。
Qt の offscreen 環境ではシステム フォントの自動発見に制約があったため、
テスト側だけでインストール済み Meiryo を読み込み、画面キャプチャで日本語も確認した。
本体やプラグインによるフォント設定変更はしていない。

### 0.1.0 初回実装時の Definition of Done

| 項目 | 状態 |
|---|---|
| 1. build | 成功 |
| 2. beta.9 で読み込み | 実際の beta.9 ローダーで wheel/ZIP を確認 |
| 3. Japanese Books 表示 | 実際の標準 GUI で確認（offscreen） |
| 4. API key なし | 設定を非表示、実 API 接続成功 |
| 5–7. ISBN-13 / ISBN-10 / 日本語検索 | 実応答調査・単体／連携テストで確認 |
| 8. 複数候補 | 標準シリーズ UI で 2 候補を確認 |
| 9. GenericMetadata | 実際のクラスで変換・型検証 |
| 10. GTIN/ISBN | gtin 保持、CIX の GTIN 要素で往復確認 |
| 11–14. 著者・出版社・出版日・日本語 | CBZ 保存／再読込・Unicode 比較で確認 |
| 15. ComicInfo.xml 保存 | 実際の ComicArchive/CR/CIX で確認 |
| 16. unit tests | 111 passed（通常ネットワーク テスト 1 件 skip） |
| 17–18. README / 利用条件 | README と公式リンクを追加 |

### 0.1.0 初回実装時の手動確認事項

1. 利用中の **Windows 配布版 ComicTagger.exe beta.9** の正しい plugins フォルダーへ ZIP を置き、
   再起動後に Japanese Books が表示されること。本検証は Python パッケージ版の beta.9 で行っており、
   利用者が既に配置している exe そのものは起動していない。
2. 標準検索欄で ISBN を検索し、複数候補の版・著者・出版社を確認して選択すること。
3. CIX を単独の書き込みタグに選び、利用者の CBZ で保存・再読込して GTIN 等を確認すること。
4. Kavita で再スキャンし、シリーズ名・巻番号・日本語表示を確認すること。
   Kavita への API 接続・実機検証は行っていない。
5. 実利用の目的・提供機関に合う NDL メタデータ利用条件を確認すること。

### 0.1.0 初回実装時の既知の制限

beta.9 の標準検索メソッドに既存 GTIN や metadata が渡らないため、
GTIN の自動優先検索は補助メソッド経由のみ。標準 UI では ISBN を検索欄へ入力する。
表紙を取得しないため、表紙照合を行うホスト auto-tagging は対象外。
CR の GTIN/Translator 非対応は CIX で対応する。本体の変更や独自 writer では回避しない。
1 書誌 1 候補、件数上限、NDL 叢書名の意味、曖昧な巻次・著者役割等の制約は README 参照。

### 0.1.0 初回実装時の追加ファイル

初回実装時はすべて新規。既存ファイルの削除・置換はなかった。

- `pyproject.toml`, `MANIFEST.in`, `.gitignore`, `LICENSE`, `README.md`
- `comictagger_jp_talker/{__init__,talker,models,isbn,mapping}.py`
- `comictagger_jp_talker/sources/{__init__,base,ndl}.py`
- `tests/conftest.py`, `tests/fixtures/ndl.xml`
- `tests/test_{isbn,mapping,ndl,talker,comicinfo,gui,packaging,integration}.py`
- `scripts/build_plugin.py`, `.github/workflows/test.yml`
- `docs/research.md`, `docs/validation.md`

調査用 checkout・Python／依存環境・一時キャッシュは `.research`, `.tools`, `.venv` に分離して
`.gitignore` 対象とし、配布 wheel には含めない。
0.1.0 初回検証時点では GitHub Actions の設定ファイルを追加済みだったが、リモート CI 自体は未実行だった。

## Phase 2C-2B: Imprint 候補評価 API の検証

検証期間: **2026-10-08～2026-10-09 (JST)**。パッケージは **v0.3.0** のまま。評価仕様は `phase2c2b-v1`。
詳細は [実装仕様書](phase2c2b_imprint_candidates.md)、実装は
[imprint_candidates.py](../comictagger_jp_talker/imprint_candidates.py)。
Phase 2A～2C-2A の過去の観測値・判断は維持した。

### 実装範囲と確認結果

取得済み MADBRecordBundle から schema:brand の抽出・言語と構造の分類・Book / Series / NDL の比較・採用可否を返す。
入力は変更せず、raw RDFTerm と subject / predicate / object、各出現位置、取得状態、全意味確認証拠を保持する。
ELIGIBLE / HOLD / REJECT に加え、既存値・安全な候補欠損を SKIP として区別する。
ELIGIBLE の場合だけ単一の Book 候補を返し、他は selected_candidate=None とする。

意味確認は、明示的な trusted / VERIFIED、独立性、既知の origin group、同巻・同 ISBN・出版主体・版・媒体・時期の適用確認が必要。
URL、Book / Series 一致、NDL の系列表記だけで意味を確定しない。
M1032569 は、保存済み集英社の確認注記に基づくテスト用の明示的な信頼・適用契約を与えた場合だけ ELIGIBLE。
証拠なしの M1032569 / M1032568 は、実測の MATCHED / EXACT でも HOLD。
M197767 の版表示重複、M353277 / M1080059 の不一致、階層・数値・雑誌・別表記混在を採用しない。
Series-only、未知 term、不完全取得、identity conflict、XML 不正文字、異なる対象の意味確認も採用しない。

### 実測・synthetic の区別

保存済み Phase 2C-2A evidence から **39 Book / 27 Series** を必要な predicate に縮約し、
tests/fixtures/madb/imprint_measured.json に収録した。
元ファイルの SHA-256、raw binding、取得日時、request_id、出典・加工表示を検証した。
11 NDL 書誌の選択フィールドと、M1032568 / M1032569 の実測 discovery を再利用した。
他資料の discovery / linkage 完了条件、すべての authority trust / scope envelope、
未観測の RDF 型・言語・datatype・取得失敗・Unicode 境界は synthetic と明記した。
正例の成功は公式サイトを自動取得・検証する実運用機能の成功ではない。

### 実行環境と結果

Windows、CPython 3.12.14、ComicTagger 1.6.0b9、pytest 9.1.1、Ruff 0.16.8。
通常の python が PATH にないため、既存 .venv/Scripts/python.exe を使用した。

| 検証 | 最終結果 |
|---|---|
| Imprint 専用単体テスト | **235 passed**（0.71 秒）。新規の test_imprint_candidates.py |
| 全回帰テスト | **1,612 passed / 13 skipped / 1 xfailed**（25.57 秒） |
| 既存基準との差分 | 1,376 passed に対し、Imprint 235 件 + sdist 検証 1 件を追加 |
| Ruff check | All checks passed |
| Ruff format --check | **59 files already formatted** |
| sdist → wheel ビルド | 成功。既存依存環境を利用する --no-isolation |
| build_plugin.py | 成功。jpbooks_talker-plugin-0.3.0.zip を生成 |
| packaging | **3 件通過**。entry point、beta.9 ZIP loader、sdist 内容の検証 |
| wheel / ZIP の収録内容 | imprint_candidates.py が作業ソースと byte 単位で一致。ComicTagger 本体・docs・tests を wheel / ZIP に同梱しない |
| sdist の再現性 | 評価モジュール、専用テスト、縮約 fixture、検証元 evidence が作業ファイルと一致 |
| 既存動作の保持 | 通常 NDL 検索・取得、ISBN、照合、Series 補完、既定 OFF、通信抑止、fail-open、Notes、ComicInfo.xml、標準 GUI / ZIP 統合試験を既存 suite で確認 |
| pure function の境界 | 新規評価の network / file I/O 禁止、GenericMetadata・Book / Series / bundle 不変、繰り返し・順序不変を確認 |
| 改行を考慮した Git 差分確認 | git -c core.whitespace=cr-at-eol diff --check が成功 |
| 実 API テスト | 新規アクセスなし。既存 opt-in テストは有効化していない |

再現コマンド:

```powershell
.venv/Scripts/python.exe -m pytest tests/test_imprint_candidates.py -v -p no:cacheprovider --basetemp .research/phase2c2b-unit-release
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .research/phase2c2b-regression-release
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m build --no-isolation
.venv/Scripts/python.exe -X utf8 scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -m pytest tests/test_packaging.py -v -p no:cacheprovider --basetemp .research/phase2c2b-packaging-final
git -c core.whitespace=cr-at-eol diff --check
```

### 初回の失敗と修正

- 初回単体テストの 1 件は、壊した Book URI から検証済み authority を作ろうとする synthetic fixture の不整合だった。
  正常な authority と壊れた snapshot を別に用意して、不一致の拒否を検証するよう修正した。
- 初回の全体 format check は既存 10 ファイルの整形不一致だった。機械的な改行・行配置・コード例の空白を修正した。
  9 Python ファイルの HEAD との AST 同一性、Phase 2A 仕様書の本文の非空白文字列・Python コード例の AST 同一性を確認した。
  mapping.py の規則、既存テストの意味、過去の観測値は変更していない。
- sandbox 内のビルド・配布物確認では、既存配布物の置換や生成済み wheel / sdist の読み込みに Windows のアクセス拒否が発生した。
  承認された環境でビルド・読み取り検証・全回帰テストを再実行し、成功した。
- CRLF が Git の既定差分検査で行末空白と見なされたため、検証コマンドだけ cr-at-eol を明示した。
  リポジトリの Git 設定は変更していない。既知の xfail、既存の skip、失敗したテストは無効化していない。

### 変更と互換性

追加: imprint_candidates.py、test_imprint_candidates.py、imprint_measured.json、phase2c2b_imprint_candidates.md。
validation.md に本記録を追記し、test_packaging.py に ZIP import 確認と sdist 検証を追加した。
MANIFEST.in は fixture の検証元 evidence を sdist に収録するための 1 行だけ変更した。
既存の整形対象は mapping.py、test_comicinfo.py、test_madb.py、test_madb_boundary.py、test_mapping.py、
test_ndl.py、test_numbers.py、test_phase1_audit.py、test_talker.py と phase2_madb_spec.md。
開始時に存在した未コミットの Phase 2C-2A の 4 成果物は保持した。

通常の Talker 経路、GenericMetadata.imprint、その他の出力、設定、バージョン、identity algorithm、Series 補完を変更していない。
commit / merge / push / tag / GitHub Release は実行していない。
実際の Imprint 書き込み、公式情報の自動取得、補完設定、ComicInfo.xml への新値保存・再読込、
実際の Imprint 補完を伴う built-plugin integration は未実施で、Phase 2C-2C の範囲とする。

### 移行判断

**CONDITIONAL GO**。候補評価 API の条件付き採用と安全な保留・拒否の検証は完了した。
本番の補完には、信頼済み意味確認の供給・独立性・更新と失効、対象版・媒体・時期・構造の確認を確立する必要がある。
LinkageResult は raw bundle を返さないため、同一 snapshot と AcquisitionContext を Series / Imprint に共有する内部契約が必要。
次フェーズでは OFF 互換性、同時 ON、cache / refresh、要求数、fail-open、CR / CIX 往復、ZIP の実補完を追加検証する。
