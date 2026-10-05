"""MADB supplement uses complete identity snapshots without fetching related people/copies."""

import contextlib
import json
from dataclasses import replace
from unittest.mock import Mock

import pytest
from test_linkage import OTHER_URL, URL, bundle, record, source_for
from test_madb import fixture, response, serve_bundle

from comictagger_jp_talker.linkage import LinkageStatus, link_ndl_record, link_ndl_record_for_series
from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.series_supplement import apply_series_supplement, supplement_series
from comictagger_jp_talker.sources import madb
from comictagger_jp_talker.sources.madb_queries import DCTERMS_NS, ID_NS, PROPERTY_NS, REF_NS, SCHEMA_NS


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())
    with madb.MADBSource(tmp_path) as value:
        value.session.post = Mock()
        yield value


def serve(source):
    content = serve_bundle(source)
    old = source.session.post.side_effect

    def post(url, **kwargs):
        return (
            response(fixture("single"))
            if "SELECT DISTINCT" in kwargs["data"]["query"]
            else old(url, **kwargs)
        )

    source.session.post.side_effect = post
    return content


@pytest.mark.parametrize("direct", [False, True])
def test_lightweight_cold_cache_exactly_three_requests_and_cache_reuse(source, tmp_path, direct):
    content = serve(source)
    if not direct:
        book = json.loads(content[ID_NS + "M1"])
        book["results"]["bindings"] = [
            row for row in book["results"]["bindings"] if row["p"]["value"] != PROPERTY_NS + "dataUrl"
        ]
        content[ID_NS + "M1"] = json.dumps(book).encode()
    ndl = BookRecord(
        "R100000002-Itest", "", "https://ndlsearch.ndl.go.jp/books/R100000002-Itest", isbns=["9784592880714"]
    )
    result = link_ndl_record_for_series(ndl, source)
    assert result.status == LinkageStatus.MATCHED
    assert result.matches[0].confidence.value == ("exact" if direct else "strong")
    assert apply_series_supplement(to_metadata(ndl), result).series == "Series"
    assert source.session.post.call_count == 3
    queries = [call.kwargs["data"]["query"] for call in source.session.post.call_args_list]
    assert "SELECT DISTINCT" in queries[0] and "/M1>" in queries[1] and "/C1>" in queries[2]
    assert not any("/C2>" in q or "/C3>" in q or "/ref/" in q for q in queries)
    assert link_ndl_record_for_series(ndl, source) == result
    assert source.session.post.call_count == 3
    # A new source instance reuses the on-disk Book/Series caches too.
    with madb.MADBSource(tmp_path) as restarted:
        restarted.session.post = Mock(side_effect=AssertionError("Warm cache"))
        assert link_ndl_record_for_series(ndl, restarted) == result


def test_lightweight_scope_is_explicit_and_full_get_still_acquires_relations(source):
    serve_bundle(source)
    light = source.get_for_series_linkage("M1")
    assert source.session.post.call_count == 2
    assert light.retrieval_scope == "series_linkage" and light.completeness == "complete"
    assert not light.agents and not light.holdings
    # URI references remain in whole direct evidence; their detail is not requested.
    predicates = {statement.predicate for statement in light.book.statements}
    assert SCHEMA_NS + "provider" in predicates and DCTERMS_NS + "creator" in predicates
    full = source.get("M1")
    assert full.retrieval_scope == "full" and full.completeness == "complete"
    assert full.book == light.book and full.series == light.series
    assert len(full.agents) == 2 and len(full.holdings) == 1
    assert source.session.post.call_count == 5  # Book/Series reused; 3 detail requests added.


@pytest.mark.parametrize(
    "case",
    [
        "exact",
        "strong",
        "unsafe",
        "ambiguous",
        "truncated",
        "book_limit",
        "series_limit",
        "multiple_series",
        "reading",
        "unavailable",
    ],
)
def test_lightweight_reuses_full_linkage_identity_and_series_rules(case):
    candidate = bundle(
        names=("作品名",), urls=(URL,) if case == "exact" else (OTHER_URL,) if case == "unsafe" else ()
    )
    candidates = [candidate]
    if case == "ambiguous":
        candidates.append(bundle("M2", names=("作品名",)))
    elif case == "book_limit":
        candidates = [replace(candidate, book=replace(candidate.book, completeness="truncated"))]
    elif case == "series_limit":
        candidates = [replace(candidate, series=(replace(candidate.series[0], completeness="truncated"),))]
    elif case == "multiple_series":
        candidates = [bundle(names=("作品名",), series_ids=("C1", "C2"))]
    elif case == "reading":
        from comictagger_jp_talker.sources.madb_models import RDFTerm

        candidates = [bundle(names=(RDFTerm("literal", "ヨミ", language="ja-hrkt"),))]
    source = source_for(*candidates, truncated=case == "truncated")
    source.get_for_series_linkage = Mock(side_effect=source.get.side_effect)
    if case == "unavailable":
        from comictagger_jp_talker.sources.madb_models import MADBError

        source.get.side_effect = source.get_for_series_linkage.side_effect = MADBError("timeout", "failure")
    ndl = record(title="")
    full = link_ndl_record(ndl, source)
    light = link_ndl_record_for_series(ndl, source)
    assert light == full
    output = apply_series_supplement(to_metadata(ndl), light)
    assert bool(output.series) == (case in ("exact", "strong"))


def test_supplement_actual_source_has_no_agent_or_holding_requests(tmp_path, monkeypatch):
    sources = []
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())

    def factory(cache_folder):
        value = madb.MADBSource(cache_folder)
        value.session.post = Mock()
        serve(value)
        sources.append(value)
        return value

    monkeypatch.setattr("comictagger_jp_talker.series_supplement.MADBSource", factory)
    ndl = BookRecord(
        "R100000002-Itest", "", "https://ndlsearch.ndl.go.jp/books/R100000002-Itest", isbns=["9784592880714"]
    )
    assert supplement_series(to_metadata(ndl), ndl, tmp_path, enabled=True).series == "Series"
    assert sources[0]._closed
    queries = [call.kwargs["data"]["query"] for call in sources[0].session.post.call_args_list]
    assert len(queries) == 3
    assert all(REF_NS not in q and "/C2>" not in q and "/C3>" not in q for q in queries)
