"""ISBN validation; display metadata is never normalized here."""

from __future__ import annotations

import re


def normalize_isbn(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    value = re.sub(r"[\s-]", "", value).upper()
    if re.fullmatch(r"[0-9]{9}[0-9X]", value):
        digits = [int(c) if c != "X" else 10 for c in value]
        return value if sum(d * (10 - i) for i, d in enumerate(digits)) % 11 == 0 else None
    if re.fullmatch(r"97[89][0-9]{10}", value):
        return (
            value if sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(value)) % 10 == 0 else None
        )
    return None


def isbn13(value: str | None) -> str | None:
    value = normalize_isbn(value)
    if value is None or len(value) == 13:
        return value
    stem = "978" + value[:9]
    check = (-sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(stem))) % 10
    return stem + str(check)


def isbn10(value: str | None) -> str | None:
    value = normalize_isbn(value)
    if value is None or len(value) == 10:
        return value
    if not value.startswith("978"):
        return None  # 979 ISBNs have no ISBN-10 equivalent.
    stem = value[3:12]
    check = (-sum(int(c) * (10 - i) for i, c in enumerate(stem))) % 11
    return stem + ("X" if check == 10 else str(check))


def isbn_from_gtin(value: str | None) -> str | None:
    if isinstance(value, str):
        clean = re.sub(r"[\s-]", "", value)
        if len(clean) == 14 and clean.startswith("0"):
            return normalize_isbn(clean[1:])
    return normalize_isbn(value)
