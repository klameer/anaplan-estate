"""Regenerate the checked-in example outputs and, when the private inputs are present, the private estate report.

    python scripts/regen_reports.py                       # examples/caldergate-estate -> examples/.../estate.* and out/caldergate.html
    ANAPLAN_ESTATE_PRIVATE_ROOT="G:\\...\\Winddown" python scripts/regen_reports.py --private

The private estate is never substituted with fictional data: with --private and no readable root the script stops
and says so. Links are the project's own pages; the theme is the CodelessOps report theme when its path exists.
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from anaplan_estate.cli import main  # noqa: E402

FEEDBACK = "https://github.com/klameer/anaplan-estate/discussions"
SOURCE = "https://github.com/klameer/anaplan-estate"
THEME = Path(r"C:\Projects\20260714_Grounded\config\brand\report-theme-dark.css")
LOGO = Path(r"C:\Projects\20260714_Grounded\config\brand\assets\logo.svg")


def common(theme: bool) -> list[str]:
    args = ["--feedback-url", FEEDBACK, "--source-url", SOURCE]
    if theme and THEME.exists():
        args += ["--theme", str(THEME)]
    return args


def run(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", action="store_true", help="also regenerate the private estate from ANAPLAN_ESTATE_PRIVATE_ROOT")
    ap.add_argument("--no-theme", action="store_true")
    a = ap.parse_args(argv)
    ex = ROOT / "examples" / "caldergate-estate"
    out = ROOT / "out"; out.mkdir(exist_ok=True)
    main([str(ex), "--out", str(ex / "estate.md"), "--json", str(ex / "estate.json"), "--html", str(ex / "estate.html"), "--csv", str(ex / "register.csv"),
          "--title", "Caldergate Distribution Group: Anaplan estate (fictional example)"] + common(not a.no_theme))
    main([str(ex), "--html", str(out / "caldergate.html"), "--title", "Caldergate Distribution Group: Anaplan estate (fictional example)"] + common(not a.no_theme))
    if a.private:
        root = os.environ.get("ANAPLAN_ESTATE_PRIVATE_ROOT", "")
        if not root or not Path(root).is_dir():
            sys.exit("ANAPLAN_ESTATE_PRIVATE_ROOT is not set to a readable folder; the private report was NOT regenerated and no fictional data was substituted.")
        main([root, "--name", "FPA=FP&A", "--skip", "Exec", "--title", "Exscientia Anaplan estate",
              "--out", str(out / "exs_estate.md"), "--json", str(out / "exs_estate.json"), "--html", str(out / "exs_estate.html"), "--csv", str(out / "exs_register.csv")] + common(not a.no_theme))


if __name__ == "__main__":
    run()
