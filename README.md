# anaplan-estate

An action report for a whole estate of Anaplan models, from two exports per
model, run on your own machine. Nothing leaves it. It opens with what to do,
ranked; the evidence sits behind each action.

For each model it reports where the calculation time goes, what depends on
what, what is unreferenced, circular or daisy-chained, which imports are
stale or outside any process, and which rule findings collapse into the
same design decision. Across models it infers which model feeds which
from the import actions, finds logic duplicated between models, and
lists the dimensions they share.

Deterministic. No opinion. Every formula is parsed with
[anaplan-grammar](https://github.com/klameer/anaplan-grammar) and the
dependency graph is checked against Anaplan's own Referenced By column,
so the report tells you how much to trust it.

## Try it first on the example estate

Four fictional models built to look inherited: two consultancies, three
build years, a leftover module carrying half the calculation time, a
formula nobody dares touch, an import from a hub that no longer exists.

```bash
git clone https://github.com/klameer/anaplan-estate
cd anaplan-estate
pip install -e .
anaplan-estate examples/caldergate-estate --out estate.md --html estate.html
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

- **What to do**: the front page. Every action ranked by what it reclaims
  (cells, calculation effort, dead actions) over what it touches (formulas
  to repoint, exports, downstream models, pages). Each says what the
  exports prove and what they cannot: pages and saved views are not in
  any export, so an action that removes something is marked "check
  pages". Click through for the why, the steps, how to verify, and the
  evidence table.
- **Redundant calculation**: line items that repeat a calculation already
  made in the same model (same resolved formula and dimensions), plain
  copies of another line item, near-twins that differ in one place, and
  whole modules nothing reads.
- **The estate at a glance**: one row per model, with parse rate.
- **How the models connect**: an inferred feed graph (Mermaid) and the
  external sources named in imports.
- **Logic duplicated across models**: same line item, same formula tree.
- Per model: where the calculation time goes (Anaplan's Calculation
  Effort column, top line items and modules), largest modules by cells,
  most depended-on line items, actions (orphans, stale, slowest), and
  findings grouped into patterns.
- **Procedures performed**: the rules run, so the report reads as
  agreed-upon procedures, not an opinion.

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
