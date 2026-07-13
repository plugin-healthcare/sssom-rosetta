"""Tests for ontology/catalog.py, using small fixture subgraphs (no network, no full ontology downloads)."""

from rdflib import Graph

from sssom_rosetta.ontology.catalog import (
    list_classes,
    list_properties,
    resolve_label,
    resource_exists,
)

FIXTURE_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ex: <http://example.org/onto#> .

ex:Person a owl:Class ;
    rdfs:label "Person" .

ex:Client a owl:Class ;
    skos:prefLabel "Client" .

ex:LegacyThing a rdfs:Class .

ex:hasName a owl:DatatypeProperty ;
    rdfs:label "has name" .

ex:relatesTo a rdf:Property .

ex:Person rdfs:subClassOf ex:LegacyThing .

ex:Unlabelled a owl:Class .
"""


def _fixture_graph() -> Graph:
    graph = Graph()
    graph.parse(data=FIXTURE_TTL, format="turtle")
    return graph


def test_list_classes_finds_owl_and_rdfs_classes() -> None:
    graph = _fixture_graph()
    classes = list_classes(graph)
    assert classes == sorted(
        [
            "http://example.org/onto#Person",
            "http://example.org/onto#Client",
            "http://example.org/onto#LegacyThing",
            "http://example.org/onto#Unlabelled",
        ]
    )


def test_list_properties_finds_all_property_kinds() -> None:
    graph = _fixture_graph()
    properties = list_properties(graph)
    assert properties == sorted(
        [
            "http://example.org/onto#hasName",
            "http://example.org/onto#relatesTo",
        ]
    )


def test_resolve_label_prefers_rdfs_label() -> None:
    graph = _fixture_graph()
    assert resolve_label(graph, "http://example.org/onto#Person") == "Person"


def test_resolve_label_falls_back_to_skos_pref_label() -> None:
    graph = _fixture_graph()
    assert resolve_label(graph, "http://example.org/onto#Client") == "Client"


def test_resolve_label_returns_none_when_unresolved() -> None:
    graph = _fixture_graph()
    assert resolve_label(graph, "http://example.org/onto#Unlabelled") is None
    assert resolve_label(graph, "http://example.org/onto#DoesNotExist") is None


def test_resource_exists_true_for_subject_and_object() -> None:
    graph = _fixture_graph()
    assert resource_exists(graph, "http://example.org/onto#Person") is True
    assert resource_exists(graph, "http://example.org/onto#LegacyThing") is True


def test_resource_exists_false_for_unknown_iri() -> None:
    graph = _fixture_graph()
    assert resource_exists(graph, "http://example.org/onto#DoesNotExist") is False
