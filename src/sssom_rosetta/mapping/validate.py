"""Validate SSSOM ``MappingSet`` objects: schema conformance + referential integrity.

Two independent checks are performed here:

1. **Schema conformance** — round-tripping a ``MappingSet`` (or a bare list
   of ``Mapping`` objects) through the generated Pydantic models via
   ``model_validate``/``model_dump``. Since callers typically already hold
   live ``Mapping``/``MappingSet`` instances (e.g. from
   ``mapping.author.build_mapping``), this mostly catches data that was
   constructed by bypassing the models (e.g. read from a raw dict).
2. **Referential integrity** — re-checking every mapping's
   ``subject_id``/``object_id`` CURIE against the ontology graph it should
   belong to, using ``ontology.catalog.resource_exists``. This is what
   catches "was valid when authored, but the ontology was re-fetched and
   the term is now gone" drift.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rdflib import Graph

from sssom_rosetta.mapping.author import UnknownPrefixError, expand_curie
from sssom_rosetta.models.sssom import Mapping, MappingSet
from sssom_rosetta.ontology.catalog import resource_exists


class SchemaConformanceError(ValueError):
    """Raised when data cannot be round-tripped through the generated SSSOM models."""


@dataclass
class ReferentialIntegrityIssue:
    """One mapping row that failed referential integrity checking."""

    mapping_index: int
    field: str
    curie: str
    reason: str


@dataclass
class ValidationResult:
    """Outcome of validating a mapping set."""

    mapping_set: MappingSet
    issues: list[ReferentialIntegrityIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no referential integrity issues were found."""
        return not self.issues


def validate_schema_conformance(
    mapping_set: MappingSet | dict[str, object],
) -> MappingSet:
    """Round-trip ``mapping_set`` through the generated Pydantic ``MappingSet`` model.

    Args:
        mapping_set: Either an existing ``MappingSet`` instance (re-validated
            via ``model_dump``/``model_validate`` to catch any mutation that
            bypassed the model) or a raw dict (e.g. parsed from JSON/CSVW).

    Returns:
        A freshly validated ``MappingSet`` instance.

    Raises:
        SchemaConformanceError: If the data doesn't conform to the SSSOM
            schema's generated Pydantic models.
    """
    payload = (
        mapping_set.model_dump() if isinstance(mapping_set, MappingSet) else mapping_set
    )
    try:
        return MappingSet.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 - re-raised as a domain-specific error
        raise SchemaConformanceError(
            f"MappingSet failed schema validation: {exc}"
        ) from exc


def _check_mapping_referential_integrity(
    index: int,
    mapping: Mapping,
    prefix_map: dict[str, str],
    subject_graph: Graph,
    object_graph: Graph,
) -> list[ReferentialIntegrityIssue]:
    issues: list[ReferentialIntegrityIssue] = []
    for field_name, curie, graph in (
        ("subject_id", mapping.subject_id, subject_graph),
        ("object_id", mapping.object_id, object_graph),
    ):
        if curie is None:
            issues.append(
                ReferentialIntegrityIssue(
                    index, field_name, "", f"{field_name} is missing"
                )
            )
            continue
        try:
            iri = expand_curie(curie, prefix_map)
        except UnknownPrefixError as exc:
            issues.append(ReferentialIntegrityIssue(index, field_name, curie, str(exc)))
            continue
        if not resource_exists(graph, iri):
            issues.append(
                ReferentialIntegrityIssue(
                    index,
                    field_name,
                    curie,
                    f"{curie!r} (expands to {iri!r}) was not found in the ontology graph",
                )
            )
    return issues


def validate_referential_integrity(
    mapping_set: MappingSet,
    *,
    prefix_map: dict[str, str],
    subject_graph: Graph,
    object_graph: Graph,
) -> list[ReferentialIntegrityIssue]:
    """Re-check every mapping's ``subject_id``/``object_id`` against ontology graphs.

    Args:
        mapping_set: The mapping set to check.
        prefix_map: Maps CURIE prefixes to namespace IRIs.
        subject_graph: Ontology graph every ``subject_id`` must resolve against.
        object_graph: Ontology graph every ``object_id`` must resolve against.

    Returns:
        A list of issues found (empty if every mapping is referentially intact).
    """
    mappings = mapping_set.mappings or []
    issues: list[ReferentialIntegrityIssue] = []
    for index, mapping in enumerate(mappings):
        issues.extend(
            _check_mapping_referential_integrity(
                index, mapping, prefix_map, subject_graph, object_graph
            )
        )
    return issues


def validate_mapping_set(
    mapping_set: MappingSet,
    *,
    prefix_map: dict[str, str],
    subject_graph: Graph,
    object_graph: Graph,
) -> ValidationResult:
    """Run both schema conformance and referential integrity checks on ``mapping_set``.

    Args:
        mapping_set: The mapping set to validate.
        prefix_map: Maps CURIE prefixes to namespace IRIs.
        subject_graph: Ontology graph every ``subject_id`` must resolve against.
        object_graph: Ontology graph every ``object_id`` must resolve against.

    Returns:
        A ``ValidationResult`` holding the re-validated ``MappingSet`` and any
        referential integrity issues found. Check ``result.is_valid``.

    Raises:
        SchemaConformanceError: If the mapping set doesn't conform to the
            generated SSSOM Pydantic schema.
    """
    validated = validate_schema_conformance(mapping_set)
    issues = validate_referential_integrity(
        validated,
        prefix_map=prefix_map,
        subject_graph=subject_graph,
        object_graph=object_graph,
    )
    return ValidationResult(mapping_set=validated, issues=issues)
