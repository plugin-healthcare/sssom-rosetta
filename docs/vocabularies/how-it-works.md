# How it's built

Building the vocabulary graph is a three-step process: **ingest**, **build**,
**merge**.

## 1. Ingest

A curator downloads a release (a ZIP file) and hands it to sssom-rosetta.
sssom-rosetta checks the file is the one expected, then stores it under a
version-specific folder. Nothing is guessed: every release keeps its own
copy.

## 2. Build

Each vocabulary is turned into its own graph file: one for OMOP, one for the
Diagnosethesaurus, one for the Verrichtingenthesaurus. These are built
separately, so a problem in one release never affects the others.

Every relationship in OMOP is kept in the graph, not just the handful used
for mapping, each with a readable label. For example, "has ingredient"
stays "has ingredient", instead of being collapsed into a generic term.
This means nothing gets silently dropped.

## 3. Merge

The three graphs are combined into one. Codes that already match across
vocabularies (for example, a shared SNOMED CT code) get connected
automatically.

The merge step uses [maplib](https://github.com/DataTreehouse/maplib), a
fast graph-processing tool. This matters because OMOP's release is huge,
with tens of millions of connections, and older tools would take much
longer to process it.

## Building everything at once

By default, building the vocabulary graph includes OMOP and both DHD
thesauri: they are the standard set, not optional extras. A single command
runs all three steps and produces the combined graph.
