# Vocabulary integration (LOINC-SNOMED + SNOMED International + OMOP)

This page documents the `rosetta vocabulary` pipeline, which integrates large
terminology releases into a single RDF/Turtle graph — distinct from the curated
SSSOM mapping sets under `mappings/`.

## What it produces

`build/vocabularies/rosetta-vocabularies.ttl` — a merged SKOS/RDFS graph in which
each OMOP `concept_id` node is cross-linked to SNOMED, LOINC, RxNorm and ICD10 /
ICD10CM concepts, and to the LOINC-SNOMED Ontology hierarchy.

Intermediate artifacts, each a **separate, independently versioned graph**:
`build/vocabularies/loinc-snomed.ttl`, `build/vocabularies/snomed-international.ttl`
and `build/vocabularies/omop.ttl`. All are gitignored, generated on demand.

### Why SNOMED International is a separate graph

The LOINC-SNOMED extension package contains **only** the LOINC Extension module
(`11010000107`). Its `Is a` relationships point up to top-level SNOMED groupings
(Body structure, Clinical finding, Observable entity, Substance, …) and the root
`138875005`, but those parent concepts live in the **International core** module
(`900000000000207008`) and are **not** in the extension package. So
`loinc-snomed.ttl` on its own shows those groupings as bare, unlabelled IRIs —
i.e. a "flat" hierarchy.

Ingesting the full SNOMED CT International Edition into its own
`snomed-international.ttl` materialises those groupings (typed, labelled, linked
to the root). Because both graphs mint identical `sct:<id>` IRIs, the `merge`
step reconnects the extension concepts to the International backbone
automatically — the same mechanism that links OMOP `concept_id`s. Keeping the two
graphs separate preserves per-release provenance and lets consumers who only need
the extension skip the (large) International download.

## Sources

| Source | Format | Version | Licence / access |
|--------|--------|---------|------------------|
| LOINC-SNOMED Ontology | SNOMED CT RF2 extension (module `11010000107`) | 2.82 | SNOMED International affiliate licence + LOINC licence; download from <https://loincsnomed.org/downloads> |
| SNOMED CT International Edition | SNOMED CT RF2 (core module `900000000000207008`) | 20260101 | SNOMED International affiliate licence; download from <https://www.nlm.nih.gov/healthit/snomedct/international.html> (pin the release the LOINC extension's module-dependency refset targets) |
| OMOP Standardized Vocabularies | Athena tab-delimited CSV bundle | pinned per download | OHDSI Athena account; select `SNOMED, LOINC, RxNorm, RxNorm Extension, ICD10, ICD10CM` |

Because both are licence-gated, there is **no open download URL**. The curator
downloads the ZIP manually and ingests it; the loader verifies its SHA-256
checksum (when pinned in `vocabulary/sources.py`) and extracts it under
`data/vocabularies/<name>/<version>/`.

## IRI schemes

| Prefix | Namespace |
|--------|-----------|
| `sct` | `http://snomed.info/id/` |
| `omopconcept` | `https://w3id.org/omop/concept/` |
| `loinc` | `https://loinc.org/` |
| `rxnorm` | `http://purl.bioontology.org/ontology/RXNORM/` |
| `icd10` | `http://hl7.org/fhir/sid/icd-10/` |
| `icd10cm` | `http://hl7.org/fhir/sid/icd-10-cm/` |

Shared `sct:` / `loinc:` IRIs are what let OMOP concepts connect to the
LOINC-SNOMED hierarchy after merging.

## Relationship → SKOS mapping

| OMOP / RF2 relationship | SKOS predicate |
|-------------------------|----------------|
| OMOP `Maps to` | `skos:exactMatch` |
| OMOP `Is a`, RF2 `Is a` (116680003) | `skos:broadMatch` (child → parent) |
| OMOP `Subsumes` | `skos:narrowMatch` |
| `concept_name` / FSN | `skos:prefLabel` |
| synonyms | `skos:altLabel` |

`broadMatch` direction follows the project convention: the subject is the more
specific concept (see `AGENTS.md`).

## Workflow

```
# 1. Ingest the licence-gated release ZIPs (once per release)
just vocab-ingest loinc-snomed /path/to/SnomedCT_LOINC_Extension_...zip
just vocab-ingest snomed-international /path/to/SnomedCT_InternationalRF2_...zip
just vocab-ingest omop /path/to/athena-bundle.zip

# 2. Build and merge
just vocab-build   # build-loinc-snomed + build-snomed-international + build-omop + merge
```

`merge` combines whichever of `loinc-snomed.ttl`, `snomed-international.ttl` and
`omop.ttl` are present (at least two required), so you can build a subset — e.g.
just the extension + International — without OMOP.

## Deferred: full OWL-DL axioms

The pipeline emits a lightweight SKOS/RDFS graph from the RF2 `Relationship`
snapshot (already inferred). Materialising the full OWL logical definitions from
the OWL Expression refset (via `snomed-owl-toolkit` + ELK) is a deliberately
separate follow-up — see
`.agents/plan/2026-07-21-owl-dl-classification-deferral-note.md`.
