"""Repeated calculation inside one model.

Classes, each with a different strength of evidence:

  exact      same resolved formula AND the same effective context: dimensions
             (the line item's own Applies To, or its module's when inherited),
             time scale, time range, versions, data type, summary method,
             formula scope. Under two or more names. Evidence: strong.
  alias      B = A, same context. Readers of B could read A. Evidence: strong.
  near       same formula skeleton, one leaf differs (a constant, a reference,
             a list item), same context. May be intentional. Evidence: weak.
  same_text  identical formula text but a context the exports cannot resolve
             (COLLECT(), whose value depends on the line item subset and its
             source membership; or missing metadata). Not declared equivalent.
  overlap    a module with no formula consumer detected outside itself and no
             export action reading it, some of whose calculated line items
             have an exact twin in a module that IS read. Reported with unique
             source items matched, unique target items, unmatched items, and
             coverage that cannot exceed 100 percent. Never "superseded" from
             partial similarity, matching names, or reader counts.

Resolution: every line-item reference is rewritten to its target so `A` in
the same module and `'Mod'.A` from elsewhere compare equal; commutative
operators are sorted so `X * Y` equals `Y * X`.

Missing metadata stays missing: two blank values are not evidence of
equivalence, so an item with any blank context field cannot be "exact".

Equality does not make consolidation desirable. Legitimate reasons for two
objects with the same formula: access boundaries, a reporting contract, a
different summary the page needs, deliberately separate processes. The
report says so next to every group.
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
CONTEXT_FIELDS = ("dims", "time_scale", "time_range", "versions", "format", "summary", "formula_scope")


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


def effective_dims(m: Model, li: LineItem) -> tuple[str, ...] | None:
    """The line item's own Applies To when the export gives one; else the module's (inherited);
    None when neither is known (no Modules export and the line item row is blank)."""
    if li.applies_to:
        return tuple(sorted(li.applies_to))
    mod = m.modules.get(li.module)
    if mod and mod.applies_to:
        return tuple(sorted(mod.applies_to))
    if m.has_modules_export:
        return ()          # module row present and blank: no dimensions
    return None


def context(m: Model, li: LineItem) -> dict:
    """Every field that has to agree before two formulas can be called the same calculation.
    A missing value is None, and None never equals None here."""
    return {"dims": effective_dims(m, li), "time_scale": li.time_scale or None, "time_range": li.time_range or None,
            "versions": li.versions or None, "format": li.format_type or None, "summary": li.summary or None,
            "formula_scope": li.formula_scope or None}


def context_key(ctx: dict):
    if any(v is None for v in ctx.values()):
        return None
    return tuple(ctx[f] for f in CONTEXT_FIELDS)


def _uses_collect(formula: str) -> bool:
    return "COLLECT" in formula.upper()


@dataclass
class Redundancy:
    exact: list[dict] = field(default_factory=list)
    aliases: list[dict] = field(default_factory=list)
    near: list[dict] = field(default_factory=list)
    same_text: list[dict] = field(default_factory=list)      # identical text, context unresolved (COLLECT or missing metadata)
    overlap: list[dict] = field(default_factory=list)        # orphan modules with exact twins elsewhere, with coverage
    orphan_modules: list[dict] = field(default_factory=list) # no formula consumer outside, no export action; may have page/view/LISS consumers
    output_like: list[str] = field(default_factory=list)
    unknown: list[dict] = field(default_factory=list)
    unresolved_context: int = 0                              # calculated line items whose context had a blank field

    def counts(self):
        return {"exact_groups": len(self.exact), "exact_redundant": sum(len(e["items"]) - 1 for e in self.exact),
                "exact_cells": sum(e["redundant_cells"] for e in self.exact),
                "aliases": len(self.aliases), "alias_cells": sum(a["cells"] for a in self.aliases),
                "near": len(self.near), "same_text_groups": len(self.same_text), "overlap": len(self.overlap),
                "orphan_modules": len(self.orphan_modules), "unresolved_context": self.unresolved_context,
                "output_like": len(self.output_like), "unknown_items": sum(len(u["items"]) for u in self.unknown),
                "unknown_cells": sum(u["cells"] for u in self.unknown)}

    def to_dict(self):
        return {"counts": self.counts(), "exact": self.exact, "aliases": self.aliases, "near": self.near, "same_text": self.same_text,
                "overlap": self.overlap, "orphan_modules": self.orphan_modules, "output_like_count": len(self.output_like), "unknown": self.unknown}


def analyse(m: Model, g: Graph, export_sources: set[str] = frozenset(), import_targets: set[str] = frozenset()) -> Redundancy:
    r = Redundancy()
    canon: dict = {}
    ctxs: dict = {}
    for key, li in m.line_items.items():
        if li.is_header or not li.formula or key in g.parse_errors:
            continue
        c = canonical(li, g, key)
        if c is None:
            continue
        canon[key] = c
        ctxs[key] = context(m, li)

    def item(k):
        li = m.line_items[k]; ctx = ctxs[k]
        return {"key": f"{k[0]}.{k[1]}", "module": k[0], "name": k[1], "cells": li.cell_count, "readers": len(g.rev.get(k, ())),
                "summary": ctx["summary"] or "unknown", "format": ctx["format"] or "unknown",
                "dims": ", ".join(ctx["dims"]) if ctx["dims"] else ("none" if ctx["dims"] == () else "unknown"),
                "time_scale": ctx["time_scale"] or "unknown", "time_range": ctx["time_range"] or "unknown",
                "versions": ctx["versions"] or "unknown", "formula_scope": ctx["formula_scope"] or "unknown", "formula": li.formula}

    # exact: same canonical formula AND same complete context; COLLECT and blank-context items go to same_text
    groups = defaultdict(list); text_groups = defaultdict(list)
    for key, c in canon.items():
        ck = context_key(ctxs[key])
        if ck is None:
            r.unresolved_context += 1
        if _uses_collect(m.line_items[key].formula) or ck is None:
            text_groups[(unparse(c), "collect" if _uses_collect(m.line_items[key].formula) else "context")].append(key)
            continue
        groups[(unparse(c), ck)].append(key)
    for (formula, ck), keys in groups.items():
        if len(keys) < 2:
            continue
        keys.sort(key=lambda k: (-len(g.rev.get(k, ())), k))
        items = [item(k) for k in keys]
        r.exact.append({"formula": formula, "dims": items[0]["dims"], "context": dict(zip(CONTEXT_FIELDS, ck)), "items": items,
                        "redundant_cells": sum(i["cells"] for i in items[1:]), "readers_to_repoint": sum(i["readers"] for i in items[1:]),
                        "same_summary": len({i["summary"] for i in items}) == 1})
    r.exact.sort(key=lambda e: -e["redundant_cells"])
    for (formula, why), keys in text_groups.items():
        if len(keys) < 2:
            continue
        r.same_text.append({"formula": formula, "why": "COLLECT(): value depends on the line item subset and its sources, which the exports do not describe" if why == "collect"
                            else "a context field (dimensions, time range, versions, format, summary or scope) is blank in the export",
                            "items": [item(k) for k in keys]})
    r.same_text.sort(key=lambda e: -len(e["items"]))

    # aliases: B = A with identical context
    for key, c in canon.items():
        if c.get("t") != "ref" or len(g.edges.get(key, ())) != 1:
            continue
        tgt = next(iter(g.edges[key]))
        if tgt not in ctxs:
            continue
        ka, kb = context_key(ctxs[key]), context_key(ctxs[tgt])
        if ka is None or kb is None or ka != kb:
            continue
        li = m.line_items[key]
        r.aliases.append({"item": f"{key[0]}.{key[1]}", "target": f"{tgt[0]}.{tgt[1]}", "cells": li.cell_count,
                          "readers": len(g.rev.get(key, ())), "summary": li.summary or "-", "target_summary": m.line_items[tgt].summary or "-",
                          "exported": key[0] in export_sources})
    r.aliases.sort(key=lambda a: -a["cells"])

    # near: same skeleton, same complete context, exactly one leaf differs
    by_skel = defaultdict(list)
    for key, c in canon.items():
        ck = context_key(ctxs[key])
        if ck is None or _uses_collect(m.line_items[key].formula):
            continue
        sk, leaves = skeleton(c)
        if len(leaves) >= 4:                      # trivial shapes (A * k, A + B) pair with everything; not evidence of copy-and-tweak
            by_skel[(sk, ck)].append((key, leaves))
    seen = set()
    for (sk, ck), members in by_skel.items():
        if len(members) < 2 or len(members) > 60:  # a shape shared by more than 60 line items is a template, reported by the pattern clusters
            continue
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                (ka, la), (kb, lb) = members[i], members[j]
                if ka[0] == kb[0] and len(la) <= 3:
                    continue
                diff = [(x, y) for x, y in zip(la, lb) if x != y]
                if len(diff) == 1 and (ka, kb) not in seen:
                    seen.add((ka, kb))
                    r.near.append({"a": f"{ka[0]}.{ka[1]}", "b": f"{kb[0]}.{kb[1]}", "differs": diff[0], "skeleton": sk,
                                   "cells": m.line_items[kb].cell_count, "same_module": ka[0] == kb[0],
                                   "formula_a": m.line_items[ka].formula, "formula_b": m.line_items[kb].formula})
    r.near.sort(key=lambda n: (n["same_module"], -n["cells"]))

    # orphan modules and overlap
    exact_twin: dict = defaultdict(set)
    for e in r.exact:
        ks = [(i["module"], i["name"]) for i in e["items"]]
        for a in ks:
            for b in ks:
                if a[0] != b[0]:
                    exact_twin[a].add(b)
    read_modules = {k[0] for k, users in g.rev.items() if any(a[0] != k[0] for a in users)}
    for mod_name, mod in m.modules.items():
        keys = [(mod_name, n) for n in mod.line_items if (mod_name, n) in m.line_items and not m.line_items[(mod_name, n)].is_header]
        calc = [k for k in keys if m.line_items[k].formula]
        if len(calc) < 2 or mod_name in export_sources:
            continue
        if any(a[0] != mod_name for k in keys for a in g.rev.get(k, ())):
            continue
        cells = sum(m.line_items[k].cell_count for k in keys)
        effort = round(sum(m.line_items[k].calc_effort for k in keys), 2)
        unparsed = sum(1 for k in calc if k in g.parse_errors)
        entry = {"module": mod_name, "line_items": len(keys), "calculated": len(calc), "cells": cells, "effort": effort,
                 "imported_into": mod_name in import_targets, "notes": mod.notes, "output_like": bool(_OUTPUT_MODULE.search(mod_name)),
                 "unparsed": unparsed, "collect": sum(1 for k in calc if _uses_collect(m.line_items[k].formula))}
        by_target = defaultdict(set)
        for k in calc:
            for t in exact_twin.get(k, ()):
                if t[0] in read_modules:
                    by_target[t[0]].add(k)
        if by_target:
            target, matched_src = max(by_target.items(), key=lambda kv: len(kv[1]))
            matched_tgt = {t for k in matched_src for t in exact_twin[k] if t[0] == target}
            unmatched = [k[1] for k in calc if k not in matched_src]
            r.overlap.append({**entry, "target": target, "matched_source": len(matched_src), "matched_target": len(matched_tgt),
                              "pairs": sum(len([t for t in exact_twin[k] if t[0] == target]) for k in matched_src),
                              "coverage": round(len(matched_src) / len(calc), 3), "unmatched": unmatched,
                              "complete": not unmatched and unparsed == 0})
        else:
            r.orphan_modules.append(entry)
    r.overlap.sort(key=lambda s: -s["cells"])
    r.orphan_modules.sort(key=lambda s: -s["cells"])

    # unreferenced calculated items outside those modules: output-like vs unknown
    covered = {s["module"] for s in r.overlap} | {s["module"] for s in r.orphan_modules}
    unknown_by_mod = defaultdict(list)
    for key, li in m.line_items.items():
        if li.is_header or not li.formula or g.rev.get(key) or key[0] in covered:
            continue
        looks_output = bool(_OUTPUT_MODULE.search(key[0])) or key[0] in export_sources or li.format_type == "TEXT" or li.time_scale in ("Year", "Quarter") \
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
