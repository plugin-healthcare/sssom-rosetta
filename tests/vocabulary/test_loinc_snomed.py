"""Tests for RF2 polars readers and the LOINC-SNOMED graph builder."""

from __future__ import annotations

import polars as pl
from rdflib import Literal, URIRef
from rdflib.namespace import RDF, RDFS, SKOS

from sssom_rosetta.vocabulary import loinc_snomed, rf2
from sssom_rosetta.vocabulary.namespaces import sct_iri

# --- synthetic RF2 frames -------------------------------------------------

CONCEPT = pl.DataFrame(
    {
        "id": ["100001", "100002", "100003"],
        "effectiveTime": ["20260101"] * 3,
        "active": ["1", "1", "0"],
        "moduleId": ["11010000107"] * 3,
        "definitionStatusId": ["900000000000074008"] * 3,
    }
)

DESCRIPTION = pl.DataFrame(
    {
        "id": ["200001", "200002", "200003"],
        "effectiveTime": ["20260101"] * 3,
        "active": ["1", "1", "1"],
        "moduleId": ["11010000107"] * 3,
        "conceptId": ["100001", "100001", "100002"],
        "languageCode": ["en", "en", "en"],
        "typeId": [
            rf2.FSN_TYPE_ID,
            rf2.SYNONYM_TYPE_ID,
            rf2.FSN_TYPE_ID,
        ],
        "term": ["Glucose measurement (FSN)", "Glucose test", "Sodium (FSN)"],
        "caseSignificanceId": ["900000000000448009"] * 3,
    }
)

LANGUAGE = pl.DataFrame(
    {
        "id": ["300001", "300002"],
        "effectiveTime": ["20260101"] * 2,
        "active": ["1", "1"],
        "moduleId": ["11010000107"] * 2,
        "refsetId": ["900000000000509007"] * 2,
        "referencedComponentId": ["200001", "200003"],
        "acceptabilityId": [rf2.PREFERRED_ACCEPTABILITY_ID] * 2,
    }
)

RELATIONSHIP = pl.DataFrame(
    {
        "id": ["400001", "400002"],
        "effectiveTime": ["20260101"] * 2,
        "active": ["1", "1"],
        "moduleId": ["11010000107"] * 2,
        "sourceId": ["100001", "100002"],
        "destinationId": ["100002", "100003"],
        "relationshipGroup": ["0", "0"],
        "typeId": [rf2.IS_A_TYPE_ID, "246093002"],
        "characteristicTypeId": ["900000000000011006"] * 2,
        "modifierId": ["900000000000451002"] * 2,
    }
)


def test_active_rows_filters_inactive() -> None:
    assert rf2.active_rows(CONCEPT).height == 2


def test_isa_edges_only_isa_type() -> None:
    edges = rf2.isa_edges(RELATIONSHIP)
    assert edges.to_dicts() == [{"sourceId": "100001", "destinationId": "100002"}]


def test_preferred_terms_join() -> None:
    prefs = rf2.preferred_terms(DESCRIPTION, LANGUAGE)
    rows = {row["conceptId"]: row["term"] for row in prefs.iter_rows(named=True)}
    assert rows == {
        "100001": "Glucose measurement (FSN)",
        "100002": "Sodium (FSN)",
    }


def test_synonyms() -> None:
    syns = rf2.synonyms(DESCRIPTION)
    assert syns.to_dicts() == [
        {"conceptId": "100001", "term": "Glucose test", "lang": "en"}
    ]


def test_build_graph_emits_expected_triples() -> None:
    graph = loinc_snomed.build_graph(CONCEPT, DESCRIPTION, LANGUAGE, RELATIONSHIP)

    c1 = sct_iri("100001")
    # Concept typing (only active concepts).
    assert (c1, RDF.type, SKOS.Concept) in graph
    assert (sct_iri("100003"), RDF.type, SKOS.Concept) not in graph
    # Preferred label + synonym.
    assert (
        c1,
        SKOS.prefLabel,
        Literal("Glucose measurement (FSN)", lang="en"),
    ) in graph
    assert (c1, RDFS.label, Literal("Glucose measurement (FSN)", lang="en")) in graph
    assert (c1, SKOS.altLabel, Literal("Glucose test", lang="en")) in graph
    # Is-a edge -> subClassOf + broadMatch.
    parent: URIRef = sct_iri("100002")
    assert (c1, RDFS.subClassOf, parent) in graph
    assert (c1, SKOS.broadMatch, parent) in graph
