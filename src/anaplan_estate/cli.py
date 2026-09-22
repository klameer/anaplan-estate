"""anaplan-estate: one command over a folder of Anaplan model exports.

  anaplan-estate ROOT [--out estate.md] [--json estate.json] [--html estate.html] [--csv register.csv]
                      [--alias "Headcount Model=HR"] [--name "2 HR Model Documentation=HR"] [--skip Exec]
                      [--stale-months 12] [--theme kit.css] [--logo mark.svg] [--brand "..."] [--title "..."]
                      [--service-url URL] [--contact "text"]

ROOT holds one folder per model; each folder holds the model's
'Line Items*.csv' and, optionally, 'Actions*.csv' and 'Modules*.csv'
anywhere beneath it. ROOT itself may be a single model.

Output: automated findings and candidate recommendations in three levels
(summary, findings by decision area, full reference). --service-url and
--contact are the only way a link or contact appears in the report; with
neither, the invitation is plain text.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import fleet, report, report_html


def _kv(items):
    out = {}
    for s in items or []:
        k, _, v = s.partition("=")
        if k and v:
            out[k.strip()] = v.strip()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="anaplan-estate", description="Automated findings and candidate recommendations from Line Items, Modules and Actions exports.")
    ap.add_argument("root")
    ap.add_argument("--out", help="write the Markdown report here (default: stdout)")
    ap.add_argument("--json", help="write the full report data (JSON) here")
    ap.add_argument("--html", help="write a self-contained HTML report here")
    ap.add_argument("--csv", help="write the findings register (CSV) here")
    ap.add_argument("--theme", help="CSS file whose tokens and embedded fonts are used (HTML only)")
    ap.add_argument("--logo", help="SVG file placed in the header (HTML only)")
    ap.add_argument("--brand", help="kicker line in the header, e.g. 'CODELESSOPS · ESTATE REPORT' (HTML only)")
    ap.add_argument("--title", help="page title (HTML only)")
    ap.add_argument("--service-url", help="URL for the estate analysis service invitation; omitted = no link")
    ap.add_argument("--contact", help="contact text or markdown link shown with the invitation; omitted = none")
    ap.add_argument("--alias", action="append", metavar="PHRASE=MODEL", help="map an import-name phrase to a model name")
    ap.add_argument("--name", action="append", metavar="FOLDER=MODEL", help="rename a discovered model")
    ap.add_argument("--skip", action="append", metavar="MODEL", help="leave a discovered model out (e.g. a copy)")
    ap.add_argument("--stale-months", type=int, default=12, help="window before the Actions snapshot after which an action counts as having no recent recorded run")
    ap.add_argument("--list", action="store_true", help="only list the models that would be analysed")
    args = ap.parse_args(argv)
    if args.list:
        for s in fleet.discover(args.root):
            print(f"{s['name']:30s} {s['line_items']}  actions={'yes' if s['actions'] else 'no'} modules={'yes' if s['modules'] else 'no'}")
        return
    er = fleet.run(args.root, aliases=_kv(args.alias), stale_months=args.stale_months, names=_kv(args.name), skip=args.skip)
    rep = report.build(er, service_url=args.service_url, contact=args.contact)
    if args.title:
        rep["title"] = args.title
    csv_text = report.register_csv(rep)
    if args.json:
        Path(args.json).write_text(json.dumps(rep, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"wrote {args.json}", file=sys.stderr)
    if args.csv:
        Path(args.csv).write_text(csv_text, encoding="utf-8")
        print(f"wrote {args.csv}", file=sys.stderr)
    if args.html:
        css = Path(args.theme).read_text(encoding="utf-8") if args.theme else None
        logo = Path(args.logo).read_text(encoding="utf-8") if args.logo else None
        Path(args.html).write_text(report_html.render(rep, theme_css=css, logo_svg=logo, brand=args.brand, csv_text=csv_text), encoding="utf-8")
        print(f"wrote {args.html}", file=sys.stderr)
    md = report.render_markdown(er)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8"); print(f"wrote {args.out}", file=sys.stderr)
    elif not (args.json or args.html or args.csv):
        try:
            print(md)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(md.encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
