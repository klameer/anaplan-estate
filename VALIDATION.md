# Validation status and follow-up protocol

## What has been checked (implementation checks)

These establish that the mechanics do what they say. They do not establish
generalisation, recommendation quality or user value.

- Automated tests (`python -m pytest -q tests`): 134 tests over the parser and
  rules, the test catalogue, the example estate, the action-plan selection,
  the change-impact traversal, corrected facts, input guards, thin and hostile
  input, HTML views and exports. Run on Python 3.10, 3.11, 3.12, 3.13 and
  3.14, with anaplan-grammar installed from its public repository as CI and
  the Dockerfile install it. The page script's breadth-first traversal is
  executed under node on a synthetic graph and compared with the Python
  implementation.
- The Change impact explorer reconciles with the analysis engine on the
  example estate (every model's top three hubs) and on one private real estate
  (the widest-read line item: 197 direct readers, 822 unique downstream line
  items across 56 modules, twelve links deep; the ten export actions listed
  are module-level associations, not ten proven consumers).
- Plan: every test that found something offers a candidate action; the
  first five that meet the bar are the plan (`--top N`), and every other
  candidate is listed beneath it with the reason. On the private estate that
  is 5 cards from 125 candidates, 32 of which met the bar. The earlier
  three-action, 450-word, one-page version was measured (441 and 446 visible
  words, one A4 page in headless Edge) before these changes; the current plan
  prints on several pages. "Print evidence" remains a separate, explicit choice.
- Browser checks (desktop pane): no console errors on load; deep links
  `#F12`, `#impact`, `#impact=<node>`, `#catalogue` open the right view, clear
  conflicting filters visibly, focus the target and select the row; the
  explorer renders summary, columns, table and paths. At a 375-pixel
  viewport the home page, the list of tests and the report lay out without
  horizontal scrolling (the report declares its encoding and viewport, so a
  saved copy opens the same way from disk).

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
Four kinds of action card are written by hand (a heavy line item matched to the
pattern that explains it, the largest module nothing reads, the largest
duplicated calculation, a long IF chain); every other card is assembled from
its finding's own fields and reads more plainly.

## Checks made before the 42-test release (2026-09-30)

These are still implementation checks. They say the tool runs, counts
consistently and fails safely; they do not say the advice is right.

- **Real exports.** Eleven real model exports went through the whole pipeline:
  six models of one private estate and five single-model exports, the largest
  16,987 line items. No crash; the slowest took 3.5 seconds end to end through
  the web service and produced an 8.7 MB page. Formulas parsed: 100%.
- **What the first real run changed.** Four of the seven tests added with the
  catalogue were wrong or noisy on real models and were corrected the same
  day: summed ratios were mostly currency conversions and spreads (the test
  now looks only at percentage-formatted line items: 40 hits became 1 on the
  private estate, and 28 plausible ones on another model); the odd one out
  caught subtotals among the line items they add up; leftover names caught
  'Delete?' flags and version names; unused dimensions caught flags, line
  item subset modules and list properties. Those estates are now regression
  evidence for these tests, not unseen tests of them.
- **Known weak spots after that.** The odd one out is noisy in runs of only
  five or six line items; unused dimensions still reports flags dimensioned by
  Users; summed ratios that are not formatted as a percentage are missed.
- **Thin input.** Each optional column of the Line Items export removed in
  turn, and all at once: no crash, and no test that found something on the
  full export reports "clear" on the thinner one. It reports "not run" and
  names the column.
- **Hostile input.** Module, line item, action and model names, notes and
  formulas carrying markup: none reaches the page as markup, and the embedded
  data cannot close its own script element.
- **The service over HTTP.** Every page; zip and per-model uploads; a real
  six-model estate; refusals (not a zip, no Line Items file, no Formula
  column, empty, binary, nothing, 81 MB) each with a plain page and no
  traceback; eight uploads at once; no temporary folder left behind.
- **Independent code review** of the change, which found and led to fixes
  for: a syntax error on Python 3.10 and 3.11, tests reported clear when a
  column they rely on was absent, counts that multiplied when two folders
  cleaned to one model name, a count that disagreed with its finding, and
  quadratic work on very large findings.
- **Same input twice** gives the same report, byte for byte.

## What remains pending (product validation)

The rules, ranking and presentation were developed around one real estate and
one fictional estate constructed around known scenarios, and since adjusted
against four further single-model exports. The "worth doing"
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
