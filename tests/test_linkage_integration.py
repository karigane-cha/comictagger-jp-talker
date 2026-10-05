"""Opt-in checks using only Phase 2A/Phase 1 recorded live identities."""

import os

import pytest

from comictagger_jp_talker.linkage import (
    LinkageStatus,
    MatchConfidence,
    MatchReason,
    compare_candidates,
    link_ndl_record_for_series,
)
from comictagger_jp_talker.models import SearchQuery
from comictagger_jp_talker.provenance import FieldComparisonState
from comictagger_jp_talker.sources.madb import MADBSource
from comictagger_jp_talker.sources.ndl import NDLSource

pytestmark = [
    pytest.mark.network,
    pytest.mark.skipif(os.getenv("JPBOOKS_RUN_NETWORK_TESTS") != "1", reason="opt-in linkage network tests"),
]


@pytest.fixture
def ndl_source(tmp_path):
    source = NDLSource(tmp_path, maximum_records=5)
    yield source
    source.session.close()
    source.cache.close()


def fetch_ndl(source, identifier):
    page = source.search(SearchQuery(itemno=identifier, mediatype=""), refresh=True)
    return next(record for record in page.records if record.id == identifier)


def test_live_direct_ndl_identity(ndl_source, tmp_path):
    # Phase 2A examples.md example 14: this Book has a direct ma:dataUrl.
    record = fetch_ndl(ndl_source, "R100000002-I033625982")
    with MADBSource(tmp_path) as source:
        bundle = source.get("M1032568", refresh=True)
        result = compare_candidates(record, [bundle])
    assert result.status == LinkageStatus.MATCHED, result
    (match,) = result.matches
    assert match.confidence == MatchConfidence.EXACT
    assert MatchReason.DIRECT_NDL_URL in match.reasons
    assert MatchReason.ISBN_NORMALIZED in match.reasons
    assert match.series is not None
    print("direct observation:", match.madb_id, match.series.state.value, match.series.normalized_madb)


def test_live_isbn_discovery_and_series(ndl_source, tmp_path):
    # Phase 2A example 1 + Phase 1 verified NDL record. No invented URL reverse query.
    record = fetch_ndl(ndl_source, "R100000002-I023440575")
    with MADBSource(tmp_path) as source:
        result = link_ndl_record_for_series(record, source, refresh=True)
    assert result.status in (LinkageStatus.MATCHED, LinkageStatus.AMBIGUOUS), result
    match = next(m for m in result.matches if m.madb_id == "M381096")
    assert MatchReason.ISBN_NORMALIZED in match.reasons
    assert not match.conflicts
    if result.status == LinkageStatus.MATCHED and match.confidence in (
        MatchConfidence.EXACT,
        MatchConfidence.STRONG,
    ):
        comparison = match.series
        assert comparison is not None
        assert comparison.normalized_ndl == "ご注文はうさぎですか?"
        assert comparison.normalized_madb == ("ご注文はうさぎですか?",)
        # The Phase 2A reading remains raw evidence, separate from display candidates.
        assert comparison.state == FieldComparisonState.BOTH_AGREE
        (classification,) = comparison.name_classifications
        assert classification.effective_display_values == ("ご注文はうさぎですか?",)
        assert [(e.raw_value.value, e.raw_value.language) for e in classification.display_names] == [
            ("ご注文はうさぎですか?", None)
        ]
        assert [(e.raw_value.value, e.raw_value.language) for e in classification.readings] == [
            ("ゴチュウモン ワ ウサギ デスカ", "ja-hrkt")
        ]
        assert any(e.related_uri.endswith("/C334830") for e in comparison.madb)
        print("ISBN observation:", result.status.value, comparison.state.value, comparison.normalized_madb)
        print("raw Series names:", [(e.raw_value.value, e.raw_value.language) for e in comparison.madb])
    else:
        assert match.series is None  # Dataset growth may introduce additional ambiguous candidates.
        print("ISBN observation: ambiguous; retained", len(result.candidates), "candidates")
