"""Redundant calculation inside one model.

Four classes, each with a concrete action:

  exact      same resolved formula, same dimensions, time scale and versions,
             under two or more names. Keep one, repoint the readers.
  alias      B = A, same dimensions. Readers of B can read A.
  near       same formula skeleton, one leaf differs (a constant, a reference,
             a list item). Name the difference; ask whether it is intended.
  superseded a module with no readers outside itself and no export, most of
             whose line items have an exact or near twin in a module that IS
             read. The "replaced by" link.

Resolution: every line-item reference is rewritten to its target, so `A` in
the same module and `'Mod'.A` from elsewhere compare equal; commutative
operators are sorted so `X * Y` equals `Y * X`.

Honesty: same formula and dimensions can still be deliberate (different
summary method, different access driver, one feeds a page and one feeds a
calc). Every pair is reported with its summary methods so the reader can
see the difference at a glance; nothing here says "delete".
"""
from __future__ import annotations
from collections import defaultdict, Counter
from dataclasses import dataclass, field
import re
from anaplan_grammar.parser import parse
from anaplan_grammar.unparse import unparse
from .model import Model, LineItem
from .graph import Graph

COMMUTATIVE = {"+", "*", "=", "<>", "AND", "OR"}
_OUTPUT_MODULE = re.compile(r"^(OUT|REP|DASH|RPT|O |R )|report|output|dashboard|pack", re.I)


def canonical(li: LineItem, g: Graph, key) -> dict | None:
    """AST with references resolved to (module, name) and commutative operands sorted."""
    try:
        ast = parse(li.formula)
    except Exception:
        return None
    refs = {tuple(r.path): r for r in g.refs.get(key, [])}

    def walk(n):
        if not isinstance(n, dict):
            return n
        if n.get("t") == "ref":
            r = refs.get(tuple(n["path"]))
            if r and r.kind == "line_item":
                return {"t": "ref", "path": [r.target[0], r.target[1]]}
            return n
        out = {k: ([walk(x) for x in v] if isinstance(v, list) else walk(v)) for k, v in n.items()}
        if out.get("t") == "bin" and out.get("op") in COMMUTATIVE:
            l, r = unparse(out["l"]), unparse(out["r"])
            if l > r:
                out["l"], out["r"] = out["r"], out["l"]
        return out
    return walk(ast)


def skeleton(ast) -> tuple[str, list[str]]:
    """Formula with every leaf (reference, number, string) replaced by '?', plus the leaves in order."""
    leaves: list[str] = []

    def walk(n):
        if not isinstance(n, dict):
            return n
        t = n.get("t")
        if t == "ref":
            leaves.append(".".join(n["path"])); return {"t": "ref", "path": ["?"]}
        if t in ("num", "str"):
            leaves.append(str(n.get("v"))); return {"t": t, "v": "?"}
        return {k: ([walk(x) for x in v] if isinstance(v, list) else walk(v)) for k, v in n.items()}
    return unparse(walk(ast)), leaves


def _dims(li: LineItem):
    return (tuple(sorted(li.applies_to)), li.time_scale, li.versions)


@dataclass
class Redundancy:
    exact: list[dict] = field(default_factory=list)       # {formula, dims, items:[{key, cells, summary}], redundant_cells}
    aliases: list[dict] = field(default_factory=list)     # {item, target, cells, readers, summary, target_summary}
    near: list[dict] = field(default_factory=list)        # {a, b, differs: (left, right), skeleton, cells}
    superseded: list[dict] = field(default_factory=list)  # {module, by, matched, of, cells, effort}
    output_like: list[str] = field(default_factory=list)  # unreferenced calculated items that look like page outputs
    unknown: list[dict] = field(default_factory=list)     # unreferenced calculated items with no classification: {module, items, cells}

    def counts(self):
        return {"exact_groups": len(self.exact), "exact_redundant": sum(len(e["items"]) - 1 for e in self.exact),
                "exact_cells": sum(e["redundant_cells"] for e in self.exact),
                "aliases": len(self.aliases), "alias_cells": sum(a["cells"] for a in self.aliases),
                "near": len(self.near), "superseded": len(self.superseded),
                "output_like": len(self.output_like), "unknown_items": sum(len(u["items"]) for u in self.unknown),
                "unknown_cells": sum(u["cells"] for u in self.unknown)}

    def to_dict(self):
        return {"counts": self.counts(), "exact": self.exact[:60], "aliases": self.aliases[:60], "near": self.near[:60],
                "superseded": self.superseded, "output_like_count": len(self.output_like), "unknown": self.unknown[:40]}


def analyse(m: Model, g: Graph, export_sources: set[str] = frozenset(), import_targets: set[str] = frozenset()) -> Redundancy:
    r = Redundancy()
    canon: dict = {}
    for key, li in m.line_items.items():
        if li.is_header or not li.formula or key in g.parse_errors:
            continue
        c = canonical(li, g, key)
        if c is not None:
            canon[key] = c

    # exact
    groups = defaultdict(list)
    for key, c in canon.items():
        groups[(unparse(c), _dims(m.line_items[key]))].append(key)
    for (formula, dims), keys in groups.items():
        if len(keys) < 2:
            continue
        keys.sort(key=lambda k: (-len(g.rev.get(k, ())), k))   # keeper = most read
        items = [{"key": f"{k[0]}.{k[1]}", "cells": m.line_items[k].cell_count, "summary": m.line_items[k].summary or "-", "readers": len(g.rev.get(k, ()))} for k in keys]
        r.exact.append({"formula": formula, "dims": ", ".join(dims[0]) or "-", "items": items,
                        "redundant_cells": sum(i["cells"] for i in items[1:]), "readers_to_repoint": sum(i["readers"] for i in items[1:])})
    r.exact.sort(key=lambda e: -e["redundant_cells"])

    # aliases
    for key, c in canon.items():
        if c.get("t") != "ref" or len(g.edges.get(key, ())) != 1:
            continue
        tgt = next(iter(g.edges[key]))
        li, tl = m.line_items[key], m.line_items[tgt]
        if _dims(li) != _dims(tl):
            continue
        r.aliases.append({"item": f"{key[0]}.{key[1]}", "target": f"{tgt[0]}.{tgt[1]}", "cells": li.cell_count,
                          "readers": len(g.rev.get(key, ())), "summary": li.summary or "-", "target_summary": tl.summary or "-"})
    r.aliases.sort(key=lambda a: -a["cells"])

    # near: same skeleton, exactly one leaf differs, same dims; skip pairs already exact

    by_skel = defaultdict(list)
    for key, c in canon.items():
        sk, leaves = skeleton(c)
        if len(leaves) >= 2:
            by_skel[(sk, _dims(m.line_items[key]))].append((key, leaves))
    seen_pairs = set()
    for (sk, dims), members in by_skel.items():
        if len(members) < 2 or len(members) > 200:
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                (ka, la), (kb, lb) = members[i], members[j]
                if ka[0] == kb[0] and len(la) <= 3:
                    continue      # short same-module variants (Rent, Rates, ...) are the normal copy-down, not redundancy
                diff = [(x, y) for x, y in zip(la, lb) if x != y]
                if len(diff) == 1 and (ka, kb) not in seen_pairs:
                    seen_pairs.add((ka, kb))
                    r.near.append({"a": f"{ka[0]}.{ka[1]}", "b": f"{kb[0]}.{kb[1]}", "differs": diff[0], "skeleton": sk[:120],
                                   "cells": m.line_items[kb].cell_count, "same_module": ka[0] == kb[0]})
    r.near.sort(key=lambda n: (n["same_module"], -n["cells"]))

    # orphan modules: nothing outside reads any line item, no export reads it, has calculations.
    # superseded = orphan with a twin module (by near/exact formulas or by line-item names) that IS read.
    twin_of: dict = {}
    for e in r.exact:
        for it in e["items"]:
            twin_of.setdefault(it["key"], set()).update(x["key"].split(".")[0] for x in e["items"] if x["key"] != it["key"])
    for n in r.near:
        if not n["same_module"]:
            twin_of.setdefault(n["a"], set()).add(n["b"].split(".")[0])
            twin_of.setdefault(n["b"], set()).add(n["a"].split(".")[0])
    read_modules = {a[0] for k, users in g.rev.items() for a in users if a[0] != k[0]} | {k[0] for k, users in g.rev.items() if any(a[0] != k[0] for a in users)}
    for mod_name, mod in m.modules.items():
        keys = [(mod_name, n) for n in mod.line_items if (mod_name, n) in m.line_items]
        calc = [k for k in keys if m.line_items[k].formula]
        if len(calc) < 2 or mod_name in export_sources or _OUTPUT_MODULE.search(mod_name):
            continue
        if any(a[0] != mod_name for k in keys for a in g.rev.get(k, ())):
            continue
        cells = sum(m.line_items[k].cell_count for k in keys)
        effort = round(sum(m.line_items[k].calc_effort for k in keys), 2)
        twins = Counter(t for k in calc for t in twin_of.get(f"{k[0]}.{k[1]}", ()) if t != mod_name)
        names = {k[1] for k in keys}
        reads = {b[0] for k in keys for b in g.edges.get(k, ())}     # modules this one reads: a downstream summary is not a copy of its source
        for other, om in m.modules.items():
            if other == mod_name or other not in read_modules or other in reads:
                continue
            overlap = len(names & set(om.line_items))
            if overlap and overlap / max(len(names), 1) >= 0.6:
                twins[other] += overlap
        twins = Counter({t: n for t, n in twins.items() if t not in reads})
        by, matched = (twins.most_common(1)[0] if twins else (None, 0))
        if cells < 50_000 and effort < 1 and not by:
            continue                                                  # a small orphan module is a note, not an action
        r.superseded.append({"module": mod_name, "by": by, "matched": matched, "of": len(calc), "cells": cells, "effort": effort,
                             "imported_into": mod_name in import_targets, "notes": mod.notes, "line_items": len(keys)})
    r.superseded.sort(key=lambda s: -s["cells"])

    # unreferenced calculated items: output-like vs unknown
    sup = {s["module"] for s in r.superseded}
    unknown_by_mod = defaultdict(list)
    for key, li in m.line_items.items():
        if li.is_header or not li.formula or g.rev.get(key) or key[0] in sup:
            continue
        looks_output = bool(_OUTPUT_MODULE.search(key[0])) or key[0] in export_sources or li.format_type in ("TEXT",) or li.time_scale in ("Year", "Quarter") \
            or (li.format_type == "NUMBER" and li.summary.startswith("FORMULA"))
        if looks_output:
            r.output_like.append(f"{key[0]}.{key[1]}")
        else:
            unknown_by_mod[key[0]].append(key)
    for mod_name, keys in unknown_by_mod.items():
        r.unknown.append({"module": mod_name, "items": [k[1] for k in keys], "cells": sum(m.line_items[k].cell_count for k in keys),
                          "effort": round(sum(m.line_items[k].calc_effort for k in keys), 2)})
    r.unknown.sort(key=lambda u: -u["cells"])
    return r
