r"""Build a SKOS Turtle graph from an OHDSI/OMOP Athena vocabulary bundle.

Athena files are tab-delimited despite their ``.csv`` extension, so they are
read with the same polars settings as RF2 (``separator="\\t",
quote_char=None``): OMOP ``concept_name`` values contain unescaped quotes. The
large ``CONCEPT.csv`` / ``CONCEPT_RELATIONSHIP.csv`` files are read lazily and
filtered to :data:`~sssom_rosetta.vocabulary.namespaces.TARGET_VOCABULARIES`
early.

Each OMOP concept becomes a hub node ``omopconcept:<concept_id>``:

* ``skos:prefLabel`` = ``concept_name``; ``skos:notation`` = ``concept_code``,
* linked to its native source-vocabulary IRI (SNOMED SCTID, LOINC Num, RxNorm
  RXCUI, ICD10/ICD10CM code) via ``skos:exactMatch`` when one exists.

Relationships (current rows only) map to SKOS:

* ``Maps to`` → ``skos:exactMatch`` (source → standard concept),
* ``Is a`` → ``skos:broadMatch`` (child → parent),
* ``Subsumes`` → ``skos:narrowMatch``.

The graph is assembled with **maplib**, not rdflib: concept nodes are built
by mapping the filtered ``concepts`` DataFrame through the
:data:`~sssom_rosetta.vocabulary.templates.CONCEPT_TEMPLATE` OTTR template,
and relationship edges are built with ``Model.map_triples`` over a
subject/predicate/object frame (the ``relationship_id`` -> SKOS predicate
lookup is a plain column mapping, not a template, since it doesn't need
OTTR's optional-value semantics).

See :doc:`/vocabularies/index` for the rationale behind choosing maplib/OTTR
over a hand-written rdflib triple-add loop.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl
from maplib import Model

from sssom_rosetta.vocabulary.fetch import find_file
from sssom_rosetta.vocabulary.namespaces import (
    OMOP_CONCEPT,
    PREFIX_MAP,
    TARGET_VOCABULARIES,
    source_concept_iri,
)
from sssom_rosetta.vocabulary.templates import (
    CONCEPT_TEMPLATE,
    CONCEPT_TEMPLATE_IRI,
    language_tagged_column,
)

if TYPE_CHECKING:
    from pathlib import Path

_SKOS = "http://www.w3.org/2004/02/skos/core#"

#: OMOP relationship_id -> SKOS predicate IRI. Others are ignored for this graph.
_RELATIONSHIP_PREDICATES = {
    "Maps to": f"{_SKOS}exactMatch",
    "Is a": f"{_SKOS}broadMatch",
    "Subsumes": f"{_SKOS}narrowMatch",
}

#: Prefixes bound on the produced model, purely for readable Turtle output.
_PREFIXES = {prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()} | {"skos": _SKOS}


def _omop_iri_column(concept_id_column: str) -> pl.Expr:
    """Vectorised ``omopconcept:<id>`` IRI expression for a concept-id column.

    OMOP ``concept_id`` values are plain digit strings, so (unlike
    :func:`~sssom_rosetta.vocabulary.namespaces.source_concept_iri`) no
    percent-encoding is needed and this can be a fast Polars string
    concatenation instead of a per-row Python call.
    """
    return pl.concat_str([pl.lit(str(OMOP_CONCEPT)), pl.col(concept_id_column)])


def _scan_athena(path: Path) -> pl.LazyFrame:
    """Lazily scan an Athena tab-delimited CSV as all-``Utf8`` columns."""
    return pl.scan_csv(path, separator="\t", quote_char=None, infer_schema_length=0)


def load_target_concepts(concept_csv: Path) -> pl.DataFrame:
    """Lazily read ``CONCEPT.csv`` and keep only target-vocabulary rows."""
    return (
        _scan_athena(concept_csv)
        .filter(pl.col("vocabulary_id").is_in(list(TARGET_VOCABULARIES)))
        .select(
            "concept_id",
            "concept_name",
            "vocabulary_id",
            "concept_code",
        )
        .collect()
    )


def load_relationships(relationship_csv: Path, concept_ids: pl.Series) -> pl.DataFrame:
    """Read ``CONCEPT_RELATIONSHIP.csv``, keep current rows within target set.

    Only relationships whose *both* endpoints are target-vocabulary concepts
    and whose ``invalid_reason`` is empty are retained, and only the
    relationship types in :data:`_RELATIONSHIP_PREDICATES`.
    """
    wanted = concept_ids.implode()
    return (
        _scan_athena(relationship_csv)
        .filter(
            (pl.col("invalid_reason").is_null() | (pl.col("invalid_reason") == ""))
            & pl.col("relationship_id").is_in(list(_RELATIONSHIP_PREDICATES))
            & pl.col("concept_id_1").is_in(wanted)
            & pl.col("concept_id_2").is_in(wanted)
        )
        .select("concept_id_1", "concept_id_2", "relationship_id")
        .collect()
    )


def _concept_rows(concepts: pl.DataFrame) -> pl.DataFrame:
    """Prepare the concept frame for :data:`CONCEPT_TEMPLATE`.

    Blank-vs-null handling mirrors the previous rdflib implementation's
    ``if row["concept_name"]:`` / ``if row["concept_code"]:`` guards: empty
    strings are nulled out here so the OTTR template's optional parameters
    drop the corresponding triple, rather than emitting e.g.
    ``skos:notation ""``.
    """

    def non_blank(column: str) -> pl.Expr:
        return pl.when(pl.col(column).is_not_null() & (pl.col(column) != "")).then(pl.col(column)).otherwise(None)

    concept_name = concepts.select(non_blank("concept_name")).to_series()
    rows = concepts.with_columns(
        subject=_omop_iri_column("concept_id"),
        label=language_tagged_column(concept_name),
        code=non_blank("concept_code"),
    )
    # source_concept_iri needs per-row vocabulary lookup + percent-encoding
    # (see namespaces.py), which isn't a plain column expression, so this one
    # column stays a Python-level pass rather than a Polars expression.
    source_iris = [
        str(iri) if (iri := source_concept_iri(vocabulary_id, concept_code)) is not None else None
        for vocabulary_id, concept_code in zip(concepts["vocabulary_id"], concepts["concept_code"], strict=True)
    ]
    return rows.with_columns(source=pl.Series(source_iris, dtype=pl.Utf8))


def _relationship_rows(relationships: pl.DataFrame) -> pl.DataFrame:
    """Prepare the relationship frame as a plain subject/predicate/object table."""
    return relationships.with_columns(
        subject=_omop_iri_column("concept_id_1"),
        object=_omop_iri_column("concept_id_2"),
        predicate=pl.col("relationship_id").replace_strict(_RELATIONSHIP_PREDICATES),
    ).select("subject", "predicate", "object")


def build_graph(concepts: pl.DataFrame, relationships: pl.DataFrame) -> Model:
    """Assemble the OMOP SKOS graph from filtered concept/relationship frames.

    Concept nodes are mapped through the declarative :data:`CONCEPT_TEMPLATE`
    OTTR template; relationship edges are mapped as plain triples (see the
    module docstring). Returns a maplib ``Model`` rather than an
    ``rdflib.Graph``.
    """
    model = Model()
    model.add_prefixes(_PREFIXES)
    model.add_template(CONCEPT_TEMPLATE)

    concept_rows = _concept_rows(concepts)
    model.map(CONCEPT_TEMPLATE_IRI, concept_rows.select("subject", "label", "code", "source"))

    if relationships.height:
        model.map_triples(_relationship_rows(relationships))

    return model


def build_from_release(release_dir: Path) -> Model:
    """Locate Athena CSVs under ``release_dir`` and build the OMOP graph."""
    # CONCEPT.csv and CONCEPT_RELATIONSHIP.csv both start with "CONCEPT", so
    # match by exact filename rather than a shared prefix.
    concept_csv = _exact(release_dir, "CONCEPT.csv")
    relationship_csv = _exact(release_dir, "CONCEPT_RELATIONSHIP.csv")

    concepts = load_target_concepts(concept_csv)
    relationships = load_relationships(relationship_csv, concepts["concept_id"])
    return build_graph(concepts, relationships)


def _exact(root: Path, filename: str) -> Path:
    """Find a file named exactly ``filename`` anywhere under ``root``."""
    return find_file(root, prefix=filename, suffix=filename)


def write_ttl(model: Model, output_path: Path) -> Path:
    """Serialize ``model`` to Turtle at ``output_path``, creating parents."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(output_path), format="turtle")
    return output_path
