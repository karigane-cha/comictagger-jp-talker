"""Copyable diagnostics through the host's existing error dialog and logging."""

from __future__ import annotations

import logging
import threading
import traceback
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import requests
from comictalker.comictalker import TalkerError, TalkerNetworkError

from comictagger_jp_talker import __version__
from comictagger_jp_talker import http_diagnostics as diagnostics

logger = logging.getLogger(__name__)
_LOCK = threading.Lock()


def report_error(error: Exception, cache_folder: Path, context: str) -> str:
    """Keep host exception codes, add a copy hint, and retain the latest traceback.

    Windows QMessageBox supports Ctrl+C without changing ComicTagger or adding a
    GUI. The root logger also feeds ComicTagger's standard application log window.
    """
    if getattr(error, "_jpbooks_reported", False):
        return str(error)
    http_failure = isinstance(error, TalkerNetworkError) and (
        isinstance(getattr(error, "_jpbooks_http_failure", None), diagnostics.HttpFailure)
        or isinstance(error.__cause__, requests.RequestException)
    )
    if http_failure:
        context = context.split("(", 1)[0]
    report = (
        f"Japanese Books {__version__}\n"
        f"UTC: {datetime.now(timezone.utc).isoformat()}\n"
        f"Operation: {context}\n"
        + (
            diagnostics.safe_failure_report(error)
            if http_failure
            else "API: https://ndlsearch.ndl.go.jp/api/sru\n"
            "Summary API: https://ndlsearch.ndl.go.jp/api/bib/external/search\n\n"
            + "".join(traceback.format_exception(type(error), error, error.__traceback__))
        )
    )
    logger.error("%s", report)
    path = cache_folder / "jpbooks" / "latest-error.txt"
    try:
        with _LOCK:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding="utf-8", errors="backslashreplace")
        location = f"詳細ログ: {path.resolve()}"
    except OSError:
        # Failure to write a diagnostic must not mask the original failure.
        logger.warning("Could not save Japanese Books error log", exc_info=not http_failure)
        location = "詳細ログは ComicTagger のログ画面を参照してください。"
    hint = (
        "\n\nこの画面を選択して Ctrl+C でエラー全文をコピーできます。\n"
        + location
        + f"\nOperation: {context}"
    )
    if isinstance(error, TalkerError):
        error.desc += hint
        error._jpbooks_reported = True
        return str(error)
    return str(error) + hint


def copyable_errors(method):
    """Report at public Talker boundaries; nested calls log each error only once."""

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        operation = "search" if method.__name__.startswith("search") else "get"
        with diagnostics.operation_scope(operation, method.__name__):
            try:
                return method(self, *args, **kwargs)
            except TalkerError as error:
                # The HTTP report strips arguments; other errors retain existing diagnostics.
                inputs = [repr(v) for v in args if isinstance(v, str)]
                inputs.extend(f"{k}={v!r}" for k, v in kwargs.items() if isinstance(v, str))
                report_error(error, self.cache_folder, f"{method.__name__}({', '.join(inputs)})")
                raise

    return wrapped
