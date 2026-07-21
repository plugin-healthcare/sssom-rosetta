"""Build a SKOS Turtle graph from an OHDSI/OMOP Athena vocabulary bundle.

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
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from rdflib import Graph, Literal
from rdflib.namespace import RDF, SKOS

from sssom_rosetta.vocabulary.fetch import find_file
from sssom_rosetta.vocabulary.namespaces import (
    PREFIX_MAP,
    TARGET_VOCABULARIES,
    omop_iri,
    source_concept_iri,
)

#: OMOP relationship_id -> SKOS predicate. Others are ignored for this graph.
_RELATIONSHIP_PREDICATES = {
    "Maps to": SKOS.exactMatch,
    "Is a": SKOS.broadMatch,
    "Subsumes": SKOS.narrowMatch,
}


def _bind_prefixes(graph: Graph) -> None:
    for prefix, namespace in PREFIX_MAP.items():
        graph.bind(prefix, namespace)
    graph.bind("skos", SKOS)


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


def build_graph(concepts: pl.DataFrame, relationships: pl.DataFrame) -> Graph:
    """Assemble the OMOP SKOS graph from filtered concept/relationship frames."""
    graph = Graph()
    _bind_prefixes(graph)

    for row in concepts.iter_rows(named=True):
        subject = omop_iri(row["concept_id"])
        graph.add((subject, RDF.type, SKOS.Concept))
        if row["concept_name"]:
            graph.add(
                (subject, SKOS.prefLabel, Literal(row["concept_name"], lang="en"))
            )
        if row["concept_code"]:
            graph.add((subject, SKOS.notation, Literal(row["concept_code"])))
        source = source_concept_iri(row["vocabulary_id"], row["concept_code"])
        if source is not None:
            graph.add((subject, SKOS.exactMatch, source))

    for row in relationships.iter_rows(named=True):
        predicate = _RELATIONSHIP_PREDICATES[row["relationship_id"]]
        graph.add(
            (
                omop_iri(row["concept_id_1"]),
                predicate,
                omop_iri(row["concept_id_2"]),
            )
        )

    return graph


def build_from_release(release_dir: Path) -> Graph:
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


def write_ttl(graph: Graph, output_path: Path) -> Path:
    """Serialize ``graph`` to Turtle at ``output_path``, creating parents."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(output_path), format="turtle")
    return output_path
