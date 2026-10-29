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

## Phase 2C-2C-2A: MADB 取得状態モデルと構造化取得台帳

検証日: **2026-10-20 (JST)**。開始時は `main`、`cbce602f07a3559b8299a8e55c2dfc9d13d29022`。
前工程の `docs/phase2c2c_integration_design.md` だけが未追跡であり、既存本文を保持して工程 A の実装記録を追記した。
実装範囲は [統合設計](phase2c2c_integration_design.md) の §13 を参照。

### 変更内容と境界

- `acquisition.py`: 既存の AcquisitionState / ResourceAcquisition / AcquisitionContext を移動。
  AcquisitionStage / AcquisitionReason と frozen な AcquisitionFailure / AcquisitionEvent / AcquisitionTrace を追加。
- `imprint_candidates.py`: 移動した三つの型を同一オブジェクトとして再公開。評価 algorithm、authority、既存入力検証は変更しない。
  移動前の三定義と移動後の AST が完全一致することも確認した。
- `sources/madb_acquisition.py`: 呼び出し内の記録器と frozen な MADBAcquisition を追加。
  一回の検索 / Book 取得の value、context、trace、error を返す。複数 ISBN / 候補の全体集約は未実装。
- `sources/madb.py`: `_search_by_isbn_with_trace()` / `_get_with_trace()` を追加。
  同じ private 取得処理の分岐から状態・根拠を記録し、公開 API の戻り値と例外を維持する。
- `test_madb_acquisition.py`: synthetic な専用テスト **58 件**。
  `test_packaging.py`: sdist の新規 module / テスト収録、実 ZIP の型再公開と台帳取得・warm cache の確認を追加。
- 設計書は工程 A の実装・例外境界を追記。既存の Python コード例だけ Ruff の指摘に従って空行・折返しを修正した。
  取得共有の CONDITIONAL GO と Imprint 自動補完の NO-GO の判断は変更していない。

`linkage.py`、`talker.py`、Series 補完、NDL mapping、parser、query template、
endpoint、timeout、limiter、cache namespace / key / 期限 / 保存条件、各上限は変更していない。
追加 HTTP 要求・自動 retry・Imprint 設定・metadata 書き込み・authority provider は追加していない。
version は `0.3.0`、identity は `phase2b2-v1`、Imprint 評価は `phase2c2b-v1` のまま。

### 台帳の具体例

以下は HTTP mock による synthetic 結果。実 API の観測ではない。

| 入力・経路 | 結果と台帳 |
|---|---|
| Book / Series 各 1 件、軽量 cold | HTTP 2 要求。各 resource に cache miss → network COMPLETE → snapshot COMPLETE。Book / Series / relations が COMPLETE、discovery と Agent / Holding は NOT_REQUESTED |
| 完全な Book、Series relation なし | HTTP 1 要求。series / relations は NOT_RELATED。Book partial / truncated で参照が見えない場合はこの状態にしない |
| 正常な discovery 0 件、cold → warm | cold は HTTP 1、warm の追加 HTTP は 0。page.records は空 tuple、discovery は COMPLETE。warm は CACHE_HIT で原取得時刻・HTTP status は None |
| Series C1 成功、C2 が 503、C3 成功 | Book を含む HTTP 4 要求。C1 / C3 snapshot と C2 の http / 503 / Retry-After=17 を保持。bundle は partial、最上位 error は None、series / relations は PARTIAL。後続 C3 の取得を中断しない |
| Book が 503 | value=None、error.kind=http、status=503。book は UNAVAILABLE、後続 Series は UPSTREAM_FAILED / NOT_REQUESTED。偽の空 Book / 関係不存在を作らない |
| 13 Series relation | Book + 12 Series の HTTP 13 要求。13 件目は RELATION_BUDGET / NOT_REQUESTED、limit=12。全 raw relation を保持し、relations は PARTIAL |
| literal / bnode / 不正 URI の relation | 無効値への HTTP は 0。INVALID_REFERENCE / PARTIAL、raw statement と位置を保持。有効な Series と併存しても relations を COMPLETE にしない |
| 壊れた cache | CACHE_INVALID と原 bytes の hash / error を保持して従来どおり 1 回再取得。成功結果だけ保存し、過去の破損観測を消さない |
| byte cap 到達 | BYTE_LIMIT / TRUNCATED、上限値を保持。完全な原応答 hash と受信完了時刻は None。切り詰めを正常な空結果にしない |

context.resources は Book / Series 範囲。同じ URI に対する未要求 Agent の役割で、
取得済み Series の状態を上書きしない。Agent / Holding の参照は kind 付きの event に保持する。
原応答本文が完全に得られた場合だけその bytes の SHA-256 を記録する。
cache 保存時刻、cache の原 HTTP 取得時刻、bundle 共通の取得時刻は推測せず None。

### 実行環境と検証結果

既存 `.venv`、Python `3.12.14`、ComicTagger `1.6.0b9`、comicinfoxml `0.5.1`、
pytest `9.1.1`、Ruff `0.16.8`、build `1.6.1`、setuptools `84.0.0`。依存追加・更新なし。
通常テストの外部 HTTP 禁止 fixture を維持し、実通信の opt-in は有効化していない。

| 検証 | 結果 |
|---|---|
| 最終の取得台帳専用テスト | **58 passed**、3.18 秒 |
| 指定コマンドによる全回帰試験 | **1 failed / 1,689 passed / 13 skipped / 1 xfailed**、34.22 秒。失敗は sdist 読み取りの PermissionError |
| 権限のある環境で packaging を再実行 | **3 passed**、14.49 秒。sdist byte 一致、entry point、実 ZIP の beta9 loader、既存 Series と新規台帳経路を確認 |
| 全回帰の範囲 | identity、Series、NDL mapping / summary、ComicInfo.xml の既存 CR / CIX 試験、GUI、Imprint pure API を含む |
| Ruff check | **All checks passed** |
| Ruff format --check | **63 files already formatted** |
| sdist → wheel → ZIP | **成功**。Windows の権限問題により sandbox 外の許可された環境で実行 |
| diff check / 改行 | `git diff --check` と新規未追跡ファイルの `git diff --no-index --check` を確認。変更・新規ファイルは UTF-8 / LF |
| raw evidence | SHA-256 `780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12` を維持。`.gitattributes` の例外を変更していない |

**全体 suite が一度で成功したとは記録しない。**
通常環境では sdist の内容検証を実行できず、許可された環境の packaging 再実行でその未確認範囲を解消した。
13 skipped は既存の opt-in network 試験、1 xfailed は既知の CIX の整数 Volume 0 出力制約。
今回の実装不具合として残った失敗はない。実 API における最新 endpoint の挙動は未検証。

### 初回の失敗と対応

- 専用テスト初回は 47 passed / 2 failed。cache の complete 行を incomplete へ書き換える想定は、
  ComicCacher が downgrade を拒否する契約と合わなかった。テスト側で legacy な incomplete 読込結果を明示的に作った。
- もう一件は synthetic な publisher の URI 追加時に既存 literal も残したため、
  現行 source がその literal を未解決 relation として正しく partial にしたもの。
  重複 URI の正常系試験では literal を除いた fixture に修正した。production の規則は緩和していない。
- 初回 format check は前工程の未追跡設計書にある Python コード例の空行・折返しを指摘した。
  指摘された配置だけ修正し、判断・本文・raw 値を変更していない。
- 通常環境の build は既存 sdist の置換で WinError 5、ZIP 生成は wheel 読み取りで PermissionError。
  許可された環境で再実行して成功した。全回帰時の sdist 読み取りも同種の権限問題であり、
  テスト削除・skip 化・assertion 緩和は行っていない。

再現コマンド（build / packaging の一部は上記の許可された環境を使用）:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2a-trace-release tests/test_madb_acquisition.py
.venv/Scripts/python.exe -X utf8 -m build --no-isolation
.venv/Scripts/python.exe -X utf8 scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2a-pytest
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2a-packaging tests/test_packaging.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
git diff --check
git status --short
```

### 未解決事項と工程 B への判断

**CONDITIONAL GO**。工程 A の取得台帳は利用可能。
工程 B で全 ISBN の予定・discovery の中断・全候補集合を集約し、
同一 snapshot を既存の照合規則で使用して、公開 LinkageResult と Series 出力を維持することが条件となる。
本工程では linkage core を変更していない。

原取得時刻がない旧 cache、複数 HTTP 間の snapshot isolation、parser が既に除去した Book の重複は未解決。
取得台帳を理由にそれらを観測済みへ格上げしない。
ValueError / RuntimeError / OSError / SQLite error / 内部 assertion は従来の例外境界のまま送出し、
この場合の trace 返却は今回の内部 outcome 契約の対象外である。
意味確認の本番供給・失効運用と保存先既存 Imprint の保護も未解決で、自動補完の NO-GO は維持する。
commit / push / merge / tag / GitHub Release は実行していない。

## Phase 2C-2C-2B：共通 linkage core と取得済み snapshot（2026-10-20）

### 開始時点と変更範囲

開始時の branch は `main`、HEAD は `cbce602f07a3559b8299a8e55c2dfc9d13d29022`。
工程 A の未コミット変更が存在した。開始時の内容を
`.research/phase2c2c2b-start/` に保存して、今回の差分と区別した。

| 開始時の状態 | ファイル |
|---|---|
| 変更済み | `imprint_candidates.py`、`sources/madb.py`、`docs/validation.md`、`tests/test_packaging.py` |
| 未追跡 | `acquisition.py`、`sources/madb_acquisition.py`、`docs/phase2c2c_integration_design.md`、`tests/test_madb_acquisition.py` |

上記の production code と工程 A の専用テストは開始時と byte 単位で一致する。
設計書と本記録の既存部分もそのまま保持し、工程 B の節を追記した。
packaging テストは工程 A の assertion を維持したうえで拡張した。

工程 B の変更は次の 7 ファイル。

- `comictagger_jp_talker/linkage.py`：単一 core、公開 wrapper の projection、共有結果型。
- `comictagger_jp_talker/linked_acquisition.py`（新規）：NDL 入力、ISBN / Book / run 全体の immutable モデル。
- `tests/test_linkage_evidence.py`（新規）：165 件の専用テスト。
- `tests/fixtures/linkage_evidence_baseline.json`（新規）：旧 core で取得した synthetic な公開結果。
- `tests/test_packaging.py`：新規モデルと固定 fixture の sdist 収録、全 production Python の ZIP byte 比較、
  loader 後の共有 core と warm cache の検証。
- `docs/phase2c2c_integration_design.md`：§14 に確定契約と次工程の条件。
- `docs/validation.md`：本記録。

`talker.py`、`series_supplement.py`、NDL mapping、authority、Imprint 設定・書き込みには変更を加えていない。
package `0.3.0`、identity `phase2b2-v1`、evaluator `phase2c2b-v1` を維持した。

### 確定した内部契約と互換性

`acquire_linked_record_evidence(record, source, *, refresh=False, scope="series_linkage")` は、
`LinkedRecordEvidence(linkage, bundles, acquisition_context)` を返す。
公開 `link_ndl_record()` は full、`link_ndl_record_for_series()` は軽量 scope を使い、
従来の `LinkageResult` のみを返す。取得ループは一本で、source の trace outcome.value を再利用する。
`_evaluate()` / `_url()` / `compare_candidates()` は開始時と AST が一致する。

`NDLInputSnapshot` は ID、URL、title、ISBN、volumes、publishers、editions、issued、dates、
series_titles の raw 値を固定する。比較には独立した private BookRecord を使う。
全 ISBN の予定順・成功・失敗・中断を `DiscoveryAcquisition` に集約し、発見した全 Book に
`BookAcquisitionContext` を対応付ける。元 source outcome / trace と、全体 discovery を加えた
context を分け、同じ取得を二度実行しない。全成果物を frozen / tuple とし、mutable handle を保持しない。

旧 core を変更する前に 24 ケース × full / series_linkage の公開結果を JSON に固定した。
新しい trace 対応 source と既存 fake source の両方で固定値と比較したため、
新 wrapper と新 core に同じ誤りがある場合にも回帰を検出できる。
status、confidence、reason / conflict、候補の順序・URI・completeness、warnings、error、
Retry-After、truncated、SeriesComparison を全体比較している。

同じ ID に別 URI が出た場合の「最後の URI を採用する」既存処理も維持した。
新台帳には全 page と `conflicting_discovery_uri:<ID>` を保存する。
取得した Book が discovery と一致しない場合の公開 schema failure は維持し、
その raw bundle は Book 個別の台帳に保存して `included_in_linkage=False` とする。

trace を持たない fake / 公開メソッドの monkeypatch は、一回だけ公開メソッドを呼ぶ adapter で対応。
非 truncated 成功でも台帳は PARTIAL / `trace_unavailable` とし、COMPLETE を推測しない。
最上位 MADBError は既存 UNAVAILABLE、Series 内の失敗は従来の partial bundle。
ValueError / RuntimeError / OSError / SQLite error / assertion はそのまま送出する。
これらの例外での途中台帳の返却は内部 outcome 契約に含めない。

### 台帳の具体例と通信数

| 入力・結果 | 新しい台帳 |
|---|---|
| ISBN 1 件 → Book 1 件 → Series 1 件 | discovery COMPLETE、Book / Series COMPLETE。元の source trace 2 個と同一 bundle を保持 |
| ISBN 1 件目成功、2 件目 timeout、3 件目未実行 | discovery PARTIAL。個別に COMPLETE / UNAVAILABLE / NOT_REQUESTED。発見済み Book は未要求 |
| discovery row cap と後続 timeout | discovery PARTIAL、truncated=True、cap と failure の双方を保持 |
| Book M1 成功、M2 が 503、M9 未実行 | M1 の bundle と trace を保持、M2 は UNAVAILABLE / status=503 / Retry-After、M9 は NOT_REQUESTED |
| Series C1 成功、C2 失敗 | Book の outcome は partial bundle、Series は PARTIAL。成功と失敗両方の event を保持 |
| Book と discovery の ID / URI 不一致 | 公開結果は従来の UNAVAILABLE。取得した raw bundle は個別台帳だけに保存 |
| 有効 ISBN なし | NOT_REQUESTED / `no_valid_isbn`、通信ゼロ |
| 正常な空 discovery | COMPLETE、候補ゼロ。未取得や failure と区別 |

標準 synthetic fixture の軽量 linkage は cold **3**、warm **0**、refresh **3** 要求。
full fixture は Agent / Holding を含み cold **6**、warm **0**、refresh **6** 要求。
Series cache だけの失効・不正 cache は追加 **1** 要求。
取得前に公開メソッド経路／trace 経路を切り替えた対照試験で、cold / warm / refresh と
discovery / Book / Series の 429 における HTTP 引数・順序・回数、cache 保存呼び出しの一致を確認した。
再取得や追加 retry はない。標準 Talker の default OFF、候補取得、既存 Series 補完の通信数も既存試験で確認した。

新規 fixture、fake trace、HTTP mock はすべて **synthetic**。新しい実測データや authority は含まない。
既存実測 evidence の SHA-256 は
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12` を維持する。

### 実行結果

既存 `.venv` と工程 A と同じ依存環境を使用。外部 HTTP を禁止する autouse fixture を維持した。
依存の追加・更新、実 API の opt-in、テストの無効化、権限設定の変更は行っていない。

| 検証 | 結果 |
|---|---|
| 変更前の関連試験 | **575 passed / 2 skipped**、6.98 秒 |
| 共通 core 移行後の初期回帰 | **239 passed / 2 skipped**、5.24 秒 |
| 新規専用試験の初回実行 | **157 passed**、1.39 秒。その後、公開 source と trace の I/O 対照 8 件を追加 |
| 新規 165 件を含む最終の関連試験 | **740 passed / 2 skipped**、9.53 秒。工程 A の専用 58 件を含む |
| 指定形式の全回帰 | **1 failed / 1,854 passed / 13 skipped / 1 xfailed**、32.70 秒 |
| 権限のある環境で packaging を再実行 | **3 passed**、14.13 秒 |
| Ruff check | **All checks passed** |
| Ruff format --check | 新規コード例の折返し 1 箇所を修正後、**65 files already formatted** |
| sdist → wheel → plugin ZIP | **成功**。既存スクリプトを使用し、現在の production code を収録 |
| 実 ZIP | production Python **21 ファイルすべて byte 一致**。新規モデル、工程 A のモデル、最新 linkage を含む |
| ComicTagger 1.6.0b9 loader | 実 ZIP の path cleanup 後、既存 Series 補完と共有 core、取得済み bundle、warm cache を確認 |
| 改行・差分 | UTF-8 / BOM なし / LF。`git diff --check`、新規ファイルの差分検査を確認 |
| 保護対象 | 工程 A の code / 専用テストは開始時と byte 一致。旧文書部分、raw evidence、`.gitattributes` を維持 |

全回帰の唯一の失敗は `test_sdist_contains_imprint_fixture_and_its_source` が
`dist/comictagger_jp_talker-0.3.0.tar.gz` を開く際の `PermissionError`。
今回の traceback でファイルを開く段階の拒否であることを確認し、
権限のある環境で同じ packaging assertion を再実行して成功した。
**全体 suite が一度で成功したとは記録しない。**
13 skipped は既存の実通信 opt-in、1 xfailed は既知の CIX writer の整数 Volume 0 出力制約。
NDL mapping、summary、Series、Imprint pure API、CR / CIX、GUI を含む既存回帰に実装上の失敗は残っていない。

最初の build は既存 sdist の置換時に WinError 5、ZIP 生成は wheel 読み取り時に PermissionError。
それぞれ権限のある環境で同一コマンドを再実行した。旧成果物を成功の根拠にしていない。
最初の Ruff check では追加テストの import 順・折返し・zip の strict 指定を修正し、
format check では設計書の新規 Python コード例だけを修正した。無関係な整形はしていない。

再現コマンド（上記の build / ZIP / packaging の再実行は許可された環境）:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2b-focused-final tests/test_linkage_evidence.py tests/test_linkage.py tests/test_linkage_integration.py tests/test_madb_acquisition.py tests/test_madb.py tests/test_madb_boundary.py tests/test_series_supplement.py tests/test_series_retrieval.py tests/test_imprint_candidates.py
.venv/Scripts/python.exe -X utf8 -m build --no-isolation
.venv/Scripts/python.exe -X utf8 scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2b-full
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2b-packaging tests/test_packaging.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
git diff --check
git status --short
```

### 工程 C への判断と未解決事項

取得共有基盤は **CONDITIONAL GO**。公開 linkage の互換性と一回の取得による snapshot 共有を確認した。
次工程は補完要否の個別判定 → 共有取得の接続 → 既存 Series の出力・通信回帰の順とする。
Imprint の採用には run 全体の issues、discovery、Book 対応、relation 完全性を検証する必要がある。

**Imprint 自動補完は NO-GO**。信頼済み authority の供給・失効・対象適合性は未解決で、
この取得基盤では意味確認を VERIFIED へ変更できない。
旧 cache の原 HTTP 時刻、cache 保存日時、複数 HTTP の同時点性、parser 内で除去された重複、
parsed snapshot digest は引き続き未確認・未実装。bundle 共通の取得時刻は捏造しない。
NDL snapshot は現行比較の参照フィールドに限り、将来の媒体等の authority 検証には別途拡張が必要。
trace がない adapter の結果は自動補完の完全性根拠に使えない。
工程 C の本番統合、Imprint 設定・書き込み、authority provider は実装していない。
commit / push / merge / tag / GitHub Release は行っていない。

## Phase 2C-2C-2C：既存 Series 補完の共通取得入口への移行（2026-10-20）

### 開始時点と差分の区別

実際の開始状態は `main` / `cbce602f07a3559b8299a8e55c2dfc9d13d29022`、package `0.3.0`。
工程 A / B の変更が未コミットで残っていた。

| 開始時の状態 | ファイル |
|---|---|
| 変更済み 5 ファイル | `imprint_candidates.py`、`linkage.py`、`sources/madb.py`、`docs/validation.md`、`tests/test_packaging.py` |
| 未追跡 7 ファイル | `acquisition.py`、`linked_acquisition.py`、`sources/madb_acquisition.py`、`docs/phase2c2c_integration_design.md`、`tests/fixtures/linkage_evidence_baseline.json`、`tests/test_linkage_evidence.py`、`tests/test_madb_acquisition.py` |

開始時の production code、既存テスト、設計・検証文書、固定 fixture、`.gitattributes` の
52 ファイルを `.research/phase2c2c2c-start/` に byte 単位で保存した。
工程 A / B の production code、専用テスト、公開 linkage 固定 fixture は開始時と byte 一致。
既存文書の内容も prefix としてそのまま保持し、工程 C を追記した。
packaging は工程 A / B の assertion を残して、新しい接続位置と収録ファイルへ対応させた。

今回の変更は次の 11 ファイル。

| 区分 | ファイルと変更 |
|---|---|
| production 新規 | `metadata_supplement.py`：共通取得入口。`series_supplement_policy.py`：既存の純粋な採用関数を移動 |
| production 変更 | `series_supplement.py`：互換 wrapper と採用関数の再公開。`talker.py`：最終 fetch の補完入口だけ変更 |
| テスト新規 | `tests/test_metadata_supplement.py`、`tests/fixtures/metadata_supplement_baseline.json` |
| テスト変更 | `tests/test_series_supplement.py`、`tests/test_series_retrieval.py`：constructor の monkeypatch 対象だけ移動。`tests/test_packaging.py`：新入口・収録内容を追加 |
| 文書 | `docs/phase2c2c_integration_design.md` に §15、本記録 |

### 入口・出力・失敗の契約

`supplement_metadata(metadata, record, cache_folder, *, series_enabled=False)` を追加した。
`series_enabled and not (metadata.series or "").strip()` が False なら入力をそのまま返す。
source、session、cache は生成しない。
必要なときだけ一つの MADBSource から一回の
`acquire_linked_record_evidence(..., scope="series_linkage")` を実行し、close 完了後に
`evidence.linkage` を既存の `apply_series_supplement()` へ渡す。
取得済み bundles / context は同じ evidence に保持し、再取得・再構築しない。

`supplement_series(..., enabled=False)` は同じ引数・戻り値を保つ wrapper とした。
純粋な採用関数を独立 module に移し、旧 path から同一関数を再公開することで循環 import を避けた。
移動した関数本体は開始時と AST が一致する。
Talker は NDL get、巻の解決・照合、to_metadata 後の呼び出しだけを新入口へ切り替えた。
候補取得・check_status・NDL summary policy・mapping・巻処理・設定の挙動は変更しない。

EXACT / STRONG、MADB_ONLY、一意な表示、完全性の既存条件を維持し、
truncated / ambiguous / unsafe / unavailable / XML 不正値を救済しない。
採用時に変わる全フィールド集合は `series` / `notes` のみ。
raw display、既存 Notes 本文・改行、行単位の重複抑止、既存 Imprint 等を保持する。

source 生成成功後は正常・異常とも close を一度試みる。取得・close が完了するまで apply しない。
constructor / 取得 / close の MADBError / OSError / sqlite3.Error は baseline を返す。
UNAVAILABLE と warning の扱いは従来どおり。
logger 名 `comictagger_jp_talker.series_supplement` とメッセージ・順序・回数も維持した。
TypeError / ValueError / RuntimeError / assertion は伝播し、包括的な except は追加しない。
実 source の session / cache の close をそれぞれ観測し、一方が失敗しても二重 close しないことを確認した。
constructor が失敗してオブジェクトを返さない場合の部分初期化処理は既存 source の責務を維持する。

### 独立した移行前の基準と通信確認

production code を変更する前に、29 ケースの全 GenericMetadata と warning の
logger 名・level・本文を `metadata_supplement_baseline.json` へ固定した。
fixture と HTTP 応答は **synthetic**。実測 evidence の追加や authority の意味確認ではない。
新入口・互換入口・Talker の三経路をこの固定値と比較し、新旧入口同士の比較だけに依存していない。
比較対象には EXACT / STRONG / ambiguous / unsafe、途中失敗、ID / URI 不整合、
raw display、reading-only、複数 display / Series、XML 不正値を含める。

| 条件 | MADB の観測 |
|---|---|
| OFF、または非空 Series | source 0、HTTP 0 |
| 単一 ISBN / Book / Series の最終 fetch | source 1、共有 core 1、cold 3 要求 |
| 次の最終 fetch | 別の source で既存 cache を利用、追加 HTTP 0 |
| 明示的な内部 refresh=True | 3 要求。検索 refresh_cache からは伝搬しない |
| relation なし | 2 要求 |
| 二つの有効 ISBN、同じ Book | 4 要求 |
| 二つの Book、同じ Series URI | 5 要求。既存 relation cache key が親 Book を含むため |
| Series cache の部分失効・破損 | 追加 1 要求 |
| discovery / Book / Series の 429 / 503 / timeout | 各 1 / 2 / 3 要求、追加 retry なし |
| Agent / Holding | 0 要求 |

NDL の SRU / summary は別カウンターで計測。
summary 200 / 429 と欠損 Series の組合せでは cold は SRU 1、summary 1、MADB 3、
warm はそれぞれ追加 0。既存 Series があれば MADB source の生成は 0。
summary の既存抑止期限・cache を変更していない。
候補 API と check_status は共通入口を呼ばず、NDL エラー・巻不一致も補完前に終了する。
optional MADB の constructor / 取得 / close と実 transport の各失敗で、
既存 `latest-error.txt` の bytes を保持することを確認した。

NDL parser はタイトル欠落を拒否する。通常の NDL mapping ではタイトルが Series になるため、
欠損 Series の複合試験は正常な SRU / summary 取得後に test adapter で欠損 BookRecord を注入した。
本番 parser を緩めたものではなく、実 API に補完対象が存在するという実測証明でもない。

### 検証結果

既存 `.venv`、Python `3.12.14`、ComicTagger `1.6.0b9` と既存依存を使用し、追加・更新はしていない。
通常テストの外部通信禁止を維持し、network opt-in は有効化していない。

| 検証 | 結果 |
|---|---|
| 移行前の関連試験 | **394 passed**、9.51 秒 |
| 初期の新規入口試験＋既存 Series 試験 | **243 passed**、7.13 秒 |
| 最終の工程 C 専用試験 | **163 passed**、6.50 秒 |
| 工程 A / B・Series・Talker・summary・Imprint を含む関連試験 | **871 passed / 2 skipped**、15.72 秒 |
| 全回帰 | **1 failed / 2,017 passed / 13 skipped / 1 xfailed**、39.88 秒 |
| 権限のある環境で packaging を再実行 | **3 passed**、14.14 秒 |
| Ruff check / format check | **All checks passed / 68 files already formatted** |
| sdist → wheel → plugin ZIP | **成功**。既存 build 手順と `scripts/build_plugin.py` を使用 |
| ZIP の production Python | **23 ファイルすべて byte 一致**。実一覧から比較し、旧 21 ファイルに固定していない |
| beta9 loader | path cleanup 後の新入口、既存 Series、共有 core、NDL summary / 巻処理、default OFF、軽量 3 / 0 要求が成功 |
| 差分・形式 | `git diff --check`、新規ファイルの差分検査、UTF-8 / BOM なし / LF を確認 |
| 保護対象 | 工程 A / B の code・専用テスト・固定 fixture と `.gitattributes` を維持。過去文書もそのまま保持 |

全回帰の唯一の失敗は、sdist の `tarfile.open()` が
`dist/comictagger_jp_talker-0.3.0.tar.gz` を読み取る際の `PermissionError`。
今回の traceback で内容検証前の権限拒否と確認し、許可された環境の packaging 再実行で全件成功した。
**全体 suite が一度で成功したとは記録しない。**
13 skipped は既存 network opt-in、1 xfailed は既知の CIX writer の整数 Volume 0 の制約。
既存 CR / CIX 回帰は実行したが、工程 E の新しい保存境界の調査や実装は行っていない。

今回も通常 build は sdist 置換の WinError 5、ZIP 生成は wheel 読み取りの PermissionError で停止した。
同一コマンドを許可された環境で再実行し、現在の production code を含む配布物を生成した。
テスト削除・skip 化・権限設定変更による回避は行っていない。

通信試験を追加した初回は **5 failed / 156 passed**。いずれもテスト側の想定を修正した。

- refresh 比較の baseline に要求巻由来の Notes が欠けていたため、同じ `existing_issue` を渡した。
- 複数 ISBN の mock が検索 ISBN と違う binding を返し、既存 parser が schema failure として拒否した。
  検索条件に一致する synthetic 応答へ修正した。
- 複数 Book の同じ Series を一回に共有できるという想定を、親 Book を含む既存 cache key に合わせた。
  このケースだけの確認でも 1 failed を記録し、最終期待値を従来どおり 5 要求とした。
- summary 200 / 429 の二つの fixture はタイトルを削除していたため、NDL parser が正しく拒否した。
  正常な XML と取得後の synthetic 入力注入に分け、通常タイトルの対照も追加した。

production の安全性判定・parser・cache・Series 採用条件は変更していない。
raw evidence の SHA-256 は次の値を維持する。
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`

再現コマンド（build / ZIP / packaging の再実行は上記の許可された環境）:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2c-focused tests/test_metadata_supplement.py tests/test_series_supplement.py tests/test_series_retrieval.py tests/test_linkage_evidence.py tests/test_madb_acquisition.py tests/test_linkage.py tests/test_linkage_integration.py tests/test_talker.py tests/test_summary_policy.py tests/test_imprint_candidates.py
.venv/Scripts/python.exe -X utf8 -m build --no-isolation
.venv/Scripts/python.exe -X utf8 scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2c-full
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c2c-packaging tests/test_packaging.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
git diff --check
git status --short
```

### 受入判断と未解決事項

工程 A～C は **既存 Series 補完を対象とする取得共有基盤として GO**。
出力・ログ・HTTP 回数・cache・障害時の処理が移行前と等価であることを上記の範囲で確認した。
旧 cache の原 HTTP 時刻、保存日時、複数 HTTP 応答の同時点性、parsed snapshot digest、
parser が既に除去した重複等の制限は工程 B のままである。

**Imprint 自動補完は NO-GO を維持する。**
工程 D の authority 真正性・独立性・対象適合・失効運用の実証、
工程 E の host 保存先既存値保護と保存・再読込境界の解決が別途必要。
これらの調査・実装、Imprint 設定・評価の本番接続・書き込みには進んでいない。
commit / push / merge / tag / GitHub Release は実行していない。

## Phase 2C-2C-3E0：ComicTagger の Imprint 保存境界（2026-10-20）

### 対象と変更範囲

導入済み Windows 11、Python `3.12.14`、ComicTagger `1.6.0b9`、
comicinfoxml `0.5.1` を調査した。既存 `.venv` を使い、依存の更新・追加はしていない。
開始ブランチは `main`、HEAD は `cbce602f07a3559b8299a8e55c2dfc9d13d29022`。
工程 A～C 等の既存差分（変更済み 9、未追跡 11 ファイル）を保持した。

今回の成果物は次の 4 ファイルのみ。

- `tests/test_imprint_host_boundary.py`: 実 host 保存 API に対する synthetic CBZ 試験。
- `docs/phase2c2c_host_imprint_boundary.md`: 取得・merge・保存・reader の調査、反例、代替方式と受入判断。
- `docs/phase2c2c_integration_design.md`: §15 までを維持し、§16 を追記。
- 本記録: 従来の validation を保持して追記。

開始時に `.research/phase2c2c3e0-start/` に既存 production / tests / fixtures の SHA-256、
両文書のコピーを保存した。比較により、既存 code / tests / fixtures の bytes が変わらず、
両文書の旧内容が新内容の完全な prefix として残ることを確認した。
package version `0.3.0`、`.gitattributes`、既存 raw evidence を維持する。
production への Imprint 設定・評価接続・書き込み、authority provider は追加していない。

### 実測の主要結果

1. `fetch_comic_data()` へ archive metadata / raw XML / host 設定は渡らない。
   `search_metadata()` は beta9 の callback ではない。候補の詳細表示から最終 fetch が呼ばれる場合もある。
2. 既定の OVERLAY は非空の取得 Imprint で既存値を上書きする。
   ADD_MISSING はメモリ内の空白文字列を保護するが、reader で None になった空白値は保護できない。
3. `prepare_metadata()` は import transform → clear → merge → auto_imprint の順。
   現行 CBLTransformer は Imprint を直接変更しない。fix_publisher は既存値にも作用する。
4. GUI の None はフォームに代入されないため、clear 後に旧フォーム値が保存時に復活する実測例がある。
   CLI / 自動 worker の clear は消去となった。この経路差を保護機能とは扱わない。
5. CR / CIX は同じ `ComicInfo.xml` を使用し、両方向の reader 呼出しが可能。
   通常の日本語・英数字・内部空白・XML 特殊文字・非 BMP は往復した。
   外周空白は xlate で失い、空白だけなら None。CR / CRLF は XML parser が LF にする。
6. XML 不正値の書き込みも True となり得る。両 reader はタグなしとして扱い、
   `read_selected_tags()` の error も None のため、成功戻り値・例外監視だけでは保護できない。

実 XML 全文、parser text、CR / CIX reader 値、入力 / merge / 保存値は、
各試験の `tmp_path/observation.json` と CBZ に記録する。今回の主な保存先は
`.research/phase2c2c3e0-host/` と `.research/phase2c2c3e0-full/`。
調査値はすべて synthetic。既存の MADB 実測 fixture や意味確認済み authority と混同しない。

### 試験範囲と結果

新規 592 件の内訳は、既定値 1、raw 往復 30、不正 XML 10、archive の値マトリクス 384、
overlay 対照 96、設定相互作用 32、auto_imprint 分岐 8、共有 XML 4、実 CLI 14、
実 GUI 1（内部で 14 シナリオ）、実自動 worker 12。
既存値 8 種類 × 取得値 6 種類 × merge 2 × clear 2 × writer 2 を全組合せにした。
auto_imprint は publisher の変換・維持・消去を生じる代表例と設定の直積で分岐を覆う。
raw 入力を正規化して assertion を通していない。

CLI は `CLI.save()` から実保存、自動 worker は `identify_and_tag_single_archive()` →
実 `identify_comic()` / prepare / writer を通す。取得結果と画像照合だけを Mock に置換する。
GUI は実 TaggerWindow を offscreen で生成し、load / apply / form / write / reread を同期実行する。
検索のクリック・非同期スレッド・曖昧候補ダイアログ・配布 exe 全体の操作を実証したとはしない。
自動開始ダイアログの設定伝搬等は報告書の手動試験に残した。
通常テストの外部 HTTP 禁止を維持し、network opt-in は有効化していない。

| 検証 | 結果 |
|---|---|
| 最終の新規保存境界試験 | **592 passed**、16.79 秒 |
| 既存 ComicInfo / Talker / 工程 C の関連試験 | **206 passed / 1 xfailed**、7.30 秒 |
| 全回帰 | **1 failed / 2,609 passed / 13 skipped / 1 xfailed**、53.95 秒 |
| 権限のある環境で packaging 再実行 | **3 passed**、14.31 秒 |
| Ruff 指摘対応後の該当試験 | **4 passed / 588 deselected**、0.52 秒 |
| Ruff check | **All checks passed** |
| Ruff format check | **70 files already formatted** |
| 差分検査 | `git diff --check`、新規ファイルの差分検査、UTF-8 / BOM なし / LF を確認 |

全回帰の失敗は既知の `dist/comictagger_jp_talker-0.3.0.tar.gz` に対する
`tarfile.open()` 内の `PermissionError`。内容検証に到達する前の読み取り拒否であり、
許可された環境で既存 packaging 試験を再実行して 3 件成功した。
**全体 suite が一度で成功したとは記録しない。**
13 skipped は既存の実通信 opt-in、1 xfailed は既知の CIX writer の整数 Volume 0 の制約。
production を変更していないため今回は再 build せず、工程 C の配布物を検証した。
既存 sdist の選択ファイル照合、ZIP の全 production Python の byte 照合、
beta9 loader の既存統合試験は成功。E0 の新規文書・試験が配布物へ収録済みという意味ではない。

初回の新規試験は **30 failed / 549 passed**、16.31 秒。
ADD_MISSING の旧 None + 新 `""` が `""`、旧 `""` + 新 None が None となる実装を、
欠損表現まで同じと仮定していた期待値が原因だった。raw 入力を変えず、表現差を明示して修正した。
単独の GUI 試験の初回は plugin registry 初期化不足の `KeyError: cr` で **1 failed**。
host と同じ `load_archive_plugins()` / `load_tag_plugins()` を setup に追加し、
再実行は **1 passed / 579 deselected**、1.23 秒。その後上記の全 592 件で確認した。
Ruff の初回は B905 が 1 件。固定長の zip に `strict=True` を明記し、対象 4 件と Ruff を再確認した。
これらは新規調査テストの修正であり、既存機能や安全性判定の緩和ではない。

再現コマンド（packaging 再実行のみ許可された環境）:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e0-host tests/test_imprint_host_boundary.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e0-related tests/test_comicinfo.py tests/test_talker.py tests/test_metadata_supplement.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e0-full
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e0-packaging tests/test_packaging.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e0-final-focus tests/test_imprint_host_boundary.py -k share_one_xml
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
git diff --check
git status --short
```

raw evidence の SHA-256 は次の値を維持した。
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`

### 判定と未解決事項

E0 の調査・実証は **GO**、通常文字列の指定版での保存・再読込は **GO**。
既存値保護・host 変換の抑止は、正しい読取、通常値、ADD_MISSING、clear / auto OFF、
後段変更なし、保存検証を満たす部分集合だけ **CONDITIONAL GO**。
任意 raw の往復と Talker 単独の保存安全性保証は **NO-GO**。

将来の診断専用方式、または明示確認・host 保存直前契約を伴う限定方式は設計に限り
**CONDITIONAL GO**。現行設定の案内だけではプラグインの保証にならない。
raw 空白値を参照できる契約、設定とファイルの対応、同時更新、保存検証、
配布 exe の残る操作試験を解決する必要がある。
工程 E の全対象保護は未達で、工程 D の authority 供給・失効・監査も未完了。
**Imprint 自動補完全体は NO-GO**。工程 A～C の基盤の GO は維持する。
commit / push / merge / tag / GitHub Release は実行していない。

## Phase 2C-2C-3E1：Imprint 提供方式と host 保存契約（2026-10-20）

### 調査・設計の範囲

開始状態は `main`、HEAD `cbce602f07a3559b8299a8e55c2dfc9d13d29022`。
工程 A～C・E0 等の既存差分は変更済み 9 / 未追跡 13 ファイル。
Windows 11、既存 `.venv` の Python `3.12.14`、ComicTagger `1.6.0b9`、
comicinfoxml `0.5.1` を使用し、依存を変更していない。

E0 報告・専用 592 件、統合設計 §5～§7・§15・§16、工程 A～C・E0 の履歴、
現在の共有取得 / Imprint evaluator / Talker、導入済み host の ComicTalker、
IssueSelectionWindow / QueryThread、ログ表示・ファイル出力、ZIP writer を確認した。

変更は次の 4 ファイルに限定する。

- `docs/phase2c2c_imprint_delivery_design.md`: 新規の提供方式・保存契約の詳細設計。
- `docs/phase2c2c_integration_design.md`: §16 までを保持し §17 を追記。
- `tests/test_imprint_delivery_contract.py`: 現行 API の能力と制約の test-only 実験。
- 本記録: 過去の成功・失敗を保持して E1 を追記。

開始時の既存 84 ファイルの hash と文書コピーを `.research/phase2c2c3e1-start/` に保存した。
production、既存テスト・fixture、E0 報告書、`.gitattributes` は byte 一致を確認した。
設計書と validation の旧本文が完全な prefix として残ることも検査した。
package version `0.3.0`、identity `phase2b2-v1`、evaluator `phase2c2b-v1` は維持。
診断 command、設定、authority provider、Imprint への代入、host patch は追加していない。

### 現行 API の確認と選定

ComicTalker に診断専用 callback / 保存先 / purpose はない。
進捗 callback と `RLCallBack(callback, interval)` は archive の同一性を伝えない。
metadata の Notes / description、check_status、NDL エラー履歴を候補表示の代替に使わない。
ApplicationLogWindow と ComicTagger.log は実在する閲覧経路だが、独立した診断実行口は別途必要。

第一候補は **明示診断 command（比較方式 B、CONDITIONAL GO）**。
NDL ID 一件・通信許可・既存の制限を使い、raw / 完全性 / issues / 理由・unknown 時刻と、
authority 未供給・保存先未評価・書込なしを表示する。通常 fetch / Series OFF に通信を追加しない。
現行 Series 入口は evidence を外へ返さないため、別 command の取得を同じ snapshot と称しない。
pure report は供給された evidence を再利用して通信ゼロにできる。

将来候補は host の保存直前確認付き限定補完（比較方式 C）。
raw の存在、ファイル同一性、operation token、最終 metadata、設定、authority、有効な receipt、
排他と条件付き commit、fresh reader 検証・監査を別々の責務として定義した。
現在の ZIP writer は append / remove / repack / write で、原子的な欠損時適用契約はない。
事前・事後 hash、plugin 内 mutex、atomic rename だけで TOCTOU を解消したと扱わない。
初期契約案は空要素も既存値として保護し、正常に確認した要素不存在だけを適用対象とする。
E0 の reader 損失を normalize で隠さず、通常単一行だけに出力範囲を限定する。
CR / CIX は同じ XML なので初期版は一 writer を選択し、両 reader で検証する。
これらの gate / transaction は今回実装しておらず、その動作を実証済みとはしない。

### test-only 実測

新規 6 件はすべて synthetic / offline。

| 対象 | 実測 |
|---|---|
| host の API | 公開メソッド 8 種、fetch の引数を base / plugin 両方で確認。診断・archive・purpose 引数なし |
| 取得済み evidence の評価（cold / warm 各 1 件） | native source を HTTP mock で取得し、同じ bundle / context を既存 pure API で評価。cold の 3 要求から追加 0。metadata 全体・二つの CBZ の bytes は不変 |
| authority・時刻 | authority tuple は空、ELIGIBLE なし、SEMANTIC_UNVERIFIED を保持。warm の origin_fetched_at と bundle 共通の acquired_at は unknown |
| プレビュー（候補完備 / 不足 各 1 件） | 実 `_fetch()` を周辺 widget の test double で実行。同じ Talker / ID を二つの呼出側で各二回使用。不足時 4 fetch、完備時 0。詳細結果は issue_list に戻らない |
| 最終 fetch との比較 | 実 QueryThread.run() を同期実行。callback が別でも archive / purpose は渡らず、CBZ は不変 |
| 実ログ表示 | host file handler と実 ApplicationLogWindow へ JSON と markup の可逆 escape を行った raw を渡し、ファイルと画面から元の値を復元 |

ログ画面の rich text 解釈を避ける表示形式の検証であり、production renderer ではない。
プレビューの関数単位実行は、検索クリック、取消の競合、実スレッド並行実行、exe 全体の試験ではない。
原子的な保存・利用者確認・保存 gate・authority 供給は未実装のため、後続試験計画と阻害条件に残した。
通常試験の外部 HTTP 禁止を維持し、実 API の opt-in は使っていない。

### 検証結果

| 検証 | 結果 |
|---|---|
| E1 専用試験 | **6 passed**、0.65 秒 |
| E0 保存境界試験の再利用 | **592 passed**、20.88 秒。既存テストは変更なし |
| E1 / Imprint / 共有 evidence / Series 入口 / Talker / GUI / ComicInfo 関連試験 | **616 passed / 1 xfailed**、12.70 秒 |
| 全回帰 | **1 failed / 2,615 passed / 13 skipped / 1 xfailed**、58.12 秒 |
| 権限のある環境で packaging 再実行 | **3 passed**、14.16 秒 |
| Ruff check | **All checks passed** |
| Ruff format check | **72 files already formatted** |
| 差分・形式 | `git diff --check` と未追跡文書・試験の差分検査、UTF-8 / BOM なし / LF を確認 |

全回帰の唯一の失敗は既知の sdist 読み取り `PermissionError`。
`tarfile.open(dist/comictagger_jp_talker-0.3.0.tar.gz)` が内容検証前に失敗した。
同じ既存 packaging 試験を許可された環境で再実行して 3 件成功した。
**全体 suite が一度で成功したとは記録しない。**
13 skipped は既存の network opt-in、1 xfailed は既知の CIX の整数 Volume 0 制約。
今回配布物を再生成していない。工程 C の sdist / ZIP と既存 beta9 loader の互換性を再確認した結果であり、
E1 の文書・試験・将来の command が配布済みという意味ではない。

専用試験の初回は **1 failed / 5 passed**、0.71 秒。
test-only の `RLCallBack` フィールド名の期待値を誤って `sleep_before_callback` としていた。
導入実装の `callback / interval` を確認してテストを訂正し、6 件成功後に関連・全回帰を実行した。
host や production を修正して合わせたものではない。

再現コマンド（packaging 再実行のみ許可された環境）:

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e1-probes-final tests/test_imprint_delivery_contract.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e1-e0 tests/test_imprint_host_boundary.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e1-related tests/test_imprint_delivery_contract.py tests/test_imprint_candidates.py tests/test_linkage_evidence.py tests/test_metadata_supplement.py tests/test_talker.py tests/test_gui.py tests/test_comicinfo.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e1-full
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra -p no:cacheprovider --basetemp .research/phase2c2c3e1-packaging tests/test_packaging.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
git diff --check
git status --short
```

raw evidence の SHA-256 は維持:
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`

### 判定と次工程

- 比較 A（現行 Talker API だけの独立診断）: **NO-GO**。既存ログという表示手段と専用入口を区別する。
- 比較 B（明示診断 command）: **CONDITIONAL GO**、第一候補。pure report → 明示実行 → 配布受入の順。
- 比較 C（host の確認付き限定保存）: host 側の設計・実験は **CONDITIONAL GO**、現行の補完実装は **NO-GO**。
- 比較 D（限定自動補完）: **NO-GO**。保存契約・authority・無人処理の受入が不足。
- 比較 E（自動補完を見送る）: **GO**。B の診断と両立する現在の production 方針。

host 改変、Windows / filesystem ごとの transaction 保証、raw 状態の契約、receipt と複数 archive の対応、
監査・復旧、配布 exe の操作確認が残る。工程 D の真正性・独立性・対象適合・期限・失効・監査も未解決。
工程 D が成功しても host 保存が未達なら F を開始しない。
工程 A～C の基盤と E0 の調査 GO を保持し、**Imprint 自動補完全体は NO-GO**。
commit / push / merge / tag / GitHub Release は実行していない。


## CI / Release の証明書対策と Python 3.14 系への対応（2026-10-23）

### 背景と変更範囲

[Python Packaging の公式勧告](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576)
に基づき、eMudhra / emSign の証明書問題に対して CI / Release のパッケージ取得を保護し、
Python 3.14 系の互換性を継続的に検証する構成とした。
安全性を確認していない pip による依存取得を避け、Python のパッチ選択とパッケージ管理の
セキュリティ下限をそれぞれ検証する。

実装と検証記録の対象は次の 5 ファイル。

- `.github/workflows/test.yml`: Python 3.10 / 3.12 / 3.14 のテスト、最新安定パッチの選択、
  Python 3.14 の下限検証、test / build の pip 更新と依存関係検証。
- `.github/workflows/release.yml`: 依存導入前の pip 更新と導入後のセキュリティ検証。
- `.github/scripts/bootstrap-pip.ps1`: 共通の pip 更新処理と実際の Python バージョンの出力。
- `.github/scripts/verify-python-security.py`: pip、同梱 certifi、必要な環境の独立した certifi の検証。
- `docs/validation.md`: 仕様・検証結果・残存する制約の記録。

### Python バージョンの選択とセキュリティ下限

CI テスト マトリックスは `['3.10', '3.12', '3.14']`。
`actions/setup-python@v7` と `check-latest: true` を使用し、各系列について
Actions の配布一覧で利用可能な最新安定パッチを選択する。
`allow-prereleases` は既定の false を維持する。
キャッシュ内の古いパッチを優先しない選択方法は
[setup-python の公式仕様](https://github.com/actions/setup-python/blob/v7/docs/advanced-usage.md#check-latest-version)
に基づく。将来の 3.14 パッチも Actions で利用可能になればワークフローの変更なしで選択できるが、
Python 本体の公開直後から Actions で取得できることを保証する設定ではない。

`matrix.python-version == '3.14'` のステップだけで、実際の `sys.version_info` が
3.14 系、3.14.9 以上、かつ `releaselevel == "final"` であることを検証する。
3.14.9 未満、プレリリース、別系列は拒否する。
実バージョンをログに出力し、違反時は `SystemExit` と PowerShell の終了コード検査で停止する。
`assert` を使わないため、Python の最適化設定によって検証が無効にならない。
この 3.14 専用条件を Python 3.10 / 3.12 に適用しない。build / Release は Python 3.12 を維持する。

[Python 3.14.9 の公式案内](https://www.python.org/downloads/release/python-3149/)
に同梱 pip 26.2.2 / certifi 2026.10.19 による eMudhra 対策が記載されているため、
3.14 系の最低セキュリティ バージョンを 3.14.9 とした。
ローカルで互換性を検証した具体的なバージョンは Python 3.12.14 と Python 3.14.9。

### pip / certifi のセキュリティ対策

pip >=26.2.2、certifi >=2026.10.19 を必須とする。
公式勧告にある uv >=0.13.4、sigstore >=4.5.1 については、CI で使用していないため導入していない。
古い pip は独立した certifi を更新しても自身の同梱 CA を使い続けるため、両者を区別して検証する。

全ジョブで checkout → setup-python → ハッシュ付き pip wheel の再導入 → pip / 同梱 CA の検証
→ 各ジョブの依存導入、の順序とする。3.14 の test ジョブでは setup-python の直後に Python の下限も検証する。
[PyPI の pip 26.2.2](https://pypi.org/project/pip/26.2.2/) と公式案内で
wheel URL、SHA-256、Python >=3.10 の要件を照合した。
公式 wheel は `pip-26.2.2-py3-none-any.whl`、SHA-256 は
`fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70`。
完全な URL とハッシュは共通スクリプトに一元化している。

`--no-deps --no-cache-dir --force-reinstall` を指定し、同一バージョンも再導入する。
`--disable-pip-version-check` で古い pip の追加の更新確認通信を止め、
TLS 検証を無効化せずに取得した wheel のハッシュ照合を必須とする。
[setup-python v7 の実装](https://github.com/actions/setup-python/blob/v7/src/find-python.ts)
では `pip-version` が既存 pip による通常の更新を呼び出すため、安全な更新の起点には使用しない。

バージョン比較は pip 同梱の `packaging.version.Version` を使い、追加依存を導入しない。
pip と同梱 certifi を検証し、test / Release では独立した `certifi>=2026.10.19` も
明示的に導入して実バージョンを検証する。依存導入後には `pip check` を実行する。
最低版未満、最低版の rc / dev 版、必要なパッケージの欠落、更新・検証コマンドの非ゼロ終了は
ジョブを失敗させる。

build では `build` 導入直後に `pip check` を実行し、続いて `--no-deps -e .` で
バージョン取得用のメタデータを導入する。メタデータ導入後の全体 `pip check` は、
意図的に省いた本体依存を不足と判定するため実行せず、pip / 同梱 CA を再検証する。
GUI / 開発用依存や独立した certifi は追加しない。
ローカルで確認した build 1.6.1 は、隔離ビルドの依存取得にも外側の更新済み pip を使用する。

### CI / Release の既存動作と互換性

`requires-python = ">=3.10"`、Ruff の `target-version = "py310"`、公開バージョン `0.3.0` を維持。
NDL / MADB の取得・検索、Imprint の判定、メタデータのマッピング、GUI を含む本番コード、
既存テスト、`pyproject.toml`、`.gitignore`、`scripts/build_plugin.py` は変更していない。
既存の未コミット変更も保持した。CI 専用スクリプトは `.github/scripts/` に配置している。

Ruff、`pytest -m "not network"`、`QT_QPA_PLATFORM=offscreen`、`PYTHONUTF8=1`、
テスト失敗時のジョブ停止、既存の除外条件を維持する。
build / Release の wheel / sdist / ComicTagger プラグイン ZIP の生成、
成果物の名前と内部構造、アップロード処理、GitHub Actions の権限・認証も保持する。
Release の `vX.Y.Z` タグ検証、パッケージ バージョンとの照合、安全な生成物削除、
ZIP の隔離ホスト テスト、構造・メタデータ検証、同名資産の重複アップロード防止を維持する。
YAML の構造比較で、build のバージョン取得以降と Release のタグ照合以降のステップが
変更前と一致することを確認した。

`gh release create --verify-tag` は
[タグの存在確認](https://cli.github.com/manual/gh_release_create) であり、暗号学的な署名検証ではない。
現行ワークフローには署名済みタグの暗号学的な検証処理はなく、この対策でも追加していない。

### ローカル検証結果

以下は最終検証の実測結果。Python 3.14.9 はローカルの検証環境のバージョンを示す。

| 検証 | 結果 |
|---|---|
| Python 3.12.14 / `.venv` | **2,616 passed / 13 deselected / 1 xfailed**、65.70 秒 |
| Python 3.14.9 / `.tools/venv-py314` | **2,616 passed / 13 deselected / 1 xfailed**、65.43 秒 |
| Ruff | 両環境の `ruff check .`、CI 専用スクリプトの明示検査とも成功 |
| 依存整合性 | uv 0.13.4 の `pip check` が両環境で成功、40 / 38 パッケージ。両環境の certifi は 2026.10.19 |
| Actions / YAML | actionlint 1.7.12、PyYAML の構文・順序・マトリックス・権限・既存処理比較が成功 |
| PowerShell 構文 | GitHub 式を仮の値に置換して全 run ブロックと更新スクリプトの構文解析に成功 |
| Python 下限 | 3.14.8 / 3.14.9 / 3.14.10 / 3.14.11 / rc / alpha / 別系列の 8 ケースが成功。最適化付きコンパイルでも確認 |
| 実環境の下限検証 | ワークフローから抽出した PowerShell ステップを Python 3.14.9 で実行して成功 |
| pip / certifi | 一時環境で公式 wheel の取得・再導入、同梱 / 独立 certifi の検査、`pip check` が成功 |
| pip / certifi の条件検証 | 版境界・欠落など 18 ケースが成功 |
| PowerShell の失敗停止 | 更新処理の正常 / 異常終了 4 ケースが成功 |
| Python 3.10 の構文互換性 | CI 専用 Python スクリプトを `ast.parse(feature_version=(3, 10))` で確認 |
| 配布物 | 安全な pip の一時環境で wheel / sdist の隔離ビルド、既存スクリプトによる ZIP 生成が成功 |
| packaging テスト | 新規生成物で **3 passed**、14.83 秒。sdist 内容と ZIP の本体一致、隔離ホストでの読み込みを確認 |
| Release 用 ZIP 検証 | ワークフロー内の Python 検証コードを抽出し、新規 ZIP に対して成功 |
| Git / 改行 | `git diff --check` 成功。実装・記録の変更ファイルは UTF-8（BOM なし）/ LF |

回帰テストは以下の条件で実行した。`network` マーカーは有効化せず、警告の出力もなかった。

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
$env:PYTHONUTF8 = '1'
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m pytest -m 'not network' -p no:cacheprovider
.tools/venv-py314/Scripts/python.exe -m ruff check .
.tools/venv-py314/Scripts/python.exe -m pytest -m 'not network' -p no:cacheprovider
.tools/actionlint-1.7.12/actionlint.exe .github/workflows/test.yml .github/workflows/release.yml
```

既知の Windows のアクセス制約については許可された環境を使用し、pytest のキャッシュを無効化した。
所有権・ACL・既存キャッシュ、`.venv` / `.tools/venv-py314` の依存は変更していない。
検証用コード、ビルド ログ、最終成果物は Git 対象外の `.research/ci-security-py314-20261023/`、
pip の更新・ビルド用一時環境は `.research/ci-security-20261022/bootstrap-env/` にある。
最終成果物は `source/dist/` に出力し、リポジトリ直下の既存 `dist/` は変更していない。

### 未検証事項と今後の確認

GitHub Actions 実環境での実行、Python 3.10 のローカル・CI 実行、
ホストされた Windows での最新パッチ取得・依存解決・資産アップロード・Release 登録は未検証。
[公式 versions-manifest](https://github.com/actions/python-versions/blob/main/versions-manifest.json)
で 3.14.9 の Windows x64 配布を確認したことは、実ジョブの成功を意味しない。
将来の Python 3.14 パッチとの互換性は未保証であり、選択された版ごとに CI で確認する。

この対策は CI / Release の Python パッケージ取得が対象で、OS の証明書ストア、
既存の全仮想環境、配布済み ComicTagger ホスト、利用者環境の更新は対象外。
依存全体のハッシュ固定や署名検証の新設も行っていない。
pip の wheel を更新する際は、公式 URL・SHA-256・最低バージョン・同梱 certifi の検証条件を
まとめて見直す必要がある。

PR 前には CI 関連の変更と既存の機能開発差分を区別し、新規スクリプトの追加漏れを確認する。
通常の CI で test の 3 系列と Python 3.12 の build、実際の Python / pip / certifi のログ、
生成 ZIP を確認してからマージする。Release 前にはタグとバージョン、同名資産の保持、
隔離ホスト テストを確認する。
将来 Release を Python 3.14 系へ移す場合は、ビルド依存・wheel / sdist・ZIP メタデータ、
ComicTagger 1.6.0b9 の隔離ホスト テスト、公開経路を改めて検証する。
commit / push / tag / GitHub Release の作成・更新 / Actions の手動実行は行っていない。

## Phase 2C-2C-4R1：純粋 Imprint 診断 report（2026-10-23）

開始状態は `feat/madb-imprint-integration` / `2a12b22360dc1c129abbd8b6d678f6df725074cb`、
clean、package `0.3.0`。指定された基点と一致し、既存 6 コミットを変更していない。
`commit.gpgsign=true` / `gpg.format=ssh` を確認した。
環境は Python `3.12.14`、ComicTagger `1.6.0b9`、comicinfoxml `0.5.1`。

### 実装範囲と純粋性

`imprint_report.py` に frozen な report と純粋な構築・JSON 変換 API を追加した。
確定契約は [R1 文書](phase2c2c_imprint_report.md)、統合設計の追記は §18。
schema は `imprint-report-v1`。既存の取得・identity・意味判定規則と通常 Talker / Series 出力は維持する。
全 Book 台帳・discovery page・traces・issues、raw provenance、分類・比較・意味評価を保持する。
除外 bundle を再照合せず、失敗・未取得を空 bundle に変換しない。

authority は未供給、保存先・既存値は未評価、operation=READ_ONLY、
apply_allowed / writes_performed=false。HOLD / REJECT / SKIP をそのまま残す。
report に mutable な BookRecord を保持せず、snapshot の独立コピーだけを evaluator に渡す。

専用試験では import 後に source / session 生成、HTTP、cache、SQLite、Path / open、clock helper、
logger、GenericMetadata 生成・更新、ComicArchive 生成・保存を禁止して API を実行した。
同一入力の結果一致、入力・元 BookRecord・metadata・CBZ・既存エラー履歴の不変、stdout / stderr 無出力を確認。
JSON 変換後の dict を変更しても report は変わらない。
通常試験は既存 autouse fixture で外部 HTTP を禁止し、通信試験の opt-in は有効にしていない。

### 検証結果

| 対象 | 結果 |
|---|---|
| R1 専用試験 | **208 passed**、8.57 秒 |
| 指定の関連 9 ファイル、権限付き再実行 | **1,519 passed**、56.00 秒。skip / xfail / fail なし |
| 全体 suite、権限付き実行 | **2,825 passed / 13 skipped / 1 xfailed**、69.59 秒。fail なし |
| Ruff check | **All checks passed** |
| Ruff format check | **76 files already formatted** |
| sdist / wheel | 最新 source から `build --no-isolation` で生成成功。wheel は sdist から生成 |
| plugin ZIP | 既存 `scripts/build_plugin.py` に wheel を渡して生成 |
| 配布物の source 比較 | sdist / wheel / ZIP それぞれ全 **24 production Python ファイル**の集合・bytes が一致 |
| wheel import | 隔離プロセスで wheel 内の report API を import・実行。session 生成なし |
| ComicTagger loader | 実 ZIP を beta9 loader で読込。path cleanup 後の従来 fetch / Series 補完・共有 core が成功 |
| 設定・entry point | 既存 Talker のみ。新規 console entry point・Imprint 設定・自動書込なし |
| 差分・文字形式 | `git diff --check`、明示ステージ後の cached diff check。変更テキストは UTF-8 / BOM なし / LF |

13 skipped は NDL 関連 9、linkage 2、MADB 2 の既存 opt-in 通信試験。
1 xfailed は既知の CIX writer の整数 Volume 0 省略。配布物依存試験の skip はない。
既報の 2,614 passed / 15 skipped / 1 xfailed に対し、新規 R1 の 208 件、
新規 wheel 試験 1 件、配布物が存在して実行された既存 2 件が passed に加わった。

専用 208 件には既存 linkage 24 ケース × 2 scope × trace 有無、実測 RDF 39 件、
単一・複数 brand、Book / Series 一致・競合、Series-only、reading / IRI / bnode / datatype、
publisher / edition 同名、階層・結合・雑誌名・XML 不正値、authority 未供給を含む。
実測 RDF に付けた取得 context は synthetic と明示し、本番 authority を供給・検証したとは扱わない。
正常 0 件・有効 ISBN なし・partial 0 件・truncated・Book / Series failure・relation budget・
Agent / Holding 未要求・trace 不在・cache 原時刻不明を元台帳と照合した。
500 候補、同一 ID の重複項目、1,000 件以上の event を省略せず保持する。
JSON の全文 roundtrip と独立した dataclass 展開の一致、制御文字・Unicode・空白・時刻 offset の保持、
未対応型・NaN / Infinity・schema / 保存状態の契約違反拒否を確認した。

### 失敗の原因と対応

最初の専用試験は 94 failed / 111 passed。
共通の test helper が既存 `source_for()` の full 用 `get` だけを設定し、
軽量取得の `get_for_series_linkage` に synthetic bundle を返していなかったことが原因。
helper の対応を修正すると 204 passed / 1 failed となった。
残った大量候補試験は既存 fixture parser の 300 行 cap を超えていたため、
取得済み parsed snapshot を直接組み立てる synthetic 試験へ変更した。production cap は変更していない。
その後の追加試験では 207 passed / 1 failed。異なる ISBN を UNMATCHED と期待していたが、
既存 linkage は ISBN conflict を UNSAFE とする。URL / ISBN 証拠がない UNMATCHED 入力へ訂正し、
208 passed を確認した。identity や evaluator をテストに合わせて緩和していない。

最初の sandbox 内 build は既存 sdist を置換する `os.remove(result_path)` で
`PermissionError: [WinError 5]`。同じ build を許可された権限で再実行して成功した。
ZIP 生成も wheel を開く段階の PermissionError を確認し、権限付きで成功した。
関連試験の最初の実行は **2 failed / 1,517 passed**、53.78 秒。
失敗は sdist の `tarfile.open` と wheel の `zipfile.ZipFile` の読み取り権限で、内容検証前の例外。
この実測 stack を確認したうえで同じ関連試験を権限付きで再実行し、1,519 passed となった。
全体 suite はこの権限制約を踏まえて権限付きで実行し、上記のとおり成功した。
以前の PermissionError と同じものだと仮定して失敗を除外した結果ではない。

### 再現手順と配布境界

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp .research/r1-final tests/test_imprint_report.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -m build --no-isolation
.venv/Scripts/python.exe scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp .research/r1-related-authorized tests/test_imprint_report.py tests/test_imprint_candidates.py tests/test_linkage_evidence.py tests/test_madb_acquisition.py tests/test_metadata_supplement.py tests/test_series_supplement.py tests/test_imprint_delivery_contract.py tests/test_imprint_host_boundary.py tests/test_packaging.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp .research/r1-full
git diff --check
git diff --cached --check
```

配布物は `dist/comictagger_jp_talker-0.3.0.tar.gz`、
`dist/comictagger_jp_talker-0.3.0-py3-none-any.whl`、`dist/jpbooks_talker-plugin-0.3.0.zip`。
保存先の権限制約があるため build / ZIP / 配布物を含む pytest は許可された権限で実行した。
文書確定後にも build / ZIP と packaging 4 件を再実行する。
loader 試験は従来の default OFF、EXACT / STRONG、cold 3 要求 / warm 追加 0、
Agent / Holding 詳細要求 0、出力変更が Series / Notes のみであることを維持する。
Windows 配布 exe の画面操作、未実装の診断コマンドの起動・実用性を確認したものではない。

raw evidence の SHA-256 は変更なし:
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`。
`.gitattributes`、既存 production module、package version は変更していない。

### 判断と残る事項

**R1 は GO**。取得済み evidence の純粋な診断、全候補・失敗・raw・unknown の保持、
未供給 authority / 保存先未評価 / 保存不可、既存回帰と配布互換性を確認した。
R1 の重大な未解決問題はない。report の JSON は意図的に snapshot を複数箇所に含み、
R2 の renderer は表示の escape と出力失敗を扱う必要がある。
R2 は明示通信許可、既存制限、確実な close、中断・失敗、通常経路非接続を条件に開始できる。
R2 / R3 は未実装、authority の真正性・対象・期限・失効と host 保存契約は未解決。
**Imprint 自動補完全体は引き続き NO-GO**。

R1 の 6 ファイルのみを明示的にステージし、SSH 署名付きの独立したローカル commit として記録する。
既存履歴の rebase / amend / squash、push / merge / tag / GitHub Release は行わない。

## Phase 2C-2C-4R2：明示実行の読み取り専用 Imprint 診断 CLI（2026-10-23）

### 開始状態と範囲

ブランチは `feat/madb-imprint-integration`、開始 HEAD は
`20d7cad92ff0abbdb3ceb63a054e7b0c5eb603aa`。作業ツリーは clean で、依頼された R1 完了状態と一致した。
Windows の既存 `.venv`、Python **3.12.14**、package version **0.3.0** を使用した。
Git の `commit.gpgsign=true` / `gpg.format=ssh` を維持する。

新規 production module は `imprint_diagnostics.py` のみ。
`tests/test_imprint_diagnostics.py` と新規契約文書を追加し、packaging 試験を拡張した。
統合設計には §18 を維持して §19 を追記した。R1 / E0 / E1 の試験、既存 production module、
identity / evaluator、通常 Talker、metadata_supplement、Series policy、package version は変更しない。

### 確定した動作

- `--ndl-id` 一件と `--allow-network` が必須。`--format` の既定は text、JSON も選択可能。
  help / version、無許可・不正入力で source / session / cache / HTTP の生成・操作は 0。
- NDL は既存 `get(..., summary_mode="none")` と ID 一致確認。NDL 失敗時に MADB は開始しない。
  MADB は `refresh=False / series_linkage` の既存共有 core を一回呼ぶ。
- source を close してから R1 API を一回呼ぶ。schema は `imprint-report-v1`、
  authority / archive は未供給、保存先未評価、apply_allowed / writes_performed は false。
- text は概要と全 field / trace / candidate を省略せず表示。制御・不可視文字を可逆 escape する。
  JSON は R1 変換だけを使用し、`ensure_ascii=True / allow_nan=False`、stdout に一つの document。
- 標準 logging は処理中だけ抑止し、終了時に復元。stderr のエラー文字列も安全に quote する。
  取得失敗と close 失敗を同時に保持し、全 cleanup を試みる。source 下位 resource の二重 close はしない。
- 終了コードは 0 / 2 / 3 / 4 / 130。HOLD / REJECT / identity conflict は取得失敗にしない。
  no_valid_isbn は意図された非実行として 0、評価材料なしを明示する。不完全 report は出力したうえで 3。
- NDL get の全 refresh 契約がないため `--refresh` は省略した。source constructor 内部の部分初期化、
  失敗した close の解放保証、全 report のメモリ使用、単一スレッドの logging 抑止を既知の制限として記録した。

### 検証結果

| 対象 | 結果 |
|---|---|
| R2 専用試験 | **191 passed**。下記 focused / 関連 / 全体で実行 |
| R1 再検証 | 既存 **208 passed**。変更・削除なし |
| 最終 focused（R2 + R1） | **399 passed**、22.49 秒 |
| 関連 10 ファイル | **1,718 passed**、75.97 秒。skip / xfail / failed なし |
| Python 3.12 全体 suite | **3,024 passed / 13 skipped / 1 xfailed**、82.70 秒。failed 0 |
| Packaging | **12 passed**。既存 4 件と新規 wheel CLI 8 ケース。関連 / 全体にも含む |
| Ruff check | **All checks passed** |
| Ruff format check | **79 files already formatted** |
| sdist → wheel → ZIP | 既存 build と build_plugin.py で成功。version は 0.3.0 |
| 全 production Python | **25 ファイル**。source / sdist / wheel / ZIP の集合・bytes が一致 |
| wheel module | 隔離 subprocess で help / version / text / JSON が成功。実 wheel の module を起動 |
| 文字コード・出力障害 | UTF-8 ファイル出力、ASCII JSON roundtrip、text の UnicodeEncodeError=4、broken pipe=4 |
| 中断 | 取得・report・renderer・cleanup の KeyboardInterrupt=130。wheel subprocess の中断も 130 |
| beta9 loader | 最新 ZIP を読み込み、path cleanup 後の通常 NDL / Series 動作を確認 |
| 既存保存境界 | E0 592 件、E1 6 件を維持。GenericMetadata 全 field / Notes / description / Imprint / CBZ bytes / NDL 履歴の不変を確認 |
| テキスト形式 | 変更対象は UTF-8 / BOM なし / LF。git diff check を実施 |

全体の 13 skipped は既存の opt-in 実通信試験（NDL 9、linkage 2、MADB 2）。
1 xfailed は既知の CIX writer による整数 Volume 0 の省略。
配布物未生成による skip はなく、実通信試験は有効化していない。
開始時の 2,825 passed に新規専用 191 件と wheel CLI 8 ケースを加えた 3,024 passed である。

### HTTP mock の実測と安全性

| 条件 | NDL SRU | MADB HTTP |
|---|---:|---:|
| ISBN 1 / Book 1 / Series 1、cold | 1 | 3 |
| 同条件、warm | 0 | 0 |
| Series relation なし、cold | 1 | 2 |
| ISBN 2 / Book 2 / Series 2、cold | 1 | 6 |
| relation 13 件、budget 12 | 1 | 14（discovery + Book + Series 12） |
| 有効 ISBN なし | 1 | 0 |

すべて固定 fixture / synthetic 応答で実 source / parser / cache を通した試験。
全書誌の要求数を保証する表ではない。NDL summary 追加要求 **0**、Agent / Holding 詳細要求 **0**。
典型例では core と CLI からの R1 report API 呼出が各一回で、report 生成中の追加取得はない。
HTTP timeout / 429 / 503 / 接続失敗、NDL 0 件 / ID 不一致 / SRU protocol / XML、
MADB discovery / Book / Series failure、row / byte cap、relation budget、trace 不在も検証した。

24 種の既存 linkage scenario を trace 有無で通し、除外・未取得・失敗・重複台帳、
複数 ISBN / Book、identity conflict を R1 JSON と比較した。
HOLD / REJECT / SKIP の意味を終了コードへ混入しない。
500 raw 候補と 1,001 event を含む重複台帳も text / JSON の両方で省略せず出力した。
日本語・非 BMP・XML 特殊文字・CR / LF / TAB・ESC / ANSI・C0 / C1 / DEL・双方向制御・
ゼロ幅文字・結合文字・外周空白について、terminal-safe 表示と raw の JSON 復元を検証した。

実 source の session / cache close を計数した。
NDL session が失敗しても cache を閉じ、MADB は自身の close で session / cache を閉じる。
取得失敗 + 複数 close 失敗、context exit の例外、nested KeyboardInterrupt を保持する。
JSON serialization 前の未知型拒否、短い stdout write、BrokenPipe、flush、encoding の失敗を非ゼロにする。
stdout を事前に捕捉した logging handler も JSON を汚染せず、logging 設定は復元される。

### 途中の失敗と対応

最初の focused は **16 failed / 374 passed**。
新規 HTTP fixture の ISBN 置換が `488594287X` を探していたが、既存 XML の原値は
`4-88594-287-X` だった。NDL と MADB fixture の ISBN が一致せず、parser が
`Unexpected ISBN exact-search binding` を正しく拒否した。
新規 fixture の置換を訂正し、複数 ISBN fixture の応答も実 query の ISBN に一致させた。
production の ID / ISBN 検証を緩和せず、既存 fixture は変更していない。
修正後 390 passed、異常終了試験の追加後に 397 passed、最終 399 passed となった。

最初の sandbox 内 build は既存 sdist の `os.remove(result_path)` で
`PermissionError: [WinError 5]`。同じ build を権限付きで再実行して成功した。
ZIP 生成も最新 wheel の open で PermissionError を確認し、権限付きで成功した。
配布物の読取を含む packaging / 関連 / 全体試験はこの実測制約に基づき権限付きで実行した。
試験失敗の再分類・除外ではない。

開始 HEAD の SSH 検証は sandbox 内では allowedSigners の読取で Permission denied。
権限付きで同じ `git verify-commit HEAD` を実行し、既存署名設定で正常検証できた。
署名なし commit への切替は行わない。

### 再現コマンドと最終成果物

```powershell
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp .research/r2-focused-contract tests/test_imprint_diagnostics.py tests/test_imprint_report.py
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
.venv/Scripts/python.exe -X utf8 -m build --no-isolation
.venv/Scripts/python.exe scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp .research/r2-related tests/test_imprint_diagnostics.py tests/test_imprint_report.py tests/test_imprint_candidates.py tests/test_linkage_evidence.py tests/test_madb_acquisition.py tests/test_metadata_supplement.py tests/test_series_supplement.py tests/test_imprint_delivery_contract.py tests/test_imprint_host_boundary.py tests/test_packaging.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp .research/r2-full
```

配布物は `dist/comictagger_jp_talker-0.3.0.tar.gz`、
`dist/comictagger_jp_talker-0.3.0-py3-none-any.whl`、`dist/jpbooks_talker-plugin-0.3.0.zip`。
文書確定後にも build / ZIP を更新し、packaging と文書表記を再確認する。
既存 Talker の entry point / 設定、Series default OFF、ON の cold 3 / warm 追加 0 を維持した。
exe 内の診断起動を実装・確認した結果ではない。

raw evidence の SHA-256 は変更なし:
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`。
`.gitattributes` と raw evidence を維持し、R2 の 6 ファイルだけを明示的にステージして
独立した SSH 署名付きローカル commit に記録する。
push / merge / tag / GitHub Release / Actions 手動実行は行わない。

### 判断

**R2 は GO**。明示許可の単一書誌診断、既存取得制限、R1 の意味・schema 保持、
安全な text / JSON、異常終了、通常経路非接続と配布互換性の必須検証に未解決の失敗はない。
constructor 内部の部分初期化など、既存 source の制限は R2 文書に明記した。
R3 は配布方式の合意、実環境での表示・文字コード・終了コード・beta9 共存の受入を条件に開始できる。
実通信の実用性、exe 利用者向け提供、一般配布は R2 の結果だけで完了扱いしない。
本番 authority と host 保存契約は未実装。**Imprint 自動補完全体は NO-GO を維持する。**

## Phase 2C-2C-4R3：Wheel / python -m 配布・実環境利用の受入（2026-10-26）

### 判定と開始状態

**GO 候補・ユーザー レビュー待ち**。既存 Wheel を独立 Python venv に導入し、
`python -m comictagger_jp_talker.imprint_diagnostics` で利用する方式の必須検証は成功した。
未解決の配布阻害要因は見つかっていない。実 exe GUI 操作は NOT RUN だが、独立 Wheel 実行の阻害条件ではない。
正式受入・commit・公開の承認を意味しない。**Imprint 自動補完全体は NO-GO**。

開始時の branch は `feat/madb-imprint-integration`、HEAD は
`450ee5d78eaecb5034f95db39c7ee95915489be6`。status / diff / cached diff は空。
package version は 0.3.0、開発 Python は 3.12.14。
`commit.gpgsign=true`、`gpg.format=ssh` を確認し、変更していない。
使用した PowerShell は 7.6.9。ユーザー報告の実環境は Windows 11 / PowerShell 7.6.8。

今回の検証用ディレクトリは `.research/r3-acceptance-20261026-2aed5ca7/`。
既存 dist の 3 成果物は同ディレクトリの `artifacts-before/` に複製してから build した。
ユーザーの `.research/phase2c2c4r3/` の 5 ファイルは変更せず、前後 hash の一致を確認した。
リポジトリ直下の `report.json` は存在しなかった。

### 独立 Wheel インストールと実行

開発 `.venv` の Python で新しい venv を作成し、site-packages をコピーせず、生成 Wheel を
通常の `pip install` で導入した。依存解決は成功し、外部 package のダウンロードと既存 cache の利用があった。
この package 取得は NDL / MADB の実 endpoint 試験とは別である。
`pip-install.json` に取得元・解決結果、`outputs/pip-freeze.stdout` に導入一覧を保存した。

| 項目 | 実測 |
|---|---|
| Python | 3.12.14。metadata の要件は 3.10 以上で、全 version の実測ではない |
| 独立 venv | `.research/r3-acceptance-20261026-2aed5ca7/venv` |
| package | comictagger-jp-talker 0.3.0 |
| 解決した主な依存 | comictagger 1.6.0b11.dev0 / requests 2.34.2 |
| pip check | No broken requirements found |
| GUI / CIX extras | 独立診断の導入では指定していない |
| 最終 Wheel の反映 | 依存解決済み venv に `--force-reinstall --no-deps` で同一版を反映。metadata の依存指定は変更なし |

実 import 元は
`C:\Work\VSCode\comictagger-jp-talker\.research\r3-acceptance-20261026-2aed5ca7\venv\Lib\site-packages\comictagger_jp_talker\imprint_diagnostics.py`。
`sys.executable / sys.prefix / sys.path / __file__ / direct_url.json` を記録した。
実行 cwd はリポジトリ外の新規 temp ディレクトリ、PYTHONPATH / PYTHONHOME は除去し、editable install は不使用。
`-I` は追加の独立性確認で、正式起動に必須とする変更ではない。
通常モードと `-I` の実 `python -m` で、help / version と 6 種の入力拒否をそれぞれ確認した。
拒否時の stdout は空、exit 2、診断 cache は未生成。
installed module の入力検証には、source factory / HTTP session / cache / mkdir が呼ばれれば失敗する guard も適用した。

`acceptance.py` は既存 packaging test の fixture / HTTP mock を再利用し、Wheel を sys.path に追加する処理を除き、
インストール済み module を実行する検証用スクリプト。合計 **29 subprocess 確認**を記録した
（pip check / freeze 2、実 `-m` 16、入力 guard 1、既存 8 mode、追加 HOLD / 不完全取得 2）。
JSON は単一 document として parse 可能で、schema / version / 全 evidence / 日本語の復元を確認した。
text は日本語を表示し、正常時 stderr は空。ASCII JSON は成功、ASCII text と broken pipe は 4、
中断は 130、取得不完全は report と 3、HOLD / REJECT は 0。
`authority_state=archive_state=not_supplied`、`apply_allowed=writes_performed=false` を維持した。
このスクリプトと結果は Git 管理外に置き、production / 既存テストは変更していない。

### 回帰試験と共存の範囲

| 検証 | 結果 |
|---|---|
| 指定の関連 10 ファイル | **1,718 passed**、75.44 秒 |
| 全体 pytest | **3,024 passed / 13 skipped / 1 xfailed**、86.11 秒、failed 0 |
| Ruff check | **All checks passed** |
| Ruff format check | **80 files already formatted** |
| sdist → Wheel → ZIP | 既存 build / build_plugin.py で成功 |
| production 整合性 | **25 ファイル**。HEAD / source / sdist / Wheel / ZIP / installed の集合・bytes を確認 |
| 配布 metadata | version 0.3.0、Python 要件、従来の Talker entry point を維持。console_scripts なし |
| 混入監査 | .research / venv / 実測 report / 資格情報ファイル / cache DB なし。全 member 一覧を記録 |
| beta9 loader | 最終 ZIP を用いた実 loader コードのロード、path cleanup、NDL 検索・取得が成功 |
| Series 回帰 | default OFF、opt-in ON、exact / strong、cold MADB 3 回・warm 追加 0 回を HTTP mock で確認 |
| Imprint 境界 | 通常経路への診断接続・自動保存なし。E0 / E1 と既存設定を維持 |
| 実 ComicTagger.exe GUI | **NOT RUN**。検索した PATH / 配置候補で exe を確認できず、機械全体での不存在は断定しない |
| 実 NDL / MADB | **今回 Codex は未実行**。追加ライブ通信・opt-in の有効化なし |

13 skipped は既存の opt-in 実通信試験（NDL 9、linkage 2、MADB 2）。
1 xfailed は既知の beta9 CIX writer による整数 Volume 0 の省略。変更・除外による合格ではない。
開発環境の beta9 loader 試験と、独立 venv に解決された beta11.dev0 は別の検証である。
通常検索・候補選択時の不要な MADB 追加取得、Agent / Holding の取得は行わない。
GUI preview の一部は最終 fetch を呼ぶ既知の経路であり、全 preview の通信 0 を保証するものではない。
Series 補完由来の既存 Notes と、禁止する Imprint 診断内容の迂回出力も区別する。

専用 venv は host の Python package と分離され、CLI は host 設定ファイルを読み込まない。
通常 Talker は host から渡された cache folder、診断は専用 root を使用する。
ただし同一ユーザーの診断 venv 同士は root を共有し得る。任意の host カスタム設定まで絶対分離を保証しない。
実 exe での隔離 config / テスト用 CBZ を用いた共存手順は
[R3 配布ガイド](phase2c2c_imprint_distribution_r3.md#6-実測の読み方と手動受入) に記載した。
offscreen 自動試験や loader の成功を、実 exe の画面操作の成功に置き換えない。

### ユーザー報告による実 endpoint 実測と保存証拠

次は **ユーザー報告による実測**であり、Codex は保存ファイルを読み取って照合した。
今回 Codex が同じ書誌を live 再取得した結果ではない。
対象は `R100000002-I023440575`、title は `ご注文はうさぎですか? volume 1`。
ユーザー報告の exit は 0、JSON parse 成功、日本語 text は PowerShell 7.6.8 で正常。
schema は imprint-report-v1、plugin は 0.3.0、identity は phase2b2-v1、evaluator は phase2c2b-v1。
linkage は matched、discovery は complete、Book 1 件、acquisition issues 0 件。
Book M381096 / Series C334830、strong / isbn_normalized、identity conflicts なし。

評価は evaluated / reject、selected candidate は null。
理由は context_conflict / multiple_displays / semantic_unverified。
Book brand は `Kirara menu` と `Manga time KR comics`、Series brand は
`Manga time KR comics　／　Kirara menu`。
MADB publisher `芳文社　∥　ホウブンシャ` と NDL `芳文社` の比較で conflict=true。
表記差が原因の可能性はあるが、確認済み候補の誤拒否とは断定せず、比較アルゴリズムは変更しない。
READ_ONLY、authority / archive 未供給、target_known / existing_value_assessed /
apply_allowed / writes_performed=false を保存 JSON で確認した。matched は保存許可ではない。

保存ファイルは `.research/phase2c2c4r3/` にあった。JSON は UTF-16LE BOM 付きであり、
読み取り時に BOM に従って decode した。既存ファイルを UTF-8 に上書き変換していない。
これは今回の CLI 自身の stdout encoding を実測した証拠とはしない。
Windows PowerShell 5.1 の text リダイレクト時の文字化けと 7.6.8 での正常表示はユーザー報告であり、
Python の取得不良や NDL データ破損、全環境での解消保証には結び付けない。

| 保存済み text の集計範囲 | cache / hit / miss | network | snapshot | relation | scope |
|---|---|---:|---:|---:|---:|
| 全文の trace 表示 | 6 / 6 / 0 | 0 | 6 | 14 | 14 |
| 主台帳 acquisition.traces 部分 | 3 / 3 / 0 | 0 | 3 | 7 | 7 |

全文は同じ trace の重複表示を含む。6 件を独立した HTTP 6 要求とは解釈しない。
network stage がないことも NDL / MADB の実 HTTP 0 件の証明ではない。
text run は `b956146581e642adb9a6bce5e07cbed1`、JSON run は `50b8482dcfc34570bbcf6576d821dd13`。
保存 JSON は別 run で、主台帳の network stage は 3 件。warm text の集計と混ぜない。
ファイル別 hash と集計は `acceptance-results.json` に記録し、再読取時の一致を確認した。

### 再現コマンド・ローカル証跡

新規検証ディレクトリに作成した venv を使用する。既存の同名ディレクトリを使い回す例ではない。

```powershell
$run = '.research/r3-acceptance-20261026-2aed5ca7'
.venv/Scripts/python.exe -X utf8 -m build --no-isolation
.venv/Scripts/python.exe scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -m venv "$run/venv"
& "$run/venv/Scripts/python.exe" -m pip install --report "$run/pip-install.json" dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
& "$run/venv/Scripts/python.exe" -I -X utf8 "$run/acceptance.py" (Get-Location).Path
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp "$run/related" tests/test_imprint_diagnostics.py tests/test_imprint_report.py tests/test_packaging.py tests/test_imprint_candidates.py tests/test_linkage_evidence.py tests/test_madb_acquisition.py tests/test_metadata_supplement.py tests/test_series_supplement.py tests/test_imprint_delivery_contract.py tests/test_imprint_host_boundary.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp "$run/full"
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
git diff --check
```

`build.log / related.log / full.log`、`acceptance.py / acceptance-results.json / outputs/`、
`audit.py / artifact-manifest.json` を検証ディレクトリに保存した。
導入・バックアップ時の sandbox の dist 読取は PermissionError となったため、同じ操作を権限付きで実行した。
build / ZIP / 配布物を読む pytest / 監査も確認済みの制約に基づき権限付きで実施した。
検証スクリプトは初回に保存 JSON の UTF-16 BOM、監査は生成 metadata の CRLF を考慮しておらず停止した。
読取側のみを修正して成功し、製品・証拠ファイルの改変で回避していない。

### 変更と Git の扱い

README に入口、新規 R3 ガイドに導入・実行・更新・アンインストール・文字コード・cache・
トラブルシューティング・手動受入、integration design §20 に配布方式と暫定判定、本文に検証記録を追加した。
R1 / R2 の歴史的な結果や契約を書き換えていない。production、既存テスト、version、build metadata、workflow は不変。
README の追記重複は差分レビューで除去し、その文書を含む配布物を更新する。
最終 hash は以下に追記するため、sdist 内の validation.md は hash 追記前の検証記録となる。
これは hash の自己参照を避けた記録時点の区別であり、production bytes の差分ではない。

すべての変更は未ステージ。HEAD / branch / SSH 署名設定を維持し、cached diff は空。
git add / commit / push / merge / rebase / reset / stash / clean / branch 切替、tag / Release 作成、
Actions 手動実行は行っていない。人間のレビュー後の承認まで正式確定・公開へ進まない。

### 最終配布物の SHA-256 と追確認

上記の文書整理後に配布物を更新し、最終 Wheel の独立 venv 検証 **29 subprocess** と
packaging 12 件 + 文書表記 2 件の **14 passed（21.62 秒）**を確認した。
以下の hash は各成果物を二度読み取って一致した値。異なる build 間の byte-identical 性は保証しない。
ZIP は正式な build_plugin.py が Wheel を複製する仕様のため、両者の hash は同一。
各 production file の bytes、member 一覧、最終 installed Wheel の direct_url hash も照合済み。

| 成果物（dist 内） | SHA-256 |
|---|---|
| `comictagger_jp_talker-0.3.0.tar.gz` | `726df5a7ae067d1d9807f15388c5259f06ba5f5d872cbae0c7ecfb681bd2f151` |
| `comictagger_jp_talker-0.3.0-py3-none-any.whl` | `a024a6e83fd64e6ad6e78c134a5bd24c0e8bebdde5173d2d1dac9a660c07ba95` |
| `jpbooks_talker-plugin-0.3.0.zip` | `a024a6e83fd64e6ad6e78c134a5bd24c0e8bebdde5173d2d1dac9a660c07ba95` |

raw evidence `docs/research/madb/imprint_evidence.json` は変更なし。
SHA-256 は `780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`。
最終 doc 差分と新規ガイドの全文をレビューし、UTF-8 / BOM なし / LF、git diff check、cached diff が空であることを確認した。

## Phase 2C-2C-4R3：レビュー後の文書改善・CLI 英語化（2026-10-26）

### 開始状態とメッセージの棚卸し

branch は `feat/madb-imprint-integration`、HEAD は `450ee5d78eaecb5034f95db39c7ee95915489be6`。
version 0.3.0、署名設定 `commit.gpgsign=true / gpg.format=ssh` を維持した。
開始時は README / integration design / validation の 3 ファイルが変更済み、R3 配布ガイドが未追跡。
これは前回 R3 の意図された変更であり、すべて保持して今回の改善を加えた。cached diff は空。
今回の証跡は `.research/r3-english-review-20261026-8c4f21/` に分離する。

編集前に CLI の全固定文字列・関連例外・R1 report・既存テストを確認し、表示も保存した。
**CLI 自身の固定案内文は既に英語で統一されており、production code の変更は不要**と判断した。
外部例外の詳細、書誌原文、機械判定用の値を英訳するものではない。

| 出力箇所 | 現在の表示・言語 | 変更要否と理由 |
|---|---|---|
| help 説明 | `Read-only Imprint diagnostics for one NDL record. No archive or save operation.` | No。既に英語 |
| 引数説明 | `One NDL bibliographic ID (not a URL)` / `Permit NDL/MADB requests and source cache I/O` | No。既に英語 |
| format / version | format は choices の表示、version は `0.3.0` | No。表示形式を維持 |
| 必須 ID 不足 | `the following arguments are required: --ndl-id` | No。標準 argparse の英語表示 |
| 通信許可不足 | `--allow-network is required (including permission for source cache I/O)` | No。既に英語 |
| ID 不正 | `Invalid NDL ID; expected [A-Za-z0-9_-]+` | No。既に英語 |
| format 不正・未知引数 | `invalid choice:` / `unrecognized arguments:` | No。標準 argparse の英語表示 |
| ID 重複 | `Specify --ndl-id exactly once` | No。既に英語 |
| 外部取得・内部・出力・close エラー | `Imprint diagnostics error: ` と安全に引用した例外 chain | No。CLI 接頭辞は英語。外部詳細は原文を保持 |
| 中断 | `Imprint diagnostics error: ["KeyboardInterrupt: "]` | No。exit 130 と既存の詳細を維持 |
| 不完全取得 | report 内の acquisition state / reasons と exit 3。専用の stderr 文はない | No。新たなメッセージを追加せず、既存表現を維持 |
| text 見出し・状態 | `Read-only Imprint diagnostics` / `Authority: not supplied` / `Apply allowed: no` など | No。既に英語 |
| text 補足 | `Origin timestamp: unknown wherever origin_fetched_at is null; cache is not an origin clock.` など | No。既に英語 |
| JSON field / schema / enum | 既存の英語識別子 | No。機械向け契約 |
| NDL / MADB 原文 | タイトル・出版社・brand・RDF term・provenance | No。翻訳・正規化しない |
| 通常 Talker | 日本語 UI / 設定 / エラー / Notes | No。CLI 固有表示の対象外 |

標準ライブラリの locale / gettext、logging 抑止、取得・評価・保存、cache、依存要件、version は変更しない。
あらゆる OS / locale で外部ライブラリの文章も英語になるという保証はしない。

### 文書とテストの改善

R3 ガイドは構成を保ち、JSON 読込を exit 0 / 3、LiteralPath の Leaf、非空サイズの短絡評価へ変更した。
UTF-8 と `-ErrorAction Stop` を指定し、欠損・ディレクトリ・空ファイルは読まず、不正 JSON は処理を停止する。
stderr の存在確認も追加した。exit 4 / 130 の部分出力を完全な report として利用しない。
pip check / help / version は直後に終了コードを確認し、更新例にも適用した。
PowerShell 7 / `-X utf8 / --format text`、GUID による新規出力先、stdout / stderr 分離、
終了コード保持、UTF-8 読込の text 保存例を追加した。各例で共有する `$python` の前提も明記した。
README と integration design に英語案内と原文保持を短く追記。R2 の仕様・歴史的結果は変更していない。

`tests/test_imprint_diagnostics.py` の既存入力境界・例外テストへ具体的な英語表示の確認を追加した。
不完全取得は text / JSON の両方を通し、日本語書誌原文と外部例外詳細の保持も確認する。
新規テストファイル・共通基盤・production 分岐は追加していない。focused は **416 passed（22.00 秒）**。
全回帰・最終配布物・PowerShell 実行結果は build 後の追記に記録する。
前回の R3 結果と hash は履歴として保持し、新しい値で置換しない。

### 比較・PowerShell・独立実行の結果（2026-10-27）

`compare_cli.py` で編集前後の stdout / stderr / exit を 14 ケース比較し、**すべて同一**だった。
対象は help、version、引数なし、許可なし、ID 不正、format 不正、未知オプション、
正常 text / JSON、HOLD、REJECT、部分取得、取得失敗、中断。
synthetic evidence の run ID と時計だけを固定し、JSON 全文の構造・順序・値・Unicode escaping を含めて比較した。
一部フィールドを無視して一致とする比較ではない。
代表表示は変更前後とも次のとおり。外部取得失敗例は mock によるもの。

```text
Read-only Imprint diagnostics for one NDL record. No archive or save
operation.
imprint_diagnostics.py: error: "--allow-network is required (including permission for source cache I/O)"
Imprint diagnostics error: ["AcquisitionError: NDL timeout"]
Imprint diagnostics error: ["KeyboardInterrupt: "]
Read-only Imprint diagnostics
```

`verify_guide.ps1` はガイドの PowerShell block を抽出して実行した。PowerShell は **7.6.9**。
導入後の pip check / help / version は新規 venv の実コマンドで成功し、それぞれに非ゼロ終了を注入すると
直後の throw で停止することも確認した。
保存例は native Python の起動部分だけを HTTP mock wrapper に置き換え、出力先を新規 temp にした。
wrapper は最終的に installed CLI を runpy で実行し、実 source / parser に fixture 応答を返す。
通常の requests.Session.request は禁止し、live NDL / MADB は使わない。
保存・終了コード保持・ファイル条件分岐・読込・parse はガイドそのものの処理を実行した。

| PowerShell 確認 | ケース数 | 結果 |
|---|---:|---|
| 実 pip check / help / version 一式 | 1 | 全コマンド exit 0 |
| 各確認コマンドの非ゼロ終了注入 | 3 | 指定の日本語 throw で停止 |
| JSON / text 保存 × 完全 / 不完全 HTTP mock | 4 | exit 0 / 3 を保持、UTF-8 読込成功、stderr 空 |
| JSON 欠損・空・ディレクトリ | 3 | Get-Item / parse の不要なエラーなし、読込なし |
| 不正 JSON | 1 | parse 失敗で停止 |
| 正常 JSON、exit 3 JSON | 2 | 日本語を保持して parse |
| exit 4 / 130 の不正な部分 JSON | 2 | parse 対象にしない |
| 角括弧を含む LiteralPath | 1 | wildcard と解釈せず読込 |
| **合計** | **17** | **全件成功** |

文書全 block の構文も解析した。更新・アンインストールの例は構文確認のみで、
架空の次版への更新やアンインストールを実行済みとはしない。
ガイドの実 ID に対するライブ診断、実 ComicTagger.exe GUI、全 locale の表示確認は **NOT RUN**。
前回のユーザー実測は履歴のまま保持し、今回の mock 試験を実 endpoint の結果と表現しない。

新規 venv は `.research/r3-english-review-20261026-8c4f21/venv`。
Python 3.12.14、comictagger 1.6.0b11.dev0、requests 2.34.2、plugin 0.3.0。
通常の pip 依存解決は成功し、package は cache 利用と表示された。package index へのアクセスを含む通常導入であり、
外部通信 0 の証明とはしない。NDL / MADB への追加ライブ通信は行っていない。
開発 site-packages のコピーや editable install は使っていない。
実 import 元は
`C:\Work\VSCode\comictagger-jp-talker\.research\r3-english-review-20261026-8c4f21\venv\Lib\site-packages\comictagger_jp_talker\imprint_diagnostics.py`。
リポジトリ外の temp を cwd とし、通常 / `-I` の実 `python -m` と HTTP mock を含む
**29 subprocess 確認**に成功した。source / cache / session の許可前未生成も維持している。

### 回帰結果と再現コマンド

| 検証 | 結果 |
|---|---|
| focused（CLI / R1 / wording） | **416 passed**、22.00 秒 |
| 関連 7 ファイル | **1,261 passed**、59.85 秒 |
| 全体 pytest | **3,039 passed / 13 skipped / 1 xfailed / 0 failed**、89.98 秒 |
| Ruff check | All checks passed |
| Ruff format | 80 files already formatted |
| build | sdist → Wheel → ZIP 成功。既存手順・version 0.3.0 |
| production Python | 25 ファイル。HEAD / 作業ツリー / sdist / Wheel / ZIP / installed の bytes 一致 |
| beta9 loader | ZIP ロード・path cleanup・NDL 検索 / 取得・Series default OFF / opt-in ON が成功 |
| Series HTTP mock | exact / strong の cold 3 回、warm 追加 0 回。Agent / Holding 詳細なし |
| CLI 出力・保存境界 | 全 evidence と安全な escape、JSON、exit 0 / 2 / 3 / 4 / 130、E0 / E1 を維持 |

前回との差は不完全取得 text 12 ケース、日本語原文 text / JSON 2 ケース、外部例外詳細 1 ケースの計 15。
既存の 13 skipped は opt-in 実通信試験、1 xfailed は既知の CIX Volume 0。無効化や分類変更はしていない。
通常 Talker の production bytes と日本語 about 表示、既存 wording / GUI / 設定の回帰を確認した。
JSON schema・enum・reason・原文・publisher 比較・authority・保存契約には変更がない。

```powershell
$run = '.research/r3-english-review-20261026-8c4f21'
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp "$run/focused" tests/test_imprint_diagnostics.py tests/test_imprint_report.py tests/test_wording.py
.venv/Scripts/python.exe -X utf8 -m build --no-isolation
.venv/Scripts/python.exe scripts/build_plugin.py dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
.venv/Scripts/python.exe -m venv "$run/venv"
& "$run/venv/Scripts/python.exe" -m pip install --report "$run/pip-install.json" dist/comictagger_jp_talker-0.3.0-py3-none-any.whl
& "$run/venv/Scripts/python.exe" -I -X utf8 "$run/acceptance.py" (Get-Location).Path
& "$run/verify_guide.ps1" -Repository (Get-Location).Path
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp "$run/related" tests/test_imprint_diagnostics.py tests/test_imprint_report.py tests/test_packaging.py tests/test_imprint_candidates.py tests/test_imprint_delivery_contract.py tests/test_imprint_host_boundary.py tests/test_wording.py
.venv/Scripts/python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider --basetemp "$run/full"
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m ruff format --check .
git diff --check
```

上記は今回の実行記録であり、存在する venv / basetemp / 証跡を上書きして再実行する案内ではない。
前回成果物は `artifacts-before/`、今回の stdout / stderr・比較・PowerShell 結果・試験ログは新規検証ディレクトリに保持した。
README の重複追記を差分確認で除去した後、最終配布物と独立 venv を更新する。
build 後の最終確認・hash は以下へ追記するため、sdist 内の validation.md はその追記前の記録である。
本番 source は全工程で不変。**GO 候補・ユーザー レビュー待ち**であり、Imprint 自動補完は **NO-GO**。
署名設定を維持し、git add / commit / push / merge / rebase / tag / Release / Actions 手動実行は行わない。

### 今回の最終成果物・Git 確認

文書整理後の最終 build を新規 venv に `--force-reinstall --no-deps` で反映した。
最終 Wheel の **29 subprocess 確認**と packaging / wording の **14 passed（21.89 秒）**が成功した。
production 25 ファイルの bytes、version、従来の Talker entry point を再確認し、console_scripts の追加や
.research / venv / 実測 report / 資格情報 / cache DB の混入はなかった。
以下は今回の最終成果物を二度読み取って一致した SHA-256。前回 hash の置換ではない。
異なる build 間の byte-identical 性は保証せず、Wheel と ZIP の一致は既存の複製仕様による。

| 成果物（dist 内） | SHA-256 |
|---|---|
| `comictagger_jp_talker-0.3.0.tar.gz` | `e4f49fd74bb1013125e771dbfc0b7c0d673c48c0135aece13668b6843441e27b` |
| `comictagger_jp_talker-0.3.0-py3-none-any.whl` | `3a83f87cbb63ac5cf83fdc31f329b8ade8e0af7501e30f51c1c5c55ebd387053` |
| `jpbooks_talker-plugin-0.3.0.zip` | `3a83f87cbb63ac5cf83fdc31f329b8ade8e0af7501e30f51c1c5c55ebd387053` |

raw evidence の SHA-256 は `780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12` を維持。
既存ユーザー実測ファイルも hash が一致し、移動・削除・上書きしていない。
変更は文書 4 ファイルと既存 CLI テスト 1 ファイル。production、package version、build metadata、workflow は不変。
git diff と未追跡ガイドを確認し、すべて未ステージで保持する。HEAD / branch / SSH 署名設定は開始時のまま。
git add / commit / push / merge / rebase / reset / cherry-pick / stash / clean / branch 切替は未実施。
tag / GitHub Release は未作成、Actions 手動実行も未実施。**GO 候補・ユーザー レビュー待ち**を維持する。

## Python サポート方針・2026 年 10 月セキュリティ更新

調査日: 2026-10-28。開始時は `feat/madb-imprint-integration`、
HEAD `2fec0baa24120a473c5f4bc47a6cd12e73fc5489`、未コミット変更なし。
ローカルの `main` 参照は古かった。GitHub の `main` が
`22b588ec467bb13d034112632064ee447fdcf41a` で R3 をマージ済みと確認し、
開始時 HEAD との差がマージ コミットのみでツリーに差がないことを確認した。
`git fetch --no-tags origin main` 後、そのコミットを基点に
`chore/python-runtime-security-202610` を作成し、未ステージの変更を保持した。
`commit.gpgsign=true`、`gpg.format=ssh` は変更していない。

### サポート判断と互換性

- Python 3.10 は [3.10.22 で公式 EOL](https://www.python.org/downloads/release/python-31022/)。
  このプロジェクトの対応も終了し、公開下限を変えずに CI だけ削除することはしない。
- Python 3.11 は [2027 年 10 月まで公式セキュリティ保守中](https://devguide.python.org/versions/)。
  本プロジェクトでは CI の組み合わせと継続保証の範囲を絞るため、3.10 と別の判断として対応を終了する。
  既存利用者がアップグレードを要する互換性変更であり、3.10 の EOL の帰結ではない。
- `requires-python = ">=3.12"`、Ruff `target-version = "py312"`。
  対応下限を上げると Ruff の UP017 / UP042 が新たに有効になるため、
  無関係な日時表記変更と Enum の文字列表現変更を避け、この 2 規則を明示的に除外した。
  本番の Python コード、依存指定、package version は変更していない。
- [ComicTagger beta.9 の設定](https://github.com/comictagger/comictagger/blob/1.6.0-beta.9/setup.cfg)
  は Python 3.10 以上、`gui` は PyQt6、`cix` は comicinfoxml 0.5 系、
  非 Windows は PyICU を要求する。requests との指定に 3.12 / 3.14 を排除する条件はない。
  従来の直接実測は Windows / 3.12.14 / beta.9 であり、今回の新しい安全な系列での実測ではない。
- pip は Wheel の `Requires-Python` を判断するが、ZIP のローダーが同 metadata を拒否条件として
  強制するとは限らない。読み込めることとサポート・安全性は別である。
  [beta.9 の公式配布ワークフロー](https://github.com/comictagger/comictagger/blob/1.6.0-beta.9/.github/workflows/package.yaml)
  は Python 3.13 系を使い、配布は今回の修正以前である。同梱 Python の実際のパッチと更新方法は未確認。
  独立診断用の Python 更新や ZIP 差し替えで、ComicTagger 本体の Python は更新されない。
  安全なホストでの再検証が必要であり、元の beta.9 配布バイナリを修正済みと主張しない。
- 3.13 と 3.15 は metadata の下限を満たすが、今回の CI matrix に含まず、全体回帰は未実施。
  3.15 の依存解決・互換性は将来の実環境試験を要する。

### 公式修正と安全な下限

[2026-10-26 の Python 公式発表](https://blog.python.org/2026/10/python-3152-31410-31318-31216-31118/)
の修正を確認した。実行環境の更新により対処し、このプラグインの通信・書誌・診断処理は変更しない。

| 対象 | 修正が入る版と対応 |
|---|---|
| CVE-2026-115557、eMudhra 中間 CA の失効 | 3.11.18 / 3.12.16 / 3.13.18 / 3.14.10 / 3.15.2 の `ssl` で対象鍵を拒否 |
| CVE-2026-114583、`tarfile.tar_filter` のリンク | 同じ 5 版で修正 |
| `http.cookiejar` の負の version | 同じ 5 版で拒否 |
| CVE-2026-77214 / CVE-2026-102633、同梱 Expat 2.9.0 | 3.11.18 / 3.12.16 / 3.13.18、3.14.9 / 3.15.1 以降で修正 |
| CVE-2024-3220、Windows の `mimetypes.knownfiles` | 3.11.18 / 3.12.16 / 3.13.18、3.14.9 / 3.15.1 以降で修正 |
| header の再折り返し・引用符 | 3.11.18 / 3.12.16 / 3.13.18、3.14.9 / 3.15.1 以降で修正 |
| `tempfile.TemporaryDirectory` の cleanup 競合 | 3.12.16 / 3.13.18、3.14.9 / 3.15.0 以降で修正 |

外部 Expat を使う独自ビルドでは、そのライブラリの修正状況も別途確認する。
CI で実際に選択する安全な最低版は **3.12.16 と 3.14.10**。
標準ライブラリのみの検証スクリプトは、利用者が明示的に検査できるよう 3.13.18 と 3.15.2 も扱う。
期待系列の一致、micro の下限、`releaselevel == "final"` を検査し、未知系列と prerelease を拒否する。
これは CI の fail-closed 判定であり、`Requires-Python >=3.12` 自体は古いパッチを拒否しない。

### CI、配布環境、信頼境界

| ジョブ | 変更前 | 変更後 |
|---|---|---|
| test | Windows / 3.10・3.12・3.14 | Ubuntu 24.04 / 3.12、Windows / 3.14 |
| build | Windows / 3.12 | Windows / 3.14 |
| Release | Windows / 3.12 | Windows / 3.14 |

すべて `check-latest: true` の後、依存インストールの前に実際の Python を検証する。
失敗時は後続の bootstrap を実行しない構成で、[GitHub の既定の成功条件](https://docs.github.com/en/actions/reference/workflows-and-actions/expressions#status-check-functions)
を前提とする。Release の tag / version 確認、Ruff、ネットワークを使わない pytest、
sdist / Wheel / ZIP、beta.9 ローダー、asset 検証と重複回避は維持し、Wheel 公開方式は追加しない。

[Python 3.12.16](https://www.python.org/downloads/release/python-31216/) は source-only で
python.org の Windows installer はない。[Actions の配布一覧](https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json)
には 3.12.16 の Ubuntu 24.04 x64 と 3.14.10 の Windows x64 がある。
[Ubuntu 24.04 runner 一覧](https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md)
には PowerShell、`pkg-config`、`libicu-dev` が掲載されているが、Linux の実ジョブと
PowerShell bootstrap、PyICU / Qt / CIX を含む全テストは **NOT RUN**。
Linux では既存の Windows 専用 GUI テストに元から OS 条件がある。今回新たな skip は追加せず、
Linux で全体回帰を実際に実行する設定としたが、成功を保証するものではない。

既存の SHA-256 固定 pip 26.2.2、pip 同梱 certifi 2026.10.19 以上、独立 certifi 2026.10.19 以上の
検証は維持する。Python の `ssl` の eMudhra 対策と、pip / requests 等の証明書束の更新は別の対策。
Python の修正版は pip 自体の更新前の当該鍵による攻撃を防ぐが、証明書束の検証が不要になる根拠ではない。
Python を検査するまでの `checkout` / `setup-python`、runner イメージと Python の取得・完全性は
別の初期信頼境界である。バージョン検査は配布元やダウンロードの真正性を保証しない。

### 今回のローカル結果

検証コピーは `.research/python-security-20261028/source`。既存 `.venv` は Windows /
Python 3.12.14、ComicTagger 1.6.0b9。3.14.9 の旧 venv は参照先がなく起動できず、
3.14.10 以上のローカル実行ファイルと Linux 実行環境は確認できなかった。
3.12.14 で行った以下の実行は互換性の補助確認であり、今回のセキュリティ受入の成功ではない。
新しい依存パッケージをネットワークからインストールしていない。

| 項目 | 結果 |
|---|---|
| バージョン境界・workflow の順序 | 23 passed。実在しない版を作成する試験ではなく、判定値の単体試験 |
| 実 Python の拒否 | 3.12.14 を 3.12.16 未満として非ゼロ終了。Windows PowerShell の模擬実行で後続 pip 呼出 0 件。実 GitHub runner の停止動作は未実行 |
| bootstrap | Windows PowerShell で Python 呼出を模擬し、hash 固定・検証順序と導入失敗時の停止を確認。実際の pip インストールなし。Linux は未実行 |
| R3 導入例 | PowerShell 構文を検査し、導入例内の Python 検査が 3.12.14 を拒否することを確認。導入は行っていない |
| focused | 611 passed / 4 deselected。診断 CLI、Series、NDL / MADB mock、linkage、packaging を含む |
| 全体 | 3,062 passed / 13 deselected / 1 xfailed / 0 failed。従来の 3,039 passed に新しい 23 件を追加。13 件は `-m "not network"` で除外 |
| Ruff / actionlint | Ruff check、format check と actionlint が成功 |
| sdist / Wheel / ZIP | `build --no-isolation` で新規コピーに生成し、packaging 12 passed。beta.9 の Python package を使う ZIP ローダーと mock による text / JSON CLI を確認 |
| pip check / 依存導入 | **NOT RUN**。既存 venv に pip がなく、古い Python でネットワーク導入しない |
| 3.12.16 / 3.14.10 の実環境、Linux、GitHub Actions | **NOT RUN**。安全な Python による build / Release と独立 Wheel 導入も未確認 |

今回生成した配布物は試験用であり、セキュリティ受入済みの配布物ではない。
metadata の version は 0.3.0、`Requires-Python: >=3.12`、
基本依存は `requests<3,>=2.28` と `comictagger<1.7,>=1.6.0b9`。
`jpbooks = comictagger_jp_talker.talker:JapaneseBooksTalker` を確認し、
本番 Python ファイルの bytes、Wheel と ZIP の bytes、不要な cache / venv / 秘密ファイルの不在を確認した。
sdist に workflow と検証スクリプトを含めるのは、同梱するセキュリティ テストを実行可能にするため。
検証記録と hash の追記前に build したため、その sdist 内の本ファイルは追記前の状態。

| 試験用成果物 | SHA-256 |
|---|---|
| `comictagger_jp_talker-0.3.0.tar.gz` | `a116c08eda7c202229a9c144be8fe38150847ab6bdc94f7ab58b9971bf05bf1e` |
| `comictagger_jp_talker-0.3.0-py3-none-any.whl` | `4b58d447ba27f45808dc825b5bac3218d0bd1cbf9ed24fc16f1985aedc9ef5c3` |
| `jpbooks_talker-plugin-0.3.0.zip` | `4b58d447ba27f45808dc825b5bac3218d0bd1cbf9ed24fc16f1985aedc9ef5c3` |

raw evidence の SHA-256 は引き続き
`780581e27e6041950e12dd93df6e90513d3b8023e7fa4efece411f5a58a43d12`。
実 NDL / MADB endpoint には接続していない。既存の READ_ONLY、`apply_allowed=false`、
`writes_performed=false`、Imprint 自動補完 NO-GO、Series の default OFF は維持する。

次の確認には [Python 3.14.10 の公式配布ページ](https://www.python.org/downloads/release/python-31410/)
を参照し、既存環境を上書きせず新しい環境で 3.14 系の安定版が 3.14.10 以上と確認する。
そのうえで依存導入、`pip check`、全体試験と build / ZIP ローダーを再実行する。
Ubuntu 24.04 / 3.12.16 以上での依存導入・全体試験と GitHub Actions の実行確認も必要。
補助的なローカル検証完了・CI 実行待ちだが、修正版 Python の受入と配布物の安全性は未完了。
変更は未ステージで保持し、git add / commit / push / merge / rebase / reset / stash / clean、
tag、GitHub Release の作成・更新、Actions の手動実行は行っていない。

## Ubuntu / Python 3.13 の CI 設定追加（2026-10-28）

開始時の branch は `chore/python-runtime-security-202610`、HEAD は
`22b588ec467bb13d034112632064ee447fdcf41a`。既存の未ステージ変更を保持して作業した。
直前の「Python サポート方針・2026 年 10 月セキュリティ更新」はその時点の記録である。
以下は、その後の Python 3.13 CI 追加と Python 3.14.10 検証についての更新であり、
直前の 2 系列の matrix と 3.14.10 未実施という記述を現在の状態として扱わない。

| 用途 | OS | Python | 最低セキュリティ版 |
|---|---|---|---|
| test | Ubuntu 24.04 | 3.12 | 3.12.16 |
| test | Ubuntu 24.04 | 3.13 | 3.13.18 |
| test | Windows | 3.14 | 3.14.10 |
| build / Release | Windows | 3.14 | 3.14.10 |

`matrix.include` に Ubuntu / 3.13 を追加し、OS と Python 系列の直積を作らない。
各 test ジョブは `setup-python` の `check-latest: true` の後、
matrix の系列を既存の `verify-python-runtime.py` に渡してから pip を起動する。
3.13.18 の最低版判定は元から実装済みで、同スクリプト、pip の固定、
certifi の下限、Windows / 3.14 の build / Release は変更していない。
全系列で既存の Ruff、依存関係確認、`not network` の pytest を実行する設定を維持する。
[Actions の Python 配布一覧](https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json)
に Ubuntu 24.04 x64 向け Python 3.13.18 があることを確認した。

ユーザーから、今回の追加前に Windows / Python 3.14.10 で次の受入結果を得たと報告されている。
関連 pytest **241 passed**、全体 pytest **3,062 passed / 13 deselected / 1 xfailed**、
Ruff check / format 成功、sdist / Wheel / plugin ZIP の build 成功、
Wheel の `Requires-Python >=3.12`、独立 Wheel の導入と CLI 起動の成功、
Wheel と plugin ZIP の SHA-256 一致。これらは今回のテスト追加前の結果として保持する。

今回のローカル確認は次のとおり。指定された Python 3.14.10 の仮想環境は
サンドボックス内から本体へのアクセスが拒否されたため、許可を得て既存環境を使用した。
依存の追加や更新は行っていない。

| 確認 | 結果 |
|---|---|
| Python runtime | 実行中の Windows / Python 3.14.10 を既存スクリプトで受理 |
| runtime / matrix テスト | **28 passed**。既存 23 件に 3.13 の不足境界 4 件と matrix / build 構成 1 件を追加 |
| Ruff | `ruff check .` 成功、`ruff format --check .` は 82 files already formatted |
| workflow 構文 | 既存 actionlint で `.github/workflows/test.yml` を検査して成功 |
| 既存環境の補助確認 | Python 3.12.14 でも同じ 28 件と Ruff が成功。安全な実環境の受入結果とは区別 |
| GitHub Actions、Ubuntu / Python 3.13 | **NOT RUN**。追加した構成での実ジョブ検証待ち |

3.13.17 / 3.13.18 / 3.13.19、異なる系列と prerelease の判定は単体テストであり、
実際の Python 3.13.18 を起動した結果ではない。Ubuntu / 3.13 のテストは、
Windows 向け ComicTagger beta.9 配布バイナリそのものの統合検証ではない。
Python 3.13 実ジョブ、Ubuntu での依存導入と全体回帰、GitHub Actions の実行結果は引き続き未確認。
Python 3.13 専用の Wheel / ZIP は生成していない。

実行コマンド:

```powershell
.\.tools\venv-py31410-security\Scripts\python.exe .github/scripts/verify-python-runtime.py 3.14
.\.tools\venv-py31410-security\Scripts\python.exe -X utf8 -m pytest -q -ra --tb=short -p no:cacheprovider tests/test_python_runtime.py
.\.tools\venv-py31410-security\Scripts\python.exe -m ruff check .
.\.tools\venv-py31410-security\Scripts\python.exe -m ruff format --check .
.\.tools\actionlint-1.7.12\actionlint.exe .github/workflows/test.yml
git diff --check
```

変更は引き続き未ステージ。git add / commit / push / tag、GitHub Release と Pull Request の作成、
GitHub Actions の手動実行、既存変更を破棄する Git 操作は行っていない。

## 文書統合時の補足検証と CI 失敗記録（2026-10-29 整理前）

2026-10-28 の CI 追加と後続の文書統合時の検証記録。コミット `942691f` 時点の `validation.md` を基準とし、I1 / I2 とは別工程の結果として保持する。

### Qt 修正前の CI 実ジョブ

[GitHub Actions run 40836015773](https://github.com/karigane-cha/comictagger-jp-talker/actions/runs/40836015773) では、Ubuntu の両系列で Python runtime、pip / certifi のセキュリティ検証、`pip check`、Ruff は成功したが、PyQt6 の import 時に `libEGL.so.1` が見つからず pytest が失敗した。各結果は **3,036 passed / 16 failed / 3 errors / 12 skipped / 13 deselected / 1 xfailed**。修正として Linux ジョブに `libegl1` と `libgl1` の導入、および pytest 前の PyQt6 offscreen 初期化確認を追加した。修正後の各実ジョブの成否は未確認。

### 文書統合前後のローカル結果

以下は **2026-10-28 の Python 3.13 CI 追加時までに記録された結果**。表の先頭 3 行は手動検証の報告値であり、実行ログは未確認。後半のローカル検証記録や CI 実ジョブとは区別する。

| 時点・環境 | 検証と結果 | 根拠・範囲 |
|---|---|---|
| 3.13 CI 追加前、Windows / Python 3.14.10 | 関連 pytest **241 passed** | runtime / packaging / diagnostics とされるが、対象内訳の裏付けは未確認 |
| 同上 | 非 network 全体 **3,062 passed / 13 deselected / 1 xfailed**、Ruff check / format 成功 | 関連試験とは別の集計 |
| 同上 | 隔離 build で sdist / Wheel を生成し、`scripts/build_plugin.py` で plugin ZIP を作成。Wheel の `Requires-Python >=3.12`、独立 venv への導入と CLI `--help` / `--version` 成功 | Wheel と ZIP の bytes / SHA-256 は一致 |
| 3.13 CI 追加後、Windows / Python 3.14.10 | runtime / matrix テスト **28 passed**、Ruff check / format と test workflow の actionlint 成功 | ローカル記録。全体 pytest と配布物は再実行していない |
| 3.13 CI 追加後、Windows / Python 3.12.14 | 同じ runtime / matrix テスト **28 passed** と Ruff 成功 | 補助確認。3.12.16 未満のためセキュリティ受入ではない |
| 3.13 CI 追加前、Windows / Python 3.12.14 | 非 network 全体 **3,062 passed / 13 deselected / 1 xfailed** | 別環境での旧記録。上記 3.14.10 の報告とは別の実測 |

後続の文書統合時のローカル検証では、Windows / Python 3.14.10 の既存セキュリティ用 venv で runtime、pip **26.2.2**、pip 同梱 certifi **2026.10.19**、独立 certifi **2026.10.23** の検査と `pip check` が成功した。先行する `pip check` 成功の報告については、実行ログ未確認。

同じローカル検証で、既存の独立診断用 venv をリポジトリ外から `-I` で起動し、Python 3.14.10 と `site-packages` からの import、CLI の `--help` および `--version` **0.3.0** を確認した。導入記録の Wheel ハッシュは下表の旧試験用 Wheel と一致する。新規 build の検証ではない。

3.13.17 / 3.13.18 / 3.13.19 の境界値テストは version 判定の単体試験であり、Python 3.13.18 を実際に起動した証拠ではない。既知の `xfail` は ComicTagger 1.6.0b9 の CIX writer による整数 `Volume=0` の省略。`13 deselected` はネットワーク試験の除外であり、過去の `13 skipped` と混同しない。

3.14.9 の旧環境が起動できなかったこと、当初の 3.14.10 未実施判定、および sandbox 内の権限問題は [履歴](#python-サポート方針2026-年-10-月セキュリティ更新) と [後続の確認](#ubuntu--python-313-の-ci-設定追加2026-10-28) に残している。

### 旧試験用 0.3.0 配布物の確認

2026-10-28 にローカルで生成された **試験用**成果物の SHA-256 は以下のとおり。公開 Release の成果物のハッシュではない。文書統合時に保存済みの 3 ファイルを読み取り、これらの値との一致を確認した。

| 成果物 | SHA-256 |
|---|---|
| `comictagger_jp_talker-0.3.0.tar.gz` | `626d9c3701d765ea43619e1a086552f33b416f17c5b705ca4bc0bfe814d55579` |
| `comictagger_jp_talker-0.3.0-py3-none-any.whl` | `49657a48922eb6b8fa95ca30015fcd6d3d2b05910fb60b28996525908bdf0cc6` |
| `jpbooks_talker-plugin-0.3.0.zip` | `49657a48922eb6b8fa95ca30015fcd6d3d2b05910fb60b28996525908bdf0cc6` |

Wheel / ZIP の生成契約と用途は [配布物の検証](validation.md#配布物の検証)、導入先ごとの手順は [配布ガイド](phase2c2c_imprint_distribution_r3.md) を参照する。

[MANIFEST.in](../MANIFEST.in) の `recursive-include docs *.md` は source tree に存在する両方の検証文書を sdist に収録する設定である。保存済みの上記 sdist を調べたところ、旧 `validation.md` は含まれるが、`validation_history.md` と整理案は含まれない。今後の sdist に履歴を含めるには、その build の source tree に履歴ファイルが必要であり、GitHub Actions では checkout 対象になっている必要がある。

同じ 0.3.0 でも build 時点によって内容は異なる。文書編集後に build した sdist や将来の公開成果物に、上表のハッシュを流用しない。2026-10-26 と 10-27 の異なる試験用ハッシュも [R3 履歴](#phase-2c-2c-4r3wheel--python--m-配布実環境利用の受入2026-10-26) と [レビュー後の履歴](#phase-2c-2c-4r3レビュー後の文書改善cli-英語化2026-10-26) に保持している。

## I1：NDL HTTP 429 診断強化（2026-10-29）

### 実装と署名付きコミット

基準は v0.4.0 の `755b2c56190bf6772bd29de98ba676f253ec208f`。`feat/ndl-http-diagnostics-i1` で実装し、コミット `942691f7f31e3f37d167dcfe24446d1eb788b5d7`、メッセージ `feat: add opt-in NDL HTTP diagnostics` として確定した。署名方式は SSH / ED25519、`git verify-commit HEAD` は I1 コミット確定時に PASS。I2 記録時点で `main` には未マージである。

再現コマンドは固定コミット ID を指定する。確定時の検証とは別の再実行結果は未記録。

```powershell
git verify-commit 942691f7f31e3f37d167dcfe24446d1eb788b5d7
```

対象は次の 6 ファイル。検証成果物・実機ログはコミットに含めていない。

- `comictagger_jp_talker/http_diagnostics.py`：診断コンテキスト、ID、安全なヘッダー解析。
- `comictagger_jp_talker/talker.py`：公開操作と条件緩和段階の識別。
- `comictagger_jp_talker/sources/ndl.py`：HTTP、キャッシュ、limiter / lock 待機の診断。
- `comictagger_jp_talker/errors.py`：HTTP 失敗報告のプライバシー保護。
- `tests/test_http_diagnostics.py`：診断・並行実行・安全性のオフライン試験。
- `docs/ndl_http_diagnostics_i1.md`：診断仕様と Windows 実測手順。

`JPBOOKS_HTTP_DIAGNOSTICS=1` の場合だけ詳細診断を有効にし、環境変数は import 時に固定する。既定 OFF。Correlation ID / Request ID、API、cache、status、elapsed、limiter / lock 待機を記録する。Retry-After / Date だけを長さ制限付きで解析し、検索 URL、CQL、ISBN、Cookie、認証値、外部例外の自由文、不要な個人用パスを追加診断と HTTP 失敗報告へ出さない。root logger と他の logger、handler を変更せず、本体の標準ログを使う。

観測専用であり、通信数・制御、`RequestRate(1, 2)`、SRU `(5, 60)` / Summary `(5, 15)` の timeout、Session の利用方法、キャッシュキー・期限・refresh、CQL・条件緩和順序、検索結果の並び順・`rank_records()`・書誌マッピングは変更していない。自動リトライと SRU クールダウンは追加していない。TalkerNetworkError の型・sub_code・元例外の `__cause__`、Series / Imprint の契約を維持する。

### 実行済みのオフライン検証

以下は I1 実装時の Windows / Python **3.14.10** による結果。コミット対象の 6 ファイルと検証済み隔離ソースの一致を確認している。

| 対象 | 結果 |
|---|---|
| 新規 HTTP 診断 | **68 passed** |
| 既存 NDL / error | **60 passed / 7 passed** |
| その他の重点試験 | **113 passed**。重点全体は **248 passed** |
| ビルド後の非 network 全体 | **3,135 passed / 0 skipped / 13 deselected / 1 xfailed** |
| packaging | **12 passed**。I1 の隔離成果物を参照 |
| Ruff check / format | **PASS** |
| runtime / pip / certifi、`pip check` | **PASS** |
| 差分・ステージ照合 | 指定 6 ファイルのみ、追加 1,297 行・削除 54 行。`git diff --check`、cached diff check は PASS |

13 deselected は実通信試験の除外。1 xfailed は既知の ComicTagger 1.6.0b9 CIX writer の整数 Volume 0 省略であり、新規失敗ではない。保存済みの I1 JUnit XML で `tests=3136` / `failures=0` / `errors=0` / `skipped=1` を確認した。唯一の skipped は `test_zero_volume_is_written_as_zero_in_cix` の `type="pytest.xfail"` で、この既知 xfail に対応する。pytest の通常 skip は 0 件であり、JUnit の skipped と同じ分類ではない。

429 → 次操作の 200、refresh の 429 → 次操作の HIT、条件緩和、例外チェーン、プライバシー、同時実行を mock / fake clock で検証した。HTTP 200 と `http_calls=0` を区別し、既存ログ・時計呼び出し回数の assertion は変更していない。ComicTagger 1.6.0b9 の既存ファイル handler へ DEBUG が到達することと、root WARNING・handler 非追加を確認した。これらは実 NDL 通信による 429 検証ではない。

### 隔離配布物

保存済みビルド依存を RECORD のハッシュで検証し、ネットワーク取得なしの隔離環境で sdist / Wheel を生成した。既存 `scripts/build_plugin.py` で Wheel から plugin ZIP を作成。正準バージョンは **0.4.0** のままだが、正式公開済み v0.4.0 とは異なる診断用ローカルビルドである。

| I1 の成果物 | SHA-256 |
|---|---|
| `comictagger_jp_talker-0.4.0.tar.gz` | `48d453e7b4043adaf201030e62f447cd0b98f99f35440e7641592264d22edc84` |
| `comictagger_jp_talker-0.4.0-py3-none-any.whl` | `c4f0edc08812011bc6fccae476d7d8c9431ac21fabbe2991307e432115cf0e6e` |
| `jpbooks_talker-plugin-0.4.0.zip` | `c4f0edc08812011bc6fccae476d7d8c9431ac21fabbe2991307e432115cf0e6e` |

Name、Version、`Requires-Python >=3.12`、entry point と production Python **26 ファイル**の集合・bytes を照合し、新規モジュールの収録、ZIP の正常性、tests / pyc の非収録を確認した。sdist にはビルド時点の両検証文書を含む。ビルド後に追記された I2 記録はその成果物に含まれない。

本体ローダーによる ZIP 読み込みを診断 ON/OFF の両方で検証した。ローダーの path cleanup 後に保持された ZIP 内のクラスと診断モジュールを確認し、editable install の再 import と混同しないようにした。各モードの fake HTTP は 9 件で同数。既存の `dist/` は変更せず、正式公開 ZIP を置換・公開していない。詳細な使い方は [I1 診断ガイド](ndl_http_diagnostics_i1.md) を参照する。

## I2：Windows GUI 実測（2026-10-29）

### 環境・情報源・確認範囲

Windows GUI で通常検索・書誌取得を手動検証した記録。対象は後に `942691f` として確定した I1 実装。保存済みの 3 ログ原本を読み取り専用で解析し、報告された集計・応答時間との一致を確認した。解析時の新規実通信は未実施。

| 項目 | 値と根拠 |
|---|---|
| OS | Windows 11（環境情報の報告値。ログ上は Windows） |
| ComicTagger | **1.6.0b9**。3 起動のログで確認 |
| Python | **3.14 系**（環境情報の報告値。GUI ホストのパッチ版は未確認） |
| Plugin | **I1 診断ビルド v0.4.0**。ZIP の読み込み記録を確認。正式公開済み v0.4.0 と区別する |
| 診断設定 | `JPBOOKS_HTTP_DIAGNOSTICS=1`。3 起動に `NDL diagnostics enabled:` が各 1 件 |
| API / 操作 | NDL Search SRU / Summary、通常の GUI 検索・書誌取得 |
| 日時 | **2026-10-29 JST**、3 起動分 |
| 配布方式の境界 | Python パッケージ版（全起動に **`PyInstaller: No`**）。Windows 配布版 exe の同梱 Python や保存境界の確認とは区別する |

原本の同一性を照合できるよう、起動順の番号と SHA-256 を保持する。ログ原本・個人用パス・検索内容は公開対象に含めない。

| 起動 | 原本の SHA-256 |
|---|---|
| 1 | `6e756ca28b0f688bc044fcd76abb0c4c0b969ef1f652a7a5cdc7f9a618f4f76e` |
| 2 | `8d0d78cb592d0b12ab0a08ff26aed4aa0cde5cf58fff271cffcce91ffa2b5deb` |
| 3 | `9400f8cc8f7605312c33b02a28ff91355b547ae7b3e4e1a348ebf936839b2869` |

### 起動別の集計

| 起動 | 公開操作 | SRU HTTP | Summary HTTP | HTTP 200 | HTTP 429 | `http_calls=0` の操作 | 成功操作 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 16 | 1 | 1 | 2 | 0 | 14 | 16 |
| 2 | 7 | 1 | 2 | 3 | 0 | 4 | 7 |
| 3 | 7 | 2 | 2 | 4 | 0 | 3 | 7 |
| 合計 | **30** | **4** | **5** | **9** | **0** | **21** | **30** |

公開操作の started / completed はそれぞれ 30 件、HTTP の started / completed はそれぞれ 9 件で、Request ID による対応と各操作の `http_calls` の合計も一致した。HTTP failed イベントはない。Correlation ID / Request ID、cache HIT、API、elapsed の記録を確認できた。

`http_calls=0` の操作は HTTP 200 に含めず、cache HIT の確認イベント数も操作数とは区別する。

<a id="sru-の実-http-応答時間"></a>
<a id="summary-の実-http-応答時間"></a>

### HTTP 応答時間

全 9 件とも HTTP 200。elapsed は本文受信を含む実通信時間で、lock / limiter 待機を含めない。個別値は API ごとに通信開始順で並べ、小数点以下 6 桁にそろえた。

| API | 件数 | elapsed（秒） |
|---|---:|---|
| SRU | 4 | 24.352612 / 7.450194 / 12.190236 / 5.928215 |
| Summary | 5 | 3.319680 / 3.289700 / 1.640061 / 5.295898 / 2.954137 |

応答時間にはばらつきがあるが、その差だけで NDL のアクセス制限や障害を断定しない。

### 判定と未確認事項

ZIP 読み込み、有効化マーカー、ID、実 HTTP と HIT の区別、通信時間、通常検索・書誌取得の成功を根拠に、**I2 の Windows GUI 正常系・キャッシュ系は GO**。

**HTTP 429 は未再現。原因は未特定で、問題が解消したとは判断しない。SRU クールダウンと自動リトライの追加は HOLD**。

- 429 の実機再現と、その応答の Retry-After / Date は未確認。
- 429 直後の別操作で HTTP 200 か cache HIT かを比較する実測は未確認。I1 の mock 検証とは区別する。
- NDL のアクセス制限条件、制限の共有範囲、クールダウンの必要性、自動リトライの採否は未確定。
- Windows 配布版 exe、GUI ホストの正確な Python パッチ版、独立 Imprint 診断との共存・保存境界は確認範囲外。
- `oldest` / `newest` の表示順、本体の画像取得エラー、QWebEngineView は I2 の修正・受入対象外。

追加の接続確認、キャッシュ削除、意図的な連続アクセスで 429 を再現せず、必要な通常利用で継続観測する。429 が発生した場合に、その操作と次の明示操作の cache / status / 通信数 / ヘッダー / 待機 / elapsed / Session ID を比較する。
