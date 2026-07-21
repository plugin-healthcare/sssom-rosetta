# Plan: Integrate LOINC-SNOMED Ontology + OHDSI/OMOP vocabularies into a single TTL

**Date:** 2026-07-21
**Status:** Draft
**Scope:** Add a reproducible pipeline that (a) parses the LOINC-SNOMED Ontology
RF2 release into Turtle, and (b) integrates OHDSI/OMOP vocabularies so that OMOP
`concept_id`s are woven together with SNOMED, LOINC, RxNorm and ICD10 concepts
into a single `.ttl` graph — using **polars** for tabular parsing and **rdflib**
for graph construction.

---

## 1. Goals & non-goals

### Goals
1. Fetch/cache the **LOINC-SNOMED Ontology** RF2 release (SNOMED CT extension
   format) reproducibly, consistent with the existing `ontology/` fetch+cache
   design.
2. Parse the RF2 tab-separated files with **polars** and build a Turtle graph
   with **rdflib** → `build/vocabularies/loinc-snomed.ttl`.
3. Fetch/cache an **OHDSI/OMOP (Athena)** vocabulary bundle limited to
   `SNOMED`, `LOINC`, `RxNorm`, `RxNorm Extension`, `ICD10`, `ICD10CM`.
4. Parse OMOP `CONCEPT.csv` / `CONCEPT_RELATIONSHIP.csv` with polars and emit
   Turtle where each **OMOP `concept_id`** is a node cross-linked (via SKOS) to
   the underlying source-vocabulary concepts (SNOMED SCTIDs, LOINC codes, RxNorm
   codes, ICD10/ICD10CM codes).
5. Merge everything into **one** `build/vocabularies/rosetta-vocabularies.ttl`.
6. Wire it into the `rosetta` CLI and `justfile` as reproducible recipes.

### Non-goals (this increment)
- No hand-authored SSSOM mappings for these vocabularies (that stays the
  CSV+CSVW → SSSOM path already in `mapping/`). This pipeline produces a
  *vocabulary graph*, not curated SSSOM mapping sets.
- No full OWL-DL classification of SNOMED axioms (see §7, optional follow-up
  using `snomed-owl-toolkit`). We emit a lightweight SKOS/RDFS graph.
- No redistribution of licensed source files (SNOMED/UMLS); only local build
  artifacts, gitignored.

---

## 2. Background: source file formats (from research)

### 2.1 LOINC-SNOMED Ontology (loincsnomed.org)
- Distributed as a **standard SNOMED CT RF2 extension package** (module
  `11010000107 |LOINC Extension module|`). Current v2.82 (March 2026).
- Access requires a **SNOMED International affiliate licence** + LOINC licence.
  Download page: https://loincsnomed.org/downloads (moving to loinc.org/ontology).
- RF2 files are UTF-8, **tab-separated**, header row, one component-version per
  row. Use the **Snapshot/** folder (latest active state).
- Key files & columns:
  - `sct2_Concept_Snapshot_*.txt`: `id, effectiveTime, active, moduleId, definitionStatusId`
  - `sct2_Description_Snapshot-en_*.txt`: `id, effectiveTime, active, moduleId, conceptId, languageCode, typeId, term, caseSignificanceId`
    (`typeId` 900000000000003001 = FSN, 900000000000013009 = synonym)
  - `sct2_Relationship_Snapshot_*.txt`: `id, effectiveTime, active, moduleId, sourceId, destinationId, relationshipGroup, typeId, characteristicTypeId, modifierId`
    (`typeId` 116680003 = `Is a`)
  - `sct2_sRefset_OWLExpressionSnapshot_*.txt`: `id, effectiveTime, active, moduleId, refsetId, referencedComponentId, owlExpression` (OWL 2 functional syntax — the authoritative logical definitions)
  - `der2_cRefset_LanguageSnapshot-en_*.txt`: `id, …, referencedComponentId (=descriptionId), acceptabilityId` (900000000000548007 = preferred)
  - `der2_…Map…` / alternate-identifier refset: **LOINC Num ↔ SCTID** binding.
- IRI scheme: **`http://snomed.info/id/{sctid}`**.

### 2.2 OHDSI/OMOP Standardized Vocabularies (Athena)
- ZIP of **tab-delimited** files with `.csv` extension (NOT comma-delimited),
  UTF-8, dates `YYYYMMDD`. Portal: https://athena.ohdsi.org/ (tick the desired
  vocabularies before requesting). CPT4 needs `cpt4.jar` + UMLS key — **not
  needed** for our target set.
- Key files & columns:
  - `CONCEPT.csv`: `concept_id, concept_name, domain_id, vocabulary_id, concept_class_id, standard_concept, concept_code, valid_start_date, valid_end_date, invalid_reason`
  - `CONCEPT_RELATIONSHIP.csv`: `concept_id_1, concept_id_2, relationship_id, valid_start_date, valid_end_date, invalid_reason`
  - `CONCEPT_ANCESTOR.csv`: `ancestor_concept_id, descendant_concept_id, min_levels_of_separation, max_levels_of_separation`
  - `RELATIONSHIP.csv`, `VOCABULARY.csv`, `CONCEPT_SYNONYM.csv`, `CONCEPT_CLASS.csv`, `DOMAIN.csv`, `DRUG_STRENGTH.csv`.
- Target `vocabulary_id` values: `SNOMED`, `LOINC`, `RxNorm`, `RxNorm Extension`,
  `ICD10`, `ICD10CM`. `ICD10` = WHO base; `ICD10CM` = US clinical modification
  (separate, more granular code namespace). Both non-standard → `Maps to` SNOMED.
- Crosswalk semantics:
  - `Maps to` (source → standard) → `skos:exactMatch` (or `skos:closeMatch`
    when source maps to multiple standards).
  - `Is a` → `skos:broadMatch` (subject = more specific, per AGENTS.md).
  - `Subsumes` → `skos:narrowMatch`.
  - `concept_name` → `skos:prefLabel`; `CONCEPT_SYNONYM` → `skos:altLabel`.
- No official OMOP IRI scheme — **pin one and document it**:
  proposed `https://w3id.org/omop/concept/{concept_id}`.

---

## 3. IRI & namespace decisions

| Prefix | Namespace | Used for |
|--------|-----------|----------|
| `sct` | `http://snomed.info/id/` | SNOMED CT + LOINC-Extension SCTIDs |
| `omopconcept` | `https://w3id.org/omop/concept/` | OMOP integer `concept_id` nodes |
| `loinc` | `https://loinc.org/` | LOINC Num codes (`loinc:<num>`) |
| `rxnorm` | `http://purl.bioontology.org/ontology/RXNORM/` | RxNorm RXCUIs |
| `icd10` | `http://hl7.org/fhir/sid/icd-10/` | WHO ICD-10 codes |
| `icd10cm` | `http://hl7.org/fhir/sid/icd-10-cm/` | ICD-10-CM codes |
| `skos` | `http://www.w3.org/2004/02/skos/core#` | matches/labels |

Decision to confirm during implementation: whether to bridge source concepts to
OMOP nodes by minting one IRI per source code, or to rely on the OMOP node as the
hub and attach `skos:notation` + `skos:exactMatch` to source-vocabulary IRIs.
**Recommended:** OMOP node is the hub; each source concept gets an IRI per the
table above and is linked to its OMOP node.

---

## 4. Architecture / where code goes

Add a new subpackage mirroring the existing `ontology/` conventions:

```
src/sssom_rosetta/vocabulary/
  __init__.py
  sources.py        # VocabularySource registry (RF2 package + Athena bundle), pinned version + checksum
  fetch.py          # download/cache (or point at a locally-provided licensed zip); unzip into data/vocabularies/<name>/<version>/
  rf2.py            # polars readers for RF2 files (Concept/Description/Relationship/OWL/Language)
  loinc_snomed.py   # RF2 -> rdflib.Graph -> loinc-snomed.ttl
  omop.py           # Athena CSV -> rdflib.Graph -> omop.ttl (+ cross-links)
  merge.py          # combine graphs -> rosetta-vocabularies.ttl
tests/vocabulary/
  test_rf2.py
  test_loinc_snomed.py
  test_omop.py
  test_merge.py
  fixtures/         # tiny synthetic RF2 + Athena samples (a handful of rows)
```

CLI: add a `vocabulary` sub-app in `cli.py`:
- `rosetta vocabulary fetch <name>` (loinc-snomed | omop)
- `rosetta vocabulary build-loinc-snomed`
- `rosetta vocabulary build-omop`
- `rosetta vocabulary merge` → `build/vocabularies/rosetta-vocabularies.ttl`

`justfile`: `vocab-fetch`, `vocab-build`, `vocab-merge`, folded into `build-all`.

### Reuse vs. new
- Reuse the **fetch/cache/checksum** pattern from `ontology/loader.py` (idempotent
  download, `data/…/<name>/<version>/`, SHA-256 verification). Because RF2 is a
  ZIP and requires a licence, `fetch.py` must also support a
  `--from-local <zip>` path (user supplies the licensed download) rather than an
  open URL, and still checksum/cache it.
- The existing `ontology/catalog.py` operates on rdflib graphs; the merged
  vocabulary TTL can be consumed by the same helpers if needed.

---

## 5. Implementation phases

### Phase 0 — Dependencies & scaffolding
- Confirm `polars` and `rdflib` already in `pyproject.toml` (they are). No new
  runtime deps required for the lightweight path.
- Create `vocabulary/` package + empty modules + `tests/vocabulary/` with tiny
  synthetic fixtures (so tests never need licensed data).

### Phase 1 — RF2 reader (`rf2.py`)
- polars readers: `read_rf2(path)` → `pl.read_csv(path, separator="\t",
  quote_char=None, infer_schema_length=0)`. Keep SCTIDs as `Utf8`.
- Helpers: `active_snapshot(df)` (filter `active == "1"`), `preferred_terms`
  (Description ⨝ Language on descriptionId, filter FSN/preferred), `isa_edges`
  (Relationship filter `typeId == "116680003"`).
- Tests against fixtures.

### Phase 2 — LOINC-SNOMED → TTL (`loinc_snomed.py`)
- Build `rdflib.Graph`, bind `sct`, `skos`, `owl`, `rdfs`.
- For each active concept: `sct:<id> a skos:Concept` (+ `owl:Class` optionally).
- FSN → `skos:prefLabel` / `rdfs:label`; synonyms → `skos:altLabel` (lang tag).
- `Is a` → `rdfs:subClassOf` **and/or** `skos:broadMatch`.
- LOINC Num ↔ SCTID map refset → `sct:<id> skos:exactMatch loinc:<num>` and
  `skos:notation` for the LOINC Num.
- Output `build/vocabularies/loinc-snomed.ttl`.
- (Logical OWL axioms from the OWL refset are deferred — see §7.)

### Phase 3 — OMOP → TTL (`omop.py`)
- polars lazy scan of `CONCEPT.csv`, filter target `vocabulary_id`s.
- Emit `omopconcept:<concept_id> a skos:Concept`, `skos:prefLabel` = concept_name,
  `skos:notation` = concept_code, `dct:source`/custom prop = vocabulary_id.
- Link each OMOP concept to its **source-vocabulary IRI** (SNOMED SCTID, LOINC
  Num, RxNorm RXCUI, ICD10/ICD10CM code) via `skos:exactMatch`, built from
  `vocabulary_id` + `concept_code`.
- Scan `CONCEPT_RELATIONSHIP.csv`, filter `invalid_reason` null:
  - `Maps to` → `skos:exactMatch` (OMOP source concept → OMOP standard concept)
  - `Is a` → `skos:broadMatch`; `Subsumes` → `skos:narrowMatch`.
- Output `build/vocabularies/omop.ttl`.

### Phase 4 — Merge (`merge.py`)
- Load `loinc-snomed.ttl` + `omop.ttl` into one rdflib graph; the shared
  `sct:` / `loinc:` IRIs make SNOMED/LOINC concepts coincide between the two
  sources automatically, so OMOP concept_ids become connected to the
  LOINC-SNOMED ontology nodes.
- Serialize `build/vocabularies/rosetta-vocabularies.ttl`.

### Phase 5 — CLI + justfile + docs
- Add the `vocabulary` Typer sub-app and recipes.
- Add `docs/vocabularies/` page describing provenance, versions, licences, IRI
  scheme. Fold `vocab-*` into `build-all`.

### Phase 6 — Tests & verification
- Unit tests per module on synthetic fixtures; an integration test that runs the
  full fetch(local fixture)→build→merge and asserts expected triples
  (e.g. an OMOP SNOMED concept `skos:exactMatch` its `sct:` node, an ICD10CM
  `Maps to` SNOMED becomes `skos:exactMatch`).
- `just check` (lint + ty + pytest) green.

---

## 6. Data volume & performance notes
- Full Athena `CONCEPT.csv` + `CONCEPT_RELATIONSHIP.csv` are large (millions of
  rows). Use **polars lazy** (`scan_csv` + `.filter` + `.collect(streaming=True)`)
  and restrict to target `vocabulary_id`s early.
- rdflib in-memory serialization of millions of triples is slow/heavy; consider
  writing N-Triples incrementally (stream) or partitioning by vocabulary. Decide
  based on the actual filtered size; the merged graph should be scoped to the
  six target vocabularies, not the whole of OMOP.
- Keep SCTIDs/concept_ids as strings throughout to avoid int overflow / loss.
- All `pl.read_csv` calls: `separator="\t", quote_char=None` (unescaped quotes in
  names/terms).

## 7. Optional follow-up (not this increment)
- Run **snomed-owl-toolkit** (github.com/IHTSDO/snomed-owl-toolkit) on the RF2
  OWL Expression refset to produce a fully classified OWL ontology, then load it
  via rdflib for exact stated axioms (EquivalentClasses / role groups) instead of
  the lightweight `Is a`/subClassOf graph.
- Use `CONCEPT_ANCESTOR.csv` to materialise transitive hierarchy if consumers
  need closure.

## 8. Licensing & reproducibility guardrails
- **Never commit** licensed source files or large build artifacts. Add
  `data/vocabularies/` and `build/vocabularies/` to `.gitignore`.
- `sources.py` pins version + SHA-256; fetch verifies checksum. For the licensed
  RF2/Athena zips, `fetch --from-local <zip>` records the checksum of the
  user-provided file so builds are reproducible without redistributing data.
- Document required licences (SNOMED International affiliate, LOINC, and any UMLS
  requirement if CPT4 were ever added) in the docs vocabulary page.

## 9. Open questions to confirm before/at implementation
1. Exact RxNorm / ICD10 / ICD10CM IRI schemes to standardise on (proposed in §3;
   confirm against FHIR/BioPortal conventions).
2. Whether OMOP nodes should also carry `Is a` hierarchy from OMOP or rely solely
   on the SNOMED/LOINC hierarchy.
3. Whether to include `RxNorm Extension` (OMOP-minted) concepts — recommended yes,
   under the `omopconcept:` namespace since they lack a native RxNorm code.
4. Merge output format: single Turtle vs. also N-Triples for scale.
5. Confirm the LOINC-SNOMED alternate-identifier/map refset filename in the actual
   downloaded package (varies by release).

## 10. Deliverables checklist
- [ ] `src/sssom_rosetta/vocabulary/` package (sources, fetch, rf2, loinc_snomed, omop, merge)
- [ ] `rosetta vocabulary` CLI sub-app
- [ ] `justfile` recipes (`vocab-fetch`, `vocab-build`, `vocab-merge`) + `build-all`
- [ ] `build/vocabularies/loinc-snomed.ttl`, `omop.ttl`, `rosetta-vocabularies.ttl` (generated)
- [ ] `.gitignore` entries for `data/vocabularies/`, `build/vocabularies/`
- [ ] `docs/vocabularies/` provenance page
- [ ] Tests with synthetic fixtures + integration test
- [ ] `just check` green
