"""Tests for the OMOP/Athena graph builder and cross-linking.

``omop.build_graph`` returns a ``maplib.Model`` (see
``.agents/plan/2026-07-30-implementation-maplib.md``), not an
``rdflib.Graph``, so membership is checked with SPARQL SELECT queries
instead of ``(s, p, o) in graph`` -- :func:`objects` below runs
``SELECT ?o WHERE { <subject> <predicate> ?o }`` and returns the bound
values as plain Python strings (IRIs unwrapped from their ``<...>`` form).
Literals come back in maplib's own query-result rendering: a
language-tagged literal renders as ``"value"@lang`` (quoted, with the tag),
while a plain/untyped literal (e.g. ``xsd:string`` with no language tag)
renders as the bare value with no surrounding quotes.
"""

from __future__ import annotations

import polars as pl

from sssom_rosetta.vocabulary import omop
from sssom_rosetta.vocabulary.namespaces import omop_iri, sct_iri, source_concept_iri

CONCEPTS = pl.DataFrame(
    {
        "concept_id": ["1001", "1002", "1003", "1004"],
        "concept_name": [
            "Glucose [Mass/volume]",
            "Type 2 diabetes mellitus",
            'Aspirin 81 MG "low dose"',
            "RxNorm-ext product",
        ],
        "vocabulary_id": ["LOINC", "SNOMED", "ICD10CM", "RxNorm Extension"],
        "concept_code": ["2345-7", "44054006", "E11.9", ""],
    }
)

RELATIONSHIPS = pl.DataFrame(
    {
        "concept_id_1": ["1003", "1002"],
        "concept_id_2": ["1002", "1001"],
        "relationship_id": ["Maps to", "Is a"],
    }
)


def objects(model, subject: str, predicate: str) -> list[str]:
    """Return the bound ``?o`` values for ``<subject> <predicate> ?o``.

    Language-tagged literals come back quoted, e.g. ``'"value"@en'``; plain
    literals come back bare, e.g. ``"value"`` with no quotes -- see the
    module docstring above for why these two forms differ.
    """
    query = f"SELECT ?o WHERE {{ <{subject}> <{predicate}> ?o }}"
    return model.query(query)["o"].to_list()


def iris(model, subject: str, predicate: str) -> list[str]:
    """Like :func:`objects`, but strips the ``<...>`` wrapper from IRI results."""
    return [value.removeprefix("<").removesuffix(">") for value in objects(model, subject, predicate)]


def test_source_concept_iri_returns_none_for_rxnorm_extension() -> None:
    assert source_concept_iri("RxNorm Extension", "") is None
    assert source_concept_iri("SNOMED", "44054006") == sct_iri("44054006")


def test_source_concept_iri_percent_encodes_illegal_chars() -> None:
    # LOINC class codes can contain spaces/ampersands that are illegal in an
    # IRI path; they must be percent-encoded so rdflib can serialize them.
    iri = source_concept_iri("LOINC", "H&P.SURG PROC")
    assert iri is not None
    assert str(iri) == "https://loinc.org/H%26P.SURG%20PROC"
    # Plain codes with unreserved chars are left intact.
    assert str(source_concept_iri("LOINC", "2345-7")) == "https://loinc.org/2345-7"


def test_build_graph_concept_nodes_and_crosslinks() -> None:
    model = omop.build_graph(CONCEPTS, RELATIONSHIPS)

    loinc_node = str(omop_iri("1001"))
    rdf_type = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
    skos_concept = "http://www.w3.org/2004/02/skos/core#Concept"
    pref_label = "http://www.w3.org/2004/02/skos/core#prefLabel"
    notation = "http://www.w3.org/2004/02/skos/core#notation"
    exact_match = "http://www.w3.org/2004/02/skos/core#exactMatch"

    assert iris(model, loinc_node, rdf_type) == [skos_concept]
    assert objects(model, loinc_node, pref_label) == ['"Glucose [Mass/volume]"@en']
    assert objects(model, loinc_node, notation) == ['"2345-7"']
    # LOINC concept cross-linked to its native source IRI.
    assert str(source_concept_iri("LOINC", "2345-7")) in iris(model, loinc_node, exact_match)

    # SNOMED concept cross-linked to sct: IRI (the merge bridge).
    assert str(sct_iri("44054006")) in iris(model, str(omop_iri("1002")), exact_match)

    # RxNorm Extension: no native code, so no exactMatch to a source IRI.
    ext_node = str(omop_iri("1004"))
    assert iris(model, ext_node, rdf_type) == [skos_concept]
    assert objects(model, ext_node, exact_match) == []
    assert objects(model, ext_node, notation) == []


def test_build_graph_relationship_predicates() -> None:
    model = omop.build_graph(CONCEPTS, RELATIONSHIPS)
    exact_match = "http://www.w3.org/2004/02/skos/core#exactMatch"
    broad_match = "http://www.w3.org/2004/02/skos/core#broadMatch"

    # 'Maps to' -> exactMatch between OMOP nodes.
    assert str(omop_iri("1002")) in iris(model, str(omop_iri("1003")), exact_match)
    # 'Is a' -> broadMatch (child -> parent).
    assert iris(model, str(omop_iri("1002")), broad_match) == [str(omop_iri("1001"))]
