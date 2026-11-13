"""Pure Publisher shadow diagnostics; never an eligibility or metadata policy.

N0/N1 describe strings, explicit Publisher edges describe RDF associations, and
identity remains unverified. Nothing imports this module into the existing flow.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, fields, is_dataclass, replace
from enum import Enum
from itertools import combinations, product

from comictagger_jp_talker.acquisition import AcquisitionContext, AcquisitionState
from comictagger_jp_talker.imprint_candidates import ContextComparison, ImprintTermRole, _role
from comictagger_jp_talker.linked_acquisition import NDLInputSnapshot
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.provenance import EvidenceSource, FieldEvidence
from comictagger_jp_talker.sources.madb_models import MADBRecordBundle, MADBStatement, RDFTerm
from comictagger_jp_talker.sources.madb_queries import CLASS_NS, DCTERMS_NS, RDF_NS, SCHEMA_NS, resource_uri

POLICY_VERSION = "publisher-shadow-p2-v1"
NORMALIZATION_VERSION = "nfc-strip-v1"


class PublisherOrigin(str, Enum):
    BOOK = "book"
    SERIES = "series"
    NDL = "ndl"


class PublisherRawLayer(str, Enum):
    RDF_STATEMENT = "rdf_statement"
    MODEL_FIELD = "model_field"
    PARSED_VALUE = "parsed_value"


class PublisherRole(str, Enum):
    PUBLISHER = "publisher"
    REFERENCE = "reference"
    AGENT_NAME = "agent_name"
    AGENT_READING = "agent_reading"


class PublisherLexicalState(str, Enum):
    EXACT = "exact"
    NORMALIZED_EQUAL = "normalized_equal"
    DIFFERENT = "different"
    UNCOMPARABLE = "uncomparable"


class PublisherStructuralState(str, Enum):
    SAME_AGENT = "same_agent"
    EXPLICIT_READING = "explicit_reading"
    DISTINCT_RESOURCES = "distinct_resources"
    UNVERIFIED = "unverified"


class PublisherAssociationState(str, Enum):
    EXPLICIT = "explicit"
    UNVERIFIED = "unverified"


class PublisherIdentityState(str, Enum):
    VERIFIED_SAME = "verified_same"
    VERIFIED_DIFFERENT = "verified_different"
    UNVERIFIED = "unverified"


def _immutable(value) -> None:
    """Reject mutable containers even inside hand-constructed frozen inputs."""
    if value is None or type(value) in (str, int, bool) or isinstance(value, Enum):
        return
    if type(value) is tuple:
        for item in value:
            _immutable(item)
        return
    if is_dataclass(value) and not isinstance(value, type) and value.__dataclass_params__.frozen:
        for field in fields(value):
            _immutable(getattr(value, field.name))
        return
    raise ValueError("Publisher diagnostics require immutable values")


class _FrozenModel:
    def __post_init__(self) -> None:
        _immutable(self)


@dataclass(frozen=True, kw_only=True)
class PublisherComparisonPolicy(_FrozenModel):
    version: str = POLICY_VERSION
    normalization_version: str = NORMALIZATION_VERSION

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.version != POLICY_VERSION or self.normalization_version != NORMALIZATION_VERSION:
            raise ValueError("Unsupported Publisher comparison policy")


@dataclass(frozen=True, kw_only=True)
class PublisherObservation(_FrozenModel):
    observation_id: str
    group_id: str
    source: EvidenceSource
    origin: PublisherOrigin
    record_id: str
    record_uri: str | None
    raw_value: str | RDFTerm
    role: PublisherRole
    provenance: FieldEvidence
    raw_layer: PublisherRawLayer
    scope: str
    completeness: AcquisitionState
    statement: MADBStatement | None = None
    statement_index: int | None = None
    value_index: int | None = None
    # Parsed NDL values have list positions, never invented XML node positions.
    node_index: int | None = None
    document_scope: str | None = None
    provenance_verified: bool = True

    @property
    def kind(self) -> str | None:
        return self.raw_value.kind if isinstance(self.raw_value, RDFTerm) else None

    @property
    def language(self) -> str | None:
        return self.raw_value.language if isinstance(self.raw_value, RDFTerm) else None

    @property
    def datatype(self) -> str | None:
        return self.raw_value.datatype if isinstance(self.raw_value, RDFTerm) else None

    @property
    def raw_string(self) -> str | None:
        if isinstance(self.raw_value, str):
            return self.raw_value
        return self.raw_value.value if self.raw_value.kind == "literal" else None


@dataclass(frozen=True, kw_only=True)
class PublisherAgentAssociation(_FrozenModel):
    association_id: str
    edge_observation_id: str
    record_uri: str
    agent_reference: RDFTerm
    document_scope: str | None
    name_observation_ids: tuple[str, ...]
    reading_observation_ids: tuple[str, ...]
    state: PublisherAssociationState
    acquisition_state: AcquisitionState
    snapshot_state: AcquisitionState | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class PublisherLexicalResult(_FrozenModel):
    left_id: str
    right_id: str
    raw_equal: bool | None
    left_key: str | None
    right_key: str | None
    state: PublisherLexicalState
    rules: tuple[str, ...]
    normalization_version: str
    reasons: tuple[str, ...]
    # Reserved for diagnostic-only N2 rules; P2 runs none of those rules.
    notation_notes: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class PublisherStructuralResult(_FrozenModel):
    left_id: str
    right_id: str
    state: PublisherStructuralState
    association_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class PublisherIdentityAssessment(_FrozenModel):
    left_id: str
    right_id: str
    state: PublisherIdentityState = PublisherIdentityState.UNVERIFIED
    reasons: tuple[str, ...] = ("authority_not_supplied",)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.state != PublisherIdentityState.UNVERIFIED:
            raise ValueError("P2 has no verified Publisher authority input path")


@dataclass(frozen=True, kw_only=True)
class PublisherGroup(_FrozenModel):
    group_id: str
    origin: PublisherOrigin
    record_id: str
    record_uri: str | None
    related_to_book: bool
    observation_ids: tuple[str, ...]
    publisher_ids: tuple[str, ...]
    reference_ids: tuple[str, ...]
    keys: tuple[str, ...]
    acquisition_state: AcquisitionState
    snapshot_state: AcquisitionState | None
    completeness: AcquisitionState


@dataclass(frozen=True, kw_only=True)
class PublisherGroupComparison(_FrozenModel):
    left_group_id: str
    right_group_id: str
    left_keys: tuple[str, ...]
    right_keys: tuple[str, ...]
    state: PublisherLexicalState
    left_completeness: AcquisitionState
    right_completeness: AcquisitionState


@dataclass(frozen=True, kw_only=True)
class PublisherIssue(_FrozenModel):
    reason: str
    group_ids: tuple[str, ...]
    observation_ids: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class PublisherComparisonDiagnostic(_FrozenModel):
    observations: tuple[PublisherObservation, ...]
    agent_associations: tuple[PublisherAgentAssociation, ...]
    lexical_results: tuple[PublisherLexicalResult, ...]
    structural_results: tuple[PublisherStructuralResult, ...]
    identity_assessments: tuple[PublisherIdentityAssessment, ...]
    groups: tuple[PublisherGroup, ...]
    group_comparisons: tuple[PublisherGroupComparison, ...]
    acquisition: AcquisitionContext
    bundle_completeness: AcquisitionState
    retrieval_scope: str
    ndl_snapshot: NDLInputSnapshot
    conflict_reasons: tuple[PublisherIssue, ...]
    unresolved_reasons: tuple[PublisherIssue, ...]
    legacy: ContextComparison | None
    policy: PublisherComparisonPolicy

    @property
    def conflict(self) -> bool:
        return bool(self.conflict_reasons)

    @property
    def unresolved(self) -> bool:
        return bool(self.unresolved_reasons)


def _key(observation: PublisherObservation) -> str | None:
    if not observation.provenance_verified or observation.role not in (
        PublisherRole.PUBLISHER,
        PublisherRole.AGENT_NAME,
    ):
        return None
    raw = observation.raw_value
    if isinstance(raw, RDFTerm) and _role(raw) != ImprintTermRole.DISPLAY:
        return None
    value = observation.raw_string
    if value is None:
        return None
    return unicodedata.normalize("NFC", value).strip() or None


def _lexical(left, right, policy) -> PublisherLexicalResult:
    a, b = left.raw_string, right.raw_string
    ka, kb = _key(left), _key(right)
    rules = ("unicode_nfc", "outer_str_strip")
    if ka is None or kb is None:
        state, reasons = PublisherLexicalState.UNCOMPARABLE, ("non_display_empty_or_unverified",)
    elif a == b:
        state, reasons = PublisherLexicalState.EXACT, ()
    elif ka == kb:
        state, reasons = PublisherLexicalState.NORMALIZED_EQUAL, ("n1_only_equal",)
    else:
        state, reasons = PublisherLexicalState.DIFFERENT, ("lexical_difference",)
    changes = []
    for side, value in (("left", a), ("right", b)):
        if value is not None:
            nfc = unicodedata.normalize("NFC", value)
            if nfc != value:
                changes.append(side + "_nfc_changed")
            if nfc.strip() != nfc:
                changes.append(side + "_outer_whitespace")
    return PublisherLexicalResult(
        left_id=left.observation_id,
        right_id=right.observation_id,
        raw_equal=a == b if a is not None and b is not None else None,
        left_key=ka,
        right_key=kb,
        state=state,
        rules=rules,
        normalization_version=policy.normalization_version,
        reasons=(*reasons, *changes),
    )


def _effective(declared, snapshot):
    return snapshot if declared == AcquisitionState.COMPLETE and snapshot is not None else declared


class _Collector:
    """Invocation-local construction only; the returned graph is immutable."""

    def __init__(self, bundle, acquisition, document_scopes):
        self.bundle = bundle
        self.acquisition = acquisition
        self.document_scopes = dict(document_scopes)
        self.observations = []
        self.associations = []
        self.conflicts = []
        self.unresolved = []

    def issue(self, reason, groups, observations=(), *, conflict=False):
        target = self.conflicts if conflict else self.unresolved
        target.append(PublisherIssue(reason=reason, group_ids=groups, observation_ids=observations))

    def declared(self, uri, fallback):
        states = tuple(r.state for r in self.acquisition.resources if r.uri == uri)
        if len(states) > 1:
            return AcquisitionState.PARTIAL
        return _effective(fallback, states[0] if states else None)

    def observe(
        self,
        group_id,
        origin,
        record,
        statement,
        index,
        role,
        state,
        *,
        value_index=None,
        expected_subject=None,
        provenance_verified=True,
    ):
        raw = statement.object
        observation_id = f"{group_id}:observation:{len(self.observations)}"
        verified = (
            index is not None
            and statement.subject == (expected_subject if expected_subject is not None else record.uri)
            and provenance_verified
        )
        observation = PublisherObservation(
            observation_id=observation_id,
            group_id=group_id,
            source=EvidenceSource.MADB,
            origin=origin,
            record_id=record.id,
            record_uri=record.uri,
            raw_value=raw,
            role=role,
            provenance=FieldEvidence(
                EvidenceSource.MADB,
                "publishers",
                raw.value if raw.kind == "literal" else None,
                raw,
                statement.subject.rsplit("/", 1)[-1],
                statement.subject,
                statement.predicate,
            ),
            raw_layer=PublisherRawLayer.RDF_STATEMENT if index is not None else PublisherRawLayer.MODEL_FIELD,
            scope=self.bundle.retrieval_scope,
            completeness=state,
            statement=statement if index is not None else None,
            statement_index=index,
            value_index=value_index,
            document_scope=self.document_scopes.get(statement.subject),
            provenance_verified=verified,
        )
        self.observations.append(observation)
        if not verified:
            self.issue("provenance_mismatch", (group_id,), (observation_id,), conflict=True)
            self.issue("provenance_unverified", (group_id,), (observation_id,))
        return observation

    def associate(self, edge, parent):
        raw = edge.raw_value
        names, readings, reasons = [], [], []
        snapshot_state = None
        state = PublisherAssociationState.UNVERIFIED
        declared = self.declared(raw.value, self.acquisition.agents)
        if not edge.provenance_verified or _role(raw) == ImprintTermRole.INVALID:
            reasons.append("publisher_edge_unverified")
        elif raw.kind == "literal":
            reasons.append("literal_reference_unverified")
        elif raw.kind == "bnode":
            # No MADBAgentRecord bnode decoder exists. Keep caller-supplied scope.
            reasons.append("bnode_snapshot_unsupported")
            if edge.document_scope is None:
                reasons.append("bnode_document_scope_unknown")
        elif raw.kind == "uri":
            try:
                if resource_uri(raw.value, "agent") != raw.value:
                    raise ValueError("Publisher Agent references must be absolute URIs")
            except ValueError:
                reasons.append("unsupported_agent_uri")
            else:
                agents = tuple(a for a in self.bundle.agents if a.uri == raw.value)
                if len(agents) != 1:
                    reasons.append("agent_snapshot_missing" if not agents else "agent_snapshot_ambiguous")
                else:
                    agent = agents[0]
                    snapshot_state = AcquisitionState(agent.completeness)
                    raw_names = tuple(s.object for s in agent.statements if s.predicate == SCHEMA_NS + "name")
                    consistent = (
                        set(raw_names) == set(agent.names)
                        and all(s.subject == agent.uri for s in agent.statements)
                        and any(
                            s.predicate == RDF_NS + "type" and s.object == RDFTerm("uri", CLASS_NS + "Agent")
                            for s in agent.statements
                        )
                    )
                    if not consistent:
                        reasons.append("agent_provenance_mismatch")
                        self.issue("agent_provenance_mismatch", (edge.group_id,), conflict=True)
                    for i, statement in enumerate(agent.statements):
                        if statement.predicate != SCHEMA_NS + "name":
                            continue
                        role = (
                            PublisherRole.AGENT_READING
                            if _role(statement.object) == ImprintTermRole.READING
                            else PublisherRole.AGENT_NAME
                        )
                        if _role(statement.object) not in (ImprintTermRole.DISPLAY, ImprintTermRole.READING):
                            reasons.append("agent_name_uncomparable")
                        # The parent remains the Book/Series; provenance identifies the Agent.
                        observation = self.observe(
                            edge.group_id,
                            edge.origin,
                            parent,
                            statement,
                            i,
                            role,
                            _effective(declared, snapshot_state),
                            expected_subject=agent.uri,
                            provenance_verified=consistent,
                        )
                        (readings if role == PublisherRole.AGENT_READING else names).append(
                            observation.observation_id
                        )
                    for i, raw_name in enumerate(agent.names):
                        if raw_name in raw_names:
                            continue
                        role = (
                            PublisherRole.AGENT_READING
                            if _role(raw_name) == ImprintTermRole.READING
                            else PublisherRole.AGENT_NAME
                        )
                        observation = self.observe(
                            edge.group_id,
                            edge.origin,
                            parent,
                            MADBStatement(agent.uri, SCHEMA_NS + "name", raw_name),
                            None,
                            role,
                            _effective(declared, snapshot_state),
                            value_index=i,
                            expected_subject=agent.uri,
                        )
                        (readings if role == PublisherRole.AGENT_READING else names).append(
                            observation.observation_id
                        )
                    if consistent:
                        state = PublisherAssociationState.EXPLICIT
        else:
            reasons.append("unsupported_agent_reference")
        if raw.kind in ("uri", "bnode") and declared != AcquisitionState.COMPLETE:
            reasons.append("agent_acquisition_incomplete")
        if snapshot_state not in (None, AcquisitionState.COMPLETE):
            reasons.append("agent_snapshot_incomplete")
        for reason in reasons:
            self.issue(reason, (edge.group_id,), (edge.observation_id,))
        self.associations.append(
            PublisherAgentAssociation(
                association_id=f"association:{len(self.associations)}",
                edge_observation_id=edge.observation_id,
                record_uri=parent.uri,
                agent_reference=raw,
                document_scope=edge.document_scope,
                name_observation_ids=tuple(names),
                reading_observation_ids=tuple(readings),
                state=state,
                acquisition_state=declared,
                snapshot_state=snapshot_state,
                reasons=tuple(reasons),
            )
        )

    def record(self, record, origin, group_id, declared, related):
        start = len(self.observations)
        snapshot = AcquisitionState(record.completeness)
        completeness = _effective(declared, snapshot)
        publishers, references = [], []
        for predicate, field, role, target in (
            (SCHEMA_NS + "publisher", "publishers", PublisherRole.PUBLISHER, publishers),
            (DCTERMS_NS + "publisher", "publisher_references", PublisherRole.REFERENCE, references),
        ):
            statements = tuple((i, s) for i, s in enumerate(record.statements) if s.predicate == predicate)
            projected = tuple(getattr(record, field))
            for i, statement in statements:
                observation = self.observe(group_id, origin, record, statement, i, role, completeness)
                target.append(observation.observation_id)
                if role == PublisherRole.REFERENCE or statement.object.kind in ("uri", "bnode"):
                    self.associate(observation, record)
            for i, raw in enumerate(projected):
                if raw not in tuple(s.object for _, s in statements):
                    observation = self.observe(
                        group_id,
                        origin,
                        record,
                        MADBStatement(record.uri, predicate, raw),
                        None,
                        role,
                        completeness,
                        value_index=i,
                    )
                    target.append(observation.observation_id)
            if set(projected) != {s.object for _, s in statements}:
                self.issue("field_projection_mismatch", (group_id,), conflict=True)
        return self.group(
            group_id,
            origin,
            record.id,
            record.uri,
            related,
            tuple(o.observation_id for o in self.observations[start:]),
            tuple(publishers),
            tuple(references),
            declared,
            snapshot,
        )

    def group(
        self, group_id, origin, record_id, uri, related, ids, publishers, references, declared, snapshot
    ):
        observed = {o.observation_id: o for o in self.observations}
        keys = tuple(sorted({key for oid in publishers if (key := _key(observed[oid])) is not None}))
        completeness = _effective(declared, snapshot)
        if (
            origin == PublisherOrigin.SERIES
            and snapshot is None
            and completeness == AcquisitionState.COMPLETE
        ):
            completeness = AcquisitionState.UNAVAILABLE
        if related:
            if completeness != AcquisitionState.COMPLETE:
                self.issue("acquisition_incomplete", (group_id,))
            if not keys:
                self.issue(
                    "publisher_missing"
                    if completeness == AcquisitionState.COMPLETE
                    else "publisher_unobserved",
                    (group_id,),
                )
            if len(keys) > 1:
                self.issue("multiple_publisher_values", (group_id,), publishers)
            unsupported = tuple(oid for oid in publishers if _key(observed[oid]) is None)
            if unsupported:
                self.issue("publisher_uncomparable", (group_id,), unsupported)
        return PublisherGroup(
            group_id=group_id,
            origin=origin,
            record_id=record_id,
            record_uri=uri,
            related_to_book=related,
            observation_ids=ids,
            publisher_ids=publishers,
            reference_ids=references,
            keys=keys,
            acquisition_state=declared,
            snapshot_state=snapshot,
            completeness=completeness,
        )


def _structural(left_id, right_id, associations, observations):
    def containing(oid):
        return tuple(
            a
            for a in associations
            if a.state == PublisherAssociationState.EXPLICIT
            and oid
            in (
                a.edge_observation_id,
                *a.name_observation_ids,
                *a.reading_observation_ids,
            )
        )

    left, right = containing(left_id), containing(right_id)
    common = tuple(a for a in left if a in right)
    if common:
        reading = any(
            left_id in a.name_observation_ids
            and right_id in a.reading_observation_ids
            and _key(observations[left_id]) is not None
            or right_id in a.name_observation_ids
            and left_id in a.reading_observation_ids
            and _key(observations[right_id]) is not None
            for a in common
        )
        state = PublisherStructuralState.EXPLICIT_READING if reading else PublisherStructuralState.SAME_AGENT
        used = common
    elif left and right:
        same = tuple(a for a in left if any(a.agent_reference == b.agent_reference for b in right))
        state = PublisherStructuralState.SAME_AGENT if same else PublisherStructuralState.DISTINCT_RESOURCES
        used = (*left, *right)
    else:
        state, used = PublisherStructuralState.UNVERIFIED, ()
    return PublisherStructuralResult(
        left_id=left_id,
        right_id=right_id,
        state=state,
        association_ids=tuple(dict.fromkeys(a.association_id for a in used)),
        reasons=("explicit_publisher_edge",) if used else ("no_verified_agent_association",),
    )


def compare_publisher_observations(
    bundle: MADBRecordBundle,
    ndl_snapshot: NDLInputSnapshot | BookRecord,
    acquisition: AcquisitionContext,
    policy: PublisherComparisonPolicy | None = None,
    *,
    legacy: ContextComparison | None = None,
    ndl_completeness: AcquisitionState = AcquisitionState.NOT_REQUESTED,
    document_scopes: tuple[tuple[str, str], ...] = (),
) -> PublisherComparisonDiagnostic:
    """Compare supplied snapshots only. No XML decoding, acquisition or adoption.

    document_scopes is an explicit (subject URI, RDF document scope) assertion;
    bnodes are retained but cannot be resolved with the current Agent model.
    Missing legacy input means not supplied, never an invented legacy verdict.
    """
    ndl = NDLInputSnapshot.from_record(ndl_snapshot) if isinstance(ndl_snapshot, BookRecord) else ndl_snapshot
    policy = policy if policy is not None else PublisherComparisonPolicy()
    for value in (bundle, ndl, acquisition, policy, document_scopes, legacy):
        _immutable(value)
    if not isinstance(ndl, NDLInputSnapshot) or not isinstance(policy, PublisherComparisonPolicy):
        raise ValueError("Invalid Publisher comparison snapshot/policy")
    if not isinstance(ndl_completeness, AcquisitionState):
        raise ValueError("Invalid NDL acquisition state")
    if any(len(pair) != 2 or any(not isinstance(v, str) or not v for v in pair) for pair in document_scopes):
        raise ValueError("Invalid document scopes")
    if len({uri for uri, _ in document_scopes}) != len(document_scopes):
        raise ValueError("Ambiguous document scopes")
    if legacy is not None and (not isinstance(legacy, ContextComparison) or legacy.field != "publishers"):
        raise ValueError("Expected a legacy Publisher comparison")
    legacy_snapshot = (
        replace(legacy, book=tuple(legacy.book), series=tuple(legacy.series), ndl=tuple(legacy.ndl))
        if legacy is not None
        else None
    )
    collector = _Collector(bundle, acquisition, document_scopes)
    book = bundle.book
    groups = [
        collector.record(
            book, PublisherOrigin.BOOK, "book", collector.declared(book.uri, acquisition.book), True
        )
    ]
    relations = tuple(s for s in book.statements if s.predicate == SCHEMA_NS + "isPartOf")
    explicit = {s.object.value for s in relations if s.subject == book.uri and s.object.kind == "uri"}
    expected = set(book.series_uris) | explicit
    if explicit != set(book.series_uris) or any(
        s.subject != book.uri or s.object.kind != "uri" for s in relations
    ):
        collector.issue("series_relation_provenance_mismatch", ("book",), conflict=True)
        collector.issue("series_relation_unverified", ("book",))
    if acquisition.discovery != AcquisitionState.COMPLETE:
        collector.issue("discovery_incomplete", ("book",))
    required_relation_state = AcquisitionState.COMPLETE if expected else AcquisitionState.NOT_RELATED
    if acquisition.relations != required_relation_state or acquisition.series != required_relation_state:
        collector.issue("series_scope_unverified", ("book",))
    for i, series in enumerate(bundle.series):
        related = series.uri in explicit
        group_id = f"series:{i}"
        groups.append(
            collector.record(
                series,
                PublisherOrigin.SERIES,
                group_id,
                collector.declared(series.uri, acquisition.series),
                related,
            )
        )
        if not related:
            collector.issue("unrelated_series", (group_id,))
        if sum(s.uri == series.uri for s in bundle.series) > 1:
            collector.issue("duplicate_series_snapshot", (group_id,))
    for i, uri in enumerate(sorted(expected - {s.uri for s in bundle.series})):
        state = collector.declared(uri, acquisition.series)
        groups.append(
            collector.group(
                f"missing_series:{i}",
                PublisherOrigin.SERIES,
                uri.rsplit("/", 1)[-1],
                uri,
                uri in explicit,
                (),
                (),
                (),
                state,
                None,
            )
        )
    ndl_ids = []
    for i, raw in enumerate(ndl.publishers):
        oid = f"ndl:{i}"
        ndl_ids.append(oid)
        collector.observations.append(
            PublisherObservation(
                observation_id=oid,
                group_id="ndl",
                source=EvidenceSource.NDL,
                origin=PublisherOrigin.NDL,
                record_id=ndl.id,
                record_uri=ndl.url or None,
                raw_value=raw,
                role=PublisherRole.PUBLISHER,
                provenance=FieldEvidence(
                    EvidenceSource.NDL,
                    "publishers",
                    raw,
                    raw,
                    ndl.id,
                    ndl.url or None,
                    "BookRecord.publishers",
                ),
                raw_layer=PublisherRawLayer.PARSED_VALUE,
                scope="ndl_parsed_publishers",
                completeness=ndl_completeness,
                value_index=i,
            )
        )
    groups.append(
        collector.group(
            "ndl",
            PublisherOrigin.NDL,
            ndl.id,
            ndl.url or None,
            True,
            tuple(ndl_ids),
            tuple(ndl_ids),
            (),
            ndl_completeness,
            None,
        )
    )
    observations = {o.observation_id: o for o in collector.observations}
    group_results, pairs = [], []
    for left, right in combinations((g for g in groups if g.related_to_book), 2):
        if not left.keys or not right.keys:
            state = PublisherLexicalState.UNCOMPARABLE
        elif left.keys != right.keys:
            state = PublisherLexicalState.DIFFERENT
            collector.issue("observed_lexical_set_difference", (left.group_id, right.group_id), conflict=True)
        else:
            raw_left = {observations[oid].raw_string for oid in left.publisher_ids if _key(observations[oid])}
            raw_right = {
                observations[oid].raw_string for oid in right.publisher_ids if _key(observations[oid])
            }
            if any(_key(observations[oid]) is None for oid in (*left.publisher_ids, *right.publisher_ids)):
                state = PublisherLexicalState.UNCOMPARABLE
            else:
                state = (
                    PublisherLexicalState.EXACT
                    if raw_left == raw_right
                    else PublisherLexicalState.NORMALIZED_EQUAL
                )
        group_results.append(
            PublisherGroupComparison(
                left_group_id=left.group_id,
                right_group_id=right.group_id,
                left_keys=left.keys,
                right_keys=right.keys,
                state=state,
                left_completeness=left.completeness,
                right_completeness=right.completeness,
            )
        )
        pairs.extend(product(left.observation_ids, right.observation_ids))
    for association in collector.associations:
        pairs.extend(product(association.name_observation_ids, association.reading_observation_ids))
    pairs = tuple(dict.fromkeys(pairs))
    return PublisherComparisonDiagnostic(
        observations=tuple(collector.observations),
        agent_associations=tuple(collector.associations),
        lexical_results=tuple(_lexical(observations[a], observations[b], policy) for a, b in pairs),
        structural_results=tuple(_structural(a, b, collector.associations, observations) for a, b in pairs),
        identity_assessments=tuple(PublisherIdentityAssessment(left_id=a, right_id=b) for a, b in pairs),
        groups=tuple(groups),
        group_comparisons=tuple(group_results),
        acquisition=acquisition,
        bundle_completeness=AcquisitionState(bundle.completeness),
        retrieval_scope=bundle.retrieval_scope,
        ndl_snapshot=ndl,
        conflict_reasons=tuple(collector.conflicts),
        unresolved_reasons=tuple(collector.unresolved),
        legacy=legacy_snapshot,
        policy=policy,
    )
