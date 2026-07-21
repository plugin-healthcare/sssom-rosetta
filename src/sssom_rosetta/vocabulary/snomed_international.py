"""Build a standalone SKOS/RDFS Turtle graph from the SNOMED CT International Edition.

The International Edition (core module ``900000000000207008``) supplies the
top-level concept hierarchy — Body structure, Clinical finding, Observable
entity, Substance, … up to the root ``138875005`` — that the LOINC-SNOMED
extension depends on but does **not** itself contain. Rather than embedding those
concepts into ``loinc-snomed.ttl``, we build them into their own
``snomed-international.ttl`` so each release stays a separate, independently
versioned artifact. They mint identical ``sct:<id>`` IRIs (see
:mod:`~sssom_rosetta.vocabulary.namespaces`), so a later ``merge`` connects the
extension's concepts to this backbone automatically.

The graph shape is identical to the extension's, so this module delegates to
:func:`sssom_rosetta.vocabulary.loinc_snomed.build_graph`; only the RF2 file
location differs. International RF2 packages ship ``Full/``, ``Snapshot/`` and
``Delta/`` copies plus multiple language files, so we constrain lookups to the
``Snapshot/`` English (``-en``) files (see :func:`find_file`'s ``contains``).

Full OWL-DL logical definitions are intentionally not materialised here — see
``.agents/plan/2026-07-21-owl-dl-classification-deferral-note.md``.
"""

from __future__ import annotations

from pathlib import Path

from rdflib import Graph

from sssom_rosetta.vocabulary import loinc_snomed, rf2
from sssom_rosetta.vocabulary.fetch import find_file

_SNAPSHOT = "/Snapshot/"


def build_from_release(release_dir: Path) -> Graph:
    """Locate International RF2 Snapshot files under ``release_dir`` and build.

    Constrains every lookup to the ``Snapshot/`` tree (International packages
    also ship ``Full/`` and ``Delta/`` copies) and to the English description
    and language refset files.
    """
    concept = rf2.read_rf2(
        find_file(
            release_dir,
            prefix="sct2_Concept_Snapshot",
            suffix=".txt",
            contains=_SNAPSHOT,
        )
    )
    description = rf2.read_rf2(
        find_file(
            release_dir,
            prefix="sct2_Description_Snapshot-en",
            suffix=".txt",
            contains=_SNAPSHOT,
        )
    )
    language = rf2.read_rf2(
        find_file(
            release_dir,
            prefix="der2_cRefset_LanguageSnapshot-en",
            suffix=".txt",
            contains=_SNAPSHOT,
        )
    )
    relationship = rf2.read_rf2(
        find_file(
            release_dir,
            prefix="sct2_Relationship_Snapshot",
            suffix=".txt",
            contains=_SNAPSHOT,
        )
    )
    return loinc_snomed.build_graph(concept, description, language, relationship)


def write_ttl(graph: Graph, output_path: Path) -> Path:
    """Serialize ``graph`` to Turtle at ``output_path``, creating parents."""
    return loinc_snomed.write_ttl(graph, output_path)
