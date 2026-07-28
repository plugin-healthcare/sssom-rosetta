# Plan: Jelly serialization + in-memory SPARQL (maplib) — benchmarked, Jelly reverted

**Status:** Trialled on `feat/rdf-optimization`, benchmarked against the real
Athena-derived `build/vocabularies/omop.ttl` (19,843,930 triples, 908.6MB),
then **backed out**. The Jelly hypothesis (smaller on-disk footprint) was
**not confirmed** by the real-data benchmark — see "Results" below — so
`pyjelly` was removed again and Turtle remains the project's only
serialization format; no `--format` option was added to the CLI. The maplib
hypothesis (fast in-memory SPARQL) **was confirmed** and exceeded
expectations, and **maplib is kept** as a dev dependency for the SPARQL
benchmark script (see `scripts/benchmark_sparql.py`); it is not yet wired
into any CLI command or consumer.

## Problem

`rosetta vocabulary build-omop` / `merge` build the vocabulary graph with
`rdflib.Graph` — pure-Python triples, in-memory dict-of-dicts storage,
Turtle serialization via Python string formatting. On the real Athena release
this pipeline takes minutes to build+serialize `omop.ttl` and produces a
~900MB-1GB Turtle file per graph, with **no query capability** short of
reloading the whole file into another rdflib graph (slow) or standing up a
separate triple store — which is why `.agents/design/2027-07-21-choice-of-
backend.md` proposes QLever as a SPARQL layer, adding an operated server
process to an otherwise file-based, `uv`-only pipeline.

This plan evaluated two concrete improvements without changing the project's
"no JVM/server dependency, everything through `uv`" posture:

1. **Smaller on-disk footprint** — trial **Jelly** (via `pyjelly`, which
   integrates directly with rdflib's `serialize()`/`parse()`) as the
   artifact format alongside/instead of Turtle.
2. **In-memory SPARQL over the merged graph** — trial **maplib** (Rust/Arrow,
   `pip install maplib`) as the query engine, as an alternative to standing
   up QLever for the "single node, embedded, no server" use case.

## What was implemented, benchmarked, then reverted (Jelly)

- Added `pyjelly[rdflib]` as a dependency; a new `serialize.py` module with
  `write_graph`/`read_graph` dispatching Turtle vs. Jelly by format/suffix;
  `write_jelly()` alongside `write_ttl()` in `omop.py`/`loinc_snomed.py`/
  `snomed_international.py`; a Jelly-aware `merge_ttl_files`; and a CLI
  `--format {turtle,jelly,both}` option on the vocabulary build/merge
  commands.
- Benchmarked against the real, full-scale graph (see "Results" below) —
  Jelly measured **larger on disk, worse under gzip, and slower to parse
  back** than Turtle for this project's data.
- **Reverted all of the above**: `pyjelly` was removed from
  `pyproject.toml`, `serialize.py` was deleted, and `omop.py`/
  `loinc_snomed.py`/`snomed_international.py`/`merge.py`/`cli.py` were
  restored to their pre-trial state (Turtle-only, no `--format` option).
  This plan and the benchmark numbers are kept as the documented reason not
  to re-attempt this without new evidence (e.g. a future non-0.x pyjelly
  release, or a grouped-streaming write path).

## What was kept (maplib)

- `maplib` added as a **dev** dependency (`pyproject.toml`) — used only by
  the benchmark script below, not wired into any `rosetta` CLI command or
  application code yet.
- `scripts/benchmark_sparql.py` (new): reproducible benchmark — parses a
  Turtle graph with rdflib, loads the same file into a `maplib.Model`, and
  times four representative SPARQL queries against both. Run it with
  `uv run python scripts/benchmark_sparql.py [path/to/graph.ttl]`.

## Results (measured on `build/vocabularies/omop.ttl`, 19,843,930 triples)

### Serialization (Jelly — hypothesis not confirmed)

| Metric | Turtle | Jelly (default preset) | Jelly (tuned preset*) |
|---|---|---|---|
| File size | 908.6MB | 1.1GB (**119%** of Turtle) | 1.1GB (**119%**) |
| gzip'd size | **111.8MB** | 483.5MB (4.3× larger) | 483.6MB |
| rdflib parse (read back) | 360s | — | 797s (**2.2× slower**) |
| rdflib serialize (write) | (baseline, included in build) | 236s | 208s |

\* Tuned = `LookupPreset(max_names=4096, ...)`, the wire format's hard cap
(pyjelly raises `JellyAssertionError` above 4096 — this is a protocol limit,
not just a tuning knob). Tuning made no measurable difference at this scale.

**Jelly was larger on disk, compressed far worse, and was slower for rdflib
to parse back than Turtle**, contradicting the initial hypothesis. Root
cause, most likely: Jelly's "more compact than Turtle" claim on
jelly-rdf.github.io is benchmarked on the **JVM implementation's grouped
RDF-dataset/graph streaming** profile (many small graphs/frames sharing a
dictionary) — not a single flat triple-stream write through **pyjelly's
current (v0.8.0, pre-1.0) Python integration**, which is what
`rdflib.Graph.serialize(format="jelly")` actually exercises. Separately,
Turtle's compact syntax (`;`/`,`-grouped predicates per subject, shared
`@prefix` declarations) produces highly repetitive text that gzip's LZ77
handles very well; Jelly's binary varint/protobuf-style framing is already
higher-entropy and gzip barely helps.

**Consequence:** the CLI's `--format` option defaults to `turtle`, not
`both`/`jelly` as originally planned. Jelly stays available as an **opt-in**
format for interop with other Jelly-consuming tools (Apache Jena, RDF4J via
jelly-jvm) — genuinely useful for that purpose — but is not recommended as
this project's default or preferred artifact.

### SPARQL (maplib — hypothesis confirmed, exceeded expectations)

| Query | rdflib | maplib | Speedup |
|---|---|---|---|
| Bulk load (Turtle) | 360.35s | 78.43s | **4.6×** |
| `SELECT (COUNT(*))` over all triples | 138.85s | 0.69s | **≈201×** |
| `COUNT(?s) WHERE { ?s a skos:Concept }` | 17.34s | 0.09s | **≈193×** |
| `broadMatch` sample (`LIMIT 20`) | 0.01s | 0.00s | both negligible |
| exact `prefLabel` lookup | 0.00s | 0.00s | both negligible |

These are **larger** speedups than the Trainmarks blog's 10M-triple numbers
(≈20× load, ≈2,270× on one aggregation query), on a comparably-sized graph
(19.8M triples) with this project's actual SKOS/OMOP data and query shapes —
i.e. the maplib hypothesis holds up on real data, not just the cited
benchmark.

## Recommendation (revised after benchmarking)

1. **Do not adopt Jelly at all — `pyjelly` has been removed as a
   dependency.** Turtle remains the project's only vocabulary serialization
   format, with no `--format` option on the CLI. The above numbers are kept
   as the documented reason not to re-add it casually. Revisit only if/when
   `pyjelly` matures past 0.x and/or gains grouped-streaming support that
   might change these numbers — and re-run
   `scripts/benchmark_sparql.py`-style benchmarking on real data before
   re-adopting, not before.
2. **Adopt maplib for querying the merged graph.** It decisively beats
   rdflib for both bulk load and SPARQL query on this project's real data,
   confirming it as a credible embedded, zero-extra-process alternative to
   standing up QLever for the "single node, no server" workload described in
   `.agents/design/2027-07-21-choice-of-backend.md` §3 Option B. That design
   doc's open questions (§6) should be updated to reflect this evidence when
   the OMOPHub API (or first live-SPARQL consumer) is built — this plan
   stops at "benchmarked, evidence-based recommendation," not "wired into a
   consumer," matching how that doc is already framed ("deliberately does
   not choose").
3. **rdflib stays** for graph *construction* (`omop.py::build_graph`,
   `loinc_snomed.py`, `snomed_international.py`) — those triple-add loops are
   a one-time cost per release and rdflib's ergonomics (typed `URIRef`/
   `Literal`, `RDF`/`SKOS` namespace constants) are still the best fit for
   that code. Only the serialize/parse and query boundaries are affected by
   this plan.

## Risks / open questions (updated)

- **maplib's SHACL/Datalog features are proprietary**; only mapping,
  querying, and serialization are open source (Apache 2.0) — confirmed
  sufficient for our needs (plain SPARQL SELECT/CONSTRUCT).
- **maplib has no native Jelly support yet** (on its roadmap) — moot for now
  since Jelly isn't the recommended artifact format either.
- **pyjelly is pre-1.0 (v0.8.0)** and, per the benchmark above, currently
  slower to parse and larger on disk than Turtle for this project's graph
  shape — treat any future re-evaluation as needing a fresh benchmark run
  with `scripts/benchmark_rdf_serialization.py`, not an assumption that a
  version bump alone fixes this.
- **Don't over-rotate on the Trainmarks blog numbers as a substitute for
  project-specific benchmarking** — this plan is the cautionary example:
  the Jelly compactness claim, taken from JVM-benchmark marketing copy
  without verifying against this project's actual pyjelly/rdflib code path,
  did not hold up. The maplib claim did hold up, independently verified here.
