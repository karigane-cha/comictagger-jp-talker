"""Synthetic MADB evidence; no fixture is downloaded or used as host metadata."""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from urllib3.exceptions import ReadTimeoutError

from comictagger_jp_talker.sources import madb
from comictagger_jp_talker.sources.madb_models import MADBError, RDFTerm
from comictagger_jp_talker.sources.madb_parser import parse_resource, parse_search, parse_term, select_rows
from comictagger_jp_talker.sources.madb_queries import (
    CLASS_NS,
    DCTERMS_NS,
    ENDPOINT,
    ID_NS,
    PROPERTY_NS,
    REF_NS,
    SCHEMA_NS,
    XSD_NS,
    isbn_candidates,
    isbn_query,
    resource_query,
    resource_uri,
    sparql_literal,
)

FIXTURES = Path(__file__).parent / "fixtures" / "madb"


def fixture(name):
    return (FIXTURES / f"{name}.json").read_bytes()


def altered(name, change):
    data = json.loads(fixture(name))
    change(data["results"]["bindings"])
    return json.dumps(data).encode()


def response(content, *, status=200, content_type="application/sparql-results+json; charset=UTF-8"):
    result = requests.Response()
    result.status_code = status
    result.headers["Content-Type"] = content_type
    result.raw = io.BytesIO(content)
    return result


@pytest.fixture
def source(tmp_path, monkeypatch):
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())
    with madb.MADBSource(tmp_path) as source:
        source.session.post = Mock()
        yield source


def serve_bundle(source, *, book="book"):
    content = {
        ID_NS + "M1": fixture(book),
        ID_NS + "C1": fixture("series"),
        ID_NS + "C2": fixture("agent"),
        ID_NS + "C3": fixture("agent_other"),
        REF_NS + "S1": fixture("holding"),
    }

    def post(url, **kwargs):
        query = kwargs["data"]["query"]
        uri = query.split("<", 1)[1].split(">", 1)[0]
        return response(content[uri])

    source.session.post.side_effect = post
    return content


@pytest.mark.parametrize("value", ["4592880714", "9784592880714", "4-592-88071-4"])
def test_equivalent_isbn_candidates(value):
    assert isbn_candidates(value) == ("4592880714", "9784592880714")
    query = isbn_query(value)
    assert '"4592880714"' in query and '"9784592880714"' in query
    assert "MangaWork" not in query and "REGEX" not in query and "CONTAINS" not in query
    assert "schema:name" not in query and "schema:brand" not in query


def test_979_has_no_isbn10():
    assert isbn_candidates("9791090636071") == ("9791090636071",)


@pytest.mark.parametrize(
    "value",
    [
        "(set)",
        "9.78402e+12",
        "4088466361",
        "9784592880714(set)",
        "9784592880715",
        '9784592880714" } SERVICE <https://evil.invalid> {',
        "",
        "9784592880714\x00",
        "459288\x0b0714",
    ],
)
def test_invalid_isbn_never_requests(source, value):
    with pytest.raises(ValueError):
        source.search_by_isbn(value)
    source.session.post.assert_not_called()


def test_literal_escaping():
    raw = 'quote" slash\\\n\r\t日本語'
    assert sparql_literal(raw) == '"quote\\" slash\\\\\\n\\r\\t日本語"'


@pytest.mark.parametrize("value", ["\x00", "\x01", "\x0b", "\x1f", "\x7f", "\x85", "\ud800"])
def test_invalid_literal_controls(value):
    with pytest.raises(ValueError):
        sparql_literal(value)


@pytest.mark.parametrize(
    "kind,identifier,namespace",
    [
        ("book", "M123", ID_NS),
        ("series", "C1", ID_NS),
        ("agent", "C2", ID_NS),
        ("holding", "S3", REF_NS),
    ],
)
def test_resource_validation(kind, identifier, namespace):
    assert resource_uri(identifier, kind) == namespace + identifier
    assert resource_uri(namespace + identifier, kind) == namespace + identifier
    assert "MangaWork" not in resource_query(identifier, kind)


@pytest.mark.parametrize(
    "value,kind",
    [
        ("C1", "book"),
        ("M1", "series"),
        ("P1", "agent"),
        ("C1", "holding"),
        (ID_NS + "S1", "holding"),
        ("https://evil.invalid/id/M1", "book"),
        (ID_NS + "M1> } SERVICE <https://evil.invalid> {", "book"),
        (ID_NS + "M1?x=1", "book"),
        ("M1\n", "book"),
        ("M１", "book"),
        ("../M1", "book"),
    ],
)
def test_arbitrary_uri_rejected(value, kind):
    with pytest.raises(ValueError):
        resource_query(value, kind)


@pytest.mark.parametrize("limit", [0, -1, 1001, True, "1", 1.5])
def test_bounded_limits(limit):
    with pytest.raises(ValueError):
        resource_query("M1", "book", limit)
    with pytest.raises(ValueError):
        isbn_query("4592880714", limit)


def test_measured_namespaces():
    assert ENDPOINT == "https://mediaarts-db.artmuseums.go.jp/sparql"
    assert CLASS_NS == "https://mediaarts-db.artmuseums.go.jp/data/class#"
    assert PROPERTY_NS == "https://mediaarts-db.artmuseums.go.jp/data/property#"
    assert SCHEMA_NS == "https://schema.org/"
    assert DCTERMS_NS == "http://purl.org/dc/terms/"
    assert "PREFIX class: <https://mediaarts-db.artmuseums.go.jp/data/class#>" in isbn_query("4592880714")


@pytest.mark.parametrize(
    "binding,expected",
    [
        ({"type": "uri", "value": ID_NS + "C1"}, RDFTerm("uri", ID_NS + "C1")),
        ({"type": "bnode", "value": "b1"}, RDFTerm("bnode", "b1")),
        ({"type": "literal", "value": ""}, RDFTerm("literal", "")),
        (
            {"type": "literal", "value": "1", "datatype": XSD_NS + "integer"},
            RDFTerm("literal", "1", XSD_NS + "integer"),
        ),
        (
            {"type": "literal", "value": "ヨミ", "xml:lang": "ja-hrkt"},
            RDFTerm("literal", "ヨミ", language="ja-hrkt"),
        ),
    ],
)
def test_rdf_terms(binding, expected):
    assert parse_term(binding) == expected


@pytest.mark.parametrize(
    "binding",
    [
        None,
        [],
        {},
        {"type": "new-kind", "value": "v"},
        {"type": "literal", "value": 1},
        {"type": "uri", "value": "x", "xml:lang": "ja"},
        {"type": "literal", "value": "x", "datatype": 3},
        {"type": "literal", "value": "x", "datatype": XSD_NS + "integer", "xml:lang": "ja"},
        {"type": "literal", "value": "\ud800"},
    ],
)
def test_invalid_terms(binding):
    with pytest.raises(MADBError):
        parse_term(binding)


@pytest.mark.parametrize(
    "name,count,isbns",
    [
        ("single", 1, {"9784592880714"}),
        ("isbn10_only", 1, {"4592880714"}),
        ("equivalent", 1, {"4592880714", "9784592880714"}),
        ("multiple_books", 2, {"4592880714"}),
        ("empty", 0, set()),
    ],
)
def test_discovery_preserves_distinct_books(source, name, count, isbns):
    source.session.post.return_value = response(fixture(name))
    page = source.search_by_isbn("9784592880714")
    assert len(page.records) == count and not page.truncated
    if count:
        assert {t.value for t in page.records[0].isbns} == isbns
        assert page.records[0].id == "M1"
    assert source.search_by_isbn("4592880714") == page  # Equivalent candidate-set cache key.
    assert source.session.post.call_count == 1
    call = source.session.post.call_args
    assert call.args == (ENDPOINT,)
    assert call.kwargs["timeout"] == (5, 30)
    assert call.kwargs["allow_redirects"] is False and call.kwargs["stream"] is True


def test_full_bundle_preserves_source_evidence(source):
    serve_bundle(source)
    bundle = source.get("M1")
    assert bundle.completeness == "complete" and not bundle.warnings
    book = bundle.book
    assert book.id == "M1" and book.types == (CLASS_NS + "MangaBook",)
    assert book.titles[1].language == "ja-hrkt"
    assert book.volumes == (RDFTerm("literal", "volume 1"),)
    assert book.positions[0].datatype == XSD_NS + "decimal"
    assert len(book.labels) == 3 and book.labels[2].value == "150"
    assert book.publisher_references == (RDFTerm("literal", "P123"),)
    assert book.publication_dates[0].value == "1968-1968-1968"
    assert len(book.isbns) == 7 and len(book.extent) == 2
    assert any(s.object.kind == "bnode" for s in book.statements)
    assert book.credits[0].role_raw == "原作" and book.credits[0].name_candidate == "Author"
    assert book.credits[2].role_raw == "未知"
    assert book.credits[3].name_candidate is None and book.credits[4].name_candidate is None
    assert all(c.association == "unresolved" and c.agent_uri is None for c in book.credits)
    assert len(bundle.agents) == 2  # Reversed names never zip with responsibility literals.
    assert bundle.agents[0].classifications[1].value == "団体"
    assert bundle.agents[0].external_identifiers[0].scheme == "ndl_authority_uri"
    assert book.series_uris == (ID_NS + "C1",)
    assert bundle.series[0].titles[0].value == "Series" and len(bundle.series[0].labels) == 2
    assert bundle.series[0].number_of_items[0].value == "7"
    holding = bundle.holdings[0]
    assert holding.book_uri == book.uri and holding.uri == REF_NS + "S1"
    assert holding.provider_names[0].value == "Synthetic Library"
    assert holding.notes[0].value == "20th printing"
    assert holding.external_identifiers[0].scheme == "holding_material_id"
    assert holding.external_identifiers[0].provider == "Synthetic Library"
    identifiers = book.external_identifiers
    assert {e.scheme for e in identifiers} == {"madb_uri", "madb_book_id", "isbn", "jpno", "ndl_search_url"}
    invalid = [e for e in identifiers if e.raw.value in ("4088466361", "(set)", "9.78402e+12")]
    assert len(invalid) == 3 and all(e.normalized is None for e in invalid)
    assert source.get(book.uri) == bundle and source.session.post.call_count == 5
    assert all("MangaWork" not in call.kwargs["data"]["query"] for call in source.session.post.call_args_list)


def test_missing_series_is_normal(source):
    serve_bundle(source, book="book_without_series")
    bundle = source.get("M1")
    assert bundle.series == () and bundle.completeness == "complete"
    assert source.session.post.call_count == 1


@pytest.mark.parametrize("target", ["C1", "C2", "S1"])
def test_relation_failure_returns_partial(source, target):
    content = serve_bundle(source)
    content[(REF_NS if target.startswith("S") else ID_NS) + target] = fixture("malformed")
    bundle = source.get("M1")
    assert bundle.book.completeness == "complete" and bundle.completeness == "partial"
    assert any("protocol" in w for w in bundle.warnings)


def test_wrong_series_type_does_not_become_series(source):
    content = serve_bundle(source)
    content[ID_NS + "C1"] = altered("series", lambda rows: rows[0]["o"].update(value=CLASS_NS + "Agent"))
    bundle = source.get("M1")
    assert bundle.series == () and bundle.completeness == "partial"
    assert any("schema" in w for w in bundle.warnings)


def test_relation_budget_and_refresh(source, monkeypatch):
    serve_bundle(source)
    monkeypatch.setattr(madb, "MAX_RELATIONS", 1)
    bundle = source.get("M1")
    assert source.session.post.call_count == 2 and bundle.completeness == "partial"
    assert "Related resource budget reached" in bundle.warnings
    source.get("M1", refresh=True)
    assert source.session.post.call_count == 4


def test_untrusted_and_blank_relations_are_not_queried(source):
    content = serve_bundle(source)
    content[ID_NS + "M1"] = altered(
        "book",
        lambda rows: rows.extend(
            [
                {
                    "p": {"type": "uri", "value": SCHEMA_NS + "provider"},
                    "o": {"type": "uri", "value": "https://evil.invalid/S2"},
                },
                {
                    "p": {"type": "uri", "value": DCTERMS_NS + "creator"},
                    "o": {"type": "bnode", "value": "b1"},
                },
            ]
        ),
    )
    bundle = source.get("M1")
    assert bundle.completeness == "partial" and source.session.post.call_count == 5
    assert len(bundle.warnings) == 2


@pytest.mark.parametrize(
    "data",
    [
        b"<html>error</html>",
        b"{",
        b"[]",
        b"{}",
        b'{"head":{},"results":{}}',
        b'{"head":{"vars":["p","o"]},"results":{}}',
        b'{"head":{"vars":["p","o"]},"results":{"bindings":[{}]}}',
        b'{"head":{"vars":["p","p"]},"results":{"bindings":[]}}',
    ],
)
def test_malformed_select(data):
    with pytest.raises(MADBError) as error:
        select_rows(data, {"p", "o"}, {"p", "o"}, 300)
    assert error.value.kind == "protocol"


@pytest.mark.parametrize(
    "status,kind",
    [(400, "query"), (403, "http"), (429, "rate_limited"), (500, "http"), (503, "http"), (302, "http")],
)
def test_http_errors_no_retry_or_cache(source, status, kind):
    result = response(b"sensitive arbitrary body", status=status)
    result.headers["Retry-After"] = "10"
    source.session.post.return_value = result
    source.cache.add_search_results = Mock()
    with pytest.raises(MADBError) as error:
        source.search_by_isbn("4592880714")
    assert error.value.kind == kind and error.value.status == status
    assert error.value.retry_after == "10"
    assert "sensitive" not in str(error.value)
    assert source.session.post.call_count == 1
    source.cache.add_search_results.assert_not_called()


@pytest.mark.parametrize(
    "exception,kind", [(requests.Timeout(), "timeout"), (requests.ConnectionError(), "network")]
)
def test_transport_failure_is_not_empty_search(source, exception, kind):
    source.session.post.side_effect = exception
    with pytest.raises(MADBError) as error:
        source.search_by_isbn("4592880714")
    assert error.value.kind == kind and source.session.post.call_count == 1


def test_html_200_and_stream_byte_cap(source, monkeypatch):
    source.session.post.return_value = response(b"<html/>", content_type="text/html")
    with pytest.raises(MADBError, match="Content-Type"):
        source.search_by_isbn("4592880714")
    monkeypatch.setattr(madb, "MAX_RESPONSE_BYTES", 10)
    result = response(b"x" * 11)
    source.session.post.return_value = result
    with pytest.raises(MADBError) as error:
        source.search_by_isbn("4592880714")
    assert error.value.kind == "truncated" and result.raw.closed


def test_streaming_read_timeout_is_classified_and_closed(source):
    result = response(b"")
    result.raw = Mock()
    result.raw.stream.side_effect = ReadTimeoutError(None, ENDPOINT, "synthetic timeout")
    source.session.post.return_value = result
    with pytest.raises(MADBError) as error:
        source.search_by_isbn("4592880714")
    assert error.value.kind == "timeout"
    result.raw.close.assert_called_once()


def test_row_caps_and_truncated_discovery(source):
    source.maximum_candidates = 1
    source.session.post.side_effect = lambda *a, **k: response(fixture("single"))
    assert source.search_by_isbn("4592880714").truncated
    assert source.search_by_isbn("4592880714").warnings
    assert source.session.post.call_count == 2  # Truncated data isn't a full cache hit.
    with pytest.raises(MADBError) as error:
        parse_search(fixture("equivalent"), "4592880714", 1)
    assert error.value.kind == "truncated"


def test_resource_limit_does_not_claim_complete(source):
    source.maximum_triples = 3
    serve_bundle(source, book="book_without_series")
    bundle = source.get("M1")
    assert bundle.book.completeness == bundle.completeness == "truncated" and bundle.warnings
    source.get("M1")
    assert source.session.post.call_count == 2


@pytest.mark.parametrize(
    "which,kind", [("empty", "not_found"), ("wrong_id", "schema"), ("wrong_type", "schema")]
)
def test_book_identity_errors(which, kind):
    content = fixture("book_without_series")
    if which == "empty":
        content = altered("book_without_series", lambda rows: rows.clear())
    elif which == "wrong_id":
        content = altered("book_without_series", lambda rows: rows[1]["o"].update(value="M2"))
    else:
        content = altered("book_without_series", lambda rows: rows[0]["o"].update(value=CLASS_NS + "Agent"))
    with pytest.raises(MADBError) as error:
        parse_resource(content, ID_NS + "M1", "book", 300)
    assert error.value.kind == kind


@pytest.mark.parametrize(
    "corruption",
    [
        b"not-json",
        fixture("malformed"),
        altered("book_without_series", lambda rows: rows[1]["o"].update(value="M2")),
    ],
)
def test_corrupt_resource_cache_refresh(source, caplog, corruption):
    serve_bundle(source, book="book_without_series")
    original = source.cache.add_search_results
    writes = Mock(wraps=original)
    source.cache.add_search_results = writes
    source.get("M1")
    namespace, key, entries, _ = writes.call_args.args
    original(namespace, key, [type(entries[0])(key, corruption)], True)
    assert source.get("M1").book.id == "M1"
    assert source.session.post.call_count == 2 and "Invalid cached MADB" in caplog.text
    source.get("M1")
    assert source.session.post.call_count == 2 and writes.call_count == 2


def test_corrupt_query_and_relation_cache_refresh(source, caplog):
    source.session.post.return_value = response(fixture("single"))
    original = source.cache.add_search_results
    writes = Mock(wraps=original)
    source.cache.add_search_results = writes
    source.search_by_isbn("4592880714")
    namespace, key, entries, _ = writes.call_args.args
    original(namespace, key, [type(entries[0])(key, b"{}")], True)
    source.session.post.return_value = response(fixture("single"))
    source.search_by_isbn("4592880714")
    serve_bundle(source)
    source.get("M1")  # Search identity cache cannot satisfy resource fetch.
    assert source.session.post.call_count == 7
    namespace, key, entries, _ = writes.call_args.args  # Holding relation is last.
    assert namespace == madb.RELATION_CACHE
    original(namespace, key, [type(entries[0])(key, b"{}")], True)
    source.get("M1")
    assert source.session.post.call_count == 8
    assert caplog.text.count("Invalid cached MADB") == 2
    assert {call.args[0] for call in writes.call_args_list} == {
        madb.QUERY_CACHE,
        madb.RESOURCE_CACHE,
        madb.RELATION_CACHE,
    }


def test_lifecycle_and_independent_limiter(source):
    from comictagger_jp_talker.sources import ndl

    assert madb._LIMITER is not ndl._LIMITER and madb._LOCK is not ndl._LOCK
    assert source.cache_folder.name == "jpbooks-madb-v1"
    source.session.close = Mock()
    source.cache.close = Mock()
    source.close()
    source.close()
    source.session.close.assert_called_once()
    source.cache.close.assert_called_once()
    with pytest.raises(RuntimeError, match="closed"):
        source.search_by_isbn("4592880714")
