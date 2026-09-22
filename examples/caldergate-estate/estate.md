# Anaplan estate: 4 models

Generated 2026-09-22 from each model's Line Items and Actions exports. Deterministic; no opinion. Model-to-model links are inferred from import action names and say so.

## In one page

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

## How to read this report

Two parts. The first four sections look across the estate. Then one chapter per model, all the same shape, so you can compare them. The last section lists what was checked. In the HTML view each chapter is folded; open the one you came for.

| Section | What it tells you |
|---|---|
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