"""Benchmark rdflib vs. maplib for *constructing* the OMOP SKOS graph.

Companion to ``scripts/benchmark_sparql.py`` (which benchmarked maplib for
*querying* an already-built Turtle graph). This script benchmarks the
construction step itself: ``sssom_rosetta.vocabulary.omop.build_graph`` now
maps ``CONCEPT.csv`` / ``CONCEPT_RELATIONSHIP.csv`` through a maplib OTTR
template (see ``.agents/plan/2026-07-30-implementation-maplib.md``), replacing
the previous rdflib triple-add loop. The rdflib version is kept here, inline,
as ``_build_graph_rdflib`` purely for this comparison -- it is no longer part
of the shipped pipeline.

Run against an ingested OMOP/Athena release directory (produced by
``rosetta vocabulary ingest omop <zip>``)::

    uv run python scripts/benchmark_omop_construction.py [path/to/release_dir]

Defaults to the release directory ``rosetta vocabulary build-omop`` itself
would use, i.e. wherever ``CONCEPT.csv`` / ``CONCEPT_RELATIONSHIP.csv`` are
findable under ``data/vocabularies/omop/``.
"""

from __future__ import annotations

import sys
import time
from contextlib import contextmanager
from pathlib import Path

from rdflib import Graph, Literal
from rdflib.namespace import RDF, SKOS

from sssom_rosetta.vocabulary import omop
from sssom_rosetta.vocabulary.namespaces import omop_iri, source_concept_iri

DEFAULT_DIR = Path("data/vocabularies/omop")


@contextmanager
def timed(label: str):
    """Print elapsed wall-clock time for the wrapped block."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"{label}: {elapsed:.2f}s")


def _build_graph_rdflib(concepts, relationships) -> Graph:  # noqa: ANN001
    """The pre-maplib implementation of ``omop.build_graph``, kept only for
    this benchmark's before/after comparison (not used by the pipeline).
    """
    predicates = {
        "Maps to": SKOS.exactMatch,
        "Is a": SKOS.broadMatch,
        "Subsumes": SKOS.narrowMatch,
    }
    graph = Graph()
    for row in concepts.iter_rows(named=True):
        subject = omop_iri(row["concept_id"])
        graph.add((subject, RDF.type, SKOS.Concept))
        if row["concept_name"]:
            graph.add((subject, SKOS.prefLabel, Literal(row["concept_name"], lang="en")))
        if row["concept_code"]:
            graph.add((subject, SKOS.notation, Literal(row["concept_code"])))
        source = source_concept_iri(row["vocabulary_id"], row["concept_code"])
        if source is not None:
            graph.add((subject, SKOS.exactMatch, source))
    for row in relationships.iter_rows(named=True):
        predicate = predicates[row["relationship_id"]]
        graph.add((omop_iri(row["concept_id_1"]), predicate, omop_iri(row["concept_id_2"])))
    return graph


def benchmark_construction(release_dir: Path) -> None:
    """Compare rdflib vs. maplib construction time for the OMOP graph."""
    print(f"\n=== OMOP graph construction: rdflib vs. maplib ({release_dir}) ===")

    concept_csv = omop._exact(release_dir, "CONCEPT.csv")  # noqa: SLF001
    relationship_csv = omop._exact(release_dir, "CONCEPT_RELATIONSHIP.csv")  # noqa: SLF001

    with timed("load CONCEPT.csv + CONCEPT_RELATIONSHIP.csv (shared, not timed separately)"):
        concepts = omop.load_target_concepts(concept_csv)
        relationships = omop.load_relationships(relationship_csv, concepts["concept_id"])
    print(f"Concepts: {concepts.height:,}  Relationships: {relationships.height:,}")

    with timed("rdflib build_graph"):
        rdflib_graph = _build_graph_rdflib(concepts, relationships)
    print(f"rdflib triples: {len(rdflib_graph):,}")

    with timed("maplib build_graph"):
        maplib_model = omop.build_graph(concepts, relationships)
    print(f"maplib triples: {maplib_model.size():,}")


def main() -> None:
    """Entry point: resolve the release directory and run the benchmark."""
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    release_dir = Path(arg) if arg else DEFAULT_DIR
    if not release_dir.is_dir():
        raise SystemExit(f"Release directory not found: {release_dir}")
    benchmark_construction(release_dir)


if __name__ == "__main__":
    main()
