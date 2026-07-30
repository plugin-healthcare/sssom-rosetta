"""Merge the LOINC-SNOMED and OMOP graphs into one vocabulary Turtle file.

The two graphs share IRI schemes (``sct:``/``loinc:`` etc. from
:mod:`~sssom_rosetta.vocabulary.namespaces`), so concepts referenced from both
sides coincide automatically once their triples live in a single graph — that
is how an OMOP ``concept_id`` node ends up connected to the LOINC-SNOMED
ontology hierarchy.

``omop.build_graph`` returns a ``maplib.Model`` while ``loinc_snomed`` and
``snomed_international`` still build ``rdflib.Graph`` (see
``.agents/plan/2026-07-30-implementation-maplib.md`` -- only OMOP's
construction step moved to maplib). :func:`merge_graphs` accepts either kind
of graph object and normalises both to rdflib triples before merging.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from rdflib import Graph
from rdflib.namespace import OWL, SKOS

from sssom_rosetta.vocabulary.namespaces import PREFIX_MAP

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from rdflib.term import Node


class _MaplibModel(Protocol):
    """Structural type for a maplib ``Model``, to avoid an import-time dependency."""

    def writes(self, format: str) -> str: ...  # noqa: A002


def _iter_triples(graph: Graph | _MaplibModel) -> Iterator[tuple[Node, Node, Node]]:
    """Yield ``(s, p, o)`` triples from an rdflib ``Graph`` or a maplib ``Model``."""
    if isinstance(graph, Graph):
        yield from graph
        return
    # maplib.Model: round-trip through N-Triples so we get plain rdflib terms
    # without importing maplib here (this module has no runtime need for it).
    reparsed = Graph()
    reparsed.parse(data=graph.writes(format="ntriples"), format="ntriples")
    yield from reparsed


def merge_graphs(*graphs: Graph | _MaplibModel) -> Graph:
    """Combine any number of graphs into one, re-binding the shared prefixes."""
    merged = Graph()
    for prefix, namespace in PREFIX_MAP.items():
        merged.bind(prefix, namespace)
    merged.bind("skos", SKOS)
    merged.bind("owl", OWL)
    for graph in graphs:
        for triple in _iter_triples(graph):
            merged.add(triple)
    return merged


def merge_ttl_files(inputs: list[Path], output_path: Path) -> Path:
    """Parse each input Turtle file, merge, and serialize to ``output_path``."""
    graphs = []
    for path in inputs:
        graph = Graph()
        graph.parse(str(path), format="turtle")
        graphs.append(graph)
    merged = merge_graphs(*graphs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.serialize(destination=str(output_path), format="turtle")
    return output_path
