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
        mod = first.split(".", 1)[0] if "." in first else first
        if fam == "text":
            n = len(names)
            c = Candidate(key=f"hotspot-text:{m.name}", kind="change",
                          title=(f"Move {n} text formulas that run on every cell into a system module in {m.name}" if n != 1
                                 else f"Move the text formula {first} into a system module in {m.name}"),
                          why=(f"{first}" + (f" and {n - 1} similar line item{'s' if n > 2 else ''}" if n > 1 else "") +
                               f" {'build' if n > 1 else 'builds'} a text or per-item value on every cell of a multi-dimensional module ({_c(cells)} cells) and {'carry' if n > 1 else 'carries'} {eff:.1f}% of {m.name}'s measured effort; "
                               "in a module dimensioned only by the list the value varies by, each is calculated once per list item and read from there."),
                          steps=[f"Read {first} ({first_eff:.1f}%): name the list its value varies by (often Time or one list).",
                                 "In a development copy, compute it in a SYS module on that list and repoint the readers; keep the original until reconciled.",
                                 "Record Calculation Effort before and after."],
                          done_when="Readers reconcile cell for cell and the measured effort share falls.",
                          role=f"model builder, {m.name}", model=m.name, objects=names, finding_ids=ids, strength="confirmed",
                          footprint_cells=cells, footprint_effort=eff, explorer=[mi, mod, first.split(".", 1)[1] if "." in first else None])
        elif fam == "mixed":
            c = Candidate(key=f"hotspot-mixed:{m.name}", kind="change",
                          title=f"Split SUM from LOOKUP or SELECT in {first}" + (f" and {len(names) - 1} more" if len(names) > 1 else ""),
                          why=f"{_pl(len(names), 'formula')} carrying {eff:.1f}% of {m.name}'s measured effort combine SUM with LOOKUP or SELECT, which Anaplan's documentation advises against for calculation time.",
                          steps=[f"In a development copy, split {first} into one line item that aggregates and one that looks up or selects from it.",
                                 "Reconcile cell for cell against the original; record Calculation Effort before and after.",
                                 "Keep the split only where the share falls."],
                          done_when="Values reconcile cell for cell and the measured effort share falls.",
                          role=f"model builder, {m.name}", model=m.name, objects=names, finding_ids=ids, strength="confirmed",
                          footprint_cells=cells, footprint_effort=eff, explorer=[mi, mod, first.split(".", 1)[1] if "." in first else None])
        else:
            c = Candidate(key=f"hotspot-if:{m.name}", kind="change",
                          title=f"Replace the IF chain in {first} with a mapping module and LOOKUP",
                          why=f"{first} carries {first_eff:.1f}% of {m.name}'s measured effort and evaluates every IF branch for every cell; a mapping module makes each case a row, not a formula edit.",
                          steps=["In a development copy, load the branch-to-value table (in the evidence) into a mapping module on the list the branches test.",
                                 f"Replace the chain in {first} with one LOOKUP; keep the original formula in a note until reconciled.",
                                 "Export the line item before and after; every cell equal."],
                          done_when="Every cell is equal before and after and the mapping module holds every case the chain held.",
                          role=f"model builder, {m.name}", model=m.name, objects=names, finding_ids=ids, strength="confirmed",
                          footprint_cells=cells, footprint_effort=eff, explorer=[mi, mod, first.split(".", 1)[1] if "." in first else None])
        out.append(c)
    if not out:
        first = top[0][0]
        out.append(Candidate(key=f"hotspot-investigate:{m.name}", kind="investigation",
                             title=f"Read the five largest calculation hotspots in {m.name}",
                             why=f"Ten line items carry {f['effort_top10_share']}% of {m.name}'s measured effort and none matches a rule finding, so concentration is the only evidence: a place to look, not a change to make.",
                             steps=[f"Read the five largest with the owner, led by {first} ({top[0][1]:.1f}%): what each computes and how often it changes.",
                                    "Note where a documented pattern applies (SUM with LOOKUP, text per cell, IF chains) or the effort is the model's main job.",
                                    "Choose at most one to trial in a development copy, with Calculation Effort read before and after."],
                             done_when="Each of the five has a recorded reading (keep, or one named change to trial) agreed with the owner.",
                             role=f"model builder, {m.name}", model=m.name, objects=[n for n, *_ in top[:5]], finding_ids=[eff_id] if eff_id else [], strength="confirmed",
                             footprint_cells=sum(t[2] for t in top[:5]), footprint_effort=None,   # concentration is not a change footprint; banded by cells only
                             explorer=[mi, first.split(".", 1)[0], first.split(".", 1)[1] if "." in first else None]))
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
    fp = f"{_c(s['cells'])} cells" + (f" and {s['effort']:.1f}% of {m.name}'s measured effort" if m.facts["has_effort"] and s["effort"] else "")
    steps = [f"Ask the page builder which pages, saved views and line item subsets use {s['module']}" + (" (no Modules export: classic dashboards unchecked too)" if not m.model.has_modules_export else "") + ".",
             "Check whether another model imports from a saved view on it" + ("; it is an import target, so its data may be kept on purpose" if s.get("imported_into") else "") + ".",
             "Record keep or retire. If retire: change a development copy with the original intact, reconcile the owner's named outputs over a cycle, sign off."]
    notices = []
    if not has_actions:
        notices.append("Export-action usage not assessed (no Actions export).")
    if s.get("target"):
        notices.append(f"{s['matched_source']} of {s['calculated']} calculated line items match {s['target']}; the rest do not, so it is not a proven duplicate.")
    return Candidate(key=f"retire:{m.name}", kind="investigation",
                     title=f"Check for consumers of {s['module']} in {m.name} before keeping or retiring it",
                     why=f"No formula outside it reads its {s['line_items']} line items" + (" and no export action reads it" if has_actions else "") + f"; it holds {fp}: an observed footprint, not a saving.",
                     steps=steps, done_when="Every consumer check has a recorded answer and the owner has signed a keep-or-retire decision.",
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
    return Candidate(key=f"duplicate:{m.name}", kind="change",
                     title=f"Consolidate {len(rest)} {'copy' if len(rest) == 1 else 'copies'} of {keep['key']} in {m.name}",
                     why=f"{rest[0]['key']}{f' and {len(rest) - 1} more' if len(rest) > 1 else ''} {'has' if len(rest) == 1 else 'have'} the same resolved formula and context as {keep['key']}; the copies hold {_c(g['redundant_cells'])} cells and {g['readers_to_repoint']} formulas read them.",
                     steps=["Confirm with the owner and page builder that no copy serves a separate page, export column or access boundary.",
                            f"In a development copy, repoint the {g['readers_to_repoint']} readers to {keep['key']}; keep the copies until reconciled.",
                            "Reconcile the outputs that read them cell for cell, sign off, then remove the copies."],
                     done_when="Readers reconcile cell for cell and the copies are removed with no blank page or missing export column.",
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
                     title=f"Replace the IF chain in {first} with a mapping module and LOOKUP",
                     why="The chain encodes a lookup table (the evidence lists every branch), so each new case is a formula edit; a mapping module makes it a row"
                         + (f", and the line item carries {x.footprint_effort:.1f}% of {m.name}'s measured effort" if x.footprint_effort else "") + ".",
                     steps=["In a development copy, load the branch-to-value table (in the evidence) into a mapping module on the list the branches test.",
                            f"Replace the chain in {first} with one LOOKUP; keep the original formula in a note until reconciled.",
                            "Export the line item before and after; every cell equal."],
                     done_when="Every cell is equal before and after and the mapping module holds every case the chain held.",
                     role=f"model builder, {m.name}", model=m.name, objects=[first], finding_ids=[x.id], strength=x.strength,
                     footprint_effort=x.footprint_effort, explorer=[mi, first.split(".", 1)[0], first.split(".", 1)[1] if "." in first else None])


def candidates(er) -> list[Candidate]:
    fmap = _fmap(er)
    out: list[Candidate] = []
    for mi, m in enumerate(er.models):
        out += _hotspot_candidates(er, fmap, mi, m)
        for gen in (_retire_candidate, _duplicate_candidate, _if_chain_candidate):
            c = gen(er, fmap, mi, m)
            if c:
                out.append(c)
    # de-duplicate the IF-chain candidate when the hotspot join already carries the same object
    keys = {(c.model, tuple(c.objects)) for c in out if c.key.startswith("hotspot-if:")}
    out = [c for c in out if not (c.key.startswith("if:") and (c.model, tuple(c.objects)) in keys)]
    # merge overlapping findings and mark dependencies on the consumer check
    by_model = {m.name: m for m in er.models}
    for c in out:
        m = by_model[c.model]
        usage = _usage_modules(m)
        if c.key.startswith("retire:"):
            mod = c.objects[0]
            c.finding_ids = sorted(set(c.finding_ids) | {x.id for x in er.findings if x.model == c.model and mod in x.objects}, key=lambda i: int(i[1:]))
            continue
        mods = {o.split(".", 1)[0] for o in c.objects if "." in o}
        hit = sorted(mods & set(usage))
        if hit:
            r = next((r for r in out if r.key == f"retire:{c.model}" and r.objects[0] in hit), None)
            if r:
                c.depends_on.append(r.key)
                c.notices.append(f"{hit[0]}{f' and {len(hit) - 1} more' if len(hit) > 1 else ''} has no consumer detected: complete that consumer check first.")
            else:
                c.notices.append(f"{_pl(len(hit), 'module')} named here {'has' if len(hit) == 1 else 'have'} no consumer detected: confirm {'it is' if len(hit) == 1 else 'they are'} needed before optimising.")
        c.notices += [n for n in _coverage_notices(m) if n not in c.notices][:2]
    for c in out:
        c.rank_reason = _reason(c)
    return sorted(out, key=rank_key)


def select(er, limit: int = 5) -> dict:
    """At most `limit` cards, ordered; a dependency selected alongside its dependant is placed first."""
    ranked = candidates(er)
    by_key = {c.key: c for c in ranked}
    chosen: list[Candidate] = []
    for c in ranked:
        if len(chosen) >= limit:
            break
        deps = [by_key[d] for d in c.depends_on if d in by_key and by_key[d] not in chosen]
        for d in deps:                       # a prerequisite is placed before the action that needs it
            if len(chosen) < limit:
                chosen.append(d)
        if c not in chosen and len(chosen) < limit and all(by_key[d] in chosen for d in c.depends_on if d in by_key):
            chosen.append(c)
    for i, c in enumerate(chosen, 1):
        c.rank_reason = f"#{i}: " + c.rank_reason
    nothing = None
    if not chosen:
        checks = []
        if not any(m.facts["has_effort"] for m in er.models):
            checks.append("export the Line Items grid with the Calculation Effort column so hotspots can be joined to findings")
        if any(not m.facts.get("actions") for m in er.models):
            checks.append("supply the Actions export for " + ", ".join(m.name for m in er.models if not m.facts.get("actions")))
        if not checks:
            checks.append("no finding met the bar for a bounded, evidenced action; the catalogue in Evidence lists what was observed")
        nothing = {"message": "No action is suggested from these exports.", "next_check": "; ".join(checks)}
    return {"actions": [c.to_dict() for c in chosen], "candidates": [c.to_dict() for c in ranked], "ranking": RANKING, "limit": limit, "none": nothing}
