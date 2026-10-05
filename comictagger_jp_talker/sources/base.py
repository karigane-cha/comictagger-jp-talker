from __future__ import annotations

from typing import Protocol

from comictalker.comictalker import RLCallBack

from comictagger_jp_talker.models import BookRecord, SearchPage, SearchQuery
from comictagger_jp_talker.sources.ndl_summary import SummaryMode


class BookSource(Protocol):
    def search(
        self, query: SearchQuery, *, refresh: bool = False, on_rate_limit: RLCallBack | None = None
    ) -> SearchPage: ...

    def get(
        self, record_id: str, *, summary_mode: SummaryMode = "fetch", on_rate_limit: RLCallBack | None = None
    ) -> BookRecord: ...
