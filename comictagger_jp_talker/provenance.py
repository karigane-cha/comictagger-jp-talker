"""Internal cross-source evidence and Series observation; never metadata selection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from comictagger_jp_talker.mapping import ResolvedNumber, infer_volume, resolve_record_number
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.sources.madb_models import MADBRecordBundle, RDFTerm
from comictagger_jp_talker.sources.madb_parser import terms
from comictagger_jp_talker.sources.madb_queries import RDF_NS, SCHEMA_NS, XSD_NS


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
class SeriesNameClassification:
    series_uri: str
    display_names: tuple[FieldEvidence, ...]
    readings: tuple[FieldEvidence, ...]
    other_names: tuple[FieldEvidence, ...]

    @property
    def effective_display_values(self) -> tuple[str, ...]:
        # Deduplicate within this resource only; evidence remains untouched.
        return tuple(
            dict.fromkeys(e.value.strip() for e in self.display_names if e.value and e.value.strip())
        )


def classify_series_names(series_uri: str, names: tuple[FieldEvidence, ...]) -> SeriesNameClassification:
    """Use explicit RDF language metadata, never script or title heuristics.

    Phase 2A C334830 and current fixtures establish untagged string displays.
    Unknown languages/datatypes remain unresolved, even beside a known display.
    """
    display, readings, other = [], [], []
    for evidence in names:
        term = evidence.raw_value
        if not isinstance(term, RDFTerm) or term.kind != "literal":
            other.append(evidence)
            continue
        language = term.language.casefold() if term.language else None
        if language in ("ja", "ja-hrkt") and term.datatype in (None, RDF_NS + "langString"):
            (readings if language == "ja-hrkt" else display).append(evidence)
        elif language is None and term.datatype in (None, XSD_NS + "string"):
            display.append(evidence)
        else:
            other.append(evidence)
    return SeriesNameClassification(series_uri, tuple(display), tuple(readings), tuple(other))


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
    name_classifications: tuple[SeriesNameClassification, ...] = ()


def compare_series(record: BookRecord, bundle: MADBRecordBundle) -> SeriesComparison:
    """Observe an already-linked pair. This pure function does not establish identity.

    Raw names remain evidence. Only supported displays are comparison values;
    recognized readings do not introduce ambiguity. Unresolved names block selection.
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
    classifications = tuple(
        classify_series_names(series.uri, tuple(e for e in evidence if e.related_uri == series.uri))
        for series in related
    )
    madb_keys = tuple(value for c in classifications for value in c.effective_display_values)
    unresolved_names = any(e.value and e.value.strip() for c in classifications for e in c.other_names)
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
    elif len(expected) > 1 or len(madb_keys) > 1 or unresolved_names:
        state = FieldComparisonState.MULTIPLE
        warnings.append("Multiple Series relations, distinct displays, or unsupported name classification")
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
        classifications,
    )
