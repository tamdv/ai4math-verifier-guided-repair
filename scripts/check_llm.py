"""Smoke test for the LLM backend: lists usable Gemini models and runs one tiny call.

Usage:
    python3 scripts/check_llm.py [--model gemini-3.5-flash-lite] [--list]
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_client import GeminiClient, load_env  # noqa: E402

PROBE = (
    "Fix this Lean 4 code so it compiles. Reply with only the fixed code.\n\n"
    "theorem t (n : Nat) : n + 0 = n := by\n  simpp"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Gemini API access")
    parser.add_argument("--model", default="gemini-3.5-flash-lite")
    parser.add_argument("--list", action="store_true", help="List available Gemini models")
    args = parser.parse_args()

    load_env()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY not found in environment or .env")

    if args.list:
        from google import genai

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        for m in client.models.list():
            if "generateContent" in (m.supported_actions or []) and "gemini" in m.name:
                print(m.name)
        return

    resp = GeminiClient(model=args.model).complete(PROBE)
    print(f"[OK] model={resp.model} latency={resp.latency_ms:.0f}ms")
    print(
        f"     tokens in={resp.input_tokens} out={resp.output_tokens} "
        f"thinking={resp.thinking_tokens}"
    )
    print("     reply:\n" + resp.text)


if __name__ == "__main__":
    main()
