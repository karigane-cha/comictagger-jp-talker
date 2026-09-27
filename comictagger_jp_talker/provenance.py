"""Internal cross-source evidence and Series observation; never metadata selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from comictagger_jp_talker.mapping import ResolvedNumber, infer_volume, resolve_record_number
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.sources.madb_models import MADBRecordBundle, RDFTerm
from comictagger_jp_talker.sources.madb_parser import terms
from comictagger_jp_talker.sources.madb_queries import SCHEMA_NS


class EvidenceSource(str, Enum):
    NDL = "ndl"
    MADB = "madb"


@dataclass(frozen=True)
class FieldEvidence:
    source: EvidenceSource
    field: str
    value: str | None
    raw_value: str | RDFTerm
    record_id: str
    record_uri: str | None
    predicate_or_path: str
    transform: str | None = None
    related_uri: str | None = None


class FieldComparisonState(str, Enum):
    NDL_ONLY = "ndl_only"
    MADB_ONLY = "madb_only"
    BOTH_AGREE = "both_agree"
    BOTH_CONFLICT = "both_conflict"
    NONE = "none"
    MULTIPLE = "multiple"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class SeriesComparison:
    state: FieldComparisonState
    ndl: FieldEvidence
    madb: tuple[FieldEvidence, ...]
    normalized_ndl: str | None
    normalized_madb: tuple[str, ...]
    relations: tuple[FieldEvidence, ...]
    ndl_number: ResolvedNumber
    warnings: tuple[str, ...] = ()


def compare_series(record: BookRecord, bundle: MADBRecordBundle) -> SeriesComparison:
    """Observe an already-linked pair. This pure function does not establish identity.

    All language variants remain candidates, including readings: there is no
    language preference policy yet. Missing/unresolved resources are not absence.
    """
    inferred, _ = infer_volume(record.title)
    ndl = FieldEvidence(
        EvidenceSource.NDL,
        "series",
        inferred or None,
        record.title,
        record.id,
        record.url or None,
        "BookRecord.title",
        "mapping.infer_volume",
    )
    book = bundle.book
    raw_relations = terms(book.statements, SCHEMA_NS + "isPartOf")
    relations = tuple(
        FieldEvidence(
            EvidenceSource.MADB,
            "series_relation",
            term.value,
            term,
            book.id,
            book.uri,
            SCHEMA_NS + "isPartOf",
        )
        for term in raw_relations
    )
    expected = set(book.series_uris)
    related = tuple(series for series in bundle.series if series.uri in expected)
    evidence = tuple(
        FieldEvidence(
            EvidenceSource.MADB,
            "series",
            term.value if term.kind == "literal" else None,
            term,
            book.id,
            book.uri,
            SCHEMA_NS + "isPartOf / " + SCHEMA_NS + "name",
            related_uri=series.uri,
        )
        for series in related
        for term in series.titles
    )
    ndl_key = inferred.strip() or None
    madb_keys = tuple(dict.fromkeys(e.value.strip() for e in evidence if e.value and e.value.strip()))
    warnings = list(bundle.warnings)
    incomplete = (
        book.completeness != "complete"
        or expected != {series.uri for series in related}
        or any(term.kind != "uri" or term.value not in expected for term in raw_relations)
        or any(series.completeness != "complete" for series in related)
        or any(e.raw_value.kind != "literal" for e in evidence)
    )
    if incomplete:
        state = FieldComparisonState.UNAVAILABLE
        warnings.append("Series evidence is incomplete; missing values are not established absence")
    elif len(expected) > 1 or len(madb_keys) > 1:
        state = FieldComparisonState.MULTIPLE
        warnings.append("Multiple Series relations or distinct names; no name/language is selected")
    elif ndl_key and madb_keys:
        state = (
            FieldComparisonState.BOTH_AGREE if madb_keys == (ndl_key,) else FieldComparisonState.BOTH_CONFLICT
        )
    elif ndl_key:
        state = FieldComparisonState.NDL_ONLY
    elif madb_keys:
        state = FieldComparisonState.MADB_ONLY
    else:
        state = FieldComparisonState.NONE
    return SeriesComparison(
        state,
        ndl,
        evidence,
        ndl_key,
        madb_keys,
        relations,
        resolve_record_number(record),
        tuple(dict.fromkeys(warnings)),
    )
