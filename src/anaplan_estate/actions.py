"""Turn facts and findings into an action list.

An action is something a builder can do on Monday: what, to which objects,
what it reclaims (cells, effort, actions), what it touches (formulas to
repoint, exports, downstream models, pages), how to prove it worked, and
what the exports cannot tell. Ranked by payoff over blast radius.

No opinion is expressed. Every action reads "if you want this, here is
how, what it costs, what it touches, how to verify"; whether it matters
for this estate is a review, and this list is its evidence.

Score = payoff points / (1 + touch points), where
  payoff  = 100 x (cells reclaimed / estate cells) + effort share (%) + 3 x log10(1 + objects) + 3 x log10(1 + actions)
  touch   = readers to repoint / 50 + 2 x exports on the module + 3 x downstream models
            + 1 if page exposure is unknown and the action removes something;
  halved when the action needs judgment the exports cannot supply
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter
import re, math
from anaplan_grammar.parser import parse
from anaplan_grammar.unparse import unparse
from .lint import _walk, RULES

CONFIDENCE = {
    "proven": "Everything this action touches is in the exports.",
    "check pages": "Formulas, exports and imports are in the exports; pages and saved views are not. Check them before removing anything.",
    "judgment": "The exports show the shape; whether the change is right needs someone who knows the model.",
}


@dataclass
class Action:
    id: str
    kind: str                 # retire | merge | collapse | fix | refactor | tidy | schedule | dedupe
    title: str                # imperative, one line
    model: str
    objects: list[str]
    payoff: dict              # cells, effort, objects, actions
    touches: dict             # readers, exports, downstream_models, pages
    confidence: str           # proven | check pages | judgment
    why: str
    steps: list[str]
    verify: list[str]
    evidence: list[str]       # markdown lines (tables allowed)
    score: float = 0.0
    rules: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def _c(x) -> str:
    if not isinstance(x, (int, float)):
        return str(x)
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            v = x / div
            return f"{v:.0f}{suf}" if v >= 100 else f"{v:.1f}{suf}"
    return f"{x:,}"


def _score(a: Action, estate_cells: int) -> float:
    p = a.payoff; t = a.touches
    payoff = 100 * p.get("cells", 0) / max(estate_cells, 1) + p.get("effort", 0) + 3 * math.log10(1 + p.get("objects", 0)) + 3 * math.log10(1 + p.get("actions", 0))
    touch = t.get("readers", 0) / 50 + 2 * t.get("exports", 0) + 3 * t.get("downstream_models", 0)
    if t.get("pages") == "unknown" and a.kind in ("retire", "merge", "collapse"):
        touch += 1
    score = payoff / (1 + touch)
    if a.confidence == "judgment":
        score *= 0.5           # the exports show the shape, not the answer
    return round(score, 3)


def _pl(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


# ---------------------------------------------------------------- helpers over one model

def _exports_on(m, module: str) -> list[str]:
    return [a.name for a in m.actions.actions.values() if a.kind == "export" and a.target == module]


def _downstream_models(er, m, module: str) -> list[str]:
    """Models that import from this model, when this module is an export source."""
    if not _exports_on(m, module):
        return []
    return sorted({e["to"] for e in er.edges if e["from"] == m.name})


def _readers_outside(g, keys, module=None) -> int:
    return sum(1 for k in keys for a in g.rev.get(k, ()) if module is None or a[0] != module)


def _divide_fix(formula: str) -> str | None:
    try:
        ast = parse(formula)
    except Exception:
        return None
    def walk(n):
        if not isinstance(n, dict):
            return n
        out = {k: ([walk(x) for x in v] if isinstance(v, list) else walk(v)) for k, v in n.items()}
        if out.get("t") == "bin" and out["op"] == "/" and out["r"].get("t") != "num":
            return {"t": "call", "f": "DIVIDE", "args": [out["l"], out["r"]]}
        return out
    try:
        return unparse(walk(ast))
    except Exception:
        return None


def _if_mapping(formula: str) -> list[tuple[str, str]] | None:
    """IF ITEM(L) = L.'x' THEN <expr> ELSE IF ... : the (item, expr) table the chain encodes."""
    try:
        n = parse(formula)
    except Exception:
        return None
    rows = []
    while isinstance(n, dict) and n.get("t") == "if":
        c = n["c"]
        if not (c.get("t") == "bin" and c["op"] == "=" and c["l"].get("t") == "call" and c["l"]["f"] == "ITEM" and c["r"].get("t") == "ref"):
            return None
        rows.append((".".join(c["r"]["path"]), unparse(n["a"])))
        n = n["b"]
    return rows if len(rows) >= 3 else None


# ---------------------------------------------------------------- generators

def _actions_for_model(er, m, n0: int) -> list[Action]:
    out: list[Action] = []
    g, model, f, red = m.graph, m.model, m.facts, m.redundancy
    findings = m.lint.findings
    by_rule = defaultdict(list)
    for x in findings:
        by_rule[x.rule].append(x)
    export_sources = {a.target for a in m.actions.actions.values() if a.kind == "export"}
    nid = [n0]

    def new(kind, title, objects, payoff, touches, confidence, why, steps, verify, evidence, rules=()):
        nid[0] += 1
        a = Action(f"A{nid[0]}", kind, title, m.name, objects, payoff, touches, confidence, why, steps, verify, evidence, rules=list(rules))
        out.append(a)

    # 1 orphan modules (nothing outside reads them), superseded when a twin exists
    for s in red.superseded:
        mod = s["module"]
        twin = f", superseded by {s['by']}" if s["by"] else ": no formula or export reads it"
        why = (f"No formula outside {mod} reads any of its {s['line_items']} line items, and no export action reads it. "
               + (f"{s['matched']} of its {s['of']} calculated line items have a twin in {s['by']}, which other formulas do read. " if s["by"] else "")
               + f"It holds {_c(s['cells'])} cells" + (f" and {s['effort']}% of the model's calculation effort" if s["effort"] else "") + ", recalculated on every change."
               + (f" Module note: \"{s['notes']}\"" if s["notes"] else ""))
        new("retire", (f"Retire {mod}{twin}" if s["by"] else f"Find out what reads {mod}{twin}"), [mod],
            {"cells": s["cells"], "effort": s["effort"], "objects": s["line_items"]},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "unknown"},
            "check pages", why,
            [f"List the pages and saved views that use {mod} (Modules export: Used in Dashboards covers classic dashboards only; UX pages need the page builder).",
             (f"Where a page reads {mod}, repoint the card to the twin line item in {s['by']}." if s["by"] else f"Where a page reads {mod}, decide whether the page is still used."),
             f"In a sandbox copy, blank every formula in {mod}; open the pages listed in step 1.",
             f"Delete {mod}." + (" It is an import target: retire the import first." if s["imported_into"] else "")],
            [f"Workspace size falls by about {_c(s['cells'])} cells." + (f" Calculation effort falls by about {s['effort']}%." if s["effort"] else ""),
             "Every page listed in step 1 opens without a blank card."],
            [f"Readers outside the module: 0. Exports reading it: 0." + (f" Twin module: {s['by']} ({s['matched']} matches)." if s["by"] else "")])

    # 2 exact duplicates
    if red.exact:
        c = red.counts()
        rows = ["| Keep (most read) | Also computed as | Dimensions | Redundant cells | Summary methods |", "|---|---|---|---|---|"]
        for e in red.exact[:25]:
            keep, rest = e["items"][0], e["items"][1:]
            rows.append(f"| {keep['key']} | {', '.join(i['key'] for i in rest[:4])}{' ...' if len(rest) > 4 else ''} | {e['dims']} | {_c(e['redundant_cells'])} | {', '.join(sorted({i['summary'] for i in e['items']}))} |")
        new("merge", f"Merge {_pl(c['exact_redundant'], 'line item')} that repeat a calculation already made ({_pl(c['exact_groups'], 'group')})",
            [e["items"][0]["key"] for e in red.exact[:8]],
            {"cells": c["exact_cells"], "effort": 0, "objects": c["exact_redundant"]},
            {"readers": sum(e["readers_to_repoint"] for e in red.exact), "exports": 0, "downstream_models": 0, "pages": "unknown"},
            "check pages",
            f"{c['exact_redundant']} calculated line items have the same resolved formula, dimensions, time scale and versions as another line item in the model. "
            f"Each is computed and stored twice: {_c(c['exact_cells'])} cells. The keeper in each group is the one most formulas already read.",
            ["For each group, keep the line item most formulas read (first column).",
             "Repoint every formula that reads a duplicate to the keeper (the readers count is in the table).",
             "Where the summary methods differ (last column), decide which one the pages need before merging; that is the one legitimate reason for two copies.",
             "Check pages for the duplicates, then delete them."],
            [f"Cell count falls by about {_c(c['exact_cells'])}.", "No page shows a blank; no export loses a column.",
             "Re-run this report: the group count reaches zero."],
            rows, rules=["REDUNDANT-EXACT"])

    # 3 aliases
    if red.aliases:
        c = red.counts()
        rows = ["| Alias | Is just | Cells | Readers to repoint | Summary (alias / target) |", "|---|---|---|---|---|"]
        for a in red.aliases[:25]:
            rows.append(f"| {a['item']} | {a['target']} | {_c(a['cells'])} | {a['readers']} | {a['summary']} / {a['target_summary']} |")
        new("collapse", f"Collapse {_pl(c['aliases'], 'line item')} that only copy another line item",
            [a["item"] for a in red.aliases[:8]],
            {"cells": c["alias_cells"], "effort": 0, "objects": c["aliases"]},
            {"readers": sum(a["readers"] for a in red.aliases), "exports": 0, "downstream_models": 0, "pages": "unknown"},
            "check pages",
            f"{c['aliases']} line items have the formula `B = A` with the same dimensions as A. Each stores a second copy of A: {_c(c['alias_cells'])} cells. "
            "Readers of B can read A directly. Some exist to give a page a friendlier name; those are the ones to keep.",
            ["Repoint each reader of the alias to the target (readers column).",
             "Keep an alias only where a page or export needs it under that name.",
             "Delete the rest."],
            [f"Cell count falls by up to {_c(c['alias_cells'])}.", "Re-run this report: the alias count falls to the ones kept on purpose."],
            rows, rules=["REDUNDANT-ALIAS"])

    # 4 near duplicates
    cross = [n for n in red.near if not n["same_module"]]
    if cross:
        rows = ["| Line item | Near twin | The one difference | Cells |", "|---|---|---|---|"]
        for n in cross[:25]:
            rows.append(f"| {n['a']} | {n['b']} | `{n['differs'][0][:40]}` vs `{n['differs'][1][:40]}` | {_c(n['cells'])} |")
        new("merge", f"Reconcile {_pl(len(cross), 'pair')} of formulas that differ in exactly one place", [n["a"] for n in cross[:8]],
            {"cells": 0, "effort": 0, "objects": len(cross)},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "n/a"},
            "judgment",
            "Same formula skeleton, same dimensions, one leaf differs: a constant, a reference or a list item. This is what copy, paste and tweak leaves behind. "
            "Either the difference is intended (then the name should say so) or one of the pair is the stale copy.",
            ["For each pair, read the difference column and decide: intended, or drift.",
             "Intended: rename so the difference is in the name, or add a note.",
             "Drift: fix the stale one, or merge as an exact duplicate."],
            ["Re-run this report: pairs that were drift are gone; pairs that were intended carry a note."],
            rows, rules=["REDUNDANT-NEAR"])

    # 5 pass-through chains
    chains = g.daisy_chains()
    if chains:
        rows = ["| Head | Steps | Reads, in the end |", "|---|---|---|"]
        for ch in chains[:20]:
            rows.append(f"| {ch[0][0]}.{ch[0][1]} | {len(ch)} | {ch[-1][0]}.{ch[-1][1]} |")
        cells = sum(model.line_items[k].cell_count for ch in chains for k in ch[1:-1] if k in model.line_items)
        new("collapse", f"Shorten {_pl(len(chains), 'pass-through chain')}", [f"{ch[0][0]}.{ch[0][1]}" for ch in chains[:8]],
            {"cells": cells, "effort": 0, "objects": sum(len(ch) - 2 for ch in chains)},
            {"readers": len(chains), "exports": 0, "downstream_models": 0, "pages": "unknown"},
            "check pages",
            "A reads B reads C, each a pure copy. Every step recalculates on any change, and each intermediate is a stored copy. Anaplan's checklist: never.",
            ["Point each head at the line item at the end of its chain.",
             "The intermediates then have no formula readers; treat them as aliases (previous action) and check pages before deleting."],
            ["Re-run this report: pass-through chains reach zero."],
            rows, rules=["A-DAISY"])

    # 6 unreferenced, unclassified
    if red.unknown:
        big = [u for u in red.unknown if u["cells"] >= 50_000]
        if big:
            rows = ["| Module | Line items with no reader | Cells | Effort |", "|---|---|---|---|"]
            for u in big[:20]:
                rows.append(f"| {u['module']} | {len(u['items'])}: {', '.join(u['items'][:5])}{' ...' if len(u['items']) > 5 else ''} | {_c(u['cells'])} | {u['effort']}% |")
            new("retire", f"Confirm and retire {_pl(sum(len(u['items']) for u in big), 'calculated line item')} that no formula, export or twin explains",
                [u["module"] for u in big[:8]],
                {"cells": sum(u["cells"] for u in big), "effort": sum(u["effort"] for u in big), "objects": sum(len(u["items"]) for u in big)},
                {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "unknown"},
                "check pages",
                "Calculated, read by no formula, not exported, not in an output-style module, and not a twin of anything. Either a page reads them or nothing does. "
                f"({len(red.output_like)} other unreferenced line items look like page outputs by their module, format or time scale and are not listed here.)",
                ["For each module, list the pages that use it.",
                 "Where nothing does, set the formula blank in a sandbox and wait a cycle.",
                 "Delete what nobody missed."],
                ["Cell count falls by what was deleted.", "Re-run this report: the unknown list shrinks to the ones a page needs."],
                rows, rules=["G-UNUSED"])

    # 9 IF chains that are mapping tables
    if by_rule.get("A-IF-COUNT"):
        for x in by_rule["A-IF-COUNT"][:6]:
            li = model.line_items.get((x.module, x.line_item))
            mapping = _if_mapping(li.formula) if li else None
            if mapping:
                lst = mapping[0][0].split(".")[0]
                rows = [f"| {lst} item | Value |", "|---|---|"] + [f"| {k.split('.', 1)[1] if '.' in k else k} | `{v[:80]}` |" for k, v in mapping[:30]]
                new("refactor", f"Replace the {len(mapping)}-branch IF in {x.object} with a mapping module", [x.object],
                    {"cells": 0, "effort": li.calc_effort if li else 0, "objects": 1},
                    {"readers": len(g.rev.get((x.module, x.line_item), ())), "exports": 0, "downstream_models": 0, "pages": "n/a"},
                    "proven",
                    f"The formula is a lookup table written as {len(mapping)} nested IFs over {lst}. Every branch is evaluated for every cell" + (f"; this line item carries {li.calc_effort}% of the model's calculation effort." if li and li.calc_effort else ".")
                    + " The table below is the mapping the formula encodes, ready to load.",
                    [f"Create a module dimensioned by {lst} with one list-formatted line item (the driver) loaded from the table below.",
                     f"Replace the formula with a single LOOKUP against that module.",
                     "The next new account is a row in the mapping, not a new branch."],
                    ["Same values on every cell before and after (export the line item, diff).", f"Calculation effort of {x.object} falls."],
                    rows, rules=["A-IF-COUNT"])
            else:
                new("refactor", f"Split the {x.value}-IF formula in {x.object}", [x.object],
                    {"cells": 0, "effort": li.calc_effort if li else 0, "objects": 1},
                    {"readers": len(g.rev.get((x.module, x.line_item), ())), "exports": 0, "downstream_models": 0, "pages": "n/a"},
                    "judgment", f"{x.message}. Anaplan's checklist: refactor above 10.",
                    ["Split the conditions into Boolean line items, one per condition, named for what they test.", "Combine with a short IF or a LOOKUP."],
                    ["Same values before and after."], [f"`{(li.formula if li else '')[:300]}`"], rules=["A-IF-COUNT"])

    # 14 oversized modules, empty modules
    for x in by_rule.get("A-LI-COUNT", [])[:5]:
        new("tidy", f"Split {x.module} ({x.value} line items)", [x.module], {"cells": 0, "effort": 0, "objects": 1},
            {"readers": _readers_outside(g, [(x.module, n) for n in model.modules[x.module].line_items], x.module), "exports": len(_exports_on(m, x.module)), "downstream_models": 0, "pages": "unknown"},
            "judgment", "Modules with many line items are slow to open and hard to read. Anaplan's checklist: no more than 50. Split by purpose, not by count.",
            ["Group the line items by what reads them (the graph gives the groups).", "Move each group to a module named for its purpose; repoint readers."],
            ["No module over 50 line items."], [f"Readers outside the module to repoint: {_readers_outside(g, [(x.module, n) for n in model.modules[x.module].line_items], x.module)}."], rules=["A-LI-COUNT"])
    # 16 critical: parse errors and impossible cycles
    crit = [x for x in findings if x.severity == "critical"]
    if crit:
        new("fix", f"Look at {len(crit)} formulas the parser could not follow", [x.object for x in crit[:8]], {"cells": 0, "effort": 0, "objects": len(crit)},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "judgment",
            "Either the grammar has a gap or the export is corrupt. Until resolved, the graph is missing these edges and every count above is slightly low.",
            ["Open an issue with the formula shape (not the model).", "Re-run when the parser is updated."], ["Parse rate 100%."], [f"{x.object}: {x.message[:120]}" for x in crit[:10]])
    return out


def _grouped(er, n0: int) -> list[Action]:
    """Rule-based fixes are the same job in every model, so one action each across the estate, with a Model column."""
    out: list[Action] = []
    nid = [n0]
    per = []   # (m, by_rule)
    for m in er.models:
        br = defaultdict(list)
        for x in m.lint.findings:
            br[x.rule].append(x)
        per.append((m, br))

    def new(kind, title, objects, payoff, touches, confidence, why, steps, verify, evidence, rules=(), models=()):
        nid[0] += 1
        label = ", ".join(models) if len(models) <= 2 else f"{len(models)} models"
        out.append(Action(f"A{nid[0]}", kind, title, label, objects, payoff, touches, confidence, why, steps, verify, evidence, rules=list(rules)))

    def li(m, x):
        return m.model.line_items.get((x.module, x.line_item))

    # stale and orphan actions
    rows = ["| Model | Action | Last run | In a process | Target |", "|---|---|---|---|---|"]; n = both = 0; models = []; objs = []
    for m, _ in per:
        a = m.facts.get("actions")
        if not a or not (a["stale"] or a["orphans"]):
            continue
        models.append(m.name)
        stale = dict(a["stale"]); orphans = set(a["orphans"]); allx = orphans | set(stale)
        n += len(allx); both += len(orphans & set(stale))
        for name in sorted(allx, key=lambda x: (not (x in orphans and x in stale), stale.get(x, "9999"))):
            act = m.actions.actions.get(name); objs.append(name)
            rows.append(f"| {m.name} | {name} | {stale.get(name, 'recent')} | {'no' if name in orphans else 'yes'} | {act.target if act else ''} |")
    if n:
        new("schedule", f"Retire or schedule {n} imports and exports that no process runs or that have not run in a year",
            objs[:8], {"cells": 0, "effort": 0, "objects": 0, "actions": n},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "proven",
            f"{both} of them are both outside every process and stale. An action nobody schedules is either run by hand (document it) or dead (delete it). "
            "An import that was the only load into its target module takes the module with it; an import from a source that no longer exists (see external sources) is dead by definition.",
            ["For each action, ask the owner: run by hand, or forgotten?",
             "Forgotten: delete the action; if it was the only import into its target module, that module joins the retire list.",
             "Run by hand: put it in a process with a name that says when."],
            ["Actions export shows every import and export inside a process, each with a run date inside the window."], rows, models=models)

    # unguarded divides
    rows = ["| Model | Line item | Replace with |", "|---|---|---|"]; objs = []; models = []
    for m, br in per:
        for x in br.get("F-DIVIDE", []):
            l = li(m, x); fixed = _divide_fix(l.formula) if l else None
            rows.append(f"| {m.name} | {x.object} | `{(fixed or 'DIVIDE(numerator, denominator)')[:140]}` |"); objs.append(x.object)
            if m.name not in models: models.append(m.name)
    if objs:
        new("fix", f"Guard {_pl(len(objs), 'division')} that error on zero", objs[:8], {"cells": 0, "effort": 0, "objects": len(objs)},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "proven",
            "A / B shows an error cell when B is zero, and every summary above it shows an error too. DIVIDE() returns zero. The replacement formula is written out; paste it.",
            ["Paste the replacement formula from the table into each line item.", "Where a zero denominator should show blank rather than zero, wrap in IF instead."],
            ["No error cells on the pages that show these line items at a total level."], rows, rules=["F-DIVIDE"], models=models)

    # hard-coded constants
    consts = defaultdict(list); nf = 0; models = []
    for m, br in per:
        for x in br.get("F-HARDCODE", []):
            nf += 1
            if m.name not in models: models.append(m.name)
            for v in x.value.split(","):
                if v: consts[v].append(f"{m.name}: {x.object}")
    if consts:
        rows = ["| Constant | Used in | Suggested input |", "|---|---|---|"] + [f"| {v} | {', '.join(o[:4])}{' ...' if len(o) > 4 else ''} | Assumption {i + 1} |" for i, (v, o) in enumerate(sorted(consts.items(), key=lambda kv: -len(kv[1])))]
        new("refactor", f"Move {_pl(len(consts), 'hard-coded constant')} into assumptions modules", list(consts)[:8], {"cells": 0, "effort": 0, "objects": nf},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "proven",
            "Numbers inside formulas are assumptions nobody can see or change without a model builder. The same constant in more than one formula drifts.",
            ["Create (or reuse) a settings module per model with one line item per constant, named, with a note saying who owns it.",
             "Replace each constant with the reference.", "Tell the owner where the number now lives."],
            ["Search formulas for the constant: zero hits."], rows, rules=["F-HARDCODE"], models=models)

    # subsidiary views
    rows = ["| Model | Line item | Applies to | Module applies to | Readers |", "|---|---|---|---|---|"]; objs = []; readers = 0; models = []
    for m, br in per:
        for x in br.get("A-SUBSIDIARY", []):
            l = li(m, x); mod = m.model.modules.get(x.module)
            rows.append(f"| {m.name} | {x.object} | {', '.join(l.applies_to) if l else ''} | {', '.join(mod.applies_to) if mod else ''} | {x.value} |")
            objs.append(x.object); readers += int(x.value or 0)
            if m.name not in models: models.append(m.name)
    if objs:
        new("tidy", f"Move {_pl(len(objs), 'subsidiary-view line item')} into modules of their own dimensions", objs[:8], {"cells": 0, "effort": 0, "objects": len(objs)},
            {"readers": readers, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "proven",
            "A line item dimensioned differently from its module is a subsidiary view. Used in calculation, it hides a lookup and confuses the next builder. Anaplan's checklist: display only.",
            ["Create or find a module dimensioned as the line item is (usually a SYS module for that list).", "Move the line item; repoint its readers."],
            ["Modules export: no calculation module has a line item whose Applies To differs from the module's."], rows, rules=["A-SUBSIDIARY"], models=models)

    # summaries on
    rows = ["| Model | Line item | Summary | Cells |", "|---|---|---|---|"]; objs = []; models = []
    for m, br in per:
        for x in br.get("A-SUMMARY-ON", []):
            l = li(m, x); rows.append(f"| {m.name} | {x.object} | {x.value} | {_c(l.cell_count) if l else ''} |"); objs.append(x.object)
            if m.name not in models: models.append(m.name)
    if objs:
        new("tidy", f"Turn summaries off on {_pl(len(objs), 'large line item')} no formula reads", objs[:8], {"cells": 0, "effort": 0, "objects": len(objs)},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "unknown"}, "check pages",
            "Summaries calculate on every parent of every dimension. Where no formula reads the line item, only a page could need the total.",
            ["For each, check whether a page shows it at a parent level.", "If not, set Summary to None."],
            ["Model open time and calculation effort fall; no page shows a blank total."], rows, rules=["A-SUMMARY-ON"], models=models)

    # text, FINDITEM, joins, system functions in big modules
    rows = ["| Model | Line item | What | Cells |", "|---|---|---|---|"]; objs = []; readers = 0; models = []
    for m, br in per:
        for r in ("A-TEXT-FORMAT", "A-FINDITEM", "A-TEXT-JOIN", "A-SYSTEMS-FN"):
            for x in br.get(r, []):
                l = li(m, x); rows.append(f"| {m.name} | {x.object} | {RULES[r].title} | {_c(l.cell_count) if l else ''} |"); objs.append(x.object)
                readers += len(m.graph.rev.get((x.module, x.line_item), ()))
                if m.name not in models: models.append(m.name)
    if objs:
        new("tidy", f"Move {_pl(len(objs), 'text and lookup line item')} out of large calculation modules", objs[:8], {"cells": 0, "effort": 0, "objects": len(objs)},
            {"readers": readers, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "proven",
            "Text, FINDITEM, ITEM() and text joins in a multi-dimensional line item are computed once per cell. In a one-dimension system module they are computed once per list item.",
            ["Compute each once in a SYS module dimensioned by the list it depends on.", "Reference it from the calculation module."],
            ["Calculation effort of the listed line items falls; cell count of TEXT line items falls."], rows,
            rules=["A-TEXT-FORMAT", "A-FINDITEM", "A-TEXT-JOIN", "A-SYSTEMS-FN"], models=models)

    # mixed clauses
    rows = ["| Model | Line item | Clause | Formula |", "|---|---|---|---|"]; objs = []; models = []
    for m, br in per:
        for x in br.get("F-MIXED-CLAUSE", []):
            l = li(m, x); rows.append(f"| {m.name} | {x.object} | {x.value} | `{l.formula[:100] if l else ''}` |"); objs.append(x.object)
            if m.name not in models: models.append(m.name)
    if objs:
        new("fix", f"Split {_pl(len(objs), 'formula')} that aggregate and look up in one bracket", objs[:8], {"cells": 0, "effort": 0, "objects": len(objs)},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "proven",
            "SUM with LOOKUP or SELECT in one expression makes the engine build a large intermediate mapping. Anapedia: never combine them.",
            ["Aggregate into an intermediate line item first.", "Look up from the intermediate."], ["Same values; calculation effort falls."], rows, rules=["F-MIXED-CLAUSE"], models=models)

    # empty modules
    empties = [(m.name, x.module) for m, br in per for x in br.get("G-EMPTY-MODULE", [])]
    if empties:
        new("tidy", f"Delete {_pl(len(empties), 'empty module')}", [f"{a}: {b}" for a, b in empties][:8], {"cells": 0, "effort": 0, "objects": len(empties)},
            {"readers": 0, "exports": 0, "downstream_models": 0, "pages": "n/a"}, "proven", "No line items. Usually a leftover from a build that moved on.",
            ["Delete."], ["Modules export: none with an empty Line Items column."], [", ".join(f"{a}: {b}" for a, b in empties)], rules=["G-EMPTY-MODULE"], models=sorted({a for a, _ in empties}))
    return out


def _estate_actions(er, n0: int) -> list[Action]:
    out = []
    if er.duplicates:
        hub = Counter(mm for d in er.duplicates for mm in d["models"]).most_common(1)[0][0]
        rows = ["| Line item | Models | Formula |", "|---|---|---|"] + [f"| {d['line_item']} | {', '.join(d['models'])} | `{d['formula'][:80]}` |" for d in er.duplicates[:25]]
        out.append(Action(f"A{n0 + 1}", "dedupe", f"Give {len(er.duplicates)} calculations that exist in more than one model a single owner", "Estate",
                          [d["line_item"] for d in er.duplicates[:8]], {"cells": 0, "effort": 0, "objects": len(er.duplicates)},
                          {"readers": 0, "exports": 0, "downstream_models": len({mm for d in er.duplicates for mm in d["models"]}), "pages": "n/a"}, "judgment",
                          f"The same line item, same formula, in more than one model. A change in one must be repeated in the others, and one day it is not. {hub} holds the most copies; where a feed already exists, it can own the value and the others import it.",
                          ["Pick the owner per line item (usually the hub).", "Add the line item to an export the other model already imports.", "Replace the copy with the imported value."],
                          ["Re-run this report: the cross-model duplicate list is empty or annotated."], rows, rules=["DUP-CROSS"]))
    return out


def build(er) -> list[Action]:
    estate_cells = sum(m.facts["cells"] for m in er.models) or 1
    acts: list[Action] = []
    for m in er.models:
        acts += _actions_for_model(er, m, len(acts))
    acts += _grouped(er, len(acts))
    acts += _estate_actions(er, len(acts))
    for a in acts:
        a.score = _score(a, estate_cells)
    acts.sort(key=lambda a: -a.score)
    for i, a in enumerate(acts, 1):
        a.id = f"A{i}"
    return acts


# ---------------------------------------------------------------- rendering

def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def _reclaims(a: Action) -> str:
    p = a.payoff; parts = []
    upto = "up to " if a.kind in ("refactor", "tidy", "fix") else ""
    if p.get("cells"):
        parts.append(f"{upto}{_c(p['cells'])} cells")
    if p.get("effort"):
        parts.append(f"{upto}{p['effort']:.1f}% effort")
    if p.get("actions"):
        parts.append(_pl(p["actions"], "action"))
    if not parts and p.get("objects"):
        parts.append(_pl(p["objects"], "object"))
    return ", ".join(parts)


def _touches(a: Action) -> str:
    t = a.touches; parts = []
    if t.get("readers"):
        parts.append(_pl(t["readers"], "formula"))
    if t.get("exports"):
        parts.append(_pl(t["exports"], "export"))
    if t.get("downstream_models"):
        parts.append(_pl(t["downstream_models"], "model"))
    if t.get("pages") == "unknown":
        parts.append("pages: check")
    return ", ".join(parts) or "nothing in the exports"


def heading(a: Action) -> str:
    return f"{a.id}. {a.title}"


def render_list(acts: list[Action], limit: int = 40) -> list[str]:
    out = ["| # | Do this | Model | Reclaims | Touches | Exports can prove |", "|---|---|---|---|---|---|"]
    for a in acts[:limit]:
        out.append(f"| {a.id} | [{a.title}](#{_slug(heading(a))}) | {a.model} | {_reclaims(a)} | {_touches(a)} | {a.confidence} |")
    if len(acts) > limit:
        out += ["", f"{len(acts) - limit} more, smaller, in [Actions in detail](#actions-in-detail)."]
    return out


def render_detail(acts: list[Action]) -> list[str]:
    out = []
    for a in acts:
        out += [f"## {heading(a)}", "",
                f"**{a.model}.** {a.why}", "",
                f"| Reclaims | Touches | Exports can prove |", "|---|---|---|",
                f"| {_reclaims(a) or 'nothing measurable; readability'} | {_touches(a)} | {a.confidence}: {CONFIDENCE[a.confidence]} |", "",
                "**Steps**", ""]
        out += [f"{i}. {s}" for i, s in enumerate(a.steps, 1)]
        out += ["", "**Verify**", ""] + [f"- {v}" for v in a.verify]
        if a.evidence:
            out += ["", "**Evidence**", ""] + a.evidence
        out.append("")
    return out
