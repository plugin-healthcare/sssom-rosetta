"""Registry of pinned vocabulary sources (LOINC-SNOMED RF2, OMOP/Athena).

Unlike ``ontology/sources.py``, these releases are large, ZIP-packaged, and
**licence-gated** (SNOMED International affiliate licence for the LOINC-SNOMED
extension; an Athena account for the OMOP bundle). There is therefore no open,
stable download URL to pin: the curator downloads the release manually and the
loader ingests that local ZIP (see ``fetch.py``'s ``from_local`` path),
recording its checksum for reproducibility.
"""

from __future__ import annotations

from dataclasses import dataclass


class UnknownVocabularySourceError(KeyError):
    """Raised when a requested vocabulary source is not in the registry."""

    def __init__(self, name: str) -> None:
        known = ", ".join(sorted(VOCABULARY_SOURCES))
        super().__init__(f"Unknown vocabulary source {name!r}. Known sources: {known}")


@dataclass(frozen=True)
class VocabularySource:
    """A pinned, licence-gated vocabulary release ingested from a local ZIP.

    Attributes:
        name: Short registry key, e.g. ``"loinc-snomed"`` or ``"omop"``.
        version: Pinned release version string.
        kind: ``"rf2"`` (SNOMED CT RF2 package) or ``"athena"`` (OMOP bundle).
        description: Human-readable provenance note.
        download_page: The (licence-gated) page the ZIP is obtained from;
            informational only — the loader never scrapes it.
        checksum: SHA-256 of the curator-provided ZIP, verified on ingest.
            ``None`` until a specific release is pinned by a curator.
    """

    name: str
    version: str
    kind: str
    description: str
    download_page: str
    checksum: str | None = None


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
