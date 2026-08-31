# Sources

sssom-rosetta combines a small number of large, licensed vocabularies. Each
one keeps its own version, so it's always clear which release a code came
from.

## OMOP Standardized Vocabularies

The base layer. OHDSI's Athena bundle brings SNOMED CT, LOINC, RxNorm and
ICD-10/ICD-10-CM together in one place, with relationships already worked
out between them. Access requires an OHDSI Athena account.

## DHD Diagnosethesaurus (DT)

The Dutch national thesaurus of diagnosis codes, maintained by DHD. Used to
add Dutch diagnosis terms that OMOP doesn't have. Access requires a Mijn DHD
account. Both the diagnosis and procedure thesauri are delivered in the same
format, **uitleverformaat 4.3**.

## DHD Verrichtingenthesaurus (VT)

The Dutch national thesaurus of procedure codes, maintained by DHD. Same
access and format as the Diagnosethesaurus above.

## Why no open downloads

All of these vocabularies are licence-gated: there's no public download
link. A curator downloads the release manually and hands it to
sssom-rosetta, which then checks and stores it.

## Planned: Z-Index (G-Standaard)

Z-Index's G-Standaard, the Dutch medicines reference, is on the
[roadmap](../roadmap.md) as a future addition to the vocabulary graph.
