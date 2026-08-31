"""Merge vocabulary Turtle files into one combined output.

The graphs share IRI schemes (``sct:``/``loinc:``/``omop:``/``dhd-dt:`` etc.
from :mod:`~sssom_rosetta.vocabulary.namespaces`), so concepts referenced from
multiple sides coincide automatically once their triples live in a single
graph — that is how an OMOP ``concept_id`` node ends up connected to the
LOINC-SNOMED ontology hierarchy or a DHD thesaurus concept.

:func:`merge_ttl_files` is the file-based merge path used by the ``rosetta
vocabulary merge`` CLI command. It uses :mod:`maplib` (``Model.read`` /
``Model.write``) rather than rdflib's ``Graph.parse``/``serialize``: on the
production-scale OMOP export (944 MB / ~19.8M triples) maplib reads the file
in roughly a minute, whereas rdflib's pure-Python parser is an order of
magnitude slower and made ``just vocab-merge`` impractically slow. maplib
reads triples straight from Turtle text, so it does not care which library
wrote the file.

``omop.build_graph`` returns a ``maplib.Model`` while ``loinc_snomed`` and
``snomed_international`` still build ``rdflib.Graph`` (only OMOP's
construction step moved to maplib; see :doc:`/vocabularies/index` for why).
:func:`merge_graphs` accepts either kind of graph object, normalises both to
rdflib triples, and merges them in-memory; it remains available for callers
that need an in-memory rdflib ``Graph`` (e.g. tests asserting cross-graph
SPARQL-style triple lookups) but is no longer used by the CLI's file-merge
path.
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

_PREFIXES = {prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()} | {
    "skos": str(SKOS),
    "owl": str(OWL),
}


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
    """Read each input Turtle file into one maplib ``Model`` and write ``output_path``.

    ``Model.read`` accumulates triples across repeated calls on the same
    instance, so reading every input into a single model has the same effect
    as an rdflib union merge, without the slow rdflib parse/serialize
    round-trip.
    """
    import maplib  # noqa: PLC0415 -- deferred so this module has no import-time maplib dependency

    model = maplib.Model()
    for path in inputs:
        model.read(str(path), format="turtle", parallel=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(output_path), format="turtle", prefixes=_PREFIXES)
    return output_path
