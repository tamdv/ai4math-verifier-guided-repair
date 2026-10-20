"""LLM repair engine: one repair attempt per call, blind (baseline) or diagnostic-guided.

- `blind`: the broken file only (assignment baseline: retry without structured
  Lean messages and without error classification).
- `diagnostic`: numbered source + parsed Lean diagnostics with taxonomy labels.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.error_parser import LeanErrorParser
from src.llm_client import LLMClient

PROMPT_DIR = Path(__file__).resolve().parent.parent / "configs" / "prompts"
CODE_BLOCK = re.compile(r"```(?:lean4?|Lean)?\s*\n(.*?)```", re.DOTALL)
MAX_DIAGNOSTICS = 5
MAX_MESSAGE_CHARS = 400


@dataclass
class RepairAttempt:
    """Output of one LLM call."""

    repaired_code: str
    mode: str
    model: str
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    latency_ms: float
    prompt_version: str


def load_prompts(version: str = "repair_v1") -> dict[str, Any]:
    """Loads a prompt template file from configs/prompts/."""
    import yaml  # only needed for live LLM calls; replay demo runs on the standard library

    with open(PROMPT_DIR / f"{version}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_code(text: str) -> str:
    """Returns the last fenced code block, or the raw text if there is none."""
    blocks = CODE_BLOCK.findall(text)
    return (blocks[-1] if blocks else text).strip() + "\n"


def strip_comments(code: str) -> str:
    """Removes Lean comments (`-- ...`, nested `/- ... -/`, docstrings) to save tokens.

    Lines *and* columns are preserved: comment characters become spaces (Lean
    tactic blocks are indentation-sensitive, and diagnostics carry line:column),
    then trailing whitespace is trimmed, so comment-only lines become empty.
    """
    out: list[str] = []
    i, depth, n = 0, 0, len(code)
    while i < n:
        two = code[i : i + 2]
        if depth == 0 and two == "--":
            while i < n and code[i] != "\n":
                i += 1
            continue
        if two == "/-":
            depth += 1
            out.append("  ")
            i += 2
            continue
        if depth > 0 and two == "-/":
            depth -= 1
            out.append("  ")
            i += 2
            continue
        if depth > 0:
            out.append("\n" if code[i] == "\n" else " ")
            i += 1
            continue
        out.append(code[i])
        i += 1
    return "\n".join(line.rstrip() for line in "".join(out).split("\n"))


def number_lines(code: str) -> str:
    return "\n".join(f"{i:>3}| {line}" for i, line in enumerate(code.splitlines(), 1))


def format_diagnostics(diagnostics: list[dict[str, Any]], code: str) -> str:
    """Renders error diagnostics (errors first, then sorry warnings) for the prompt."""
    errors = [d for d in diagnostics if d.get("severity") == "error"]
    rest = [d for d in diagnostics if d.get("severity") != "error" and "sorry" in d.get("message", "")]
    lines = []
    for d in (errors + rest)[:MAX_DIAGNOSTICS]:
        record = LeanErrorParser.parse_diagnostic(d, code)
        msg = d.get("message", "").strip()
        if len(msg) > MAX_MESSAGE_CHARS:
            msg = msg[:MAX_MESSAGE_CHARS] + " ..."
        lines.append(f"- {d.get('line', 0)}:{d.get('column', 0)} [{record.category.value}] {msg}")
    return "\n".join(lines) if lines else "- (no diagnostics)"


class LLMRepairEngine:
    """Builds the prompt for the chosen mode and calls the LLM once.

    Args:
        client: Any `LLMClient` backend.
        mode: "blind" or "diagnostic".
        prompt_version: Template file name under configs/prompts/.
    """

    def __init__(self, client: LLMClient, mode: str = "diagnostic",
                 prompt_version: str = "repair_v1") -> None:
        if mode not in ("blind", "diagnostic"):
            raise ValueError(f"Unknown mode: {mode}")
        self.client = client
        self.mode = mode
        self.prompts = load_prompts(prompt_version)
        self.prompt_version = self.prompts.get("version", prompt_version)

    def build_prompt(self, code: str, diagnostics: list[dict[str, Any]]) -> str:
        """Renders the user prompt for `code` (diagnostics ignored in blind mode)."""
        code = code.rstrip("\n")
        if self.mode == "blind":
            return self.prompts["blind"].format(code=code)
        return self.prompts["diagnostic"].format(
            numbered_code=number_lines(code),
            diagnostics=format_diagnostics(diagnostics, code),
        )

    def repair(self, code: str, diagnostics: list[dict[str, Any]]) -> RepairAttempt:
        """One LLM repair attempt."""
        resp = self.client.complete(self.build_prompt(code, diagnostics),
                                    system=self.prompts["system"])
        return RepairAttempt(
            repaired_code=extract_code(resp.text),
            mode=self.mode,
            model=resp.model,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
            thinking_tokens=resp.thinking_tokens,
            latency_ms=resp.latency_ms,
            prompt_version=self.prompt_version,
        )
