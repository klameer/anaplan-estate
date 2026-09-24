"""Usage counts for the hosted service, without personal data.

What is recorded per report request: a minute-resolution timestamp, the outcome (ok, or the
refusal reason), how many models and line items, an upload-size bucket, and the duration.
Never the address, a name, a file name, a formula or any content.

Distinct visitors per day are counted with a keyed hash of the client address. The key is
random, lives only in this process's memory and is replaced every day; it is never written
anywhere, so the hashes in memory cannot be traced back and nothing about a person is stored.
Only the count survives the day.

Where it goes: one structured log line per event (no content), an in-memory summary for
today, and, when ESTATE_STATS_DIR points at a writable folder (a Railway volume), one JSON
line per day appended to usage.jsonl when the day rolls over and on shutdown. GET /stats
shows the summaries when ESTATE_STATS_TOKEN is set and supplied; otherwise the route is off.
"""
from __future__ import annotations
import hmac, hashlib, json, os, secrets, threading, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STATS_DIR = os.environ.get("ESTATE_STATS_DIR", "")
STATS_TOKEN = os.environ.get("ESTATE_STATS_TOKEN", "")
_lock = threading.Lock()


def _day(ts: float | None = None) -> str:
    return datetime.fromtimestamp(ts or time.time(), timezone.utc).strftime("%Y-%m-%d")


def _size_bucket(n_bytes: int) -> str:
    for lim, lab in ((256 * 1024, "<256KB"), (2 * 1024 * 1024, "<2MB"), (10 * 1024 * 1024, "<10MB"), (40 * 1024 * 1024, "<40MB")):
        if n_bytes < lim:
            return lab
    return ">=40MB"


class Usage:
    def __init__(self):
        self.day = _day()
        self.key = secrets.token_bytes(32)
        self.visitors: set[str] = set()
        self.events = Counter()          # outcome -> count
        self.models = 0; self.line_items = 0; self.durations: list[int] = []; self.sizes = Counter(); self.page_views = 0

    # -- rolling over --
    def _roll(self):
        today = _day()
        if today != self.day:
            self.flush()
            self.day = today; self.key = secrets.token_bytes(32); self.visitors = set()
            self.events = Counter(); self.models = 0; self.line_items = 0; self.durations = []; self.sizes = Counter(); self.page_views = 0

    def summary(self) -> dict:
        d = sorted(self.durations)
        return {"day": self.day, "page_views": self.page_views, "distinct_visitors": len(self.visitors), "reports": dict(self.events),
                "reports_ok": self.events.get("ok", 0), "models": self.models, "line_items": self.line_items,
                "duration_ms_p50": d[len(d) // 2] if d else None, "duration_ms_max": d[-1] if d else None, "upload_sizes": dict(self.sizes)}

    def flush(self):
        if not STATS_DIR:
            return
        try:
            p = Path(STATS_DIR); p.mkdir(parents=True, exist_ok=True)
            with open(p / "usage.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(self.summary()) + "\n")
        except OSError:
            pass

    # -- recording --
    def visit(self, client: str):
        with _lock:
            self._roll()
            self.page_views += 1
            self.visitors.add(hmac.new(self.key, client.encode(), hashlib.sha256).hexdigest()[:16])

    def report(self, client: str, outcome: str, models: int = 0, line_items: int = 0, upload_bytes: int = 0, duration_ms: int = 0):
        with _lock:
            self._roll()
            self.visitors.add(hmac.new(self.key, client.encode(), hashlib.sha256).hexdigest()[:16])
            self.events[outcome] += 1
            if outcome == "ok":
                self.models += models; self.line_items += line_items; self.durations.append(duration_ms)
            self.sizes[_size_bucket(upload_bytes)] += 1
        print(json.dumps({"usage": "report", "minute": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"), "outcome": outcome, "models": models,
                          "line_items": line_items, "upload": _size_bucket(upload_bytes), "duration_ms": duration_ms}), flush=True)

    def history(self) -> list[dict]:
        if not STATS_DIR or not (Path(STATS_DIR) / "usage.jsonl").exists():
            return []
        out = []
        for line in (Path(STATS_DIR) / "usage.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
        return out[-90:]


usage = Usage()
