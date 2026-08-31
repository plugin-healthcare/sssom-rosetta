# Roadmap

What's planned next for sssom-rosetta.

## FHIR ⇄ OMOP mappings

The next big step is mapping FHIR to OMOP. This builds on earlier work from
the HL7 Vulcan accelerator and the linkml-rosetta project. Unlike that
earlier work, these mappings will be ontology-first, using SSSOM.

## More Dutch vocabularies

The OMOP base is now joined by the DHD Diagnosethesaurus and
Verrichtingenthesaurus. Next up: Z-Index's G-Standaard, the Dutch reference
for medicines.

## A vocabulary backend

Right now the combined vocabulary graph is a file. The plan is to serve it
through a proper backend, so mappings and other tools can query it directly,
without needing their own copy of the file.

## Deferred: deeper SNOMED reasoning

SNOMED CT supports a richer, formal style of reasoning (OWL-DL) than the
current graph provides. Adding that is deliberately on hold: it's a bigger
piece of work that isn't needed for the mappings we support today.
