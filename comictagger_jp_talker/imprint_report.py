"""Pure diagnostics for acquired evidence; never an authority or save permit.

The v1 JSON schema explicitly names every field of the immutable evidence graph.
Repeated snapshots are intentional: source outcomes, the run ledger and evaluator
inputs have distinct meanings even when they reference the same Python object.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime
from enum import Enum
from types import UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

from comictagger_jp_talker import __version__, acquisition, linkage, linked_acquisition, provenance
from comictagger_jp_talker import imprint_candidates as imprint
from comictagger_jp_talker.mapping import ResolvedNumber
from comictagger_jp_talker.sources import madb_models as madb
from comictagger_jp_talker.sources.madb_acquisition import MADBAcquisition

SCHEMA_VERSION = "imprint-report-v1"


class BookEvaluationState(str, Enum):
    EVALUATED = "evaluated"
    EXCLUDED = "excluded_from_linkage"
    BUNDLE_UNAVAILABLE = "bundle_unavailable"


@dataclass(frozen=True, kw_only=True)
class ImprintBookDiagnostic:
    """Index addresses the ledger, not a dictionary keyed by possibly conflicting ID.

    Excluded bundles retain classification but never undergo identity comparison
    or eligibility evaluation. Missing bundles have neither kind of result.
    """

    book_index: int
    state: BookEvaluationState
    excluded_classification: imprint.ImprintClassification | None = None
    evaluation: imprint.ImprintEligibility | None = None


@dataclass(frozen=True, kw_only=True)
class ImprintDiagnosticReport:
    acquisition: linked_acquisition.LinkedAcquisitionContext
    linkage: linkage.LinkageResult
    books: tuple[ImprintBookDiagnostic, ...]
    schema_version: Literal["imprint-report-v1"] = SCHEMA_VERSION
    plugin_version: str = __version__
    identity_algorithm_version: Literal["phase2b2-v1"] = linkage.ALGORITHM_VERSION
    evaluator_version: Literal["phase2c2b-v1"] = imprint.EVALUATION_VERSION
    operation: Literal["READ_ONLY"] = "READ_ONLY"
    authority_state: Literal["not_supplied"] = "not_supplied"
    authority_authenticity_assessed: Literal[False] = False
    authority_scope_assessed: Literal[False] = False
    authority_validity_assessed: Literal[False] = False
    archive_state: Literal["not_supplied"] = "not_supplied"
    target_known: Literal[False] = False
    existing_value_assessed: Literal[False] = False
    apply_allowed: Literal[False] = False
    writes_performed: Literal[False] = False
    # No aggregate origin time or digest is derivable from separate responses.
    snapshot_simultaneity: Literal["unknown"] = "unknown"
    parsed_snapshot_digest: None = None
    run_id_kind: Literal["local_correlation_id"] = "local_correlation_id"
    response_sha256_kind: Literal["response_body_bytes"] = "response_body_bytes"


def _check_evidence(evidence: linkage.LinkedRecordEvidence) -> None:
    ledger = evidence.acquisition_context
    if tuple(book.bundle for book in ledger.books if book.included_in_linkage) != evidence.bundles:
        raise ValueError("Accepted bundles differ from the ordered Book ledger")
    traces = []
    for attempt in ledger.discovery.attempts:
        if attempt.acquisition is not None:
            outcome = attempt.acquisition
            if outcome.value != attempt.page or outcome.error != attempt.error:
                raise ValueError("Discovery outcome differs from its ledger entry")
            traces.append(outcome.trace)
    for book in ledger.books:
        if book.included_in_linkage and (
            book.bundle is None
            or book.error is not None
            or (book.bundle.book.id, book.bundle.book.uri) != (book.book_id, book.book_uri)
        ):
            raise ValueError("Accepted Book differs from discovery")
        if book.context.discovery != ledger.discovery.state:
            raise ValueError("Book discovery context differs from the run")
        if book.acquisition is not None:
            if book.acquisition.value != book.bundle:
                raise ValueError("Book outcome differs from its ledger entry")
            if replace(book.acquisition.context, discovery=ledger.discovery.state) != book.context:
                raise ValueError("Book context differs from its source outcome")
            traces.append(book.acquisition.trace)
    if tuple(traces) != ledger.traces:
        raise ValueError("Run traces differ from ordered source outcomes")


def describe_imprint_evidence(evidence: linkage.LinkedRecordEvidence) -> ImprintDiagnosticReport:
    """Describe one immutable run without I/O, clock reads or metadata changes.

    existing_imprint=None is solely an evaluator input, never an observation of
    a missing archive value. The report explicitly withholds all save permission.
    """
    _encode(evidence, linkage.LinkedRecordEvidence)
    _check_evidence(evidence)
    results = []
    for index, book in enumerate(evidence.acquisition_context.books):
        if book.bundle is None:
            results.append(
                ImprintBookDiagnostic(book_index=index, state=BookEvaluationState.BUNDLE_UNAVAILABLE)
            )
            continue
        classification = imprint.classify_imprint_terms(
            imprint.extract_imprint_evidence(book.bundle, book.context)
        )
        if not book.included_in_linkage:
            results.append(
                ImprintBookDiagnostic(
                    book_index=index,
                    state=BookEvaluationState.EXCLUDED,
                    excluded_classification=classification,
                )
            )
            continue
        comparison = imprint.compare_imprint_candidates(
            classification, evidence.acquisition_context.ndl_input.to_record()
        )
        evaluation = imprint.evaluate_imprint_eligibility(
            evidence.linkage, comparison, authority_evidence=(), existing_imprint=None
        )
        if (
            evaluation.authority
            or evaluation.state == imprint.ImprintEligibilityState.ELIGIBLE
            or any(
                t.semantic_kind == imprint.ImprintSemanticKind.VERIFIED_LABEL for t in classification.terms
            )
        ):
            raise ValueError("Evaluator violated the unsupplied-authority contract")
        results.append(
            ImprintBookDiagnostic(
                book_index=index, state=BookEvaluationState.EVALUATED, evaluation=evaluation
            )
        )
    report = ImprintDiagnosticReport(
        acquisition=evidence.acquisition_context, linkage=evidence.linkage, books=tuple(results)
    )
    # Validate the output contract too; programming errors must not become HOLD.
    report_to_json_data(report)
    return report


# Explicit v1 field lists. Never derive JSON keys with asdict()/vars(); upstream
# model changes require a deliberate schema decision instead of silent drift.
_FIELDS = {
    ImprintDiagnosticReport: (
        "acquisition linkage books schema_version plugin_version identity_algorithm_version "
        "evaluator_version "
        "operation authority_state authority_authenticity_assessed authority_scope_assessed "
        "authority_validity_assessed archive_state target_known existing_value_assessed apply_allowed "
        "writes_performed snapshot_simultaneity parsed_snapshot_digest run_id_kind response_sha256_kind"
    ),
    ImprintBookDiagnostic: "book_index state excluded_classification evaluation",
    linkage.LinkedRecordEvidence: "linkage bundles acquisition_context",
    linked_acquisition.LinkedAcquisitionContext: (
        "run_id started_at finished_at scope ndl_input discovery books traces issues"
    ),
    linked_acquisition.NDLInputSnapshot: (
        "id url title isbns volumes publishers editions issued dates series_titles"
    ),
    linked_acquisition.DiscoveryAcquisition: "planned_isbns attempts state truncated reasons",
    linked_acquisition.ISBNDiscovery: "isbn state reason page acquisition error",
    linked_acquisition.BookAcquisitionContext: (
        "book_id book_uri context reason acquisition bundle error included_in_linkage"
    ),
    acquisition.AcquisitionContext: (
        "discovery book series relations resources agents holdings request_id acquired_at medium "
        "book_series_scope"
    ),
    acquisition.ResourceAcquisition: "uri state",
    acquisition.AcquisitionFailure: "kind message status retry_after",
    acquisition.AcquisitionEvent: (
        "stage state reason kind observed_at uri parent_uri predicate statement statement_index isbn "
        "namespace query_key started_at origin_fetched_at cache_stored_at response_sha256 limit "
        "status retry_after error"
    ),
    acquisition.AcquisitionTrace: "run_id started_at finished_at events",
    MADBAcquisition: "value context trace error",
    linkage.LinkageResult: "status matches candidates warnings error truncated",
    linkage.RecordMatch: (
        "ndl_id madb_id confidence reasons conflicts evidence candidate_count algorithm_version series"
    ),
    linkage.CandidateSummary: "id uri completeness",
    linkage.LinkageError: "kind message status retry_after",
    provenance.FieldEvidence: (
        "source field value raw_value record_id record_uri predicate_or_path transform related_uri"
    ),
    provenance.SeriesComparison: (
        "state ndl madb normalized_ndl normalized_madb relations ndl_number warnings name_classifications"
    ),
    provenance.SeriesNameClassification: "series_uri display_names readings other_names",
    ResolvedNumber: "value explicit inferred conflict requested source",
    madb.RDFTerm: "kind value datatype language",
    madb.MADBStatement: "subject predicate object",
    madb.MADBCredit: "raw source_predicate name_candidate role_raw agent_uri association",
    madb.ExternalIdentifier: "scheme raw normalized subject_uri predicate provider",
    madb.MADBRecordBundle: "book series agents holdings warnings completeness retrieval_scope",
    madb.MADBBookRecord: (
        "id uri types titles alternative_titles subtitles display_labels volumes positions isbns editions "
        "publication_dates publishers publisher_references labels series_statements series_uris credits "
        "creator_references languages genres extent external_identifiers statements completeness"
    ),
    madb.MADBSeriesRecord: (
        "id uri types titles alternative_titles publishers publisher_references labels credits "
        "creator_references editions publication_dates number_of_items statements completeness"
    ),
    madb.MADBAgentRecord: "uri names classifications ndla external_identifiers statements completeness",
    madb.MADBHoldingRecord: (
        "uri book_uri provider_names material_identifiers owner_identifiers notes external_identifiers "
        "statements completeness"
    ),
    madb.MADBSearchPage: "records truncated warnings",
    madb.MADBSearchResult: "id uri identifiers isbns",
    imprint.ImprintCandidate: "origin evidence statements statement_indices label_indices related_to_book",
    imprint.ImprintExtraction: "bundle acquisition candidates relations expected_series_uris blockers",
    imprint.ClassifiedImprintTerm: "candidate role display equality_key semantic_kind reasons",
    imprint.ImprintClassification: "extraction terms blockers",
    imprint.ContextComparison: "field book series ndl conflict unresolved",
    imprint.ImprintComparison: (
        "state classification ndl_id ndl_url ndl_isbns ndl_dates book_displays series_displays book_values "
        "series_values book_keys series_keys normalized_set_equal overlap ndl_series_titles ndl_overlap "
        "publisher edition required_series_states blockers"
    ),
    imprint.ImprintEligibility: (
        "state selected_candidate reasons comparison linkage authority evaluation_version"
    ),
    # Authority is required to be empty in R1. Its populated types are deliberately
    # unsupported, so serialization cannot accidentally accept a supplied verifier.
}
_SCHEMA = {cls: tuple(names.split()) for cls, names in _FIELDS.items()}
_HINTS = {cls: get_type_hints(cls) for cls in _SCHEMA}
_TIMES = {"started_at", "finished_at", "observed_at", "origin_fetched_at", "cache_stored_at", "acquired_at"}


def _accepts(value: object, expected: object) -> bool:
    origin, args = get_origin(expected), get_args(expected)
    if origin in (Union, UnionType):
        return any(_accepts(value, item) for item in args)
    if origin is Literal:
        return any(type(value) is type(item) and value == item for item in args)
    if origin is tuple:
        return type(value) is tuple
    return type(value) is expected


def _encode(value: object, expected: object) -> object:
    """Strict closed-schema conversion; floats, mutable and unknown types fail."""
    if not _accepts(value, expected):
        raise TypeError(f"Invalid report field type: expected {expected}, got {type(value).__name__}")
    origin, args = get_origin(expected), get_args(expected)
    if origin in (Union, UnionType):
        return _encode(value, next(item for item in args if _accepts(value, item)))
    if value is None or type(value) in (str, bool, int):
        return value
    if isinstance(value, Enum):
        if type(value.value) is not str:
            raise TypeError("Report enums require string values")
        return value.value
    if origin is tuple:
        if len(args) != 2 or args[1] is not Ellipsis:
            raise TypeError("Unsupported report tuple annotation")
        return [_encode(item, args[0]) for item in value]
    cls = type(value)
    if cls not in _SCHEMA:
        raise TypeError(f"Unsupported report type: {cls.__name__}")
    if tuple(field.name for field in fields(cls)) != _SCHEMA[cls]:
        raise ValueError(f"Report schema drift: {cls.__name__}")
    result = {}
    for name in _SCHEMA[cls]:
        item = getattr(value, name)
        result[name] = _encode(item, _HINTS[cls][name])
        if name in _TIMES and item is not None:
            # Existing evidence stores ISO strings, not datetime objects. Preserve
            # the original offset and spelling; reject naive/invalid times.
            instant = datetime.fromisoformat(item.replace("Z", "+00:00"))
            if "T" not in item or instant.utcoffset() is None:
                raise ValueError(f"Timezone-aware ISO 8601 required: {name}")
    return result


def report_to_json_data(report: ImprintDiagnosticReport) -> dict[str, object]:
    """Return fresh JSON data, preserving raw Unicode and all ordered evidence.

    No renderer, JSON text, current timestamp, I/O or implicit string coercion.
    All float values (including NaN/Infinity) and unknown types are rejected.
    """
    data = _encode(report, ImprintDiagnosticReport)
    _check_evidence(
        linkage.LinkedRecordEvidence(
            report.linkage,
            tuple(book.bundle for book in report.acquisition.books if book.included_in_linkage),
            report.acquisition,
        )
    )
    if len(report.books) != len(report.acquisition.books):
        raise ValueError("Report diagnostics do not cover every Book")
    for index, (diagnostic, book) in enumerate(zip(report.books, report.acquisition.books, strict=True)):
        if diagnostic.book_index != index:
            raise ValueError("Report Book order differs from the ledger")
        decision = diagnostic.evaluation
        excluded = diagnostic.excluded_classification
        if book.bundle is None:
            valid = (
                diagnostic.state == BookEvaluationState.BUNDLE_UNAVAILABLE and decision is excluded is None
            )
        elif not book.included_in_linkage:
            valid = (
                diagnostic.state == BookEvaluationState.EXCLUDED
                and decision is None
                and excluded is not None
                and excluded.extraction.bundle == book.bundle
                and excluded.extraction.acquisition == book.context
            )
        else:
            valid = (
                diagnostic.state == BookEvaluationState.EVALUATED
                and excluded is None
                and decision is not None
                and decision.linkage == report.linkage
                and decision.comparison.classification.extraction.bundle == book.bundle
                and decision.comparison.classification.extraction.acquisition == book.context
                and not decision.authority
                and decision.state != imprint.ImprintEligibilityState.ELIGIBLE
                and decision.evaluation_version == report.evaluator_version
            )
        if not valid:
            raise ValueError("Report evaluation differs from its Book ledger or read-only contract")
    return data
