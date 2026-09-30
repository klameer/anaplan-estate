# Changelog

## Unreleased

- The tests are now a numbered catalogue (`checks.py`, published as
  docs/TESTS.md and at /tests): 42 tests in six areas. The home page says
  what to upload, what is tested and what comes back. The report's Evidence
  view opens on "Tests run", each test with its result (found, clear, or
  not run and why), and every finding carries the number of the test that
  produced it.
- The action plan is now picked from the results of every test: each test
  that found something offers a candidate, candidates are ranked (evidence,
  scope, materiality, change before investigation, ease, footprint), and
  the first five that meet the bar are the plan (`--top N`, `ESTATE_TOP`).
  Materiality comes from measured effort and cells, or is fixed by the test
  where cells say nothing about what is at stake: a total that may be wrong
  ranks high, upkeep ranks low. Everything else is listed under the plan
  with the reason. The four grouped sections are gone.
- Home page and /tests: "Don't see a test you want?" with a way to get in
  touch.
- Seven new tests: line items with a dimension their formula does not use
  (1.7, with the cells that repeat a value), where the cells are (1.8), data
  loaded but never read (2.4), names that say leftover (2.5), ratios whose
  totals are added up (4.16), the odd one out in a run of matching formulas
  (4.17), several imports loading one target (5.4). Developed on the
  fictional estate; not yet run against an unseen one.
- Example estate: one summed ratio and one odd one out planted (PLANTED.md
  rows 29 and 30).

- Hosted page at anaplan-estate.codelessops.com: the example first ("what
  could changing Forecast Opex affect?"), two buttons under the headline,
  a one-model form with the zip as the alternative, inline validation, the
  local browser interface first in the local instructions, a private
  contact route beside the public feedback route.
- IF-chain advice framed as a refactoring candidate whose performance is
  measured, not assumed; below-the-bar reasons state the figures actually
  used.
- Service: fail-fast upload checks, per-request subprocess with a bounded
  pool, usage counted without personal data, example cached.

## 0.1.0 (2026-09-24)

First release.

- Action plan: every candidate action, grouped (make heavy calculations
  cheaper, remove duplicated calculations, check whether modules are still
  used, look at where the calculation time goes), those that meet a stated
  "worth doing" bar first, the rest labelled with the reason; plain-language
  cards with the named line items and their formulas, steps and a completion
  check; summary table on top.
- Change impact explorer: what a line item or module depends on and what
  depends on it, shortest-link distances, a diagram, module-level action
  links, inferred model feeds shown as a boundary, change-review download.
- Evidence: the complete findings catalogue with search, filters, local
  status and notes, working-register download, coverage, methodology,
  glossary.
- Input guards: delimiter and encoding sniffing, locale numbers, a required
  Formula column, absent columns reported as unavailable rather than zero,
  module dimensions inferred when no Modules export is supplied.
- Web front (`anaplan-estate-web`, Dockerfile, railway.toml): upload a zip
  or per-model files, get the report; bad uploads refused before analysis;
  each analysis in its own subprocess with a bounded pool; usage counted
  without personal data.
- Parse cache: one parse per distinct formula.
- 74 tests; VALIDATION.md records what has been checked and what remains.
