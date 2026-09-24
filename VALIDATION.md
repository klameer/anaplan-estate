# Validation status and follow-up protocol

## What has been checked (implementation checks)

These establish that the mechanics do what they say. They do not establish
generalisation, recommendation quality or user value.

- Automated tests (`python -m pytest -q tests`): 63 tests over the parser and
  rules, the example estate, the action-plan selection, the change-impact
  traversal, corrected facts, input guards, HTML views and exports. The page script's
  breadth-first traversal is executed under node on a synthetic graph and
  compared with the Python implementation.
- The Change impact explorer reconciles with the analysis engine on the
  example estate (every model's top three hubs) and on one private real estate
  (the widest-read line item: 197 direct readers, 822 unique downstream line
  items across 56 modules, twelve links deep; the ten export actions listed
  are module-level associations, not ten proven consumers).
- Plan length: the plan now shows every candidate (those that met the bar
  first, the rest labelled with the reason), grouped, with a summary table on
  top; on the private estate that is 14 cards. The earlier three-action,
  450-word, one-page version was measured (441 and 446 visible words, one A4
  page in headless Edge) before that change; the current plan prints on
  several pages. "Print evidence" remains a separate, explicit choice.
- Browser checks (desktop pane): no console errors on load; deep links
  `#F12`, `#impact`, `#impact=<node>`, `#catalogue` open the right view, clear
  conflicting filters visibly, focus the target and select the row; the
  explorer renders summary, columns, table and paths. Narrow-screen layout
  rests on the stylesheet's responsive rules; viewport emulation did not take
  effect in the tooling used, so it was not observed in a browser.

## Input variations checked (generalisation of the loader, not of the advice)

Variants of the example export were fed through the whole pipeline. Before the
input guards (added the same day) every one of these produced a report with no
error; the outcome column is after the guards.

| Variation | Outcome now |
|---|---|
| Semicolon or tab delimiter | sniffed; identical results; notice shown |
| No Formula column | stops with a message listing the columns found |
| No Format column | all 278 line items kept (before: 107 inputs dropped as headers); column listed as absent |
| No Cell Count column | cells "unavailable", not zero; notice on the plan; rule skipped and listed |
| No Referenced By column | agreement "not checkable" (before: 0%) |
| No Calculation Effort column | effort unavailable, as before |
| No Module Name column | modules taken from header rows, as before |
| Comma decimals (16,04) and dot thousands (5.017.824) | read correctly; effort values over 100% flagged as unreliable |
| cp1252 encoding | decoded with a notice |
| Every formula unparseable / no formulas | reported as parse coverage 0% / no graph; no actions meet the bar |
| Names with commas, parentheses, dots, duplicates across modules | handled |
| 11,000 line items (40 replicated modules) | 4 s, 8.8 MB page; above 25,000 line items the page drops the per-finding search index and says so |

Not covered: exports with localised (non-English) column headers stop at the
Formula check with a message; Polaris versus Classic effort semantics remain
unknown from the export; naming heuristics (output-module prefixes, "from X" in
import names) are labelled inferred and simply find less on other conventions.
The action cards match five patterns only; the report says so on the plan.

## What remains pending (product validation)

The rules, ranking and presentation were developed around one real estate and
one fictional estate constructed around known scenarios. The "worth doing"
bar and the ordering are design choices, not established optima; the ranking
is a hypothesis. Nothing below has been done yet.

### Unseen-estate protocol

1. Obtain written permission to run the tool on genuinely unseen estates with
   different designs and use cases (different partner, industry, model size,
   engine). Record the tool version (git commit) and the rule set.
2. Freeze the first outputs (HTML, JSON, register) before any adaptation to
   that estate. Keep at least one estate aside from all tuning. Random
   line-item splits or repeated snapshots of the same estate do not count as
   independent estates.
3. Once an estate has been used to fix or tune anything, later results on it
   are regression evidence, not a fresh unseen test. Say so in the record.

### Expert and owner expectations, before seeing the ranking

1. An experienced reviewer and the estate owner each record, before opening
   the report: the facts they expect (hotspots, unused modules, duplicates,
   stale imports), the improvement candidates they consider valuable, and
   important exceptions (things that look wrong but are right).
2. Then compare with the report: record disagreements, missing business
   context, and both the selected actions and significant opportunities the
   report omitted.

### Scoring, kept separate

Score three things separately, per estate, as cases and counts (small samples
are never reported as accuracy percentages):

- Facts: correct detections, false alarms, facts missed.
- Recommended actions: unsupported or unsafe advice; advice that is supported
  but not worth doing; advice judged useful by the reviewer and owner
  independently.
- Priority choices: whether the actions that met the bar are the ones the
  reviewer and owner would have chosen first; which material opportunity, if
  any, was left out or placed below the bar.

Include negative cases on purpose: an estate where keeping the current design
is the right answer, an estate with a missing Actions export, a legitimate
high-fan-out object, intentional duplication (access boundary, reporting
contract), and an estate where the inputs support no worthwhile change (the
report should say so and name the next data check).

### Presentation test with representative users

1. Recruit model owners, builders and consultants who have not seen the estate.
2. Give comparable tasks on the short presentation and on the fuller catalogue
   view: choose an appropriate next action, explain its evidence and limits,
   identify what it depends on, describe a validation step. No coaching.
3. Vary the order of presentations between participants to limit learning
   effects. Record errors and time to completion, not only preferences about
   length.

### Establishing actual benefit

A reviewer agreeing that something deserves investigation is not a saving.
Benefit is established only after an authorised change is validated in a
development copy with comparable inputs and scenarios, then measured in
production with the relevant operational readings (Calculation Effort before
and after within the same model, model open time, workspace size). Record the
baseline, the change, the reconciliation and the readings with dates.

## What this release can support

An exploratory pilot on an estate whose owner understands the above, with the
free report as the starting point and the pending validation recorded per
estate. Broader claims (accuracy, typical savings, "best" improvements) remain
unproven and must not be made.
