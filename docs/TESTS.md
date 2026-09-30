# The tests

Every test the engine runs on an estate: 42 tests in 6 areas. Generated from `src/anaplan_estate/checks.py`; the report's *Tests run* table shows the result of each one on your exports.

A test that needs an optional export or column says so; without it the test is reported as not run, never as clear. A hit is an observation or a review candidate, not a verdict.

## 1. Performance and size

Where calculation time and cells go, and the formula patterns Anaplan documents as expensive.

| # | Test | What is tested | Needs |
|---|---|---|---|
| 1.1 | Where calculation effort concentrates | The line items and modules carrying the largest share of Anaplan's measured Calculation Effort, and the share held by the top ten. | the Calculation Effort column |
| 1.2 | SUM combined with LOOKUP or SELECT | A formula that aggregates (SUM) and looks up or selects in the same formula, which Anaplan documents as slow. |  |
| 1.3 | Large text line items | A text-formatted line item with more than 50,000 cells. | the Cell Count column, the Format column |
| 1.4 | FINDITEM on a large line item | FINDITEM in a line item with 10,000 cells or more. | the Cell Count column |
| 1.5 | Text joins on a large line item | Text concatenation (&) in a line item with 10,000 cells or more. | the Cell Count column |
| 1.6 | Per-item functions repeated on every cell | PARENT, ITEM, NAME, CODE, START, END and similar in a line item with two or more dimensions and 5,000 cells or more, where a one-dimension system module would compute the answer once. | the Cell Count column, the Applies To column |
| 1.7 | Line items with a dimension their formula does not use | A calculated line item of 10,000 cells or more that applies to a list, Time or Versions that nothing in its formula varies over: the dimension multiplies cells without changing the value. TRUE or FALSE flags and modules on a line item subset are not counted. | the Cell Count column, the Applies To column |
| 1.8 | Where the cells are | The modules and line items holding the largest share of the model's cells. | the Cell Count column |

## 2. Usage and leftovers

What nothing appears to read: candidates to ask about, never verdicts.

| # | Test | What is tested | Needs |
|---|---|---|---|
| 2.1 | Modules nothing reads | A module with two or more calculated line items that no formula outside it reads and no export action uses. |  |
| 2.2 | Unread modules that repeat a module in use | An unread module whose calculated line items match, in formula and context, line items of a module that is read, with the share matched. | the Format, Applies To, Summary, Time Scale, Time Range, Versions and Formula Scope columns |
| 2.3 | Calculated line items nothing reads | A calculated line item of 50,000 cells or more that no formula reads, outside the modules above and outside output-style modules. | the Cell Count column |
| 2.4 | Data loaded but never read | A module that an import action loads, none of whose line items is read by any formula or used by an export action. | the Actions export |
| 2.5 | Names that say leftover | Modules, line items, actions and referenced list items whose name carries a leftover marker (OLD, TEMP, COPY, BACKUP, DO NOT USE, v2, 'Copy of', default names), with whether anything still reads them. 'Delete' flags and version names are not counted. |  |

## 3. Dependencies and change impact

What depends on what, inside a model and between models.

| # | Test | What is tested | Needs |
|---|---|---|---|
| 3.1 | Line items with the widest change impact | A line item read directly by 25 or more formulas, with its full downstream reach. |  |
| 3.2 | Pass-through chains | Three or more line items in a row that only copy the one before. |  |
| 3.3 | Circular references | Line items that depend on each other: a balance pattern through a time offset, or a reference the parser may have misread. |  |
| 3.4 | Which model feeds which | Model-to-model feeds, inferred from the names of import actions. | the Actions export; two or more models |
| 3.5 | Dimensions shared across models | List names used as a dimension in more than one model. | the Applies To column; two or more models |

## 4. Correctness and maintainability

Totals that may be wrong, repeated logic, and formulas the next builder has to decode.

| # | Test | What is tested | Needs |
|---|---|---|---|
| 4.1 | The same calculation under two names | Line items with the same resolved formula and the same dimensions, time scale, time range, versions, format, summary and formula scope. | the Format, Applies To, Summary, Time Scale, Time Range, Versions and Formula Scope columns |
| 4.2 | Line items that only copy another | A formula that is a single reference to a line item with identical context. | the Format, Applies To, Summary, Time Scale, Time Range, Versions and Formula Scope columns |
| 4.3 | Formulas that differ in exactly one place | Two line items in different modules with the same formula shape and context, differing in one constant, reference or list item. | the Format, Applies To, Summary, Time Scale, Time Range, Versions and Formula Scope columns |
| 4.4 | Identical formula text that cannot be compared | Identical formula text where COLLECT() or a blank context field stops the comparison; listed so it is not read as a duplicate. |  |
| 4.5 | The same line item and formula in more than one model | A line item name with the same formula tree in two or more models. | two or more models |
| 4.6 | Formulas with more than 10 IFs | More than 10 IF THEN ELSE in one formula, with the lookup table the chain encodes where there is one. |  |
| 4.7 | Hard-coded numbers in formulas | Numeric literals other than structural ones (0, 1, 12, 100 and similar) and function arguments. |  |
| 4.8 | Very long formulas | A formula of more than 120 tokens. |  |
| 4.9 | SELECT on a fixed period or version | SELECT naming a specific time period or version. |  |
| 4.10 | DIVIDE() where a zero divisor shows Infinity | DIVIDE() present: it returns Infinity on a zero divisor where / returns zero. |  |
| 4.11 | Subsidiary views used in calculation | A line item dimensioned differently from its module and read by formulas. | the Applies To column |
| 4.12 | Summaries on line items nothing reads | A number line item of 10,000 cells or more with a summary method and no formula reader. | the Cell Count column, the Summary column, the Format column |
| 4.13 | Modules with more than 50 line items | A module holding more than 50 line items. |  |
| 4.14 | Empty modules | A module with no line items. |  |
| 4.15 | Modules without notes | How many modules carry no notes, largest first. | the Modules export |
| 4.16 | Percentages whose totals are added up | A line item formatted as a percentage that divides one amount by another and has the summary method Sum, so every total is the sum of the percentages below it and not the percentage of the totals. | the Summary column, the Format column |
| 4.17 | The odd one out in a run of matching formulas | Five or more neighbouring line items in a module share one formula shape and exactly one among them differs: a different shape, no formula at all, or one reference its siblings do not share. A subtotal of its neighbours is not counted. |  |

## 5. Imports, exports and processes

What loads the model, what has stopped running, what sits outside every process.

| # | Test | What is tested | Needs |
|---|---|---|---|
| 5.1 | Imports and exports outside every process | An import or export action that is in no process. | the Actions export |
| 5.2 | Imports and exports with no recent run | No recorded run in the 12 months before the latest run in the export. | the Actions export |
| 5.3 | Imports and exports never run | No recorded run at all. | the Actions export |
| 5.4 | Several imports loading one target | A module or list loaded by two or more import actions, with the last run of each. | the Actions export |

## 6. How far to trust the analysis

Checks the report runs on itself, so every finding says how strong its evidence is.

| # | Test | What is tested | Needs |
|---|---|---|---|
| 6.1 | Formulas the parser did not follow | Formulas whose references are therefore missing from the dependency graph. |  |
| 6.2 | Agreement with Anaplan's own Referenced By | The parsed dependency graph compared edge by edge with Anaplan's Referenced By column; below 95% every dependent finding is downgraded. | the Referenced By column |
| 6.3 | Input checks on the files | Delimiter, encoding and number format are detected; a missing column disables the checks that need it and is reported as unavailable, never as zero. |  |

