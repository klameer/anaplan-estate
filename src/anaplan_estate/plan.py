"""The action plan: one to three suggested starting points, chosen from the findings by
an explainable, deterministic ordering, and written as compact cards (do this / why /
steps / done when).

Selection is separate from presentation: `candidates` produces generic records with
evidence fields; `select` orders them and keeps at most five; the renderers only
format. Nothing here names this or that estate: generators read rule ids, effort
shares, cell counts and evidence strength, and the same code returns fewer than
three cards (or none, with the next data check) when the evidence is thin.

Ordering (RANKING below), in this order: candidates resting on inferred evidence
last (hypotheses); a bounded scope (a named object or a small group) before an
open-ended review; a materiality band from the observed footprint (effort share
within its own model, or cells; bands, never cross-model comparison of raw
shares); a concrete change before an investigation; confirmed before partial
evidence; then the larger footprint in cells; then the title, so ties never depend
on input order. A large footprint on inferred evidence or an open scope therefore
does not displace a small, well-evidenced change. This is a hypothesis about what is
worth doing first, developed on a small number of estates; it is meant to be revised.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from .findings import _c, _pl, STRENGTH_ORDER

BOUNDED = 10          # a scope of this many named objects or fewer counts as bounded
TEXT_RULES = ("A-TEXT-FORMAT", "A-FINDITEM", "A-TEXT-JOIN", "A-SYSTEMS-FN")

RANKING = [
    "Inferred evidence last: a candidate resting on names or an unresolved comparison is a hypothesis, whatever its footprint.",
    f"Scope: a bounded scope ({BOUNDED} named objects or fewer) before an open-ended review.",
    "Materiality band from the observed footprint: high (5% or more of its own model's measured effort, or 50M cells or more), medium (1% or 1M), low. Effort shares are banded within one model and never compared across models as absolute value.",
    "Kind: a concrete change with a validation criterion before an investigation.",
    "Evidence: confirmed before partial (observation confidence, not confidence in the recommendation).",
    "Then the larger observed footprint in cells, then the title. Ties never depend on the order the files were read.",
    "Overlapping findings on the same objects are merged into one decision; a change whose objects sit in a module with no consumer detected depends on that consumer check, which is then placed first.",
]


@dataclass
class Candidate:
    key: str
    kind: str                     # change | investigation
    title: str                    # action-led, names the object or bounded group
    why: str                      # one sentence: evidence and supportable value
    steps: list[str]
    done_when: str
    role: str
    model: str
    objects: list[str]
    finding_ids: list[str]
    strength: str                 # confirmed | partial | inferred
    footprint_cells: int | None = None
    footprint_effort: float | None = None   # share of THIS model's measured effort
    notices: list[str] = field(default_factory=list)      # decision-changing uncertainty, kept on the card
    depends_on: list[str] = field(default_factory=list)   # keys of candidates to complete first
    explorer: list | None = None                          # [model_index, module, name|None] for the Change impact link
    rank_reason: str = ""

    @property
    def bounded(self) -> bool:
        return len(self.objects) <= BOUNDED

    @property
    def footprint_measured(self) -> bool:
        return bool(self.footprint_cells) or bool(self.footprint_effort)

    def to_dict(self):
        d = asdict(self); d["bounded"] = self.bounded; d["footprint_measured"] = self.footprint_measured
        return d


def band(c: Candidate) -> int:
    """0 high, 1 medium, 2 low: the thresholds the findings use for importance."""
    eff = c.footprint_effort or 0; cells = c.footprint_cells or 0
    return 0 if (eff >= 5 or cells >= 50_000_000) else 1 if (eff >= 1 or cells >= 1_000_000) else 2


def rank_key(c: Candidate):
    return (1 if c.strength == "inferred" else 0, 0 if c.bounded else 1, band(c), 0 if c.kind == "change" else 1,
            STRENGTH_ORDER[c.strength], -(c.footprint_cells or 0), c.title)


def _reason(c: Candidate) -> str:
    return (f"evidence {c.strength}; " + ("bounded scope" if c.bounded else "open scope") + f"; materiality {('high', 'medium', 'low')[band(c)]}; {c.kind}"
            + (f"; {_c(c.footprint_cells)} cells" if c.footprint_cells else "; no measured footprint")
            + (f"; {c.footprint_effort:.1f}% of its model's effort" if c.footprint_effort else ""))


# ---------------------------------------------------------------- helpers

def _fmap(er):
    """object name -> finding ids naming it (complete object sets), per model."""
    out = defaultdict(list)
    for x in er.findings:
        for o in x.objects:
            out[(x.model, o)].append(x.id)
    return out


def _coverage_notices(m) -> list[str]:
    out = []
    rc = m.facts["referenced_by_check"]
    if rc["agreement"] is not None and rc["agreement"] < 0.95:
        out.append(f"Dependency coverage {rc['agreement']:.0%} in {m.name}: readers may be missing (details in Evidence).")
    if m.facts["parse_errors"]:
        out.append(f"{m.facts['parse_errors']} formulas in {m.name} did not parse; their references are absent from the graph.")
    if not m.facts.get("actions"):
        out.append(f"No Actions export for {m.name}: import and export usage not assessed.")
    return out


def _usage_modules(m) -> dict[str, dict]:
    return {s["module"]: s for s in (m.redundancy.overlap + m.redundancy.orphan_modules)}


# ---------------------------------------------------------------- generators
#
# Every card is written for someone who owns or uses the model, not only for a builder: the "why" opens with a
# plain explanation of the kind of problem, then names the modules and line items involved, then the figures.

def _li(name: str, m=None) -> tuple[str, str]:
    """(module, line item) for a 'Module.Line item' name, resolved against the model because both parts can contain dots."""
    if m is not None:
        for k in m.model.line_items:
            if f"{k[0]}.{k[1]}" == name:
                return k
        if name in m.model.modules:
            return (name, "")
    mod, _, item = name.partition(".")
    return (mod, item) if item else (name, "")


def _named(name: str, m=None) -> str:
    mod, item = _li(name, m)
    return f"the line item '{item}' in the module '{mod}'" if item else f"the module '{mod}'"


def _hotspot_candidates(er, fmap, mi, m) -> list[Candidate]:
    """Join the named high-effort line items to the findings that name them; one candidate per (model, rule family).
    Where nothing joins, an investigation of the top five, not an optimisation."""
    f = m.facts
    if not f["has_effort"] or not f["effort_top"]:
        return []
    top = f["effort_top"][:10]
    by_obj = defaultdict(list)
    for x in m.lint.findings:
        by_obj[x.object].append(x.rule)
    families = defaultdict(list)     # family -> [(name, eff, cells)]; each line item joins one family only (the more specific cause first)
    for name, eff, cells, _ in top:
        rules = set(by_obj.get(name, []))
        if "A-IF-COUNT" in rules:
            families["if"].append((name, eff, cells))
        elif "F-MIXED-CLAUSE" in rules:
            families["mixed"].append((name, eff, cells))
        elif rules & set(TEXT_RULES):
            families["text"].append((name, eff, cells))
    eff_id = next((x.id for x in er.findings if x.model == m.name and x.rules == ["EFFORT"]), None)
    out = []
    for fam, items in families.items():
        names = [n for n, *_ in items]
        eff = round(sum(e for _, e, _ in items), 1); cells = sum(c for *_, c in items)
        first, first_eff = items[0][0], items[0][1]
        ids = sorted({i for n in names for i in fmap.get((m.name, n), [])} | ({eff_id} if eff_id else set()), key=lambda s: int(s[1:]))
        n = len(names)
        others = (f" and {n - 1} similar line item{'s' if n > 2 else ''} (listed under Evidence)" if n > 1 else "")
        explorer = [mi, _li(first, m)[0], _li(first, m)[1] or None]
        if fam == "text":
            c = Candidate(key=f"hotspot-text:{m.name}", kind="change",
                          title=f"Stop working out text labels on every cell in {m.name} ({_pl(n, 'formula')})",
                          why=(f"Anaplan runs a formula once for every cell of a module. When the formula only produces a label (a text value such as a period code) "
                               f"that is the same across a whole row, working it out for every cell of a large grid is wasted effort. Moving the formula into a small helper module "
                               f"that has only the list the label depends on means it is worked out once per item and simply looked up from there. "
                               f"In {m.name} this applies to {_named(first, m)}{others}: together {_c(cells)} cells and {eff:.1f}% of the model's measured calculation effort."),
                          steps=[f"Open {_named(first, m)} ({first_eff:.1f}% of measured effort) and note which list its value actually changes with (often Time, or one list).",
                                 "In a development copy of the model, create a small system module with just that list, put the formula there, and point the places that used the old formula at the new one. Keep the old line item until the check below passes.",
                                 "Compare the results before and after, and read the Calculation Effort column before and after."],
                          done_when="Every value that used the label still matches the original, cell for cell, and the measured effort share has fallen.",
                          role=f"model builder, {m.name}", model=m.name, objects=names, finding_ids=ids, strength="confirmed",
                          footprint_cells=cells, footprint_effort=eff, explorer=explorer)
        elif fam == "mixed":
            c = Candidate(key=f"hotspot-mixed:{m.name}", kind="change",
                          title=f"Split the heavy 'add up and look up' formulas in {m.name} ({_pl(n, 'formula')})",
                          why=(f"A formula that adds values up (SUM) and looks a value up (LOOKUP or SELECT) in the same step makes Anaplan do both jobs for every cell at once; "
                               f"Anaplan's own guidance is to do them in two line items, one that adds up and one that looks up from the result. "
                               f"In {m.name} this applies to {_named(first, m)}{others}: together {eff:.1f}% of the model's measured calculation effort."),
                          steps=[f"In a development copy, split {_named(first, m)} into two line items: one that adds up, one that looks up from it.",
                                 "Compare the results with the original, cell for cell, and read the Calculation Effort column before and after.",
                                 "Keep the split only where the effort share falls; then do the next formula."],
                          done_when="Values match the original cell for cell and the measured effort share has fallen.",
                          role=f"model builder, {m.name}", model=m.name, objects=names, finding_ids=ids, strength="confirmed",
                          footprint_cells=cells, footprint_effort=eff, explorer=explorer)
        else:
            c = Candidate(key=f"hotspot-if:{m.name}", kind="change",
                          title=f"Replace the long chain of IF tests in {_named(first, m)} with a lookup table",
                          why=(f"A formula built as a long chain of 'if this then that' tests checks every branch for every cell, and each new case means editing the formula. "
                               f"The same mapping held as rows in a small table module, read with one lookup, is quicker to calculate and can be maintained without a builder. "
                               f"In {m.name}, {_named(first, m)} carries {first_eff:.1f}% of the model's measured calculation effort."),
                          steps=["In a development copy, load the 'case to value' table (it is written out under Evidence) into a small mapping module keyed by the list the tests refer to.",
                                 f"Replace the chain in {_named(first, m)} with a single lookup on that table; keep the old formula in a note until the check below passes.",
                                 "Export the line item before and after and confirm every cell is equal."],
                          done_when="Every cell is equal before and after, and the table holds every case the chain held.",
                          role=f"model builder, {m.name}", model=m.name, objects=names, finding_ids=ids, strength="confirmed",
                          footprint_cells=cells, footprint_effort=eff, explorer=explorer)
        out.append(c)
    if not out:
        first = top[0][0]
        out.append(Candidate(key=f"hotspot-investigate:{m.name}", kind="investigation",
                             title=f"Look at the five heaviest calculations in {m.name}",
                             why=(f"Anaplan records how much of a model's calculation effort each line item takes. In {m.name}, ten line items take {f['effort_top10_share']}% of it, "
                                  f"led by {_named(first, m)} at {top[0][1]:.1f}%. None of them matches a known pattern this report can name, so this is a place to look, not a change to make: "
                                  f"heavy calculation is often simply the model doing its main job."),
                             steps=[f"With the owner, read the five heaviest formulas (they are listed under Evidence) and note what each one is for and how often it changes.",
                                    "For each, decide: leave as is, or one named change to try (for example the patterns in the other actions).",
                                    "Try at most one change in a development copy, reading Calculation Effort before and after."],
                             done_when="Each of the five has a recorded decision (keep, or one named change to trial) agreed with the owner.",
                             role=f"model builder, {m.name}", model=m.name, objects=[n for n, *_ in top[:5]], finding_ids=[eff_id] if eff_id else [], strength="confirmed",
                             footprint_cells=sum(t[2] for t in top[:5]), footprint_effort=None,   # concentration is not a change footprint; banded by cells only
                             explorer=[mi, _li(first, m)[0], _li(first, m)[1] or None]))
    return out


def _retire_candidate(er, fmap, mi, m) -> Candidate | None:
    """The largest module with no consumer detected: a consumer check, bounded to one module."""
    mods = sorted(_usage_modules(m).values(), key=lambda s: (-s["cells"], s["module"]))
    if not mods:
        return None
    s = mods[0]
    x = next((x for x in er.findings if x.model == m.name and x.area == "usage" and s["module"] in x.objects and "G-UNUSED" in x.rules), None)
    ids = sorted(set(fmap.get((m.name, s["module"]), [])), key=lambda i: int(i[1:]))
    has_actions = bool(m.facts.get("actions"))
    fp = f"{_c(s['cells'])} cells" + (f" and {s['effort']:.1f}% of the model's measured calculation effort" if m.facts["has_effort"] and s["effort"] else "")
    steps = [f"Ask the page builder whether any page, dashboard, saved view or line item subset still uses '{s['module']}'" + (" (no Modules export was supplied, so old-style dashboards could not be checked either)" if not m.model.has_modules_export else "") + ".",
             "Ask whether another model imports from a saved view on it" + ("; it is also loaded by an import, so its data may be kept on purpose" if s.get("imported_into") else "") + ".",
             "Record the decision: keep, or retire. If retire: make the change in a development copy first, keep the original for comparison, check the owner's key outputs over a full cycle, then sign off."]
    notices = []
    if not has_actions:
        notices.append("Whether an export reads this module could not be checked (no Actions export).")
    if s.get("target"):
        notices.append(f"{s['matched_source']} of its {s['calculated']} calculated line items match line items in '{s['target']}'; the rest do not, so it is not a proven duplicate.")
    return Candidate(key=f"retire:{m.name}", kind="investigation",
                     title=f"Find out whether anyone still uses the module '{s['module']}' in {m.name}",
                     why=(f"A module that no formula reads and no export uses may be left over from earlier work, or it may be read only by pages and views, which the exports do not show. "
                          f"Until someone checks, it can neither be removed nor trusted. In {m.name}, no formula outside '{s['module']}' reads any of its {s['line_items']} line items"
                          + (" and no export reads it" if has_actions else "") + f"; it occupies {fp}. That is what it takes up now, not a saving."),
                     steps=steps, done_when="Every question above has a recorded answer and the owner has signed a keep-or-retire decision.",
                     role=f"model owner with a page builder, {m.name}", model=m.name, objects=[s["module"]], finding_ids=ids,
                     strength=(x.strength if x else "partial"), footprint_cells=s["cells"], footprint_effort=(s["effort"] if m.facts["has_effort"] and s["effort"] else None),
                     notices=notices, explorer=[mi, s["module"], None])


def _duplicate_candidate(er, fmap, mi, m) -> Candidate | None:
    if not m.redundancy.exact:
        return None
    g = m.redundancy.exact[0]
    keep, rest = g["items"][0], g["items"][1:]
    x = next((x for x in er.findings if x.model == m.name and x.rules == ["REDUNDANT-EXACT"]), None)
    ids = [x.id] if x else []
    names = [i["key"] for i in g["items"]]
    n = len(rest)
    return Candidate(key=f"duplicate:{m.name}", kind="change",
                     title=f"Remove {n} duplicate {'copy' if n == 1 else 'copies'} of one calculation in {m.name}",
                     why=(f"The same calculation exists more than once under different names, with the same formula and the same dimensions. Two copies can drift apart when one is changed, "
                          f"and each copy takes space and calculation time. In {m.name}, {_named(rest[0]['key'], m)}"
                          + (f" and {n - 1} more" if n > 1 else "") + f" {'is' if n == 1 else 'are'} the same calculation as {_named(keep['key'], m)}; the copies occupy {_c(g['redundant_cells'])} cells "
                          f"and {g['readers_to_repoint']} other formulas read them."),
                     steps=["Ask the owner and page builder whether any copy exists for a reason: a page that shows it under that name, an export column, or different access rights.",
                            f"In a development copy, point the {g['readers_to_repoint']} formulas that read the copies at {_named(keep['key'], m)} instead; keep the copies until the check below passes.",
                            "Compare the outputs that depend on them cell for cell, get sign-off, then remove the copies."],
                     done_when="Everything that read the copies gives the same values from the kept line item, and the copies are gone with no blank page or missing export column.",
                     role=f"model builder, {m.name}", model=m.name, objects=names, finding_ids=ids,
                     strength=(x.strength if x else "confirmed"), footprint_cells=g["redundant_cells"],
                     explorer=[mi, keep["module"], keep["name"]])


def _if_chain_candidate(er, fmap, mi, m) -> Candidate | None:
    xs = [x for x in er.findings if x.model == m.name and x.rules == ["A-IF-COUNT"] and x.title.startswith("IF chain that encodes")]
    if not xs:
        return None
    x = sorted(xs, key=lambda x: (-(x.footprint_effort or 0), x.objects[0]))[0]
    first = x.objects[0]
    return Candidate(key=f"if:{m.name}:{first}", kind="change",
                     title=f"Replace the long chain of IF tests in {_named(first, m)} with a lookup table",
                     why=("A formula built as a long chain of 'if this then that' tests checks every branch for every cell, and each new case means editing the formula. "
                          "The same mapping held as rows in a small table module, read with one lookup, is easier to maintain without a builder"
                          + (f" and, in {m.name}, the line item carries {x.footprint_effort:.1f}% of the model's measured calculation effort" if x.footprint_effort else "") + "."),
                     steps=["In a development copy, load the 'case to value' table (written out under Evidence) into a small mapping module keyed by the list the tests refer to.",
                            f"Replace the chain in {_named(first, m)} with a single lookup on that table; keep the old formula in a note until the check below passes.",
                            "Export the line item before and after and confirm every cell is equal."],
                     done_when="Every cell is equal before and after, and the table holds every case the chain held.",
                     role=f"model builder, {m.name}", model=m.name, objects=[first], finding_ids=[x.id], strength=x.strength,
                     footprint_effort=x.footprint_effort, explorer=[mi, _li(first, m)[0], _li(first, m)[1] or None])


def candidates(er) -> list[Candidate]:
    fmap = _fmap(er)
    out: list[Candidate] = []
    for mi, m in enumerate(er.models):
        out += _hotspot_candidates(er, fmap, mi, m)
        for gen in (_retire_candidate, _duplicate_candidate, _if_chain_candidate):
            c = gen(er, fmap, mi, m)
            if c:
                out.append(c)
    keys = {(c.model, tuple(c.objects)) for c in out if c.key.startswith("hotspot-if:")}
    out = [c for c in out if not (c.key.startswith("if:") and (c.model, tuple(c.objects)) in keys)]
    by_model = {m.name: m for m in er.models}
    for c in out:
        m = by_model[c.model]
        usage = _usage_modules(m)
        if c.key.startswith("retire:"):
            mod = c.objects[0]
            c.finding_ids = sorted(set(c.finding_ids) | {x.id for x in er.findings if x.model == c.model and mod in x.objects}, key=lambda i: int(i[1:]))
            continue
        mods = {_li(o, m)[0] for o in c.objects if _li(o, m)[1]}
        hit = sorted(mods & set(usage))
        if hit:
            r = next((r for r in out if r.key == f"retire:{c.model}" and r.objects[0] in hit), None)
            if r:
                c.depends_on.append(r.key)
                c.notices.append(f"The module '{hit[0]}'{f' and {len(hit) - 1} more' if len(hit) > 1 else ''} may no longer be used: do that check first, since a retired module needs no tuning.")
            else:
                c.notices.append(f"{_pl(len(hit), 'module')} named here {'has' if len(hit) == 1 else 'have'} no reader the exports can see: confirm {'it is' if len(hit) == 1 else 'they are'} still needed before tuning.")
        c.notices += [n for n in _coverage_notices(m) if n not in c.notices][:2]
    for c in out:
        c.rank_reason = _reason(c)
    return sorted(out, key=rank_key)


WORTH = [
    "A change is worth doing when its evidence is not merely inferred, its scope is bounded, and its observed footprint is at least medium (1% of its model's measured effort, or 1M cells).",
    "An investigation is worth doing only when the footprint is high (5% of its model's measured effort, or 50M cells): asking someone to check a small module is not a good use of their time.",
    "A prerequisite (for example a consumer check on a module that a change would tune) is included whenever the action that needs it is.",
]


def worth_doing(c: Candidate) -> bool:
    if c.strength == "inferred" or not c.bounded:
        return False
    b = band(c)
    return b <= 1 if c.kind == "change" else b == 0


def select(er, limit: int | None = None) -> dict:
    """Every candidate that is worth doing, in rank order; `limit` caps the count only when given.
    A prerequisite is placed before the action that needs it."""
    ranked = candidates(er)
    by_key = {c.key: c for c in ranked}
    chosen: list[Candidate] = []
    for c in ranked:
        if limit is not None and len(chosen) >= limit:
            break
        if not worth_doing(c):
            continue
        for d in [by_key[d] for d in c.depends_on if d in by_key and by_key[d] not in chosen]:
            if limit is None or len(chosen) < limit:
                chosen.append(d)
        if c not in chosen and (limit is None or len(chosen) < limit) and all(by_key[d] in chosen for d in c.depends_on if d in by_key):
            chosen.append(c)
    for i, c in enumerate(chosen, 1):
        c.rank_reason = f"#{i}: " + c.rank_reason
    nothing = None
    if not chosen:
        checks = []
        if not any(m.facts["has_effort"] for m in er.models):
            checks.append("export the Line Items grid with the Calculation Effort column so the heaviest calculations can be matched to known patterns")
        if any(not m.facts.get("actions") for m in er.models):
            checks.append("supply the Actions export for " + ", ".join(m.name for m in er.models if not m.facts.get("actions")))
        if not checks:
            checks.append("no finding met the bar for a bounded, evidenced action worth doing; the catalogue under Evidence lists everything that was observed")
        nothing = {"message": "No action is suggested from these exports.", "next_check": "; ".join(checks)}
    return {"actions": [c.to_dict() for c in chosen], "candidates": [c.to_dict() for c in ranked], "ranking": RANKING, "worth": WORTH, "limit": limit,
            "considered": len(ranked), "none": nothing}
