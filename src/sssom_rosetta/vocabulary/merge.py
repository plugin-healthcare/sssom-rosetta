"""Merge the LOINC-SNOMED and OMOP graphs into one vocabulary Turtle file.

The two graphs share IRI schemes (``sct:``/``loinc:`` etc. from
:mod:`~sssom_rosetta.vocabulary.namespaces`), so concepts referenced from both
sides coincide automatically once their triples live in a single graph — that
is how an OMOP ``concept_id`` node ends up connected to the LOINC-SNOMED
ontology hierarchy.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph
from rdflib.namespace import OWL, SKOS

from sssom_rosetta.vocabulary.namespaces import PREFIX_MAP


def merge_graphs(*graphs: Graph) -> Graph:
    """Combine any number of graphs into one, re-binding the shared prefixes."""
    merged = Graph()
    for prefix, namespace in PREFIX_MAP.items():
        merged.bind(prefix, namespace)
    merged.bind("skos", SKOS)
    merged.bind("owl", OWL)
    for graph in graphs:
        for triple in graph:
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
