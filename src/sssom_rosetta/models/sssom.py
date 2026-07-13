"""Pydantic models for the SSSOM data model.

Generated, do not hand-edit. Regenerate with:

    uv run gen-pydantic \
        "$(uv run python -c 'import sssom_schema, os; print(os.path.join(os.path.dirname(sssom_schema.__file__), "schema", "sssom_schema.yaml"))')" \
        > src/sssom_rosetta/models/sssom.py

The `sssom-schema` version is pinned in pyproject.toml (currently 1.1.0a5,
the version required by the pinned `sssom` (sssom-py) release; see the
"Reproducible schema" design principle in AGENTS.md). Bump `sssom-schema`
and `sssom` together, then rerun the command above, rather than editing
generated fields by hand.

Note: gen-pydantic 1.11.1 emits a bare `URI` annotation for slots typed
`NonRelativeURI` (typeof: uri) without importing it; the import below of
`linkml_runtime.utils.metamodelcore.URI` is a manual patch on top of the
generated output to fix that, since linkml_runtime is already a transitive
runtime dependency of sssom-schema. If a future gen-pydantic release fixes
this upstream, this patch (and its callout here) can be dropped.
"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from typing import Any, ClassVar, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator
from linkml_runtime.utils.metamodelcore import URI


metamodel_version = "1.11.0"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias=True,
        validate_by_name=True,
        validate_assignment=True,
        validate_default=True,
        extra="forbid",
        arbitrary_types_allowed=True,
        use_enum_values=True,
        strict=False,
    )


class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key: str):
        return getattr(self.root, key)

    def __getitem__(self, key: str):
        return self.root[key]

    def __setitem__(self, key: str, value):
        self.root[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta(
    {
        "default_curi_maps": ["semweb_context", "obo_context"],
        "default_prefix": "sssom",
        "default_range": "string",
        "description": "Datamodel for Simple Standard for Sharing Ontological "
        "Mappings (SSSOM)",
        "id": "https://w3id.org/sssom/schema/",
        "imports": ["linkml:types"],
        "name": "sssom",
        "prefixes": {
            "dcterms": {
                "prefix_prefix": "dcterms",
                "prefix_reference": "http://purl.org/dc/terms/",
            },
            "linkml": {
                "prefix_prefix": "linkml",
                "prefix_reference": "https://w3id.org/linkml/",
            },
            "oboInOwl": {
                "prefix_prefix": "oboInOwl",
                "prefix_reference": "http://www.geneontology.org/formats/oboInOwl#",
            },
            "pav": {"prefix_prefix": "pav", "prefix_reference": "http://purl.org/pav/"},
            "prov": {
                "prefix_prefix": "prov",
                "prefix_reference": "http://www.w3.org/ns/prov#",
            },
            "rdf": {
                "prefix_prefix": "rdf",
                "prefix_reference": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            },
            "rdfs": {
                "prefix_prefix": "rdfs",
                "prefix_reference": "http://www.w3.org/2000/01/rdf-schema#",
            },
            "semapv": {
                "prefix_prefix": "semapv",
                "prefix_reference": "https://w3id.org/semapv/vocab/",
            },
            "skos": {
                "prefix_prefix": "skos",
                "prefix_reference": "http://www.w3.org/2004/02/skos/core#",
            },
            "sssom": {
                "prefix_prefix": "sssom",
                "prefix_reference": "https://w3id.org/sssom/",
            },
            "xsd": {
                "prefix_prefix": "xsd",
                "prefix_reference": "http://www.w3.org/2001/XMLSchema#",
            },
        },
        "see_also": [
            "https://github.com/mapping-commons/sssom",
            "https://mapping-commons.github.io/sssom/home/",
        ],
        "source_file": "/Users/dkapitan/git/plugin-healthcare/sssom-rosetta/.venv/lib/python3.13/site-packages/sssom_schema/schema/sssom_schema.yaml",
        "types": {
            "EntityReference": {
                "base": "str",
                "description": "A reference to an entity involved in the mapping.\n",
                "from_schema": "https://w3id.org/sssom/schema/",
                "name": "EntityReference",
                "see_also": ["https://mapping-commons.github.io/sssom/spec/#tsv"],
                "typeof": "uriorcurie",
                "uri": "rdfs:Resource",
            },
            "NonRelativeURI": {
                "base": "URI",
                "description": "A URI as per RFC 3986, that is a "
                "string that matches the "
                'production of the "URI" rule '
                "defined in Appendix A of that "
                "RFC. Contrary to the underlying "
                "LinkML type, this specifically "
                "excludes _relative URI "
                "references_, which do not start "
                "with a scheme component. "
                "Relative URI references are "
                "forbidden because SSSOM has no "
                "built-in mechanism to provide "
                "the base URI that would be "
                "needed to resolve relative URI "
                "references into non-relative "
                "ones.",
                "examples": [
                    {
                        "description": "A URI that is URL to a HTTP resource.",
                        "value": "https://example.org/path/to/file.txt#L4",
                    },
                    {
                        "description": "A URI that is the "
                        "URN of the "
                        "namespace for the "
                        "OASIS XML Catalogs "
                        "specification.",
                        "value": "urn:oasis:names:tc:entity:xmlns:xml:catalog",
                    },
                    {
                        "description": "A URI that is a LDAP query URL.",
                        "value": "ldap://example.org/cn=Alice,dc=example,dc=org?mail",
                    },
                    {
                        "description": "A URI that is an email address.",
                        "value": "mailto:alice@example.org",
                    },
                    {
                        "description": "An _invalid_ "
                        "example, as it a "
                        "relative URI (path "
                        "only, no scheme).",
                        "value": "file.txt",
                    },
                    {
                        "description": "An _invalid_ "
                        "example; though it "
                        "appears to be an "
                        "_absolute path_, "
                        "it is a _relative "
                        "URI_ because of "
                        "the absence of a "
                        "scheme.",
                        "value": "/path/to/file.txt",
                    },
                    {
                        "description": "An _invalid_ "
                        "example; though it "
                        "includes an "
                        "authority "
                        "component "
                        "(example.org), it "
                        "has no scheme and "
                        "is therefore a "
                        "_relative URI_.",
                        "value": "//example.org/path/to/file.txt",
                    },
                ],
                "from_schema": "https://w3id.org/sssom/schema/",
                "name": "NonRelativeURI",
                "see_also": ["https://github.com/mapping-commons/sssom/issues/448"],
                "typeof": "uri",
                "uri": "xsd:anyURI",
            },
        },
    }
)


class SssomVersionEnum(str, Enum):
    number_1FULL_STOP0 = "1.0"
    """
    SSSOM specification version 1.0
    """
    number_1FULL_STOP1 = "1.1"
    """
    SSSOM specification version 1.1
    """


class EntityTypeEnum(str, Enum):
    owl_class = "owl class"
    owl_object_property = "owl object property"
    owl_data_property = "owl data property"
    owl_annotation_property = "owl annotation property"
    owl_named_individual = "owl named individual"
    skos_concept = "skos concept"
    rdfs_resource = "rdfs resource"
    rdfs_class = "rdfs class"
    rdfs_literal = "rdfs literal"
    """
    This value indicates that the entity being mapped is not a semantic entity with a distinct identifier, but is instead represented entirely by its literal label. This value MUST NOT be used in the predicate_type slot.
    """
    rdfs_datatype = "rdfs datatype"
    rdf_property = "rdf property"
    composed_entity_expression = "composed entity expression"
    """
    This value indicates that the entity ID does not represent a single entity, but a composite involving several individual entities. This value MUST NOT be used in the predicate_type slot. This specifications does not prescribe how an ID representing a composite entity should be interpreted; this is left at the discretion of applications.
    """


class PredicateModifierEnum(str, Enum):
    Not = "Not"
    """
    Negating the mapping predicate. The meaning of the triple becomes subject_id is not a predicate_id match to object_id.
    """


class MappingCardinalityEnum(str, Enum):
    number_1COLON1 = "1:1"
    """
    Indicates the mapping record is about a one-to-one mapping, that is, the subject and the object are only mapped to each other, exclusive of any other subject or object.
    """
    number_1COLONn = "1:n"
    """
    Indicates the mapping record is about a one-to-many mapping, that is, the same subject is mapped to several different objects.
    """
    nCOLON1 = "n:1"
    """
    Indicates the mapping record is about a many-to-one mapping, that is, several different subjects are mapped to the same object.
    """
    nCOLONn = "n:n"
    """
    Indicates the mapping record is about a many-to-many mapping, that is, the subject is mapped to several different objects and the object is mapped to several different subjects.
    """
    number_1COLON0 = "1:0"
    """
    Indicates that the subject has no match in the object vocabulary. This value MUST only be used when the object_id is sssom:NoTermFound.
    """
    number_0COLON1 = "0:1"
    """
    Indicates that the object has no match in the subject vocabulary. This value MUST only be used when the subject_id is sssom:NoTermFound.
    """
    number_0COLON0 = "0:0"
    """
    Indicates that there is no match between the subject vocabulary and the object vocabulary. This value MUST only be used when both the subject_id and the object_id are sssom:NoTermFound.
    """


class MappingSet(ConfiguredBaseModel):
    """
    Represents a set of mappings.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "from_schema": "https://w3id.org/sssom/schema/",
            "slot_usage": {
                "curation_rule": {
                    "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                    "instantiates": ["sssom:Versionable"],
                    "name": "curation_rule",
                },
                "curation_rule_text": {
                    "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                    "instantiates": ["sssom:Versionable"],
                    "name": "curation_rule_text",
                },
                "license": {"name": "license", "required": True},
                "similarity_measure": {
                    "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                    "instantiates": ["sssom:Versionable"],
                    "name": "similarity_measure",
                },
            },
        }
    )

    sssom_version: Optional[SssomVersionEnum] = Field(
        default=None,
        description="""The version of the SSSOM specification a mapping set is compliant with.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping set"],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/439",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/version.sssom.tsv",
                ],
            }
        },
    )
    curie_map: Optional[dict[str, Union[str, Prefix]]] = Field(
        default=None,
        description="""A dictionary that contains prefixes as keys and their URI expansions as values.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/225",
                    "https://github.com/mapping-commons/sssom/pull/349",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curie_map.sssom.tsv",
                ],
            }
        },
    )
    mappings: Optional[list[Mapping]] = Field(
        default=None,
        description="""Contains a list of mapping objects.""",
        json_schema_extra={
            "linkml_meta": {"domain_of": ["mapping set"], "recommended": True}
        },
    )
    mapping_set_id: URI = Field(
        default=...,
        description="""A globally unique identifier for the mapping set (not each individual mapping). Should ideally be resolvable.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping set reference"],
                "examples": [
                    {
                        "description": "A persistent URI pointing to the latest version "
                        "of the Mondo - NCIT mapping in the Mondo "
                        "namespace.",
                        "value": "http://purl.obolibrary.org/obo/mondo/mappings/mondo_exactmatch_ncit.sssom.tsv",
                    }
                ],
            }
        },
    )
    mapping_set_version: Optional[str] = Field(
        default=None,
        description="""A version string for the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set"],
                "examples": [
                    {
                        "description": "A date-based version that indicates that the "
                        "mapping was published on the 1st January in "
                        "2021.",
                        "value": "2020-01-01",
                    },
                    {
                        "description": "(A semantic version tag that indicates that "
                        "this is the 1st major, 2nd minor version, patch "
                        "1 (https://semver.org/).)",
                        "value": "1.2.1",
                    },
                ],
                "slot_uri": "owl:versionInfo",
            }
        },
    )
    mapping_set_source: Optional[list[URI]] = Field(
        default=None,
        description="""A mapping set or set of mapping set that was used to derive the mapping set.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set"],
                "examples": [
                    {
                        "description": "A persistent, ideally versioned, link to the "
                        "mapping set from which the current mapping set "
                        "is derived.",
                        "value": "http://purl.obolibrary.org/obo/mondo/mappings/2022-05-20/mondo_exactmatch_ncit.sssom.tsv",
                    }
                ],
                "slot_uri": "prov:wasDerivedFrom",
            }
        },
    )
    mapping_set_title: Optional[str] = Field(
        default=None,
        description="""The display name of a mapping set.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set"],
                "examples": [
                    {"value": "The Mondo-OMIM mappings by Monarch Initiative."}
                ],
                "slot_uri": "dcterms:title",
            }
        },
    )
    mapping_set_description: Optional[str] = Field(
        default=None,
        description="""A description of the mapping set.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set"],
                "examples": [
                    {
                        "value": "This mapping set was produced to integrate human and "
                        "mouse phenotype data at the IMPC. It is primarily "
                        "used for making mouse phenotypes searchable by human "
                        "synonyms at https://mousephenotype.org/."
                    }
                ],
                "slot_uri": "dcterms:description",
            }
        },
    )
    mapping_set_confidence: Optional[float] = Field(
        default=None,
        description="""Mapping-set level confidence is assigned by the creator of the mapping set to indicate their overall confidence in the correctness (i.e., precision) of mappings in the mapping set. Mapping set confidence is intended to be used in cases were the creator wants to express an overall confidence into the agent that curated the individual mappings, for example a lexical matching tool, or a group of students.
When not explicitly specified, confidence estimation algorithms should consider the mapping set confidence to be 1.0 by default.""",
        ge=0.0,
        le=1.0,
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping set"],
                "examples": [
                    {
                        "description": "A confidence score of 0.95, indicating 95% "
                        "confidence that the mappings in the mapping set "
                        "are correct.",
                        "value": "0.95",
                    }
                ],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/confidence-model",
                    "https://github.com/mapping-commons/sssom/issues/438",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/mapping_set_confidence.sssom.tsv",
                ],
            }
        },
    )
    creator_id: Optional[list[str]] = Field(
        default=None,
        description="""Identifies the persons or groups responsible for the creation of the mapping. The creator is the agent that put the mapping in its published form, which may be different from the author, which is a person that was actively involved in the assertion of the mapping. Recommended to be a list of ORCIDs or otherwise identifying URIs.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The ORCID of the (multiple) creators of the "
                        "mapping. Note that this is how the example "
                        "would look like specifically in the SSSOM/TSV "
                        "format, where multivalued slots such as "
                        "`creator_id` are represented as single strings "
                        "containing `|`-separated values.",
                        "value": "orcid:0000-0002-7356-1779|orcid:0000-0002-6601-2165",
                    },
                    {
                        "description": "The ORCID of the creator of the mapping.",
                        "value": "orcid:0000-0002-7356-1779",
                    },
                ],
                "slot_uri": "dcterms:creator",
            }
        },
    )
    creator_label: Optional[list[str]] = Field(
        default=None,
        description="""A string representing the creator of this mapping. This should only be used in the absence of a proper semantic identifier (which would be stored in creator_id) for that creator. It is not expected that there should be any link between creator_id and creator_label; in particular, creator_label is not intended to provide a human-friendly version of an identifier in creator_id.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The human-readable names of the (multiple) "
                        "creators of the mapping. Note that this is how "
                        "the example would look like specifically in the "
                        "SSSOM/TSV format, where multivalued slots such "
                        "as `creator_label` are represented as single "
                        "strings containing `|`-separated values.",
                        "value": "Nicolas Matentzoglu|Chris Mungall",
                    },
                    {
                        "description": "The human-readable name of the creator of the "
                        "mapping.",
                        "value": "Nicolas Matentzoglu",
                    },
                ],
            }
        },
    )
    license: URI = Field(
        default=...,
        description="""A url to the license of the mapping. In absence of a license we assume no license.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The URI of the Creative Commons Attribution 4.0 "
                        "International license.",
                        "value": "https://creativecommons.org/licenses/by/4.0/",
                    }
                ],
                "slot_uri": "dcterms:license",
            }
        },
    )
    subject_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="""The type of entity that is being mapped.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "owl:Class"}],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    subject_source: Optional[str] = Field(
        default=None,
        description="""URI of vocabulary or identifier source for the subject.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent OBO CURIE pointing to the latest "
                        "version of the Mondo ontology.",
                        "value": "obo:mondo.owl",
                    },
                    {
                        "description": "A Wikidata identifier for the Uberon ontology "
                        "resource.",
                        "value": "wikidata:Q7876491",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    subject_source_version: Optional[str] = Field(
        default=None,
        description="""Version IRI or version string of the source of the subject term.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent Version IRI pointing to the Mondo "
                        "version '2021-01-30'",
                        "value": "http://purl.obolibrary.org/obo/mondo/releases/2021-01-30/mondo.owl",
                    }
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="""The type of entity that is being mapped.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "owl:Class"}],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_source: Optional[str] = Field(
        default=None,
        description="""URI of vocabulary or identifier source for the object.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent OBO CURIE pointing to the latest "
                        "version of the Mondo ontology.",
                        "value": "obo:mondo.owl",
                    },
                    {
                        "description": "A Wikidata identifier for the Uberon ontology "
                        "resource.",
                        "value": "wikidata:Q7876491",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_source_version: Optional[str] = Field(
        default=None,
        description="""Version IRI or version string of the source of the object term.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent Version IRI pointing to the Mondo "
                        "version '2021-01-30'",
                        "value": "http://purl.obolibrary.org/obo/mondo/releases/2021-01-30/mondo.owl",
                    }
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    predicate_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="""The type of the predicate used to map the subject and object entities.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {
                    "added_in": {"tag": "added_in", "value": "1.1"},
                    "propagated": {"tag": "propagated", "value": True},
                },
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {"value": "owl:AnnotationProperty"},
                    {"value": "owl:ObjectProperty"},
                ],
                "instantiates": ["sssom:Propagatable", "sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/143",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/predicate-types.sssom.tsv",
                ],
            }
        },
    )
    mapping_provider: Optional[URI] = Field(
        default=None,
        description="""URL pointing to the source that provided the mapping, for example an ontology that already contains the mappings, or a database from which it was derived.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A URL pointing to the Observational Health Data "
                        "Sciences and Informatics initiative.",
                        "value": "https://www.ohdsi.org/",
                    },
                    {
                        "description": "A URL pointing to the Monarch Initiative "
                        "Resource.",
                        "value": "https://monarchinitiative.org/",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    cardinality_scope: Optional[list[str]] = Field(
        default=None,
        description="""A list of mapping slots that define the scope for the value found in the mapping_cardinality slot. Mappings are considered to belong to the same scope if they have the same value for all slots listed in the scope. If no scope is defined, the default scope is empty, meaning that all mappings belong to a single scope that is identical to the entire mapping set. The behaviour if a value in the list does not correspond to a valid slot name is undefined.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {
                    "added_in": {"tag": "added_in", "value": "1.1"},
                    "propagated": {"tag": "propagated", "value": True},
                },
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "Indicates that mapping_cardinality is computed "
                        "relatively to all mappings that have the same "
                        "predicate.",
                        "value": "predicate_id",
                    },
                    {
                        "description": "Indicates that mapping_cardinality is computed "
                        "relatively to all mappings that have the same "
                        "predicate and the same object source. Note that "
                        "this is how the example would look like "
                        "specifically in the SSSOM/TSV format, where "
                        "multivalued slots like `cardinality_scope` are "
                        "represented as a single string containing "
                        "`|`-separated values.",
                        "value": "predicate_id|object_source",
                    },
                ],
                "instantiates": ["sssom:Propagatable", "sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/467",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/cardinality-scope-predicate.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/cardinality-scope-predicate+object_source.sssom.tsv",
                ],
            }
        },
    )
    mapping_tool: Optional[str] = Field(
        default=None,
        description="""A reference to the tool or algorithm that was used to generate the mapping. Should be a URL pointing to more info about it, but can be free text. Consider using the mapping_tool_id slot for a more standardised reference.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A URL pointing to the AgreementMakerLight "
                        "project.",
                        "value": "https://github.com/AgreementMakerLight/AML-Project",
                    },
                    {
                        "description": "A string (name) denoting the "
                        "AgreementMakerLight project.",
                        "value": "AgreementMakerLight",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    mapping_tool_id: Optional[str] = Field(
        default=None,
        description="""The ID (entity reference) of the tool or algorithm that was used to generate the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {
                    "added_in": {"tag": "added_in", "value": "1.1"},
                    "propagated": {"tag": "propagated", "value": True},
                },
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A wikidata PURL identifying the "
                        "AgreementMakerLight project.",
                        "value": "wikidata:Q58057366",
                    }
                ],
                "instantiates": ["sssom:Propagatable", "sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/mapping_tool_id.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/issues/449",
                ],
            }
        },
    )
    mapping_tool_version: Optional[str] = Field(
        default=None,
        description="""Version string that denotes the version of the mapping tool used.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "v3.2"}],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    mapping_date: Optional[date] = Field(
        default=None,
        description="""The date the mapping was asserted. This is different from the date the mapping was published or compiled in a SSSOM file.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "2021-01-01"}],
                "instantiates": ["sssom:Propagatable"],
                "slot_uri": "dcterms:created",
            }
        },
    )
    publication_date: Optional[date] = Field(
        default=None,
        description="""The date the mapping was published. This is different from the date the mapping was asserted.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "2021-01-01"}],
                "slot_uri": "dcterms:issued",
            }
        },
    )
    subject_match_field: Optional[list[str]] = Field(
        default=None,
        description="""A list of properties, annotations or attributes related to the subject that was used to establish the match. This property is recommended for use in conjunction with  mapping justifications related to lexical matching, such as `semapv:LexicalMatching`.  For additional information see the 'See Also' section.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The RDFS label property (rdfs:label) was used "
                        "to match the subject.",
                        "value": "rdfs:label",
                    },
                    {
                        "description": "The SKOS preferred label property "
                        "(skos:prefLabel) was used to match the subject.",
                        "value": "skos:prefLabel",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/mapping-justifications/#lexical-matching",
                    "https://github.com/mapping-commons/sssom/issues/413",
                ],
            }
        },
    )
    object_match_field: Optional[list[str]] = Field(
        default=None,
        description="""A list of properties, annotations or attributes related to the object that was used to establish the match. This property is recommended for use in conjunction with  mapping justifications related to lexical matching, such as `semapv:LexicalMatching`.  For additional information see the 'See Also' section.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The RDFS label property (rdfs:label) was used "
                        "to match the object.",
                        "value": "rdfs:label",
                    },
                    {
                        "description": "The SKOS preferred label property "
                        "(skos:prefLabel) was used to match the object.",
                        "value": "skos:prefLabel",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/mapping-justifications/#lexical-matching",
                    "https://github.com/mapping-commons/sssom/issues/413",
                ],
            }
        },
    )
    subject_preprocessing: Optional[list[str]] = Field(
        default=None,
        description="""Method of preprocessing applied to the fields of the subject. If different preprocessing steps were performed on different fields, it is recommended to store the match in separate rows.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {"value": "semapv:Stemming"},
                    {"value": "semapv:StopWordRemoval"},
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_preprocessing: Optional[list[str]] = Field(
        default=None,
        description="""Method of preprocessing applied to the fields of the object. If different preprocessing steps were performed on different fields, it is recommended to store the match in separate rows.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {"value": "semapv:Stemming"},
                    {"value": "semapv:StopWordRemoval"},
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    similarity_measure: Optional[str] = Field(
        default=None,
        description="""The measure used for computing a similarity score. This field is meant to be used in conjunction with the similarity_score field, to document, for example, the lexical or semantic match of a matching algorithm. To make processing this field as unambiguous as possible, we recommend using wikidata CURIEs, but the type of this field is deliberately unspecified.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "the Wikidata IRI for the Jaccard index "
                        "measure).",
                        "value": "https://www.wikidata.org/entity/Q865360",
                    },
                    {
                        "description": "the Wikidata CURIE for the Jaccard index "
                        "measure).",
                        "value": "wikidata:Q865360",
                    },
                    {
                        "description": "a score to measure the distance between two "
                        "character sequences).",
                        "value": "Levenshtein distance",
                    },
                ],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/385",
                    "https://github.com/mapping-commons/sssom/pull/386",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/similarity_score.sssom.tsv",
                ],
            }
        },
    )
    curation_rule: Optional[list[str]] = Field(
        default=None,
        description="""A curation rule is a (potentially) complex condition executed by an agent that led to the establishment of a mapping. Curation rules often involve complex domain-specific considerations, which are hard to capture in an automated fashion. The curation rule is captured as a resource rather than a string, which enables higher levels of transparency and sharing across mapping sets. The URI representation of the curation rule is expected to be a resolvable identifier which provides details about the nature of the curation rule.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A reference to the Disease Mapping Commons rule "
                        "with the ID MPR2.",
                        "value": "DISEASE_MAPPING_COMMONS_RULES:MPR2",
                    }
                ],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/166",
                    "https://github.com/mapping-commons/sssom/pull/258",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule-propagated.sssom.tsv",
                ],
            }
        },
    )
    curation_rule_text: Optional[list[str]] = Field(
        default=None,
        description="""A curation rule is a (potentially) complex condition executed by an agent that led to the establishment of a mapping. Curation rules often involve complex domain-specific considerations, which are hard to capture in an automated fashion. The curation rule should be captured as a resource (entity reference) rather than a string (see curation_rule element), which enables higher levels of transparency and sharing across mapping sets. The textual representation of curation rule is intended to be used in cases where the creation of a resource is not practical from the perspective of the mapping_provider.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "value": "The two phenotypes inhere in homologous structures "
                        "and exhibit the same phenotypic quality."
                    },
                    {
                        "value": "The two diseases are used synonymous in the medical "
                        "literature."
                    },
                ],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/166",
                    "https://github.com/mapping-commons/sssom/pull/258",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule_text.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule_text-propagated.sssom.tsv",
                ],
            }
        },
    )
    see_also: Optional[list[URI]] = Field(
        default=None,
        description="""A URL specific for the mapping instance. E.g. for kboom we have a per-mapping image that shows surrounding axioms that drive probability. Could also be a github issue URL that discussed a complicated alignment""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A URL pointing to the pull request that "
                        "introduced the mapping.",
                        "value": "https://github.com/mapping-commons/mh_mapping_initiative/pull/41",
                    }
                ],
                "see_also": ["https://github.com/mapping-commons/sssom/issues/422"],
                "slot_uri": "rdfs:seeAlso",
            }
        },
    )
    issue_tracker: Optional[URI] = Field(
        default=None,
        description="""A URL location of the issue tracker for this entity.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping registry"],
                "examples": [
                    {
                        "description": "A URL resolving to the issue tracker of the "
                        "Mouse-Human mapping initiative",
                        "value": "https://github.com/mapping-commons/mh_mapping_initiative/issues",
                    }
                ],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/78",
                    "https://github.com/mapping-commons/sssom/pull/259",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/issue_tracker.sssom.tsv",
                ],
            }
        },
    )
    other: Optional[str] = Field(
        default=None,
        description="""Pipe separated list of key value pairs for properties not part of the SSSOM spec. Can be used to encode additional provenance data. NOTE. This field is not recommended for general use, and should be used sparingly. See https://github.com/mapping-commons/sssom/blob/master/examples/schema/extension-slots.sssom.tsv for an alternative approach based on extension slots.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping set", "mapping"]}},
    )
    comment: Optional[str] = Field(
        default=None,
        description="""Free text field containing either curator notes or text generated by tool providing additional informative information.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A comment explaining a mapping authors "
                        "reservation on a mapping.",
                        "value": "This mapping is weird in that the hierarchical "
                        "position of the two terms is very different.",
                    }
                ],
                "slot_uri": "rdfs:comment",
            }
        },
    )
    extension_definitions: Optional[list[ExtensionDefinition]] = Field(
        default=None,
        description="""A list that defines the extension slots used in the mapping set.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/328",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/extension-slots.sssom.tsv",
                ],
            }
        },
    )


class Mapping(ConfiguredBaseModel):
    """
    Represents an individual mapping between a pair of entities.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "class_uri": "owl:Axiom",
            "from_schema": "https://w3id.org/sssom/schema/",
            "rules": [
                {
                    "postconditions": {
                        "slot_conditions": {
                            "subject_label": {"name": "subject_label", "required": True}
                        }
                    },
                    "preconditions": {
                        "slot_conditions": {
                            "subject_type": {
                                "equals_string": "rdfs literal",
                                "name": "subject_type",
                            }
                        }
                    },
                },
                {
                    "postconditions": {
                        "slot_conditions": {
                            "subject_id": {"name": "subject_id", "required": True}
                        }
                    },
                    "preconditions": {
                        "slot_conditions": {
                            "subject_type": {
                                "name": "subject_type",
                                "none_of": [{"equals_string": "rdfs literal"}],
                            }
                        }
                    },
                },
                {
                    "postconditions": {
                        "slot_conditions": {
                            "object_label": {"name": "object_label", "required": True}
                        }
                    },
                    "preconditions": {
                        "slot_conditions": {
                            "object_type": {
                                "equals_string": "rdfs literal",
                                "name": "object_type",
                            }
                        }
                    },
                },
                {
                    "postconditions": {
                        "slot_conditions": {
                            "object_id": {"name": "object_id", "required": True}
                        }
                    },
                    "preconditions": {
                        "slot_conditions": {
                            "object_type": {
                                "name": "object_type",
                                "none_of": [{"equals_string": "rdfs literal"}],
                            }
                        }
                    },
                },
                {
                    "description": "If a review date is provided, then at at least one "
                    "of reviewer_id or reviewer_label must also be "
                    "provided",
                    "postconditions": {
                        "any_of": [
                            {
                                "slot_conditions": {
                                    "reviewer_id": {
                                        "name": "reviewer_id",
                                        "required": True,
                                    }
                                }
                            },
                            {
                                "slot_conditions": {
                                    "reviewer_label": {
                                        "name": "reviewer_label",
                                        "required": True,
                                    }
                                }
                            },
                        ]
                    },
                    "preconditions": {
                        "slot_conditions": {
                            "review_date": {"name": "review_date", "required": True}
                        }
                    },
                },
                {
                    "description": "If a reviewer agreement value is provided, then at "
                    "at least one of reviewer_id or reviewer_label must "
                    "also be provided",
                    "postconditions": {
                        "any_of": [
                            {
                                "slot_conditions": {
                                    "reviewer_id": {
                                        "name": "reviewer_id",
                                        "required": True,
                                    }
                                }
                            },
                            {
                                "slot_conditions": {
                                    "reviewer_label": {
                                        "name": "reviewer_label",
                                        "required": True,
                                    }
                                }
                            },
                        ]
                    },
                    "preconditions": {
                        "slot_conditions": {
                            "reviewer_agreement": {
                                "name": "reviewer_agreement",
                                "required": True,
                            }
                        }
                    },
                },
            ],
            "unique_keys": {
                "record_identifier": {
                    "description": "Each mapping within a "
                    "mapping set MAY be "
                    "identified by a unique, "
                    "opaque record "
                    "identifier. This slot "
                    "MUST be used "
                    "consistently, in that "
                    "either all mappings in "
                    "the set have a such a "
                    "record identifier, or "
                    "none of them have one. "
                    "The behaviour when a "
                    "set contains both "
                    "mappings with a record "
                    "identifier and mappings "
                    "without a record "
                    "identifier is "
                    "unspecified. The "
                    "behaviour when two "
                    "mappings have the same "
                    "record identifier is "
                    "unspecified.",
                    "unique_key_name": "record_identifier",
                    "unique_key_slots": ["record_id"],
                }
            },
        }
    )

    record_id: Optional[str] = Field(
        default=None,
        description="""A unique identifier for a mapping record, that is for an instance of the Mapping class (in the SSSOM/TSV serialisation, this corresponds to an individual row after propagation is applied). This slot is intended to uniquely identify one such record within a mapping set and may for example act as the resource identifier for the record when it is serialised into RDF. This slot MUST NOT be used to “group” several records together to indicate that they pertain to a single mapping (for example, that they represent different versions of the same mapping), by assigning the same ID to several records. When it is used, every record within a set MUST have a unique, non-empty value. The identifier MUST be a URI; beyond that, its format is unconstrained and the identifier MUST be treated as an opaque string.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping"],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/359",
                    "https://github.com/mapping-commons/blob/master/examples/schema/record-ids.sssom.tsv",
                ],
            }
        },
    )
    subject_id: Optional[str] = Field(
        default=None,
        description="""The ID of the subject of the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The CURIE denoting the Human Phenotype Ontology "
                        "concept of 'Thickened ears'",
                        "value": "HP:0009894",
                    }
                ],
                "mappings": ["owl:annotatedSource"],
                "slot_uri": "owl:annotatedSource",
            }
        },
    )
    subject_label: Optional[str] = Field(
        default=None,
        description="""The label of subject of the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [{"value": "Thickened ears"}],
                "recommended": True,
            }
        },
    )
    subject_category: Optional[str] = Field(
        default=None,
        description="""The conceptual category to which the subject belongs to. This can be a string denoting the category or a term from a controlled vocabulary. This slot is deliberately underspecified. Conceptual categories can range from those that are found in general upper ontologies such as BFO (e.g. process, temporal region, etc) to those that serve as upper ontologies in specific domains, such as COB or BioLink (e.g. gene, disease, chemical entity). The purpose of this optional field is documentation for human reviewers - when a category is known and documented clearly, the cost of interpreting and evaluating the mapping decreases.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": 'The CURIE of the Uberon term for "anatomical '
                        'entity".',
                        "value": "UBERON:0001062",
                    },
                    {
                        "description": "A string, rather than ID, describing the "
                        '"anatomical entity" category. This is possible, '
                        "but less preferred than using an ID.",
                        "value": "anatomical entity",
                    },
                    {
                        "description": "The CURIE of the biolink class for genes.",
                        "value": "biolink:Gene",
                    },
                ],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/13",
                    "https://github.com/mapping-commons/sssom/issues/256",
                ],
            }
        },
    )
    predicate_id: str = Field(
        default=...,
        description="""The ID of the predicate or relation that relates the subject and object of this match.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The subject and the object are instances (owl "
                        "individuals), and the two instances are the "
                        "same.",
                        "value": "owl:sameAs",
                    },
                    {
                        "description": "The subject and the object are classes (owl "
                        "class), and the two classes are the same.",
                        "value": "owl:equivalentClass",
                    },
                    {
                        "description": "The subject and the object are properties (owl "
                        "object, data, annotation properties), and the "
                        "two properties are the same.",
                        "value": "owl:equivalentProperty",
                    },
                    {
                        "description": "The subject and the object are classes (owl "
                        "class), and the subject is a subclass of the "
                        "object.",
                        "value": "rdfs:subClassOf",
                    },
                    {
                        "description": "The subject and the object are properties (owl "
                        "object, data, annotation properties), and the "
                        "subject is a subproperty of the object.",
                        "value": "rdfs:subPropertyOf",
                    },
                    {
                        "description": "The subject and the object are associated in "
                        "some unspecified way.",
                        "value": "skos:relatedMatch",
                    },
                    {
                        "description": "The subject and the object are sufficiently "
                        "similar that they can be used interchangeably "
                        "in some information retrieval applications.",
                        "value": "skos:closeMatch",
                    },
                    {
                        "description": "The subject and the object can, with a high "
                        "degree of confidence, be used interchangeably "
                        "across a wide range of information retrieval "
                        "applications.",
                        "value": "skos:exactMatch",
                    },
                    {
                        "description": "From the SKOS primer: A triple skos:narrower "
                        "(and skos:narrowMatch) asserts that , the "
                        "object of the triple, is a narrower concept "
                        "than , the subject of the triple.",
                        "value": "skos:narrowMatch",
                    },
                    {
                        "description": "From the SKOS primer: A triple skos:broader "
                        "(and skos:broadMatch) asserts that , the object "
                        "of the triple, is a broader concept than , the "
                        "subject of the triple.",
                        "value": "skos:broadMatch",
                    },
                    {
                        "description": "Two terms are related in some way. The meaning "
                        "is frequently consistent across a single set of "
                        "mappings. Note this property is often "
                        "overloaded even where the terms are of a "
                        "different nature (e.g. interpro2go).",
                        "value": "oboInOwl:hasDbXref",
                    },
                    {
                        "description": "The subject and the object are associated in "
                        "some unspecified way. The object IRI often "
                        "resolves to a resource on the web that provides "
                        "additional information.",
                        "value": "rdfs:seeAlso",
                    },
                ],
                "mappings": ["owl:annotatedProperty"],
                "slot_uri": "owl:annotatedProperty",
            }
        },
    )
    predicate_label: Optional[str] = Field(
        default=None,
        description="""The label of the predicate/relation of the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The label of the oboInOwl:hasDbXref property to "
                        "represent cross-references.",
                        "value": "has cross-reference",
                    }
                ],
            }
        },
    )
    predicate_modifier: Optional[PredicateModifierEnum] = Field(
        default=None,
        description="""A modifier for negating the predicate. See https://github.com/mapping-commons/sssom/issues/40 for discussion""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "Negates the predicate, see documentation of "
                        "predicate_modifier_enum",
                        "value": "Not",
                    }
                ],
                "see_also": ["https://github.com/mapping-commons/sssom/issues/107"],
            }
        },
    )
    object_id: Optional[str] = Field(
        default=None,
        description="""The ID of the object of the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The CURIE denoting the Human Phenotype Ontology "
                        "concept of 'Thickened ears'.",
                        "value": "HP:0009894",
                    }
                ],
                "mappings": ["owl:annotatedTarget"],
                "slot_uri": "owl:annotatedTarget",
            }
        },
    )
    object_label: Optional[str] = Field(
        default=None,
        description="""The label of object of the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [{"value": "Thickened ears"}],
                "recommended": True,
            }
        },
    )
    object_category: Optional[str] = Field(
        default=None,
        description="""The conceptual category to which the subject belongs to. This can be a string denoting the category or a term from a controlled vocabulary. This slot is deliberately underspecified. Conceptual categories can range from those that are found in general upper ontologies such as BFO (e.g. process, temporal region, etc) to those that serve as upper ontologies in specific domains, such as COB or BioLink (e.g. gene, disease, chemical entity). The purpose of this optional field is documentation for human reviewers - when a category is known and documented clearly, the cost of interpreting and evaluating the mapping decreases.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": 'The CURIE of the Uberon term for "anatomical '
                        'entity".',
                        "value": "UBERON:0001062",
                    },
                    {
                        "description": "A string, rather than ID, describing the "
                        '"anatomical entity" category. This is possible, '
                        "but less preferred than using an ID.",
                        "value": "anatomical entity",
                    },
                    {
                        "description": "The CURIE of the biolink class for genes.",
                        "value": "biolink:Gene",
                    },
                ],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/13",
                    "https://github.com/mapping-commons/sssom/issues/256",
                ],
            }
        },
    )
    mapping_justification: str = Field(
        default=...,
        description="""A mapping justification is an action (or the written representation of that action) of showing a mapping to be right or reasonable.""",
        json_schema_extra={
            "linkml_meta": {
                "any_of": [
                    {"equals_string": "semapv:LexicalMatching"},
                    {"equals_string": "semapv:LogicalReasoning"},
                    {"equals_string": "semapv:CompositeMatching"},
                    {"equals_string": "semapv:UnspecifiedMatching"},
                    {"equals_string": "semapv:SemanticSimilarityThresholdMatching"},
                    {"equals_string": "semapv:LexicalSimilarityThresholdMatching"},
                    {"equals_string": "semapv:MappingChaining"},
                    {"equals_string": "semapv:MappingReview"},
                    {"equals_string": "semapv:ManualMappingCuration"},
                    {"equals_string": "semapv:MappingInversion"},
                    {"equals_string": "semapv:StructuralMatching"},
                    {"equals_string": "semapv:InstanceBasedMatching"},
                    {"equals_string": "semapv:BackgroundKnowledgeBasedMatching"},
                ],
                "domain_of": ["mapping"],
                "examples": [
                    {"value": "semapv:LexicalMatching"},
                    {"value": "semapv:ManualMappingCuration"},
                ],
                "see_also": [
                    "https://mapping-commons.github.io/semantic-mapping-vocabulary/",
                    "https://www.ebi.ac.uk/ols4/ontologies/semapv",
                ],
            }
        },
    )
    author_id: Optional[list[str]] = Field(
        default=None,
        description="""Identifies the persons or groups responsible for asserting the mappings. Recommended to be a list of ORCIDs or otherwise identifying URIs.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The ORCID of the (multiple) authors of the "
                        "mapping. Note that this is how the example "
                        "would look like specifically in the SSSOM/TSV "
                        "format, where multivalued slots such as "
                        "`author_id` are represented as single strings "
                        "containing `|`-separated values.",
                        "value": "orcid:0000-0002-7356-1779|orcid:0000-0002-6601-2165",
                    },
                    {
                        "description": "The ORCID of the author of the mapping.",
                        "value": "orcid:0000-0002-7356-1779",
                    },
                ],
                "slot_uri": "pav:authoredBy",
            }
        },
    )
    author_label: Optional[list[str]] = Field(
        default=None,
        description="""A string representing the author of this mapping. This should only be used in the absence of a proper semantic identifier (which would be stored in author_id) for that author. It is not expected that there should be any link between author_id and author_label; in particular, author_label is not intended to provide a human-friendly version of an identifier in author_id.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The human-readable names of the (multiple) "
                        "authors of the mapping. Note that this is how "
                        "the example would look like specifically in the "
                        "SSSOM/TSV format, where multivalued slots such "
                        "as `author_label` are represented as single "
                        "strings containing `|`-separated values.",
                        "value": "Nicolas Matentzoglu|Chris Mungall",
                    },
                    {
                        "description": "The human-readable name of the author of the "
                        "mapping.",
                        "value": "Nicolas Matentzoglu",
                    },
                ],
            }
        },
    )
    reviewer_id: Optional[list[str]] = Field(
        default=None,
        description="""Identifies the persons or groups that reviewed and confirmed the mapping. Recommended to be a list of ORCIDs or otherwise identifying URIs.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The ORCID of the (multiple) reviewers of the "
                        "mapping. Note that this is how the example "
                        "would look like specifically in the SSSOM/TSV "
                        "format, where multivalued slots such as "
                        "`reviewer_id` are represented as single strings "
                        "containing `|`-separated values.",
                        "value": "orcid:0000-0002-7356-1779|orcid:0000-0002-6601-2165",
                    },
                    {
                        "description": "The ORCID of the reviewer of the mapping.",
                        "value": "orcid:0000-0002-7356-1779",
                    },
                ],
            }
        },
    )
    reviewer_label: Optional[list[str]] = Field(
        default=None,
        description="""A string representing the reviewer of this mapping. This should only be used in the absence of a proper semantic identifier (which would be stored in reviewer_id) for that reviewer. It is not expected that there should be any link between reviewer_id and reviewer_label; in particular, reviewer_label is not intended to provide a human-friendly version of an identifier in reviewer_id.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The human-readable names of the (multiple) "
                        "reviewers of the mapping. Note that this is how "
                        "the example would look like specifically in the "
                        "SSSOM/TSV format, where multivalued slots such "
                        "as `reviewer_label` are represented as single "
                        "strings containing `|`-separated values.",
                        "value": "Nicolas Matentzoglu|Chris Mungall",
                    },
                    {
                        "description": "The human-readable name of the reviewer of the "
                        "mapping.",
                        "value": "Nicolas Matentzoglu",
                    },
                ],
            }
        },
    )
    creator_id: Optional[list[str]] = Field(
        default=None,
        description="""Identifies the persons or groups responsible for the creation of the mapping. The creator is the agent that put the mapping in its published form, which may be different from the author, which is a person that was actively involved in the assertion of the mapping. Recommended to be a list of ORCIDs or otherwise identifying URIs.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The ORCID of the (multiple) creators of the "
                        "mapping. Note that this is how the example "
                        "would look like specifically in the SSSOM/TSV "
                        "format, where multivalued slots such as "
                        "`creator_id` are represented as single strings "
                        "containing `|`-separated values.",
                        "value": "orcid:0000-0002-7356-1779|orcid:0000-0002-6601-2165",
                    },
                    {
                        "description": "The ORCID of the creator of the mapping.",
                        "value": "orcid:0000-0002-7356-1779",
                    },
                ],
                "slot_uri": "dcterms:creator",
            }
        },
    )
    creator_label: Optional[list[str]] = Field(
        default=None,
        description="""A string representing the creator of this mapping. This should only be used in the absence of a proper semantic identifier (which would be stored in creator_id) for that creator. It is not expected that there should be any link between creator_id and creator_label; in particular, creator_label is not intended to provide a human-friendly version of an identifier in creator_id.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The human-readable names of the (multiple) "
                        "creators of the mapping. Note that this is how "
                        "the example would look like specifically in the "
                        "SSSOM/TSV format, where multivalued slots such "
                        "as `creator_label` are represented as single "
                        "strings containing `|`-separated values.",
                        "value": "Nicolas Matentzoglu|Chris Mungall",
                    },
                    {
                        "description": "The human-readable name of the creator of the "
                        "mapping.",
                        "value": "Nicolas Matentzoglu",
                    },
                ],
            }
        },
    )
    license: Optional[URI] = Field(
        default=None,
        description="""A url to the license of the mapping. In absence of a license we assume no license.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The URI of the Creative Commons Attribution 4.0 "
                        "International license.",
                        "value": "https://creativecommons.org/licenses/by/4.0/",
                    }
                ],
                "slot_uri": "dcterms:license",
            }
        },
    )
    subject_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="""The type of entity that is being mapped.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "owl:Class"}],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    subject_source: Optional[str] = Field(
        default=None,
        description="""URI of vocabulary or identifier source for the subject.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent OBO CURIE pointing to the latest "
                        "version of the Mondo ontology.",
                        "value": "obo:mondo.owl",
                    },
                    {
                        "description": "A Wikidata identifier for the Uberon ontology "
                        "resource.",
                        "value": "wikidata:Q7876491",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    subject_source_version: Optional[str] = Field(
        default=None,
        description="""Version IRI or version string of the source of the subject term.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent Version IRI pointing to the Mondo "
                        "version '2021-01-30'",
                        "value": "http://purl.obolibrary.org/obo/mondo/releases/2021-01-30/mondo.owl",
                    }
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="""The type of entity that is being mapped.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "owl:Class"}],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_source: Optional[str] = Field(
        default=None,
        description="""URI of vocabulary or identifier source for the object.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent OBO CURIE pointing to the latest "
                        "version of the Mondo ontology.",
                        "value": "obo:mondo.owl",
                    },
                    {
                        "description": "A Wikidata identifier for the Uberon ontology "
                        "resource.",
                        "value": "wikidata:Q7876491",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_source_version: Optional[str] = Field(
        default=None,
        description="""Version IRI or version string of the source of the object term.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A persistent Version IRI pointing to the Mondo "
                        "version '2021-01-30'",
                        "value": "http://purl.obolibrary.org/obo/mondo/releases/2021-01-30/mondo.owl",
                    }
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    predicate_type: Optional[EntityTypeEnum] = Field(
        default=None,
        description="""The type of the predicate used to map the subject and object entities.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {
                    "added_in": {"tag": "added_in", "value": "1.1"},
                    "propagated": {"tag": "propagated", "value": True},
                },
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {"value": "owl:AnnotationProperty"},
                    {"value": "owl:ObjectProperty"},
                ],
                "instantiates": ["sssom:Propagatable", "sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/143",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/predicate-types.sssom.tsv",
                ],
            }
        },
    )
    mapping_provider: Optional[URI] = Field(
        default=None,
        description="""URL pointing to the source that provided the mapping, for example an ontology that already contains the mappings, or a database from which it was derived.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A URL pointing to the Observational Health Data "
                        "Sciences and Informatics initiative.",
                        "value": "https://www.ohdsi.org/",
                    },
                    {
                        "description": "A URL pointing to the Monarch Initiative "
                        "Resource.",
                        "value": "https://monarchinitiative.org/",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    mapping_source: Optional[str] = Field(
        default=None,
        description="""The mapping set this mapping was originally defined in. mapping_source is used for example when merging multiple mapping sets or deriving one mapping set from another.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "A reference to the mapping set that originally "
                        "contained this mapping.",
                        "value": "MONDO_MAPPINGS:mondo_exactmatch_ncit.sssom.tsv",
                    }
                ],
            }
        },
    )
    mapping_cardinality: Optional[MappingCardinalityEnum] = Field(
        default=None,
        description="""A value indicating whether the subject (respectively object) of this mapping record is present in other records involving a different object (respectively subject), within the subset of records defined by the cardinality_scope slot (or within the entire mapping set if cardinality_scope is undefined). Note that this is a convenience field, whose values can always be derived from the mapping set.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "A one-to-one mapping. There are no other "
                        "records in which the same subject is mapped to "
                        "a different object, and no other records in "
                        "which the same object is mapped to a different "
                        "subject.",
                        "value": "1:1",
                    },
                    {
                        "description": "A one-to-many mapping. There are other records "
                        "in which the same subject is mapped to at least "
                        "one different object than the object present in "
                        "this record; there are no other records in "
                        "which the object is mapped to a different "
                        "subject.",
                        "value": "1:n",
                    },
                ],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/cardinality.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/cardinality-with-unmapped-entities.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/cardinality-scope-empty.sssom.tsv",
                ],
            }
        },
    )
    cardinality_scope: Optional[list[str]] = Field(
        default=None,
        description="""A list of mapping slots that define the scope for the value found in the mapping_cardinality slot. Mappings are considered to belong to the same scope if they have the same value for all slots listed in the scope. If no scope is defined, the default scope is empty, meaning that all mappings belong to a single scope that is identical to the entire mapping set. The behaviour if a value in the list does not correspond to a valid slot name is undefined.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {
                    "added_in": {"tag": "added_in", "value": "1.1"},
                    "propagated": {"tag": "propagated", "value": True},
                },
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "Indicates that mapping_cardinality is computed "
                        "relatively to all mappings that have the same "
                        "predicate.",
                        "value": "predicate_id",
                    },
                    {
                        "description": "Indicates that mapping_cardinality is computed "
                        "relatively to all mappings that have the same "
                        "predicate and the same object source. Note that "
                        "this is how the example would look like "
                        "specifically in the SSSOM/TSV format, where "
                        "multivalued slots like `cardinality_scope` are "
                        "represented as a single string containing "
                        "`|`-separated values.",
                        "value": "predicate_id|object_source",
                    },
                ],
                "instantiates": ["sssom:Propagatable", "sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/467",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/cardinality-scope-predicate.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/cardinality-scope-predicate+object_source.sssom.tsv",
                ],
            }
        },
    )
    mapping_tool: Optional[str] = Field(
        default=None,
        description="""A reference to the tool or algorithm that was used to generate the mapping. Should be a URL pointing to more info about it, but can be free text. Consider using the mapping_tool_id slot for a more standardised reference.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A URL pointing to the AgreementMakerLight "
                        "project.",
                        "value": "https://github.com/AgreementMakerLight/AML-Project",
                    },
                    {
                        "description": "A string (name) denoting the "
                        "AgreementMakerLight project.",
                        "value": "AgreementMakerLight",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    mapping_tool_id: Optional[str] = Field(
        default=None,
        description="""The ID (entity reference) of the tool or algorithm that was used to generate the mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {
                    "added_in": {"tag": "added_in", "value": "1.1"},
                    "propagated": {"tag": "propagated", "value": True},
                },
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A wikidata PURL identifying the "
                        "AgreementMakerLight project.",
                        "value": "wikidata:Q58057366",
                    }
                ],
                "instantiates": ["sssom:Propagatable", "sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/mapping_tool_id.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/issues/449",
                ],
            }
        },
    )
    mapping_tool_version: Optional[str] = Field(
        default=None,
        description="""Version string that denotes the version of the mapping tool used.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "v3.2"}],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    mapping_date: Optional[date] = Field(
        default=None,
        description="""The date the mapping was asserted. This is different from the date the mapping was published or compiled in a SSSOM file.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "2021-01-01"}],
                "instantiates": ["sssom:Propagatable"],
                "slot_uri": "dcterms:created",
            }
        },
    )
    publication_date: Optional[date] = Field(
        default=None,
        description="""The date the mapping was published. This is different from the date the mapping was asserted.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [{"value": "2021-01-01"}],
                "slot_uri": "dcterms:issued",
            }
        },
    )
    review_date: Optional[date] = Field(
        default=None,
        description="""The date the mapping was reviewed. This is different from the date the mapping was asserted and published. If this field is used in a mapping, reviewer_id and/or reviewer_label MUST also be be set.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping"],
                "examples": [{"value": "2021-01-01"}],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/511",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/review_date.sssom.tsv",
                ],
            }
        },
    )
    confidence: Optional[float] = Field(
        default=None,
        description="""A value assigned by the creator of the mapping to denote the creator's confidence or estimated probability that the mapping record is correct. A value of 1.0 means the creator has full confidence in the correctness of the mapping record, while a value of 0.0 means the creator is fully unsure whether the mapping record is correct or not.
When not explicitly specified, confidence estimation algorithms should consider the mapping confidence to be 1.0 by default.""",
        ge=0.0,
        le=1.0,
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "A confidence score of 0.95, indicating 95% "
                        "confidence.",
                        "value": "0.95",
                    }
                ],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/confidence-model"
                ],
            }
        },
    )
    reviewer_agreement: Optional[float] = Field(
        default=None,
        description="""A value assigned by the reviewer of the mapping to denote their confidence that the mapping record is correct. A value of 1.0 means the reviewer fully agrees with the mapping record. A value of -1.0 means the reviewer fully disagrees with the mapping record. A value of 0.0 means the reviewer is not sure whether the mapping record is correct or not.
When not explicitly specified, confidence estimation algorithms should consider the reviewer agreement to be 1.0 by default.""",
        ge=-1.0,
        le=1.0,
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"added_in": {"tag": "added_in", "value": "1.1"}},
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "A reviewer agreement of 1.0 denotes that the "
                        "reviewer considers the mapping record to be "
                        "correct with full confidence",
                        "value": "1.0",
                    },
                    {
                        "description": "A reviewer agreement of -1.0 denotes that the "
                        "reviewer considers the mapping record to be "
                        "incorrect with full confidence",
                        "value": "-1.0",
                    },
                    {
                        "description": "A reviewer agreement of 0.0 denotes that the "
                        "reviewer is not sure whether the mapping record "
                        "is correct or not.",
                        "value": "0.0",
                    },
                ],
                "instantiates": ["sssom:Versionable"],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/confidence-model",
                    "https://github.com/mapping-commons/sssom/issues/510",
                    "https://github.com/mapping-commons/sssom/pull/519",
                ],
            }
        },
    )
    curation_rule: Optional[list[str]] = Field(
        default=None,
        description="""A curation rule is a (potentially) complex condition executed by an agent that led to the establishment of a mapping. Curation rules often involve complex domain-specific considerations, which are hard to capture in an automated fashion. The curation rule is captured as a resource rather than a string, which enables higher levels of transparency and sharing across mapping sets. The URI representation of the curation rule is expected to be a resolvable identifier which provides details about the nature of the curation rule.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A reference to the Disease Mapping Commons rule "
                        "with the ID MPR2.",
                        "value": "DISEASE_MAPPING_COMMONS_RULES:MPR2",
                    }
                ],
                "instantiates": ["sssom:Propagatable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/166",
                    "https://github.com/mapping-commons/sssom/pull/258",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule-propagated.sssom.tsv",
                ],
            }
        },
    )
    curation_rule_text: Optional[list[str]] = Field(
        default=None,
        description="""A curation rule is a (potentially) complex condition executed by an agent that led to the establishment of a mapping. Curation rules often involve complex domain-specific considerations, which are hard to capture in an automated fashion. The curation rule should be captured as a resource (entity reference) rather than a string (see curation_rule element), which enables higher levels of transparency and sharing across mapping sets. The textual representation of curation rule is intended to be used in cases where the creation of a resource is not practical from the perspective of the mapping_provider.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "value": "The two phenotypes inhere in homologous structures "
                        "and exhibit the same phenotypic quality."
                    },
                    {
                        "value": "The two diseases are used synonymous in the medical "
                        "literature."
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/166",
                    "https://github.com/mapping-commons/sssom/pull/258",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule_text.sssom.tsv",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/curation_rule_text-propagated.sssom.tsv",
                ],
            }
        },
    )
    subject_match_field: Optional[list[str]] = Field(
        default=None,
        description="""A list of properties, annotations or attributes related to the subject that was used to establish the match. This property is recommended for use in conjunction with  mapping justifications related to lexical matching, such as `semapv:LexicalMatching`.  For additional information see the 'See Also' section.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The RDFS label property (rdfs:label) was used "
                        "to match the subject.",
                        "value": "rdfs:label",
                    },
                    {
                        "description": "The SKOS preferred label property "
                        "(skos:prefLabel) was used to match the subject.",
                        "value": "skos:prefLabel",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/mapping-justifications/#lexical-matching",
                    "https://github.com/mapping-commons/sssom/issues/413",
                ],
            }
        },
    )
    object_match_field: Optional[list[str]] = Field(
        default=None,
        description="""A list of properties, annotations or attributes related to the object that was used to establish the match. This property is recommended for use in conjunction with  mapping justifications related to lexical matching, such as `semapv:LexicalMatching`.  For additional information see the 'See Also' section.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "The RDFS label property (rdfs:label) was used "
                        "to match the object.",
                        "value": "rdfs:label",
                    },
                    {
                        "description": "The SKOS preferred label property "
                        "(skos:prefLabel) was used to match the object.",
                        "value": "skos:prefLabel",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/mapping-justifications/#lexical-matching",
                    "https://github.com/mapping-commons/sssom/issues/413",
                ],
            }
        },
    )
    match_string: Optional[list[str]] = Field(
        default=None,
        description="""String that is shared by subj/obj. It is recommended to indicate the fields for the match using the object and subject_match_field slots.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "The 'gala' string was matched for both subject "
                        "and object.",
                        "value": "gala",
                    }
                ],
            }
        },
    )
    subject_preprocessing: Optional[list[str]] = Field(
        default=None,
        description="""Method of preprocessing applied to the fields of the subject. If different preprocessing steps were performed on different fields, it is recommended to store the match in separate rows.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {"value": "semapv:Stemming"},
                    {"value": "semapv:StopWordRemoval"},
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    object_preprocessing: Optional[list[str]] = Field(
        default=None,
        description="""Method of preprocessing applied to the fields of the object. If different preprocessing steps were performed on different fields, it is recommended to store the match in separate rows.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {"value": "semapv:Stemming"},
                    {"value": "semapv:StopWordRemoval"},
                ],
                "instantiates": ["sssom:Propagatable"],
            }
        },
    )
    similarity_score: Optional[float] = Field(
        default=None,
        description="""A score between 0 and 1 to denote the similarity between two entities, where 1 denotes equivalence, and 0 denotes disjointness. The score is meant to be used in conjunction with the similarity_measure field, to document, for example, the lexical or semantic match of a matching algorithm.""",
        ge=0.0,
        le=1.0,
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "A similarity score of 0.95, indicating 95% "
                        "similarity.",
                        "value": "0.95",
                    }
                ],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/385",
                    "https://github.com/mapping-commons/sssom/pull/386",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/similarity_score.sssom.tsv",
                ],
            }
        },
    )
    similarity_measure: Optional[str] = Field(
        default=None,
        description="""The measure used for computing a similarity score. This field is meant to be used in conjunction with the similarity_score field, to document, for example, the lexical or semantic match of a matching algorithm. To make processing this field as unambiguous as possible, we recommend using wikidata CURIEs, but the type of this field is deliberately unspecified.""",
        json_schema_extra={
            "linkml_meta": {
                "annotations": {"propagated": {"tag": "propagated", "value": True}},
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "the Wikidata IRI for the Jaccard index "
                        "measure).",
                        "value": "https://www.wikidata.org/entity/Q865360",
                    },
                    {
                        "description": "the Wikidata CURIE for the Jaccard index "
                        "measure).",
                        "value": "wikidata:Q865360",
                    },
                    {
                        "description": "a score to measure the distance between two "
                        "character sequences).",
                        "value": "Levenshtein distance",
                    },
                ],
                "instantiates": ["sssom:Propagatable"],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/385",
                    "https://github.com/mapping-commons/sssom/pull/386",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/similarity_score.sssom.tsv",
                ],
            }
        },
    )
    see_also: Optional[list[URI]] = Field(
        default=None,
        description="""A URL specific for the mapping instance. E.g. for kboom we have a per-mapping image that shows surrounding axioms that drive probability. Could also be a github issue URL that discussed a complicated alignment""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A URL pointing to the pull request that "
                        "introduced the mapping.",
                        "value": "https://github.com/mapping-commons/mh_mapping_initiative/pull/41",
                    }
                ],
                "see_also": ["https://github.com/mapping-commons/sssom/issues/422"],
                "slot_uri": "rdfs:seeAlso",
            }
        },
    )
    issue_tracker_item: Optional[str] = Field(
        default=None,
        description="""The issue tracker item discussing this mapping.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping"],
                "examples": [
                    {
                        "description": "A URL resolving to an issue discussing a new "
                        "SSSOM element request",
                        "value": "SSSOM_GITHUB_ISSUE:166",
                    }
                ],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/78",
                    "https://github.com/mapping-commons/sssom/pull/259",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/issue_tracker_item.sssom.tsv",
                ],
            }
        },
    )
    other: Optional[str] = Field(
        default=None,
        description="""Pipe separated list of key value pairs for properties not part of the SSSOM spec. Can be used to encode additional provenance data. NOTE. This field is not recommended for general use, and should be used sparingly. See https://github.com/mapping-commons/sssom/blob/master/examples/schema/extension-slots.sssom.tsv for an alternative approach based on extension slots.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping set", "mapping"]}},
    )
    comment: Optional[str] = Field(
        default=None,
        description="""Free text field containing either curator notes or text generated by tool providing additional informative information.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping"],
                "examples": [
                    {
                        "description": "A comment explaining a mapping authors "
                        "reservation on a mapping.",
                        "value": "This mapping is weird in that the hierarchical "
                        "position of the two terms is very different.",
                    }
                ],
                "slot_uri": "rdfs:comment",
            }
        },
    )

    @field_validator("mapping_justification")
    def pattern_mapping_justification(cls, v):
        pattern = re.compile(
            r"^semapv:(MappingReview|ManualMappingCuration|LogicalReasoning|LexicalMatching|CompositeMatching|UnspecifiedMatching|SemanticSimilarityThresholdMatching|LexicalSimilarityThresholdMatching|MappingChaining|MappingInversion|StructuralMatching|InstanceBasedMatching|BackgroundKnowledgeBasedMatching)$"
        )
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid mapping_justification format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid mapping_justification format: {v}"
            raise ValueError(err_msg)
        return v


class MappingRegistry(ConfiguredBaseModel):
    """
    A registry for managing mapping sets. It holds a set of mapping set references, and can import other registries.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://w3id.org/sssom/schema/"}
    )

    mapping_registry_id: str = Field(
        default=...,
        description="""The unique identifier of a mapping registry.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping registry"]}},
    )
    mapping_registry_title: Optional[str] = Field(
        default=None,
        description="""The title of a mapping registry.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping registry"]}},
    )
    mapping_registry_description: Optional[str] = Field(
        default=None,
        description="""The description of a mapping registry.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping registry"]}},
    )
    imports: Optional[list[URI]] = Field(
        default=None,
        description="""A list of registries that should be imported into this one.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping registry"]}},
    )
    mapping_set_references: Optional[list[MappingSetReference]] = Field(
        default=None,
        description="""A list of mapping set references.""",
        json_schema_extra={
            "linkml_meta": {"domain_of": ["mapping registry"], "recommended": True}
        },
    )
    documentation: Optional[URI] = Field(
        default=None,
        description="""A URL to the documentation of this mapping commons.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping registry"]}},
    )
    homepage: Optional[URI] = Field(
        default=None,
        description="""A URL to a homepage of this mapping commons.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping registry"]}},
    )
    issue_tracker: Optional[URI] = Field(
        default=None,
        description="""A URL location of the issue tracker for this entity.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping registry"],
                "examples": [
                    {
                        "description": "A URL resolving to the issue tracker of the "
                        "Mouse-Human mapping initiative",
                        "value": "https://github.com/mapping-commons/mh_mapping_initiative/issues",
                    }
                ],
                "see_also": [
                    "https://github.com/mapping-commons/sssom/issues/78",
                    "https://github.com/mapping-commons/sssom/pull/259",
                    "https://github.com/mapping-commons/sssom/blob/master/examples/schema/issue_tracker.sssom.tsv",
                ],
            }
        },
    )


class MappingSetReference(ConfiguredBaseModel):
    """
    A reference to a mapping set. It allows to augment mapping set metadata from the perspective of the registry, for example, providing confidence, or a local filename or a grouping.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://w3id.org/sssom/schema/"}
    )

    mapping_set_id: URI = Field(
        default=...,
        description="""A globally unique identifier for the mapping set (not each individual mapping). Should ideally be resolvable.""",
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set", "mapping set reference"],
                "examples": [
                    {
                        "description": "A persistent URI pointing to the latest version "
                        "of the Mondo - NCIT mapping in the Mondo "
                        "namespace.",
                        "value": "http://purl.obolibrary.org/obo/mondo/mappings/mondo_exactmatch_ncit.sssom.tsv",
                    }
                ],
            }
        },
    )
    mirror_from: Optional[URI] = Field(
        default=None,
        description="""A URL location from which to obtain a resource, such as a mapping set.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping set reference"]}},
    )
    registry_confidence: Optional[float] = Field(
        default=None,
        description="""This value is set by the creator/maintainer of the mapping registry and reflects the confidence the mapping registry has in the correctness (i.e., precision) of mappings in the mapping set.
When not explicitly specified, confidence estimation algorithms should consider the registry confidence in a mapping set to be 1.0 by default.""",
        ge=0.0,
        le=1.0,
        json_schema_extra={
            "linkml_meta": {
                "domain_of": ["mapping set reference"],
                "examples": [
                    {
                        "description": "A confidence score of 0.95, indicating 95% "
                        "confidence.",
                        "value": "0.95",
                    }
                ],
                "see_also": [
                    "https://mapping-commons.github.io/sssom/confidence-model"
                ],
            }
        },
    )
    mapping_set_group: Optional[str] = Field(
        default=None,
        description="""Set by the owners of the mapping registry. A way to group related mapping sets for example for UI purposes.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping set reference"]}},
    )
    last_updated: Optional[date] = Field(
        default=None,
        description="""The date this reference was last updated.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping set reference"]}},
    )
    local_name: Optional[str] = Field(
        default=None,
        description="""The local name assigned to file that corresponds to the downloaded mapping set.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["mapping set reference"]}},
    )


class Prefix(ConfiguredBaseModel):
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://w3id.org/sssom/schema/"}
    )

    prefix_name: str = Field(
        default=..., json_schema_extra={"linkml_meta": {"domain_of": ["prefix"]}}
    )
    prefix_url: Optional[str] = Field(
        default=None, json_schema_extra={"linkml_meta": {"domain_of": ["prefix"]}}
    )


class ExtensionDefinition(ConfiguredBaseModel):
    """
    A definition of an extension (non-standard) slot.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {"from_schema": "https://w3id.org/sssom/schema/"}
    )

    slot_name: str = Field(
        default=...,
        description="""The name of the extension slot.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["extension definition"]}},
    )
    property: Optional[str] = Field(
        default=None,
        description="""The property associated with the extension slot. It is intended to provide a non-ambiguous meaning to the slot (contrary to the slot_name, which for brevity reasons may be ambiguous).""",
        json_schema_extra={"linkml_meta": {"domain_of": ["extension definition"]}},
    )
    type_hint: Optional[str] = Field(
        default=None,
        description="""Expected type of the values of the extension slot.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["extension definition"]}},
    )


class Propagatable(ConfiguredBaseModel):
    """
    Metamodel extension class to describe slots whose value can be propagated down from the MappingSet class to the Mapping class.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "class_uri": "sssom:Propagatable",
            "from_schema": "https://w3id.org/sssom/schema/",
            "see_also": ["https://github.com/mapping-commons/sssom/issues/305"],
        }
    )

    propagated: Optional[bool] = Field(
        default=None,
        description="""Indicates whether a slot can be propagated from a mapping down to individual mappings.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Propagatable"]}},
    )


class Versionable(ConfiguredBaseModel):
    """
    Metamodel extension class to manage slots that may not exist in all versions of the model.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "class_uri": "sssom:Versionable",
            "from_schema": "https://w3id.org/sssom/schema/",
        }
    )

    added_in: Optional[SssomVersionEnum] = Field(
        default=None,
        description="""The version of the specification in which the slot was added. If not specified, the slot must be assumed to have been added in version 1.0.""",
        json_schema_extra={"linkml_meta": {"domain_of": ["Versionable"]}},
    )


class NoTermFound(ConfiguredBaseModel):
    """
    sssom:NoTermFound can be used in place of a subject_id or object_id when the corresponding entity could not be found. It SHOULD be used in conjunction with a corresponding subject_source or object_source to signify where the term was not found.
    """

    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta(
        {
            "class_uri": "sssom:NoTermFound",
            "from_schema": "https://w3id.org/sssom/schema/",
            "see_also": [
                "https://github.com/mapping-commons/sssom/issues/28",
                "https://github.com/mapping-commons/sssom/blob/master/examples/schema/no_term_found.sssom.tsv",
            ],
        }
    )

    pass


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
MappingSet.model_rebuild()
Mapping.model_rebuild()
MappingRegistry.model_rebuild()
MappingSetReference.model_rebuild()
Prefix.model_rebuild()
ExtensionDefinition.model_rebuild()
Propagatable.model_rebuild()
Versionable.model_rebuild()
NoTermFound.model_rebuild()
