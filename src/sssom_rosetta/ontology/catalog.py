"""Query helpers over a loaded ontology ``rdflib.Graph``.

These are read-only lookups used both by mapping authoring (to resolve and
validate CURIEs/IRIs against a source ontology) and by validation (to check
referential integrity of a mapping set). Nothing here fetches or caches
data; callers pass in a graph already produced by ``ontology.loader``.
"""

from __future__ import annotations

from rdflib import RDF, RDFS, Graph, URIRef
from rdflib.namespace import OWL, SKOS

_CLASS_TYPES = (OWL.Class, RDFS.Class)
_PROPERTY_TYPES = (
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.AnnotationProperty,
    RDF.Property,
)
_LABEL_PREDICATES = (RDFS.label, SKOS.prefLabel)


def list_classes(graph: Graph) -> list[str]:
    """Return the sorted IRIs of every class declared in the graph.

    A resource is considered a class if it is the subject of an
    ``rdf:type`` triple whose object is ``owl:Class`` or ``rdfs:Class``.
    """
    iris: set[str] = set()
    for class_type in _CLASS_TYPES:
        for subject in graph.subjects(RDF.type, class_type):
            if isinstance(subject, URIRef):
                iris.add(str(subject))
    return sorted(iris)


def list_properties(graph: Graph) -> list[str]:
    """Return the sorted IRIs of every property declared in the graph.

    A resource is considered a property if it is the subject of an
    ``rdf:type`` triple whose object is ``owl:ObjectProperty``,
    ``owl:DatatypeProperty``, ``owl:AnnotationProperty``, or ``rdf:Property``.
    """
    iris: set[str] = set()
    for property_type in _PROPERTY_TYPES:
        for subject in graph.subjects(RDF.type, property_type):
            if isinstance(subject, URIRef):
                iris.add(str(subject))
    return sorted(iris)


def resolve_label(graph: Graph, iri: str) -> str | None:
    """Return a human-readable label for ``iri``, or ``None`` if unresolved.

    Tries ``rdfs:label`` first, then ``skos:prefLabel``. If the graph has
    several labels for the same predicate (e.g. in different languages),
    the first one encountered is returned; callers that need
    language-specific labels should query the graph directly.
    """
    subject = URIRef(iri)
    for predicate in _LABEL_PREDICATES:
        for label in graph.objects(subject, predicate):
            return str(label)
    return None


def resource_exists(graph: Graph, iri: str) -> bool:
    """Return True if ``iri`` appears as a subject or object anywhere in the graph.

    Used for referential integrity checks: a mapping's ``subject_id``/
    ``object_id`` should resolve to *something* the ontology describes, not
    necessarily a declared class or property (e.g. it could be an
    individual, or a term only ever used as an object of ``rdfs:subClassOf``).
    """
    resource = URIRef(iri)
    return (resource, None, None) in graph or (None, None, resource) in graph
