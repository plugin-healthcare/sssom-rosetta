"""Shared RDF namespaces and IRI-minting helpers for the vocabulary pipeline.

Centralised so ``loinc_snomed``, ``omop`` and ``merge`` all mint identical IRIs
for the same underlying concept — that shared identity is what lets an OMOP
``concept_id`` node connect to the LOINC-SNOMED ontology graph after merging.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from rdflib import Namespace, URIRef

from sssom_rosetta.vocabulary.errors import VocabularyError


@dataclass(frozen=True)
class VocabularyNamespace:
    """One CURIE prefix -> RDF namespace binding used by this pipeline.

    Attributes:
        prefix: The CURIE prefix bound on every graph produced by this
            package (e.g. ``"sct"``).
        namespace: The RDF namespace the prefix expands to.
    """

    prefix: str
    namespace: Namespace


#: Single source of truth for every prefix/namespace pair the vocabulary
#: pipeline mints IRIs in or binds on its graphs.
_NAMESPACES: tuple[VocabularyNamespace, ...] = (
    VocabularyNamespace("sct", Namespace("http://snomed.info/id/")),
    VocabularyNamespace("omopconcept", Namespace("https://w3id.org/omop/concept/")),
    VocabularyNamespace("loinc", Namespace("https://loinc.org/")),
    VocabularyNamespace("rxnorm", Namespace("http://purl.bioontology.org/ontology/RXNORM/")),
    VocabularyNamespace("icd10", Namespace("http://hl7.org/fhir/sid/icd-10/")),
    VocabularyNamespace("icd10cm", Namespace("http://hl7.org/fhir/sid/icd-10-cm/")),
    VocabularyNamespace("dhddt", Namespace("https://w3id.org/dhd/diagnosethesaurus/concept/")),
    VocabularyNamespace("dhdvt", Namespace("https://w3id.org/dhd/verrichtingenthesaurus/concept/")),
    VocabularyNamespace("dbc", Namespace("https://w3id.org/dhd/dbc/")),
)

#: CURIE prefix -> namespace, bound on every graph produced by this package.
#: See :doc:`/vocabularies/index` ("IRI schemes") for what each prefix means.
PREFIX_MAP: dict[str, Namespace] = {entry.prefix: entry.namespace for entry in _NAMESPACES}

SCT = PREFIX_MAP["sct"]
OMOP_CONCEPT = PREFIX_MAP["omopconcept"]
LOINC = PREFIX_MAP["loinc"]
RXNORM = PREFIX_MAP["rxnorm"]
ICD10 = PREFIX_MAP["icd10"]
ICD10CM = PREFIX_MAP["icd10cm"]
DHD_DIAGNOSETHESAURUS = PREFIX_MAP["dhddt"]
DHD_VERRICHTINGENTHESAURUS = PREFIX_MAP["dhdvt"]
DBC = PREFIX_MAP["dbc"]

#: DHD ``thesaurus`` key -> its dedicated namespace. Kept as separate
#: namespaces since a DT and a VT ``ConceptID`` could coincidentally collide
#: as strings. Single source of truth shared with ``dhd.py``'s vectorised
#: (polars) IRI-minting, so the two never drift apart.
THESAURUS_NAMESPACES: dict[str, Namespace] = {
    "dt": DHD_DIAGNOSETHESAURUS,
    "vt": DHD_VERRICHTINGENTHESAURUS,
}

#: OMOP ``vocabulary_id`` -> the namespace its native ``concept_code`` lives in.
#: ``RxNorm Extension`` concepts have no native code, so they stay OMOP-minted
#: (handled by returning ``None`` from :func:`source_concept_iri`).
_VOCABULARY_NAMESPACES: dict[str, Namespace] = {
    "SNOMED": SCT,
    "LOINC": LOINC,
    "RxNorm": RXNORM,
    "ICD10": ICD10,
    "ICD10CM": ICD10CM,
}

#: The OMOP ``vocabulary_id`` values this pipeline integrates.
TARGET_VOCABULARIES: frozenset[str] = frozenset({"SNOMED", "LOINC", "RxNorm", "RxNorm Extension", "ICD10", "ICD10CM"})


class UnknownThesaurusError(VocabularyError, ValueError):
    """Raised when a ``thesaurus`` key is neither ``"dt"`` nor ``"vt"``."""

    def __init__(self, thesaurus: str) -> None:
        """Build the error message from the unknown ``thesaurus``, listing known keys."""
        known = ", ".join(sorted(THESAURUS_NAMESPACES))
        super().__init__(f"Unknown DHD thesaurus {thesaurus!r}. Known values: {known}")


def sct_iri(sctid: str) -> URIRef:
    """Return the SNOMED CT IRI for an SCTID string."""
    return SCT[sctid]


def dhd_concept_iri(thesaurus: str, concept_id: str) -> URIRef:
    """Return the DHD concept IRI for a ``ConceptID``, in the ``thesaurus``-specific namespace.

    ``thesaurus`` is ``"dt"`` (Diagnosethesaurus) or ``"vt"``
    (Verrichtingenthesaurus).

    Raises:
        UnknownThesaurusError: If ``thesaurus`` is neither ``"dt"`` nor
            ``"vt"`` -- a typo here must fail loudly rather than silently
            minting a ``vt`` IRI for what was meant to be a ``dt`` concept.
    """
    try:
        namespace = THESAURUS_NAMESPACES[thesaurus]
    except KeyError as exc:
        raise UnknownThesaurusError(thesaurus) from exc
    return namespace[concept_id]


def dbc_iri(dbc_id: str) -> URIRef:
    """Return the DBC diagnosis-code IRI for a composite DBC code string.

    ``dbc_id`` is expected to already be the ``f"{SpecialismeCode}-{DBC_ID}"``
    composite produced by ``dhd.load_dbc`` -- a raw ``DBC_ID`` alone is not
    unique, since the same code can be reused across different specialisms.
    """
    return DBC[dbc_id]


def omop_iri(concept_id: str) -> URIRef:
    """Return the OMOP concept IRI for an integer ``concept_id`` (as a string)."""
    return OMOP_CONCEPT[concept_id]


def source_concept_iri(vocabulary_id: str, concept_code: str) -> URIRef | None:
    """Mint the native source-vocabulary IRI for an OMOP row, or ``None``.

    Returns ``None`` for vocabularies without a native code namespace (e.g.
    ``RxNorm Extension``), signalling the caller to keep the OMOP-minted node
    as the concept's only identity.
    """
    namespace = _VOCABULARY_NAMESPACES.get(vocabulary_id)
    if namespace is None:
        return None
    # Concept codes can contain characters that are illegal in an IRI path
    # (e.g. LOINC class codes like "H&P.SURG PROC" or "NR STATS" with spaces
    # and ampersands). Percent-encode them so rdflib can serialize the IRI.
    return URIRef(str(namespace) + quote(concept_code, safe=""))
