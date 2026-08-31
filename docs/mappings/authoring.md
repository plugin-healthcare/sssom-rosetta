# Authoring SSSOM mappings

This page documents the conventions used when hand-authoring mapping rows under `mappings/*.csv`.

## `skos:broadMatch` / `skos:narrowMatch` direction

To assert that one concept is broader in meaning (i.e. more general) than another, use `skos:broadMatch`.
Use `skos:narrowMatch` to assert the inverse: that one concept is narrower in meaning (i.e. more specific) than another.

For example:

```turtle
ex:animals rdf:type skos:Concept;
  skos:prefLabel "animals"@en;
  skos:narrowMatch ex:mammals.
ex:mammals rdf:type skos:Concept;
  skos:prefLabel "mammals"@en;
  skos:broadMatch ex:animals.
```

For historic reasons, the name of the `skos:broadMatch` property does not provide an explicit indication of its direction.
Read "broadMatch" here as "has broader concept": the subject of a `skos:broadMatch` statement is the more specific concept, and its object is the more generic one.

As is often the case in a knowledge organization system (KOS), a SKOS concept can be attached to several broader concepts at the same time.
For example, a concept `ex:dog` could have both `ex:mammals` and `ex:domesticatedAnimals` as broader concepts.

Prefer `broadMatch`, `narrowMatch` and `exactMatch` over `relatedMatch`.
