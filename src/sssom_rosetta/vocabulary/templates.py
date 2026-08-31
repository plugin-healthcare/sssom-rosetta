"""OTTR (stOTTR) templates used to map OMOP tabular rows to SKOS triples.

Templates are the declarative counterpart to the ``if row[...]:`` branches a
hand-written triple-add loop would need: a leading ``?`` on a template
parameter (e.g. ``? ?label``) marks it *optional*, and maplib silently omits
any triple that uses an unbound optional variable for a given row, instead of
requiring Python-side conditionals. See :doc:`/vocabularies/index` for the
rationale behind choosing maplib/OTTR templates over a hand-written triple-add
loop.
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
@prefix ottr: <http://ns.ottr.xyz/0.4/> .

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


#: IRI of the DHD concept template below, passed to ``Model.map``.
DHD_CONCEPT_TEMPLATE_IRI = "http://www.w3.org/2004/02/skos/core#DhdConceptTemplate"

#: Maps one DHD ``ThesaurusConcept`` row (already joined to its active FSN
#: term, see ``dhd.py``) to a SKOS concept node:
#:
#: * ``subject`` (required) -- the ``dhddt:``/``dhdvt:`` concept IRI.
#: * ``label`` (optional) -- the FSN's ``Omschrijving`` as a language-tagged
#:   literal (``nl`` preferred over ``en`` when both are active) ->
#:   ``skos:prefLabel``.
#: * ``snomed`` (optional) -- the ``sct:`` IRI of the concept's SNOMED CT
#:   FSN term -> ``skos:exactMatch``. Left unbound (null) when the concept
#:   has no active SNOMED mapping, so no triple is emitted for that row --
#:   the same optional-drop mechanism as :data:`CONCEPT_TEMPLATE`'s ``label``.
#:
#: Used for both DT and VT: VT rows simply never carry an
#: ``AfleidingICD10``/``AfleidingDBC``-derived match (see
#: :data:`DHD_CLOSE_MATCH_TEMPLATE`, which is DT-only).
DHD_CONCEPT_TEMPLATE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .

skos:DhdConceptTemplate [
    ?subject,
    ? ?label,
    ? ?snomed
] :: {
    ottr:Triple(?subject, rdf:type, skos:Concept),
    ottr:Triple(?subject, skos:prefLabel, ?label),
    ottr:Triple(?subject, skos:exactMatch, ?snomed)
} .
"""

#: IRI of the DHD close-match template below, passed to ``Model.map``.
DHD_CLOSE_MATCH_TEMPLATE_IRI = "http://www.w3.org/2004/02/skos/core#DhdCloseMatchTemplate"

#: Maps a plain ``(subject, object)`` row to a ``skos:closeMatch`` triple.
#: Both parameters are required (unlike :data:`DHD_CONCEPT_TEMPLATE`'s
#: ``snomed``): the DT-only ``AfleidingICD10``/``AfleidingDBC`` derivations
#: are pre-filtered to non-blank rows before mapping (see ``dhd.py``'s
#: ``load_icd10``/``load_dbc``), so every row here always has both an
#: ``ICD10``/``DBC_ID`` value. Reused for both the ``icd10:`` and ``dbc:``
#: cross-links -- these are administrative/classification derivations, not
#: asserted subsumption relationships, hence ``closeMatch`` rather than
#: ``broadMatch``/``narrowMatch`` (see :doc:`/vocabularies/index`'s
#: relationship-to-SKOS mapping table).
DHD_CLOSE_MATCH_TEMPLATE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .

skos:DhdCloseMatchTemplate [
    ?subject,
    ?object
] :: {
    ottr:Triple(?subject, skos:closeMatch, ?object)
} .
"""
