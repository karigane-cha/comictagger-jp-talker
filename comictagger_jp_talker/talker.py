"""ComicTagger 1.6 Talker adapter. NDL XML stays entirely in the source layer."""

from __future__ import annotations

import argparse
import logging
import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import settngs
from comicapi.genericmetadata import ComicSeries, GenericMetadata
from comictalker.comictalker import ComicTalker, RLCallBack, TalkerDataError, TalkerError

from comictagger_jp_talker.errors import copyable_errors, report_error
from comictagger_jp_talker.isbn import isbn_from_gtin, normalize_isbn
from comictagger_jp_talker.mapping import infer_volume, resolve_record_number, to_metadata, to_series
from comictagger_jp_talker.mapping import issue_number as normalize_issue
from comictagger_jp_talker.models import SearchPage, SearchQuery
from comictagger_jp_talker.sources.base import BookSource
from comictagger_jp_talker.sources.ndl import ENDPOINT, NDLSource

logger = logging.getLogger(__name__)


class JapaneseBooksTalker(ComicTalker):
    name = "Japanese Books"
    id = "jpbooks"
    website = "https://ndlsearch.ndl.go.jp/"
    logo_url = ""
    comictagger_min_ver = "1.6.0b9"
    attribution = "NDL サーチの API を使用：<a href='https://ndlsearch.ndl.go.jp/'>国立国会図書館サーチ</a>"
    about = (
        "日本語書籍・漫画の書誌メタデータを NDL Search SRU から取得します。API キーは不要です。"
        "<a href='https://ndlsearch.ndl.go.jp/help/api'>API 利用条件</a>と"
        "<a href='https://ndlsearch.ndl.go.jp/help/api/provider'>提供機関別の利用条件</a>をご確認ください。"
    )

    def __init__(self, version: str, cache_folder: Path) -> None:
        super().__init__(version, cache_folder)
        self.api_url = self.default_api_url = ENDPOINT
        self.mediatype = "books"
        self.creator = ""
        self.publisher = ""
        self.maximum_records = 20
        self.search_order = "oldest"
        self.volume_output = "issue"
        self.date_source = "auto"
        self.subject_tags = False
        self._source: BookSource | None = None

    @property
    def source(self) -> BookSource:
        if self._source is None:
            self._source = NDLSource(self.cache_folder, maximum_records=self.maximum_records)
        return self._source

    def register_settings(self, parser: settngs.Manager) -> None:
        # Override ComicTagger's automatically registered key/url settings, as GCD does.
        parser.add_setting("--jpbooks-key", file=False, cmdline=False)
        parser.add_setting("--jpbooks-url", file=False, cmdline=False)
        parser.add_setting(
            "--jpbooks-mediatype",
            default="books",
            choices=["books", "booklet", "digital", "online", "electronic", ""],
            display_name="NDL material type",
            help="books=図書（紙限定ではありません）, booklet=紙, 空欄=限定なし",
        )
        parser.add_setting(
            "--jpbooks-creator", default="", display_name="Author filter", help="タイトル検索の著者"
        )
        parser.add_setting(
            "--jpbooks-publisher", default="", display_name="Publisher filter", help="タイトル検索の出版社"
        )
        parser.add_setting(
            "--jpbooks-maximum-records",
            default=20,
            type=int,
            display_name="Maximum candidates (1–100)",
            help="1 回の検索で取得する候補数。既定 20、最大 100",
        )
        parser.add_setting(
            "--jpbooks-search-order",
            default="oldest",
            choices=["oldest", "newest", "title"],
            display_name="Title search order",
            help="取得順：oldest=刊行年の古い順、newest=新しい順、title=タイトル順。画面の表示順は別設定",
        )
        parser.add_setting(
            "--jpbooks-date-source",
            default="auto",
            choices=["auto", "bibliographic", "digital"],
            display_name="Publication date source",
            help="出版年月日の取得元：auto=デジタル資料のみ優先、bibliographic=書誌、digital=デジタル優先",
        )
        parser.add_setting(
            "--jpbooks-volume-output",
            default="issue",
            choices=["volume", "issue", "both"],
            display_name="Volume number output",
            help="巻番号の書き込み先：volume=Volume only、issue=Issue only（既定）、both=Volume and Issue",
        )
        parser.add_setting(
            "--jpbooks-subject-tags",
            default=False,
            action=argparse.BooleanOptionalAction,
            display_name="Copy subjects to Tags (max 10)",
            help="件名のみ最大 10 件。分類や NDC は変換しません",
        )

    @staticmethod
    def _validate_settings(settings: dict[str, Any]) -> None:
        if settings.get("jpbooks_key"):
            raise ValueError("API キーは使用しません。空欄にしてください。")
        if settings.get("jpbooks_url") not in (None, "", ENDPOINT):
            raise ValueError("NDL の公式 HTTPS SRU エンドポイントのみ対応します。")
        if settings.get("jpbooks_mediatype", "books") not in (
            "books",
            "booklet",
            "digital",
            "online",
            "electronic",
            "",
        ):
            raise ValueError("不正な mediatype です。")
        if settings.get("jpbooks_search_order", "oldest") not in ("oldest", "newest", "title"):
            raise ValueError("検索順は oldest・newest・title のいずれかにしてください。")
        if settings.get("jpbooks_volume_output", "issue") not in ("volume", "issue", "both"):
            raise ValueError("巻番号の書き込み先は volume・issue・both のいずれかにしてください。")
        if settings.get("jpbooks_date_source", "auto") not in ("auto", "bibliographic", "digital"):
            raise ValueError("日付の取得元は auto・bibliographic・digital のいずれかにしてください。")
        maximum = settings.get("jpbooks_maximum_records", 20)
        if not isinstance(maximum, int) or isinstance(maximum, bool) or not 1 <= maximum <= 100:
            raise ValueError("候補数は 1〜100 にしてください。")
        if not isinstance(settings.get("jpbooks_subject_tags", False), bool):
            raise ValueError("件名を Tags に出力する設定は boolean にしてください。")

    def parse_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        self._validate_settings(settings)
        self.mediatype = settings.get("jpbooks_mediatype", "books")
        self.creator = settings.get("jpbooks_creator", "")
        self.publisher = settings.get("jpbooks_publisher", "")
        self.maximum_records = settings.get("jpbooks_maximum_records", 20)
        self.search_order = settings.get("jpbooks_search_order", "oldest")
        self.volume_output = settings.get("jpbooks_volume_output", "issue")
        self.date_source = settings.get("jpbooks_date_source", "auto")
        self.subject_tags = settings.get("jpbooks_subject_tags", False)
        self._source = None
        return settings

    def check_status(self, settings: dict[str, Any]) -> tuple[str, bool]:
        try:
            self._validate_settings(settings)
            # A fresh connection, no cached response or mutation of live settings.
            source = NDLSource(self.cache_folder, maximum_records=1)
            try:
                source.check_status()
            finally:
                source.session.close()
                source.cache.close()
        except (ValueError, TalkerError) as exc:
            return report_error(exc, self.cache_folder, "check_status"), False
        return "NDL Search SRU に接続できました（API キー不要）。", True

    def _query(self, name: str, literal: bool = False) -> SearchQuery:
        text = name.strip()
        prefix = re.match(r"^ISBN(?:-1[03])?\s*:?\s*", text, re.IGNORECASE)
        isbn = isbn_from_gtin(text[prefix.end() :] if prefix else text)
        if isbn:
            # ISBN searches span media types and ignore stale author/publisher filters.
            return SearchQuery(isbn=isbn, mediatype="")
        compact = re.sub(r"[\s-]", "", text)
        if prefix or (len(compact) in (10, 13, 14) and re.fullmatch(r"[0-9Xx]+", compact)):
            raise TalkerDataError(self.name, 2, "ISBN の長さ・文字・チェック ディジットを確認してください。")
        if not text:
            raise TalkerDataError(self.name, 3, "ISBN またはタイトルを入力してください。")
        title, number = (text, None) if literal else infer_volume(text)
        return SearchQuery(
            title=title,
            issue=number or "",
            creator=(self.creator or "").strip(),
            publisher=(self.publisher or "").strip(),
            mediatype=self.mediatype,
            sort_order=self.search_order,
        )

    def _search(self, query: SearchQuery, refresh: bool, on_rate_limit: RLCallBack | None) -> SearchPage:
        if query.isbn or query.itemno:
            return self.source.search(query, refresh=refresh, on_rate_limit=on_rate_limit)
        # More specific searches first, relaxing issue/author only when there are no records.
        # Publisher/material restrictions are explicit user filters and never relaxed.
        attempts = [query]
        if query.issue:
            attempts.append(replace(query, creator=""))
        if query.creator:
            attempts.append(replace(query, issue=""))
        attempts.append(replace(query, issue="", creator=""))
        for attempt in dict.fromkeys(attempts):
            page = self.source.search(attempt, refresh=refresh, on_rate_limit=on_rate_limit)
            if page.records:
                return page
        return page

    @copyable_errors
    def search_for_series(
        self,
        series_name: str,
        callback: Callable[[int, int], None] | None = None,
        refresh_cache: bool = False,
        literal: bool = False,
        series_match_thresh: int = 90,
        *,
        on_rate_limit: RLCallBack | None = None,
    ) -> list[ComicSeries]:
        query = self._query(series_name, literal)
        page = (
            self.source.search(query, refresh=refresh_cache, on_rate_limit=on_rate_limit)
            if literal
            else self._search(query, refresh_cache, on_rate_limit)
        )
        warnings = list(page.warnings)
        if page.truncated:
            warnings.append(
                f"検索結果 {page.total} 件のうち最初の {self.maximum_records} 件です。検索を絞ってください。"
            )
        for message in warnings:
            logger.warning("%s", message)
        if callback:
            callback(len(page.records), page.total)
        return [
            to_series(record, "\n".join(warnings), date_source=self.date_source) for record in page.records
        ]

    @copyable_errors
    def search_metadata(
        self, metadata: GenericMetadata, *, on_rate_limit: RLCallBack | None = None
    ) -> SearchPage:
        """Programmatic helper, NOT a beta.9 host callback (the host never passes metadata)."""
        isbn = isbn_from_gtin(metadata.gtin) or normalize_isbn(metadata.identifier)
        title = (metadata.series or "").strip() or (metadata.title or "").strip()
        author = next((c.person for c in metadata.credits if c.role.casefold() == "writer"), "").strip()
        number = str(metadata.volume) if metadata.volume is not None else metadata.issue or ""
        if not isbn and not title and not number.strip():
            raise TalkerDataError(self.name, 3, "ISBN またはタイトルを入力してください。")
        query = SearchQuery(
            isbn=isbn or "",
            title=title,
            issue=number.strip(),
            creator=author,
            publisher=(self.publisher or "").strip(),
            mediatype="" if isbn else self.mediatype,
            sort_order=self.search_order,
        )
        return self._search(query, False, on_rate_limit)

    @copyable_errors
    def fetch_series(self, series_id: str, *, on_rate_limit: RLCallBack | None = None) -> ComicSeries:
        return to_series(
            self.source.get(series_id, on_rate_limit=on_rate_limit), date_source=self.date_source
        )

    @copyable_errors
    def fetch_issues_in_series(
        self, series_id: str, *, on_rate_limit: RLCallBack | None = None
    ) -> list[GenericMetadata]:
        return [
            to_metadata(
                self.source.get(series_id, on_rate_limit=on_rate_limit),
                subject_tags=self.subject_tags,
                volume_output=self.volume_output,
                date_source=self.date_source,
            )
        ]

    @copyable_errors
    def fetch_comic_data(
        self,
        issue_id: str | None = None,
        series_id: str | None = None,
        issue_number: str = "",
        *,
        on_rate_limit: RLCallBack | None = None,
    ) -> GenericMetadata:
        selected = issue_id or series_id
        if not selected:
            raise TalkerDataError(self.name, 3, "標準候補選択で NDL 書誌を選んでください。")
        record = self.source.get(selected, on_rate_limit=on_rate_limit)
        resolved = resolve_record_number(record)
        if issue_number:
            if resolved.conflict:
                raise TalkerDataError(
                    self.name, 3, "書誌の巻番号に不一致があります。NDL 原データとタイトルを確認してください。"
                )
            if resolved.value and normalize_issue(resolved.value) != normalize_issue(issue_number):
                raise TalkerDataError(self.name, 3, "選択した書誌の巻番号が要求と一致しません。")
        return to_metadata(
            record,
            existing_issue=issue_number,
            subject_tags=self.subject_tags,
            volume_output=self.volume_output,
            date_source=self.date_source,
        )

    @copyable_errors
    def fetch_issues_by_series_issue_num_and_year(
        self,
        series_id_list: list[str],
        issue_number: str,
        year: int | None,
        *,
        on_rate_limit: RLCallBack | None = None,
    ) -> list[GenericMetadata]:
        result = []
        for series_id in dict.fromkeys(series_id_list):
            record = self.source.get(series_id, on_rate_limit=on_rate_limit)
            resolved = resolve_record_number(record)
            if resolved.conflict:
                continue
            if issue_number and normalize_issue(resolved.value or "") != normalize_issue(issue_number):
                continue
            md = to_metadata(
                record,
                subject_tags=self.subject_tags,
                volume_output=self.volume_output,
                date_source=self.date_source,
            )
            if year is None or md.year is None or md.year == year:
                result.append(md)
        return result
