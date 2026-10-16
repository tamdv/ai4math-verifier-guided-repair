"""Bounded verifier-guided repair loop (router -> rule/LLM -> Lean -> audit -> retry).

Strategies (ablation axis):
- `none`:       no repair, measures the floor.
- `blind`:      assignment baseline, LLM sees the broken file only, no router/rules.
- `llm_only`:   LLM with structured Lean diagnostics, no rules.
- `rule_only`:  rules only (0 tokens).
- `hybrid`:     router sends rule-routable errors to rules first, LLM otherwise.

Every attempt is verified by Lean and audited; the loop stops on the first
audited success, when the attempt budget or wall-clock budget is exhausted, or
when a candidate repeats (dedup, prevents infinite loops on unrepairable input).
"""

import hashlib
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from src.error_parser import LeanErrorParser, RepairRoute
from src.llm_repair import LLMRepairEngine, strip_comments
from src.rule_repair import RuleRepairEngine
from src.semantic_auditor import audit
from src.verifier_pool import Verifier

STRATEGIES = ("none", "blind", "llm_only", "rule_only", "hybrid")
RULE_ROUTES = (RepairRoute.RULE_REPAIR, RepairRoute.HYBRID_REPAIR, RepairRoute.SYSTEM_CONTROL)


@dataclass
class RepairPolicy:
    """Knobs of one experiment configuration."""

    strategy: str = "hybrid"
    max_attempts: int = 1
    wall_budget_s: float = 300.0
    strip_comments: bool = True  # cost option C: drop comments, keep line numbers

    def __post_init__(self) -> None:
        if self.strategy not in STRATEGIES:
            raise ValueError(f"Unknown strategy {self.strategy}")


@dataclass
class Attempt:
    """One replayable repair step."""

    attempt: int
    engine: str
    rule: str | None
    category: str | None
    status: str
    compiled: bool
    audit_passed: bool
    audit_reasons: list[str]
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    llm_latency_ms: float
    verify_latency_ms: float
    candidate_sha256: str
    candidate_code: str


@dataclass
class RepairOutcome:
    """Final result for one error sample."""

    error_id: str
    strategy: str
    success: bool
    compiled: bool
    attempts_used: int
    stop_reason: str
    total_tokens: int
    llm_calls: int
    wall_ms: float
    final_category: str | None
    attempts: list[Attempt] = field(default_factory=list)

    def to_dict(self, include_code: bool = True) -> dict[str, Any]:
        d = asdict(self)
        if not include_code:
            for a in d["attempts"]:
                a.pop("candidate_code", None)
        return d


def _sha(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


class RepairPipeline:
    """Runs the bounded loop for one sample at a time (one instance per worker).

    Args:
        verifier: Lean verifier owned by the calling worker.
        policy: Strategy and budgets.
        llm_blind / llm_diag: LLM engines (required for LLM strategies).
    """

    def __init__(
        self,
        verifier: Verifier,
        policy: RepairPolicy,
        llm_blind: LLMRepairEngine | None = None,
        llm_diag: LLMRepairEngine | None = None,
    ) -> None:
        self.verifier = verifier
        self.policy = policy
        self.rules = RuleRepairEngine()
        self.llm_blind = llm_blind
        self.llm_diag = llm_diag
        if policy.strategy == "blind" and llm_blind is None:
            raise ValueError("blind strategy needs llm_blind")
        if policy.strategy in ("llm_only", "hybrid") and llm_diag is None:
            raise ValueError(f"{policy.strategy} strategy needs llm_diag")

    def _propose(
        self, code: str, diagnostics: list[dict[str, Any]], category: str | None,
        route: RepairRoute | None, tried_rule: set[str]
    ) -> tuple[str, str | None, str | None, dict[str, Any]]:
        """Returns (engine, rule, candidate_code, llm_usage) for the next attempt."""
        strategy = self.policy.strategy
        primary_msg = next((d["message"] for d in diagnostics if d.get("severity") == "error"), "")
        use_rules = strategy == "rule_only" or (strategy == "hybrid" and route in RULE_ROUTES)
        if use_rules and category:
            res = self.rules.repair_file(code, category, primary_msg)
            if res and res.rule_applied not in tried_rule:
                return "rule", res.rule_applied, res.repaired_code, {}
        if strategy == "rule_only":
            return "rule", None, None, {}
        engine = self.llm_blind if strategy == "blind" else self.llm_diag
        assert engine is not None
        att = engine.repair(code, diagnostics)
        usage = {
            "input_tokens": att.input_tokens,
            "output_tokens": att.output_tokens,
            "thinking_tokens": att.thinking_tokens,
            "llm_latency_ms": att.latency_ms,
        }
        return f"llm_{engine.mode}", None, att.repaired_code, usage

    def run(self, sample: dict[str, Any]) -> RepairOutcome:
        """Repairs one dataset record (fields: error_id, code, diagnostics, statement)."""
        start = time.perf_counter()
        code, diagnostics = sample["code"], sample["diagnostics"]
        if self.policy.strip_comments:
            code = strip_comments(code)
        reference = sample.get("statement")
        seen = {_sha(code)}
        tried_rules: set[str] = set()
        attempts: list[Attempt] = []
        stop = "budget_exhausted"
        success = compiled = False
        primary = LeanErrorParser.primary(diagnostics, code)

        if self.policy.strategy == "none" or self.policy.max_attempts == 0:
            stop = "no_repair"
        for n in range(1, self.policy.max_attempts + 1):
            if self.policy.strategy == "none":
                break
            if time.perf_counter() - start > self.policy.wall_budget_s:
                stop = "wall_budget"
                break
            category = primary.category.value if primary else None
            route = primary.route if primary else None
            engine, rule, candidate, usage = self._propose(
                code, diagnostics, category, route, tried_rules
            )
            if candidate is None:
                stop = "no_rule"
                break
            if rule:
                tried_rules.add(rule)
            digest = _sha(candidate)
            if digest in seen:
                attempts.append(Attempt(n, engine, rule, category, "DUPLICATE", False, False,
                                        ["duplicate_candidate"], usage.get("input_tokens", 0),
                                        usage.get("output_tokens", 0),
                                        usage.get("thinking_tokens", 0),
                                        usage.get("llm_latency_ms", 0.0), 0.0, digest, candidate))
                stop = "duplicate"
                break
            seen.add(digest)
            res = self.verifier.verify(candidate)
            verdict = audit(candidate, res, reference)
            attempts.append(Attempt(
                attempt=n, engine=engine, rule=rule, category=category, status=res.status,
                compiled=res.compiled, audit_passed=verdict.passed, audit_reasons=verdict.reasons,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                thinking_tokens=usage.get("thinking_tokens", 0),
                llm_latency_ms=usage.get("llm_latency_ms", 0.0),
                verify_latency_ms=res.latency_ms, candidate_sha256=digest,
                candidate_code=candidate,
            ))
            compiled = compiled or res.compiled
            if verdict.passed:
                success, stop = True, "success"
                break
            # Iterate on the latest candidate and its fresh diagnostics.
            code, diagnostics = candidate, res.diagnostics
            primary = LeanErrorParser.primary(diagnostics, code)

        return RepairOutcome(
            error_id=sample.get("error_id", ""),
            strategy=self.policy.strategy,
            success=success,
            compiled=compiled,
            attempts_used=len(attempts),
            stop_reason=stop,
            total_tokens=sum(a.input_tokens + a.output_tokens + a.thinking_tokens
                             for a in attempts),
            llm_calls=sum(a.engine.startswith("llm") for a in attempts),
            wall_ms=round((time.perf_counter() - start) * 1000, 3),
            final_category=primary.category.value if primary else None,
            attempts=attempts,
        )
