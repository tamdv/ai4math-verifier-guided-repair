"""Semantic safety audit: a repair only counts if it proves the *original* statement.

Checks (all must pass):
1. Lean accepted the file and no declaration uses `sorry`.
2. No escape hatches in the source (`sorry`, `admit`, `axiom`, `native_decide`, ...).
3. The theorem statement (name, binders, goal) is unchanged versus the reference,
   compared after whitespace normalization.

Limitation: (3) is textual, so a semantically equivalent but re-formatted
statement is flagged as changed (conservative: may under-count successes, never
over-counts them).
"""

import re
from dataclasses import dataclass, field

from src.lean_verifier import VerificationResult
from src.mutations import theorem_statement

FORBIDDEN = re.compile(
    r"\bsorry\b|\badmit\b|^\s*axiom\b|\bnative_decide\b|\bimplemented_by\b|@\[extern|\bunsafe\b",
    re.MULTILINE,
)
COMMENT = re.compile(r"/-.*?-/|--[^\n]*", re.DOTALL)


@dataclass
class AuditResult:
    """Outcome of the semantic audit."""

    passed: bool
    reasons: list[str] = field(default_factory=list)


def normalize_statement(stmt: str | None) -> str | None:
    """Collapses whitespace (and spaces around brackets) for comparison."""
    if stmt is None:
        return None
    stmt = re.sub(r"\s+", " ", stmt).strip()
    return re.sub(r"\s*([(){}\[\]:,])\s*", r"\1", stmt)


def audit(
    candidate_code: str, verification: VerificationResult, reference_statement: str | None
) -> AuditResult:
    """Audits a compiled repair against the reference theorem statement.

    Args:
        candidate_code: Repaired Lean source.
        verification: Lean result for `candidate_code`.
        reference_statement: Statement of the intended theorem (from the seed
            proof for synthetic samples, from the broken file for natural ones).
    """
    reasons = []
    if not verification.compiled:
        reasons.append("does_not_compile")
    if verification.uses_sorry:
        reasons.append("uses_sorry")
    if FORBIDDEN.search(COMMENT.sub(" ", candidate_code)):
        reasons.append("forbidden_construct")
    if reference_statement is not None:
        cand = normalize_statement(theorem_statement(candidate_code))
        if cand is None:
            reasons.append("theorem_missing")
        elif cand != normalize_statement(reference_statement):
            reasons.append("statement_changed")
    return AuditResult(passed=not reasons, reasons=reasons)
