"""Optional metadata acquisition, followed by the existing Series-only policy."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from comicapi.genericmetadata import GenericMetadata

from comictagger_jp_talker.linkage import LinkageStatus, acquire_linked_record_evidence
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.series_supplement_policy import apply_series_supplement
from comictagger_jp_talker.sources.madb import MADBSource
from comictagger_jp_talker.sources.madb_models import MADBError

# Preserve the existing optional-Series log category as well as its messages.
logger = logging.getLogger("comictagger_jp_talker.series_supplement")


def supplement_metadata(
    metadata: GenericMetadata,
    record: BookRecord,
    cache_folder: Path,
    *,
    series_enabled: bool = False,
) -> GenericMetadata:
    """Acquire once when needed, close, then apply only the existing Series policy."""
    need_series = series_enabled and not (metadata.series or "").strip()
    if not need_series:
        return metadata
    try:
        with MADBSource(cache_folder) as source:
            evidence = acquire_linked_record_evidence(record, source, scope="series_linkage")
        result = evidence.linkage
        if result.status == LinkageStatus.UNAVAILABLE:
            logger.warning("Optional MADB Series supplement unavailable: %s", result.error)
        for warning in result.warnings:
            logger.warning("Optional MADB Series supplement: %s", warning)
        return apply_series_supplement(metadata, result)
    except (MADBError, OSError, sqlite3.Error) as exc:
        # Do not invoke report_error/latest-error.txt, which describe NDL fetch failures.
        logger.warning("Optional MADB Series supplement failed; retaining NDL metadata: %s", exc)
        return metadata
