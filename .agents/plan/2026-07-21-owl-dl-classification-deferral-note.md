# Note: "Full OWL-DL axiom classification via snomed-owl-toolkit deferred as optional follow-up"

**Date:** 2026-07-21
**Companion to:** `2026-07-21-add-snomed-loinc-omop-vocabularies.md` (§2.1, §5 Phase 2, §7)

This note unpacks one sentence from the vocabulary-integration plan, because it
carries a design trade-off that is easy to misread.

---

## 1. The one-sentence claim, restated

The LOINC-SNOMED pipeline (Phase 2) will build its Turtle graph the **lightweight
way**: read the RF2 `Relationship` snapshot with polars and emit
`rdfs:subClassOf` / `skos:broadMatch` edges (plus labels from the Description +
Language refsets). It will **not**, in this increment, compute the full
description-logic (OWL-DL) form of the ontology. Doing that properly is a
separate, heavier step that we consciously push to a later, optional follow-up.

---

## 2. What "OWL-DL axiom classification" actually means here

SNOMED CT (and therefore the LOINC-SNOMED extension) is not just a hierarchy of
"is-a" links. Each concept has a **logical definition** written as an OWL 2 axiom
— in the RF2 package these live in the OWL Expression refset file
(`sct2_sRefset_OWLExpression*.txt`), one axiom per row in **OWL functional
syntax**, e.g.:

```
EquivalentClasses(
  :100000001
  ObjectIntersectionOf(
    :123037004
    ObjectSomeValuesFrom(:roleGroup
      ObjectSomeValuesFrom(:246093002 :387517004))))
```

Two distinct things are involved:

1. **The stated axioms** — the `EquivalentClasses` / `SubClassOf` expressions
   above, including role groups (`ObjectSomeValuesFrom` on attributes like
   Component, Property, System, Scale, Method). These are the *authoring* truth.
2. **Classification** — running an **OWL reasoner** (ELK is the standard one for
   SNOMED's EL++ profile) over those stated axioms to compute the **inferred**
   subsumption hierarchy: which concepts are subclasses of which, once all the
   logical definitions are taken into account. This is what "classification"
   means, and it can move concepts to new parents that no single stated `Is a`
   edge shows.

**snomed-owl-toolkit** (SNOMED International's Java library,
github.com/IHTSDO/snomed-owl-toolkit) is the canonical tool that: reads the RF2
Snapshot (Concept file + OWL Expression refset + the ontology/header refset),
assembles a single `.owl` ontology, and can run ELK to classify it.

---

## 3. What the lightweight path gives us instead

The RF2 `Relationship` snapshot file already contains the **inferred**
relationships (the distribution ships the post-classification result — that is
what the `Relationship_Snapshot` file is, as opposed to the legacy
`StatedRelationship`). So by reading it with polars we get, for free:

- `typeId == 116680003` ("Is a") rows → a usable subsumption hierarchy.
- other `typeId` rows → attribute relationships (Component, System, …) we can
  optionally emit as plain RDF triples.

This yields a faithful **SKOS/RDFS graph** — good enough to place every concept
in the hierarchy and cross-link OMOP concept_ids — **without** us running a
reasoner or parsing functional-syntax axioms.

---

## 4. Why defer the full axiom route

1. **New heavy dependency / toolchain.** snomed-owl-toolkit is a **Java**
   library; wiring it into a Python (polars/rdflib) pipeline means shelling out
   to a JAR, managing a JVM, and a much slower build. That is out of proportion
   to this increment's goal (a cross-vocabulary linking graph).
2. **We don't need inferred-only subsumptions yet.** The distributed
   `Relationship` snapshot already encodes the inferred hierarchy, so our
   consumers (OMOP concept_id cross-linking, SKOS matches) get correct is-a
   structure without re-running ELK ourselves.
3. **Functional-syntax parsing is non-trivial.** Faithfully turning role groups
   and `ObjectIntersectionOf`/`ObjectSomeValuesFrom` into RDF/OWL restrictions
   (blank nodes, `owl:Restriction`, `owl:onProperty`, `owl:someValuesFrom`) is a
   meaningful chunk of work and easy to get subtly wrong — better done
   deliberately, with its own tests, than bolted on now.
4. **Scale.** Classifying 45k+ LOINC-extension concepts on top of full SNOMED CT
   International is memory- and time-intensive; not something to run on every
   `just build-all`.
5. **YAGNI for the stated goal.** The objective is "OMOP concept_ids integrated
   with SNOMED/LOINC/RxNorm/ICD10 in one TTL". That needs identity + labels +
   hierarchy + SKOS matches — all reachable from the tabular RF2/Athena files.
   Formal DL equivalence axioms add expressive power we don't consume yet.

---

## 5. What the follow-up would add (and when to do it)

Do the follow-up when a consumer actually needs one of:

- **Exact stated logical definitions** — e.g. reasoning over "any measurement
  whose Component is glucose", querying by concept-model attributes, or
  round-tripping to a real OWL ontology for Protégé/ELK.
- **Reclassification** — recomputing subsumptions after combining LOINC-SNOMED
  with other extensions, where the shipped inferred `Relationship` file no longer
  reflects the merged whole.
- **owl:equivalentClass / restriction edges** in the graph (mirrors what
  `mapping/protege.py` already does for the curated mappings, but for the source
  ontology itself).

Concrete follow-up shape:

1. Add a `vocabulary/owl_axioms.py` step that runs snomed-owl-toolkit (JAR) over
   the cached RF2 Snapshot to produce `loinc-snomed.owl`.
2. Load that `.owl` with rdflib (or owlready2) and merge the restriction/
   equivalence triples into `loinc-snomed.ttl`, replacing the lightweight
   `rdfs:subClassOf`-only edges.
3. Optionally run ELK for a fully classified hierarchy if a merged/edited edition
   is involved.
4. Gate it behind an explicit CLI flag (e.g. `rosetta vocabulary
   build-loinc-snomed --with-owl-axioms`) and keep it **out** of the default
   `build-all` so routine builds stay fast and JVM-free.

---

## 6. One-line summary

> The default pipeline uses the RF2 `Relationship` snapshot (already inferred) to
> emit a lightweight SKOS/RDFS hierarchy with polars+rdflib — no reasoner, no
> Java. Turning the OWL Expression refset into full OWL-DL restriction/
> equivalence axioms (via snomed-owl-toolkit + ELK) is a deliberately separate,
> flag-gated follow-up we only build when a consumer needs formal logical
> definitions or reclassification.
