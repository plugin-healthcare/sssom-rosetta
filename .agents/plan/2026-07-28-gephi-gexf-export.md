# Plan: Gephi (.gexf) export — ontology and vocabulary graphs

## Problem

Curators want to explore this project's RDF graphs in
[Gephi](https://gephi.org) (force-directed layouts, degree/partition
colouring, community detection) — capabilities the current viewers
(Protégé/OntoGraf, GraphDB) don't offer. Gephi doesn't read RDF; it reads
[GEXF](https://gexf.net) (Graph Exchange XML Format).

The project actually has **two distinct combined graphs**, built by two
separate pipelines, that curators want to see separately rather than as one
undifferentiated export:

1. **The combined ontology graph**: OMOP CDM + ONZ-G source ontologies plus
   the hand-authored `mappings/omop-onz-g.csv` mapping set (same inputs as
   `rosetta protege build`).
2. **The combined vocabulary graph**: `build/vocabularies/
   rosetta-vocabularies.ttl`, produced by `rosetta vocabulary merge`.
   Today this is OMOP-only (`build/vocabularies/omop.ttl`), but the roadmap
   (README "Roadmap": Z-Index, DHD Diagnosethesaurus, DHD
   Verrichtingenthesaurus) adds more vocabularies, each contributing their
   own `skos:exactMatch`/`broadMatch`/`narrowMatch` mappings into the same
   merged graph (see `vocabulary/merge.py`, `vocabulary/omop.py`). This
   graph has no relationship to the `mappings/*.csv` authored mapping sets
   or the OMOP-CDM/ONZ-G ontologies — it is a different subject domain
   (source vocabularies/terminologies, not the OMOP CDM data model).

Conflating the two into a single `.gexf` would mix unrelated identifier
spaces and mapping predicates in one hairball; keeping them separate lets
each be explored (and coloured/partitioned) on its own terms.

[`sparna-git/rdf2gephi`](https://github.com/sparna-git/rdf2gephi) already
solves RDF→GEXF conversion, using SPARQL queries to define edges, node
labels, and node attributes. However, it is a Java CLI (`java -jar
rdf2gephi-x.y-onejar.jar ...`). This repo has **zero** Java/JVM or
subprocess-to-external-binary dependencies today — everything runs through
`uv`/Python (see `README.md`'s "Key dependencies"). Shelling out to a
downloaded jar would require: bundling/pinning a JRE requirement, a
jar-fetch-and-checksum step mirroring `ontology/loader.py`, and a new
"how to install Java" section in the README — a heavy addition for one
output format.

## Decision: `rdflib` → `networkx` → GEXF, no JVM dependency

Evaluated complexity of a native reimplementation vs. wrapping the jar:

- **RDF → graph object**: `rdflib.extras.external_graph_libs.rdflib_to_networkx_graph`
  (or `..._multidigraph` — see step 2) converts an `rdflib.Graph` directly
  into a `networkx` graph, one call, no SPARQL query-writing needed.
  `rdflib` is already a hard dependency (`pyproject.toml`).
- **GEXF serialization**: `networkx.readwrite.gexf.write_gexf` writes a
  `networkx` graph straight to `.gexf`
  (https://networkx.org/documentation/stable/reference/readwrite/generated/networkx.readwrite.gexf.write_gexf.html).
  This needs `networkx` as a new runtime dependency (pure Python, no JVM,
  no compiled extensions — a lightweight, well-maintained addition
  consistent with the project's other pure-Python deps).
- **Scope actually needed**: both graphs only need a subset of their
  triples as edges — the structural/hierarchy predicates plus the SKOS
  mapping predicates — not every triple (annotations would otherwise bury
  the structural edges as noise). Filter the `rdflib.Graph` down to the
  relevant triples *before* calling `rdflib_to_networkx_graph` (see step
  2), using a **module-level constant per graph type** rather than one
  shared hardcoded set, since the two graphs' relevant predicates differ
  and may need independent tuning later:
  - the ontology graph's default constant includes `rdfs:subClassOf`
    (ontology hierarchy) in addition to all SKOS mapping predicates;
  - the vocabulary graph's default constant includes only the SKOS mapping
    predicates — it has no `rdfs:subClassOf` hierarchy of its own; OMOP's
    `Is a`/`Subsumes` relationships are already mapped to
    `skos:broadMatch`/`narrowMatch` (see `vocabulary/omop.py`), so the
    hierarchy is captured by the SKOS predicates alone.
  `rdfs:label` is deliberately **excluded** from both edge-predicate sets:
  its object is a `Literal`, not a resource, so treating it as an edge
  would make `rdflib_to_networkx_multidigraph` create a standalone node for
  the label *string* with an edge into it — a degree-1 "phantom" node that
  isn't part of the real graph structure, and unconventional for how Gephi
  graphs are normally modelled (entities and relationships between them,
  not entities and their own text metadata). Labels (and all other
  metadata) belong on the node as **attributes**, not as separate nodes —
  see the expanded node-attribute pass below.

Net assessment: delegating both the RDF→graph conversion and the GEXF
serialization to `rdflib`/`networkx` utilities is simpler and lower-
maintenance than either hand-writing GEXF XML or wrapping rdf2gephi's Java
jar, and keeps the project JVM-free while adding one small, pure-Python
dependency (`networkx`).

## Design: two entry points, one shared conversion core

Add `src/sssom_rosetta/mapping/gephi.py` with:

- **Configuration constants**: two module-level `frozenset[URIRef]`
  constants declaring which predicates are included as **edges** by
  default — `ONTOLOGY_PREDICATES` (`rdfs:subClassOf` plus all SKOS mapping
  predicates) and `VOCABULARY_PREDICATES` (all SKOS mapping predicates
  only). Built from one shared `SKOS_MAPPING_PREDICATES` constant
  (`skos:exactMatch`, `skos:closeMatch`, `skos:broadMatch`,
  `skos:narrowMatch`, `skos:relatedMatch`) so the two don't drift
  independently:
  ```python
  SKOS_MAPPING_PREDICATES: frozenset[URIRef] = frozenset({
      SKOS.exactMatch, SKOS.closeMatch, SKOS.broadMatch,
      SKOS.narrowMatch, SKOS.relatedMatch,
  })
  ONTOLOGY_PREDICATES: frozenset[URIRef] = SKOS_MAPPING_PREDICATES | {
      RDFS.subClassOf,
  }
  VOCABULARY_PREDICATES: frozenset[URIRef] = SKOS_MAPPING_PREDICATES
  ```
  `rdfs:label` is not in either set — see "Scope actually needed" above
  for why (it becomes a node attribute instead, alongside every other
  piece of literal metadata — see the node-attribute pass below).
  Both `build_ontology_graph` and `build_vocabulary_graph` accept an
  optional `predicates: frozenset[URIRef]` parameter defaulting to their
  respective constant, so callers/tests can override the edge scope
  without editing the module.
- **Shared core** (used by both): `_relevant_triples`, `to_networkx`,
  `write_gexf` — generic over any `rdflib.Graph` and an explicit
  `predicates` argument, no knowledge of where the graph came from.
- **`build_combined_ontology_graph(...)`** + **`build_ontology_graph(...)`**:
  the former assembles the OMOP CDM + ONZ-G ontology graphs with the
  mapping set's triples; the latter converts the result to GEXF.
  Deliberately **not** a reuse of `mapping.protege.build_combined_graph`:
  that function represents each mapping as an OWL class-level axiom
  (`owl:equivalentClass`, or an `owl:Restriction` blank node) so Protege/
  OntoGraf render it as a structural class relationship — but neither
  `owl:equivalentClass` nor the restriction pattern is in
  `ONTOLOGY_PREDICATES`, so reusing it would silently drop every mapping
  edge from the Gephi export. `build_combined_ontology_graph` instead keeps
  each mapping as one flat `subject_id predicate_id object_id` triple (via
  a new `mapping.io.mapping_set_to_graph` helper, extracted from
  `write_ttl`) so its predicate is a literal `skos:exactMatch`/
  `broadMatch`/etc. IRI — exactly what `ONTOLOGY_PREDICATES` matches, and
  the same shape the vocabulary graph already uses. `build_ontology_graph`
  then calls `write_gexf` with `predicates=ONTOLOGY_PREDICATES` by default.
- **`build_vocabulary_graph(...)`**: loads `build/vocabularies/
  rosetta-vocabularies.ttl` (or whichever vocabulary `.ttl` is passed in —
  forward-compatible with more vocabularies landing in that same merged
  file per the roadmap) and calls `write_gexf` with
  `predicates=VOCABULARY_PREDICATES` by default. No mapping-set CSV, no
  ontology cache involved — this graph is already fully merged by
  `rosetta vocabulary merge`.

Exposed as two CLI subcommands and two `justfile` recipes (steps 4/6 below)
so curators can build/open either graph independently, e.g. `just
gephi-ontology` vs. `just gephi-vocabulary`.

## Steps

1. **Dependency** (`gephi-dependency`)
   Add `networkx>=3,<4` (pure Python, no compiled/JVM deps) to
   `pyproject.toml`'s `dependencies` and to the "Key dependencies" list in
   `README.md`.

2. **Shared graph-filtering + conversion core** (`gephi-conversion`,
   depends on step 1)
   Add `src/sssom_rosetta/mapping/gephi.py`:
   - the `SKOS_MAPPING_PREDICATES` / `ONTOLOGY_PREDICATES` /
     `VOCABULARY_PREDICATES` constants described in "Design" above.
   - `_relevant_triples(graph: rdflib.Graph, predicates:
     frozenset[URIRef]) -> rdflib.Graph`: filters any combined
     `rdflib.Graph` down to triples whose predicate is in `predicates` —
     the structural edges worth visualising. No graph-type-specific logic
     here; callers pass `ONTOLOGY_PREDICATES` or `VOCABULARY_PREDICATES`
     (or an override) explicitly.
   - `to_networkx(graph: rdflib.Graph, predicates: frozenset[URIRef]) ->
     networkx.MultiDiGraph`: calls `_relevant_triples`, then
     `rdflib.extras.external_graph_libs.rdflib_to_networkx_multidigraph`
     on the filtered graph, with an `edge_attrs` callback that records the
     predicate's CURIE/local name as the edge's `label`/`predicate`
     attribute, then a **node-attribute pass over the full, unfiltered
     graph** (not just the filtered edge subgraph, so metadata is captured
     even for predicates that aren't edge-worthy) via
     `_node_attributes(graph, node) -> dict[str, str]`:
     - iterates every `(predicate, obj)` pair from
       `graph.predicate_objects(subject=node)` where `obj` is a
       `rdflib.Literal` (e.g. `rdfs:label`, `skos:prefLabel`,
       `skos:altLabel`, `skos:notation`, `skos:definition`,
       `rdfs:comment`, `dc:description`, and any other literal-valued
       property present — no allowlist, so new metadata predicates on
       either ontology or vocabulary are picked up automatically) and adds
       one GEXF attribute per distinct predicate, keyed by its CURIE/local
       name (e.g. `skos_prefLabel`, `rdfs_comment`);
     - also handles `rdf:type` (object is a URI, not a literal) as its own
       `type` attribute;
     - when a predicate has multiple values for the same node (e.g.
       several `skos:altLabel`s), joins them into one string with `"; "`
       so each GEXF attribute stays single-valued per node, as the format
       requires;
     - **stringifies every attribute value** (`str(literal)`), because
       `networkx.write_gexf` infers each attribute's GEXF type from the
       first value it sees for that key and raises/misbehaves if later
       nodes supply a different Python type for the same key — using
       strings throughout keeps every node consistent regardless of which
       predicates happen to be present on it;
     - sets a human-friendly `label` attribute from
       `COALESCE(skos:prefLabel, rdfs:label)` (falling back to the URI's
       local name if neither is present), used by Gephi as the on-canvas
       node caption, in addition to (not instead of) the raw
       `skos_prefLabel`/`rdfs_label` attributes above;
     - adds the `source` attribute so nodes can be partitioned/coloured by
       origin in Gephi:
     - for the ontology graph, `"omop-cdm"` / `"onz-g"` (derived from which
       ontology namespace the node's URI belongs to);
     - for the vocabulary graph, the OMOP `vocabulary_id`/native namespace
       (`"SNOMED"`, `"LOINC"`, `"omop"`, etc. — derived from the node's URI
       prefix per `vocabulary/namespaces.py`'s `PREFIX_MAP`, so it stays
       correct as more vocabularies are added).
   - `write_gexf(graph: rdflib.Graph, output_path: Path, *, predicates:
     frozenset[URIRef]) -> None`: calls `to_networkx(graph, predicates)`,
     creates `output_path`'s parent directory, then calls
     [`networkx.readwrite.gexf.write_gexf`](https://networkx.org/documentation/stable/reference/readwrite/generated/networkx.readwrite.gexf.write_gexf.html)
     (re-exported as `networkx.write_gexf`) with `version="1.3"`
     (the current, non-deprecated GEXF version `networkx` supports) to serialize the `MultiDiGraph`
     straight to `output_path`.

3. **Two graph-assembly functions** (`gephi-assembly`, depends on step 2)
   In the same module:
   - `build_combined_ontology_graph(mapping_set, prefix_map, subject_graph,
     object_graph) -> rdflib.Graph`: merges the two ontology graphs with the
     mapping set's **flat** SKOS triples (via a new
     `mapping.io.mapping_set_to_graph` helper extracted from `write_ttl` —
     *not* `mapping.protege.build_combined_graph`'s OWL-restriction axioms,
     which `ONTOLOGY_PREDICATES` can't match; see "Design" above).
     `build_ontology_graph(graph, output_path, *, predicates:
     frozenset[URIRef] = ONTOLOGY_PREDICATES) -> None` then calls
     `write_gexf` on the assembled graph.
   - `build_vocabulary_graph(ttl_path: Path, output_path: Path, *,
     predicates: frozenset[URIRef] = VOCABULARY_PREDICATES) -> None`:
     `rdflib.Graph().parse(...)` over the pre-merged vocabulary Turtle file
     (no assembly needed since `vocabulary_merge` already did it), then
     calls `write_gexf`.

4. **CLI commands** (`gephi-cli`, depends on step 3)
   Add a `gephi_app = typer.Typer(...)` sub-app registered as
   `app.add_typer(gephi_app, name="gephi")`, with two commands:
   - `rosetta gephi build-ontology` (options mirroring `protege_build`:
     `csv_path`, `metadata_path`, `mapping_set_id`, `license`, `curie_map`,
     `subject_source`, `object_source`, `cache_dir`, and `--output-path`
     defaulting to `build/gephi/omop-onz-g.gexf`) — assembles the mapping
     set + ontology graphs via `build_combined_ontology_graph`, then calls
     `build_ontology_graph(..., predicates=ONTOLOGY_PREDICATES,
     output_path=output_path)`.
   - `rosetta gephi build-vocabulary` (`--input-path` defaulting to
     `build/vocabularies/rosetta-vocabularies.ttl`, `--output-path`
     defaulting to `build/gephi/rosetta-vocabularies.gexf`) — calls
     `build_vocabulary_graph(input_path, predicates=VOCABULARY_PREDICATES,
     output_path=output_path)`; errors clearly (matching
     `vocabulary_merge`'s existing style) if the input file doesn't exist
     yet, pointing at `rosetta vocabulary merge`.
   Neither command exposes a `--predicates` CLI flag (see "Out of scope");
   the constants are code-level configuration, not user-facing options.
   Both print the output path on success, matching existing command
   conventions.

5. **Tests** (`gephi-tests`, depends on steps 2–4)
   - `tests/mapping/test_gephi.py`: assert `ONTOLOGY_PREDICATES` contains
     `rdfs:subClassOf` and all of `SKOS_MAPPING_PREDICATES` but **not**
     `rdfs:label`, and `VOCABULARY_PREDICATES` equals exactly
     `SKOS_MAPPING_PREDICATES` (pins the defaults the task specifies).
     Small fixture `rdflib.Graph` (2–3 classes across two
     "ontologies"/vocabularies, 2–3 mappings, and several literal-valued
     metadata triples per node — e.g. `rdfs:label`, `skos:prefLabel`,
     `skos:altLabel` (repeated), `skos:notation`, `rdfs:comment` — plus
     some irrelevant triples to prove edge-filtering works) asserting:
     - `to_networkx` produces the expected node/edge counts for each
       predicate set, with **no phantom literal nodes** for `rdfs:label`
       (proving it stays out of the edge set);
     - every node in the resulting graph carries an attribute for each
       distinct literal predicate present on it in the source graph
       (`rdfs_label`, `skos_prefLabel`, `rdfs_comment`, etc.), a joined
       `"; "`-separated `skos_altLabel` when multiple values exist, a
       `label` attribute (from `COALESCE(skos:prefLabel, rdfs:label)`), a
       `type` attribute, and a `source` attribute;
     - all attribute values are `str` (proving the stringification that
       keeps `networkx.write_gexf` from choking on mixed types across
       nodes);
     - `write_gexf` produces a file `networkx.read_gexf` can parse back
       with matching node/edge counts *and* matching attribute values
       (round-trip test).
     Cover both the ontology-shaped fixture (with `rdfs:subClassOf`,
     filtered with `ONTOLOGY_PREDICATES`) and the vocabulary-shaped
     fixture (`skos:broadMatch`/`narrowMatch` only, no `subClassOf`,
     filtered with `VOCABULARY_PREDICATES`), since they exercise the same
     filter/convert code with different edge-predicate sets but the same
     full-metadata node-attribute pass. Also test an explicit
     `predicates=` override to prove the parameter, not just the constant,
     is honoured.
   - `tests/test_cli.py`: invoke both `rosetta gephi build-ontology`
     (against fixture ontologies + mapping CSVs) and `rosetta gephi
     build-vocabulary` (against a small fixture vocabulary `.ttl`),
     asserting each `.gexf` file is written and `networkx.read_gexf` can
     load it. Also assert `build-vocabulary` exits non-zero with a helpful
     message when the input `.ttl` is missing.

6. **`justfile` recipes** (`gephi-justfile`, depends on step 4)
   Add, near the `protege` recipe:
   ```just
   # Build the combined ontology Gephi export (build/gephi/).
   gephi-ontology:
       uv run rosetta gephi build-ontology {{ mapping_csv }} {{ mapping_metadata }} \
           --mapping-set-id "{{ mapping_set_id }}" \
           --license "{{ mapping_license }}" \
           --curie-map '{{ curie_map }}'

   # Build the combined vocabulary Gephi export (build/gephi/).
   gephi-vocabulary:
       uv run rosetta gephi build-vocabulary
   ```
   Add `gephi-ontology` to the `build-all` recipe's dependency list
   (alongside `protege`), so `just build-all` also refreshes the ontology
   `.gexf` export. Do **not** add `gephi-vocabulary` to `build-all` —
   mirroring why `vocab-*` recipes are excluded (README: licence-gated
   source ZIPs, curator-driven ingestion), it can only run after `just
   vocab-build` has produced `rosetta-vocabularies.ttl`.

7. **README documentation** (`gephi-readme`, depends on step 4)
   Add an "Exploring the graphs in Gephi" subsection (peer to "Protégé as a
   viewer") under "Architecture & technical details", covering:
   - the two separate exports and why they're kept separate: `just
     gephi-ontology` → `build/gephi/omop-onz-g.gexf` (OMOP CDM + ONZ-G +
     the authored mapping set) vs. `just gephi-vocabulary` → `build/gephi/
     rosetta-vocabularies.gexf` (the merged source-vocabulary graph from
     `rosetta vocabulary merge` — grows as more vocabularies, e.g.
     Z-Index/DHD, are integrated per the Roadmap),
   - the conversion pipeline: `rdflib.Graph` → filtered to structural
     triples for edges → `rdflib_to_networkx_multidigraph` →
     `networkx.write_gexf`, crediting
     [rdf2gephi](https://github.com/sparna-git/rdf2gephi) as the
     inspiration for which edges/attributes matter, without taking on its
     JVM dependency,
   - **every node carries its full literal metadata as GEXF attributes**
     (not just a label) — every `skos:*`/`rdfs:*` literal property present
     on a concept (`prefLabel`, `altLabel`, `notation`, `definition`,
     `comment`, etc.) is exposed as its own attribute, plus `type` and
     `source`, so curators can inspect a node's underlying data directly
     in Gephi's Data Laboratory / node inspector, not just its position in
     the graph,
   - opening either file in Gephi (File > Open) and the typical next steps
     (Force Atlas 2 layout, Appearance > Nodes > Partition on the `source`
     or `type` attribute, Data Laboratory to browse per-node attributes,
     Statistics > Modularity for clustering) per rdf2gephi's own "Typical
     actions in Gephi" guidance,
   - the new `networkx` entry in "Key dependencies".

## Out of scope (deferred)

- Dynamic/time-sliced graphs — no temporal data in the current mapping
  model, and `networkx`/GEXF dynamic-graph support would need bespoke
  attribute wiring.
- Arbitrary SPARQL-endpoint or multi-file directory input — this repo
  always has exactly one combined graph per pipeline to export.
- A single unified export mixing both graphs — rejected by design (see
  "Problem"): the ontology and vocabulary graphs are different subject
  domains with unrelated identifier spaces.
- Configurable edge/attribute selection via CLI flags — `ONTOLOGY_PREDICATES`
  / `VOCABULARY_PREDICATES` are module-level constants (overridable via the
  `predicates` function parameter for tests/programmatic reuse), but no
  `--predicates` CLI flag is added until a concrete need for per-invocation
  overrides arises (YAGNI).
