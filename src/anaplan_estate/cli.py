"""anaplan-estate: one command over a folder of Anaplan model exports.

  anaplan-estate ROOT [--out estate.md] [--json estate.json] [--alias "Headcount Model=HR"]
                      [--name "2 HR Model Documentation=HR"] [--stale-months 12]

ROOT holds one folder per model; each folder holds the model's
'Line Items*.csv' and, optionally, 'Actions*.csv' and 'Modules*.csv'
anywhere beneath it. ROOT itself may be a single model.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from . import fleet


def _kv(items):
    out = {}
    for s in items or []:
        k, _, v = s.partition("=")
        if k and v:
            out[k.strip()] = v.strip()
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="anaplan-estate", description="Deterministic estate report from Line Items and Actions exports.")
    ap.add_argument("root")
    ap.add_argument("--out", help="write the Markdown report here (default: stdout)")
    ap.add_argument("--json", help="write the JSON bundle here")
    ap.add_argument("--alias", action="append", metavar="PHRASE=MODEL", help="map an import-name phrase to a model name")
    ap.add_argument("--name", action="append", metavar="FOLDER=MODEL", help="rename a discovered model")
    ap.add_argument("--skip", action="append", metavar="MODEL", help="leave a discovered model out (e.g. a copy)")
    ap.add_argument("--stale-months", type=int, default=12)
    ap.add_argument("--max-patterns", type=int, default=20)
    ap.add_argument("--list", action="store_true", help="only list the models that would be analysed")
    args = ap.parse_args(argv)
    if args.list:
        for s in fleet.discover(args.root):
            print(f"{s['name']:30s} {s['line_items']}  actions={'yes' if s['actions'] else 'no'} modules={'yes' if s['modules'] else 'no'}")
        return
    er = fleet.run(args.root, aliases=_kv(args.alias), stale_months=args.stale_months, names=_kv(args.name), skip=args.skip)
    md = fleet.render_markdown(er, max_patterns=args.max_patterns)
    if args.json:
        Path(args.json).write_text(json.dumps(er.to_dict(), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {args.json}", file=sys.stderr)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8"); print(f"wrote {args.out}", file=sys.stderr)
    else:
        try:
            print(md)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(md.encode("utf-8", "replace"))


if __name__ == "__main__":
    main()
