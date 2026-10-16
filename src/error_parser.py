"""Structured Lean 4 Compiler Error Parser & Taxonomy Classifier.

Rules are matched against real Lean 4 (v4.35) diagnostic text. Order matters:
the first matching rule wins, from most to least specific.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ErrorCategory(str, Enum):
    """Normalized Lean 4 error categories (taxonomy v0.2)."""
    SYNTAX_ERROR = "SYN_01"
    MISSING_IMPORT = "IMP_02"
    UNKNOWN_IDENTIFIER = "ID_03"
    TYPE_MISMATCH = "TYP_04"
    TIMEOUT_EXCEEDED = "TMO_05"
    SEMANTIC_MISMATCH = "SEM_06"
    TACTIC_FAILURE = "TAC_07"
    UNKNOWN = "UNK_99"


class RepairRoute(str, Enum):
    """Routing destinations based on error characteristics."""
    RULE_REPAIR = "rule_repair"
    LLM_REPAIR = "llm_repair"
    HYBRID_REPAIR = "hybrid_repair"
    SYSTEM_CONTROL = "system_control"
    SEMANTIC_AUDIT = "semantic_audit"


@dataclass
class DiagnosticRecord:
    """Structured diagnostic representation."""
    line: int
    column: int
    severity: str
    message: str
    category: ErrorCategory
    route: RepairRoute
    raw_payload: Optional[dict[str, Any]] = None


# (substring patterns, category, route) in priority order; matched on lowercase text.
_RULES: list[tuple[tuple[str, ...], ErrorCategory, RepairRoute]] = [
    (
        ("heartbeats", "deterministic) timeout", "timeout at", "deep recursion",
         "timed out", "maximum recursion depth"),
        ErrorCategory.TIMEOUT_EXCEEDED,
        RepairRoute.SYSTEM_CONTROL,
    ),
    (
        ("unknown package", "module not found", "failed to import", "unknown module prefix",
         "module does not exist", "of module", "unknown module"),
        ErrorCategory.MISSING_IMPORT,
        RepairRoute.RULE_REPAIR,
    ),
    (
        ("unexpected token", "expected token", "unexpected end of input", "unterminated",
         "unclosed", "expected ':='", "expected command", "expected term", "expected '"),
        ErrorCategory.SYNTAX_ERROR,
        RepairRoute.RULE_REPAIR,
    ),
    (
        ("unknown identifier", "unknown constant", "unknown tactic", "unknown theorem",
         "unknown namespace", "invalid field `", "invalid dotted identifier",
         "has been deprecated"),
        ErrorCategory.UNKNOWN_IDENTIFIER,
        RepairRoute.HYBRID_REPAIR,
    ),
    (
        ("type mismatch", "failed to synthesize", "cannot be unified with",
         "dimension mismatch", "subtype violation", "invalid field notation",
         "function expected", "don't know how to synthesize"),
        ErrorCategory.TYPE_MISMATCH,
        RepairRoute.LLM_REPAIR,
    ),
    (
        ("unsolved goals", "linarith failed", "nlinarith failed", "omega could not prove",
         "could not prove", "failed to prove", "made no progress", "tactic `", "tactic '",
         "is false", "positivity failed", "ring failed", "no goals to be proved",
         "failed with a nested error", "not a valid", "contradiction failed",
         "not a positivity goal", "no goals to be solved", "has not been provided",
         "interval_cases failed", "nlinarith failed", "decide failed"),
        ErrorCategory.TACTIC_FAILURE,
        RepairRoute.LLM_REPAIR,
    ),
    (
        ("uses sorry", "uses `sorry`", "altered quantifier", "dubious assumption"),
        ErrorCategory.SEMANTIC_MISMATCH,
        RepairRoute.SEMANTIC_AUDIT,
    ),
]

# Names that only exist with Mathlib imported; their presence in import-less code
# means an "unknown identifier" is really a missing import.
_MATHLIB_MARKERS = re.compile(
    r"ℝ|ℚ|ℂ|\bReal\b|\bFinset\b|\bnlinarith\b|\bpositivity\b|\bnorm_num\b|\bfield_simp\b"
    r"|\blinarith\b|\bpolyrith\b|\bsq_nonneg\b|\bmul_pos\b"
)
_IMPORT_LINE = re.compile(r"^\s*import\s", re.MULTILINE)


def _is_consequence(message: str) -> bool:
    return message.lower().startswith("unsolved goals")


class LeanErrorParser:
    """Parses raw Lean compiler diagnostics into structured categories and routes."""

    @staticmethod
    def classify_message(
        message: str, code: str | None = None
    ) -> tuple[ErrorCategory, RepairRoute]:
        """Maps a Lean message (and optionally the source code) to a category and route.

        Args:
            message: Diagnostic text from Lean.
            code: Full source; when given, enables missing-import detection for
                code that uses Mathlib names without importing Mathlib.
        """
        msg_lower = message.lower()

        if (
            code is not None
            and not _IMPORT_LINE.search(code)
            and _MATHLIB_MARKERS.search(code)
            and any(p in msg_lower for p in ("unknown", "unexpected token", "expected"))
        ):
            return ErrorCategory.MISSING_IMPORT, RepairRoute.RULE_REPAIR

        for patterns, category, route in _RULES:
            if any(p in msg_lower for p in patterns):
                return category, route
        return ErrorCategory.UNKNOWN, RepairRoute.LLM_REPAIR

    @classmethod
    def parse_diagnostic(
        cls, diag_dict: dict[str, Any], code: str | None = None
    ) -> DiagnosticRecord:
        """Parses a dictionary diagnostic message."""
        line = diag_dict.get("line", 1)
        col = diag_dict.get("column", 1)
        severity = diag_dict.get("severity", "error")
        message = diag_dict.get("message", "")

        cat, route = cls.classify_message(message, code)
        return DiagnosticRecord(
            line=line,
            column=col,
            severity=severity,
            message=message,
            category=cat,
            route=route,
            raw_payload=diag_dict
        )

    @classmethod
    def primary(
        cls, diagnostics: list[dict[str, Any]], code: str | None = None
    ) -> DiagnosticRecord | None:
        """Classifies the root-cause error (or, failing that, the first sorry warning).

        `unsolved goals` is reported at the declaration (an earlier position) as a
        *consequence* of a broken tactic below it, so it only wins when it is the
        sole kind of error.
        """
        errors = [d for d in diagnostics if d.get("severity") == "error"]
        causes = [d for d in errors if not _is_consequence(d.get("message", ""))]
        if causes:
            errors = causes
        if errors:
            first = min(errors, key=lambda d: (d.get("line") or 0, d.get("column") or 0))
            return cls.parse_diagnostic(first, code)
        sorry = [d for d in diagnostics if "sorry" in d.get("message", "")]
        if sorry:
            return cls.parse_diagnostic(sorry[0], code)
        return None
