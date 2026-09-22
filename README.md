# anaplan-estate

Automated findings and candidate recommendations for a whole estate of
Anaplan models, from the grid exports, run on your own machine. Nothing
leaves it. Three levels: a summary with priority investigations, findings
grouped by decision area, and the full reference with every formula.

For each model it reports where the calculation time goes, what depends on
what, what is unreferenced, circular or daisy-chained, which imports are
stale or outside any process, and which rule findings collapse into the
same design decision. Across models it infers which model feeds which
from the import actions, finds logic duplicated between models, and
lists the dimensions they share.

Every formula is parsed with
[anaplan-grammar](https://github.com/klameer/anaplan-grammar) and the
dependency graph is checked against Anaplan's own Referenced By column, so
the report says how far to trust it. Observations, hypotheses and
recommendations are labelled apart; every finding carries its evidence
strength, what the exports cannot tell, and when keeping the current
design is reasonable.

## Try it first on the example estate

Four fictional models built to look inherited: two consultancies, three
build years, a leftover module carrying half the calculation time, a
formula nobody dares touch, an import from a hub that no longer exists.

```bash
git clone https://github.com/klameer/anaplan-estate
cd anaplan-estate
pip install -e .
anaplan-estate examples/caldergate-estate --out estate.md --html estate.html --csv register.csv
```

Open `estate.html`. Then read
[examples/caldergate-estate/PLANTED.md](examples/caldergate-estate/PLANTED.md):
everything that was planted and where the report finds it. Then export
your own models and run it on those.

## Export the two files

In each model, as a workspace administrator:

1. **Line items**: Model Settings > Modules > Line Items tab > Export.
   The grid export with every column (Formula, Applies To, Cell Count,
   Calculation Effort, Referenced By, Notes, Module Name).
2. **Actions**: Model Settings > Actions > Export. All sections.

Put them in one folder per model:

```
estate/
  FP&A/       Line Items.csv   Actions.csv
  HR/         Line Items.csv   Actions.csv
  Pipeline/   Line Items.csv   Actions.csv
```

Subfolders are fine (`FP&A/line items/Line Items.csv`). A `Modules.csv`
export alongside adds subsidiary-view and module-notes checks.

## Run

```bash
pip install anaplan-estate
anaplan-estate estate/ --out estate.md --json estate.json
```

`estate.md` is the report. `estate.json` is the same facts for anything
that wants to read them, including an architect's review.

Options: `--alias "Headcount Model=HR"` when an import action names a
model differently from its folder; `--name "2 HR Model Documentation=HR"`
to rename; `--stale-months 12`; `--list` to see what would be analysed.

## What you get

- **Summary**: scope and freshness, three or four observations computed
  from the inputs, up to three priority investigations (observed, why it
  matters, what to do next), the model map with feeds marked inferred,
  and the coverage limitations that matter most.
- **Findings by decision area**: capacity and performance, usage and
  retirement, dependencies and change impact, maintainability and
  consistency, integration and operations. Each finding: observed fact,
  why it matters, affected scope, potential benefit (footprint,
  conditional, or none), evidence strength and basis, missing
  information, one next step, when keeping the design is reasonable,
  expandable evidence with complete formulas, validation guidance.
- **Reference**: findings register (downloadable CSV), per-model
  statistics and coverage (files supplied, snapshot date, rules run and
  skipped with reasons, confirmed vs inferred relationships, what is
  missing), dependency evidence with Referenced By discrepancies by
  cause, source-name candidates, shared dimensions, methodology with
  documentation references, glossary.
- **In the HTML**: search, filters (model, category, evidence, review
  status), sorting, expand/collapse, review statuses kept in your
  browser and exportable, a light print stylesheet with a summary-only
  option. No external requests; all links are within the file.

## What should it show next?

Once line items and actions are in one place, most questions about an
estate become a query over them. The report answers the ones above. Open
a [Discussion](https://github.com/klameer/anaplan-estate/discussions) with
the one it does not answer for your estate, or an Issue where the parser
broke. The most useful contribution is an anonymised line-items export
from an old model.

## What it does not do

Say whether a finding matters for your model. A formula that breaks a
rule may be doing its job. That judgement is a review, and this report is
its evidence.

## Development

```bash
pip install -e .
python -m pytest -q tests
```

MIT.
