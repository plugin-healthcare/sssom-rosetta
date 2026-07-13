"""Tests for mapping/author.py, using small fixture ontology graphs (no network)."""

import pytest
from rdflib import Graph

from sssom_rosetta.mapping.author import (
    UnknownPrefixError,
    UnresolvableCurieError,
    build_mapping,
    expand_curie,
    resolve_curie,
)

OMOP_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix omop: <https://w3id.org/omop/ontology#> .

omop:Person a owl:Class ;
    rdfs:label "Person" .
"""

ONZ_G_TTL = """
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix onz-g: <http://purl.org/ozo/onz-g#> .

onz-g:Client a owl:Class ;
    rdfs:label "Client" .
"""

PREFIX_MAP = {
    "omop": "https://w3id.org/omop/ontology#",
    "onz-g": "http://purl.org/ozo/onz-g#",
}


@pytest.fixture
def omop_graph() -> Graph:
    graph = Graph()
    graph.parse(data=OMOP_TTL, format="turtle")
    return graph


@pytest.fixture
def onz_g_graph() -> Graph:
    graph = Graph()
    graph.parse(data=ONZ_G_TTL, format="turtle")
    return graph


def test_expand_curie() -> None:
    assert (
        expand_curie("omop:Person", PREFIX_MAP)
        == "https://w3id.org/omop/ontology#Person"
    )


def test_expand_curie_unknown_prefix_raises() -> None:
    with pytest.raises(UnknownPrefixError):
        expand_curie("nope:Thing", PREFIX_MAP)


def test_expand_curie_missing_separator_raises() -> None:
    with pytest.raises(ValueError, match="Not a CURIE"):
        expand_curie("NotACurie", PREFIX_MAP)


def test_resolve_curie_success(omop_graph: Graph) -> None:
    iri = resolve_curie("omop:Person", PREFIX_MAP, omop_graph)
    assert iri == "https://w3id.org/omop/ontology#Person"


def test_resolve_curie_unresolvable_raises(omop_graph: Graph) -> None:
    with pytest.raises(UnresolvableCurieError):
        resolve_curie("omop:DoesNotExist", PREFIX_MAP, omop_graph)


def test_build_mapping_accepts_valid_curie_pair(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    mapping = build_mapping(
        subject_curie="omop:Person",
        predicate="skos:exactMatch",
        object_curie="onz-g:Client",
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
        mapping_justification="semapv:ManualMappingCuration",
        author_id=["orcid:0000-0000-0000-0000"],
        confidence=0.9,
    )
    assert mapping.subject_id == "omop:Person"
    assert mapping.predicate_id == "skos:exactMatch"
    assert mapping.object_id == "onz-g:Client"
    assert mapping.mapping_justification == "semapv:ManualMappingCuration"
    assert mapping.author_id == ["orcid:0000-0000-0000-0000"]
    assert mapping.confidence == 0.9


def test_build_mapping_rejects_unknown_subject_iri(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    with pytest.raises(UnresolvableCurieError):
        build_mapping(
            subject_curie="omop:NoSuchClass",
            predicate="skos:exactMatch",
            object_curie="onz-g:Client",
            prefix_map=PREFIX_MAP,
            subject_graph=omop_graph,
            object_graph=onz_g_graph,
            mapping_justification="semapv:ManualMappingCuration",
        )


def test_build_mapping_rejects_unknown_object_iri(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    with pytest.raises(UnresolvableCurieError):
        build_mapping(
            subject_curie="omop:Person",
            predicate="skos:exactMatch",
            object_curie="onz-g:NoSuchClass",
            prefix_map=PREFIX_MAP,
            subject_graph=omop_graph,
            object_graph=onz_g_graph,
            mapping_justification="semapv:ManualMappingCuration",
        )


def test_build_mapping_rejects_unknown_prefix(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    with pytest.raises(UnknownPrefixError):
        build_mapping(
            subject_curie="nope:Person",
            predicate="skos:exactMatch",
            object_curie="onz-g:Client",
            prefix_map=PREFIX_MAP,
            subject_graph=omop_graph,
            object_graph=onz_g_graph,
            mapping_justification="semapv:ManualMappingCuration",
        )


def test_build_mapping_accepts_arbitrary_predicate(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    """No predicate allowlist: any predicate_id string is passed through (see AGENTS.md)."""
    mapping = build_mapping(
        subject_curie="omop:Person",
        predicate="owl:equivalentClass",
        object_curie="onz-g:Client",
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
        mapping_justification="semapv:ManualMappingCuration",
    )
    assert mapping.predicate_id == "owl:equivalentClass"
