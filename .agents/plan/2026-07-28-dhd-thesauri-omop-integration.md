# Plan: Integrate DHD Diagnose-/Verrichtingenthesaurus with OMOP vocabularies

**Date:** 2026-07-28
**Status:** Draft
**Scope:** Ingest the DHD Diagnosethesaurus (DT) and Verrichtingenthesaurus (VT)
CSV releases (uitleverformaat 5.0 / 4.3), build a SKOS Turtle graph per
thesaurus, and cross-link it to the existing OMOP/LOINC-SNOMED vocabulary
graph (`.agents/plan/2026-07-21-add-snomed-loinc-omop-vocabularies.md`) via
shared SNOMED CT IRIs.

---

## 1. Source material reviewed

- Spec: `data/downloads/dhd-thesauri/Uitleverformaat-Thesauri-5.0-v1.0.pdf`
  (converted to Markdown with `docling` for review; see §9 tooling note).
- Sample releases on disk:
  - DT: `data/downloads/dhd-thesauri/DT/20250819_142606_Diagnosethesaurus_3.44_uitleverformaat4.3/`
  - VT: `data/downloads/dhd-thesauri/VT/20250813_112107_Verrichtingenthesaurus_2.43_uitleverformaat4.3/`

### 1.1 Common data model (both thesauri)

- `ThesaurusConcept`: `ConceptID` (**globally unique**, the "ThesaurusID" —
  the central key used throughout the whole model), `TypeConcept`
  (`Diagnose`/`Zorgbehoefte`/`@DBC` for DT; `Medische verrichting` etc. for
  VT), `Complicatie`, `GebruiktImplantaat`, `Lateraliteit`, `Gradatie`,
  `Begindatum`/`Mutatiedatum`/`Einddatum`, `LOINCCode` (unfilled for DT).
- `ThesaurusTerm`: one row per term of a concept — `ConceptID`, `TermID`,
  `Omschrijving`, validity dates, `TaalCode`, `TypeTerm`
  (`voorkeursterm`/`synoniem`/`PVO`/`PVT`/`FSN`/`Zoekterm`), **`SnomedID`**
  (SCTID). Per spec §4.2: "Het Snomed ID voor codes (FSN) in de DT is uniek.
  Er kunnen niet meerdere concepten zijn, die naar dezelfde Snomed ID
  verwijzen" — i.e. a given SnomedID maps to at most one active concept at a
  time (historically it may have belonged to a different, since-superseded
  concept). `SnomedID` is populated on the FSN term row(s), not on every
  term row.
- `CodeMapping`: `ConceptID` → zero, one, or many codes in another
  "codestelsel" (APACHE IV, PICE, DSM-5, KinCor, ORPHA, MSRpatientgroep, ...).
  Not used for this increment (out of scope — see §4).
- `ThesaurusConceptRelaties`, `ThesaurusConceptRol`, `SpecialismeGroep`,
  `BronSpecialisme`, `Parapluterm`: out of scope for this increment.

### 1.2 Diagnosethesaurus (DT)-specific derivations

- `AfleidingICD10`: `ConceptID` → `ICD10` (dotted code), with `Volgnummer`
  (ordering when multiple), `Advies`/`Logica` (selection guidance, not a
  data-model concern), validity + authorisation dates. Spec §4.7: "Elke
  afleiding is geassocieerd met één ThesaurusConcept en **nul of meer**
  BronICD10" → confirms zero/one/many ICD-10 codes per concept.
  `BronICD10` supplies `ICD10_code` (unique) + `ICD10_omschrijving` + version.
- `AfleidingDBC`: `ConceptID` → `DBC_ID` (nullable — a specialism can have a
  row with no DBC), `SpecialismeCode`, `Registrerend_SpecialismeCode`,
  `Volgnummer`, plus validity/authorisation dates. Spec §4.6: multiple rows
  occur per `(ConceptID, SpecialismeCode)` when there are multiple candidate
  DBCs, `Volgnummer` orders them (1 = default). `BronDBC` supplies `DBC_ID`
  (unique) + `DBC_omschrijving` + `Specialismecode` + version.
- Not used for VT (see §1.3).

### 1.3 Verrichtingenthesaurus (VT)-specific note

- Per the file-matrix in spec §2.2: VT has **no** `AfleidingDBC` /
  `AfleidingICD10` / `BronDBC` / `BronICD10` files at all — VT instead has
  `AfleidingZA`, `AfleidingConcilium`, `AfleidingUPT`, `Combinatieverrichting`.
  None of those are in scope here. **VT integration is therefore SNOMED-only**,
  via `ThesaurusTerm.SnomedID`, confirming the user's instruction.

---

## 2. Mapping semantics (per user decision + AGENTS.md conventions)

| Source column | Target | SKOS predicate | Cardinality |
|---|---|---|---|
| `ThesaurusTerm.SnomedID` (DT + VT) | `sct:<SnomedID>` | `skos:exactMatch` | 0 or 1 per concept (spec: unique SCTID per active DT concept) |
| `AfleidingICD10.ICD10` (DT only) | `icd10:<code>` | `skos:closeMatch` | 0, 1, or many per concept |
| `AfleidingDBC.DBC_ID` (DT only) | `dbc:<DBC_ID>` | `skos:closeMatch` | 0, 1, or many per concept |

- `skos:exactMatch` for SNOMED reflects the user's instruction and the 1:1,
  stable-identity nature of the FSN/SCTID link.
- `skos:closeMatch` (not `broadMatch`/`narrowMatch`) for ICD10/DBC because
  these are **derivations for administrative/classification purposes**
  (billing, registries), not asserted subsumption relationships between DHD
  and ICD10/DBC concepts — this matches AGENTS.md's general preference order
  (`exactMatch`/`broadMatch`/`narrowMatch` over `relatedMatch`) while
  correctly avoiding a false claim of hierarchical/exact identity.
- `Volgnummer`, `Advies`, `Logica`, authorisation dates are **not** modelled
  as RDF for this increment (recorded as an open question, §7).

---

## 3. IRI & namespace decisions

Reuse/extend `src/sssom_rosetta/vocabulary/namespaces.py`:

| Prefix | Namespace | Used for |
|---|---|---|
| `dhddt` | `https://w3id.org/dhd/diagnosethesaurus/concept/` | DT `ConceptID` nodes |
| `dhdvt` | `https://w3id.org/dhd/verrichtingenthesaurus/concept/` | VT `ConceptID` nodes |
| `sct` | `http://snomed.info/id/` | *(existing)* SNOMED SCTIDs — shared with the OMOP/LOINC-SNOMED graph |
| `icd10` | `http://hl7.org/fhir/sid/icd-10/` | *(existing)* WHO ICD-10 (dotted) codes |
| `dbc` | `https://w3id.org/dhd/dbc/` | **new** — DBC diagnosis codes (no stable external IRI scheme found; DBC codes are NZa/DHD-internal, not per-specialism-namespaced in the source data) |

DT and VT get **separate concept namespaces** (`dhddt:`/`dhdvt:`) even though
each `ConceptID` is globally unique within its own thesaurus release, because
the two thesauri are independent code systems (a DT `ConceptID` and a VT
`ConceptID` could coincidentally collide as strings) and keeping them
distinct matches the existing per-source-vocabulary IRI convention in
`namespaces.py`.

Reusing the existing `sct:` and `icd10:` namespaces from
`vocabulary/namespaces.py` is what lets DHD concepts connect to the
already-planned OMOP/LOINC-SNOMED graph after merging (same mechanism as
`merge.py` §description).

---

## 4. Scope for this increment

### Goals
1. Parse DT `ThesaurusConcept` + `ThesaurusTerm` + `AfleidingICD10` +
   `AfleidingDBC` with polars → SKOS Turtle (`dhd-diagnosethesaurus.ttl`).
2. Parse VT `ThesaurusConcept` + `ThesaurusTerm` (SNOMED only) with polars →
   SKOS Turtle (`dhd-verrichtingenthesaurus.ttl`).
3. Wire both into the existing `rosetta vocabulary` CLI + `merge` step so DHD
   concepts land in the same merged `rosetta-vocabularies.ttl` as OMOP/LOINC-
   SNOMED, connected via shared `sct:`/`icd10:` IRIs.
4. Respect DHD's temporal validity model (`Begindatum`/`Einddatum`) — only
   emit triples for currently-active rows.

### Non-goals (this increment)
- `CodeMapping` (APACHE IV/PICE/DSM-5/KinCor/ORPHA/MSRpatientgroep) — not
  requested; revisit if a future increment needs it.
- `ThesaurusConceptRelaties`, `ThesaurusConceptRol`, `SpecialismeGroep`,
  `Parapluterm`, `Combinatieverrichting`, and VT's ZA/Concilium/UPT
  derivations — out of scope.
- Modelling `Volgnummer` ordering, `Advies`/`Logica` selection guidance, or
  authorisation date ranges as RDF (see open question §7).
- Re-fetch/versioning automation for DHD releases (these are licence-gated,
  curator-provided ZIPs like LOINC-SNOMED/OMOP — same pattern as
  `vocabulary/sources.py` + `fetch.py`, see §5).

---

## 5. Architecture: extend the existing `vocabulary/` package

Mirror the `omop.py` / `rf2.py` pattern already in
`src/sssom_rosetta/vocabulary/`:

```
src/sssom_rosetta/vocabulary/
  namespaces.py       # extend: add dhddt:, dhdvt:, dbc: to PREFIX_MAP
  sources.py           # extend: register "dhd-diagnosethesaurus", "dhd-verrichtingenthesaurus" VocabularySource entries (kind="dhd-csv")
  dhd.py               # NEW: polars readers + SKOS graph builder for DT + VT
  merge.py             # no change needed — already generic over any Graph
tests/vocabulary/
  test_dhd.py          # NEW
  fixtures/dhd/         # NEW: tiny synthetic ThesaurusConcept/ThesaurusTerm/AfleidingICD10/AfleidingDBC CSVs (DT) and ThesaurusConcept/ThesaurusTerm (VT)
```

### `dhd.py` design (mirrors `omop.py`)

- `_scan_dhd(path)`: `pl.scan_csv(path, quote_char='"', infer_schema_length=0)`
  — note DHD files are **comma-separated with quoted fields** (unlike RF2/
  Athena's tab-separated), per spec §2.2.2. All columns read as `Utf8`.
- `_active(df)`: filter rows where today (or a pinned as-of date) falls
  within `[Begindatum, Einddatum]` — DHD's temporal-validity convention
  (spec §3.3). Parametrize the as-of date for reproducible builds.
- `load_concepts(thesaurus_concept_csv)` → concepts with `ConceptID`,
  `TypeConcept`.
- `load_snomed_terms(thesaurus_term_csv)` → one row per `ConceptID` with a
  non-empty `SnomedID` on an active FSN term (dedupe: spec guarantees at most
  one active SnomedID per concept at any point in time).
- `load_icd10(afleiding_icd10_csv)` (DT only) → `(ConceptID, ICD10)` pairs,
  active rows, deduplicated by `Volgnummer` if needed (kept — cardinality is
  intentionally 0..N).
- `load_dbc(afleiding_dbc_csv)` (DT only) → `(ConceptID, DBC_ID)` pairs,
  active rows, **excluding rows where `DBC_ID` is empty** (spec §4.6: a row
  may exist for a specialism with no DBC).
- `build_graph(thesaurus: Literal["dt", "vt"], concepts, snomed_terms,
  icd10=None, dbc=None) -> Graph`:
  - `dhddt:<ConceptID>` / `dhdvt:<ConceptID>` `a skos:Concept`.
  - `... skos:exactMatch sct:<SnomedID>` when present.
  - DT only: `... skos:closeMatch icd10:<code>` for each ICD10 row;
    `... skos:closeMatch dbc:<DBC_ID>` for each DBC row.
- `build_from_release(release_dir, thesaurus) -> Graph`: locate files by
  exact name (reuse `fetch.find_file`), dispatch DT vs VT column set.
- `write_ttl` — reuse `omop.write_ttl` (already generic) rather than
  duplicating.

### CLI (`cli.py`, `vocabulary_app`)

Add, following the existing `vocabulary build-omop` pattern:
- `rosetta vocabulary build-dhd-diagnosethesaurus <release_dir>` →
  `build/vocabularies/dhd-diagnosethesaurus.ttl`
- `rosetta vocabulary build-dhd-verrichtingenthesaurus <release_dir>` →
  `build/vocabularies/dhd-verrichtingenthesaurus.ttl`
- Fold both into the existing `vocabulary merge` inputs.

### `justfile`

Add `vocab-build-dhd-dt`, `vocab-build-dhd-vt` recipes; fold into
`vocab-build`/`build-all`.

---

## 6. Temporal validity handling

Spec §3.3 confirms DHD uses `Begindatum`/`Mutatiedatum`/`Einddatum` on every
row (concepts, terms, and derivations independently) to model changes over
time — a concept, a term, and a derivation can each have their own validity
window. For a single reproducible graph build:
- Filter to rows valid on a single **as-of date** (default: build time,
  overridable via a CLI option) independently per table — a concept could be
  active while a specific ICD10 derivation for it has since expired.
- Document this as a simplification: no temporal/versioned RDF (e.g. no
  reified validity intervals) in this increment — only the single as-of
  snapshot is materialized.

---

## 7. Open questions to confirm before/at implementation

1. **DBC IRI scheme**: no external stable URI scheme found for NZa DBC
   diagnosis codes; proposed `https://w3id.org/dhd/dbc/{DBC_ID}` — confirm or
   supply an authoritative alternative (e.g. if NZa/DHD publish one).
2. Should `Volgnummer` ordering / `Advies` / `Logica` be captured (e.g. as
   `skos:notation` "rank" or `rdf:List`) in a follow-up, or dropped entirely
   as UI/EPD-only guidance? Current plan: drop.
3. Confirm whether DT `TypeConcept` (`Diagnose`/`Zorgbehoefte`/`@DBC`) and VT
   `TypeConcept` (`Medische verrichting`, ...) should be modelled as
   `skos:Concept` subtypes / an extra triple (e.g. `dct:type`) — not
   requested but likely useful downstream; default: out of scope, revisit.
3. As-of-date default: build time vs. pinning to the release's own
   "content version" (e.g. `3.44` for DT) — recommend the latter for
   reproducible builds (same day every time the same release is rebuilt).
4. `AfleidingICD10.ICD10` values are dotted-format ICD-10 (`G52.3`) —
   confirm this matches the `icd10:` namespace's existing code format
   convention in `namespaces.py` (used by OMOP `ICD10` vocabulary rows) so
   the two graphs' `icd10:` IRIs actually coincide on merge.

---

## 8. Deliverables checklist

- [ ] `namespaces.py`: add `dhddt:`, `dhdvt:`, `dbc:` prefixes
- [ ] `sources.py`: register DHD DT/VT `VocabularySource` entries
- [ ] `dhd.py`: readers + graph builder (DT full, VT SNOMED-only) + tests
- [ ] `tests/vocabulary/fixtures/dhd/`: tiny synthetic CSVs for DT and VT
- [ ] `cli.py`: `vocabulary build-dhd-diagnosethesaurus` /
      `build-dhd-verrichtingenthesaurus` commands, folded into `merge`
- [ ] `justfile`: recipes folded into `vocab-build`/`build-all`
- [ ] `docs/vocabularies/` provenance entry (licence: DHD/Mijn DHD terms)
- [ ] `just check` (lint + ty + pytest) green

---

## 9. Tooling note: PDF spec review

The spec PDF was converted to Markdown using **docling**
(`docling.document_converter.DocumentConverter`) rather than `pypdf`/
`pymupdf4llm`, per explicit instruction. docling's dependency chain
(`docling` → `docling-slim` → `docling-core`) pins `typer<0.25.0`, which
conflicts with this project's `typer>=0.26,<0.27` (required by the `rosetta`
CLI). Resolution:
- Forked `docling-project/docling-core` → `plugin-healthcare/docling-core`
  (branch `fix/relax-typer-upper-bound`), relaxing the pin to
  `typer>=0.12.5,<0.27.0` — matching docling's own already-loosened
  constraint. Verified docling-core's CLI (`docling_core/cli/{serialize,
  view}.py`) only uses stable Typer/Click APIs (`Typer`, `Exit`, `Argument`,
  `Option`, `BadParameter`, `echo`, `typer.main.get_command`) and works
  correctly under typer 0.26.8.
- Wired via `[tool.uv.sources]` in `pyproject.toml`:
  `docling-core = { git = "https://github.com/plugin-healthcare/docling-core", branch = "fix/relax-typer-upper-bound" }`,
  plus an explicit `docling-core` entry in the `dev` dependency group (uv
  only honours `[tool.uv.sources]` overrides for packages that are direct
  dependencies somewhere in the project).
- `docling` pinned to `>=2.92,<=2.113` in the `dev` group (uv's
  `exclude-newer = "14 days"` policy excludes the newest published
  `docling` releases; this range is the newest available within the
  cutoff window that resolves cleanly against the forked `docling-core`).
- This is dev-only tooling (spec review), not a runtime dependency of the
  `dhd.py` ingestion pipeline itself, which only needs `polars` + `rdflib`
  (already project dependencies).
