"""Strict SPARQL JSON decoding and term-preserving MADB resource construction."""

from __future__ import annotations

import json
import re

from comictagger_jp_talker.isbn import isbn13
from comictagger_jp_talker.sources.madb_models import (
    ExternalIdentifier,
    MADBAgentRecord,
    MADBBookRecord,
    MADBCredit,
    MADBError,
    MADBHoldingRecord,
    MADBSearchPage,
    MADBSearchResult,
    MADBSeriesRecord,
    MADBStatement,
    RDFTerm,
)
from comictagger_jp_talker.sources.madb_queries import (
    CLASS_NS,
    DCTERMS_NS,
    PROPERTY_NS,
    RDF_NS,
    RDFS_NS,
    SCHEMA_NS,
    XSD_NS,
    ResourceKind,
    isbn_candidates,
    resource_uri,
)

MAX_RESPONSE_BYTES = 2 * 1024 * 1024


def parse_term(binding: object) -> RDFTerm:
    if not isinstance(binding, dict) or not isinstance(binding.get("value"), str):
        raise MADBError("protocol", "Invalid RDF binding")
    kind = binding.get("type")
    datatype, language = binding.get("datatype"), binding.get("xml:lang")
    if kind not in ("uri", "literal", "bnode"):
        raise MADBError("schema", "Unknown RDF term type")
    if any(v is not None and (not isinstance(v, str) or not v) for v in (datatype, language)):
        raise MADBError("protocol", "Invalid RDF datatype/language")
    if (kind != "literal" and (datatype is not None or language is not None)) or (
        language is not None and datatype not in (None, RDF_NS + "langString")
    ):
        raise MADBError("protocol", "Inconsistent RDF term qualifiers")
    if any(0xD800 <= ord(c) <= 0xDFFF for v in (binding["value"], datatype, language) if v for c in v):
        raise MADBError("protocol", "Invalid Unicode in RDF term")
    return RDFTerm(kind, binding["value"], datatype, language)


def select_rows(
    content: bytes, columns: set[str], required: set[str], limit: int
) -> list[dict[str, RDFTerm]]:
    if len(content) > MAX_RESPONSE_BYTES:
        raise MADBError("truncated", "SPARQL response exceeds byte cap")
    try:
        data = json.loads(content)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise MADBError("protocol", "Malformed SPARQL JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("head"), dict):
        raise MADBError("protocol", "Missing SPARQL head")
    variables = data["head"].get("vars")
    if not isinstance(variables, list) or any(not isinstance(v, str) for v in variables):
        raise MADBError("protocol", "Invalid SPARQL variables")
    if set(variables) != columns or len(variables) != len(columns):
        raise MADBError("protocol", "Unexpected SPARQL columns")
    results = data.get("results")
    if not isinstance(results, dict) or not isinstance(results.get("bindings"), list):
        raise MADBError("protocol", "Missing SPARQL bindings")
    bindings = results["bindings"]
    if len(bindings) > limit:
        raise MADBError("truncated", "SPARQL response exceeds row cap")
    rows = []
    for row in bindings:
        if not isinstance(row, dict) or not required <= row.keys() or not row.keys() <= columns:
            raise MADBError("protocol", "Missing or unexpected SPARQL binding")
        rows.append({key: parse_term(value) for key, value in row.items()})
    return rows


def parse_search(content: bytes, isbn: str, limit: int) -> MADBSearchPage:
    rows = select_rows(content, {"book", "identifier", "isbn"}, {"book", "isbn"}, limit)
    candidates = isbn_candidates(isbn)
    grouped: dict[str, tuple[list[RDFTerm], list[RDFTerm]]] = {}
    for row in rows:
        book, raw = row["book"], row["isbn"]
        try:
            if book.kind != "uri":
                raise ValueError
            uri = resource_uri(book.value, "book")
        except ValueError as exc:
            raise MADBError("schema", "Invalid candidate Book URI") from exc
        if (
            raw.kind != "literal"
            or raw.language
            or raw.datatype not in (None, XSD_NS + "string")
            or raw.value not in candidates
        ):
            raise MADBError("schema", "Unexpected ISBN exact-search binding")
        identifiers, isbns = grouped.setdefault(uri, ([], []))
        if "identifier" in row:
            identifier = row["identifier"]
            if identifier.kind != "literal" or identifier.value != uri.rsplit("/", 1)[1]:
                raise MADBError("schema", "Book URI/identifier mismatch")
            if identifier not in identifiers:
                identifiers.append(identifier)
        if raw not in isbns:
            isbns.append(raw)
    truncated = len(rows) == limit
    return MADBSearchPage(
        tuple(
            MADBSearchResult(uri.rsplit("/", 1)[1], uri, tuple(ids), tuple(isbns))
            for uri, (ids, isbns) in sorted(grouped.items())
        ),
        truncated,
        ("ISBN discovery row limit reached; candidates may be incomplete",) if truncated else (),
    )


def terms(statements: tuple[MADBStatement, ...], *predicates: str) -> tuple[RDFTerm, ...]:
    return tuple(s.object for s in statements if s.predicate in predicates)


def _credits(statements: tuple[MADBStatement, ...]) -> tuple[MADBCredit, ...]:
    credits = []
    for statement in statements:
        if statement.predicate not in (
            SCHEMA_NS + "creator",
            SCHEMA_NS + "contributor",
            PROPERTY_NS + "originalWorkCreator",
            PROPERTY_NS + "creator",
        ):
            continue
        raw = statement.object
        name, role = None, None
        if raw.kind == "literal" and raw.language in (None, "ja"):
            match = re.fullmatch(r"\[([^\[\]]+)\](.+)", raw.value)
            if match:
                role, name = match.groups()
            elif not raw.value.startswith("["):
                name = raw.value or None
        # No role-to-host mapping, name matching, or positional Agent association.
        credits.append(MADBCredit(raw, statement.predicate, name, role))
    return tuple(credits)


def _external(statements: tuple[MADBStatement, ...], kind: ResourceKind) -> tuple[ExternalIdentifier, ...]:
    uri = statements[0].subject
    output = []
    if kind == "book":
        output.append(ExternalIdentifier("madb_uri", RDFTerm("uri", uri), uri, uri, "@id"))
    names = terms(statements, SCHEMA_NS + "name") if kind == "holding" else ()
    provider = names[0].value if len(names) == 1 and names[0].kind == "literal" else None
    for s in statements:
        raw, scheme, normalized = s.object, None, None
        text = raw.value if raw.kind in ("literal", "uri") else None
        if kind == "book" and s.predicate == SCHEMA_NS + "identifier":
            scheme, normalized = "madb_book_id", text
        elif s.predicate == SCHEMA_NS + "isbn":
            scheme = "isbn"
            normalized = isbn13(text) if raw.kind == "literal" else None
        elif s.predicate == PROPERTY_NS + "jpno":
            scheme, normalized = "jpno", text
        elif s.predicate == PROPERTY_NS + "dataUrl":
            scheme = "data_url"
            if text and re.fullmatch(r"https://ndlsearch\.ndl\.go\.jp/books/[A-Za-z0-9_-]+", text):
                scheme, normalized = "ndl_search_url", text
        elif kind == "agent" and s.predicate == PROPERTY_NS + "ndla":
            scheme = "ndl_authority_uri"
            if text and re.fullmatch(r"https?://id\.ndl\.go\.jp/auth/[A-Za-z0-9/_-]+", text):
                normalized = text
        elif kind == "holding" and s.predicate == PROPERTY_NS + "materialIdentifier":
            scheme, normalized = "holding_material_id", text if provider else None
        if scheme:
            output.append(ExternalIdentifier(scheme, raw, normalized, uri, s.predicate, provider))
    return tuple(output)


def parse_resource(content: bytes, uri: str, kind: ResourceKind, limit: int, *, book_uri: str = ""):
    rows = select_rows(content, {"p", "o"}, {"p", "o"}, limit)
    if not rows:
        raise MADBError("not_found", "MADB resource not found")
    if any(row["p"].kind != "uri" for row in rows):
        raise MADBError("schema", "RDF predicate must be a URI")
    statements = tuple(dict.fromkeys(MADBStatement(uri, row["p"].value, row["o"]) for row in rows))
    truncated = len(rows) == limit
    types = terms(statements, RDF_NS + "type")
    expected = (
        CLASS_NS
        + {"book": "MangaBook", "series": "MangaBookSeries", "agent": "Agent", "holding": "Supplement"}[kind]
    )
    if RDFTerm("uri", expected) not in types:
        raise MADBError("truncated" if truncated else "schema", "Required MADB rdf:type missing")
    identifier = uri.rsplit("/", 1)[1]
    ids = terms(statements, SCHEMA_NS + "identifier")
    if (kind in ("book", "series") and not ids) or any(
        t.kind != "literal" or t.value != identifier for t in ids
    ):
        raise MADBError("truncated" if truncated and not ids else "schema", "MADB URI/identifier mismatch")
    common = {"uri": uri, "statements": statements, "completeness": "truncated" if truncated else "complete"}
    if kind == "agent":
        return MADBAgentRecord(
            **common,
            names=terms(statements, SCHEMA_NS + "name"),
            classifications=terms(
                statements,
                PROPERTY_NS + "additionalGenre",
                SCHEMA_NS + "genre",
                SCHEMA_NS + "additionalType",
                RDF_NS + "type",
            ),
            ndla=terms(statements, PROPERTY_NS + "ndla"),
            external_identifiers=_external(statements, kind),
        )
    if kind == "holding":
        return MADBHoldingRecord(
            **common,
            book_uri=book_uri,
            provider_names=terms(statements, SCHEMA_NS + "name"),
            material_identifiers=terms(statements, PROPERTY_NS + "materialIdentifier"),
            owner_identifiers=terms(statements, PROPERTY_NS + "ownerIdentifier"),
            notes=terms(statements, SCHEMA_NS + "note", PROPERTY_NS + "note"),
            external_identifiers=_external(statements, kind),
        )
    shared = {
        **common,
        "id": identifier,
        "types": tuple(t.value for t in types if t.kind == "uri"),
        "titles": terms(statements, SCHEMA_NS + "name"),
        "alternative_titles": terms(statements, SCHEMA_NS + "alternateName"),
        "publishers": terms(statements, SCHEMA_NS + "publisher"),
        "publisher_references": terms(statements, DCTERMS_NS + "publisher"),
        "labels": terms(statements, SCHEMA_NS + "brand"),
        "credits": _credits(statements),
        "creator_references": terms(statements, DCTERMS_NS + "creator"),
        "editions": terms(statements, SCHEMA_NS + "version"),
        "publication_dates": terms(statements, SCHEMA_NS + "datePublished"),
    }
    if kind == "series":
        return MADBSeriesRecord(**shared, number_of_items=terms(statements, SCHEMA_NS + "numberOfItems"))
    return MADBBookRecord(
        **shared,
        subtitles=terms(statements, SCHEMA_NS + "alternativeHeadline"),
        display_labels=terms(statements, RDFS_NS + "label"),
        volumes=terms(statements, SCHEMA_NS + "volumeNumber"),
        positions=terms(statements, SCHEMA_NS + "position"),
        isbns=terms(statements, SCHEMA_NS + "isbn"),
        series_statements=terms(statements, PROPERTY_NS + "seriesName"),
        series_uris=tuple(t.value for t in terms(statements, SCHEMA_NS + "isPartOf") if t.kind == "uri"),
        languages=terms(statements, SCHEMA_NS + "inLanguage"),
        genres=terms(statements, SCHEMA_NS + "genre"),
        extent=tuple(
            s for s in statements if s.predicate in (SCHEMA_NS + "size", SCHEMA_NS + "numberOfPages")
        ),
        external_identifiers=_external(statements, kind),
    )
