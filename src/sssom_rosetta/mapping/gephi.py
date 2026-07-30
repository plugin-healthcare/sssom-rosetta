"""Export combined RDF graphs to GEXF for exploring in Gephi (https://gephi.org).

Two graphs in this project are worth visualising in Gephi, and are exported
separately (see ``.agents/plan/2026-07-28-gephi-gexf-export.md``):

- the **ontology** graph: OMOP CDM + ONZ-G source ontologies plus the
  hand-authored ``mappings/*.csv`` mapping set (:func:`build_ontology_graph`);
- the **vocabulary** graph: the merged source-vocabulary graph produced by
  ``rosetta vocabulary merge`` (:func:`build_vocabulary_graph`).

Conversion pipeline: ``rdflib.Graph`` -> filtered to a small set of
structural/mapping predicates for edges -> ``networkx.MultiDiGraph`` (via
``rdflib.extras.external_graph_libs.rdflib_to_networkx_multidigraph``) ->
``networkx.write_gexf``. This mirrors the *approach* of
`rdf2gephi <https://github.com/sparna-git/rdf2gephi>`_ (which predicates
matter for edges vs. attributes) without taking on its JVM dependency:
``rdflib``/``networkx`` are both pure-Python packages already used
elsewhere in this project (or, for ``networkx``, added specifically for
this GEXF export).

``rdfs:label`` is deliberately *not* included as an edge predicate: its
object is a ``Literal``, not a resource, so treating it as an edge would
create a standalone graph node for the label string itself. Labels (and
every other literal-valued property on a node) are instead captured as
node **attributes** by :func:`_node_attributes`, so curators can inspect a
node's full metadata in Gephi's Data Laboratory, not just its position in
the graph.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx
from rdflib import Graph, Literal, URIRef
from rdflib.extras.external_graph_libs import rdflib_to_networkx_multidigraph
from rdflib.namespace import RDF, RDFS, SKOS

from sssom_rosetta.mapping.io import mapping_set_to_graph

if TYPE_CHECKING:
    from pathlib import Path

    from rdflib.term import Node

    from sssom_rosetta.models.sssom import MappingSet

#: Every SKOS mapping predicate, shared by both graph types below.
SKOS_MAPPING_PREDICATES: frozenset[URIRef] = frozenset(
    {
        SKOS.exactMatch,
        SKOS.closeMatch,
        SKOS.broadMatch,
        SKOS.narrowMatch,
        SKOS.relatedMatch,
    }
)

#: Predicates included as edges when exporting the combined ontology graph
#: (OMOP CDM + ONZ-G + the authored mapping set): the ontology hierarchy
#: plus all SKOS mapping predicates.
ONTOLOGY_PREDICATES: frozenset[URIRef] = SKOS_MAPPING_PREDICATES | {RDFS.subClassOf}

#: Predicates included as edges when exporting the combined vocabulary graph
#: (``rosetta vocabulary merge``'s output): SKOS mapping predicates only.
#: OMOP's ``Is a``/``Subsumes`` relationships are already mapped to
#: ``skos:broadMatch``/``narrowMatch`` (see ``vocabulary/omop.py``), so the
#: vocabulary's hierarchy is captured by the SKOS predicates alone.
VOCABULARY_PREDICATES: frozenset[URIRef] = SKOS_MAPPING_PREDICATES


def _qname(graph: Graph, term: Node) -> str:
    """Return the CURIE for a URI, e.g. ``skos:prefLabel`` (or ``onz-g:Person``)."""
    return graph.namespace_manager.qname(str(term))


def _attribute_key(graph: Graph, term: Node) -> str:
    """Return a GEXF-attribute-friendly name for a URI, e.g. ``skos_prefLabel``."""
    return _qname(graph, term).replace(":", "_")


def _relevant_triples(graph: Graph, predicates: frozenset[URIRef]) -> Graph:
    """Return a new graph containing only triples whose predicate is in ``predicates``.

    These are the structural/mapping edges worth visualising in Gephi;
    without this filter, every triple (including literal-valued metadata
    triples) would be converted into an edge, burying the structure in
    noise.
    """
    filtered = Graph()
    for prefix, namespace in graph.namespace_manager.namespaces():
        filtered.bind(prefix, namespace)
    for subject, predicate, obj in graph:
        if predicate in predicates:
            filtered.add((subject, predicate, obj))
    return filtered


def _node_attributes(graph: Graph, node: URIRef) -> dict[str, str]:
    """Collect every literal-valued property of ``node`` as GEXF node attributes.

    No allowlist: any literal-valued predicate present on the node (e.g.
    ``rdfs:label``, ``skos:prefLabel``, ``skos:altLabel``,
    ``skos:notation``, ``skos:definition``, ``rdfs:comment``, ...) becomes
    its own attribute, keyed by its CURIE (e.g. ``skos_prefLabel``). When a
    predicate has multiple values, they are joined with ``"; "`` so each
    attribute stays single-valued, as GEXF requires. Every value is
    stringified: ``networkx.write_gexf`` infers each attribute's GEXF type
    from the first value it sees for that key across the whole graph and
    raises if a later node supplies a different Python type for the same
    key, so keeping everything as ``str`` avoids type clashes regardless of
    which predicates happen to be present on any given node.

    Also derives:
        ``type``: the CURIE(s) of the node's ``rdf:type``(s).
        ``label``: ``skos:prefLabel`` (preferred) or ``rdfs:label``,
            falling back to the node's own CURIE -- used by Gephi as
            the on-canvas node caption.
        ``source``: the CURIE prefix of the node's own URI (e.g. ``omop``,
            ``onz-g``, ``sct``), so nodes can be partitioned/coloured by
            origin ontology/vocabulary in Gephi's Appearance panel.
    """
    values_by_key: dict[str, list[str]] = {}
    type_names: list[str] = []
    for predicate, obj in graph.predicate_objects(subject=node):
        if predicate == RDF.type:
            if isinstance(obj, URIRef):
                type_names.append(_qname(graph, obj))
            continue
        if isinstance(obj, Literal):
            key = _attribute_key(graph, predicate)
            values_by_key.setdefault(key, []).append(str(obj))

    attributes = {key: "; ".join(values) for key, values in values_by_key.items()}

    if type_names:
        attributes["type"] = "; ".join(sorted(set(type_names)))

    pref_label_key = _attribute_key(graph, SKOS.prefLabel)
    rdfs_label_key = _attribute_key(graph, RDFS.label)
    label_values = values_by_key.get(pref_label_key) or values_by_key.get(rdfs_label_key)
    attributes["label"] = label_values[0] if label_values else _qname(graph, node)

    attributes["source"] = _qname(graph, node).split(":", 1)[0]

    return attributes


def to_networkx(graph: Graph, predicates: frozenset[URIRef]) -> nx.MultiDiGraph:
    """Convert ``graph`` into a ``networkx.MultiDiGraph`` ready for GEXF export.

    Edges come only from triples whose predicate is in ``predicates``
    (see :func:`_relevant_triples`); node attributes are drawn from the
    *full*, unfiltered ``graph`` (see :func:`_node_attributes`), so metadata
    is captured even for predicates that aren't edge-worthy.
    """
    filtered = _relevant_triples(graph, predicates)

    def edge_attrs(s: URIRef, p: URIRef, o: URIRef) -> dict[str, str]:  # noqa: ARG001
        key = _attribute_key(filtered, p)
        return {"label": key, "predicate": key}

    multidigraph = rdflib_to_networkx_multidigraph(filtered, edge_attrs=edge_attrs)
    for node in multidigraph.nodes:
        if isinstance(node, URIRef):
            multidigraph.nodes[node].update(_node_attributes(graph, node))
    return multidigraph


def write_gexf(graph: Graph, output_path: Path, *, predicates: frozenset[URIRef]) -> None:
    """Convert ``graph`` to ``networkx`` and serialize it to ``output_path`` as GEXF."""
    multidigraph = to_networkx(graph, predicates)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_gexf(multidigraph, output_path, version="1.3")


def build_ontology_graph(
    graph: Graph,
    output_path: Path,
    *,
    predicates: frozenset[URIRef] = ONTOLOGY_PREDICATES,
) -> None:
    """Write the combined ontology graph (OMOP CDM + ONZ-G + mappings) as GEXF.

    ``graph`` is expected to already be the merged graph produced by
    :func:`build_combined_ontology_graph` -- the ontology triples plus the
    mapping set's *flat* SKOS triples (``skos:exactMatch`` etc.), not the
    OWL-restriction axioms ``mapping.protege.build_combined_graph`` emits
    for Protege/OntoGraf (``owl:equivalentClass``/blank-node restrictions
    aren't in ``ONTOLOGY_PREDICATES`` and would make every mapping edge
    silently disappear from the export).
    """
    write_gexf(graph, output_path, predicates=predicates)


def build_combined_ontology_graph(
    mapping_set: MappingSet, prefix_map: dict[str, str], subject_graph: Graph, object_graph: Graph
) -> Graph:
    """Merge both ontology graphs with the mapping set's *flat* SKOS triples.

    Unlike ``mapping.protege.build_combined_graph`` (which represents each
    mapping as an OWL class-level axiom for Protege/OntoGraf), this keeps
    each mapping as one flat ``subject_id predicate_id object_id`` triple
    (via ``mapping.io.mapping_set_to_graph``) so its predicate is a literal
    ``skos:exactMatch``/``broadMatch``/etc. IRI that ``ONTOLOGY_PREDICATES``
    (and Gephi) can match directly as an edge -- no OWL DL semantics needed
    for a force-directed layout.
    """
    combined = Graph()
    for source in (subject_graph, object_graph):
        for prefix, namespace in source.namespace_manager.namespaces():
            combined.bind(prefix, namespace)
        combined += source
    combined += mapping_set_to_graph(mapping_set, prefix_map=prefix_map)
    return combined


def build_vocabulary_graph(
    ttl_path: Path,
    output_path: Path,
    *,
    predicates: frozenset[URIRef] = VOCABULARY_PREDICATES,
) -> None:
    """Load a merged vocabulary Turtle file and write it as GEXF.

    ``ttl_path`` is normally ``build/vocabularies/rosetta-vocabularies.ttl``,
    produced by ``rosetta vocabulary merge``. No assembly is needed here --
    that graph is already fully merged.
    """
    graph = Graph()
    graph.parse(str(ttl_path), format="turtle")
    write_gexf(graph, output_path, predicates=predicates)
