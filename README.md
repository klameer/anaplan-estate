# anaplan-estate

Find what to improve in Anaplan. See what a change could affect.

Automated findings and candidate recommendations for a whole estate of
Anaplan models, from the grid exports, run on your own machine. Nothing
leaves it. The report opens on a one-page **action plan** (at most three
suggested actions, each with steps and a completion check), with a
**Change impact** explorer (what depends on a line item or module, what it
depends on, offline) and the complete **Evidence** (every finding, object,
formula and coverage gap) behind it. It is meant to be useful without
contacting anyone.

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

## Use it online, or run it yourself

Two ways to get the report, same engine, same output:

- **Online**: open the upload page (a Railway service behind a CodelessOps
  subdomain; the exact address is set when it is deployed), upload a zip of
  your estate folder or add models one by one, and the report comes back as
  one HTML file. Files are written to a temporary folder for the seconds the
  analysis takes and deleted before the response is sent; nothing is stored
  and no names or formulas are logged. There is no account.
- **Locally**, if you would rather nothing leaves your machine:

```bash
pip install "https://github.com/klameer/anaplan-grammar/archive/refs/heads/main.zip"
pip install "https://github.com/klameer/anaplan-estate/archive/refs/heads/main.zip"
anaplan-estate my-estate-folder --html estate.html
```

The same upload page can be run locally too: `pip install ".[web]"` then
`anaplan-estate-web` (or `uvicorn anaplan_estate.web:app`), open
http://localhost:8000. `Dockerfile` and `railway.toml` describe the hosted
service; limits and links come from `ESTATE_MAX_MB`, `ESTATE_MAX_MODELS`,
`ESTATE_TIMEOUT_S`, `ESTATE_WORKERS`, `ESTATE_RATE_PER_HOUR`, `ESTATE_FEEDBACK_URL`,
`ESTATE_SOURCE_URL`, `ESTATE_HELP_URL`.

Usage of the hosted service is counted without personal data: per report,
the outcome, model and line-item counts, an upload-size bucket and the
duration; visitors per day via a random daily key that is never stored.
Set `ESTATE_STATS_TOKEN` to enable `GET /stats?token=...` and
`ESTATE_STATS_DIR` (a mounted volume) to keep one summary line per day.

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

The loader sniffs the delimiter (comma, semicolon, tab), reads UTF-8 or
cp1252, and accepts comma-decimal and dot-thousands numbers. English column
headers are required; `Formula` is the only mandatory column, and every other
absent column is listed on the report with what it disables (Cell Count
absent means footprints are unavailable, never zero). Above 25,000 line items
the page leaves out the per-finding search index to stay usable.

## Run

```bash
pip install anaplan-estate
anaplan-estate estate/ --out estate.md --json estate.json
```

`estate.md` is the report. `estate.json` is the same facts for anything
that wants to read them, including an architect's review.

Options: `--alias "Headcount Model=HR"` when an import action names a
model differently from its folder; `--name "2 HR Model Documentation=HR"`
to rename; `--skip Exec` to leave a copy out; `--stale-months 12`;
`--title "Your estate"`; `--html estate.html --csv register.csv`;
`--feedback-url`, `--source-url`, `--help-url` for the footer links
(omitted when absent or not http(s)); `--list` to see what would be
analysed. `scripts/regen_reports.py` regenerates the example outputs.

## What you get

- **Action plan** (the default view): the estate name, one scope and
  freshness line, and one to three suggested actions. Each: do this, why
  (evidence and supportable value; footprint is called footprint, never
  savings), two or three steps naming the actual objects, done when, a
  suggested role, links to the evidence and to Change impact, and any
  decision-changing uncertainty or coverage blocker on the card. Fewer
  than three appear when fewer are supported; none, with the next data
  check, when nothing qualifies. The ordering is deterministic and
  explained under Evidence ("How the actions were chosen"); it is a
  hypothesis, not a verdict. "Print action plan" gives one A4 page.
- **Change impact**: search or select a model, module or line item.
  "What depends on this" follows readers downstream; "what this depends
  on" follows sources upstream. Shortest-link distances, unique counts,
  modules, a grouped view by distance with expandable modules, a table
  with one shortest path per object, module-level import/export actions
  (or "not assessed" when there is no Actions export), inferred model
  feeds shown as a boundary, an observed-footprint cell total (not a
  saving), and a change-review download with the full analysed reach.
- **Evidence**: the complete findings catalogue as a searchable table
  (open one for the working detail: what was found, proposed step,
  preconditions, dependencies, validation plan, reasons to keep the
  design, all affected objects, evidence with complete formulas), how
  the actions were chosen, coverage and limitations, models and
  inventory, model map, dependency evidence with Referenced By
  discrepancies by cause, methodology, glossary, register downloads.
- **Your review state**: a status and a note per finding, kept in your
  browser only, keyed by a stable id that survives regeneration, and
  downloadable as a working register (CSV). Nothing is sent anywhere.
- **Offline, self-contained**: no external requests, no analytics, no
  login. Links appear only when configured on the command line
  (`--feedback-url`, `--source-url`, optional `--help-url`).

See [VALIDATION.md](VALIDATION.md) for what has been checked and what has
not: the rules and ranking were developed on one real estate and one
fictional one, and remain a hypothesis until tested on unseen estates.

## Something missing or not quite right?

Help improve this review for everyone. Open a
[Discussion](https://github.com/klameer/anaplan-estate/discussions) with
what was missed or wrong, what you expected and why it matters; no code
or estate upload is needed. An Issue is right where the parser broke. The
reporting engine is free and open source, maintained by CodelessOps and
open to contributions; accepted improvements stay in the project. Private
examples are only reused in tests or documentation with explicit
permission. Optional paid help is separate from the report and never
required to use it.

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
