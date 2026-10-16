"""Unit tests for budget caps, ledger and response cache (no network)."""

import tempfile
import unittest
from pathlib import Path

from src.cost_guard import BudgetExceeded, CostGuard, GuardedClient, ResponseCache
from src.llm_client import LLMResponse, MockClient


class PricedMock(MockClient):
    """Mock that reports tokens like a real model priced in configs/llm_prices.yaml."""

    def __init__(self) -> None:
        super().__init__(reply="ok", model="gemini-3.5-flash-lite")

    def complete(self, prompt, system=None):
        super().complete(prompt, system)
        return LLMResponse(text="ok", model=self.model, input_tokens=1000, output_tokens=1000)


class TestCostGuard(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name) / "ledger.jsonl"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def guard(self, run_cap=1.0, monthly_cap=1.0) -> CostGuard:
        return CostGuard("t", monthly_cap_usd=monthly_cap, run_cap_usd=run_cap,
                         ledger_path=self.ledger)

    def test_records_cost_and_persists_month_total(self) -> None:
        client = GuardedClient(PricedMock(), self.guard(), cache=None, max_output_tokens=10)
        client.complete("x")
        # 1000 in * 0.30 + 1000 out * 2.50 per 1M tokens
        self.assertAlmostEqual(client.guard.run_spent, 0.0028, places=6)
        self.assertAlmostEqual(self.guard().month_spent, 0.0028, places=6)

    def test_run_cap_blocks_call_before_spending(self) -> None:
        inner = PricedMock()
        client = GuardedClient(inner, self.guard(run_cap=0.001), cache=None,
                               max_output_tokens=2048)
        with self.assertRaises(BudgetExceeded):
            client.complete("x")
        self.assertEqual(inner.calls, [])  # the API was never called

    def test_monthly_cap_counts_previous_runs(self) -> None:
        GuardedClient(PricedMock(), self.guard(monthly_cap=0.004), None, 10).complete("a")
        second = GuardedClient(PricedMock(), self.guard(monthly_cap=0.004), None, 1000)
        with self.assertRaises(BudgetExceeded):
            second.complete("b")

    def test_unpriced_model_refused(self) -> None:
        client = GuardedClient(MockClient(model="unknown-model"), self.guard(), None)
        with self.assertRaises(BudgetExceeded):
            client.complete("x")

    def test_cache_hit_is_free(self) -> None:
        cache = ResponseCache(Path(self.tmp.name) / "c.sqlite")
        inner = PricedMock()
        client = GuardedClient(inner, self.guard(), cache, max_output_tokens=10)
        first = client.complete("same prompt", system="s")
        spent = client.guard.run_spent
        second = client.complete("same prompt", system="s")
        self.assertEqual(len(inner.calls), 1)
        self.assertEqual(client.guard.run_spent, spent)
        self.assertTrue(second.cached)
        self.assertFalse(first.cached)
        self.assertEqual(second.input_tokens, 1000)
        self.assertEqual((cache.hits, cache.misses), (1, 1))


if __name__ == "__main__":
    unittest.main()
