# Vocabulary integration (LOINC-SNOMED + SNOMED International + OMOP + DHD)

This page documents the `rosetta vocabulary` pipeline, which integrates large terminology releases into a single RDF/Turtle graph — distinct from the curated SSSOM mapping sets under `mappings/`.

## What it produces

`build/vocabularies/rosetta-vocabularies.ttl` — a merged SKOS/RDFS graph in which each OMOP `concept_id` node is cross-linked to SNOMED, LOINC, RxNorm and ICD10 / ICD10CM concepts, and to the LOINC-SNOMED Ontology hierarchy.

Intermediate artifacts, each a **separate, independently versioned graph**: `build/vocabularies/loinc-snomed.ttl`, `build/vocabularies/snomed-international.ttl`, `build/vocabularies/omop.ttl`, `build/vocabularies/dhd-diagnosethesaurus.ttl` and `build/vocabularies/dhd-verrichtingenthesaurus.ttl`.
All are gitignored, generated on demand.

### Why SNOMED International is a separate graph

The LOINC-SNOMED extension package contains **only** the LOINC Extension module (`11010000107`).
Its `Is a` relationships point up to top-level SNOMED groupings (Body structure, Clinical finding, Observable entity, Substance, …) and the root `138875005`, but those parent concepts live in the **International core** module (`900000000000207008`) and are **not** in the extension package.
So `loinc-snomed.ttl` on its own shows those groupings as bare, unlabelled IRIs — i.e. a "flat" hierarchy.

Ingesting the full SNOMED CT International Edition into its own `snomed-international.ttl` materialises those groupings (typed, labelled, linked to the root).
Because both graphs mint identical `sct:<id>` IRIs, the `merge` step reconnects the extension concepts to the International backbone automatically — the same mechanism that links OMOP `concept_id`s.
Keeping the two graphs separate preserves per-release provenance and lets consumers who only need the extension skip the (large) International download.

## Sources

| Source | Format | Version | Licence / access |
|--------|--------|---------|------------------|
| LOINC-SNOMED Ontology | SNOMED CT RF2 extension (module `11010000107`) | 2.82 | SNOMED International affiliate licence + LOINC licence; download from <https://loincsnomed.org/downloads> |
| SNOMED CT International Edition | SNOMED CT RF2 (core module `900000000000207008`) | 20260101 | SNOMED International affiliate licence; download from <https://www.nlm.nih.gov/healthit/snomedct/international.html> (pin the release the LOINC extension's module-dependency refset targets) |
| OMOP Standardized Vocabularies | Athena tab-delimited CSV bundle | pinned per download | OHDSI Athena account; select `SNOMED, LOINC, RxNorm, RxNorm Extension, ICD10, ICD10CM` |
| DHD Diagnose-/Verrichtingenthesaurus | CSV bundle, **uitleverformaat4.3** (both DT and VT) | DT 3.44 / VT 2.43 (combined release `202508`) | Mijn DHD terms; download from <https://mijn.dhd.nl/> |

Because both are licence-gated, there is **no open download URL**.
The curator downloads the ZIP manually and ingests it; the loader verifies its SHA-256 checksum (when pinned in `vocabulary/sources.py`) and extracts it under `data/vocabularies/<name>/<version>/`.

## IRI schemes

| Prefix | Namespace |
|--------|-----------|
| `sct` | `http://snomed.info/id/` |
| `omopconcept` | `https://w3id.org/omop/concept/` |
| `loinc` | `https://loinc.org/` |
| `rxnorm` | `http://purl.bioontology.org/ontology/RXNORM/` |
| `icd10` | `http://hl7.org/fhir/sid/icd-10/` |
| `icd10cm` | `http://hl7.org/fhir/sid/icd-10-cm/` |
| `dhddt` | `https://w3id.org/dhd/diagnosethesaurus/concept/` |
| `dhdvt` | `https://w3id.org/dhd/verrichtingenthesaurus/concept/` |
| `dbc` | `https://w3id.org/dhd/dbc/` |

Shared `sct:` / `loinc:` IRIs are what let OMOP concepts connect to the LOINC-SNOMED hierarchy after merging.
DHD DT/VT concepts connect the same way via shared `sct:` (SNOMED FSN match) and `icd10:` (DT's ICD10 derivation, same namespace as OMOP's ICD10 rows) IRIs.

## Relationship → SKOS mapping

| OMOP / RF2 relationship | SKOS predicate |
|-------------------------|----------------|
| OMOP `Maps to` | `skos:exactMatch` |
| OMOP `Is a`, RF2 `Is a` (116680003) | `skos:broadMatch` (child → parent) |
| OMOP `Subsumes` | `skos:narrowMatch` |
| `concept_name` / FSN | `skos:prefLabel` |
| synonyms | `skos:altLabel` |
| DHD `ThesaurusTerm.SnomedID` (DT + VT) | `skos:exactMatch` |
| DHD `AfleidingICD10.ICD10` (DT only) | `skos:closeMatch` |
| DHD `AfleidingDBC.DBC_ID` (DT only) | `skos:closeMatch` |

`broadMatch` direction follows the project convention: the subject is the more specific concept (see [Authoring SSSOM mappings](../mappings/authoring.md)).
DHD's ICD10/DBC derivations use `closeMatch` rather than `broadMatch`/`narrowMatch` because they are administrative/classification derivations, not asserted subsumption relationships.

## Workflow

```
# 1. Ingest the licence-gated release ZIPs (once per release)
just vocab-ingest omop /path/to/athena-bundle.zip
just vocab-ingest dhd-thesauri /path/to/dhd-thesauri-<release>.zip
just vocab-ingest loinc-snomed /path/to/SnomedCT_LOINC_Extension_...zip           # optional
just vocab-ingest snomed-international /path/to/SnomedCT_InternationalRF2_...zip  # optional

# 2. Build and merge
just vocab-build   # build-omop + build-dhd-dt + build-dhd-vt + merge (all standard, not optional)
```

`merge` combines whichever of `omop.ttl`, `dhd-diagnosethesaurus.ttl`, `dhd-verrichtingenthesaurus.ttl`, `loinc-snomed.ttl` and `snomed-international.ttl` are present (at least one required).
OMOP and both DHD thesauri are standard, always-built inputs; the native RF2 graphs remain opt-in (`vocab-build-loinc-snomed` / `vocab-build-snomed-international` + `vocab-merge`) for the deferred OWL-DL follow-up.

## Why DHD uitleverformaat4.3 is pinned explicitly

DHD ("Dutch Hospital Data") publishes the Diagnosethesaurus (DT) and Verrichtingenthesaurus (VT) as CSV bundles in a versioned "uitleverformaat" (delivery format).
`dhd.py` targets **uitleverformaat4.3 only**: the reviewed spec PDF describes a different, 5.0 file layout that this module does not parse.
`dhd.FORMAT_VERSION` is asserted (not just documented) against the release directory layout, so a future non-4.3 release fails fast instead of silently mis-parsing columns that moved between spec versions.

DHD rows carry their own `Begindatum`/`Einddatum` validity window.
`dhd._active` filters each table independently to the rows valid on a single as-of date; this is a deliberate temporal-validity simplification for this increment (no reified validity intervals).

## Why maplib/OTTR instead of rdflib

`omop.py` and `dhd.py` assemble their graphs with **maplib**, not `rdflib`: concept nodes and cross-links are built by mapping polars DataFrames through declarative OTTR (stOTTR) templates (`vocabulary/templates.py`) via `Model.map`, instead of a hand-written Python triple-add loop.
A leading `?` on a template parameter marks it *optional*, and maplib silently omits any triple that uses an unbound optional variable for a given row — this replaces the `if row[...]:` branches a hand-written loop would otherwise need.
`loinc_snomed.py` and `snomed_international.py` still build an `rdflib.Graph`; `merge.merge_graphs` accepts either kind of graph object and normalises both to rdflib triples before merging.

## Deferred: full OWL-DL axioms

The pipeline emits a lightweight SKOS/RDFS graph from the RF2 `Relationship` snapshot (already inferred).
Materialising the full OWL logical definitions from the OWL Expression refset (via `snomed-owl-toolkit` + ELK) is a deliberately separate follow-up, not yet scheduled.
