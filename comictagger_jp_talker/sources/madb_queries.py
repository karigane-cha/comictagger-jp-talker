"""Bounded SELECT templates using namespaces measured in Phase 2A.

No endpoint, raw query, graph, SERVICE, or update input is exposed by MADBSource.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Literal

from comictagger_jp_talker.isbn import isbn10, isbn13, normalize_isbn

ENDPOINT = "https://mediaarts-db.artmuseums.go.jp/sparql"
ID_NS = "https://mediaarts-db.artmuseums.go.jp/id/"
REF_NS = "https://mediaarts-db.artmuseums.go.jp/ref/"
CLASS_NS = "https://mediaarts-db.artmuseums.go.jp/data/class#"
PROPERTY_NS = "https://mediaarts-db.artmuseums.go.jp/data/property#"
SCHEMA_NS = "https://schema.org/"
DCTERMS_NS = "http://purl.org/dc/terms/"
RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"
XSD_NS = "http://www.w3.org/2001/XMLSchema#"
PREFIXES = f"PREFIX schema: <{SCHEMA_NS}>\nPREFIX class: <{CLASS_NS}>\n"
ResourceKind = Literal["book", "series", "agent", "holding"]
DEFAULT_CANDIDATES = 20
DEFAULT_TRIPLES = 300
MAX_CANDIDATES = 100
MAX_TRIPLES = 1000


def sparql_literal(value: str) -> str:
    """Escape permitted whitespace; reject other controls and lone surrogates."""
    if not isinstance(value, str) or any(
        unicodedata.category(c) in ("Cc", "Cs") and c not in "\n\r\t" for c in value
    ):
        raise ValueError("Invalid SPARQL literal")
    return json.dumps(value, ensure_ascii=False)


def isbn_candidates(value: str) -> tuple[str, ...]:
    # Validate controls BEFORE the shared normalizer removes whitespace.
    sparql_literal(value)
    normalized = normalize_isbn(value)
    if normalized is None:
        raise ValueError("A valid ISBN-10 or ISBN-13 is required")
    return tuple(sorted({v for v in (normalized, isbn10(normalized), isbn13(normalized)) if v}))


def resource_uri(value: str, kind: ResourceKind) -> str:
    prefix, namespace = {
        "book": ("M", ID_NS),
        "series": ("C", ID_NS),
        "agent": ("C", ID_NS),
        "holding": ("S", REF_NS),
    }[kind]
    if not isinstance(value, str):
        raise ValueError("Invalid MADB resource ID")
    identifier = value.removeprefix(namespace)
    if not re.fullmatch(prefix + r"[0-9]+", identifier):
        raise ValueError("Invalid MADB resource ID or URI")
    return namespace + identifier


def bounded_limit(value: int, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ValueError(f"LIMIT must be an integer in 1..{maximum}")
    return value


def isbn_query(value: str, limit: int = DEFAULT_CANDIDATES) -> str:
    values = " ".join(sparql_literal(v) for v in isbn_candidates(value))
    limit = bounded_limit(limit, MAX_CANDIDATES)
    # Only identity and matched ISBN terms: no metadata OPTIONAL cross product.
    return (
        PREFIXES
        + f"""SELECT DISTINCT ?book ?identifier ?isbn WHERE {{
  VALUES ?isbn {{ {values} }}
  ?book a class:MangaBook ; schema:isbn ?isbn .
  OPTIONAL {{ ?book schema:identifier ?identifier }}
}} ORDER BY ?book ?identifier ?isbn LIMIT {limit}"""
    )


def resource_query(value: str, kind: ResourceKind, limit: int = DEFAULT_TRIPLES) -> str:
    uri = resource_uri(value, kind)
    limit = bounded_limit(limit, MAX_TRIPLES)
    # Fetch type as evidence; a type-filtered join would hide schema mismatches.
    return f"SELECT ?p ?o WHERE {{ <{uri}> ?p ?o }} ORDER BY ?p ?o LIMIT {limit}"
