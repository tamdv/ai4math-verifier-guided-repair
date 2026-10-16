"""Spending control for paid LLM calls: hard budget caps, a persistent ledger, and a
response cache so repeated prompts are never paid twice.

- Ledger (`results/cost_ledger.jsonl`): one line per paid call, survives restarts;
  the monthly total is recomputed from it at startup.
- Caps (`configs/budget.yaml`): monthly cap and per-run cap in USD. Before each
  call the *worst-case* cost (prompt estimate + max output tokens) is checked;
  if it would cross a cap the call is refused with `BudgetExceeded`.
- Cache (`data/llm_cache.sqlite`): identical (model, system, prompt, params)
  requests return the stored reply at $0 (temperature 0 makes this sound).
"""

import datetime
import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from src.llm_client import LLMClient, LLMResponse

ROOT = Path(__file__).resolve().parent.parent
LEDGER_PATH = ROOT / "results" / "cost_ledger.jsonl"
BUDGET_PATH = ROOT / "configs" / "budget.yaml"
PRICES_PATH = ROOT / "configs" / "llm_prices.yaml"
CACHE_PATH = ROOT / "data" / "llm_cache.sqlite"
CHARS_PER_TOKEN = 3.0  # conservative (over-estimates tokens) for code + math unicode


class BudgetExceeded(RuntimeError):
    """Raised when a call would push spending over a configured cap."""


def load_prices() -> dict[str, dict[str, float]]:
    return yaml.safe_load(PRICES_PATH.read_text()) or {}


def price_usd(prices: dict[str, Any], model: str, inp: int, out: int) -> float:
    p = prices.get(model)
    if not p or p.get("input") is None or p.get("output") is None:
        raise BudgetExceeded(f"No price configured for {model}; refusing unpriced paid call")
    return (inp * p["input"] + out * p["output"]) / 1e6


class CostGuard:
    """Thread-safe spend tracker shared by all workers of a run.

    Args:
        run_id: Tag written into each ledger line.
        monthly_cap_usd / run_cap_usd: Override configs/budget.yaml.
        ledger_path: Where paid calls are appended.
    """

    def __init__(
        self,
        run_id: str,
        monthly_cap_usd: float | None = None,
        run_cap_usd: float | None = None,
        ledger_path: Path = LEDGER_PATH,
    ) -> None:
        cfg = yaml.safe_load(BUDGET_PATH.read_text()) if BUDGET_PATH.exists() else {}
        self.monthly_cap = monthly_cap_usd if monthly_cap_usd is not None else cfg.get(
            "monthly_cap_usd", 8.0)
        self.run_cap = run_cap_usd if run_cap_usd is not None else cfg.get("run_cap_usd", 2.0)
        self.run_id = run_id
        self.ledger_path = ledger_path
        self.prices = load_prices()
        self._lock = threading.Lock()
        self.run_spent = 0.0
        self.month_spent = self._month_total()
        self.calls = 0

    def _month_total(self) -> float:
        if not self.ledger_path.exists():
            return 0.0
        month = datetime.date.today().strftime("%Y-%m")
        total = 0.0
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                if rec["timestamp"].startswith(month):
                    total += rec["cost_usd"]
        return total

    def reserve(self, model: str, prompt_chars: int, max_output_tokens: int) -> float:
        """Checks the worst-case cost of a call against both caps; returns it."""
        worst = price_usd(self.prices, model, int(prompt_chars / CHARS_PER_TOKEN) + 1,
                          max_output_tokens)
        with self._lock:
            if self.run_spent + worst > self.run_cap:
                raise BudgetExceeded(
                    f"run cap ${self.run_cap:.2f} reached (spent ${self.run_spent:.4f})")
            if self.month_spent + worst > self.monthly_cap:
                raise BudgetExceeded(
                    f"monthly cap ${self.monthly_cap:.2f} reached (spent ${self.month_spent:.4f})")
        return worst

    def record(self, resp: LLMResponse) -> float:
        """Books the actual cost of a completed call into the ledger."""
        cost = price_usd(self.prices, resp.model, resp.input_tokens,
                         resp.output_tokens + resp.thinking_tokens)
        entry = {
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "run_id": self.run_id,
            "model": resp.model,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "thinking_tokens": resp.thinking_tokens,
            "cost_usd": round(cost, 8),
        }
        with self._lock:
            self.run_spent += cost
            self.month_spent += cost
            self.calls += 1
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        return cost


class ResponseCache:
    """SQLite cache of LLM replies keyed by a hash of the full request."""

    def __init__(self, path: Path = CACHE_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT)")
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(model: str, system: str | None, prompt: str, params: dict[str, Any]) -> str:
        blob = json.dumps([model, system, prompt, params], sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(blob.encode()).hexdigest()

    def get(self, key: str) -> LLMResponse | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
            if row is None:
                self.misses += 1
                return None
            self.hits += 1
        return LLMResponse(**json.loads(row[0]))

    def put(self, key: str, resp: LLMResponse) -> None:
        with self._lock:
            self._conn.execute("INSERT OR REPLACE INTO cache VALUES (?, ?)",
                               (key, json.dumps(asdict(resp), ensure_ascii=False)))
            self._conn.commit()


class GuardedClient:
    """Wraps an LLMClient with cache lookup, budget reservation and ledger booking.

    Cached replies keep their original token counts and latency (for replayable
    metrics) but are flagged so the run reports real spend separately.
    """

    def __init__(self, inner: LLMClient, guard: CostGuard, cache: ResponseCache | None,
                 max_output_tokens: int = 2048) -> None:
        self.inner = inner
        self.model = inner.model
        self.guard = guard
        self.cache = cache
        self.max_output_tokens = max_output_tokens
        self.params = {k: getattr(inner, k) for k in
                       ("temperature", "max_output_tokens", "seed", "thinking_level")
                       if hasattr(inner, k)}

    def complete(self, prompt: str, system: str | None = None) -> LLMResponse:
        key = ResponseCache.key(self.model, system, prompt, self.params)
        if self.cache is not None:
            cached = self.cache.get(key)
            if cached is not None:
                cached.cached = True
                return cached
        self.guard.reserve(self.model, len(prompt) + len(system or ""), self.max_output_tokens)
        resp = self.inner.complete(prompt, system)
        self.guard.record(resp)
        if self.cache is not None:
            self.cache.put(key, resp)
        return resp
