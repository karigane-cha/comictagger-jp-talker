"""Phase 2C-2A research only; bounded sequential snapshots, never metadata output.

Run with the repository virtualenv. Reuses the verified Phase 2A local archives
and the existing MADB transport (limiter, timeout, byte cap, no retries).
The captured JSON contains query text and raw bindings; --offline never fetches.
Existing observations are reused, not silently refreshed or overwritten.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from comictalker.comictalker import TalkerError  # noqa: E402
from research_madb_dataset import records, values  # noqa: E402

from comictagger_jp_talker.isbn import isbn13  # noqa: E402
from comictagger_jp_talker.models import SearchQuery  # noqa: E402
from comictagger_jp_talker.sources.madb import MADBSource  # noqa: E402
from comictagger_jp_talker.sources.madb_models import MADBError  # noqa: E402
from comictagger_jp_talker.sources.madb_parser import select_rows  # noqa: E402
from comictagger_jp_talker.sources.madb_queries import (  # noqa: E402
    ENDPOINT,
    ID_NS,
    resource_uri,
)
from comictagger_jp_talker.sources.ndl import NDLSource, build_cql  # noqa: E402

LOCAL = ROOT / ".research" / "madb"
OUTPUT = ROOT / "docs" / "research" / "madb" / "imprint_evidence.json"
SELECTED = {
    "M381096": "指定例。上位・下位候補と Series の結合表記",
    "M852457": "指定例。MF コミックスとフラッパーシリーズ",
    "M299519": "指定例。白泉社文庫と ISBN-10",
    "M292389": "指定例。完全版とジャンプ・コミックスデラックス",
    "M1032569": "指定例。新しい書誌と直接 NDL URL",
    "M519976": "指定例。数値を含む brand",
    "M1032568": "指定例。既存 EXACT 照合の再確認",
    "M1032570": "秋田書店。英語と日本語の結合別表記",
    "M1032672": "新しい書誌。Series 未接続とジャンプコミックス",
    "M1032913": "空文字 brand と新しい直接 NDL URL",
    "M1065430": "一迅社と頒布元の講談社を区別",
    "M1033548": "ひらがな表示と読みの区別",
    "M1033549": "英語表示と空の読み",
    "M1076947": "バイリンガル版の英語レーベル候補",
    "M1118994": "セット書誌。レーベルと雑誌名を含む単一文字列",
    "M1080059": "古い出版社の汎用的レーベル名",
    "M189455": "言語タグなしの英語表示",
    "M189501": "旧発行主体と現在のレーベル移管の検証課題",
    "M189667": "旧レーベル Jets comics",
    "M190399": "brand に雑誌名が混在。ISBN の不正値も保持",
    "M191237": "ジャンプ・コミックスと新しい表記との差",
    "M196308": "復刻版、非商業的発行主体、brand 欠損",
    "M196908": "愛蔵版と Book / Series brand 欠損",
    "M197041": "略称と正式名が並ぶ複数表示値",
    "M197767": "単一 brand が版表示の愛蔵版",
    "M208827": "特別版。異なる複数の有効 ISBN",
    "M215577": "発行・発売の役割付き publisher",
    "M224983": "ヤンマガ KC と番号 productID",
    "M256549": "上位・下位候補の複数値",
    "M280044": "作品の通常版と完全版を区別",
    "M307396": "同作品の完全版と通常版を比較",
    "M255146": "KC DELUXE と日本語別表記",
    "M299514": "複数表記と複数 publisher。文庫版との比較",
    "M280225": "Book brand 欠損と別版の Series を検証",
    "M280574": "手塚治虫漫画全集。叢書とレーベルの境界",
    "M353277": "Book / Series の DX 差異",
    "M807088": "上位・下位候補と Series の結合表記",
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(data):
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def seed():
    old = json.loads((ROOT / "docs/research/madb/evidence.json").read_text(encoding="utf-8"))
    audit = json.loads((LOCAL / "audit.json").read_text(encoding="utf-8"))
    books = {r["@id"].rsplit("/", 1)[-1]: r for r in audit["books"]}
    series = {r["@id"]: r for r in audit["series"]}
    reasons = dict(SELECTED)
    publisher_same = series_only = None
    # Verified cached archive, no live discovery query. Keep two adversarial cases.
    for record in records("books"):
        identifier = record["@id"].rsplit("/", 1)[-1]
        if identifier in reasons:
            books[identifier] = record
        displays = values(record, "schema:brand", display=True)
        if publisher_same is None and set(displays) & set(values(record, "schema:publisher")):
            publisher_same = identifier
            reasons[identifier] = "追加例。brand と publisher に同じ文字列がある"
            books[identifier] = record
        if series_only is None and not any(v.strip() for v in displays):
            related = [series[u] for u in values(record, "schema:isPartOf") if u in series]
            if any(values(s, "schema:brand", display=True) for s in related):
                series_only = identifier
                reasons[identifier] = "追加例。Book brand 欠損と Series brand 存在"
                books[identifier] = record
        if all(i in books for i in reasons) and publisher_same and series_only:
            break
    wanted = {u for i in reasons for u in values(books[i], "schema:isPartOf")}
    if wanted - series.keys():
        for record in records("series"):
            if record["@id"] in wanted:
                series[record["@id"]] = record
    sources = [s for s in old["sources"] if s["name"] in ("books_json", "series_json", "schema")]
    data = {
        "schema_version": "phase2c2a-v1",
        "research_date_jst": "2026-10-08",
        "assembled_at": stamp(),
        "endpoint": ENDPOINT,
        "attribution": old["attribution"],
        "historical": {
            "observed_on": old["observed_on"],
            "release": old["release"],
            "source_evidence": "docs/research/madb/evidence.json",
            "sources": sources,
            "books": [books[i] for i in reasons],
            "series": [series[u] for u in sorted(wanted) if u in series],
            "encoding": "raw JSON-LD from verified release; not current endpoint observations",
        },
        "selection": [{"book_id": i, "reason": r} for i, r in reasons.items()],
        "requests": [],
        "observations": [],
        "analysis": {},
    }
    save(data)
    return data


def capture(data, source, identifiers, kind, *, retry_network=False):
    uris = [resource_uri(i, kind) for i in identifiers]
    # Same direct-triple shape as resource_query, with a small VALUES batch.
    # No JOIN, traversal, DISTINCT, ORDER BY, title scan or query parallelism.
    limit = 300 * len(uris) + 1
    query = "SELECT ?s ?p ?o WHERE {\n  VALUES ?s { " + " ".join(f"<{u}>" for u in uris)
    query += f" }}\n  ?s ?p ?o .\n}} LIMIT {limit}"
    digest = hashlib.sha256(query.encode()).hexdigest()
    previous = next((r for r in reversed(data["requests"]) if r["query_sha256"] == digest), None)
    retry = previous and retry_network and previous.get("error", {}).get("kind") == "network"
    if previous and not retry:
        print("reuse", previous["id"], previous["state"], flush=True)
        if previous["state"] == "unavailable":
            raise SystemExit(1)
        return
    request = {
        "id": f"imprint-{kind}-{len(data['requests']) + 1:02d}",
        "at": stamp(),
        "endpoint": ENDPOINT,
        "method": "POST",
        "query": query,
        "query_sha256": digest,
        "limit": limit,
        "targets": uris,
    }
    try:
        body = source._request(query)  # Research only: existing protected transport.
        rows = select_rows(body, {"s", "p", "o"}, {"s", "p", "o"}, limit)
        raw = json.loads(body)
        if any(r["s"].kind != "uri" or r["s"].value not in uris or r["p"].kind != "uri" for r in rows):
            raise MADBError("schema", "Unexpected subject or predicate")
        request.update(
            {
                "state": "truncated" if len(rows) >= limit else "complete",
                "status": 200,
                "bytes": len(body),
                "response_sha256": hashlib.sha256(body).hexdigest(),
                "raw_response": raw,
                "row_count": len(rows),
            }
        )
        for uri in uris:
            bindings = [r for r in raw["results"]["bindings"] if r["s"]["value"] == uri]
            state = (
                "unavailable" if not bindings else "truncated" if len(bindings) >= 300 else request["state"]
            )
            data["observations"].append(
                {
                    "resource": uri,
                    "kind": kind,
                    "request_id": request["id"],
                    "at": request["at"],
                    "state": state,
                    "direct_triple_count": len(bindings),
                    "raw_bindings": bindings,
                }
            )
    except MADBError as error:
        request.update(
            {
                "state": "unavailable",
                "error": {
                    "kind": error.kind,
                    "message": error.desc,
                    "status": error.status,
                    "retry_after": error.retry_after,
                },
            }
        )
        for uri in uris:
            data["observations"].append(
                {
                    "resource": uri,
                    "kind": kind,
                    "request_id": request["id"],
                    "at": request["at"],
                    "state": "unavailable",
                    "raw_bindings": [],
                }
            )
    request["completed_at"] = stamp()
    data["requests"].append(request)
    save(data)
    print(request["id"], request["state"], request.get("row_count"), request.get("error"), flush=True)
    if request["state"] == "unavailable":
        # Stop the run; no automatic retry or continuing during rate/transport errors.
        raise SystemExit(1)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="seed historical evidence only; no network")
    parser.add_argument("--collect", action="store_true", help="capture live Book/Series batches explicitly")
    parser.add_argument("--ndl", action="store_true", help="bounded NDL comparison and two ISBN discoveries")
    parser.add_argument("--verify", action="store_true", help="validate captured artifacts without network")
    parser.add_argument("--retry-network-once", action="store_true", help="explicit manual transport retry")
    args = parser.parse_args()
    if sum((args.offline, args.collect, args.ndl, args.verify)) != 1:
        parser.error("Choose exactly one of --offline, --collect, --ndl and --verify")
    if args.verify:
        verify()
        return
    data = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else seed()
    if args.collect:
        with MADBSource(LOCAL / "imprint-cache") as source:
            identifiers = [r["book_id"] for r in data["selection"]]
            for start in range(0, len(identifiers), 8):
                capture(
                    data,
                    source,
                    identifiers[start : start + 8],
                    "book",
                    retry_network=args.retry_network_once,
                )
            # Only current explicit Book relations; do not traverse historical relations.
            related = sorted(
                {
                    r["o"]["value"]
                    for o in data["observations"]
                    if o["kind"] == "book"
                    for r in o["raw_bindings"]
                    if r["p"]["value"] == "https://schema.org/isPartOf" and r["o"]["type"] == "uri"
                }
            )
            for start in range(0, len(related), 8):
                capture(
                    data,
                    source,
                    related[start : start + 8],
                    "series",
                    retry_network=args.retry_network_once,
                )
    if args.ndl:
        collect_ndl(data)
    print(
        json.dumps(
            {
                "books": len(data["selection"]),
                "observed": dict(Counter(o["state"] for o in data["observations"])),
            },
            ensure_ascii=False,
        )
    )


def collect_ndl(data):
    from xml.etree import ElementTree as ET

    latest = {o["resource"]: o for o in data["observations"]}
    identifiers = list(SELECTED)[:7] + ["M1032570", "M197767", "M280574", "M190399"]
    data.setdefault("ndl_observations", [])
    source = NDLSource(LOCAL / "imprint-cache", maximum_records=5)
    try:
        for identifier in identifiers:
            if any(o["book_id"] == identifier for o in data["ndl_observations"]):
                continue
            book = latest[ID_NS + identifier]
            triples = book["raw_bindings"]
            urls = [r["o"]["value"] for r in triples if r["p"]["value"].endswith("#dataUrl")]
            isbns = [
                r["o"]["value"]
                for r in triples
                if r["p"]["value"] == "https://schema.org/isbn" and isbn13(r["o"]["value"])
            ]
            query = (
                SearchQuery(itemno=urls[0].rsplit("/", 1)[-1], mediatype="")
                if urls
                else SearchQuery(isbn=isbns[0], mediatype="")
            )
            observation = {
                "book_id": identifier,
                "at": stamp(),
                "endpoint": "https://ndlsearch.ndl.go.jp/api/sru",
                "cql": build_cql(query),
                "maximumRecords": 5,
            }
            try:
                page = source.search(query)
                selected = []
                for record in page.records:
                    node = ET.fromstring(record.raw_xml)
                    raw_fields = [
                        ET.tostring(n, encoding="unicode")
                        for n in node.iter()
                        if n.tag.rsplit("}", 1)[-1] in {"seriesTitle", "publisher", "edition"}
                    ]
                    selected.append(
                        {
                            "id": record.id,
                            "url": record.url,
                            "title": record.title,
                            "isbns": record.isbns,
                            "publishers": record.publishers,
                            "series_titles": record.series_titles,
                            "editions": record.editions,
                            "raw_selected_xml": raw_fields,
                            "record_xml_sha256": hashlib.sha256(record.raw_xml.encode()).hexdigest(),
                        }
                    )
                observation.update(
                    {
                        "state": "complete",
                        "total": page.total,
                        "truncated": page.truncated or page.total > len(page.records),
                        "records": selected,
                    }
                )
            except TalkerError as error:
                observation.update({"state": "unavailable", "error": str(error)})
            data["ndl_observations"].append(observation)
            save(data)
            print("NDL", identifier, observation["state"], observation.get("total"), flush=True)
            if observation["state"] == "unavailable":
                raise SystemExit(1)
    finally:
        source.session.close()
        source.cache.close()
    data.setdefault("isbn_discoveries", [])
    with MADBSource(LOCAL / "imprint-cache") as madb:
        for identifier in ("M1032568", "M1032569"):
            if any(o["book_id"] == identifier for o in data["isbn_discoveries"]):
                continue
            isbn = next(
                r["o"]["value"]
                for r in latest[ID_NS + identifier]["raw_bindings"]
                if r["p"]["value"] == "https://schema.org/isbn"
            )
            from comictagger_jp_talker.sources.madb_queries import isbn_query

            observation = {"book_id": identifier, "at": stamp(), "query": isbn_query(isbn), "isbn": isbn}
            try:
                page = madb.search_by_isbn(isbn)
                observation.update({"state": "complete", "page": asdict(page)})
            except MADBError as error:
                observation.update({"state": "unavailable", "error": error.kind, "status": error.status})
            data["isbn_discoveries"].append(observation)
            save(data)
            print("ISBN discovery", identifier, observation["state"], flush=True)
            if observation["state"] == "unavailable":
                raise SystemExit(1)


def verify():
    import re
    import unicodedata

    from comictagger_jp_talker.sources.madb_parser import parse_resource

    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    latest = {o["resource"]: o for o in data["observations"]}
    for request in data["requests"]:
        assert hashlib.sha256(request["query"].encode()).hexdigest() == request["query_sha256"]
        assert request["endpoint"] == ENDPOINT and request["method"] == "POST"
        assert "SELECT ?s ?p ?o" in request["query"] and "VALUES ?s" in request["query"]
        assert request["query"].endswith(f"LIMIT {request['limit']}")
        if request["state"] == "complete":
            raw_body = json.dumps(request["raw_response"]).encode()
            rows = select_rows(raw_body, {"s", "p", "o"}, {"s", "p", "o"}, request["limit"])
            assert len(rows) == request["row_count"] < request["limit"]
    for uri, observation in latest.items():
        assert observation["state"] == "complete"
        assert resource_uri(uri, observation["kind"]) == uri
        bindings = observation["raw_bindings"]
        assert len(bindings) == observation["direct_triple_count"] < 300
        assert all(r["s"] == {"type": "uri", "value": uri} for r in bindings)
        document = {
            "head": {"vars": ["p", "o"]},
            "results": {"bindings": [{"p": r["p"], "o": r["o"]} for r in bindings]},
        }
        parsed = parse_resource(json.dumps(document).encode(), uri, observation["kind"], 300)
        assert parsed.id == uri.rsplit("/", 1)[-1] and parsed.completeness == "complete"
    cases = data["analysis"]["cases"]
    assert {c["book_id"] for c in cases} == {s["book_id"] for s in data["selection"]}
    assert len(cases) == len(data["selection"])
    for case in cases:
        uri = ID_NS + case["book_id"]
        assert uri == case["book_uri"]
        displays = list(
            dict.fromkeys(
                unicodedata.normalize("NFC", r["o"]["value"].strip())
                for r in latest[uri]["raw_bindings"]
                if r["p"]["value"] == "https://schema.org/brand"
                and r["o"]["type"] == "literal"
                and r["o"].get("xml:lang", "").casefold() in ("", "ja")
                and r["o"]["value"].strip()
            )
        )
        assert displays == case["book_display_values"]
        assert all(uri in latest for uri in case["series_uris"])
        assert case["judgment_kind"] == "human_annotation"
    stats = data["analysis"]["statistics"]
    assert stats["books"] == len(cases)
    assert stats["series"] == sum(o["kind"] == "series" for o in latest.values())
    assert stats["ground_truth"] == dict(Counter(c["ground_truth"] for c in cases))
    assert stats["comparison_states"] == dict(Counter(c["comparison_state"] for c in cases))
    assert stats["single_nonempty_display"] == sum(len(c["book_display_values"]) == 1 for c in cases)
    assert stats["multiple_nonempty_display"] == sum(len(c["book_display_values"]) > 1 for c in cases)
    for check in data["analysis"]["existing_identity_checks"]:
        assert check["result"]["status"] == "matched" and not check["result"]["truncated"]
        assert len(check["result"]["matches"]) == 1
        match = check["result"]["matches"][0]
        assert match["confidence"] == "exact" and not match["conflicts"]
    checked_links = 0
    for path in (ROOT / "docs/phase2c2a_imprint_research.md", OUTPUT.with_name("imprint_examples.md")):
        body = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)\n]+)\)", body):
            if target.startswith(("https://", "http://", "#")):
                continue
            assert (path.parent / target.split("#", 1)[0]).resolve().exists(), (path, target)
            checked_links += 1
    print(
        json.dumps(
            {
                "json": "valid",
                "parsed_resources": len(latest),
                "book_cases": len(cases),
                "existing_exact_identity_checks": 2,
                "local_links": checked_links,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
