"""Change-impact data: the dependency graph of every model in a form the report can
embed and query offline, plus the reach queries the Change impact view and the
change-review download rest on.

Identities are composite and stable: a node is (model index, module, line item name),
numbered once per report; display names are never split on dots (real names carry
punctuation and repeat across modules and models).

Relationship types, each kept apart so a reader knows what a link rests on:
  ref        line item A reads line item B (parsed formula reference, checked against
             Referenced By where the column exists). Line-item level. Evidenced.
  import     an import action writes a module (target). Module level: an action touching
             a module says nothing about which line items it fills.
  export     an export action reads a module (source). Module level.
  process    an action is a step of a process. Membership, not data flow.
  feed       model X feeds model Y, inferred from the words after "from" in import
             action names. Model level. Inferred; never expanded into line-item lineage.

Where a model has no Actions export its action links are "not assessed" (None), never
an empty list; a supplied Actions export with no matching action gives an empty list.

Distance is the shortest number of known `ref` links from the selection; direct is 1.
The selection is excluded from its own totals even when a cycle returns to it.
"""
from __future__ import annotations
from collections import deque, defaultdict


def graph_data(er) -> dict:
    """Everything the explorer needs, compact and JSON-safe.

    nodes:   [id, model_index, module, name, cells, effort|null, calculated(0/1)]
    edges:   [reader_id, source_id]   reader uses source (ref)
    modules: per model: {module: [node ids]}  (derived client-side from nodes; kept here for size accounting only)
    actions: per model: null when not assessed, else [{name, kind, module, direction, processes}]
    feeds:   er.edges as {from, to, actions, targets, basis}
    coverage: per model: {agreement, anaplan_only, unparsed, has_actions, has_effort, referenced_by}
    """
    nodes, edges, ids = [], [], {}
    actions, coverage, models = [], [], []
    for mi, m in enumerate(er.models):
        models.append(m.name)
        for k, li in m.model.line_items.items():
            if li.is_header:
                continue
            nid = len(nodes)
            ids[(mi, k)] = nid
            nodes.append([nid, mi, k[0], k[1], li.cell_count, (li.calc_effort if m.facts["has_effort"] else None), 1 if li.formula else 0])
        for a, bs in m.graph.edges.items():
            if (mi, a) not in ids:
                continue
            for b in bs:
                if (mi, b) in ids:
                    edges.append([ids[(mi, a)], ids[(mi, b)]])
        if m.facts.get("actions"):
            acts = []
            steps = defaultdict(list)
            for p in m.actions.processes.values():
                for s in p.steps:
                    steps[s].append(p.name)
            for a in m.actions.actions.values():
                if a.kind not in ("import", "export"):
                    continue
                procs = sorted(set(a.processes) | set(steps.get(a.name, [])))
                acts.append({"name": a.name, "kind": a.kind, "module": a.target if a.target in m.model.modules else "",
                             "target": a.target, "direction": "writes" if a.kind == "import" else "reads", "processes": procs,
                             "last_run": a.last_run[:10] if a.last_run else ""})
            actions.append(acts)
        else:
            actions.append(None)
        rc = m.facts["referenced_by_check"]
        coverage.append({"agreement": rc["agreement"], "anaplan_only": rc["anaplan_only"], "unparsed": m.facts["parse_errors"],
                         "has_actions": bool(m.facts.get("actions")), "has_effort": m.facts["has_effort"],
                         "referenced_by": rc["agreement"] is not None})
    feeds = [{"from": e["from"], "to": e["to"], "actions": e["actions"], "targets": e["targets"], "basis": e["basis"]} for e in er.edges]
    return {"models": models, "nodes": nodes, "edges": edges, "actions": actions, "feeds": feeds, "coverage": coverage,
            "edge_types": {"ref": "line item reads line item (parsed formula reference; evidenced)",
                           "import": "import action writes a module (module level; from the Actions export)",
                           "export": "export action reads a module (module level; from the Actions export)",
                           "process": "action is a step of a process (membership, not data flow)",
                           "feed": "model feeds model (inferred from import action names; never line-item lineage)"}}


def node_index(gd: dict) -> dict:
    """(model_index, module, name) -> node id."""
    return {(n[1], n[2], n[3]): n[0] for n in gd["nodes"]}


def adjacency(gd: dict, direction: str) -> dict[int, list[int]]:
    """downstream: source -> readers (what depends on this). upstream: reader -> sources (what this depends on)."""
    adj = defaultdict(list)
    for r, s in gd["edges"]:
        if direction == "downstream":
            adj[s].append(r)
        else:
            adj[r].append(s)
    return adj


def reach(adj: dict, start: int, depth: int | None = None) -> tuple[dict[int, int], dict[int, int]]:
    """Breadth-first closure. Returns (distance, parent): shortest link count from start, and one predecessor
    per reached node so a shortest path can be shown. Iterative; cycles and diamonds visit each node once;
    the start is not in the result even when a cycle returns to it."""
    dist = {start: 0}; parent = {}
    q = deque([start])
    while q:
        n = q.popleft(); d = dist[n]
        if depth is not None and d >= depth:
            continue
        for x in adj.get(n, ()):
            if x not in dist:
                dist[x] = d + 1; parent[x] = n; q.append(x)
    dist.pop(start, None)
    return dist, parent


def path(parent: dict, start: int, node: int) -> list[int]:
    out = [node]
    while out[-1] != start and out[-1] in parent:
        out.append(parent[out[-1]])
    return list(reversed(out))


def summarise(gd: dict, start: int, direction: str, depth: int | None = None) -> dict:
    """The figures the explorer shows and the change review records, computed the same way in Python (tests,
    reconciliation with Graph.impact) and in the page script."""
    adj = adjacency(gd, direction)
    dist, parent = reach(adj, start, depth)
    nodes = {n[0]: n for n in gd["nodes"]}
    mi = nodes[start][1]
    mods = defaultdict(list)
    for nid, d in dist.items():
        mods[nodes[nid][2]].append((nid, d))
    by_dist = defaultdict(int)
    for d in dist.values():
        by_dist[d] += 1
    acts = gd["actions"][mi]
    if acts is None:
        act_links = None
    else:
        act_links = [a for a in acts if a["module"] in mods or a["module"] == nodes[start][2]]
    feeds = [f for f in gd["feeds"] if f["from"] == gd["models"][mi]] if direction == "downstream" else [f for f in gd["feeds"] if f["to"] == gd["models"][mi]]
    return {"selection": {"id": start, "model": gd["models"][mi], "module": nodes[start][2], "name": nodes[start][3]},
            "direction": direction, "depth": depth,
            "direct": sum(1 for d in dist.values() if d == 1), "indirect": sum(1 for d in dist.values() if d > 1), "total": len(dist),
            "modules": len(mods), "max_distance": max(dist.values(), default=0), "by_distance": dict(sorted(by_dist.items())),
            "footprint_cells": sum(nodes[n][4] for n in dist), "actions": act_links, "feeds_inferred": feeds,
            "coverage": gd["coverage"][mi], "distance": dist, "parent": parent}
