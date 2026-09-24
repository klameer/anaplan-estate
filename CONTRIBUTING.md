# Contributing

Thank you for looking. This is a small project maintained by one person at
CodelessOps; contributions of every size are welcome.

## The most useful contribution

An anonymised Line Items export (and, if you have it, the Actions export)
from a real model that the tool gets wrong or says nothing useful about.
Rename modules and line items if you must, keep the formulas' shape. Open a
Discussion describing what was missed or wrong, what you expected and why it
matters; you do not need to attach anything to be heard.

## Running it

```bash
pip install "https://github.com/klameer/anaplan-grammar/archive/refs/heads/main.zip"
pip install -e ".[web,dev]"
python -m pytest -q tests
anaplan-estate examples/caldergate-estate --html estate.html
```

The example estate is fictional and every planted fault is listed in
`examples/caldergate-estate/PLANTED.md`; a change that stops the report
finding one of them needs a reason.

## Ground rules

- Findings state what the exports show; recommendations are labelled as
  candidates with their evidence strength and what is missing. Never add a
  claim of savings, "unused" or a percentage improvement the exports cannot
  support.
- New rules cite official Anaplan documentation (see `lint.DOCS`) and come
  with a fixture in `tests/test_rules.py`.
- Private model exports are never committed, quoted in issues, or turned into
  fixtures without the owner's written permission.
- Keep the report self-contained: no external requests, no analytics in the
  HTML.

## Issues and pull requests

Use the issue template. Small pull requests with a test are easiest to
review. The CI runs the tests on Python 3.10 to 3.13 and builds the example
report.
