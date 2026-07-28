"""Tests for mapping/gephi.py: RDF -> networkx -> GEXF export for Gephi.

Covers both the ontology-shaped predicate set (``ONTOLOGY_PREDICATES``,
which includes ``rdfs:subClassOf``) and the vocabulary-shaped predicate set
(``VOCABULARY_PREDICATES``, SKOS mapping predicates only), since both share
the same filter/convert code but exercise different edges. See
``.agents/plan/2026-07-28-gephi-gexf-export.md`` for the design rationale.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest
from rdflib import Graph, URIRef
from rdflib.namespace import RDFS, SKOS

from sssom_rosetta.mapping.gephi import (
    ONTOLOGY_PREDICATES,
    SKOS_MAPPING_PREDICATES,
    VOCABULARY_PREDICATES,
    build_vocabulary_graph,
    to_networkx,
    write_gexf,
)

# A fixture graph shaped like the ontology export: two "ontologies", an
# rdfs:subClassOf hierarchy edge, a skos:exactMatch mapping edge, several
# literal-valued metadata triples per node (including a repeated
# skos:altLabel), and one irrelevant triple that must be filtered out.
ONTOLOGY_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix omop: <https://w3id.org/omop/ontology#> .
@prefix onz-g: <http://purl.org/ozo/onz-g#> .

omop:Person a owl:Class ;
    rdfs:label "Person" ;
    skos:prefLabel "Person"@en ;
    skos:altLabel "Individual"@en, "Human"@en ;
    skos:notation "P1" ;
    rdfs:comment "A human being."@en ;
    owl:versionInfo "irrelevant, not an edge predicate" .

onz-g:Client a owl:Class ;
    rdfs:label "Client" ;
    rdfs:subClassOf onz-g:Person .

onz-g:Person a owl:Class .

omop:Person skos:exactMatch onz-g:Client .
"""

# A fixture graph shaped like the vocabulary export: no rdfs:subClassOf,
# hierarchy expressed only via skos:broadMatch/narrowMatch.
VOCABULARY_TTL = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix sct: <http://snomed.info/id/> .
@prefix omopconcept: <https://w3id.org/omop/concept/> .

sct:73211009 a skos:Concept ;
    skos:prefLabel "Diabetes mellitus"@en .

omopconcept:201820 a skos:Concept ;
    skos:prefLabel "Diabetes mellitus"@en ;
    skos:exactMatch sct:73211009 .

sct:73211010 a skos:Concept ;
    skos:prefLabel "Type 2 diabetes"@en ;
    skos:broadMatch sct:73211009 .
"""


def _parse(ttl: str) -> Graph:
    graph = Graph()
    graph.parse(data=ttl, format="turtle")
    return graph


def test_ontology_predicates_include_subclassof_and_skos_but_not_label() -> None:
    assert RDFS.subClassOf in ONTOLOGY_PREDICATES
    assert SKOS_MAPPING_PREDICATES <= ONTOLOGY_PREDICATES
    assert RDFS.label not in ONTOLOGY_PREDICATES


def test_vocabulary_predicates_are_exactly_skos_mapping_predicates() -> None:
    assert VOCABULARY_PREDICATES == SKOS_MAPPING_PREDICATES
    assert RDFS.subClassOf not in VOCABULARY_PREDICATES
    assert RDFS.label not in VOCABULARY_PREDICATES


def test_ontology_graph_has_expected_edges_and_no_phantom_label_nodes() -> None:
    graph = _parse(ONTOLOGY_TTL)

    multidigraph = to_networkx(graph, ONTOLOGY_PREDICATES)

    assert multidigraph.number_of_nodes() == 3
    assert multidigraph.number_of_edges() == 2
    for node in multidigraph.nodes:
        assert node not in {"Person", "Client"}, "rdfs:label must not become a node"


def test_ontology_node_carries_full_literal_metadata() -> None:
    graph = _parse(ONTOLOGY_TTL)

    multidigraph = to_networkx(graph, ONTOLOGY_PREDICATES)

    person = URIRef("https://w3id.org/omop/ontology#Person")
    attrs = multidigraph.nodes[person]
    assert attrs["rdfs_label"] == "Person"
    assert attrs["skos_prefLabel"] == "Person"
    assert attrs["skos_altLabel"] in {"Individual; Human", "Human; Individual"}
    assert attrs["skos_notation"] == "P1"
    assert attrs["rdfs_comment"] == "A human being."
    assert attrs["type"] == "owl:Class"
    assert attrs["label"] == "Person"
    assert attrs["source"] == "omop"
    assert all(isinstance(value, str) for value in attrs.values())


def test_ontology_node_without_metadata_falls_back_to_curie_label() -> None:
    graph = _parse(ONTOLOGY_TTL)

    multidigraph = to_networkx(graph, ONTOLOGY_PREDICATES)

    onz_g_person = URIRef("http://purl.org/ozo/onz-g#Person")
    attrs = multidigraph.nodes[onz_g_person]
    assert attrs["label"] == "onz-g:Person"
    assert attrs["source"] == "onz-g"


def test_vocabulary_graph_has_no_subclassof_edges() -> None:
    graph = _parse(VOCABULARY_TTL)

    multidigraph = to_networkx(graph, VOCABULARY_PREDICATES)

    assert multidigraph.number_of_nodes() == 3
    assert multidigraph.number_of_edges() == 2
    for _, _, data in multidigraph.edges(data=True):
        assert data["predicate"] != "rdfs_subClassOf"


def test_vocabulary_node_attributes() -> None:
    graph = _parse(VOCABULARY_TTL)

    multidigraph = to_networkx(graph, VOCABULARY_PREDICATES)

    concept = URIRef("https://w3id.org/omop/concept/201820")
    attrs = multidigraph.nodes[concept]
    assert attrs["skos_prefLabel"] == "Diabetes mellitus"
    assert attrs["type"] == "skos:Concept"
    assert attrs["source"] == "omopconcept"


def test_predicates_override_is_honoured() -> None:
    graph = _parse(ONTOLOGY_TTL)

    only_subclassof = frozenset({RDFS.subClassOf})
    multidigraph = to_networkx(graph, only_subclassof)

    assert multidigraph.number_of_edges() == 1
    for _, _, data in multidigraph.edges(data=True):
        assert data["predicate"] == "rdfs_subClassOf"


def test_write_gexf_roundtrips_node_and_edge_counts(tmp_path: Path) -> None:
    graph = _parse(ONTOLOGY_TTL)
    output_path = tmp_path / "build" / "gephi" / "omop-onz-g.gexf"

    write_gexf(graph, output_path, predicates=ONTOLOGY_PREDICATES)

    assert output_path.exists()
    roundtrip = nx.read_gexf(output_path)
    assert roundtrip.number_of_nodes() == 3
    assert roundtrip.number_of_edges() == 2


def test_write_gexf_creates_parent_directories(tmp_path: Path) -> None:
    graph = _parse(VOCABULARY_TTL)
    output_path = tmp_path / "nested" / "dir" / "rosetta-vocabularies.gexf"

    write_gexf(graph, output_path, predicates=VOCABULARY_PREDICATES)

    assert output_path.parent.is_dir()
    assert output_path.exists()


def test_build_vocabulary_graph_loads_ttl_and_writes_gexf(tmp_path: Path) -> None:
    ttl_path = tmp_path / "rosetta-vocabularies.ttl"
    ttl_path.write_text(VOCABULARY_TTL)
    output_path = tmp_path / "build" / "gephi" / "rosetta-vocabularies.gexf"

    build_vocabulary_graph(ttl_path, output_path)

    assert output_path.exists()
    roundtrip = nx.read_gexf(output_path)
    assert roundtrip.number_of_nodes() == 3


@pytest.mark.parametrize("predicates", [ONTOLOGY_PREDICATES, VOCABULARY_PREDICATES])
def test_edges_never_include_a_literal_valued_predicate(
    predicates: frozenset[URIRef],
) -> None:
    # Sanity check that neither default predicate set could ever produce a
    # literal-object edge (which would create a phantom node in networkx).
    assert RDFS.label not in predicates
    assert SKOS.notation not in predicates
