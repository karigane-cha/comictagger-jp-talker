"""Research-only, not production: bounded read-only MADB HTTP/query recorder.

Uses existing requests dependency. Responses stay in ignored .research/madb.
No automatic retries, parallel requests, or dataset crawling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".research" / "madb"
ENDPOINT = "https://mediaarts-db.artmuseums.go.jp/sparql"
HOSTS = {
    "mediaarts-db.artmuseums.go.jp",
    "mediaarts-db.bunka.go.jp",
    "mediag.bunka.go.jp",
    "api.github.com",
    "raw.githubusercontent.com",
    "github.com",
}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--url", default=ENDPOINT)
    parser.add_argument("--query", type=Path)
    parser.add_argument("--method", choices=("GET", "POST"), default="GET")
    parser.add_argument("--accept", default="application/sparql-results+json")
    parser.add_argument("--show-body", action="store_true")
    args = parser.parse_args()
    if urlparse(args.url).hostname not in HOSTS:
        parser.error("Only the explicit research host allowlist is permitted")
    if not args.name.replace("-", "").replace("_", "").isalnum():
        parser.error("name must be alphanumeric, dash or underscore")
    OUT.mkdir(parents=True, exist_ok=True)
    previous = OUT / "last-request.txt"
    if previous.exists():
        time.sleep(max(0, 3 - (time.time() - float(previous.read_text()))))
    query = args.query.read_text(encoding="utf-8") if args.query else None
    if query and ("SELECT" not in query.upper() or "LIMIT" not in query.upper()):
        parser.error("Research queries must be SELECT with an explicit LIMIT")
    if args.method == "POST" and not query:
        parser.error("POST is only used for read-only query requests")
    headers = {"Accept": args.accept, "User-Agent": "comictagger-jp-talker-Phase2A-research/1"}
    kwargs = {"params" if args.method == "GET" else "data": {"query": query}} if query else {}
    started = time.monotonic()
    stamp = datetime.now(timezone.utc).isoformat()
    try:
        response = requests.request(args.method, args.url, headers=headers, timeout=(5, 65), **kwargs)
        body = response.content
        (OUT / f"{args.name}.body").write_bytes(body)
        meta = {
            "at": stamp,
            "url": args.url,
            "method": args.method,
            "accept": args.accept,
            "query": query,
            "status": response.status_code,
            "final_url": response.url,
            "redirects": [{"status": r.status_code, "url": r.url} for r in response.history],
            "headers": dict(response.headers),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "elapsed": time.monotonic() - started,
        }
        print(
            json.dumps(
                {k: meta[k] for k in ("at", "url", "method", "status", "bytes", "sha256")}, ensure_ascii=True
            )
        )
        if args.show_body and len(body) < 25000:
            print(body.decode("utf-8", errors="replace"))
    except requests.RequestException as error:
        meta = {
            "at": stamp,
            "url": args.url,
            "method": args.method,
            "query": query,
            "error": str(error),
            "elapsed": time.monotonic() - started,
        }
        print(json.dumps(meta, ensure_ascii=True))
    finally:
        previous.write_text(str(time.time()))
    (OUT / f"{args.name}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
