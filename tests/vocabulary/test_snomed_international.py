"""Tests for the SNOMED CT International graph builder."""

from __future__ import annotations

from pathlib import Path

from rdflib import Literal
from rdflib.namespace import RDF, RDFS, SKOS

from sssom_rosetta.vocabulary import rf2, snomed_international
from sssom_rosetta.vocabulary.namespaces import sct_iri

# Minimal International-style RF2: root 138875005 and Observable entity
# 363787002 as its child, plus one leaf under Observable entity.
_ROOT = "138875005"
_OBSERVABLE = "363787002"
_LEAF = "260245000"


def _write_tsv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(header)]
    lines += ["\t".join(row) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_release(root: Path, *, subdir: str = "Snapshot") -> Path:
    term = root / subdir / "Terminology"
    lang_dir = root / subdir / "Refset" / "Language"

    _write_tsv(
        term / "sct2_Concept_Snapshot_INT_20260101.txt",
        ["id", "effectiveTime", "active", "moduleId", "definitionStatusId"],
        [
            [_ROOT, "20260101", "1", "900000000000207008", "900000000000074008"],
            [_OBSERVABLE, "20260101", "1", "900000000000207008", "900000000000074008"],
            [_LEAF, "20260101", "1", "900000000000207008", "900000000000074008"],
        ],
    )
    _write_tsv(
        term / "sct2_Description_Snapshot-en_INT_20260101.txt",
        [
            "id", "effectiveTime", "active", "moduleId", "conceptId",
            "languageCode", "typeId", "term", "caseSignificanceId",
        ],
        [
            ["1", "20260101", "1", "900000000000207008", _ROOT, "en",
             rf2.FSN_TYPE_ID, "SNOMED CT Concept (SNOMED RT+CTV3)", "900000000000448009"],
            ["2", "20260101", "1", "900000000000207008", _OBSERVABLE, "en",
             rf2.FSN_TYPE_ID, "Observable entity (observable entity)", "900000000000448009"],
            ["3", "20260101", "1", "900000000000207008", _LEAF, "en",
             rf2.FSN_TYPE_ID, "Finding of color (observable entity)", "900000000000448009"],
        ],
    )
    _write_tsv(
        lang_dir / "der2_cRefset_LanguageSnapshot-en_INT_20260101.txt",
        [
            "id", "effectiveTime", "active", "moduleId", "refsetId",
            "referencedComponentId", "acceptabilityId",
        ],
        [
            ["a", "20260101", "1", "900000000000207008", "900000000000509007",
             "1", rf2.PREFERRED_ACCEPTABILITY_ID],
            ["b", "20260101", "1", "900000000000207008", "900000000000509007",
             "2", rf2.PREFERRED_ACCEPTABILITY_ID],
            ["c", "20260101", "1", "900000000000207008", "900000000000509007",
             "3", rf2.PREFERRED_ACCEPTABILITY_ID],
        ],
    )
    _write_tsv(
        term / "sct2_Relationship_Snapshot_INT_20260101.txt",
        [
            "id", "effectiveTime", "active", "moduleId", "sourceId",
            "destinationId", "relationshipGroup", "typeId",
            "characteristicTypeId", "modifierId",
        ],
        [
            ["r1", "20260101", "1", "900000000000207008", _OBSERVABLE, _ROOT,
             "0", rf2.IS_A_TYPE_ID, "900000000000011006", "900000000000451002"],
            ["r2", "20260101", "1", "900000000000207008", _LEAF, _OBSERVABLE,
             "0", rf2.IS_A_TYPE_ID, "900000000000011006", "900000000000451002"],
        ],
    )
    return root


def test_build_from_release_emits_hierarchy(tmp_path: Path) -> None:
    release = _make_release(tmp_path / "release")
    graph = snomed_international.build_from_release(release)

    root = sct_iri(_ROOT)
    observable = sct_iri(_OBSERVABLE)
    leaf = sct_iri(_LEAF)

    assert (observable, RDF.type, SKOS.Concept) in graph
    assert (
        observable,
        SKOS.prefLabel,
        Literal("Observable entity (observable entity)", lang="en"),
    ) in graph
    assert (observable, RDFS.subClassOf, root) in graph
    assert (observable, SKOS.broadMatch, root) in graph
    assert (leaf, RDFS.subClassOf, observable) in graph


def test_build_from_release_prefers_snapshot_over_full(tmp_path: Path) -> None:
    release = tmp_path / "release"
    _make_release(release, subdir="Snapshot")
    # A decoy Full/ copy with the same filenames must be ignored.
    _make_release(release, subdir="Full")

    graph = snomed_international.build_from_release(release)
    assert (sct_iri(_OBSERVABLE), RDFS.subClassOf, sct_iri(_ROOT)) in graph


def test_write_ttl_round_trips(tmp_path: Path) -> None:
    release = _make_release(tmp_path / "release")
    graph = snomed_international.build_from_release(release)
    out = snomed_international.write_ttl(
        graph, tmp_path / "out" / "snomed-international.ttl"
    )
    assert out.exists()
    from rdflib import Graph

    loaded = Graph()
    loaded.parse(str(out), format="turtle")
    assert (sct_iri(_OBSERVABLE), RDFS.subClassOf, sct_iri(_ROOT)) in loaded
