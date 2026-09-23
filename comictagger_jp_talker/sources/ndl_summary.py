"""Summary fields observed in NDL's documented external bibliographic JSON API.

The endpoint is documented in external interface specification 1.4, section 2(7).
Internal field codes are not a stable public schema: validate the envelope and
exact selected ID, inspect only its items, and never search arbitrary nested text.
"""

from __future__ import annotations

from dataclasses import dataclass

from comictalker.comictalker import TalkerDataError

DETAIL_ENDPOINT = "https://ndlsearch.ndl.go.jp/api/bib/external/search"


@dataclass(frozen=True)
class Summary:
    texts: list[str]
    provider: str
    medium: str
    item_id: str


def _values(meta: dict, key: str) -> list[str]:
    values = meta.get(key, [])
    if not isinstance(values, list) or any(
        not isinstance(value, dict) or not isinstance(value.get("v"), str) for value in values
    ):
        raise TalkerDataError("NDL Search", 2, f"Malformed summary field: {key}")
    return list(dict.fromkeys(value["v"].strip() for value in values if value["v"].strip()))


def parse_summary(data: object, record_id: str) -> Summary | None:
    if not isinstance(data, dict) or not isinstance(data.get("list"), list):
        raise TalkerDataError("NDL Search", 2, "Malformed summary response: list がありません。")
    records = data["list"]
    if not records and data.get("hit") == 0:
        return None
    if len(records) != 1 or not isinstance(records[0], dict) or records[0].get("id") != record_id:
        raise TalkerDataError("NDL Search", 2, "要約の書誌 ID が選択した書誌と一致しません。")
    items = records[0].get("items")
    if not isinstance(items, list):
        raise TalkerDataError("NDL Search", 2, "Malformed summary response: items がありません。")
    candidates: list[Summary] = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("meta"), dict):
            raise TalkerDataError("NDL Search", 2, "Malformed summary item")
        meta = item["meta"]
        # t35200 is the item-level abstract, k39022 is its physical/digital medium.
        # Do not use t35000 (notes), rels (other books), or IDs derived from ISBNs.
        texts = _values(meta, "t35200")
        media = _values(meta, "k39022")
        medium = next((m for m in ("紙", "デジタル") if m in media), "")
        if not texts or not medium:
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id:
            raise TalkerDataError("NDL Search", 2, "Malformed summary item: id がありません。")
        provider = " / ".join(_values(meta, "k80404"))
        candidates.append(Summary(texts, provider, medium, item_id))
    # Retain response order within a medium; don't concatenate different editions.
    return next((s for m in ("紙", "デジタル") for s in candidates if s.medium == m), None)
