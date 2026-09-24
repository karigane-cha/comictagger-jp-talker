"""Live MADB checks: opt in explicitly, production limiter remains enabled."""

import os

import pytest

from comictagger_jp_talker.sources.madb import MADBSource
from comictagger_jp_talker.sources.madb_queries import CLASS_NS, ID_NS, isbn_candidates

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(os.getenv("JPBOOKS_RUN_NETWORK_TESTS") != "1", reason="opt-in MADB network tests"),
]


def test_live_isbn_and_book_series(tmp_path):
    with MADBSource(tmp_path) as source:
        page = source.search_by_isbn("9784832241190", refresh=True)
        # Phase 2A observed 2026-09-24: intentional ID baseline, not a timeless identity guarantee.
        candidate = next(r for r in page.records if r.id == "M381096")
        assert candidate.isbns
        bundle = source.get(candidate.uri, refresh=True)
        book = bundle.book
        assert book.id == "M381096" and CLASS_NS + "MangaBook" in book.types
        assert book.titles and book.volumes and book.isbns
        assert any(s.uri == ID_NS + "C334830" and s.titles for s in bundle.series)
        assert bundle.completeness == "complete", bundle.warnings


def test_live_isbn13_finds_isbn10_only_book(tmp_path):
    assert isbn_candidates("9784592880714") == ("4592880714", "9784592880714")
    with MADBSource(tmp_path) as source:
        page = source.search_by_isbn("9784592880714", refresh=True)
        # Phase 2A baseline M299519 had only ISBN-10; query the user's equivalent ISBN-13.
        candidate = next(r for r in page.records if r.id == "M299519")
        assert any(term.value == "4592880714" for term in candidate.isbns)
