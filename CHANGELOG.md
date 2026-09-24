# Changelog

## Unreleased

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
