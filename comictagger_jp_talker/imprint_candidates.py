"""Pure, Book-scoped Imprint evaluation. No acquisition or metadata output.

Authority trust is an explicit caller assertion, never inferred from a URL or
VERIFIED flag. See docs/phase2c2b_imprint_candidates.md for the input contract.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Literal

from comictagger_jp_talker.isbn import isbn13
from comictagger_jp_talker.linkage import LinkageResult, LinkageStatus, MatchConfidence, RecordMatch
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.provenance import EvidenceSource, FieldEvidence
from comictagger_jp_talker.sources.madb_models import MADBRecordBundle, MADBStatement, RDFTerm
from comictagger_jp_talker.sources.madb_parser import terms
from comictagger_jp_talker.sources.madb_queries import CLASS_NS, RDF_NS, SCHEMA_NS, XSD_NS, resource_uri

EVALUATION_VERSION = "phase2c2b-v1"


class ImprintTermRole(str, Enum):
    DISPLAY = "display"
    READING = "reading"
    OTHER_LANGUAGE = "other_language"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"
    EMPTY = "empty"


class ImprintSemanticKind(str, Enum):
    VERIFIED_LABEL = "verified_label"
    PUBLISHER_OR_ISSUER = "publisher_or_issuer"
    NUMERIC_IDENTIFIER = "numeric_identifier"
    PUBLICATION_SERIES = "publication_series"
    MAGAZINE = "magazine"
    EDITION_STATEMENT = "edition_statement"
    OTHER_BRAND = "other_brand"
    UNVERIFIED = "unverified"


class LabelRelation(str, Enum):
    UPPER = "upper"
    LOWER = "lower"
    ALTERNATIVE = "alternative"
    COMPOSITE = "composite"
    UNRESOLVED = "unresolved"


class AuthorityState(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CONTRADICTED = "contradicted"


class AuthoritySourceKind(str, Enum):
    PUBLISHER_BIBLIOGRAPHY = "publisher_bibliography"
    LABEL_AUTHORITY = "label_authority"
    NDL = "ndl"
    MADB = "madb"


class AcquisitionState(str, Enum):
    COMPLETE = "complete"
    TRUNCATED = "truncated"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    NOT_REQUESTED = "not_requested"
    NOT_RELATED = "not_related"


class ImprintComparisonState(str, Enum):
    BOOK_ONLY = "book_only"
    SERIES_ONLY = "series_only"
    BOTH_AGREE = "both_agree"
    BOTH_CONFLICT = "both_conflict"
    MULTIPLE = "multiple"
    NONE = "none"
    UNAVAILABLE = "unavailable"


class ImprintEligibilityState(str, Enum):
    ELIGIBLE = "eligible"
    HOLD = "hold"
    REJECT = "reject"
    SKIP = "skip"


class ImprintEligibilityReason(str, Enum):
    NOT_MATCHED = "not_matched"
    IDENTITY_AMBIGUOUS = "identity_ambiguous"
    IDENTITY_CONFLICT = "identity_conflict"
    SNAPSHOT_MISMATCH = "snapshot_mismatch"
    DISCOVERY_TRUNCATED = "discovery_truncated"
    DISCOVERY_INCOMPLETE = "discovery_incomplete"
    BOOK_INCOMPLETE = "book_incomplete"
    SERIES_INCOMPLETE = "series_incomplete"
    RELATION_UNRESOLVED = "relation_unresolved"
    PROVENANCE_MISSING = "provenance_missing"
    CONTEXT_CONFLICT = "context_conflict"
    CONTEXT_UNVERIFIED = "context_unverified"
    EXISTING_IMPRINT = "existing_imprint"
    NO_DISPLAY = "no_display"
    UNSUPPORTED_TERM = "unsupported_term"
    INVALID_TERM = "invalid_term"
    MULTIPLE_DISPLAYS = "multiple_displays"
    MULTIPLE_RELATIONS = "multiple_relations"
    COMPOSITE_UNRESOLVED = "composite_unresolved"
    HIERARCHY_UNRESOLVED = "hierarchy_unresolved"
    SEMANTIC_UNVERIFIED = "semantic_unverified"
    PUBLISHER_EQUAL = "publisher_equal"
    NUMERIC_LIKE = "numeric_like"
    NONLABEL_VALUE = "nonlabel_value"
    EDITION_EQUAL = "edition_equal"
    SERIES_CONFLICT = "series_conflict"
    SERIES_ONLY_DISABLED = "series_only_disabled"
    INVALID_XML = "invalid_xml"
    AUTHORITY_UNTRUSTED = "authority_untrusted"
    AUTHORITY_UNVERIFIED = "authority_unverified"
    AUTHORITY_CONTRADICTED = "authority_contradicted"
    AUTHORITY_SCOPE_MISMATCH = "authority_scope_mismatch"
    AUTHORITY_RAW_MISMATCH = "authority_raw_mismatch"
    AUTHORITY_INDEPENDENCE_UNVERIFIED = "authority_independence_unverified"


@dataclass(frozen=True, kw_only=True)
class ResourceAcquisition:
    uri: str
    state: AcquisitionState

    def __post_init__(self) -> None:
        if not isinstance(self.uri, str) or not self.uri or not isinstance(self.state, AcquisitionState):
            raise ValueError("Invalid resource acquisition")


@dataclass(frozen=True, kw_only=True)
class AcquisitionContext:
    """Caller-supplied completion, not an instruction to fetch anything.

    NOT_REQUESTED defaults deliberately withhold eligibility. Resource states
    augment the Book/Series states; they cannot override incomplete snapshots.
    Agent/Holding states are informational and never used to infer absence.
    """

    discovery: AcquisitionState = AcquisitionState.NOT_REQUESTED
    book: AcquisitionState = AcquisitionState.NOT_REQUESTED
    series: AcquisitionState = AcquisitionState.NOT_REQUESTED
    relations: AcquisitionState = AcquisitionState.NOT_REQUESTED
    resources: tuple[ResourceAcquisition, ...] = ()
    agents: AcquisitionState = AcquisitionState.NOT_REQUESTED
    holdings: AcquisitionState = AcquisitionState.NOT_REQUESTED
    request_id: str | None = None
    acquired_at: str | None = None
    medium: str | None = None
    # Explicitly attested requested Book/Series scope, for a full bundle whose
    # partial state is confined to unneeded Agent/Holding acquisition.
    book_series_scope: AcquisitionState = AcquisitionState.NOT_REQUESTED

    def __post_init__(self) -> None:
        for name in ("discovery", "book", "series", "relations", "agents", "holdings", "book_series_scope"):
            if not isinstance(getattr(self, name), AcquisitionState):
                raise ValueError(f"Acquisition {name} must be an enum")
        if not isinstance(self.resources, tuple) or any(
            not isinstance(r, ResourceAcquisition) for r in self.resources
        ):
            raise ValueError("Acquisition resources must be an immutable tuple")
        for name in ("request_id", "acquired_at", "medium"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"Invalid acquisition {name}")


@dataclass(frozen=True, kw_only=True)
class LabelAuthorityEvidence:
    label_name: str
    source: str
    locator: str
    source_kind: AuthoritySourceKind
    book_id: str
    book_uri: str
    isbn: str
    publisher: str
    checked_at: str
    verification_state: AuthorityState = AuthorityState.UNVERIFIED
    semantic_kind: ImprintSemanticKind = ImprintSemanticKind.VERIFIED_LABEL
    trusted: bool = False
    independence_verified: bool = False
    origin_group: str | None = None
    # None means unconfirmed; () means explicitly checked no edition statement.
    editions: tuple[str, ...] | None = None
    medium: str | None = None
    publication_dates: tuple[str, ...] | None = None
    # Exact Book+ISBN bibliography confirms edition/medium/time applicability,
    # including when MADB has no structured medium field. No default affirmation.
    target_scope_verified: bool = False
    unconfirmed: tuple[str, ...] = ()
    relation: LabelRelation | None = None
    # Explicit external assertion of raw correspondence; no alias inference.
    raw_label_values: tuple[str, ...] = ()
    volume: str | None = None

    def __post_init__(self) -> None:
        for name in ("label_name", "source", "locator", "book_id", "book_uri", "isbn", "publisher"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Authority {name} must be a nonempty string")
        for name, kind in (
            ("source_kind", AuthoritySourceKind),
            ("verification_state", AuthorityState),
            ("semantic_kind", ImprintSemanticKind),
        ):
            if not isinstance(getattr(self, name), kind):
                raise ValueError(f"Authority {name} must be an enum")
        if self.relation is not None and not isinstance(self.relation, LabelRelation):
            raise ValueError("Invalid authority relation")
        for name in ("trusted", "independence_verified", "target_scope_verified"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"Authority {name} must be bool")
        for name in ("editions", "publication_dates", "unconfirmed", "raw_label_values"):
            value = getattr(self, name)
            if value is None and name in ("editions", "publication_dates"):
                continue
            if not isinstance(value, tuple) or any(not isinstance(v, str) or not v.strip() for v in value):
                raise ValueError(f"Authority {name} must be an immutable string tuple")
        for name in ("medium", "origin_group", "volume"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"Invalid authority {name}")
        try:
            checked = datetime.fromisoformat(self.checked_at)
            if checked.utcoffset() is None:
                raise ValueError
            if resource_uri(self.book_id, "book") != self.book_uri or isbn13(self.isbn) is None:
                raise ValueError
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid authority time, Book identity or ISBN") from exc
        if self.publication_dates is not None and any(not _valid_date(v) for v in self.publication_dates):
            raise ValueError("Invalid authority publication date")


@dataclass(frozen=True)
class ImprintCandidate:
    origin: Literal["book", "series"]
    evidence: FieldEvidence
    statements: tuple[MADBStatement, ...]
    statement_indices: tuple[int, ...]
    label_indices: tuple[int, ...]
    related_to_book: bool

    @property
    def term(self) -> RDFTerm:
        return self.evidence.raw_value


@dataclass(frozen=True)
class ImprintExtraction:
    bundle: MADBRecordBundle
    acquisition: AcquisitionContext
    candidates: tuple[ImprintCandidate, ...]
    relations: tuple[MADBStatement, ...]
    expected_series_uris: tuple[str, ...]
    blockers: tuple[ImprintEligibilityReason, ...]


@dataclass(frozen=True)
class ClassifiedImprintTerm:
    candidate: ImprintCandidate
    role: ImprintTermRole
    display: str | None
    equality_key: str | None
    semantic_kind: ImprintSemanticKind
    reasons: tuple[ImprintEligibilityReason, ...] = ()


@dataclass(frozen=True)
class ImprintClassification:
    extraction: ImprintExtraction
    terms: tuple[ClassifiedImprintTerm, ...]
    blockers: tuple[ImprintEligibilityReason, ...]


@dataclass(frozen=True)
class ContextComparison:
    field: str
    book: tuple[FieldEvidence, ...]
    series: tuple[FieldEvidence, ...]
    ndl: tuple[FieldEvidence, ...]
    conflict: bool
    unresolved: bool


@dataclass(frozen=True)
class ImprintComparison:
    state: ImprintComparisonState
    classification: ImprintClassification
    ndl_id: str
    ndl_url: str
    ndl_isbns: tuple[str, ...]
    ndl_dates: tuple[str, ...]
    book_displays: tuple[ClassifiedImprintTerm, ...]
    series_displays: tuple[ClassifiedImprintTerm, ...]
    book_values: tuple[str, ...]
    series_values: tuple[str, ...]
    book_keys: tuple[str, ...]
    series_keys: tuple[str, ...]
    normalized_set_equal: bool
    overlap: tuple[str, ...]
    ndl_series_titles: tuple[FieldEvidence, ...]
    ndl_overlap: tuple[str, ...]
    publisher: ContextComparison
    edition: ContextComparison
    required_series_states: tuple[ResourceAcquisition, ...]
    blockers: tuple[ImprintEligibilityReason, ...]

    @property
    def book_candidate_count(self) -> int:
        return len(self.book_displays)

    @property
    def series_candidate_count(self) -> int:
        return len(self.series_displays)

    @property
    def book_occurrence_count(self) -> int:
        return sum(len(t.candidate.label_indices) for t in self.book_displays)

    @property
    def series_occurrence_count(self) -> int:
        return sum(len(t.candidate.label_indices) for t in self.series_displays)


@dataclass(frozen=True)
class AuthorityAssessment:
    evidence: LabelAuthorityEvidence
    applicable: bool
    reasons: tuple[ImprintEligibilityReason, ...]

    @property
    def semantic_kind(self) -> ImprintSemanticKind:
        # External semantics become established only after trust and scope pass.
        if set(self.reasons) <= {ImprintEligibilityReason.NONLABEL_VALUE}:
            return self.evidence.semantic_kind
        return ImprintSemanticKind.UNVERIFIED


@dataclass(frozen=True)
class ImprintEligibility:
    state: ImprintEligibilityState
    selected_candidate: ImprintCandidate | None
    reasons: tuple[ImprintEligibilityReason, ...]
    comparison: ImprintComparison
    linkage: LinkageResult
    authority: tuple[AuthorityAssessment, ...] = ()
    evaluation_version: str = EVALUATION_VERSION

    def __post_init__(self) -> None:
        if (self.state == ImprintEligibilityState.ELIGIBLE) != (self.selected_candidate is not None):
            raise ValueError("Only ELIGIBLE has a selected candidate")
        if self.state == ImprintEligibilityState.ELIGIBLE:
            if self.reasons or not self.authority or not all(a.applicable for a in self.authority):
                raise ValueError("ELIGIBLE requires applicable authority and no blockers")
            if (
                self.comparison.blockers
                or self.comparison.state
                not in (ImprintComparisonState.BOOK_ONLY, ImprintComparisonState.BOTH_AGREE)
                or _identity_reasons(self.linkage, self.comparison)
            ):
                raise ValueError("ELIGIBLE requires a safe comparison and identity")
            displays = self.comparison.book_displays
            if len(self.comparison.book_values) != 1 or self.selected_candidate not in tuple(
                t.candidate for t in displays
            ):
                raise ValueError("ELIGIBLE requires one unique Book display")
            if not _xml_valid(self.selected_candidate.term.value):
                raise ValueError("ELIGIBLE requires an XML-safe display")
        elif not self.reasons:
            raise ValueError("Non-eligible results require reasons")


def _reasons(values) -> tuple[ImprintEligibilityReason, ...]:
    return tuple(sorted(set(values), key=lambda v: v.value))


def _key(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _xml_valid(value: str) -> bool:
    return not any(
        ord(c) < 32 and c not in "\t\n\r" or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in (0xFFFE, 0xFFFF)
        for c in value
    )


def _valid_date(value: str) -> bool:
    if not re.fullmatch(r"[0-9]{4}(?:-[0-9]{2}){0,2}", value):
        return False
    try:
        date.fromisoformat(value + {4: "-01-01", 7: "-01", 10: ""}[len(value)])
    except ValueError:
        return False
    return True


def _dates_agree(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return (
        bool(left and right)
        and all(_valid_date(v) for v in (*left, *right))
        and all(a.startswith(b) or b.startswith(a) for a in left for b in right)
    )


def _role(term: RDFTerm) -> ImprintTermRole:
    if (
        term.kind not in ("uri", "bnode", "literal")
        or not isinstance(term.value, str)
        or any(v is not None and (not isinstance(v, str) or not v) for v in (term.language, term.datatype))
        or any(0xD800 <= ord(c) <= 0xDFFF for v in (term.value, term.language, term.datatype) if v for c in v)
        or term.kind != "literal"
        and (term.language is not None or term.datatype is not None)
        or term.language is not None
        and term.datatype not in (None, RDF_NS + "langString")
        or term.language is None
        and term.datatype == RDF_NS + "langString"
    ):
        return ImprintTermRole.INVALID
    if term.kind != "literal":
        return ImprintTermRole.UNSUPPORTED
    language = term.language.casefold() if term.language else None
    if language is None and term.datatype not in (None, XSD_NS + "string"):
        return ImprintTermRole.UNSUPPORTED
    if language not in (None, "ja", "ja-hrkt"):
        return ImprintTermRole.OTHER_LANGUAGE
    if not term.value.strip():
        return ImprintTermRole.EMPTY
    return ImprintTermRole.READING if language == "ja-hrkt" else ImprintTermRole.DISPLAY


def _candidate_sort(candidate: ImprintCandidate):
    term = candidate.term
    return (
        candidate.origin,
        candidate.evidence.record_uri,
        repr((term.kind, term.value, term.language, term.datatype)),
    )


def extract_imprint_evidence(bundle: MADBRecordBundle, acquisition: AcquisitionContext) -> ImprintExtraction:
    """Retain every label occurrence and matching statement index, including duplicates.

    Book parsing already deduplicates identical triples; this API cannot recreate
    occurrences absent from its input. Unrelated Series remain raw evidence only.
    """
    book = bundle.book
    relations = tuple(s for s in book.statements if s.predicate == SCHEMA_NS + "isPartOf")
    expected = tuple(sorted(set(book.series_uris)))
    blockers = []
    try:
        if resource_uri(book.id, "book") != book.uri:
            blockers.append(ImprintEligibilityReason.SNAPSHOT_MISMATCH)
        for uri in expected:
            resource_uri(uri, "series")
    except ValueError:
        blockers.append(ImprintEligibilityReason.RELATION_UNRESOLVED)
    if any(
        s.subject != book.uri or s.object.kind != "uri" or _role(s.object) == ImprintTermRole.INVALID
        for s in relations
    ) or {s.object.value for s in relations if s.object.kind == "uri"} != set(expected):
        blockers.append(ImprintEligibilityReason.RELATION_UNRESOLVED)
    candidates = []
    for origin, record in (("book", book), *(("series", s) for s in bundle.series)):
        identifiers = terms(record.statements, SCHEMA_NS + "identifier")
        record_type = CLASS_NS + ("MangaBook" if origin == "book" else "MangaBookSeries")
        if (
            not identifiers
            or any(_role(t) != ImprintTermRole.DISPLAY or t.value != record.id for t in identifiers)
            or RDFTerm("uri", record_type) not in terms(record.statements, RDF_NS + "type")
        ):
            blockers.append(ImprintEligibilityReason.SNAPSHOT_MISMATCH)
        if origin == "series":
            try:
                if resource_uri(record.id, "series") != record.uri:
                    blockers.append(ImprintEligibilityReason.SNAPSHOT_MISMATCH)
            except ValueError:
                blockers.append(ImprintEligibilityReason.SNAPSHOT_MISMATCH)
            if record.uri not in expected:
                blockers.append(ImprintEligibilityReason.RELATION_UNRESOLVED)
        raw_brands = tuple(s for s in record.statements if s.predicate == SCHEMA_NS + "brand")
        for field, predicate in (
            ("publishers", "publisher"),
            ("editions", "version"),
            ("publication_dates", "datePublished"),
        ):
            if set(getattr(record, field)) != set(terms(record.statements, SCHEMA_NS + predicate)):
                blockers.append(ImprintEligibilityReason.PROVENANCE_MISSING)
        if origin == "book":
            for field, predicate in (("isbns", "isbn"), ("volumes", "volumeNumber")):
                if set(getattr(record, field)) != set(terms(record.statements, SCHEMA_NS + predicate)):
                    blockers.append(ImprintEligibilityReason.PROVENANCE_MISSING)
        if any(s.subject != record.uri for s in record.statements) or set(record.labels) != {
            s.object for s in raw_brands
        }:
            blockers.append(ImprintEligibilityReason.PROVENANCE_MISSING)
        # Union prevents malformed manually assembled snapshots hiding raw terms.
        for term in dict.fromkeys((*record.labels, *(s.object for s in raw_brands))):
            indices = tuple(
                i
                for i, s in enumerate(record.statements)
                if s.subject == record.uri and s.predicate == SCHEMA_NS + "brand" and s.object == term
            )
            candidates.append(
                ImprintCandidate(
                    origin,
                    FieldEvidence(
                        EvidenceSource.MADB,
                        "imprint",
                        term.value if term.kind == "literal" else None,
                        term,
                        record.id,
                        record.uri,
                        SCHEMA_NS + "brand",
                    ),
                    tuple(record.statements[i] for i in indices),
                    indices,
                    tuple(i for i, value in enumerate(record.labels) if value == term),
                    origin == "book" or record.uri in expected,
                )
            )
    uris = [s.uri for s in bundle.series]
    if len(set(uris)) != len(uris):
        blockers.append(ImprintEligibilityReason.RELATION_UNRESOLVED)
    return ImprintExtraction(
        bundle,
        acquisition,
        tuple(sorted(candidates, key=_candidate_sort)),
        relations,
        expected,
        _reasons(blockers),
    )


def _display_keys(raw: tuple[RDFTerm, ...]) -> set[str]:
    return {_key(t.value) for t in raw if _role(t) == ImprintTermRole.DISPLAY}


def classify_imprint_terms(extraction: ImprintExtraction) -> ImprintClassification:
    """Language roles plus evidence-backed diagnostics, never a label dictionary.

    Publisher equality and numeric appearance leave semantic kind UNVERIFIED.
    Edition equality records a duplicate description, not proof that a brand
    with that name cannot exist. Verified external semantics are assessed later.
    """
    result, blockers = [], list(extraction.blockers)
    records = (extraction.bundle.book, *extraction.bundle.series)
    for candidate in extraction.candidates:
        role = _role(candidate.term)
        display = candidate.term.value if role == ImprintTermRole.DISPLAY else None
        key = _key(display) if display is not None else None
        reasons, semantic = [], ImprintSemanticKind.UNVERIFIED
        record = next(r for r in records if r.uri == candidate.evidence.record_uri)
        if role == ImprintTermRole.INVALID:
            reasons.append(ImprintEligibilityReason.INVALID_TERM)
        elif role in (ImprintTermRole.UNSUPPORTED, ImprintTermRole.OTHER_LANGUAGE):
            reasons.append(ImprintEligibilityReason.UNSUPPORTED_TERM)
        if display is not None:
            if key in _display_keys(record.editions):
                semantic = ImprintSemanticKind.EDITION_STATEMENT
                reasons.append(ImprintEligibilityReason.EDITION_EQUAL)
            if key in _display_keys(record.publishers):
                reasons.append(ImprintEligibilityReason.PUBLISHER_EQUAL)
            if re.fullmatch(r"[0-9]+", display):
                reasons.append(ImprintEligibilityReason.NUMERIC_LIKE)
        result.append(ClassifiedImprintTerm(candidate, role, display, key, semantic, _reasons(reasons)))
        if candidate.related_to_book:
            blockers.extend(
                r
                for r in reasons
                if r
                in (
                    ImprintEligibilityReason.INVALID_TERM,
                    ImprintEligibilityReason.UNSUPPORTED_TERM,
                )
            )
    return ImprintClassification(extraction, tuple(result), _reasons(blockers))


def _field(record, field: str, predicate: str) -> tuple[FieldEvidence, ...]:
    return tuple(
        FieldEvidence(
            EvidenceSource.MADB,
            field,
            t.value if t.kind == "literal" else None,
            t,
            record.id,
            record.uri,
            predicate,
        )
        for t in getattr(record, field)
    )


def _context_comparison(
    classification: ImprintClassification, ndl: BookRecord, field: str, predicate: str
) -> ContextComparison:
    extraction = classification.extraction
    book = _field(extraction.bundle.book, field, predicate)
    series = tuple(
        e
        for s in extraction.bundle.series
        if s.uri in extraction.expected_series_uris
        for e in _field(s, field, predicate)
    )
    ndl_values = tuple(
        FieldEvidence(EvidenceSource.NDL, field, raw, raw, ndl.id, ndl.url or None, "BookRecord." + field)
        for raw in getattr(ndl, field)
    )
    groups = [_display_keys(tuple(e.raw_value for e in book))]
    groups.extend(
        _display_keys(getattr(s, field))
        for s in extraction.bundle.series
        if s.uri in extraction.expected_series_uris
    )
    groups.append({_key(e.raw_value) for e in ndl_values if e.raw_value.strip()})
    present = [g for g in groups if g]
    conflict = any(a != b for i, a in enumerate(present) for b in present[i + 1 :])
    unresolved = any(
        _role(e.raw_value) not in (ImprintTermRole.DISPLAY, ImprintTermRole.READING, ImprintTermRole.EMPTY)
        for e in (*book, *series)
    )
    # A missing edition beside an explicit one does not establish same edition.
    if field == "editions" and present and any(not g for g in groups):
        unresolved = True
    if field == "publishers" and (any(not g for g in groups) or any(len(g) > 1 for g in groups)):
        unresolved = True
    return ContextComparison(field, book, series, ndl_values, conflict, unresolved)


def _complete_book_series_scope(extraction: ImprintExtraction) -> bool:
    return (
        extraction.bundle.retrieval_scope == "full"
        and extraction.bundle.completeness == "partial"
        and extraction.acquisition.book_series_scope == AcquisitionState.COMPLETE
    )


def _availability(extraction: ImprintExtraction):
    acquisition, bundle = extraction.acquisition, extraction.bundle
    blockers = []
    if acquisition.discovery == AcquisitionState.TRUNCATED:
        blockers.append(ImprintEligibilityReason.DISCOVERY_TRUNCATED)
    elif acquisition.discovery != AcquisitionState.COMPLETE:
        blockers.append(ImprintEligibilityReason.DISCOVERY_INCOMPLETE)
    if acquisition.book != AcquisitionState.COMPLETE or bundle.book.completeness != "complete":
        blockers.append(ImprintEligibilityReason.BOOK_INCOMPLETE)
    if bundle.completeness != "complete" and not _complete_book_series_scope(extraction):
        blockers.append(ImprintEligibilityReason.BOOK_INCOMPLETE)
    expected = extraction.expected_series_uris
    if acquisition.relations != (AcquisitionState.COMPLETE if expected else AcquisitionState.NOT_RELATED):
        blockers.append(ImprintEligibilityReason.RELATION_UNRESOLVED)
    if acquisition.series != (AcquisitionState.COMPLETE if expected else AcquisitionState.NOT_RELATED):
        blockers.append(ImprintEligibilityReason.SERIES_INCOMPLETE)
    declared = {r.uri: r.state for r in acquisition.resources}
    if len(declared) != len(acquisition.resources):
        blockers.append(ImprintEligibilityReason.RELATION_UNRESOLVED)
    if declared.get(bundle.book.uri, AcquisitionState.COMPLETE) != AcquisitionState.COMPLETE:
        blockers.append(ImprintEligibilityReason.BOOK_INCOMPLETE)
    actual = {s.uri: s for s in bundle.series}
    states = []
    for uri in expected:
        record = actual.get(uri)
        state = declared.get(
            uri, AcquisitionState(record.completeness) if record else AcquisitionState.NOT_REQUESTED
        )
        if state == AcquisitionState.COMPLETE:
            if record is None:
                state = AcquisitionState.UNAVAILABLE
            elif record.completeness != "complete":
                state = AcquisitionState(record.completeness)
        if record is None or record.completeness != "complete" or state != AcquisitionState.COMPLETE:
            blockers.append(ImprintEligibilityReason.SERIES_INCOMPLETE)
        states.append(ResourceAcquisition(uri=uri, state=state))
    blockers.extend(r for r in extraction.blockers if r == ImprintEligibilityReason.RELATION_UNRESOLVED)
    return tuple(states), _reasons(blockers)


def compare_imprint_candidates(
    classification: ImprintClassification, ndl_record: BookRecord
) -> ImprintComparison:
    extraction = classification.extraction
    book = tuple(
        t for t in classification.terms if t.role == ImprintTermRole.DISPLAY and t.candidate.origin == "book"
    )
    series = tuple(
        t
        for t in classification.terms
        if t.role == ImprintTermRole.DISPLAY
        and t.candidate.origin == "series"
        and t.candidate.related_to_book
    )
    book_values, series_values = (tuple(sorted({t.display for t in group})) for group in (book, series))
    book_keys, series_keys = (tuple(sorted({t.equality_key for t in group})) for group in (book, series))
    states, availability = _availability(extraction)
    blockers = list((*classification.blockers, *availability))
    if len(extraction.expected_series_uris) > 1:
        blockers.append(ImprintEligibilityReason.MULTIPLE_RELATIONS)
    if len(book_values) > 1 or len(series_values) > 1:
        blockers.append(ImprintEligibilityReason.MULTIPLE_DISPLAYS)
    if availability:
        state = ImprintComparisonState.UNAVAILABLE
    elif len(book_values) > 1 or len(series_values) > 1 or len(extraction.expected_series_uris) > 1:
        state = ImprintComparisonState.MULTIPLE
    elif book_values and series_values:
        state = (
            ImprintComparisonState.BOTH_AGREE
            if book_keys == series_keys
            else ImprintComparisonState.BOTH_CONFLICT
        )
    elif book_values:
        state = ImprintComparisonState.BOOK_ONLY
    elif series_values:
        state = ImprintComparisonState.SERIES_ONLY
    else:
        state = ImprintComparisonState.NONE
    ndl_titles = tuple(
        FieldEvidence(
            EvidenceSource.NDL,
            "series_titles",
            raw,
            raw,
            ndl_record.id,
            ndl_record.url or None,
            "BookRecord.series_titles",
        )
        for raw in ndl_record.series_titles
    )
    publisher = _context_comparison(classification, ndl_record, "publishers", SCHEMA_NS + "publisher")
    edition = _context_comparison(classification, ndl_record, "editions", SCHEMA_NS + "version")
    if publisher.conflict or edition.conflict:
        blockers.append(ImprintEligibilityReason.CONTEXT_CONFLICT)
    if publisher.unresolved or edition.unresolved:
        blockers.append(ImprintEligibilityReason.CONTEXT_UNVERIFIED)
    return ImprintComparison(
        state,
        classification,
        ndl_record.id,
        ndl_record.url,
        tuple(ndl_record.isbns),
        tuple((*ndl_record.issued, *ndl_record.dates)),
        book,
        series,
        book_values,
        series_values,
        book_keys,
        series_keys,
        book_keys == series_keys,
        tuple(sorted(set(book_keys) & set(series_keys))),
        ndl_titles,
        tuple(sorted(set(book_keys) & {_key(e.raw_value) for e in ndl_titles})),
        publisher,
        edition,
        states,
        _reasons(blockers),
    )


def _authority_assessment(
    evidence: LabelAuthorityEvidence, comparison: ImprintComparison
) -> AuthorityAssessment:
    book = comparison.classification.extraction.bundle.book
    reasons = []
    if not evidence.trusted:
        reasons.append(ImprintEligibilityReason.AUTHORITY_UNTRUSTED)
    if evidence.verification_state == AuthorityState.CONTRADICTED:
        reasons.append(ImprintEligibilityReason.AUTHORITY_CONTRADICTED)
    elif evidence.verification_state != AuthorityState.VERIFIED:
        reasons.append(ImprintEligibilityReason.AUTHORITY_UNVERIFIED)
    if (
        not evidence.independence_verified
        or not evidence.origin_group
        or evidence.source_kind in (AuthoritySourceKind.NDL, AuthoritySourceKind.MADB)
    ):
        reasons.append(ImprintEligibilityReason.AUTHORITY_INDEPENDENCE_UNVERIFIED)
    madb_isbns = {isbn13(t.value) for t in book.isbns if _role(t) == ImprintTermRole.DISPLAY}
    ndl_isbns = {isbn13(v) for v in comparison.ndl_isbns}
    if (
        evidence.book_id != book.id
        or evidence.book_uri != book.uri
        or isbn13(evidence.isbn) not in madb_isbns
        or isbn13(evidence.isbn) not in ndl_isbns
    ):
        reasons.append(ImprintEligibilityReason.AUTHORITY_SCOPE_MISMATCH)
    if len(comparison.book_values) != 1 or comparison.book_values[0] not in (
        evidence.raw_label_values or (evidence.label_name,)
    ):
        reasons.append(ImprintEligibilityReason.AUTHORITY_RAW_MISMATCH)
    if (
        not evidence.target_scope_verified
        or evidence.unconfirmed
        or evidence.editions is None
        or not evidence.medium
        or not evidence.publication_dates
    ):
        reasons.append(ImprintEligibilityReason.CONTEXT_UNVERIFIED)
    for field, context, asserted in (
        ("publishers", comparison.publisher, (evidence.publisher,)),
        ("editions", comparison.edition, evidence.editions),
    ):
        if asserted is None:
            continue
        expected = {_key(v) for v in asserted}
        actual = _display_keys(getattr(book, field))
        ndl = {_key(e.raw_value) for e in context.ndl if e.raw_value.strip()}
        if actual != expected or ndl != expected:
            reasons.append(ImprintEligibilityReason.CONTEXT_CONFLICT)
    acquisition = comparison.classification.extraction.acquisition
    if acquisition.medium is not None and acquisition.medium != evidence.medium:
        reasons.append(ImprintEligibilityReason.CONTEXT_CONFLICT)
    dates = tuple(t.value for t in book.publication_dates if _role(t) == ImprintTermRole.DISPLAY)
    if any(_role(t) not in (ImprintTermRole.DISPLAY, ImprintTermRole.EMPTY) for t in book.publication_dates):
        reasons.append(ImprintEligibilityReason.CONTEXT_UNVERIFIED)
    if evidence.volume is not None and _display_keys(book.volumes) != {_key(evidence.volume)}:
        reasons.append(ImprintEligibilityReason.AUTHORITY_SCOPE_MISMATCH)
    if not dates:
        reasons.append(ImprintEligibilityReason.CONTEXT_UNVERIFIED)
    elif evidence.publication_dates and not _dates_agree(dates, evidence.publication_dates):
        reasons.append(ImprintEligibilityReason.CONTEXT_CONFLICT)
    if (
        comparison.ndl_dates
        and evidence.publication_dates
        and not _dates_agree(comparison.ndl_dates, evidence.publication_dates)
    ):
        reasons.append(ImprintEligibilityReason.CONTEXT_CONFLICT)
    if evidence.relation is not None:
        reasons.append(
            ImprintEligibilityReason.COMPOSITE_UNRESOLVED
            if evidence.relation == LabelRelation.COMPOSITE
            else ImprintEligibilityReason.HIERARCHY_UNRESOLVED
        )
    if evidence.semantic_kind == ImprintSemanticKind.UNVERIFIED:
        reasons.append(ImprintEligibilityReason.SEMANTIC_UNVERIFIED)
    elif evidence.semantic_kind != ImprintSemanticKind.VERIFIED_LABEL:
        reasons.append(ImprintEligibilityReason.NONLABEL_VALUE)
    return AuthorityAssessment(evidence, not reasons, _reasons(reasons))


def _identity_reasons(linkage: LinkageResult, comparison: ImprintComparison):
    reasons = []
    book = comparison.classification.extraction.bundle.book
    if linkage.status != LinkageStatus.MATCHED:
        reasons.append(ImprintEligibilityReason.NOT_MATCHED)
    if linkage.error is not None:
        reasons.append(ImprintEligibilityReason.DISCOVERY_INCOMPLETE)
    if linkage.truncated:
        reasons.append(ImprintEligibilityReason.DISCOVERY_TRUNCATED)
    # An unsafe target still has explicit contradictions to report. Do not lose
    # them at the no-safe-match gate or transfer another Book's conflict here.
    if any(m.madb_id == book.id and m.ndl_id == comparison.ndl_id and m.conflicts for m in linkage.matches):
        reasons.append(ImprintEligibilityReason.IDENTITY_CONFLICT)
    safe = tuple(
        m for m in linkage.matches if m.confidence in (MatchConfidence.EXACT, MatchConfidence.STRONG)
    )
    if len(safe) != 1:
        reasons.append(ImprintEligibilityReason.IDENTITY_AMBIGUOUS)
        return _reasons(reasons)
    match: RecordMatch = safe[0]
    if match.conflicts:
        reasons.append(ImprintEligibilityReason.IDENTITY_CONFLICT)
    summaries = linkage.candidates
    if (
        match.madb_id != book.id
        or match.ndl_id != comparison.ndl_id
        or len({s.id for s in summaries}) != len(summaries)
        or len({s.uri for s in summaries}) != len(summaries)
        or match.candidate_count != len(summaries)
        or not any(s.id == book.id and s.uri == book.uri for s in summaries)
    ):
        reasons.append(ImprintEligibilityReason.SNAPSHOT_MISMATCH)
    if any(
        s.completeness != "complete"
        and not (
            s.id == book.id
            and s.uri == book.uri
            and s.completeness == "partial"
            and _complete_book_series_scope(comparison.classification.extraction)
        )
        for s in summaries
    ):
        reasons.append(ImprintEligibilityReason.DISCOVERY_INCOMPLETE)
    # Check supplied raw identity evidence against this particular snapshot.
    madb_evidence = tuple(e for e in match.evidence if e.source == EvidenceSource.MADB)
    if not madb_evidence:
        reasons.append(ImprintEligibilityReason.PROVENANCE_MISSING)
    for e in madb_evidence:
        if (
            e.record_id != book.id
            or e.record_uri != book.uri
            or not isinstance(e.raw_value, RDFTerm)
            or e.raw_value not in terms(book.statements, e.predicate_or_path)
        ):
            reasons.append(ImprintEligibilityReason.SNAPSHOT_MISMATCH)
    for e in match.evidence:
        if e.source == EvidenceSource.NDL:
            if (
                e.record_id != comparison.ndl_id
                or e.record_uri != (comparison.ndl_url or None)
                or e.field == "isbn"
                and e.raw_value not in comparison.ndl_isbns
                or e.field == "url"
                and e.raw_value != comparison.ndl_url
            ):
                reasons.append(ImprintEligibilityReason.SNAPSHOT_MISMATCH)
    return _reasons(reasons)


def evaluate_imprint_eligibility(
    linkage: LinkageResult,
    comparison: ImprintComparison,
    *,
    existing_imprint: str | None = None,
    authority_evidence: tuple[LabelAuthorityEvidence, ...] = (),
) -> ImprintEligibility:
    """Return a decision only. Even ELIGIBLE never writes GenericMetadata.

    Every supplied authority is retained; a contradicted/inapplicable assertion
    cannot be silently dropped beside a convenient verified assertion.
    """
    if existing_imprint is not None and not isinstance(existing_imprint, str):
        raise ValueError("existing_imprint must be str or None")
    assessments = tuple(_authority_assessment(e, comparison) for e in authority_evidence)
    if existing_imprint is not None and existing_imprint != "":
        return ImprintEligibility(
            ImprintEligibilityState.SKIP,
            None,
            (ImprintEligibilityReason.EXISTING_IMPRINT,),
            comparison,
            linkage,
            assessments,
        )
    reasons = list((*comparison.blockers, *_identity_reasons(linkage, comparison)))
    state = comparison.state
    if state == ImprintComparisonState.MULTIPLE:
        reasons.append(ImprintEligibilityReason.MULTIPLE_DISPLAYS)
    elif state == ImprintComparisonState.BOTH_CONFLICT:
        reasons.append(ImprintEligibilityReason.SERIES_CONFLICT)
    elif state == ImprintComparisonState.SERIES_ONLY:
        reasons.append(ImprintEligibilityReason.SERIES_ONLY_DISABLED)
    elif state == ImprintComparisonState.NONE:
        reasons.append(ImprintEligibilityReason.NO_DISPLAY)
    for term in (*comparison.book_displays, *comparison.series_displays):
        if ImprintEligibilityReason.EDITION_EQUAL in term.reasons:
            reasons.extend((ImprintEligibilityReason.EDITION_EQUAL, ImprintEligibilityReason.NONLABEL_VALUE))
        display = term.display
        if not _xml_valid(display):
            reasons.append(ImprintEligibilityReason.INVALID_XML)
    for assessment in assessments:
        reasons.extend(assessment.reasons)
    if not assessments or not all(a.applicable for a in assessments):
        reasons.append(ImprintEligibilityReason.SEMANTIC_UNVERIFIED)
        for term in comparison.book_displays:
            reasons.extend(
                r
                for r in term.reasons
                if r in (ImprintEligibilityReason.PUBLISHER_EQUAL, ImprintEligibilityReason.NUMERIC_LIKE)
            )
    reasons = _reasons(reasons)
    hard = {
        ImprintEligibilityReason.IDENTITY_CONFLICT,
        ImprintEligibilityReason.SNAPSHOT_MISMATCH,
        ImprintEligibilityReason.PROVENANCE_MISSING,
        ImprintEligibilityReason.CONTEXT_CONFLICT,
        ImprintEligibilityReason.NONLABEL_VALUE,
        ImprintEligibilityReason.SERIES_CONFLICT,
        ImprintEligibilityReason.INVALID_XML,
        ImprintEligibilityReason.INVALID_TERM,
        ImprintEligibilityReason.AUTHORITY_CONTRADICTED,
        ImprintEligibilityReason.AUTHORITY_SCOPE_MISMATCH,
        ImprintEligibilityReason.AUTHORITY_RAW_MISMATCH,
    }
    if not reasons and state in (ImprintComparisonState.BOTH_AGREE, ImprintComparisonState.BOOK_ONLY):
        candidate = min((t.candidate for t in comparison.book_displays), key=_candidate_sort)
        return ImprintEligibility(
            ImprintEligibilityState.ELIGIBLE, candidate, (), comparison, linkage, assessments
        )
    if hard.intersection(reasons):
        decision = ImprintEligibilityState.REJECT
    elif state == ImprintComparisonState.NONE and set(reasons) <= {
        ImprintEligibilityReason.NO_DISPLAY,
        ImprintEligibilityReason.SEMANTIC_UNVERIFIED,
    }:
        decision = ImprintEligibilityState.SKIP
    else:
        decision = ImprintEligibilityState.HOLD
    return ImprintEligibility(decision, None, reasons, comparison, linkage, assessments)
