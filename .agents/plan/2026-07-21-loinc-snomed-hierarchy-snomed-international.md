# Plan: Add full SNOMED CT International hierarchy as a separate vocabulary graph

**Date:** 2026-07-21
**Status:** Accepted — **Option A (full SNOMED CT International ingest)**.
**Scope:** Add a reproducible pipeline that ingests the **full SNOMED CT
International Edition** RF2 release and builds it into its **own** Turtle file
`build/vocabularies/snomed-international.ttl`, kept **separate** from the existing
`loinc-snomed.ttl`. The two graphs share the `sct:` IRI scheme, so a later
`merge` step connects the LOINC-SNOMED extension concepts to the International
top-level groupings (Body structure, Clinical finding, Observable entity,
Substance, …) up to the root `138875005`.
**Supersedes:** the lightweight-backbone approach (Option B) previously drafted.
**Companion to:** `2026-07-21-add-snomed-loinc-omop-vocabularies.md`,
`2026-07-21-owl-dl-classification-deferral-note.md`

---

## 1. Problem statement

The built `build/vocabularies/loinc-snomed.ttl` looks "flat": it does not show
the top-level concept grouping (Body structure, Clinical finding, Observable
entity, Substance, Procedure, Pharmaceutical/biologic product, …) that the
LOINC-SNOMED browser displays as the roots of the hierarchy.

## 2. Root-cause analysis (confirmed against the extracted RF2)

`vocabulary/loinc_snomed.py::build_graph()` **already** emits, per Is-a edge,
both `rdfs:subClassOf` and `skos:broadMatch` (child → parent). The graph is not
edge-less. The defect is that **the hierarchy is truncated at the
extension-module boundary**:

- The ingested package (`SnomedCT_LOINCExtension_PRODUCTION_LO1010000_…`) contains
  **only the LOINC Extension module `11010000107`** — 46,057 concepts. Verified:
  every concept row has `moduleId == 11010000107`.
- The `sct2_Relationship_Snapshot` file has **55,494 active Is-a edges** whose
  `destinationId` includes **70 unique parent SCTIDs absent from the package's
  Concept file**. These are **International-edition** concepts the extension
  depends on (declared in `der2_ssRefset_ModuleDependencySnapshot`, target module
  `900000000000207008`).
- Those 70 missing parents are the **top-level groupings** and their ancestors —
  e.g. `363787002` Observable entity has **11,274** children pointing straight at
  it, `404684003` Clinical finding, `123037004` Body structure, `105590001`
  Substance, `71388002` Pharmaceutical/biologic product, root `138875005`.

Net effect in `loinc-snomed.ttl`: the grouping concepts appear only as **bare
object IRIs** (`sct:363787002` …) — no `rdf:type`, no `skos:prefLabel`, no path
to the root. Rendering shows a shallow forest of ~70 unlabelled roots.

**Conclusion:** the International backbone is missing. Option A supplies it in
full by ingesting the **entire SNOMED CT International Edition** as its own
graph, then merging.

## 3. Goals & non-goals

### Goals
1. Fetch/cache the **full SNOMED CT International Edition** RF2 release
   (licence-gated), reusing the existing `fetch.ingest_zip` / `cache_dir_for`
   design and the RF2 polars readers in `rf2.py`.
2. Build it into a **standalone** `build/vocabularies/snomed-international.ttl`
   with the same SKOS/RDFS shape as `loinc-snomed.ttl` (concepts, prefLabels,
   synonyms, `Is a` → `subClassOf` + `broadMatch`), terminating at root
   `138875005`.
3. **Keep the two TTLs separate** so each can be built, versioned, inspected and
   consumed independently.
4. Provide a **merge** that combines `loinc-snomed.ttl` +
   `snomed-international.ttl` (and, when present, `omop.ttl`) into a single graph
   in which the extension concepts attach to the International backbone via the
   shared `sct:` IRIs — no rewiring needed because both mint identical IRIs.
5. Reproducible, tested, consistent with the existing polars→rdflib pipeline.

### Non-goals
- No OWL-DL classification / reasoner (still deferred — see the deferral note).
  We emit the lightweight SKOS/RDFS graph from the **inferred** `Relationship`
  snapshot only.
- No redistribution of licensed SNOMED International files; only local,
  gitignored build artifacts.
- We do **not** rewrite `loinc-snomed.ttl` to embed the International concepts;
  the connection is made only at merge time.

## 4. Why a separate graph (not embedding into loinc-snomed.ttl)

- **Separation of provenance:** LOINC-SNOMED extension (module `11010000107`) and
  the International core (module `900000000000207008`) are distinct releases with
  distinct versions/licences. Keeping one TTL per release makes provenance,
  diffing and version bumps clean.
- **Reuse & size control:** the International graph is large (~350k+ concepts);
  building it once as its own artifact lets consumers who only need the extension
  skip it, and lets the merge be an explicit, opt-in step.
- **Merge is trivial and lossless:** both graphs mint `sct:<id>` via
  `namespaces.sct_iri`, so union in `merge.merge_ttl_files` reconnects children
  to their (now labelled) International parents automatically — the exact
  mechanism already used to link OMOP concept_ids.

## 5. Design & implementation

### 5.1 New source registry entry — `vocabulary/sources.py`
Add a `VocabularySource` for the International edition:

```python
"snomed-international": VocabularySource(
    name="snomed-international",
    version="<pinned, e.g. 20260101>",   # International edition effectiveTime
    kind="rf2",
    description=(
        "SNOMED CT International Edition (core module 900000000000207008), "
        "distributed as an RF2 package. Provides the top-level concept "
        "hierarchy the LOINC extension depends on."
    ),
    download_page="https://www.nlm.nih.gov/healthit/snomedct/international.html",
),
```

- Pin `version` to the International release whose `ModuleDependencySnapshot`
  target the ingested LOINC extension declares (v2.82 targets International
  `20260101`; confirm against the extension's module-dependency rows).
- Backfill `checksum` once a curator pins a specific ZIP.

### 5.2 Build module — reuse, don't duplicate
The International build has **exactly the same shape** as `loinc_snomed.py`. Two
options; recommend the first:

**Preferred — generalise the existing builder.** Rename the graph-building core
to a shared, module-agnostic function and call it from both:

- Keep `loinc_snomed.build_graph(concept, description, language, relationship)`
  as-is (it is already module-agnostic — it just reads whatever RF2 frames it is
  given).
- Add `vocabulary/snomed_international.py` with:
  - `build_from_release(release_dir) -> Graph` that locates the International
    Snapshot files with `find_file` and delegates to
    `loinc_snomed.build_graph`. **Note the International Description/Language
    filenames** differ only by the module token (e.g.
    `sct2_Description_Snapshot-en_INT_*.txt`,
    `der2_cRefset_LanguageSnapshot-en_INT_*.txt`); the `prefix=` patterns used
    by `find_file` already match on the leading token, but verify there is
    exactly one match per pattern in the International package (it may ship
    multiple language/description files — see §5.5).
  - `write_ttl(graph, output_path)` (or reuse `loinc_snomed.write_ttl`).

This keeps a single, tested graph-construction code path.

### 5.3 CLI — `cli.py`
- `vocabulary ingest` help text: extend the argument description to include
  `'snomed-international'` (the underlying `get_vocabulary_source` already works
  generically once the registry entry exists).
- New command `build-snomed-international`, mirroring
  `build-loinc-snomed`:
  ```
  rosetta vocabulary build-snomed-international
      → build/vocabularies/snomed-international.ttl
  ```
- Update `vocabulary merge` to include the International graph as an input:
  - inputs become `[loinc-snomed.ttl, snomed-international.ttl, omop.ttl]`,
    **skipping any that don't exist** (so merge still works with a subset), or
  - accept explicit `--input` paths. Recommend: merge whatever of the known set
    is present, and error only if fewer than two inputs exist.
- Output of merge stays `build/vocabularies/rosetta-vocabularies.ttl`.

### 5.4 justfile
- Add:
  ```
  vocab-build-snomed-international:
      uv run rosetta vocabulary build-snomed-international
  ```
- Update `vocab-build` to run `build-loinc-snomed`,
  `build-snomed-international`, `build-omop`, then `merge`.
- Keep vocab-* **out** of `build-all` (unchanged rationale: large, licence-gated,
  slow — same reason omop/loinc-snomed are excluded today).

### 5.5 RF2 file-location caveats (International vs extension)
The International package differs from the extension in ways `find_file` must
tolerate (it raises if 0 or >1 match):
- **Multiple Description/Language files.** International may ship additional
  language variants. Constrain patterns to the `-en` + `INT` tokens, or extend
  `find_file` to accept an explicit `contains=` filter. Verify exactly one match
  during Phase 1 against the real download.
- **Snapshot vs Full/Delta.** Continue to prefer the `Snapshot/Terminology`
  path; `find_file`'s `rglob` will otherwise also see `Full/` and `Delta/`
  copies → add a `Snapshot/` path guard (e.g. filter matches whose path contains
  `/Snapshot/`).
- **Concrete values / OWL refset files** present but unused (consistent with the
  deferral note).

### 5.6 Merge semantics
`merge.merge_graphs` already unions triples and re-binds prefixes. Because
`sct:363787002` in `loinc-snomed.ttl` (a bare object) and `sct:363787002` in
`snomed-international.ttl` (a typed, labelled `skos:Concept` with its own
`subClassOf` chain to `138875005`) are the **same IRI**, the union yields a
fully connected, labelled hierarchy. No dedup logic needed — RDF set semantics
handle it. Add a merge-time sanity check/log: count `skos:Concept` nodes that
are objects of `subClassOf` but lack any `prefLabel` (should drop to ~0 after
adding the International graph).

## 6. Tests
- `tests/vocabulary/test_snomed_international.py`:
  - `build_from_release` on a **small synthetic International fixture** (a handful
    of RF2 rows incl. root `138875005` and `363787002`) yields labelled
    `skos:Concept` nodes with `subClassOf`/`broadMatch` up to the root.
  - file-location: a fixture with `Snapshot/`, `Full/`, `Delta/` copies resolves
    to the `Snapshot/` file only (guards §5.5).
- Extend `tests/vocabulary/test_merge.py`:
  - given a tiny `loinc-snomed`-style graph whose parent (`363787002`) is a bare
    object, plus an `international`-style graph that types+labels `363787002` and
    links it to `138875005`, the merged graph has: `363787002` typed
    `skos:Concept`, carrying a `prefLabel`, with a `subClassOf` path to
    `138875005`; and the extension child reaches the root transitively.
  - merge tolerates a missing input (e.g. no `omop.ttl`).
- `tests/test_cli.py`: add coverage for `build-snomed-international` (success +
  "no ingested release" error path) mirroring the existing loinc-snomed tests.
- Extend `tests/vocabulary/test_sources.py`: `snomed-international` resolves and
  has `kind == "rf2"`.

## 7. Docs
- `docs/vocabularies/index.md`: document the new `snomed-international.ttl`
  artifact, how to ingest the International edition, and that the top-level
  grouping/hierarchy becomes navigable **after merge** (with the two graphs kept
  separate as source artifacts).
- Note the pinned International edition version and its correspondence to the
  LOINC extension's module dependency.

## 8. Acceptance criteria
1. `rosetta vocabulary ingest snomed-international <zip>` extracts the release
   into the cache (checksum verified when pinned).
2. `rosetta vocabulary build-snomed-international` produces a standalone
   `build/vocabularies/snomed-international.ttl` with labelled `skos:Concept`
   nodes for the top-level groupings (Body structure, Clinical finding,
   Observable entity, Substance, Procedure, Pharmaceutical/biologic product) and
   the root `138875005`.
3. `loinc-snomed.ttl` is **unchanged** (still the extension-only graph).
4. `rosetta vocabulary merge` produces `rosetta-vocabularies.ttl` in which a
   sample LOINC-extension concept has a `subClassOf`/`broadMatch` path
   terminating at `sct:138875005`, and no `skos:Concept` object of `subClassOf`
   is left unlabelled.
5. vocab-* recipes stay out of `build-all`; all new/existing tests pass.

## 9. Risks & mitigations
- **International RF2 filename/layout differences** break `find_file` → §5.5
  guards (`Snapshot/` path filter, `-en`/`INT` constraints) + a Phase-1
  smoke-test against the real download before writing the builder.
- **Graph size / build time & memory** (~350k concepts in rdflib) → acceptable
  for an opt-in, non-`build-all` step; if it becomes a problem, a follow-up can
  stream triples or emit N-Triples. Not in scope now.
- **Version mismatch** between the ingested International edition and the LOINC
  extension's declared module dependency → pin `version` from the extension's
  `ModuleDependencySnapshot`; document; assert in a test that the pinned version
  matches the extension's target `sourceEffectiveTime`/`targetEffectiveTime` if
  both are ingested.
- **Duplicate/other-language descriptions** inflating labels → constrain to
  preferred + `-en` as the extension builder already does via
  `rf2.preferred_terms`.

## 10. Work breakdown (suggested phases)
1. **Ingest + locate:** add the `snomed-international` source; ingest a real
   International ZIP; verify `find_file` patterns against the actual layout;
   add the `Snapshot/` path guard to `find_file` (or a `contains=` param) with
   tests. (De-risks §5.5.)
2. **Build graph:** `vocabulary/snomed_international.py::build_from_release`
   delegating to `loinc_snomed.build_graph`; `build-snomed-international` CLI
   command + justfile recipe; unit tests with a synthetic fixture.
3. **Merge:** extend `vocabulary merge` to include the International graph
   (tolerant of missing inputs) + merge tests proving end-to-end connectivity to
   the root; merge-time unlabelled-parent sanity log.
4. **Docs + version pinning:** update `docs/vocabularies/index.md`; pin/record
   the International edition version and checksum.

## Appendix A — External parent SCTIDs the International graph must resolve (from extension v2.82)

Direct-child fan-out (why the extension graph looks flat); the International
graph provides these as labelled concepts with their own ancestry to root:

```
11274  363787002   (Observable entity — dominant grouping)
 442   1290195007      269   1234806008      122   7120007
  61   399807005        51   702946003        49   568131000005103
  14   1371017004       14   1285434004       10   364681000119104
   9   376261000119107   6   272391002         5   372461000119109
   5   121051005
   4   871555000  737094009  726447007  68498002  375701000119105  1335902000
   3   372361000119104  365331000119108  29246005  1306902009
   2   74889000  446609009  374451000119101  372661000119106  121044001
       119297000  118598001
   1   9680003  900000000000453004  871552002  766763002  762705008  703446000
       702873001  46046006  418315003  404642006  404273000  399824004  399806001
       397020000  395531003  373265006  365451000119108  364351000119103
       364321000119106  364061000119103  363891000119100  30234008  272099008
       1335901007  1306386000  1295447006  1285667006  1285654008  1285370002
       1285329004  1240461000000109  123038009  121232006  1201891009  117207003
       116186008  11257001  106205006  103242005
```

All of these are concepts in the International core module `900000000000207008`
and will be materialised (typed, labelled, connected to `138875005`) by the
International graph, then linked to the extension at merge time.
