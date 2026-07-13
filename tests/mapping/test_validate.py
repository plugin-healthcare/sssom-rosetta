"""Tests for mapping/validate.py, using small fixture ontology graphs (no network)."""

import pytest
from linkml_runtime.utils.metamodelcore import URI
from rdflib import Graph

from sssom_rosetta.mapping.author import build_mapping
from sssom_rosetta.mapping.validate import (
    SchemaConformanceError,
    validate_mapping_set,
    validate_referential_integrity,
    validate_schema_conformance,
)
from sssom_rosetta.models.sssom import Mapping, MappingSet

MAPPING_SET_ID = URI("https://example.org/mappings/omop-onz-g")
LICENSE = URI("https://creativecommons.org/publicdomain/zero/1.0/")

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


@pytest.fixture
def valid_mapping_set(omop_graph: Graph, onz_g_graph: Graph) -> MappingSet:
    mapping = build_mapping(
        subject_curie="omop:Person",
        predicate="skos:exactMatch",
        object_curie="onz-g:Client",
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
        mapping_justification="semapv:ManualMappingCuration",
    )
    return MappingSet(
        mapping_set_id=MAPPING_SET_ID, license=LICENSE, mappings=[mapping]
    )


def test_validate_schema_conformance_accepts_valid_mapping_set(
    valid_mapping_set: MappingSet,
) -> None:
    result = validate_schema_conformance(valid_mapping_set)
    assert isinstance(result, MappingSet)
    assert len(result.mappings or []) == 1


def test_validate_schema_conformance_accepts_raw_dict() -> None:
    payload = {
        "mapping_set_id": MAPPING_SET_ID,
        "license": LICENSE,
        "mappings": [
            {
                "subject_id": "omop:Person",
                "predicate_id": "skos:exactMatch",
                "object_id": "onz-g:Client",
                "mapping_justification": "semapv:ManualMappingCuration",
            }
        ],
    }
    result = validate_schema_conformance(payload)
    assert isinstance(result, MappingSet)


def test_validate_schema_conformance_rejects_missing_required_field() -> None:
    with pytest.raises(SchemaConformanceError):
        validate_schema_conformance({"mappings": [{"subject_id": "omop:Person"}]})


def test_validate_referential_integrity_no_issues_for_valid_set(
    valid_mapping_set: MappingSet, omop_graph: Graph, onz_g_graph: Graph
) -> None:
    issues = validate_referential_integrity(
        valid_mapping_set,
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
    )
    assert issues == []


def test_validate_referential_integrity_flags_missing_subject(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    bad_mapping = Mapping(
        subject_id="omop:NoSuchClass",
        predicate_id="skos:exactMatch",
        object_id="onz-g:Client",
        mapping_justification="semapv:ManualMappingCuration",
    )
    mapping_set = MappingSet(
        mapping_set_id=MAPPING_SET_ID, license=LICENSE, mappings=[bad_mapping]
    )
    issues = validate_referential_integrity(
        mapping_set,
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
    )
    assert len(issues) == 1
    assert issues[0].field == "subject_id"
    assert issues[0].curie == "omop:NoSuchClass"


def test_validate_referential_integrity_flags_unknown_prefix(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    bad_mapping = Mapping(
        subject_id="nope:Thing",
        predicate_id="skos:exactMatch",
        object_id="onz-g:Client",
        mapping_justification="semapv:ManualMappingCuration",
    )
    mapping_set = MappingSet(
        mapping_set_id=MAPPING_SET_ID, license=LICENSE, mappings=[bad_mapping]
    )
    issues = validate_referential_integrity(
        mapping_set,
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
    )
    assert len(issues) == 1
    assert issues[0].field == "subject_id"


def test_validate_mapping_set_is_valid_for_good_data(
    valid_mapping_set: MappingSet, omop_graph: Graph, onz_g_graph: Graph
) -> None:
    result = validate_mapping_set(
        valid_mapping_set,
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
    )
    assert result.is_valid
    assert result.issues == []


def test_validate_mapping_set_reports_issues_for_bad_data(
    omop_graph: Graph, onz_g_graph: Graph
) -> None:
    bad_mapping = Mapping(
        subject_id="omop:Person",
        predicate_id="skos:exactMatch",
        object_id="onz-g:NoSuchClass",
        mapping_justification="semapv:ManualMappingCuration",
    )
    mapping_set = MappingSet(
        mapping_set_id=MAPPING_SET_ID, license=LICENSE, mappings=[bad_mapping]
    )
    result = validate_mapping_set(
        mapping_set,
        prefix_map=PREFIX_MAP,
        subject_graph=omop_graph,
        object_graph=onz_g_graph,
    )
    assert not result.is_valid
    assert len(result.issues) == 1
    assert result.issues[0].field == "object_id"
