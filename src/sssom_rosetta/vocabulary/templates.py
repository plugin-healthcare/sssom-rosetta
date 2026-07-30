"""OTTR (stOTTR) templates used to map OMOP tabular rows to SKOS triples.

Templates are the declarative counterpart to the ``if row[...]:`` branches a
hand-written triple-add loop would need: a leading ``?`` on a template
parameter (e.g. ``? ?label``) marks it *optional*, and maplib silently omits
any triple that uses an unbound optional variable for a given row, instead of
requiring Python-side conditionals. See
``.agents/plan/2026-07-30-implementation-maplib.md`` for the rationale.
"""

from __future__ import annotations

import polars as pl

#: The struct field name maplib recognises as the string value of an
#: ``rdf:langString`` literal, paired with an ``"l"`` field for the language
#: tag. Building a two-field ``Struct`` column with these exact field names
#: is how a Polars column becomes a language-tagged literal for ``Model.map``.
LANG_STRING_FIELD = "<http://www.w3.org/1999/02/22-rdf-syntax-ns#langString>"

#: IRI of the concept template below, passed to ``Model.map``.
CONCEPT_TEMPLATE_IRI = "http://www.w3.org/2004/02/skos/core#OmopConceptTemplate"

#: Maps one OMOP ``CONCEPT.csv`` row to a SKOS concept node:
#:
#: * ``subject`` (required) -- the OMOP concept IRI.
#: * ``label`` (optional) -- ``concept_name`` as an ``@en`` literal -> ``skos:prefLabel``.
#: * ``code`` (optional) -- ``concept_code`` -> ``skos:notation``.
#: * ``source`` (optional) -- the native source-vocabulary IRI -> ``skos:exactMatch``.
#:
#: Optional columns left null for a given row (e.g. ``RxNorm Extension``
#: concepts, which have no native code) simply produce no triple for that
#: predicate on that row.
CONCEPT_TEMPLATE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

skos:OmopConceptTemplate [
    ?subject,
    ? ?label,
    ? ?code,
    ? ?source
] :: {
    ottr:Triple(?subject, rdf:type, skos:Concept),
    ottr:Triple(?subject, skos:prefLabel, ?label),
    ottr:Triple(?subject, skos:notation, ?code),
    ottr:Triple(?subject, skos:exactMatch, ?source)
} .
"""


def language_tagged_column(values: pl.Series, language: str = "en") -> pl.Series:
    """Wrap a string column as maplib's language-tagged-literal struct.

    maplib recognises a two-field ``Struct`` -- the string value under
    :data:`LANG_STRING_FIELD`, the language tag under ``"l"`` -- as an
    ``rdf:langString`` literal when mapped through a template. Nulls in
    ``values`` stay null, so the concept template's optional-parameter
    handling drops the ``skos:prefLabel`` triple entirely for those rows.
    """
    return (
        pl.DataFrame({"v": values})
        .with_columns(pl.lit(language).alias("l"))
        .select(pl.struct([pl.col("v").alias(LANG_STRING_FIELD), pl.col("l")]).alias("x"))
        .to_series()
    )
