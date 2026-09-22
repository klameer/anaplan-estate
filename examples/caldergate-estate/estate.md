# Anaplan estate: 4 models

Generated 2026-09-22 from each model's Line Items and Actions exports. Deterministic; no opinion. Model-to-model links are inferred from import action names and say so.

## What to do

21 actions in 8 categories, biggest reclaim first. Click a category for its actions ranked by impact, and an action for the why, the steps, how to verify, and the evidence. Every action says what the exports prove and what they cannot: formulas, imports and exports are in the files; pages and saved views are not, so anything that needs a page check says so.

| Category | Actions | Estimated reclaim | Need a page check | What it covers |
|---|---|---|---|---|
| [Retire what nothing reads](#retire-what-nothing-reads) | 3 | 85.4M cells; 61% of Caldergate FP&A's effort, 3% of Board Reporting's effort | 3 | Modules and line items no formula, export or twin explains. Cells and calculation effort back, once the pages are checked. |
| [Move logic into inputs and mappings](#move-logic-into-inputs-and-mappings) | 2 | up to 16% of Caldergate FP&A's effort | none | Hard-coded constants and IF chains that are really tables. Replacement artefacts included. |
| [Tidy structure](#tidy-structure) | 5 | 59 objects | 1 | Subsidiary views, summaries left on, text and lookups in big modules, oversized and empty modules. |
| [Collapse copies and chains](#collapse-copies-and-chains) | 3 | 441K cells | 3 | Line items that only copy another, and pass-through chains. Readers can read the source. |
| [Clean up imports and exports](#clean-up-imports-and-exports) | 1 | 12 actions | none | Actions no process runs, or that have not run in a year. Document or delete. |
| [Merge duplicate calculations](#merge-duplicate-calculations) | 4 | 23.6K cells | 2 | The same calculation made twice under different names, and near-twins that differ in one place. |
| [Fix formulas that error or strain](#fix-formulas-that-error-or-strain) | 2 | 5 objects | none | Divisions with no zero guard, aggregate-and-lookup in one bracket, formulas the parser could not follow. |
| [Give shared logic one owner](#give-shared-logic-one-owner) | 1 | 8 objects | none | The same calculation in more than one model. Pick the owner; the others import it. |

The five biggest single actions, across every category:

1. [Retire CAL05 Opex OLD, superseded by CAL03 Opex](#a1-retire-cal05-opex-old-superseded-by-cal03-opex) (Caldergate FP&A; 70.2M cells, 50.8% effort)
2. [Replace the 12-branch IF in CAL03 Opex.Forecast Opex with a mapping module](#a2-replace-the-12-branch-if-in-cal03-opex-forecast-opex-with-a-mapping-module) (Caldergate FP&A; up to 16.0% effort)
3. [Confirm and retire 5 calculated line items that no formula, export or twin explains](#a3-confirm-and-retire-5-calculated-line-items-that-no-formula-export-or-twin-explains) (Caldergate FP&A; 15.1M cells, 10.0% effort)
4. [Turn summaries off on 37 large line items no formula reads](#a4-turn-summaries-off-on-37-large-line-items-no-formula-reads) (4 models; 37 objects)
5. [Retire or schedule 12 imports and exports that no process runs or that have not run in a year](#a5-retire-or-schedule-12-imports-and-exports-that-no-process-runs-or-that-have-not-run-in-a-year) (4 models; 12 actions)

## The estate in one page

1. **4 models, 426 line items, 145M cells.** Caldergate FP&A is 90% of the estate by cells; its largest module alone holds 70.2M (CAL05 Opex OLD). [Estate at a glance](#the-estate-at-a-glance)
2. **Caldergate Data Hub is the hub.** It feeds Caldergate FP&A, Workforce Planning through 6 import actions; 6 feeds between models in all, read off the import action names. [How the models connect](#how-the-models-connect-inferred)
3. **Outside data arrives from 7 named sources**, the busiest being NetSuite with 3 imports. [External sources](#how-the-models-connect-inferred)
4. **Calculation time is concentrated.** In Caldergate FP&A, ten line items carry 68.0% of the model's effort; the single largest is CAL03 Opex.Forecast Opex at 16.0%. [Where the time goes](#caldergate-fp-a)
5. **157 calculated line items feed nothing.** Caldergate FP&A has 77 of them: formulas that run on every recalculation and are read by no other formula. Some are outputs read by pages or exports, which the exports do not show. [Caldergate FP&A](#caldergate-fp-a)
6. **7 imports and exports have not run inside the stale window, and 12 sit outside any process.** Either is a candidate for retirement, or a load nobody schedules. [Actions, per model](#caldergate-data-hub)
7. **8 formulas are copied between models.** COGS? appears in Caldergate Data Hub, Caldergate FP&A with the same logic; a change to one must be repeated in the others. [Logic duplicated across models](#logic-duplicated-across-models)
8. **1 circular reference**: 1 through a time offset (the opening-balance pattern, normal) and 0 without (a parser misread or a real fault).
9. **94 rule findings collapse to 73 patterns.** A pattern is one decision copied across modules or line items; fix the template and the copies follow. None of this says whether a finding matters for this estate. That is a review, and this report is its evidence. [Procedures performed](#procedures-performed)
10. **How far to trust the graph.** Every formula parsed. Our dependency edges agree with Anaplan's own Referenced By column at Caldergate Data Hub 100%, Caldergate FP&A 100%, Workforce Planning 100%, Board Reporting 100%; the gap is line-item subsets through COLLECT(), which the export does not describe.
11. **21 line items repeat a calculation already made in the same model** (311K cells stored twice): same resolved formula and dimensions under another name, or a plain copy of another line item. [Actions](#what-to-do)

## How to read this report

Three parts. The action list above and its detail chapter. Then the estate: how the models connect, what is shared, and one chapter per model, all the same shape, so you can compare them. The last section lists what was checked. In the HTML view each chapter is folded; a link opens the one it points to.

| Section | What it tells you |
|---|---|
| [Actions in detail](#actions-in-detail) | One section per action: why, steps, verify, evidence. |
| [The estate](#the-estate) | One row per model, how the models connect, logic and dimensions shared across them. |
| [The estate at a glance](#the-estate-at-a-glance) | One row per model. Size, how much of it is calculated, how many imports and processes, when it last ran. |
| [How the models connect (inferred)](#how-the-models-connect-inferred) | Which model feeds which, read off the names of import actions, plus the outside systems those names mention. Inferred, and labelled so. |
| [Logic duplicated across models](#logic-duplicated-across-models) | The same line item with the same formula in more than one model. One change, several places. |
| [Dimensions shared across models](#dimensions-shared-across-models) | Lists that appear in more than one model. Where a hierarchy change ripples. |
| [Caldergate Data Hub](#caldergate-data-hub) | 12 modules, 63 line items, 8.1M cells. Where its calculation time goes, what everything depends on, its actions, and its patterns. |
| [Caldergate FP&A](#caldergate-fp-a) | 30 modules, 278 line items, 130M cells. Where its calculation time goes, what everything depends on, its actions, and its patterns. |
| [Workforce Planning](#workforce-planning) | 9 modules, 55 line items, 6.3M cells. Where its calculation time goes, what everything depends on, its actions, and its patterns. |
| [Board Reporting](#board-reporting) | 7 modules, 30 line items, 138K cells. Where its calculation time goes, what everything depends on, its actions, and its patterns. |
| [Procedures performed](#procedures-performed) | Every rule that ran and its source, so you know exactly what was and was not checked. |

A few words that carry weight here:

- **Cells** are what Anaplan bills for and what makes a model slow to open: every line item multiplied out over its dimensions and time. 10.9B means ten thousand million.
- **Calculation effort** is Anaplan's own measure of where the engine spends its time, as a share of the model, exported from Blueprint. Ten line items usually carry most of it.
- **Patterns** are findings grouped by the decision behind them. A formula copied into 96 month columns is one pattern, not 96 problems.
- **Referenced By agreement** is our dependency graph checked against the column Anaplan exports. High means the graph can be trusted; the gap is explained where it appears.
- **Inferred** means read off names, not off a system table. Anaplan does not export which model imports from which; the action names usually say.

# Actions in detail

One section per category, each a ranked table and then every action: why, in the words of the exports; the steps; how to prove it worked; and the evidence. Nothing here says whether an action is worth taking for this business. That is a review, and this is its evidence.

## Retire what nothing reads

Modules and line items no formula, export or twin explains. Cells and calculation effort back, once the pages are checked. 3 actions, biggest first; estimated reclaim 85.4M cells; 61% of Caldergate FP&A's effort, 3% of Board Reporting's effort.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A1 | [Retire CAL05 Opex OLD, superseded by CAL03 Opex](#a1-retire-cal05-opex-old-superseded-by-cal03-opex) | Caldergate FP&A | 70.2M cells, 50.8% effort | pages: check | check pages |
| A3 | [Confirm and retire 5 calculated line items that no formula, export or twin explains](#a3-confirm-and-retire-5-calculated-line-items-that-no-formula-export-or-twin-explains) | Caldergate FP&A | 15.1M cells, 10.0% effort | pages: check | check pages |
| A8 | [Find out what reads SYS01 Time: no formula or export reads it](#a8-find-out-what-reads-sys01-time-no-formula-or-export-reads-it) | Board Reporting | 72 cells, 2.8% effort | pages: check | check pages |

### A1. Retire CAL05 Opex OLD, superseded by CAL03 Opex

**Caldergate FP&A.** No formula outside CAL05 Opex OLD reads any of its 14 line items, and no export action reads it. 2 of its 14 calculated line items have a twin in CAL03 Opex, which other formulas do read. It holds 70.2M cells and 50.78% of the model's calculation effort, recalculated on every change. Module note: "Replaced by CAL03 in 2021. Keep until the FY22 audit is closed."

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 70.2M cells, 50.8% effort | pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. List the pages and saved views that use CAL05 Opex OLD (Modules export: Used in Dashboards covers classic dashboards only; UX pages need the page builder).
2. Where a page reads CAL05 Opex OLD, repoint the card to the twin line item in CAL03 Opex.
3. In a sandbox copy, blank every formula in CAL05 Opex OLD; open the pages listed in step 1.
4. Delete CAL05 Opex OLD.

**Verify**

- Workspace size falls by about 70.2M cells. Calculation effort falls by about 50.78%.
- Every page listed in step 1 opens without a blank card.

**Evidence**

Readers outside the module: 0. Exports reading it: 0. Twin module: CAL03 Opex (2 matches).

### A3. Confirm and retire 5 calculated line items that no formula, export or twin explains

**Caldergate FP&A.** Calculated, read by no formula, not exported, not in an output-style module, and not a twin of anything. Either a page reads them or nothing does. (30 other unreferenced line items look like page outputs by their module, format or time scale and are not listed here.)

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 15.1M cells, 10.0% effort | pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. For each module, list the pages that use it.
2. Where nothing does, set the formula blank in a sandbox and wait a cycle.
3. Delete what nobody missed.

**Verify**

- Cell count falls by what was deleted.
- Re-run this report: the unknown list shrinks to the ones a page needs.

**Evidence**

| Module | Line items with no reader | Cells | Effort |
|---|---|---|---|
| DAT01 Actuals GL | 2: Journal Cost Centre, Loaded? | 10.0M | 7.71% |
| CAL03 Opex | 1: Opex Variance | 5.0M | 2.31% |
| CAL02 Revenue | 2: Revenue USD, VAT | 72.6K | 0.02% |

### A8. Find out what reads SYS01 Time: no formula or export reads it

**Board Reporting.** No formula outside SYS01 Time reads any of its 2 line items, and no export action reads it. It holds 72 cells and 2.8% of the model's calculation effort, recalculated on every change.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 72 cells, 2.8% effort | pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. List the pages and saved views that use SYS01 Time (Modules export: Used in Dashboards covers classic dashboards only; UX pages need the page builder).
2. Where a page reads SYS01 Time, decide whether the page is still used.
3. In a sandbox copy, blank every formula in SYS01 Time; open the pages listed in step 1.
4. Delete SYS01 Time.

**Verify**

- Workspace size falls by about 72 cells. Calculation effort falls by about 2.8%.
- Every page listed in step 1 opens without a blank card.

**Evidence**

Readers outside the module: 0. Exports reading it: 0.

## Move logic into inputs and mappings

Hard-coded constants and IF chains that are really tables. Replacement artefacts included. 2 actions, biggest first; estimated reclaim up to 16% of Caldergate FP&A's effort.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A2 | [Replace the 12-branch IF in CAL03 Opex.Forecast Opex with a mapping module](#a2-replace-the-12-branch-if-in-cal03-opex-forecast-opex-with-a-mapping-module) | Caldergate FP&A | up to 16.0% effort | 1 formula | proven |
| A7 | [Move 11 hard-coded constants into assumptions modules](#a7-move-11-hard-coded-constants-into-assumptions-modules) | Caldergate FP&A, Workforce Planning | 9 objects | nothing in the exports | proven |

### A2. Replace the 12-branch IF in CAL03 Opex.Forecast Opex with a mapping module

**Caldergate FP&A.** The formula is a lookup table written as 12 nested IFs over Accounts. Every branch is evaluated for every cell; this line item carries 16.04% of the model's calculation effort. The table below is the mapping the formula encodes, ready to load.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| up to 16.0% effort | 1 formula | proven: Everything this action touches is in the exports. |

**Steps**

1. Create a module dimensioned by Accounts with one list-formatted line item (the driver) loaded from the table below.
2. Replace the formula with a single LOOKUP against that module.
3. The next new account is a row in the mapping, not a new branch.

**Verify**

- Same values on every cell before and after (export the line item, diff).
- Calculation effort of CAL03 Opex.Forecast Opex falls.

**Evidence**

| Accounts item | Value |
|---|---|
| 6100 Rent | `INP02 Opex Drivers.Rent` |
| 6110 Rates | `INP02 Opex Drivers.Business Rates` |
| 6120 Utilities | `INP02 Opex Drivers.Utilities` |
| 6200 Travel | `INP02 Opex Drivers.Travel` |
| 6210 Subsistence | `INP02 Opex Drivers.Subsistence` |
| 6300 Marketing | `INP02 Opex Drivers.Marketing Events` |
| 6310 Digital | `INP02 Opex Drivers.Marketing Digital` |
| 6400 Software | `INP02 Opex Drivers.Software Licences` |
| 6410 Hardware | `INP02 Opex Drivers.Hardware` |
| 6500 Professional Fees | `INP02 Opex Drivers.Consultancy` |
| 6510 Audit | `INP02 Opex Drivers.Audit Fees` |
| 6600 Recruitment | `INP02 Opex Drivers.Recruitment Fees` |

### A7. Move 11 hard-coded constants into assumptions modules

**Caldergate FP&A, Workforce Planning.** Numbers inside formulas are assumptions nobody can see or change without a model builder. The same constant in more than one formula drifts.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 9 objects | nothing in the exports | proven: Everything this action touches is in the exports. |

**Steps**

1. Create (or reuse) a settings module per model with one line item per constant, named, with a note saying who owns it.
2. Replace each constant with the reference.
3. Tell the owner where the number now lives.

**Verify**

- Search formulas for the constant: zero hits.

**Evidence**

| Constant | Used in | Suggested input |
|---|---|---|
| 0.1 | Workforce Planning: Calcs - Cost.Bonus, Workforce Planning: Calcs - Headcount by CC.Bonus % | Assumption 1 |
| 1.27 | Caldergate FP&A: CAL02 Revenue.Revenue USD | Assumption 2 |
| 0.2 | Caldergate FP&A: CAL02 Revenue.VAT | Assumption 3 |
| 30 | Caldergate FP&A: CAL08 Cash Flow.Debtors | Assumption 4 |
| 0.25 | Caldergate FP&A: CAL08 Cash Flow.Tax | Assumption 5 |
| 10 | Caldergate FP&A: CAL10 Depreciation.Charge | Assumption 6 |
| 119 | Caldergate FP&A: CAL10 Depreciation.Charge | Assumption 7 |
| 120 | Caldergate FP&A: CAL10 Depreciation.Charge | Assumption 8 |
| 239 | Caldergate FP&A: CAL10 Depreciation.Charge | Assumption 9 |
| 0.05 | Caldergate FP&A: INP03 Headcount.Pension | Assumption 10 |
| 11 | Workforce Planning: Calcs - Attrition.Annualised Attrition | Assumption 11 |

## Tidy structure

Subsidiary views, summaries left on, text and lookups in big modules, oversized and empty modules. 5 actions, biggest first; estimated reclaim 59 objects.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A4 | [Turn summaries off on 37 large line items no formula reads](#a4-turn-summaries-off-on-37-large-line-items-no-formula-reads) | 4 models | 37 objects | pages: check | check pages |
| A6 | [Move 18 text and lookup line items out of large calculation modules](#a6-move-18-text-and-lookup-line-items-out-of-large-calculation-modules) | 3 models | 18 objects | 11 formulas | proven |
| A12 | [Move 2 subsidiary-view line items into modules of their own dimensions](#a12-move-2-subsidiary-view-line-items-into-modules-of-their-own-dimensions) | Caldergate FP&A, Workforce Planning | 2 objects | 2 formulas | proven |
| A17 | [Delete 1 empty module](#a17-delete-1-empty-module) | Caldergate FP&A | 1 object | nothing in the exports | proven |
| A21 | [Split INP02 Opex Drivers (58 line items)](#a21-split-inp02-opex-drivers-58-line-items) | Caldergate FP&A | 1 object | 50 formulas, 1 export, pages: check | judgment |

### A4. Turn summaries off on 37 large line items no formula reads

**4 models.** Summaries calculate on every parent of every dimension. Where no formula reads the line item, only a page could need the total.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 37 objects | pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. For each, check whether a page shows it at a parent level.
2. If not, set Summary to None.

**Verify**

- Model open time and calculation effort fall; no page shows a blank total.

**Evidence**

| Model | Line item | Summary | Cells |
|---|---|---|---|
| Caldergate Data Hub | DAT05 CRM Pipeline.Weighted Pipeline | SUM | 17.3K |
| Caldergate FP&A | CAL01 Volumes.Volume Growth | FORMULA | 36.3K |
| Caldergate FP&A | CAL02 Revenue.Average Price | FORMULA | 36.3K |
| Caldergate FP&A | CAL02 Revenue.Revenue Growth | FORMULA | 36.3K |
| Caldergate FP&A | CAL02 Revenue.Revenue USD | SUM | 36.3K |
| Caldergate FP&A | CAL02 Revenue.Revenue per Unit | FORMULA | 36.3K |
| Caldergate FP&A | CAL02 Revenue.VAT | SUM | 36.3K |
| Caldergate FP&A | CAL03 Opex.Opex Variance | SUM | 5.0M |
| Caldergate FP&A | CAL04 Margn.Margin % | FORMULA | 36.3K |
| Caldergate FP&A | CAL04 Margn.Margin GBP | SUM | 36.3K |
| Caldergate FP&A | CAL05 Opex OLD.Opex Cumulative | SUM | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Opex Run Rate | SUM | 5.0M |
| Caldergate FP&A | CAL07 P&L by Cost Centre.EBIT | SUM | 19.2K |
| Caldergate FP&A | CAL07 P&L by Cost Centre.EBITDA Margin | FORMULA | 19.2K |
| Caldergate FP&A | CAL07 P&L by Cost Centre.Opex Variance to Budget | SUM | 19.2K |
| Caldergate FP&A | CAL10 Depreciation.NBV | SUM;time=CLOSING_BALANCE | 19.2K |
| Caldergate FP&A | DAT02 Actuals Volumes.Revenue Actual | SUM | 36.3K |
| Caldergate FP&A | INP02 Opex Drivers.Check | SUM | 19.2K |
| Caldergate FP&A | INP02 Opex Drivers.Driver Count | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Capex | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Depreciation | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.EBITDA YTD | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Headcount | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Opex | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Phased Drivers | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Revenue YTD | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Staff Cost | SUM | 19.2K |
| Caldergate FP&A | OUT01 Management Pack.Total Cost | SUM | 19.2K |
| Caldergate FP&A | OUT02 Board Pack.EBITDA | SUM | 19.2K |
| Caldergate FP&A | OUT02 Board Pack.Old Budget Revenue | SUM | 19.2K |
| Caldergate FP&A | OUT02 Board Pack.Revenue Variance % | FORMULA | 19.2K |
| Workforce Planning | Calcs - Headcount by CC.Average Salary | FORMULA | 594K |
| Board Reporting | DAT01 P&L.COGS | SUM | 19.2K |
| Board Reporting | DAT01 P&L.Depreciation | SUM | 19.2K |
| Board Reporting | DAT01 P&L.EBIT | SUM | 19.2K |
| Board Reporting | DAT01 P&L.EBITDA | SUM | 19.2K |
| Board Reporting | DAT01 P&L.Staff Cost | SUM | 19.2K |

### A6. Move 18 text and lookup line items out of large calculation modules

**3 models.** Text, FINDITEM, ITEM() and text joins in a multi-dimensional line item are computed once per cell. In a one-dimension system module they are computed once per list item.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 18 objects | 11 formulas | proven: Everything this action touches is in the exports. |

**Steps**

1. Compute each once in a SYS module dimensioned by the list it depends on.
2. Reference it from the calculation module.

**Verify**

- Calculation effort of the listed line items falls; cell count of TEXT line items falls.

**Evidence**

| Model | Line item | What | Cells |
|---|---|---|---|
| Caldergate Data Hub | DAT01 GL Transactions.Source System | Text-formatted line item | 1.3M |
| Caldergate Data Hub | DAT06 Sales Orders.Last Order Ref | Text-formatted line item | 726K |
| Caldergate FP&A | DAT01 Actuals GL.Source Journal | Text-formatted line item | 5.0M |
| Caldergate FP&A | DAT01 Actuals GL.Journal Cost Centre | FINDITEM in a large line item | 5.0M |
| Caldergate FP&A | CAL02 Revenue.Revenue Label | Text concatenation in a large line item | 36.3K |
| Caldergate FP&A | CAL02 Revenue.Revenue Label | Unchanging function in a calculation module | 36.3K |
| Caldergate FP&A | CAL03 Opex.Forecast Opex | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Fees Forecast | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Marketing Forecast | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Other Forecast | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Rates Forecast | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Rent Forecast | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Software Forecast | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Travel Forecast | Unchanging function in a calculation module | 5.0M |
| Caldergate FP&A | CAL05 Opex OLD.Utilities Forecast | Unchanging function in a calculation module | 5.0M |
| Workforce Planning | Data - Employees.Employee Name | Text-formatted line item | 66.6K |
| Workforce Planning | Data - Employees.Name and Role | Text-formatted line item | 66.6K |
| Workforce Planning | Data - Employees.Name and Role | Text concatenation in a large line item | 66.6K |

### A12. Move 2 subsidiary-view line items into modules of their own dimensions

**Caldergate FP&A, Workforce Planning.** A line item dimensioned differently from its module is a subsidiary view. Used in calculation, it hides a lookup and confuses the next builder. Anaplan's checklist: display only.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 2 objects | 2 formulas | proven: Everything this action touches is in the exports. |

**Steps**

1. Create or find a module dimensioned as the line item is (usually a SYS module for that list).
2. Move the line item; repoint its readers.

**Verify**

- Modules export: no calculation module has a line item whose Applies To differs from the module's.

**Evidence**

| Model | Line item | Applies to | Module applies to | Readers |
|---|---|---|---|---|
| Caldergate FP&A | CAL01 Volumes.Launched? | Products | Products, Regions | 1 |
| Workforce Planning | Calcs - Attrition.Leavers | Employees | Roles | 1 |

### A17. Delete 1 empty module

**Caldergate FP&A.** No line items. Usually a leftover from a build that moved on.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 1 object | nothing in the exports | proven: Everything this action touches is in the exports. |

**Steps**

1. Delete.

**Verify**

- Modules export: none with an empty Line Items column.

**Evidence**

Caldergate FP&A: CAL09 Scenario Planning

### A21. Split INP02 Opex Drivers (58 line items)

**Caldergate FP&A.** Modules with many line items are slow to open and hard to read. Anaplan's checklist: no more than 50. Split by purpose, not by count.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 1 object | 50 formulas, 1 export, pages: check | judgment: The exports show the shape; whether the change is right needs someone who knows the model. |

**Steps**

1. Group the line items by what reads them (the graph gives the groups).
2. Move each group to a module named for its purpose; repoint readers.

**Verify**

- No module over 50 line items.

**Evidence**

Readers outside the module to repoint: 50.

## Collapse copies and chains

Line items that only copy another, and pass-through chains. Readers can read the source. 3 actions, biggest first; estimated reclaim 441K cells.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A10 | [Collapse 15 line items that only copy another line item](#a10-collapse-15-line-items-that-only-copy-another-line-item) | Caldergate FP&A | 287K cells | 14 formulas, pages: check | check pages |
| A11 | [Shorten 4 pass-through chains](#a11-shorten-4-pass-through-chains) | Caldergate FP&A | 153K cells | 4 formulas, pages: check | check pages |
| A14 | [Collapse 4 line items that only copy another line item](#a14-collapse-4-line-items-that-only-copy-another-line-item) | Board Reporting | 576 cells | pages: check | check pages |

### A10. Collapse 15 line items that only copy another line item

**Caldergate FP&A.** 15 line items have the formula `B = A` with the same dimensions as A. Each stores a second copy of A: 287K cells. Readers of B can read A directly. Some exist to give a page a friendlier name; those are the ones to keep.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 287K cells | 14 formulas, pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. Repoint each reader of the alias to the target (readers column).
2. Keep an alias only where a page or export needs it under that name.
3. Delete the rest.

**Verify**

- Cell count falls by up to 287K.
- Re-run this report: the alias count falls to the ones kept on purpose.

**Evidence**

| Alias | Is just | Cells | Readers to repoint | Summary (alias / target) |
|---|---|---|---|---|
| CAL07 P&L by Cost Centre.Depreciation | CAL10 Depreciation.Charge | 19.2K | 1 | SUM / SUM |
| CAL11 Reporting Prep.Revenue | CAL07 P&L by Cost Centre.Revenue | 19.2K | 1 | SUM / SUM |
| CAL11 Reporting Prep.EBITDA | CAL07 P&L by Cost Centre.EBITDA | 19.2K | 1 | SUM / SUM |
| CAL11 Reporting Prep.Opex | CAL07 P&L by Cost Centre.Opex | 19.2K | 2 | SUM / SUM |
| CAL11 Reporting Prep.Staff Cost | CAL07 P&L by Cost Centre.Staff Cost | 19.2K | 2 | SUM / SUM |
| OUT01 Management Pack.Revenue | CAL11 Reporting Prep.Revenue | 19.2K | 4 | SUM / SUM |
| OUT01 Management Pack.EBITDA | CAL11 Reporting Prep.EBITDA | 19.2K | 2 | SUM / SUM |
| OUT01 Management Pack.Opex | CAL11 Reporting Prep.Opex | 19.2K | 0 | SUM / SUM |
| OUT01 Management Pack.Staff Cost | CAL11 Reporting Prep.Staff Cost | 19.2K | 0 | SUM / SUM |
| OUT01 Management Pack.Total Cost | CAL11 Reporting Prep.Total Cost | 19.2K | 0 | SUM / SUM |
| OUT01 Management Pack.Capex | INP04 Capex.Capex Spend | 19.2K | 0 | SUM / SUM |
| OUT01 Management Pack.Depreciation | CAL10 Depreciation.Charge | 19.2K | 0 | SUM / SUM |
| OUT01 Management Pack.Phased Drivers | CAL12 Driver Phasing.Total Phased | 19.2K | 0 | SUM / SUM |
| OUT02 Board Pack.Revenue | OUT01 Management Pack.Revenue | 19.2K | 1 | SUM / SUM |
| OUT02 Board Pack.EBITDA | OUT01 Management Pack.EBITDA | 19.2K | 0 | SUM / SUM |

### A11. Shorten 4 pass-through chains

**Caldergate FP&A.** A reads B reads C, each a pure copy. Every step recalculates on any change, and each intermediate is a stored copy. Anaplan's checklist: never.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 153K cells | 4 formulas, pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. Point each head at the line item at the end of its chain.
2. The intermediates then have no formula readers; treat them as aliases (previous action) and check pages before deleting.

**Verify**

- Re-run this report: pass-through chains reach zero.

**Evidence**

| Head | Steps | Reads, in the end |
|---|---|---|
| OUT01 Management Pack.Opex | 4 | CAL03 Opex.Opex GBP |
| OUT01 Management Pack.Staff Cost | 4 | INP03 Headcount.Total Cost |
| OUT02 Board Pack.Revenue | 4 | CAL07 P&L by Cost Centre.Revenue |
| OUT02 Board Pack.EBITDA | 4 | CAL07 P&L by Cost Centre.EBITDA |

### A14. Collapse 4 line items that only copy another line item

**Board Reporting.** 4 line items have the formula `B = A` with the same dimensions as A. Each stores a second copy of A: 576 cells. Readers of B can read A directly. Some exist to give a page a friendlier name; those are the ones to keep.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 576 cells | pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. Repoint each reader of the alias to the target (readers column).
2. Keep an alias only where a page or export needs it under that name.
3. Delete the rest.

**Verify**

- Cell count falls by up to 576.
- Re-run this report: the alias count falls to the ones kept on purpose.

**Evidence**

| Alias | Is just | Cells | Readers to repoint | Summary (alias / target) |
|---|---|---|---|---|
| OUT01 Board Dashboard.Revenue | DAT02 Board Lines.Revenue | 144 | 0 | SUM / SUM |
| OUT01 Board Dashboard.EBITDA | DAT02 Board Lines.EBITDA | 144 | 0 | SUM / SUM |
| OUT01 Board Dashboard.Revenue per FTE | CAL01 KPIs.Revenue per FTE | 144 | 0 | SUM / FORMULA |
| OUT01 Board Dashboard.Revenue Growth | CAL01 KPIs.Revenue Growth | 144 | 0 | SUM / FORMULA |

## Clean up imports and exports

Actions no process runs, or that have not run in a year. Document or delete. 1 action, biggest first; estimated reclaim 12 actions.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A5 | [Retire or schedule 12 imports and exports that no process runs or that have not run in a year](#a5-retire-or-schedule-12-imports-and-exports-that-no-process-runs-or-that-have-not-run-in-a-year) | 4 models | 12 actions | nothing in the exports | proven |

### A5. Retire or schedule 12 imports and exports that no process runs or that have not run in a year

**4 models.** 7 of them are both outside every process and stale. An action nobody schedules is either run by hand (document it) or dead (delete it). An import that was the only load into its target module takes the module with it; an import from a source that no longer exists (see external sources) is dead by definition.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 12 actions | nothing in the exports | proven: Everything this action touches is in the exports. |

**Steps**

1. For each action, ask the owner: run by hand, or forgotten?
2. Forgotten: delete the action; if it was the only import into its target module, that module joins the retire list.
3. Run by hand: put it in a process with a name that says when.

**Verify**

- Actions export shows every import and export inside a process, each with a run date inside the window.

**Evidence**

| Model | Action | Last run | In a process | Target |
|---|---|---|---|---|
| Caldergate Data Hub | Import Products from PIM file | 2023-06-14 | no | DAT04 Product Master |
| Caldergate Data Hub | Export Pipeline for Sales Ops | 2025-02-11 | no | DAT05 CRM Pipeline |
| Caldergate Data Hub | Import Customers from Salesforce | recent | no | DAT07 Customer Master |
| Caldergate FP&A | Import from Caldergate Hub v1 - Cost Centres | 2021-03-19 | no | SYS02 Cost Centre Attributes |
| Caldergate FP&A | Import FX from Treasury file | 2023-11-02 | no | SYS05 FX Rates |
| Caldergate FP&A | Export Opex Drivers to Excel | 2024-05-30 | no | INP02 Opex Drivers |
| Caldergate FP&A | Export Assumptions for Workforce | recent | no | SYS00 Model Settings |
| Caldergate FP&A | Import Budget from Excel | recent | no | INP02 Opex Drivers |
| Workforce Planning | Import from Caldergate FP&A - Assumptions | 2022-08-17 | no | Inputs - Settings |
| Workforce Planning | Export Leavers Report | 2024-12-19 | no | Calcs - Attrition |
| Workforce Planning | Export Headcount by Department | recent | no | Reports - Headcount |
| Board Reporting | Export Board Pack PDF Data | recent | no | OUT01 Board Dashboard |

## Merge duplicate calculations

The same calculation made twice under different names, and near-twins that differ in one place. 4 actions, biggest first; estimated reclaim 23.6K cells.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A13 | [Reconcile 6 pairs of formulas that differ in exactly one place](#a13-reconcile-6-pairs-of-formulas-that-differ-in-exactly-one-place) | Caldergate FP&A | 6 objects | nothing in the exports | judgment |
| A15 | [Reconcile 3 pairs of formulas that differ in exactly one place](#a15-reconcile-3-pairs-of-formulas-that-differ-in-exactly-one-place) | Workforce Planning | 3 objects | nothing in the exports | judgment |
| A18 | [Merge 1 line item that repeat a calculation already made (1 group)](#a18-merge-1-line-item-that-repeat-a-calculation-already-made-1-group) | Caldergate FP&A | 19.2K cells | pages: check | check pages |
| A19 | [Merge 1 line item that repeat a calculation already made (1 group)](#a19-merge-1-line-item-that-repeat-a-calculation-already-made-1-group) | Workforce Planning | 4.5K cells | 1 formula, pages: check | check pages |

### A13. Reconcile 6 pairs of formulas that differ in exactly one place

**Caldergate FP&A.** Same formula skeleton, same dimensions, one leaf differs: a constant, a reference or a list item. This is what copy, paste and tweak leaves behind. Either the difference is intended (then the name should say so) or one of the pair is the stale copy.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 6 objects | nothing in the exports | judgment: The exports show the shape; whether the change is right needs someone who knows the model. |

**Steps**

1. For each pair, read the difference column and decide: intended, or drift.
2. Intended: rename so the difference is in the name, or add a note.
3. Drift: fix the stale one, or merge as an exact duplicate.

**Verify**

- Re-run this report: pairs that were drift are gone; pairs that were intended carry a note.

**Evidence**

| Line item | Near twin | The one difference | Cells |
|---|---|---|---|
| CAL03 Opex.Actual Opex | CAL05 Opex OLD.Actual | `SYS03 Account Attributes.Opex?` vs `SYS01 Time Settings.Actual?` | 5.0M |
| CAL03 Opex.Opex GBP | CAL05 Opex OLD.Opex GBP | `CAL03 Opex.Opex` vs `CAL05 Opex OLD.Opex` | 5.0M |
| CAL02 Revenue.Gross Revenue | CAL04 Margn.COGS | `INP01 Volumes.Price` vs `INP06 Unit Costs.Landed Cost` | 36.3K |
| CAL01 Volumes.Sellable Units Prior Year | CAL02 Revenue.Revenue Prior Year | `CAL01 Volumes.Sellable Units` vs `CAL02 Revenue.Revenue GBP` | 36.3K |
| CAL02 Revenue.Revenue GBP | CAL04 Margn.Margin GBP | `CAL02 Revenue.Net Revenue` vs `CAL04 Margn.Margin` | 36.3K |
| CAL07 P&L by Cost Centre.Opex Budget | OUT02 Board Pack.Budget Revenue | `CAL07 P&L by Cost Centre.Opex` vs `OUT01 Management Pack.Revenue` | 19.2K |

### A15. Reconcile 3 pairs of formulas that differ in exactly one place

**Workforce Planning.** Same formula skeleton, same dimensions, one leaf differs: a constant, a reference or a list item. This is what copy, paste and tweak leaves behind. Either the difference is intended (then the name should say so) or one of the pair is the stale copy.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 3 objects | nothing in the exports | judgment: The exports show the shape; whether the change is right needs someone who knows the model. |

**Steps**

1. For each pair, read the difference column and decide: intended, or drift.
2. Intended: rename so the difference is in the name, or add a note.
3. Drift: fix the stale one, or merge as an exact duplicate.

**Verify**

- Re-run this report: pairs that were drift are gone; pairs that were intended carry a note.

**Evidence**

| Line item | Near twin | The one difference | Cells |
|---|---|---|---|
| Calcs - Attrition.Headcount | zz Archive - 2021 Cost.Cost | `Data - Employees.FTE` vs `Calcs - Cost.Total Cost` | 4.5K |
| Calcs - Attrition.Leavers by Role | zz Archive - 2021 Cost.Headcount | `Calcs - Attrition.Leavers` vs `Data - Employees.FTE` | 4.5K |
| Calcs - Attrition.Leavers by Role | zz Archive - 2021 Cost.Cost | `Calcs - Attrition.Leavers` vs `Calcs - Cost.Total Cost` | 4.5K |

### A18. Merge 1 line item that repeat a calculation already made (1 group)

**Caldergate FP&A.** 1 calculated line items have the same resolved formula, dimensions, time scale and versions as another line item in the model. Each is computed and stored twice: 19.2K cells. The keeper in each group is the one most formulas already read.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 19.2K cells | pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. For each group, keep the line item most formulas read (first column).
2. Repoint every formula that reads a duplicate to the keeper (the readers count is in the table).
3. Where the summary methods differ (last column), decide which one the pages need before merging; that is the one legitimate reason for two copies.
4. Check pages for the duplicates, then delete them.

**Verify**

- Cell count falls by about 19.2K.
- No page shows a blank; no export loses a column.
- Re-run this report: the group count reaches zero.

**Evidence**

| Keep (most read) | Also computed as | Dimensions | Redundant cells | Summary methods |
|---|---|---|---|---|
| CAL07 P&L by Cost Centre.Depreciation | OUT01 Management Pack.Depreciation | Cost Centres | 19.2K | SUM |

### A19. Merge 1 line item that repeat a calculation already made (1 group)

**Workforce Planning.** 1 calculated line items have the same resolved formula, dimensions, time scale and versions as another line item in the model. Each is computed and stored twice: 4.5K cells. The keeper in each group is the one most formulas already read.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 4.5K cells | 1 formula, pages: check | check pages: Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything. |

**Steps**

1. For each group, keep the line item most formulas read (first column).
2. Repoint every formula that reads a duplicate to the keeper (the readers count is in the table).
3. Where the summary methods differ (last column), decide which one the pages need before merging; that is the one legitimate reason for two copies.
4. Check pages for the duplicates, then delete them.

**Verify**

- Cell count falls by about 4.5K.
- No page shows a blank; no export loses a column.
- Re-run this report: the group count reaches zero.

**Evidence**

| Keep (most read) | Also computed as | Dimensions | Redundant cells | Summary methods |
|---|---|---|---|---|
| Calcs - Attrition.Headcount | zz Archive - 2021 Cost.Headcount | Roles | 4.5K | SUM |

## Fix formulas that error or strain

Divisions with no zero guard, aggregate-and-lookup in one bracket, formulas the parser could not follow. 2 actions, biggest first; estimated reclaim 5 objects.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A9 | [Guard 4 divisions that error on zero](#a9-guard-4-divisions-that-error-on-zero) | 3 models | 4 objects | nothing in the exports | proven |
| A16 | [Split 1 formula that aggregate and look up in one bracket](#a16-split-1-formula-that-aggregate-and-look-up-in-one-bracket) | Caldergate FP&A | 1 object | nothing in the exports | proven |

### A9. Guard 4 divisions that error on zero

**3 models.** A / B shows an error cell when B is zero, and every summary above it shows an error too. DIVIDE() returns zero. The replacement formula is written out; paste it.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 4 objects | nothing in the exports | proven: Everything this action touches is in the exports. |

**Steps**

1. Paste the replacement formula from the table into each line item.
2. Where a zero denominator should show blank rather than zero, wrap in IF instead.

**Verify**

- No error cells on the pages that show these line items at a total level.

**Evidence**

| Model | Line item | Replace with |
|---|---|---|
| Caldergate FP&A | CAL02 Revenue.Revenue per Unit | `DIVIDE(Net Revenue, CAL01 Volumes.Net Units)` |
| Workforce Planning | Calcs - Attrition.Annualised Attrition | `DIVIDE(MOVINGSUM(Leavers by Role, -11, 0), Headcount)` |
| Workforce Planning | Calcs - Attrition.Attrition % | `DIVIDE(Leavers by Role, Headcount)` |
| Board Reporting | CAL01 KPIs.Revenue per FTE | `DIVIDE(DAT02 Board Lines.Revenue, FTE)` |

### A16. Split 1 formula that aggregate and look up in one bracket

**Caldergate FP&A.** SUM with LOOKUP or SELECT in one expression makes the engine build a large intermediate mapping. Anapedia: never combine them.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 1 object | nothing in the exports | proven: Everything this action touches is in the exports. |

**Steps**

1. Aggregate into an intermediate line item first.
2. Look up from the intermediate.

**Verify**

- Same values; calculation effort falls.

**Evidence**

| Model | Line item | Clause | Formula |
|---|---|---|---|
| Caldergate FP&A | CAL06 Department Summary.Benchmark Opex | LOOKUP+SUM | `'CAL03 Opex'.Opex GBP[SUM: 'SYS02 Cost Centre Attributes'.Department, LOOKUP: 'SYS09 Department Sett` |

## Give shared logic one owner

The same calculation in more than one model. Pick the owner; the others import it. 1 action, biggest first; estimated reclaim 8 objects.

| # | Do this | Model | Reclaims | Touches | Exports can prove |
|---|---|---|---|---|---|
| A20 | [Give 8 calculations that exist in more than one model a single owner](#a20-give-8-calculations-that-exist-in-more-than-one-model-a-single-owner) | Estate | 8 objects | 3 models | judgment |

### A20. Give 8 calculations that exist in more than one model a single owner

**Estate.** The same line item, same formula, in more than one model. A change in one must be repeated in the others, and one day it is not. Caldergate FP&A holds the most copies; where a feed already exists, it can own the value and the others import it.

| Reclaims | Touches | Exports can prove |
|---|---|---|
| 8 objects | 3 models | judgment: The exports show the shape; whether the change is right needs someone who knows the model. |

**Steps**

1. Pick the owner per line item (usually the hub).
2. Add the line item to an export the other model already imports.
3. Replace the copy with the imported value.

**Verify**

- Re-run this report: the cross-model duplicate list is empty or annotated.

**Evidence**

| Line item | Models | Formula |
|---|---|---|
| COGS? | Caldergate Data Hub, Caldergate FP&A | `(Account Type = Account Types.COGS)` |
| Current Period? | Caldergate Data Hub, Caldergate FP&A | `(ITEM(Time) = SYS00 Model Settings.Current Period)` |
| Employer NI | Caldergate FP&A, Workforce Planning | `(IF (Monthly Salary > NI Threshold) THEN ((Monthly Salary - NI Threshold) * NI R` |
| Group | Caldergate Data Hub, Caldergate FP&A | `PARENT(ITEM(Cost Centres))` |
| Opex? | Caldergate Data Hub, Caldergate FP&A | `(Account Type = Account Types.Opex)` |
| Revenue? | Caldergate Data Hub, Caldergate FP&A | `(Account Type = Account Types.Revenue)` |
| Sign | Caldergate Data Hub, Caldergate FP&A | `(IF 'Revenue?' THEN -1 ELSE 1)` |
| Working Days | Caldergate FP&A, Workforce Planning | `(Days in Month - Weekend Days - Bank Holidays)` |


# The estate

## The estate at a glance

| Model | Modules | Line items | Calculated | Cells | Parse | Imports | Exports | Processes | Latest run | Patterns |
|---|---|---|---|---|---|---|---|---|---|---|
| Caldergate Data Hub | 12 | 63 | 28 | 8.1M | 100.0% | 8 | 6 | 14 | 2026-09-21 | 5 |
| Caldergate FP&A | 30 | 278 | 171 | 130M | 100.0% | 10 | 4 | 15 | 2026-09-08 | 51 |
| Workforce Planning | 9 | 55 | 36 | 6.3M | 100.0% | 3 | 3 | 5 | 2026-09-08 | 14 |
| Board Reporting | 7 | 30 | 13 | 138K | 100.0% | 3 | 1 | 4 | 2026-09-08 | 3 |

## How the models connect (inferred)

| From | To | Import actions | Into (sample) | Named as |
|---|---|---|---|---|
| Caldergate Data Hub | Caldergate FP&A | 5 | DAT01 Actuals GL, DAT02 Actuals Volumes, SYS02 Cost Centre Attributes, SYS04 Product Attributes | Caldergate Data Hub |
| Caldergate FP&A | Board Reporting | 2 | DAT01 P&L, DAT02 Board Lines | Caldergate FP&A |
| Workforce Planning | Caldergate FP&A | 1 | INP03 Headcount | Workforce Planning |
| Caldergate Data Hub | Workforce Planning | 1 | Data - Cost Centre Map | Caldergate Data Hub |
| Caldergate FP&A | Workforce Planning | 1 | Inputs - Settings | Caldergate FP&A |
| Workforce Planning | Board Reporting | 1 | DAT03 Headcount | Workforce Planning |

```mermaid
flowchart LR
  M0["Caldergate Data Hub"]
  M1["Caldergate FP&A"]
  M2["Workforce Planning"]
  M3["Board Reporting"]
  M0 -->|5| M1
  M1 -->|2| M3
  M2 -->|1| M1
  M0 -->|1| M2
  M1 -->|1| M2
  M2 -->|1| M3
```

External sources named in import actions (not a model in this set):

- **NetSuite**: 3 action(s), e.g. Caldergate Data Hub: Import GL from NetSuite
- **Salesforce**: 3 action(s), e.g. Caldergate Data Hub: Import Orders from Salesforce
- **Workday**: 2 action(s), e.g. Caldergate Data Hub: Import Employees from Workday
- **PIM file**: 1 action(s), e.g. Caldergate Data Hub: Import Products from PIM file
- **Treasury file**: 1 action(s), e.g. Caldergate FP&A: Import FX from Treasury file
- **Caldergate Hub v1**: 1 action(s), e.g. Caldergate FP&A: Import from Caldergate Hub v1 - Cost Centres
- **Excel**: 1 action(s), e.g. Caldergate FP&A: Import Budget from Excel

## Logic duplicated across models

Same line item name with the same formula tree in more than one model. One change must be made in each.

| Line item | Models | Copies | Formula |
|---|---|---|---|
| COGS? | Caldergate Data Hub, Caldergate FP&A | 2 | `(Account Type = Account Types.COGS)` |
| Current Period? | Caldergate Data Hub, Caldergate FP&A | 2 | `(ITEM(Time) = SYS00 Model Settings.Current Period)` |
| Employer NI | Caldergate FP&A, Workforce Planning | 2 | `(IF (Monthly Salary > NI Threshold) THEN ((Monthly Salary - NI Threshold) * NI Rate) ELSE ` |
| Group | Caldergate Data Hub, Caldergate FP&A | 2 | `PARENT(ITEM(Cost Centres))` |
| Opex? | Caldergate Data Hub, Caldergate FP&A | 2 | `(Account Type = Account Types.Opex)` |
| Revenue? | Caldergate Data Hub, Caldergate FP&A | 2 | `(Account Type = Account Types.Revenue)` |
| Sign | Caldergate Data Hub, Caldergate FP&A | 2 | `(IF 'Revenue?' THEN -1 ELSE 1)` |
| Working Days | Caldergate FP&A, Workforce Planning | 2 | `(Days in Month - Weekend Days - Bank Holidays)` |

## Dimensions shared across models

Cost Centres (4), Departments (3), Accounts (2), Employees (2), Products (2), Regions (2), Roles (2)

---

# Caldergate Data Hub

| | |
|---|---|
| Modules | 12 |
| Line items | 63 (28 calculated, 35 input) |
| Cells (as exported) | 8.1M (8,060,698) |
| Dimensions | 6 |
| Formulas parsed | 100.00% (0 failed) |
| References | 24 line-item edges, 5 module edges |
| Agreement with Anaplan's Referenced By | 1.0 (ours only 0, Anaplan only 0; Anaplan-only edges are mostly line-item subsets via COLLECT(), which the export does not describe) |
| Circular references | 0 (0 through a time offset, 0 without) |
| Pass-through chains | 0 |
| Calculated but unreferenced | 46 |
| Line items with notes | 0% |
| Inputs used | Line Items + Modules + Actions; rules skipped: none |

## Where the calculation time goes (top 10 line items = 99.9% of the model's effort)

| Line item | Effort | Cells | Formula |
|---|---|---|---|
| DAT01 GL Transactions.Loaded? | 88.35% | 1.3M | `Journal Count > 0` |
| CAL01 Volume Summary.Units | 2.88% | 9.1K | `'DAT06 Sales Orders'.Units[SUM: 'DAT07 Customer Master'.Region]` |
| CAL01 Volume Summary.Revenue | 2.88% | 9.1K | `'DAT06 Sales Orders'.Order Revenue[SUM: 'DAT07 Customer Master'.Region]` |
| CAL01 Volume Summary.Orders | 2.88% | 9.1K | `'DAT06 Sales Orders'.Order Count[SUM: 'DAT07 Customer Master'.Region]` |
| DAT05 CRM Pipeline.Weighted Pipeline | 1.83% | 17.3K | `Open Pipeline * Probability` |
| CAL01 Volume Summary.Average Order Value | 0.96% | 9.1K | `DIVIDE(Revenue, Orders)` |
| DAT08 Employee Master.Employee Id | 0.07% | 1.9K | `CODE(ITEM(Employees))` |
| DAT03 Account Master.Sign | 0.03% | 262 | `IF Revenue? THEN -1 ELSE 1` |
| DAT07 Customer Master.Region Code | 0.03% | 480 | `CODE(Region)` |
| DAT03 Account Master.Revenue? | 0.02% | 262 | `Account Type = Account Types.Revenue` |
| DAT03 Account Master.Opex? | 0.02% | 262 | `Account Type = Account Types.Opex` |
| DAT03 Account Master.COGS? | 0.02% | 262 | `Account Type = Account Types.COGS` |
| DAT07 Customer Master.Customer Code | 0.02% | 480 | `CODE(ITEM(Customers))` |
| DAT03 Account Master.Account Code | 0.01% | 262 | `CODE(ITEM(Accounts))` |
| SYS02 Data Checks.Check Message | 0.01% | 36 | `IF Within Tolerance? THEN "OK" ELSE "GL and orders differ by " & TEXT(Difference` |

By module: DAT01 GL Transactions 88.3%, CAL01 Volume Summary 9.6%, DAT05 CRM Pipeline 1.8%, DAT03 Account Master 0.1%, DAT08 Employee Master 0.1%, DAT07 Customer Master 0.1%, SYS02 Data Checks 0.0%

## Largest modules by cells

| Module | Cells | Share |
|---|---|---|
| DAT01 GL Transactions | 5.0M | 62.3% |
| DAT06 Sales Orders | 2.9M | 36.0% |
| DAT05 CRM Pipeline | 86.4K | 1.1% |
| CAL01 Volume Summary | 36.3K | 0.5% |
| DAT08 Employee Master | 11.1K | 0.1% |
| DAT07 Customer Master | 2.4K | 0.0% |
| DAT03 Account Master | 1.8K | 0.0% |
| DAT02 Cost Centre Master | 1.2K | 0.0% |

## Most depended-on line items

| Line item | Direct dependents |
|---|---|
| DAT07 Customer Master.Region | 4 |
| DAT03 Account Master.Account Type | 3 |
| DAT06 Sales Orders.Order Revenue | 2 |
| SYS02 Data Checks.Difference | 2 |
| SYS00 Model Settings.Current Period | 1 |
| DAT01 GL Transactions.Journal Count | 1 |
| DAT03 Account Master.Revenue? | 1 |
| DAT05 CRM Pipeline.Open Pipeline | 1 |

## Actions

8 imports, 6 exports, 14 processes. Latest run 2026-09-21; stale = not run since 2025-09-26.

- Imports not in any process: 3 (e.g. Import Products from PIM file, Import Customers from Salesforce, Export Pipeline for Sales Ops)
- Stale or never-run imports and exports: 2 (e.g. Import Products from PIM file [2023-06-14], Export Pipeline for Sales Ops [2025-02-11])
- Slowest actions: Import GL from NetSuite 39s, Export GL to FP&A 10s, Import Employees from Workday 8s, Import Orders from Salesforce 2s, Import Customers from Salesforce 2s
- Most imported-into: DAT01 GL Transactions (1), DAT06 Sales Orders (1), DAT05 CRM Pipeline (1), DAT02 Cost Centre Master (1), DAT03 Account Master (1), DAT08 Employee Master (1)

## Patterns (5 findings in 5 patterns)

| Severity | Rule | Pattern | Count | Example | Fix |
|---|---|---|---|---|---|
| minor | A-SUMMARY-ON | DAT05 CRM Pipeline.Weighted Pipeline | 1 | DAT05 CRM Pipeline.Weighted Pipeline: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-TEXT-FORMAT | DAT01 GL Transactions.Source System | 1 | DAT01 GL Transactions.Source System: TEXT with 1,254,456 cells | Use a list-formatted item or move text to a system module. |
| minor | A-TEXT-FORMAT | DAT06 Sales Orders.Last Order Ref | 1 | DAT06 Sales Orders.Last Order Ref: TEXT with 725,760 cells | Use a list-formatted item or move text to a system module. |
| info | G-UNUSED | DAT01 GL Transactions.Loaded? | 1 | DAT01 GL Transactions.Loaded?: calculated, 1,254,456 cells, referenced by no formula | Check views and exports; remove if unused. |
| info | H-NOTES | (model) | 1 | (model): 8 of 12 modules have no notes; largest: DAT06 Sales Orders, DAT05 CRM  | Add a one-line purpose note to each module, largest first. |

---

# Caldergate FP&A

| | |
|---|---|
| Modules | 30 |
| Line items | 278 (171 calculated, 107 input) |
| Cells (as exported) | 130M (130,001,662) |
| Dimensions | 9 |
| Formulas parsed | 100.00% (0 failed) |
| References | 384 line-item edges, 54 module edges |
| Agreement with Anaplan's Referenced By | 1.0 (ours only 0, Anaplan only 0; Anaplan-only edges are mostly line-item subsets via COLLECT(), which the export does not describe) |
| Circular references | 1 (1 through a time offset, 0 without) |
| Pass-through chains | 4 |
| Calculated but unreferenced | 77 |
| Line items with notes | 3% |
| Inputs used | Line Items + Modules + Actions; rules skipped: none |

## Where the calculation time goes (top 10 line items = 68.0% of the model's effort)

| Line item | Effort | Cells | Formula |
|---|---|---|---|
| CAL03 Opex.Forecast Opex | 16.04% | 5.0M | `IF ITEM(Accounts) = Accounts.'6100 Rent' THEN 'INP02 Opex Drivers'.Rent ELSE IF ` |
| CAL03 Opex.Opex GBP | 9.26% | 5.0M | `Opex * 'SYS05 FX Rates'.Rate to GBP[LOOKUP: 'SYS02 Cost Centre Attributes'.Curre` |
| CAL05 Opex OLD.Opex GBP | 9.26% | 5.0M | `Opex * 'SYS05 FX Rates'.Rate to GBP[LOOKUP: 'SYS02 Cost Centre Attributes'.Curre` |
| CAL05 Opex OLD.Forecast | 6.94% | 5.0M | `Rent Forecast + Rates Forecast + Utilities Forecast + Travel Forecast + Marketin` |
| DAT01 Actuals GL.Journal Cost Centre | 6.17% | 5.0M | `FINDITEM(Cost Centres, Source Journal)` |
| CAL03 Opex.Opex | 4.94% | 5.0M | `IF 'SYS01 Time Settings'.Actual? THEN Actual Opex ELSE Forecast Opex` |
| CAL05 Opex OLD.Opex | 4.94% | 5.0M | `IF 'SYS01 Time Settings'.Actual? THEN Actual ELSE Forecast` |
| CAL03 Opex.Actual Opex | 3.70% | 5.0M | `IF 'SYS03 Account Attributes'.Opex? THEN 'DAT01 Actuals GL'.Amount ELSE 0` |
| CAL05 Opex OLD.Actual | 3.70% | 5.0M | `IF 'SYS01 Time Settings'.Actual? THEN 'DAT01 Actuals GL'.Amount ELSE 0` |
| CAL05 Opex OLD.Opex Cumulative | 3.09% | 5.0M | `CUMULATE(Opex GBP)` |
| CAL05 Opex OLD.Opex Run Rate | 3.09% | 5.0M | `MOVINGSUM(Opex GBP, -2, 0) / 3` |
| CAL05 Opex OLD.Rent Forecast | 2.47% | 5.0M | `IF ITEM(Accounts) = Accounts.'6100 Rent' THEN 'INP02 Opex Drivers'.Rent ELSE 0` |
| CAL05 Opex OLD.Rates Forecast | 2.47% | 5.0M | `IF ITEM(Accounts) = Accounts.'6110 Rates' THEN 'INP02 Opex Drivers'.Business Rat` |
| CAL05 Opex OLD.Utilities Forecast | 2.47% | 5.0M | `IF ITEM(Accounts) = Accounts.'6120 Utilities' THEN 'INP02 Opex Drivers'.Utilitie` |
| CAL05 Opex OLD.Travel Forecast | 2.47% | 5.0M | `IF ITEM(Accounts) = Accounts.'6200 Travel' THEN 'INP02 Opex Drivers'.Travel ELSE` |

By module: CAL05 Opex OLD 50.8%, CAL03 Opex 37.8%, DAT01 Actuals GL 7.7%, INP03 Headcount 2.1%, CAL12 Driver Phasing 0.4%, INP02 Opex Drivers 0.3%, CAL02 Revenue 0.2%, CAL01 Volumes 0.1%

## Largest modules by cells

| Module | Cells | Share |
|---|---|---|
| CAL05 Opex OLD | 70.2M | 54.0% |
| CAL03 Opex | 30.1M | 23.2% |
| DAT01 Actuals GL | 20.1M | 15.4% |
| INP03 Headcount | 5.9M | 4.6% |
| INP02 Opex Drivers | 1.1M | 0.9% |
| CAL12 Driver Phasing | 594K | 0.5% |
| CAL02 Revenue | 435K | 0.3% |
| INP01 Volumes | 254K | 0.2% |

## Most depended-on line items

| Line item | Direct dependents |
|---|---|
| SYS01 Time Settings.Actual? | 36 |
| SYS02 Cost Centre Attributes.Department | 6 |
| SYS05 FX Rates.Rate to GBP | 6 |
| CAL02 Revenue.Net Revenue | 6 |
| INP02 Opex Drivers.Rent | 5 |
| INP02 Opex Drivers.Business Rates | 5 |
| INP02 Opex Drivers.Utilities | 5 |
| INP02 Opex Drivers.Travel | 5 |

## Actions

10 imports, 4 exports, 15 processes. Latest run 2026-09-08; stale = not run since 2025-09-13.

- Imports not in any process: 5 (e.g. Import FX from Treasury file, Import from Caldergate Hub v1 - Cost Centres, Import Budget from Excel, Export Assumptions for Workforce)
- Stale or never-run imports and exports: 3 (e.g. Import FX from Treasury file [2023-11-02], Import from Caldergate Hub v1 - Cost Centres [2021-03-19], Export Opex Drivers to Excel [2024-05-30])
- Slowest actions: Import from Caldergate Data Hub - GL Actuals 58s, Import from Workforce Planning - Headcount Cost 8s, Import Budget from Excel 4s, Export Board Pack 3s, Import from Caldergate Data Hub - Volumes 3s
- Most imported-into: SYS02 Cost Centre Attributes (2), DAT01 Actuals GL (1), DAT02 Actuals Volumes (1), SYS04 Product Attributes (1), SYS03 Account Attributes (1), INP03 Headcount (1)

## Patterns (68 findings in 51 patterns)

| Severity | Rule | Pattern | Count | Example | Fix |
|---|---|---|---|---|---|
| major | A-DAISY | OUT01 Management Pack.Opex | 1 | OUT01 Management Pack.Opex: 4-step pass-through chain ending at CAL03 Opex.Opex GBP | Reference CAL03 Opex.Opex GBP directly. |
| major | A-DAISY | OUT01 Management Pack.Staff Cost | 1 | OUT01 Management Pack.Staff Cost: 4-step pass-through chain ending at INP03 Headcount.Total Cost | Reference INP03 Headcount.Total Cost directly. |
| major | A-DAISY | OUT02 Board Pack.EBITDA | 1 | OUT02 Board Pack.EBITDA: 4-step pass-through chain ending at CAL07 P&L by Cost Centre.EBITDA | Reference CAL07 P&L by Cost Centre.EBITDA directly. |
| major | A-DAISY | OUT02 Board Pack.Revenue | 1 | OUT02 Board Pack.Revenue: 4-step pass-through chain ending at CAL07 P&L by Cost Centre.Revenue | Reference CAL07 P&L by Cost Centre.Revenue directly. |
| major | A-IF-COUNT | CAL03 Opex.Forecast Opex | 1 | CAL03 Opex.Forecast Opex: 12 IF THEN ELSE in one formula | Split conditions into Boolean line items or use a mapping module with  |
| major | A-LI-COUNT | INP02 Opex Drivers | 1 | INP02 Opex Drivers: 58 line items | Split into modules by purpose (DISCO). |
| major | A-SUBSIDIARY | CAL01 Volumes.Launched? | 1 | CAL01 Volumes.Launched?: applies to Products in a module on Products, Regions; used by 1 formul | Move to a module dimensioned as the line item is. |
| major | F-DIVIDE | CAL02 Revenue.Revenue per Unit | 1 | CAL02 Revenue.Revenue per Unit: unguarded / by a line item | Use DIVIDE(a, b) or IF b <> 0 THEN a / b ELSE 0. |
| major | F-MIXED-CLAUSE | CAL06 Department Summary.Benchmark Opex | 1 | CAL06 Department Summary.Benchmark Opex: [LOOKUP + SUM] in one bracket | Split into two line items: aggregate first, then look up. |
| minor | A-SUMMARY-ON | OUT01 Management Pack (9 line items) | 9 | OUT01 Management Pack.Capex: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-SYSTEMS-FN | CAL05 Opex OLD (8 line items) | 8 | CAL05 Opex OLD.Fees Forecast: ITEM in a 5,017,824-cell line item | Compute in a single-dimension systems module and reference it. |
| minor | A-SUMMARY-ON | CAL02 Revenue (3 line items) | 3 | CAL02 Revenue.Average Price: summary FORMULA, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-FINDITEM | DAT01 Actuals GL.Journal Cost Centre | 1 | DAT01 Actuals GL.Journal Cost Centre: FINDITEM in a 5,017,824-cell line item | Map once in a systems module. |
| minor | A-SUMMARY-ON | CAL01 Volumes.Volume Growth | 1 | CAL01 Volumes.Volume Growth: summary FORMULA, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-SUMMARY-ON | CAL02 Revenue.Revenue USD | 1 | CAL02 Revenue.Revenue USD: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-SUMMARY-ON | CAL02 Revenue.VAT | 1 | CAL02 Revenue.VAT: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-SUMMARY-ON | CAL03 Opex.Opex Variance | 1 | CAL03 Opex.Opex Variance: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-SUMMARY-ON | CAL04 Margn.Margin % | 1 | CAL04 Margn.Margin %: summary FORMULA, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-SUMMARY-ON | CAL04 Margn.Margin GBP | 1 | CAL04 Margn.Margin GBP: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-SUMMARY-ON | CAL05 Opex OLD.Opex Cumulative | 1 | CAL05 Opex OLD.Opex Cumulative: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| | | ... 31 more patterns | | | |

---

# Workforce Planning

| | |
|---|---|
| Modules | 9 |
| Line items | 55 (36 calculated, 19 input) |
| Cells (as exported) | 6.3M (6,343,559) |
| Dimensions | 4 |
| Formulas parsed | 100.00% (0 failed) |
| References | 64 line-item edges, 11 module edges |
| Agreement with Anaplan's Referenced By | 1.0 (ours only 0, Anaplan only 0; Anaplan-only edges are mostly line-item subsets via COLLECT(), which the export does not describe) |
| Circular references | 0 (0 through a time offset, 0 without) |
| Pass-through chains | 0 |
| Calculated but unreferenced | 14 |
| Line items with notes | 2% |
| Inputs used | Line Items + Modules + Actions; rules skipped: none |

_No Calculation Effort column in this export (Blueprint > Calculation Effort, Classic engine, from March 2025)._

## Largest modules by cells

| Module | Cells | Share |
|---|---|---|
| Calcs - Headcount by CC | 3.0M | 46.8% |
| Calcs - Cost | 2.4M | 37.8% |
| Data - Employees | 666K | 10.5% |
| Calcs - Attrition | 284K | 4.5% |
| zz Archive - 2021 Cost | 13.4K | 0.2% |
| Reports - Headcount | 13.0K | 0.2% |
| Data - Cost Centre Map | 532 | 0.0% |
| Inputs - Calendar | 252 | 0.0% |

## Most depended-on line items

| Line item | Direct dependents |
|---|---|
| Data - Employees.Role | 8 |
| Calcs - Cost.Inflated Salary | 4 |
| Data - Employees.FTE | 3 |
| Data - Employees.Cost Centre | 3 |
| Reports - Headcount.FTE | 3 |
| Data - Employees.End Date | 2 |
| Calcs - Cost.Monthly Salary | 2 |
| Calcs - Cost.Total Cost | 2 |

## Actions

3 imports, 3 exports, 5 processes. Latest run 2026-09-08; stale = not run since 2025-09-13.

- Imports not in any process: 3 (e.g. Import from Caldergate FP&A - Assumptions, Export Headcount by Department, Export Leavers Report)
- Stale or never-run imports and exports: 2 (e.g. Import from Caldergate FP&A - Assumptions [2022-08-17], Export Leavers Report [2024-12-19])
- Slowest actions: Import Employees from Workday 22s, Export Headcount Cost to FP&A 4s, Import from Caldergate Data Hub - Cost Centre Map 0s, Export Headcount by Department 0s, Export Leavers Report 0s
- Most imported-into: Data - Employees (1), Data - Cost Centre Map (1), Inputs - Settings (1)

## Patterns (14 findings in 14 patterns)

| Severity | Rule | Pattern | Count | Example | Fix |
|---|---|---|---|---|---|
| major | A-SUBSIDIARY | Calcs - Attrition.Leavers | 1 | Calcs - Attrition.Leavers: applies to Employees in a module on Roles; used by 1 formulas | Move to a module dimensioned as the line item is. |
| major | F-DIVIDE | Calcs - Attrition.Annualised Attrition | 1 | Calcs - Attrition.Annualised Attrition: unguarded / by a line item | Use DIVIDE(a, b) or IF b <> 0 THEN a / b ELSE 0. |
| major | F-DIVIDE | Calcs - Attrition.Attrition % | 1 | Calcs - Attrition.Attrition %: unguarded / by a line item | Use DIVIDE(a, b) or IF b <> 0 THEN a / b ELSE 0. |
| minor | A-SUMMARY-ON | Calcs - Headcount by CC.Average Salary | 1 | Calcs - Headcount by CC.Average Salary: summary FORMULA, referenced by no formula | Set summary to None unless a view needs the total. |
| minor | A-TEXT-FORMAT | Data - Employees.Employee Name | 1 | Data - Employees.Employee Name: TEXT with 66,600 cells | Use a list-formatted item or move text to a system module. |
| minor | A-TEXT-FORMAT | Data - Employees.Name and Role | 1 | Data - Employees.Name and Role: TEXT with 66,600 cells | Use a list-formatted item or move text to a system module. |
| minor | A-TEXT-JOIN | Data - Employees.Name and Role | 1 | Data - Employees.Name and Role: & in a 66,600-cell line item | Build the text once in a systems module. |
| minor | F-HARDCODE | Calcs - Attrition.Annualised Attrition | 1 | Calcs - Attrition.Annualised Attrition: constants 11 | Move to an input line item with a name and a note. |
| minor | F-HARDCODE | Calcs - Cost.Bonus | 1 | Calcs - Cost.Bonus: constants 0.1 | Move to an input line item with a name and a note. |
| minor | F-HARDCODE | Calcs - Headcount by CC.Bonus % | 1 | Calcs - Headcount by CC.Bonus %: constants 0.1 | Move to an input line item with a name and a note. |
| info | G-UNUSED | Calcs - Headcount by CC.Average Salary | 1 | Calcs - Headcount by CC.Average Salary: calculated, 593,712 cells, referenced by no formula | Check views and exports; remove if unused. |
| info | G-UNUSED | Calcs - Headcount by CC.Bonus % | 1 | Calcs - Headcount by CC.Bonus %: calculated, 593,712 cells, referenced by no formula | Check views and exports; remove if unused. |
| info | G-UNUSED | Data - Employees.Name and Role | 1 | Data - Employees.Name and Role: calculated, 66,600 cells, referenced by no formula | Check views and exports; remove if unused. |
| info | H-NOTES | (model) | 1 | (model): 5 of 9 modules have no notes; largest: Calcs - Cost, Calcs - Attrition | Add a one-line purpose note to each module, largest first. |

---

# Board Reporting

| | |
|---|---|
| Modules | 7 |
| Line items | 30 (13 calculated, 17 input) |
| Cells (as exported) | 138K (137,882) |
| Dimensions | 2 |
| Formulas parsed | 100.00% (0 failed) |
| References | 16 line-item edges, 6 module edges |
| Agreement with Anaplan's Referenced By | 1.0 (ours only 0, Anaplan only 0; Anaplan-only edges are mostly line-item subsets via COLLECT(), which the export does not describe) |
| Circular references | 0 (0 through a time offset, 0 without) |
| Pass-through chains | 0 |
| Calculated but unreferenced | 20 |
| Line items with notes | 0% |
| Inputs used | Line Items + Modules + Actions; rules skipped: none |

## Where the calculation time goes (top 10 line items = 89.7% of the model's effort)

| Line item | Effort | Cells | Formula |
|---|---|---|---|
| CAL01 KPIs.Revenue per FTE | 11.21% | 144 | `'DAT02 Board Lines'.Revenue / FTE` |
| CAL01 KPIs.Opex Ratio | 11.21% | 144 | `DIVIDE('DAT01 P&L'.Opex, 'DAT01 P&L'.Revenue)` |
| CAL01 KPIs.Revenue Growth | 11.21% | 144 | `DIVIDE('DAT02 Board Lines'.Revenue - Revenue Prior Year, Revenue Prior Year)` |
| CAL01 KPIs.EBITDA Margin | 11.21% | 144 | `DIVIDE('DAT02 Board Lines'.EBITDA, 'DAT02 Board Lines'.Revenue)` |
| CAL01 KPIs.FTE | 7.48% | 144 | `'DAT03 Headcount'.FTE` |
| CAL01 KPIs.Revenue Prior Year | 7.48% | 144 | `LAG('DAT02 Board Lines'.Revenue, 12, 0)` |
| CAL01 KPIs.Revenue YTD | 7.48% | 144 | `YEARTODATE('DAT02 Board Lines'.Revenue)` |
| OUT01 Board Dashboard.Revenue | 7.48% | 144 | `'DAT02 Board Lines'.Revenue` |
| OUT01 Board Dashboard.EBITDA | 7.48% | 144 | `'DAT02 Board Lines'.EBITDA` |
| OUT01 Board Dashboard.Revenue per FTE | 7.48% | 144 | `'CAL01 KPIs'.Revenue per FTE` |
| OUT01 Board Dashboard.Revenue Growth | 7.48% | 144 | `'CAL01 KPIs'.Revenue Growth` |
| SYS01 Time.Current Period? | 1.87% | 36 | `ITEM(Time) = 'SYS00 Settings'.Current Period` |
| SYS01 Time.Period Label | 0.93% | 36 | `NAME(ITEM(Time))` |

By module: CAL01 KPIs 67.3%, OUT01 Board Dashboard 29.9%, SYS01 Time 2.8%

## Largest modules by cells

| Module | Cells | Share |
|---|---|---|
| DAT01 P&L | 134K | 97.2% |
| DAT03 Headcount | 1.3K | 0.9% |
| CAL01 KPIs | 1.0K | 0.7% |
| OUT01 Board Dashboard | 864 | 0.6% |
| DAT02 Board Lines | 576 | 0.4% |
| SYS01 Time | 72 | 0.1% |
| SYS00 Settings | 2 | 0.0% |

## Most depended-on line items

| Line item | Direct dependents |
|---|---|
| DAT02 Board Lines.Revenue | 6 |
| DAT02 Board Lines.EBITDA | 2 |
| SYS00 Settings.Current Period | 1 |
| DAT03 Headcount.FTE | 1 |
| CAL01 KPIs.FTE | 1 |
| DAT01 P&L.Opex | 1 |
| DAT01 P&L.Revenue | 1 |
| CAL01 KPIs.Revenue Prior Year | 1 |

## Actions

3 imports, 1 exports, 4 processes. Latest run 2026-09-08; stale = not run since 2025-09-13.

- Imports not in any process: 1 (e.g. Export Board Pack PDF Data)
- Stale or never-run imports and exports: 0
- Slowest actions: Import from Caldergate FP&A - P&L by Cost Centre 3s, Import from Caldergate FP&A - Board Pack 1s, Import from Workforce Planning - Headcount by Department 0s, Export Board Pack PDF Data 0s
- Most imported-into: DAT01 P&L (1), DAT02 Board Lines (1), DAT03 Headcount (1)

## Patterns (7 findings in 3 patterns)

| Severity | Rule | Pattern | Count | Example | Fix |
|---|---|---|---|---|---|
| major | F-DIVIDE | CAL01 KPIs.Revenue per FTE | 1 | CAL01 KPIs.Revenue per FTE: unguarded / by a line item | Use DIVIDE(a, b) or IF b <> 0 THEN a / b ELSE 0. |
| minor | A-SUMMARY-ON | DAT01 P&L (5 line items) | 5 | DAT01 P&L.COGS: summary SUM, referenced by no formula | Set summary to None unless a view needs the total. |
| info | H-NOTES | (model) | 1 | (model): 5 of 7 modules have no notes; largest: DAT03 Headcount, CAL01 KPIs, OU | Add a one-line purpose note to each module, largest first. |

## Procedures performed

Every formula parsed with anaplan-grammar; dependency graph built from the parse trees and checked against Anaplan's Referenced By column; rules below run where the inputs allow; findings grouped into patterns. No opinion is expressed; nothing here says whether a finding matters for this model.

| Rule | Severity | Source | Description |
|---|---|---|---|
| A-LI-COUNT More than 50 line items in a module | major | ANAPLAN | Modules with many line items are slow to open and hard to maintain. Anaplan's checklist: no more than 50. |
| A-SUMMARY-ON Summary method on where a formula suggests it is not needed | minor | ANAPLAN | Summaries calculate on every parent; turn them off unless a parent value is used. Flags large number line item |
| A-TEXT-FORMAT Text-formatted line item | minor | ANAPLAN | Text line items use more memory and cannot aggregate. Anaplan's checklist: minimise; prefer list-formatted ite |
| A-SUBSIDIARY Subsidiary view on a calculation line item | major | ANAPLAN | A line item whose Applies To differs from its module's is a subsidiary view. Anaplan's checklist: display and  |
| A-DAISY Daisy-chain formula | major | ANAPLAN | A references B references C where each is a pure pass-through; the whole sequence recalculates on any change.  |
| A-IF-COUNT Formula with more than 10 IF THEN ELSE | major | ANAPLAN | Anaplan's checklist: refactor above 10 IF conditions; use a LOOKUP or Boolean flag line items. |
| A-SYSTEMS-FN Unchanging function in a calculation module | minor | ANAPLAN | PARENT(), text joins, START(), CURRENTPERIODSTART() produce values that do not change per cell; Anaplan's chec |
| A-TEXT-JOIN Text concatenation in a large line item | minor | ANAPLAN | Anaplan's checklist: combining text strings takes memory; restructure into systems modules. |
| A-FINDITEM FINDITEM in a large line item | minor | ANAPLAN | Anaplan's checklist: FINDITEM is expensive; minimise and null-check first. |
| F-MIXED-CLAUSE SUM and LOOKUP (or SELECT) in one bracket | major | FORMULA | Anapedia: never combine SUM with LOOKUP or SELECT in the same expression; the engine builds a large intermedia |
| F-HARDCODE Hard-coded constant in a formula | minor | FORMULA | Numbers other than 0, 1, 100, 12 inside formulas are assumptions that belong in an input line item. |
| F-LONG Very long formula | minor | FORMULA | Anaplan's checklist: a formula should be explainable in one sentence. |
| F-DIVIDE Division with no zero guard | major | FORMULA | A / B errors when B is zero; the summary then shows an error too. Use DIVIDE() or guard with IF. |
| F-PARSE Formula does not parse | critical | FORMULA | The parser rejected this formula; either the grammar has a gap or the export is corrupt. |
| G-CYCLE Circular reference | info | GRAPH | Line items that depend on each other at the line-item level. Anaplan rejects a direct circular reference at fo |
| G-UNUSED Line item with a formula that nothing references | info | GRAPH | Not used by any formula. May be used by a view, export or dashboard, which the exports do not show; confirm be |
| G-HUB Hub line item | info | GRAPH | Referenced by many line items; a change here has a wide blast radius. Not a fault, a fact for reviewers. |
| G-EMPTY-MODULE Module with no line items | minor | GRAPH | Empty modules are usually leftovers. |
| H-NOTES Modules without notes | info | GRAPH | Documentation coverage. One finding per model: how many modules carry no notes, and the largest of them. |