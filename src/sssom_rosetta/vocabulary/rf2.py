"""Polars readers for SNOMED CT RF2 tab-separated release files.

All RF2 files are UTF-8, tab-separated, with a header row and one
component-version per row. Two hard rules when reading them with polars:

* ``separator="\\t", quote_char=None`` — RF2 terms contain unescaped ``"`` and
  ``'`` characters that break naive CSV quote handling.
* ``infer_schema_length=0`` — read every column as ``Utf8``; SCTIDs are up to
  18-digit integers we must keep as strings to avoid overflow/precision loss.

Callers should prefer the ``Snapshot`` folder (latest active state per
component); helpers here still filter ``active == "1"`` defensively.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

# Well-known SCTIDs used to classify RF2 rows.
IS_A_TYPE_ID = "116680003"
FSN_TYPE_ID = "900000000000003001"
SYNONYM_TYPE_ID = "900000000000013009"
PREFERRED_ACCEPTABILITY_ID = "900000000000548007"


def read_rf2(path: Path) -> pl.DataFrame:
    """Read an RF2 tab-separated file into an all-``Utf8`` DataFrame."""
    return pl.read_csv(
        path,
        separator="\t",
        quote_char=None,
        infer_schema_length=0,
    )


def active_rows(frame: pl.DataFrame) -> pl.DataFrame:
    """Return only the rows whose ``active`` flag is ``"1"``."""
    return frame.filter(pl.col("active") == "1")


def isa_edges(relationship: pl.DataFrame) -> pl.DataFrame:
    """Return active ``Is a`` edges as ``sourceId`` / ``destinationId`` pairs.

    ``sourceId`` is the more specific (child) concept; ``destinationId`` the
    broader (parent), matching ``skos:broadMatch`` direction.
    """
    return (
        active_rows(relationship)
        .filter(pl.col("typeId") == IS_A_TYPE_ID)
        .select("sourceId", "destinationId")
    )


def preferred_terms(description: pl.DataFrame, language: pl.DataFrame) -> pl.DataFrame:
    """Return the preferred term per concept: ``conceptId``, ``term``, ``lang``.

    A description is *preferred* when it appears in the language refset with
    ``acceptabilityId`` = preferred. Joins Description (active) to the active
    language refset on the description ``id`` = ``referencedComponentId``.
    """
    active_desc = active_rows(description).select(
        "id", "conceptId", "term", "languageCode"
    )
    preferred = (
        active_rows(language)
        .filter(pl.col("acceptabilityId") == PREFERRED_ACCEPTABILITY_ID)
        .select("referencedComponentId")
        .unique()
    )
    joined = active_desc.join(
        preferred, left_on="id", right_on="referencedComponentId", how="inner"
    )
    return joined.select("conceptId", "term", pl.col("languageCode").alias("lang"))


def synonyms(description: pl.DataFrame) -> pl.DataFrame:
    """Return active synonym descriptions: ``conceptId``, ``term``, ``lang``."""
    return (
        active_rows(description)
        .filter(pl.col("typeId") == SYNONYM_TYPE_ID)
        .select("conceptId", "term", pl.col("languageCode").alias("lang"))
    )
