"""Compatibility entry points for the existing optional Series supplement."""

from __future__ import annotations

from pathlib import Path

from comicapi.genericmetadata import GenericMetadata

from comictagger_jp_talker.metadata_supplement import supplement_metadata
from comictagger_jp_talker.models import BookRecord
from comictagger_jp_talker.series_supplement_policy import apply_series_supplement as apply_series_supplement


def supplement_series(
    metadata: GenericMetadata, record: BookRecord, cache_folder: Path, *, enabled: bool = False
) -> GenericMetadata:
    """Keep the historical signature while delegating acquisition and application."""
    return supplement_metadata(metadata, record, cache_folder, series_enabled=enabled)
