"""Parse LOINC-SNOMED (RF2) and OHDSI/OMOP (Athena) vocabularies into RDF.

This subpackage mirrors ``ontology/`` but targets large tabular terminology
releases rather than pre-built OWL ontologies. The workflow is:

1. ``sources`` — a registry of pinned :class:`VocabularySource` entries.
2. ``fetch`` — download/cache (or accept a locally-provided licensed ZIP) and
   unzip into ``data/vocabularies/<name>/<version>/``.
3. ``rf2`` — polars readers for SNOMED CT RF2 tab-separated files.
4. ``loinc_snomed`` — RF2 → ``rdflib.Graph`` → ``loinc-snomed.ttl``.
5. ``omop`` — Athena CSV → ``rdflib.Graph`` → ``omop.ttl`` with OMOP
   ``concept_id`` nodes cross-linked to source-vocabulary concepts.
6. ``merge`` — combine the graphs into ``rosetta-vocabularies.ttl``.

Everything here produces a lightweight SKOS/RDFS graph (see
``.agents/plan/2026-07-21-owl-dl-classification-deferral-note.md`` for why full
OWL-DL axiom classification is deferred).
"""

from __future__ import annotations
