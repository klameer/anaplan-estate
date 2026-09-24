"""Load an Anaplan model's structure from the standard exports.

Inputs (both from Anaplan's grid exports, CSV):
  line_items.csv  Modules > Line Items grid: Format, Formula, Summary,
                  Applies To, Time Scale, Time Range, Versions, ...,
                  Referenced By, Module Name
  modules.csv     Modules grid: Functional Area, Applies To, ..., Line Items

Only the columns needed for structure are read. Cell counts and access
drivers are kept as strings on the line item for later reports.
"""
from __future__ import annotations
import csv, json, re
from dataclasses import dataclass, field
from pathlib import Path

csv.field_size_limit(10**8)

# Columns the analyses rely on, and what is lost without each. "Formula" is required; the rest degrade with a notice.
COLUMN_ROLES = {
    "Formula": "required: no dependency graph, no rules, no findings",
    "Format": "line items without a formula cannot be told apart from section headers by format; all rows are kept",
    "Cell Count": "cell footprints unavailable (shown as unavailable, never as zero)",
    "Calculation Effort": "no effort figures for this model",
    "Referenced By": "dependency completeness not checkable against Anaplan's own column",
    "Applies To": "dimensions unknown; duplicate and context comparisons limited",
    "Summary": "summary-method checks skipped",
    "Time Scale": "time-scale context unknown",
    "Module Name": "modules taken from section header rows",
}
DELIMITERS = ",;\t|"


class InputError(SystemExit):
    pass


def open_csv(path: str | Path):
    """Open an Anaplan grid export whatever the delimiter and encoding: sniff among , ; tab |, try UTF-8 (with BOM) then cp1252.
    Returns (rows as DictReader list, fieldnames, delimiter, encoding)."""
    raw = Path(path).read_bytes()
    text = None; enc = "utf-8-sig"
    for e in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(e); enc = e; break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("utf-8", "replace")
    head = text[:20000]
    try:
        delim = csv.Sniffer().sniff(head, delimiters=DELIMITERS).delimiter
    except csv.Error:
        first = head.splitlines()[0] if head else ""
        delim = max(DELIMITERS, key=lambda d: first.count(d)) if first else ","
    r = csv.DictReader(text.splitlines(True), delimiter=delim)
    rows = list(r)
    return rows, list(r.fieldnames or []), delim, enc


@dataclass
class LineItem:
    module: str
    name: str
    formula: str = ""
    format_type: str = ""
    applies_to: tuple[str, ...] = ()
    time_scale: str = ""
    versions: str = ""
    time_range: str = ""
    formula_scope: str = ""
    format_raw: str = ""
    summary: str = ""
    cell_count: int = 0
    referenced_by_raw: str = ""
    notes: str = ""
    calc_effort: float = 0.0  # Calculation Effort column, percent of model total (0 when absent)
    is_header: bool = False   # "▼▼▼ SECTION ▼▼▼" style rows and other no-format rows

    @property
    def key(self) -> tuple[str, str]:
        return (self.module, self.name)

    def __str__(self):
        return f"{self.module}.{self.name}"


@dataclass
class Module:
    name: str
    functional_area: str = ""
    applies_to: tuple[str, ...] = ()
    time_scale: str = ""
    versions: str = ""
    cell_count: int = 0
    line_items: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class Model:
    name: str = ""
    modules: dict[str, Module] = field(default_factory=dict)
    line_items: dict[tuple[str, str], LineItem] = field(default_factory=dict)
    # dimension names seen in Applies To (lists, subsets, pseudo-lists)
    dimensions: set[str] = field(default_factory=set)
    has_modules_export: bool = False
    columns: set[str] = field(default_factory=set)         # column headers found in the Line Items export
    missing_columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)      # input problems a reader must see (locale, delimiter, dropped rows)
    delimiter: str = ","
    encoding: str = "utf-8-sig"

    def has(self, col: str) -> bool:
        return col in self.columns

    def by_module(self, module: str) -> list[LineItem]:
        return [li for li in self.line_items.values() if li.module == module]

    def line_item_names(self) -> dict[str, list[LineItem]]:
        """name -> all line items with that name, across modules."""
        out: dict[str, list[LineItem]] = {}
        for li in self.line_items.values():
            out.setdefault(li.name, []).append(li)
        return out


def _split_applies(s: str) -> tuple[str, ...]:
    s = (s or "").strip()
    if not s or s == "-":
        return ()
    # Applies To is a comma-separated list of dimension names; names may be quoted
    parts = []
    for p in s.split(","):
        p = p.strip().strip("'")
        if p:
            parts.append(p)
    return tuple(parts)


def _fmt(s: str) -> str:
    if not s:
        return ""
    try:
        return json.loads(s).get("dataType", "")
    except Exception:
        return s[:20]


def _summary(s: str) -> str:
    """Summary column is JSON in newer exports ({"summaryMethod":"SUM",...}); reduce to 'SUM' / 'NONE' / 'SUM;time=NONE'."""
    if not s:
        return ""
    try:
        j = json.loads(s)
    except Exception:
        return s[:40]
    m, t = j.get("summaryMethod", ""), j.get("timeSummaryMethod", "")
    return m if j.get("timeSummarySameAsMainSummary", True) or t == m else f"{m};time={t}"


_NUM_DOT_THOUSANDS = re.compile(r"^-?\d{1,3}(\.\d{3})+$")
_NUM_COMMA_THOUSANDS = re.compile(r"^-?\d{1,3}(,\d{3})+$")


def _pct(s: str) -> float:
    """Percent as exported. Accepts 16.04, 16.04%, 16,04 (comma decimal), 1 234,5. Never treats a comma as a thousands
    separator here: effort is a share, so a value above 100 is an input problem, flagged by the loader."""
    t = str(s).strip().rstrip("%").replace(" ", "").replace("\u00a0", "")
    if not t:
        return 0.0
    if "," in t and "." not in t:
        t = t.replace(",", ".")
    elif "," in t and "." in t:
        t = t.replace(",", "") if t.rfind(".") > t.rfind(",") else t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


def _int(s: str) -> int:
    """Integer as exported. Accepts 5,017,824 and 5.017.824 and 5 017 824."""
    t = str(s).strip().replace(" ", "").replace("\u00a0", "")
    if not t:
        return 0
    if _NUM_DOT_THOUSANDS.match(t):
        t = t.replace(".", "")
    elif _NUM_COMMA_THOUSANDS.match(t):
        t = t.replace(",", "")
    else:
        t = t.replace(",", "")
    try:
        return int(float(t))
    except ValueError:
        return 0


def load_line_items(path: str | Path, model: Model) -> None:
    rows, fields, delim, enc = open_csv(path)
    model.columns = set(fields); model.delimiter = delim; model.encoding = enc
    model.missing_columns = [c for c in COLUMN_ROLES if c not in model.columns]
    if not fields:
        raise InputError(f"{path}: no header row found")
    if "Formula" not in model.columns:
        raise InputError(f"{path}: no 'Formula' column. Found columns: {', '.join(c or '(blank)' for c in fields[:12])}. "
                         "Export the Line Items grid from Model Settings > Modules > Line Items with every column; localised headers are not recognised.")
    if delim != ",":
        model.warnings.append(f"Line Items export read with '{'tab' if delim == chr(9) else delim}' as the delimiter.")
    if enc != "utf-8-sig":
        model.warnings.append(f"Line Items export decoded as {enc}, not UTF-8; check names with accents.")
    has_fmt, has_mod = "Format" in model.columns, "Module Name" in model.columns
    first = fields[0]
    current_module = None
    effort_over = 0
    for row in rows:
        name = row.get(first, "") or ""
        mod_col = row.get("Module Name", "") or ""
        formula = (row.get("Formula") or "").strip()
        fmt = row.get("Format", "") or ""
        # a module header row carries the module's own name in column 0 and nothing else
        if has_fmt:
            is_hdr_row = not fmt and not formula and not mod_col
        elif has_mod:
            is_hdr_row = not mod_col and not formula
        else:
            is_hdr_row = not formula and not (row.get("Applies To") or row.get("Cell Count") or row.get("Time Scale"))
        if is_hdr_row:
            current_module = name
            model.modules.setdefault(name, Module(name=name))
            continue
        module = mod_col or current_module or ""
        model.modules.setdefault(module, Module(name=module))
        eff = _pct(row.get("Calculation Effort", ""))
        if eff > 100:
            effort_over += 1
        li = LineItem(
            module=module, name=name, formula=formula, format_type=_fmt(fmt),
            applies_to=_split_applies(row.get("Applies To", "")),
            time_scale=row.get("Time Scale", "") or "", versions=row.get("Versions", "") or "",
            time_range=row.get("Time Range", "") or "", formula_scope=row.get("Formula Scope", "") or "", format_raw=fmt or "",
            summary=_summary(row.get("Summary") or ""), cell_count=_int(row.get("Cell Count", "0")),
            referenced_by_raw=row.get("Referenced By", "") or "", notes=row.get("Notes", "") or "",
            calc_effort=eff,
            is_header=(has_fmt and not fmt and not formula),
        )
        model.line_items[li.key] = li
        model.modules[module].line_items.append(name)
        model.dimensions.update(li.applies_to)
    if effort_over:
        model.warnings.append(f"{effort_over} Calculation Effort values exceed 100%: the column was not read as a percentage (check the number format); effort figures for this model are unreliable.")
    if not model.line_items:
        model.warnings.append("No line items were read from the Line Items export.")


def load_modules(path: str | Path, model: Model) -> None:
    model.has_modules_export = True
    rows, fields, delim, enc = open_csv(path)
    if fields:
        first = fields[0]
        for row in rows:
            name = row.get(first, "") or ""
            m = model.modules.setdefault(name, Module(name=name))
            m.functional_area = row.get("Functional Area", "") or ""
            m.applies_to = _split_applies(row.get("Applies To", ""))
            m.time_scale = row.get("Time Scale", "") or ""
            m.versions = row.get("Versions", "") or ""
            m.cell_count = _int(row.get("Cell Count", "0"))
            m.notes = row.get("Notes", "") or ""
            model.dimensions.update(m.applies_to)


def load_model(line_items_csv: str | Path, modules_csv: str | Path | None = None, name: str = "") -> Model:
    model = Model(name=name)
    load_line_items(line_items_csv, model)
    if modules_csv:
        load_modules(modules_csv, model)
    return model
