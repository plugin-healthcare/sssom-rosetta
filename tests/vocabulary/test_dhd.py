"""Tests for the DHD Diagnose-/Verrichtingenthesaurus graph builder.

Mirrors ``tests/vocabulary/test_omop.py``'s ``objects``/``iris`` helpers,
since ``dhd.build_graph`` also returns a ``maplib.Model`` rather than an
``rdflib.Graph`` (see the module docstring in ``dhd.py``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl
import pytest

from sssom_rosetta.vocabulary import dhd
from sssom_rosetta.vocabulary.namespaces import ICD10 as ICD10_NS
from sssom_rosetta.vocabulary.namespaces import dbc_iri, dhd_concept_iri, sct_iri

if TYPE_CHECKING:
    from pathlib import Path

AS_OF = "20250101"

RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
SKOS_CONCEPT = "http://www.w3.org/2004/02/skos/core#Concept"
EXACT_MATCH = "http://www.w3.org/2004/02/skos/core#exactMatch"
CLOSE_MATCH = "http://www.w3.org/2004/02/skos/core#closeMatch"


def objects(model, subject: str, predicate: str) -> list[str]:
    """Return the bound ``?o`` values for ``<subject> <predicate> ?o``."""
    query = f"SELECT ?o WHERE {{ <{subject}> <{predicate}> ?o }}"
    return model.query(query)["o"].to_list()


def iris(model, subject: str, predicate: str) -> list[str]:
    """Like :func:`objects`, but strips the ``<...>`` wrapper from IRI results."""
    return [value.removeprefix("<").removesuffix(">") for value in objects(model, subject, predicate)]


# --- loaders -----------------------------------------------------------------


def _write_csv(path: Path, rows: list[str], header: str) -> Path:
    path.write_text(header + "\n" + "\n".join(rows) + "\n")
    return path


def test_load_concepts_filters_to_active(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "ThesaurusConcept.csv",
        rows=[
            '"0000000001","Diagnose","false","false","niet bepaald","false","20000101","20200101","20991231",""',
            # Einddatum before AS_OF -> not active.
            '"0000000002","Diagnose","false","false","niet bepaald","false","20000101","20100101","20100601",""',
        ],
        header='"ConceptID","TypeConcept","Complicatie","GebruiktImplantaat","Lateraliteit","Gradatie",'
        '"Begindatum","Mutatiedatum","Einddatum","LOINCCode"',
    )
    concepts = dhd.load_concepts(csv_path, AS_OF)
    assert concepts["ConceptID"].to_list() == ["0000000001"]


def test_load_snomed_terms_dedupes_concurrent_fsn_rows(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "ThesaurusTerm.csv",
        rows=[
            # English + Dutch FSN, both active, same SnomedID -> dedupe to one row.
            '"0000000001","1","cyst (disorder)","20000101","20020131","20991231","en-GB","FSN","39462005"',
            '"0000000001","2","cyste (aandoening)","20000101","20211201","20991231","nl-NL","FSN","39462005"',
            # Non-FSN term with a SnomedID is not a concept-level SNOMED mapping.
            '"0000000001","3","synoniem","20000101","20211201","20991231","nl-NL","synoniem","99999999"',
            # FSN with a blank SnomedID -> excluded.
            '"0000000002","4","other (disorder)","20000101","20211201","20991231","en-GB","FSN",""',
        ],
        header='"ConceptID","TermID","Omschrijving","Begindatum","Mutatiedatum","Einddatum","TaalCode",'
        '"TypeTerm","SnomedID"',
    )
    terms = dhd.load_snomed_terms(csv_path, AS_OF)
    assert terms.rows() == [("0000000001", "39462005")]


def test_load_icd10_excludes_blank_and_inactive(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "AfleidingICD10.csv",
        rows=[
            '"0000000001","G52.3","1","","","20000101","20151031","20991231","20150101","20991231"',
            # Inactive (Einddatum before AS_OF).
            '"0000000001","G52.4","1","","","20000101","20141031","20141101","20140101","20141101"',
            # Blank ICD10.
            '"0000000002","","1","","","20000101","20151031","20991231","20150101","20991231"',
        ],
        header='"ConceptID","ICD10","Volgnummer","Advies","Logica","Begindatum","Mutatiedatum","Einddatum",'
        '"AutorisatieBegindatum","AutorisatieEinddatum"',
    )
    icd10 = dhd.load_icd10(csv_path, AS_OF)
    assert icd10.rows() == [("0000000001", "G52.3")]


def test_load_dbc_excludes_blank_dbc_id(tmp_path: Path) -> None:
    csv_path = _write_csv(
        tmp_path / "AfleidingDBC.csv",
        rows=[
            '"0000000001","0389","130","0389","1","","","20000101","20231117","20991231","20150501","20991231"',
            # Blank DBC_ID (specialism row with no DBC).
            '"0000000002","0389","","0389","1","","","20000101","20141120","20991231","",""',
        ],
        header='"ConceptID","SpecialismeCode","DBC_ID","Registrerend_SpecialismeCode","Volgnummer","Advies",'
        '"Logica","Begindatum","Mutatiedatum","Einddatum","AutorisatieBegindatum","AutorisatieEinddatum"',
    )
    dbc = dhd.load_dbc(csv_path, AS_OF)
    assert dbc.rows() == [("0000000001", "130")]


# --- build_graph ---------------------------------------------------------------


CONCEPTS = pl.DataFrame({"ConceptID": ["1", "2"], "TypeConcept": ["Diagnose", "Diagnose"]})
SNOMED_TERMS = pl.DataFrame({"ConceptID": ["1"], "SnomedID": ["44054006"]})
ICD10_ROWS = pl.DataFrame({"ConceptID": ["1"], "ICD10": ["G52.3"]})
DBC_ROWS = pl.DataFrame({"ConceptID": ["1"], "DBC_ID": ["130"]})


def test_build_graph_dt_concept_and_crosslinks() -> None:
    model = dhd.build_graph("dt", CONCEPTS, SNOMED_TERMS, ICD10_ROWS, DBC_ROWS)

    node1 = str(dhd_concept_iri("dt", "1"))
    node2 = str(dhd_concept_iri("dt", "2"))

    assert iris(model, node1, RDF_TYPE) == [SKOS_CONCEPT]
    assert iris(model, node1, EXACT_MATCH) == [str(sct_iri("44054006"))]
    assert sorted(iris(model, node1, CLOSE_MATCH)) == sorted([str(ICD10_NS["G52.3"]), str(dbc_iri("130"))])

    # Concept with no SNOMED/ICD10/DBC match: typed, but no exactMatch/closeMatch triples.
    assert iris(model, node2, RDF_TYPE) == [SKOS_CONCEPT]
    assert objects(model, node2, EXACT_MATCH) == []
    assert objects(model, node2, CLOSE_MATCH) == []


def test_build_graph_vt_is_snomed_only() -> None:
    model = dhd.build_graph("vt", CONCEPTS, SNOMED_TERMS)

    node1 = str(dhd_concept_iri("vt", "1"))
    assert iris(model, node1, RDF_TYPE) == [SKOS_CONCEPT]
    assert iris(model, node1, EXACT_MATCH) == [str(sct_iri("44054006"))]
    assert objects(model, node1, CLOSE_MATCH) == []


def test_dt_and_vt_use_separate_namespaces() -> None:
    assert str(dhd_concept_iri("dt", "1")) != str(dhd_concept_iri("vt", "1"))


# --- build_from_release --------------------------------------------------------


def _write_release(root: Path) -> None:
    dt_dir = root / "thesauri" / "DT" / f"20250819_142606_Diagnosethesaurus_3.44_{dhd.FORMAT_VERSION}"
    vt_dir = root / "thesauri" / "VT" / f"20250813_112107_Verrichtingenthesaurus_2.43_{dhd.FORMAT_VERSION}"
    dt_dir.mkdir(parents=True)
    vt_dir.mkdir(parents=True)

    concept_header = (
        '"ConceptID","TypeConcept","Complicatie","GebruiktImplantaat","Lateraliteit","Gradatie",'
        '"Begindatum","Mutatiedatum","Einddatum","LOINCCode"'
    )
    term_header = (
        '"ConceptID","TermID","Omschrijving","Begindatum","Mutatiedatum","Einddatum","TaalCode","TypeTerm","SnomedID"'
    )
    icd10_header = (
        '"ConceptID","ICD10","Volgnummer","Advies","Logica","Begindatum","Mutatiedatum","Einddatum",'
        '"AutorisatieBegindatum","AutorisatieEinddatum"'
    )
    dbc_header = (
        '"ConceptID","SpecialismeCode","DBC_ID","Registrerend_SpecialismeCode","Volgnummer","Advies",'
        '"Logica","Begindatum","Mutatiedatum","Einddatum","AutorisatieBegindatum","AutorisatieEinddatum"'
    )

    for release_dir, infix in ((dt_dir, ""), (vt_dir, "_VT")):
        prefix = f"20250101_000000_{dhd.FORMAT_VERSION}{infix}"
        _write_csv(
            release_dir / f"{prefix}_ThesaurusConcept.csv",
            ['"0000000001","Diagnose","false","false","niet bepaald","false","20000101","20200101","20991231",""'],
            concept_header,
        )
        _write_csv(
            release_dir / f"{prefix}_ThesaurusTerm.csv",
            ['"0000000001","1","cyst (disorder)","20000101","20020131","20991231","en-GB","FSN","39462005"'],
            term_header,
        )

    _write_csv(
        dt_dir / f"20250101_000000_{dhd.FORMAT_VERSION}_AfleidingICD10.csv",
        ['"0000000001","G52.3","1","","","20000101","20151031","20991231","20150101","20991231"'],
        icd10_header,
    )
    _write_csv(
        dt_dir / f"20250101_000000_{dhd.FORMAT_VERSION}_AfleidingDBC.csv",
        ['"0000000001","0389","130","0389","1","","","20000101","20231117","20991231","20150501","20991231"'],
        dbc_header,
    )


def test_build_from_release_dt_and_vt(tmp_path: Path) -> None:
    _write_release(tmp_path)

    dt_model = dhd.build_from_release(tmp_path, "dt", as_of=AS_OF)
    node = str(dhd_concept_iri("dt", "0000000001"))
    assert iris(dt_model, node, EXACT_MATCH) == [str(sct_iri("39462005"))]
    assert sorted(iris(dt_model, node, CLOSE_MATCH)) == sorted([str(ICD10_NS["G52.3"]), str(dbc_iri("130"))])

    vt_model = dhd.build_from_release(tmp_path, "vt", as_of=AS_OF)
    vt_node = str(dhd_concept_iri("vt", "0000000001"))
    assert iris(vt_model, vt_node, EXACT_MATCH) == [str(sct_iri("39462005"))]
    assert objects(vt_model, vt_node, CLOSE_MATCH) == []


def test_find_release_dir_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(dhd.DhdFormatVersionError):
        dhd.build_from_release(tmp_path, "dt", as_of=AS_OF)


def test_find_release_dir_ambiguous_raises(tmp_path: Path) -> None:
    _write_release(tmp_path)
    # A second, stray DT release directory makes the lookup ambiguous.
    (tmp_path / "thesauri" / "DT" / f"stray_{dhd.FORMAT_VERSION}").mkdir(parents=True)
    with pytest.raises(dhd.DhdFormatVersionError):
        dhd.build_from_release(tmp_path, "dt", as_of=AS_OF)
