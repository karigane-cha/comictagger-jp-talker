"""Research-only, not production: offline audit of MADB 1.2.20 JSON-LD ZIPs.

Run after downloading books_json.body and series_json.body with research_madb.py.
This reader intentionally requires the release's pretty-printed @graph layout;
it fails if that layout changes. It does not fetch data or import the package.
"""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / ".research" / "madb"
ZIP_SHA256 = {
    "books": "250548820717850a8783c7ac66465eb6875b2107898f3a06703dc79cf495ecf7",
    "series": "e47432ec0e03be3310814f6db0354a37024869b5d2a691b4b502c9478c40458b",
}
TITLES = (
    "ご注文はうさぎですか?",
    "こちら葛飾区亀有公園前派出所",
    "パタリロ!",
    "ブルーロック",
    "FX戦士くるみちゃん",
    "お兄ちゃんはおしまい!",
    "SLAM DUNK",
    "ドラゴンボール",
    "美少女戦士セーラームーン",
    "AKIRA",
    "寄生獣",
    "ブラック・ジャック",
)
EDITIONS = ("新装版", "完全版", "文庫版", "愛蔵版", "特装版", "新版", "改訂版", "復刻版", "電子版")
VOLUMES = ("1", "第1巻", "volume 1", "上", "下", "1.5", "別巻", "外伝")


def records(name):
    path = ROOT / f"{name}_json.body"
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != ZIP_SHA256[name]:
        raise ValueError("Input is not the verified MADB 1.2.20 release ZIP")
    with zipfile.ZipFile(path) as archive:
        with archive.open(archive.namelist()[0]) as source:
            block = []
            count = 0
            for raw in source:
                line = raw.decode("utf-8")
                if line.rstrip() == "    {":
                    if block:
                        raise ValueError("Unexpected nested record boundary")
                    block = [line]
                elif block:
                    block.append(line)
                    if line.rstrip() in ("    },", "    }"):
                        yield json.loads("".join(block).rstrip().removesuffix(","))
                        count += 1
                        block = []
            if block or not count:
                raise ValueError("Incomplete or unrecognized release JSON layout")


def values(record, prop, *, display=False):
    raw = record.get(prop, [])
    raw = raw if isinstance(raw, list) else [raw]
    return [
        item if isinstance(item, str) else item.get("@value", item.get("@id", ""))
        for item in raw
        if not display or not isinstance(item, dict) or not item.get("@language")
    ]


def isbn13(raw):
    clean = re.sub(r"[-\s]", "", raw).upper()
    if re.fullmatch(r"\d{9}[\dX]", clean):
        digits = [int(c) if c != "X" else 10 for c in clean]
        if sum((10 - i) * n for i, n in enumerate(digits)) % 11:
            return None
        clean = "978" + clean[:9]
        clean += str((-sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(clean))) % 10)
    if not re.fullmatch(r"97[89]\d{10}", clean):
        return None
    if sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(clean)) % 10:
        return None
    return clean


def main():
    counts = Counter()
    props = Counter()
    formats = Counter()
    date_formats = Counter()
    samples = defaultdict(list)
    selected = {}
    isbn_index = defaultdict(list)
    roles = Counter()
    title_counts = Counter()
    for record in records("books"):
        counts["books"] += 1
        props.update(record.keys())
        names = values(record, "schema:name", display=True)
        volume = values(record, "schema:volumeNumber")
        version = values(record, "schema:version")
        isbns = values(record, "schema:isbn")
        normalized = {n for raw in isbns if (n := isbn13(raw))}
        counts["has_isbn"] += bool(isbns)
        counts["has_valid_isbn"] += bool(normalized)
        counts["multiple_raw_isbn"] += len(isbns) > 1
        counts["multiple_distinct_valid_isbn13"] += len(normalized) > 1
        for raw in isbns:
            shape = (
                "10"
                if re.fullmatch(r"\d{9}[\dXx]", raw)
                else "13"
                if re.fullmatch(r"\d{13}", raw)
                else "hyphenated"
                if "-" in raw
                else "other"
            )
            formats[shape] += 1
            key = "isbn_" + (shape if isbn13(raw) else "invalid")
            if len(samples[key]) < 3:
                samples[key].append(record)
        for number in normalized:
            isbn_index[number].append(record["@id"])
        if len(normalized) > 1 and len(samples["isbn_multiple"]) < 3:
            samples["isbn_multiple"].append(record)
        for raw in values(record, "schema:datePublished"):
            kind = next(
                (
                    name
                    for pattern, name in [
                        (r"\d{4}", "year"),
                        (r"\d{4}-\d{2}", "month"),
                        (r"\d{4}-\d{2}-\d{2}", "day"),
                    ]
                    if re.fullmatch(pattern, raw)
                ),
                "other",
            )
            date_formats[kind] += 1
            if len(samples["date_" + kind]) < 2:
                samples["date_" + kind].append(record)
        links = values(record, "ma:dataUrl")
        counts["direct_ndl_url"] += any(
            re.search(r"ndlsearch\.ndl\.go\.jp/books/R\d+-I\d+", u) for u in links
        )
        counts["data_url"] += bool(links)
        counts["series_relation"] += bool(values(record, "schema:isPartOf"))
        for credit in values(record, "schema:creator", display=True):
            if match := re.match(r"\[([^]]+)\]", credit):
                roles[match[1]] += 1
        for title in TITLES:
            if title in names:
                title_counts[title] += 1
                key = "title_" + title
                # Include early volumes, longer runs, and differing editions.
                if len(samples[key]) < 4 and any(
                    v in {"1", "第1巻", "volume 1", "10", "100"} for v in volume
                ):
                    samples[key].append(record)
        for edition in EDITIONS:
            if any(edition in v for v in version) and len(samples["edition_" + edition]) < 2:
                samples["edition_" + edition].append(record)
        for item in VOLUMES:
            if item in volume and len(samples["volume_" + item]) < 1:
                samples["volume_" + item].append(record)
        if "M452977" == record["@id"].rsplit("/", 1)[-1]:
            samples["electronic_mention"].append(record)
        if record["@id"].endswith("/M1032568"):
            samples["direct_ndl"].append(record)
    for group in samples.values():
        selected.update((r["@id"], r) for r in group)
    series_ids = {u for r in selected.values() for u in values(r, "schema:isPartOf")}
    linked_series = []
    series_props = Counter()
    for record in records("series"):
        counts["series"] += 1
        series_props.update(record.keys())
        if record["@id"] in series_ids:
            linked_series.append(record)
    output = {
        "release": "1.2.20",
        "counts": dict(counts),
        "book_properties": dict(props),
        "series_properties": dict(series_props),
        "isbn_formats": dict(formats),
        "date_formats": dict(date_formats),
        "roles": roles.most_common(),
        "isbn_shared_by_books": sum(len(ids) > 1 for ids in isbn_index.values()),
        "shared_isbn_examples": {
            k: v for k, v in list((k, v) for k, v in isbn_index.items() if len(v) > 1)[:5]
        },
        "exact_title_counts": dict(title_counts),
        "sample_groups": {k: [r["@id"] for r in v] for k, v in samples.items()},
        "books": list(selected.values()),
        "series": linked_series,
    }
    (ROOT / "audit.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in output.items() if k not in {"books", "series", "sample_groups"}},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
