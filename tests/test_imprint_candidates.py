"""Measured RDF regression and explicitly synthetic safety conditions.

Only the two saved discoveries are measured identity input. All authority
trust/applicability envelopes below are synthetic caller assertions, including
the one backed by the recorded publisher-anemone annotation.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
from itertools import permutations
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from comicapi.genericmetadata import GenericMetadata
from test_linkage import ISBN, OTHER_ISBN, OTHER_URL, URL, bundle, literal, record, resource_bytes

from comictagger_jp_talker.imprint_candidates import (
    AcquisitionContext,
    AuthoritySourceKind,
    AuthorityState,
    LabelAuthorityEvidence,
    LabelRelation,
    ResourceAcquisition,
    classify_imprint_terms,
    compare_imprint_candidates,
    evaluate_imprint_eligibility,
    extract_imprint_evidence,
)
from comictagger_jp_talker.imprint_candidates import (
    AcquisitionState as Acquisition,
)
from comictagger_jp_talker.imprint_candidates import (
    ImprintComparisonState as Comparison,
)
from comictagger_jp_talker.imprint_candidates import (
    ImprintEligibilityReason as Reason,
)
from comictagger_jp_talker.imprint_candidates import (
    ImprintEligibilityState as Decision,
)
from comictagger_jp_talker.imprint_candidates import (
    ImprintSemanticKind as Semantic,
)
from comictagger_jp_talker.imprint_candidates import (
    ImprintTermRole as Role,
)
from comictagger_jp_talker.linkage import (
    CandidateSummary,
    LinkageError,
    LinkageStatus,
    MatchConfidence,
    MatchConflict,
    compare_candidates,
)
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.series_supplement import apply_series_supplement
from comictagger_jp_talker.sources.madb_models import MADBRecordBundle, MADBStatement, RDFTerm
from comictagger_jp_talker.sources.madb_parser import parse_resource
from comictagger_jp_talker.sources.madb_queries import ID_NS, RDF_NS, SCHEMA_NS, XSD_NS

MEASURED = json.loads(
    (Path(__file__).parent / "fixtures/madb/imprint_measured.json").read_text(encoding="utf-8")
)


def acquired(b, **changes):
    """Synthetic attestation except where tests explicitly use saved discovery."""
    related = bool(b.book.series_uris)
    return replace(
        AcquisitionContext(
            discovery=Acquisition.COMPLETE,
            book=Acquisition.COMPLETE,
            series=Acquisition.COMPLETE if related else Acquisition.NOT_RELATED,
            relations=Acquisition.COMPLETE if related else Acquisition.NOT_RELATED,
        ),
        **changes,
    )


def synthetic(
    labels=("Label",), *, series_labels=None, identifier="M1", urls=(URL,), isbns=(ISBN,), extra=()
):
    fields = [(SCHEMA_NS + "brand", v if isinstance(v, RDFTerm) else literal(v)) for v in labels]
    fields += [
        (SCHEMA_NS + "publisher", literal("Publisher")),
        (SCHEMA_NS + "datePublished", literal("2024-09-06")),
        (SCHEMA_NS + "volumeNumber", literal("2")),
        *extra,
    ]
    b = bundle(
        identifier, isbns=isbns, urls=urls, names=("Work",) if series_labels is not None else (), extra=fields
    )
    if series_labels is not None:
        s = parse_resource(
            resource_bytes(
                "C1",
                "MangaBookSeries",
                [
                    (SCHEMA_NS + "name", literal("Work")),
                    (SCHEMA_NS + "publisher", literal("Publisher")),
                    *(
                        (SCHEMA_NS + "brand", v if isinstance(v, RDFTerm) else literal(v))
                        for v in series_labels
                    ),
                ],
            ),
            ID_NS + "C1",
            "series",
            300,
        )
        b = replace(b, series=(s,))
    return b


def ndl_synthetic():
    return replace(record(title=""), publishers=["Publisher"], issued=["2024-09-06"])


def measured_bundle(identifier):
    observations = {r["uri"]: r for r in MEASURED["resources"]}

    def resource(uri):
        o = observations[uri]
        content = json.dumps(
            {
                "head": {"vars": ["p", "o"]},
                "results": {
                    "bindings": [{"p": r["p"], "o": r["o"]} for r in o["raw_bindings"]],
                },
            }
        ).encode()
        assert o["state"] == "complete"
        return parse_resource(content, uri, o["kind"], 300)

    book = resource(ID_NS + identifier)
    return MADBRecordBundle(
        book, tuple(resource(uri) for uri in book.series_uris), retrieval_scope="series_linkage"
    )


def measured_ndl(identifier):
    return BookRecord(**MEASURED["ndl_records"][identifier])


def compare(b, ndl=None, context=None):
    ndl = ndl if ndl is not None else ndl_synthetic()
    extraction = extract_imprint_evidence(b, context if context is not None else acquired(b))
    return compare_imprint_candidates(classify_imprint_terms(extraction), ndl)


def authority(b=None, **changes):
    """Synthetic external verifier contract; URL alone provides no trust."""
    b = b if b is not None else synthetic()
    evidence = LabelAuthorityEvidence(
        label_name="Label",
        source="Synthetic publisher bibliography",
        locator="https://publisher.example/book/2",
        source_kind=AuthoritySourceKind.PUBLISHER_BIBLIOGRAPHY,
        book_id=b.book.id,
        book_uri=b.book.uri,
        isbn=b.book.isbns[0].value,
        publisher="Publisher",
        checked_at="2026-10-08T12:00:00+09:00",
        verification_state=AuthorityState.VERIFIED,
        trusted=True,
        independence_verified=True,
        origin_group="synthetic-publisher-primary",
        editions=(),
        medium="paper",
        publication_dates=("2024-09-06",),
        target_scope_verified=True,
        volume="2",
    )
    return replace(evidence, **changes)


def evaluate(b=None, *, ndl=None, context=None, linkage=None, evidence=(), existing=None):
    b = b if b is not None else synthetic()
    ndl = ndl if ndl is not None else ndl_synthetic()
    linkage = linkage if linkage is not None else compare_candidates(ndl, [b])
    return evaluate_imprint_eligibility(
        linkage, compare(b, ndl, context), authority_evidence=evidence, existing_imprint=existing
    )


@pytest.mark.parametrize("identifier", sorted(MEASURED["expected_states"]))
def test_all_39_measured_book_series_states(identifier):
    """RDF measured; completed acquisition context synthetic; no label inference."""
    b = measured_bundle(identifier)
    ndl = measured_ndl(identifier) if identifier in MEASURED["ndl_records"] else BookRecord("synthetic", "")
    c = compare(b, ndl)
    assert c.state.value == MEASURED["expected_states"][identifier]
    assert len(c.classification.extraction.candidates) > 0 or not b.book.labels
    assert all(t.semantic_kind != Semantic.VERIFIED_LABEL for t in c.classification.terms)


def test_measured_fixture_raw_source_and_occurrences_are_exact():
    root = Path(__file__).resolve().parents[1]
    source = root / MEASURED["source"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == MEASURED["source_sha256"]
    latest = {o["resource"]: o for o in json.loads(source.read_text(encoding="utf-8"))["observations"]}
    for reduced in MEASURED["resources"]:
        observed = latest[reduced["uri"]]
        assert reduced["at"] == observed["at"] and reduced["request_id"] == observed["request_id"]
        predicates = {r["p"]["value"] for r in reduced["raw_bindings"]}
        assert reduced["raw_bindings"] == [
            r for r in observed["raw_bindings"] if r["p"]["value"] in predicates
        ]


@pytest.mark.parametrize("identifier", ["M1032569", "M1032568"])
def test_measured_complete_discovery_exact_still_requires_authority(identifier):
    b, ndl = measured_bundle(identifier), measured_ndl(identifier)
    discovery = next(d for d in MEASURED["discoveries"] if d["book_id"] == identifier)
    assert discovery["state"] == "complete" and not discovery["page"]["truncated"]
    assert [r["id"] for r in discovery["page"]["records"]] == [b.book.id]
    linkage = compare_candidates(ndl, [b], truncated=discovery["page"]["truncated"])
    assert linkage.status == LinkageStatus.MATCHED
    assert linkage.matches[0].confidence == MatchConfidence.EXACT
    result = evaluate(b, ndl=ndl, linkage=linkage)
    assert result.state == Decision.HOLD and result.selected_candidate is None
    assert Reason.SEMANTIC_UNVERIFIED in result.reasons


def test_m1032569_publisher_annotation_with_explicit_synthetic_trust_contract_is_eligible():
    b, ndl = measured_bundle("M1032569"), measured_ndl("M1032569")
    annotation = next(s for s in MEASURED["official_sources"] if s["id"] == "publisher-anemone")
    evidence = authority(
        b,
        label_name="ジャンプコミックス",
        publisher="集英社",
        source="Phase 2C-2A publisher-anemone human annotation",
        locator=annotation["url"],
        origin_group="shueisha-primary-bibliography",
    )
    assert evidence.isbn == annotation["isbn"] == "9784088841748"
    result = evaluate(b, ndl=ndl, evidence=(evidence,))
    assert result.state == Decision.ELIGIBLE and not result.reasons
    assert result.selected_candidate.term.value == "ジャンプコミックス"
    assert result.authority[0].applicable
    assert result.comparison.ndl_overlap == ("ジャンプコミックス",)


@pytest.mark.parametrize(
    "identifier",
    [
        "M381096",
        "M852457",
        "M519976",
        "M190399",
        "M255146",
        "M299514",
        "M807088",
    ],
)
def test_measured_multiple_candidates_never_filtered_to_a_winner(identifier):
    b = measured_bundle(identifier)
    result = evaluate(b)
    assert result.comparison.state == Comparison.MULTIPLE
    assert len(result.comparison.book_values) > 1
    assert result.selected_candidate is None


def test_measured_edition_duplicate_and_publisher_equal_diagnostics():
    edition = evaluate(measured_bundle("M197767"))
    assert edition.state == Decision.REJECT and Reason.EDITION_EQUAL in edition.reasons
    b = measured_bundle("M197011")
    ndl = BookRecord("synthetic", "", publishers=["太平洋文庫"])
    result = evaluate(b, ndl=ndl)
    assert Reason.PUBLISHER_EQUAL in result.reasons
    assert result.state != Decision.ELIGIBLE
    assert all(t.semantic_kind == Semantic.UNVERIFIED for t in result.comparison.book_displays)


@pytest.mark.parametrize(
    "term,expected",
    [
        (RDFTerm("literal", "ひらがな"), Role.DISPLAY),
        (RDFTerm("literal", "ASCII Label", language="JA"), Role.DISPLAY),
        (RDFTerm("literal", "漢字 and English", language="Ja-HrKt"), Role.READING),
        (RDFTerm("literal", "A", language="en"), Role.OTHER_LANGUAGE),
        (RDFTerm("literal", "A", language="ja-Jpan"), Role.OTHER_LANGUAGE),
        (RDFTerm("literal", "A", language="ja-Latn"), Role.OTHER_LANGUAGE),
        (RDFTerm("literal", "A", datatype=XSD_NS + "string"), Role.DISPLAY),
        (RDFTerm("literal", "A", language="ja", datatype=RDF_NS + "langString"), Role.DISPLAY),
        (RDFTerm("literal", "A", datatype=XSD_NS + "integer"), Role.UNSUPPORTED),
        (RDFTerm("uri", "https://example.org/Label"), Role.UNSUPPORTED),
        (RDFTerm("bnode", "Label"), Role.UNSUPPORTED),
        (RDFTerm("literal", ""), Role.EMPTY),
        (RDFTerm("literal", " \t\n　"), Role.EMPTY),
    ],
)
def test_synthetic_language_datatype_roles_preserve_raw(term, expected):
    b = synthetic((term,))
    c = compare(b)
    (classified,) = c.classification.terms
    assert classified.role == expected
    assert classified.candidate.term == term
    assert classified.candidate.term.language == term.language


@pytest.mark.parametrize(
    "bad",
    [
        RDFTerm("literal", "Label", datatype=XSD_NS + "integer"),
        RDFTerm("literal", "Label", language="en"),
        RDFTerm("uri", "https://example.org/Label"),
        RDFTerm("bnode", "Label"),
        RDFTerm("literal", "", language="en"),
        RDFTerm("literal", "", datatype=XSD_NS + "boolean"),
    ],
)
@pytest.mark.parametrize("in_series", [False, True])
def test_unknown_term_beside_good_display_is_an_independent_blocker(bad, in_series):
    b = synthetic(
        ("Label",) if in_series else ("Label", bad), series_labels=("Label", bad) if in_series else None
    )
    result = evaluate(b, evidence=(authority(b),))
    assert result.comparison.state in (Comparison.BOOK_ONLY, Comparison.BOTH_AGREE)
    assert result.state == Decision.HOLD and Reason.UNSUPPORTED_TERM in result.reasons
    assert result.selected_candidate is None


@pytest.mark.parametrize(
    "term",
    [
        RDFTerm("literal", "Label", language="ja", datatype=XSD_NS + "string"),
        RDFTerm("literal", "Label", datatype=RDF_NS + "langString"),
        RDFTerm("literal", "Label", language=""),
        RDFTerm("uri", "Label", language="ja"),
        RDFTerm("literal", "\ud800"),
        RDFTerm("literal", 7),
        RDFTerm("unknown", "Label"),
    ],
)
def test_invalid_manually_constructed_terms_do_not_escape_parser_policy(term):
    b = synthetic()
    raw = MADBStatement(b.book.uri, SCHEMA_NS + "brand", term)
    statements = tuple(s for s in b.book.statements if s.predicate != SCHEMA_NS + "brand") + (raw,)
    b = replace(b, book=replace(b.book, labels=(term,), statements=statements))
    result = evaluate(b)
    assert result.state == Decision.REJECT and Reason.INVALID_TERM in result.reasons
    assert result.comparison.classification.terms[0].candidate.term == term


@pytest.mark.parametrize(
    "left,right",
    [
        ("ABC", " ABC "),
        ("が", "か\u3099"),
        ("ABC", "ＡＢＣ"),
        ("ABC", "abc"),
        ("Label・X", "LabelX"),
        ("Label X", "Label  X"),
        ("A/B", "A／B"),
        ("ß", "ss"),
    ],
)
def test_raw_display_variants_are_multiple_even_when_equality_keys_agree(left, right):
    b = synthetic((left, right))
    result = evaluate(b)
    assert result.comparison.state == Comparison.MULTIPLE
    assert result.comparison.book_values == tuple(sorted((left, right)))
    assert result.selected_candidate is None


@pytest.mark.parametrize(
    "left,right,expected",
    [
        ("ABC", " ABC ", Comparison.BOTH_AGREE),
        ("が", "か\u3099", Comparison.BOTH_AGREE),
        ("ABC", "ＡＢＣ", Comparison.BOTH_CONFLICT),
        ("ABC", "abc", Comparison.BOTH_CONFLICT),
        ("A・B", "AB", Comparison.BOTH_CONFLICT),
        ("A B", "A  B", Comparison.BOTH_CONFLICT),
        ("A/B", "A／B", Comparison.BOTH_CONFLICT),
        ("Label.X", "Label=X", Comparison.BOTH_CONFLICT),
    ],
)
def test_equality_is_nfc_and_outer_strip_only(left, right, expected):
    c = compare(synthetic((left,), series_labels=(right,)))
    assert c.state == expected
    assert c.book_values == (left,) and c.series_values == (right,)


def test_duplicate_statements_and_label_occurrences_remain_traceable_and_eligible():
    b = synthetic(series_labels=("Label", "Label"))
    statement = next(s for s in b.book.statements if s.predicate == SCHEMA_NS + "brand")
    b = replace(
        b, book=replace(b.book, labels=(literal("Label"),) * 2, statements=(*b.book.statements, statement))
    )
    extraction = extract_imprint_evidence(b, acquired(b))
    for candidate in extraction.candidates:
        assert (
            len(candidate.statements) == len(candidate.statement_indices) == len(candidate.label_indices) == 2
        )
        assert candidate.evidence.record_uri == candidate.statements[0].subject
    series = next(c for c in extraction.candidates if c.origin == "series")
    assert series.evidence.record_id == "C1" and series.evidence.record_uri == ID_NS + "C1"
    result = evaluate(b, evidence=(authority(b),))
    assert result.state == Decision.ELIGIBLE
    assert len(result.selected_candidate.statements) == 2
    assert result.comparison.book_candidate_count == result.comparison.series_candidate_count == 1
    assert result.comparison.book_occurrence_count == result.comparison.series_occurrence_count == 2


@pytest.mark.parametrize(
    "labels,series_labels,expected",
    [
        (("Label",), None, Comparison.BOOK_ONLY),
        (("Label",), (), Comparison.BOOK_ONLY),
        ((), ("Label",), Comparison.SERIES_ONLY),
        ((), (), Comparison.NONE),
        (("",), None, Comparison.NONE),
        (("Label",), ("Other",), Comparison.BOTH_CONFLICT),
        (("Label", "Other"), ("Label", "Other"), Comparison.MULTIPLE),
        (("Label", "Other"), ("Label",), Comparison.MULTIPLE),
    ],
)
def test_comparison_states_and_set_observation(labels, series_labels, expected):
    b = synthetic(labels, series_labels=series_labels)
    c = compare(b)
    assert c.state == expected
    assert c.normalized_set_equal == (set(c.book_keys) == set(c.series_keys))
    assert set(c.overlap) == set(c.book_keys) & set(c.series_keys)
    if expected in (Comparison.SERIES_ONLY, Comparison.NONE):
        assert evaluate(b).selected_candidate is None


def test_multiple_series_even_with_identical_labels_and_complete_data():
    b = synthetic(series_labels=("Label",))
    second = replace(
        b.series[0],
        id="C2",
        uri=ID_NS + "C2",
        statements=tuple(
            replace(s, subject=ID_NS + "C2", object=literal("C2"))
            if s.predicate == SCHEMA_NS + "identifier"
            else replace(s, subject=ID_NS + "C2")
            for s in b.series[0].statements
        ),
    )
    b = replace(
        b,
        book=replace(
            b.book,
            series_uris=(ID_NS + "C1", ID_NS + "C2"),
            statements=(
                *b.book.statements,
                MADBStatement(b.book.uri, SCHEMA_NS + "isPartOf", RDFTerm("uri", ID_NS + "C2")),
            ),
        ),
        series=(*b.series, second),
    )
    result = evaluate(b, evidence=(authority(b),))
    assert result.comparison.state == Comparison.MULTIPLE and Reason.MULTIPLE_RELATIONS in result.reasons
    assert result.selected_candidate is None


@pytest.mark.parametrize("field", ["discovery", "book", "series", "relations"])
@pytest.mark.parametrize(
    "state", [Acquisition.TRUNCATED, Acquisition.PARTIAL, Acquisition.UNAVAILABLE, Acquisition.NOT_REQUESTED]
)
def test_explicit_incomplete_acquisition_dominates_comparison(field, state):
    b = synthetic(series_labels=("Label", "Other"))
    c = compare(b, context=acquired(b, **{field: state}))
    assert c.state == Comparison.UNAVAILABLE
    assert (
        evaluate(b, context=acquired(b, **{field: state}), evidence=(authority(b),)).state
        != Decision.ELIGIBLE
    )


@pytest.mark.parametrize("part", ["book", "series", "bundle"])
@pytest.mark.parametrize("state", ["partial", "truncated"])
def test_complete_context_cannot_override_incomplete_snapshot(part, state):
    b = synthetic(series_labels=("Label",))
    if part == "book":
        b = replace(b, book=replace(b.book, completeness=state))
    elif part == "series":
        b = replace(b, series=(replace(b.series[0], completeness=state),))
    else:
        b = replace(b, completeness=state)
    assert compare(b).state == Comparison.UNAVAILABLE


def test_unfetched_series_never_becomes_brand_absence():
    b = replace(synthetic(series_labels=("Label",)), series=(), completeness="partial")
    c = compare(b)
    assert c.state == Comparison.UNAVAILABLE
    assert c.required_series_states[0].state == Acquisition.NOT_REQUESTED
    assert Reason.SERIES_INCOMPLETE in c.blockers


def test_not_requested_and_not_related_and_default_context_differ():
    b = synthetic()
    assert compare(b).state == Comparison.BOOK_ONLY
    assert compare(b, context=AcquisitionContext()).state == Comparison.UNAVAILABLE
    assert compare(b, context=acquired(b, series=Acquisition.NOT_REQUESTED)).state == Comparison.UNAVAILABLE


def test_unneeded_agent_holding_partial_requires_explicit_scope_attestation():
    b = replace(synthetic(), completeness="partial", retrieval_scope="full")
    assert compare(b).state == Comparison.UNAVAILABLE
    ctx = acquired(
        b,
        book_series_scope=Acquisition.COMPLETE,
        agents=Acquisition.UNAVAILABLE,
        holdings=Acquisition.NOT_REQUESTED,
    )
    result = compare_candidates(ndl_synthetic(), [b])
    assert result.candidates[0].completeness == "partial"
    assert evaluate(b, context=ctx, linkage=result, evidence=(authority(b),)).state == Decision.ELIGIBLE
    lightweight = replace(b, retrieval_scope="series_linkage")
    assert compare(lightweight, context=ctx).state == Comparison.UNAVAILABLE


@pytest.mark.parametrize("state", [Acquisition.PARTIAL, Acquisition.UNAVAILABLE, Acquisition.NOT_REQUESTED])
def test_per_resource_acquisition_blocks_complete_aggregate(state):
    b = synthetic(series_labels=("Label",))
    ctx = acquired(b, resources=(ResourceAcquisition(uri=ID_NS + "C1", state=state),))
    assert compare(b, context=ctx).state == Comparison.UNAVAILABLE


def test_raw_relation_projection_mismatch_and_unrelated_series_are_blocked():
    b = synthetic(series_labels=("Label",))
    for broken in (
        replace(b, book=replace(b.book, series_uris=())),
        replace(b, series=(replace(b.series[0], uri=ID_NS + "C99"),)),
        replace(b, series=(b.series[0], b.series[0])),
    ):
        result = evaluate(broken)
        assert result.state != Decision.ELIGIBLE
        assert Reason.RELATION_UNRESOLVED in result.reasons


@pytest.mark.parametrize("field", ["labels", "publishers", "editions", "isbns", "publication_dates"])
def test_projection_cannot_hide_or_invent_raw_evidence(field):
    b = synthetic()
    b = replace(b, book=replace(b.book, **{field: (literal("invented"),)}))
    result = evaluate(b)
    assert Reason.PROVENANCE_MISSING in result.reasons and result.state == Decision.REJECT
    if field == "labels":
        assert len(result.comparison.classification.extraction.candidates) == 2


def test_direct_exact_isbn_conflict_is_additionally_rejected():
    b = synthetic(isbns=(OTHER_ISBN,))
    linkage = compare_candidates(ndl_synthetic(), [b])
    assert linkage.status == LinkageStatus.MATCHED and linkage.matches[0].confidence == MatchConfidence.EXACT
    assert linkage.matches[0].conflicts == (MatchConflict.ISBN,)
    result = evaluate(b, linkage=linkage)
    assert result.state == Decision.REJECT and Reason.IDENTITY_CONFLICT in result.reasons
    unsafe = synthetic(urls=(OTHER_URL,))
    unsafe_linkage = compare_candidates(ndl_synthetic(), [unsafe])
    assert unsafe_linkage.status == LinkageStatus.UNSAFE
    assert MatchConflict.NDL_URL in unsafe_linkage.matches[0].conflicts
    rejected = evaluate(unsafe, linkage=unsafe_linkage)
    assert rejected.state == Decision.REJECT and Reason.IDENTITY_CONFLICT in rejected.reasons


def test_conflict_in_other_nonselected_complete_candidate_does_not_contaminate_winner():
    b = synthetic()
    other = synthetic(identifier="M2", urls=(OTHER_URL,), isbns=(OTHER_ISBN,))
    linkage = compare_candidates(ndl_synthetic(), [other, b])
    assert linkage.status == LinkageStatus.MATCHED and linkage.matches[1].conflicts
    result = evaluate(b, linkage=linkage, evidence=(authority(b),))
    assert result.state == Decision.ELIGIBLE


@pytest.mark.parametrize(
    "part", ["match_id", "match_ndl", "summary_uri", "summary_id", "book_uri", "raw_isbn"]
)
def test_linkage_and_supplied_snapshot_identity_mismatch_rejected(part):
    b = synthetic()
    linkage = compare_candidates(ndl_synthetic(), [b])
    if part in ("match_id", "match_ndl"):
        linkage = replace(
            linkage,
            matches=(
                replace(
                    linkage.matches[0],
                    **{
                        "madb_id" if part == "match_id" else "ndl_id": "different",
                    },
                ),
            ),
        )
    elif part.startswith("summary"):
        linkage = replace(
            linkage,
            candidates=(
                replace(
                    linkage.candidates[0],
                    **{
                        "uri" if part == "summary_uri" else "id": ID_NS + "M2"
                        if part == "summary_uri"
                        else "M2",
                    },
                ),
            ),
        )
    elif part == "book_uri":
        b = replace(b, book=replace(b.book, uri=ID_NS + "M2"))
    else:
        b = synthetic(isbns=(OTHER_ISBN,))
    evidence = authority() if part == "book_uri" else authority(b)
    result = evaluate(b, linkage=linkage, evidence=(evidence,))
    assert result.state == Decision.REJECT and Reason.SNAPSHOT_MISMATCH in result.reasons


def test_multiple_safe_matches_and_incomplete_candidate_set_never_establish_uniqueness():
    b = synthetic()
    linkage = compare_candidates(ndl_synthetic(), [b])
    second = replace(linkage.matches[0], madb_id="M2")
    multiple = replace(
        linkage,
        matches=(*linkage.matches, second),
        candidates=(
            *linkage.candidates,
            CandidateSummary("M2", ID_NS + "M2", "complete"),
        ),
    )
    assert evaluate(b, linkage=multiple).state == Decision.HOLD
    assert Reason.IDENTITY_AMBIGUOUS in evaluate(b, linkage=multiple).reasons
    for incomplete in (
        replace(linkage, truncated=True),
        replace(linkage, error=LinkageError("network", "synthetic")),
        replace(linkage, candidates=(*linkage.candidates, CandidateSummary("M2", ID_NS + "M2", None))),
    ):
        assert evaluate(b, linkage=incomplete, evidence=(authority(b),)).state != Decision.ELIGIBLE


@pytest.mark.parametrize(
    "status",
    [LinkageStatus.AMBIGUOUS, LinkageStatus.UNSAFE, LinkageStatus.UNMATCHED, LinkageStatus.UNAVAILABLE],
)
def test_status_gate_respected(status):
    b = synthetic()
    result = replace(compare_candidates(ndl_synthetic(), [b]), status=status)
    output = evaluate(b, linkage=result, evidence=(authority(b),))
    assert output.state == Decision.HOLD and Reason.NOT_MATCHED in output.reasons


@pytest.mark.parametrize("existing", ["Already", "   ", "\t\n", "　"])
def test_existing_imprint_protected_including_whitespace(existing):
    result = evaluate(existing=existing, evidence=(authority(),))
    assert result.state == Decision.SKIP and result.reasons == (Reason.EXISTING_IMPRINT,)
    assert result.selected_candidate is None
    assert len(result.authority) == 1


@pytest.mark.parametrize("existing", [None, ""])
def test_only_none_or_empty_is_unset(existing):
    result = evaluate(existing=existing, evidence=(authority(),))
    assert result.state == Decision.ELIGIBLE


@pytest.mark.parametrize("control", ["\x00", "\x01", "\x0b", "\ufffe", "\uffff"])
def test_invalid_xml_rejected_without_sanitizing(control):
    b = synthetic(("Label" + control,))
    result = evaluate(b, evidence=(authority(b, label_name="Label" + control),))
    assert result.state == Decision.REJECT and Reason.INVALID_XML in result.reasons
    assert result.comparison.book_values == ("Label" + control,)


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"trusted": False}, Reason.AUTHORITY_UNTRUSTED),
        ({"verification_state": AuthorityState.UNVERIFIED}, Reason.AUTHORITY_UNVERIFIED),
        ({"verification_state": AuthorityState.CONTRADICTED}, Reason.AUTHORITY_CONTRADICTED),
        ({"book_id": "M2", "book_uri": ID_NS + "M2"}, Reason.AUTHORITY_SCOPE_MISMATCH),
        ({"isbn": OTHER_ISBN}, Reason.AUTHORITY_SCOPE_MISMATCH),
        ({"volume": "1"}, Reason.AUTHORITY_SCOPE_MISMATCH),
        ({"publisher": "Other Publisher"}, Reason.CONTEXT_CONFLICT),
        ({"editions": ("New edition",)}, Reason.CONTEXT_CONFLICT),
        ({"publication_dates": ("2023-09-06",)}, Reason.CONTEXT_CONFLICT),
        ({"publication_dates": None}, Reason.CONTEXT_UNVERIFIED),
        ({"editions": None}, Reason.CONTEXT_UNVERIFIED),
        ({"medium": None}, Reason.CONTEXT_UNVERIFIED),
        ({"target_scope_verified": False}, Reason.CONTEXT_UNVERIFIED),
        ({"label_name": " Label "}, Reason.AUTHORITY_RAW_MISMATCH),
        ({"label_name": "Ｌａｂｅｌ"}, Reason.AUTHORITY_RAW_MISMATCH),
        ({"origin_group": None}, Reason.AUTHORITY_INDEPENDENCE_UNVERIFIED),
        ({"independence_verified": False}, Reason.AUTHORITY_INDEPENDENCE_UNVERIFIED),
        ({"source_kind": AuthoritySourceKind.NDL}, Reason.AUTHORITY_INDEPENDENCE_UNVERIFIED),
        ({"source_kind": AuthoritySourceKind.MADB}, Reason.AUTHORITY_INDEPENDENCE_UNVERIFIED),
        ({"unconfirmed": ("medium",)}, Reason.CONTEXT_UNVERIFIED),
    ],
)
def test_authority_trust_and_book_applicability_each_required(changes, reason):
    result = evaluate(evidence=(authority(**changes),))
    assert result.state != Decision.ELIGIBLE and reason in result.reasons
    assert result.selected_candidate is None and not result.authority[0].applicable


def test_medium_unknown_requires_exact_isbn_attestation_and_known_conflict_is_rejected():
    b = synthetic()
    assert evaluate(b, evidence=(authority(b),)).state == Decision.ELIGIBLE
    assert evaluate(b, evidence=(authority(b, target_scope_verified=False),)).state == Decision.HOLD
    result = evaluate(b, context=acquired(b, medium="digital"), evidence=(authority(b),))
    assert result.state == Decision.REJECT and Reason.CONTEXT_CONFLICT in result.reasons


@pytest.mark.parametrize(
    "kind", [s for s in Semantic if s not in (Semantic.VERIFIED_LABEL, Semantic.UNVERIFIED)]
)
def test_external_verified_nonlabel_role_cannot_be_accepted(kind):
    result = evaluate(evidence=(authority(semantic_kind=kind),))
    assert result.state == Decision.REJECT and Reason.NONLABEL_VALUE in result.reasons


@pytest.mark.parametrize("relation", list(LabelRelation))
def test_authority_cannot_resolve_hierarchy_or_composition_into_new_output(relation):
    result = evaluate(evidence=(authority(relation=relation),))
    assert result.state == Decision.HOLD and result.selected_candidate is None


def test_bad_authority_is_not_silently_ignored_beside_valid_authority():
    good, bad = authority(), authority(verification_state=AuthorityState.CONTRADICTED)
    for ordered in ((good, bad), (bad, good)):
        result = evaluate(evidence=ordered)
        assert result.state == Decision.REJECT and len(result.authority) == 2


def test_explicit_raw_correspondence_preserves_output_and_is_never_inferred():
    b = synthetic((" Label ",))
    assert evaluate(b, evidence=(authority(b),)).state == Decision.REJECT
    result = evaluate(b, evidence=(authority(b, raw_label_values=(" Label ",)),))
    assert result.state == Decision.ELIGIBLE and result.selected_candidate.term.value == " Label "


def test_no_candidate_is_skip_but_unfetched_and_unsupported_are_hold():
    b = synthetic(())
    result = evaluate(b)
    assert result.state == Decision.SKIP and Reason.NO_DISPLAY in result.reasons
    assert evaluate(b, context=acquired(b, book=Acquisition.NOT_REQUESTED)).state == Decision.HOLD
    assert evaluate(synthetic((RDFTerm("uri", "https://example.org/a"),))).state == Decision.HOLD


def test_numeric_appearance_alone_does_not_certify_or_remove_candidates():
    b = synthetic(("150", "Label"))
    c = compare(b)
    numeric = next(t for t in c.book_displays if t.display == "150")
    assert numeric.semantic_kind == Semantic.UNVERIFIED and Reason.NUMERIC_LIKE in numeric.reasons
    assert c.state == Comparison.MULTIPLE
    assert evaluate(synthetic(("150",))).state == Decision.HOLD


def test_ndl_series_title_observation_alone_is_never_semantic_authority():
    b = synthetic(series_labels=("Label",))
    ndl = replace(ndl_synthetic(), series_titles=["Label"])
    result = evaluate(b, ndl=ndl)
    assert result.comparison.ndl_overlap == ("Label",) and result.comparison.state == Comparison.BOTH_AGREE
    assert result.state == Decision.HOLD and Reason.SEMANTIC_UNVERIFIED in result.reasons


@pytest.mark.parametrize(
    "field,values", [("publishers", ["Different"]), ("publishers", []), ("editions", ["New Edition"])]
)
def test_ndl_context_conflicts_and_missing_values_do_not_default_to_match(field, values):
    ndl = replace(ndl_synthetic(), **{field: values})
    result = evaluate(ndl=ndl, evidence=(authority(),))
    assert result.state != Decision.ELIGIBLE


def test_returned_comparison_snapshots_mutable_ndl_input():
    ndl = ndl_synthetic()
    b = synthetic()
    linkage = compare_candidates(ndl, [b])
    c = compare(b, ndl)
    ndl.publishers[:] = ["Changed"]
    ndl.series_titles.append("Changed")
    ndl.isbns.clear()
    result = evaluate_imprint_eligibility(linkage, c, authority_evidence=(authority(b),))
    assert result.state == Decision.ELIGIBLE
    assert c.publisher.ndl[0].raw_value == "Publisher" and c.ndl_isbns == (ISBN,)


def test_permutations_and_repeat_calls_preserve_decision_and_every_raw_occurrence():
    b = synthetic(
        ("Label", "Label", RDFTerm("literal", "English 漢字", language="ja-hrkt")),
        series_labels=("Label", "Label"),
    )
    before = deepcopy(b)
    ndl = ndl_synthetic()
    linkage = compare_candidates(ndl, [b])
    outcomes = set()
    for label_order in permutations(b.book.labels):
        changed = replace(
            b,
            book=replace(b.book, labels=label_order, statements=tuple(reversed(b.book.statements))),
            series=tuple(
                replace(s, labels=tuple(reversed(s.labels)), statements=tuple(reversed(s.statements)))
                for s in b.series
            ),
        )
        c = compare(changed, ndl)
        a = evaluate_imprint_eligibility(linkage, c, authority_evidence=(authority(b),))
        repeated = evaluate_imprint_eligibility(linkage, c, authority_evidence=(authority(b),))
        assert a == repeated and a.state == Decision.ELIGIBLE
        outcomes.add((a.state, a.reasons, a.selected_candidate.term, c.state))
        for candidate in c.classification.extraction.candidates:
            r = changed.book if candidate.origin == "book" else changed.series[0]
            assert candidate.statements == tuple(r.statements[i] for i in candidate.statement_indices)
            assert all(r.labels[i] == candidate.term for i in candidate.label_indices)
    assert len(outcomes) == 1 and b == before


def test_multiple_and_unknown_order_never_changes_hold():
    terms = (literal("Label"), literal(" Label "), RDFTerm("literal", "other", language="en"))
    outcomes = set()
    for order in permutations(terms):
        result = evaluate(synthetic(order))
        outcomes.add((result.state, result.reasons, result.comparison.state))
        assert result.selected_candidate is None
    assert len(outcomes) == 1


def test_no_network_no_file_io_no_metadata_mutation_and_series_supplement_unchanged(monkeypatch):
    b = synthetic(series_labels=("Label",))
    ndl = ndl_synthetic()
    md = GenericMetadata(imprint="Existing", series=None, title="Existing Title")
    original, original_ndl, original_bundle = asdict(md), deepcopy(ndl), deepcopy(b)
    linkage = compare_candidates(ndl, [b])
    before = apply_series_supplement(md, linkage)
    forbidden = Mock(side_effect=AssertionError("Evaluation must be pure"))
    monkeypatch.setattr(requests.Session, "request", forbidden)
    monkeypatch.setattr("builtins.open", forbidden)
    output = evaluate(b, ndl=ndl, linkage=linkage, evidence=(authority(b),), existing=md.imprint)
    assert output.state == Decision.SKIP
    assert evaluate(b, ndl=ndl, linkage=linkage, evidence=(authority(b),)).state == Decision.ELIGIBLE
    assert asdict(md) == original and ndl == original_ndl and b == original_bundle
    assert apply_series_supplement(md, linkage) == before and before.series == "Work"
    forbidden.assert_not_called()
    with pytest.raises(FrozenInstanceError):
        output.state = Decision.ELIGIBLE


@pytest.mark.parametrize(
    "changes",
    [
        {"trusted": "yes"},
        {"verification_state": "verified"},
        {"source_kind": "publisher"},
        {"publisher": ""},
        {"isbn": "invalid"},
        {"book_uri": ID_NS + "M2"},
        {"checked_at": "2026-10-08"},
        {"checked_at": None},
        {"editions": []},
        {"publication_dates": ("2024-99-01",)},
        {"origin_group": ""},
    ],
)
def test_invalid_authority_contract_raises_before_evaluation(changes):
    with pytest.raises(ValueError):
        authority(**changes)


def test_invalid_acquisition_contract_and_result_invariants():
    with pytest.raises(ValueError):
        AcquisitionContext(discovery="complete")
    with pytest.raises(ValueError):
        AcquisitionContext(resources=[])
    output = evaluate(evidence=(authority(),))
    with pytest.raises(ValueError):
        replace(output, selected_candidate=None)
    with pytest.raises(ValueError):
        replace(output, state=Decision.HOLD)
    with pytest.raises(ValueError):
        replace(output, authority=())
    with pytest.raises(ValueError):
        replace(output, comparison=replace(output.comparison, state=Comparison.MULTIPLE))
    with pytest.raises(ValueError):
        evaluate(existing=0)


def test_strong_identity_with_trusted_scope_is_eligible_without_rewriting_identity():
    b = synthetic(urls=())
    linkage = compare_candidates(ndl_synthetic(), [b])
    assert linkage.matches[0].confidence == MatchConfidence.STRONG
    result = evaluate(b, linkage=linkage, evidence=(authority(b),))
    assert result.state == Decision.ELIGIBLE
    assert result.authority[0].semantic_kind == Semantic.VERIFIED_LABEL


def test_explicit_unverified_semantics_is_hold_even_with_verified_authority_state():
    result = evaluate(evidence=(authority(semantic_kind=Semantic.UNVERIFIED),))
    assert result.state == Decision.HOLD
    assert result.authority[0].semantic_kind == Semantic.UNVERIFIED


@pytest.mark.parametrize(
    "term",
    [RDFTerm("bnode", "C1"), RDFTerm("literal", ID_NS + "C1"), RDFTerm("uri", ID_NS + "C1", language="ja")],
)
def test_invalid_raw_series_relation_never_counts_as_resolved(term):
    b = synthetic(series_labels=("Label",))
    statements = tuple(
        replace(s, object=term) if s.predicate == SCHEMA_NS + "isPartOf" else s for s in b.book.statements
    )
    b = replace(b, book=replace(b.book, statements=statements))
    assert compare(b).state == Comparison.UNAVAILABLE
    assert Reason.RELATION_UNRESOLVED in evaluate(b).reasons


@pytest.mark.parametrize("predicate", [SCHEMA_NS + "identifier", RDF_NS + "type"])
def test_raw_identifier_or_type_mismatch_cannot_be_overridden_by_model_fields(predicate):
    b = synthetic()
    b = replace(
        b, book=replace(b.book, statements=tuple(s for s in b.book.statements if s.predicate != predicate))
    )
    result = evaluate(b, evidence=(authority(b),))
    assert result.state == Decision.REJECT and Reason.SNAPSHOT_MISMATCH in result.reasons


@pytest.mark.parametrize("display", [" Label\t", "Label\nX", "髙﨑𠮷"])
def test_xml_safe_unicode_and_whitespace_are_preserved(display):
    b = synthetic((display,))
    result = evaluate(b, evidence=(authority(b, label_name=display),))
    assert result.state == Decision.ELIGIBLE and result.selected_candidate.term.value == display


def test_missing_publisher_or_date_and_unknown_date_beside_supported_value_are_not_matches():
    for b in (
        synthetic(extra=((SCHEMA_NS + "datePublished", RDFTerm("literal", "date", language="en")),)),
        replace(
            synthetic(),
            book=replace(
                synthetic().book,
                publishers=(),
                statements=tuple(
                    s for s in synthetic().book.statements if s.predicate != SCHEMA_NS + "publisher"
                ),
            ),
        ),
        replace(
            synthetic(),
            book=replace(
                synthetic().book,
                publication_dates=(),
                statements=tuple(
                    s for s in synthetic().book.statements if s.predicate != SCHEMA_NS + "datePublished"
                ),
            ),
        ),
    ):
        assert evaluate(b, evidence=(authority(b),)).state != Decision.ELIGIBLE


def test_series_unknown_empty_and_missing_context_are_separate_from_no_brand():
    b = synthetic(series_labels=())
    assert evaluate(b, evidence=(authority(b),)).state == Decision.ELIGIBLE
    unknown = synthetic(series_labels=(RDFTerm("literal", "", language="en"),))
    result = evaluate(unknown, evidence=(authority(unknown),))
    assert result.comparison.state == Comparison.BOOK_ONLY and result.state == Decision.HOLD
    edition = synthetic(series_labels=("Label",), extra=((SCHEMA_NS + "version", literal("Edition")),))
    assert (
        Reason.CONTEXT_UNVERIFIED in compare(edition, replace(ndl_synthetic(), editions=["Edition"])).blockers
    )
