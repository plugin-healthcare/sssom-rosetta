---
name: ottr
description: Reading and writing OTTR templates and instances in stOTTR (terse) syntax. Use this skill whenever the user works with OTTR templates, stOTTR / .stottr files, ottr:Triple, template signatures, template instances, list expanders (cross / zipMin / zipMax), parameter modifiers (optional / non-blank), OTTR types (List / NEList / LUB), or asks how to capture an RDF/OWL modelling pattern as a reusable, parameterised template. Covers core OTTR concepts plus the complete stOTTR grammar. Pair with the maplib skill when the templates are expanded over DataFrames in Python.
---

# OTTR & stOTTR

## What OTTR is

**OTTR** (Reasonable Ontology Templates, pronounced "otter") is a language for
capturing and instantiating **RDF graph and OWL ontology modelling patterns**. A
*template* is a parameterised RDF graph: you define the shape of the triples once,
then create many *instances* by supplying arguments. Expanding the instances against
their templates produces ordinary RDF.

The core idea is a clean separation between **design** (templates, owned by modelling
experts) and **content** (instances, often produced by domain experts from
spreadsheets or databases). Templates can be nested — one template's body is built
from instances of other templates — which makes patterns modular and DRY.

**stOTTR** ("terse OTTR") is the compact, human-readable serialisation for writing
templates and instances. It is the syntax this skill focuses on. (Templates can also
be serialised as RDF/OWL via *wOTTR*, specified in spreadsheets via *tabOTTR*, or
mapped from queryable sources via *bOTTR* — but stOTTR is what you read and write by
hand, and what `maplib` consumes.)

stOTTR **extends Turtle**: prefixes, IRIs, blank nodes, and literals all follow
Turtle rules. stOTTR adds syntax for parameters, instances, types, and expanders on
top of that. Files use the `.stottr` extension.

## The shape of a stOTTR document

A document is any number of Turtle prefix/base directives followed by any number of
**statements**. Every statement — a signature, a template, a base template, or a
standalone instance — is terminated by a dot `.`.

```stottr
@prefix ex:   <http://example.net/ns#> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

# A template: signature  ::  pattern
ex:Person [ ottr:IRI ?id, xsd:string ?name, xsd:int ?age ] :: {
    ottr:Triple(?id, rdf:type,  ex:Person),
    ottr:Triple(?id, rdfs:label, ?name),
    ottr:Triple(?id, ex:age,    ?age)
} .

# An instance of it
ex:Person(ex:alice, "Alice", 34) .
```

`ottr:Triple` is the **base template** for a single RDF triple — it is the primitive
every other template ultimately expands down to. The conventional OTTR namespace is
`<http://ns.ottr.xyz/0.4/>`; bind it to the `ottr:` prefix.

## Anatomy of a template

A template is a **signature**, then `::`, then a **pattern** (`{ ... }`):

```
templateName [ parameters ]  ::  { instances }  .
```

### Signature

`templateName [ parameter, parameter, ... ]`

- **Template name** is an IRI (prefixed name like `ex:Person`, or a full
  `<http://...>`).
- **Parameters** sit in square brackets `[ ]`, comma-separated. The list may be empty.
- Each parameter is: `modifiers? type? ?variable defaultValue?`
  - **Variable**: `?name` — a `?` followed by a Turtle blank-node label. The parameter
    name is the variable without the `?`.
  - **Type** (optional): a prefixed name such as `xsd:string`, `owl:Class`,
    `ottr:IRI`. If omitted, the type defaults to the most general type, **Top**.
  - **Modifiers** (optional, zero or more, before the type):
    - `?` = **optional** — the argument may be missing.
    - `!` = **non-blank** — the argument may not be a blank node.
    - Both may be combined in any order: `!?`, `?!`, `!??var`, etc.
  - **Default value** (optional): `= constant`, e.g. `?age = 0` or
    `?toppings = (ex:Cheese, ex:Tomato)`. Defaults may be lists.

```stottr
ex:T1 [ ?a, ?b ] .                          # two untyped, unmodified params
ex:T2 [ ! owl:Class ?a, ? xsd:int ?b = 5 ] . # non-blank class; optional int default 5
ex:T3 [ !??a ] .                             # non-blank AND optional
```

A signature on its own (ending in `.` with no `::`) is a valid statement — it declares
the parameters without giving a pattern.

### Pattern

The body, in curly brackets `{ }`, is a list of **instances** that define the triples
the template expands to. The comma between instances is optional. Variables from the
signature are referenced inside the pattern.

### Base templates

A **base template** has a signature but no pattern — in place of the body it has the
keyword `BASE`. Base templates are the primitives that bottom out expansion (e.g.
`ottr:Triple`). You rarely write your own.

```stottr
ex:MyBase [ ?a, ?b ] :: BASE .
```

## Instances

An instance applies a template to **arguments**:

```
(expander |)?  templateName ( arg, arg, ... )
```

- **Arguments** in round brackets `( )`, comma-separated; the list may be empty.
- An argument is a **term**, optionally prefixed by the list-expand marker `++`.
- An optional **list expander** may precede the name, separated by a vertical bar `|`.

```stottr
ex:Template(ex:A, ex:B) .            # two IRI arguments
ex:Template(none, none) .            # two no-value arguments (see `none` below)
ex:Template(?var, "string") .        # a variable and a literal
```

### Terms

A term is a **variable**, a **constant**, or a **list of terms**.

- **Variable**: `?name`.
- **Constant**: an IRI (`ex:iri`, `<http://...>`, `:iri`), a blank node (`[]` or
  `_:b`), or a literal (`"string"`, `"typed"^^xsd:string`, `23`, `3.4`, `true`) — all
  per Turtle.
- **`none`**: shorthand for `ottr:none`, the empty term. Use it to pass "no value" for
  an optional parameter.
- **List**: terms separated by commas inside round brackets, e.g.
  `(ex:Mozzarella, ex:Tomato)` or nested `(("a", 23), ex:iri, (34))`.

Note: the variable `?x` and the blank node `_:x` denote the same RDF node, so avoid
using a blank node whose label matches a variable in the same template.

## List expanders

Expanders turn one instance with list arguments into **many** instances — one per
element — so you don't have to repeat instances by hand. Mark each list argument to be
expanded with `++`; choose how multiple lists are combined with the expander keyword
before the `|`:

- **`cross`** — Cartesian product across all `++`-marked list arguments.
- **`zipMin`** — pairwise, stopping at the **shortest** list.
- **`zipMax`** — pairwise, padding shorter lists with `none` up to the **longest**.

```stottr
# One instance per element of the list:
cross | ex:Template(++(ex:A, ex:B)) .

# Fixed args 1, 2 then expand the list — one instance per element:
zipMin | ex:Template(1, 2, ++(ex:A, ex:B, ex:C)) .

# Common pattern: expand a list parameter inside a template body
cross | ax:SubObjectSomeValuesFrom(?pizza, ex:hasTopping, ++?toppings)
```

## Types

A type is a **basic type**, a **list type**, or a **LUB-type**.

- **Basic type**: a prefixed name only (never a full IRI), e.g. `xsd:string`,
  `owl:Class`, `rdfs:Resource`, `ottr:IRI`.
- **List type**: `List<TYPE>` or `NEList<TYPE>` (non-empty list). Nestable:
  `List<NEList<xsd:int>>`.
- **LUB-type** (least upper bound): `LUB<TYPE>` where `TYPE` is a basic type. **Not**
  nestable — `LUB<LUB<...>>` is illegal.

```stottr
xsd:string                 # basic
List<xsd:string>           # list
NEList<ottr:IRI>           # non-empty list of IRIs
LUB<owl:Class>             # least upper bound
```

`ottr:IRI` is the type to use when a parameter must be an IRI (very common for subject
and object positions, as in the examples below).

## Annotations

A signature (or template) may carry **annotation instances**, each prefixed with `@@`.
Annotations are themselves template instances that describe the template. They go after
the parameter list and before `::` (if a pattern follows).

```stottr
ex:Template4 [ ]
@@ex:Doc(ex:Template4, "describes something"),
@@ex:Doc(ex:Template4, "another note")
.
```

## Comments

- Single line: everything after `#` to end of line.
- Multi-line: anything between `/***` and `***/`.

```stottr
# single-line comment
@prefix foaf: <http://xmlns.com/foaf/0.1/> . # trailing comment is fine

/***
 multi-line
 comment
***/
```

## Worked examples (idiomatic, from real template libraries)

Typical maplib-style templates mint a canonical subject IRI and attach a handful of
triples. `ottr:IRI` types the IRI-valued parameters; `!` marks the identifier
parameter non-blank so every row produces a stable node:

```stottr
@prefix ex:   <http://example.data-treehouse.com/> .
@prefix tpl:  <http://example.data-treehouse.com/tpl/> .
@prefix ottr: <http://ns.ottr.xyz/0.4/> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

tpl:Equipment[
    ! ottr:IRI ?equipment_uri,
    xsd:string ?name,
    ottr:IRI   ?system_uri,
    ottr:IRI   ?type_uri,
    xsd:string ?manufacturer,
    xsd:gYear  ?installed_year
] :: {
    ottr:Triple(?equipment_uri, rdf:type,        ex:Equipment),
    ottr:Triple(?equipment_uri, rdf:type,        ?type_uri),
    ottr:Triple(?equipment_uri, rdfs:label,      ?name),
    ottr:Triple(?equipment_uri, ex:partOfSystem, ?system_uri),
    ottr:Triple(?equipment_uri, ex:manufacturer, ?manufacturer),
    ottr:Triple(?equipment_uri, ex:installedYear, ?installed_year)
} .
```

The classic nested-template example — a `NamedPizza` whose body instantiates other
(axiom) templates, with an optional country, a non-empty list of toppings, and a
`cross` expander over the toppings:

```stottr
ex:NamedPizzaTemplate [
    owl:Class ?pizza,
    ? owl:NamedIndividual ?country,
    NEList<ottr:IRI> ?toppings
] :: {
    ax:SubClassOf(?pizza, ex:NamedPizza),
    ax:SubObjectHasValue(?pizza, ex:hasCountryOfOrigin, ?country),
    ax:SubObjectAllValuesFrom(?pizza, ex:hasTopping, _:toppingsUnion),
    rstr:ObjectUnionOf(_:toppingsUnion, ?toppings),
    cross | ax:SubObjectSomeValuesFrom(?pizza, ex:hasTopping, ++?toppings)
} .

# Instances — note `none` for the optional country:
ex:NamedPizzaTemplate(ex:Margherita, ex:Italy, (ex:Mozzarella, ex:Tomato)) .
ex:NamedPizzaTemplate(ex:Hawaii, none, (ex:Cheese, ex:Ham, ex:Pineapple)) .
```

## Common mistakes

- **Forgetting the terminating `.`** on a statement. Every signature, template, base
  template, and standalone instance ends with `.`.
- **Full IRI as a type.** Types must be prefixed names: write `owl:Class`, not
  `<http://www.w3.org/2002/07/owl#Class>`.
- **Nesting `LUB`.** `LUB<owl:Class>` is fine; `LUB<LUB<...>>` is not.
- **`++` without an expander** (or vice versa). To expand a list argument you both mark
  it with `++` and put `cross`/`zipMin`/`zipMax` before the template name.
- **Confusing brackets**: parameters use `[ ]`, instance arguments and term lists use
  `( )`, the template pattern uses `{ }`.
- **Re-using a blank-node label that matches a variable** in the same template — `?x`
  and `_:x` are the same node.
- **Putting modifiers after the type.** Order is `modifiers type ?var = default`, e.g.
  `! owl:Class ?a = ex:Foo`.

## Quick grammar reference

```
document     ::= ( prefix | base | statement )*
statement    ::= ( signature | template | baseTemplate | instance ) '.'

signature    ::= templateName '[' (parameter (',' parameter)*)? ']' annotation*
parameter    ::= modifier* type? Variable ('=' constant)?
modifier     ::= '?'  (optional)  |  '!'  (non-blank)
annotation   ::= '@@' instance

template     ::= signature '::' '{' (instance ','?)* '}'
baseTemplate ::= signature '::' 'BASE'

instance     ::= (expander '|')? templateName '(' (argument (',' argument)*)? ')'
expander     ::= 'cross' | 'zipMin' | 'zipMax'
argument     ::= '++'? term

term         ::= Variable | constant | '(' (term (',' term)*)? ')'
constant     ::= iri | blankNode | literal | 'none'
Variable     ::= '?' name

type         ::= basicType | 'List<' type '>' | 'NEList<' type '>' | 'LUB<' basicType '>'
basicType    ::= prefixedName
```

Terms, IRIs, blank nodes, and literals follow the Turtle grammar. The authoritative
spec is the stOTTR specification at <https://spec.ottr.xyz/stOTTR/> (this skill tracks
0.1.x); core semantics are defined in mOTTR and rOTTR at <https://spec.ottr.xyz/>.

## Relationship to maplib

In `maplib`, you register stOTTR templates with `model.add_template(doc)` and expand
them over a Polars DataFrame with `model.map("ex:Person", df)`, where DataFrame columns
correspond to the template's parameters (by the variable name without the `?`). When
the user is generating an RDF graph from tabular data in Python, combine this skill with
the **maplib** skill: write the templates here, drive the expansion there.
