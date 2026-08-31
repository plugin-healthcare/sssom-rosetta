# Plan: rebuild the OMOP graph construction step on maplib/OTTR

**Date:** 2026-07-30 (revised after critical review, same day)
**Status:** Implemented
**Scope:** Replace the rdflib triple-add loop in
`src/sssom_rosetta/vocabulary/omop.py::build_graph` with a **maplib** (OTTR
template) mapping, keeping everything else about the pipeline unchanged: one
`build/vocabularies/omop.ttl` output, the same six target vocabularies, the
same `Maps to`/`Is a`/`Subsumes` → SKOS predicate mapping, no `CONCEPT_ANCESTOR`
processing.

**Related:**
- `.agents/plan/2026-07-21-add-snomed-loinc-omop-vocabularies.md` (original
  OMOP vocabulary pipeline design; this plan only touches its Phase 3
  construction step)
- `.agents/plan/2026-07-28-jelly-maplib-serialization-and-sparql.md`
  (benchmarked maplib for **querying** a pre-built Turtle graph; this plan
  extends maplib's role to **construction** — see §5 "Relationship to the
  prior maplib decision")

---

## 0. Revision note (this document supersedes the 2026-07-30 draft)

An earlier draft of this plan proposed switching to maplib/OTTR **and**
partitioning the graph by `domain_id` into multiple `omop-<domain>.ttl`
files, plus adding `CONCEPT_ANCESTOR` ingestion. A critical review against
the OHDSI *Book of OHDSI* "Standardized Vocabularies" chapter found that
domain-based chunking doesn't match how OMOP actually assigns domains
(heuristic, per-concept, only guaranteed singular for Standard Concepts;
`standard_concept` — not `domain_id` — is the more fundamental structural
axis) and that cross-domain relationships are the norm rather than an edge
case for this project's own vocabularies (e.g. SNOMED "Has finding site"
Condition→Body Structure, LOINC "Has component" Measurement→Substance).
Following that review, the following decisions were made and are reflected
in this revision:

1. **Keep the maplib/OTTR switch for construction.** No in-repo benchmark of
   maplib-as-a-mapping-engine exists yet (the 2026-07-28 plan only
   benchmarked maplib for *querying* an already-built Turtle file). We are
   proceeding anyway because (a) OTTR templates make the tabular→triple
   mapping declarative and explicit — a real, non-performance benefit for
   maintainability and review — and (b) the peer-reviewed maplib paper
   reports consistent construction/mapping performance improvements over
   comparable tools. This plan still includes a step to record actual
   before/after numbers on our real data once implemented (§4 step 5), so we
   have project-specific evidence either way, consistent with how the
   Jelly/maplib query benchmark was documented.
2. **Domain-based chunking is dropped.** Output stays a single
   `build/vocabularies/omop.ttl`, exactly as today.
3. **Vocabulary scope is unchanged.** Still limited to
   `TARGET_VOCABULARIES` (`SNOMED`, `LOINC`, `RxNorm`, `RxNorm Extension`,
   `ICD10`, `ICD10CM`) — no expansion to the full Athena vocabulary set.
4. **`CONCEPT_ANCESTOR` is out of scope.** Not read, not mapped, not
   mentioned further in this plan.
5. **Verification is an automated test, not a manual QA step.** A synthetic
   multi-vocabulary fixture (already the pattern used in
   `tests/vocabulary/`) is loaded and queried with maplib's own SPARQL
   engine — no external triplestore is stood up, keeping the project's
   "no extra server process" posture intact.
6. **No merge.py/CLI plumbing for multiple files is needed.** Because output
   stays single-file, `merge.py`'s existing `loinc-snomed.ttl` + `omop.ttl` →
   `rosetta-vocabularies.ttl` combination step is untouched. This plan
   requires no changes to `merge.py`, the CLI, or the `justfile` beyond
   what's already wired for `build-omop`.

## 1. Goal

Replace the rdflib in-memory triple-add loop in `omop.py::build_graph` with a
declarative **maplib OTTR template** mapping, so that the OMOP CONCEPT /
CONCEPT_RELATIONSHIP → SKOS transformation is expressed as data (a template)
rather than imperative Python, while producing an identical
`build/vocabularies/omop.ttl` artifact (same triples, same IRIs, same
predicates) as today.

## 2. Modules to change

* **`src/sssom_rosetta/vocabulary/omop.py`:**
  * Keep `load_target_concepts` / `load_relationships` (Polars filtering)
    unchanged — they already select exactly the columns needed.
  * Replace `build_graph(concepts, relationships) -> Graph` (rdflib) with a
    maplib-based equivalent that returns triples/serializes directly, or
    returns a small wrapper so `write_ttl` keeps working.
  * `write_ttl` becomes a thin call into maplib's `model.write_ttl(...)` (or
    equivalent) instead of `rdflib.Graph.serialize`.
* **New `src/sssom_rosetta/vocabulary/templates.py` (or similar):** the OTTR
  `Template` definitions for (a) concept nodes (`skos:Concept`,
  `skos:prefLabel`, `skos:notation`, `skos:exactMatch` to source IRI) and
  (b) relationship edges (`Maps to`/`Is a`/`Subsumes` → SKOS predicate).
  Kept separate from `omop.py` so the templates are reviewable/reusable
  independent of the Polars I/O.
* **`pyproject.toml`:** promote `maplib` from **dev** dependency (added in
  the 2026-07-28 plan for the benchmark script only) to a **runtime**
  dependency, since it now sits in the main `build-omop` path.
* **`tests/vocabulary/test_omop.py`:** existing assertions on the produced
  graph's triples must still pass unchanged (this is the correctness
  contract — see §4 step 3). Add a maplib-SPARQL-based verification test
  (§4 step 5).

## 3. Risks & edge cases

* **Semantic parity with the current rdflib output.** The existing
  `build_graph` has small conditionals (skip empty `concept_name`/
  `concept_code`, only add `skos:exactMatch` to source IRI when
  `source_concept_iri` returns non-`None`, percent-encoding of concept codes
  via `source_concept_iri`/`quote`). OTTR templates must reproduce these
  exactly — a template that unconditionally emits a triple for a blank/null
  column would silently change behaviour (e.g. emit `skos:notation ""` where
  today nothing is emitted for `RxNorm Extension` rows with no native code).
  Mitigate by keeping the "does this concept have a source IRI" branch as a
  Polars-side null/filter step *before* the maplib mapping, so the template
  only ever sees rows it should fully map, rather than trying to express
  conditionals inside OTTR itself.
* **IRI minting stays centralised.** `namespaces.py` (`omop_iri`,
  `source_concept_iri`, percent-encoding for illegal IRI characters) must
  remain the single source of truth. Either the OTTR template parameters are
  fed pre-minted IRI strings computed by the existing `namespaces.py`
  helpers (recommended — reuses tested logic, keeps maplib as a pure
  triple-assembly layer), or the encoding/minting logic is reimplemented as
  OTTR expressions (higher risk, duplicates logic, not recommended).
* **maplib construction API maturity/performance is unverified on this data
  shape.** Unlike the query-side benchmark, we have no project-specific
  numbers for `Model.map()` throughput on ~millions of concept/relationship
  rows. Treat the benchmark in §4 step 5 as a gate: if maplib construction
  turns out slower or memory-heavier than rdflib on the real Athena-scale
  `CONCEPT.csv`/`CONCEPT_RELATIONSHIP.csv`, that is a documented finding for
  this plan (à la the Jelly reversal), not a blocker to merging the
  correctness work — but it should change the recommendation in §5.
* **Runtime dependency addition.** Moving `maplib` from dev to runtime
  dependency is a real footprint change (Rust-backed wheel) for anyone
  running `rosetta vocabulary build-omop`; confirm this is acceptable (it
  should be, since `maplib` is already installed for the benchmark script,
  but the dependency **group** changes).
* **Licensing scope.** Confirm the `Model`/`Template`/`Parameter`/`.map()`
  mapping API used here is part of maplib's Apache-2.0 core and not the
  proprietary SHACL/Datalog tier (per public docs, mapping and SPARQL are
  open source; only SHACL and Datalog validation/enrichment are gated) —
  record this confirmation in the PR description.

## 4. Implementation steps

1. **Add `maplib` as a runtime dependency** in `pyproject.toml` (move out of
   the dev group), `uv lock`.
2. **Define OTTR templates** in a new `templates.py`: one template for
   concept nodes, one for relationship edges, mirroring exactly the
   conditionals already in `build_graph` (see §3). Feed them pre-minted IRIs
   / labels / notations computed via the existing `namespaces.py` helpers
   and Polars `.with_columns(...)` on `concepts`/`relationships`, so the
   template itself stays a simple, declarative triple pattern.
3. **Reimplement `build_graph`** to build a `maplib.Model`, call
   `.map(template, df)` for the concept frame and the relationship frame,
   and expose whatever object `write_ttl` needs. Keep the function
   signature (`concepts: pl.DataFrame, relationships: pl.DataFrame`) and
   its output contract identical so `tests/vocabulary/test_omop.py`'s
   existing triple-level assertions require no changes — this is the
   correctness check that the maplib version is behaviourally equivalent to
   the rdflib version it replaces.
4. **Update `write_ttl`** to serialize via maplib's Turtle writer instead of
   `rdflib.Graph.serialize`, preserving the `output_path` /
   `mkdir(parents=True, exist_ok=True)` contract.
5. **Benchmark + automated verification (new, replaces the old manual QA
   step):**
   - Extend `scripts/benchmark_sparql.py` (or add a sibling script) to time
     `omop.py::build_graph` construction under the old rdflib path (kept
     temporarily on a branch/tag for comparison) vs. the new maplib path on
     the real Athena-derived `CONCEPT.csv`/`CONCEPT_RELATIONSHIP.csv`, and
     record the numbers in this plan doc once available, the same way the
     2026-07-28 plan recorded its query-benchmark numbers.
   - Add a `tests/vocabulary/test_omop.py` case that builds a graph from a
     small synthetic multi-vocabulary fixture (already the pattern used for
     the other fixtures in `tests/vocabulary/`) and runs a SPARQL query
     directly against the resulting `maplib.Model` (not a re-parsed file) to
     assert expected triples exist — e.g. an ICD10CM concept's
     `skos:exactMatch` to its SNOMED standard concept, and an `Is a` edge
     rendered as `skos:broadMatch`. This replaces the earlier plan's vague
     "load into a lightweight triplestore" step with an automated,
     in-process check and keeps the project's "no extra server" posture.
6. **`just check` green** (lint + `ty` + pytest) before considering this
   done.

## 5. Relationship to the prior maplib decision

The 2026-07-28 plan adopted maplib only for **querying** an already-built
Turtle graph and explicitly left rdflib in place for **construction**,
reasoning that "those triple-add loops are a one-time cost per release and
rdflib's ergonomics... are still the best fit for that code." This plan
knowingly revises that conclusion for the construction step specifically,
on the basis of the OTTR-template explicitness benefit and the published
maplib benchmark, while acknowledging (§3) that we have not yet reproduced
that benchmark on our own construction workload. §4 step 5 closes that gap
with project-specific numbers; if those numbers show a regression, update
this section and reconsider before this becomes the default recommendation
in `.agents/design/2027-07-21-choice-of-backend.md`.

## 6. Deliverables checklist

- [x] `maplib` present as a runtime dependency in `pyproject.toml` (already
      listed there, alongside the pre-existing dev-group entry, before this
      implementation pass started)
- [x] `src/sssom_rosetta/vocabulary/templates.py` (OTTR template for concept
      nodes; relationship edges use `Model.map_triples` directly — see
      deviation note below)
- [x] `omop.py::build_graph` reimplemented on maplib, same signature/contract
      (`build_graph(concepts, relationships) -> Model`)
- [x] `omop.py::write_ttl` serializes via maplib (`Model.write(..., format="turtle")`)
- [x] Existing `tests/vocabulary/test_omop.py` assertions carried over,
      rewritten to query the maplib `Model` via SPARQL (`model.query(...)`)
      instead of rdflib graph-membership syntax, since `maplib.Model` isn't
      iterable — semantics preserved, syntax necessarily changed
- [x] New maplib-SPARQL fixture test added (all 4 `test_omop.py` cases now
      exercise `model.query()`)
- [x] Construction benchmark run against the real Athena release under
      `data/vocabularies/omop/unversioned/` (6.9M `CONCEPT.csv` rows, 42.2M
      `CONCEPT_RELATIONSHIP.csv` rows on disk;
      `scripts/benchmark_omop_construction.py`):

      | Step | Value |
      |---|---|
      | Concepts (filtered to the 6 target vocabularies) | 3,974,193 |
      | Relationships (filtered) | 6,118,610 |
      | Triples produced (rdflib and maplib, identical) | 19,843,930 |
      | rdflib `build_graph` | 204.3s |
      | maplib `build_graph` | 56.4s |
      | **Speedup** | **~3.6x** |

      This confirms the expected construction-time win holds for this
      project's actual filtered workload (not just the general benchmark
      numbers from `scripts/benchmark_sparql.py` or the referenced paper),
      closing the "no in-repo benchmark yet" gap noted in §0/§3.
- [x] `just typecheck` and the `tests/vocabulary/` suite green; `just lint`
      / `just test` (repo-wide) still fail on ~113 and 7 pre-existing,
      unrelated issues respectively (ruff baseline violations elsewhere in
      the repo; a pandas 4.0 deprecation-as-error in `mapping/`-adjacent
      tests) that predate and are unrelated to this change — confirmed via
      `git stash` against the base branch. **Update:** the repo-wide ruff
      violations have since been fixed in a follow-up pass; `just lint` and
      `just typecheck` are now green. The 7 pandas-related `just test`
      collection errors remain, unrelated and pre-existing.

### Deviations from the original plan discovered during implementation

- `src/sssom_rosetta/vocabulary/merge.py` needed a small compatibility fix
  not explicitly called out in §2: `merge_graphs()` combines OMOP's output
  with `loinc_snomed.py`'s (still rdflib) output, so it now accepts either a
  rdflib `Graph` or a maplib `Model` via a structural `_MaplibModel` Protocol
  and an `_iter_triples()` helper that normalizes a `Model` to plain rdflib
  triples via an N-Triples round-trip. This was implicit in the plan's
  scope (§0/§5 note there'd be no *new* multi-file merge plumbing) but the
  type-level adapter was a necessary, previously unlisted addition.
- Relationship edges are built via `Model.map_triples()` over a plain
  subject/predicate/object frame, not a second OTTR template — the
  `relationship_id` → SKOS predicate mapping is a simple column lookup with
  no optional-value semantics, so a template added no value there.
