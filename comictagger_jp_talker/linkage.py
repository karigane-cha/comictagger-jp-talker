"""Explicit NDL/MADB identity linkage, independent of the normal Talker path."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum

from comictagger_jp_talker.isbn import isbn13, normalize_isbn
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.provenance import EvidenceSource, FieldEvidence, SeriesComparison, compare_series
from comictagger_jp_talker.sources.madb import MADBSource
from comictagger_jp_talker.sources.madb_models import MADBError, MADBRecordBundle
from comictagger_jp_talker.sources.madb_parser import terms
from comictagger_jp_talker.sources.madb_queries import PROPERTY_NS, SCHEMA_NS
from comictagger_jp_talker.sources.ndl import ndl_record_url

ALGORITHM_VERSION = "phase2b2-v1"


class MatchConfidence(str, Enum):
    EXACT = "exact"
    STRONG = "strong"
    AMBIGUOUS = "ambiguous"
    UNSAFE = "unsafe"


class LinkageStatus(str, Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"
    UNSAFE = "unsafe"


class MatchReason(str, Enum):
    DIRECT_NDL_URL = "direct_ndl_url"
    ISBN_RAW = "isbn_raw"
    ISBN_NORMALIZED = "isbn_normalized"
    ISBN_EQUIVALENT = "isbn_10_13_equivalent"


class MatchConflict(str, Enum):
    NDL_URL = "ndl_url_mismatch"
    ISBN = "isbn_discrepancy"


@dataclass(frozen=True)
class RecordMatch:
    ndl_id: str
    madb_id: str
    confidence: MatchConfidence
    reasons: tuple[MatchReason, ...]
    conflicts: tuple[MatchConflict, ...]
    evidence: tuple[FieldEvidence, ...]
    candidate_count: int
    algorithm_version: str = ALGORITHM_VERSION
    series: SeriesComparison | None = None


@dataclass(frozen=True)
class CandidateSummary:
    id: str
    uri: str
    # None means discovered but not retrieved. No RDF bundle duplication.
    completeness: str | None = None


@dataclass(frozen=True)
class LinkageError:
    kind: str
    message: str
    status: int | None = None
    retry_after: str | None = None


@dataclass(frozen=True)
class LinkageResult:
    status: LinkageStatus
    matches: tuple[RecordMatch, ...] = ()
    candidates: tuple[CandidateSummary, ...] = ()
    warnings: tuple[str, ...] = ()
    error: LinkageError | None = None
    truncated: bool = False


def _url(value: str) -> str | None:
    # Reuse Phase 1's HTTPS/host/path/query policy, including fragment removal.
    try:
        identity = ndl_record_url(value)
    except ValueError:  # Malformed URL, e.g. unmatched IPv6 bracket.
        return None
    return identity[1] if identity else None


def _evaluate(
    record: BookRecord, bundle: MADBRecordBundle, count: int, truncated: bool
) -> RecordMatch | None:
    book = bundle.book
    ndl_url = _url(record.url)
    evidence = [
        FieldEvidence(
            EvidenceSource.NDL,
            "url",
            ndl_url,
            record.url,
            record.id,
            record.url or None,
            "BookRecord.url",
            "ndl.ndl_record_url",
        )
    ]
    urls = set()
    for term in terms(book.statements, PROPERTY_NS + "dataUrl"):
        value = _url(term.value) if term.kind in ("uri", "literal") else None
        evidence.append(
            FieldEvidence(
                EvidenceSource.MADB,
                "url",
                value,
                term,
                book.id,
                book.uri,
                PROPERTY_NS + "dataUrl",
                "ndl.ndl_record_url",
            )
        )
        if value:
            urls.add(value)
    ndl_isbns = [(raw, isbn13(raw)) for raw in record.isbns]
    madb_isbns = [(term, isbn13(term.value) if term.kind == "literal" else None) for term in book.isbns]
    evidence.extend(
        FieldEvidence(
            EvidenceSource.NDL,
            "isbn",
            value,
            raw,
            record.id,
            record.url or None,
            "BookRecord.isbns",
            "isbn.isbn13",
        )
        for raw, value in ndl_isbns
    )
    evidence.extend(
        FieldEvidence(
            EvidenceSource.MADB,
            "isbn",
            value,
            term,
            book.id,
            book.uri,
            SCHEMA_NS + "isbn",
            "isbn.isbn13",
        )
        for term, value in madb_isbns
    )
    reasons, conflicts = [], []
    if ndl_url and ndl_url in urls:
        reasons.append(MatchReason.DIRECT_NDL_URL)
    if ndl_url and urls - {ndl_url}:
        conflicts.append(MatchConflict.NDL_URL)
    ndl_set = {value for _, value in ndl_isbns if value}
    madb_set = {value for _, value in madb_isbns if value}
    if ndl_set and madb_set and not ndl_set & madb_set:
        conflicts.append(MatchConflict.ISBN)
    for raw, value in ndl_isbns:
        for term, other in madb_isbns:
            if value and value == other:
                reasons.append(MatchReason.ISBN_NORMALIZED)
                if raw == term.value:
                    reasons.append(MatchReason.ISBN_RAW)
                if len(normalize_isbn(raw)) != len(normalize_isbn(term.value)):
                    reasons.append(MatchReason.ISBN_EQUIVALENT)
    if not reasons and not conflicts:
        return None
    if MatchConflict.NDL_URL in conflicts or not reasons:
        confidence = MatchConfidence.UNSAFE
    elif book.completeness != "complete":
        confidence = MatchConfidence.AMBIGUOUS  # Unseen direct URLs could contradict identity.
    elif MatchReason.DIRECT_NDL_URL in reasons:
        confidence = MatchConfidence.EXACT  # ISBN discrepancy is field evidence, not a different identity.
    elif count == 1 and not truncated:
        confidence = MatchConfidence.STRONG
    else:
        confidence = MatchConfidence.AMBIGUOUS
    return RecordMatch(
        record.id,
        book.id,
        confidence,
        tuple(dict.fromkeys(reasons)),
        tuple(conflicts),
        tuple(evidence),
        count,
    )


def compare_candidates(
    record: BookRecord,
    candidates: Sequence[MADBRecordBundle],
    *,
    truncated: bool = False,
    warnings: Sequence[str] = (),
) -> LinkageResult:
    """Pure comparison over the supplied candidate set (not global MADB uniqueness).

    Callers must mark incomplete discovery truncated. Repeated identical snapshots
    are deduplicated; contradictory snapshots of the same ID are rejected.
    """
    bundles: dict[str, MADBRecordBundle] = {}
    for bundle in candidates:
        if bundle.book.id in bundles and bundles[bundle.book.id] != bundle:
            raise ValueError("Conflicting snapshots of the same MADB Book")
        bundles[bundle.book.id] = bundle
    bundles = dict(sorted(bundles.items()))
    messages = list(warnings)
    if truncated:
        messages.append("MADB candidate discovery truncated; ISBN uniqueness is not established")
    if len(bundles) > 1:
        messages.append(f"{len(bundles)} distinct MADB candidates retained; no first-result selection")
    for bundle in bundles.values():
        messages.extend(bundle.warnings)
        if bundle.book.completeness != "complete":
            messages.append(f"{bundle.book.id}: Book evidence incomplete")
    matches = tuple(
        match
        for bundle in bundles.values()
        if (match := _evaluate(record, bundle, len(bundles), truncated)) is not None
    )
    exact = [match for match in matches if match.confidence == MatchConfidence.EXACT]
    strong = [match for match in matches if match.confidence == MatchConfidence.STRONG]
    if len(exact) > 1:
        status = LinkageStatus.AMBIGUOUS
        matches = tuple(
            replace(m, confidence=MatchConfidence.AMBIGUOUS) if m in exact else m for m in matches
        )
        messages.append("Multiple Books assert the same direct NDL identity")
    elif exact or strong:
        status = LinkageStatus.MATCHED
        winner = (exact or strong)[0]  # Exactly one evidence-qualified candidate, never search ordering.
        matches = tuple(
            replace(m, series=compare_series(record, bundles[m.madb_id])) if m == winner else m
            for m in matches
        )
    elif any(m.confidence == MatchConfidence.AMBIGUOUS for m in matches) or truncated:
        status = LinkageStatus.AMBIGUOUS
    elif matches:
        status = LinkageStatus.UNSAFE
    elif any(b.book.completeness != "complete" for b in bundles.values()):
        status = LinkageStatus.AMBIGUOUS
    else:
        status = LinkageStatus.UNMATCHED
    return LinkageResult(
        status,
        matches,
        tuple(CandidateSummary(b.book.id, b.book.uri, b.completeness) for b in bundles.values()),
        tuple(dict.fromkeys(messages)),
        truncated=truncated,
    )


def link_ndl_record(record: BookRecord, madb_source: MADBSource, *, refresh: bool = False) -> LinkageResult:
    """Explicit ISBN discovery, then pure comparison. Never called by the Talker.

    All distinct valid ISBNs are queried using the existing source's 10/13 query.
    Any discovery/Book failure makes the overall result unavailable, retaining
    completed evidence but withholding automatic Series comparison.
    """
    isbns = sorted({value for raw in record.isbns if (value := isbn13(raw))})
    discovered: dict[str, CandidateSummary] = {}
    bundles = []
    warnings: list[str] = []
    truncated = False
    try:
        for value in isbns:
            page = madb_source.search_by_isbn(value, refresh=refresh)
            truncated |= page.truncated
            warnings.extend(page.warnings)
            for candidate in page.records:
                discovered[candidate.id] = CandidateSummary(candidate.id, candidate.uri)
        for candidate in sorted(discovered.values(), key=lambda item: item.id):
            bundle = madb_source.get(candidate.id, refresh=refresh)
            if bundle.book.id != candidate.id or bundle.book.uri != candidate.uri:
                raise MADBError("schema", "Retrieved Book differs from discovered candidate")
            bundles.append(bundle)
            discovered[candidate.id] = replace(candidate, completeness=bundle.completeness)
    except MADBError as exc:
        # Retain observations without invoking Series comparison on a failed run.
        matches = tuple(
            match
            for bundle in bundles
            if (match := _evaluate(record, bundle, len(discovered), True)) is not None
        )
        if sum(m.confidence == MatchConfidence.EXACT for m in matches) > 1:
            matches = tuple(
                replace(m, confidence=MatchConfidence.AMBIGUOUS)
                if m.confidence == MatchConfidence.EXACT
                else m
                for m in matches
            )
        for bundle in bundles:
            warnings.extend(bundle.warnings)
        if truncated:
            warnings.append("MADB candidate discovery truncated; ISBN uniqueness is not established")
        warnings.append("MADB acquisition failed; candidate evaluation and ISBN uniqueness are incomplete")
        return LinkageResult(
            LinkageStatus.UNAVAILABLE,
            matches,
            tuple(discovered[key] for key in sorted(discovered)),
            tuple(dict.fromkeys(warnings)),
            LinkageError(exc.kind, exc.desc, exc.status, exc.retry_after),
            truncated=truncated,
        )
    return compare_candidates(record, bundles, truncated=truncated, warnings=warnings)
