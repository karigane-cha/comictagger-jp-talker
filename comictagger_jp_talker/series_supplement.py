"""Opt-in, missing-Series-only policy over the existing linkage/evidence API."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import replace
from pathlib import Path

from comicapi.genericmetadata import GenericMetadata

from comictagger_jp_talker.linkage import (
    LinkageResult,
    LinkageStatus,
    MatchConfidence,
    link_ndl_record_for_series,
)
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.provenance import FieldComparisonState
from comictagger_jp_talker.sources.madb import MADBSource
from comictagger_jp_talker.sources.madb_models import MADBError

logger = logging.getLogger(__name__)


def apply_series_supplement(metadata: GenericMetadata, result: LinkageResult) -> GenericMetadata:
    """Pure output transformation. All structured evidence stays in result.

    Truncated discovery is rejected even for direct identity: automatic output
    follows a stricter boundary than the explicit Phase 2B-2 comparison API.
    """
    if (metadata.series or "").strip() or result.status != LinkageStatus.MATCHED or result.truncated:
        return metadata
    eligible = [
        m
        for m in result.matches
        if m.confidence in (MatchConfidence.EXACT, MatchConfidence.STRONG) and m.series is not None
    ]
    if len(eligible) != 1:
        return metadata
    match = eligible[0]
    comparison = match.series
    if comparison.state != FieldComparisonState.MADB_ONLY or len(comparison.name_classifications) != 1:
        return metadata
    classification = comparison.name_classifications[0]
    if len(classification.effective_display_values) != 1:
        return metadata
    display = next(e.value for e in classification.display_names if e.value and e.value.strip())
    # Never sanitize source display strings into a different value, or emit invalid XML.
    if any(
        ord(c) < 32 and c not in "\t\n\r" or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in (0xFFFE, 0xFFFF)
        for c in display
    ):
        return metadata
    reasons = ", ".join(reason.value for reason in match.reasons)
    lines = (
        f"MADB Series（補完）: {display}",
        f"MADB Book ID: {match.madb_id}",
        f"MADB Series ID: {classification.series_uri.rsplit('/', 1)[-1]}",
        f"MADB 照合: {match.confidence.value} ({reasons})",
    )
    notes = metadata.notes or ""
    existing = set(notes.splitlines())
    addition = "\n".join(line for line in lines if line not in existing)
    if addition:
        notes += ("\n" if notes and not notes.endswith("\n") else "") + addition
    return replace(metadata, series=display, notes=notes)


def supplement_series(
    metadata: GenericMetadata, record: BookRecord, cache_folder: Path, *, enabled: bool = False
) -> GenericMetadata:
    """Lazily acquire optional evidence and fail open to the NDL output."""
    if not enabled or (metadata.series or "").strip():
        return metadata
    try:
        with MADBSource(cache_folder) as source:
            result = link_ndl_record_for_series(record, source)
        if result.status == LinkageStatus.UNAVAILABLE:
            logger.warning("Optional MADB Series supplement unavailable: %s", result.error)
        for warning in result.warnings:
            logger.warning("Optional MADB Series supplement: %s", warning)
        return apply_series_supplement(metadata, result)
    except (MADBError, OSError, sqlite3.Error) as exc:
        # Do not invoke report_error/latest-error.txt, which describe NDL fetch failures.
        logger.warning("Optional MADB Series supplement failed; retaining NDL metadata: %s", exc)
        return metadata
