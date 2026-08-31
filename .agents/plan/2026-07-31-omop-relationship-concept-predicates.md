# Plan: use OMOP relationship_concept_id as the relationship predicate

**Date:** 2026-07-31
**Status:** Implemented
**Scope:** Change how `src/sssom_rosetta/vocabulary/omop.py` maps
`CONCEPT_RELATIONSHIP.csv` rows to triples: instead of collapsing every kept
`relationship_id` onto one of three fixed SKOS predicates
(`skos:exactMatch`/`broadMatch`/`narrowMatch`), each OMOP relationship type
becomes its own predicate node, IRI'd by its `relationship_concept_id`, with
a `skos:prefLabel` carrying the human-readable `relationship_name`. No other
part of the pipeline (concept nodes, DHD, merge, CLI) changes.

**Related:**
- `.agents/plan/2026-07-21-add-snomed-loinc-omop-vocabularies.md` (original
  OMOP vocabulary pipeline design; this plan revises its relationship-mapping
  decision only)
- `.agents/plan/2026-07-30-implementation-maplib.md` (moved `build_graph` to
  maplib/OTTR; this plan builds on that maplib-based implementation)

---

## 1. Motivation

The current implementation only keeps three `relationship_id` values —
`Maps to`, `Is a`, `Subsumes` — and maps each to a fixed SKOS predicate:

```python
_RELATIONSHIP_PREDICATES = {
    "Maps to": f"{_SKOS}exactMatch",
    "Is a": f"{_SKOS}broadMatch",
    "Subsumes": f"{_SKOS}narrowMatch",
}
```

This drops the actual OMOP relationship semantics. For example, the first
row of `CONCEPT_RELATIONSHIP.csv`:

```
concept_id_1  concept_id_2  relationship_id     valid_start_date  valid_end_date  invalid_reason
738263        738156        RxNorm has ing      20050404          20991231
```

is currently discarded entirely (`RxNorm has ing` isn't one of the three
kept types), so there is no triple in `omop.ttl` reflecting that 738263 (a
drug) has ingredient 738156. More generally, `RELATIONSHIP.csv` — an OMOP
lookup table with ~700 rows — shows that **every relationship type is itself
an OMOP concept**, carrying its own `relationship_concept_id`:

```
relationship_id  relationship_name              relationship_concept_id
RxNorm has ing   Has ingredient (RxNorm)        44818719
Is a             Is a                            44818821
Maps to          Non-standard to Standard map   44818977
                 (OMOP)
```

The user wants predicates of the form `omop:44818719` (i.e.
`omopconcept:44818719`, reusing the existing `omopconcept:` namespace/IRI
scheme already used for concept nodes) instead of the three hard-coded SKOS
predicates, with the relationship's own name attached as a label so the
predicate IRI is self-describing when browsing the Turtle file.

## 2. Requirements (from user instruction)

1. Predicates are `omopconcept:<relationship_concept_id>` — the OMOP integer
   concept ID for the relationship type, in the same IRI namespace already
   used for concept nodes (`omop_iri()` / `OMOP_CONCEPT` in
   `namespaces.py`). No new namespace needed.
2. Add the relationship name as a **label** on the predicate node, e.g.:
   ```turtle
   omopconcept:44818719 skos:prefLabel "Has ingredient (RxNorm)"@en .
   ```
3. Include **all** relationship types whose endpoints are already in scope
   — i.e. no separate vocabulary allow-list on `relationship_name` at all.
   The existing endpoint filter (`concept_id_1`/`concept_id_2` both already
   in the filtered `TARGET_VOCABULARIES` concept set, `invalid_reason`
   empty) is the only scoping mechanism: since `CONCEPT_RELATIONSHIP.csv` is
   already filtered down to relationships *between* SNOMED/LOINC/RxNorm/
   RxNorm Extension/ICD10/ICD10CM concepts, whatever relationship types
   naturally occur between those concepts are exactly "the limitative list
   of vocabularies, as inferable from context" — no separate
   `relationship_name` string-matching needed (an earlier draft of this plan
   proposed matching a `(SNOMED)`/`(OMOP)`/`(RxNorm)`/`(LOINC)` suffix on
   `relationship_name`; **dropped** per user feedback as unnecessary
   complexity — the endpoint filter alone already achieves the same scoping,
   more robustly, since it's structural rather than a string convention).

## 3. New data dependency

This requires reading **`RELATIONSHIP.csv`** (not currently read by
`omop.py`) — the small lookup table (~700 rows, ~40KB) mapping
`relationship_id` → `relationship_name`/`relationship_concept_id`. It ships
in the same Athena bundle as `CONCEPT.csv`/`CONCEPT_RELATIONSHIP.csv`, so
`build_from_release` locates it the same way (`find_file` by exact filename).

## 4. Design

### 4.1 New loader: `load_relationship_types`

```python
def load_relationship_types(relationship_types_csv: Path) -> pl.DataFrame:
    """Read RELATIONSHIP.csv: relationship_id -> concept_id/name lookup."""
```

No filtering here — this just reads the full ~700-row lookup table as-is
(`relationship_id`, `relationship_concept_id`, `relationship_name`). Scoping
to "the limitative list of vocabularies" happens implicitly via
`load_relationships`'s existing endpoint filter (§4.2), not via a
`relationship_name`/vocabulary-suffix match on this table.

### 4.2 `load_relationships` — endpoint filter unchanged, no relationship_id allow-list

`load_relationships` keeps its current signature and filtering logic
(`concept_id_1`/`concept_id_2` both in the filtered target-vocabulary
concept set, `invalid_reason` empty) — the one change is **dropping** the
`pl.col("relationship_id").is_in(list(_RELATIONSHIP_PREDICATES))` clause, so
every relationship type is kept as long as both endpoints qualify. This is
simpler than the original draft (no second loader parameter needed):

```python
relationship_types = load_relationship_types(relationship_types_csv)
relationships = load_relationships(relationship_csv, concepts["concept_id"])
```

### 4.3 `build_graph` gains a `relationship_types` parameter

```python
def build_graph(
    concepts: pl.DataFrame,
    relationships: pl.DataFrame,
    relationship_types: pl.DataFrame,
) -> Model:
```

Two new/changed triple-mapping steps (plain `Model.map_triples`, no OTTR
template needed — same reasoning as the current relationship-edge mapping:
no optional-value semantics required):

1. **Relationship edges**: join `relationships` to `relationship_types` on
   `relationship_id` to bring in `relationship_concept_id`, then emit
   `(omopconcept:<concept_id_1>, omopconcept:<relationship_concept_id>,
   omopconcept:<concept_id_2>)` triples for **every** kept row — a single
   `omopconcept:` predicate per row, no legacy SKOS predicate emitted
   alongside it (per the confirmed decision in §6.1: option (c), legacy SKOS
   predicates are dropped entirely and `gephi.py` is fixed in a later,
   separate change).
2. **Relationship labels**: one `(omopconcept:<relationship_concept_id>,
   skos:prefLabel, "<relationship_name>"@en)` triple per **distinct**
   `relationship_concept_id` that actually appears in the joined
   relationship-edge frame (i.e. restricted to relationship types that
   actually occur between in-scope concepts, not all ~700 rows of
   `RELATIONSHIP.csv` — no point labelling a predicate that's never used).

`build_from_release` locates and loads `RELATIONSHIP.csv` alongside the
existing two files and threads it through.

### 4.4 Backwards compatibility / removed behaviour

- `_RELATIONSHIP_PREDICATES` (the 3-entry SKOS predicate dict) is **removed
  entirely** — no legacy SKOS predicate is emitted for any relationship
  type, including `Maps to`/`Is a`/`Subsumes`. This is a confirmed breaking
  change to `omop.ttl`'s relationship-edge predicates.
- **Known, deferred regression**: `src/sssom_rosetta/mapping/gephi.py`'s
  `VOCABULARY_PREDICATES` (a fixed frozenset of the 5 SKOS mapping
  predicates) is what `build_vocabulary_graph()` uses to decide which
  triples become Gephi edges vs. node attributes. Once `Maps to`/`Is a`/
  `Subsumes` no longer emit `skos:exactMatch`/`broadMatch`/`narrowMatch`,
  the Gephi vocabulary-graph export (`rosetta ... gephi`, vocabulary graph
  mode) will **stop showing OMOP-internal relationship edges** (it will
  still show cross-vocabulary `exactMatch` edges from concept-node
  `source_concept_iri` links, which are untouched by this plan). Per the
  confirmed decision in §6.1 (option (c)), fixing `gephi.py` to discover
  `omopconcept:` relationship predicates is **out of scope for this plan**
  and tracked as a follow-up; this plan's PR description must call out the
  regression explicitly so it isn't a silent surprise.

## 5. Modules to change

- **`src/sssom_rosetta/vocabulary/omop.py`**: add `load_relationship_types`;
  change `load_relationships` signature (add `relationship_ids` param);
  change `build_graph` signature (add `relationship_types` param); rewrite
  `_relationship_rows` (join in `relationship_concept_id`, drop the fixed
  predicate dict); add a `_relationship_label_rows` helper; update
  `build_from_release` to locate/load `RELATIONSHIP.csv`; update module
  docstring (currently documents the 3-predicate mapping).
- **`tests/vocabulary/test_omop.py`**: existing
  `test_build_graph_relationship_predicates` asserts `skos:exactMatch`/
  `broadMatch` for `Maps to`/`Is a` — must be rewritten to assert
  `omopconcept:<relationship_concept_id>` predicates instead, plus a new
  fixture `RELATIONSHIP.csv`-equivalent `pl.DataFrame` and a new assertion
  for the `skos:prefLabel` on a relationship predicate node. Add a case for
  a previously-dropped-but-now-kept type (e.g. `RxNorm has ing`) to cover
  the motivating example directly.
- **`docs/vocabularies/index.md`**: documents the current
  `Maps to`/`Is a`/`Subsumes` → SKOS mapping (§ relationship mappings table)
  — needs rewriting to describe the new `omopconcept:<relationship_concept_id>`
  scheme and the endpoint-based scoping (no vocabulary-name matching).
- **`.agents/plan/2026-07-21-add-snomed-loinc-omop-vocabularies.md`**: the
  original plan documents the 3-predicate design as a decision; add a note
  pointing at this plan as the superseding revision (same pattern as how
  `2026-07-30-implementation-maplib.md` superseded parts of the original
  plan for construction).

## 6. Open questions for review

1. **Breaking change to `omop.ttl` semantics, with a confirmed downstream
   consumer** (§4.4): today's `omop.ttl` relationship edges use plain SKOS
   predicates (`exactMatch`/`broadMatch`/`narrowMatch`). Two things depend
   on that today, checked directly in the codebase:
   - `merge.py`'s cross-linking between OMOP and SNOMED/LOINC/DHD graphs
     does **not** depend on the `Maps to`/`Is a`/`Subsumes` relationship
     edges — it depends on the **concept-node** `skos:exactMatch` to a
     `sct:`/`loinc:`/`rxnorm:` IRI, minted via `source_concept_iri` in
     `CONCEPT_TEMPLATE` (`tests/vocabulary/test_merge.py::
     test_merge_connects_omop_to_snomed`). That part of `omop.py` is
     untouched by this plan, so **this specific cross-linking mechanism is
     unaffected** either way.
   - `src/sssom_rosetta/mapping/gephi.py` (the `rosetta ... gephi` GEXF
     export for Gephi visualisation), however, **does** depend on the
     relationship edges' predicates directly: `VOCABULARY_PREDICATES` is a
     fixed `frozenset` of the 5 SKOS mapping predicates
     (`exactMatch`/`closeMatch`/`broadMatch`/`narrowMatch`/`relatedMatch`),
     and `build_vocabulary_graph()` only renders edges whose predicate is in
     that set (everything else becomes a node **attribute**, not a graph
     edge — see the module docstring's `rdfs:label`-as-attribute rationale,
     which generalises to any predicate not in `VOCABULARY_PREDICATES`).
     The module comment is explicit about relying on the very design this
     plan changes: *"OMOP's `Is a`/`Subsumes` relationships are already
     mapped to `skos:broadMatch`/`narrowMatch` ..., so the vocabulary's
     hierarchy is captured by the SKOS predicates alone."* If OMOP
     relationship edges switch fully to `omopconcept:<relationship_concept_id>`
     predicates, **every OMOP-internal relationship edge (including `Is a`/
     `Subsumes`) disappears from the Gephi export** — the vocabulary graph
     visualisation would show only cross-vocabulary `exactMatch` edges from
     concept nodes, losing the entire OMOP hierarchy/relationship structure
     it currently displays.

   **Options to resolve:**
   - **(a)** Switch fully to `omopconcept:` predicates for all relationship
     edges (as originally proposed), and **also update `gephi.py`** so
     `VOCABULARY_PREDICATES` (or a new parameter) includes the OMOP
     relationship-concept predicates too — e.g. by having
     `build_vocabulary_graph` discover which predicates in the loaded graph
     have an `omopconcept:` IRI and a `skos:prefLabel` (marking them as
     relationship types), rather than a fixed frozenset. More invasive, but
     keeps one predicate scheme per edge and fixes Gephi to match.
   - **(b)** Emit **both**: the new `omopconcept:<relationship_concept_id>`
     predicate (satisfying the user's ask) **and** keep the existing
     `skos:exactMatch`/`broadMatch`/`narrowMatch` triple for the 3
     originally-mapped types (`Maps to`/`Is a`/`Subsumes` only — the other
     ~387 newly-included types get *only* the `omopconcept:` predicate,
     since they have no prior SKOS mapping to preserve). This keeps
     `gephi.py` working unchanged for the hierarchy/mapping edges it already
     visualises, at the cost of `Maps to`/`Is a`/`Subsumes` edges appearing
     twice (once under each predicate).
   - **(c)** Do (a) but scope `gephi.py`'s fix to a **separate, later** PR —
     ship this plan's change first, accept that the Gephi vocabulary export
     temporarily loses OMOP-internal edges, and file it as a known
     follow-up. Simplest for this PR, but leaves a real regression live in
     the meantime.

   **Decision (confirmed with user, revised 2026-07-31): option (c).** Drop
   the legacy SKOS predicates (`skos:exactMatch`/`broadMatch`/`narrowMatch`)
   for OMOP relationship edges entirely — every kept relationship row
   (including `Maps to`/`Is a`/`Subsumes`) emits **only** the
   `omopconcept:<relationship_concept_id>` predicate, no double-emission.
   `gephi.py`'s regression (losing OMOP-internal edges from its vocabulary
   graph export) is accepted as a known, deferred issue and fixed in a
   later, separate change — **not** part of this plan's implementation.
2. **Scale**: dropping the relationship-type allow-list means whatever
   distinct relationship types actually occur between target-vocabulary
   concepts in `CONCEPT_RELATIONSHIP.csv` are now all kept (likely closer to
   the ~390-ish figure observed for SNOMED/OMOP/RxNorm/LOINC-tagged types,
   since those are the vocabularies represented among target concepts, but
   not guaranteed to exactly match — some previously-unseen relationship
   types may appear once endpoint-only filtering is the sole criterion).
   This increases both the row count kept after filtering and the number of
   predicate/label triples in `omop.ttl` versus today's 3-type-only mapping.
   Acceptable, given the goal is completeness of the OMOP relationship graph
   — flagging so the resulting file-size/triple-count increase isn't a
   surprise (no numeric estimate yet; can be measured once implemented,
   similar to the benchmark table in the maplib plan).
3. **`relationship_name` as label**: confirmed — `skos:prefLabel` (not
   `rdfs:label`), matching `CONCEPT_TEMPLATE`'s existing convention for
   concept nodes.
4. **~~Vocabulary-suffix matching~~ — resolved, dropped**: an earlier draft
   proposed matching a `(VOCAB)` suffix on `relationship_name` to scope
   which relationship types count as "the limitative list of vocabularies".
   Per user feedback, this is unnecessary: the existing endpoint filter
   (`concept_id_1`/`concept_id_2` both already restricted to
   `TARGET_VOCABULARIES`) already scopes relationship types structurally,
   with no dependency on a free-text naming convention. §4.1/§4.2 above
   reflect this simplification.

## 7. Out of scope

- No change to concept-node mapping (`CONCEPT_TEMPLATE`, `skos:prefLabel`/
  `notation`/`exactMatch` to source IRI) — untouched.
- No change to DHD (`dhd.py`), `loinc_snomed.py`, `merge.py`'s file-merge
  mechanics, or the CLI surface (`vocabulary build-omop` keeps the same
  signature/output path).
- No change to `TARGET_VOCABULARIES` (still SNOMED, LOINC, RxNorm, RxNorm
  Extension, ICD10, ICD10CM) or which OMOP concepts are included — this plan
  only changes which *relationship rows between already-included concepts*
  are kept, and how they're predicated.
