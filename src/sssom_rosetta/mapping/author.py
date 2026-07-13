"""Author SSSOM ``Mapping`` objects, resolving CURIEs against ontology graphs.

This module is the single place where a raw ``subject_id``/``object_id``
CURIE gets checked against the ontology it's supposed to come from *before*
a ``Mapping`` is constructed. It never invents or guesses IRIs: callers must
supply a prefix map (CURIE prefix -> namespace IRI) and, for each side of
the mapping, the ``rdflib.Graph`` the CURIE should resolve against (see
``ontology.loader.load_ontology`` and ``ontology.catalog``).
"""

from __future__ import annotations

from typing import Any

from rdflib import Graph

from sssom_rosetta.models.sssom import Mapping
from sssom_rosetta.ontology.catalog import resource_exists


class UnknownPrefixError(KeyError):
    """Raised when a CURIE's prefix isn't in the supplied prefix map."""

    def __init__(self, curie: str, prefix_map: dict[str, str]) -> None:
        prefix = curie.split(":", 1)[0]
        known = ", ".join(sorted(prefix_map)) or "(none)"
        super().__init__(
            f"Unknown CURIE prefix {prefix!r} in {curie!r}. Known prefixes: {known}"
        )


class UnresolvableCurieError(ValueError):
    """Raised when a CURIE expands to an IRI that doesn't exist in its ontology graph."""

    def __init__(self, curie: str, iri: str) -> None:
        super().__init__(
            f"CURIE {curie!r} (expands to {iri!r}) was not found in the ontology graph"
        )


def expand_curie(curie: str, prefix_map: dict[str, str]) -> str:
    """Expand a CURIE (e.g. ``"omop:Person"``) into a full IRI using ``prefix_map``.

    Args:
        curie: A CURIE of the form ``"<prefix>:<local_name>"``.
        prefix_map: Maps CURIE prefixes to their namespace IRI (the IRI is
            prepended directly to ``local_name``, no separator is inserted,
            so namespace IRIs must already end in ``#`` or ``/`` as needed).

    Returns:
        The expanded IRI.

    Raises:
        UnknownPrefixError: If the CURIE's prefix isn't in ``prefix_map``.
        ValueError: If ``curie`` doesn't contain a ``:`` separator.
    """
    if ":" not in curie:
        raise ValueError(f"Not a CURIE (missing ':'): {curie!r}")
    prefix, local_name = curie.split(":", 1)
    try:
        namespace = prefix_map[prefix]
    except KeyError as exc:
        raise UnknownPrefixError(curie, prefix_map) from exc
    return f"{namespace}{local_name}"


def resolve_curie(curie: str, prefix_map: dict[str, str], graph: Graph) -> str:
    """Expand ``curie`` and verify it resolves to a resource in ``graph``.

    Returns:
        The expanded IRI.

    Raises:
        UnknownPrefixError: If the CURIE's prefix isn't in ``prefix_map``.
        UnresolvableCurieError: If the expanded IRI isn't a resource in ``graph``.
    """
    iri = expand_curie(curie, prefix_map)
    if not resource_exists(graph, iri):
        raise UnresolvableCurieError(curie, iri)
    return iri


def build_mapping(
    *,
    subject_curie: str,
    predicate: str,
    object_curie: str,
    prefix_map: dict[str, str],
    subject_graph: Graph,
    object_graph: Graph,
    mapping_justification: str,
    author_id: list[str] | None = None,
    confidence: float | None = None,
    **extra_fields: Any,
) -> Mapping:
    """Build a validated SSSOM ``Mapping`` from CURIEs, resolved against ontology graphs.

    ``subject_curie`` is resolved against ``subject_graph`` and
    ``object_curie`` against ``object_graph``; both must exist as
    resources in their respective graphs or this raises before
    constructing the ``Mapping``. ``predicate`` (e.g. ``"skos:exactMatch"``)
    is passed straight through as ``predicate_id``: the SSSOM schema's
    ``predicate_id`` range covers the full SKOS/OWL/RDFS/semapv predicate
    space, so it is not independently resolved against either ontology.

    Args:
        subject_curie: CURIE for the subject entity, e.g. ``"omop:Person"``.
        predicate: SSSOM mapping predicate CURIE, e.g. ``"skos:exactMatch"``.
        object_curie: CURIE for the object entity, e.g. ``"onz-g:Client"``.
        prefix_map: Maps CURIE prefixes (for both subject and object) to
            namespace IRIs.
        subject_graph: Ontology graph the subject CURIE must resolve against.
        object_graph: Ontology graph the object CURIE must resolve against.
        mapping_justification: SSSOM justification CURIE, e.g.
            ``"semapv:ManualMappingCuration"``.
        author_id: Optional list of author identifiers, e.g. ORCID CURIEs/IRIs.
        confidence: Optional confidence score in ``[0, 1]``.
        **extra_fields: Any other SSSOM ``Mapping`` fields (e.g.
            ``subject_label``, ``object_label``, ``comment``).

    Returns:
        A validated ``Mapping`` instance. ``subject_id``/``object_id`` are
        stored as the CURIEs passed in (matching SSSOM/TSV convention, where
        a mapping set's ``curie_map`` header does the CURIE-to-IRI
        expansion); this function only uses the expanded IRIs internally to
        validate against the ontology graphs.

    Raises:
        UnknownPrefixError: If either CURIE's prefix isn't in ``prefix_map``.
        UnresolvableCurieError: If either CURIE doesn't resolve in its graph.
    """
    resolve_curie(subject_curie, prefix_map, subject_graph)
    resolve_curie(object_curie, prefix_map, object_graph)

    return Mapping(
        subject_id=subject_curie,
        predicate_id=predicate,
        object_id=object_curie,
        mapping_justification=mapping_justification,
        author_id=author_id,
        confidence=confidence,
        **extra_fields,
    )
