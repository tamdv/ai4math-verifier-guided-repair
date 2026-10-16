"""Error-injection operators: turn a verified Lean proof into a broken candidate.

Each operator targets one taxonomy category and returns the mutated code, or
None when it does not apply to the given proof. The intended category is only a
hint: the final label always comes from the real Lean diagnostics.
"""

import random
import re
from collections.abc import Callable
from dataclasses import dataclass

IMPORT_LINE = re.compile(r"^\s*import\s+.*$", re.MULTILINE)
DECL = re.compile(r"^(theorem|lemma)\s", re.MULTILINE)
LEMMA_NAME = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")
TACTIC_SWAPS = {
    "nlinarith": "nlinarth",
    "linarith": "linarth",
    "positivity": "positivty",
    "norm_num": "norm_nm",
    "simp": "smp",
    "omega": "omgea",
    "field_simp": "field_smp",
    "ring_nf": "ring_fn",
}
WEAKER_TACTIC = {"nlinarith": "linarith", "positivity": "linarith", "norm_num": "rfl",
                 "field_simp": "simp", "omega": "simp"}


@dataclass(frozen=True)
class Mutation:
    """Operator metadata."""

    name: str
    category: str
    fn: Callable[[str, random.Random], str | None]


def _split_decl(code: str) -> tuple[str, str] | None:
    """(prefix up to and incl. the statement's `:=`, proof part)."""
    m = DECL.search(code)
    if not m:
        return None
    idx = code.find(":=", m.end())
    if idx < 0:
        return None
    return code[: idx + 2], code[idx + 2 :]


def syn_drop_paren(code: str, rng: random.Random) -> str | None:
    """SYN_01: delete one closing parenthesis in the theorem statement."""
    parts = _split_decl(code)
    if not parts:
        return None
    head, proof = parts
    start = DECL.search(head).start()  # type: ignore[union-attr]
    positions = [i for i, ch in enumerate(head) if ch == ")" and i > start]
    if not positions:
        return None
    i = rng.choice(positions)
    return head[:i] + head[i + 1 :] + proof


def syn_drop_assign(code: str, rng: random.Random) -> str | None:
    """SYN_01: remove the `:=` between statement and proof."""
    parts = _split_decl(code)
    if not parts:
        return None
    head, proof = parts
    return head[:-2] + proof


def imp_drop_import(code: str, rng: random.Random) -> str | None:
    """IMP_02: remove all `import` lines (Mathlib no longer available)."""
    if not IMPORT_LINE.search(code):
        return None
    return IMPORT_LINE.sub("", code).lstrip("\n")


def id_lemma_typo(code: str, rng: random.Random) -> str | None:
    """ID_03: corrupt one lemma name used in the proof (drop a character)."""
    parts = _split_decl(code)
    if not parts:
        return None
    head, proof = parts
    body = re.sub(r"/-.*?-/", lambda m: " " * len(m.group(0)), proof, flags=re.DOTALL)
    names = sorted({m.group(1) for m in LEMMA_NAME.finditer(body)
                    if m.group(1) not in TACTIC_SWAPS and len(m.group(1)) > 5})
    if not names:
        return None
    name = rng.choice(names)
    cut = rng.randrange(1, len(name) - 1)
    typo = name[:cut] + name[cut + 1 :]
    # Locate the occurrence in the comment-blanked body (same offsets as `proof`).
    m = re.search(rf"\b{re.escape(name)}\b", body)
    assert m is not None
    return head + proof[: m.start()] + typo + proof[m.end() :]


def id_tactic_typo(code: str, rng: random.Random) -> str | None:
    """ID_03: misspell one tactic name."""
    parts = _split_decl(code)
    if not parts:
        return None
    head, proof = parts
    present = [t for t in TACTIC_SWAPS if re.search(rf"\b{t}\b", proof)]
    if not present:
        return None
    t = rng.choice(sorted(present))
    return head + re.sub(rf"\b{t}\b", TACTIC_SWAPS[t], proof, count=1)


def typ_change_type(code: str, rng: random.Random) -> str | None:
    """TYP_04: change one binder type ℝ -> ℕ (or ℕ -> ℝ) in the statement."""
    parts = _split_decl(code)
    if not parts:
        return None
    head, proof = parts
    hits = [m for m in re.finditer(r":\s*(ℝ|ℕ)\s*\)", head)]
    if not hits:
        return None
    m = rng.choice(hits)
    new = "ℕ" if m.group(1) == "ℝ" else "ℝ"
    return head[: m.start(1)] + new + head[m.end(1) :] + proof


def tac_weaken(code: str, rng: random.Random) -> str | None:
    """TAC_07: replace a strong closing tactic by a weaker one."""
    parts = _split_decl(code)
    if not parts:
        return None
    head, proof = parts
    present = [t for t in WEAKER_TACTIC if re.search(rf"\b{t}\b", proof)]
    if not present:
        return None
    t = rng.choice(sorted(present))
    # Drop the hint list of nlinarith/positivity calls so the weaker tactic is bare.
    pattern = rf"\b{t}\b(\s*\[[^\]]*\])?"
    return head + re.sub(pattern, WEAKER_TACTIC[t], proof, count=1)


def tmo_low_heartbeats(code: str, rng: random.Random) -> str | None:
    """TMO_05: cap heartbeats far below what the proof needs."""
    if "set_option maxHeartbeats" in code:
        return re.sub(r"set_option maxHeartbeats \d+", "set_option maxHeartbeats 500", code)
    m = DECL.search(code)
    if not m:
        return None
    return code[: m.start()] + "set_option maxHeartbeats 500 in\n" + code[m.start() :]


def sem_sorry(code: str, rng: random.Random) -> str | None:
    """SEM_06: replace the whole proof by `sorry` (compiles, proves nothing)."""
    parts = _split_decl(code)
    if not parts:
        return None
    head, _ = parts
    return head + " by\n  sorry\n"


MUTATIONS: list[Mutation] = [
    Mutation("syn_drop_paren", "SYN_01", syn_drop_paren),
    Mutation("syn_drop_assign", "SYN_01", syn_drop_assign),
    Mutation("imp_drop_import", "IMP_02", imp_drop_import),
    Mutation("id_lemma_typo", "ID_03", id_lemma_typo),
    Mutation("id_tactic_typo", "ID_03", id_tactic_typo),
    Mutation("typ_change_type", "TYP_04", typ_change_type),
    Mutation("tac_weaken", "TAC_07", tac_weaken),
    Mutation("tmo_low_heartbeats", "TMO_05", tmo_low_heartbeats),
    Mutation("sem_sorry", "SEM_06", sem_sorry),
]


def theorem_statement(code: str) -> str | None:
    """Normalized theorem statement (text before the proof's `:=`), for semantic audit."""
    parts = _split_decl(code)
    if not parts:
        return None
    head = parts[0][:-2]
    head = head[DECL.search(head).start() :]  # type: ignore[union-attr]
    return re.sub(r"\s+", " ", head).strip()
