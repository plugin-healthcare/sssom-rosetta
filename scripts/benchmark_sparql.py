"""Benchmark rdflib vs. maplib in-memory SPARQL over a Turtle vocabulary graph.

Run against an already-built vocabulary graph under ``build/vocabularies/``
(produced by ``rosetta vocabulary build-omop`` / ``rosetta vocabulary
merge``). Not part of the pytest suite — it's a one-off measurement script,
kept for reproducibility (see
``.agents/plan/2026-07-28-jelly-maplib-serialization-and-sparql.md``).

A Jelly-based binary serialization format was also trialled here and
rejected: on this project's real ~20M-triple vocabulary graph it was larger
on disk than Turtle, compressed far worse under gzip, and was slower for
rdflib to parse back — see the plan doc for the numbers. That code path has
been removed; ``pyjelly`` is no longer a dependency.

Usage::

    uv run python scripts/benchmark_sparql.py [path/to/graph.ttl]

Defaults to ``build/vocabularies/omop.ttl`` (falls back to any ``*.ttl``
found under ``build/vocabularies/`` if that specific file is missing).
"""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from pathlib import Path

from rdflib import Graph

DEFAULT_DIR = Path("build/vocabularies")

# A handful of representative SPARQL queries over the SKOS vocabulary shape
# (see vocabulary/omop.py's module docstring for the predicates in use).
QUERIES = {
    "count_all": "SELECT (COUNT(*) AS ?c) WHERE { ?s ?p ?o }",
    "count_concepts": (
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "SELECT (COUNT(?s) AS ?c) WHERE { ?s a skos:Concept }"
    ),
    "broad_match_sample": (
        "PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n"
        "SELECT ?child ?parent WHERE { ?child skos:broadMatch ?parent } LIMIT 20"
    ),
    "label_lookup": (
        'PREFIX skos: <http://www.w3.org/2004/02/skos/core#>\n'
        'SELECT ?s WHERE { ?s skos:prefLabel "Ondansetron 4 MG Disintegrating '
        'Tablet [Zofran ODT]"@en }'
    ),
}


@contextmanager
def timed(label: str):
    """Print elapsed wall-clock time for the wrapped block."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.2f}s")


def find_input(arg: str | None) -> Path:
    """Resolve the Turtle file to benchmark from a CLI arg or sensible default."""
    if arg:
        return Path(arg)
    default = DEFAULT_DIR / "omop.ttl"
    if default.exists():
        return default
    candidates = sorted(DEFAULT_DIR.glob("*.ttl"))
    if not candidates:
        raise SystemExit(f"No .ttl files found under {DEFAULT_DIR}")
    return candidates[0]


def benchmark_sparql(ttl_path: Path) -> None:
    """Compare rdflib vs. maplib load time and SPARQL query time."""
    print(f"\n=== SPARQL: rdflib vs. maplib ({ttl_path}) ===")

    graph = Graph()
    with timed("rdflib parse (turtle)"):
        graph.parse(str(ttl_path), format="turtle")
    print(f"Triples: {len(graph):,}")

    import maplib

    model = maplib.Model()
    with timed("maplib read (turtle)"):
        model.read(str(ttl_path))

    for name, query in QUERIES.items():
        print(f"\n-- {name} --")
        with timed(f"rdflib  [{name}]"):
            list(graph.query(query))
        with timed(f"maplib  [{name}]"):
            model.query(query)


def main() -> None:
    """Entry point: resolve the input path and run the benchmark."""
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    benchmark_sparql(find_input(arg))


if __name__ == "__main__":
    main()
