"""Synthetic identity, provenance, and observation tests; no metadata selection."""

import contextlib
import io
import json
from copy import deepcopy
from dataclasses import replace
from unittest.mock import Mock, call

import pytest
import requests

from comictagger_jp_talker.linkage import (
    LinkageStatus,
    MatchConfidence,
    MatchConflict,
    MatchReason,
    compare_candidates,
    link_ndl_record,
)
from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.provenance import EvidenceSource, FieldComparisonState
from comictagger_jp_talker.sources import madb
from comictagger_jp_talker.sources.madb_models import (
    MADBError,
    MADBRecordBundle,
    MADBSearchPage,
    MADBSearchResult,
    RDFTerm,
)
from comictagger_jp_talker.sources.madb_parser import parse_resource
from comictagger_jp_talker.sources.madb_queries import (
    CLASS_NS,
    ID_NS,
    PROPERTY_NS,
    RDF_NS,
    SCHEMA_NS,
)

URL = "https://ndlsearch.ndl.go.jp/books/R100000002-I025437130"
OTHER_URL = "https://ndlsearch.ndl.go.jp/books/R100000002-I029306375"
ISBN = "9784592880714"
OTHER_ISBN = "9784832241190"


def literal(value):
    return RDFTerm("literal", value)


def resource_bytes(identifier, kind, fields):
    properties = [
        (RDF_NS + "type", RDFTerm("uri", CLASS_NS + kind)),
        (SCHEMA_NS + "identifier", literal(identifier)),
        *fields,
    ]
    rows = []
    for predicate, term in properties:
        obj = {"type": term.kind, "value": term.value}
        if term.language:
            obj["xml:lang"] = term.language
        if term.datatype:
            obj["datatype"] = term.datatype
        rows.append({"p": {"type": "uri", "value": predicate}, "o": obj})
    return json.dumps({"head": {"vars": ["p", "o"]}, "results": {"bindings": rows}}).encode()


def bundle(identifier="M1", *, isbns=(ISBN,), urls=(), names=(), series_ids=("C1",), extra=()):
    fields = [(SCHEMA_NS + "isbn", literal(v)) for v in isbns]
    fields += [(PROPERTY_NS + "dataUrl", literal(v)) for v in urls]
    series = []
    if names:
        for series_id in series_ids:
            fields.append((SCHEMA_NS + "isPartOf", RDFTerm("uri", ID_NS + series_id)))
            content = resource_bytes(
                series_id,
                "MangaBookSeries",
                [(SCHEMA_NS + "name", v if isinstance(v, RDFTerm) else literal(v)) for v in names],
            )
            series.append(parse_resource(content, ID_NS + series_id, "series", 300))
    content = resource_bytes(identifier, "MangaBook", [*fields, *extra])
    return MADBRecordBundle(parse_resource(content, ID_NS + identifier, "book", 300), tuple(series))


def record(*, isbns=(ISBN,), title="作品名", url=URL):
    return BookRecord("R100000002-I025437130", title, url, isbns=list(isbns))


def source_for(*bundles, truncated=False):
    source = Mock(spec=madb.MADBSource)
    source.search_by_isbn.return_value = MADBSearchPage(
        tuple(MADBSearchResult(b.book.id, b.book.uri, (), b.book.isbns) for b in bundles), truncated
    )
    source.get.side_effect = lambda identifier, **kw: next(b for b in bundles if b.book.id == identifier)
    return source


def test_direct_url_and_isbn():
    result = link_ndl_record(record(), source_for(bundle(urls=(URL,))))
    assert result.status == LinkageStatus.MATCHED
    (match,) = result.matches
    assert match.confidence == MatchConfidence.EXACT
    assert set(match.reasons) == {
        MatchReason.DIRECT_NDL_URL,
        MatchReason.ISBN_NORMALIZED,
        MatchReason.ISBN_RAW,
    }
    assert match.conflicts == () and match.candidate_count == 1
    assert match.algorithm_version == "phase2b2-v1"
    assert match.series.state == FieldComparisonState.NDL_ONLY


def test_direct_without_isbn():
    result = compare_candidates(record(isbns=()), [bundle(isbns=(), urls=(URL,))])
    assert result.status == LinkageStatus.MATCHED
    assert result.matches[0].confidence == MatchConfidence.EXACT
    assert result.matches[0].reasons == (MatchReason.DIRECT_NDL_URL,)


@pytest.mark.parametrize(
    "ndl,madb_isbn,extra_reason",
    [
        (ISBN, ISBN, MatchReason.ISBN_RAW),
        ("4592880714", ISBN, MatchReason.ISBN_EQUIVALENT),
        (ISBN, "4-592-88071-4", MatchReason.ISBN_EQUIVALENT),
        ("978-4-592-88071-4", ISBN, None),
        ("4-592-88071-4", "4592880714", None),
    ],
)
def test_unique_isbn_equivalence(ndl, madb_isbn, extra_reason):
    source = source_for(bundle(isbns=(madb_isbn,)))
    result = link_ndl_record(record(isbns=(ndl,)), source)
    (match,) = result.matches
    assert result.status == LinkageStatus.MATCHED
    assert match.confidence == MatchConfidence.STRONG
    assert MatchReason.ISBN_NORMALIZED in match.reasons
    assert set(match.reasons) == {MatchReason.ISBN_NORMALIZED} | ({extra_reason} if extra_reason else set())
    source.search_by_isbn.assert_called_once_with(ISBN, refresh=False)
    assert any(e.raw_value == ndl and e.value == ISBN for e in match.evidence)


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_isbn_never_first(reverse):
    books = [bundle("M1"), bundle("M2")]
    result = link_ndl_record(record(), source_for(*(reversed(books) if reverse else books)))
    assert result.status == LinkageStatus.AMBIGUOUS
    assert len(result.matches) == len(result.candidates) == 2
    assert all(m.confidence == MatchConfidence.AMBIGUOUS and m.series is None for m in result.matches)


def test_direct_disambiguates_but_retains_other_candidate():
    result = link_ndl_record(record(), source_for(bundle(), bundle("M2", urls=(URL,))))
    assert result.status == LinkageStatus.MATCHED
    assert [(m.madb_id, m.confidence) for m in result.matches] == [
        ("M1", MatchConfidence.AMBIGUOUS),
        ("M2", MatchConfidence.EXACT),
    ]
    assert result.matches[0].series is None and result.matches[1].series is not None
    assert result.warnings and all(m.candidate_count == 2 for m in result.matches)


@pytest.mark.parametrize("urls", [(OTHER_URL,), (URL, OTHER_URL)])
def test_url_contradiction_is_unsafe(urls):
    result = compare_candidates(record(), [bundle(urls=urls)])
    assert result.status == LinkageStatus.UNSAFE
    assert result.matches[0].confidence == MatchConfidence.UNSAFE
    assert MatchConflict.NDL_URL in result.matches[0].conflicts
    assert result.matches[0].series is None


def test_two_direct_identities_are_ambiguous():
    result = compare_candidates(record(), [bundle(urls=(URL,)), bundle("M2", urls=(URL,))])
    assert result.status == LinkageStatus.AMBIGUOUS
    assert all(m.confidence == MatchConfidence.AMBIGUOUS and m.series is None for m in result.matches)


def test_direct_identity_retains_isbn_discrepancy():
    result = compare_candidates(record(), [bundle(urls=(URL,), isbns=(OTHER_ISBN,))])
    assert result.status == LinkageStatus.MATCHED
    assert result.matches[0].confidence == MatchConfidence.EXACT
    assert result.matches[0].conflicts == (MatchConflict.ISBN,)
    assert {e.value for e in result.matches[0].evidence if e.field == "isbn"} == {ISBN, OTHER_ISBN}


def test_isbn_intersection_is_not_discrepancy():
    result = compare_candidates(record(), [bundle(isbns=(ISBN, OTHER_ISBN))])
    assert result.status == LinkageStatus.MATCHED
    assert not result.matches[0].conflicts


@pytest.mark.parametrize("value", ["invalid", "4088466361", "9784592880714(set)", "9.78402e+12", ""])
def test_invalid_isbn_never_evidence(value):
    source = source_for(bundle(isbns=(value,)))
    result = link_ndl_record(record(isbns=(value,)), source)
    assert result.status == LinkageStatus.UNMATCHED
    source.search_by_isbn.assert_not_called()
    assert compare_candidates(record(isbns=(value,)), [bundle(isbns=(value,))]).matches == ()
    direct = compare_candidates(record(isbns=(value,)), [bundle(urls=(URL,), isbns=(value,))])
    assert direct.matches[0].reasons == (MatchReason.DIRECT_NDL_URL,)
    assert all(e.value is None for e in direct.matches[0].evidence if e.field == "isbn")


@pytest.mark.parametrize(
    "field,predicate",
    [
        ("title", SCHEMA_NS + "name"),
        ("creators", SCHEMA_NS + "creator"),
        ("publishers", SCHEMA_NS + "publisher"),
    ],
)
def test_no_descriptive_fallback(field, predicate):
    ndl = record(isbns=())
    setattr(ndl, field, "作品名" if field == "title" else ["作品名"])
    result = compare_candidates(ndl, [bundle(isbns=(), extra=((predicate, literal("作品名")),))])
    assert result.status == LinkageStatus.UNMATCHED and not result.matches


def test_zero_candidates_and_no_isbn():
    source = source_for()
    assert link_ndl_record(record(), source).status == LinkageStatus.UNMATCHED
    source.get.assert_not_called()
    source.reset_mock()
    assert link_ndl_record(record(isbns=()), source).status == LinkageStatus.UNMATCHED
    source.search_by_isbn.assert_not_called()


@pytest.mark.parametrize("kind", ["timeout", "network", "http", "rate_limited", "protocol", "schema"])
@pytest.mark.parametrize("stage", ["search_by_isbn", "get"])
def test_acquisition_failures_are_unavailable(kind, stage):
    source = source_for(bundle())
    getattr(source, stage).side_effect = MADBError(kind, "failure", status=429, retry_after="10")
    result = link_ndl_record(record(), source)
    assert result.status == LinkageStatus.UNAVAILABLE
    assert (result.error.kind, result.error.status, result.error.retry_after) == (kind, 429, "10")
    assert all(m.series is None for m in result.matches)


def test_second_get_failure_keeps_evidence_without_false_unique():
    source = source_for(bundle(), bundle("M2"))
    source.get.side_effect = [bundle(), MADBError("not_found", "resource disappeared")]
    result = link_ndl_record(record(), source)
    assert result.status == LinkageStatus.UNAVAILABLE
    assert len(result.candidates) == 2 and result.candidates[1].completeness is None
    assert result.matches[0].confidence == MatchConfidence.AMBIGUOUS
    assert result.matches[0].candidate_count == 2 and result.matches[0].series is None


def test_failure_after_direct_match_never_compares_series(monkeypatch):
    from comictagger_jp_talker import linkage

    forbidden = Mock(side_effect=AssertionError("Unavailable run must not compare Series"))
    monkeypatch.setattr(linkage, "compare_series", forbidden)
    b = bundle(urls=(URL,))
    source = source_for(b, bundle("M2"))
    source.get.side_effect = [b, MADBError("timeout", "second Book failed")]
    result = link_ndl_record(record(), source)
    assert result.status == LinkageStatus.UNAVAILABLE
    assert result.matches[0].confidence == MatchConfidence.EXACT
    assert result.matches[0].series is None
    forbidden.assert_not_called()


def test_second_isbn_discovery_failure_retains_discovered_ids():
    source = source_for(bundle())
    page = source.search_by_isbn.return_value
    source.search_by_isbn.side_effect = [page, MADBError("timeout", "second search failed")]
    result = link_ndl_record(record(isbns=(ISBN, OTHER_ISBN)), source)
    assert result.status == LinkageStatus.UNAVAILABLE
    assert result.candidates[0].id == "M1" and result.candidates[0].completeness is None
    source.get.assert_not_called()


def test_get_identity_must_match_discovery():
    source = source_for(bundle())
    source.get.side_effect = None
    source.get.return_value = bundle("M2")
    result = link_ndl_record(record(), source)
    assert result.status == LinkageStatus.UNAVAILABLE and result.error.kind == "schema"


@pytest.mark.parametrize("direct", [False, True])
def test_truncated_search(direct):
    source = source_for(bundle(urls=(URL,) if direct else ()), truncated=True)
    result = link_ndl_record(record(), source)
    assert result.status == (LinkageStatus.MATCHED if direct else LinkageStatus.AMBIGUOUS)
    assert result.matches[0].confidence == (MatchConfidence.EXACT if direct else MatchConfidence.AMBIGUOUS)
    assert result.truncated and any("truncated" in w for w in result.warnings)


def test_truncated_empty_page_does_not_prove_absence():
    assert link_ndl_record(record(), source_for(truncated=True)).status == LinkageStatus.AMBIGUOUS


@pytest.mark.parametrize("direct", [False, True])
def test_truncated_book_never_strong_or_exact(direct):
    b = bundle(urls=(URL,) if direct else ())
    b = replace(b, book=replace(b.book, completeness="truncated"), completeness="truncated")
    result = compare_candidates(record(), [b])
    assert result.status == LinkageStatus.AMBIGUOUS
    assert result.matches[0].confidence == MatchConfidence.AMBIGUOUS
    assert result.matches[0].series is None


@pytest.mark.parametrize(
    "url,matched",
    [
        (URL, True),
        (URL + "#material", True),
        (URL.replace("https:", "http:"), False),
        (URL.replace("ndlsearch.ndl.go.jp", "example.com"), False),
        (URL + "?foo=bar", False),
        ("https://ndlsearch.ndl.go.jp/books/X?foo=bar", False),
        (URL + "/", False),
        ("https://[broken", False),
    ],
)
def test_direct_url_normalization(url, matched):
    result = compare_candidates(record(isbns=(), url=URL + "#material"), [bundle(isbns=(), urls=(url,))])
    assert result.status == (LinkageStatus.MATCHED if matched else LinkageStatus.UNMATCHED)


def test_deduplicate_queries_and_candidates():
    b = bundle(isbns=(ISBN, OTHER_ISBN))
    source = source_for(b, b)
    result = link_ndl_record(record(isbns=(ISBN, "4592880714", OTHER_ISBN)), source, refresh=True)
    assert source.search_by_isbn.call_args_list == [call(ISBN, refresh=True), call(OTHER_ISBN, refresh=True)]
    source.get.assert_called_once_with("M1", refresh=True)
    assert result.matches[0].candidate_count == 1
    assert len(compare_candidates(record(), [b, b]).matches) == 1
    with pytest.raises(ValueError, match="Conflicting snapshots"):
        compare_candidates(record(), [b, bundle()])


@pytest.mark.parametrize(
    "title,names,state",
    [
        ("ご注文はうさぎですか?", ("ご注文はうさぎですか?",), FieldComparisonState.BOTH_AGREE),
        ("作品名", ("作品名 完全版",), FieldComparisonState.BOTH_CONFLICT),
        ("作品名", (), FieldComparisonState.NDL_ONLY),
        ("", ("作品名",), FieldComparisonState.MADB_ONLY),
        ("", (), FieldComparisonState.NONE),
        ("作品名", ("作品名", "別作品"), FieldComparisonState.MULTIPLE),
        (
            "作品名",
            ("作品名", RDFTerm("literal", "サクヒンメイ", language="ja-hrkt")),
            FieldComparisonState.BOTH_AGREE,
        ),
        ("作品名", (" 作品名 ",), FieldComparisonState.BOTH_AGREE),
        ("作品名?", ("作品名",), FieldComparisonState.BOTH_CONFLICT),
        ("作品名!", ("作品名！",), FieldComparisonState.BOTH_CONFLICT),
        ("作品名 : 副題", ("作品名 副題",), FieldComparisonState.BOTH_CONFLICT),
        ("作品名", ("作品名 volume 1",), FieldComparisonState.BOTH_CONFLICT),
        ("作品名", ("作品名 = Title",), FieldComparisonState.BOTH_CONFLICT),
        ("ば", ("は\u3099",), FieldComparisonState.BOTH_CONFLICT),
    ],
)
def test_series_states(title, names, state):
    result = compare_candidates(record(title=title), [bundle(names=names)])
    comparison = result.matches[0].series
    assert comparison.state == state
    assert len(comparison.madb) == len(names)


def test_multiple_relations_even_same_names():
    result = compare_candidates(record(), [bundle(names=("作品名",), series_ids=("C1", "C2"))])
    comparison = result.matches[0].series
    assert comparison.state == FieldComparisonState.MULTIPLE
    assert len(comparison.madb) == len(comparison.relations) == 2


@pytest.mark.parametrize("missing", [True, False])
def test_incomplete_series_is_not_absence_or_agreement(missing):
    b = bundle(names=("作品名",))
    b = replace(b, series=() if missing else (replace(b.series[0], completeness="truncated"),))
    result = compare_candidates(record(), [b])
    assert result.status == LinkageStatus.MATCHED
    assert result.matches[0].series.state == FieldComparisonState.UNAVAILABLE


def test_unresolved_relation_and_unrelated_failure():
    unresolved = bundle(extra=((SCHEMA_NS + "isPartOf", RDFTerm("bnode", "unknown")),))
    assert (
        compare_candidates(record(), [unresolved]).matches[0].series.state == FieldComparisonState.UNAVAILABLE
    )
    unrelated = replace(bundle(), warnings=("Agent failed",), completeness="partial")
    comparison = compare_candidates(record(), [unrelated]).matches[0].series
    assert comparison.state == FieldComparisonState.NDL_ONLY and comparison.warnings == ("Agent failed",)


def test_nonliteral_name_preserves_term_and_reports_unavailable():
    term = RDFTerm("uri", "https://example.com/not-a-name")
    result = compare_candidates(record(), [bundle(names=(term,))])
    comparison = result.matches[0].series
    assert comparison.state == FieldComparisonState.UNAVAILABLE
    assert comparison.madb[0].raw_value == term and comparison.madb[0].value is None


@pytest.mark.parametrize(
    "title,volume,series,number",
    [
        ("My Girl. vol.31", "vol.31", "My Girl", "31"),
        (
            "ご注文はうさぎですか? : アンソロジーコミック. volume 1",
            "volume 1",
            "ご注文はうさぎですか? : アンソロジーコミック",
            "1",
        ),
        ("ご注文はうさぎですか? = Is the order a rabbit? 7", "7", "ご注文はうさぎですか?", "7"),
        ("ブルーロック = BLUELOCK. 1", "1", "ブルーロック", "1"),
    ],
)
def test_phase1_series_and_provenance(title, volume, series, number):
    ndl = replace(record(title=title), volumes=[volume])
    b = bundle(names=(" " + series + " ",))
    result = compare_candidates(ndl, [b])
    comparison = result.matches[0].series
    assert comparison.state == FieldComparisonState.BOTH_AGREE
    assert comparison.ndl.value == to_metadata(ndl).series == series
    assert comparison.ndl_number.value == to_metadata(ndl).issue == number
    assert comparison.ndl.source == EvidenceSource.NDL
    assert comparison.ndl.record_id == ndl.id and comparison.ndl.raw_value == title
    assert comparison.ndl.transform == "mapping.infer_volume"
    (evidence,) = comparison.madb
    assert evidence.source == EvidenceSource.MADB and evidence.record_id == "M1"
    assert evidence.record_uri == ID_NS + "M1" and evidence.related_uri == ID_NS + "C1"
    assert evidence.raw_value == literal(" " + series + " ")
    assert evidence.predicate_or_path == SCHEMA_NS + "isPartOf / " + SCHEMA_NS + "name"
    assert comparison.normalized_madb == (series,)


def test_linkage_does_not_mutate_phase1_metadata(record):
    before = deepcopy(record)
    metadata = to_metadata(record)
    b = bundle(urls=(record.url,), names=("different Series",))
    original_bundle = deepcopy(b)
    result = compare_candidates(record, [b])
    assert result.status == LinkageStatus.MATCHED
    assert record == before and b == original_bundle
    assert to_metadata(record) == metadata  # Includes credits, date, Notes, links, and all other fields.


def test_source_parser_linkage_integration(tmp_path, monkeypatch):
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())
    book_content = resource_bytes(
        "M1",
        "MangaBook",
        [
            (SCHEMA_NS + "isbn", literal(ISBN)),
            (PROPERTY_NS + "dataUrl", literal(URL)),
            (SCHEMA_NS + "isPartOf", RDFTerm("uri", ID_NS + "C1")),
        ],
    )
    series_content = resource_bytes("C1", "MangaBookSeries", [(SCHEMA_NS + "name", literal("作品名"))])
    search_content = json.dumps(
        {
            "head": {"vars": ["book", "identifier", "isbn"]},
            "results": {
                "bindings": [
                    {
                        "book": {"type": "uri", "value": ID_NS + "M1"},
                        "isbn": {"type": "literal", "value": ISBN},
                    }
                ]
            },
        }
    ).encode()

    def response(content):
        r = requests.Response()
        r.status_code = 200
        r.headers["Content-Type"] = "application/sparql-results+json"
        r.raw = io.BytesIO(content)
        return r

    with madb.MADBSource(tmp_path) as source:
        post = Mock(side_effect=[response(c) for c in (search_content, book_content, series_content)])
        monkeypatch.setattr(source.session, "post", post)
        result = link_ndl_record(record(), source)
        assert result.status == LinkageStatus.MATCHED
        assert result.matches[0].series.state == FieldComparisonState.BOTH_AGREE
        assert post.call_count == 3
        assert link_ndl_record(record(), source) == result  # Existing source cache, no linkage cache.
        assert post.call_count == 3
        post.side_effect = [response(b"{broken")]
        failure = link_ndl_record(record(), source, refresh=True)
        assert failure.status == LinkageStatus.UNAVAILABLE and failure.error.kind == "protocol"
