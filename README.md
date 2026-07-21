# sssom-rosetta

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![SSSOM](https://img.shields.io/badge/format-SSSOM-6f42c1.svg)](https://mapping-commons.github.io/sssom/)
[![Built with uv](https://img.shields.io/badge/built%20with-uv-de5fe9.svg)](https://github.com/astral-sh/uv)

> **TL;DR** — sssom-rosetta integrates the ontologies and vocabularies used in
> Dutch healthcare into one validated, reproducible graph, using
> [SSSOM](https://mapping-commons.github.io/sssom/) as the interchange format for
> the mappings between them.

---

## Project vision

Healthcare data integration in the Netherlands constantly needs crosswalks
between international reference models (OMOP CDM, FHIR, SNOMED CT, LOINC) and
Dutch domain models (ONZ-G, Z-Index, the DHD thesauri). Today those crosswalks
live in hand-maintained spreadsheets that drift from the ontologies they
describe and are hard to validate, review, or reuse.

**The core aim of sssom-rosetta is to integrate the ontologies and vocabularies
of the Dutch healthcare domain into a single, machine-checkable graph**, built on
a few principles:

- **Ontologies are the source of truth.** Entity lists are never hand-authored;
  every mapped concept must resolve in a loaded ontology graph.
- **SSSOM is the wire format.** Mappings are authored as typed CSV, validated
  against the SSSOM schema, and exchanged as SSSOM/TSV — interoperable with the
  wider `sssom-py` / SSSOM Toolkit ecosystem.
- **Everything is reproducible.** Sources are pinned by version/commit, generated
  artifacts are derived on demand, and a single command reproduces the whole
  pipeline.

Unlike the earlier
[linkml-rosetta](https://docs.plugin.dhd.nl/linkml-rosetta/) prototype, which
mapped between LinkML *schemas*, this project starts from existing RDF/OWL
*ontologies* as the source of truth and treats SSSOM as the format for the
mappings themselves.

---

## Integration ecosystem

sssom-rosetta integrates two complementary kinds of artifact: **ontologies**
(information models, mapped pairwise with curated SSSOM mappings) and
**vocabularies** (large terminologies, integrated as a reference graph).

### Ontologies

Curated, hand-authored SSSOM mappings between information models. The first pair
mapped:

| Ontology | Version | IRI | Source |
|----------|---------|-----|--------|
| **ONZ-G** (Een Ontologie voor de Nederlandse Zorg — Generiek) | 2.8.1 | `http://purl.org/ozo/onz-g` | [KIK-V publicatieplatform](https://kik-v-publicatieplatform.nl/ontologie/onz-g/2.8.1) |
| **OMOP CDM OWL** (generated from OMOP CDM v5.4) | 5.4 | `https://w3id.org/omop/ontology/` | [omop-cdm-owl](https://github.com/plugin-healthcare/omop-cdm-owl) |

Example mapping: `omop:Person skos:exactMatch onz-g:Client`.

**Roadmap — FHIR ⇄ OMOP integration.** The next major ontology axis is a
FHIR-to-OMOP mapping, anchored in the
[HL7 Vulcan](https://confluence.hl7.org/display/VA) accelerator work and the
[linkml-rosetta](https://docs.plugin.dhd.nl/linkml-rosetta/) legacy that
originally explored FHIR ⇄ OMOP schema alignment. sssom-rosetta will carry that
forward as ontology-first SSSOM mappings rather than LinkML-schema mappings.

### Vocabularies

Where ontologies are mapped pairwise, **vocabularies** are integrated as a single
reference graph that mappings and ETL pipelines can plug into. The goal is to
make terminologies **plug-and-play**: a curator ingests a release, and every
`concept_id` / code becomes a resolvable node other mappings can point at.

- **OMOP is the base layer.** The OHDSI/OMOP Standardized Vocabularies already
  harmonise SNOMED CT International, LOINC, RxNorm, and ICD-10/CM into one concept
  space with a pre-computed hierarchy — so we do **not** separately ingest SNOMED
  or LOINC for the default graph.
- **Dutch-domain vocabularies are layered on top** (what OMOP does not contain):
  KIK-V ONZ-G (available), and — on the roadmap — Z-Index (G-Standaard), the DHD
  Diagnosethesaurus, and the DHD Verrichtingenthesaurus.
- **The OMOPHub model** ([omophub-python](https://github.com/OMOPHub/omophub-python))
  informs how we expose these vocabularies programmatically — concepts,
  hierarchy, relationships, mappings, and search over a versioned,
  snapshot-per-release store — so the integrated vocabulary can drive both
  mapping authoring and downstream ETL. See
  `.agents/design/2027-07-21-choice-of-backend.md` for the backend options under
  consideration.

---

## Getting started

### Install

```
uv sync --all-groups
```

`just` (a command runner) is installed as a dev dependency, so `uv sync` alone is
enough. Run recipes via `uv run just <recipe>` (or `just <recipe>` if `just` is on
your `PATH`). Run `just` with no arguments to list every recipe.

### Quick start

```
# Fetch the pinned source ontologies (omop-cdm, onz-g)
just fetch

# Validate a mapping set (CSV + CSVW metadata)
just validate

# Build the derived SSSOM/TSV + RDF/TTL artifacts
just build

# Run the whole local pipeline (fetch → validate → build → report → docs)
just build-all

# Lint + type-check + tests
just check
```

Author a mapping programmatically:

```python
from sssom_rosetta.mapping.author import build_mapping

mapping = build_mapping(
    subject_curie="omop:Person",
    predicate="skos:exactMatch",
    object_curie="onz-g:Client",
    mapping_justification="semapv:ManualMappingCuration",
    author_id="orcid:0000-0000-0000-0000",
    confidence=0.9,
)
```

`build_mapping` rejects unresolvable IRIs before the object is constructed, so an
invalid mapping never reaches the build.

---

## Architecture & technical details

### Design principles

1. **Ontologies are the source of truth.** Every `subject_id`/`object_id` is
   validated against a loaded RDF graph before a mapping is accepted.
2. **SSSOM is the wire format, Pydantic is the authoring interface.** Mappings are
   authored as Python objects and serialized to SSSOM/TSV (+ YAML header).
3. **CSVW is the human-authored source of truth; TSV and TTL are derived.**
   Curators edit `mappings/<name>.csv` paired with `mappings/<name>.metadata.json`
   ([CSVW](https://csvw.org)), declaring column datatypes and `valueUrl` URI
   templates. The direction is strictly CSVW → {TSV, TTL}, never the reverse.
4. **Ontology-first, code-generated models.** `models/sssom.py` is generated by
   LinkML's `gen-pydantic` from the pinned
   [`sssom-schema`](https://github.com/mapping-commons/sssom-schema) — never
   hand-edited.
5. **Validation over convention.** Every mapping is checked against the SSSOM
   schema, IRI existence in the source graphs, and the full `predicate_id` value
   space (no curated allowlist).
6. **Reproducible fetch & schema.** Sources are pinned by version/commit;
   `sssom-schema` is pinned to a released tag so generated models only change on a
   deliberate bump.

### Repository layout

```
src/sssom_rosetta/
  models/sssom.py        # generated Pydantic models (gen-pydantic output)
  ontology/              # source registry, rdflib loader/cache, class/property catalog
  mapping/               # author, validate, io (CSVW→TSV/TTL), report, protege
  vocabulary/            # OMOP/RF2 ingest → reference vocabulary graph
  cli.py                 # typer app, installed as the `rosetta` console script
mappings/                # curated CSV + CSVW metadata (the only PR-reviewed source)
data/                    # cached ontology + vocabulary downloads (gitignored)
build/                   # generated SSSOM/TSV, TTL, reports (gitignored)
docs/                    # Zensical static site
tests/                   # offline fixtures for ontology + mapping + vocabulary
```

### Mapping workflow (CSVW → SSSOM)

1. **Fetch** — `rosetta ontology fetch <name>` caches the pinned TTL and records
   checksum + source URL.
2. **Catalog** — the loader parses TTL into an `rdflib.Graph`; `catalog.py`
   exposes class/property/label lookups used by authoring and validation.
3. **Author** — edit rows in `mappings/*.csv` (SSSOM core columns) with a paired
   CSVW `*.metadata.json`.
4. **Validate** — `rosetta mapping validate` checks CSVW shape conformance, SSSOM
   schema conformance, and ontology referential integrity.
5. **Build** — `rosetta mapping build` writes the canonical `.sssom.tsv` (YAML
   header via `sssom-py`) and an RDF/Turtle representation.
6. **Report** — CI renders a Markdown/HTML diff of added/removed/changed mappings
   on every PR touching `mappings/**`.

### SKOS mapping semantics

When authoring, mind the direction and **transitivity** of SKOS predicates:

- `skos:broadMatch` reads as *"has broader concept"* — the **subject** is the more
  specific concept, the object the more generic. `skos:narrowMatch` is the
  inverse. A concept may have several broader concepts.
- **`skos:exactMatch` is transitive** (chains propagate); **`skos:closeMatch`,
  `broadMatch`, `narrowMatch` are not** — the W3C SKOS Reference deliberately
  omits `broadMatchTransitive`/`narrowMatchTransitive` to discourage unsafe
  cross-vocabulary reasoning. When in doubt, prefer the weaker,
  non-transitive claim over `exactMatch`.

### Vocabulary integration

The `rosetta vocabulary` sub-app builds a reference graph from the OMOP base
(plus optional native SNOMED/LOINC RF2 for the deferred OWL-DL follow-up). OMOP
relationships map to SKOS (`Maps to` → `exactMatch`, `Is a` → `broadMatch`,
`Subsumes` → `narrowMatch`). Releases are licence-gated, so `vocab-*` recipes are
intentionally **not** part of `build-all`; the curator ingests a downloaded ZIP
first. See `docs/vocabularies/index.md` and the callout above for full detail.

### Protégé as a viewer

`rosetta protege build` merges both source ontologies with the mapping set into a
single Turtle file for exploration in [Protégé](https://protege.stanford.edu),
emitting each mapping as an OWL class-level axiom (so OntoGraf and the reasoner
render the mapping edges). See `docs/` for the full Protégé setup.

### Key dependencies

`rdflib` (graph loading/SPARQL), `csvw` (CSVW parsing + `csv2rdf`), `linkml`
(`gen-pydantic`), `sssom` / `sssom-schema` (SSSOM I/O + schema), `pydantic`
(runtime validation), `typer` (the `rosetta` CLI), `polars` (tabular + RF2/Athena
parsing), `zensical` (docs site).

### Testing

```
uv run pytest        # or: just test / just check
```

Follows TDD: fixtures are small extracted subgraphs, tests run offline and never
hit the network (`ontology fetch` is tested against mocked HTTP).

---

## Contributing & roadmap

### Contributing

Contributions follow standard GitHub flow: fork or branch, edit the CSV+CSVW
mapping sets or the `sssom_rosetta` package, run `uv run pytest`, and open a PR.
Every PR touching `mappings/**` gets automated validation and a rendered mapping
diff report. Contributors and ORCIDs are tracked in `mappings/contributors.csv`.

Design rationale and open decisions live in `.agents/plan/` and
`.agents/design/` — check there before re-litigating a settled choice.

### Roadmap

- **FHIR ⇄ OMOP** ontology mappings, anchored in HL7 Vulcan / linkml-rosetta.
- **Dutch-domain vocabularies:** Z-Index (G-Standaard), DHD Diagnosethesaurus, DHD
  Verrichtingenthesaurus.
- **Vocabulary backend** for plug-and-play mappings/ETL — an OMOPHub-compatible
  API over a single-node store (DuckDB / QLever / LadybugDB under evaluation; see
  `.agents/design/2027-07-21-choice-of-backend.md`).
- **Deferred:** full OWL-DL classification of native SNOMED
  (`.agents/plan/2026-07-21-owl-dl-classification-deferral-note.md`).

### Getting help

Open an issue for bugs, questions, or mapping proposals.
