"""Tests for graph merging and the fetch/ingest helpers."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import polars as pl
import pytest
from rdflib import Graph, Literal
from rdflib.namespace import SKOS

from sssom_rosetta.vocabulary import loinc_snomed, merge, omop
from sssom_rosetta.vocabulary.fetch import (
    VocabularyIngestError,
    find_file,
    ingest_zip,
)
from sssom_rosetta.vocabulary.namespaces import omop_iri, sct_iri
from sssom_rosetta.vocabulary.sources import VocabularySource


def _tiny_loinc_snomed_graph() -> Graph:
    concept = pl.DataFrame({"id": ["44054006"], "active": ["1"]})
    description = pl.DataFrame(
        {
            "id": ["d1"],
            "active": ["1"],
            "conceptId": ["44054006"],
            "languageCode": ["en"],
            "typeId": [loinc_snomed.rf2.FSN_TYPE_ID],
            "term": ["Type 2 diabetes mellitus (FSN)"],
        }
    )
    language = pl.DataFrame(
        {
            "id": ["l1"],
            "active": ["1"],
            "referencedComponentId": ["d1"],
            "acceptabilityId": [loinc_snomed.rf2.PREFERRED_ACCEPTABILITY_ID],
        }
    )
    relationship = pl.DataFrame(
        {
            "id": ["r1"],
            "active": ["1"],
            "sourceId": ["44054006"],
            "destinationId": ["73211009"],
            "typeId": [loinc_snomed.rf2.IS_A_TYPE_ID],
        }
    )
    return loinc_snomed.build_graph(concept, description, language, relationship)


def _tiny_omop_graph() -> Graph:
    concepts = pl.DataFrame(
        {
            "concept_id": ["1002"],
            "concept_name": ["Type 2 diabetes mellitus"],
            "vocabulary_id": ["SNOMED"],
            "concept_code": ["44054006"],
        }
    )
    relationships = pl.DataFrame(
        {"concept_id_1": [], "concept_id_2": [], "relationship_id": []},
        schema={
            "concept_id_1": pl.Utf8,
            "concept_id_2": pl.Utf8,
            "relationship_id": pl.Utf8,
        },
    )
    return omop.build_graph(concepts, relationships)


def test_merge_connects_omop_to_snomed() -> None:
    merged = merge.merge_graphs(_tiny_loinc_snomed_graph(), _tiny_omop_graph())

    # The OMOP SNOMED concept exact-matches sct:44054006 ...
    assert (omop_iri("1002"), SKOS.exactMatch, sct_iri("44054006")) in merged
    # ... and that sct: node carries the LOINC-SNOMED subClassOf/broadMatch,
    # so OMOP concept_id 1002 is now connected to the ontology hierarchy.
    assert (sct_iri("44054006"), SKOS.broadMatch, sct_iri("73211009")) in merged


def test_merge_ttl_files_roundtrip(tmp_path: Path) -> None:
    ls_path = tmp_path / "loinc-snomed.ttl"
    omop_path = tmp_path / "omop.ttl"
    loinc_snomed.write_ttl(_tiny_loinc_snomed_graph(), ls_path)
    omop.write_ttl(_tiny_omop_graph(), omop_path)

    out = merge.merge_ttl_files([ls_path, omop_path], tmp_path / "merged.ttl")
    reloaded = Graph()
    reloaded.parse(str(out), format="turtle")
    assert (omop_iri("1002"), SKOS.exactMatch, sct_iri("44054006")) in reloaded


def _tiny_international_graph() -> Graph:
    """A backbone where 73211009 (the extension parent) is typed and labelled,
    and links up to root 138875005."""
    concept = pl.DataFrame({"id": ["73211009", "138875005"], "active": ["1", "1"]})
    description = pl.DataFrame(
        {
            "id": ["d1", "d2"],
            "active": ["1", "1"],
            "conceptId": ["73211009", "138875005"],
            "languageCode": ["en", "en"],
            "typeId": [loinc_snomed.rf2.FSN_TYPE_ID, loinc_snomed.rf2.FSN_TYPE_ID],
            "term": ["Diabetes mellitus (disorder)", "SNOMED CT Concept"],
        }
    )
    language = pl.DataFrame(
        {
            "id": ["l1", "l2"],
            "active": ["1", "1"],
            "referencedComponentId": ["d1", "d2"],
            "acceptabilityId": [loinc_snomed.rf2.PREFERRED_ACCEPTABILITY_ID] * 2,
        }
    )
    relationship = pl.DataFrame(
        {
            "id": ["r1"],
            "active": ["1"],
            "sourceId": ["73211009"],
            "destinationId": ["138875005"],
            "typeId": [loinc_snomed.rf2.IS_A_TYPE_ID],
        }
    )
    return loinc_snomed.build_graph(concept, description, language, relationship)


def test_merge_connects_extension_to_international_backbone() -> None:
    from rdflib.namespace import RDF, RDFS

    merged = merge.merge_graphs(
        _tiny_loinc_snomed_graph(), _tiny_international_graph()
    )

    parent = sct_iri("73211009")
    root = sct_iri("138875005")
    # In the extension graph alone, 73211009 was a bare object. After merge it
    # is a typed, labelled Concept that reaches the root.
    assert (parent, RDF.type, SKOS.Concept) in merged
    assert (
        parent,
        SKOS.prefLabel,
        Literal("Diabetes mellitus (disorder)", lang="en"),
    ) in merged
    assert (parent, RDFS.subClassOf, root) in merged
    # ... and the extension child reaches the root transitively.
    assert (sct_iri("44054006"), RDFS.subClassOf, parent) in merged


# --- fetch/ingest ---------------------------------------------------------


def _make_zip(tmp_path: Path, files: dict[str, str]) -> Path:
    zip_path = tmp_path / "release.zip"
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    zip_path.write_bytes(buffer.getvalue())
    return zip_path


def _source() -> VocabularySource:
    return VocabularySource(
        name="test-vocab",
        version="1.0",
        kind="rf2",
        description="test",
        download_page="https://example.org",
    )


def test_ingest_zip_extracts(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"Snapshot/Terminology/foo.txt": "a\tb\n1\t2\n"})
    cache = tmp_path / "cache"
    target = ingest_zip(_source(), zip_path, cache_dir=cache)
    assert (target / "Snapshot" / "Terminology" / "foo.txt").exists()


def test_ingest_zip_idempotent(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"a.txt": "x"})
    cache = tmp_path / "cache"
    ingest_zip(_source(), zip_path, cache_dir=cache)
    # Deleting the ZIP and re-calling should reuse the cache, not error.
    zip_path.unlink()
    target = ingest_zip(_source(), zip_path, cache_dir=cache)
    assert (target / "a.txt").exists()


def test_ingest_zip_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(VocabularyIngestError):
        ingest_zip(_source(), tmp_path / "nope.zip", cache_dir=tmp_path / "c")


def test_find_file_unique(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    target = tmp_path / "sub" / "CONCEPT.csv"
    target.write_text("x")
    assert find_file(tmp_path, prefix="CONCEPT.csv", suffix="CONCEPT.csv") == target


def test_find_file_ambiguous_raises(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    with pytest.raises(VocabularyIngestError):
        find_file(tmp_path, suffix=".txt")
