"""Controlled Series integration with raw evidence and a strict NDL output boundary."""

import contextlib
import io
import json
from copy import deepcopy
from dataclasses import asdict, replace
from unittest.mock import Mock

import pytest
import requests
import settngs
from comicapi.genericmetadata import GenericMetadata
from comictaggerlib.ctsettings.plugin import register_talker_settings
from test_linkage import ISBN, OTHER_URL, URL, bundle, literal, record, resource_bytes

from comictagger_jp_talker import series_supplement
from comictagger_jp_talker.linkage import MatchConfidence, compare_candidates
from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import SearchPage
from comictagger_jp_talker.provenance import FieldComparisonState, compare_series
from comictagger_jp_talker.sources import madb
from comictagger_jp_talker.sources.madb_models import MADBError, RDFTerm
from comictagger_jp_talker.sources.madb_queries import ID_NS, RDF_NS, SCHEMA_NS, XSD_NS


@pytest.mark.parametrize("language", [None, "ja", "JA", "Ja"])
@pytest.mark.parametrize("display", ["作品名", "サクヒンメイ", "ASCII title", " 髙﨑𠮷は\u3099? "])
def test_display_language_policy_preserves_raw(language, display):
    term = RDFTerm("literal", display, language=language)
    b = bundle(names=(term, RDFTerm("literal", "ヨミ", language="JA-HrKt")))
    comparison = compare_series(record(title=display), b)
    classification = comparison.name_classifications[0]
    assert comparison.state == FieldComparisonState.BOTH_AGREE
    assert classification.effective_display_values == (display.strip(),)
    assert classification.display_names[0].raw_value == term
    assert classification.display_names[0].value == display
    assert classification.readings[0].raw_value.language == "JA-HrKt"
    assert not classification.other_names
    assert len(comparison.madb) == 2
    assert all(e.related_uri == ID_NS + "C1" and e.record_uri == ID_NS + "M1" for e in comparison.madb)
    assert all(e.predicate_or_path == SCHEMA_NS + "isPartOf / " + SCHEMA_NS + "name" for e in comparison.madb)


@pytest.mark.parametrize("language", ["ja-hrkt", "JA-HRKT", "Ja-Hrkt"])
def test_reading_only_is_no_display(language):
    comparison = compare_series(
        record(title=""), bundle(names=(RDFTerm("literal", "漢字", language=language),))
    )
    assert comparison.state == FieldComparisonState.NONE
    assert comparison.normalized_madb == ()
    assert len(comparison.name_classifications[0].readings) == 1


@pytest.mark.parametrize(
    "term",
    [
        RDFTerm("literal", "Title", language="en"),
        RDFTerm("literal", "作品名", language="ja-Jpan"),
        RDFTerm("literal", "ヨミ", language="ja-Latn"),
        RDFTerm("literal", "作品名", datatype=XSD_NS + "integer"),
    ],
)
@pytest.mark.parametrize("with_display", [False, True])
def test_unsupported_names_block_selection(term, with_display):
    names = (literal("作品名"), term) if with_display else (term,)
    comparison = compare_series(record(), bundle(names=names))
    assert comparison.state == FieldComparisonState.MULTIPLE
    assert comparison.name_classifications[0].other_names[0].raw_value == term


@pytest.mark.parametrize(
    "term",
    [
        RDFTerm("literal", "作品名", datatype=XSD_NS + "string"),
        RDFTerm("literal", "作品名", datatype=RDF_NS + "langString", language="ja"),
    ],
)
def test_supported_string_datatypes(term):
    assert compare_series(record(), bundle(names=(term,))).state == FieldComparisonState.BOTH_AGREE


def test_duplicate_raw_statements_survive_parser_and_effective_dedupe():
    b = bundle(names=("作品名", "作品名", " 作品名 "))
    comparison = compare_series(record(), b)
    assert comparison.state == FieldComparisonState.BOTH_AGREE
    assert len(b.series[0].titles) == len(comparison.madb) == 3
    assert comparison.normalized_madb == ("作品名",)


@pytest.mark.parametrize(
    "names,series_ids",
    [
        (("作品名", "別作品"), ("C1",)),
        (("作品名",), ("C1", "C2")),
    ],
)
def test_actual_ambiguity_never_collapses(names, series_ids):
    comparison = compare_series(record(), bundle(names=names, series_ids=series_ids))
    assert comparison.state == FieldComparisonState.MULTIPLE
    assert {c.series_uri for c in comparison.name_classifications} == {ID_NS + v for v in series_ids}


@pytest.mark.parametrize("enabled", [False, True])
def test_settings_roundtrip_and_command_line(talker, tmp_path, enabled):
    manager = settngs.Manager()
    register_talker_settings(manager, {talker.id: talker})
    definition = manager.definitions["Source jpbooks"].v["jpbooks_madb_series_supplement"]
    assert definition.default is False and definition.file
    assert definition.display_name == "Supplement missing Series from MADB (experimental)"
    option = "--jpbooks-madb-series-supplement" if enabled else "--no-jpbooks-madb-series-supplement"
    config = manager.parse_cmdline([option])
    path = tmp_path / "settings.json"
    assert manager.save_file(config, path)
    restored, success = manager.parse_file(path)
    value = restored.values["Source jpbooks"]["jpbooks_madb_series_supplement"]
    assert success and value is enabled
    assert (
        talker.parse_settings({"jpbooks_madb_series_supplement": value})["jpbooks_madb_series_supplement"]
        is enabled
    )
    assert talker.madb_series_supplement is enabled
    talker.parse_settings({})
    assert talker.madb_series_supplement is False
    path.write_text('{"Source jpbooks": {"jpbooks_subject_tags": false}}', encoding="utf-8")
    restored, success = manager.parse_file(path)
    assert success and restored.values["Source jpbooks"]["jpbooks_madb_series_supplement"] is False


@pytest.mark.parametrize("invalid", [None, "true", "false", 0, 1, [], {}])
def test_invalid_settings_rejected_before_mutation(talker, invalid):
    with pytest.raises(ValueError, match="boolean"):
        talker.parse_settings({"jpbooks_madb_series_supplement": invalid, "jpbooks_volume_output": "both"})
    assert talker.madb_series_supplement is False and talker.volume_output == "issue"


@pytest.mark.parametrize("enabled,title", [(False, ""), (False, "作品名 1"), (True, "作品名 1")])
def test_all_talker_paths_no_source_creation(talker, monkeypatch, enabled, title):
    ndl = replace(record(title=title), volumes=["1"])
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([ndl], 1)
    talker.source.get.return_value = ndl
    talker.madb_series_supplement = enabled
    forbidden = Mock(side_effect=AssertionError("No MADB source should be constructed"))
    monkeypatch.setattr(series_supplement, "MADBSource", forbidden)
    assert talker.search_for_series("ISBN: " + ISBN)
    assert talker.search_metadata(GenericMetadata(series="作品名"))
    assert talker.fetch_series(ndl.id)
    expected = to_metadata(ndl)
    assert talker.fetch_comic_data(issue_id=ndl.id) == expected
    assert talker.fetch_issues_in_series(ndl.id) == [expected]
    assert talker.fetch_issues_by_series_issue_num_and_year([ndl.id], "1", None) == [expected]
    forbidden.assert_not_called()


def test_opt_in_candidate_search_with_missing_series_is_ndl_only(talker, monkeypatch):
    talker.madb_series_supplement = True
    talker._source = Mock()
    talker.source.search.return_value = SearchPage([record(title="")], 1)
    talker.source.get.return_value = record(title="")
    forbidden = Mock(side_effect=AssertionError("Search must not construct MADBSource"))
    monkeypatch.setattr(series_supplement, "MADBSource", forbidden)
    assert talker.search_for_series(ISBN)
    assert talker.fetch_series("selected")
    forbidden.assert_not_called()


@pytest.mark.parametrize("direct", [False, True])
@pytest.mark.parametrize("title", ["", "  "])
def test_safe_supplement_only_series_and_notes_change(direct, title, record):
    ndl = replace(record, title=title, isbns=[ISBN], url=URL)
    b = bundle(
        urls=(URL,) if direct else (),
        names=(
            RDFTerm("literal", " 髙﨑𠮷は\u3099? ", language="ja"),
            RDFTerm("literal", "ヨミ", language="ja-hrkt"),
        ),
    )
    original_ndl, original_bundle = deepcopy(ndl), deepcopy(b)
    result = compare_candidates(ndl, [b])
    assert result.matches[0].confidence == (MatchConfidence.EXACT if direct else MatchConfidence.STRONG)
    metadata = to_metadata(ndl, subject_tags=True, volume_output="both")
    original_metadata = deepcopy(metadata)
    output = series_supplement.apply_series_supplement(metadata, result)
    assert output.series == " 髙﨑𠮷は\u3099? "
    assert "MADB Series（補完）:  髙﨑𠮷は\u3099? " in output.notes
    assert "MADB Book ID: M1" in output.notes and "MADB Series ID: C1" in output.notes
    assert f"MADB 照合: {result.matches[0].confidence.value}" in output.notes
    changed = {key for key, value in asdict(metadata).items() if asdict(output)[key] != value}
    assert changed == {"series", "notes"}
    assert metadata == original_metadata and ndl == original_ndl and b == original_bundle
    assert series_supplement.apply_series_supplement(output, result) is output
    # Even if Series is cleared externally, an identical audit block is not duplicated.
    repeated = series_supplement.apply_series_supplement(replace(output, series=""), result)
    assert repeated.notes == output.notes


@pytest.mark.parametrize(
    "scenario",
    [
        "ambiguous",
        "unsafe",
        "truncated_isbn",
        "truncated_exact",
        "unmatched",
        "reading_only",
        "multiple_display",
        "multiple_uri",
        "unsupported",
        "empty_display",
        "missing_series",
        "truncated_series",
        "truncated_book",
        "xml_control",
        "unavailable_relation",
    ],
)
def test_rejected_evidence_preserves_entire_output(scenario):
    ndl = record(title="")
    b = bundle(names=("作品名",))
    candidates = [b]
    truncated = False
    if scenario == "ambiguous":
        candidates.append(bundle("M2", names=("作品名",)))
    elif scenario == "unsafe":
        candidates = [bundle(urls=(OTHER_URL,), names=("作品名",))]
    elif scenario.startswith("truncated_") and scenario in ("truncated_isbn", "truncated_exact"):
        truncated = True
        candidates = [bundle(urls=(URL,) if scenario == "truncated_exact" else (), names=("作品名",))]
    elif scenario == "unmatched":
        candidates = []
    elif scenario == "reading_only":
        candidates = [bundle(names=(RDFTerm("literal", "ヨミ", language="ja-hrkt"),))]
    elif scenario == "multiple_display":
        candidates = [bundle(names=("作品名", "別作品"))]
    elif scenario == "multiple_uri":
        candidates = [bundle(names=("作品名",), series_ids=("C1", "C2"))]
    elif scenario == "unsupported":
        candidates = [bundle(names=("作品名", RDFTerm("literal", "Title", language="en")))]
    elif scenario == "empty_display":
        candidates = [bundle(names=("  ",))]
    elif scenario == "missing_series":
        candidates = [bundle()]
    elif scenario == "truncated_series":
        candidates = [replace(b, series=(replace(b.series[0], completeness="truncated"),))]
    elif scenario == "truncated_book":
        candidates = [replace(b, book=replace(b.book, completeness="truncated"))]
    elif scenario == "xml_control":
        candidates = [bundle(names=("作品\x00名",))]
    elif scenario == "unavailable_relation":
        candidates = [replace(b, series=(), completeness="partial", warnings=("Series failed",))]
    result = compare_candidates(ndl, candidates, truncated=truncated)
    metadata = to_metadata(ndl)
    assert series_supplement.apply_series_supplement(metadata, result) is metadata
    assert "MADB" not in metadata.notes


def response(content, status=200):
    value = requests.Response()
    value.status_code = status
    value.headers["Content-Type"] = "application/sparql-results+json"
    value.raw = io.BytesIO(content)
    return value


def mock_transport(monkeypatch, *, failure=None, stage="search", direct=True):
    monkeypatch.setattr(madb._LIMITER, "ratelimit", lambda *a, **kw: contextlib.nullcontext())
    search = json.dumps(
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
    fields = [(SCHEMA_NS + "isbn", literal(ISBN)), (SCHEMA_NS + "isPartOf", RDFTerm("uri", ID_NS + "C1"))]
    if direct:
        from comictagger_jp_talker.sources.madb_queries import PROPERTY_NS

        fields.append((PROPERTY_NS + "dataUrl", literal(URL)))
    book = resource_bytes("M1", "MangaBook", fields)
    series = resource_bytes(
        "C1",
        "MangaBookSeries",
        [
            (SCHEMA_NS + "name", RDFTerm("literal", "作品名", language="ja")),
            (SCHEMA_NS + "name", RDFTerm("literal", "ヨミ", language="ja-hrkt")),
        ],
    )
    payloads = {"search": search, "book": book, "series": series}

    def post(session, url, **kwargs):
        query = kwargs["data"]["query"]
        current = "search" if "SELECT DISTINCT" in query else "book" if "/M1>" in query else "series"
        if failure is not None and stage == current:
            if isinstance(failure, Exception):
                raise failure
            return failure
        return response(payloads[current])

    monkeypatch.setattr(requests.Session, "post", post)


@pytest.mark.parametrize("direct", [False, True])
def test_talker_real_transport_parser_linkage_and_cache(talker, monkeypatch, direct):
    ndl = replace(record(title=""), volumes=["1"])
    talker._source = Mock()
    talker.source.get.return_value = ndl
    talker.parse_settings({"jpbooks_madb_series_supplement": True})
    talker._source = Mock()
    talker.source.get.return_value = ndl
    mock_transport(monkeypatch, direct=direct)
    output = talker.fetch_comic_data(issue_id=ndl.id)
    assert output.series == "作品名" and "MADB Series（補完）" in output.notes
    forbidden = Mock(side_effect=AssertionError("Cached second fetch must not contact MADB"))
    monkeypatch.setattr(requests.Session, "post", forbidden)
    assert talker.fetch_comic_data(issue_id=ndl.id) == output
    forbidden.assert_not_called()


@pytest.mark.parametrize("stage", ["search", "book", "series"])
@pytest.mark.parametrize("kind", ["timeout", "network", "http", "rate_limit", "protocol", "schema"])
def test_fail_open_through_transport(talker, monkeypatch, caplog, stage, kind):
    ndl = record(title="")
    talker._source = Mock()
    talker.source.get.return_value = ndl
    talker.madb_series_supplement = True
    failures = {
        "timeout": requests.Timeout("timeout"),
        "network": requests.ConnectionError("network"),
        "http": response(b"failure", 503),
        "rate_limit": response(b"failure", 429),
        "protocol": response(b"{broken"),
        "schema": response(resource_bytes("M1", "Agent", [])),
    }
    mock_transport(monkeypatch, failure=failures[kind], stage=stage)
    assert talker.fetch_comic_data(issue_id=ndl.id) == to_metadata(ndl)
    assert "Optional MADB Series supplement" in caplog.text
    assert not (talker.cache_folder / "jpbooks/latest-error.txt").exists()


@pytest.mark.parametrize("failure", [MADBError("timeout", "failure"), OSError("cache failure")])
def test_source_constructor_fail_open(tmp_path, monkeypatch, caplog, failure):
    ndl = record(title="")
    metadata = to_metadata(ndl)
    monkeypatch.setattr(series_supplement, "MADBSource", Mock(side_effect=failure))
    assert series_supplement.supplement_series(metadata, ndl, tmp_path, enabled=True) is metadata
    assert "retaining NDL metadata" in caplog.text


def test_source_closed_on_success_and_failure(tmp_path, monkeypatch):
    mock_transport(monkeypatch)
    sources = []

    def factory(cache_folder):
        source = madb.MADBSource(cache_folder)
        sources.append(source)
        return source

    monkeypatch.setattr(series_supplement, "MADBSource", factory)
    ndl = record(title="")
    assert (
        series_supplement.supplement_series(to_metadata(ndl), ndl, tmp_path, enabled=True).series == "作品名"
    )
    assert all(source._closed for source in sources)
    mock_transport(monkeypatch, failure=requests.Timeout("failure"))
    ndl.isbns = ["9784832241190"]  # New query bypasses the previous successful cache.
    assert series_supplement.supplement_series(to_metadata(ndl), ndl, tmp_path, enabled=True) == to_metadata(
        ndl
    )
    assert len(sources) == 2 and all(source._closed for source in sources)


def test_no_isbn_never_discovers_by_title(tmp_path, monkeypatch):
    forbidden = Mock(side_effect=AssertionError("No title fallback"))
    monkeypatch.setattr(requests.Session, "post", forbidden)
    ndl = record(title="", isbns=())
    metadata = to_metadata(ndl)
    assert series_supplement.supplement_series(metadata, ndl, tmp_path, enabled=True) is metadata
    forbidden.assert_not_called()
