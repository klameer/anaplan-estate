"""Dimension inference: which axes a formula's value really varies over, and what an unused axis costs.

The exports never say how big a list is, how many periods a time range holds
or how many versions there are. Every line item's Cell Count is the product of
those sizes over its dimensions, its time scale and range, and Versions, so
the sizes can be solved from the items whose factors are all known but one,
each solved size voted for by every item that gives it. A size is reported
with the number of items that agree, never as a fact the export stated.

Applies To is blank on most line items of a model-level export: it means the
line item takes its module's dimensions, and the Modules export names them.
Without that export a module's dimensions are one unnamed factor, sized like
a list (it solves to 1 where blank really means none), and the line items
that carry it are judged on Time and Versions only, since their lists cannot
be compared by name.

A formula's references say which axes a line item's value really varies
over. A referenced line item brings its own axes; SELECT removes one; LOOKUP
brings the mapping's axes in place of the source's; SUM and its kin aggregate
to a list the export does not name, so those items are judged only as far as
that allows; time functions bring Time, version functions bring Versions,
ITEM(List) brings that list. An axis the item applies to that no reference
needs multiplies its cells without varying its value: over-dimensioned,
priced as the cells it would not have without that axis when the axis size
is known. An axis the references carry that the item lacks is aggregated or
mapped implicitly by Anaplan (hierarchy, subset, summary): listed, not
judged, since the exports do not carry those relations.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from .parsing import parse, ParseError, LexError
from .graph import LIST_ARG
from anaplan_grammar.functions import CLAUSE_KINDS

TIME, VERSIONS = "Time", "Versions"
_NA = {"", "-", "not applicable", "none", "no"}
TIME_FUNCS = {"ADDMONTHS", "ADDYEARS", "CUMULATE", "DAYS", "DAYSINMONTH", "DAYSINYEAR", "CURRENTPERIODEND", "CURRENTPERIODSTART", "DECUMULATE", "END", "HALFYEARTODATE", "HALFYEARVALUE",
              "INPERIOD", "LAG", "LEAD", "MONTHTODATE", "MONTHVALUE", "MOVINGSUM", "NEXT", "OFFSET", "PERIOD", "POST", "PREVIOUS", "PROFILE",
              "QUARTERTODATE", "QUARTERVALUE", "SPREAD", "START", "WEEKTODATE", "WEEKVALUE", "YEARTODATE", "YEARVALUE"}
TIME_AGG_FUNCS = {"TIMESUM"}                    # aggregate Time away
VERSION_FUNCS = {"CURRENTVERSION", "ISCURRENTVERSION", "ISACTUALVERSION", "PREVIOUSVERSION", "NEXTVERSION"}
AGG_CLAUSES = frozenset(CLAUSE_KINDS) - {"SELECT", "LOOKUP"}
MAX_ROUNDS = 12
BUNDLE_PREFIX = "[dimensions of "


def bundle(module: str) -> str:
    """The axis standing for a module's unnamed dimensions."""
    return f"{BUNDLE_PREFIX}{module}]"


def is_bundle(axis: str) -> bool:
    return axis.startswith(BUNDLE_PREFIX)


def bundle_module(axis: str) -> str:
    return axis[len(BUNDLE_PREFIX):-1]


def has_time(li) -> bool:
    return (li.time_scale or "").strip().lower() not in _NA


def has_versions(li) -> bool:
    return (li.versions or "").strip().lower() not in _NA


def module_dims(model, module: str) -> tuple | None:
    """The module's dimensions as the Modules export names them; None when no export named them (an imputed
    majority of explicit line items is not that: in a model-level export the explicit ones are the exceptions)."""
    mod = model.modules.get(module)
    if mod is not None and mod.applies_to and not mod.dims_inferred:
        return tuple(mod.applies_to)
    return None


def list_axes(li, model) -> tuple[tuple, str | None]:
    """(named lists, bundle axis or None): the line item's own Applies To, else its module's as the Modules export
    names them, else its module's unnamed dimensions as one bundle."""
    if li.applies_to:
        return tuple(li.applies_to), None
    md = module_dims(model, li.module)
    if md is not None:
        return md, None
    return (), bundle(li.module)


def factors(li, model) -> list[tuple]:
    """The unknowns a line item's cell count multiplies: one per named list, one per unnamed module bundle, one per
    (time scale, time range), one per Versions setting."""
    dims, b = list_axes(li, model)
    fs: list[tuple] = [("dim", d) for d in dims]
    if b:
        fs.append(("mod", bundle_module(b)))
    if has_time(li):
        fs.append(("time", (li.time_scale.strip(), (li.time_range or "").strip())))
    if has_versions(li):
        fs.append(("versions", (li.versions or "").strip()))
    return fs


def factor_label(f: tuple) -> str:
    if f[0] == "dim":
        return f[1]
    if f[0] == "mod":
        return bundle(f[1])
    if f[0] == "time":
        return f"{TIME} ({f[1][0]}" + (f", {f[1][1]}" if f[1][1] and f[1][1].lower() not in _NA else "") + ")"
    return f"{VERSIONS} ({f[1]})" if f[1] and f[1].lower() != "all" else VERSIONS


def _ordered(axes) -> list[str]:
    dims = sorted(a for a in axes if a not in (TIME, VERSIONS) and not is_bundle(a))
    bundles = sorted(a for a in axes if is_bundle(a))
    return dims + bundles + [a for a in (TIME, VERSIONS) if a in axes]


def infer_sizes(model) -> dict:
    """Solve list, module-bundle, time and version sizes from cell counts. Returns {factor: {"size", "evidence",
    "agreement", "items"}} plus "_explained" (how many cell counts the sizes reproduce exactly) and "_unknown"."""
    items = [li for li in model.line_items.values() if not li.is_header and li.cell_count > 0]
    fmap = {li.key: factors(li, model) for li in items}
    known: dict[tuple, int] = {}
    assumed: set[tuple] = set()

    def rounds() -> None:
        for _ in range(MAX_ROUNDS):
            votes: dict[tuple, Counter] = defaultdict(Counter)
            for li in items:
                fs = fmap[li.key]
                unknown = [f for f in fs if f not in known]
                if len(unknown) != 1:
                    continue
                prod = 1
                for f in fs:
                    if f in known:
                        prod *= known[f]
                if prod and li.cell_count % prod == 0 and li.cell_count // prod > 0:
                    votes[unknown[0]][li.cell_count // prod] += 1
            fresh = {f: c.most_common(1)[0][0] for f, c in votes.items() if f not in known}
            if not fresh:
                break
            known.update(fresh)

    rounds()
    # A module bundle nothing isolates (every blank line item in it also carries Time or Versions) is assumed to be no
    # dimension at all, which is what blank means in an export that names every dimension; the sizes that follow from
    # the assumption are marked as such.
    stuck = {f for fs in fmap.values() for f in fs if f not in known and f[0] == "mod"}
    if stuck:
        before = set(known)
        for f in stuck:
            known[f] = 1
            assumed.add(f)
        rounds()
        for f in set(known) - before - stuck:
            assumed.add(f)
    out: dict = {}
    counts: Counter = Counter()
    agree: Counter = Counter()
    evidence: Counter = Counter()
    explained = 0
    for li in items:
        fs = fmap[li.key]
        for f in fs:
            counts[f] += 1
        if all(f in known for f in fs):
            prod = 1
            for f in fs:
                prod *= known[f]
            if prod == li.cell_count:
                explained += 1
            for f in fs:
                others = prod // known[f] if known[f] else 0
                if others and li.cell_count % others == 0:
                    evidence[f] += 1
                    if li.cell_count // others == known[f]:
                        agree[f] += 1
    for f, size in known.items():
        out[f] = {"size": size, "evidence": evidence[f], "agreement": round(agree[f] / evidence[f], 3) if evidence[f] else None, "items": counts[f],
                  "assumed": f in assumed}
    out["_explained"] = {"items": explained, "of": len(items), "share": round(explained / len(items), 3) if items else None}
    out["_assumed"] = sorted(assumed, key=factor_label)
    out["_unknown"] = sorted({f for fs in fmap.values() for f in fs if f not in known}, key=factor_label)
    out["_blank"] = sum(1 for li in model.line_items.values() if not li.is_header and not li.applies_to)
    out["_bundled_modules"] = sorted({f[1] for f, size in known.items() if f[0] == "mod" and size != 1})
    return out


class Judge:
    """Which axes each formula requires, over one parsed model and its graph."""

    def __init__(self, model, graph, sizes: dict | None = None):
        self.model = model
        self.graph = graph
        self.sizes = sizes or {}

    def axes_of(self, li) -> frozenset:
        dims, b = list_axes(li, self.model)
        s = set(dims)
        if b:
            sz = self.sizes.get(("mod", bundle_module(b)))
            if sz is None or sz["size"] != 1:          # a bundle that solved to 1 is no dimension at all
                s.add(b)
        if has_time(li):
            s.add(TIME)
        if has_versions(li):
            s.add(VERSIONS)
        return frozenset(s)

    def _mapping_target(self, m, li) -> str | None:
        """What an aggregation mapping points into: Time for a time-period formatted line item, Versions for a version
        formatted one, None for a list (the export does not name which)."""
        if not isinstance(m, dict) or m.get("t") != "ref":
            return None
        r = self.graph.resolve(li, list(m.get("path") or []))
        if r.kind != "line_item":
            return None
        fmt = (self.model.line_items[r.target].format_type or "").upper()
        if "TIME" in fmt:
            return TIME
        if "VERSION" in fmt:
            return VERSIONS
        return None

    def bundle_assumed(self, li) -> bool:
        """True when the line item's module bundle was not solved but assumed to be no dimension."""
        _, b = list_axes(li, self.model)
        if not b:
            return False
        sz = self.sizes.get(("mod", bundle_module(b)))
        return bool(sz and sz.get("assumed"))

    def _walk(self, node, li, own: frozenset, fn: str | None = None, argi: int | None = None) -> tuple[set, dict]:
        """(axes the expression varies over, flags). Flags: unresolved (a reference the model does not contain),
        sums (number of aggregation clauses), collect (line item subsets, not in the exports)."""
        axes: set = set()
        flags: dict = {"unresolved": 0, "sums": 0, "collect": 0, "assumed": 0}
        if not isinstance(node, dict):
            return axes, flags

        def merge(a, f):
            axes.update(a)
            for k in flags:
                flags[k] += f.get(k, 0)

        t = node.get("t")
        if t == "ref":
            r = self.graph.resolve(li, list(node.get("path") or []), fn, argi)
            if r.kind == "line_item":
                target = self.model.line_items[r.target]
                axes.update(self.axes_of(target))
                if self.bundle_assumed(target):
                    flags["assumed"] += 1
            elif r.kind == "dimension":
                name = (node.get("path") or [""])[0]
                up = str(name).upper()
                axes.add(TIME if up == "TIME" else VERSIONS if up in ("VERSIONS", "VERSION") else name)
            elif r.kind == "unresolved":
                flags["unresolved"] += 1
            return axes, flags
        if t == "clause":
            a, f = self._walk(node.get("x"), li, own)
            merge(a, f)
            for cl in node.get("clauses") or []:
                k = (cl.get("k") or "").upper()
                m = cl.get("m")
                if k == "SELECT":
                    path = (m or {}).get("path") if isinstance(m, dict) else None
                    if path:
                        up = str(path[0]).upper()
                        axes.discard(TIME if up == "TIME" else VERSIONS if up in ("VERSIONS", "VERSION") else path[0])
                elif k == "LOOKUP":
                    ma, mf = self._walk(m, li, own)
                    axes = (axes & set(own)) | ma          # the source axis the mapping replaces is one the item does not carry
                    for kk in flags:
                        flags[kk] += mf.get(kk, 0)
                else:                                       # SUM, AVERAGE, MIN, MAX, ANY, ALL, TEXTLIST, ...: aggregated along the mapping
                    ma, mf = self._walk(m, li, own)
                    axes -= ma
                    tgt = self._mapping_target(m, li)
                    if tgt:
                        axes.add(tgt)                       # a time-period or version formatted mapping aggregates into Time or Versions
                    else:
                        flags["sums"] += 1                  # a list-formatted mapping: into a list the export does not name
                    for kk in flags:
                        flags[kk] += mf.get(kk, 0)
            return axes, flags
        if t == "call":
            f = (node.get("f") or "").upper()
            for i, arg in enumerate(node.get("args") or []):
                if (f, i) in LIST_ARG and f != "ITEM":
                    continue                                # FINDITEM(List, ..), PREVIOUS(x, List): the list says where to look, it is not an axis
                a, fl = self._walk(arg, li, own, f, i)
                merge(a, fl)
            if f in TIME_FUNCS:
                axes.add(TIME)
            if f in TIME_AGG_FUNCS:
                axes.discard(TIME)
            if f in VERSION_FUNCS:
                axes.add(VERSIONS)
            if f == "COLLECT":
                flags["collect"] += 1
            return axes, flags
        for key in ("l", "r", "c", "a", "b", "x"):
            if isinstance(node.get(key), dict):
                a, f = self._walk(node[key], li, own)
                merge(a, f)
        return axes, flags

    def judge(self, li) -> dict:
        own = self.axes_of(li)
        out = {"ref": f"{li.module}.{li.name}", "module": li.module, "name": li.name, "cells": li.cell_count, "formula": li.formula,
               "applied": _ordered(own), "required": [], "extra": [], "implicit": [], "judged": False, "reason": "", "sums": 0,
               "constant": False, "partial": False, "unplaced": [], "lists_judged": True}
        if li.is_header or not (li.formula or "").strip():
            out["reason"] = "input: no formula to judge"
            return out
        try:
            ast = parse(li.formula)
        except (ParseError, LexError) as ex:
            out["reason"] = f"formula not parsed: {ex}"[:200]
            return out
        req, flags = self._walk(ast, li, own)
        out["required"] = _ordered(req)
        out["sums"] = flags["sums"]
        if flags["unresolved"]:
            out["reason"] = f"{flags['unresolved']} reference(s) the export does not contain"
            return out
        if flags["collect"]:
            out["reason"] = "COLLECT(): line item subsets are not in the exports"
            return out
        assumed = flags["assumed"] > 0 or self.bundle_assumed(li)
        opaque = any(is_bundle(a) for a in own | req) or assumed
        notes = []
        if opaque:
            # lists cannot be compared by name on either side: only Time and Versions are judged
            out["lists_judged"] = False
            notes.append("module dimensions assumed none, not solved: lists not compared, Time and Versions judged" if assumed and not any(is_bundle(a) for a in own | req)
                         else "module dimensions unnamed in this export (no Modules export): lists not compared, Time and Versions judged")
            own_j = {a for a in own if a in (TIME, VERSIONS)}
            req_j = {a for a in req if a in (TIME, VERSIONS)}
        else:
            own_j, req_j = set(own), set(req)
        out["implicit"] = _ordered(req_j - own_j)
        extra = own_j - req_j
        out["constant"] = not req and not flags["sums"]
        out["judged"] = True
        if flags["sums"] and not opaque:
            if len(extra) <= flags["sums"]:
                out["unplaced"] = _ordered(extra)
                notes.append(f"{flags['sums']} aggregation clause(s) target a list the export does not name"
                             + (f": {', '.join(_ordered(extra))} taken as the target(s)" if extra else ""))
                out["reason"] = "; ".join(notes)
                return out
            out["partial"] = True
            out["extra"] = _ordered(extra)
            notes.append(f"{flags['sums']} aggregation clause(s) target a list the export does not name: at most {flags['sums']} of "
                         f"{', '.join(_ordered(extra))} can be that target; the rest multiply cells without varying the value")
            out["reason"] = "; ".join(notes)
            return out
        if flags["sums"] and opaque:
            # the aggregation target is a list; Time and Versions are never a SUM target, so they stay judged
            notes.append(f"{flags['sums']} aggregation clause(s) target a list the export does not name")
        out["extra"] = _ordered(extra)
        if out["constant"]:
            notes.append("a constant: no reference varies over any axis" if extra else "a scalar constant")
        out["reason"] = "; ".join(notes)
        return out


def factor_of(axis: str, li) -> tuple:
    if axis == TIME:
        return ("time", (li.time_scale.strip(), (li.time_range or "").strip()))
    if axis == VERSIONS:
        return ("versions", (li.versions or "").strip())
    if is_bundle(axis):
        return ("mod", bundle_module(axis))
    return ("dim", axis)


def price(j: dict, li, sizes: dict) -> None:
    """Cells the item would not have without its extra axes, when every extra axis has an inferred size. A price that
    rests on an assumed size says so."""
    j["saved_cells"] = None
    j["unpriced"] = []
    j["price_assumed"] = False
    if not j["extra"] or j["partial"] or not li.cell_count:
        return
    div = 1
    for a in j["extra"]:
        s = sizes.get(factor_of(a, li))
        if not s:
            j["unpriced"].append(a)
        else:
            div *= s["size"]
            if s.get("assumed"):
                j["price_assumed"] = True
    if j["unpriced"]:
        return
    j["saved_cells"] = li.cell_count - li.cell_count // div
