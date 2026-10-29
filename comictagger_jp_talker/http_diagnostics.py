"""Opt-in HTTP observations; never retries, sleeps, or changes acquisition policy.

JPBOOKS_HTTP_DIAGNOSTICS is read once, at module import. Only the exact value
"1" enables detail; restart the host to change it. This logger uses the host's
existing handlers. Importing with diagnostics disabled changes no logger levels
and generates neither IDs nor clock reads.
"""

from __future__ import annotations

import contextlib
import contextvars
import json
import logging
import os
import re
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from functools import wraps

from comictalker.comictalker import TalkerDataError, TalkerNetworkError

logger = logging.getLogger(__name__)
_ENABLED = os.environ.get("JPBOOKS_HTTP_DIAGNOSTICS") == "1"
_IDS_LOCK = threading.Lock()
_RUN_ID: str | None = None
_OPERATION_SEQ = 0
MAX_HEADER_LENGTH = 128
MAX_RETRY_SECONDS = 2_147_483_647  # Diagnostic representation bound, never a delay policy.
QUERY_STAGES = frozenset({"initial", "relaxed_creator", "relaxed_issue", "relaxed_both"})


def enabled() -> bool:
    return _ENABLED


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


def exception_name(error: BaseException) -> str:
    name = type(error).__name__
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,63}", name) else "Exception"


def format_fields(fields: dict) -> str:
    def value(item):
        if isinstance(item, str) and re.fullmatch(r"[A-Za-z_0-9.:+-]+", item):
            return item
        return json.dumps(item, ensure_ascii=True, separators=(",", ":"))

    return " ".join(f"{key}={value(item)}" for key, item in fields.items())


def emit(event: str, **fields) -> None:
    # Diagnostic formatting/handlers must not replace an acquisition result.
    try:
        logger.debug("NDL %s: %s", event, format_fields(fields), extra={"ndl_event": event, "ndl": fields})
    except Exception:
        pass


@dataclass
class Operation:
    run_id: str
    operation_seq: int
    correlation_id: str
    operation: str
    entrypoint: str
    http_calls: int = 0
    outcome: str = "success"
    counter_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def fields(self) -> dict:
        return {
            "run_id": self.run_id,
            "operation_seq": self.operation_seq,
            "correlation_id": self.correlation_id,
            "operation": self.operation,
            "entrypoint": self.entrypoint,
        }


_CURRENT: contextvars.ContextVar[Operation | None] = contextvars.ContextVar("ndl_operation", default=None)
_STAGE: contextvars.ContextVar[str] = contextvars.ContextVar("ndl_query_stage", default="initial")
_CACHE: contextvars.ContextVar[str] = contextvars.ContextVar("ndl_cache", default="BYPASS")


@contextlib.contextmanager
def operation_scope(operation: str, entrypoint: str, *, join: bool = False):
    """Public calls are independent; only source-internal delegation joins a call.

    Context is created inside the executing worker, not inherited from a GUI
    thread. Explicitly copying a context to workers shares a locked HTTP counter.
    """
    global _RUN_ID, _OPERATION_SEQ
    if not enabled() or (join and _CURRENT.get() is not None):
        yield
        return
    with _IDS_LOCK:
        if _RUN_ID is None:
            _RUN_ID = _new_id()
        _OPERATION_SEQ += 1
        operation_context = Operation(_RUN_ID, _OPERATION_SEQ, _new_id(), operation, entrypoint)
    token = _CURRENT.set(operation_context)
    stage_token = _STAGE.set("initial")
    cache_token = _CACHE.set("BYPASS")
    emit("operation started", **operation_context.fields())
    try:
        yield
    except BaseException as error:
        operation_context.outcome = (
            "network_error"
            if isinstance(error, TalkerNetworkError)
            else "data_error"
            if isinstance(error, TalkerDataError)
            else "error"
        )
        raise
    finally:
        try:
            emit(
                "operation completed",
                **operation_context.fields(),
                outcome=operation_context.outcome,
                http_calls=operation_context.http_calls,
            )
        finally:
            _CACHE.reset(cache_token)
            _STAGE.reset(stage_token)
            _CURRENT.reset(token)


def mark_error(error: Exception) -> None:
    # check_status converts its exception into a (message, False) return value.
    if enabled() and (operation := _CURRENT.get()) is not None:
        operation.outcome = "network_error" if isinstance(error, TalkerNetworkError) else "data_error"


def observed(operation: str, *, public: bool = False):
    def decorate(method):
        @wraps(method)
        def wrapped(*args, **kwargs):
            if not enabled():
                return method(*args, **kwargs)
            with operation_scope(operation, method.__name__, join=not public):
                return method(*args, **kwargs)

        return wrapped

    return decorate


@contextlib.contextmanager
def query_stage(stage: str):
    if not enabled():
        yield
        return
    if stage not in QUERY_STAGES:
        raise ValueError("Unknown diagnostic query stage")
    token = _STAGE.set(stage)
    try:
        yield
    finally:
        _STAGE.reset(token)


def source_fields(source) -> dict:
    with _IDS_LOCK:
        if not hasattr(source, "_http_source_id"):
            source._http_source_id = _new_id()
        previous = getattr(source, "_http_session", None)
        if previous is None or previous[0] is not source.session:
            source._http_session = (source.session, _new_id())
        return {"source_id": source._http_source_id, "session_id": source._http_session[1]}


def source_created(source) -> None:
    if enabled():
        emit("source created", **source_fields(source))


@contextlib.contextmanager
def source_lock(lock, source, clock):
    if not enabled():
        with lock:
            yield
        return
    started = clock()
    with lock:
        waited = clock() - started
        operation = _CURRENT.get()
        emit(
            "lock acquired",
            **(operation.fields() if operation else {}),
            **source_fields(source),
            lock_wait_ms=round(waited * 1000, 3),
        )
        yield


@contextlib.contextmanager
def cache_result(source, api: str, cache: str, *, layer: str, reason: str = "lookup"):
    if not enabled():
        yield
        return
    operation = _CURRENT.get()
    emit(
        "cache resolved",
        **(operation.fields() if operation else {}),
        **source_fields(source),
        api=api,
        cache=cache,
        layer=layer,
        reason=reason,
        query_stage=_STAGE.get(),
    )
    token = _CACHE.set(cache)
    try:
        yield
    finally:
        _CACHE.reset(token)


def start_request(source, api: str, limiter_wait: float) -> dict:
    operation = _CURRENT.get()
    if operation is None:
        return {}
    with operation.counter_lock:
        operation.http_calls += 1
        number = operation.http_calls
    fields = {
        **operation.fields(),
        **source_fields(source),
        "request_id": _new_id(),
        "http_call_no": number,
        "api": api,
        "cache": _CACHE.get(),
        "query_stage": _STAGE.get(),
        "limiter_wait_ms": round(limiter_wait * 1000, 3),
        "started_utc": utc_now().isoformat(),
        "sru_cooldown": "none",
    }
    emit(f"{api} request started", **fields)
    return fields


def _header_state(value) -> str | None:
    if value is None:
        return "absent"
    if not isinstance(value, str):
        return "invalid"
    if len(value) > MAX_HEADER_LENGTH:
        return "oversized"
    if not value or not value.isascii() or any(ord(char) < 32 or ord(char) == 127 for char in value):
        return "invalid"
    return None


def parse_date(value) -> tuple[str, datetime | None]:
    if state := _header_state(value):
        return state, None
    try:
        date = parsedate_to_datetime(value)
        if date.tzinfo is None:
            return "invalid", None
        return "valid", date.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError, IndexError):
        return "invalid", None


def parse_retry_after(value, received: datetime) -> dict:
    if state := _header_state(value):
        return {"retry_after_kind": state}
    if value.isdigit():
        significant = value.lstrip("0") or "0"
        # Bound before int(), including long inputs below the character limit.
        if len(significant) > 10 or (len(significant) == 10 and significant > str(MAX_RETRY_SECONDS)):
            return {"retry_after_kind": "excessive"}
        return {"retry_after_kind": "delta", "retry_after_seconds": int(significant)}
    state, date = parse_date(value)
    if state != "valid":
        return {"retry_after_kind": "invalid"}
    seconds = (date - received).total_seconds()
    if seconds > MAX_RETRY_SECONDS:
        return {"retry_after_kind": "excessive"}
    return {
        "retry_after_kind": "http_date",
        "retry_after_utc": date.isoformat(),
        "retry_after_seconds": max(0, round(seconds, 3)),
        "retry_after_past": seconds < 0,
    }


def response_headers(response, received: datetime) -> dict:
    """Read exactly two allowlisted names. Never stringify external values."""
    try:
        retry = response.headers.get("Retry-After") if response is not None else None
        date_value = response.headers.get("Date") if response is not None else None
        fields = parse_retry_after(retry, received)
        state, date = parse_date(date_value)
        fields["response_date_state"] = state
        if date is not None:
            fields["response_date_utc"] = date.isoformat()
            fields["response_clock_delta_seconds"] = round((received - date).total_seconds(), 3)
        return fields
    except Exception:
        return {"retry_after_kind": "invalid", "response_date_state": "invalid"}


@dataclass(frozen=True)
class HttpFailure:
    fields: tuple[tuple[str, str | int | float | None], ...]


def result_fields(api: str, response, elapsed: float, timeout: tuple[int, int], request: dict) -> dict:
    received = utc_now()
    return {
        **request,
        "api": api,
        "status": response.status_code if response is not None else None,
        "elapsed": round(elapsed, 6),
        "connect_timeout": timeout[0],
        "read_timeout": timeout[1],
        "redirect_count": len(response.history) if response is not None else 0,
        "ended_utc": received.isoformat(),
        **response_headers(response, received),
    }


def annotate(error: TalkerNetworkError, fields: dict | None) -> TalkerNetworkError:
    if fields is not None:
        error._jpbooks_http_failure = HttpFailure(tuple(fields.items()))
    return error


def safe_failure_report(error: TalkerNetworkError) -> str:
    """Walk frames without filenames, source lines, locals, or exception text."""
    lines = ["Traceback (safe HTTP diagnostic; external messages and paths omitted):"]
    seen = set()
    current = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        for frame, number in traceback.walk_tb(current.__traceback__):
            name = frame.f_code.co_name
            name = name if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name) else "function"
            lines.append(f"  function={name} line={number}")
        lines.append(exception_name(current))
        current = current.__cause__
    lines.append(f"TalkerNetworkError code={error.code} sub_code={error.sub_code}")
    failure = getattr(error, "_jpbooks_http_failure", None)
    if isinstance(failure, HttpFailure):
        fields = dict(failure.fields)
        lines.append("HTTP diagnostics: " + format_fields(fields))
        # Construct timeout descriptions from our configuration, not external messages.
        if fields.get("error") == "ReadTimeout":
            lines.append(f"read timeout={fields['read_timeout']}")
    return "\n".join(lines) + "\n"


def safe_retry_after(value) -> str | int:
    """A safe representation for the existing optional-summary warning only."""
    result = parse_retry_after(value, utc_now())
    return result.get("retry_after_seconds", result["retry_after_kind"])


if _ENABLED:
    logger.setLevel(logging.DEBUG)
    emit("diagnostics enabled", schema=1, environment="import_time", retry_policy="unchanged")
