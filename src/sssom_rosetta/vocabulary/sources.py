"""Registry of pinned vocabulary sources (LOINC-SNOMED RF2, OMOP/Athena).

Unlike ``ontology/sources.py``, these releases are large, ZIP-packaged, and
**licence-gated** (SNOMED International affiliate licence for the LOINC-SNOMED
extension; an Athena account for the OMOP bundle). There is therefore no open,
stable download URL to pin: the curator downloads the release manually and the
loader ingests that local ZIP (see ``fetch.py``'s ``from_local`` path),
recording its checksum for reproducibility.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from sssom_rosetta.vocabulary.errors import VocabularyError


class UnknownVocabularySourceError(VocabularyError, KeyError):
    """Raised when a requested vocabulary source is not in the registry."""

    def __init__(self, name: str) -> None:
        """Build the error message from the unknown ``name``, listing known sources."""
        known = ", ".join(sorted(VOCABULARY_SOURCES))
        super().__init__(f"Unknown vocabulary source {name!r}. Known sources: {known}")


class VocabularySource(BaseModel):
    """A pinned, licence-gated vocabulary release ingested from a local ZIP.

    A frozen (immutable) pydantic model rather than a plain dataclass, so the
    registry below gets field-level validation for free (e.g. a future YAML
    loader for this registry can call ``VocabularySource.model_validate`` on
    parsed YAML directly, instead of hand-rolling a validator).

    Attributes:
        name: Short registry key, e.g. ``"loinc-snomed"`` or ``"omop"``.
        version: Pinned release version string.
        kind: ``"rf2"`` (SNOMED CT RF2 package), ``"athena"`` (OMOP bundle),
            or ``"dhd-csv"`` (DHD thesaurus CSV release).
        description: Human-readable provenance note.
        download_page: The (licence-gated) page the ZIP is obtained from;
            informational only — the loader never scrapes it.
        checksum: SHA-256 of the curator-provided ZIP, verified on ingest.
            ``None`` until a specific release is pinned by a curator.
        format_version: The source's own file/column-layout format version
            (e.g. DHD's ``"uitleverformaat4.3"``), when the source publishes
            one and it's distinct from ``version`` (the pinned release/content
            version). ``None`` for sources without a separate format version.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    kind: str
    description: str
    download_page: str
    checksum: str | None = None
    format_version: str | None = None


VOCABULARY_SOURCES: dict[str, VocabularySource] = {
    "loinc-snomed": VocabularySource(
        name="loinc-snomed",
        version="2.82",
        kind="rf2",
        description=(
            "LOINC-SNOMED Ontology, a SNOMED CT extension (module 11010000107 "
            "|LOINC Extension module|) distributed as an RF2 package."
        ),
        download_page="https://loincsnomed.org/downloads",
    ),
    "omop": VocabularySource(
        name="omop",
        version="unversioned",
        kind="athena",
        description=(
            "OHDSI OMOP Standardized Vocabularies bundle (SNOMED, LOINC, "
            "RxNorm, RxNorm Extension, ICD10, ICD10CM), tab-delimited CSVs "
            "downloaded from Athena."
        ),
        download_page="https://athena.ohdsi.org/",
    ),
    "snomed-international": VocabularySource(
        name="snomed-international",
        version="20260101",
        kind="rf2",
        description=(
            "SNOMED CT International Edition (core module 900000000000207008), "
            "distributed as an RF2 package. Supplies the top-level concept "
            "hierarchy (Body structure, Clinical finding, Observable entity, "
            "Substance, ...) up to the root that the LOINC Extension depends "
            "on. Pinned to the International release targeted by the ingested "
            "LOINC-SNOMED extension's module-dependency refset."
        ),
        download_page="https://www.nlm.nih.gov/healthit/snomedct/international.html",
    ),
    "dhd-thesauri": VocabularySource(
        name="dhd-thesauri",
        version="202508",
        kind="dhd-csv",
        format_version="uitleverformaat4.3",
        description=(
            "DHD Diagnosethesaurus (DT, release 3.44) and Verrichtingenthesaurus "
            "(VT, release 2.43) CSV bundles, both in uitleverformaat4.3, "
            "distributed together as one ZIP under `thesauri/DT/` and "
            "`thesauri/VT/`. `dhd.build_from_release` locates the DT or VT "
            "subtree within the ingested release directory and asserts its "
            "`FORMAT_VERSION` marker (see `dhd.py`)."
        ),
        download_page="https://mijn.dhd.nl/",
    ),
}


def get_vocabulary_source(name: str) -> VocabularySource:
    """Look up a registered vocabulary source by name.

    Raises:
        UnknownVocabularySourceError: If ``name`` is not registered.
    """
    try:
        return VOCABULARY_SOURCES[name]
    except KeyError as exc:
        raise UnknownVocabularySourceError(name) from exc
