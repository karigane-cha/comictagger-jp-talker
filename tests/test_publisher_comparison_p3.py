"""P3 fixed regressions; synthetic inputs unless explicitly labelled measured.

P01-P20 refer to the P1 requirements, not to new normalization/identity rules.
The private P1 report is a design reference only, never a runtime dependency.
Existing P2 tests retain the measured Houbunsha case and broad I/O guards.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from itertools import permutations

import pytest
from test_imprint_candidates import acquired, authority, evaluate, ndl_synthetic
from test_imprint_candidates import synthetic as imprint_bundle
from test_imprint_report import evidence_for
from test_publisher_comparison import (
    compare,
    complete,
    legacy_comparison,
    literal,
    primary_pair,
    resource,
    synthetic,
)

from comictagger_jp_talker import imprint_diagnostics, imprint_report, linkage
from comictagger_jp_talker import publisher_comparison as shadow
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.acquisition import ResourceAcquisition
from comictagger_jp_talker.linked_acquisition import NDLInputSnapshot
from comictagger_jp_talker.mapping import to_metadata
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.publisher_comparison import PublisherAssociationState as Association
from comictagger_jp_talker.publisher_comparison import PublisherIdentityState as Identity
from comictagger_jp_talker.publisher_comparison import PublisherLexicalState as Lexical
from comictagger_jp_talker.publisher_comparison import PublisherRole as Role
from comictagger_jp_talker.publisher_comparison import PublisherStructuralState as Structural
from comictagger_jp_talker.sources.madb_models import MADBError, MADBStatement, RDFTerm
from comictagger_jp_talker.sources.madb_parser import parse_term
from comictagger_jp_talker.sources.madb_queries import DCTERMS_NS, ID_NS, RDF_NS, SCHEMA_NS, XSD_NS
from comictagger_jp_talker.talker import JapaneseBooksTalker


def agent(identifier="C8", names=("Publisher",), readings=("ヨミ",)):
    """Synthetic Agent; no assertion of real-world publisher identity."""
    return resource(
        identifier,
        "Agent",
        [(SCHEMA_NS + "name", literal(v)) for v in names]
        + [(SCHEMA_NS + "name", literal(v, "ja-hrkt")) for v in readings],
    )


def with_references(record, references):
    return replace(
        record,
        publisher_references=tuple(references),
        statements=(
            *record.statements,
            *(MADBStatement(record.uri, DCTERMS_NS + "publisher", v) for v in references),
        ),
    )


def assert_unverified(result):
    assert result.identity_assessments
    assert all(i.state == Identity.UNVERIFIED for i in result.identity_assessments)
    assert all(i.reasons == ("authority_not_supplied",) for i in result.identity_assessments)


@pytest.mark.parametrize(
    "book,series,ndl,states,conflict,unresolved",
    [
        pytest.param(("芳文社",), ("芳文社",), ("芳文社",), (Lexical.EXACT,) * 3, False, False, id="P01"),
        pytest.param(
            ("芳文社", "他社"),
            ("芳文社", "他社"),
            ("芳文社", "他社"),
            (Lexical.EXACT,) * 3,
            False,
            True,
            id="P08",
        ),
        pytest.param(
            ("芳文社",),
            ("他社",),
            ("芳文社",),
            (Lexical.DIFFERENT, Lexical.EXACT, Lexical.DIFFERENT),
            True,
            False,
            id="P09",
        ),
        pytest.param(
            ("芳文社",),
            ("芳文社",),
            (),
            (Lexical.EXACT, Lexical.UNCOMPARABLE, Lexical.UNCOMPARABLE),
            False,
            True,
            id="P10",
        ),
    ],
)
def test_p01_p08_p09_p10_three_group_contract(book, series, ndl, states, conflict, unresolved):
    bundle = synthetic(book, series=(series,))
    record = BookRecord("ndl", "", publishers=list(ndl))
    context = complete(bundle)
    legacy = legacy_comparison(bundle, record, context).publisher
    result = shadow.compare_publisher_observations(
        bundle, record, context, legacy=legacy, ndl_completeness=State.COMPLETE
    )
    assert tuple(p.state for p in result.group_comparisons) == states
    assert (result.conflict, result.unresolved) == (conflict, unresolved)
    assert (legacy.conflict, legacy.unresolved) == (conflict, unresolved)
    assert result.legacy == legacy
    assert len(result.observations) == len(book) + len(series) + len(ndl)
    assert {i.group_ids for i in result.conflict_reasons} == (
        {("book", "series:0"), ("series:0", "ndl")} if conflict else set()
    )
    assert_unverified(result)


def test_p02_mixed_unicode_keeps_both_raw_strings_and_change_reasons():
    left, right = " \tカ\u3099社 Cafe\u0301・Ω\u3000", "ガ社 Café・Ω"
    result = compare(synthetic((left,)), (right,))
    pair = primary_pair(result)
    assert pair.state == Lexical.NORMALIZED_EQUAL and pair.raw_equal is False
    assert (pair.left_key, pair.right_key) == (right, right)
    assert pair.reasons == ("n1_only_equal", "left_nfc_changed", "left_outer_whitespace")
    assert tuple(o.raw_string for o in result.observations) == (left, right)
    assert_unverified(result)


NOTATION_PAIRS = [
    pytest.param("芳文社", "ホウブンシャ", id="reading"),
    pytest.param("學藝社", "学芸社", id="old-new-kanji"),
    pytest.param("ﾎｳﾌﾞﾝｼｬ", "ホウブンシャ", id="halfwidth-katakana"),
    pytest.param("ＡＢＣ出版", "ABC出版", id="fullwidth-latin"),
    pytest.param("A　B出版", "A B出版", id="internal-width"),
    pytest.param("A\tB出版", "AB出版", id="internal-tab"),
    pytest.param("A\u200bB出版", "AB出版", id="zero-width"),
    pytest.param("ABC出版", "abc出版", id="case"),
    pytest.param("A-B出版", "AB出版", id="hyphen"),
    pytest.param("A・B出版", "AB出版", id="middle-dot"),
    pytest.param("コール社", "コル社", id="long-vowel"),
    pytest.param("A∥エー", "A", id="delimiter-reading"),
    pytest.param("[発売]出版社", "出版社", id="role-prefix"),
    pytest.param("別名出版", "正式出版", id="alias-without-evidence"),
]


@pytest.mark.parametrize("left,right", NOTATION_PAIRS)
def test_p13_p14_notation_boundary(left, right):
    result = compare(synthetic((left,)), (right,))
    pair = primary_pair(result)
    assert pair.state == Lexical.DIFFERENT
    assert (pair.left_key, pair.right_key) == (left, right)
    assert pair.notation_notes == ()  # P2 reserves N2 notes; it implements no N2 rules.
    assert pair.rules == ("unicode_nfc", "outer_str_strip")
    assert result.conflict
    assert_unverified(result)


@pytest.mark.parametrize("same_resource", [True, False], ids=["same-agent", "distinct-agents"])
@pytest.mark.parametrize(
    "left,right", [("株式会社芳文社", "芳文社"), ("①出版", "1出版"), ("Publisher", "Publisher")]
)
def test_p07_p13_p14_agent_collision(left, right, same_resource):
    a = agent(names=(left, right), readings=()) if same_resource else agent(names=(left,), readings=())
    b = a if same_resource else agent("C9", names=(right,), readings=())
    bundle = synthetic(references=(RDFTerm("uri", a.uri),), series=(("Publisher",),), agents=(a,))
    bundle = replace(
        bundle,
        agents=(a,) if same_resource else (a, b),
        series=(with_references(bundle.series[0], (RDFTerm("uri", b.uri),)),),
    )
    result = compare(bundle)
    observations = {o.observation_id: o for o in result.observations}
    pairs = [
        p
        for p in result.lexical_results
        if observations[p.left_id].role == observations[p.right_id].role == Role.AGENT_NAME
        and observations[p.left_id].raw_string == left
        and observations[p.right_id].raw_string == right
    ]
    assert pairs
    for pair in pairs:
        structure = next(
            s for s in result.structural_results if (s.left_id, s.right_id) == (pair.left_id, pair.right_id)
        )
        assert pair.state == (Lexical.EXACT if left == right else Lexical.DIFFERENT)
        assert structure.state == (Structural.SAME_AGENT if same_resource else Structural.DISTINCT_RESOURCES)
    assert len(result.agent_associations) == 2
    assert_unverified(result)


@pytest.mark.parametrize("reading_on_same_agent", [True, False], ids=["P06", "P15"])
def test_p06_p15_multi_edge_names_and_readings(reading_on_same_agent):
    a = agent(names=("Name", "Alias"), readings=("ヨミ", "ベツヨミ") if reading_on_same_agent else ())
    b = agent("C9", names=(), readings=() if reading_on_same_agent else ("ヨミ", "ベツヨミ"))
    bundle = synthetic(
        references=(RDFTerm("uri", a.uri), RDFTerm("uri", b.uri)),
        series=(("Publisher",),),
        agents=(a, b),
    )
    bundle = replace(bundle, series=(with_references(bundle.series[0], (RDFTerm("uri", b.uri),)),))
    result = compare(bundle)
    associations = result.agent_associations
    assert tuple(a.agent_reference.value for a in associations) == (a.uri, b.uri, b.uri)
    assert len(associations[0].name_observation_ids) == 2
    name_ids = set(associations[0].name_observation_ids)
    reading_ids = {oid for a in associations for oid in a.reading_observation_ids}
    pairs = [s for s in result.structural_results if s.left_id in name_ids and s.right_id in reading_ids]
    assert len(pairs) == 4
    assert all(
        p.state == (Structural.EXPLICIT_READING if reading_on_same_agent else Structural.DISTINCT_RESOURCES)
        for p in pairs
    )
    assert_unverified(result)


@pytest.mark.parametrize("variant", ["identical", "different-name", "partial"])
def test_p11_duplicate_agent_snapshot_is_ambiguous(variant):
    a = agent()
    b = (
        a
        if variant == "identical"
        else (agent(names=("Other",)) if variant == "different-name" else replace(a, completeness="partial"))
    )
    result = compare(synthetic(references=(RDFTerm("uri", a.uri),), agents=(a, b)))
    association = result.agent_associations[0]
    assert association.state == Association.UNVERIFIED
    assert association.reasons == ("agent_snapshot_ambiguous",)
    assert association.name_observation_ids == association.reading_observation_ids == ()
    assert result.unresolved
    assert_unverified(result)


@pytest.mark.parametrize(
    "scopes", [(), ("doc-a", "doc-a"), ("doc-a", "doc-b")], ids=["unknown", "same", "cross"]
)
def test_p12_p15_bnode_scope_never_creates_agent_identity(scopes):
    node = RDFTerm("bnode", "publisher")
    bundle = synthetic(references=(node,), series=(("Publisher",),))
    bundle = replace(bundle, series=(with_references(bundle.series[0], (node,)),))
    documents = tuple(zip((bundle.book.uri, bundle.series[0].uri), scopes, strict=True)) if scopes else ()
    result = compare(bundle, document_scopes=documents)
    assert tuple(a.document_scope for a in result.agent_associations) == (scopes or (None, None))
    for association in result.agent_associations:
        assert association.agent_reference == node
        assert association.state == Association.UNVERIFIED
        assert "bnode_snapshot_unsupported" in association.reasons
        assert ("bnode_document_scope_unknown" in association.reasons) is (not scopes)
    assert all(s.state == Structural.UNVERIFIED for s in result.structural_results)
    assert_unverified(result)


@pytest.mark.parametrize(
    "scopes",
    [((ID_NS + "M1", ""),), ((ID_NS + "M1", "a"), (ID_NS + "M1", "b")), ((ID_NS + "M1",),)],
)
def test_p12_invalid_or_ambiguous_document_scope_is_rejected(scopes):
    with pytest.raises(ValueError, match="[Dd]ocument scopes"):
        compare(document_scopes=scopes)


ACQUISITION_STATES = [State.COMPLETE, State.PARTIAL, State.UNAVAILABLE, State.NOT_REQUESTED, State.TRUNCATED]


@pytest.mark.parametrize("scope", ["book", "series", "agents", "ndl"])
@pytest.mark.parametrize("state", ACQUISITION_STATES)
def test_p10_p11_acquisition_scope_does_not_hide_incomplete_observations(scope, state):
    a = agent()
    bundle = synthetic(series=(("Publisher",),), references=(RDFTerm("uri", a.uri),), agents=(a,))
    context = complete(bundle, **({scope: state} if scope != "ndl" else {}))
    result = shadow.compare_publisher_observations(
        bundle,
        BookRecord("ndl", "", publishers=["Publisher"]),
        context,
        ndl_completeness=state if scope == "ndl" else State.COMPLETE,
    )
    assert primary_pair(result).state == Lexical.EXACT  # Observed lexical axis, not acquisition success.
    if scope == "agents":
        assert result.agent_associations[0].acquisition_state == state
        assert ("agent_acquisition_incomplete" in result.agent_associations[0].reasons) is (
            state != State.COMPLETE
        )
    else:
        group_id = "series:0" if scope == "series" else scope
        group = next(g for g in result.groups if g.group_id == group_id)
        assert group.completeness == group.acquisition_state == state
        comparisons = [p for p in result.group_comparisons if group_id in (p.left_group_id, p.right_group_id)]
        assert comparisons
        assert all(
            (p.left_completeness if p.left_group_id == group_id else p.right_completeness) == state
            for p in comparisons
        )
    assert result.unresolved is (state != State.COMPLETE)
    assert not result.conflict
    assert_unverified(result)


@pytest.mark.parametrize("scope", ["book", "series", "ndl"])
@pytest.mark.parametrize("state", ACQUISITION_STATES)
def test_p10_p18_acquisition_absence_is_not_empty_set_equality(scope, state):
    bundle = synthetic((), series=((),))
    context = complete(bundle, **({scope: state} if scope != "ndl" else {}))
    result = shadow.compare_publisher_observations(
        bundle,
        BookRecord("ndl", ""),
        context,
        ndl_completeness=state if scope == "ndl" else State.COMPLETE,
    )
    group_id = "series:0" if scope == "series" else scope
    reasons = {i.reason for i in result.unresolved_reasons if i.group_ids == (group_id,)}
    assert ("publisher_missing" in reasons) is (state == State.COMPLETE)
    assert ("publisher_unobserved" in reasons) is (state != State.COMPLETE)
    assert all(p.state == Lexical.UNCOMPARABLE for p in result.group_comparisons)
    assert result.unresolved and not result.conflict


@pytest.mark.parametrize("scope", ["book", "series", "agents"])
@pytest.mark.parametrize("state", [State.PARTIAL, State.TRUNCATED])
def test_p11_complete_declaration_cannot_override_partial_snapshot(scope, state):
    a = agent()
    bundle = synthetic(series=(("Publisher",),), references=(RDFTerm("uri", a.uri),), agents=(a,))
    if scope == "book":
        bundle = replace(bundle, book=replace(bundle.book, completeness=state.value))
    elif scope == "series":
        bundle = replace(bundle, series=(replace(bundle.series[0], completeness=state.value),))
    else:
        bundle = replace(bundle, agents=(replace(a, completeness=state.value),))
    result = compare(bundle)
    if scope == "agents":
        association = result.agent_associations[0]
        assert association.acquisition_state == State.COMPLETE and association.snapshot_state == state
        assert "agent_snapshot_incomplete" in association.reasons
    else:
        group = result.groups[0 if scope == "book" else 1]
        assert group.acquisition_state == State.COMPLETE
        assert group.snapshot_state == group.completeness == state
    assert result.unresolved


@pytest.mark.parametrize("scope", ["book", "series", "agents"])
@pytest.mark.parametrize("duplicate", [False, True])
def test_p11_resource_acquisition_overrides_and_duplicate_states(scope, duplicate):
    a = agent()
    bundle = synthetic(series=(("Publisher",),), references=(RDFTerm("uri", a.uri),), agents=(a,))
    uri = {"book": bundle.book.uri, "series": bundle.series[0].uri, "agents": a.uri}[scope]
    states = (State.COMPLETE, State.UNAVAILABLE) if duplicate else (State.UNAVAILABLE,)
    context = complete(bundle, resources=tuple(ResourceAcquisition(uri=uri, state=s) for s in states))
    result = compare(bundle, context=context)
    expected = State.PARTIAL if duplicate else State.UNAVAILABLE
    actual = (
        result.agent_associations[0].acquisition_state
        if scope == "agents"
        else result.groups[0 if scope == "book" else 1].completeness
    )
    assert actual == expected
    assert result.unresolved and result.acquisition.resources == context.resources


@pytest.mark.parametrize("part", ["subject", "predicate", "object", "field-only"])
@pytest.mark.parametrize("scope", ["book", "series"])
def test_p16_provenance_mismatch_retains_raw_without_invented_evidence(scope, part):
    bundle = synthetic(series=(("Publisher",),))
    record = bundle.book if scope == "book" else bundle.series[0]
    index = next(i for i, s in enumerate(record.statements) if s.predicate == SCHEMA_NS + "publisher")
    original = record.statements[index]
    statements = list(record.statements)
    if part == "field-only":
        statements.pop(index)
    else:
        value = {"subject": ID_NS + "M999", "predicate": SCHEMA_NS + "creator", "object": literal("Other")}[
            part
        ]
        statements[index] = replace(original, **{part: value})
    changed = replace(record, statements=tuple(statements))
    bundle = replace(bundle, **({"book": changed} if scope == "book" else {"series": (changed,)}))
    result = compare(bundle)
    group = result.groups[0 if scope == "book" else 1]
    observations = [o for o in result.observations if o.group_id == group.group_id]
    assert result.conflict and result.unresolved
    for observation in observations:
        assert observation.source.value == "madb" and observation.origin.value == scope
        assert observation.raw_value == observation.provenance.raw_value
        if observation.statement_index is None:
            assert observation.statement is None and not observation.provenance_verified
            assert observation.raw_layer == shadow.PublisherRawLayer.MODEL_FIELD
        else:
            assert observation.statement == changed.statements[observation.statement_index]
            assert observation.provenance.record_uri == observation.statement.subject
            assert observation.provenance.predicate_or_path == observation.statement.predicate
    suspect = [o for o in observations if not o.provenance_verified]
    assert suspect
    suspect_ids = {o.observation_id for o in suspect}
    assert all(
        p.state == Lexical.UNCOMPARABLE
        for p in result.lexical_results
        if p.left_id in suspect_ids or p.right_id in suspect_ids
    )


@pytest.mark.parametrize("part", ["subject", "type", "name-projection", "field-only"])
def test_p06_p15_agent_provenance_mismatch_disables_structural_promotion(part):
    a = agent()
    if part == "subject":
        a = replace(a, statements=tuple(replace(s, subject=ID_NS + "C9") for s in a.statements))
    elif part == "type":
        a = replace(a, statements=tuple(s for s in a.statements if s.predicate != RDF_NS + "type"))
    elif part == "name-projection":
        a = replace(a, names=(literal("Invented"),))
    else:
        a = replace(a, statements=tuple(s for s in a.statements if s.predicate != SCHEMA_NS + "name"))
    result = compare(synthetic(references=(RDFTerm("uri", a.uri),), agents=(a,)))
    association = result.agent_associations[0]
    assert association.state == Association.UNVERIFIED
    assert "agent_provenance_mismatch" in association.reasons
    assert all(s.state == Structural.UNVERIFIED for s in result.structural_results)
    assert all(
        not o.provenance_verified
        for o in result.observations
        if o.role in (Role.AGENT_NAME, Role.AGENT_READING)
    )
    assert result.conflict and result.unresolved


def test_p16_duplicate_occurrences_distinguish_book_parser_from_series_input():
    bundle = synthetic(("Publisher", "Publisher"), series=(("Publisher", "Publisher"),))
    result = compare(bundle, ("Publisher", "Publisher"))
    assert tuple(len(g.publisher_ids) for g in result.groups) == (1, 2, 2)
    assert tuple(o.statement_index for o in result.observations if o.origin.value == "series") == (2, 3)
    assert tuple(o.value_index for o in result.observations if o.origin.value == "ndl") == (0, 1)
    # A caller-supplied repeated Book statement is preserved; discarded parser rows cannot be recreated.
    book = bundle.book
    publisher = next(s for s in book.statements if s.predicate == SCHEMA_NS + "publisher")
    repeated = compare(replace(bundle, book=replace(book, statements=(*book.statements, publisher))))
    assert len(repeated.groups[0].publisher_ids) == 2
    assert all(p.state == Lexical.EXACT for p in repeated.group_comparisons)


def semantic_summary(result):
    """Ignore invocation-local IDs/order while retaining resource and occurrence evidence."""
    groups = {g.group_id: (g.origin, g.record_uri) for g in result.groups}
    return (
        Counter(
            (o.origin, o.record_uri, o.raw_value, o.statement, o.completeness) for o in result.observations
        ),
        Counter(
            (frozenset((groups[p.left_group_id], groups[p.right_group_id])), p.state)
            for p in result.group_comparisons
        ),
        Counter((i.reason, frozenset(groups[g] for g in i.group_ids)) for i in result.conflict_reasons),
        Counter((i.reason, frozenset(groups[g] for g in i.group_ids)) for i in result.unresolved_reasons),
        Counter(i.state for i in result.identity_assessments),
    )


def test_p08_p09_p16_series_permutation_preserves_meaning_and_every_occurrence():
    bundle = synthetic(("A", "B"), series=(("A", "B"), ("A", "A"), ("C",)))
    expected = semantic_summary(compare(bundle, ("A", "B")))
    for series in permutations(bundle.series):
        reordered = replace(
            bundle, series=tuple(replace(s, statements=tuple(reversed(s.statements))) for s in series)
        )
        result = compare(reordered, ("A", "B"))
        assert semantic_summary(result) == expected
        for observation in result.observations:
            if observation.origin.value == "series":
                source = next(s for s in reordered.series if s.uri == observation.record_uri)
                assert source.statements[observation.statement_index] == observation.statement


def test_p11_duplicate_series_snapshots_remain_unresolved():
    bundle = synthetic(series=(("Publisher",),))
    result = compare(replace(bundle, series=bundle.series * 2))
    assert len(result.groups) == 4 and len(result.observations) == 4
    issues = [i for i in result.unresolved_reasons if i.reason == "duplicate_series_snapshot"]
    assert {i.group_ids for i in issues} == {("series:0",), ("series:1",)}
    assert result.unresolved and not result.conflict


QUALIFIERS = [
    pytest.param(None, None, Lexical.EXACT, id="plain"),
    pytest.param("ja", None, Lexical.EXACT, id="ja"),
    pytest.param("JA", RDF_NS + "langString", Lexical.EXACT, id="case-langString"),
    pytest.param(None, XSD_NS + "string", Lexical.EXACT, id="xsd-string"),
    pytest.param("ja-hrkt", None, Lexical.UNCOMPARABLE, id="reading"),
    pytest.param("en", None, Lexical.UNCOMPARABLE, id="foreign"),
    pytest.param("??", None, Lexical.UNCOMPARABLE, id="unknown-tag"),
    pytest.param(None, RDF_NS + "langString", Lexical.UNCOMPARABLE, id="missing-language"),
    pytest.param(None, XSD_NS + "integer", Lexical.UNCOMPARABLE, id="non-string"),
    pytest.param("ja", XSD_NS + "integer", Lexical.UNCOMPARABLE, id="invalid-combination"),
]


@pytest.mark.parametrize("language,datatype,expected", QUALIFIERS)
def test_p17_qualifier_preserves_raw_and_never_promotes_unknown_terms(language, datatype, expected):
    term = RDFTerm("literal", "Publisher", language=language, datatype=datatype)
    # Deliberately hand-constructed snapshot: invalid combinations cannot come through the parser.
    bundle = synthetic()
    book = bundle.book
    bundle = replace(
        bundle,
        book=replace(
            book,
            publishers=(term,),
            statements=tuple(
                replace(s, object=term) if s.predicate == SCHEMA_NS + "publisher" else s
                for s in book.statements
            ),
        ),
    )
    result = compare(bundle)
    pair = primary_pair(result)
    assert pair.state == expected and pair.raw_equal is True
    observation = result.observations[0]
    assert observation.raw_value == observation.statement.object == term
    assert (observation.language, observation.datatype) == (language, datatype)
    assert result.unresolved is (expected == Lexical.UNCOMPARABLE)
    assert_unverified(result)


@pytest.mark.parametrize(
    "binding",
    [
        {"type": "literal", "value": "Publisher", "xml:lang": "ja", "datatype": XSD_NS + "integer"},
        {"type": "uri", "value": ID_NS + "C8", "xml:lang": "ja"},
        {"type": "bnode", "value": "b1", "datatype": XSD_NS + "string"},
    ],
)
def test_p17_qualifier_parser_protocol_error_stays_outside_shadow(binding):
    original = deepcopy(binding)
    with pytest.raises(MADBError) as error:
        parse_term(binding)
    assert error.value.kind == "protocol" and binding == original


def test_p17_unknown_language_and_invalid_term_have_distinct_diagnostic_reasons():
    """P1 P17: OTHER_LANGUAGE and INVALID must remain separately diagnosable."""
    foreign = compare(synthetic((parse_term({"type": "literal", "value": "Publisher", "xml:lang": "??"}),)))
    invalid = compare(
        synthetic((parse_term({"type": "literal", "value": "Publisher", "datatype": RDF_NS + "langString"}),))
    )
    assert primary_pair(foreign).state == primary_pair(invalid).state == Lexical.UNCOMPARABLE
    foreign_reasons = (primary_pair(foreign).reasons, tuple(i.reason for i in foreign.unresolved_reasons))
    invalid_reasons = (primary_pair(invalid).reasons, tuple(i.reason for i in invalid.unresolved_reasons))
    assert foreign_reasons != invalid_reasons, (
        "P17: OTHER_LANGUAGE and INVALID are collapsed into identical reasons"
    )


@pytest.mark.parametrize(
    "term,verified,expected_reason",
    [
        pytest.param(literal("Publisher", "??"), True, "publisher_other_language", id="other-language"),
        pytest.param(literal("", "??"), True, "publisher_other_language", id="unknown-tag-before-empty"),
        pytest.param(
            RDFTerm("literal", "Publisher", datatype=RDF_NS + "langString"),
            True,
            "publisher_invalid_term",
            id="invalid",
        ),
        pytest.param(literal(""), True, None, id="empty"),
        pytest.param(literal("　"), True, None, id="whitespace"),
        pytest.param(literal("Publisher", "ja-hrkt"), True, None, id="reading"),
        pytest.param(RDFTerm("uri", "https://example.invalid/publisher"), True, None, id="unsupported-uri"),
        pytest.param(
            RDFTerm("literal", "Publisher", datatype=XSD_NS + "integer"),
            True,
            None,
            id="unsupported-datatype",
        ),
        pytest.param(literal("Publisher", "??"), False, None, id="unverified-other-language"),
        pytest.param(
            RDFTerm("literal", "Publisher", datatype=RDF_NS + "langString"),
            False,
            None,
            id="unverified-invalid",
        ),
    ],
)
def test_p17_cause_specific_group_reasons_do_not_reclassify_other_uncomparable_values(
    term, verified, expected_reason
):
    bundle = synthetic()
    book = bundle.book
    statements = (
        tuple(
            replace(s, object=term) if s.predicate == SCHEMA_NS + "publisher" else s for s in book.statements
        )
        if verified
        else book.statements
    )
    bundle = replace(bundle, book=replace(book, publishers=(term,), statements=statements))
    original = deepcopy(bundle)
    result = compare(bundle)
    observation = next(o for o in result.observations if o.raw_value == term)
    pair = next(p for p in result.lexical_results if p.left_id == observation.observation_id)
    assert pair.state == Lexical.UNCOMPARABLE and pair.left_key is None
    assert pair.reasons[0] == "non_display_empty_or_unverified"
    assert pair.rules == ("unicode_nfc", "outer_str_strip")
    assert observation.provenance_verified is verified
    causes = tuple(
        issue
        for issue in result.unresolved_reasons
        if issue.reason in ("publisher_other_language", "publisher_invalid_term")
    )
    assert tuple(issue.reason for issue in causes) == (() if expected_reason is None else (expected_reason,))
    if causes:
        assert causes[0].group_ids == ("book",)
        assert causes[0].observation_ids == (observation.observation_id,)
    assert any(
        issue.reason == "publisher_uncomparable" and observation.observation_id in issue.observation_ids
        for issue in result.unresolved_reasons
    )
    assert result.unresolved
    assert_unverified(result)
    assert bundle == original


@pytest.mark.parametrize("state", [Identity.VERIFIED_SAME, Identity.VERIFIED_DIFFERENT])
def test_p07_n4_both_verified_identity_states_are_rejected(state):
    result = compare()
    with pytest.raises(ValueError, match="authority"):
        replace(result.identity_assessments[0], state=state)


def frozen_models(value):
    if is_dataclass(value):
        yield value
        for field in fields(value):
            yield from frozen_models(getattr(value, field.name))
    elif isinstance(value, tuple):
        for item in value:
            yield from frozen_models(item)


def test_p01_p06_all_nested_diagnostic_models_reject_mutation():
    a = agent()
    result = compare(synthetic(("Other",), references=(RDFTerm("uri", a.uri),), agents=(a,)))
    models = {type(m): m for m in frozen_models(result) if type(m).__module__ == shadow.__name__}
    assert {t.__name__ for t in models} == {
        "PublisherComparisonDiagnostic",
        "PublisherComparisonPolicy",
        "PublisherObservation",
        "PublisherAgentAssociation",
        "PublisherLexicalResult",
        "PublisherStructuralResult",
        "PublisherIdentityAssessment",
        "PublisherGroup",
        "PublisherGroupComparison",
        "PublisherIssue",
    }
    for model in models.values():
        field = fields(model)[0].name
        with pytest.raises(FrozenInstanceError):
            setattr(model, field, getattr(model, field))
        for field in fields(model):
            if isinstance(getattr(model, field.name), tuple):
                with pytest.raises(ValueError, match="immutable"):
                    replace(model, **{field.name: []})


@pytest.mark.parametrize("container", [[], {}, set()], ids=["list", "dict", "set"])
@pytest.mark.parametrize("location", ["bundle", "term", "scope"])
def test_p01_p16_mutable_inputs_are_rejected_at_nested_boundaries(container, location):
    bundle = synthetic()
    scopes = ()
    if location == "bundle":
        bundle = replace(bundle, series=container)
    elif location == "term":
        bundle = replace(
            bundle, book=replace(bundle.book, publishers=(replace(literal("Publisher"), value=container),))
        )
    else:
        scopes = ((bundle.book.uri, container),)
    with pytest.raises(ValueError, match="immutable"):
        compare(bundle, document_scopes=scopes)


def test_p06_ndl_snapshot_does_not_invent_xml_readings_or_resource_identity():
    record = BookRecord("ndl", "", publishers=["Publisher"], url="")
    snapshot = NDLInputSnapshot.from_record(record)
    record.raw_xml = (
        '<foaf:Agent rdf:about="invented"><dcndl:transcription>ヨミ</dcndl:transcription></foaf:Agent>'
    )
    record.publishers[:] = ["Changed"]
    bundle = synthetic()
    result = shadow.compare_publisher_observations(
        bundle, snapshot, complete(bundle), ndl_completeness=State.COMPLETE
    )
    observation = next(o for o in result.observations if o.origin.value == "ndl")
    assert observation.raw_value == "Publisher" and observation.value_index == 0
    assert observation.record_uri is observation.provenance.record_uri is None
    assert observation.statement is observation.statement_index is observation.node_index is None
    assert observation.language is observation.datatype is observation.document_scope is None
    assert result.agent_associations == ()
    assert_unverified(result)


@pytest.mark.parametrize("gate", ["edition", "medium", "date", "authority", "existing"])
def test_p19_legacy_gate_cannot_be_released_by_publisher_match(gate):
    bundle = imprint_bundle()
    ndl = ndl_synthetic()
    context = acquired(bundle, medium="digital" if gate == "medium" else "paper")
    changes = {"edition": {"editions": ("Other edition",)}, "date": {"publication_dates": ("2023-09-06",)}}
    evidence = () if gate == "authority" else (authority(bundle, **changes.get(gate, {})),)
    existing = "　" if gate == "existing" else None
    before = evaluate(bundle, ndl=ndl, context=context, evidence=evidence, existing=existing)
    result = shadow.compare_publisher_observations(
        bundle, ndl, context, legacy=before.comparison.publisher, ndl_completeness=State.COMPLETE
    )
    assert primary_pair(result).state == Lexical.EXACT
    assert result.legacy == before.comparison.publisher
    assert before == evaluate(bundle, ndl=ndl, context=context, evidence=evidence, existing=existing)
    assert before.state.value == (
        "skip" if gate == "existing" else "hold" if gate == "authority" else "reject"
    )
    assert before.selected_candidate is None
    reason = (
        "existing_imprint"
        if gate == "existing"
        else "semantic_unverified"
        if gate == "authority"
        else "context_conflict"
    )
    assert reason in {r.value for r in before.reasons}


@pytest.mark.parametrize("decision", ["eligible", "hold", "skip", "reject"])
@pytest.mark.parametrize("shadow_state", ["conflict", "unresolved"])
def test_p19_p20_legacy_decision_is_independent_of_shadow_issues(decision, shadow_state):
    # Authority here is an existing test-only Imprint contract, never Publisher N4 evidence.
    bundle = imprint_bundle(("Label", "Other") if decision == "hold" else ("Label",))
    # Legacy compares direct schema:publisher, not dcterms:publisher references.
    # Both evaluators receive the same snapshot, including these shadow-only issues.
    if shadow_state == "conflict":
        bundle = replace(bundle, book=replace(bundle.book, publisher_references=(literal("Invented"),)))
    else:
        bundle = replace(bundle, book=with_references(bundle.book, (RDFTerm("uri", ID_NS + "C8"),)))
    ndl = ndl_synthetic()
    context = acquired(bundle)
    evidence = (
        ()
        if decision == "hold"
        else (authority(bundle, medium="digital" if decision == "reject" else "paper"),)
    )
    context = replace(context, medium="paper")
    kwargs = dict(
        ndl=ndl, context=context, evidence=evidence, existing="Preserved" if decision == "skip" else None
    )
    before = evaluate(bundle, **kwargs)
    assert before.state.value == decision
    if decision == "hold":
        assert "multiple_displays" in {r.value for r in before.reasons}
        assert "semantic_unverified" in {r.value for r in before.reasons}
    result = shadow.compare_publisher_observations(bundle, ndl, context, legacy=before.comparison.publisher)
    assert result.conflict is (shadow_state == "conflict")
    assert result.unresolved
    assert not result.legacy.conflict and not result.legacy.unresolved
    assert result.legacy == before.comparison.publisher
    assert evaluate(bundle, **kwargs) == before


def test_p20_report_read_only_and_metadata_stay_unchanged():
    bundle = imprint_bundle(("Label", "Other"))
    ndl = ndl_synthetic()
    evidence = evidence_for(bundle, ndl)
    report = imprint_report.describe_imprint_evidence(evidence)
    encoded = imprint_report.report_to_json_data(report)
    metadata = to_metadata(ndl)
    before = deepcopy((bundle, ndl, evidence, report, metadata))
    result = shadow.compare_publisher_observations(
        bundle,
        evidence.acquisition_context.ndl_input,
        evidence.acquisition_context.books[0].context,
        legacy=report.books[0].evaluation.comparison.publisher,
        ndl_completeness=State.COMPLETE,
    )
    assert primary_pair(result).state == Lexical.EXACT
    assert (bundle, ndl, evidence, report, metadata) == before
    assert imprint_report.report_to_json_data(imprint_report.describe_imprint_evidence(evidence)) == encoded
    assert report.operation == "READ_ONLY"
    assert not report.apply_allowed and not report.writes_performed
    assert report.books[0].evaluation.state.value == "hold"


def test_p19_talker_cli_report_and_linkage_entrypoints_are_not_called(monkeypatch):
    # Complements P2's network/file/cache/clock/metadata/evaluator guards.
    bundle = synthetic()
    snapshot = NDLInputSnapshot.from_record(BookRecord("ndl", "", publishers=["Publisher"]))
    context = complete(bundle)

    def forbidden(*args, **kwargs):
        pytest.fail("Shadow must not enter Talker, CLI, report or acquisition/linkage flows")

    with monkeypatch.context() as guard:
        for target, name in (
            (JapaneseBooksTalker, "__init__"),
            (JapaneseBooksTalker, "fetch_comic_data"),
            (JapaneseBooksTalker, "search_for_series"),
            (imprint_diagnostics, "main"),
            (imprint_diagnostics, "acquire_diagnostic_evidence"),
            (imprint_report, "describe_imprint_evidence"),
            (imprint_report, "report_to_json_data"),
            (linkage, "acquire_linked_record_evidence"),
            (linkage, "compare_candidates"),
        ):
            guard.setattr(target, name, forbidden)
        result = shadow.compare_publisher_observations(bundle, snapshot, context)
    assert result.legacy is None


@pytest.mark.parametrize("size", [1, 8, 32])
def test_p08_p16_scaling_keeps_all_cross_group_observation_pairs(size):
    values = tuple(f"Publisher {i}" for i in range(size))
    result = compare(synthetic(values, series=(values, values)), values)
    assert len(result.observations) == 4 * size
    assert len(result.group_comparisons) == 6
    assert (
        len(result.lexical_results)
        == len(result.structural_results)
        == len(result.identity_assessments)
        == 6 * size * size
    )
    assert len({(p.left_id, p.right_id) for p in result.lexical_results}) == 6 * size * size
    assert all(p.state == Lexical.EXACT for p in result.group_comparisons)
