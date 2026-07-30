import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo
    from maplib import Model
    import polars as pl

    ROOT = Path(__file__).parent.parent
    VOCAB = ROOT / "build/vocabularies/omop.ttl"
    OMOP_CONCEPT_RELATIONSHIP = ROOT / "data/vocabularies/omop/unversioned/CONCEPT_RELATIONSHIP.csv"
    return Model, OMOP_CONCEPT_RELATIONSHIP, VOCAB, mo, pl


@app.cell
def _(Model, VOCAB):
    vocab = Model()
    vocab.read(VOCAB)
    return (vocab,)


@app.cell
def _(vocab):
    vocab_pair_counts = vocab.query("""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    SELECT ?s_vocab ?o_vocab (COUNT(*) AS ?n)
    WHERE {
      ?s skos:exactMatch ?o .
      FILTER(?s != ?o)
      BIND(
        IF(CONTAINS(STR(?s), "w3id.org/omop/concept/"), "omop",
        IF(CONTAINS(STR(?s), "snomed.info/id/"), "snomed",
        IF(CONTAINS(STR(?s), "purl.bioontology.org/ontology/RXNORM/"), "rxnorm",
        IF(CONTAINS(STR(?s), "fhir/sid/icd-10-cm/"), "icd10cm",
        IF(CONTAINS(STR(?s), "fhir/sid/icd-10/"), "icd10",
        "other"))))) AS ?s_vocab
      )
      BIND(
        IF(CONTAINS(STR(?o), "w3id.org/omop/concept/"), "omop",
        IF(CONTAINS(STR(?o), "snomed.info/id/"), "snomed",
        IF(CONTAINS(STR(?o), "purl.bioontology.org/ontology/RXNORM/"), "rxnorm",
        IF(CONTAINS(STR(?o), "fhir/sid/icd-10-cm/"), "icd10cm",
        IF(CONTAINS(STR(?o), "fhir/sid/icd-10/"), "icd10",
        "other"))))) AS ?o_vocab
      )
    }
    GROUP BY ?s_vocab ?o_vocab
    ORDER BY DESC(?n)
    """)
    vocab_pair_counts
    return


@app.cell
def _(vocab):
    # Check for a direct SNOMED <-> ICD10 bridge via a shared OMOP concept.
    # All exactMatch triples in this graph originate from OMOP (s = omop concept),
    # so cross-terminology counts (e.g. SNOMED-ICD10) only exist if the same OMOP
    # concept has exactMatch triples to both targets.
    snomed_icd10_bridge = vocab.query("""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    SELECT (COUNT(*) AS ?n_pairs) (COUNT(DISTINCT ?omop) AS ?n_omop_bridges)
    WHERE {
      ?omop skos:exactMatch ?snomed .
      ?omop skos:exactMatch ?icd .
      FILTER(CONTAINS(STR(?snomed), "snomed.info/id/"))
      FILTER(CONTAINS(STR(?icd), "fhir/sid/icd-10"))
    }
    """)
    snomed_icd10_bridge
    return


@app.cell
def _(OMOP_CONCEPT_RELATIONSHIP, pl):
    omop_relationship = pl.scan_csv(OMOP_CONCEPT_RELATIONSHIP, separator="\t")
    return


@app.cell
def _(mo):
    cdm = """
    erDiagram
        CONCEPT }|--|| DOMAIN : "pertains to"
        CONCEPT }|--|{ CONCEPT_CLASS : "classified in"
        SOURCE_TO_CONCEPT_MAP }|--|{ CONCEPT : "maps to"
        CONCEPT_RELATIONSHIP }|--|| CONCEPT : "relates two concepts"
        RELATIONSHIP ||--|{ CONCEPT_RELATIONSHIP : "type of relationship"

    """
    mo.mermaid(
        cdm,
        theme="neutral",
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
