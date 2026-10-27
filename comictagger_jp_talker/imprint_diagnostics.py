"""Explicit, single-record read-only diagnostics; never called by the Talker."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import unicodedata
from contextlib import ExitStack, contextmanager
from pathlib import Path

from comictalker.comictalker import TalkerDataError, TalkerNetworkError

from comictagger_jp_talker import __version__
from comictagger_jp_talker.acquisition import AcquisitionState as State
from comictagger_jp_talker.imprint_report import (
    ImprintDiagnosticReport,
    describe_imprint_evidence,
    report_to_json_data,
)
from comictagger_jp_talker.linkage import LinkedRecordEvidence, acquire_linked_record_evidence
from comictagger_jp_talker.sources.madb import MADBSource
from comictagger_jp_talker.sources.madb_models import MADBError
from comictagger_jp_talker.sources.ndl import NDLSource


class AcquisitionError(Exception):
    """External source failure before a reportable evidence graph exists."""


class ResourceCloseError(Exception):
    def __init__(self, primary, failures):
        self.primary = primary
        self.failures = tuple(failures)
        super().__init__("Resource cleanup failed")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # Unknown options/choices can contain terminal control characters too.
        super().error(json.dumps(message, ensure_ascii=True))


def parse_args(argv=None):
    parser = _Parser(
        description="Read-only Imprint diagnostics for one NDL record. No archive or save operation.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--ndl-id", required=True, action="append", help="One NDL bibliographic ID (not a URL)"
    )
    parser.add_argument(
        "--allow-network", action="store_true", help="Permit NDL/MADB requests and source cache I/O"
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    validate_request(parser, args)
    return args


def validate_request(parser, args):
    if len(args.ndl_id) != 1:
        parser.error("Specify --ndl-id exactly once")
    args.ndl_id = args.ndl_id[0]
    # Same accepted ID grammar as NDLSource.get(); never accept URLs or CQL.
    if re.fullmatch(r"[A-Za-z0-9_-]+", args.ndl_id) is None:
        parser.error("Invalid NDL ID; expected [A-Za-z0-9_-]+")
    if not args.allow_network:
        parser.error("--allow-network is required (including permission for source cache I/O)")


def default_cache_folder() -> Path:
    """Resolve only after validation; independent of host settings/error history."""
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.environ.get("XDG_CACHE_HOME")
    return (Path(base) if base else Path.home() / ".cache") / "comictagger-jp-talker" / "imprint-diagnostics"


def acquire_diagnostic_evidence(
    ndl_id: str, cache_folder: Path, *, ndl_factory=NDLSource, madb_factory=MADBSource
) -> LinkedRecordEvidence:
    """Called only after CLI authorization. Close before pure reporting/output.

    NDL has no close/context-manager API: close its session and cache separately.
    MADB owns those resources: invoke its context exit once, never double-close.
    Constructors that raise before returning retain their existing limitations.
    """
    failures = []
    primary = None

    def close(label, action, *args):
        try:
            action(*args)
        except BaseException as exc:
            failures.append((label, exc))

    try:
        with ExitStack() as stack:
            ndl = ndl_factory(cache_folder)
            stack.callback(close, "NDL cache", ndl.cache.close)
            stack.callback(close, "NDL session", ndl.session.close)
            record = ndl.get(ndl_id, summary_mode="none")
            if record.id != ndl_id:
                raise AcquisitionError("NDL returned a different bibliographic ID")
            madb = madb_factory(cache_folder)
            # Register before enter so even a failing enter releases a constructed source.
            stack.push(lambda *exc: close("MADB exit/close", madb.__exit__, *exc))
            source = madb.__enter__()
            evidence = acquire_linked_record_evidence(record, source, refresh=False, scope="series_linkage")
    except BaseException as exc:
        primary = exc
    if failures:
        raise ResourceCloseError(primary, failures) from primary
    if primary is not None:
        if isinstance(primary, (TalkerNetworkError, TalkerDataError, MADBError, OSError, sqlite3.Error)):
            raise AcquisitionError(str(primary)) from primary
        raise primary
    return evidence


def acquisition_exit_code(report: ImprintDiagnosticReport) -> int:
    """Classify acquisition completeness, never HOLD/REJECT or identity confidence."""
    discovery = report.acquisition.discovery
    if (
        discovery.state == State.NOT_REQUESTED
        and discovery.reasons == ("no_valid_isbn",)
        and not discovery.planned_isbns
        and not report.acquisition.books
    ):
        return 0  # An intentional non-request; the report explicitly lacks MADB material.
    if discovery.state != State.COMPLETE or discovery.truncated:
        return 3
    for attempt in discovery.attempts:
        if attempt.error is not None or attempt.state != State.COMPLETE:
            return 3
    for book in report.acquisition.books:
        if book.bundle is None or book.error is not None:
            return 3
        context = book.context
        if context.book != State.COMPLETE or context.book_series_scope != State.COMPLETE:
            return 3
        if any(s not in (State.COMPLETE, State.NOT_RELATED) for s in (context.series, context.relations)):
            return 3
        if any(r.state != State.COMPLETE for r in context.resources):
            return 3
        if book.bundle.completeness != "complete" or any(
            r.completeness != "complete" for r in (book.bundle.book, *book.bundle.series)
        ):
            return 3
    return 0


def terminal_string(value: str) -> str:
    """A reversible JSON string literal with readable Japanese/non-BMP characters.

    Escape all controls, separators other than ASCII space, combining marks and
    the invisible Hangul fillers. No trim, replacement, or Unicode normalization.
    """
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    return "".join(
        json.dumps(char, ensure_ascii=True)[1:-1]
        if char != " "
        and (unicodedata.category(char)[0] in "CZM" or char in "\u115f\u1160\u2800\u3164\uffa0")
        else char
        for char in encoded
    )


def render_text(report: ImprintDiagnosticReport) -> str:
    data = report_to_json_data(report)
    ledger = report.acquisition
    lines = [
        "Read-only Imprint diagnostics",
        f"NDL ID: {terminal_string(ledger.ndl_input.id)}",
        f"Title: {terminal_string(ledger.ndl_input.title)}",
        f"ISBN: {', '.join(terminal_string(v) for v in ledger.ndl_input.isbns) or '(none)'}",
        f"Scope: {ledger.scope}",
        f"Run ID: {terminal_string(ledger.run_id)}",
        f"Discovery: {ledger.discovery.state.value}",
        f"Linkage: {report.linkage.status.value}",
        f"Candidates: {len(ledger.books)}",
        "Authority: not supplied",
        "Archive: not supplied",
        "Existing Imprint: not assessed",
        "Apply allowed: no",
        "Writes performed: no",
        "Origin timestamp: unknown wherever origin_fetched_at is null; cache is not an origin clock.",
    ]
    if ledger.discovery.reasons == ("no_valid_isbn",):
        lines.append("No valid ISBN: diagnosis completed without MADB candidate evaluation material.")
    for diagnostic in report.books:
        book = ledger.books[diagnostic.book_index]
        decision = diagnostic.evaluation.state.value if diagnostic.evaluation is not None else "not evaluated"
        lines.append(
            f"Book [{diagnostic.book_index}] {terminal_string(book.book_id)}: "
            f"acquisition={book.context.book.value}; evaluation={diagnostic.state.value}; "
            f"eligibility={decision}"
        )
    lines.extend(("", "Complete report detail (no display truncation; indices preserve ledger order):"))

    def append(value, indent):
        if type(value) is dict:
            for key, item in value.items():
                entry(key, item, indent)
        elif type(value) is list:
            for index, item in enumerate(value):
                entry(f"[{index}]", item, indent)
        else:
            raise TypeError("Expected report container")

    def entry(label, value, indent):
        prefix = " " * indent + label + ":"
        if isinstance(value, (dict, list)) and value:
            lines.append(prefix)
            append(value, indent + 2)
        else:
            scalar = terminal_string(value) if isinstance(value, str) else json.dumps(value, allow_nan=False)
            lines.append(prefix + " " + scalar)

    append(data, 0)
    return "\n".join(lines) + "\n"


def render_json(report: ImprintDiagnosticReport) -> str:
    return json.dumps(report_to_json_data(report), ensure_ascii=True, allow_nan=False, indent=2) + "\n"


@contextmanager
def _quiet_logging():
    # A standalone single-threaded command. Suppression also covers handlers that
    # captured stdout before main(); redirect_stdout alone would not cover them.
    previous = logging.root.manager.disable
    logging.disable(sys.maxsize)
    try:
        yield
    finally:
        logging.disable(previous)


def _error_details(error, seen=None):
    seen = set() if seen is None else seen
    if id(error) in seen:
        return
    seen.add(id(error))
    if isinstance(error, ResourceCloseError):
        if error.primary is not None:
            yield from _error_details(error.primary, seen)
        for label, failure in error.failures:
            yield label
            yield from _error_details(failure, seen)
    else:
        yield f"{type(error).__name__}: {error}"
        if error.__cause__ is not None:
            yield from _error_details(error.__cause__, seen)
        elif error.__context__ is not None and not error.__suppress_context__:
            yield from _error_details(error.__context__, seen)


def _interrupted(error, seen=None):
    seen = set() if seen is None else seen
    if error is None or id(error) in seen:
        return False
    seen.add(id(error))
    if isinstance(error, KeyboardInterrupt):
        return True
    if isinstance(error, ResourceCloseError):
        return _interrupted(error.primary, seen) or any(_interrupted(e, seen) for _, e in error.failures)
    cause = error.__cause__
    if cause is None and not error.__suppress_context__:
        cause = error.__context__
    return _interrupted(cause, seen)


def main(argv=None, *, ndl_factory=NDLSource, madb_factory=MADBSource) -> int:
    try:
        try:
            args = parse_args(argv)
        except SystemExit as exc:
            sys.stdout.flush()
            sys.stderr.flush()
            return int(exc.code)
        with _quiet_logging():
            evidence = acquire_diagnostic_evidence(
                args.ndl_id, default_cache_folder(), ndl_factory=ndl_factory, madb_factory=madb_factory
            )
            report = describe_imprint_evidence(evidence)
            code = acquisition_exit_code(report)
            output = render_json(report) if args.format == "json" else render_text(report)
        # Serialization and cleanup must finish before a single report is written.
        count = sys.stdout.write(output)
        if count != len(output):
            raise OSError("Incomplete stdout write")
        sys.stdout.flush()
        return code
    except (Exception, KeyboardInterrupt) as exc:
        code = 130 if _interrupted(exc) else 3 if isinstance(exc, AcquisitionError) else 4
        try:
            # ASCII JSON quoting also makes external exception messages terminal-safe.
            sys.stderr.write("Imprint diagnostics error: " + json.dumps(list(_error_details(exc))) + "\n")
            sys.stderr.flush()
        except (OSError, UnicodeError):
            pass  # The nonzero process status still reports an unsuccessful command.
        return code


if __name__ == "__main__":
    exit_code = main()
    if exit_code in (4, 130):
        # A failed flush can leave buffered bytes pending. Close at the process
        # boundary so interpreter shutdown does not replace our status with 120.
        try:
            sys.stdout.close()
        except (Exception, KeyboardInterrupt):
            pass
    raise SystemExit(exit_code)
