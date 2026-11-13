"""P2 basics: synthetic contracts and a separately labelled measured RDF case."""

from __future__ import annotations

import builtins
import hashlib
import io
import json
import os
import socket
import sqlite3
import time
from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
from pathlib import Path

import pytest
import requests
from comicapi.genericmetadata import GenericMetadata

from comictagger_jp_talker import publisher_comparison as shadow
from comictagger_jp_talker.acquisition import AcquisitionContext
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.imprint_candidates import (
    classify_imprint_terms,
    compare_imprint_candidates,
    evaluate_imprint_eligibility,
    extract_imprint_evidence,
)
from comictagger_jp_talker.linkage import compare_candidates
from comictagger_jp_talker.linked_acquisition import NDLInputSnapshot
from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.publisher_comparison import (
    PublisherAssociationState as Association,
)
from comictagger_jp_talker.publisher_comparison import (
    PublisherComparisonPolicy,
    PublisherIdentityAssessment,
    compare_publisher_observations,
)
from comictagger_jp_talker.publisher_comparison import (
    PublisherIdentityState as Identity,
)
from comictagger_jp_talker.publisher_comparison import (
    PublisherLexicalState as Lexical,
)
from comictagger_jp_talker.publisher_comparison import (
    PublisherRawLayer as Layer,
)
from comictagger_jp_talker.publisher_comparison import (
    PublisherRole as Role,
)
from comictagger_jp_talker.publisher_comparison import (
    PublisherStructuralState as Structural,
)
from comictagger_jp_talker.sources.madb import MADBSource
from comictagger_jp_talker.sources.madb_models import MADBRecordBundle, RDFTerm
from comictagger_jp_talker.sources.madb_parser import parse_resource
from comictagger_jp_talker.sources.madb_queries import CLASS_NS, DCTERMS_NS, ID_NS, RDF_NS, SCHEMA_NS
from comictagger_jp_talker.sources.ndl import NDLSource


def literal(value, language=None):
    return RDFTerm("literal", value, language=language)


def resource(identifier, kind, entries):
    """Synthetic RDF builder; parser behavior is exercised without changing it."""
    bindings = []
    for predicate, term in (
        (RDF_NS + "type", RDFTerm("uri", CLASS_NS + kind)),
        (SCHEMA_NS + "identifier", literal(identifier)),
        *entries,
    ):
        obj = {"type": term.kind, "value": term.value}
        if term.language is not None:
            obj["xml:lang"] = term.language
        if term.datatype is not None:
            obj["datatype"] = term.datatype
        bindings.append({"p": {"type": "uri", "value": predicate}, "o": obj})
    payload = {"head": {"vars": ["p", "o"]}, "results": {"bindings": bindings}}
    resource_kind = {"MangaBook": "book", "MangaBookSeries": "series", "Agent": "agent"}[kind]
    return parse_resource(json.dumps(payload).encode(), ID_NS + identifier, resource_kind, 300)


def synthetic(publishers=("Publisher",), *, series=(), references=(), agents=(), extra=()):
    entries = [(SCHEMA_NS + "publisher", v if isinstance(v, RDFTerm) else literal(v)) for v in publishers]
    entries += [(DCTERMS_NS + "publisher", v) for v in references]
    entries += [(SCHEMA_NS + "isPartOf", RDFTerm("uri", ID_NS + f"C{i + 1}")) for i in range(len(series))]
    book = resource("M1", "MangaBook", [*entries, *extra])
    series_records = tuple(
        resource(f"C{i + 1}", "MangaBookSeries", [(SCHEMA_NS + "publisher", literal(v)) for v in values])
        for i, values in enumerate(series)
    )
    return MADBRecordBundle(book, series_records, tuple(agents))


def complete(bundle, **changes):
    related = bool(bundle.book.series_uris)
    return replace(
        AcquisitionContext(
            discovery=State.COMPLETE,
            book=State.COMPLETE,
            series=State.COMPLETE if related else State.NOT_RELATED,
            relations=State.COMPLETE if related else State.NOT_RELATED,
            agents=State.COMPLETE,
        ),
        **changes,
    )


def compare(bundle=None, publishers=("Publisher",), *, context=None, **kwargs):
    bundle = bundle if bundle is not None else synthetic()
    return compare_publisher_observations(
        bundle,
        BookRecord("ndl-test", "Title", publishers=list(publishers)),
        context if context is not None else complete(bundle),
        ndl_completeness=State.COMPLETE,
        **kwargs,
    )


def primary_pair(result, left="book", right="ndl"):
    groups = {group.group_id: group for group in result.groups}
    ids = (groups[left].publisher_ids[0], groups[right].publisher_ids[0])
    return next(pair for pair in result.lexical_results if (pair.left_id, pair.right_id) == ids)


@pytest.mark.parametrize(
    "left,right,state,keys,reasons",
    [
        ("芳文社", "芳文社", Lexical.EXACT, ("芳文社", "芳文社"), ()),
        (
            "ガ社",
            "カ\u3099社",
            Lexical.NORMALIZED_EQUAL,
            ("ガ社", "ガ社"),
            ("n1_only_equal", "right_nfc_changed"),
        ),
        (
            " 芳文社 ",
            "芳文社",
            Lexical.NORMALIZED_EQUAL,
            ("芳文社", "芳文社"),
            ("n1_only_equal", "left_outer_whitespace"),
        ),
        (
            "芳文社　",
            "芳文社",
            Lexical.NORMALIZED_EQUAL,
            ("芳文社", "芳文社"),
            ("n1_only_equal", "left_outer_whitespace"),
        ),
        ("①出版", "1出版", Lexical.DIFFERENT, ("①出版", "1出版"), ("lexical_difference",)),
        ("A  B出版", "A B出版", Lexical.DIFFERENT, ("A  B出版", "A B出版"), ("lexical_difference",)),
        (
            "株式会社芳文社",
            "芳文社",
            Lexical.DIFFERENT,
            ("株式会社芳文社", "芳文社"),
            ("lexical_difference",),
        ),
        ("A / B", "A", Lexical.DIFFERENT, ("A / B", "A"), ("lexical_difference",)),
    ],
)
def test_n0_n1_and_diagnostic_only_n2_boundary(left, right, state, keys, reasons):
    result = compare(synthetic((left,)), (right,))
    pair = primary_pair(result)
    assert pair.state == state
    assert pair.raw_equal is (left == right)
    assert (pair.left_key, pair.right_key) == keys
    assert pair.reasons == reasons
    assert pair.rules == ("unicode_nfc", "outer_str_strip")
    assert pair.normalization_version == "nfc-strip-v1"
    assert pair.notation_notes == ()
    assert result.observations[0].raw_value == literal(left)
    assert result.observations[-1].raw_value == right
    assert all(identity.state == Identity.UNVERIFIED for identity in result.identity_assessments)


@pytest.mark.parametrize("value", ["", " ", "　", "\t\n"])
def test_empty_strings_have_raw_equality_but_no_comparable_key(value):
    result = compare(synthetic((value,)), (value,))
    pair = primary_pair(result)
    assert pair.raw_equal is True
    assert pair.state == Lexical.UNCOMPARABLE
    assert pair.left_key is pair.right_key is None
    assert result.group_comparisons[0].state == Lexical.UNCOMPARABLE
    assert result.unresolved and not result.conflict


def test_parsed_ndl_has_only_known_provenance_and_preserves_duplicate_list_values():
    ndl = BookRecord("ndl", "Title", publishers=["Publisher", "Publisher"])
    # Existing raw_xml is deliberately ignored: P2 has no XML association adapter.
    ndl.raw_xml = '<Agent about="invented"><name>Publisher</name></Agent>'
    result = compare_publisher_observations(synthetic(), ndl, complete(synthetic()))
    values = [o for o in result.observations if o.origin == shadow.PublisherOrigin.NDL]
    assert len(values) == 2 and values[0].observation_id != values[1].observation_id
    assert tuple(o.value_index for o in values) == (0, 1)
    assert all(o.raw_layer == Layer.PARSED_VALUE and o.kind is None for o in values)
    assert all(o.node_index is o.statement is o.statement_index is o.document_scope is None for o in values)
    assert all(o.provenance.predicate_or_path == "BookRecord.publishers" for o in values)
    assert result.agent_associations == ()
    assert result.groups[-1].completeness == State.NOT_REQUESTED


def test_multiple_publishers_and_each_series_are_preserved_without_partial_set_match():
    bundle = synthetic(("A", "B"), series=(("A", "B"), ("A",)))
    result = compare(bundle, ("A",))
    assert tuple(group.keys for group in result.groups) == (("A", "B"), ("A", "B"), ("A",), ("A",))
    assert tuple(group.group_id for group in result.groups) == ("book", "series:0", "series:1", "ndl")
    assert result.group_comparisons[0].state == Lexical.EXACT
    assert result.group_comparisons[1].state == Lexical.DIFFERENT
    assert result.conflict and result.unresolved
    assert any(issue.reason == "multiple_publisher_values" for issue in result.unresolved_reasons)
    assert len(result.observations) == 6


def test_series_duplicate_statements_keep_individual_positions():
    result = compare(synthetic(series=(("Publisher", "Publisher"),)))
    group = result.groups[1]
    observations = [o for o in result.observations if o.group_id == group.group_id]
    assert len(group.publisher_ids) == 2
    assert group.keys == ("Publisher",)
    assert [o.statement_index for o in observations] == [2, 3]
    assert observations[0].observation_id != observations[1].observation_id


def test_shared_display_beside_unknown_publisher_cannot_establish_whole_group_equality():
    bundle = synthetic(("Publisher", RDFTerm("uri", "https://example.invalid/unknown")))
    result = compare(bundle)
    assert primary_pair(result).state == Lexical.EXACT
    assert result.group_comparisons[0].state == Lexical.UNCOMPARABLE
    assert result.groups[0].keys == ("Publisher",)
    assert len(result.groups[0].publisher_ids) == 2
    assert result.unresolved


def test_valid_agent_uri_without_snapshot_stays_unverified():
    result = compare(synthetic(references=(RDFTerm("uri", ID_NS + "C8"),)))
    association = result.agent_associations[0]
    assert association.state == Association.UNVERIFIED
    assert association.reasons == ("agent_snapshot_missing",)
    assert association.snapshot_state is None
    assert result.unresolved and not result.conflict


def test_explicit_publisher_edge_links_agent_names_and_readings_but_not_sibling_literal():
    agent = resource(
        "C8",
        "Agent",
        [(SCHEMA_NS + "name", literal("Publisher")), (SCHEMA_NS + "name", literal("ヨミ", "ja-hrkt"))],
    )
    bundle = synthetic(references=(RDFTerm("uri", agent.uri),), agents=(agent,))
    result = compare(bundle)
    association = result.agent_associations[0]
    assert association.state == Association.EXPLICIT
    assert association.snapshot_state == State.COMPLETE
    assert association.reasons == ()
    assert not result.conflict and not result.unresolved
    assert len(association.name_observation_ids) == len(association.reading_observation_ids) == 1
    local = result.structural_results[-1]
    assert local.state == Structural.EXPLICIT_READING
    assert local.association_ids == (association.association_id,)
    assert result.lexical_results[-1].state == Lexical.UNCOMPARABLE
    pair = primary_pair(result)
    structural = next(
        s for s in result.structural_results if (s.left_id, s.right_id) == (pair.left_id, pair.right_id)
    )
    assert pair.state == Lexical.EXACT and structural.state == Structural.UNVERIFIED
    assert all(i.state == Identity.UNVERIFIED for i in result.identity_assessments)
    names = [o for o in result.observations if o.role in (Role.AGENT_NAME, Role.AGENT_READING)]
    assert all(o.record_uri == bundle.book.uri and o.provenance.record_uri == agent.uri for o in names)


def test_creator_and_provider_agents_are_never_publisher_associations():
    agent = resource("C8", "Agent", [(SCHEMA_NS + "name", literal("Publisher"))])
    bundle = synthetic(
        agents=(agent,),
        extra=(
            (DCTERMS_NS + "creator", RDFTerm("uri", agent.uri)),
            (SCHEMA_NS + "provider", RDFTerm("uri", agent.uri)),
        ),
    )
    result = compare(bundle)
    assert result.agent_associations == ()
    assert len(result.observations) == 2
    assert result.structural_results[0].state == Structural.UNVERIFIED


@pytest.mark.parametrize(
    "name", [literal("Foreign", "en"), RDFTerm("literal", "Broken", RDF_NS + "langString")]
)
def test_unknown_or_invalid_agent_name_does_not_get_promoted_to_a_verified_reading_pair(name):
    agent = resource(
        "C8", "Agent", [(SCHEMA_NS + "name", name), (SCHEMA_NS + "name", literal("ヨミ", "ja-hrkt"))]
    )
    result = compare(synthetic(references=(RDFTerm("uri", agent.uri),), agents=(agent,)))
    assert "agent_name_uncomparable" in result.agent_associations[0].reasons
    assert result.structural_results[-1].state == Structural.SAME_AGENT
    assert result.lexical_results[-1].state == Lexical.UNCOMPARABLE
    assert result.unresolved
    assert all(i.state == Identity.UNVERIFIED for i in result.identity_assessments)


def test_same_named_different_agent_resources_are_not_merged_or_treated_as_different_legal_entities():
    agents = tuple(resource(f"C{i}", "Agent", [(SCHEMA_NS + "name", literal("Publisher"))]) for i in (8, 9))
    bundle = synthetic((RDFTerm("uri", agents[0].uri),), series=(("Publisher",),), agents=agents)
    s = bundle.series[0]
    bundle = replace(
        bundle,
        series=(
            replace(
                s,
                publisher_references=(RDFTerm("uri", agents[1].uri),),
                statements=(
                    *s.statements,
                    shadow.MADBStatement(s.uri, DCTERMS_NS + "publisher", RDFTerm("uri", agents[1].uri)),
                ),
            ),
        ),
    )
    result = compare(bundle)
    assert len(result.agent_associations) == 2
    names = {o.observation_id for o in result.observations if o.role == Role.AGENT_NAME}
    pair = next(p for p in result.lexical_results if p.left_id in names and p.right_id in names)
    structural = next(
        s for s in result.structural_results if (s.left_id, s.right_id) == (pair.left_id, pair.right_id)
    )
    assert pair.state == Lexical.EXACT and structural.state == Structural.DISTINCT_RESOURCES
    assert all(i.state == Identity.UNVERIFIED for i in result.identity_assessments)


@pytest.mark.parametrize(
    "term,reason",
    [
        (literal("P4832200000"), "literal_reference_unverified"),
        (RDFTerm("uri", "https://example.invalid/publisher"), "unsupported_agent_uri"),
        (RDFTerm("uri", "C8"), "unsupported_agent_uri"),
        (RDFTerm("bnode", "b1"), "bnode_snapshot_unsupported"),
    ],
)
def test_unknown_publisher_references_are_retained_without_uri_or_identity_invention(term, reason):
    result = compare(synthetic(references=(term,)))
    association = result.agent_associations[0]
    assert association.agent_reference == term
    assert association.state == Association.UNVERIFIED
    assert reason in association.reasons
    assert association.name_observation_ids == association.reading_observation_ids == ()
    observation = next(o for o in result.observations if o.role == Role.REFERENCE)
    assert observation.raw_value == term and observation.statement.object == term
    assert all(
        p.state == Lexical.UNCOMPARABLE
        for p in result.lexical_results
        if p.left_id == observation.observation_id
    )


def test_bnode_keeps_explicit_document_scope_without_attempting_resolution():
    result = compare(
        synthetic(references=(RDFTerm("bnode", "b1"),)), document_scopes=((ID_NS + "M1", "doc-a"),)
    )
    association = result.agent_associations[0]
    assert association.document_scope == "doc-a"
    assert association.state == Association.UNVERIFIED
    assert association.reasons == ("bnode_snapshot_unsupported",)


@pytest.mark.parametrize("state", list(State))
def test_completeness_states_are_preserved_independently_of_lexical_equality(state):
    bundle = synthetic()
    result = compare(bundle, context=complete(bundle, book=state))
    assert result.acquisition.book == state
    assert result.groups[0].acquisition_state == result.groups[0].completeness == state
    assert result.groups[0].snapshot_state == State.COMPLETE
    assert primary_pair(result).state == Lexical.EXACT
    if state != State.COMPLETE:
        assert any(i.reason == "acquisition_incomplete" for i in result.unresolved_reasons)


def test_complete_missing_and_not_requested_publishers_are_distinct():
    bundle = synthetic(())
    missing = compare(bundle, ())
    not_requested = compare(bundle, (), context=complete(bundle, book=State.NOT_REQUESTED))
    assert missing.groups[0].completeness == State.COMPLETE
    assert any(
        i.reason == "publisher_missing" and i.group_ids == ("book",) for i in missing.unresolved_reasons
    )
    assert not_requested.groups[0].completeness == State.NOT_REQUESTED
    assert any(
        i.reason == "publisher_unobserved" and i.group_ids == ("book",)
        for i in not_requested.unresolved_reasons
    )
    assert all(
        c.state == Lexical.UNCOMPARABLE
        for c in (*missing.group_comparisons, *not_requested.group_comparisons)
    )


@pytest.mark.parametrize(
    "declared,effective",
    [
        (State.NOT_REQUESTED, State.NOT_REQUESTED),
        (State.COMPLETE, State.UNAVAILABLE),
    ],
)
def test_expected_series_without_snapshot_preserves_declared_and_effective_states(declared, effective):
    bundle = replace(synthetic(series=(("Publisher",),)), series=())
    result = compare(bundle, context=complete(bundle, series=declared))
    missing = result.groups[1]
    assert missing.group_id == "missing_series:0" and missing.record_uri == ID_NS + "C1"
    assert missing.snapshot_state is None and missing.completeness == effective
    assert missing.acquisition_state == declared
    assert missing.related_to_book and missing.observation_ids == ()
    assert result.unresolved
    assert not result.conflict


def test_agent_partial_does_not_turn_into_identity_or_lexical_conflict():
    agent = resource("C8", "Agent", [(SCHEMA_NS + "name", literal("Publisher"))])
    bundle = synthetic(
        references=(RDFTerm("uri", agent.uri),), agents=(replace(agent, completeness="partial"),)
    )
    result = compare(bundle, context=complete(bundle, agents=State.PARTIAL))
    association = result.agent_associations[0]
    assert association.acquisition_state == association.snapshot_state == State.PARTIAL
    assert "agent_acquisition_incomplete" in association.reasons
    assert "agent_snapshot_incomplete" in association.reasons
    assert primary_pair(result).state == Lexical.EXACT
    assert result.unresolved and not result.conflict


def test_unrelated_series_is_retained_without_becoming_a_comparison_group():
    unrelated = resource("C9", "MangaBookSeries", [(SCHEMA_NS + "publisher", literal("Different"))])
    result = compare(replace(synthetic(), series=(unrelated,)))
    assert result.groups[1].related_to_book is False
    assert result.groups[1].keys == ("Different",)
    assert len(result.group_comparisons) == 1
    assert not result.conflict


def test_field_only_value_is_retained_but_not_given_statement_provenance_or_matching_key():
    bundle = synthetic()
    bundle = replace(bundle, book=replace(bundle.book, publishers=(literal("Invented"),)))
    result = compare(bundle)
    extra = next(o for o in result.observations if o.raw_value == literal("Invented"))
    assert extra.raw_layer == Layer.MODEL_FIELD
    assert extra.statement is extra.statement_index is None
    assert not extra.provenance_verified
    assert result.groups[0].keys == ("Publisher",)
    assert result.conflict and result.unresolved


@pytest.fixture
def measured_houbunsha():
    """2026-10-08 measured RDF/NDL values; completion/linkage envelope is synthetic."""
    root = Path(__file__).resolve().parents[1]
    raw_bytes = (root / "docs/research/madb/imprint_evidence.json").read_bytes()
    data = json.loads(raw_bytes)
    fixture = json.loads((root / "tests/fixtures/madb/imprint_measured.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(raw_bytes).hexdigest() == fixture["source_sha256"]
    observations = {o["resource"]: o for o in data["observations"] if o["state"] == "complete"}

    def parse(uri):
        o = observations[uri]
        assert all(r["s"]["value"] == uri for r in o["raw_bindings"])
        payload = {
            "head": {"vars": ["p", "o"]},
            "results": {
                "bindings": [{"p": r["p"], "o": r["o"]} for r in o["raw_bindings"]],
            },
        }
        return parse_resource(json.dumps(payload).encode(), uri, o["kind"], 300)

    book = parse(ID_NS + "M381096")
    bundle = MADBRecordBundle(
        book, tuple(parse(uri) for uri in book.series_uris), retrieval_scope="series_linkage"
    )
    ndl = BookRecord(**fixture["ndl_records"]["M381096"])
    return bundle, ndl, complete(bundle, agents=State.NOT_REQUESTED)


def legacy_comparison(bundle, ndl, context):
    classification = classify_imprint_terms(extract_imprint_evidence(bundle, context))
    return compare_imprint_candidates(classification, ndl)


def test_measured_houbunsha_raw_shadow_and_legacy_eligibility_are_independent(measured_houbunsha):
    bundle, ndl, context = measured_houbunsha
    comparison = legacy_comparison(bundle, ndl, context)
    linkage = compare_candidates(ndl, (bundle,))
    before = evaluate_imprint_eligibility(linkage, comparison)
    result = compare_publisher_observations(
        bundle, ndl, context, legacy=comparison.publisher, ndl_completeness=State.COMPLETE
    )
    assert tuple(group.keys for group in result.groups) == (
        ("芳文社　∥　ホウブンシャ",),
        ("芳文社　∥　ホウブンシャ",),
        ("芳文社",),
    )
    assert primary_pair(result).state == Lexical.DIFFERENT
    assert primary_pair(result, "series:0").state == Lexical.DIFFERENT
    assert all(s.state == Structural.UNVERIFIED for s in result.structural_results)
    assert all(i.state == Identity.UNVERIFIED for i in result.identity_assessments)
    assert tuple(a.agent_reference for a in result.agent_associations) == (literal("P4832200000"),) * 2
    assert all(a.state == Association.UNVERIFIED for a in result.agent_associations)
    assert result.legacy == comparison.publisher and result.legacy is not comparison.publisher
    assert result.legacy.conflict is True and result.legacy.unresolved is False
    assert before == evaluate_imprint_eligibility(linkage, comparison)
    assert before.state.value == "reject" and before.selected_candidate is None
    assert tuple(reason.value for reason in before.reasons) == (
        "context_conflict",
        "multiple_displays",
        "semantic_unverified",
    )


def test_input_result_and_legacy_snapshots_are_immutable_and_deterministic(measured_houbunsha):
    bundle, ndl, context = measured_houbunsha
    legacy = legacy_comparison(bundle, ndl, context).publisher
    before = deepcopy((bundle, ndl, context, legacy))
    policy = PublisherComparisonPolicy()
    result = compare_publisher_observations(bundle, ndl, context, policy, legacy=legacy)
    assert result == compare_publisher_observations(bundle, ndl, context, policy, legacy=legacy)
    assert hash(result) == hash(compare_publisher_observations(bundle, ndl, context, policy, legacy=legacy))
    assert (bundle, ndl, context, legacy) == before
    ndl.publishers.append("Changed")
    assert result.ndl_snapshot.publishers == ("芳文社",)
    assert result.legacy == before[-1]
    with pytest.raises(FrozenInstanceError):
        result.groups = ()
    with pytest.raises(FrozenInstanceError):
        result.observations[0].raw_value = "Changed"
    with pytest.raises(ValueError, match="immutable"):
        replace(result, observations=[])


def test_mutable_ndl_is_not_reread_during_comparison(monkeypatch):
    bundle = synthetic()
    ndl = BookRecord("ndl", "Title", publishers=["Publisher"])
    original_key = shadow._key

    def interrupt(observation):
        ndl.publishers[:] = ["Changed"]
        return original_key(observation)

    monkeypatch.setattr(shadow, "_key", interrupt)
    result = compare_publisher_observations(bundle, ndl, complete(bundle))
    assert result.ndl_snapshot.publishers == ("Publisher",)
    assert primary_pair(result).state == Lexical.EXACT


def test_no_network_files_cache_clock_metadata_or_existing_evaluator_side_effects(
    monkeypatch, measured_houbunsha
):
    bundle, ndl, context = measured_houbunsha
    legacy = legacy_comparison(bundle, ndl, context).publisher
    metadata = to_metadata(ndl)
    metadata_before = deepcopy(metadata)
    before = deepcopy((bundle, ndl, context, legacy))

    def forbidden(*args, **kwargs):
        raise AssertionError("Shadow comparison must have no I/O or metadata/evaluator calls")

    with monkeypatch.context() as guarded:
        for target, name in (
            (builtins, "open"),
            (io, "open"),
            (os, "open"),
            (sqlite3, "connect"),
            (socket.socket, "connect"),
            (socket, "create_connection"),
            (requests.sessions.Session, "request"),
            (requests.sessions.Session, "__init__"),
            (MADBSource, "__init__"),
            (NDLSource, "__init__"),
            (GenericMetadata, "__init__"),
            (time, "time"),
            (time, "monotonic"),
            (time, "perf_counter"),
        ):
            guarded.setattr(target, name, forbidden)
        from comictagger_jp_talker import imprint_candidates, mapping, metadata_supplement

        guarded.setattr(imprint_candidates, "compare_imprint_candidates", forbidden)
        guarded.setattr(imprint_candidates, "evaluate_imprint_eligibility", forbidden)
        guarded.setattr(imprint_candidates, "_authority_assessment", forbidden)
        guarded.setattr(mapping, "to_metadata", forbidden)
        guarded.setattr(metadata_supplement, "supplement_metadata", forbidden)
        result = compare_publisher_observations(
            bundle, NDLInputSnapshot.from_record(ndl), context, legacy=legacy
        )
    assert result.legacy == legacy
    assert metadata == metadata_before
    assert (bundle, ndl, context, legacy) == before
    assert asdict(result)["ndl_snapshot"]["publishers"] == ("芳文社",)


def test_no_authority_acceptance_path_or_unknown_normalization_policy():
    with pytest.raises(ValueError, match="authority"):
        PublisherIdentityAssessment(left_id="a", right_id="b", state=Identity.VERIFIED_SAME)
    with pytest.raises(ValueError, match="policy"):
        PublisherComparisonPolicy(normalization_version="nfkc")
    result = compare()
    assert result.legacy is None
    assert result.policy.version == "publisher-shadow-p2-v1"
