# sssom-rosetta

Dutch healthcare data uses many different models. OMOP CDM, FHIR, SNOMED CT and LOINC are international standards. ONZ-G, Z-Index and the DHD thesauri are Dutch. Today, the links between them live in spreadsheets that go out of date fast.

sssom-rosetta brings these models together in one place. It checks that every mapping points to something real. It uses [Turtle (Terse RDF Triple Language)](https://www.w3.org/TR/turtle/) as the shared format for ontologies and vocabularies, while [SSSOM](https://mapping-commons.github.io/sssom/) is used for the for mappings, so they stay easy to read, review and reuse.

## Two kinds of building blocks

- **[Ontologies](ontologies/onz-g.md)** are information models. We map them to each other, one pair at a time, by hand. See [Mappings](mappings/omop-onz-g.md) for the current mapping set.
- **[Vocabularies](vocabularies/index.md)** are large code lists and terminologies, such as OMOP's standard vocabularies and the DHD thesauri. We combine them into one graph using [maplib](https://datatreehouse.github.io/documentation/), so every code becomes something other mappings can point at.

## Where this is going

The aim of sssom-rosetta is to expose these vocabularies programmatically — concepts, hierarchy, relationships, mappings, and search over a versioned, snapshot-per-release store — so the integrated vocabulary can drive both mapping authoring and downstream ETL. We take inspiration from ([omophub-python](https://github.com/OMOPHub/omophub-python)).

See the [roadmap](roadmap.md) for what's planned next.

## Links

- Source: this repository
- Turtle: https://www.w3.org/TR/turtle/
- SSSOM specification: https://mapping-commons.github.io/sssom/
- CSVW Metadata Vocabulary: https://www.w3.org/TR/tabular-metadata/
- maplib: [background article](https://ieeexplore.ieee.org/stamp/stamp.jsp?arnumber=10106242) on applying RDF knowledge graphs at industrial scale
