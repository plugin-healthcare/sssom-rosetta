# AGENTS.md — sssom-rosetta

## Dev environment

- adhere to instructions, skills, prompts and recipse as defined by wingman in `.wingman`

## Authoring of SSSOM mappings

- Follow the `skos:broadMatch`/`skos:narrowMatch`/`skos:exactMatch` conventions documented in
  [docs/mappings/authoring.md](docs/mappings/authoring.md); do not duplicate that content here.

## Architectural decisions log

- **Predicates**: no curated allowlist. Any `predicate_id` value permitted by the `sssom-schema` LinkML range is accepted; validation relies on schema   conformance rather than an app-level list.
- **sssom-schema version**: pinned to a specific released tag in `pyproject.toml` (e.g. `sssom-schema==<x.y.z>`); `models/sssom.py` is regenerated only on a deliberate version bump, never against `main`.
- **PR review**: rendered Markdown/HTML report is generated per PR (see CI section above) in addition to the raw TSV diff.
- **Documentation site**: static site under `/docs`, built with Zensical, published to GitHub Pages on merge to `main`. Mapping pages are generated from the same renderer as the PR report, not hand-maintained.
- **CLI name**: the console script is `rosetta` (not `sssom-rosetta`), configured via `[project.scripts]` in `pyproject.toml`; the Python package/import path remains `sssom_rosetta`.
- **CSV as authored source**: mapping sets are hand-edited as CSV under `mappings/*.csv`, each paired with a CSVW metadata file `mappings/*.metadata.json` (https://csvw.org, W3C Tabular Metadata), declaring column datatypes and `valueUrl` URI templates for the `*_id` columns. `rosetta mapping build` derives the canonical SSSOM/TSV (with YAML header) and an RDF/TTL representation into `build/mappings/`, using the CSVW `csv2rdf` conversion as the basis for the TTL; these are generated artifacts, gitignored, never hand-edited, and never the source for the CSV+CSVW pair.
