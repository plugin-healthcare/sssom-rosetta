"""Build a lightweight SKOS/RDFS Turtle graph from a LOINC-SNOMED RF2 release.

Reads the RF2 Snapshot files with :mod:`rf2` (polars) and emits, per active
concept:

* ``sct:<id> a skos:Concept`` (also ``owl:Class`` for tooling compatibility),
* preferred term → ``skos:prefLabel`` / ``rdfs:label`` (language-tagged),
* synonyms → ``skos:altLabel``,
* ``Is a`` → ``rdfs:subClassOf`` **and** ``skos:broadMatch`` (child → parent).

Full OWL-DL logical definitions from the OWL Expression refset are intentionally
not materialised here — see
``.agents/plan/2026-07-21-owl-dl-classification-deferral-note.md``.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from sssom_rosetta.vocabulary import rf2
from sssom_rosetta.vocabulary.fetch import find_file
from sssom_rosetta.vocabulary.namespaces import PREFIX_MAP, sct_iri


def _bind_prefixes(graph: Graph) -> None:
    for prefix, namespace in PREFIX_MAP.items():
        graph.bind(prefix, namespace)
    graph.bind("skos", SKOS)
    graph.bind("owl", OWL)


def build_graph(
    concept: pl.DataFrame,
    description: pl.DataFrame,
    language: pl.DataFrame,
    relationship: pl.DataFrame,
) -> Graph:
    """Assemble an ``rdflib.Graph`` from already-loaded RF2 DataFrames.

    Kept separate from :func:`build_from_release` so tests can drive it with
    small in-memory polars DataFrames instead of on-disk fixtures.
    """
    graph = Graph()
    _bind_prefixes(graph)

    for row in rf2.active_rows(concept).iter_rows(named=True):
        subject = sct_iri(row["id"])
        graph.add((subject, RDF.type, SKOS.Concept))
        graph.add((subject, RDF.type, OWL.Class))

    for row in rf2.preferred_terms(description, language).iter_rows(named=True):
        subject = sct_iri(row["conceptId"])
        label = Literal(row["term"], lang=row["lang"])
        graph.add((subject, SKOS.prefLabel, label))
        graph.add((subject, RDFS.label, label))

    for row in rf2.synonyms(description).iter_rows(named=True):
        subject = sct_iri(row["conceptId"])
        graph.add((subject, SKOS.altLabel, Literal(row["term"], lang=row["lang"])))

    for row in rf2.isa_edges(relationship).iter_rows(named=True):
        child: URIRef = sct_iri(row["sourceId"])
        parent: URIRef = sct_iri(row["destinationId"])
        graph.add((child, RDFS.subClassOf, parent))
        graph.add((child, SKOS.broadMatch, parent))

    return graph


def build_from_release(release_dir: Path) -> Graph:
    """Locate RF2 Snapshot files under ``release_dir`` and build the graph."""
    concept = rf2.read_rf2(
        find_file(release_dir, prefix="sct2_Concept_Snapshot", suffix=".txt")
    )
    description = rf2.read_rf2(
        find_file(release_dir, prefix="sct2_Description_Snapshot", suffix=".txt")
    )
    language = rf2.read_rf2(
        find_file(release_dir, prefix="der2_cRefset_LanguageSnapshot", suffix=".txt")
    )
    relationship = rf2.read_rf2(
        find_file(release_dir, prefix="sct2_Relationship_Snapshot", suffix=".txt")
    )
    return build_graph(concept, description, language, relationship)


def write_ttl(graph: Graph, output_path: Path) -> Path:
    """Serialize ``graph`` to Turtle at ``output_path``, creating parents."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output_path), format="turtle")
    return output_path
