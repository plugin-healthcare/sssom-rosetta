"""Build SKOS Turtle graphs from DHD Diagnose-/Verrichtingenthesaurus CSV releases.

DHD ("Dutch Hospital Data") publishes the Diagnosethesaurus (DT) and
Verrichtingenthesaurus (VT) as CSV bundles in a versioned "uitleverformaat"
(delivery format). This module targets **uitleverformaat4.3 only**, asserted
via :data:`FORMAT_VERSION`.

Unlike RF2/Athena, DHD uitleverformaat4.3 files are **comma-separated with
quoted fields** (``quote_char='"'``); all columns are read as ``Utf8`` since
``ConceptID``/``TermID``/``DBC_ID`` are zero-padded or otherwise non-numeric
strings that must not be reinterpreted as integers.

DHD rows carry their own ``Begindatum``/``Einddatum`` validity window
(``YYYYMMDD``, fixed-width, so plain string comparison sorts correctly without
parsing to ``pl.Date``). :func:`_active` filters each table independently to
the rows valid on a single as-of date.

As with ``omop.py``, graphs are assembled with **maplib**, not ``rdflib``:
:data:`~sssom_rosetta.vocabulary.templates.DHD_CONCEPT_TEMPLATE` and
:data:`~sssom_rosetta.vocabulary.templates.DHD_CLOSE_MATCH_TEMPLATE` are
declarative OTTR (stOTTR) templates mapped over polars DataFrames via
``Model.map``.

See :doc:`/vocabularies/index` for the rationale behind the uitleverformaat4.3
pin, the temporal-validity simplification, and the maplib/OTTR choice.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal, NamedTuple

import polars as pl
from maplib import Model

from sssom_rosetta.vocabulary.errors import VocabularyError
from sssom_rosetta.vocabulary.fetch import VocabularyIngestError, find_file
from sssom_rosetta.vocabulary.namespaces import (
    DBC,
    ICD10,
    PREFIX_MAP,
    SCT,
    THESAURUS_NAMESPACES,
)
from sssom_rosetta.vocabulary.sources import VOCABULARY_SOURCES
from sssom_rosetta.vocabulary.templates import (
    DHD_CLOSE_MATCH_TEMPLATE,
    DHD_CLOSE_MATCH_TEMPLATE_IRI,
    DHD_CONCEPT_TEMPLATE,
    DHD_CONCEPT_TEMPLATE_IRI,
    LANG_STRING_FIELD,
)

Thesaurus = Literal["dt", "vt"]

#: The DHD delivery-format version this module parses, read from the single
#: source of truth in :data:`~sssom_rosetta.vocabulary.sources.VOCABULARY_SOURCES`
#: so the two never drift apart. Asserted (not just documented) in
#: :func:`build_from_release` so a release in a differently shaped format
#: (e.g. a future ``uitleverformaat5.0``) fails fast instead of silently
#: mis-parsing columns that moved between spec versions.
_DHD_FORMAT_VERSION = VOCABULARY_SOURCES["dhd-thesauri"].format_version
if _DHD_FORMAT_VERSION is None:
    msg = "The 'dhd-thesauri' vocabulary source is missing its format_version."
    raise RuntimeError(msg)
FORMAT_VERSION: str = _DHD_FORMAT_VERSION

_SKOS = "http://www.w3.org/2004/02/skos/core#"

#: Prefixes bound on the produced model, purely for readable Turtle output.
_PREFIXES = {prefix: str(namespace) for prefix, namespace in PREFIX_MAP.items()} | {"skos": _SKOS}


class DhdFormatVersionError(VocabularyError):
    """Raised when a release directory doesn't match :data:`FORMAT_VERSION`."""


class DhdSchemaError(VocabularyError):
    """Raised when a DHD CSV file is missing an expected column.

    Files are located by filename pattern only (see :func:`_exact_suffix`),
    so a silent upstream column rename/removal would otherwise surface as a
    confusing ``ColumnNotFoundError`` deep inside a later transform instead
    of a clear error at read time.
    """


#: Expected header columns per DHD uitleverformaat4.3 CSV file, keyed by the
#: filename suffix :func:`_exact_suffix` locates them by. Validated by
#: :func:`_scan_dhd` so an upstream header change fails fast and loudly.
_EXPECTED_COLUMNS: dict[str, frozenset[str]] = {
    "_ThesaurusConcept.csv": frozenset({"ConceptID", "Begindatum", "Einddatum"}),
    "_ThesaurusTerm.csv": frozenset(
        {"ConceptID", "Omschrijving", "TaalCode", "TypeTerm", "SnomedID", "Begindatum", "Einddatum"}
    ),
    "_AfleidingICD10.csv": frozenset({"ConceptID", "ICD10", "Begindatum", "Einddatum"}),
    "_AfleidingDBC.csv": frozenset({"ConceptID", "SpecialismeCode", "DBC_ID", "Begindatum", "Einddatum"}),
}


def _scan_dhd(path: Path, *, suffix: str) -> pl.LazyFrame:
    """Lazily scan a DHD uitleverformaat4.3 comma-separated CSV as all-``Utf8``.

    Validates the header against :data:`_EXPECTED_COLUMNS` for ``suffix``
    (e.g. ``"_ThesaurusConcept.csv"``) before returning, so a missing column
    -- an upstream format change DHD didn't flag by version -- is caught here
    rather than downstream.

    Raises:
        DhdSchemaError: If any expected column is missing from ``path``'s header.
    """
    frame = pl.scan_csv(path, quote_char='"', infer_schema_length=0)
    expected = _EXPECTED_COLUMNS[suffix]
    missing = expected - set(frame.collect_schema().names())
    if missing:
        msg = f"{path} is missing expected column(s) {sorted(missing)} for a {suffix!r} file."
        raise DhdSchemaError(msg)
    return frame


def _non_blank(column: str) -> pl.Expr:
    """``column`` when non-null and non-empty, ``None`` otherwise."""
    return pl.when(pl.col(column).is_not_null() & (pl.col(column) != "")).then(pl.col(column)).otherwise(None)


def _active(frame: pl.LazyFrame, as_of: str) -> pl.LazyFrame:
    """Filter to rows valid on ``as_of`` (``YYYYMMDD``) per DHD's validity model.

    ``Begindatum``/``Einddatum`` are fixed-width ``YYYYMMDD`` strings, so a
    plain lexicographic string comparison sorts identically to a numeric/date
    comparison -- no need to parse them to ``pl.Date``. A blank/null
    ``Einddatum`` means the row has no known end date (common for currently
    active codes), so it is treated as still valid rather than excluded.
    """
    einddatum = _non_blank("Einddatum")
    return frame.filter((pl.col("Begindatum") <= as_of) & (einddatum.is_null() | (einddatum >= as_of)))


def _concept_subject_column(concept_id_column: str, thesaurus: Thesaurus) -> pl.Expr:
    """Vectorised ``dhddt:<id>``/``dhdvt:<id>`` IRI expression for a ConceptID column."""
    namespace = THESAURUS_NAMESPACES[thesaurus]
    return pl.concat_str([pl.lit(str(namespace)), pl.col(concept_id_column)], separator="")


def load_concepts(thesaurus_concept_csv: Path, as_of: str) -> pl.DataFrame:
    """Read ``ThesaurusConcept.csv``, keep only rows active on ``as_of``.

    Only ``ConceptID`` is kept: ``TypeConcept`` is not used anywhere in the
    graph this module builds.
    """
    return (
        _active(_scan_dhd(thesaurus_concept_csv, suffix="_ThesaurusConcept.csv"), as_of).select("ConceptID").collect()
    )


def load_snomed_terms(thesaurus_term_csv: Path, as_of: str) -> pl.DataFrame:
    """Return one active ``(ConceptID, SnomedID)`` row per concept with a SNOMED mapping.

    ``SnomedID`` is populated on the FSN term row(s); per the spec, a given
    concept has at most one active SnomedID at any point in time (an English
    and a Dutch FSN row can both be concurrently active with the *same*
    SnomedID, hence the final ``.unique()``).
    """
    return (
        _active(_scan_dhd(thesaurus_term_csv, suffix="_ThesaurusTerm.csv"), as_of)
        .filter(pl.col("TypeTerm") == "FSN")
        .with_columns(SnomedID=_non_blank("SnomedID"))
        .filter(pl.col("SnomedID").is_not_null())
        .select("ConceptID", "SnomedID")
        .unique()
        .collect()
    )


def load_labels(thesaurus_term_csv: Path, as_of: str) -> pl.DataFrame:
    """Return one active ``(ConceptID, Omschrijving, Language)`` preferred-label row per concept.

    Uses the FSN term's ``Omschrijving`` as the concept's ``skos:prefLabel``
    text, tagged with a two-letter ``Language`` derived from ``TaalCode``
    (e.g. ``"nl-NL"`` -> ``"nl"``). When both an English (``en-GB``) and
    Dutch (``nl-NL``) FSN are concurrently active for a concept, the Dutch
    one is preferred, since the produced graph targets a Dutch-healthcare
    audience.
    """
    return (
        _active(_scan_dhd(thesaurus_term_csv, suffix="_ThesaurusTerm.csv"), as_of)
        .filter(pl.col("TypeTerm") == "FSN")
        .with_columns(Omschrijving=_non_blank("Omschrijving"))
        .filter(pl.col("Omschrijving").is_not_null())
        .select("ConceptID", "Omschrijving", "TaalCode")
        .collect()
        .sort("TaalCode")  # "en-GB" sorts before "nl-NL"
        .group_by("ConceptID", maintain_order=True)
        .agg(pl.col("Omschrijving").last(), pl.col("TaalCode").last())  # last -> nl-NL when present
        .with_columns(Language=pl.col("TaalCode").str.slice(0, 2).str.to_lowercase())
        .drop("TaalCode")
    )


def load_icd10(afleiding_icd10_csv: Path, as_of: str) -> pl.DataFrame:
    """Return active ``(ConceptID, ICD10)`` pairs from ``AfleidingICD10.csv`` (DT only).

    Cardinality is intentionally 0..N per concept (multiple ``Volgnummer``
    candidates are all kept, not just the default/first one).
    """
    return (
        _active(_scan_dhd(afleiding_icd10_csv, suffix="_AfleidingICD10.csv"), as_of)
        .with_columns(ICD10=_non_blank("ICD10"))
        .filter(pl.col("ICD10").is_not_null())
        .select("ConceptID", "ICD10")
        .collect()
    )


def load_dbc(afleiding_dbc_csv: Path, as_of: str) -> pl.DataFrame:
    """Return active ``(ConceptID, DBC_ID)`` pairs from ``AfleidingDBC.csv`` (DT only).

    A DBC diagnosis code is only unique in combination with its specialism
    code (``SpecialismeCode``): the same ``DBC_ID`` can be reused across
    different specialisms. ``DBC_ID`` here is therefore the composite
    ``f"{SpecialismeCode}-{DBC_ID}"`` string, not the raw ``DBC_ID`` column,
    so :func:`_close_match_rows` mints a correctly-scoped ``dbc:`` IRI.
    Rows with an empty ``DBC_ID`` (a specialism row with no DBC) are dropped.
    """
    return (
        _active(_scan_dhd(afleiding_dbc_csv, suffix="_AfleidingDBC.csv"), as_of)
        .with_columns(DBC_ID=_non_blank("DBC_ID"))
        .filter(pl.col("DBC_ID").is_not_null())
        .select(
            "ConceptID",
            DBC_ID=pl.concat_str([pl.col("SpecialismeCode"), pl.col("DBC_ID")], separator="-"),
        )
        .collect()
    )


def _concept_rows(
    concepts: pl.DataFrame, snomed_terms: pl.DataFrame, labels: pl.DataFrame, thesaurus: Thesaurus
) -> pl.DataFrame:
    """Prepare the concept frame for :data:`DHD_CONCEPT_TEMPLATE`.

    Left-joins concepts to their (optional) active SNOMED FSN term and
    preferred label, so concepts without a match keep a null ``snomed``/
    ``label`` column -- the template's optional-parameter handling then drops
    the corresponding triple for those rows entirely.
    """
    joined = concepts.join(snomed_terms, on="ConceptID", how="left").join(labels, on="ConceptID", how="left")
    return joined.with_columns(
        subject=_concept_subject_column("ConceptID", thesaurus),
        snomed=pl.when(pl.col("SnomedID").is_not_null())
        .then(pl.concat_str([pl.lit(str(SCT)), pl.col("SnomedID")], separator=""))
        .otherwise(None),
        label=pl.when(pl.col("Omschrijving").is_not_null())
        .then(pl.struct([pl.col("Omschrijving").alias(LANG_STRING_FIELD), pl.col("Language").alias("l")]))
        .otherwise(None),
    )


def _close_match_rows(
    pairs: pl.DataFrame, code_column: str, code_namespace: object, thesaurus: Thesaurus
) -> pl.DataFrame:
    """Prepare an ICD10/DBC pair frame for :data:`DHD_CLOSE_MATCH_TEMPLATE`."""
    return pairs.with_columns(
        subject=_concept_subject_column("ConceptID", thesaurus),
        object=pl.concat_str([pl.lit(str(code_namespace)), pl.col(code_column)], separator=""),
    ).select("subject", "object")


class DhdCrossLinks(NamedTuple):
    """DT-only ICD10/DBC ``skos:closeMatch`` derivation frames, bundled to keep :func:`build_graph`'s arity down.

    Both fields are ``None`` for VT, which has no ICD10/DBC derivations.
    """

    icd10: pl.DataFrame | None = None
    dbc: pl.DataFrame | None = None


def build_graph(
    thesaurus: Thesaurus,
    concepts: pl.DataFrame,
    snomed_terms: pl.DataFrame,
    labels: pl.DataFrame | None = None,
    cross_links: DhdCrossLinks | None = None,
) -> Model:
    """Assemble a DHD SKOS graph (DT or VT) from filtered concept/derivation frames.

    Concept nodes are mapped through :data:`DHD_CONCEPT_TEMPLATE`; ICD10/DBC
    cross-links (DT only -- ``cross_links`` is ``None`` for VT) are mapped
    through :data:`DHD_CLOSE_MATCH_TEMPLATE`. Returns a maplib ``Model``
    rather than an ``rdflib.Graph``, mirroring ``omop.build_graph``.
    """
    model = Model()
    model.add_prefixes(_PREFIXES)
    model.add_template(DHD_CONCEPT_TEMPLATE)
    model.add_template(DHD_CLOSE_MATCH_TEMPLATE)

    if labels is None:
        labels = pl.DataFrame(
            schema={"ConceptID": pl.Utf8, "Omschrijving": pl.Utf8, "Language": pl.Utf8},
        )
    concept_rows = _concept_rows(concepts, snomed_terms, labels, thesaurus)
    model.map(DHD_CONCEPT_TEMPLATE_IRI, concept_rows.select("subject", "label", "snomed"))

    if cross_links is not None:
        if cross_links.icd10 is not None and cross_links.icd10.height:
            model.map(DHD_CLOSE_MATCH_TEMPLATE_IRI, _close_match_rows(cross_links.icd10, "ICD10", ICD10, thesaurus))
        if cross_links.dbc is not None and cross_links.dbc.height:
            model.map(DHD_CLOSE_MATCH_TEMPLATE_IRI, _close_match_rows(cross_links.dbc, "DBC_ID", DBC, thesaurus))

    return model


def _find_release_dir(root: Path, thesaurus: Thesaurus) -> Path:
    """Find the single ``uitleverformaat4.3`` release directory for ``thesaurus`` under ``root``.

    The ingested ``dhd-thesauri`` ZIP nests both DT and VT under
    ``thesauri/DT/`` / ``thesauri/VT/``, each containing one dated,
    ``FORMAT_VERSION``-suffixed subdirectory.

    Raises:
        DhdFormatVersionError: If zero or more than one matching directory is found.
    """
    marker = f"/{thesaurus.upper()}/"
    matches = [
        path for path in root.rglob(f"*_{FORMAT_VERSION}") if path.is_dir() and marker in f"/{path.relative_to(root)}/"
    ]
    if len(matches) != 1:
        msg = (
            f"Expected exactly one {thesaurus.upper()} release directory ending in "
            f"'_{FORMAT_VERSION}' under {root}, found: {sorted(str(m) for m in matches)}"
        )
        raise DhdFormatVersionError(msg)
    return matches[0]


def _exact_suffix(root: Path, suffix: str) -> Path:
    """Find the single file under ``root`` whose name ends with ``suffix``.

    Thin wrapper over :func:`~sssom_rosetta.vocabulary.fetch.find_file`
    (already used by ``omop.py``) that re-raises as :class:`DhdFormatVersionError`
    for consistency with :func:`_find_release_dir`'s error type.
    """
    try:
        return find_file(root, suffix=suffix)
    except VocabularyIngestError as exc:
        raise DhdFormatVersionError(str(exc)) from exc


def build_from_release(
    release_dir: Path,
    thesaurus: Thesaurus,
    as_of: str | None = None,
) -> Model:
    """Locate ``thesaurus``'s uitleverformaat4.3 CSVs under ``release_dir`` and build its graph.

    Args:
        release_dir: The ingested ``dhd-thesauri`` release directory (contains
            both ``thesauri/DT/`` and ``thesauri/VT/`` subtrees).
        thesaurus: ``"dt"`` (Diagnosethesaurus, full: SNOMED + ICD10 + DBC) or
            ``"vt"`` (Verrichtingenthesaurus, SNOMED-only).
        as_of: ``YYYYMMDD`` validity date; defaults to today.
    """
    as_of_str = as_of if as_of is not None else date.today().strftime("%Y%m%d")  # noqa: DTZ011
    thesaurus_dir = _find_release_dir(release_dir, thesaurus)

    concept_csv = _exact_suffix(thesaurus_dir, "_ThesaurusConcept.csv")
    term_csv = _exact_suffix(thesaurus_dir, "_ThesaurusTerm.csv")
    concepts = load_concepts(concept_csv, as_of_str)
    snomed_terms = load_snomed_terms(term_csv, as_of_str)
    labels = load_labels(term_csv, as_of_str)

    if thesaurus == "vt":
        return build_graph(thesaurus, concepts, snomed_terms, labels)

    icd10_csv = _exact_suffix(thesaurus_dir, "_AfleidingICD10.csv")
    dbc_csv = _exact_suffix(thesaurus_dir, "_AfleidingDBC.csv")
    icd10 = load_icd10(icd10_csv, as_of_str)
    dbc = load_dbc(dbc_csv, as_of_str)
    return build_graph(thesaurus, concepts, snomed_terms, labels, DhdCrossLinks(icd10=icd10, dbc=dbc))


def write_ttl(model: Model, output_path: Path) -> Path:
    """Serialize ``model`` to Turtle at ``output_path``, creating parents."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.write(str(output_path), format="turtle")
    return output_path
